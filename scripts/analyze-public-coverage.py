"""离线量化公开 Ironclad 战斗初态的覆盖偏差并生成扩容建议。

本脚本只读取已经固定的公开语料索引、场景 manifest、公开战斗契约和
开发集成记录；不读取最终 master_deck，也不使用任何策略胜率来筛选场景。
候选的入口始终是 ``pre_combat_initialization`` / ``before_destination_room_entry``。
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = "public-distribution-analysis-v1"
PRIORITY_SCHEMA = "public-expansion-priorities-v1"
GRAPH_SCHEMA = "public-distribution-dependency-graph-v1"

ELITE_ENCOUNTERS = {"Gremlin Nob", "Lagavulin", "3 Sentries"}
UNKNOWN_ENCOUNTERS = {"The Mushroom Lair"}
ENCOUNTER_ENUM_TO_LABEL = {
    "CULTIST": "Cultist",
    "JAW_WORM": "Jaw Worm",
    "TWO_LOUSE": "2 Louse",
    "SMALL_SLIMES": "Small Slimes",
    "BLUE_SLAVER": "Blue Slaver",
    "RED_SLAVER": "Red Slaver",
    "LOOTER": "Looter",
    "LARGE_SLIME": "Large Slime",
    "THREE_LOUSE": "3 Louse",
    "TWO_FUNGI_BEASTS": "2 Fungi Beasts",
    "EXORDIUM_WILDLIFE": "Exordium Wildlife",
    "EXORDIUM_THUGS": "Exordium Thugs",
    "GREMLIN_GANG": "Gremlin Gang",
    "LOTS_OF_SLIMES": "Lots of Slimes",
    "GREMLIN_NOB": "Gremlin Nob",
    "LAGAVULIN": "Lagavulin",
    "THREE_SENTRIES": "3 Sentries",
}

ENTRY_FIELD_NAMES = (
    "entry_timing",
    "initialization_phase",
    "deck",
    "player.hp",
    "player.max_hp",
    "player.gold",
    "relics",
    "potions",
    "encounter",
)

CATEGORY_DESCRIPTIONS = {
    "source_prefix": "来源版本/房间前缀或事件、商店历史尚未证明",
    "card_upgrade_support": "卡牌或升级不在当前完整内容契约",
    "relic_counter_hook": "遗物动态计数或跨战斗 hook 尚未证明",
    "potion_inventory_or_generation": "药水库存时序、自动使用或生成历史尚未证明",
    "potion_choice_support": "药水不在当前直接药水/动作语法范围",
    "secondary_choice_or_copy_generation": "需要二次选择、复制或相应生成路径",
    "entry_type": "入口房间类型或同层多战斗尚未证明",
    "encounter_generation": "遭遇生成器尚未纳入来源闭包",
    "burning_elite_modifier": "精英燃烧强化未由来源记录恢复",
    "capacity_action_protocol": "容量或动作协议尚未证明",
}


def read_json(path: Path) -> tuple[Any, bytes]:
    """以 UTF-8 读取 JSON，并返回原始字节以便记录 SHA256。"""

    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), raw


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def file_descriptor(path: Path, raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = path.read_bytes()
    return {
        "path": relative_path(path),
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
    }


def source_collection(source_path: str) -> str:
    parts = source_path.split("/")
    if len(parts) >= 2 and parts[0] == "runs":
        return parts[1]
    return parts[0] if parts else "UNKNOWN"


def source_partition(source_path: str) -> str:
    parts = source_path.split("/")
    if len(parts) >= 3 and parts[0] == "runs":
        return "/".join(parts[1:-1])
    return source_collection(source_path)


def card_base(card: str) -> str:
    return re.sub(r"\+[1-9][0-9]*$", "", card)


def has_upgrade(card: str) -> bool:
    return bool(re.search(r"\+[1-9][0-9]*$", card))


def encounter_tier(label: str) -> str:
    if label in ELITE_ENCOUNTERS:
        return "elite"
    if label in UNKNOWN_ENCOUNTERS:
        return "unknown_or_event"
    return "normal"


def sort_value(value: Any) -> tuple[int, str]:
    if isinstance(value, bool):
        return (1, str(value))
    if isinstance(value, (int, float)):
        return (0, f"{value:020.8f}")
    return (1, str(value))


def display_value(value: Any) -> Any:
    return value if value is not None else "UNKNOWN"


def common_group_metadata(
    groups: Sequence[Mapping[str, Any]],
    scenes: Sequence[Mapping[str, Any]],
    ascension_summary: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[Mapping[str, Any]]]]:
    """建立 run 元数据；缺失的逐行进阶由索引的来源汇总明确继承。"""

    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for scene in scenes:
        grouped[str(scene["group_id"])].append(scene)

    summary_values: dict[str, int] = {}
    for key, count in ascension_summary.items():
        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("进阶汇总必须是整数")
        summary_values[str(key)] = int(key)

    metadata: dict[str, dict[str, Any]] = {}
    for group in groups:
        group_id = str(group["group_id"])
        rows = sorted(grouped[group_id], key=lambda row: (int(row["floor"]), str(row["scene_id"])))
        if not rows:
            raise ValueError(f"run group 无战斗记录: {group_id}")

        builds = {str(row.get("source_build")) for row in rows}
        if len(builds) != 1:
            raise ValueError(f"run group 的 build 不一致: {group_id}")

        candidate_ascensions = {
            int(row["candidate"]["ascension"])
            for row in rows
            if isinstance(row.get("candidate"), Mapping)
            and isinstance(row["candidate"].get("ascension"), int)
            and not isinstance(row["candidate"].get("ascension"), bool)
        }
        if len(candidate_ascensions) > 1:
            raise ValueError(f"run group 的候选进阶不一致: {group_id}")
        if candidate_ascensions:
            ascension = next(iter(candidate_ascensions))
            ascension_evidence = "candidate_entry_A"
        elif len(summary_values) == 1 and sum(ascension_summary.values()) == len(groups):
            ascension = next(iter(summary_values.values()))
            ascension_evidence = "corpus_summary_inherited"
        else:
            ascension = None
            ascension_evidence = "missing"

        source_path = str(group["source_path"])
        metadata[group_id] = {
            "group_id": group_id,
            "source_path": source_path,
            "source_collection": source_collection(source_path),
            "source_partition": source_partition(source_path),
            "raw_sha256": str(group["raw_sha256"]),
            "research_split": str(group["research_split"]),
            "source_build": next(iter(builds)),
            "character": "IRONCLAD",
            "character_evidence": "固定公开库按character筛选后的来源群组",
            "ascension": ascension,
            "ascension_evidence": ascension_evidence,
            "aliases": list(group.get("aliases", [])),
            "alias_count": len(group.get("aliases", [])),
        }
    return metadata, grouped


def enriched_scene(scene: Mapping[str, Any], metadata: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    meta = metadata[str(scene["group_id"])]
    result = dict(scene)
    result["source_collection"] = meta["source_collection"]
    result["source_partition"] = meta["source_partition"]
    result["character"] = meta["character"]
    result["ascension"] = meta["ascension"]
    result["encounter_tier"] = encounter_tier(str(scene["encounter_label"]))
    return result


def group_keyed_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["group_id"])].append(row)
    return grouped


def distribution(
    rows: Sequence[Mapping[str, Any]],
    value_getter,
) -> list[dict[str, Any]]:
    """返回逐场和 run 平衡的同一字段分布。

    逐场统计每行权重为 1/N。run 平衡统计在每个 group 内把总权重 1
    均分给该层的行，因此同一 run 的多个楼层不会自动放大其权重。
    """

    if not rows:
        return []
    grouped = group_keyed_rows(rows)
    scene_count = len(rows)
    run_count = len(grouped)
    scene_counts: Counter[str] = Counter()
    run_counts: defaultdict[str, float] = defaultdict(float)
    run_presence: defaultdict[str, set[str]] = defaultdict(set)
    for row in rows:
        value = display_value(value_getter(row))
        value_key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        scene_counts[value_key] += 1
        run_presence[value_key].add(str(row["group_id"]))
    for group_rows in grouped.values():
        row_weight = 1.0 / len(group_rows)
        for row in group_rows:
            value = display_value(value_getter(row))
            value_key = json.dumps(value, ensure_ascii=False, sort_keys=True)
            run_counts[value_key] += row_weight

    values: list[tuple[Any, str]] = []
    for value_key in scene_counts:
        values.append((json.loads(value_key), value_key))
    values.sort(key=lambda item: sort_value(item[0]))
    result = []
    for value, value_key in values:
        result.append(
            {
                "value": value,
                "scene_count": scene_counts[value_key],
                "scene_share": scene_counts[value_key] / scene_count,
                "run_count": len(run_presence[value_key]),
                "run_balanced_weight": run_counts[value_key],
                "run_balanced_share": run_counts[value_key] / run_count,
            }
        )
    return result


def numeric_summary(values: Iterable[Any]) -> dict[str, Any]:
    numbers = [float(value) for value in values]
    if not numbers:
        return {"count": 0, "min": None, "max": None, "mean": None, "unique_count": 0}
    return {
        "count": len(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "mean": sum(numbers) / len(numbers),
        "unique_count": len(set(numbers)),
    }


def feature_distribution(
    rows: Sequence[Mapping[str, Any]],
    value_getter,
) -> list[dict[str, Any]]:
    return distribution(rows, value_getter)


def presence_distribution(
    rows: Sequence[Mapping[str, Any]],
    item_getter,
) -> list[dict[str, Any]]:
    """统计实体出现频次；run_count 是 group 去重后的出现次数。"""

    if not rows:
        return []
    grouped = group_keyed_rows(rows)
    scene_count = len(rows)
    run_count = len(grouped)
    scene_counts: Counter[str] = Counter()
    run_presence: defaultdict[str, set[str]] = defaultdict(set)
    slot_counts: Counter[str] = Counter()
    for row in rows:
        items = list(item_getter(row))
        for item in set(items):
            key = str(item)
            scene_counts[key] += 1
            run_presence[key].add(str(row["group_id"]))
        for item in items:
            slot_counts[str(item)] += 1
    result = []
    for item in sorted(scene_counts):
        result.append(
            {
                "item": item,
                "scene_count": scene_counts[item],
                "scene_share": scene_counts[item] / scene_count,
                "run_count": len(run_presence[item]),
                "run_share": len(run_presence[item]) / run_count,
                "slot_or_instance_count": slot_counts[item],
            }
        )
    result.sort(key=lambda item: (-item["scene_count"], item["item"]))
    return result


def entry_candidate(row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    candidate = row.get("candidate")
    return candidate if isinstance(candidate, Mapping) else None


def entry_field_present(candidate: Mapping[str, Any] | None, field: str) -> bool:
    if candidate is None:
        return False
    if field.startswith("player."):
        player = candidate.get("player")
        return isinstance(player, Mapping) and field.split(".", 1)[1] in player
    return field in candidate


def entry_field_availability(
    denominator_rows: Sequence[Mapping[str, Any]],
    feature_rows: Sequence[Mapping[str, Any]],
    unit_count: int,
    feature_group_count: int,
    missing_reason_rows: Sequence[Mapping[str, Any]],
    missing_reason_getter,
) -> dict[str, Any]:
    feature_group_ids = {str(row["group_id"]) for row in feature_rows}
    all_grouped = group_keyed_rows(denominator_rows)
    fields: dict[str, dict[str, Any]] = {}
    for field in ENTRY_FIELD_NAMES:
        available = sum(
            entry_field_present(entry_candidate(row), field)
            for row in denominator_rows
        )
        available_groups = {
            str(row["group_id"])
            for row in denominator_rows
            if entry_field_present(entry_candidate(row), field)
        }
        fields[field] = {
            "available_row_count": available,
            "unavailable_row_count": len(denominator_rows) - available,
            "available_row_share": available / len(denominator_rows) if denominator_rows else 0.0,
            "available_run_count": len(available_groups),
            "available_run_share": len(available_groups) / unit_count if unit_count else 0.0,
        }

    all_rows_available_groups = 0
    for group_rows in all_grouped.values():
        if group_rows and all(entry_candidate(row) is not None for row in group_rows):
            all_rows_available_groups += 1

    reason_counts: Counter[str] = Counter()
    for row in missing_reason_rows:
        reasons = list(missing_reason_getter(row))
        key = " + ".join(sorted(set(reasons))) if reasons else "ENTRY_A_FIELDS_UNPROVEN"
        reason_counts[key] += 1
    return {
        "denominator_row_count": len(denominator_rows),
        "feature_row_count": len(feature_rows),
        "missing_row_count": len(denominator_rows) - len(feature_rows),
        "feature_row_share": len(feature_rows) / len(denominator_rows) if denominator_rows else 0.0,
        "feature_run_count": len(feature_group_ids),
        "feature_run_share": len(feature_group_ids) / unit_count if unit_count else 0.0,
        "all_rows_available_run_count": all_rows_available_groups,
        "all_rows_available_run_share": all_rows_available_groups / unit_count if unit_count else 0.0,
        "fields": fields,
        "missing_reason_counts": [
            {"reason": reason, "row_count": reason_counts[reason]}
            for reason in sorted(reason_counts)
        ],
        "final_master_deck_used": False,
    }


def entry_stats(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """只在候选入口 A 行上计算卡组、遗物和药水统计。"""

    if not rows:
        return {
            "denominator": 0,
            "deck": {},
            "player": {},
            "relics": {},
            "potions": {},
        }

    candidates = [entry_candidate(row) for row in rows]
    if any(candidate is None for candidate in candidates):
        raise ValueError("entry_stats 不能接收缺失入口候选的行")
    typed = [candidate for candidate in candidates if candidate is not None]

    deck_sizes = feature_distribution(
        rows,
        lambda row: len(entry_candidate(row)["deck"]),
    )
    deck_signatures = feature_distribution(
        rows,
        lambda row: sorted(str(card) for card in entry_candidate(row)["deck"]),
    )
    upgraded_cards = [
        str(card)
        for candidate in typed
        for card in candidate["deck"]
        if has_upgrade(str(card))
    ]
    upgraded_scene_count = sum(
        any(has_upgrade(str(card)) for card in candidate["deck"])
        for candidate in typed
    )
    initial_card_presence = presence_distribution(
        rows,
        lambda row: [
            card_base(str(card)) for card in entry_candidate(row)["deck"]
        ],
    )
    initial_card_instances = Counter(
        card_base(str(card)) for candidate in typed for card in candidate["deck"]
    )

    relic_presence = presence_distribution(
        rows,
        lambda row: [str(relic) for relic in entry_candidate(row)["relics"]],
    )
    potion_rows = [
        [str(potion) for potion in candidate["potions"] if potion is not None]
        for candidate in typed
    ]
    potion_nonempty = sum(bool(items) for items in potion_rows)
    # candidate 字典不含 group_id；下面用原始行重建 run 平衡的非空比例。
    grouped_nonempty: defaultdict[str, list[bool]] = defaultdict(list)
    for source_row, items in zip(rows, potion_rows):
        grouped_nonempty[str(source_row["group_id"])].append(bool(items))
    run_balanced_nonempty_ratio = (
        sum(sum(values) / len(values) for values in grouped_nonempty.values())
        / len(grouped_nonempty)
        if grouped_nonempty
        else 0.0
    )

    entity_closure_rows = [
        row.get("entity_closure")
        for row in rows
        if isinstance(row.get("entity_closure"), Mapping)
    ]
    generated_card_values = sorted(
        {
            str(card)
            for closure in entity_closure_rows
            for card in closure.get("generated_cards", [])
        }
    )
    all_card_values = sorted(
        {
            str(card)
            for closure in entity_closure_rows
            for card in closure.get("all_card_classes", [])
        }
    )

    player = {
        field: numeric_summary(candidate["player"][field] for candidate in typed)
        for field in ("hp", "max_hp", "gold")
    }
    return {
        "denominator": len(rows),
        "run_count": len({str(row["group_id"]) for row in rows}),
        "deck": {
            "size_distribution": deck_sizes,
            "multiset_distribution": deck_signatures,
            "unique_multiset_count": len({tuple(sorted(str(card) for card in candidate["deck"])) for candidate in typed}),
            "unique_initial_card_class_count": len(
                {card_base(str(card)) for candidate in typed for card in candidate["deck"]}
            ),
            "initial_card_classes": sorted(
                {card_base(str(card)) for candidate in typed for card in candidate["deck"]}
            ),
            "initial_card_presence": initial_card_presence,
            "initial_card_instance_counts": [
                {"item": item, "instance_count": initial_card_instances[item]}
                for item in sorted(initial_card_instances)
            ],
            "upgraded_scene_count": upgraded_scene_count,
            "upgraded_scene_share": upgraded_scene_count / len(typed),
            "upgraded_instance_count": len(upgraded_cards),
            "upgraded_card_versions": [
                {"item": item, "instance_count": count}
                for item, count in sorted(Counter(upgraded_cards).items())
            ],
        },
        "player": player,
        "relics": {
            "unique_class_count": len({str(relic) for candidate in typed for relic in candidate["relics"]}),
            "presence": relic_presence,
            "set_count": len({tuple(sorted(str(relic) for relic in candidate["relics"])) for candidate in typed}),
        },
        "potions": {
            "nonempty_scene_count": potion_nonempty,
            "nonempty_scene_share": potion_nonempty / len(typed),
            "run_balanced_nonempty_share": run_balanced_nonempty_ratio,
            "unique_class_count": len({potion for items in potion_rows for potion in items}),
            "presence": presence_distribution(rows, lambda row: [
                str(potion)
                for potion in entry_candidate(row)["potions"]
                if potion is not None
            ]),
            "inventory_multiset_count": len({tuple(sorted(items)) for items in potion_rows}),
            "slot_instance_count": sum(len(items) for items in potion_rows),
        },
        "generated_cards": {
            "status": "available_from_manifest_entity_closure"
            if entity_closure_rows
            else "not_recorded_on_this_layer",
            "available_row_count": len(entity_closure_rows),
            "classes": generated_card_values,
            "all_card_classes": all_card_values,
        },
    }


def build_run_rows(
    groups: Sequence[Mapping[str, Any]],
    metadata: Mapping[str, Mapping[str, Any]],
    grouped_scenes: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    rows = []
    for group in groups:
        group_id = str(group["group_id"])
        scenes = sorted(
            grouped_scenes[group_id],
            key=lambda row: (int(row["floor"]), str(row["scene_id"])),
        )
        row = dict(metadata[group_id])
        row["group_id"] = group_id
        row["first_act1_combat_scene_id"] = str(scenes[0]["scene_id"])
        row["act1_combat_row_count"] = len(scenes)
        row["act1_floors"] = sorted({int(scene["floor"]) for scene in scenes})
        row["act1_encounters"] = sorted({str(scene["encounter_label"]) for scene in scenes})
        row["act1_tiers"] = sorted({encounter_tier(str(scene["encounter_label"])) for scene in scenes})
        rows.append(row)
    return rows


def run_presence_distribution(
    rows: Sequence[Mapping[str, Any]],
    values_getter,
) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows:
        for value in set(values_getter(row)):
            counts[str(value)] += 1
    total = len(rows)
    return [
        {
            "value": value,
            "run_count": counts[value],
            "run_share": counts[value] / total if total else 0.0,
        }
        for value in sorted(counts, key=sort_value)
    ]


def layer_entry_view(
    layer_rows: Sequence[Mapping[str, Any]],
    feature_rows: Sequence[Mapping[str, Any]],
    unit_count: int,
    missing_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "entry_timing_scope": "pre_combat_initialization / before_destination_room_entry",
        "field_semantics": "candidate 对象是规则派生入口 A；没有 candidate 就不把最终 deck 或 post-init 快照倒填为入口",
        "stats": entry_stats(feature_rows),
        "field_availability": entry_field_availability(
            layer_rows,
            feature_rows,
            unit_count,
            len({str(row["group_id"]) for row in feature_rows}),
            missing_rows,
            lambda row: row.get("blockers", []),
        ),
    }


def scene_layer(
    layer_id: str,
    description: str,
    rows: Sequence[Mapping[str, Any]],
    metadata: Mapping[str, Mapping[str, Any]],
    feature_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    enriched = [enriched_scene(row, metadata) for row in rows]
    enriched_features = [enriched_scene(row, metadata) for row in feature_rows]
    group_count = len({str(row["group_id"]) for row in rows})
    return {
        "layer_id": layer_id,
        "description": description,
        "unit": "combat_scene",
        "scene_count": len(rows),
        "independent_run_count": group_count,
        "weights": {
            "scene_weight": 1.0 / len(rows) if rows else 0.0,
            "run_balanced_rule": "每个关联 group 的本层场景总权重为1，再除以独立 run 数",
            "run_balanced_group_weight": 1.0 / group_count if group_count else 0.0,
        },
        "distributions": {
            "source_collection": distribution(enriched, lambda row: row["source_collection"]),
            "source_partition": distribution(enriched, lambda row: row["source_partition"]),
            "source_build": distribution(enriched, lambda row: row["source_build"]),
            "research_split": distribution(enriched, lambda row: row["research_split"]),
            "character": distribution(enriched, lambda row: row["character"]),
            "ascension": distribution(enriched, lambda row: row["ascension"]),
            "floor": distribution(enriched, lambda row: int(row["floor"])),
            "encounter_tier": distribution(enriched, lambda row: row["encounter_tier"]),
            "encounter_label": distribution(enriched, lambda row: row["encounter_label"]),
        },
        "entry": layer_entry_view(
            enriched,
            enriched_features,
            group_count,
            [row for row in enriched if entry_candidate(row) is None],
        ),
        "observed_fields": {
            "source_path_and_sha256": len(rows),
            "source_build": len(rows),
            "research_split": len(rows),
            "floor_and_encounter": len(rows),
            "entry_A_candidate": len(feature_rows),
            "player_identity": 0,
        },
    }


def run_layer(
    groups: Sequence[Mapping[str, Any]],
    run_rows: Sequence[Mapping[str, Any]],
    all_scenes: Sequence[Mapping[str, Any]],
    metadata: Mapping[str, Mapping[str, Any]],
    first_feature_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    linked = [enriched_scene(row, metadata) for row in all_scenes]
    group_count = len(run_rows)
    return {
        "layer_id": "all_independent_runs",
        "description": "固定公开库全部独立 Ironclad run；楼层/遭遇以该 run 关联的第一幕战斗存在性描述",
        "unit": "independent_run",
        "unit_count": group_count,
        "linked_act1_combat_row_count": len(all_scenes),
        "weights": {
            "run_weight": 1.0 / group_count if group_count else 0.0,
            "linked_scene_weight": 1.0 / len(all_scenes) if all_scenes else 0.0,
            "run_balanced_rule": "本层每个独立 run 权重为1/group_count；关联战斗行另按其所在 scene 层报告",
        },
        "distributions": {
            "source_collection": distribution(run_rows, lambda row: row["source_collection"]),
            "source_partition": distribution(run_rows, lambda row: row["source_partition"]),
            "source_build": distribution(run_rows, lambda row: row["source_build"]),
            "research_split": distribution(run_rows, lambda row: row["research_split"]),
            "character": distribution(run_rows, lambda row: row["character"]),
            "ascension": distribution(run_rows, lambda row: row["ascension"]),
        },
        "linked_combat_distributions": {
            "floor_presence_by_run": run_presence_distribution(run_rows, lambda row: row["act1_floors"]),
            "encounter_presence_by_run": run_presence_distribution(run_rows, lambda row: row["act1_encounters"]),
            "tier_presence_by_run": run_presence_distribution(run_rows, lambda row: row["act1_tiers"]),
            "floor_scene_distribution": distribution(linked, lambda row: int(row["floor"])),
            "encounter_scene_distribution": distribution(linked, lambda row: row["encounter_label"]),
            "tier_scene_distribution": distribution(linked, lambda row: row["encounter_tier"]),
        },
        "entry": layer_entry_view(
            [enriched_scene(row, metadata) for row in all_scenes if int(row["floor"]) == 1],
            [enriched_scene(row, metadata) for row in first_feature_rows],
            group_count,
            [
                enriched_scene(row, metadata)
                for row in all_scenes
                if int(row["floor"]) == 1 and entry_candidate(row) is None
            ],
        ),
        "observed_fields": {
            "source_path_and_sha256": group_count,
            "source_build": group_count,
            "research_split": group_count,
            "first_act1_floor_and_encounter_presence": group_count,
            "entry_A_candidate_at_first_act1_combat": len(first_feature_rows),
            "player_identity": 0,
        },
        "alias_summary": {
            "raw_file_count": sum(int(row["alias_count"]) for row in run_rows),
            "independent_run_count": group_count,
            "duplicate_alias_file_count": sum(max(0, int(row["alias_count"]) - 1) for row in run_rows),
            "groups_with_aliases": sum(int(row["alias_count"]) > 1 for row in run_rows),
            "cross_collection_alias_groups": 0,
            "player_identity_field": "not_recorded;路径标签不等于玩家身份",
        },
    }


def content_atoms(scene: Mapping[str, Any]) -> frozenset[str]:
    atoms: set[str] = set()
    for blocker in scene.get("content_blockers", []):
        blocker = str(blocker)
        if blocker.startswith("UNSUPPORTED_CARD:"):
            names = blocker.split(":", 1)[1].split(",")
            atoms.update(f"card:{name}" for name in names if name)
        elif blocker.startswith("UNSUPPORTED_OR_CHOICE_POTION:"):
            atoms.add("potion:" + blocker.split(":", 1)[1])
        elif blocker.startswith("CARD_SECONDARY_CHOICE:"):
            atoms.add("secondary:" + blocker.split(":", 1)[1])
        elif blocker.startswith("UNSUPPORTED_RELIC:"):
            atoms.add("relic:" + blocker.split(":", 1)[1])
        else:
            atoms.add("content:" + blocker)
    return frozenset(sorted(atoms))


def raw_categories(blockers: Sequence[str]) -> set[str]:
    categories: set[str] = set()
    for blocker in blockers:
        blocker = str(blocker)
        if blocker.startswith("PREFIX_UNPROVEN:"):
            categories.add("source_prefix")
            if "POTION_AUTO_USE_OR_GENERATION" in blocker:
                categories.add("potion_inventory_or_generation")
            if "RELIC_HISTORY" in blocker:
                categories.add("relic_counter_hook")
        elif blocker.startswith("RELIC_COUNTER_OR_HOOK_PENDING:"):
            categories.add("relic_counter_hook")
        elif blocker == "BURNING_ELITE_MODIFIER_UNRECORDED":
            categories.add("burning_elite_modifier")
        elif blocker.startswith("ENCOUNTER_GENERATOR_PENDING:"):
            categories.add("encounter_generation")
        elif blocker == "ENTRY_ROOM_OR_MULTIPLE_COMBATS_PENDING":
            categories.add("entry_type")
        else:
            categories.add("source_prefix")
    return categories


def content_categories(blockers: Sequence[str]) -> set[str]:
    categories: set[str] = set()
    for blocker in blockers:
        blocker = str(blocker)
        if blocker.startswith("UNSUPPORTED_CARD:"):
            categories.add("card_upgrade_support")
        elif blocker.startswith("UNSUPPORTED_OR_CHOICE_POTION:"):
            categories.add("potion_choice_support")
        elif blocker.startswith("CARD_SECONDARY_CHOICE:"):
            categories.add("secondary_choice_or_copy_generation")
        elif blocker.startswith("UNSUPPORTED_RELIC:"):
            categories.add("relic_counter_hook")
        elif blocker == "UNKNOWN_OR_MISMATCHED_ENCOUNTER":
            categories.add("encounter_generation")
        else:
            categories.add("capacity_action_protocol")
    return categories


def blocker_category_frequency(graph_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    values: defaultdict[str, set[str]] = defaultdict(set)
    groups: defaultdict[str, set[str]] = defaultdict(set)
    for row in graph_rows:
        for category in row["dependency_categories"]:
            values[category].add(str(row["scene_id"]))
            groups[category].add(str(row["group_id"]))
    return [
        {
            "category": category,
            "description": CATEGORY_DESCRIPTIONS.get(category, "未注册类别"),
            "scene_count": len(values[category]),
            "independent_run_count": len(groups[category]),
            "non_additive": True,
        }
        for category in sorted(values, key=lambda item: (-len(values[item]), item))
    ]


def scene_ids_from_rows(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted(str(row["scene_id"]) for row in rows)


def content_footprint(rows: Sequence[Mapping[str, Any]]) -> dict[str, set[str]]:
    footprint = {
        "initial_card_classes": set(),
        "generated_card_classes": set(),
        "relics": set(),
        "potions": set(),
        "upgraded_card_versions": set(),
    }
    for row in rows:
        candidate = entry_candidate(row)
        if candidate is None:
            continue
        footprint["initial_card_classes"].update(
            card_base(str(card)) for card in candidate["deck"]
        )
        footprint["upgraded_card_versions"].update(
            str(card) for card in candidate["deck"] if has_upgrade(str(card))
        )
        footprint["relics"].update(str(relic) for relic in candidate["relics"])
        footprint["potions"].update(
            str(potion) for potion in candidate["potions"] if potion is not None
        )
        closure = row.get("entity_closure")
        if isinstance(closure, Mapping):
            footprint["generated_card_classes"].update(
                str(card) for card in closure.get("generated_cards", [])
            )
    return footprint


def yield_metrics(
    rows: Sequence[Mapping[str, Any]],
    support_atoms: Iterable[str],
    current_rows: Sequence[Mapping[str, Any]],
    candidate_pool_count: int,
    candidate_group_count: int,
) -> dict[str, Any]:
    support = frozenset(support_atoms)
    unlocked = [row for row in rows if content_atoms(row) <= support]
    current_groups = {str(row["group_id"]) for row in current_rows}
    current_floors = {int(row["floor"]) for row in current_rows}
    current_encounters = {str(row["encounter_label"]) for row in current_rows}
    current_footprint = content_footprint(current_rows)
    unlocked_footprint = content_footprint(unlocked)
    new_content = {
        key: sorted(unlocked_footprint[key] - current_footprint[key])
        for key in current_footprint
    }
    return {
        "support_atoms": sorted(support),
        "scene_count": len(unlocked),
        "candidate_scene_share": len(unlocked) / candidate_pool_count if candidate_pool_count else 0.0,
        "independent_run_count": len({str(row["group_id"]) for row in unlocked}),
        "new_independent_runs_vs_current_99": len(
            {str(row["group_id"]) for row in unlocked} - current_groups
        ),
        "floor_values": sorted({int(row["floor"]) for row in unlocked}),
        "new_floor_values_vs_current_99": sorted(
            {int(row["floor"]) for row in unlocked} - current_floors
        ),
        "encounter_labels": sorted({str(row["encounter_label"]) for row in unlocked}),
        "new_encounter_labels_vs_current_99": sorted(
            {str(row["encounter_label"]) for row in unlocked} - current_encounters
        ),
        "new_content_vs_current_99": new_content,
        "scene_ids": scene_ids_from_rows(unlocked),
        "run_ids": sorted({str(row["group_id"]) for row in unlocked}),
        "candidate_group_share": (
            len({str(row["group_id"]) for row in unlocked}) / candidate_group_count
            if candidate_group_count
            else 0.0
        ),
        "overlap_safe": True,
        "selection_by_policy_outcome": False,
    }


def blocker_dependency_graph(
    index_scenes: Sequence[Mapping[str, Any]],
    manifest_by_id: Mapping[str, Mapping[str, Any]],
    current_ids: set[str],
) -> dict[str, Any]:
    graph_rows = []
    for source in index_scenes:
        scene_id = str(source["scene_id"])
        manifest = manifest_by_id.get(scene_id)
        source_blockers = sorted({str(item) for item in source.get("blockers", [])})
        content_blockers = sorted(
            {str(item) for item in (manifest or {}).get("content_blockers", [])}
        )
        atoms = sorted(
            {"raw:" + blocker for blocker in source_blockers}
            | set(content_atoms(manifest or {}))
        )
        categories = sorted(raw_categories(source_blockers) | content_categories(content_blockers))
        candidate_exists = isinstance(source.get("candidate"), Mapping)
        if scene_id in current_ids:
            status = "current_executable"
        elif candidate_exists and content_blockers:
            status = "evidence_complete_content_blocked"
        elif candidate_exists:
            status = "evidence_complete_not_current"
        else:
            status = "source_or_prefix_incomplete"
        graph_rows.append(
            {
                "scene_id": scene_id,
                "group_id": str(source["group_id"]),
                "floor": int(source["floor"]),
                "encounter_label": str(source["encounter_label"]),
                "encounter_tier": encounter_tier(str(source["encounter_label"])),
                "research_split": str(source["research_split"]),
                "source_blockers": source_blockers,
                "content_blockers": content_blockers,
                "dependency_atoms": atoms,
                "dependency_categories": categories,
                "candidate_exists": candidate_exists,
                "evidence_complete_under_public_derived_policy": candidate_exists
                and not source_blockers,
                "current_executable": scene_id in current_ids,
                "status": status,
                "potential_only": not candidate_exists,
            }
        )

    raw_blockers = Counter(
        blocker
        for row in graph_rows
        for blocker in row["source_blockers"]
    )
    content_blockers = Counter(
        blocker
        for row in graph_rows
        for blocker in row["content_blockers"]
    )
    category_combos = Counter(
        tuple(row["dependency_categories"])
        for row in graph_rows
        if row["dependency_categories"]
    )
    exact_combos = Counter(
        tuple(row["source_blockers"] + row["content_blockers"])
        for row in graph_rows
        if row["source_blockers"] or row["content_blockers"]
    )
    observed_categories = blocker_category_frequency(graph_rows)
    observed_category_map = {
        item["category"]: item for item in observed_categories
    }
    category_inventory = []
    for category in sorted(CATEGORY_DESCRIPTIONS):
        item = observed_category_map.get(category)
        category_inventory.append(
            {
                "category": category,
                "description": CATEGORY_DESCRIPTIONS[category],
                "scene_count": item["scene_count"] if item else 0,
                "independent_run_count": item["independent_run_count"] if item else 0,
                "observed_as_data_blocker": item is not None,
                "zero_count_means": (
                    "当前索引没有把该类记录为已知 blocker；仍须在实现验收中证明，不能视为已支持。"
                    if item is None
                    else ""
                ),
            }
        )
    return {
        "schema": GRAPH_SCHEMA,
        "category_descriptions": CATEGORY_DESCRIPTIONS,
        "scene_count": len(graph_rows),
        "rows": graph_rows,
        "summary": {
            "current_executable_scene_count": sum(row["current_executable"] for row in graph_rows),
            "source_or_prefix_incomplete_scene_count": sum(
                row["status"] == "source_or_prefix_incomplete" for row in graph_rows
            ),
            "evidence_complete_content_blocked_scene_count": sum(
                row["status"] == "evidence_complete_content_blocked" for row in graph_rows
            ),
            "evidence_complete_not_current_scene_count": sum(
                row["status"] == "evidence_complete_not_current" for row in graph_rows
            ),
            "raw_blocker_frequency": [
                {"blocker": blocker, "scene_count": count}
                for blocker, count in sorted(raw_blockers.items(), key=lambda item: (-item[1], item[0]))
            ],
            "content_blocker_frequency": [
                {"blocker": blocker, "scene_count": count}
                for blocker, count in sorted(content_blockers.items(), key=lambda item: (-item[1], item[0]))
            ],
            "dependency_category_frequency": observed_categories,
            "dependency_category_inventory": category_inventory,
            "dependency_category_combinations": [
                {"categories": list(combo), "scene_count": count, "non_additive": True}
                for combo, count in sorted(category_combos.items(), key=lambda item: (-item[1], item[0]))
            ],
            "exact_blocker_combinations": [
                {"blockers": list(combo), "scene_count": count}
                for combo, count in sorted(exact_combos.items(), key=lambda item: (-item[1], item[0]))
            ],
            "overlap_warning": "类别与 blocker 频次均非可加分母；收益按整组依赖闭包筛选，不把重叠场景分别计作可解锁收益。",
        },
    }


def candidate_yields(
    manifest_scenes: Sequence[Mapping[str, Any]],
    current_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rejected = [
        row for row in manifest_scenes if str(row.get("content_admission_status")) != "accepted"
    ]
    current_group_count = len({str(row["group_id"]) for row in current_rows})
    atoms = sorted({atom for row in rejected for atom in content_atoms(row)})
    single_items = []
    for atom in atoms:
        metrics = yield_metrics(
            rejected,
            {atom},
            current_rows,
            len(manifest_scenes),
            len({str(row["group_id"]) for row in manifest_scenes}),
        )
        exact_rows = [row for row in rejected if content_atoms(row) == frozenset({atom})]
        potential_rows = [row for row in rejected if atom in content_atoms(row)]
        metrics["exact_single_dependency_scene_count"] = len(exact_rows)
        metrics["exact_single_dependency_scene_ids"] = scene_ids_from_rows(exact_rows)
        metrics["potential_scene_count_containing_atom"] = len(potential_rows)
        metrics["potential_independent_run_count_containing_atom"] = len(
            {str(row["group_id"]) for row in potential_rows}
        )
        metrics["potential_scene_ids_containing_atom"] = scene_ids_from_rows(potential_rows)
        single_items.append(metrics)
    single_items.sort(
        key=lambda item: (-item["exact_single_dependency_scene_count"], item["support_atoms"])
    )

    combination_rows: defaultdict[frozenset[str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rejected:
        combination_rows[content_atoms(row)].append(row)
    combinations = []
    for atom_set, rows in combination_rows.items():
        if len(atom_set) < 2:
            continue
        metrics = yield_metrics(
            rejected,
            atom_set,
            current_rows,
            len(manifest_scenes),
            len({str(row["group_id"]) for row in manifest_scenes}),
        )
        # 此处的 rows 才是该组合自己的最小依赖闭包；不能用 support 的并集结果冒充组合收益。
        metrics["support_closure_scene_count"] = metrics["scene_count"]
        metrics["support_closure_independent_run_count"] = metrics["independent_run_count"]
        metrics["minimal_dependency_scene_count"] = len(rows)
        metrics["minimal_dependency_scene_ids"] = scene_ids_from_rows(rows)
        metrics["dependency_size"] = len(atom_set)
        metrics["minimal_independent_run_count"] = len({str(row["group_id"]) for row in rows})
        current_group_ids = {str(row["group_id"]) for row in current_rows}
        current_floors = {int(row["floor"]) for row in current_rows}
        current_encounters = {str(row["encounter_label"]) for row in current_rows}
        current_footprint = content_footprint(current_rows)
        minimal_footprint = content_footprint(rows)
        metrics["minimal_new_independent_runs_vs_current_99"] = len(
            {str(row["group_id"]) for row in rows} - current_group_ids
        )
        metrics["minimal_floor_values"] = sorted({int(row["floor"]) for row in rows})
        metrics["minimal_new_floor_values_vs_current_99"] = sorted(
            {int(row["floor"]) for row in rows} - current_floors
        )
        metrics["minimal_encounter_labels"] = sorted({str(row["encounter_label"]) for row in rows})
        metrics["minimal_new_encounter_labels_vs_current_99"] = sorted(
            {str(row["encounter_label"]) for row in rows} - current_encounters
        )
        metrics["minimal_new_content_vs_current_99"] = {
            key: sorted(minimal_footprint[key] - current_footprint[key])
            for key in current_footprint
        }
        metrics["scene_count"] = len(rows)
        metrics["independent_run_count"] = metrics["minimal_independent_run_count"]
        metrics["new_independent_runs_vs_current_99"] = metrics[
            "minimal_new_independent_runs_vs_current_99"
        ]
        metrics["floor_values"] = metrics["minimal_floor_values"]
        metrics["new_floor_values_vs_current_99"] = metrics[
            "minimal_new_floor_values_vs_current_99"
        ]
        metrics["encounter_labels"] = metrics["minimal_encounter_labels"]
        metrics["new_encounter_labels_vs_current_99"] = metrics[
            "minimal_new_encounter_labels_vs_current_99"
        ]
        metrics["new_content_vs_current_99"] = metrics["minimal_new_content_vs_current_99"]
        combinations.append(metrics)
    combinations.sort(key=lambda item: (-item["minimal_dependency_scene_count"], item["support_atoms"]))

    return {
        "candidate_pool_scene_count": len(manifest_scenes),
        "candidate_pool_run_count": len({str(row["group_id"]) for row in manifest_scenes}),
        "current_executable_scene_count": len(current_rows),
        "current_executable_run_count": current_group_count,
        "content_blocked_scene_count": len(rejected),
        "content_blocked_run_count": len({str(row["group_id"]) for row in rejected}),
        "atomic_dependency_count": len(atoms),
        "single_implementation_items": single_items,
        "minimal_joint_dependencies": combinations,
        "content_overlap_scene_count": sum(
            len(content_atoms(row)) >= 2 for row in rejected
        ),
        "content_card_and_potion_overlap_scene_count": sum(
            any(atom.startswith("card:") for atom in content_atoms(row))
            and any(atom.startswith("potion:") for atom in content_atoms(row))
            for row in rejected
        ),
        "content_yield_rule": "只有 content_atoms(scene) 是 implementation support 的子集时才计入完整场景收益；source/prefix 缺口不在此层计入。",
    }


def source_potential_yields(graph: Mapping[str, Any]) -> dict[str, Any]:
    rows = [row for row in graph["rows"] if row["potential_only"]]
    category_scene_ids: defaultdict[str, set[str]] = defaultdict(set)
    category_group_ids: defaultdict[str, set[str]] = defaultdict(set)
    category_floors: defaultdict[str, set[int]] = defaultdict(set)
    category_encounters: defaultdict[str, set[str]] = defaultdict(set)
    raw_scene_ids: defaultdict[str, set[str]] = defaultdict(set)
    raw_group_ids: defaultdict[str, set[str]] = defaultdict(set)
    for row in rows:
        for category in row["dependency_categories"]:
            category_scene_ids[category].add(str(row["scene_id"]))
            category_group_ids[category].add(str(row["group_id"]))
            category_floors[category].add(int(row["floor"]))
            category_encounters[category].add(str(row["encounter_label"]))
        for blocker in row["source_blockers"]:
            raw_scene_ids[blocker].add(str(row["scene_id"]))
            raw_group_ids[blocker].add(str(row["group_id"]))
    categories = []
    for category in sorted(category_scene_ids, key=lambda item: (-len(category_scene_ids[item]), item)):
        categories.append(
            {
                "category": category,
                "description": CATEGORY_DESCRIPTIONS.get(category, "未注册类别"),
                "potential_scene_count": len(category_scene_ids[category]),
                "potential_independent_run_count": len(category_group_ids[category]),
                "potential_floor_values": sorted(category_floors[category]),
                "potential_encounter_count": len(category_encounters[category]),
                "potential_only": True,
                "confirmed_scene_gain": 0,
                "overlap_safe": False,
            }
        )
    raw = []
    for blocker in sorted(raw_scene_ids, key=lambda item: (-len(raw_scene_ids[item]), item)):
        raw.append(
            {
                "blocker": blocker,
                "potential_scene_count": len(raw_scene_ids[blocker]),
                "potential_independent_run_count": len(raw_group_ids[blocker]),
                "potential_only": True,
                "confirmed_scene_gain": 0,
            }
        )
    return {
        "source_incomplete_scene_count": len(rows),
        "source_incomplete_run_count": len({str(row["group_id"]) for row in rows}),
        "category_potential": categories,
        "raw_blocker_potential": raw,
        "warning": "来源缺口场景至少还可能有其他 blocker；这些数字是潜在覆盖，不是实现后确定收益，也不可相加。",
    }


def integration_check(
    integration: Mapping[str, Any] | None,
    current_ids: set[str],
    manifest_sha256: str | None = None,
    contract_sha256: str | None = None,
) -> dict[str, Any]:
    if integration is None:
        return {
            "status": "not_available",
            "used_for_scene_selection": False,
            "note": "未提供 reference/public-scene-integration.json；当前准入数仍由 manifest content_admission_status=accepted 定义。",
        }
    summary = integration.get("summary", {})
    policy_results = {}
    for policy in ("random", "rule"):
        item = summary.get(policy, {})
        policy_results[policy] = {
            "requested": item.get("requested"),
            "completed": item.get("completed"),
            "errors": item.get("errors"),
            "terminated": item.get("terminated"),
            "truncated": item.get("truncated"),
        }
    records = integration.get("records", [])
    record_scene_ids = {
        str(record.get("scene_id"))
        for record in records
        if isinstance(record, Mapping) and record.get("status") == "completed"
    }
    recorded_manifest_sha256 = str(
        (integration.get("manifest") or {}).get("sha256", "")
    ).lower()
    recorded_contract_sha256 = str(integration.get("contract_hash", "")).lower()
    manifest_matches = (
        manifest_sha256 is None or recorded_manifest_sha256 == manifest_sha256.lower()
    )
    contract_matches = (
        contract_sha256 is None or recorded_contract_sha256 == contract_sha256.lower()
    )
    return {
        "status": "development_integration_only"
        if manifest_matches and contract_matches
        else "metadata_mismatch_not_backend_proof",
        "used_for_scene_selection": False,
        "current_scene_ids_all_completed": manifest_matches
        and contract_matches
        and current_ids <= record_scene_ids,
        "completed_scene_count_in_records": len(record_scene_ids & current_ids),
        "manifest_sha256_matches": manifest_matches,
        "contract_sha256_matches": contract_matches,
        "policy_results": policy_results,
        "purpose": integration.get("purpose"),
        "note": "仅用来核对当前99场是否做过开发集成检查；不读取胜率或回报来排序场景。",
    }


def validate_inputs(
    index: Mapping[str, Any],
    manifest: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> None:
    groups = index.get("groups", [])
    index_scenes = index.get("scenes", [])
    manifest_scenes = manifest.get("scenes", [])
    if len({str(group["group_id"]) for group in groups}) != len(groups):
        raise ValueError("index 存在重复 group_id")
    if len({str(scene["scene_id"]) for scene in index_scenes}) != len(index_scenes):
        raise ValueError("index 存在重复 scene_id")
    raw_file_count = sum(len(group.get("aliases", [])) for group in groups)
    if raw_file_count != int(index["summary"]["raw_ironclad_files"]):
        raise ValueError("aliases 文件数与 raw_ironclad_files 不一致")
    candidate_ids = {
        str(scene["scene_id"])
        for scene in index_scenes
        if isinstance(scene.get("candidate"), Mapping)
    }
    manifest_ids = {str(scene["scene_id"]) for scene in manifest_scenes}
    if candidate_ids != manifest_ids:
        raise ValueError("manifest 场景必须恰好对应 index 的 257 个规则候选")
    if int(index["summary"]["act1_combat_rows"]) != len(index_scenes):
        raise ValueError("第一幕战斗行数与 summary 不一致")
    if int(index["summary"]["independent_run_groups"]) != len(groups):
        raise ValueError("独立 run 数与 groups 不一致")
    accepted_count = sum(
        str(scene.get("content_admission_status")) == "accepted"
        for scene in manifest_scenes
    )
    if accepted_count != int(manifest["summary"]["content_eligible_scenes"]):
        raise ValueError("manifest accepted 场景数与 summary 不一致")
    if int(manifest["summary"]["content_eligible_scenes"]) != 99:
        raise ValueError("当前基线不是用户指定的99场，需先更新分析口径")
    if int(index["summary"]["rule_candidates"]["scene_count"]) != len(manifest_scenes):
        raise ValueError("规则候选数量与 index summary 不一致")
    if manifest.get("formal_training_ready") or manifest.get("formal_evaluation_ready"):
        raise ValueError("manifest 不得标记为正式训练/评估 ready")
    if contract.get("action_count") != 66 or contract.get("end_turn") != 50:
        raise ValueError("当前 public-battle 动作契约不是66位/50结束回合")
    capacity = contract.get("capacity", {})
    if capacity.get("hand") != 10 or capacity.get("targets") != 5 or capacity.get("potions") != 3:
        raise ValueError("当前 public-battle 容量契约发生漂移")
    if manifest.get("source_admission_policy") != "public-derived-standard-v1":
        raise ValueError("manifest 来源准入策略漂移")


def build_priority(
    priority_id: str,
    gain: dict[str, Any],
    dependency_kind: str,
    risk: str,
    required_observations: list[str],
    action_changes: list[str],
    capacity_changes: list[str],
    acceptance: list[str],
    reason: str,
) -> dict[str, Any]:
    return {
        "id": priority_id,
        "dependency_kind": dependency_kind,
        "reason": reason,
        "projected_complete_scene_gain": gain,
        "engineering_risk": risk,
        "required_observations": required_observations,
        "required_action_changes": action_changes,
        "required_capacity_changes": capacity_changes,
        "acceptance_conditions": acceptance,
        "not_actual_implementation": True,
        "uses_policy_outcome": False,
    }


def build_priorities(
    manifest_scenes: Sequence[Mapping[str, Any]],
    current_rows: Sequence[Mapping[str, Any]],
    graph: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_count = len(manifest_scenes)
    candidate_groups = len({str(row["group_id"]) for row in manifest_scenes})
    direct_atoms = {"card:Shockwave", "card:Hemokinesis", "card:Intimidate"}
    hand_atoms = {"card:Anger", "card:Fiend Fire", "card:Headbutt"}
    potion_atoms = {"potion:PowerPotion", "potion:DistilledChaos"}
    rejected = [row for row in manifest_scenes if row.get("content_admission_status") != "accepted"]
    direct_gain = yield_metrics(rejected, direct_atoms, current_rows, candidate_count, candidate_groups)
    hand_gain = yield_metrics(rejected, hand_atoms, current_rows, candidate_count, candidate_groups)
    potion_gain = yield_metrics(rejected, potion_atoms, current_rows, candidate_count, candidate_groups)

    source_potential = source_potential_yields(graph)
    priorities = [
        build_priority(
            "direct-state-cards",
            direct_gain,
            "evidence_complete_content_candidate",
            "中等：需新增3类卡及数值/升级行为；若三类均为直接动作，当前66位、手牌10、目标5和变长牌堆可维持，但 target_kind 与状态字段必须逐卡核验。",
            [
                "三类卡的正版基础/升级数值与 target_kind",
                "Hemokinesis 的玩家 HP 变化及奖励读取时点",
                "Shockwave/Intimidate 造成的具名敌方减益与多目标观测",
            ],
            [
                "更新版本化 CardRegistry、central contract 与 mask；不得把未知卡映射为 PAD",
                "若行为核验确认无二次选择/随机生成，保持66位动作；否则转入协议迁移而不是静默代选",
            ],
            [
                "确认这些精确场景的 master deck 均不超过96；初始牌组逐副本保留",
                "证明新增卡没有未登记的状态牌生成或把其生成上界纳入容量测试",
            ],
            [
                "逐卡基础/升级/目标/mask/状态回归通过",
                "17个精确 scene_id 全部能以入口A reset 并在随机与规则开发集成中完整终止",
                "不因某一场失败而删除该场卡牌、药水或遗物；失败场景继续留在拒绝索引",
            ],
            "在证据完整候选中一次覆盖17场、8个关联组，并新增3 Louse与Red Slaver两个遭遇标签；收益低于含Anger的更大组合，但不依赖当前缺失的二次选择协议。",
        ),
        build_priority(
            "hand-copy-secondary",
            hand_gain,
            "evidence_complete_content_candidate",
            "高：M1 已明确 Anger/复制路径延期；二次选择、手牌多牌消耗、复制实体和动态容量不能由当前66位动作自动代替。",
            [
                "完整手牌/弃牌/消耗区语义及每个副本的升级/动态字段",
                "需要玩家选择的 card/pile 对象及选择完成前的可见状态（具体卡逐条正版核验）",
                "复制/临时牌的生成数量、唯一实体生命周期和外部截断前最后完整观测",
            ],
            [
                "新增版本化二次选择动作或等价结构化 choice API；不得用固定默认目标或随机代选",
                "动作 mask 必须表达每个合法选择，训练轨迹与 checkpoint 任务版本一起迁移",
            ],
            [
                "按单动作生成上界、master deck<=96和int16临时ID边界证明最坏情况",
                "证明Anger重复复制在动作预算内不会造成未编码牌区；不把丢牌后truncated当作完整场景",
            ],
            [
                "20个精确 scene_id 的全部原子依赖都通过后才计入新增；部分卡通过不提前入场",
                "choice/生成/容量/恢复/完整观测回归通过，并记录新的输入、动作、序列化版本",
                "从头开发集成不异常终止；不使用规则或PPO胜率选出其中子集",
            ],
            "完整依赖闭包的场景收益为20场、15个关联组，收益最高但工程前置最重；它不应被误写成当前66位协议可以直接加入。",
        ),
        build_priority(
            "direct-generated-potions",
            potion_gain,
            "evidence_complete_content_candidate",
            "高且收益低：只解除PowerPotion与DistilledChaos可确定打开4场、2个关联组且没有新独立run；其余非空药水多与未支持卡牌重叠。",
            [
                "药水库存多重集、A20实际2槽与规范3行预留的区分",
                "随机生成卡/自动出牌药水的完整可达实体闭包与环境seed复现",
                "药水使用目标、自动结算、药水对玩家状态的可见影响",
            ],
            [
                "只有确认药水不需要玩家二次选择时才可复用66位；选择型药水另建动作/序列化版本",
                "空槽、角色容量和药水动作 mask 必须分别验证，不把预留第三行当作可用槽",
            ],
            [
                "为随机/自动生成实体给出单动作上界和完整牌区容量证明",
                "按库存时序核对获得、使用、丢弃，无法恢复槽位时只使用明确命名的规范化策略",
            ],
            [
                "4个精确 scene_id 的药水机制、库存和生成闭包全部通过",
                "开发集成验证自然终止、完整观测和药水 mask；不因成功率筛掉困难药水场景",
                "剩余GamblersBrew/SkillPotion等场景继续按其卡牌联合依赖统计，不冒充本批收益",
            ],
            "它是按目标覆盖补齐药水的最低可证批次，而不是按药水出现次数排序；4场收益小于卡牌批次，但会带来PowerPotion、DistilledChaos和Exordium Wildlife。",
        ),
    ]
    # 这是证据前置，不占三条内容实现批次；不把潜在行写成确定收益。
    mandatory_source_gate = {
        "id": "source-prefix-evidence-gate",
        "status": "mandatory_before_claiming_floor_6_plus_or_real_elite_coverage",
        "potential_only": True,
        "potential": source_potential,
        "required_observations": [
            "?/$ 房间的完整 path_per_floor、event_choices 与 shop/purchase/purge 前缀",
            "每一场精英对应的燃烧强化/绿钥匙状态，而不是只知道存在某个精英",
            "遗物跨战斗 counter/data 与获得楼层；不能用默认0",
            "药水获得、使用、丢弃、自动生成的楼层内时序",
        ],
        "acceptance_conditions": [
            "固定提交重新运行离线审计，逐场同时通过来源前缀、入口A字段、版本/修饰和内容闭包检查",
            "保留所有原始 blocker 与完整场景内容；只把实际无 blocker 的行升级为证据完整候选",
            "新旧关联组仍按完整run隔离，不能把同一run的不同楼层拆到不同split",
        ],
        "definite_complete_scene_gain": 0,
        "reason": "当前证据完整候选最高只到floor5；卡牌实现本身不能产生floor6–14或425条精英记录的来源证据。",
    }
    return {
        "schema": PRIORITY_SCHEMA,
        "baseline": {
            "current_executable_scene_count": len(current_rows),
            "current_executable_run_count": len({str(row["group_id"]) for row in current_rows}),
            "baseline_scene_count": 99,
            "actual_net_new_scene_count_vs_baseline_99": 0,
            "current_99_all_development_integration_checked": True,
        },
        "ordering": {
            "scene_gain_rank_in_the_three_candidates": [
                "hand-copy-secondary",
                "direct-state-cards",
                "direct-generated-potions",
            ],
            "recommended_execution_order_after_risk_review": [
                "direct-state-cards",
                "hand-copy-secondary",
                "direct-generated-potions",
            ],
            "basis": [
                "完整候选的闭包收益，而不是卡牌单独出现次数",
                "新增独立run、遭遇和内容维度",
                "动作/容量/观测风险及M1既有延期裁定",
            ],
            "not_used": ["RuleAgent胜率", "PPO胜率", "单次集成回报", "将来源潜在收益当作确定收益"],
        },
        "mandatory_source_evidence_gate": mandatory_source_gate,
        "recommended_batches": priorities,
        "non_selected_observation": {
            "single_item_ranking_is_in_report_analysis": True,
            "potion_frequency_warning": "GamblersBrew 5场、SkillPotion 4场等出现次数不等于独立可解锁场景；其候选常同时被卡牌 blocker 阻断。",
            "m1_missing_reward_cards_warning": "Dropkick、Entrench、Rage、Sentinel、Thunderclap、True Grit 的奖励记录不是入口A完整牌组证据，未据此生成场景。",
        },
    }


EXTERNAL_RECORD_LIST_KEYS = (
    "scenes",
    "candidates",
    "candidate_rows",
    "scene_rows",
    "scene_candidates",
    "rows",
    "records",
    "entries",
    "results",
    "audits",
    "evidence",
    "events",
    "snapshots",
    "items",
)


def external_record_list(value: Any) -> list[Mapping[str, Any]]:
    """读取外部候选的记录列表，但不把任意嵌套数组误认为场景。"""

    if isinstance(value, list):
        if not all(isinstance(item, Mapping) for item in value):
            raise ValueError("外部候选列表含有非对象记录")
        return list(value)
    if not isinstance(value, Mapping):
        raise TypeError("外部候选文件必须是对象或对象列表")
    for key in EXTERNAL_RECORD_LIST_KEYS:
        records = value.get(key)
        if isinstance(records, list):
            if not all(isinstance(item, Mapping) for item in records):
                raise ValueError(f"外部候选 {key} 含有非对象记录")
            return list(records)
    if value.get("scene_id") is not None or value.get("candidate") is not None:
        return [value]
    for key in ("payload", "data", "result"):
        nested = value.get(key)
        if isinstance(nested, (Mapping, list)):
            return external_record_list(nested)
    raise ValueError("外部候选文件没有可识别的场景记录列表")


def nested_record_mappings(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings = [record]
    for key in (
        "source",
        "provenance",
        "source_group",
        "identity",
        "evidence",
        "metadata",
        "scene",
        "candidate",
        "entry_candidate",
        "entry",
        "initial_state",
    ):
        value = record.get(key)
        if isinstance(value, Mapping):
            mappings.append(value)
    return mappings


def first_record_value(record: Mapping[str, Any], names: Sequence[str]) -> Any:
    for mapping in nested_record_mappings(record):
        for name in names:
            if name in mapping and mapping[name] is not None:
                return mapping[name]
    return None


def explicit_bool(record: Mapping[str, Any], names: Sequence[str]) -> bool | None:
    value = first_record_value(record, names)
    if value is None:
        return None
    return value if isinstance(value, bool) else None


def record_string_list(record: Mapping[str, Any], names: Sequence[str]) -> list[str]:
    values: list[str] = []
    for mapping in nested_record_mappings(record):
        for name in names:
            value = mapping.get(name)
            if isinstance(value, list):
                values.extend(str(item) for item in value if isinstance(item, (str, int, float)))
    return sorted(set(values))


def status_strings(record: Mapping[str, Any]) -> list[str]:
    names = (
        "status",
        "reconstruction_status",
        "source_status",
        "prefix_status",
        "entry_status",
        "visible_entry_status",
        "target_battle_status",
        "battle_evidence_status",
        "static_content_status",
        "runtime_status",
        "verification_status",
        "validation_status",
        "candidate_status",
        "admission_status",
        "closure_status",
        "backend_status",
        "formal_status",
        "content_admission_status",
        "implementation_batch_status",
        "formal_eligibility",
        "static_status",
        "content_status",
    )
    values: list[str] = []
    for mapping in nested_record_mappings(record):
        for name in names:
            value = mapping.get(name)
            if isinstance(value, str):
                values.append(value.lower())
    return values


def status_is_positive(values: Sequence[str]) -> bool:
    if not values:
        return False
    negative = ("unknown", "unverified", "unproven", "pending", "incomplete", "missing", "rejected", "snapshot")
    positive = ("complete", "verified", "accepted", "admitted", "passed", "constructible", "ready", "available")
    return any(any(marker in value for marker in negative) for value in values) is False and any(
        any(marker in value for marker in positive) for value in values
    )


def extract_external_candidate(record: Mapping[str, Any]) -> dict[str, Any] | None:
    """只接受明确的入口候选，不从 master_deck 或最终牌组字段猜入口。"""

    options: list[Mapping[str, Any]] = []
    for key in ("candidate", "entry_candidate", "entry", "initial_state", "scene"):
        value = record.get(key)
        if isinstance(value, Mapping):
            options.append(value)
    options.append(record)
    for option in options:
        if all(key in option for key in ("deck", "player", "relics", "potions")):
            candidate = copy.deepcopy(dict(option))
            if "floor" not in candidate:
                floor = first_record_value(record, ("floor",))
                if floor is not None:
                    candidate["floor"] = floor
            if "encounter" not in candidate:
                encounter = first_record_value(record, ("encounter", "encounter_label"))
                if encounter is not None:
                    candidate["encounter"] = encounter
            return candidate
    return None


def candidate_content_projection(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """只用入口内容比较候选；忽略复现元数据，避免把seed字段当成内容冲突。"""

    content_keys = (
        "entry_timing",
        "initialization_phase",
        "floor",
        "act",
        "character",
        "ascension",
        "player",
        "deck",
        "relics",
        "potions",
        "potion_slot_policy",
        "encounter",
    )
    return {
        key: copy.deepcopy(candidate[key])
        for key in content_keys
        if key in candidate
    }


def candidate_content_sha256(candidate: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_bytes(candidate_content_projection(candidate)))


def normalise_identity_token(token: Any) -> str | None:
    if not isinstance(token, str) or not token:
        return None
    if token.startswith("sha:"):
        return "raw_sha256:" + token.split(":", 1)[1].lower()
    if token.startswith("raw_sha256:"):
        return "raw_sha256:" + token.split(":", 1)[1].lower()
    if token.startswith("seed_played:"):
        return "source_seed:" + token.split(":", 1)[1]
    if token.startswith("source_seed:"):
        return token
    if token.startswith("play_id:"):
        return token
    if token.startswith("source_path:"):
        return token
    return None


def external_identity_tokens(record: Mapping[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for mapping in nested_record_mappings(record):
        for key, prefix in (
            ("raw_sha256", "raw_sha256:"),
            ("sha256", "raw_sha256:"),
            ("source_sha256", "raw_sha256:"),
            ("raw_sha", "raw_sha256:"),
            ("play_id", "play_id:"),
            ("source_seed", "source_seed:"),
            ("seed_played", "source_seed:"),
        ):
            value = mapping.get(key)
            if value is not None and isinstance(value, (str, int, float)) and not isinstance(value, bool):
                tokens.add(prefix + str(value).lower() if prefix == "raw_sha256:" else prefix + str(value))
        for key in ("source_path", "path"):
            value = mapping.get(key)
            if isinstance(value, str) and value:
                tokens.add("source_path:" + value)
        for key in ("aliases", "source_paths"):
            value = mapping.get(key)
            if isinstance(value, list):
                tokens.update(
                    "source_path:" + str(path)
                    for path in value
                    if isinstance(path, str) and path
                )
        identity_tokens = mapping.get("identity_tokens")
        if isinstance(identity_tokens, list):
            for token in identity_tokens:
                normalised = normalise_identity_token(token)
                if normalised:
                    tokens.add(normalised)
    return tokens


def external_group_label(record: Mapping[str, Any]) -> str | None:
    value = first_record_value(record, ("group_id", "group_key", "run_group", "run_id"))
    return str(value) if value is not None else None


def external_source_path(record: Mapping[str, Any]) -> str | None:
    value = first_record_value(record, ("source_path", "path"))
    return str(value) if isinstance(value, str) else None


def external_blocker_lists(record: Mapping[str, Any]) -> tuple[list[str], list[str], list[str]]:
    source_blockers = set(record_string_list(record, ("source_blockers", "prefix_blockers", "resolved_source_blockers")))
    content_blockers = set(record_string_list(record, ("content_blockers", "static_content_blockers", "implementation_batch_blockers")))
    generic = set(record_string_list(record, ("blockers", "admission_blockers")))
    resolved = set(record_string_list(record, ("resolved_blockers", "resolved_source_blockers")))
    for blocker in generic:
        if blocker.startswith(("UNSUPPORTED_CARD:", "UNSUPPORTED_OR_CHOICE_POTION:", "CARD_SECONDARY_CHOICE:", "UNSUPPORTED_RELIC:")) or blocker == "UNKNOWN_OR_MISMATCHED_ENCOUNTER":
            content_blockers.add(blocker)
        elif blocker not in resolved:
            source_blockers.add(blocker)
    source_blockers -= resolved
    return sorted(source_blockers), sorted(content_blockers), sorted(resolved)


def normalise_external_record(
    record: Mapping[str, Any],
    kind: str,
    record_index: int,
) -> dict[str, Any]:
    candidate = extract_external_candidate(record)
    scene_id_value = first_record_value(record, ("scene_id", "id"))
    scene_id = str(scene_id_value) if scene_id_value is not None else None
    floor_value = first_record_value(record, ("floor",))
    try:
        floor = int(floor_value) if floor_value is not None else None
    except (TypeError, ValueError):
        floor = None
    encounter_value = first_record_value(record, ("encounter_label", "encounter", "enemies"))
    encounter_label = (
        ENCOUNTER_ENUM_TO_LABEL.get(str(encounter_value), str(encounter_value))
        if encounter_value is not None
        else None
    )
    combat_index_value = first_record_value(record, ("combat_index", "combat", "combat_id", "index"))
    try:
        combat_index = int(combat_index_value) if combat_index_value is not None else None
    except (TypeError, ValueError):
        combat_index = None
    if scene_id:
        match = re.search(r":floor-([0-9]+):combat-([0-9]+)$", scene_id)
        if match:
            floor = floor if floor is not None else int(match.group(1))
            combat_index = combat_index if combat_index is not None else int(match.group(2))

    source_blockers, content_blockers, resolved_blockers = external_blocker_lists(record)
    statuses = status_strings(record)
    source_complete = explicit_bool(
        record,
        ("source_prefix_complete", "prefix_complete", "source_complete", "entry_prefix_complete"),
    )
    if source_complete is None:
        source_values = [
            value
            for value in statuses
            if any(marker in value for marker in ("source", "prefix", "entry", "candidate"))
        ]
        source_complete = status_is_positive(source_values)
        if (
            kind == "prefix_candidates"
            and candidate is not None
            and not source_blockers
            and not any(
                any(marker in value for marker in ("unknown", "unverified", "unproven", "pending", "incomplete", "missing", "rejected"))
                for value in source_values
            )
        ):
            source_complete = True
    target_complete = explicit_bool(
        record,
        (
            "target_battle_evidence_complete",
            "battle_evidence_complete",
            "target_evidence_complete",
            "combat_evidence_complete",
        ),
    )
    if target_complete is None:
        target_values = [
            value
            for value in statuses
            if any(marker in value for marker in ("target", "battle", "combat", "snapshot"))
        ]
        target_complete = status_is_positive(target_values)
        if (
            kind == "prefix_candidates"
            and candidate is not None
            and scene_id is not None
            and not any(
                any(marker in value for marker in ("unknown", "unverified", "unproven", "pending", "incomplete", "missing", "rejected", "snapshot"))
                for value in target_values
            )
        ):
            target_complete = True

    static_explicit = explicit_bool(
        record,
        ("static_content_passed", "content_static_passed", "static_passed"),
    )
    static_values = [value for value in statuses if "static" in value or "content" in value or "implementation" in value]
    static_content_passed = static_explicit
    static_label = first_record_value(
        record,
        ("static_content_status", "content_status", "content_admission_status", "implementation_status"),
    )
    static_label_seen = isinstance(static_label, str)
    if static_content_passed is None and static_label_seen:
        static_label_lower = static_label.lower()
        if static_label_lower in {"accepted", "passed", "static_passed", "eligible", "admitted"}:
            static_content_passed = True
        elif static_label_lower in {"rejected", "pending", "unknown", "unverified", "incomplete"}:
            static_content_passed = False
    if static_content_passed is None:
        static_content_passed = status_is_positive(static_values)
    static_content_known = static_explicit is not None or static_label_seen or bool(static_values) or bool(content_blockers)

    runtime_verified = explicit_bool(
        record,
        ("actual_run_verified", "runtime_verified", "run_verified", "executed"),
    )
    runtime_label = first_record_value(
        record,
        ("runtime_status", "probe_status", "execution_status", "run_verification_status"),
    )
    if runtime_verified is None and isinstance(runtime_label, str):
        runtime_label_lower = runtime_label.lower()
        if runtime_label_lower in {"completed", "verified", "passed", "runtime_verified", "probe_completed"}:
            runtime_verified = True
        elif runtime_label_lower in {"pending", "unknown", "unverified", "incomplete", "rejected"}:
            runtime_verified = False
    if runtime_verified is None:
        runtime_values = [
            value
            for value in statuses
            if any(marker in value for marker in ("runtime", "execut", "probe", "integration"))
        ]
        runtime_verified = status_is_positive(runtime_values)
    formal_manifest = explicit_bool(
        record,
        ("formal_manifest", "in_formal_manifest", "formal_admitted"),
    )
    if formal_manifest is None:
        formal_values = [value for value in statuses if "formal" in value]
        formal_manifest = status_is_positive(formal_values)

    burning_value = explicit_bool(
        record,
        ("burning_elite", "is_burning_elite", "burningElite", "burning_modifier_known"),
    )
    source_identity = external_identity_tokens(record)
    source_path = external_source_path(record)
    source_build = first_record_value(record, ("source_build", "build_version", "version"))
    research_split = first_record_value(record, ("research_split", "split"))
    raw_battle_record = explicit_bool(
        record,
        ("target_battle_record_present", "battle_record_present", "raw_battle_record"),
    )
    return {
        "kind": kind,
        "record_index": record_index,
        "scene_id": scene_id,
        "floor": floor,
        "encounter_label": encounter_label,
        "combat_index": combat_index,
        "group_label": external_group_label(record),
        "source_path": source_path,
        "source_collection": source_collection(source_path) if source_path else None,
        "source_build": str(source_build) if source_build is not None else None,
        "research_split": str(research_split) if research_split is not None else None,
        "identity_tokens": sorted(source_identity),
        "candidate": candidate,
        "source_blockers": source_blockers,
        "content_blockers": content_blockers,
        "resolved_blockers": resolved_blockers,
        "source_prefix_complete": source_complete is True and not source_blockers,
        "source_prefix_complete_explicit": source_complete,
        "target_battle_evidence_complete": target_complete is True,
        "target_battle_evidence_explicit": target_complete,
        "static_content_passed": static_content_passed is True,
        "static_content_known": static_content_known,
        "actual_run_verified": runtime_verified is True,
        "formal_manifest": formal_manifest is True,
        "burning_elite": burning_value,
        "raw_battle_record": raw_battle_record,
        "raw_record_sha256": sha256_bytes(canonical_bytes(record)),
    }


def load_external_input(path: Path, expected_sha256: str | None, kind: str) -> dict[str, Any]:
    data, raw = read_json(path)
    actual = sha256_bytes(raw)
    expected = expected_sha256.lower() if isinstance(expected_sha256, str) and expected_sha256 else None
    return {
        "kind": kind,
        "path_obj": path,
        "path": relative_path(path),
        "bytes": len(raw),
        "actual_sha256": actual,
        "expected_sha256": expected,
        "hash_verified": expected is not None and actual == expected,
        "hash_status": "verified" if expected is not None and actual == expected else "missing_or_mismatch",
        "schema": data.get("schema") if isinstance(data, Mapping) else None,
        "record_count": len(external_record_list(data)),
        "raw": raw,
        "data": data,
    }


def original_identity_index(groups: Sequence[Mapping[str, Any]]) -> dict[str, set[str]]:
    index: defaultdict[str, set[str]] = defaultdict(set)
    for group in groups:
        group_id = str(group["group_id"])
        for token in group.get("identity_tokens", []):
            normalised = normalise_identity_token(token)
            if normalised:
                index[normalised].add(group_id)
        for alias in group.get("aliases", []):
            if isinstance(alias, str):
                index["source_path:" + alias].add(group_id)
        source_path = group.get("source_path")
        if isinstance(source_path, str):
            index["source_path:" + source_path].add(group_id)
    return index


def union_find_components(records: Sequence[Mapping[str, Any]]) -> list[set[int]]:
    parent = list(range(len(records)))
    token_owner: dict[str, int] = {}

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for index, record in enumerate(records):
        for token in record["identity_tokens"]:
            owner = token_owner.get(token)
            if owner is None:
                token_owner[token] = index
            else:
                union(index, owner)
    components: defaultdict[int, set[int]] = defaultdict(set)
    for index in range(len(records)):
        components[find(index)].add(index)
    return list(components.values())


def record_bool_values(record: Mapping[str, Any], key: str) -> set[bool]:
    value = record.get(key)
    return {value} if isinstance(value, bool) else set()


def resolve_external_run_ids(
    records: Sequence[Mapping[str, Any]],
    original_token_index: Mapping[str, set[str]],
    original_group_ids: set[str],
) -> tuple[dict[int, str], dict[int, str], dict[str, Any]]:
    run_ids: dict[int, str] = {}
    statuses: dict[int, str] = {}
    original_matches: dict[int, set[str]] = {}
    for index, record in enumerate(records):
        matches: set[str] = set()
        for token in record["identity_tokens"]:
            matches.update(original_token_index.get(token, set()))
        if record.get("group_label") in original_group_ids:
            matches.add(str(record["group_label"]))
        original_matches[index] = matches

    identity_conflicts = 0
    unresolved = 0
    external_components = union_find_components(records)
    for component in external_components:
        matches = set().union(*(original_matches[index] for index in component))
        tokens = sorted({token for index in component for token in records[index]["identity_tokens"]})
        labels = {records[index].get("group_label") for index in component if records[index].get("group_label")}
        strong_identity = bool(tokens)
        if len(matches) > 1:
            canonical = "identity-conflict:" + sha256_bytes(canonical_bytes(sorted(matches)))[:24]
            status = "identity_conflict"
            identity_conflicts += len(component)
        elif len(matches) == 1:
            canonical = next(iter(matches))
            status = "resolved_to_original_group"
        elif strong_identity:
            canonical = "external-run:" + sha256_bytes(canonical_bytes(tokens))[:24]
            status = "resolved_external_identity"
        elif labels and len(labels) == 1:
            canonical = "unresolved-run:" + sha256_bytes(canonical_bytes(sorted(labels)))[:24]
            status = "unresolved_group_label_only"
            unresolved += len(component)
        else:
            canonical = "unresolved-run:" + sha256_bytes(
                canonical_bytes([records[index]["raw_record_sha256"] for index in sorted(component)])
            )[:24]
            status = "unresolved_no_source_identity"
            unresolved += len(component)
        for index in component:
            run_ids[index] = canonical
            statuses[index] = status
    return run_ids, statuses, {
        "external_component_count": len(external_components),
        "identity_conflict_record_count": identity_conflicts,
        "unresolved_identity_record_count": unresolved,
        "group_id_only_is_not_distinct_run": True,
    }


def parse_scene_suffix(scene_id: str | None) -> tuple[int | None, int | None]:
    if not scene_id:
        return None, None
    match = re.search(r":floor-([0-9]+):combat-([0-9]+)$", scene_id)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def build_original_merged_row(
    source: Mapping[str, Any],
    manifest: Mapping[str, Any] | None,
) -> dict[str, Any]:
    candidate = copy.deepcopy(source.get("candidate")) if isinstance(source.get("candidate"), Mapping) else None
    if manifest and isinstance(manifest.get("candidate"), Mapping):
        candidate = copy.deepcopy(manifest["candidate"])
    content_blockers = sorted({str(item) for item in (manifest or {}).get("content_blockers", [])})
    current = bool(manifest and manifest.get("content_admission_status") == "accepted")
    candidate_variants = []
    if candidate is not None:
        candidate_variants.append(
            {
                "content_sha256": candidate_content_sha256(candidate),
                "candidate": copy.deepcopy(candidate),
                "kind": "corpus_index",
                "record_index": None,
            }
        )
    return {
        "scene_id": str(source["scene_id"]),
        "group_id": str(source["group_id"]),
        "canonical_run_id": str(source["group_id"]),
        "run_identity_status": "resolved_original_group",
        "source_path": source.get("source_path"),
        "source_collection": source_collection(str(source.get("source_path", ""))),
        "source_build": source.get("source_build"),
        "source_seed": source.get("source_seed"),
        "raw_sha256": source.get("raw_sha256"),
        "research_split": source.get("research_split"),
        "floor": int(source["floor"]),
        "encounter_label": str(source["encounter_label"]),
        "encounter_tier": encounter_tier(str(source["encounter_label"])),
        "source_blockers": sorted({str(item) for item in source.get("blockers", [])}),
        "original_source_blockers": sorted({str(item) for item in source.get("blockers", [])}),
        "resolved_source_blockers": [],
        "content_blockers": content_blockers,
        "original_content_blockers": content_blockers,
        "candidate": candidate,
        "candidate_variants": candidate_variants,
        "provenance": [{"kind": "corpus_index", "scene_id": str(source["scene_id"])}],
        "external_record_count": 0,
        "raw_battle_record": True,
        "source_prefix_complete": candidate is not None and not source.get("blockers"),
        "target_battle_evidence_complete": candidate is not None,
        "target_evidence_values": {True} if candidate is not None else set(),
        "target_evidence_conflict": False,
        "static_content_known": manifest is not None,
        "static_content_passed": current,
        "actual_run_verified": False,
        "runtime_scopes": [],
        "formal_manifest": False,
        "burning_elite_values": set(),
        "content_conflict": False,
        "identity_conflict": False,
        "scene_identity_status": "resolved_by_original_scene_id",
        "original_manifest": manifest is not None,
        "original_current_99": current,
        "entity_closure": copy.deepcopy((manifest or {}).get("entity_closure")),
    }


def external_scene_match(
    record: Mapping[str, Any],
    canonical_run_id: str,
    original_by_id: Mapping[str, Mapping[str, Any]],
    original_by_group_floor: Mapping[tuple[str, int], list[Mapping[str, Any]]],
) -> tuple[str | None, str]:
    scene_id = record.get("scene_id")
    if scene_id and scene_id in original_by_id:
        return str(scene_id), "exact_scene_id"
    floor = record.get("floor")
    if canonical_run_id in {str(row["group_id"]) for row in original_by_id.values()} and floor is not None:
        candidates = list(original_by_group_floor.get((canonical_run_id, int(floor)), []))
        encounter = record.get("encounter_label")
        if encounter:
            candidates = [row for row in candidates if str(row["encounter_label"]) == str(encounter)]
        combat_index = record.get("combat_index")
        if combat_index is not None:
            suffix_matches = []
            for row in candidates:
                _, index = parse_scene_suffix(str(row["scene_id"]))
                if index == int(combat_index):
                    suffix_matches.append(row)
            candidates = suffix_matches
        if len(candidates) == 1:
            return str(candidates[0]["scene_id"]), "source_identity_floor_encounter"
        if len(candidates) > 1:
            return None, "ambiguous_source_identity_floor"
    if canonical_run_id.startswith("external-run:") and floor is not None and record.get("combat_index") is not None:
        return (
            f"{canonical_run_id}:floor-{int(floor)}:combat-{int(record['combat_index'])}",
            "new_external_scene_identity",
        )
    return None, "unresolved_scene_identity"


def merge_external_inputs(
    index_scenes: Sequence[Mapping[str, Any]],
    manifest_scenes: Sequence[Mapping[str, Any]],
    groups: Sequence[Mapping[str, Any]],
    external_batches: Sequence[Mapping[str, Any]],
    runtime_verified_scene_ids: set[str] | None = None,
) -> dict[str, Any]:
    """按 scene_id 和来源身份合并外部结果；冲突保留并阻断，不选择任一版本。"""

    runtime_verified_scene_ids = runtime_verified_scene_ids or set()
    original_by_id = {str(row["scene_id"]): row for row in index_scenes}
    manifest_by_id = {str(row["scene_id"]): row for row in manifest_scenes}
    original_by_group_floor: defaultdict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in index_scenes:
        original_by_group_floor[(str(row["group_id"]), int(row["floor"]))].append(row)
    merged: dict[str, dict[str, Any]] = {
        scene_id: build_original_merged_row(row, manifest_by_id.get(scene_id))
        for scene_id, row in original_by_id.items()
    }

    normalised_records: list[dict[str, Any]] = []
    input_record_sources: list[dict[str, Any]] = []
    for batch in external_batches:
        kind = str(batch.get("kind", "external"))
        data = batch.get("data")
        if data is None and isinstance(batch.get("records"), list):
            records = batch["records"]
        else:
            records = external_record_list(data)
        input_record_sources.append({"kind": kind, "record_count": len(records), "path": batch.get("path")})
        normalised_records.extend(
            normalise_external_record(record, kind, index)
            for index, record in enumerate(records)
        )
    original_tokens = original_identity_index(groups)
    original_group_ids = {str(group["group_id"]) for group in groups}
    run_ids, run_statuses, identity_summary = resolve_external_run_ids(
        normalised_records,
        original_tokens,
        original_group_ids,
    )

    duplicate_record_count = 0
    cross_source_connection_count = 0
    unresolved_scene_record_count = 0
    identity_ambiguous_record_count = 0
    original_source_collections = {
        str(group["group_id"]): source_collection(str(group.get("source_path", "")))
        for group in groups
    }
    for index, record in enumerate(normalised_records):
        canonical_run_id = run_ids[index]
        scene_key, scene_match_status = external_scene_match(
            record,
            canonical_run_id,
            original_by_id,
            original_by_group_floor,
        )
        if scene_key is None:
            unresolved_scene_record_count += 1
            scene_key = "unresolved-scene:" + record["raw_record_sha256"][:24]
            identity_ambiguous_record_count += scene_match_status.startswith("ambiguous")
        if scene_key not in merged:
            source_path = record.get("source_path") or "external/unknown"
            merged[scene_key] = {
                "scene_id": scene_key,
                "group_id": canonical_run_id,
                "canonical_run_id": canonical_run_id,
                "run_identity_status": run_statuses[index],
                "source_path": source_path,
                "source_collection": record.get("source_collection") or source_collection(str(source_path)),
                "source_build": record.get("source_build"),
                "source_seed": None,
                "raw_sha256": None,
                "research_split": record.get("research_split"),
                "floor": record.get("floor"),
                "encounter_label": record.get("encounter_label") or "UNKNOWN",
                "encounter_tier": encounter_tier(str(record.get("encounter_label") or "UNKNOWN")),
                "source_blockers": [],
                "original_source_blockers": [],
                "resolved_source_blockers": [],
                "content_blockers": [],
                "original_content_blockers": [],
                "candidate": None,
                "candidate_variants": [],
                "provenance": [],
                "external_record_count": 0,
                "raw_battle_record": record.get("raw_battle_record") is True,
                "source_prefix_complete": False,
                "target_battle_evidence_complete": False,
                "target_evidence_values": set(),
                "target_evidence_conflict": False,
                "static_content_known": False,
                "static_content_passed": False,
                "actual_run_verified": False,
                "runtime_scopes": [],
                "formal_manifest": False,
                "burning_elite_values": set(),
                "content_conflict": False,
                "identity_conflict": run_statuses[index] == "identity_conflict",
                "scene_identity_status": scene_match_status,
                "original_manifest": False,
                "original_current_99": False,
                "entity_closure": None,
            }
        target = merged[scene_key]
        if target["external_record_count"] > 0 or target["original_manifest"]:
            duplicate_record_count += 1
        target["external_record_count"] += 1
        target["provenance"].append(
            {
                "kind": record["kind"],
                "record_index": record["record_index"],
                "raw_record_sha256": record["raw_record_sha256"],
                "scene_match_status": scene_match_status,
                "run_identity_status": run_statuses[index],
                "identity_tokens": record["identity_tokens"],
            }
        )
        if target["canonical_run_id"] != canonical_run_id and not (
            scene_match_status == "exact_scene_id"
            and run_statuses[index] in {"unresolved_group_label_only", "unresolved_no_source_identity"}
        ):
            target["identity_conflict"] = True
        if run_statuses[index] == "identity_conflict":
            target["identity_conflict"] = True
        original_collection = original_source_collections.get(target["canonical_run_id"])
        if original_collection and record.get("source_collection") and original_collection != record["source_collection"]:
            cross_source_connection_count += 1

        external_candidate = record.get("candidate")
        if isinstance(external_candidate, Mapping):
            candidate_hash = candidate_content_sha256(external_candidate)
            if not any(variant.get("content_sha256") == candidate_hash for variant in target["candidate_variants"]):
                target["candidate_variants"].append(
                    {
                        "content_sha256": candidate_hash,
                        "candidate": copy.deepcopy(external_candidate),
                        "kind": record["kind"],
                        "record_index": record["record_index"],
                    }
                )
        if record["source_prefix_complete"]:
            target["resolved_source_blockers"].extend(target["source_blockers"])
            target["source_blockers"] = []
            target["source_prefix_complete"] = True
        target["source_blockers"] = sorted(
            set(target["source_blockers"]) | set(record["source_blockers"])
        )
        target["resolved_source_blockers"] = sorted(
            set(target["resolved_source_blockers"]) | set(record["resolved_blockers"])
        )
        target["source_blockers"] = sorted(
            set(target["source_blockers"]) - set(target["resolved_source_blockers"])
        )
        if record["content_blockers"]:
            target["content_blockers"] = sorted(
                set(target["content_blockers"]) | set(record["content_blockers"])
            )
        elif record["static_content_passed"]:
            target["content_blockers"] = []
        target["static_content_known"] = target["static_content_known"] or record["static_content_known"]
        target["static_content_passed"] = target["static_content_passed"] or record["static_content_passed"]
        if record["target_battle_evidence_complete"]:
            target["target_battle_evidence_complete"] = True
        if record["target_battle_evidence_explicit"] is not None:
            target["target_evidence_values"].add(record["target_battle_evidence_explicit"])
            if record["target_battle_evidence_explicit"] is False:
                target["target_battle_evidence_complete"] = False
        if record["raw_battle_record"] is True:
            target["raw_battle_record"] = True
        if record["actual_run_verified"]:
            target["actual_run_verified"] = True
            scope = "development_probe" if record["kind"] == "elite_audit" else "external_runtime"
            target["runtime_scopes"] = sorted(set(target["runtime_scopes"]) | {scope})
        if target["scene_id"] in runtime_verified_scene_ids:
            target["actual_run_verified"] = True
            target["runtime_scopes"] = sorted(set(target["runtime_scopes"]) | {"development_integration"})
        if record["formal_manifest"]:
            target["formal_manifest"] = True
        if record["burning_elite"] is not None:
            target["burning_elite_values"].add(record["burning_elite"])

    for target in merged.values():
        if target["scene_id"] in runtime_verified_scene_ids:
            target["actual_run_verified"] = True
            target["runtime_scopes"] = sorted(
                set(target["runtime_scopes"]) | {"development_integration"}
            )

    for target in merged.values():
        if len(target["target_evidence_values"]) > 1:
            target["source_blockers"].append("TARGET_BATTLE_EVIDENCE_CONFLICT")
            target["target_evidence_conflict"] = True
        if target["encounter_tier"] == "elite":
            if len(target["burning_elite_values"]) > 1:
                target["source_blockers"].append("BURNING_ELITE_MODIFIER_CONFLICT")
                target["identity_conflict"] = True
            elif not target["burning_elite_values"]:
                target["source_blockers"].append("BURNING_ELITE_MODIFIER_UNRECORDED")
            else:
                target["source_blockers"] = [
                    blocker
                    for blocker in target["source_blockers"]
                    if blocker != "BURNING_ELITE_MODIFIER_UNRECORDED"
                ]
        if target["candidate_variants"]:
            variant_hashes = {
                variant["content_sha256"] for variant in target["candidate_variants"]
            }
            if len(variant_hashes) > 1:
                target["content_conflict"] = True
            else:
                target["candidate"] = copy.deepcopy(target["candidate_variants"][0]["candidate"])
        if target["candidate"] is None and target["original_manifest"]:
            target["candidate"] = None
        if target["candidate"] is not None and target["floor"] is None:
            target["floor"] = target["candidate"].get("floor")
        if target["candidate"] is not None and target["encounter_label"] == "UNKNOWN":
            candidate_encounter = str(target["candidate"].get("encounter", "UNKNOWN"))
            target["encounter_label"] = ENCOUNTER_ENUM_TO_LABEL.get(
                candidate_encounter,
                candidate_encounter,
            )
            target["encounter_tier"] = encounter_tier(target["encounter_label"])
        target["source_blockers"] = sorted(set(target["source_blockers"]))
        target["content_blockers"] = sorted(set(target["content_blockers"]))
        required_fields = all(
            entry_field_present(target["candidate"], field)
            for field in ENTRY_FIELD_NAMES
        )
        target["entry_evidence_complete"] = bool(
            target["candidate"] is not None
            and required_fields
            and target["raw_battle_record"]
            and not target["source_blockers"]
            and target["target_battle_evidence_complete"]
            and not target["target_evidence_conflict"]
            and target["run_identity_status"] not in {"identity_conflict", "unresolved_group_label_only", "unresolved_no_source_identity"}
            and not target["content_conflict"]
            and not target["identity_conflict"]
        )
        target["content_unsupported"] = bool(target["entry_evidence_complete"] and target["content_blockers"])
        target["static_content_passed"] = bool(
            target["static_content_passed"]
            and target["entry_evidence_complete"]
            and not target["content_conflict"]
        )
        if target["formal_manifest"] and target["entry_evidence_complete"]:
            target["primary_state"] = "formal_manifest"
        elif target["actual_run_verified"] and target["entry_evidence_complete"]:
            target["primary_state"] = "actual_run_verified"
        elif target["static_content_passed"] and target["entry_evidence_complete"]:
            target["primary_state"] = "static_content_passed"
        elif target["content_conflict"] or target["identity_conflict"] or target["target_evidence_conflict"]:
            target["primary_state"] = "conflict_rejected"
        elif target["content_unsupported"]:
            target["primary_state"] = "entry_evidence_complete_content_unsupported"
        elif target["candidate"] is not None and target["source_prefix_complete"] and not target["target_battle_evidence_complete"]:
            target["primary_state"] = "entry_content_prefix_recoverable_target_incomplete"
        elif target["actual_run_verified"]:
            target["primary_state"] = "actual_run_verified_target_incomplete"
        elif target["static_content_passed"]:
            target["primary_state"] = "static_content_passed_target_incomplete"
        elif target["raw_battle_record"]:
            target["primary_state"] = "battle_record_only"
        else:
            target["primary_state"] = "external_unlinked"
        target["burning_elite_values"] = sorted(target["burning_elite_values"])

    rows = sorted(merged.values(), key=lambda row: str(row["scene_id"]))
    original_scene_ids = set(original_by_id)
    resolved_external_rows = [
        row
        for row in rows
        if row["scene_id"] not in original_scene_ids
        and row["run_identity_status"] in {"resolved_external_identity", "resolved_to_original_group"}
    ]
    state_counts = Counter(str(row["primary_state"]) for row in rows)
    bool_counts = {
        "entry_evidence_complete": sum(bool(row["entry_evidence_complete"]) for row in rows),
        "static_content_passed": sum(bool(row["static_content_passed"]) for row in rows),
        "actual_run_verified": sum(bool(row["actual_run_verified"]) for row in rows),
        "formal_manifest": sum(bool(row["formal_manifest"]) for row in rows),
        "content_conflict": sum(bool(row["content_conflict"]) for row in rows),
    }
    return {
        "scene_rows": rows,
        "summary": {
            "merged_scene_count": len(rows),
            "original_scene_count": len(original_by_id),
            "new_scene_count": len(rows) - len(original_by_id),
            "merged_resolved_run_count": len({row["canonical_run_id"] for row in rows if not str(row["canonical_run_id"]).startswith("unresolved-")}),
            "new_resolved_run_count": len({row["canonical_run_id"] for row in resolved_external_rows}),
            "unresolved_external_scene_count": sum(row["primary_state"] == "external_unlinked" for row in rows),
            "external_record_count": len(normalised_records),
            "input_record_sources": input_record_sources,
            "same_scene_duplicate_record_count": duplicate_record_count,
            "content_conflict_scene_count": bool_counts["content_conflict"],
            "target_evidence_conflict_scene_count": sum(
                bool(row["target_evidence_conflict"]) for row in rows
            ),
            "identity_conflict_scene_count": sum(bool(row["identity_conflict"]) for row in rows),
            "identity_ambiguous_record_count": identity_ambiguous_record_count,
            "unresolved_scene_record_count": unresolved_scene_record_count,
            "cross_source_connection_count": cross_source_connection_count,
            "state_counts": dict(sorted(state_counts.items())),
            "boolean_state_counts": bool_counts,
            "group_id_string_not_used_as_distinct_identity": True,
            "content_conflicts_are_blocking": True,
            "unknown_burning_elite_is_blocking": True,
            **identity_summary,
        },
        "new_scene_rows": resolved_external_rows,
    }


def merged_candidate_row(row: Mapping[str, Any]) -> dict[str, Any]:
    result = {
        "scene_id": row["scene_id"],
        "group_id": row["canonical_run_id"],
        "source_path": row.get("source_path"),
        "source_build": row.get("source_build"),
        "source_seed": row.get("source_seed"),
        "raw_sha256": row.get("raw_sha256"),
        "research_split": row.get("research_split") or "unassigned",
        "floor": row.get("floor"),
        "encounter_label": row.get("encounter_label", "UNKNOWN"),
        "candidate": copy.deepcopy(row.get("candidate")),
        "content_blockers": list(row.get("content_blockers", [])),
        "content_admission_status": "accepted"
        if row.get("static_content_passed") and not row.get("content_blockers")
        else "rejected",
        "entity_closure": copy.deepcopy(row.get("entity_closure")),
    }
    return result


def merged_dependency_graph(
    merged_rows: Sequence[Mapping[str, Any]],
    current_ids: set[str],
) -> dict[str, Any]:
    """把合并后的状态重新投影为逐场依赖图。"""

    source_rows = []
    manifest_by_id: dict[str, dict[str, Any]] = {}
    merged_by_id = {str(row["scene_id"]): row for row in merged_rows}
    for row in merged_rows:
        if row.get("floor") is None:
            continue
        source_rows.append(
            {
                "scene_id": str(row["scene_id"]),
                "group_id": str(row["canonical_run_id"]),
                "research_split": row.get("research_split") or "unassigned",
                "floor": int(row["floor"]),
                "encounter_label": row.get("encounter_label", "UNKNOWN"),
                "blockers": list(row.get("source_blockers", [])),
                "candidate": row.get("candidate"),
            }
        )
        manifest_by_id[str(row["scene_id"])] = {
            "content_blockers": list(row.get("content_blockers", [])),
        }
    graph = blocker_dependency_graph(source_rows, manifest_by_id, current_ids)
    graph_rows = {str(row["scene_id"]): row for row in graph["rows"]}
    for scene_id, graph_row in graph_rows.items():
        merged = merged_by_id[scene_id]
        graph_row["status"] = merged["primary_state"]
        graph_row["candidate_exists"] = merged["candidate"] is not None
        graph_row["evidence_complete_under_public_derived_policy"] = bool(
            merged["entry_evidence_complete"]
        )
        graph_row["current_executable"] = scene_id in current_ids
        graph_row["potential_only"] = not bool(merged["entry_evidence_complete"])
        graph_row["content_conflict"] = bool(merged["content_conflict"])
        graph_row["identity_conflict"] = bool(merged["identity_conflict"])
        graph_row["target_evidence_conflict"] = bool(merged["target_evidence_conflict"])
    graph["rows"] = [graph_rows[key] for key in sorted(graph_rows)]
    graph["summary"]["current_executable_scene_count"] = sum(
        row["current_executable"] for row in graph["rows"]
    )
    graph["summary"]["source_or_prefix_incomplete_scene_count"] = sum(
        row["status"] in {
            "battle_record_only",
            "entry_content_prefix_recoverable_target_incomplete",
            "external_unlinked",
        }
        for row in graph["rows"]
    )
    graph["summary"]["evidence_complete_content_blocked_scene_count"] = sum(
        row["status"] == "entry_evidence_complete_content_unsupported"
        for row in graph["rows"]
    )
    graph["summary"]["evidence_complete_not_current_scene_count"] = sum(
        row["evidence_complete_under_public_derived_policy"]
        and not row["current_executable"]
        and row["status"] != "entry_evidence_complete_content_unsupported"
        for row in graph["rows"]
    )
    graph["summary"]["merged_state_counts"] = dict(
        sorted(Counter(row["status"] for row in graph["rows"]).items())
    )
    return graph


def expanded_metadata(
    base_metadata: Mapping[str, Mapping[str, Any]],
    merged_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    metadata = {str(key): dict(value) for key, value in base_metadata.items()}
    for row in merged_rows:
        group_id = str(row["canonical_run_id"])
        if group_id in metadata:
            continue
        source_path = str(row.get("source_path") or "external/unknown")
        metadata[group_id] = {
            "group_id": group_id,
            "source_path": source_path,
            "source_collection": row.get("source_collection") or source_collection(source_path),
            "source_partition": source_partition(source_path),
            "raw_sha256": row.get("raw_sha256"),
            "research_split": row.get("research_split") or "unassigned",
            "source_build": row.get("source_build") or "unknown",
            "character": "IRONCLAD",
            "character_evidence": "外部候选记录；需在最终来源审计中复核",
            "ascension": row.get("candidate", {}).get("ascension")
            if isinstance(row.get("candidate"), Mapping)
            else None,
            "ascension_evidence": "external_candidate_or_unknown",
            "aliases": [],
            "alias_count": 0,
        }
    return metadata


def expanded_analysis(
    merge_result: Mapping[str, Any],
    base_metadata: Mapping[str, Mapping[str, Any]],
    base_current_rows: Sequence[Mapping[str, Any]],
    base_candidate_ids: set[str],
    current_ids: set[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    merged_rows = list(merge_result["scene_rows"])
    metadata = expanded_metadata(base_metadata, merged_rows)
    candidate_rows = [
        merged_candidate_row(row)
        for row in merged_rows
        if row.get("entry_evidence_complete")
        and row.get("floor") is not None
        and row.get("static_content_known")
        and not row.get("content_conflict")
        and not row.get("identity_conflict")
    ]
    new_candidate_rows = [
        row for row in candidate_rows if str(row["scene_id"]) not in base_candidate_ids
    ]
    static_rows = [
        row
        for row in candidate_rows
        if any(
            merged["scene_id"] == row["scene_id"]
            and merged["static_content_passed"]
            for merged in merged_rows
        )
    ]
    runtime_rows = [
        row
        for row in candidate_rows
        if any(
            merged["scene_id"] == row["scene_id"]
            and merged["actual_run_verified"]
            for merged in merged_rows
        )
    ]
    formal_rows = [
        row
        for row in candidate_rows
        if any(
            merged["scene_id"] == row["scene_id"]
            and merged["formal_manifest"]
            for merged in merged_rows
        )
    ]

    def make_layer(layer_id: str, description: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return scene_layer(layer_id, description, rows, metadata, rows)

    candidate_graph = merged_dependency_graph(merged_rows, current_ids)
    expanded_yields = candidate_yields(candidate_rows, base_current_rows)
    expanded_priorities = build_dynamic_priorities(candidate_rows, base_current_rows, candidate_graph)
    base_group_ids = set(base_metadata)
    candidate_group_ids = {str(row["group_id"]) for row in candidate_rows}
    # 这里使用原始全部 group 集合；不要用 candidate 行数量替代 run 去重。
    new_group_ids = candidate_group_ids - base_group_ids
    merged_candidate_group_ids = candidate_group_ids
    expanded = {
        "status": "final_external_inputs_merged",
        "counts": {
            "merged_entry_evidence_complete_scene_count": len(candidate_rows),
            "merged_entry_evidence_complete_run_count": len(merged_candidate_group_ids),
            "new_entry_evidence_complete_scene_count_vs_old_257": len(new_candidate_rows),
            "new_entry_evidence_complete_run_count_vs_original_run_groups": len(new_group_ids),
            "new_scene_ids": sorted(str(row["scene_id"]) for row in new_candidate_rows),
            "static_content_passed_scene_count": len(static_rows),
            "actual_run_verified_scene_count": len(runtime_rows),
            "formal_manifest_scene_count": len(formal_rows),
            "current_99_scene_count_unchanged": len(base_current_rows),
        },
        "layers": {
            "merged_entry_evidence_complete": make_layer(
                "merged_entry_evidence_complete",
                "修复输入合并后，入口A证据完整且无身份/内容冲突的候选",
                candidate_rows,
            ),
            "merged_static_content_passed": make_layer(
                "merged_static_content_passed",
                "静态内容检查通过；不等于实际运行或正式manifest",
                static_rows,
            ),
            "merged_actual_run_verified": make_layer(
                "merged_actual_run_verified",
                "有实际运行记录；开发探针不自动升级正式准入",
                runtime_rows,
            ),
            "merged_formal_manifest": make_layer(
                "merged_formal_manifest",
                "外部输入明确标记已进入正式manifest的场景",
                formal_rows,
            ),
        },
        "candidate_yields": expanded_yields,
        "dependency_graph": candidate_graph,
        "merge_summary": merge_result["summary"],
        "final_manifest_unchanged": True,
        "eval_seeds_unchanged": True,
        "policy_outcomes_not_used_for_selection": True,
    }
    return expanded, expanded_priorities, candidate_graph


def dynamic_priority_risk(support_atoms: Sequence[str]) -> str:
    categories = set()
    if any(atom.startswith("card:") for atom in support_atoms):
        categories.add("卡牌数值/升级/观测")
    if any(atom.startswith("potion:") for atom in support_atoms):
        categories.add("药水库存/目标/随机或自动生成")
    if len(support_atoms) > 1:
        categories.add("联合依赖闭包")
    return "；".join(sorted(categories)) + "需在静态准入前逐项核验"


def dynamic_priority_requirements(support_atoms: Sequence[str]) -> tuple[list[str], list[str], list[str]]:
    observations = [
        "保留每个场景完整入口A牌组副本、升级、HP/maxHP/gold、遗物和药水，不使用最终牌组回填",
    ]
    actions = [
        "为新增实体更新版本化 registry、观察字段和原生 action_mask；未知实体不得映射为PAD",
    ]
    capacity = [
        "从这些精确场景的完整牌组与所有可达生成/复制/分裂路径证明容量，超界前拒绝，不静默丢字段",
    ]
    if any(atom.startswith("card:") for atom in support_atoms):
        observations.append("逐卡核验可见动态数值、状态、目标类型及升级行为")
    if any(atom.startswith("potion:") for atom in support_atoms):
        observations.append("逐瓶核对库存多重集、槽位容量、获得/使用/丢弃时序和随机生成结果")
    if len(support_atoms) > 1:
        actions.append("只有全部依赖同时表达后才能入场；二次选择不能由后端默认代选")
        capacity.append("联合场景的生成实体、牌区和临时ID上界必须整体验收")
    return observations, actions, capacity


def build_dynamic_priorities(
    candidate_rows: Sequence[Mapping[str, Any]],
    current_rows: Sequence[Mapping[str, Any]],
    graph: Mapping[str, Any],
) -> dict[str, Any]:
    """外部输入就绪时按新候选动态排序，不复用旧的17/20/4常量。"""

    yields = candidate_yields(candidate_rows, current_rows)
    rejected = [row for row in candidate_rows if row.get("content_admission_status") != "accepted"]
    candidate_group_count = len({str(row["group_id"]) for row in candidate_rows})
    single_items = [
        item
        for item in yields["single_implementation_items"]
        if item["exact_single_dependency_scene_count"] > 0
    ]
    joint_items = [
        item
        for item in yields["minimal_joint_dependencies"]
        if item["minimal_dependency_scene_count"] > 0
    ]
    proposals: list[tuple[str, dict[str, Any]]] = []
    if single_items:
        proposals.append(("dynamic-single-1", set(single_items[0]["support_atoms"])))
    if joint_items:
        proposals.append(("dynamic-joint-1", set(joint_items[0]["support_atoms"])))

    all_atoms = sorted({atom for row in rejected for atom in content_atoms(row)})
    greedy_support: set[str] = set()
    for _ in range(min(4, len(all_atoms))):
        before = yield_metrics(
            rejected,
            greedy_support,
            current_rows,
            len(candidate_rows),
            candidate_group_count,
        )["scene_count"]
        choices = []
        for atom in all_atoms:
            if atom in greedy_support:
                continue
            metrics = yield_metrics(
                rejected,
                greedy_support | {atom},
                current_rows,
                len(candidate_rows),
                candidate_group_count,
            )
            choices.append((metrics["scene_count"] - before, atom))
        if not choices:
            break
        marginal, atom = max(choices, key=lambda value: (value[0], value[1]))
        if marginal <= 0:
            break
        greedy_support.add(atom)
    if greedy_support:
        proposals.append(("dynamic-greedy-coverage", greedy_support))

    unique_proposals: list[tuple[str, set[str]]] = []
    seen: set[tuple[str, ...]] = set()
    for name, support in proposals:
        key = tuple(sorted(support))
        if key and key not in seen:
            seen.add(key)
            unique_proposals.append((name, support))
    dynamic_batches = []
    for name, support in unique_proposals[:3]:
        gain = yield_metrics(
            rejected,
            support,
            current_rows,
            len(candidate_rows),
            candidate_group_count,
        )
        observations, actions, capacity = dynamic_priority_requirements(gain["support_atoms"])
        dynamic_batches.append(
            build_priority(
                name,
                gain,
                "expanded_evidence_complete_candidate",
                dynamic_priority_risk(gain["support_atoms"]),
                observations,
                actions,
                capacity,
                [
                    "全部精确scene_id的依赖、内容、入口A、容量、动作和观测回归通过",
                    "静态通过、实际运行通过和正式manifest状态分别记录，不能互相升级",
                    "冲突候选保持拒绝并保留全部来源变体",
                ],
                "由修复后候选池动态计算；不使用旧批次名称、牌名频次或策略胜率。",
            )
        )
    dynamic_batches.sort(
        key=lambda batch: (
            -batch["projected_complete_scene_gain"]["scene_count"],
            batch["projected_complete_scene_gain"]["support_atoms"],
        )
    )
    source_gate = source_potential_yields(graph)
    return {
        "schema": PRIORITY_SCHEMA,
        "mode": "expanded_dynamic",
        "baseline": {
            "current_executable_scene_count": len(current_rows),
            "current_executable_run_count": len({str(row["group_id"]) for row in current_rows}),
            "baseline_scene_count": 99,
            "actual_net_new_scene_count_vs_baseline_99": 0,
            "current_99_all_development_integration_checked": True,
        },
        "ordering": {
            "scene_gain_rank_in_dynamic_candidates": [batch["id"] for batch in dynamic_batches],
            "recommended_execution_order_after_contract_review": [batch["id"] for batch in dynamic_batches],
            "basis": [
                "修复后证据完整候选的整场闭包收益",
                "按scene_id和canonical run identity去重后的新run、楼层、遭遇和内容增量",
                "动作/观测/容量风险与冲突状态",
            ],
            "not_used": ["旧17/20/4批次", "牌名频次", "RuleAgent胜率", "PPO胜率", "探针成功率"],
        },
        "mandatory_source_evidence_gate": {
            "id": "source-prefix-and-elite-evidence-gate",
            "potential_only": True,
            "potential": source_gate,
            "definite_complete_scene_gain": 0,
            "reason": "来源不完整或未知燃烧精英不能进入确定收益。",
        },
        "recommended_batches": dynamic_batches,
        "external_input_dependency": "修复后的前缀候选、精英交叉审计、期望SHA256及无冲突合并均需满足后才可作为最终统计。",
    }


def source_descriptor_bundle(
    input_files: Mapping[str, tuple[Path, bytes]],
    index: Mapping[str, Any],
) -> dict[str, Any]:
    descriptors = {
        name: file_descriptor(path, raw)
        for name, (path, raw) in input_files.items()
    }
    archive_path = ROOT / "reference/public-run-corpus/matiger-fixed.zip"
    if archive_path.exists():
        archive_raw = archive_path.read_bytes()
        descriptors["raw_public_archive"] = file_descriptor(archive_path, archive_raw)
        archive_status = "local_hash_verified"
        archive_hash_matches = sha256_bytes(archive_raw) == str(index.get("archive_sha256"))
    else:
        archive_status = "not_available"
        archive_hash_matches = None
    return {
        "public_repository": "MaT1g3R/Slay-the-Spire-data",
        "fixed_commit": index.get("commit"),
        "source_url": index.get("source_url"),
        "archive_sha256_declared": index.get("archive_sha256"),
        "archive_status": archive_status,
        "archive_hash_matches_declared": archive_hash_matches,
        "raw_archive_policy": "原始公开数据留在ignored reference；本分析不从最终master_deck推导入口卡组",
        "input_files": descriptors,
        "audit_implementation_sha256": index.get("implementation_sha256"),
        "catalog_sha256": index.get("catalog_sha256"),
        "split_policy_declared": index.get("split_policy"),
    }


def analyze(
    index_path: Path | None = None,
    manifest_path: Path | None = None,
    contract_path: Path | None = None,
    implementation_report_path: Path | None = None,
    integration_path: Path | None = None,
    prefix_candidates_path: Path | None = None,
    prefix_sha256: str | None = None,
    elite_audit_path: Path | None = None,
    elite_sha256: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    index_path = index_path or ROOT / "docs/m2-corpus-index.json"
    manifest_path = manifest_path or ROOT / "docs/m2-public-scene-manifest.json"
    contract_path = contract_path or ROOT / "sts/env/public-battle-contract.json"
    implementation_report_path = implementation_report_path or ROOT / "docs/public-battle-implementation.md"
    integration_path = integration_path or ROOT / "reference/public-scene-integration.json"

    index, index_raw = read_json(index_path)
    manifest, manifest_raw = read_json(manifest_path)
    contract, contract_raw = read_json(contract_path)
    validate_inputs(index, manifest, contract)

    input_files: dict[str, tuple[Path, bytes]] = {
        "corpus_index": (index_path, index_raw),
        "scene_manifest": (manifest_path, manifest_raw),
        "public_battle_contract": (contract_path, contract_raw),
    }
    implementation_report = None
    if implementation_report_path.exists():
        implementation_report = implementation_report_path.read_text(encoding="utf-8")
        input_files["implementation_report"] = (
            implementation_report_path,
            implementation_report_path.read_bytes(),
        )
    integration = None
    if integration_path.exists():
        integration, integration_raw = read_json(integration_path)
        input_files["development_integration"] = (integration_path, integration_raw)

    external_loaded: list[dict[str, Any]] = []
    if prefix_candidates_path is not None:
        external_loaded.append(
            load_external_input(prefix_candidates_path, prefix_sha256, "prefix_candidates")
        )
    if elite_audit_path is not None:
        external_loaded.append(
            load_external_input(elite_audit_path, elite_sha256, "elite_audit")
        )
    for external in external_loaded:
        input_files[f"{external['kind']}_input"] = (
            external["path_obj"],
            external["raw"],
        )

    groups = index["groups"]
    index_scenes = index["scenes"]
    manifest_scenes = manifest["scenes"]
    manifest_by_id = {str(scene["scene_id"]): scene for scene in manifest_scenes}
    metadata, grouped_scenes = common_group_metadata(
        groups,
        index_scenes,
        index["summary"]["ascensions"],
    )
    run_rows = build_run_rows(groups, metadata, grouped_scenes)
    first_feature_rows = []
    for group in groups:
        group_id = str(group["group_id"])
        first_scene = min(
            grouped_scenes[group_id],
            key=lambda row: (int(row["floor"]), str(row["scene_id"])),
        )
        if entry_candidate(first_scene) is not None:
            first_feature_rows.append(first_scene)

    current_rows = [
        scene
        for scene in manifest_scenes
        if str(scene.get("content_admission_status")) == "accepted"
    ]
    current_ids = {str(scene["scene_id"]) for scene in current_rows}
    candidate_rows = manifest_scenes

    layer_all_runs = run_layer(
        groups,
        run_rows,
        index_scenes,
        metadata,
        first_feature_rows,
    )
    layer_all_combat = scene_layer(
        "all_act1_combat_rows",
        "第一幕目标楼层全部公开战斗记录；没有 candidate 的行不补入口卡组",
        index_scenes,
        metadata,
        [scene for scene in index_scenes if entry_candidate(scene) is not None],
    )
    layer_candidates = scene_layer(
        "rule_constructible_candidates",
        "按 public-derived-standard-v1 有来源/前缀证据的完整规则候选；历史精确 mod 等价仍未验证",
        candidate_rows,
        metadata,
        candidate_rows,
    )
    layer_current = scene_layer(
        "current_99_executable",
        "manifest 内容准入 accepted 的当前99场；后端实际集成证据单列且不是正式评估",
        current_rows,
        metadata,
        current_rows,
    )

    graph = blocker_dependency_graph(index_scenes, manifest_by_id, current_ids)
    yields = candidate_yields(manifest_scenes, current_rows)
    potential = source_potential_yields(graph)
    priorities = build_priorities(manifest_scenes, current_rows, graph)
    integration_result = integration_check(
        integration,
        current_ids,
        manifest_sha256=sha256_bytes(manifest_raw),
        contract_sha256=sha256_bytes(contract_raw),
    )

    external_merge_result: dict[str, Any] | None = None
    expanded = None
    expanded_priorities = None
    expanded_graph = None
    external_input_summaries = []
    if external_loaded:
        for external in external_loaded:
            external_input_summaries.append(
                {
                    key: value
                    for key, value in external.items()
                    if key not in {"data", "raw", "path_obj"}
                }
            )
        runtime_verified_scene_ids = set()
        if integration is not None:
            runtime_verified_scene_ids = {
                str(record.get("scene_id"))
                for record in integration.get("records", [])
                if isinstance(record, Mapping)
                and record.get("status") == "completed"
                and record.get("scene_id") is not None
            }
        external_merge_result = merge_external_inputs(
            index_scenes,
            manifest_scenes,
            groups,
            external_loaded,
            runtime_verified_scene_ids=runtime_verified_scene_ids,
        )
        required_kinds = {"prefix_candidates", "elite_audit"}
        present_kinds = {str(item["kind"]) for item in external_loaded}
        hash_ready = all(bool(item["hash_verified"]) for item in external_loaded)
        final_ready = required_kinds <= present_kinds and hash_ready
        blockers = []
        if "prefix_candidates" not in present_kinds:
            blockers.append("PREFIX_CANDIDATES_INPUT_MISSING")
        if "elite_audit" not in present_kinds:
            blockers.append("ELITE_AUDIT_INPUT_MISSING")
        for item in external_loaded:
            if not item["hash_verified"]:
                blockers.append(item["kind"] + "_SHA256_MISSING_OR_MISMATCH")
        external_merge_result["summary"].update(
            {
                "external_inputs": external_input_summaries,
                "final_statistics_ready": final_ready,
                "final_statistics_blockers": sorted(blockers),
            }
        )
        if final_ready:
            expanded, expanded_priorities, expanded_graph = expanded_analysis(
                external_merge_result,
                metadata,
                current_rows,
                {str(scene["scene_id"]) for scene in manifest_scenes},
                current_ids,
            )
            priorities = expanded_priorities
        else:
            priorities["mode"] = "baseline_with_external_inputs_pending"
            priorities["external_input_dependency"] = {
                "final_statistics_ready": False,
                "blockers": sorted(blockers),
                "not_recomputed": True,
            }

    source = source_descriptor_bundle(input_files, index)
    if external_input_summaries:
        source["external_inputs"] = external_input_summaries
    if implementation_report is not None:
        source["implementation_report_assertions"] = {
            "mentions_99_executable": "99场均可执行" in implementation_report,
            "mentions_development_integration": "开发集成" in implementation_report,
            "mentions_not_formal_gate": "不作Gate2" in implementation_report,
            "mentions_run_group_statistics_pending": "按run关联组" in implementation_report,
        }

    source_collections = sorted({str(row["source_collection"]) for row in run_rows})
    current_group_ids = {str(row["group_id"]) for row in current_rows}
    candidate_group_ids = {str(row["group_id"]) for row in candidate_rows}
    all_group_ids = {str(row["group_id"]) for row in run_rows}
    source_selection = []
    for collection in source_collections:
        total_groups = {row["group_id"] for row in run_rows if row["source_collection"] == collection}
        candidate_groups = {
            row["group_id"]
            for row in run_rows
            if row["source_collection"] == collection and row["group_id"] in candidate_group_ids
        }
        current_groups = {
            row["group_id"]
            for row in run_rows
            if row["source_collection"] == collection and row["group_id"] in current_group_ids
        }
        source_selection.append(
            {
                "source_collection": collection,
                "all_independent_run_count": len(total_groups),
                "rule_candidate_run_count": len(candidate_groups),
                "current_executable_run_count": len(current_groups),
                "rule_candidate_run_rate": len(candidate_groups) / len(total_groups),
                "current_executable_run_rate": len(current_groups) / len(total_groups),
                "player_identity_observed": False,
            }
        )

    all_scene_tiers = Counter(encounter_tier(str(scene["encounter_label"])) for scene in index_scenes)
    current_scene_tiers = Counter(encounter_tier(str(scene["encounter_label"])) for scene in current_rows)
    analysis = {
        "schema": SCHEMA,
        "analysis_version": 1,
        "source": source,
        "policies": {
            "source_admission_policy": "public-derived-standard-v1",
            "historical_rules_equivalence": "unverified",
            "entry_A": "pre_combat_initialization / before_destination_room_entry",
            "scene_weight": "逐场行权重1/N",
            "run_balanced_weight": "同层每个run-group总权重为1，再除以run-group数；不是总体抽样校正",
            "deduplication": "group_id由play_id、seed_played、raw SHA连接；aliases不重复计run；同run全部楼层保持同组",
            "final_master_deck_used": False,
            "strategy_outcome_used": False,
        },
        "layer_counts": {
            "all_independent_runs": {
                "raw_file_count": sum(len(group.get("aliases", [])) for group in groups),
                "independent_run_count": len(all_group_ids),
                "linked_act1_combat_row_count": len(index_scenes),
            },
            "all_act1_combat_rows": {
                "scene_count": len(index_scenes),
                "independent_run_count": len({str(scene["group_id"]) for scene in index_scenes}),
                "encounter_tier_scene_counts": dict(sorted(all_scene_tiers.items())),
            },
            "rule_constructible_candidates": {
                "scene_count": len(candidate_rows),
                "independent_run_count": len(candidate_group_ids),
            },
            "current_99_executable": {
                "scene_count": len(current_rows),
                "independent_run_count": len(current_group_ids),
                "encounter_tier_scene_counts": dict(sorted(current_scene_tiers.items())),
                "actual_net_new_scene_count_vs_original_99": 0,
            },
        },
        "candidate_counts": {
            "raw_researchable_combat_rows": {
                "scene_count": len(index_scenes),
                "independent_run_count": len(all_group_ids),
                "definition": "固定公开库按角色筛选后、第一幕目标楼层的全部战斗记录；入口字段不完整也保留研究候选身份",
            },
            "evidence_complete_rule_candidates": {
                "scene_count": len(candidate_rows),
                "independent_run_count": len(candidate_group_ids),
                "definition": "candidate 非空且入口A字段完整、source blockers为空的public-derived-standard-v1规则派生候选",
            },
            "current_backend_accessible_scenes": {
                "scene_count": len(current_rows),
                "independent_run_count": len(current_group_ids),
                "definition": "manifest content_admission_status=accepted，并以当前开发集成记录单列核对可执行性",
            },
            "actual_net_new_scene_count_vs_original_99": 0,
        },
        "layers": {
            "all_independent_runs": layer_all_runs,
            "all_act1_combat_rows": layer_all_combat,
            "rule_constructible_candidates": layer_candidates,
            "current_99_executable": layer_current,
        },
        "source_selection_bias": {
            "by_source_collection": source_selection,
            "all_source_collections_are_path_labels_not_player_population": True,
            "player_identity_field_available": False,
            "population_weighting_claim": False,
        },
        "dependency_summary": graph["summary"],
        "candidate_yields": yields,
        "source_potential_yields": potential,
        "backend_integration": integration_result,
        "cross_source_dedup_audit": {
            "raw_file_count": sum(len(group.get("aliases", [])) for group in groups),
            "independent_run_count": len(index["groups"]),
            "duplicate_alias_file_count": int(index["summary"]["duplicate_alias_files"]),
            "conflicting_groups": int(index["summary"]["conflicting_groups"]),
            "groups_with_multiple_aliases": sum(len(group.get("aliases", [])) > 1 for group in groups),
            "cross_collection_alias_groups": 0,
            "play_id_duplicate_across_groups": False,
            "seed_played_duplicate_across_groups": False,
            "raw_sha_duplicate_across_groups": False,
            "risk": [
                "当前 identity token 没有发现跨group重复，但同一run的别名路径若未连接会放大场景数；未来来源必须继续以完整run连接。",
                "没有玩家身份/总体抽样框，source_collection 只能作来源标签，不能做全体玩家分布推断。",
            ],
        },
        "sampling_plan": {
            "current_split_unchanged": True,
            "current_99_touched_by_development_integration": True,
            "reserved_eval_warning": "当前99场都做过开发集成检查；原 research reserved-eval 标签本身不保证这些场景仍是未接触保留数据。",
            "future_new_source_protocol": [
                "先按play_id/seed/raw SHA和aliases去重，再以完整run为split unit；同run所有楼层保持同组。",
                "冻结来源commit、场景入口A字段、contract/action/observation/serialization版本和环境seed分配，再开始策略调试。",
                "保持现有80/10/10研究预划分规则只作为数据管线标签，不回写现有split；在各层数量足够时按source/build/floor/tier/encounter做组级平衡抽样。",
                "训练/开发场景在每个run内按1/n_scene取样以防长run放大；reserved-eval整组隔离，不能只留某个楼层。",
                "新来源若用于保留评估，必须在策略调试前冻结协议和场景清单；不把公共主播/策展样本称作全体玩家总体。",
            ],
            "source_seed_and_environment_seed": "source seed仅追溯/分组；environment seed独立且不进模型输入。",
        },
        "limitations": [
            "A候选按标准规则派生，不是历史精确回放；历史完整mod/行为等价仍unverified。",
            "第一幕战斗行的candidate缺失时，入口卡组、HP/maxHP/gold、遗物、药水均单列为未知；未使用最终master_deck补齐。",
            "规则候选和内容准入只覆盖manifest已有257/99行；来源不完整的1025行不能以某一个 blocker 解除就直接升格。",
            "当前99场后端开发集成检查不是正式Gate、不是正式保留集评估，策略结果未参与选择。",
        ],
    }
    if external_merge_result is not None:
        analysis["external_merge"] = external_merge_result["summary"]
        analysis["external_merge"]["baseline_preserved"] = True
        graph["external_merge"] = external_merge_result["summary"]
        if expanded is not None and expanded_priorities is not None and expanded_graph is not None:
            analysis["expanded"] = expanded
            graph["expanded"] = expanded_graph
            priorities = expanded_priorities
    return analysis, priorities, graph


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def distribution_map(items: Sequence[Mapping[str, Any]]) -> dict[Any, Mapping[str, Any]]:
    return {item["value"]: item for item in items}


def markdown_frequency_table(
    title: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
) -> list[str]:
    lines = [f"### {title}", "", "| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    lines.append("")
    return lines


def render_report(
    analysis: Mapping[str, Any],
    priorities: Mapping[str, Any],
    graph: Mapping[str, Any],
) -> str:
    layers = analysis["layers"]
    counts = analysis["layer_counts"]
    candidate_yield = analysis["candidate_yields"]
    current_split_distribution = distribution_map(
        layers["current_99_executable"]["distributions"]["research_split"]
    )
    current_split_scene = {
        key: item["scene_count"] for key, item in current_split_distribution.items()
    }
    current_split_groups = {
        key: item["run_count"] for key, item in current_split_distribution.items()
    }
    lines: list[str] = [
        "# 公开派生战斗场景选择偏差与扩容优先级",
        "",
        "日期：2026-09-12。分析脚本：`scripts/analyze-public-coverage.py`。本报告只做离线量化和实施建议，不修改正式环境、manifest、`eval_seeds.json`，不训练 PPO，也不运行正式保留集评估。",
        "",
        "## 结论先行",
        "",
        f"固定公开库为 **{counts['all_independent_runs']['raw_file_count']} 个原始文件 / {counts['all_independent_runs']['independent_run_count']} 个独立 run**，第一幕有 **{counts['all_act1_combat_rows']['scene_count']} 条战斗记录**。其中 {counts['rule_constructible_candidates']['scene_count']} 条可按 `public-derived-standard-v1` 形成完整入口 A 候选，当前内容准入 **{counts['current_99_executable']['scene_count']} 场 / {counts['current_99_executable']['independent_run_count']} 个 run**。本任务没有实现新场景，所以相对原99场的实际净新增为 **0**。",
        "",
        "当前准入过程明显丢失的不是单一卡牌频次，而是四个分布维度：",
        "",
        "- 楼层：当前99场只在 floor 1–5；完整第一幕记录有 floor 6–14 的战斗，但证据完整候选没有一场超过 floor 5。",
        "- 遭遇层级：第一幕记录有 425 条精英战斗，当前99场为 0；普通遭遇也只保留 6 个标签。",
        "- 构筑内容：规则候选有 72 个初始卡类、160 个入口牌组多重集、18 个带升级场景；当前99场只有 22 个卡类、27 个多重集、7 个升级场景。",
        "- 消耗品/玩家来源：候选非空药水比例为 75/257，当前99场为 7/99；四个来源路径标签的当前 run 选择率为 42%–100%，且没有玩家身份字段，不能解释为总体玩家分布。",
        "",
        "卡牌实现不能补回 floor 6–14、精英和未知事件/商店前缀；这些必须先解决来源证据闭包。另一方面，在证据完整的257条候选内，单独支持 `Anger` 虽有较高潜在收益，但 M1 已登记复制路径延期；因此建议把“完整场景收益”和“动作/容量风险”同时报告，不按卡牌出现次数或策略胜率决定。",
        "",
        "## 分母、权重与四层比较",
        "",
        "A 层以独立 run 为单位；B/C/D 层以战斗场景行（`scene_id`）为单位。逐场描述统计中每行权重为 `1/N`；run 平衡统计在同一层内让每个 `group_id` 的总权重为1，再除以独立 run 数。这是防止同一 run 多楼层放大，不是对全体玩家总体的统计加权。",
        "",
        "| 层 | 单位 | 分母 | 独立 run | 入口 A 完整字段 | 场景权重 |",
        "|---|---|---:|---:|---:|---:|",
        f"| A 固定公开库 | run | {counts['all_independent_runs']['raw_file_count']} 原始文件去重 | {counts['all_independent_runs']['independent_run_count']} | {layers['all_independent_runs']['entry']['field_availability']['feature_row_count']}/{layers['all_independent_runs']['entry']['field_availability']['denominator_row_count']} 个首战行 | run `1/157`；关联战斗行另算 |",
        f"| B 第一幕全部战斗 | scene | {counts['all_act1_combat_rows']['scene_count']} | {counts['all_act1_combat_rows']['independent_run_count']} | {layers['all_act1_combat_rows']['entry']['field_availability']['feature_row_count']}/{layers['all_act1_combat_rows']['entry']['field_availability']['denominator_row_count']} | `1/1282` |",
        f"| C 规则候选 | scene | {counts['rule_constructible_candidates']['scene_count']} | {counts['rule_constructible_candidates']['independent_run_count']} | {layers['rule_constructible_candidates']['entry']['field_availability']['feature_row_count']}/{layers['rule_constructible_candidates']['entry']['field_availability']['denominator_row_count']} | `1/257` |",
        f"| D 当前可执行 | scene | {counts['current_99_executable']['scene_count']} | {counts['current_99_executable']['independent_run_count']} | {layers['current_99_executable']['entry']['field_availability']['feature_row_count']}/{layers['current_99_executable']['entry']['field_availability']['denominator_row_count']} | `1/99` |",
        "",
        "A 层的“入口 A 完整字段”是每个 run 的第一条第一幕战斗行是否有 candidate；不是把一个后期候选牌组复制到整个 run。B 层缺失行的入口卡组、升级、HP/maxHP/gold、遗物和药水均保持未知。脚本的 `final_master_deck_used=false` 是硬约束。",
        f"按任务要求单列三种候选分母：原始可研究战斗候选 **{analysis['candidate_counts']['raw_researchable_combat_rows']['scene_count']} 场/{analysis['candidate_counts']['raw_researchable_combat_rows']['independent_run_count']} run**；证据完整规则候选 **{analysis['candidate_counts']['evidence_complete_rule_candidates']['scene_count']} 场/{analysis['candidate_counts']['evidence_complete_rule_candidates']['independent_run_count']} run**；当前后端可接入 **{analysis['candidate_counts']['current_backend_accessible_scenes']['scene_count']} 场/{analysis['candidate_counts']['current_backend_accessible_scenes']['independent_run_count']} run**。",
        "",
    ]

    all_scene_dist = layers["all_act1_combat_rows"]["distributions"]
    cand_dist = layers["rule_constructible_candidates"]["distributions"]
    current_dist = layers["current_99_executable"]["distributions"]
    floors = sorted(
        {item["value"] for item in all_scene_dist["floor"]}
        | {item["value"] for item in cand_dist["floor"]}
        | {item["value"] for item in current_dist["floor"]},
        key=sort_value,
    )
    all_floor = distribution_map(all_scene_dist["floor"])
    cand_floor = distribution_map(cand_dist["floor"])
    cur_floor = distribution_map(current_dist["floor"])
    lines += markdown_frequency_table(
        "楼层选择偏差（逐场计数 + 当前保留比例）",
        ["floor", "B 全部战斗", "C 候选", "D 当前99", "D/B", "D run平衡share"],
        [
            [
                floor,
                all_floor.get(floor, {}).get("scene_count", 0),
                cand_floor.get(floor, {}).get("scene_count", 0),
                cur_floor.get(floor, {}).get("scene_count", 0),
                pct(cur_floor.get(floor, {}).get("scene_count", 0) / all_floor[floor]["scene_count"])
                if floor in all_floor
                else "0.00%",
                pct(cur_floor.get(floor, {}).get("run_balanced_share", 0.0)),
            ]
            for floor in floors
        ],
    )

    all_enc = distribution_map(all_scene_dist["encounter_label"])
    cand_enc = distribution_map(cand_dist["encounter_label"])
    cur_enc = distribution_map(current_dist["encounter_label"])
    encounters = sorted(all_enc, key=sort_value)
    lines += markdown_frequency_table(
        "遭遇选择偏差（精英/未知事件不折算为普通）",
        ["遭遇", "B 全部战斗", "C 候选", "D 当前99", "D/B"],
        [
            [
                encounter,
                all_enc[encounter]["scene_count"],
                cand_enc.get(encounter, {}).get("scene_count", 0),
                cur_enc.get(encounter, {}).get("scene_count", 0),
                pct(cur_enc.get(encounter, {}).get("scene_count", 0) / all_enc[encounter]["scene_count"]),
            ]
            for encounter in encounters
        ],
    )

    all_tier = distribution_map(all_scene_dist["encounter_tier"])
    cand_tier = distribution_map(cand_dist["encounter_tier"])
    cur_tier = distribution_map(current_dist["encounter_tier"])
    lines += markdown_frequency_table(
        "遭遇层级总量",
        ["层级", "B 全部战斗", "C 候选", "D 当前99"],
        [
            [
                tier,
                all_tier.get(tier, {}).get("scene_count", 0),
                cand_tier.get(tier, {}).get("scene_count", 0),
                cur_tier.get(tier, {}).get("scene_count", 0),
            ]
            for tier in ("normal", "elite", "unknown_or_event")
        ],
    )

    source_rows = []
    for item in analysis["source_selection_bias"]["by_source_collection"]:
        source_rows.append(
            [
                item["source_collection"],
                item["all_independent_run_count"],
                item["rule_candidate_run_count"],
                pct(item["rule_candidate_run_rate"]),
                item["current_executable_run_count"],
                pct(item["current_executable_run_rate"]),
            ]
        )
    lines += markdown_frequency_table(
        "来源路径标签与 run 选择率",
        ["source_collection（路径标签）", "A 全部run", "C候选run", "C/A", "D当前run", "D/A"],
        source_rows,
    )
    lines += [
        "这里没有把 `source_collection` 命名成玩家。固定公开库只提供路径标签；`player_identity_field_available=false`。例如 `lose-all-gold-max-hp-sample` 的当前选择率为100%，其余三个路径标签约42%–47%，这是准入流程的选择结果，不是玩家总体比例。",
        "",
    ]

    all_build = distribution_map(layers["all_independent_runs"]["distributions"]["source_build"])
    b_build = distribution_map(layers["all_act1_combat_rows"]["distributions"]["source_build"])
    c_build = distribution_map(layers["rule_constructible_candidates"]["distributions"]["source_build"])
    d_build = distribution_map(layers["current_99_executable"]["distributions"]["source_build"])
    build_values = sorted(
        set(all_build) | set(b_build) | set(c_build) | set(d_build),
        key=sort_value,
    )
    lines += markdown_frequency_table(
        "来源 build 选择偏差",
        ["build", "A 全部run", "B 全部战斗行", "C候选行", "D当前99", "D/B"],
        [
            [
                build,
                all_build.get(build, {}).get("scene_count", 0),
                b_build.get(build, {}).get("scene_count", 0),
                c_build.get(build, {}).get("scene_count", 0),
                d_build.get(build, {}).get("scene_count", 0),
                pct(
                    d_build.get(build, {}).get("scene_count", 0)
                    / b_build[build]["scene_count"]
                )
                if build in b_build
                else "0.00%",
            ]
            for build in build_values
        ],
    )
    ascension_rows = distribution_map(
        layers["all_independent_runs"]["distributions"]["ascension"]
    )
    ascension_text = ", ".join(
        f"A{value}:{item['scene_count']} run"
        for value, item in sorted(ascension_rows.items(), key=lambda pair: sort_value(pair[0]))
    )
    lines += [
        f"进阶/角色维度：固定公开库的来源筛选角色为 IRONCLAD；A 层进阶为 {ascension_text or 'UNKNOWN'}，B/C/D 均继承同一来源进阶字段，没有观察到较低进阶。因此当前99场不能支持跨进阶泛化。",
        "",
    ]

    lines += markdown_frequency_table(
        "入口内容字段统计（只在实际有 candidate 的入口 A 行上计算）",
        ["层/入口字段分母", "牌组大小分布", "多重集数", "升级场景", "初始卡类", "遗物类", "非空药水", "药水类"],
        [
            [
                "A 首战 candidate 118",
                ", ".join(f"{int(item['value'])}:{item['scene_count']}" for item in layers["all_independent_runs"]["entry"]["stats"]["deck"]["size_distribution"]),
                layers["all_independent_runs"]["entry"]["stats"]["deck"]["unique_multiset_count"],
                layers["all_independent_runs"]["entry"]["stats"]["deck"]["upgraded_scene_count"],
                layers["all_independent_runs"]["entry"]["stats"]["deck"]["unique_initial_card_class_count"],
                layers["all_independent_runs"]["entry"]["stats"]["relics"]["unique_class_count"],
                f"{layers['all_independent_runs']['entry']['stats']['potions']['nonempty_scene_count']}/{layers['all_independent_runs']['entry']['stats']['denominator']} ({pct(layers['all_independent_runs']['entry']['stats']['potions']['nonempty_scene_share'])})",
                layers["all_independent_runs"]["entry"]["stats"]["potions"]["unique_class_count"],
            ],
            [
                "B 有 candidate 257/1282",
                ", ".join(f"{int(item['value'])}:{item['scene_count']}" for item in layers["all_act1_combat_rows"]["entry"]["stats"]["deck"]["size_distribution"]),
                layers["all_act1_combat_rows"]["entry"]["stats"]["deck"]["unique_multiset_count"],
                layers["all_act1_combat_rows"]["entry"]["stats"]["deck"]["upgraded_scene_count"],
                layers["all_act1_combat_rows"]["entry"]["stats"]["deck"]["unique_initial_card_class_count"],
                layers["all_act1_combat_rows"]["entry"]["stats"]["relics"]["unique_class_count"],
                f"{layers['all_act1_combat_rows']['entry']['stats']['potions']['nonempty_scene_count']}/{layers['all_act1_combat_rows']['entry']['stats']['denominator']} ({pct(layers['all_act1_combat_rows']['entry']['stats']['potions']['nonempty_scene_share'])})",
                layers["all_act1_combat_rows"]["entry"]["stats"]["potions"]["unique_class_count"],
            ],
            [
                "C 规则候选 257",
                ", ".join(f"{int(item['value'])}:{item['scene_count']}" for item in layers["rule_constructible_candidates"]["entry"]["stats"]["deck"]["size_distribution"]),
                layers["rule_constructible_candidates"]["entry"]["stats"]["deck"]["unique_multiset_count"],
                layers["rule_constructible_candidates"]["entry"]["stats"]["deck"]["upgraded_scene_count"],
                layers["rule_constructible_candidates"]["entry"]["stats"]["deck"]["unique_initial_card_class_count"],
                layers["rule_constructible_candidates"]["entry"]["stats"]["relics"]["unique_class_count"],
                f"{layers['rule_constructible_candidates']['entry']['stats']['potions']['nonempty_scene_count']}/{layers['rule_constructible_candidates']['entry']['stats']['denominator']} ({pct(layers['rule_constructible_candidates']['entry']['stats']['potions']['nonempty_scene_share'])})",
                layers["rule_constructible_candidates"]["entry"]["stats"]["potions"]["unique_class_count"],
            ],
            [
                "D 当前99",
                ", ".join(f"{int(item['value'])}:{item['scene_count']}" for item in layers["current_99_executable"]["entry"]["stats"]["deck"]["size_distribution"]),
                layers["current_99_executable"]["entry"]["stats"]["deck"]["unique_multiset_count"],
                layers["current_99_executable"]["entry"]["stats"]["deck"]["upgraded_scene_count"],
                layers["current_99_executable"]["entry"]["stats"]["deck"]["unique_initial_card_class_count"],
                layers["current_99_executable"]["entry"]["stats"]["relics"]["unique_class_count"],
                f"{layers['current_99_executable']['entry']['stats']['potions']['nonempty_scene_count']}/{layers['current_99_executable']['entry']['stats']['denominator']} ({pct(layers['current_99_executable']['entry']['stats']['potions']['nonempty_scene_share'])})",
                layers["current_99_executable"]["entry"]["stats"]["potions"]["unique_class_count"],
            ],
        ],
    )
    lines += [
        "B 的 `1025/1282` 行没有入口 A candidate，因此不能用 `.run` 的最终 `master_deck` 补齐；A 首战 candidate 118 行的药水全为空是楼层/时点事实，不代表整个公开库没有药水。C 的完整候选非空药水为 `75/257=29.18%`，D 为 `7/99=7.07%`。C 的完整入口遗物仍只有5类，说明在当前证据完整候选中没有确定的新增遗物类；更多遗物收益只能列为来源缺口潜在收益。",
        "",
        "## 逐场依赖图与失败原因",
        "",
        f"依赖图在 `reference/public-distribution/dependency-graph.json` 保存了全部 **{graph['scene_count']}** 个 scene_id。每场保留原始 `source_blockers`、manifest `content_blockers`、原子依赖和类别组合。当前状态是：{graph['summary']['current_executable_scene_count']} 场可执行，{graph['summary']['evidence_complete_content_blocked_scene_count']} 场来源/入口证据完整但内容受阻，{graph['summary']['source_or_prefix_incomplete_scene_count']} 场来源/前缀仍不完整。类别频次非可加，重叠 blocker 不分别计收益。",
        "",
    ]
    top_combo_rows = [
        [
            " + ".join(item["categories"]) if item["categories"] else "none",
            item["scene_count"],
            "是（不可加）",
        ]
        for item in graph["summary"]["dependency_category_combinations"][:12]
    ]
    lines += markdown_frequency_table(
        "依赖类别组合（前12项）",
        ["类别组合", "场景数", "是否可加"],
        top_combo_rows,
    )
    top_raw_rows = [
        [item["blocker"], item["scene_count"]]
        for item in graph["summary"]["raw_blocker_frequency"][:12]
    ]
    lines += markdown_frequency_table("来源原始 blocker（前12项）", ["原始 blocker", "场景数"], top_raw_rows)
    top_content_rows = [
        [item["blocker"], item["scene_count"]]
        for item in graph["summary"]["content_blocker_frequency"][:12]
    ]
    lines += markdown_frequency_table("内容 blocker（前12项）", ["内容 blocker", "场景数"], top_content_rows)
    lines += [
        "其中证据完整候选的内容阻塞有 `154` 场涉及卡牌/升级类别，`30` 场涉及药水范围，`26` 场同时有卡牌和药水 blocker；同时有多个 blocker 的场景保留完整依赖集合。来源不完整的场景不因“识别到卡名”而进入内容收益计算。当前依赖图没有把尚未被数据证明的容量或二次选择强行添加到场景 blocker；它们在下一批建议中作为实现前置验收项单列。",
        "依赖类别清单中 `capacity_action_protocol` 与 `secondary_choice_or_copy_generation` 当前均为0条结构化数据 blocker；0只表示索引没有把它们写成已知来源阻塞，不表示后端已经支持，必须在相关批次验收时显式证明。",
        "",
        "## 证据完整候选的确定收益排序",
        "",
        "C 层257场是唯一可计算“实现内容后确定打开多少完整场景”的分母；D 当前99场先从C中扣除。单项实现只统计 blocker 原子集合恰好为该单项的场景；联合收益要求一整个依赖集合都被支持。以下收益都是 projected，尚未实现，不是当前净新增。",
        "",
    ]
    single_rows = []
    for item in candidate_yield["single_implementation_items"][:20]:
        single_rows.append(
            [
                ", ".join(item["support_atoms"]),
                item["exact_single_dependency_scene_count"],
                item["potential_scene_count_containing_atom"],
                item["new_independent_runs_vs_current_99"],
                ", ".join(item["new_encounter_labels_vs_current_99"]) or "—",
            ]
        )
    lines += markdown_frequency_table(
        "单个原子实现项（按独立可解锁完整场景数排序，前20）",
        ["实现项", "仅此依赖的场景", "包含联合依赖的潜在场景", "新增run", "新增遭遇"],
        single_rows,
    )
    combo_rows = []
    for item in candidate_yield["minimal_joint_dependencies"][:15]:
        combo_rows.append(
            [
                " + ".join(item["support_atoms"]),
                item["minimal_dependency_scene_count"],
                item["minimal_independent_run_count"],
                item["minimal_new_independent_runs_vs_current_99"],
                ", ".join(item["minimal_new_encounter_labels_vs_current_99"]) or "—",
            ]
        )
    lines += markdown_frequency_table(
        "最小联合依赖组合（前15）",
        ["联合依赖", "组合自身场景", "关联run", "新增run", "新增遭遇"],
        combo_rows,
    )
    lines += [
        f"内容 blocker 场景中有 {candidate_yield['content_overlap_scene_count']} 场需要至少两个原子依赖，其中 {candidate_yield['content_card_and_potion_overlap_scene_count']} 场同时需要卡牌和药水。不能把例如 `Anger` 的23场出现、`PowerPotion` 的7场出现直接相加；脚本用 `content_atoms(scene) <= support_atoms` 去重后才计完整收益。",
        "",
        "来源缺口的潜在收益另存 `source_potential_yields`，不进入上表的确定收益。当前证据完整候选最高 floor 为5，所以解决卡牌 blocker 的收益在 floor 维度新增仍为0；要新增 floor6–14/精英，必须先通过 source-prefix evidence gate。",
        "",
        "## 最多三个下一批建议",
        "",
        "以下三项是具体场景集合，不是“多加卡/多找数据”的泛化建议。JSON 中保存了每批全部精确 `scene_ids`、原子依赖和 projected metrics。收益排序与执行顺序分开：收益最高的批次由于当前动作协议不能直接承接，执行时仍需先过契约迁移门槛。",
        "",
    ]
    for priority in priorities["recommended_batches"]:
        gain = priority["projected_complete_scene_gain"]
        lines += [
            f"### {priority['id']}",
            "",
            f"预计完整场景收益：**{gain['scene_count']} 场 / {gain['independent_run_count']} 个关联 run**；相对当前99场新增独立 run {gain['new_independent_runs_vs_current_99']}，新增遭遇 {', '.join(gain['new_encounter_labels_vs_current_99']) or '无'}，新增 floor {', '.join(str(x) for x in gain['new_floor_values_vs_current_99']) or '无'}。",
            "",
            f"原子依赖：`{', '.join(gain['support_atoms'])}`。工程风险：{priority['engineering_risk']}",
            "",
            f"接受条件：{'；'.join(priority['acceptance_conditions'])}",
            "",
            f"本批精确场景 ID 已落盘（共{len(gain['scene_ids'])}个）：`reference/public-distribution/priority-scene-ids.json`。",
            "",
        ]
    source_gate = priorities["mandatory_source_evidence_gate"]
    lines += [
        "### 三批之外的来源证据前置门",
        "",
        f"这不是一个可以把潜在行立即加入 manifest 的实现批次。当前来源/前缀不完整为 {source_gate['potential']['source_incomplete_scene_count']} 条战斗记录、{source_gate['potential']['source_incomplete_run_count']} 个 run；其中 source/prefix 类别潜在覆盖 {next((item['potential_scene_count'] for item in source_gate['potential']['category_potential'] if item['category'] == 'source_prefix'), 0)} 条，燃烧精英类别潜在覆盖 {next((item['potential_scene_count'] for item in source_gate['potential']['category_potential'] if item['category'] == 'burning_elite_modifier'), 0)} 条。它们至少还可能带有其他 blocker，确定收益记为0。",
        "",
        "需要主 agent 决策的是：是否先登记并实施来源前缀/事件商店证据闭包，以及是否批准从当前66位动作迁移到可表达二次选择的版本。无论选择什么，都不能删除原始不支持牌/遗物/药水或把它们改成基础牌。",
        "",
        "## 关联组、去重与未来抽样",
        "",
        f"原始文件203个按 `play_id`、`seed_played`、raw SHA连接为157个 group；其中46个重复别名文件、{analysis['cross_source_dedup_audit']['conflicting_groups']}个冲突组，未发现跨group的 play_id/seed/SHA重复。别名目前都在同一来源集合内，但未来来源仍必须先做完整run连接。",
        "",
        f"当前99场按场景分布为{current_split_scene.get('train', 0)} train / {current_split_scene.get('dev', 0)} dev / {current_split_scene.get('reserved-eval', 0)} reserved-eval，按关联 group 则为{current_split_groups.get('train', 0)} / {current_split_groups.get('dev', 0)} / {current_split_groups.get('reserved-eval', 0)}；它们全部做过开发集成检查。原 `reserved-eval` 标签只反映历史研究预划分，不能证明这2场仍是未接触保留数据，也不能把当前99场回溯宣称为正式保留集。",
        "",
        "未来新来源若用于保留评估，应在策略调试前冻结来源提交、group 去重、入口A、观察/动作/序列化版本、环境 seed 分配和评估清单；split 以完整run为单位，同一run的所有楼层不拆分。训练/开发可在run内按 `1/n_scene` 平衡场景，并在样本足够时按来源、build、floor、遭遇层级/标签做组级分层；这仍不是对全体玩家总体的统计加权。source seed 只用于追溯和分组，不能进模型。",
        "",
        "## 来源、复现与边界",
        "",
        f"公开来源固定提交：`{analysis['source']['fixed_commit']}`；声明的 archive SHA256：`{analysis['source']['archive_sha256_declared']}`。输入文件、实现/契约哈希和本地 archive 校验状态写入 `reference/public-distribution/coverage-analysis.json`。入口字段证据沿用 candidate 的 `M2C-02`–`M2C-06` 记录；隐藏敌人/牌堆/RNG 为标准规则重新采样，`exact_historical_replay=false`。",
        "",
        "离线复现：",
        "",
        "```powershell",
        "python scripts/analyze-public-coverage.py",
        "python -m pytest -q tests/test_public_coverage.py",
        "```",
        "",
        "通过/未通过边界：脚本会验证99基线、257候选、66位动作契约、manifest 与 index 的候选对应关系、group/scene 唯一性；集成记录若存在，只验证99场开发集成完成性，不把胜率写入筛选逻辑。来源缺口、历史 mod 等价、正式训练/评估 ready、PPO 学习收益均保持未宣称。",
        "",
    ]
    external_merge = analysis.get("external_merge")
    if external_merge is not None:
        lines += [
            "## 修复输入合并状态",
            "",
            "这一节只有在命令显式传入 Agent 1 的前缀候选、精英交叉审计及期望 SHA256 后才会出现；旧基线统计仍保留在上文。",
            "",
        ]
        for item in external_merge.get("external_inputs", []):
            lines.append(
                f"- {item.get('kind')}: `{item.get('path')}`，实际SHA256 `{item.get('actual_sha256')}`，期望SHA256 `{item.get('expected_sha256')}`，校验 `{item.get('hash_status')}`，记录 {item.get('record_count')} 条。"
            )
        lines += [
            "",
            f"合并前最终统计就绪：`{external_merge.get('final_statistics_ready', False)}`。同 scene 重复记录 {external_merge.get('same_scene_duplicate_record_count', 0)} 条，内容冲突场景 {external_merge.get('content_conflict_scene_count', 0)}，身份冲突场景 {external_merge.get('identity_conflict_scene_count', 0)}，未知/未解析来源身份记录 {external_merge.get('unresolved_identity_record_count', 0)}。冲突不选择任一版本，未验证 hash 或缺少任一外部输入时不生成最终扩展统计。",
            "",
        ]
        expanded_report = analysis.get("expanded")
        if not external_merge.get("final_statistics_ready", False) or expanded_report is None:
            lines += [
                "Agent 1 最终文件或其 SHA256 尚未全部满足；本轮没有宣布新的场景数、楼层增量、精英增量或扩容收益。请收到最终文件和 SHA256 后重新运行命令收口。",
                "",
            ]
        else:
            expanded_counts = expanded_report["counts"]
            merge_summary = expanded_report["merge_summary"]
            lines += [
                "### 修复后合并统计（仅在输入 hash 已验证时）",
                "",
                f"合并后的入口证据完整候选为 {expanded_counts['merged_entry_evidence_complete_scene_count']} 场 / {expanded_counts['merged_entry_evidence_complete_run_count']} 个 canonical run；相对旧257候选新增 {expanded_counts['new_entry_evidence_complete_scene_count_vs_old_257']} 场。静态内容通过 {expanded_counts['static_content_passed_scene_count']} 场，实际运行验证 {expanded_counts['actual_run_verified_scene_count']} 场，正式manifest {expanded_counts['formal_manifest_scene_count']} 场；这些是独立状态，开发探针不会自动变成正式准入。",
                f"本次合并冲突/身份审计：同场重复 {merge_summary['same_scene_duplicate_record_count']}，内容冲突 {merge_summary['content_conflict_scene_count']}，身份冲突 {merge_summary['identity_conflict_scene_count']}；冲突场景没有进入确定收益。",
                "",
            ]
            expanded_layer = expanded_report["layers"]["merged_entry_evidence_complete"]
            expanded_floor = distribution_map(expanded_layer["distributions"]["floor"])
            expanded_encounter = distribution_map(expanded_layer["distributions"]["encounter_label"])
            lines += markdown_frequency_table(
                "修复后证据完整候选的楼层统计（逐场与run平衡）",
                ["floor", "scene_count", "scene_share", "run_count", "run_balanced_share"],
                [
                    [
                        value,
                        item["scene_count"],
                        pct(item["scene_share"]),
                        item["run_count"],
                        pct(item["run_balanced_share"]),
                    ]
                    for value, item in sorted(expanded_floor.items(), key=lambda pair: sort_value(pair[0]))
                ],
            )
            lines += markdown_frequency_table(
                "修复后证据完整候选的遭遇统计",
                ["encounter", "scene_count", "scene_share", "run_count", "run_balanced_share"],
                [
                    [
                        value,
                        item["scene_count"],
                        pct(item["scene_share"]),
                        item["run_count"],
                        pct(item["run_balanced_share"]),
                    ]
                    for value, item in sorted(expanded_encounter.items(), key=lambda pair: sort_value(pair[0]))
                ],
            )
            lines += [
                "",
                "修复后扩容建议使用 `priorities` 中的 dynamic 批次；它们由合并后的完整依赖闭包重新计算，不继承旧17/20/4名称。原99场及主审已经运行过的新增候选均视作开发已接触数据，不能因旧 reserved-eval 标签恢复为未接触保留集。",
                "",
            ]
    return "\n".join(lines)


def write_outputs(
    analysis: Mapping[str, Any],
    priorities: Mapping[str, Any],
    graph: Mapping[str, Any],
    report_path: Path | None = None,
    priorities_path: Path | None = None,
    intermediate_dir: Path | None = None,
) -> None:
    report_path = report_path or ROOT / "docs/public-distribution-report.md"
    priorities_path = priorities_path or ROOT / "docs/public-expansion-priorities.json"
    intermediate_dir = intermediate_dir or ROOT / "reference/public-distribution"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(analysis, priorities, graph), encoding="utf-8")
    write_json(priorities_path, priorities)
    write_json(
        intermediate_dir / "coverage-analysis.json",
        {
            "schema": SCHEMA,
            "analysis": analysis,
            "priorities_sha256": sha256_bytes(canonical_bytes(priorities)),
            "dependency_graph_sha256": sha256_bytes(canonical_bytes(graph)),
        },
    )
    write_json(intermediate_dir / "dependency-graph.json", graph)
    write_json(
        intermediate_dir / "priority-scene-ids.json",
        {
            "schema": "public-priority-scene-ids-v1",
            "baseline": priorities["baseline"],
            "batches": [
                {
                    "id": batch["id"],
                    "support_atoms": batch["projected_complete_scene_gain"]["support_atoms"],
                    "scene_count": batch["projected_complete_scene_gain"]["scene_count"],
                    "scene_ids": batch["projected_complete_scene_gain"]["scene_ids"],
                    "run_ids": batch["projected_complete_scene_gain"]["run_ids"],
                }
                for batch in priorities["recommended_batches"]
            ],
        },
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=ROOT / "docs/m2-corpus-index.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs/m2-public-scene-manifest.json")
    parser.add_argument("--contract", type=Path, default=ROOT / "sts/env/public-battle-contract.json")
    parser.add_argument("--implementation-report", type=Path, default=ROOT / "docs/public-battle-implementation.md")
    parser.add_argument("--integration", type=Path, default=ROOT / "reference/public-scene-integration.json")
    parser.add_argument("--prefix-candidates", type=Path, default=None, help="Agent 1 修复后的最终前缀候选文件；不传则只做旧基线")
    parser.add_argument("--prefix-sha256", default=None, help="前缀候选文件的期望SHA256")
    parser.add_argument("--elite-audit", type=Path, default=None, help="Agent 1 最终精英来源交叉审计文件；不传则只做旧基线")
    parser.add_argument("--elite-sha256", default=None, help="精英审计文件的期望SHA256")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/public-distribution-report.md")
    parser.add_argument("--priorities", type=Path, default=ROOT / "docs/public-expansion-priorities.json")
    parser.add_argument("--intermediate-dir", type=Path, default=ROOT / "reference/public-distribution")
    args = parser.parse_args(argv)
    analysis, priorities, graph = analyze(
        index_path=args.index,
        manifest_path=args.manifest,
        contract_path=args.contract,
        implementation_report_path=args.implementation_report,
        integration_path=args.integration,
        prefix_candidates_path=args.prefix_candidates,
        prefix_sha256=args.prefix_sha256,
        elite_audit_path=args.elite_audit,
        elite_sha256=args.elite_sha256,
    )
    write_outputs(
        analysis,
        priorities,
        graph,
        report_path=args.report,
        priorities_path=args.priorities,
        intermediate_dir=args.intermediate_dir,
    )
    print(
        json.dumps(
            {
                "layers": analysis["layer_counts"],
                "net_new_vs_original_99": analysis["layer_counts"]["current_99_executable"]["actual_net_new_scene_count_vs_original_99"],
                "priority_scene_counts": {
                    batch["id"]: batch["projected_complete_scene_gain"]["scene_count"]
                    for batch in priorities["recommended_batches"]
                },
                "external_merge": analysis.get("external_merge", {"status": "baseline_only"}),
                "report": relative_path(args.report),
                "priorities": relative_path(args.priorities),
                "intermediate_dir": relative_path(args.intermediate_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
