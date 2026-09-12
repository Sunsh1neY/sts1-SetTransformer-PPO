"""公开协议执行层不改旧31动作，独立随机流与截断最终观测检查。"""

import numpy as np
import pytest

from sts.agents.masked_policy import AgentDecision
from sts.agents.public_runner import PublicRandomAgent, decode_public_decision, run_public_episode


def obs():
    mask = np.zeros(66, dtype=np.bool_)
    mask[[0, 50]] = True
    return {"schema": "public-observation-v1", "action_mask": mask}


def test_同agent种子独立且只选合法动作():
    left, right = PublicRandomAgent(19), PublicRandomAgent(19)
    a = [left.decide(obs()).action for _ in range(30)]
    np.random.seed(123)
    b = [right.decide(obs()).action for _ in range(30)]
    assert a == b
    assert set(a) == {0, 50}


@pytest.mark.parametrize("truncated", [True, False])
def test_终止与截断原样保留最终观测(truncated):
    final = obs()
    final["action_mask"][:] = False
    class Env:
        def step(self, action):
            return final, 0.0 if truncated else 1.0, not truncated, truncated, {"why": "test"}
    trace = run_public_episode(Env(), PublicRandomAgent(0), obs())
    assert trace["steps"] == 1
    assert trace["truncated"] == truncated
    assert trace["terminated"] != truncated
    assert trace["final_observation"] is final
    assert trace["final_info"] == {"why": "test"}


def test_拒绝非法分布而不是代选动作():
    decision = PublicRandomAgent(0).decide(obs())
    decision.probabilities[1] = 0.1
    with pytest.raises(ValueError):
        decode_public_decision(decision, obs()["action_mask"])
    with pytest.raises(ValueError):
        decode_public_decision(AgentDecision(np.ones(31) / 31, 0), obs()["action_mask"])
