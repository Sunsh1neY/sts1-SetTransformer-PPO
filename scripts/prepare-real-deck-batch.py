"""复用已验收中途卡组，冻结新战斗条件与开发批次，不重做历史重建。"""
import hashlib
import json
from collections import Counter
from pathlib import Path

from sts.env.public_battle import CONTRACT_HASH, _canonical, load_scene_manifest

ROOT = Path(__file__).resolve().parents[1]


def build():
    metadata, scenes = load_scene_manifest()
    rows = {}
    for scene in scenes:
        deck = sorted(scene["candidate"]["deck"])
        deck_hash = hashlib.sha256(_canonical(deck)).hexdigest()
        key = (scene["group_id"], deck_hash)
        if key not in rows:
            split = "development" if int(hashlib.sha256(("real-deck-dev-v1:" + key[0]).encode()).hexdigest()[:8], 16) % 5 == 0 else "train"
            rows[key] = {
                "deck_id": f"{key[0]}:deck:{deck_hash[:16]}", "group_id": key[0],
                "deck_sha256": deck_hash, "deck": deck, "split": split,
                "source_path": scene["source_path"], "raw_sha256": scene["raw_sha256"], "source_scene_ids": [],
            }
        rows[key]["source_scene_ids"].append(scene["scene_id"])
    batch = {
        "schema": "real-deck-batch-v1", "source_admission_policy": "real-deck-configured-battle-v1",
        "contract_sha256": CONTRACT_HASH, "source_manifest_sha256": metadata["sha256"],
        "split_policy": "sha256(real-deck-dev-v1:group_id)%5;0=development;others=train;no-formal-holdout",
        "sampling_policy": "uniform run group, then uniform distinct deck within group, then uniform profile and encounter",
        "common": {"entry_timing": "pre_combat_initialization", "initialization_phase": "before_destination_room_entry",
                   "character": "IRONCLAD", "act": 1, "floor": 8, "ascension": 20, "burning_elite": False},
        "profiles": {
            "full-basic": {"player": {"hp": 75, "max_hp": 75, "gold": 0}, "relics": ["Burning Blood"], "potions": [None, None]},
            "wounded-equipped": {"player": {"hp": 45, "max_hp": 75, "gold": 0}, "relics": ["Burning Blood", "Anchor", "Vajra"], "potions": ["Block Potion", "Weak Potion"]},
        },
        "encounters": ["JAW_WORM", "EXORDIUM_THUGS", "GREMLIN_NOB", "LAGAVULIN", "THREE_SENTRIES"],
        "decks": sorted(rows.values(), key=lambda r: r["deck_id"]),
    }
    train = {r["deck_sha256"] for r in rows.values() if r["split"] == "train"}
    dev = {r["deck_sha256"] for r in rows.values() if r["split"] == "development"}
    batch["summary"] = {"source_scenes": len(scenes), "deck_rows": len(rows),
                        "run_groups": len({r["group_id"] for r in rows.values()}),
                        "unique_decks": len(train | dev), "cross_split_identical_decks": len(train & dev),
                        "rows_by_split": dict(Counter(r["split"] for r in rows.values())),
                        "groups_by_split": {s: len({r["group_id"] for r in rows.values() if r["split"] == s}) for s in ("train", "development")},
                        "configured_scenes": len(rows) * len(batch["profiles"]) * len(batch["encounters"])}
    batch["payload_sha256"] = hashlib.sha256(_canonical(batch)).hexdigest()
    return batch


if __name__ == "__main__":
    batch = build()
    (ROOT / "sts/env/real-deck-batch.json").write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(batch["summary"], ensure_ascii=False))
