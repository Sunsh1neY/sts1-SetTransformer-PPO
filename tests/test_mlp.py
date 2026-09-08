"""D25 S1：MLP 输入、掩码、梯度与 checkpoint 契约测试。"""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest
import torch

from sts import Encounter, FlattenWrapper, LightspeedBattleEnv
from sts.env.registry import CardDefinition, CardRegistry, TargetKind
from sts.models import (
    MlpActorCritic,
    MlpConfig,
    batch_flat_inputs,
    load_mlp_checkpoint,
    save_mlp_checkpoint,
)


def test_mlp_固定尺度保留hp和energy的数值梯度():
    torch.manual_seed(20260906)
    batch = batch_flat_inputs(_observations())
    model = MlpActorCritic(MlpConfig.from_registry())
    batch["global_values"].requires_grad_()
    pre_tanh = model.global_projection[0](batch["global_values"] / model.global_scales)
    assert pre_tanh.abs().max() < 3.0
    _, value = model(batch)
    value.sum().backward()
    gradient = batch["global_values"].grad
    assert torch.isfinite(gradient).all()
    assert (gradient[:, [0, 3]].abs() > 1e-6).all()
    changed = dict(batch)
    changed["global_values"] = batch["global_values"].detach().clone()
    changed["global_values"][:, 0] -= 10
    changed["global_values"][:, 3] -= 1
    assert not torch.allclose(model(changed)[1], value)


def test_mlp_checkpoint_拒绝缩放篡改(tmp_path):
    path = tmp_path / "mlp.pt"
    save_mlp_checkpoint(path, MlpActorCritic(MlpConfig.from_registry()))
    payload = torch.load(path, weights_only=True)
    payload["model_state_dict"]["global_scales"][0] = 1.0
    torch.save(payload, path)
    with pytest.raises(ValueError, match="缩放常量"):
        load_mlp_checkpoint(path)


def _observations():
    observations = []
    for offset, encounter in enumerate(Encounter):
        env = FlattenWrapper(LightspeedBattleEnv())
        observations.append(env.reset(100000 + offset, encounter))
    return observations


def test_mlp_批量前向并在softmax前屏蔽非法动作():
    torch.manual_seed(20260906)
    observations = _observations()
    batch = batch_flat_inputs(observations)
    model = MlpActorCritic(MlpConfig.from_registry())

    logits, values = model(batch)
    distribution, checked_values, masked_logits = model.distribution_and_value(batch)
    probabilities = distribution.probs.detach().numpy()
    masks = np.stack([item["action_mask"] for item in observations])

    assert logits.shape == (3, 31)
    assert values.shape == (3,)
    assert torch.equal(values, checked_values)
    assert masked_logits.shape == (3, 31)
    assert np.all(probabilities[~masks] == 0.0)
    assert np.allclose(probabilities.sum(axis=1), 1.0)
    assert torch.isfinite(masked_logits[batch["action_mask"]]).all()
    assert torch.isneginf(masked_logits[~batch["action_mask"]]).all()


def test_mlp_反向梯度有限且优化器确实更新参数():
    torch.manual_seed(20260906)
    batch = batch_flat_inputs(_observations())
    model = MlpActorCritic(MlpConfig.from_registry())
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    legal_actions = batch["action_mask"].float().argmax(dim=1)
    before = {name: value.detach().clone() for name, value in model.named_parameters()}

    _, log_prob, entropy, value, _ = model.action_and_value(batch, legal_actions)
    loss = -log_prob.mean() + 0.5 * value.square().mean() - 0.01 * entropy.mean()
    optimizer.zero_grad()
    loss.backward()

    gradients = [parameter.grad for parameter in model.parameters() if parameter.grad is not None]
    assert gradients
    assert all(torch.isfinite(gradient).all() for gradient in gradients)
    optimizer.step()
    assert any(
        not torch.equal(before[name], parameter.detach())
        for name, parameter in model.named_parameters()
    )


