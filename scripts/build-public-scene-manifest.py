"""从审计索引生成完整场景实施清单；不投影为模型输入、不批准正式评估。"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("public_corpus_manifest_dependency", ROOT / "scripts/audit-public-corpus.py")
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)
DIRECT_POTIONS = set("Weak Potion|Regen Potion|EssenceOfSteel|Explosive Potion|Ancient Potion|FearPotion|LiquidBronze|Energy Potion|SpeedPotion|Dexterity Potion|HeartOfIron|Fruit Juice|Block Potion|Strength Potion|Swift Potion".split("|"))
GENERATED_CARDS = {"Wild Strike": ["Wound"], "Reckless Charge": ["Dazed"], "Power Through": ["Wound"], "Immolate": ["Burn"]}
# 此处为保守可达类别并集，具体敌人实例和全过程容量仍需后端验证。
ENCOUNTER_GENERATED = {
    "Small Slimes": ["Slimed"], "Large Slime": ["Slimed"],
    "Exordium Wildlife": ["Slimed"], "Exordium Thugs": ["Slimed"],
    "3 Sentries": ["Dazed"],
}


def validate_index(index, raw_index, corpus_bytes):
    """先核验输入文件与其来源输出关联，再生成新的独立内容哈希。"""
    if index.get("corpus_sha256") != C.sha(corpus_bytes):
        raise ValueError("CORPUS_FILE_HASH_MISMATCH")
    base = json.loads(corpus_bytes)
    if {k: v for k, v in index.items() if k != "corpus_sha256"} != base:
        raise ValueError("INDEX_CORPUS_CONTENT_MISMATCH")
    if index.get("implementation_sha256") != C.sha((ROOT / "scripts/audit-public-corpus.py").read_bytes()):
        raise ValueError("AUDIT_IMPLEMENTATION_HASH_MISMATCH")
    if index.get("archive_sha256") != C.ZIP_SHA:
        raise ValueError("SOURCE_ARCHIVE_HASH_MISMATCH")
    return C.sha(raw_index)


def build_manifest(index, input_sha256):
    groups = {g["group_id"]: g for g in index["groups"]}
    if len(groups) != len(index["groups"]):
        raise ValueError("DUPLICATE_GROUP_ID")
    seen = set()
    scenes = []
    for source in index["scenes"]:
        if source["scene_id"] in seen:
            raise ValueError("DUPLICATE_SCENE_ID")
        seen.add(source["scene_id"])
        group = groups[source["group_id"]]
        if source["research_split"] != group["research_split"]:
            raise ValueError("GROUP_SPLIT_MISMATCH")
        if not source.get("candidate"):
            continue
        row = copy.deepcopy(source)
        candidate = row["candidate"]
        reasons = []
        cards = {C.card_base(c) for c in candidate["deck"]}
        unsupported_cards = cards - C.M1_CARDS - {"AscendersBane"}
        if unsupported_cards:
            reasons.append("UNSUPPORTED_CARD:" + ",".join(sorted(unsupported_cards)))
        if any(C.card_base(c) == "True Grit" and c != "True Grit" for c in candidate["deck"]):
            reasons.append("CARD_SECONDARY_CHOICE:True Grit upgrade")
        unknown_relics = set(candidate["relics"]) - C.RESET_RELICS
        if unknown_relics:
            reasons.append("UNSUPPORTED_RELIC:" + ",".join(sorted(unknown_relics)))
        unknown_potions = {p for p in candidate["potions"] if p is not None} - DIRECT_POTIONS
        if unknown_potions:
            reasons.append("UNSUPPORTED_OR_CHOICE_POTION:" + ",".join(sorted(unknown_potions)))
        if candidate["encounter"] != C.ENCOUNTERS.get(row["encounter_label"]):
            reasons.append("UNKNOWN_OR_MISMATCHED_ENCOUNTER")
        if source.get("source_admission_policy") != C.SOURCE_ADMISSION_POLICY or source.get("derived_data_admission_status") != "admitted_backend_pending":
            reasons.append("DERIVED_DATA_NOT_ADMITTED")
        generated = set(ENCOUNTER_GENERATED.get(row["encounter_label"], []))
        for card in cards:
            generated.update(GENERATED_CARDS.get(card, []))
        row.update({
            "source_group": copy.deepcopy(group),
            "candidate_sha256": C.sha(C.canonical(candidate)),
            "implementation_batch_status": "eligible_content_pending_backend" if not reasons else "whole_scene_deferred",
            "implementation_batch_blockers": reasons,
            "content_admission_status": "accepted" if not reasons else "rejected",
            "content_blockers": list(reasons),
            "entity_closure": {
                "initial_cards": sorted(cards), "generated_cards": sorted(generated),
                "all_card_classes": sorted(cards | generated), "relics": sorted(set(candidate["relics"])),
                "potions": sorted({p for p in candidate["potions"] if p is not None}),
                "encounter_generator": candidate["encounter"],
                "capacity_and_behavior_status": "pending_runtime_validation",
            },
        })
        scenes.append(row)
    accepted = [r for r in scenes if not r["implementation_batch_blockers"]]
    payload = {
        "schema": "public-scene-manifest-v1", "source_admission_policy": C.SOURCE_ADMISSION_POLICY,
        "input_index_sha256": input_sha256, "source_archive_sha256": index["archive_sha256"],
        "builder_sha256": C.sha(Path(__file__).read_bytes()),
        "audit_implementation_sha256": index["implementation_sha256"],
        "split_policy": index["split_policy"], "split_status": "research-only",
        "formal_training_ready": False, "formal_evaluation_ready": False,
        "source_seed_policy": "provenance-and-grouping-only;never-model-input",
        "historical_rules_equivalence": "unverified",
        "content_contract": {"cards": sorted(C.M1_CARDS | {"AscendersBane"}), "relics": sorted(C.RESET_RELICS), "direct_potions": sorted(DIRECT_POTIONS)},
        "summary": {
            "derived_candidates_preserved": len(scenes), "content_eligible_scenes": len(accepted),
            "content_eligible_groups": len({r["group_id"] for r in accepted}),
            "by_research_split": dict(Counter(r["research_split"] for r in accepted)),
            "by_encounter": dict(Counter(r["encounter_label"] for r in accepted)),
            "initial_card_classes": sorted({x for r in accepted for x in r["entity_closure"]["initial_cards"]}),
            "max_initial_deck_size": max((len(r["candidate"]["deck"]) for r in accepted), default=0),
            "formal_ready_count": 0,
        },
        "scenes": scenes,
    }
    payload["manifest_payload_sha256"] = C.sha(C.canonical(payload))
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=ROOT / "docs/m2-corpus-index.json")
    parser.add_argument("--corpus", type=Path, default=ROOT / "reference/public-run-corpus/corpus.json")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/m2-public-scene-manifest.json")
    args = parser.parse_args(argv)
    raw = args.index.read_bytes()
    index = json.loads(raw)
    digest = validate_index(index, raw, args.corpus.read_bytes())
    manifest = build_manifest(index, digest)
    C.write_json(args.output, manifest)
    print(json.dumps(manifest["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
