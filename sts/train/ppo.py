"""D25 S3：从锁定 CleanRL ppo.py 改编的显式 masked PPO。

Copyright (c) 2019 CleanRL developers，MIT许可见 licenses/cleanrl-license.txt。
来源、逐段对应与本项目差异见 docs/ppo-source.md。
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import Tensor, nn

from sts import Encounter, FlattenWrapper, LightspeedBattleEnv
from sts.env.lightspeed import _load_backend
from sts.models.mlp import (
    FlatBatch,
    MlpActorCritic,
    MlpConfig,
    batch_flat_inputs,
    load_mlp_checkpoint,
    save_mlp_checkpoint,
)
from sts.rewards import (
    BATTLE_ENVIRONMENT_VERSION,
    BATTLE_REWARD_CONTRACT,
    BATTLE_REWARD_VERSION,
    BATTLE_TASK_SPEC_ID,
    BATTLE_TERMINATION_RULE_VERSION,
    DOCUMENT_VERSION,
    TASK_TYPE_BATTLE,
    RewardContract,
    require_reward_contract,
)


@dataclass(frozen=True)
class PPOConfig:
    total_timesteps: int = 262144
    num_envs: int = 8
    num_steps: int = 128
    num_minibatches: int = 4
    update_epochs: int = 4
    learning_rate: float = 0.00025
    adam_eps: float = 0.00001
    gamma: float = 1.0
    gae_lambda: float = 0.95
    clip_coef: float = 0.2
    ent_coef: float = 0.01
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    anneal_lr: bool = True
    target_kl: float | None = None
    model_seed: int = 600000
    sampling_seed: int = 610000
    shuffle_seed: int = 620000
    train_seed_start: int = 1000000
    train_seed_stop: int = 2000000
    max_turns: int = 50
    document_version: str = DOCUMENT_VERSION
    task_type: str = TASK_TYPE_BATTLE
    task_spec_id: str = BATTLE_TASK_SPEC_ID
    reward_version: str = BATTLE_REWARD_VERSION
    alpha_hp: float = 0.5
    beta: float = 0.0
    potential_version: str | None = None
    environment_version: str = BATTLE_ENVIRONMENT_VERSION
    termination_rule_version: str = BATTLE_TERMINATION_RULE_VERSION

    @property
    def batch_size(self) -> int:
        return self.num_envs * self.num_steps

    @property
    def num_iterations(self) -> int:
        return self.total_timesteps // self.batch_size

    @property
    def reward_contract(self) -> RewardContract:
        return RewardContract(
            document_version=self.document_version,
            task_type=self.task_type,
            task_spec_id=self.task_spec_id,
            reward_version=self.reward_version,
            gamma=self.gamma,
            alpha_hp=self.alpha_hp,
            beta=self.beta,
            potential_version=self.potential_version,
            environment_version=self.environment_version,
            termination_rule_version=self.termination_rule_version,
        )

    def __post_init__(self) -> None:
        for name in ("total_timesteps", "num_envs", "num_steps", "num_minibatches", "update_epochs", "max_turns"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} 必须为正整数")
        if self.total_timesteps % self.batch_size or self.batch_size % self.num_minibatches:
            raise ValueError("总步数必须整除 rollout 大小，rollout 必须整除 minibatch 数")
        if self.batch_size // self.num_minibatches < 2:
            raise ValueError("每个 minibatch 至少需要两个样本以归一化优势")
        if self.gamma != 1.0 or not 0 <= self.gae_lambda <= 1:
            raise ValueError("D27 要求 gamma=1；GAE lambda 必须在[0,1]")
        for name in ("learning_rate", "adam_eps", "clip_coef", "max_grad_norm"):
            if not np.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} 必须是有限正数")
        if not 0 < self.clip_coef < 1 or self.ent_coef < 0 or self.vf_coef < 0:
            raise ValueError("clip_coef须在(0,1)，loss系数非负")
        if not 1000000 <= self.train_seed_start < self.train_seed_stop <= 2000000:
            raise ValueError("S3训练环境seed锁定在[1000000,2000000)，与开发诊断互斥")
        if not np.isfinite(self.ent_coef) or not np.isfinite(self.vf_coef):
            raise ValueError("loss系数必须有限")
        for name in ("model_seed", "sampling_seed", "shuffle_seed"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 100000:
                raise ValueError(f"{name} 必须是 >=100000 的整数")
        if self.target_kl is not None and (not np.isfinite(self.target_kl) or self.target_kl <= 0):
            raise ValueError("target_kl必须为None或有限正数")
        if self.reward_contract != BATTLE_REWARD_CONTRACT:
            raise ValueError("当前 PPO 入口只接入 v6 的 minimal-v1 battle 契约")


@torch.no_grad()
def compute_gae(
    rewards: Tensor, values: Tensor, next_values: Tensor, terminated: Tensor,
    *, truncated: Tensor | None = None, episode_ends: Tensor | None = None,
    gamma: float = 1.0, gae_lambda: float = 0.95,
) -> tuple[Tensor, Tensor]:
    """真终止屏蔽自举；终止、reset和buffer边界屏蔽优势递推。"""

    if rewards.ndim != 2 or rewards.numel() == 0:
        raise ValueError("GAE 输入必须为非空 [T,N]")
    truncations = torch.zeros_like(terminated) if truncated is None else truncated
    ends = terminated | truncations if episode_ends is None else episode_ends
    if any(value.shape != rewards.shape for value in (values, next_values, terminated, truncations, ends)):
        raise ValueError("GAE 输入 shape 必须全部一致")
    if any(value.dtype != torch.bool for value in (terminated, truncations, ends)):
        raise TypeError("GAE 终止、截断及episode边界必须为bool")
    if (terminated & truncations).any():
        raise ValueError("同一 transition 不能同时 terminated 与 truncated")
    if ((terminated | truncations) & ~ends).any():
        raise ValueError("终止或外部截断必须同时结束当前episode递推")
    if not 0 <= gamma <= 1 or not 0 <= gae_lambda <= 1:
        raise ValueError("gamma与GAE lambda须在[0,1]")
    if not all(bool(torch.isfinite(value).all()) for value in (rewards, values, next_values)):
        raise ValueError("GAE输入必须有限")
    advantages = torch.zeros_like(rewards)
    last_advantage = torch.zeros_like(rewards[0])
    for t in reversed(range(rewards.shape[0])):
        next_value = next_values[t].masked_fill(terminated[t], 0.0)
        delta = rewards[t] + gamma * next_value - values[t]
        last_advantage = delta + gamma * gae_lambda * last_advantage.masked_fill(ends[t], 0.0)
        advantages[t] = last_advantage
    return advantages, advantages + values


def ppo_loss(
    new_logprob: Tensor, old_logprob: Tensor, advantages: Tensor,
    new_value: Tensor, old_value: Tensor, returns: Tensor, entropy: Tensor,
    *, clip_coef: float = 0.2, ent_coef: float = 0.01, vf_coef: float = 0.5,
    norm_adv: bool = True, clip_value: bool = True,
) -> tuple[Tensor, dict[str, Tensor]]:
    """CleanRL的剪切策略目标、价值剪切、优势归一化及熵项。"""

    if new_logprob.ndim != 1 or new_logprob.numel() == 0:
        raise ValueError("PPO loss输入必须为非空[B]")
    operands = (old_logprob, advantages, new_value, old_value, returns, entropy)
    if any(value.shape != new_logprob.shape for value in operands):
        raise ValueError("PPO loss所有输入shape须一致，禁止广播混合样本")
    if norm_adv and new_logprob.numel() < 2:
        raise ValueError("优势归一化至少需要两个样本")
    old_logprob, old_value = old_logprob.detach(), old_value.detach()
    advantages, returns = advantages.detach(), returns.detach()
    logratio = new_logprob - old_logprob
    ratio = logratio.exp()
    if norm_adv:
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
    policy_loss = torch.maximum(-advantages * ratio, -advantages * ratio.clamp(1 - clip_coef, 1 + clip_coef)).mean()
    value_error = (new_value - returns).square()
    if clip_value:
        clipped_value = old_value + (new_value - old_value).clamp(-clip_coef, clip_coef)
        value_error = torch.maximum(value_error, (clipped_value - returns).square())
    value_loss = 0.5 * value_error.mean()
    entropy_mean = entropy.mean()
    loss = policy_loss + vf_coef * value_loss - ent_coef * entropy_mean
    return loss, {
        "policy_loss": policy_loss.detach(), "value_loss": value_loss.detach(),
        "entropy": entropy_mean.detach(),
        "approx_kl": ((ratio - 1) - logratio).mean().detach(),
        "clip_fraction": ((ratio - 1).abs() > clip_coef).float().mean().detach(),
    }


@dataclass
class PPOBatchDecision:
    actions: Tensor
    logprobs: Tensor
    values: Tensor


class PPOAgent:
    """批量Agent拥有独立采样RNG；采集器只转交已选动作。"""

    def __init__(self, model: MlpActorCritic, seed: int) -> None:
        self.model = model
        self.rng = torch.Generator(device="cpu").manual_seed(seed)

    @torch.no_grad()
    def decide_batch(self, batch: FlatBatch) -> PPOBatchDecision:
        distribution, values, _ = self.model.distribution_and_value(batch)
        actions = torch.multinomial(distribution.probs, 1, generator=self.rng).squeeze(-1)
        return PPOBatchDecision(actions, distribution.log_prob(actions), values)


@dataclass
class Rollout:
    observations: FlatBatch
    actions: Tensor
    logprobs: Tensor
    values: Tensor
    rewards: Tensor
    terminated: Tensor
    truncated: Tensor
    episode_ends: Tensor
    next_values: Tensor
    episodes: list[dict[str, Any]]


class RolloutCollector:
    """同步批量环境，显式reset；保存原观测mask并严格区分终止与采样切段。"""

    def __init__(self, config: PPOConfig) -> None:
        self.config = config
        self.envs = [FlattenWrapper(LightspeedBattleEnv(max_turns=config.max_turns)) for _ in range(config.num_envs)]
        self.seed_cursor = config.train_seed_start
        self.active: list[dict[str, Any]] = [{} for _ in self.envs]
        self.observations = [self._reset(index) for index in range(config.num_envs)]

    def _reset(self, index: int):
        if self.seed_cursor >= self.config.train_seed_stop:
            raise ValueError("训练seed区间耗尽，拒绝进入诊断区间或静默重用")
        seed = self.seed_cursor
        self.seed_cursor += 1
        encounter = list(Encounter)[(seed - self.config.train_seed_start) % 3]
        self.active[index] = {"seed": seed, "encounter": encounter.value, "actions": [], "total_reward": 0.0}
        return self.envs[index].reset(seed, encounter)

    @torch.no_grad()
    def collect(self, agent: PPOAgent) -> Rollout:
        batches: list[FlatBatch] = []
        decisions: list[PPOBatchDecision] = []
        rewards = torch.zeros(self.config.num_steps, self.config.num_envs)
        terminated = torch.zeros_like(rewards, dtype=torch.bool)
        truncated_flags = torch.zeros_like(rewards, dtype=torch.bool)
        next_batches: list[FlatBatch] = []
        episodes: list[dict[str, Any]] = []
        for t in range(self.config.num_steps):
            batch = batch_flat_inputs(self.observations)
            decision = agent.decide_batch(batch)
            batches.append(batch)
            decisions.append(decision)
            for index, env in enumerate(self.envs):
                action = int(decision.actions[index])
                if not self.observations[index]["action_mask"][action]:
                    raise ValueError("Agent选中非法动作")
                observation, reward, done, truncated, info = env.step(action)
                if not np.isfinite(reward) or (not done and reward != 0):
                    raise ValueError("D27 battle_reward_v1 契约失败")
                rewards[t, index], terminated[t, index] = reward, done
                truncated_flags[t, index] = truncated
                state = self.active[index]
                state["actions"].append(action)
                state["total_reward"] += reward
                final_observation = observation
                if done or truncated:
                    won = bool(info["battle_won"])
                    if done and not np.isclose(state["total_reward"], reward):
                        raise ValueError("battle_reward_v1 只能在终局发放一次")
                    episodes.append({
                        **state,
                        "episode_id": f"battle-{state['seed']}",
                        "won": won,
                        "battle_won": won,
                        "run_won": None,
                        "hp": info["player_hp"],
                        "max_hp": info["player_max_hp"],
                        "timeout": info["timeout"],
                        "terminated": done,
                        "truncated": truncated,
                        "task_outcome": info["task_outcome"],
                        "termination_reason": info["termination_reason"],
                        "reward_base": state["total_reward"],
                        "reward_train": state["total_reward"],
                        **self.config.reward_contract.to_dict(),
                        "steps": len(state["actions"]), "turns": info["turn"],
                    })
                    observation = self._reset(index)
                self.observations[index] = observation
                # 自动reset前保留的最终观测用于截断自举；不能取新episode初态。
                if index == 0:
                    transition_next_observations = []
                transition_next_observations.append(final_observation)
            next_batches.append(batch_flat_inputs(transition_next_observations))
        values = torch.stack([decision.values for decision in decisions])
        next_values = torch.stack([agent.model(batch)[1] for batch in next_batches])
        episode_ends = terminated | truncated_flags
        return Rollout(
            {key: torch.stack([batch[key] for batch in batches]) for key in batches[0]},
            torch.stack([decision.actions for decision in decisions]),
            torch.stack([decision.logprobs for decision in decisions]),
            values, rewards, terminated, truncated_flags, episode_ends, next_values, episodes,
        )

    def state_dict(self) -> dict[str, Any]:
        import copy
        return {"seed_cursor": self.seed_cursor, "active": copy.deepcopy(self.active)}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        """C++无通用快照API：用当前局的seed和已执行动作恢复，不重新采样。"""

        if len(state["active"]) != len(self.envs):
            raise ValueError("checkpoint环境数量不匹配")
        cursor = state["seed_cursor"]
        seeds = [saved["seed"] for saved in state["active"]]
        if type(cursor) is not int or not self.config.train_seed_start + self.config.num_envs <= cursor <= self.config.train_seed_stop:
            raise ValueError("checkpoint seed_cursor越界")
        if len(set(seeds)) != len(seeds) or any(seed >= cursor for seed in seeds):
            raise ValueError("checkpoint active seed重复或越过cursor")
        self.seed_cursor = state["seed_cursor"]
        self.active = []
        self.observations = []
        for env, saved in zip(self.envs, state["active"]):
            if not self.config.train_seed_start <= saved["seed"] < self.config.train_seed_stop:
                raise ValueError("checkpoint包含范围外环境seed")
            observation = env.reset(saved["seed"], saved["encounter"])
            reward_sum = 0.0
            for action in saved["actions"]:
                observation, reward, done, truncated, _ = env.step(action)
                reward_sum += reward
                if done or truncated:
                    raise ValueError("checkpoint active局不应已终止")
            if reward_sum != saved["total_reward"]:
                raise ValueError("恢复的局内累计奖励不匹配")
            self.active.append({**saved, "actions": list(saved["actions"])})
            self.observations.append(observation)


class PPOTrainer:
    """更新步骤平铺可见；训练checkpoint包含优化器及全部实际使用的RNG。"""

    def __init__(self, config: PPOConfig) -> None:
        self.config = config
        torch.manual_seed(config.model_seed)
        self.model = MlpActorCritic(MlpConfig.from_registry())
        for layer in self.model.modules():
            if isinstance(layer, nn.Linear):
                gain = 0.01 if layer is self.model.policy_head else (1.0 if layer is self.model.value_head else np.sqrt(2))
                nn.init.orthogonal_(layer.weight, gain)
                nn.init.zeros_(layer.bias)
        self.agent = PPOAgent(self.model, config.sampling_seed)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=config.learning_rate, eps=config.adam_eps)
        self.shuffle_rng = np.random.default_rng(config.shuffle_seed)
        self.collector = RolloutCollector(config)
        self.iteration = 0

    def train_iteration(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        if self.iteration >= self.config.num_iterations:
            raise ValueError("已经达到预设训练预算")
        config = self.config
        self.model.train()
        learning_rate = config.learning_rate * (1 - self.iteration / config.num_iterations) if config.anneal_lr else config.learning_rate
        self.optimizer.param_groups[0]["lr"] = learning_rate
        rollout = self.collector.collect(self.agent)
        advantages, returns = compute_gae(
            rollout.rewards,
            rollout.values,
            rollout.next_values,
            rollout.terminated,
            truncated=rollout.truncated,
            episode_ends=rollout.episode_ends,
            gamma=config.gamma,
            gae_lambda=config.gae_lambda,
        )
        observations = {key: value.flatten(0, 1) for key, value in rollout.observations.items()}
        actions, old_logprobs = rollout.actions.flatten(), rollout.logprobs.flatten()
        old_values, returns, advantages = rollout.values.flatten(), returns.flatten(), advantages.flatten()
        minibatch_size = config.batch_size // config.num_minibatches
        metrics: list[dict[str, float]] = []
        for _ in range(config.update_epochs):
            indices = self.shuffle_rng.permutation(config.batch_size)
            for start in range(0, config.batch_size, minibatch_size):
                chosen = indices[start:start + minibatch_size]
                batch = {key: value[chosen] for key, value in observations.items()}
                _, logprobs, entropy, new_values, _ = self.model.action_and_value(batch, actions[chosen])
                loss, measured = ppo_loss(logprobs, old_logprobs[chosen], advantages[chosen], new_values, old_values[chosen], returns[chosen], entropy, clip_coef=config.clip_coef, ent_coef=config.ent_coef, vf_coef=config.vf_coef)
                if not torch.isfinite(loss) or not all(bool(torch.isfinite(value)) for value in measured.values()):
                    raise FloatingPointError("PPO loss或监控量非有限")
                self.optimizer.zero_grad(set_to_none=True)
                loss.backward()
                grad_norm = nn.utils.clip_grad_norm_(self.model.parameters(), config.max_grad_norm, error_if_nonfinite=True)
                self.optimizer.step()
                metrics.append({**{key: float(value) for key, value in measured.items()}, "grad_norm": float(grad_norm)})
            if config.target_kl is not None and metrics[-1]["approx_kl"] > config.target_kl:
                break
        variance = float(returns.var(unbiased=False))
        explained_variance = None if variance == 0 else 1 - float((returns - old_values).var(unbiased=False)) / variance
        self.iteration += 1
        episode_returns = [episode["total_reward"] for episode in rollout.episodes]
        result = {
            "iteration": self.iteration, "global_step": self.iteration * config.batch_size,
            "learning_rate": learning_rate, "explained_variance": explained_variance,
            **{key: float(np.mean([item[key] for item in metrics])) for key in metrics[0]},
            "episodes": len(rollout.episodes),
            "mean_return": float(np.mean(episode_returns)) if episode_returns else None,
            "win_rate": float(np.mean([episode["won"] for episode in rollout.episodes])) if rollout.episodes else None,
            "timeouts": sum(episode["timeout"] for episode in rollout.episodes),
            "illegal_actions": 0,
        }
        return result, rollout.episodes

    def save(self, path: str | Path, metadata: dict[str, Any] | None = None) -> None:
        save_mlp_checkpoint(path, self.model, optimizer=self.optimizer, extra={
            "trainer_version": 2, "config": asdict(self.config), "iteration": self.iteration,
            "reward_contract": self.config.reward_contract.to_dict(),
            "backend_sha256": hashlib.sha256(Path(_load_backend().__file__).read_bytes()).hexdigest(),
            "sampling_rng": self.agent.rng.get_state(), "shuffle_rng": self.shuffle_rng.bit_generator.state,
            "torch_rng": torch.get_rng_state(), "collector": self.collector.state_dict(),
            "metadata": metadata or {},
        })

    @classmethod
    def load(cls, path: str | Path) -> PPOTrainer:
        model, payload = load_mlp_checkpoint(path)
        extra = payload["extra"]
        if extra.get("trainer_version") != 2:
            raise ValueError("checkpoint不是支持的PPO训练快照")
        require_reward_contract(extra.get("reward_contract", {}))
        if extra.get("backend_sha256") != hashlib.sha256(Path(_load_backend().__file__).read_bytes()).hexdigest():
            raise ValueError("checkpoint后端指纹不匹配，不能假定轨迹可重放")
        trainer = cls(PPOConfig(**extra["config"]))
        if type(extra["iteration"]) is not int or not 0 <= extra["iteration"] <= trainer.config.num_iterations:
            raise ValueError("checkpoint iteration越界")
        trainer.model.load_state_dict(model.state_dict())
        trainer.optimizer.load_state_dict(payload["optimizer_state_dict"])
        trainer.iteration = extra["iteration"]
        trainer.agent.rng.set_state(extra["sampling_rng"])
        trainer.shuffle_rng.bit_generator.state = extra["shuffle_rng"]
        trainer.collector.load_state_dict(extra["collector"])
        torch.set_rng_state(extra["torch_rng"])
        return trainer
