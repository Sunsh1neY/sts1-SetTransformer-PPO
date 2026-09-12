"""固定真实卡组任务的PPO采集、更新和可恢复训练快照。"""
from __future__ import annotations

import copy
import hashlib
import time
from pathlib import Path

import numpy as np
import torch

from sts.env.comparison import ComparisonEnv, load_contract
from sts.env.lightspeed import _load_backend
from sts.env.real_deck import load_batch, sample_scene
from sts.models.comparison import ComparisonActorCritic, encode, tensor_batch
from sts.train.ppo import compute_gae, ppo_loss


def check_deadline(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError("已达到正式训练与评估时间预算")


def fingerprint():
    root = Path(__file__).parents[2]
    files = ["sts/train/comparison.py", "sts/models/comparison.py", "sts/env/comparison.py", "sts/env/real_deck.py",
             "sts/env/public_battle.py", "sts/train/ppo.py", "sts/env/comparison-contract.json", "sts/env/real-deck-batch.json",
             "scripts/run-comparison-ppo.py", "sts/env/lightspeed.py", "sts/env/public-battle-contract.json"]
    result = {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in files}
    result["backend"] = hashlib.sha256(Path(_load_backend().__file__).read_bytes()).hexdigest()
    return result


class ComparisonTrainer:
    def __init__(self, kind, group=0, iterations=64, num_envs=8, num_steps=64, device="cpu"):
        self.config = dict(kind=kind, group=group, iterations=iterations, num_envs=num_envs, num_steps=num_steps, device=device)
        self.device, self.iteration = torch.device(device), 0
        self.env_steps, self.phase = 0, "idle"
        self.batch = load_batch()
        self.contract = load_contract()
        self.scene_rng = np.random.default_rng(700100 + group)
        self.shuffle_rng = np.random.default_rng(720100 + group)
        self.seed_cursor = 3000000 + group * 1000000
        self.envs = [ComparisonEnv() for _ in range(num_envs)]
        self.active = [{} for _ in self.envs]
        self.observations = [self.reset(i) for i in range(num_envs)]
        torch.manual_seed(710100 + group)
        if self.device.type == "cuda":
            torch.cuda.manual_seed_all(710100 + group)
        self.model = ComparisonActorCritic(kind, len(self.observations[0]["global"])).to(self.device)
        self.action_rng = torch.Generator(device=device).manual_seed(730100 + group)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.00025, eps=0.00001)

    def reset(self, i):
        scene = sample_scene(self.batch, self.scene_rng, "train")
        seed = self.seed_cursor
        self.seed_cursor += 1
        self.active[i] = {"scene": scene, "seed": seed, "actions": [], "return": 0.0}
        return encode(self.envs[i].reset(scene, seed, purpose="train"))

    def batch_tensor(self, observations):
        return {k: v.to(self.device) for k, v in tensor_batch(observations).items()}

    def iteration_step(self, deadline=None):
        if self.iteration >= self.config["iterations"]:
            raise ValueError("训练已达到固定步数")
        observations, actions, logs, values, rewards, dones, truncs, nextvalues, episodes = [], [], [], [], [], [], [], [], []
        self.model.eval()
        self.phase = "collect"
        started = time.monotonic()
        for _ in range(self.config["num_steps"]):
            check_deadline(deadline)
            current = self.batch_tensor(self.observations)
            with torch.no_grad():
                distribution, value = self.model.distribution(current)
                action = torch.multinomial(distribution.probs, 1, generator=self.action_rng).squeeze(1)
                log = distribution.log_prob(action)
            observations.append(current)
            actions.append(action)
            logs.append(log)
            values.append(value)
            r, d, tr, finals = [], [], [], []
            for i, a in enumerate(action.cpu().tolist()):
                if not self.observations[i]["mask"][a]:
                    raise RuntimeError("采集器出现非法动作")
                obs, reward, done, truncated, info = self.envs[i].step(a)
                self.env_steps += 1
                encoded = encode(obs)
                finals.append(encoded)
                self.active[i]["actions"].append(a)
                self.active[i]["return"] += reward
                r.append(reward); d.append(done); tr.append(truncated)
                if done or truncated:
                    episodes.append({"return": self.active[i]["return"] if done else None,
                                     "observed_partial_reward": self.active[i]["return"], "terminated": done, "truncated": truncated,
                                     "reason": info["termination_reason"], "steps": len(self.active[i]["actions"]),
                                     "group_id": self.active[i]["scene"]["group_id"], "seed": self.active[i]["seed"],
                                     "card_entities": info["card_entities"]})
                    self.observations[i] = self.reset(i)
                else:
                    self.observations[i] = encoded
            with torch.no_grad():
                nextvalues.append(self.model(self.batch_tensor(finals))[1])
            rewards.append(r); dones.append(d); truncs.append(tr)
        rewards = torch.tensor(rewards, device=self.device)
        dones = torch.tensor(dones, dtype=torch.bool, device=self.device)
        truncs = torch.tensor(truncs, dtype=torch.bool, device=self.device)
        values = torch.stack(values)
        advantages, returns = compute_gae(rewards, values, torch.stack(nextvalues), dones,
                                         truncated=truncs, episode_ends=dones | truncs, gamma=1.0, gae_lambda=0.95)
        flat = {k: torch.stack([o[k] for o in observations]).flatten(0, 1) for k in observations[0]}
        actions, logs, oldvalues, advantages, returns = [v.flatten() for v in (torch.stack(actions), torch.stack(logs), values, advantages, returns)]
        self.model.train()
        self.phase = "update"
        lr = 0.00025 * (1 - self.iteration / self.config["iterations"])
        self.optimizer.param_groups[0]["lr"] = lr
        metrics = []
        size = len(actions)
        for _ in range(4):
            order = self.shuffle_rng.permutation(size)
            for start in range(0, size, size // 4):
                check_deadline(deadline)
                idx = torch.as_tensor(order[start:start + size // 4], device=self.device)
                mb = {k: v[idx] for k, v in flat.items()}
                distribution, value = self.model.distribution(mb)
                loss, measured = ppo_loss(distribution.log_prob(actions[idx]), logs[idx], advantages[idx], value,
                                          oldvalues[idx], returns[idx], distribution.entropy(),
                                          clip_coef=0.2, ent_coef=0.01, vf_coef=0.5)
                if not torch.isfinite(loss):
                    raise FloatingPointError("PPO损失非有限")
                self.optimizer.zero_grad(set_to_none=True)
                loss.backward()
                grad = torch.nn.utils.clip_grad_norm_(self.model.parameters(), 0.5, error_if_nonfinite=True)
                self.optimizer.step()
                metrics.append({k: float(v.detach()) for k, v in measured.items()} | {"grad_norm": float(grad)})
        self.iteration += 1
        self.phase = "idle"
        variance = float(returns.var(unbiased=False))
        result = {"iteration": self.iteration, "steps": self.iteration * size, "seconds": time.monotonic() - started,
                  "learning_rate": lr, "episodes": len(episodes), "truncated": sum(e["truncated"] for e in episodes),
                  "actual_env_steps": self.env_steps,
                  "mean_return": float(np.mean([e["return"] for e in episodes if e["terminated"]])) if any(e["terminated"] for e in episodes) else None,
                  "explained_variance": 1 - float((returns - oldvalues).var(unbiased=False)) / variance if variance > 0 else None,
                  **{k: float(np.mean([m[k] for m in metrics])) for k in metrics[0]}}
        return result, episodes

    def save(self, path):
        state = {"schema": "comparison-ppo-checkpoint-v1", "config": self.config, "iteration": self.iteration,
                 "env_steps": self.env_steps, "phase": self.phase, "resume_allowed": self.phase == "idle",
                 "model": self.model.state_dict(), "optimizer": self.optimizer.state_dict(),
                 "scene_rng": self.scene_rng.bit_generator.state, "shuffle_rng": self.shuffle_rng.bit_generator.state,
                 "action_rng": self.action_rng.get_state(), "torch_rng": torch.get_rng_state(),
                 "cuda_rng": torch.cuda.get_rng_state_all() if self.device.type == "cuda" else [],
                 "seed_cursor": self.seed_cursor, "active": copy.deepcopy(self.active), "fingerprint": fingerprint()}
        torch.save(state, path)

    @classmethod
    def load(cls, path):
        state = torch.load(path, map_location="cpu", weights_only=False)
        if state.get("schema") != "comparison-ppo-checkpoint-v1" or state["fingerprint"] != fingerprint():
            raise ValueError("训练快照版本或源码指纹不一致")
        if not state.get("resume_allowed"):
            raise ValueError("采集或更新中途的失败快照只作诊断，不支持精确续训")
        trainer = cls(**state["config"])
        trainer.model.load_state_dict(state["model"])
        trainer.optimizer.load_state_dict(state["optimizer"])
        trainer.iteration, trainer.seed_cursor = state["iteration"], state["seed_cursor"]
        trainer.env_steps = state["env_steps"]
        trainer.active = state["active"]
        trainer.observations = []
        for env, active in zip(trainer.envs, trainer.active):
            obs = env.reset(active["scene"], active["seed"], purpose="train")
            for action in active["actions"]:
                obs, reward, done, truncated, _ = env.step(action)
                if done or truncated:
                    raise ValueError("快照包含已结束的活动局")
            trainer.observations.append(encode(obs))
        trainer.scene_rng.bit_generator.state = state["scene_rng"]
        trainer.shuffle_rng.bit_generator.state = state["shuffle_rng"]
        trainer.action_rng.set_state(state["action_rng"])
        torch.set_rng_state(state["torch_rng"])
        if state["cuda_rng"]:
            torch.cuda.set_rng_state_all(state["cuda_rng"])
        return trainer


@torch.no_grad()
def evaluate(model, cases, device, deadline=None, batch_size=8):
    """固定开发场景上贪心评估；不采样动作，逐场保留截断身份。"""
    model.eval()
    results = []
    for start in range(0, len(cases), batch_size):
        subset = cases[start:start + batch_size]
        envs = [ComparisonEnv() for _ in subset]
        observations = [encode(e.reset(c["scene"], c["seed"])) for e, c in zip(envs, subset)]
        active = list(range(len(subset)))
        totals, steps = [0.0] * len(subset), [0] * len(subset)
        while active:
            check_deadline(deadline)
            inputs = {k: v.to(device) for k, v in tensor_batch([observations[i] for i in active]).items()}
            distribution, _ = model.distribution(inputs)
            actions = distribution.probs.argmax(-1).cpu().tolist()
            next_active = []
            for i, action in zip(active, actions):
                obs, reward, done, truncated, info = envs[i].step(action)
                observations[i] = encode(obs)
                totals[i] += reward
                steps[i] += 1
                if done or truncated:
                    results.append({"case_id": subset[i]["case_id"], "group_id": subset[i]["scene"]["group_id"],
                                    "encounter": subset[i]["scene"]["encounter"], "profile": subset[i]["scene"]["profile_id"],
                                    "reward": totals[i] if done else None, "observed_partial_reward": totals[i],
                                    "terminated": done, "truncated": truncated, "reason": info["termination_reason"],
                                    "hp": obs["player"]["hp"], "max_hp": obs["player"]["max_hp"], "steps": steps[i],
                                    "card_entities": info["card_entities"]})
                else:
                    next_active.append(i)
            active = next_active
    return sorted(results, key=lambda r: r["case_id"])
