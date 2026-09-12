"""新增遭遇机制诊断；改遭遇的夹具不进入真实场景清单。"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np

from sts.env.public_battle import PublicBattleEnv, PUBLIC_CONTRACT, CONTRACT_HASH, load_scene_manifest
from sts.agents.public_runner import PublicRandomAgent
from sts.agents.rule_agent import RuleAgent

ELITES = {"GREMLIN_NOB", "LAGAVULIN", "THREE_SENTRIES"}


def diagnostic_scene(encounter, ascension):
    _, rows = load_scene_manifest()
    source = next(r for r in rows if r["candidate"]["ascension"] == 20)
    scene = copy.deepcopy(source["candidate"])
    scene["encounter"] = encounter
    scene["ascension"] = ascension
    scene["burning_elite"] = False
    if ascension < 11:
        scene["potions"] += [None] * (3 - len(scene["potions"]))
    # A0显式增补规则要求的空槽，保留所有来源库存；不是A0历史样本。
    return scene, source["scene_id"]


def check_observation(observation):
    enemies = observation["enemies"]
    mask = observation["action_mask"]
    assert len(enemies) == 5 and mask.shape == (66,) and mask.dtype == np.bool_
    for slot, enemy in enumerate(enemies):
        assert isinstance(enemy["present"], bool) and isinstance(enemy["targetable"], bool)
        assert isinstance(enemy["intent_kind"], str)
        assert enemy["intent_damage"] >= 0 and enemy["intent_hits"] >= 0
        if not enemy["targetable"]:
            assert enemy["intent_kind"] == "NONE"
            for card_slot, card in enumerate(observation["hand"]):
                if card["target_kind"] == "ENEMY":
                    assert not mask[card_slot * 5 + slot]
            for potion_slot, potion in enumerate(observation["potions"]):
                if potion.get("present") and potion["target_kind"] == "ENEMY":
                    assert not mask[51 + potion_slot * 5 + slot]


def run_case(encounter, ascension, seed, policy="random", max_actions=512):
    scene, source_id = diagnostic_scene(encounter, ascension)
    env = PublicBattleEnv(max_actions=max_actions)
    observation = env.reset(scene, seed, diagnostic=True)
    agent = PublicRandomAgent(seed + 2000000) if policy == "random" else RuleAgent()
    trace = []
    terminal = truncated = False
    reward = 0.0
    while not (terminal or truncated):
        check_observation(observation)
        action = int(agent.decide(observation).action)
        assert observation["action_mask"][action]
        trace.append({"turn": observation["player"]["turn"], "action": action,
                      "enemies": copy.deepcopy(observation["enemies"]),
                      "player_hp": observation["player"]["hp"]})
        observation, reward, terminal, truncated, info = env.step(action)
    check_observation(observation)
    assert terminal != truncated
    assert info["scene_kind"] == "mechanism-diagnostic"
    if truncated:
        assert reward == 0 and len(trace) == max_actions
    return {"encounter": encounter, "ascension": ascension, "seed": seed, "policy": policy,
            "source_scene_id": source_id, "scene_kind": "mechanism-diagnostic", "burning_elite": False,
            "diagnostic_overrides": ["encounter", "ascension", "burning_elite=false"] + (["append_empty_potion_slot_for_A0"] if ascension < 11 else []),
            "steps": len(trace), "terminated": terminal, "truncated": truncated, "reward": reward,
            "max_targetable": max(sum(e["targetable"] for e in t["enemies"]) for t in trace),
            "trace": trace, "final_observation": {k: v for k, v in observation.items() if k != "action_mask"},
            "final_info": info}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reference/public-encounter-diagnostics/diagnosis.json")
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args(argv)
    result = {"contract_sha256": CONTRACT_HASH, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "backend_sha256": hashlib.sha256((ROOT / "third_party/sts_lightspeed/build/slaythespire.cp313-win_amd64.pyd").read_bytes()).hexdigest(),
              "scene_kind": "mechanism-diagnostic", "cases": [], "failures": []}
    for encounter in PUBLIC_CONTRACT["encounters"]:
        for ascension in (0, 20):
            for policy in ("random", "rule"):
                for repeat in range(args.repeats):
                    seed = 710000 + repeat
                    try:
                        case = run_case(encounter, ascension, seed, policy)
                        result["cases"].append(case)
                    except Exception as exc:
                        result["failures"].append({"encounter": encounter, "ascension": ascension, "policy": policy, "seed": seed, "error": repr(exc)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": len(result["cases"]), "failures": result["failures"]}, ensure_ascii=False))
    return int(bool(result["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
