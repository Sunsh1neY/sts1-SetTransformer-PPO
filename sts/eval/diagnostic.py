"""D25：在独立开发种子上做逐遭遇配对诊断，保留全部样本。"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from sts.agents.episode_runner import Agent, decode_agent_decision
from sts.agents.masked_policy import MaskedRandomAgent
from sts.agents.mlp_agent import MlpAgent
from sts.env.lightspeed import GLOBAL_FEATURES, Encounter, LightspeedBattleEnv
from sts.env.wrappers import FlattenWrapper
from sts.models.mlp import MlpActorCritic
from sts.rewards import BATTLE_REWARD_CONTRACT

DIAGNOSTIC_SEED_MIN = 900000
DIAGNOSTIC_SEED_MAX = 999999


def _integer(value: Any, name: str, minimum: int) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} 必须为整数")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{name} 必须至少为 {minimum}")
    return result


def _seed_range(start: Any, count: int, name: str) -> int:
    start = _integer(start, name, DIAGNOSTIC_SEED_MIN)
    if start + count - 1 > DIAGNOSTIC_SEED_MAX:
        raise ValueError(f"{name} 使用范围必须在 900000..999999，不能进入训练区间")
    return start


def paired_bootstrap_ci(
    differences_by_encounter: Mapping[str, Sequence[float]],
    *,
    seed: int = 960000,
    repeats: int = 10000,
) -> tuple[float, float]:
    """每次在各遭遇内部重采样配对差值，保持各层样本数与总体权重。"""

    repeats = _integer(repeats, "bootstrap_repeats", 100)
    seed = _integer(seed, "bootstrap_seed", 0)
    if not differences_by_encounter:
        raise ValueError("配对 bootstrap 至少需要一个遭遇")
    strata = []
    for encounter, values in differences_by_encounter.items():
        array = np.asarray(values, dtype=np.float64)
        if array.ndim != 1 or len(array) < 2:
            raise ValueError(f"{encounter} 至少需要 2 个一维配对差值")
        if not np.isfinite(array).all():
            raise ValueError("配对差值必须为有限数")
        strata.append(array)

    rng = np.random.default_rng(seed)
    means = np.empty(repeats, dtype=np.float64)
    count = sum(len(array) for array in strata)
    # 分块避免大样本诊断时分配 repeats × episodes 的完整索引矩阵。
    for start in range(0, repeats, 256):
        size = min(256, repeats - start)
        sums = np.zeros(size, dtype=np.float64)
        for array in strata:
            indices = rng.integers(len(array), size=(size, len(array)))
            sums += array[indices].sum(axis=1)
        means[start:start + size] = sums / count
    lower, upper = np.quantile(means, [0.025, 0.975], method="linear")
    return float(lower), float(upper)


def _play_episode(
    env: FlattenWrapper,
    agent: Agent,
    *,
    seed: int,
    encounter: Encounter,
) -> dict[str, Any]:
    observation = env.reset(seed=seed, encounter=encounter, ascension=0)
    actions: list[int] = []
    total_reward = 0.0
    while True:
        decision = agent.decide(observation)
        action = decode_agent_decision(decision)
        mask = observation["action_mask"]
        if not mask[action] or (decision.probabilities[~mask] != 0).any():
            raise ValueError("开发诊断遇到非法动作或非法动作概率")
        observation, reward, terminated, truncated, info = env.step(action)
        if not math.isfinite(reward):
            raise ValueError("开发诊断遇到非有限奖励")
        actions.append(action)
        total_reward += reward
        if terminated or truncated:
            if not terminated or truncated:
                raise ValueError("minimal-v1 应返回任务终止，不能把截断当作完整对局")
            # info 仅用于终局统计，绝不传入 Agent 或状态编码。
            if info["outcome"] not in (1, 2) or info["timeout"] not in (0, 1):
                raise ValueError("开发诊断遇到未知终局或超时标志")
            won = info["outcome"] == 1
            hp = info["player_hp"]
            max_hp = info["player_max_hp"]
            if max_hp <= 0 or (won and info["timeout"]):
                raise ValueError("开发诊断终局 HP 或胜负与超时标志不一致")
            # 适配层已按共享契约核对单步奖励；这里只检查此前步骤没有重复加分。
            if not math.isclose(total_reward, reward, rel_tol=1e-6, abs_tol=1e-6):
                raise ValueError("开发诊断检测到非终局加分或终局重复发奖")
            return {
                "total_reward": float(total_reward),
                "won": won,
                "hp": int(hp),
                "max_hp": int(max_hp),
                "turns": int(observation["global"][GLOBAL_FEATURES.index("turn")]),
                "steps": len(actions),
                "timeout": bool(info["timeout"]),
                "task_outcome": info["task_outcome"],
                "termination_reason": info["termination_reason"],
                "actions": actions,
            }
        if reward != 0:
            raise ValueError("minimal-v1 非终局奖励必须为 0")
        if len(actions) >= 10000:
            raise RuntimeError("开发诊断超过 10000 步仍未终止")


def _agent_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    wins = [row for row in records if row["won"]]
    return {
        "mean_return": float(np.mean([row["total_reward"] for row in records])),
        "win_rate": float(np.mean([row["won"] for row in records])),
        "mean_hp": float(np.mean([row["hp"] for row in records])),
        "mean_win_exit_hp_ratio": (
            float(np.mean([row["hp"] / row["max_hp"] for row in wins]))
            if wins else None
        ),
        "mean_turns": float(np.mean([row["turns"] for row in records])),
        "mean_steps": float(np.mean([row["steps"] for row in records])),
        "timeout_count": sum(row["timeout"] for row in records),
        "timeout_rate": float(np.mean([row["timeout"] for row in records])),
    }


def _summarize_pairs(
    pairs: Sequence[Mapping[str, Any]],
    *,
    bootstrap_seed: int,
    bootstrap_repeats: int,
) -> dict[str, Any]:
    differences = np.array([row["return_difference"] for row in pairs])
    strata: dict[str, list[float]] = {}
    for row in pairs:
        strata.setdefault(row["encounter"], []).append(row["return_difference"])
    ci = paired_bootstrap_ci(strata, seed=bootstrap_seed, repeats=bootstrap_repeats)
    mean = float(differences.mean())
    # 重复小数的求均值舍入可能让常数序列出现极小的伪方差。
    std = 0.0 if np.all(differences == differences[0]) else float(differences.std(ddof=1))
    return {
        "episodes": len(pairs),
        "model": _agent_summary([row["model"] for row in pairs]),
        "random": _agent_summary([row["random"] for row in pairs]),
        "mean_return_difference": mean,
        "return_difference_ci95": list(ci),
        "paired_return_std": std,
        # 常数差值时 mean/std 无定义，使用 JSON null，不能写 NaN/Infinity。
        "paired_effect_size": mean / std if std > 0 else None,
        "win_rate_difference": float(np.mean([row["win_difference"] for row in pairs])),
        "improvement_detected": ci[0] > 0,
    }


def evaluate_diagnostic(
    model: MlpActorCritic,
    *,
    seed_start: int = 900000,
    episodes_per_encounter: int = 100,
    agent_seed_start: int = 950000,
    bootstrap_seed: int = 960000,
    bootstrap_repeats: int = 10000,
) -> dict[str, Any]:
    """同一初始状态与策略 RNG 种子逐局配对，异常直接抛出，绝不跳过样本。"""

    count = _integer(episodes_per_encounter, "episodes_per_encounter", 2)
    repeats = _integer(bootstrap_repeats, "bootstrap_repeats", 100)
    total = len(Encounter) * count
    seed_start = _seed_range(seed_start, total, "seed_start")
    agent_seed_start = _seed_range(agent_seed_start, total, "agent_seed_start")
    bootstrap_seed = _seed_range(bootstrap_seed, 1, "bootstrap_seed")
    config = {
        "environment": "minimal-v1",
        **BATTLE_REWARD_CONTRACT.to_dict(),
        "purpose": "development-diagnostic",
        "seed_start": seed_start,
        "seed_end_inclusive": seed_start + total - 1,
        "episodes_per_encounter": count,
        "agent_seed_start": agent_seed_start,
        "agent_seed_end_inclusive": agent_seed_start + total - 1,
        "bootstrap_seed": bootstrap_seed,
        "bootstrap_repeats": repeats,
        "ci_method": "stratified-paired-percentile-bootstrap-95",
        "effect_size": "mean-paired-difference / sample-standard-deviation",
        "zero_variance_effect_size": None,
        "ascension": 0,
        "max_turns": 50,
        "gamma": 1.0,
    }
    pairs: list[dict[str, Any]] = []
    env = FlattenWrapper(LightspeedBattleEnv(max_turns=50, gamma=1.0))
    modes = [(module, module.training) for module in model.modules()]
    try:
        model.eval()
        for encounter in Encounter:
            for _ in range(count):
                index = len(pairs)
                seed = seed_start + index
                agent_seed = agent_seed_start + index
                learned = _play_episode(
                    env, MlpAgent(model, seed=agent_seed), seed=seed, encounter=encounter
                )
                random = _play_episode(
                    env, MaskedRandomAgent(seed=agent_seed), seed=seed, encounter=encounter
                )
                pairs.append({
                    "encounter": encounter.value,
                    "env_seed": seed,
                    "agent_seed": agent_seed,
                    "model": learned,
                    "random": random,
                    "return_difference": learned["total_reward"] - random["total_reward"],
                    "win_difference": int(learned["won"]) - int(random["won"]),
                })
    finally:
        for module, training in modes:
            module.training = training
    return {
        "config": config,
        "overall": _summarize_pairs(
            pairs, bootstrap_seed=bootstrap_seed, bootstrap_repeats=repeats
        ),
        "by_encounter": {
            encounter.value: _summarize_pairs(
                [row for row in pairs if row["encounter"] == encounter.value],
                bootstrap_seed=bootstrap_seed,
                bootstrap_repeats=repeats,
            )
            for encounter in Encounter
        },
        "pairs": pairs,
    }