def test_mlp_checkpoint_重载输出一致且拒绝注册表漂移(tmp_path):
    torch.manual_seed(20260906)
    batch = batch_flat_inputs(_observations())
    model = MlpActorCritic(MlpConfig.from_registry()).eval()
    checkpoint = tmp_path / "mlp-smoke.pt"
    with torch.no_grad():
        expected = model(batch)

    save_mlp_checkpoint(checkpoint, model, extra={"purpose": "S1"})
    restored, payload = load_mlp_checkpoint(checkpoint)
    restored.eval()
    with torch.no_grad():
        actual = restored(batch)

    assert payload["extra"] == {"purpose": "S1"}
    assert all(torch.equal(left, right) for left, right in zip(expected, actual))

    changed_registry = CardRegistry(
        (
            CardDefinition(1, 25, "Bash", TargetKind.ENEMY),
            CardDefinition(2, 104, "Defend", TargetKind.NO_TARGET),
            CardDefinition(3, 321, "Strike", TargetKind.ENEMY),
            CardDefinition(4, 999999, "Synthetic Probe", TargetKind.ENEMY),
        ),
        version=2,
    )
    with pytest.raises(ValueError, match="输入契约不匹配"):
        load_mlp_checkpoint(checkpoint, registry=changed_registry)


def test_mlp_拒绝损坏输入与全非法非终局批量():
    observation = _observations()[0]
    wrong_dtype = deepcopy(observation)
    wrong_dtype["card_categorical"] = wrong_dtype["card_categorical"].astype(
        np.float32
    )
    with pytest.raises(TypeError, match="card_categorical dtype"):
        batch_flat_inputs([wrong_dtype])

    no_legal = deepcopy(observation)
    no_legal["action_mask"][:] = False
    batch = batch_flat_inputs([no_legal])
    model = MlpActorCritic(MlpConfig.from_registry())
    with pytest.raises(ValueError, match="至少需要一个合法动作"):
        model.distribution_and_value(batch)


def test_mlp_拒绝广播动作与非法动作并保持逐样本logprob():
    batch = batch_flat_inputs(_observations())
    model = MlpActorCritic(MlpConfig.from_registry())
    actions = batch["action_mask"].long().argmax(dim=1)
    distribution, _, _ = model.distribution_and_value(batch)
    chosen, log_prob, _, _, _ = model.action_and_value(batch, actions)
    assert torch.equal(chosen, actions)
    assert log_prob.shape == (3,)
    torch.testing.assert_close(log_prob, distribution.log_prob(actions))

    # [B,1] 与 [B] 的广播会产生 [B,B]，混淆不同环境的动作与状态。
    for wrong_shape in (actions[:, None], actions[0], actions[:1]):
        with pytest.raises(ValueError, match="action shape"):
            model.action_and_value(batch, wrong_shape)
    for wrong_dtype in (actions.float(), actions.bool()):
        with pytest.raises(TypeError, match="torch.int64"):
            model.action_and_value(batch, wrong_dtype)
    for out_of_range in (-1, 31):
        with pytest.raises(ValueError, match="action 必须在"):
            model.action_and_value(batch, torch.full_like(actions, out_of_range))
    illegal = (~batch["action_mask"]).long().argmax(dim=1)
    with pytest.raises(ValueError, match="非法动作"):
        model.action_and_value(batch, illegal)


def test_mlp_checkpoint_拒绝词表容量与注册表标签矛盾(tmp_path):
    model = MlpActorCritic(MlpConfig.from_registry())
    expanded = CardRegistry(
        (
            CardDefinition(1, 25, "Bash", TargetKind.ENEMY),
            CardDefinition(2, 104, "Defend", TargetKind.NO_TARGET),
            CardDefinition(3, 321, "Strike", TargetKind.ENEMY),
            CardDefinition(4, 999999, "Synthetic Probe", TargetKind.ENEMY),
        ),
        version=2,
    )
    path = tmp_path / "mislabeled.pt"
    with pytest.raises(ValueError, match="词表容量不足"):
        save_mlp_checkpoint(path, model, registry=expanded)
    assert not path.exists()

    # 旧写入器可能已经产生错误标签，加载端也必须拒绝，不能等推理才越界。
    save_mlp_checkpoint(path, model)
    payload = torch.load(path, weights_only=True)
    payload["input_contract"].update(
        registry_version=expanded.version, registry_hash=expanded.content_hash
    )
    torch.save(payload, path)
    with pytest.raises(ValueError, match="词表容量不足"):
        load_mlp_checkpoint(path, registry=expanded)
