"""读取同一固定战斗局面的 MLP checkpoint 概率，供 PPO 学习回放使用。"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import torch

from sts.env import Encounter, FlattenWrapper, LightspeedBattleEnv
from sts.env.lightspeed import ACTION_COUNT, ENEMY_FEATURES, GLOBAL_FEATURES
from sts.env.registry import DEFAULT_CARD_REGISTRY, TargetKind
from sts.models.mlp import batch_flat_inputs, load_mlp_checkpoint

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINTS = {
    32: ROOT / "runs" / "ppo-minimal-s3-20260908" / "checkpoint-0032.pt",
    128: ROOT / "runs" / "ppo-minimal-s3-20260908-resumed" / "checkpoint-0128.pt",
    256: ROOT / "runs" / "ppo-minimal-s3-20260908-resumed" / "checkpoint-0256.pt",
}


def _action_label(action: int, hand: list[Mapping[str, Any]]) -> tuple[str, str]:
    """保留动作槽位，同时给重复牌提供可读的语义合计键。"""

    if action == ACTION_COUNT - 1:
        return "end_turn", "结束回合"
    slot, target = divmod(action, 3)
    card = hand[slot]
    definition = DEFAULT_CARD_REGISTRY.from_registry_id(card["card_id"])
    if definition.target_kind == TargetKind.ENEMY:
        target_label = f"敌人[{target}]"
    else:
        target_label = "无目标"
    action_label = f"槽位{slot}:{definition.name}->{target_label}"
    semantic_label = f"{definition.name}->{target_label}"
    return action_label, semantic_label


def _state_payload(raw: Mapping[str, Any]) -> dict[str, Any]:
    """把真实规范观测转成教学展示需要的白名单字段。"""

    hand = [
        {
            "slot": slot,
            "card_id": int(card["card_id"]),
            "name": DEFAULT_CARD_REGISTRY.from_registry_id(card["card_id"]).name,
            "cost": int(card["cost"]),
            "target_kind": TargetKind(int(card["target_kind"])).name,
        }
        for slot, card in enumerate(raw["hand"])
    ]
    enemies = []
    for index, (row, valid) in enumerate(zip(raw["enemies"], raw["enemy_mask"])):
        if bool(valid):
            enemies.append({
                "index": index,
                **{
                    name: int(value)
                    for name, value in zip(ENEMY_FEATURES, row)
                },
            })

    legal_actions = []
    for action in np.flatnonzero(raw["action_mask"]):
        action_label, semantic_label = _action_label(int(action), hand)
        legal_actions.append({
            "action": int(action),
            "label": action_label,
            "semantic": semantic_label,
        })
    return {
        "global": {
            name: int(value)
            for name, value in zip(GLOBAL_FEATURES, raw["global"])
        },
        "hand": hand,
        "enemies": enemies,
        "legal_actions": legal_actions,
    }


def _read_distribution(model: torch.nn.Module, observation: Mapping[str, Any]) -> dict[str, Any]:
    """在 eval/no_grad 下读取掩码后分布、熵和 V(s)。"""

    batch = batch_flat_inputs([observation])
    model.eval()
    with torch.no_grad():
        distribution, value, masked_logits = model.distribution_and_value(batch)
    probabilities = distribution.probs[0].cpu().numpy().astype(np.float64)
    mask = np.asarray(observation["action_mask"], dtype=np.bool_)
    legal_actions = np.flatnonzero(mask)
    return {
        "value": float(value[0].item()),
        "entropy": float(distribution.entropy()[0].item()),
        "legal_probability_sum": float(probabilities[mask].sum()),
        "illegal_probability_max": float(probabilities[~mask].max()) if (~mask).any() else 0.0,
        "actions": {
            str(int(action)): {
                "probability": float(probabilities[action]),
                "masked_logit": float(masked_logits[0, action].item()),
            }
            for action in legal_actions
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=900000)
    parser.add_argument("--encounter", choices=[item.value for item in Encounter], default=Encounter.JAW_WORM.value)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "runs" / "ppo-training-observation-20260910" / "fixed-state-probabilities.json",
    )
    args = parser.parse_args()

    encounter = Encounter(args.encounter)
    base = LightspeedBattleEnv(max_turns=50, gamma=1.0)
    env = FlattenWrapper(base)
    observation = env.reset(seed=args.seed, encounter=encounter, ascension=0)
    raw = base.observation()
    state = _state_payload(raw)

    if len(state["legal_actions"]) < 2:
        raise ValueError("固定局面必须至少包含两个合法动作")

    models = []
    for iteration, checkpoint in CHECKPOINTS.items():
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)
        model, payload = load_mlp_checkpoint(checkpoint)
        result = _read_distribution(model, observation)
        actions = []
        semantic_totals: dict[str, float] = {}
        for item in state["legal_actions"]:
            action_key = str(item["action"])
            probability = result["actions"][action_key]["probability"]
            actions.append({**item, **result["actions"][action_key]})
            semantic_totals[item["semantic"]] = semantic_totals.get(item["semantic"], 0.0) + probability
        models.append({
            "iteration": iteration,
            "checkpoint": str(checkpoint),
            "checkpoint_iteration": payload["extra"].get("iteration"),
            "value": result["value"],
            "entropy": result["entropy"],
            "legal_probability_sum": result["legal_probability_sum"],
            "illegal_probability_max": result["illegal_probability_max"],
            "actions": actions,
            "semantic_probability_totals": semantic_totals,
        })

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "purpose": "ppo-training-observation-teaching",
        "state_source": {
            "seed": args.seed,
            "encounter": encounter.value,
            "selection_rule": "固定开发seed的初始状态，包含攻击、防御和结束回合选择",
        },
        "state": state,
        "models": models,
        "checks": {
            "same_action_mask_for_all_checkpoints": True,
            "action_count": len(state["legal_actions"]),
            "all_legal_probability_sums_close_to_one": all(
                np.isclose(item["legal_probability_sum"], 1.0)
                for item in models
            ),
            "all_illegal_probabilities_zero": all(
                np.isclose(item["illegal_probability_max"], 0.0)
                for item in models
            ),
        },
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "state": state, "models": models}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
