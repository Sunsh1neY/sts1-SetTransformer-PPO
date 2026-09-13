"""展示一个训练后checkpoint在固定开发场景上的逐动作贪心回放。"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch

from sts.env.comparison import ComparisonEnv, card_count
from sts.models.comparison import encode
from sts.train.comparison import ComparisonTrainer

ROOT = Path(__file__).resolve().parents[1]


def load_cases():
    path = ROOT / "scripts/run-comparison-ppo.py"
    spec = importlib.util.spec_from_file_location("comparison_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.cases()


def action_label(action, obs):
    if action == 50:
        return "结束回合"
    if action < 50:
        slot, target = divmod(action, 5)
        card = obs["hand"][slot]
        return f"出牌槽{slot}：{card['name']}（升级{card['upgrade_count']}，目标{target}）"
    slot, target = divmod(action - 51, 5)
    potion = obs["potions"][slot]
    return f"药水槽{slot}：{potion['name'] or '空'}（目标{target}）"


def compact(obs):
    enemies = [
        {"name": e["name"], "hp": e["hp"], "intent": e["intent_kind"], "intent_damage": e["intent_damage"]}
        for e in obs["enemies"] if e["present"]
    ]
    return {"hp": obs["player"]["hp"], "max_hp": obs["player"]["max_hp"],
            "block": obs["player"]["block"], "energy": obs["player"]["energy"],
            "turn": obs["player"]["turn"], "hand": [c["name"] for c in obs["hand"]],
            "enemies": enemies, "card_entities": card_count(obs)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=ROOT / "runs/comparison-ppo-20260912-gpu-v1/set-0/final.pt")
    parser.add_argument("--case-index", type=int, default=0)
    parser.add_argument("--output", type=Path, default=ROOT / "reference/post-training-eval-example.json")
    args = parser.parse_args()
    cases = load_cases()
    case = cases[args.case_index]
    trainer = ComparisonTrainer.load(args.checkpoint)
    if trainer.config["kind"] != "set":
        raise ValueError("展示脚本默认要求Set checkpoint")
    env = ComparisonEnv()
    obs = env.reset(case["scene"], case["seed"], purpose="development")
    initial = compact(obs)
    steps = []
    terminated = truncated = False
    while not (terminated or truncated):
        encoded = encode(obs)
        inputs = {key: torch.from_numpy(value[None]).to(trainer.device) for key, value in encoded.items()}
        with torch.no_grad():
            distribution, value = trainer.model.distribution(inputs)
            action = int(distribution.probs.argmax(-1).item())
            state_value = float(value.item())
        before = compact(obs)
        label = action_label(action, obs)
        obs, reward, terminated, truncated, info = env.step(action)
        steps.append({"step": len(steps) + 1, "action": action, "action_label": label,
                      "value_estimate": state_value, "before": before, "after": compact(obs),
                      "reward": reward, "terminated": terminated, "truncated": truncated,
                      "termination_reason": info["termination_reason"], "card_entities": info["card_entities"]})
    output = {"purpose": "post-training-greedy-example;not-formal-evaluation",
              "checkpoint": str(args.checkpoint.resolve()), "model": trainer.config["kind"],
              "case_id": case["case_id"], "environment_seed": case["seed"],
              "scene": {"deck_id": case["scene"]["deck_id"], "profile_id": case["scene"]["profile_id"],
                        "encounter": case["scene"]["encounter"], "group_id": case["scene"]["group_id"]},
              "initial": initial, "steps": steps,
              "result": {"total_reward": sum(s["reward"] for s in steps), "steps": len(steps),
                         "terminated": terminated, "truncated": truncated,
                         "final": compact(obs), "reason": steps[-1]["termination_reason"]}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"case_id": case["case_id"], "encounter": case["scene"]["encounter"],
                      "steps": len(steps), "reward": output["result"]["total_reward"],
                      "terminated": terminated, "truncated": truncated, "output": str(args.output)}, ensure_ascii=False))
    for row in steps:
        print(f"{row['step']:02d}. {row['action_label']} | HP {row['after']['hp']}/{row['after']['max_hp']} "
              f"格挡{row['after']['block']} 能量{row['after']['energy']} | 奖励{row['reward']} | {row['termination_reason']}")


if __name__ == "__main__":
    main()
