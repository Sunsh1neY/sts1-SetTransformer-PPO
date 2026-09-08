"""D25 S3：用手算样例验证 GAE、PPO 裁剪和掩码梯度。"""

from __future__ import annotations

import math

import pytest
import torch
from torch.distributions import Categorical

from sts.train.ppo import compute_gae, ppo_loss


def _float(values):
    return torch.tensor(values, dtype=torch.float64)


def _bool(values):
    return torch.tensor(values, dtype=torch.bool)


def _loss_inputs(batch_size=2):
    return {
        "new_logprob": torch.full((batch_size,), -1.0, dtype=torch.float64),
        "old_logprob": torch.full((batch_size,), -1.0, dtype=torch.float64),
        "advantages": torch.ones(batch_size, dtype=torch.float64),
        "new_value": torch.zeros(batch_size, dtype=torch.float64),
        "old_value": torch.zeros(batch_size, dtype=torch.float64),
        "returns": torch.zeros(batch_size, dtype=torch.float64),
        "entropy": torch.zeros(batch_size, dtype=torch.float64),
    }


@pytest.mark.parametrize("terminal_next_value", [1_000_000.0, -1_000_000.0])
def test_gae_真正终止时忽略下一状态的巨大价值(terminal_next_value):
    advantages, returns = compute_gae(
        _float([[0.0], [1.0]]),
        _float([[0.25], [0.5]]),
        _float([[0.5], [terminal_next_value]]),
        _bool([[False], [True]]),
        gamma=1.0,
        gae_lambda=1.0,
    )
    # 两步的最终回报都是 1，优势分别减去各自的价值预测。
    torch.testing.assert_close(advantages, _float([[0.75], [0.5]]))
    torch.testing.assert_close(returns, _float([[1.0], [1.0]]))


def test_gae_非终止的rollout末尾从实际下一状态bootstrap():
    advantages, returns = compute_gae(
        _float([[1.0], [2.0]]),
        _float([[0.5], [1.0]]),
        _float([[1.0], [4.0]]),
        _bool([[False], [False]]),
        gamma=0.5,
        gae_lambda=1.0,
    )
    # 最后一步目标为 2 + 0.5 * 4 = 4；前一步目标为 1 + 0.5 * 4 = 3。
    torch.testing.assert_close(advantages, _float([[2.5], [3.0]]))
    torch.testing.assert_close(returns, _float([[3.0], [4.0]]))


def test_gae_两个环境分别递推并尊重各自终止位置():
    advantages, returns = compute_gae(
        _float([[1.0, 10.0], [2.0, 20.0]]),
        _float([[0.0, 0.0], [0.0, 0.0]]),
        _float([[999.0, 0.0], [4.0, 999.0]]),
        _bool([[True, False], [False, True]]),
        gamma=1.0,
        gae_lambda=0.5,
    )
    # 环境 0 首步已终止；环境 1 首步累加下一步优势的一半。
    expected = _float([[1.0, 20.0], [6.0, 20.0]])
    torch.testing.assert_close(advantages, expected)
    torch.testing.assert_close(returns, expected)


def test_gae_未来优势同时乘折扣和lambda():
    advantages, returns = compute_gae(
        _float([[1.0], [2.0], [3.0]]),
        _float([[0.5], [1.0], [1.5]]),
        _float([[1.0], [1.5], [999.0]]),
        _bool([[False], [False], [True]]),
        gamma=0.9,
        gae_lambda=0.8,
    )
    # 残差为 [1.4, 2.35, 1.5]；每向前一步，未来优势乘 0.72。
    torch.testing.assert_close(advantages, _float([[3.8696], [3.43], [1.5]]))
    torch.testing.assert_close(returns, _float([[4.3696], [4.43], [3.0]]))


