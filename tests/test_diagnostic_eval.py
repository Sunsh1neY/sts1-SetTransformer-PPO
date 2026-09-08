"""D25 开发诊断的随机流隔离、配对统计和失败处理。"""

from __future__ import annotations

import json

import numpy as np
import pytest
import torch

from sts.agents.masked_policy import AgentDecision
from sts.agents.mlp_agent import MlpAgent
from sts.env.lightspeed import Encounter, LightspeedBattleEnv
from sts.env.wrappers import FlattenWrapper
from sts.eval import diagnostic
from sts.eval.diagnostic import evaluate_diagnostic, paired_bootstrap_ci
from sts.models.mlp import MlpActorCritic, MlpConfig


@pytest.fixture
def model():
    previous_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    with torch.random.fork_rng():
        torch.manual_seed(7)
        result = MlpActorCritic(MlpConfig.from_registry())
    yield result
    torch.set_num_threads(previous_threads)


def test_mlp_agent_同seed重现且不消耗torch随机流并保留训练模式(model):
    observation = FlattenWrapper(LightspeedBattleEnv()).reset(900000, Encounter.JAW_WORM)
    first = MlpAgent(model, seed=950000)
    second = MlpAgent(model, seed=950000)
    model.train()
    model.trunk.eval()
    modes_before = [module.training for module in model.modules()]
    rng_before = torch.get_rng_state().clone()
    for _ in range(8):
        left, right = first.decide(observation), second.decide(observation)
        assert left.action == right.action
        np.testing.assert_array_equal(left.probabilities, right.probabilities)
        assert observation["action_mask"][left.action]
        assert np.all(left.probabilities[~observation["action_mask"]] == 0)
        assert left.probabilities.sum() == pytest.approx(1.0, abs=1e-15)
    assert torch.equal(torch.get_rng_state(), rng_before)
    assert [module.training for module in model.modules()] == modes_before
    assert all(parameter.grad is None for parameter in model.parameters())


def test_开发诊断逐局配对可复现且保留全部样本与训练状态(model):
    # 零 logits 的 MLP 和均匀合法随机分布一致，同一策略 seed 必须走同一轨迹。
    with torch.no_grad():
        model.policy_head.weight.zero_()
        model.policy_head.bias.zero_()
    model.train()
    rng_before = torch.get_rng_state().clone()
    options = {"episodes_per_encounter": 2, "bootstrap_repeats": 100}
    first = evaluate_diagnostic(model, **options)
    second = evaluate_diagnostic(model, **options)
    assert first == second
    assert model.training
    assert torch.equal(torch.get_rng_state(), rng_before)
    assert first["overall"]["episodes"] == 6
    assert len(first["pairs"]) == 6
    assert set(first["by_encounter"]) == {encounter.value for encounter in Encounter}
    for index, row in enumerate(first["pairs"]):
        assert row["env_seed"] == 900000 + index
        assert row["agent_seed"] == 950000 + index
        assert row["model"] == row["random"]
    for bucket in [first["overall"], *first["by_encounter"].values()]:
        assert bucket["mean_return_difference"] == 0
        assert bucket["return_difference_ci95"] == [0, 0]
        assert bucket["paired_effect_size"] is None
        assert not bucket["improvement_detected"]
    json.dumps(first, allow_nan=False)


def test_分层paired_bootstrap保持各遭遇样本数和权重():
    # 每层内部为常数，正确分层重采样的结果恒为 (2*0 + 4*1)/6。
    assert paired_bootstrap_ci({"a": [0, 0], "b": [1, 1, 1, 1]}, repeats=100) == (
        2 / 3, 2 / 3
    )
    # 两个配对差值的重采样均值只有 -1/0/1，中央 95% 区间应保留两端。
    assert paired_bootstrap_ci({"a": [-1, 1]}, repeats=1000) == (-1.0, 1.0)


def test_配对效应量用差值标准差且常数情况可JSON序列化():
    pairs = []
    for difference in [-1.0, 0.0, 1.0, 1.0]:
        random = {"total_reward": 1.0, "won": False, "hp": 1, "max_hp": 80, "turns": 2,
                  "steps": 3, "timeout": False}
        learned = dict(random, total_reward=1.0 + difference, won=difference > 0)
        pairs.append({"encounter": "a", "return_difference": difference,
                      "win_difference": int(difference > 0), "model": learned,
                      "random": random})
    summary = diagnostic._summarize_pairs(pairs, bootstrap_seed=10, bootstrap_repeats=100)
    assert summary["mean_return_difference"] == 0.25
    assert summary["paired_return_std"] == pytest.approx(np.std([-1, 0, 1, 1], ddof=1))
    assert summary["paired_effect_size"] == pytest.approx(0.25 / np.std([-1, 0, 1, 1], ddof=1))
    assert summary["win_rate_difference"] == 0.5
    for row in pairs:
        row["return_difference"] = 0.1
    constant = diagnostic._summarize_pairs(pairs[:3], bootstrap_seed=10, bootstrap_repeats=100)
    assert constant["paired_effect_size"] is None
    json.dumps(constant, allow_nan=False)


@pytest.mark.parametrize("options", [
    {"episodes_per_encounter": 0},
    {"episodes_per_encounter": 1},
    {"episodes_per_encounter": -1},
    {"episodes_per_encounter": True},
    {"episodes_per_encounter": 2.5},
    {"seed_start": 142},
    {"seed_start": 1000000},
    {"seed_start": 999999},
    {"agent_seed_start": 1000000},
    {"agent_seed_start": 999999},
    {"bootstrap_seed": 1000000},
    {"bootstrap_repeats": 0},
    {"bootstrap_repeats": 99},
])
def test_开发诊断拒绝样本不足与训练评估种子越界(options):
    # 验参必须先于创建环境或执行模型，不能已经跑了部分样本才发现配置越界。
    with pytest.raises((TypeError, ValueError)):
        evaluate_diagnostic(None, **options)


@pytest.mark.parametrize("values", [{}, {"a": [1]}, {"a": [0, np.nan]}, {"a": [[0, 1]]}])
def test_paired_bootstrap拒绝空层单样本非有限与非一维(values):
    with pytest.raises(ValueError):
        paired_bootstrap_ci(values, repeats=100)


def test_诊断异常直接抛出且还原训练模式(model, monkeypatch):
    calls = []

    def fail(*args, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("故意的诊断异常")

    model.train()
    model.trunk.eval()
    modes_before = [module.training for module in model.modules()]
    monkeypatch.setattr(diagnostic, "_play_episode", fail)
    with pytest.raises(RuntimeError, match="故意的诊断异常"):
        evaluate_diagnostic(model, episodes_per_encounter=2, bootstrap_repeats=100)
    assert len(calls) == 1
    assert [module.training for module in model.modules()] == modes_before


def test_诊断对局拒绝非法动作而非静默跳过():
    class IllegalAgent:
        def decide(self, observation):
            action = int(np.flatnonzero(~observation["action_mask"])[0])
            probabilities = np.zeros(31)
            probabilities[action] = 1
            return AgentDecision(probabilities=probabilities, action=action)

    with pytest.raises(ValueError, match="非法动作"):
        diagnostic._play_episode(
            FlattenWrapper(LightspeedBattleEnv()), IllegalAgent(),
            seed=900000, encounter=Encounter.JAW_WORM,
        )
