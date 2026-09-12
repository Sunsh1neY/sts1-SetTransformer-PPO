"""66 位公开战斗协议的独立随机策略与通用执行层。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from sts.agents.masked_policy import AgentDecision
from sts.agents.rule_agent import PUBLIC_ACTION_COUNT, PUBLIC_SCHEMA


class PublicRandomAgent:
    """独立 NumPy 随机流，只读取公开协议标识与环境 mask。"""

    policy_version = "public-random-v1"

    def __init__(self, seed: int = 0, action_count: int = PUBLIC_ACTION_COUNT) -> None:
        if action_count != PUBLIC_ACTION_COUNT:
            raise ValueError("当前公开协议只支持 66 动作")
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def decide(self, observation: Mapping[str, Any]) -> AgentDecision:
        if observation["schema"] != PUBLIC_SCHEMA:
            raise ValueError("未知公开观测 schema")
        mask = np.asarray(observation["action_mask"])
        if mask.shape != (PUBLIC_ACTION_COUNT,) or mask.dtype != np.bool_ or not mask.any():
            raise ValueError("公开 action_mask 必须是非空 66 位 bool")
        probabilities = mask.astype(np.float64) / mask.sum()
        action = int(self._rng.choice(PUBLIC_ACTION_COUNT, p=probabilities))
        return AgentDecision(probabilities=probabilities, action=action)


def decode_public_decision(decision: AgentDecision, action_mask: Any) -> int:
    """在送交环境前验证完整分布与 mask；不修改策略选择。"""
    probabilities, mask = np.asarray(decision.probabilities), np.asarray(action_mask)
    if probabilities.shape != (PUBLIC_ACTION_COUNT,) or mask.shape != probabilities.shape:
        raise ValueError("公开决策与 mask 必须是 66 位")
    if mask.dtype != np.bool_ or not np.issubdtype(probabilities.dtype, np.floating):
        raise TypeError("概率必须为浮点数，mask 必须为 bool")
    if not np.isfinite(probabilities).all() or (probabilities < 0).any():
        raise ValueError("概率必须有限非负")
    if not np.isclose(probabilities.sum(), 1) or probabilities[~mask].any():
        raise ValueError("概率必须归一化且非法动作概率为零")
    action = decision.action
    if isinstance(action, (bool, np.bool_)) or not isinstance(action, (int, np.integer)):
        raise TypeError("动作必须为整数")
    if not 0 <= action < PUBLIC_ACTION_COUNT or not mask[action] or probabilities[action] <= 0:
        raise ValueError("选择动作必须合法且有正概率")
    return int(action)


def run_public_episode(env: Any, agent: Any, observation: Mapping[str, Any]) -> dict[str, Any]:
    """环境持有所有终止规则；外部截断和最终观测原样保留。"""
    current, actions, rewards = observation, [], []
    terminated = truncated = False
    final_info: dict[str, Any] = {}
    while not (terminated or truncated):
        if current["schema"] != PUBLIC_SCHEMA:
            raise ValueError("未知公开观测 schema")
        decision = agent.decide(current)
        action = decode_public_decision(decision, current["action_mask"])
        current, reward, terminated, truncated, final_info = env.step(action)
        if not isinstance(terminated, (bool, np.bool_)) or not isinstance(truncated, (bool, np.bool_)):
            raise TypeError("终止标志必须为 bool")
        if terminated and truncated:
            raise ValueError("本协议终止与外部截断不能同时为真")
        if not np.isfinite(reward):
            raise ValueError("奖励必须是有限数值")
        actions.append(action)
        rewards.append(float(reward))
    return {
        "actions": actions, "rewards": rewards, "steps": len(actions),
        "total_reward": sum(rewards), "terminated": bool(terminated),
        "truncated": bool(truncated), "final_observation": current, "final_info": final_info,
    }