def test_gae_截断保留bootstrap但不把重置后新局串入优势():
    arguments = {
        "rewards": _float([[1.0], [100.0]]),
        "values": _float([[0.5], [10.0]]),
        "next_values": _float([[4.0], [999.0]]),
        "terminated": _bool([[False], [True]]),
        "gamma": 0.5,
        "gae_lambda": 1.0,
    }
    advantages, returns = compute_gae(
        **arguments, episode_ends=_bool([[True], [True]])
    )
    # 第一局截断目标为 1 + 0.5 * 4 = 3，第二局的 100 不应影响它。
    torch.testing.assert_close(advantages, _float([[2.5], [90.0]]))
    torch.testing.assert_close(returns, _float([[3.0], [100.0]]))
    # 未声明截断时，两步属于同一轨迹，第一步应多出 0.5 * 90。
    continuous_advantages, _ = compute_gae(**arguments)
    torch.testing.assert_close(continuous_advantages, _float([[47.5], [90.0]]))


def test_r9_rollout边界自举而真终局失败不自举():
    advantages, returns = compute_gae(
        _float([[0.0, 0.0]]),
        _float([[0.3, 0.3]]),
        _float([[0.4, 0.4]]),
        _bool([[False, True]]),
        gamma=1.0,
        gae_lambda=0.95,
    )
    torch.testing.assert_close(advantages, _float([[0.1, -0.3]]))
    torch.testing.assert_close(returns, _float([[0.4, 0.0]]))


def test_r10_外部截断用旧episode最终观测自举且不跨reset():
    advantages, returns = compute_gae(
        _float([[0.0], [100.0]]),
        _float([[0.3], [10.0]]),
        _float([[0.4], [999.0]]),
        _bool([[False], [True]]),
        truncated=_bool([[True], [False]]),
        gamma=1.0,
        gae_lambda=1.0,
    )
    torch.testing.assert_close(advantages, _float([[0.1], [90.0]]))
    torch.testing.assert_close(returns, _float([[0.4], [100.0]]))


@pytest.mark.parametrize(
    ("ratio", "advantage", "expected_loss", "expected_gradient"),
    [
        (1.5, 1.0, -1.2, 0.0),
        (0.5, -1.0, 0.8, 0.0),
        (0.5, 1.0, -0.5, -0.25),
        (1.5, -1.0, 1.5, 0.75),
    ],
)
def test_ppo_正负优势只在改善方向越界时产生裁剪饱和(
    ratio, advantage, expected_loss, expected_gradient
):
    inputs = _loss_inputs()
    inputs["new_logprob"] = torch.full(
        (2,), -1.0 + math.log(ratio), dtype=torch.float64, requires_grad=True
    )
    inputs["advantages"] = torch.full((2,), advantage, dtype=torch.float64)
    loss, metrics = ppo_loss(**inputs, norm_adv=False, vf_coef=0.0, ent_coef=0.0)
    assert loss.item() == pytest.approx(expected_loss)
    assert metrics["policy_loss"].item() == pytest.approx(expected_loss)
    assert metrics["clip_fraction"].item() == pytest.approx(1.0)
    loss.backward()
    torch.testing.assert_close(
        inputs["new_logprob"].grad,
        torch.full((2,), expected_gradient, dtype=torch.float64),
    )


def test_ppo_同一策略ratio为一时kl和裁剪比例为零():
    inputs = _loss_inputs()
    inputs["advantages"] = _float([2.0, -1.0])
    inputs["entropy"] = _float([0.5, 1.5])
    loss, metrics = ppo_loss(**inputs, norm_adv=False, vf_coef=0.0, ent_coef=0.1)
    assert loss.item() == pytest.approx(-0.6)
    assert metrics["policy_loss"].item() == pytest.approx(-0.5)
    assert metrics["entropy"].item() == pytest.approx(1.0)
    assert metrics["approx_kl"].item() == pytest.approx(0.0, abs=1e-12)
    assert metrics["clip_fraction"].item() == pytest.approx(0.0)


def test_ppo_使用掩码后的logprob时非法动作概率和梯度均为零():
    logits = _float([[0.0, 100.0, 0.0], [0.0, 100.0, 0.0]]).requires_grad_()
    mask = _bool([[True, False, True], [True, False, True]])
    distribution = Categorical(logits=logits.masked_fill(~mask, -torch.inf))
    actions = torch.tensor([0, 2])
    inputs = _loss_inputs()
    inputs["new_logprob"] = distribution.log_prob(actions)
    inputs["old_logprob"] = inputs["new_logprob"].detach().clone()
    inputs["entropy"] = distribution.entropy()
    loss, _ = ppo_loss(**inputs, norm_adv=False, vf_coef=0.0, ent_coef=0.0)
    loss.backward()
    torch.testing.assert_close(distribution.probs[:, 1], _float([0.0, 0.0]))
    # 每个合法动作概率为 1/2，两个样本均值使策略梯度再除以 2。
    torch.testing.assert_close(
        logits.grad, _float([[-0.25, 0.0, 0.25], [0.25, 0.0, -0.25]])
    )


