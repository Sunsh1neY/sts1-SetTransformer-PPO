"""连接统一 Agent 与环境的无规则、无随机通用执行层。"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, TypedDict

import numpy as np

from sts.agents.masked_policy import AgentDecision
from sts.env.lightspeed import ACTION_COUNT


class Agent(Protocol):
    """任何正式 Agent 都只需实现这一种决策接口。"""

    def decide(self, observation: Mapping[str, Any]) -> AgentDecision: ...


class EpisodeTrace(TypedDict):
    """一场正式后端轨迹的最小验收记录。"""

    actions: list[int]
    steps: int
    total_reward: float
    terminated: bool
    truncated: bool


def decode_agent_decision(decision: AgentDecision) -> int:
    """校验统一输出，并取出 Agent 已选择的环境动作编号。"""

    probabilities = np.asarray(decision.probabilities)
    if probabilities.shape != (ACTION_COUNT,):
        raise ValueError(
            f"probabilities shape 应为 ({ACTION_COUNT},)，实际为 {probabilities.shape}"
        )
    if not np.issubdtype(probabilities.dtype, np.floating):
        raise TypeError("probabilities 必须是浮点数组")
    if not np.isfinite(probabilities).all() or (probabilities < 0).any():
        raise ValueError("probabilities 必须是有限的非负数")
    if not np.isclose(probabilities.sum(), 1.0):
        raise ValueError("probabilities 的总和必须为 1")

    if isinstance(decision.action, (bool, np.bool_)) or not isinstance(
        decision.action,
        (int, np.integer),
    ):
        raise TypeError("action 必须是整数动作编号")
    action = int(decision.action)
    if not 0 <= action < ACTION_COUNT:
        raise ValueError(f"action 必须在 0..{ACTION_COUNT - 1}，实际为 {action}")
    if probabilities[action] <= 0:
        raise ValueError("已选动作在策略分布中的概率必须大于 0")
    return action


def run_episode(
    env: Any,
    agent: Agent,
    observation: Mapping[str, Any],
) -> EpisodeTrace:
    """通用闭环：调用 Agent，解码动作，交给环境，直到环境报告终局。"""

    actions: list[int] = []
    total_reward = 0.0
    terminated = False
    truncated = False
    current = observation

    while not (terminated or truncated):
        decision = agent.decide(current)
        action = decode_agent_decision(decision)
        current, reward, terminated, truncated, _info = env.step(action)
        actions.append(action)
        total_reward += float(reward)

    return {
        "actions": actions,
        "steps": len(actions),
        "total_reward": total_reward,
        "terminated": terminated,
        "truncated": truncated,
    }
