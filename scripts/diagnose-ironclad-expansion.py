"""五类动态牌、五遭遇的受控随机采集诊断；不执行模型训练。"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sts.env.ironclad import CONTRACT, CONTRACT_HASH, REGISTRY_HASH
from sts.env.ironclad_collection import IroncladCollectionEnv, load_capacity
from sts.env.lightspeed import _load_backend
from sts.models.ironclad import encode


def run(output):
    if output.exists():
        raise ValueError("诊断输出已存在，请使用新路径保留历史")
    start = time.monotonic()
    records = []
    for name in ("Rampage", "Blood for Blood", "Barricade", "Corruption", "Combust"):
        for upgrade in (0, 1):
            for encounter in CONTRACT["scope"]["encounters"]:
                for repeat in range(2):
                    seed = 983000 + len(records)
                    card = name + ("+1" if upgrade else "")
                    scene = {"entry_timing": "pre_combat_initialization",
                             "initialization_phase": "before_destination_room_entry",
                             "character": "IRONCLAD", "act": 1, "floor": 8, "ascension": 20,
                             "encounter": encounter, "burning_elite": False,
                             "player": {"hp": 75 if repeat == 0 else 45, "max_hp": 75, "gold": 0},
                             "deck": [card] * 2 + ["Strike_R"] * 3 + ["Defend_R"] * 3 +
                                     ["Bash", "Shrug It Off", "Power Through", "Burn"],
                             "relics": ["Burning Blood"] if repeat == 0 else ["Burning Blood", "Anchor", "Vajra"],
                             "potions": [None, None] if repeat == 0 else ["Block Potion", "Weak Potion"]}
                    env = IroncladCollectionEnv(max_actions=128)
                    obs = env.reset(scene, seed, diagnostic=True)
                    rng = np.random.default_rng(seed)
                    trace, peak = [], len(scene["deck"])
                    while True:
                        encoded = encode(obs)
                        assert encoded["valid"].sum() == sum(len(obs[k]) for k in ("hand", "draw_pile", "discard_pile", "exhaust_pile"))
                        action = int(rng.choice(np.flatnonzero(obs["action_mask"])))
                        trace.append(action)
                        obs, reward, terminated, truncated, info = env.step(action)
                        peak = max(peak, info["card_entities"])
                        if terminated or truncated:
                            encode(obs)  # 最终观测同样必须完整可编码。
                            records.append({"card": name, "upgrade": upgrade, "encounter": encounter,
                                            "profile": repeat, "seed": seed, "actions": trace,
                                            "terminated": terminated, "truncated": truncated, "reward": reward,
                                            "reason": info["termination_reason"], "peak_entities": peak,
                                            "allocated_entities": info["allocated_card_entities"]})
                            break
    summary = {"episodes": len(records), "transitions": sum(len(r["actions"]) for r in records),
               "terminated": sum(r["terminated"] for r in records),
               "truncated": sum(r["truncated"] for r in records),
               "wins": sum(r["reward"] > 0 for r in records),
               "max_entities": max(r["peak_entities"] for r in records),
               "elapsed_seconds": time.monotonic() - start}
    report = {"schema": "ironclad-controlled-integration-v1", "purpose": "development-diagnostic",
              "historical_decks": False, "policy": "random-legal", "summary": summary,
              "runtime_contract_sha256": CONTRACT_HASH, "registry_sha256": REGISTRY_HASH,
              "capacity_sha256": load_capacity()["sha256"],
              "backend_sha256": hashlib.sha256(Path(_load_backend().__file__).read_bytes()).hexdigest(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "records": records}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(run(parser.parse_args().output), ensure_ascii=False))
