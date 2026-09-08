"""v6 的任务、奖励、终止与真实 RTG 契约。

环境负责产生奖励；训练、评估和离线数据只通过本模块校验或重算，
不能各自复制一份奖励公式。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from numbers import Real
from typing import Any

import numpy as np

DOCUMENT_VERSION = "v6"
TASK_TYPE_BATTLE = "battle"
TASK_TYPE_RUN = "run"
BATTLE_TASK_SPEC_ID = "minimal-v1"
BATTLE_REWARD_VERSION = "battle_reward_v1"
RUN_REWARD_VERSION = "run_reward_v1"
BATTLE_ENVIRONMENT_VERSION = "sts_lightspeed-minimal-v1"
BATTLE_TERMINATION_RULE_VERSION = "battle-termination-v1"


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} 必须是非空字符串")
    return value


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise TypeError(f"{name} 必须是数值")
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{name} 必须是有限数")
    return result


@dataclass(frozen=True)
class RewardContract:
    """可落盘、可比较的任务奖励契约。"""

    document_version: str
    task_type: str
    task_spec_id: str
    reward_version: str
    gamma: float
    alpha_hp: float | None
    beta: float
    potential_version: str | None
    environment_version: str
    termination_rule_version: str
    success_predicate_id: str | None = None

    def __post_init__(self) -> None:
        _required_text(self.document_version, "document_version")
        _required_text(self.task_spec_id, "task_spec_id")
        _required_text(self.reward_version, "reward_version")
        _required_text(self.environment_version, "environment_version")
        _required_text(self.termination_rule_version, "termination_rule_version")
        gamma = _finite_number(self.gamma, "gamma")
        beta = _finite_number(self.beta, "beta")
        if gamma != 1.0:
            raise ValueError("v6 正式奖励要求 gamma=1")
        if beta != 0.0 or self.potential_version is not None:
            raise ValueError("v6 基线固定 beta=0，potential_version 必须为 null")
        if self.task_type == TASK_TYPE_BATTLE:
            if self.reward_version != BATTLE_REWARD_VERSION:
                raise ValueError("battle 契约必须使用 battle_reward_v1")
            if _finite_number(self.alpha_hp, "alpha_hp") != 0.5:
                raise ValueError("v6 battle 正式对照固定 alpha_hp=0.5")
            if self.success_predicate_id is not None:
                raise ValueError("battle 契约不使用 run 成功谓词")
        elif self.task_type == TASK_TYPE_RUN:
            if self.reward_version != RUN_REWARD_VERSION:
                raise ValueError("run 契约必须使用 run_reward_v1")
            if self.alpha_hp is not None:
                raise ValueError("run 奖励不使用 alpha_hp")
            _required_text(self.success_predicate_id, "success_predicate_id")
        else:
            raise ValueError("task_type 必须是 battle 或 run")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> RewardContract:
        expected = set(cls.__dataclass_fields__)
        if set(values) != expected:
            missing = sorted(expected - set(values))
            extra = sorted(set(values) - expected)
            raise ValueError(f"奖励契约字段不匹配：missing={missing}, extra={extra}")
        return cls(**dict(values))


BATTLE_REWARD_CONTRACT = RewardContract(
    document_version=DOCUMENT_VERSION,
    task_type=TASK_TYPE_BATTLE,
    task_spec_id=BATTLE_TASK_SPEC_ID,
    reward_version=BATTLE_REWARD_VERSION,
    gamma=1.0,
    alpha_hp=0.5,
    beta=0.0,
    potential_version=None,
    environment_version=BATTLE_ENVIRONMENT_VERSION,
    termination_rule_version=BATTLE_TERMINATION_RULE_VERSION,
)


def make_run_reward_contract(
    *,
    task_spec_id: str,
    success_predicate_id: str,
    environment_version: str,
    termination_rule_version: str,
) -> RewardContract:
    """只有真实规则标识齐全时才允许构造正式 run 契约。"""

    return RewardContract(
        document_version=DOCUMENT_VERSION,
        task_type=TASK_TYPE_RUN,
        task_spec_id=task_spec_id,
        reward_version=RUN_REWARD_VERSION,
        gamma=1.0,
        alpha_hp=None,
        beta=0.0,
        potential_version=None,
        environment_version=environment_version,
        termination_rule_version=termination_rule_version,
        success_predicate_id=success_predicate_id,
    )


def battle_step_reward(
    *,
    battle_won: bool,
    terminated: bool,
    hp_exit: Real | None = None,
    max_hp_exit: Real | None = None,
) -> float:
    """计算 battle_reward_v1；真终局校验退出 HP，只有首次胜利计分。"""

    if not isinstance(battle_won, bool) or not isinstance(terminated, bool):
        raise TypeError("battle_won 与 terminated 必须为 bool")
    if battle_won and not terminated:
        raise ValueError("战斗尚未终止时不能标记胜利")
    if not terminated:
        return 0.0
    hp = _finite_number(hp_exit, "hp_exit")
    max_hp = _finite_number(max_hp_exit, "max_hp_exit")
    if max_hp <= 0 or hp < 0 or hp > max_hp:
        raise ValueError("终局退出 HP 必须满足 max_hp_exit>0 且 0<=hp_exit<=max_hp_exit")
    if not battle_won:
        return 0.0
    return 1.0 + 0.5 * hp / max_hp


def run_step_reward(*, run_won: bool, terminated: bool, battle_won: bool = False) -> float:
    """计算 run_reward_v1；普通战斗胜利不结束 run，也不发局部奖金。"""

    if not all(isinstance(value, bool) for value in (run_won, terminated, battle_won)):
        raise TypeError("run_won、terminated 与 battle_won 必须为 bool")
    if run_won and not terminated:
        raise ValueError("run 尚未真正终止时不能标记最终通关")
    return 1.0 if run_won else 0.0


def validate_battle_step_reward(
    actual_reward: Real,
    *,
    battle_won: bool,
    terminated: bool,
    hp_exit: Real | None = None,
    max_hp_exit: Real | None = None,
) -> None:
    """让适配层校验后端奖励，训练端不再重复实现公式。"""

    actual = _finite_number(actual_reward, "actual_reward")
    expected = battle_step_reward(
        battle_won=battle_won,
        terminated=terminated,
        hp_exit=hp_exit,
        max_hp_exit=max_hp_exit,
    )
    if not np.isclose(actual, expected, rtol=1e-6, atol=1e-6):
        raise ValueError(
            f"后端奖励不符合 {BATTLE_REWARD_VERSION}：actual={actual}, expected={expected}"
        )


def normalize_battle_step_info(
    raw_info: Mapping[str, Any],
    *,
    actual_reward: Real,
    terminated: bool,
    truncated: bool,
) -> dict[str, Any]:
    """把后端数值 info 补成 v6 的统一 battle transition 元数据。"""

    if terminated and truncated:
        raise ValueError("同一 transition 不能同时标记为 terminated 与 truncated")
    info = dict(raw_info)
    for required in ("outcome", "timeout", "player_hp", "player_max_hp"):
        if required not in info:
            raise ValueError(f"battle info 缺少 {required}")
    battle_won = terminated and info["outcome"] == 1
    validate_battle_step_reward(
        actual_reward,
        battle_won=battle_won,
        terminated=terminated,
        hp_exit=info["player_hp"] if terminated else None,
        max_hp_exit=info["player_max_hp"] if terminated else None,
    )
    if not (terminated or truncated):
        task_outcome = "in_progress"
        termination_reason = None
    elif truncated:
        task_outcome = "external_truncation"
        termination_reason = "external_truncation"
    elif battle_won:
        task_outcome = "battle_won"
        termination_reason = "battle_won"
    elif info["timeout"]:
        task_outcome = "hard_timeout"
        termination_reason = "hard_timeout"
    else:
        task_outcome = "battle_lost"
        termination_reason = "battle_lost"
    reward = float(actual_reward)
    info.update(
        {
            **BATTLE_REWARD_CONTRACT.to_dict(),
            "battle_won": battle_won,
            "run_won": None,
            "task_outcome": task_outcome,
            "termination_reason": termination_reason,
            "reward_base": reward,
            "reward_train": reward,
        }
    )
    return info


def true_return_to_go(
    rewards: Sequence[Real],
    *,
    terminated: bool,
    truncated: bool,
) -> list[float]:
    """在完整真实 episode 上计算未折扣 RTG；不把外部截断猜成失败。"""

    if not isinstance(terminated, bool) or not isinstance(truncated, bool):
        raise TypeError("terminated 与 truncated 必须为 bool")
    if terminated and truncated:
        raise ValueError("同一 transition 不能同时是真终止和外部截断")
    if not terminated:
        reason = "外部截断" if truncated else "未结束"
        raise ValueError(f"{reason}轨迹没有完整真实 RTG，禁止补造失败 0 标签")
    values = [_finite_number(value, "reward") for value in rewards]
    if not values:
        raise ValueError("完整 episode 至少包含一个 transition")
    result = [0.0] * len(values)
    running = 0.0
    for index in range(len(values) - 1, -1, -1):
        running += values[index]
        result[index] = running
    return result


def recompute_episode_reward_and_rtg(
    *,
    step_count: int,
    task_type: str,
    task_outcome: str,
    terminated: bool,
    truncated: bool,
    hp_exit: Real | None = None,
    max_hp_exit: Real | None = None,
) -> tuple[list[float], list[float]]:
    """从可验证终局字段重算逐步奖励和 RTG；字段不足时明确拒绝。"""

    if type(step_count) is not int or step_count <= 0:
        raise ValueError("step_count 必须为正整数")
    if not terminated or truncated:
        raise ValueError("只有完整真终止 episode 才能重算精确奖励与 RTG")
    if task_type == TASK_TYPE_BATTLE:
        if task_outcome not in {"battle_won", "battle_lost", "hard_timeout"}:
            raise ValueError("battle 数据缺少可验证的战斗终局结果")
        terminal_reward = battle_step_reward(
            battle_won=task_outcome == "battle_won",
            terminated=True,
            hp_exit=hp_exit,
            max_hp_exit=max_hp_exit,
        )
    elif task_type == TASK_TYPE_RUN:
        if task_outcome not in {"run_won", "run_lost", "hard_timeout"}:
            raise ValueError("run 数据缺少可验证的整局终局结果；battle win 不能改成 run win")
        terminal_reward = run_step_reward(
            run_won=task_outcome == "run_won",
            terminated=True,
        )
    else:
        raise ValueError("task_type 必须是 battle 或 run")
    rewards = [0.0] * step_count
    rewards[-1] = terminal_reward
    return rewards, true_return_to_go(rewards, terminated=True, truncated=False)


def require_reward_contract(
    actual: Mapping[str, Any], expected: RewardContract = BATTLE_REWARD_CONTRACT
) -> None:
    """恢复训练或加载数据前执行逐字段奖励版本检查。"""

    parsed = RewardContract.from_mapping(actual)
    if parsed != expected:
        raise ValueError(
            f"任务/奖励版本不匹配：actual={parsed.to_dict()}, expected={expected.to_dict()}"
        )
