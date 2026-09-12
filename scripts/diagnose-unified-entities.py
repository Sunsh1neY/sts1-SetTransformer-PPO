"""至多64步统一实体采集和两次更新诊断；不是正式PPO训练实验。"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch

from sts.env.entities import collate, encode_observation
from sts.env.entitycollection import UnifiedEntityCollectionEnv
from sts.models.entities import UnifiedEntityActorCritic
from sts.train.entitycheckpoint import load_entity_checkpoint, save_entity_checkpoint
from sts.train.ppo import compute_gae, ppo_loss


def run(output, steps):
    if not 2 <= steps <= 64 or output.exists():
        raise ValueError("诊断仅允许2..64步且输出目录必须为新目录")
    output.mkdir(parents=True)
    start = time.monotonic()
    torch.set_num_threads(1)
    torch.manual_seed(986500)
    model = UnifiedEntityActorCritic()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.00025)
    samples, actions, old_logs, values, next_values, rewards, terminals, truncations, trace = ([] for _ in range(9))
    env, obs, episode = None, None, 0
    while len(samples) < steps:
        if env is None:
            n = 5 if episode % 2 == 0 else 96
            scene = {"entry_timing": "pre_combat_initialization", "initialization_phase": "before_destination_room_entry",
                     "character": "IRONCLAD", "act": 1, "floor": 8, "ascension": 20,
                     "encounter": "LAGAVULIN" if n == 5 else "EXORDIUM_THUGS", "burning_elite": False,
                     "player": {"hp": 75, "max_hp": 75, "gold": 0},
                     "deck": ["True Grit+1", "Sentinel", *["Strike_R"] * (n - 2)],
                     "relics": ["Burning Blood", "Vajra"], "potions": ["Weak Potion", "Block Potion"]}
            env = UnifiedEntityCollectionEnv(max_actions=16)
            obs = env.reset(scene, 986500 + episode, diagnostic=True)
            # 首个小场景从真实选牌暂停状态开始采样；准备动作不是PPO样本。
            if n == 5:
                slot = next(i for i, c in enumerate(obs["hand"]) if c["name"] == "True Grit")
                obs = env.step(slot * 5)[0]
            episode += 1
        sample = encode_observation(obs)
        with torch.no_grad():
            distribution, value = model.distribution(collate([sample]))
            index = distribution.sample()
            old_log = distribution.log_prob(index)
        final, reward, terminal, truncated, info = env.step(sample.routes[index.item()])
        with torch.no_grad():
            _, final_value = model(collate([encode_observation(final)]))
        samples.append(sample)
        actions.append(index.item())
        old_logs.append(old_log.item())
        values.append(value.item())
        next_values.append(final_value.item())
        rewards.append(reward)
        terminals.append(terminal)
        truncations.append(truncated)
        trace.append({"episode": episode - 1, "candidate_index": index.item(),
                      "kind": sample.candidates[index.item()].kind, "entities": len(sample.tokens),
                      "candidates": len(sample.candidates), "reward": reward,
                      "terminated": terminal, "truncated": truncated, "reason": info["termination_reason"]})
        obs = final
        if terminal or truncated:
            env = None
    if not terminals[-1] and not truncations[-1]:
        truncations[-1] = True
        trace[-1].update(truncated=True, reason="diagnostic_step_budget")
    # 最终状态已用于next_value；关闭活动环境后才保存更新边界checkpoint。
    env = None
    advantages, returns = compute_gae(torch.tensor(rewards)[:, None], torch.tensor(values)[:, None],
                                      torch.tensor(next_values)[:, None], torch.tensor(terminals)[:, None],
                                      truncated=torch.tensor(truncations)[:, None])
    batch = collate(samples)
    actions_t, old_logs_t, old_values = torch.tensor(actions), torch.tensor(old_logs), torch.tensor(values)

    def update(current, opt):
        opt.zero_grad(set_to_none=True)
        distribution, value = current.distribution(batch)
        sampled = distribution.sample()
        loss, metrics = ppo_loss(distribution.log_prob(actions_t), old_logs_t, advantages[:, 0], value,
                                 old_values, returns[:, 0], distribution.entropy())
        loss.backward()
        if not torch.isfinite(loss) or not all(torch.isfinite(p.grad).all() for p in current.parameters() if p.grad is not None):
            raise RuntimeError("非有限PPO更新")
        torch.nn.utils.clip_grad_norm_(current.parameters(), 0.5)
        opt.step()
        return sampled, loss.detach(), {k: float(v.detach()) for k, v in metrics.items()}

    _, first_loss, first_metrics = update(model, optimizer)
    checkpoint = output / "update-1.pt"
    save_entity_checkpoint(checkpoint, model, optimizer, update_index=1)
    expected_action, expected_loss, _ = update(model, optimizer)
    expected_state = copy.deepcopy(model.state_dict())
    restored, restored_optimizer, metadata = load_entity_checkpoint(checkpoint)
    actual_action, actual_loss, _ = update(restored, restored_optimizer)
    torch.testing.assert_close(actual_action, expected_action, rtol=0, atol=0)
    torch.testing.assert_close(actual_loss, expected_loss, rtol=0, atol=0)
    for key, value in restored.state_dict().items():
        torch.testing.assert_close(value, expected_state[key], rtol=0, atol=0)
    report = {"schema": "unified-entity-diagnostic-v1", "engineering_only": True,
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "architecture": model.configuration(), "parameters": sum(p.numel() for p in model.parameters()),
              "steps": steps, "episodes_started": episode,
              "selection_steps": sum(t["kind"] == "SELECT_CARD" for t in trace),
              "max_entities": max(t["entities"] for t in trace), "batch_shape": list(batch["entity_valid"].shape),
              "terminated": sum(terminals), "truncated": sum(truncations),
              "first_loss": float(first_loss), "first_metrics": first_metrics,
              "exact_next_update": True, "checkpoint_boundary": metadata["boundary"],
              "elapsed_seconds": time.monotonic() - start, "fingerprint": metadata["fingerprint"], "trace": trace}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {k: v for k, v in report.items() if k not in {"fingerprint", "trace", "first_metrics"}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=64)
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.steps), ensure_ascii=False))
