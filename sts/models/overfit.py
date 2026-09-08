"""S2：真实轨迹小样本的有监督记忆诊断，不衡量策略强弱。"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import torch

from sts import Encounter, FlattenWrapper, LightspeedBattleEnv, MaskedRandomAgent
from sts.env.wrappers import CARD_CAPACITY, FlatInput
from sts.models.mlp import MlpActorCritic, MlpConfig, batch_flat_inputs
from sts.rewards import BATTLE_REWARD_CONTRACT, true_return_to_go


@dataclass(frozen=True)
class OverfitConfig:
    """预先固定数据、训练预算及通过门槛；不按运行结果放宽。"""

    env_seed_start: int = 200_000
    agent_seed_start: int = 300_000
    selection_seed: int = 400_000
    episodes_per_encounter: int = 8
    samples_per_encounter: int = 16
    updates: int = 1500
    learning_rate: float = 0.001
    value_weight: float = 1.0
    log_every: int = 100
    min_accuracy: float = 0.99
    max_policy_loss_ratio: float = 0.1
    max_value_mse: float = 0.001
    max_value_mse_ratio: float = 0.1

    def __post_init__(self) -> None:
        if min(self.env_seed_start, self.agent_seed_start, self.selection_seed) < 100_000:
            raise ValueError("S2 只能使用 seed >= 100000")
        for name in ("episodes_per_encounter", "samples_per_encounter", "updates", "log_every"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} 必须为正")
        if self.learning_rate <= 0 or self.value_weight <= 0:
            raise ValueError("学习率和 value_weight 必须为正")


def observation_key(observation: FlatInput) -> bytes:
    """只用模型允许输入生成去重键，不把 seed 或标签加入输入。"""

    return b"".join(
        name.encode("ascii") + observation[name].tobytes()
        for name in sorted(observation)
    )


def swapped_sample(sample: dict[str, Any]) -> dict[str, Any] | None:
    """交换两张不同手牌和动作路由；仅保留掩码完全不变的配对。"""

    action = sample["action"]
    if action == 30:
        return None
    slot, target = divmod(action, 3)
    observation = sample["observation"]
    cards = observation["card_categorical"].reshape(CARD_CAPACITY, 4)
    mask_rows = observation["action_mask"][:30].reshape(10, 3)
    for other in range(10):
        if (
            other == slot
            or not observation["card_valid"][other]
            or cards[slot, 0] == cards[other, 0]
            or not np.array_equal(mask_rows[slot], mask_rows[other])
        ):
            continue
        swapped = {name: value.copy() for name, value in observation.items()}
        for name in ("card_categorical", "card_numeric", "card_numeric_known", "card_valid"):
            rows = swapped[name].reshape(CARD_CAPACITY, -1)
            rows[[slot, other]] = rows[[other, slot]]
        return {
            **sample,
            "observation": swapped,
            "action": other * 3 + target,
            "augmentation": {"swap_hand_slots": [slot, other]},
        }
    return None


def dataset_statistics(samples: list[dict[str, Any]], pairs: list[list[int]]) -> dict[str, Any]:
    """统计仅看 mask 的最高训练准确率，量化数据是否需要读取内容。"""

    mask_labels: dict[bytes, Counter[int]] = defaultdict(Counter)
    for sample in samples:
        mask_labels[sample["observation"]["action_mask"].tobytes()][sample["action"]] += 1
    value_targets = np.asarray([sample["return_to_go"] for sample in samples])
    actions = Counter(sample["action"] for sample in samples)
    return {
        "samples": len(samples),
        "original_samples": sum(sample["augmentation"] is None for sample in samples),
        "same_mask_swap_pairs": len(pairs),
        "by_encounter": dict(Counter(sample["encounter"] for sample in samples)),
        "action_counts": dict(sorted(actions.items())),
        "majority_action_accuracy": max(actions.values()) / len(samples),
        "mask_only_max_accuracy": sum(max(labels.values()) for labels in mask_labels.values()) / len(samples),
        "uniform_legal_expected_accuracy": float(np.mean([
            1.0 / sample["observation"]["action_mask"].sum() for sample in samples
        ])),
        "return_min": float(value_targets.min()),
        "return_max": float(value_targets.max()),
        "return_unique": len(np.unique(value_targets)),
        "constant_value_mse": float(value_targets.var()),
    }


def validate_dataset(samples: list[dict[str, Any]], pairs: list[list[int]]) -> dict[str, Any]:
    """拒绝终局、冲突标签与过于简单的数据，避免诊断假通过。"""

    if not samples:
        raise ValueError("S2 数据集不能为空")
    seen: set[bytes] = set()
    for sample in samples:
        observation = sample["observation"]
        mask = observation["action_mask"]
        action = sample["action"]
        if isinstance(action, (bool, np.bool_)) or not isinstance(action, (int, np.integer)) or not 0 <= action < 31:
            raise ValueError("S2 动作标签必须是 0..30 的整数")
        if min(sample["env_seed"], sample["agent_seed"]) < 100_000:
            raise ValueError("S2 样本只能使用 seed >= 100000")
        if mask.sum() < 2 or not mask[sample["action"]]:
            raise ValueError("S2 样本必须有至少两个合法动作，且标签合法")
        if not np.isfinite(sample["return_to_go"]) or not 0 <= sample["return_to_go"] <= 1.5:
            raise ValueError("S2 回报标签超出 battle_reward_v1 范围")
        key = observation_key(observation)
        if key in seen:
            raise ValueError("S2 含重复观测，可能造成标签冲突或重复加权")
        seen.add(key)
    for first, second in pairs:
        left, right = samples[first], samples[second]
        if not np.array_equal(left["observation"]["action_mask"], right["observation"]["action_mask"]):
            raise ValueError("换位对的 mask 必须完全相同")
        if left["action"] == right["action"] or left["return_to_go"] != right["return_to_go"]:
            raise ValueError("换位必须改变动作标签并保留回报")
    stats = dataset_statistics(samples, pairs)
    if len(pairs) < 6 or stats["mask_only_max_accuracy"] >= 0.95:
        raise ValueError("S2 数据缺少足够的同 mask 不同动作对")
    if stats["constant_value_mse"] < 0.01 or stats["return_min"] != 0:
        raise ValueError("S2 回报需包含失败 0 和足够差异，不能用常数回归假通过")
    if 30 not in stats["action_counts"] or not any(action < 30 and action % 3 == 1 for action in stats["action_counts"]):
        raise ValueError("S2 必须覆盖结束回合与第二个敌方目标")
    return stats


def collect_dataset(config: OverfitConfig) -> tuple[list[dict[str, Any]], list[list[int]], list[dict[str, Any]]]:
    """按三遭遇均衡抽取随机轨迹，实际抽到的动作仅作记忆标签。"""

    selection_rng = np.random.default_rng(config.selection_seed)
    originals: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    seen: set[bytes] = set()
    for encounter in Encounter:
        candidates: list[dict[str, Any]] = []
        for _ in range(config.episodes_per_encounter):
            index = len(episodes)
            seed = config.env_seed_start + index
            agent_seed = config.agent_seed_start + index
            env = FlattenWrapper(LightspeedBattleEnv())
            observation = env.reset(seed, encounter)
            agent = MaskedRandomAgent(agent_seed)
            trajectory: list[dict[str, Any]] = []
            rewards: list[float] = []
            done = False
            while not done:
                action = agent.decide(observation).action
                trajectory.append({
                    "observation": observation,
                    "action": action,
                    "env_seed": seed,
                    "agent_seed": agent_seed,
                    "encounter": encounter.value,
                    "step": len(trajectory),
                    "augmentation": None,
                })
                observation, reward, terminated, truncated, info = env.step(action)
                rewards.append(reward)
                done = terminated or truncated
            if not terminated or truncated or any(reward != 0.0 for reward in rewards[:-1]):
                raise ValueError("采集轨迹违反 D27 battle 奖励或终止契约")
            returns_to_go = true_return_to_go(
                rewards, terminated=terminated, truncated=truncated
            )
            for sample, return_to_go in zip(trajectory, returns_to_go):
                sample["return_to_go"] = return_to_go
            for sample in trajectory:
                key = observation_key(sample["observation"])
                if sample["observation"]["action_mask"].sum() >= 2 and key not in seen:
                    candidates.append(sample)
                    seen.add(key)
            episodes.append(
                {
                    "episode_id": f"battle-{seed}",
                    "env_seed": seed,
                    "agent_seed": agent_seed,
                    "encounter": encounter.value,
                    "actions": [sample["action"] for sample in trajectory],
                    "rewards": rewards,
                    "return_to_go": returns_to_go,
                    "terminated": terminated,
                    "truncated": truncated,
                    "won": info["battle_won"],
                    "battle_won": info["battle_won"],
                    "run_won": None,
                    "task_outcome": info["task_outcome"],
                    "termination_reason": info["termination_reason"],
                    **BATTLE_REWARD_CONTRACT.to_dict(),
                }
            )
        if len(candidates) < config.samples_per_encounter:
            raise ValueError("真实轨迹不足以抽取配置要求的样本数")
        chosen = selection_rng.choice(len(candidates), config.samples_per_encounter, replace=False)
        originals.extend(candidates[int(index)] for index in chosen)
    samples = originals.copy()
    seen = {observation_key(sample["observation"]) for sample in samples}
    pairs: list[list[int]] = []
    for index, sample in enumerate(originals):
        swapped = swapped_sample(sample)
        if swapped is not None and observation_key(swapped["observation"]) not in seen:
            seen.add(observation_key(swapped["observation"]))
            pairs.append([index, len(samples)])
            samples.append(swapped)
    validate_dataset(samples, pairs)
    return samples, pairs, episodes


def serialize_dataset(samples: list[dict[str, Any]], pairs: list[list[int]], episodes: list[dict[str, Any]]) -> bytes:
    payload = {
        "format_version": 2,
        "reward_contract": BATTLE_REWARD_CONTRACT.to_dict(),
        "label_meaning": "随机策略实际选择的合法动作与实际回报，仅用于同批记忆诊断",
        "samples": [
            {**sample, "observation": {name: value.tolist() for name, value in sample["observation"].items()}}
            for sample in samples
        ],
        "swap_pairs": pairs,
        "episodes": episodes,
    }
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def train_overfit(samples: list[dict[str, Any]], pairs: list[list[int]], config: OverfitConfig, model_seed: int) -> tuple[MlpActorCritic, dict[str, Any]]:
    """固定全批量 Adam；分别记录 policy 与 value，避免总 loss 掩盖单头失败。"""

    validate_dataset(samples, pairs)
    torch.manual_seed(model_seed)
    model = MlpActorCritic(MlpConfig.from_registry())
    batch = batch_flat_inputs([sample["observation"] for sample in samples])
    actions = torch.tensor([sample["action"] for sample in samples], dtype=torch.int64)
    returns = torch.tensor([sample["return_to_go"] for sample in samples], dtype=torch.float32)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    history: list[dict[str, Any]] = []
    all_gradients_finite = True
    for update in range(config.updates + 1):
        distribution, value, _ = model.distribution_and_value(batch)
        policy_loss = -distribution.log_prob(actions).mean()
        value_mse = (value - returns).square().mean()
        loss = policy_loss + config.value_weight * value_mse
        if not torch.isfinite(loss):
            raise FloatingPointError(f"S2 第 {update} 步 loss 非有限")
        if update % config.log_every == 0 or update == config.updates:
            predicted = distribution.probs.argmax(dim=-1)
            history.append({
                "update": update,
                "policy_loss": float(policy_loss.detach()),
                "value_mse": float(value_mse.detach()),
                "accuracy": float((predicted == actions).float().mean()),
                "swap_pair_accuracy": float(np.mean([
                    bool(predicted[left] == actions[left] and predicted[right] == actions[right])
                    for left, right in pairs
                ])),
                "illegal_probability_max": float(distribution.probs[~batch["action_mask"]].max().detach()),
                "by_encounter_accuracy": {
                    encounter.value: float((predicted == actions)[torch.tensor([
                        sample["encounter"] == encounter.value for sample in samples
                    ])].float().mean()) for encounter in Encounter
                },
            })
        if update == config.updates:
            break
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        all_gradients_finite = all(
            parameter.grad is not None and bool(torch.isfinite(parameter.grad).all())
            for parameter in model.parameters()
        )
        if not all_gradients_finite:
            raise FloatingPointError(f"S2 第 {update} 步缺梯度或梯度非有限")
        optimizer.step()
    initial, final = history[0], history[-1]
    checks = {
        "accuracy": final["accuracy"] >= config.min_accuracy,
        "same_mask_pairs": final["swap_pair_accuracy"] == 1.0,
        "policy_loss_reduction": final["policy_loss"] <= initial["policy_loss"] * config.max_policy_loss_ratio,
        "value_mse": final["value_mse"] <= config.max_value_mse,
        "value_mse_reduction": final["value_mse"] <= initial["value_mse"] * config.max_value_mse_ratio,
        "gradients_finite": all_gradients_finite,
        "illegal_probability_zero": all(point["illegal_probability_max"] == 0.0 for point in history),
    }
    return model, {
        "model_seed": model_seed, "model_config": asdict(model.config),
        "history": history, "checks": checks, "passed": all(checks.values()),
    }


def weight_hash(model: MlpActorCritic) -> str:
    """按参数名和原始权重摘要比较重跑，排除容器文件时间戳差异。"""

    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(value.detach().cpu().numpy().tobytes())
    return digest.hexdigest()
