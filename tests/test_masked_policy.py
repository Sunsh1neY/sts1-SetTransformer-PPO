"""Week 4 T4：统一 Agent 输出、动作 mask 与执行层闭环。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

import sts.agents.masked_policy as masked_policy_module
from sts import (
    AgentDecision,
    Encounter,
    FlattenWrapper,
    LightspeedBattleEnv,
    MaskedRandomAgent,
    TokenWrapper,
    decode_agent_decision,
    masked_softmax,
    run_episode,
)


def test_masked_softmax_先屏蔽再归一化():
    probabilities = masked_softmax(
        np.array([0.0, np.log(2.0), np.log(3.0)]),
        np.array([True, False, True]),
    )

    assert probabilities[1] == 0.0
    assert probabilities.sum() == pytest.approx(1.0)
    assert probabilities[[0, 2]].tolist() == pytest.approx([0.25, 0.75])
    assert probabilities[2] / probabilities[0] == pytest.approx(3.0)


def test_masked_softmax_只有一个合法动作时概率为一():
    probabilities = masked_softmax(
        np.array([1000.0, -1000.0, 7.0]),
        np.array([False, True, False]),
    )

    assert probabilities.tolist() == [0.0, 1.0, 0.0]


def test_masked_softmax_全非法及错误输入显式报错():
    with pytest.raises(ValueError, match="没有合法动作"):
        masked_softmax(np.zeros(3), np.zeros(3, dtype=np.bool_))
    with pytest.raises(TypeError, match="dtype"):
        masked_softmax(np.zeros(3), np.ones(3, dtype=np.int32))
    with pytest.raises(ValueError, match="shape"):
        masked_softmax(np.zeros(3), np.ones(2, dtype=np.bool_))


def test_随机agent调用masked_softmax并输出分布与整数动作(monkeypatch):
    original = masked_policy_module.masked_softmax
    calls = []

    def recording_softmax(logits, action_mask):
        calls.append((np.asarray(logits).copy(), np.asarray(action_mask).copy()))
        return original(logits, action_mask)

    monkeypatch.setattr(masked_policy_module, "masked_softmax", recording_softmax)
    mask = np.zeros(31, dtype=np.bool_)
    mask[[3, 30]] = True
    observation = {"action_mask": mask}
    agent = MaskedRandomAgent(seed=7)

    decisions = [agent.decide(observation) for _ in range(40)]

    assert len(calls) == 40
    assert all(
        decision.probabilities[[3, 30]].tolist() == pytest.approx([0.5, 0.5])
        for decision in decisions
    )
    assert all(decision.probabilities[~mask].sum() == 0.0 for decision in decisions)
    selected = [decode_agent_decision(decision) for decision in decisions]
    assert set(selected) == {3, 30}
    assert selected == [decision.action for decision in decisions]


def test_随机agent非终局全非法显式报错():
    agent = MaskedRandomAgent(seed=0)
    observation = {"action_mask": np.zeros(31, dtype=np.bool_)}

    with pytest.raises(ValueError, match="没有合法动作"):
        agent.decide(observation)


def test_接入层严格拒绝损坏的agent输出():
    probabilities = np.zeros(31, dtype=np.float64)
    probabilities[3] = 1.0
    with pytest.raises(ValueError, match="概率必须大于 0"):
        decode_agent_decision(AgentDecision(probabilities, 30))
    with pytest.raises(ValueError, match="0..30"):
        decode_agent_decision(AgentDecision(probabilities, 31))
    with pytest.raises(TypeError, match="整数"):
        decode_agent_decision(AgentDecision(probabilities, 3.0))


class _FixedAgent:
    """证明接入层只使用 Agent 已经选好的整数，不二次抽样。"""

    def __init__(self) -> None:
        self.calls = 0

    def decide(self, observation):
        self.calls += 1
        probabilities = np.zeros(31, dtype=np.float64)
        probabilities[[3, 30]] = [0.25, 0.75]
        return AgentDecision(probabilities, 3)


class _OneStepEnv:
    def __init__(self) -> None:
        self.received = []

    def step(self, action):
        self.received.append(action)
        terminal = {"action_mask": np.zeros(31, dtype=np.bool_)}
        return terminal, 1.0, True, False, {}


def test_通用接入层无rng且不改agent已选动作():
    env = _OneStepEnv()
    agent = _FixedAgent()
    initial = {"action_mask": np.ones(31, dtype=np.bool_)}

    result = run_episode(env, agent, initial)

    assert env.received == [3]
    assert agent.calls == 1
    assert result["actions"] == [3]
    assert result["terminated"] is True


class _RecordingEnv(LightspeedBattleEnv):
    """测试探针：记录每次 step 真正收到的动作及此前的环境 mask。"""

    def __init__(self) -> None:
        super().__init__()
        self.received: list[tuple[int, np.ndarray[Any, np.dtype[np.bool_]]]] = []

    def step(self, action: int):
        self.received.append((action, self.action_mask()))
        return super().step(action)


class _RecordingAgent(MaskedRandomAgent):
    """保存 Agent 真正看到的 mask，用于检查 wrapper 没有增删合法动作。"""

    def __init__(self, seed: int) -> None:
        super().__init__(seed)
        self.observed_masks = []

    def decide(self, observation):
        self.observed_masks.append(observation["action_mask"].copy())
        return super().decide(observation)


@pytest.mark.parametrize("wrapper_type", [FlattenWrapper, TokenWrapper])
@pytest.mark.parametrize("encounter", list(Encounter))
def test_统一agent通过双wrapper只发送环境mask允许的动作并跑到终局(
    wrapper_type,
    encounter,
):
    backend = _RecordingEnv()
    env = wrapper_type(backend)
    observation = env.reset(100000, encounter)
    # Agent 与 runner 都只能消费 observation，不能重新向 wrapper 索取 mask。
    env.action_mask = lambda: (_ for _ in ()).throw(AssertionError("禁止重取 mask"))
    agent = _RecordingAgent(seed=20260905)

    result = run_episode(env, agent, observation)

    assert result["terminated"] is True
    assert result["truncated"] is False
    assert result["steps"] == len(backend.received) == len(result["actions"])
    assert result["actions"] == [action for action, _mask in backend.received]
    assert all(mask[action] for action, mask in backend.received)
    assert len(agent.observed_masks) == len(backend.received)
    assert all(
        np.array_equal(agent_mask, backend_mask)
        for agent_mask, (_action, backend_mask) in zip(
            agent.observed_masks,
            backend.received,
            strict=True,
        )
    )
    assert not backend.action_mask().any()