@pytest.mark.parametrize(
    ("clip_value", "expected_value_loss"), [(True, 109.0 / 120.0), (False, 481.0 / 600.0)]
)
def test_ppo_价值裁剪取两种平方误差的较大者(clip_value, expected_value_loss):
    inputs = _loss_inputs(3)
    inputs["advantages"] = _float([0.0, 0.0, 0.0])
    inputs["new_value"] = _float([1.0, -1.0, 0.1]).requires_grad_()
    inputs["returns"] = _float([1.0, 1.0, 1.0])
    loss, metrics = ppo_loss(
        **inputs, norm_adv=False, vf_coef=1.0, ent_coef=0.0, clip_value=clip_value
    )
    # 裁剪后 max 误差为 [0.64, 4, 0.81]，未裁剪为 [0, 4, 0.81]。
    assert metrics["value_loss"].item() == pytest.approx(expected_value_loss)
    assert loss.item() == pytest.approx(expected_value_loss)
    loss.backward()
    torch.testing.assert_close(inputs["new_value"].grad, _float([0.0, -2.0 / 3.0, -0.3]))


def test_ppo_常数优势归一化后没有nan且策略梯度为零():
    inputs = _loss_inputs()
    inputs["advantages"] = _float([4.0, 4.0])
    inputs["new_logprob"].requires_grad_()
    loss, metrics = ppo_loss(**inputs, norm_adv=True, vf_coef=0.0, ent_coef=0.0)
    assert torch.isfinite(loss)
    assert all(torch.isfinite(value).all() for value in metrics.values())
    assert metrics["policy_loss"].item() == pytest.approx(0.0)
    loss.backward()
    torch.testing.assert_close(inputs["new_logprob"].grad, _float([0.0, 0.0]))


def test_ppo_单样本优势归一化拒绝但关闭归一化可计算():
    inputs = _loss_inputs(1)
    with pytest.raises(ValueError):
        ppo_loss(**inputs, norm_adv=True)
    loss, _ = ppo_loss(**inputs, norm_adv=False, vf_coef=0.0, ent_coef=0.0)
    assert loss.item() == pytest.approx(-1.0)


@pytest.mark.parametrize("field", list(_loss_inputs()))
def test_ppo_拒绝各输入长度不一致以防广播(field):
    inputs = _loss_inputs()
    inputs[field] = inputs[field][:1]
    with pytest.raises(ValueError):
        ppo_loss(**inputs)


def test_ppo_拒绝二维小批以防广播产生交叉样本项():
    inputs = {name: value.unsqueeze(1) for name, value in _loss_inputs().items()}
    with pytest.raises(ValueError):
        ppo_loss(**inputs)


@pytest.mark.parametrize(
    "field", ["rewards", "values", "next_values", "terminated", "episode_ends"]
)
def test_gae_拒绝各输入形状不一致以防环境维广播(field):
    arguments = {
        "rewards": _float([[1.0, 2.0], [3.0, 4.0]]),
        "values": _float([[0.0, 0.0], [0.0, 0.0]]),
        "next_values": _float([[0.0, 0.0], [0.0, 0.0]]),
        "terminated": _bool([[False, False], [True, True]]),
        "episode_ends": _bool([[False, False], [True, True]]),
    }
    arguments[field] = arguments[field][:, :1]
    with pytest.raises(ValueError):
        compute_gae(**arguments)


def test_gae_拒绝缺少环境维的一维输入():
    with pytest.raises(ValueError):
        compute_gae(
            _float([1.0, 2.0]),
            _float([0.0, 0.0]),
            _float([0.0, 0.0]),
            _bool([False, True]),
        )
