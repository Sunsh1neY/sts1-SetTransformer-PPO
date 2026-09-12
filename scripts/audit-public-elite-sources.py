"""审计公开 STS1 Ironclad 精英战斗来源。

本脚本只做来源审计和候选索引生成，不修改正式环境、manifest、奖励或评估配置。
摘要型 .run 只保留公开事件证据；只有 Serialization Mod 的战斗快照才会单独
进入 B 入口证据层。任何无法证明的燃烧状态、前缀或动态计数都保持 unknown。
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DATE = "2026-09-12"
SCHEMA = "public-elite-source-audit-v1"
ELITE_LABELS = {
    "Gremlin Nob": "GREMLIN_NOB",
    "Lagavulin": "LAGAVULIN",
    "3 Sentries": "THREE_SENTRIES",
}
ELITE_IDS = {
    "GremlinNob": "Gremlin Nob",
    "Lagavulin": "Lagavulin",
    "Sentries": "3 Sentries",
}
ACT1_ELITE_FLOORS = range(6, 15)

MATIGER_COMMIT = "097aaf3564c2247835162d267cbc7c55d2c9039e"
MATIGER_ARCHIVE = ROOT / "reference/public-run-corpus/matiger-fixed.zip"
MATIGER_ARCHIVE_SHA256 = "0b21c5fe489ac0980131d0dd14350efdf1c68f180488b6d2072ae0e81cea565e"

PREDICTOR_COMMIT = "a8dd8d41193218179d52b2001953652d850fb2bd"
PREDICTOR_ARCHIVE = (
    ROOT
    / "reference/public-elite-sources"
    / f"fight-predictor-{PREDICTOR_COMMIT}.zip"
)
PREDICTOR_ARCHIVE_SHA256 = "b3887f74b766db2c33e5060a8f65d13b04268b8bd1566a423c3f775294bdac24"

RUNLOGGER_COMMIT = "02679f51c19c7a8d26da618ec0377faa390f347f"
RUNLOGGER_RAW = (
    ROOT
    / "reference/public-elite-sources"
    / f"runlogger-{RUNLOGGER_COMMIT[:7]}-ironclad_1706139943.jsonl"
)
RUNLOGGER_RAW_SHA256 = "e7e6178e1d4566f1e827c6c917471a7bec736b26d6beb53488bf97e1f3c8cb82"
RUNLOGGER_ARCHIVE = (
    ROOT
    / "reference/public-elite-sources"
    / f"runlogger-{RUNLOGGER_COMMIT[:7]}.zip"
)
RUNLOGGER_ARCHIVE_SHA256 = "321b764836233c0e2ae66121637f1825db439101f66d6b0fbad7310491476ac7"
# 上面的源码包哈希在运行时以本地文件为准；旧环境若没有源码包，只影响证据提示。
RUNLOGGER_SOURCE_ROOT = (
    ROOT
    / "reference/public-elite-sources"
    / f"runlogger-{RUNLOGGER_COMMIT}"
)
RUNLOGGER_CONVERTER = RUNLOGGER_SOURCE_ROOT / (
    "src/main/java/serializationmod/GameStateConverter.java"
)
RUNLOGGER_README = RUNLOGGER_SOURCE_ROOT / "README.md"
RUNLOGGER_LICENSE = RUNLOGGER_SOURCE_ROOT / "LICENSE"

BASELINE_MANIFEST = ROOT / "docs/m2-public-scene-manifest.json"
PREFIX_CANDIDATES = ROOT / "docs/public-prefix-expansion-candidates.json"
EVIDENCE_OUTPUT = (
    ROOT
    / "reference/public-elite-sources"
    / "runlogger-elite-evidence.json"
)
PREFIX_CROSSWALK_OUTPUT = (
    ROOT / "reference/public-elite-sources/prefix-elite-crosswalk.json"
)
REPORT_OUTPUT = ROOT / "docs/public-elite-source-report.md"
CANDIDATE_OUTPUT = ROOT / "docs/public-elite-source-candidates.json"


def sha256_bytes(data: bytes) -> str:
    """返回字节内容的 SHA-256。"""

    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """以二进制方式计算文件哈希。"""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path) -> None:
    """对审计输入做显式存在性检查。"""

    if not path.is_file():
        raise FileNotFoundError(f"缺少审计输入：{path}")


def verify_file_hash(path: Path, expected: str) -> str:
    """验证固定输入哈希，防止用未登记的来源替换审计对象。"""

    require_file(path)
    actual = sha256_file(path)
    if expected and actual.lower() != expected.lower():
        raise ValueError(f"固定来源哈希不匹配：{path}，实际={actual}，预期={expected}")
    return actual


def json_load_bytes(raw: bytes, source: str) -> dict[str, Any]:
    """解析一个 .run JSON，并拒绝非对象顶层。"""

    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法解析 JSON：{source}") from exc
    if not isinstance(value, dict):
        raise TypeError(f"来源顶层不是对象：{source}")
    return value


def safe_floor(value: Any) -> int | None:
    """仅接受不会改变语义的整数楼层。"""

    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def source_identity_tokens(record: dict[str, Any]) -> list[str]:
    """生成用于连接重复文件的身份 token。"""

    run = record["run"]
    tokens = []
    if run.get("play_id") is not None:
        tokens.append(f"play_id:{run['play_id']}")
    if run.get("seed_played") is not None:
        tokens.append(f"seed:{run['seed_played']}")
    tokens.append(f"sha:{record['raw_sha256']}")
    return tokens


def group_records(records: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    """按 play_id、source seed、原始哈希的连通分量去重。

    同一 run 的镜像文件只保留一个 canonical record；若同一身份连接到不同
    内容，保留冲突标志，绝不静默选择一个版本。
    """

    parent = list(range(len(records)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    token_owner: dict[str, int] = {}
    for index, record in enumerate(records):
        for token in source_identity_tokens(record):
            if token in token_owner:
                union(index, token_owner[token])
            else:
                token_owner[token] = index

    components: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for index, record in enumerate(records):
        components[find(index)].append(record)

    result = []
    for members in sorted(
        components.values(), key=lambda group: min(item["source_path"] for item in group)
    ):
        members = sorted(members, key=lambda item: item["source_path"])
        canonical = members[0]
        identities = sorted(
            {
                token
                for member in members
                for token in source_identity_tokens(member)
            }
        )
        group_digest = sha256_bytes("|".join(identities).encode("utf-8"))[:20]
        result.append(
            {
                "group_id": f"{prefix}-run-group:{group_digest}",
                "canonical": canonical,
                "aliases": [member["source_path"] for member in members],
                "raw_sha256s": sorted({member["raw_sha256"] for member in members}),
                "identity_tokens": identities,
                "conflicting_variants": len({member["raw_sha256"] for member in members}) > 1,
            }
        )
    return result


def indexed_value(run: dict[str, Any], key: str, floor: int) -> Any:
    """读取与楼层同索引的 summary 字段，不把缺失值补成默认值。"""

    values = run.get(key)
    index = floor - 1
    if not isinstance(values, list) or index < 0 or index >= len(values):
        return None
    return copy.deepcopy(values[index])


def summary_burning_evidence(run: dict[str, Any], floor: int) -> dict[str, Any]:
    """构造摘要日志的燃烧精英证据，永远不把未知写成 false。"""

    path_symbol = indexed_value(run, "path_per_floor", floor)
    key_log = run.get("green_key_taken_log", "<字段缺失>")
    same_floor = key_log == floor
    return {
        "ordinary": None,
        "burning": None,
        "strengthening_type": None,
        "status": "unknown",
        "direct_burning_field": "absent",
        "elite_room_path_symbol": path_symbol,
        "green_key_taken_log": copy.deepcopy(key_log),
        "same_floor_key_observation": same_floor,
        "interpretation": (
            "green_key_taken_log 只记录钥匙取得楼层，不能证明其他精英为普通，"
            "也不能恢复该战斗的燃烧强化类型；path_per_floor=E 只证明精英房间。"
        ),
    }


def summary_event_record(
    *,
    source_kind: str,
    source_url: str,
    group: dict[str, Any],
    event_index: int,
    event: dict[str, Any],
) -> dict[str, Any]:
    """把一个 .run 的精英摘要保留为逐场证据记录。

    摘要自身不能直接形成 A，但 public-derived-standard-v1 允许在另有完整、
    通过审查的历史前缀时派生 A；因此这里不把缺少 B/RNG/原始药水槽写成
    “永远不可恢复”。燃烧标志仍必须独立证明。
    """

    run = group["canonical"]["run"]
    floor = safe_floor(event.get("floor"))
    path_symbol = indexed_value(run, "path_per_floor", floor) if floor is not None else None
    path_consistent = path_symbol == "E"
    available = {
        "character": run.get("character_chosen"),
        "ascension": run.get("ascension_level"),
        "source_build": run.get("build_version"),
        "floor": floor,
        "damage_taken_event": copy.deepcopy(event),
        "path_symbol": path_symbol,
        "current_hp_per_floor_metric": (
            indexed_value(run, "current_hp_per_floor", floor) if floor is not None else None
        ),
        "max_hp_per_floor_metric": (
            indexed_value(run, "max_hp_per_floor", floor) if floor is not None else None
        ),
    }
    reasons = [
        "SUMMARY_HAS_NO_DIRECT_PRE_COMBAT_ENTRY_SNAPSHOT",
        "SUMMARY_DIRECT_ENTRY_DECK_NOT_RECORDED_MASTER_DECK_IS_FINAL_STATE",
        "SUMMARY_DIRECT_RELIC_COUNTER_TIMING_NOT_RECORDED",
        "SUMMARY_DIRECT_POTION_SLOTS_NOT_RECORDED_CANONICALIZE_IF_HISTORY_PROVEN",
        "SUMMARY_DIRECT_GOLD_TIMING_NOT_RECORDED",
        "PREFIX_HISTORY_REQUIRED_FOR_A_DERIVATION",
        "BURNING_ELITE_FLAG_AND_STRENGTHENING_TYPE_UNRECORDED",
    ]
    if not path_consistent:
        reasons.append("ELITE_LABEL_AND_PATH_SYMBOL_CONFLICT_OR_UNKNOWN")

    return {
        "candidate_id": f"{group['group_id']}:floor-{floor}:elite-{event_index}",
        "source_kind": source_kind,
        "source_url": source_url,
        "source_path": group["canonical"]["source_path"],
        "raw_sha256": group["canonical"]["raw_sha256"],
        "source_run_group": group["group_id"],
        "source_run_id": run.get("play_id"),
        "source_seed": run.get("seed_played"),
        "character": run.get("character_chosen"),
        "ascension": run.get("ascension_level"),
        "source_build": run.get("build_version"),
        "floor": floor,
        "act": 1,
        "encounter_label": event.get("enemies"),
        "encounter_backend_id": ELITE_LABELS.get(event.get("enemies")),
        "raw_event": copy.deepcopy(event),
        "available_summary_evidence": available,
        "entry_a": {
            "status": "not_directly_recorded_derivable_with_verified_prefix",
            "timing": "pre_combat_initialization",
            "phase": "before_destination_room_entry",
            "derivation_policy": "public-derived-standard-v1",
            "not_a_permanent_blocker": [
                "potion slots may use canonical inventory slots when complete obtain/use/discard history is proven",
                "hidden RNG/queues/instance ids may be regenerated by an independent versioned environment seed",
                "enemy initialization, hand and piles may be resampled by the backend from A",
            ],
            "available": [
                "character_chosen",
                "ascension_level",
                "build_version",
                "damage_taken.floor/enemies/damage/turns",
                "path_per_floor_symbol_if_present",
                "floor_metrics_as_summary_only",
            ],
            "missing_or_ambiguous": [
                "direct entry deck instances and upgrades in this summary source",
                "direct entry relic inventory and dynamic counter timing",
                "direct entry potion slot positions and capacity in this summary source",
                "direct pre-entry gold timing",
                "map node hasEmeraldKey / burning modifier",
            ],
            "fatal_or_pending_until_prefix_review": [
                "complete historical prefix chain with required event/shop effects",
                "unresolved burning flag or independently proven ordinary elite",
                "unsupported content and relic hooks after the prefix is reconstructed",
            ],
            "do_not_substitute": [
                "master_deck",
                "relics",
                "potions_obtained",
                "current_hp_per_floor_as_a_complete_snapshot",
            ],
        },
        "entry_b": {
            "status": "not_available_in_summary_source",
            "timing": "post_combat_initialization_after_initial_draw",
            "missing": ["hand", "piles", "player energy", "enemy intent/state"],
        },
        "burning_evidence": summary_burning_evidence(run, floor or 0),
        "historical_rules_equivalence": "unverified",
        "status": "summary_only_prefix_derivation_pending",
        "rejection_reasons": sorted(set(reasons)),
    }


def elite_events_from_run(run: dict[str, Any]) -> list[dict[str, Any]]:
    """返回第一幕楼层 6--14 的三种标准精英事件。"""

    events = []
    for event in run.get("damage_taken", []):
        if not isinstance(event, dict) or event.get("enemies") not in ELITE_LABELS:
            continue
        floor = safe_floor(event.get("floor"))
        if floor in ACT1_ELITE_FLOORS:
            events.append(event)
    return events


def read_archive_records(
    archive: Path,
    expected_sha256: str,
    *,
    repository_prefix: str,
    source_kind: str,
    source_url: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """读取固定 GitHub codeload ZIP 中的 .run 文件。"""

    actual_hash = verify_file_hash(archive, expected_sha256)
    records = []
    with zipfile.ZipFile(archive) as bundle:
        names = sorted(
            name
            for name in bundle.namelist()
            if name.endswith(".run") and not name.endswith("/")
        )
        for name in names:
            raw = bundle.read(name)
            run = json_load_bytes(raw, name)
            if run.get("character_chosen") != "IRONCLAD":
                continue
            relative = name
            if repository_prefix and name.startswith(repository_prefix):
                relative = name[len(repository_prefix) :]
            records.append(
                {
                    "source_path": relative,
                    "raw_sha256": sha256_bytes(raw),
                    "run": run,
                }
            )
    return records, {
        "archive": str(archive.relative_to(ROOT)).replace("\\", "/"),
        "archive_sha256": actual_hash,
        "source_kind": source_kind,
        "source_url": source_url,
        "raw_file_count_in_archive": len(names),
    }


def source_group_events(
    records: list[dict[str, Any]],
    *,
    prefix: str,
    source_kind: str,
    source_url: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """对一组摘要 .run 去重并生成精英逐场记录。"""

    groups = group_records(records, prefix)
    events = []
    for group in groups:
        for event_index, event in enumerate(elite_events_from_run(group["canonical"]["run"])):
            events.append(
                summary_event_record(
                    source_kind=source_kind,
                    source_url=source_url,
                    group=group,
                    event_index=event_index,
                    event=event,
                )
            )
    return events, groups, {
        "raw_file_count": len(records),
        "independent_run_groups": len(groups),
        "duplicate_alias_files": len(records) - len(groups),
        "conflicting_groups": sum(group["conflicting_variants"] for group in groups),
        "elite_event_count": len(events),
        "elite_run_groups": len({event["source_run_group"] for event in events}),
        "elite_by_encounter": dict(
            sorted(Counter(event["encounter_label"] for event in events).items())
        ),
        "elite_by_floor": dict(sorted(Counter(event["floor"] for event in events).items())),
        "source_builds": dict(
            sorted(Counter(str(event["source_build"]) for event in events).items())
        ),
        "ascensions": dict(
            sorted(Counter(str(event["ascension"]) for event in events).items())
        ),
        "path_symbol_counts": dict(
            sorted(
                Counter(
                    str(event["burning_evidence"]["elite_room_path_symbol"])
                    for event in events
                ).items()
            )
        ),
        "same_floor_green_key_observation_count": sum(
            event["burning_evidence"]["same_floor_key_observation"] for event in events
        ),
    }


def source_url_for_matiger(path: str) -> str:
    return (
        f"https://raw.githubusercontent.com/MaT1g3R/Slay-the-Spire-data/"
        f"{MATIGER_COMMIT}/{path}"
    )


def audit_matiger() -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """审计当前 corpus 使用的 2022 A20 summary 来源。"""

    prefix = f"Slay-the-Spire-data-{MATIGER_COMMIT}/"
    source_url = f"https://github.com/MaT1g3R/Slay-the-Spire-data/tree/{MATIGER_COMMIT}"
    records, metadata = read_archive_records(
        MATIGER_ARCHIVE,
        MATIGER_ARCHIVE_SHA256,
        repository_prefix=prefix,
        source_kind="github-run-summary",
        source_url=source_url,
    )
    events, groups, stats = source_group_events(
        records,
        prefix="matiger",
        source_kind="github-run-summary",
        source_url=source_url,
    )
    for event in events:
        event["source_repository_url"] = source_url
        event["source_url"] = source_url_for_matiger(event["source_path"])
    stats.update(metadata)
    stats.update(
        {
            "repository": "MaT1g3R/Slay-the-Spire-data",
            "commit": MATIGER_COMMIT,
            "repository_url": source_url,
            "license_status": "repository LICENSE declares Apache-2.0; raw run redistribution scope not separately verified",
            "entry_a_status": "no_direct_complete_summary_events; A_derivation_allowed_with_verified_prefix",
            "entry_b_status": "unavailable",
            "current_backend_status": "zero",
        }
    )
    return events, stats, groups


def first_archive_prefix(names: Iterable[str], marker: str) -> str:
    """从固定 codeload ZIP 推断仓库根目录。"""

    for name in names:
        if marker in name:
            return name.split(marker, 1)[0] + "/"
    raise ValueError(f"ZIP 中找不到目录标记：{marker}")


def count_predictor_outputs(bundle: zipfile.ZipFile, root_prefix: str) -> dict[str, Any]:
    """统计 predictor 已生成的派生 fight row，但不把它们当原始候选。"""

    json_names = sorted(
        name
        for name in bundle.namelist()
        if name.startswith(root_prefix + "out/") and name.endswith(".json")
    )
    total_rows = 0
    by_character: Counter[str] = Counter()
    act1_elite_rows = 0
    sample_keys: list[str] = []
    for name in json_names:
        value = json.loads(bundle.read(name).decode("utf-8"))
        if not isinstance(value, list):
            continue
        total_rows += len(value)
        if value and not sample_keys and isinstance(value[0], dict):
            sample_keys = sorted(value[0].keys())
        for row in value:
            if not isinstance(row, dict):
                continue
            character = row.get("character")
            by_character[str(character)] += 1
            floor = safe_floor(row.get("floor"))
            if (
                character == "IRONCLAD"
                and floor in ACT1_ELITE_FLOORS
                and row.get("enemies") in ELITE_LABELS
            ):
                act1_elite_rows += 1
    return {
        "json_file_count": len(json_names),
        "row_count": total_rows,
        "rows_by_character": dict(sorted(by_character.items())),
        "ironclad_act1_elite_row_count": act1_elite_rows,
        "sample_row_keys": sample_keys,
        "sample_row_has_run_identity": any(
            key in sample_keys for key in ("play_id", "seed_played", "source_path")
        ),
    }


def audit_predictor() -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """审计 Slay-I 固定提交中的原始 .run 与派生输出。"""

    source_url = (
        f"https://github.com/alexdriedger/SlayTheSpireFightPredictor/tree/{PREDICTOR_COMMIT}"
    )
    actual_hash = verify_file_hash(PREDICTOR_ARCHIVE, PREDICTOR_ARCHIVE_SHA256)
    records = []
    all_run_count = 0
    output_stats: dict[str, Any]
    with zipfile.ZipFile(PREDICTOR_ARCHIVE) as bundle:
        names = sorted(bundle.namelist())
        root_prefix = first_archive_prefix(names, "/2019SpireRuns/")
        output_root = first_archive_prefix(names, "/out/")
        run_prefix = root_prefix + "2019SpireRuns/"
        for name in names:
            if not (name.startswith(run_prefix) and name.endswith(".run")):
                continue
            all_run_count += 1
            raw = bundle.read(name)
            run = json_load_bytes(raw, name)
            if run.get("character_chosen") != "IRONCLAD":
                continue
            records.append(
                {
                    "source_path": name[len(root_prefix) :],
                    "raw_sha256": sha256_bytes(raw),
                    "run": run,
                }
            )
        output_stats = count_predictor_outputs(bundle, output_root)

    events, groups, stats = source_group_events(
        records,
        prefix="fight-predictor",
        source_kind="github-summary-and-derived-fight-data",
        source_url=source_url,
    )
    for event in events:
        event["source_repository_url"] = source_url
        event["source_url"] = (
            f"https://raw.githubusercontent.com/alexdriedger/SlayTheSpireFightPredictor/"
            f"{PREDICTOR_COMMIT}/{event['source_path']}"
        )
    stats.update(
        {
            "repository": "alexdriedger/SlayTheSpireFightPredictor",
            "commit": PREDICTOR_COMMIT,
            "repository_url": source_url,
            "archive": str(PREDICTOR_ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "archive_sha256": actual_hash,
            "raw_file_count_in_archive": all_run_count,
            "ironclad_raw_file_count": len(records),
            "license_status": "pinned tree has no LICENSE file; usage and raw-data redistribution restrictions unknown",
            "derived_outputs": output_stats,
            "entry_a_status": "no_direct_complete_summary_events; A_derivation_allowed_with_verified_prefix",
            "entry_b_status": "unavailable",
            "current_backend_status": "zero",
            "source_claims": {
                "README_declares_data_from": ["Spire Logs", "Jorbs"],
                "README_declares_training_scale": "over 325,000 fights",
            },
        }
    )
    return events, stats, groups


def parse_jsonl(content: bytes, source: str) -> list[tuple[int, dict[str, Any]]]:
    """解析带行号的 JSONL。"""

    records = []
    for line_number, line in enumerate(content.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSONL 第 {line_number} 行无法解析：{source}") from exc
        if not isinstance(value, dict):
            raise TypeError(f"JSONL 第 {line_number} 行不是对象：{source}")
        records.append((line_number, value))
    return records


def conditional_pile(
    combat_state: dict[str, Any], key: str, *, source_semantics: str
) -> dict[str, Any]:
    """按 runlogger 源码解释条件省略的空牌堆。"""

    if key not in combat_state:
        return {"items": [], "evidence": source_semantics}
    value = combat_state[key]
    if not isinstance(value, list):
        raise TypeError(f"runlogger combat_state.{key} 不是数组")
    return {"items": copy.deepcopy(value), "evidence": "direct_nonempty_record"}


def normalized_creature_field(
    creature: dict[str, Any], key: str, *, empty_evidence: str
) -> dict[str, Any]:
    """保留条件省略的玩家/敌人字段及其证据。"""

    if key not in creature:
        return {"value": 0 if key in {"block", "energy"} else [], "evidence": empty_evidence}
    return {"value": copy.deepcopy(creature[key]), "evidence": "direct_record"}


def runlogger_burning_evidence(
    run_state: dict[str, Any],
    all_floor_states: list[dict[str, Any]],
) -> dict[str, Any]:
    """利用 final_act=false 证明该 run 不可能生成燃烧精英。

    这不是把未知默认成 false：GameStateConverter 明确把 Settings.isFinalActAvailable
    写入 run 状态，而锁定版本反编译证据显示 setEmeraldElite 在该条件为 false 时直接返回。
    """

    unlocks = run_state.get("unlocks")
    final_act = unlocks.get("final_act") if isinstance(unlocks, dict) else None
    key_states = [state.get("keys") for state in all_floor_states if "keys" in state]
    if final_act is False:
        status = "ordinary_proven_by_final_act_unavailable"
        ordinary: bool | None = True
        burning: bool | None = False
    else:
        status = "unknown"
        ordinary = None
        burning = None
    return {
        "status": status,
        "ordinary": ordinary,
        "burning": burning,
        "strengthening_type": None if burning is not False else "not_applicable",
        "direct_burning_field": "absent",
        "final_act_available_recorded": final_act,
        "emerald_key_states_seen": copy.deepcopy(key_states),
        "evidence": [
            "runlogger GameStateConverter.java: getRunState writes Settings.isFinalActAvailable to unlocks.final_act",
            "reference/sts1-decompiled/m2-entry-a/abstract-dungeon.txt:1342-1347: setEmeraldElite returns when Settings.isFinalActAvailable is false",
            "reference/sts1-decompiled/m2-entry-a/abstract-player.txt:5246-5252: applyEmeraldEliteBuff is gated by MapRoomNode.hasEmeraldKey",
            "the full runlogger record contains no keys.emerald state after the elite",
        ],
        "interpretation": (
            "仅在 final_act=false 时使用不可生成燃烧精英的条件；不使用 green_key_taken_log "
            "推断其他精英为普通。"
        ),
    }


def audit_runlogger() -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """审计 Serialization Mod JSONL，并抽取每层第一个精英 B 快照。"""

    actual_hash = verify_file_hash(RUNLOGGER_RAW, RUNLOGGER_RAW_SHA256)
    content = RUNLOGGER_RAW.read_bytes()
    records = parse_jsonl(content, str(RUNLOGGER_RAW))
    if not records or records[0][1].get("_type") != "state:run":
        raise ValueError("runlogger 第一条记录必须是 state:run")
    run_state = records[0][1]
    all_floor_states = [
        record
        for _, record in records
        if record.get("_type") == "state:floor"
    ]
    current_act: int | None = None
    seen_floors: set[int] = set()
    scenes = []
    raw_elite_evidence = []
    for index, (line_number, record) in enumerate(records):
        if record.get("_type") == "state:act":
            current_act = safe_floor(record.get("act"))
        if record.get("_type") != "state:floor" or "combat_state" not in record:
            continue
        floor = safe_floor(record.get("floor"))
        if floor is None or floor in seen_floors:
            continue
        seen_floors.add(floor)
        if record.get("room_type") != "MonsterRoomElite" or floor not in ACT1_ELITE_FLOORS:
            continue
        combat = record.get("combat_state")
        if not isinstance(combat, dict):
            continue
        monsters = combat.get("monsters")
        if not isinstance(monsters, list) or not monsters:
            continue
        predecessor = records[index - 1][1] if index > 0 else None
        if not isinstance(predecessor, dict):
            predecessor = None
        raw_elite_evidence.append(
            {
                "source_line": line_number,
                "raw_state": copy.deepcopy(record),
                "predecessor": copy.deepcopy(predecessor),
            }
        )
        scenes.append(
            runlogger_scene(
                run_state=run_state,
                floor_state=record,
                predecessor=predecessor,
                source_line=line_number,
                act=current_act,
                all_floor_states=all_floor_states,
                source_hash=actual_hash,
            )
        )

    source_url = (
        f"https://github.com/colinking/runlogger/tree/{RUNLOGGER_COMMIT}"
    )
    stats = {
        "repository": "colinking/runlogger",
        "commit": RUNLOGGER_COMMIT,
        "repository_url": source_url,
        "source_url": f"https://raw.githubusercontent.com/colinking/runlogger/{RUNLOGGER_COMMIT}/runs/ironclad_1706139943.json",
        "raw_file_count": 1,
        "independent_run_groups": 1,
        "raw_sha256": actual_hash,
        "record_count": len(records),
        "record_type_counts": dict(
            sorted(Counter(str(record.get("_type")) for _, record in records).items())
        ),
        "combat_floor_count": len(
            {
                safe_floor(record.get("floor"))
                for record in all_floor_states
                if "combat_state" in record and safe_floor(record.get("floor")) is not None
            }
        ),
        "elite_b_snapshot_count": len(scenes),
        "elite_by_encounter": dict(
            sorted(
                Counter(
                    scene["encounter"]["backend_id"] for scene in scenes
                ).items()
            )
        ),
        "ascensions": {
            str(run_state.get("ascension_level", run_state.get("ascension"))): 1
        },
        "source_builds": {str(run_state.get("versions", {}).get("sts")): len(scenes)},
        "license_status": "MIT LICENSE present for source repository; example raw data redistribution scope not separately stated",
        "entry_a_status": "zero_complete_because_log starts after map selection and room entry",
        "entry_b_status": "one_visible_complete_snapshot",
        "current_backend_status": "zero_because_current_contract_is_A_only_and_content_is_not_supported",
        "field_semantics_source": {
            "format_document": f"https://raw.githubusercontent.com/colinking/runlogger/{RUNLOGGER_COMMIT}/README.md",
            "serializer_source": f"https://github.com/colinking/runlogger/blob/{RUNLOGGER_COMMIT}/src/main/java/serializationmod/GameStateConverter.java",
            "conditional_fields": [
                "combat_state.draw_pile/discard_pile/exhaust_pile/hand/limbo only emitted when non-empty",
                "player.block only emitted when >0",
                "monster.damage only emitted when >0",
                "relic.counter only emitted when >-1",
            ],
        },
    }
    return scenes, stats, raw_elite_evidence, run_state


def runlogger_scene(
    *,
    run_state: dict[str, Any],
    floor_state: dict[str, Any],
    predecessor: dict[str, Any] | None,
    source_line: int,
    act: int | None,
    all_floor_states: list[dict[str, Any]],
    source_hash: str,
) -> dict[str, Any]:
    """构造一条完整可见 B 快照，不把它伪装成 A。"""

    floor = safe_floor(floor_state.get("floor"))
    combat = floor_state["combat_state"]
    if not isinstance(combat, dict):
        raise TypeError("elite state 的 combat_state 不是对象")
    monsters = combat.get("monsters")
    player = combat.get("player")
    if not isinstance(monsters, list) or not monsters:
        raise ValueError("elite state 缺少 monsters")
    if not isinstance(player, dict) or "energy" not in player:
        raise ValueError("elite state 缺少 player.energy")
    required_floor_fields = ["deck", "hp_current", "hp_max", "gold", "relics", "potions"]
    missing_floor_fields = [key for key in required_floor_fields if key not in floor_state]
    if missing_floor_fields:
        raise ValueError(f"elite B 快照缺少字段：{missing_floor_fields}")

    empty_pile_evidence = "serializer_conditional_field_absent_proves_empty"
    piles = {
        key: conditional_pile(combat, key, source_semantics=empty_pile_evidence)
        for key in ("draw_pile", "discard_pile", "exhaust_pile", "hand", "limbo")
    }
    normalized_monsters = copy.deepcopy(monsters)
    for monster in normalized_monsters:
        if not isinstance(monster, dict):
            raise TypeError("monster 项不是对象")
        if "powers" not in monster:
            monster["powers"] = []
    normalized_player = {
        "energy": normalized_creature_field(
            player, "energy", empty_evidence="energy 必须直接记录"
        ),
        "block": normalized_creature_field(
            player,
            "block",
            empty_evidence="serializer_conditional_field_absent_proves_zero_block",
        ),
        "powers": {
            "value": copy.deepcopy(player.get("powers", [])),
            "evidence": (
                "direct_record"
                if "powers" in player
                else "serializer_conditional_field_absent_proves_empty"
            ),
        },
    }
    unsupported_relics = sorted(
        str(relic.get("id"))
        for relic in floor_state["relics"]
        if isinstance(relic, dict)
        and relic.get("id") not in {
            "Burning Blood",
            "Lantern",
            "Anchor",
            "Bag of Preparation",
            "Vajra",
            "Oddly Smooth Stone",
            "Blood Vial",
            "Bronze Scales",
        }
    )
    burning_evidence = runlogger_burning_evidence(run_state, all_floor_states)
    encounter_id = monsters[0].get("id")
    encounter_label = ELITE_IDS.get(encounter_id, encounter_id)
    return {
        "candidate_id": f"runlogger:{run_state.get('seed')}:{floor}:B",
        "source_kind": "github-runlogger-jsonl",
        "source_url": f"https://raw.githubusercontent.com/colinking/runlogger/{RUNLOGGER_COMMIT}/runs/ironclad_1706139943.json",
        "source_path": "runs/ironclad_1706139943.json",
        "raw_sha256": source_hash,
        "source_run_group": f"runlogger-run-group:{sha256_bytes(str(run_state.get('seed')).encode())[:20]}",
        "source_run_id": None,
        "source_seed": run_state.get("seed"),
        "character": run_state.get("class"),
        "ascension": run_state.get("ascension", run_state.get("ascension_level")),
        "source_build": run_state.get("versions", {}).get("sts"),
        "floor": floor,
        "act": act,
        "encounter": {
            "label": encounter_label,
            "backend_id": ELITE_LABELS.get(encounter_label),
            "raw_monster_id": encounter_id,
        },
        "entry_a": {
            "status": "not_available",
            "timing": "pre_combat_initialization",
            "phase": "before_destination_room_entry",
            "reason": "the first elite state is after action:select_map and already has combat_state",
            "missing": [
                "pre-entry room modifier/map node hasEmeraldKey",
                "pre-entry internal queues and card instance ids",
            ],
        },
        "entry_b": {
            "status": "visible_snapshot_complete",
            "timing": "post_combat_initialization_after_initial_draw",
            "source_state_line": source_line,
            "predecessor": copy.deepcopy(predecessor),
            "player": {
                "hp": floor_state["hp_current"],
                "max_hp": floor_state["hp_max"],
                "gold": floor_state["gold"],
                "combat": normalized_player,
            },
            "deck": copy.deepcopy(floor_state["deck"]),
            "relics": copy.deepcopy(floor_state["relics"]),
            "relic_counter_evidence": [
                {
                    "id": relic.get("id") if isinstance(relic, dict) else None,
                    "counter": relic.get("counter") if isinstance(relic, dict) else None,
                    "evidence": (
                        "direct_counter"
                        if isinstance(relic, dict) and "counter" in relic
                        else "serializer_omitted_when_counter_le_minus_one"
                    ),
                }
                for relic in floor_state["relics"]
            ],
            "potions": copy.deepcopy(floor_state["potions"]),
            "piles": piles,
            "enemies": normalized_monsters,
            "raw_state_preserved": copy.deepcopy(floor_state),
            "internal_state_status": "unproven",
            "internal_state_missing": [
                "InputState",
                "ActionQueue/CardQueue",
                "CardInstance dynamic values and ids",
                "backend pile order beyond serialized contents",
                "monster move/history/miscInfo",
                "RNG stream and counters",
            ],
            "field_audit": {
                "direct_recorded": [
                    "floor",
                    "room_type",
                    "hp_current/hp_max",
                    "gold",
                    "deck card display strings",
                    "relic ids and recorded counters",
                    "potion slot list",
                    "monster id/hp/intent",
                    "monster powers when present",
                    "draw_pile",
                    "hand",
                    "player.energy",
                    "select_map symbol/x/y in the predecessor action",
                ],
                "recovered_from_serializer_semantics": [
                    "absent discard_pile/exhaust_pile/limbo means empty",
                    "absent player/monster powers means empty",
                    "absent player block means zero",
                    "absent relic counter means serializer did not emit counter > -1, not an invented zero",
                ],
                "visible_dynamic_missing": [
                    "direct map-node hasEmeraldKey/burning flag and strengthening type",
                    "card current cost, per-copy uuid and runtime display attributes beyond name/+ string",
                    "any explicit positive intent damage/hit count not present in this BUFF snapshot",
                ],
            },
        },
        "burning_evidence": burning_evidence,
        "unsupported_content": {
            "relics_for_current_contract": unsupported_relics,
            "current_contract_has_B_entry": False,
        },
        "historical_rules_equivalence": "unverified",
        "exact_historical_replay": False,
        "status": "evidence_complete_B_interface_pending",
        "evidence_complete_for_public_B": True,
        "current_backend_admissible": False,
        "rejection_reasons": [
            "CURRENT_INTERFACE_SUPPORTS_ENTRY_A_ONLY",
            "CURRENT_CONTRACT_HAS_NO_B_SNAPSHOT_INPUT",
            *(["UNSUPPORTED_RELICS_PRESERVED:" + ",".join(unsupported_relics)] if unsupported_relics else []),
        ],
    }


def load_baseline() -> dict[str, Any]:
    """读取当前 99 场基线，只用于交叉去重统计。"""

    require_file(BASELINE_MANIFEST)
    data = json.loads(BASELINE_MANIFEST.read_text(encoding="utf-8"))
    scenes = data.get("scenes", [])
    summary = data.get("summary", {})
    baseline_groups = {
        (scene.get("raw_sha256"), scene.get("source_path"))
        for scene in scenes
        if scene.get("content_admission_status") == "accepted"
    }
    accepted = [
        scene for scene in scenes if scene.get("content_admission_status") == "accepted"
    ]
    return {
        "manifest": str(BASELINE_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "manifest_sha256": sha256_file(BASELINE_MANIFEST),
        "scene_count_in_manifest": len(scenes),
        "accepted_scene_count": summary.get("content_eligible_scenes", len(accepted)),
        "accepted_run_group_count": summary.get(
            "content_eligible_groups", len({scene.get("group_id") for scene in accepted})
        ),
        "accepted_group_identity_pairs": sorted(
            [list(pair) for pair in baseline_groups], key=lambda pair: str(pair)
        ),
        "elite_scene_count": sum(
            scene.get("encounter_label") in ELITE_LABELS for scene in accepted
        ),
        "accepted_by_encounter": summary.get("by_encounter", {}),
    }


def prefix_scene_key(scene: dict[str, Any]) -> tuple[str, int | None, str | None]:
    """按原始 SHA、楼层和遭遇名称连接前缀场景。"""

    raw_sha = str(scene.get("raw_sha256") or "").lower()
    return raw_sha, safe_floor(scene.get("floor")), scene.get("encounter_label")


def prefix_history_status(scene: dict[str, Any]) -> dict[str, Any]:
    """总结前缀 agent 的历史链，不把其声称直接升级为主审准入。"""

    candidate = scene.get("candidate")
    chain = scene.get("prefix_evidence_chain")
    chain_rows = chain if isinstance(chain, list) else []
    applied = all(
        isinstance(row, dict) and row.get("status") == "applied"
        for row in chain_rows
    )
    has_candidate = isinstance(candidate, dict)
    if has_candidate and applied:
        status = "prefix_candidate_chain_present_review_pending"
    elif has_candidate:
        status = "prefix_candidate_chain_has_unresolved_rows"
    else:
        status = "prefix_entry_content_not_recovered"
    return {
        "status": status,
        "prefix_claimed_entry_content": has_candidate,
        "all_chain_rows_applied": applied,
        "chain_floor_count": len(chain_rows),
        "chain_floors": [
            row.get("floor") for row in chain_rows if isinstance(row, dict)
        ],
        "prefix_types": copy.deepcopy(scene.get("prefix_types", [])),
        "prefix_touched": scene.get("prefix_touched"),
        "review_status": "returned_for_P1_burning_and_P2_event_potion_validation",
    }


def build_prefix_crosswalk(
    summary_events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """将前缀扩展的全部精英行与来源索引逐场对齐。

    连接键不依赖两份脚本的 group_id：优先使用原始文件 SHA、楼层和遭遇，
    再核对 source path、source seed 和 run identity。前缀的 burning 字段缺失
    时，最终状态保持 unknown，即使前缀 agent 声称 evidence_complete/backend_admissible。
    """

    require_file(PREFIX_CANDIDATES)
    prefix_data = json.loads(PREFIX_CANDIDATES.read_text(encoding="utf-8"))
    prefix_scenes = prefix_data.get("scenes")
    if not isinstance(prefix_scenes, list):
        raise TypeError("前缀候选文件缺少 scenes 数组")

    source_by_key: dict[tuple[str, int | None, str | None], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for index, event in enumerate(summary_events):
        source_by_key[prefix_scene_key(event)].append((index, event))

    crosswalk = []
    elite_rows = [
        (index, scene)
        for index, scene in enumerate(prefix_scenes)
        if scene.get("encounter_label") in ELITE_LABELS
    ]
    for prefix_index, scene in elite_rows:
        key = prefix_scene_key(scene)
        matches = source_by_key.get(key, [])
        source_index, source_event = matches[0] if len(matches) == 1 else (None, None)
        candidate = scene.get("candidate") if isinstance(scene.get("candidate"), dict) else None
        source_path_match = bool(
            source_event and scene.get("source_path") == source_event.get("source_path")
        )
        source_seed_match = bool(
            source_event
            and str(scene.get("source_seed")) == str(source_event.get("source_seed"))
        )
        raw_sha_match = bool(
            source_event
            and str(scene.get("raw_sha256", "")).lower()
            == str(source_event.get("raw_sha256", "")).lower()
        )
        floor_match = bool(source_event and scene.get("floor") == source_event.get("floor"))
        label_match = bool(
            source_event and scene.get("encounter_label") == source_event.get("encounter_label")
        )

        source_burning = (
            source_event.get("burning_evidence", {}) if source_event else {}
        )
        path_symbol = source_burning.get("elite_room_path_symbol")
        if source_event and path_symbol == "E":
            room_status = "confirmed_by_damage_taken_and_E_path"
        elif source_event:
            room_status = "elite_label_only_path_conflict_or_unknown"
        else:
            room_status = "source_index_not_found"

        prefix_burning_field = (
            candidate.get("burning_elite") if candidate and "burning_elite" in candidate else None
        )
        prefix_strengthening = (
            candidate.get("strengthening_type")
            if candidate and "strengthening_type" in candidate
            else None
        )
        final_missing = [
            "BURNING_ELITE_FLAG_OR_PROOF_ORDINARY",
            "BURNING_STRENGTHENING_TYPE_OR_EXPLICIT_NOT_APPLICABLE_PROOF",
        ]
        history = prefix_history_status(scene)
        if not history["prefix_claimed_entry_content"]:
            final_missing.append("PREFIX_ENTRY_CONTENT_NOT_RECOVERED")
            final_missing.append("PREFIX_AGENT_BLOCKERS_NOT_CLEARED")
        if not source_event:
            final_missing.append("SOURCE_INDEX_MATCH_MISSING")
        if source_event and not source_path_match:
            final_missing.append("SOURCE_PATH_MISMATCH")
        if source_event and not source_seed_match:
            final_missing.append("SOURCE_SEED_MISMATCH")

        if scene.get("backend_admissible"):
            final_status = "prefix_static_backend_claim_withdrawn_burning_unknown"
        elif history["prefix_claimed_entry_content"]:
            final_status = "prefix_content_claimed_but_burning_unknown_and_review_pending"
        else:
            final_status = "prefix_entry_incomplete_and_burning_unknown"

        crosswalk.append(
            {
                "prefix_scene_index": prefix_index,
                "prefix_scene_id": scene.get("scene_id"),
                "prefix_group_id": scene.get("group_id"),
                "source_path": scene.get("source_path"),
                "raw_sha256": scene.get("raw_sha256"),
                "source_seed": scene.get("source_seed"),
                "floor": scene.get("floor"),
                "encounter_label": scene.get("encounter_label"),
                "source_index_match": {
                    "status": "one_exact_key_match" if source_event else "not_found_or_ambiguous",
                    "summary_event_index": source_index,
                    "raw_sha_match": raw_sha_match,
                    "source_path_match": source_path_match,
                    "source_seed_match": source_seed_match,
                    "floor_match": floor_match,
                    "encounter_label_match": label_match,
                    "source_run_id": source_event.get("source_run_id") if source_event else None,
                    "source_run_group": source_event.get("source_run_group") if source_event else None,
                    "source_url": source_event.get("source_url") if source_event else None,
                },
                "entry_player_content_and_history": {
                    "source_summary_status": (
                        "summary_only_no_direct_A_snapshot" if source_event else "unknown"
                    ),
                    "prefix": history,
                    "prefix_candidate_content": copy.deepcopy(candidate),
                    "prefix_candidate_fields_present": sorted(candidate.keys()) if candidate else [],
                    "canonical_potion_policy": (
                        candidate.get("potion_slot_policy") if candidate else None
                    ),
                    "hidden_state_policy": (
                        candidate.get("resampling_policy") if candidate else "not_available"
                    ),
                    "exact_historical_replay": (
                        candidate.get("exact_historical_replay") if candidate else None
                    ),
                },
                "target_elite_room": {
                    "status": room_status,
                    "encounter_label": scene.get("encounter_label"),
                    "path_symbol_from_summary": path_symbol,
                    "evidence": [
                        "prefix scene encounter_label",
                        "source index raw damage_taken event",
                        "source index path_per_floor when E",
                    ],
                },
                "burning_and_strengthening": {
                    "source_index_ordinary": source_burning.get("ordinary"),
                    "source_index_burning": source_burning.get("burning"),
                    "source_index_strengthening_type": source_burning.get("strengthening_type"),
                    "prefix_burning_elite_field": prefix_burning_field,
                    "prefix_strengthening_type_field": prefix_strengthening,
                    "final_ordinary": None,
                    "final_burning": None,
                    "final_strengthening_type": None,
                    "status": "unknown",
                    "why": (
                        "前缀候选没有 burning_elite/强化字段；summary 的 green_key_taken_log "
                        "不能把其他精英证明为普通。A0 B 的 final_act=false 只适用于该 A0 run。"
                    ),
                },
                "current_backend": {
                    "prefix_claimed_backend_admissible": bool(scene.get("backend_admissible")),
                    "source_index_backend_admissible": False,
                    "final_backend_admissible": False,
                    "status": "withdrawn_or_not_admissible_until_burning_gate_is_proven",
                },
                "prefix_claimed_flags": {
                    "raw_research_candidate": bool(scene.get("raw_research_candidate")),
                    "evidence_complete": bool(scene.get("evidence_complete")),
                    "backend_admissible": bool(scene.get("backend_admissible")),
                    "evidence_blockers": copy.deepcopy(scene.get("evidence_blockers", [])),
                    "state_evidence_blockers": copy.deepcopy(scene.get("state_evidence_blockers", [])),
                    "backend_blockers": copy.deepcopy(scene.get("backend_blockers", [])),
                },
                "prefix_review_context": {
                    "status": "returned_for_P1_P2_review",
                    "known_global_issues": [
                        "P1 burning flag/strengthening evidence gate",
                        "P2 event potion accounting and required effect-field validation",
                    ],
                    "row_specific_P2_contamination_proven": False,
                },
                "final_status": final_status,
                "final_missing": sorted(set(final_missing)),
                "evidence_locations": {
                    "prefix_candidates_json_pointer": f"/scenes/{prefix_index}",
                    "source_candidates_json_pointer": (
                        f"/summary_elite_events/{source_index}" if source_index is not None else None
                    ),
                    "raw_source_url": source_event.get("source_url") if source_event else None,
                },
            }
        )

    stats = {
        "prefix_elite_row_count": len(crosswalk),
        "source_index_matched_row_count": sum(
            row["source_index_match"]["status"] == "one_exact_key_match"
            for row in crosswalk
        ),
        "source_index_unmatched_or_ambiguous_row_count": sum(
            row["source_index_match"]["status"] != "one_exact_key_match"
            for row in crosswalk
        ),
        "prefix_raw_research_candidate_count": sum(
            row["prefix_claimed_flags"]["raw_research_candidate"] for row in crosswalk
        ),
        "prefix_evidence_complete_claim_count": sum(
            row["prefix_claimed_flags"]["evidence_complete"] for row in crosswalk
        ),
        "prefix_backend_admissible_claim_count": sum(
            row["prefix_claimed_flags"]["backend_admissible"] for row in crosswalk
        ),
        "prefix_backend_claims_withdrawn_count": sum(
            row["prefix_claimed_flags"]["backend_admissible"]
            and not row["current_backend"]["final_backend_admissible"]
            for row in crosswalk
        ),
        "burning_unknown_count": sum(
            row["burning_and_strengthening"]["status"] == "unknown"
            for row in crosswalk
        ),
        "room_confirmed_count": sum(
            row["target_elite_room"]["status"] == "confirmed_by_damage_taken_and_E_path"
            for row in crosswalk
        ),
        "room_path_conflict_or_unknown_count": sum(
            row["target_elite_room"]["status"] != "confirmed_by_damage_taken_and_E_path"
            for row in crosswalk
        ),
        "by_encounter": dict(
            sorted(Counter(row["encounter_label"] for row in crosswalk).items())
        ),
        "by_floor": dict(sorted(Counter(row["floor"] for row in crosswalk).items())),
        "by_prefix_final_status": dict(
            sorted(Counter(row["final_status"] for row in crosswalk).items())
        ),
    }
    return crosswalk, stats


def source_identity_sets(
    records: list[dict[str, Any]],
) -> tuple[set[str], set[str], set[str]]:
    """返回 play_id、source seed、原始哈希集合。"""

    return (
        {str(record["run"].get("play_id")) for record in records if record["run"].get("play_id") is not None},
        {str(record["run"].get("seed_played")) for record in records if record["run"].get("seed_played") is not None},
        {record["raw_sha256"] for record in records},
    )


def read_source_metadata() -> dict[str, Any]:
    """读取固定源码包的哈希，不能下载时保留明确的 unknown。"""

    metadata: dict[str, Any] = {
        "runlogger_archive": {
            "path": str(RUNLOGGER_ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "sha256": None,
            "status": "unknown",
        },
        "runlogger_source_files": {},
        "predictor_source_files": {},
    }
    if RUNLOGGER_ARCHIVE.is_file():
        metadata["runlogger_archive"] = {
            "path": str(RUNLOGGER_ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "sha256": verify_file_hash(RUNLOGGER_ARCHIVE, RUNLOGGER_ARCHIVE_SHA256),
            "status": "available",
        }
    for label, path in {
        "README.md": RUNLOGGER_README,
        "LICENSE": RUNLOGGER_LICENSE,
        "GameStateConverter.java": RUNLOGGER_CONVERTER,
    }.items():
        if path.is_file():
            metadata["runlogger_source_files"][label] = {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(path),
                "status": "available",
            }
        else:
            metadata["runlogger_source_files"][label] = {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": None,
                "status": "missing",
            }
    predictor_root = ROOT / "reference/public-elite-sources" / f"SlayTheSpireFightPredictor-{PREDICTOR_COMMIT}"
    for relative in ("README.md", "main.py"):
        path = predictor_root / relative
        if path.is_file():
            metadata["predictor_source_files"][relative] = {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256_file(path),
                "status": "available",
            }
    return metadata


def build_audit() -> dict[str, Any]:
    """执行全部只读审计并返回机器可读结果。"""

    matiger_events, matiger_stats, matiger_groups = audit_matiger()
    predictor_events, predictor_stats, _predictor_groups = audit_predictor()
    runlogger_scenes, runlogger_stats, raw_elite_evidence, run_state = audit_runlogger()
    baseline = load_baseline()
    prefix_crosswalk, prefix_alignment = build_prefix_crosswalk(matiger_events + predictor_events)

    # 为去重计算重新读取轻量身份字段；不把别的来源的 raw 内容拼接成场景。
    with zipfile.ZipFile(MATIGER_ARCHIVE) as bundle:
        matiger_prefix = f"Slay-the-Spire-data-{MATIGER_COMMIT}/"
        matiger_records = []
        for name in sorted(bundle.namelist()):
            if not (name.startswith(matiger_prefix) and name.endswith(".run")):
                continue
            raw = bundle.read(name)
            run = json_load_bytes(raw, name)
            if run.get("character_chosen") == "IRONCLAD":
                matiger_records.append(
                    {"source_path": name[len(matiger_prefix) :], "raw_sha256": sha256_bytes(raw), "run": run}
                )
    with zipfile.ZipFile(PREDICTOR_ARCHIVE) as bundle:
        predictor_prefix = first_archive_prefix(bundle.namelist(), "/2019SpireRuns/")
        predictor_records = []
        for name in sorted(bundle.namelist()):
            if not (name.startswith(predictor_prefix + "2019SpireRuns/") and name.endswith(".run")):
                continue
            raw = bundle.read(name)
            run = json_load_bytes(raw, name)
            if run.get("character_chosen") == "IRONCLAD":
                predictor_records.append(
                    {"source_path": name[len(predictor_prefix) :], "raw_sha256": sha256_bytes(raw), "run": run}
                )
    runlogger_identity = {str(run_state.get("seed"))}
    matiger_ids = source_identity_sets(matiger_records)
    predictor_ids = source_identity_sets(predictor_records)
    source_groups_total = (
        matiger_stats["elite_run_groups"]
        + predictor_stats["elite_run_groups"]
        + runlogger_stats["elite_b_snapshot_count"]
    )
    current_baseline_pairs = {
        tuple(pair) for pair in baseline["accepted_group_identity_pairs"]
    }
    matiger_baseline_overlap = sum(
        (group["canonical"]["raw_sha256"], group["canonical"]["source_path"])
        in current_baseline_pairs
        for group in matiger_groups
    )
    raw_event_count = (
        len(matiger_events) + len(predictor_events) + len(runlogger_scenes)
    )
    evidence_complete = [
        scene for scene in runlogger_scenes if scene.get("evidence_complete_for_public_B")
    ]
    entry_a_complete = [
        scene
        for scene in [*matiger_events, *predictor_events, *runlogger_scenes]
        if scene.get("entry_a", {}).get("status") == "evidence_complete"
    ]
    current_backend = [
        scene
        for scene in [*matiger_events, *predictor_events, *runlogger_scenes]
        if scene.get("current_backend_admissible")
    ]

    all_events = [*matiger_events, *predictor_events, *runlogger_scenes]
    unique_external_group_tokens = {
        event["source_run_group"] for event in all_events
    }
    source_summary = {
        "matiger": matiger_stats,
        "fight_predictor": predictor_stats,
        "runlogger": runlogger_stats,
    }
    return {
        "schema": SCHEMA,
        "audit_date": AUDIT_DATE,
        "scope": {
            "game": "STS1 Ironclad",
            "act": 1,
            "elite_floors": [6, 14],
            "elite_encounters": ELITE_LABELS,
            "entry_a": "pre_combat_initialization / before_destination_room_entry",
            "entry_b": "post_combat_initialization_after_initial_draw",
            "source_admission_policy": "public-derived-standard-v1",
            "formal_environment_untouched": True,
        },
        "baseline": baseline,
        "counts": {
            "raw_research_candidates": raw_event_count,
            "raw_summary_elite_events": len(matiger_events) + len(predictor_events),
            "raw_visible_b_elite_events": len(runlogger_scenes),
            "evidence_complete_candidates": len(evidence_complete),
            "visible_b_snapshot_complete_candidates": len(evidence_complete),
            "entry_a_evidence_complete_candidates": len(entry_a_complete),
            "current_backend_admissible_candidates": len(current_backend),
            "strict_exact_historical_replay_candidates": 0,
            "unique_source_run_groups": len(unique_external_group_tokens),
            "unique_external_run_groups_not_in_current_99": (
                len(unique_external_group_tokens) - matiger_baseline_overlap
            ),
            "current_baseline_overlap_run_groups": matiger_baseline_overlap,
            "net_new_scenes_relative_to_current_99": 0,
            "net_new_run_groups_relative_to_current_99": 0,
            "prefix_elite_rows": prefix_alignment["prefix_elite_row_count"],
            "prefix_elite_source_index_matches": prefix_alignment["source_index_matched_row_count"],
            "prefix_elite_source_index_unmatched": prefix_alignment[
                "source_index_unmatched_or_ambiguous_row_count"
            ],
            "prefix_claimed_evidence_complete_elites": prefix_alignment[
                "prefix_evidence_complete_claim_count"
            ],
            "prefix_claimed_backend_elites_withdrawn": prefix_alignment[
                "prefix_backend_claims_withdrawn_count"
            ],
            "prefix_elites_burning_unknown": prefix_alignment["burning_unknown_count"],
        },
        "deduplication": {
            "rule": "connected identity components of play_id, source seed, raw SHA; same source run and mirror aliases count once",
            "matiger_predictor_play_id_intersection": len(matiger_ids[0] & predictor_ids[0]),
            "matiger_predictor_seed_intersection": len(matiger_ids[1] & predictor_ids[1]),
            "matiger_predictor_raw_sha_intersection": len(matiger_ids[2] & predictor_ids[2]),
            "runlogger_seed": next(iter(runlogger_identity)),
            "same_source_group_count": source_groups_total,
        },
        "sources": source_summary,
        "summary_elite_events": [*matiger_events, *predictor_events],
        "prefix_elite_crosswalk": prefix_crosswalk,
        "prefix_alignment": prefix_alignment,
        "evidence_complete_b_candidates": evidence_complete,
        "runlogger_raw_evidence": raw_elite_evidence,
        "runlogger_run_state": copy.deepcopy(run_state),
        "source_metadata": read_source_metadata(),
        "policy_notes": [
            "summary .run 的 master_deck、relics、potions_obtained 和 floor metrics 不倒填入口 A",
            "green_key_taken_log 不能单独把其他精英标成普通；未知 burning/modifier 始终保留 unknown",
            "runlogger 的 final_act=false 只用于该具体 A0 run 的不可生成条件，不外推到其他 run",
            "visible B complete 不代表 internal state complete，也不代表 current PublicBattleEnv 可接入",
            "不创建任何标准派生燃烧/普通新任务；本报告只记录原始来源审计",
        ],
    }


def compact_counter(value: dict[str, Any]) -> str:
    """把字典渲染为稳定的 Markdown 行。"""

    return ", ".join(f"{key}={val}" for key, val in value.items()) or "无"


def markdown_b_candidate(scene: dict[str, Any]) -> str:
    """渲染唯一 B 快照的完整公开内容。"""

    entry = scene["entry_b"]
    deck = ", ".join(str(card) for card in entry["deck"])
    relics = json.dumps(entry["relics"], ensure_ascii=False, separators=(",", ":"))
    potions = json.dumps(entry["potions"], ensure_ascii=False, separators=(",", ":"))
    enemies = json.dumps(entry["enemies"], ensure_ascii=False, separators=(",", ":"))
    piles = json.dumps(entry["piles"], ensure_ascii=False, separators=(",", ":"))
    return "\n".join(
        [
            "### runlogger A0 / floor 7 / Gremlin Nob（入口 B）",
            "",
            f"- source seed：`{scene['source_seed']}`；STS：`{scene['source_build']}`；raw line：`{entry['source_state_line']}`。",
            f"- burning：`ordinary=true`、`burning=false`，证据状态 `{scene['burning_evidence']['status']}`；不是默认值。该 run 的 `final_act=false`，固定版本 `setEmeraldElite` 在此条件下直接返回。",
            f"- player：HP `{entry['player']['hp']}/{entry['player']['max_hp']}`，gold `{entry['player']['gold']}`，energy `{entry['player']['combat']['energy']['value']}`，block `{entry['player']['combat']['block']['value']}`。",
            f"- 完整入口牌组记录：`{deck}`。",
            f"- 完整遗物记录：`{relics}`。",
            f"- 完整药水槽：`{potions}`。",
            f"- 初始公开敌人：`{enemies}`。",
            f"- 牌区（条件省略按源码证明为空，不是猜测）：`{piles}`。",
            "- B 的内部状态仍未证明；当前契约只接受入口 A，且 `NeowsBlessing`/`StoneCalendar` 等真实遗物不能删除来凑场景。",
        ]
    )


def render_prefix_crosswalk_rows(rows: list[dict[str, Any]]) -> list[str]:
    """渲染前缀扩展全部精英行的逐场交叉表。"""

    targets = {
        "run-group:53c16194b16286bd892d:floor-7:combat-0",
        "run-group:f2672b82929351d73ae6:floor-6:combat-0",
    }
    lines = [
        "| 重点 | source path | raw SHA | source seed | floor | 精英 | 前缀内容/历史 | 房间 | burning/强化 | 前缀声称 | 最终后端 | 最终缺失 |",
        "|---|---|---|---:|---:|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        history = row["entry_player_content_and_history"]["prefix"]
        prefix_flags = row["prefix_claimed_flags"]
        room = row["target_elite_room"]
        source_path = str(row.get("source_path", "")).replace("|", "\\|")
        missing = "; ".join(row["final_missing"])
        prefix_content = (
            "声称已恢复（待 P1/P2）"
            if history["prefix_claimed_entry_content"]
            else "未恢复"
        )
        room_text = "已确认" if room["status"].startswith("confirmed") else "路径矛盾/未知"
        prefix_flags_text = (
            f"R={int(prefix_flags['raw_research_candidate'])}/"
            f"E={int(prefix_flags['evidence_complete'])}/"
            f"B={int(prefix_flags['backend_admissible'])}"
        )
        focus = "重点" if row.get("prefix_scene_id") in targets else ""
        lines.append(
            "| "
            + " | ".join(
                [
                    focus,
                    source_path,
                    str(row.get("raw_sha256")),
                    str(row.get("source_seed")),
                    str(row.get("floor")),
                    str(row.get("encounter_label")),
                    prefix_content,
                    room_text,
                    "unknown",
                    prefix_flags_text,
                    "0（撤回/未准入）",
                    missing,
                ]
            )
            + " |"
        )
    return lines


def render_prefix_focus_details(rows: list[dict[str, Any]]) -> list[str]:
    """渲染用户点名的两条前缀候选完整 A payload。"""

    targets = {
        "run-group:53c16194b16286bd892d:floor-7:combat-0",
        "run-group:f2672b82929351d73ae6:floor-6:combat-0",
    }
    lines: list[str] = []
    for row in rows:
        if row.get("prefix_scene_id") not in targets:
            continue
        content = row["entry_player_content_and_history"]["prefix_candidate_content"]
        lines.extend(
            [
                f"### {row['prefix_scene_id']}",
                "",
                f"source path：`{row['source_path']}`；raw SHA：`{row['raw_sha256']}`；source seed：`{row['source_seed']}`；floor：`{row['floor']}`；encounter：`{row['encounter_label']}`。",
                "前缀 agent 的完整 candidate payload 原样如下；它只能证明前缀 agent 当时的内容重建结果，不覆盖 burning gate 或主审 P2 退回状态。",
                "",
                "```json",
                json.dumps(content, ensure_ascii=False, indent=2),
                "```",
                "",
                "交叉结论：入口玩家内容/历史前缀为“前缀候选声称已恢复、待 P1/P2 复核”；目标房间由来源精英事件和 `path_per_floor=E` 确认；普通/燃烧均未证明，强化类型未证明；当前后端状态撤回。",
                "",
            ]
        )
    return lines


def render_report(audit: dict[str, Any]) -> str:
    """生成审计报告。"""

    counts = audit["counts"]
    sources = audit["sources"]
    alignment = audit["prefix_alignment"]
    lines = [
        "# 公开精英战斗来源审计",
        "",
        f"审计日期：{AUDIT_DATE}。本报告只审计真实公开记录和记录器字段，不修改正式环境、中央契约、现有 manifest、`eval_seeds.json` 或 PPO。",
        "",
        "## 结论",
        "",
        "当前来源索引得到 **0 个直接入口 A 完整候选、0 个当前后端可接入候选**。这不表示 summary A 永远不可恢复：`public-derived-standard-v1` 允许用通过审查的完整历史前缀派生 A，药水可按 canonical inventory 规范化，隐藏 RNG/队列可由版本化环境 seed 重采样。当前唯一仍未销账的精英闸门是燃烧状态/强化证据。",
        f"前缀扩展的 {alignment['prefix_elite_row_count']} 条精英行中，{alignment['source_index_matched_row_count']} 条按 raw SHA + floor + encounter 精确匹配来源索引；前缀 agent 声称 evidence_complete {alignment['prefix_evidence_complete_claim_count']} 条、backend_admissible {alignment['prefix_backend_admissible_claim_count']} 条，但其中 {alignment['prefix_backend_claims_withdrawn_count']} 条后端声称必须撤回。所有 {alignment['burning_unknown_count']} 条前缀精英的 burning/强化仍为 unknown。",
        "找到 1 个可核查的入口 B 可见快照：A0、第一幕楼层 7、Gremlin Nob；它保留完整公开牌组/升级字符串、HP/maxHP、金币、遗物、药水、手牌/抽牌堆和敌方开战快照，但不等于完整内部状态，也不能倒填入口 A。相对当前 99 场库，净新增为 **0 场、0 个 run 关联组**。",
        "",
        "摘要来源共得到 890 条第一幕精英事件记录（425 条 MaT1g3R A20、465 条 FightPredictor A20）和 1 条 runlogger B 快照。摘要日志本身不是完整 A，但在历史前缀证据完整且燃烧闸门独立通过时，可以按规则派生 A；本报告不把摘要缺少原始药水槽/RNG/队列写成永久拒绝。",
        "",
        "## 计数口径",
        "",
        "| 指标 | 实际数量 | 说明 |",
        "|---|---:|---|",
        f"| 原始可研究候选 | {counts['raw_research_candidates']} | 425 条 summary 精英事件 + 465 条 summary 精英事件 + 1 条真实 B 快照；事件可重复属于同一 run 的不同战斗 |",
        f"| 摘要型精英事件 | {counts['raw_summary_elite_events']} | 有精英名称/楼层/伤害摘要，但没有完整 A/B 状态 |",
        f"| 可见 B 快照完整候选 | {counts['visible_b_snapshot_complete_candidates']} | 仅 runlogger 1 条；这里的“完整”指公开可见 B 字段，不指 exact replay/internal state |",
        f"| 入口 A 证据完整候选 | {counts['entry_a_evidence_complete_candidates']} | 必须有入口时点和完整内容；本轮为 0 |",
        f"| 当前后端可接入候选 | {counts['current_backend_admissible_candidates']} | 当前 `PublicBattleEnv` 只接受 A，B 没有输入接口 |",
        f"| 当前 99 场净新增 | {counts['net_new_scenes_relative_to_current_99']} 场 / {counts['net_new_run_groups_relative_to_current_99']} 组 | 按 run 关联组去重 |",
        f"| 前缀精英逐场交叉行 | {counts['prefix_elite_rows']} | {counts['prefix_elite_source_index_matches']} 条匹配来源索引，{counts['prefix_elite_source_index_unmatched']} 条未匹配 |",
        f"| 前缀声称完整但 burning 未证 | {counts['prefix_claimed_evidence_complete_elites']} | 包含两条静态放行记录，全部撤回到研究/待审层 |",
        "",
        "当前基线核对：manifest 共 257 条保留记录，其中内容准入 99 场、75 个 run 组；已准入精英为 0。这里沿用 `docs/public-battle-implementation.md` 的当前 99 场状态，不把历史 `m2-corpus-report.md` 回填为当前结论。",
        "",
        "## 分来源实际审计",
        "",
        "| 来源 | 固定版本 | 原始样本 | 独立 run 组 | 第一幕精英事件 | B 完整 | A 完整 | 当前后端 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
        f"| MaT1g3R `.run` | `{sources['matiger']['commit']}` | {sources['matiger']['raw_file_count']} 文件（{sources['matiger']['duplicate_alias_files']} 个镜像） | {sources['matiger']['independent_run_groups']} | {sources['matiger']['elite_event_count']} | 0 | 0 | 0 |",
        f"| FightPredictor `.run` | `{sources['fight_predictor']['commit']}` | {sources['fight_predictor']['raw_file_count_in_archive']} 文件；Ironclad {sources['fight_predictor']['ironclad_raw_file_count']} | {sources['fight_predictor']['elite_run_groups']} 个含精英 | {sources['fight_predictor']['elite_event_count']} | 0 | 0 | 0 |",
        f"| colinking/runlogger JSONL | `{sources['runlogger']['commit']}` | {sources['runlogger']['record_count']} 行、1 run | 1 | {sources['runlogger']['elite_b_snapshot_count']} | 1（B） | 0 | 0 |",
        "",
        "## 固定提交、SHA256 与许可",
        "",
        "| 证据对象 | 固定版本/路径 | SHA256 | 许可/限制 |",
        "|---|---|---|---|",
        f"| MaT1g3R 原始 ZIP | `{sources['matiger']['archive']}` | `{sources['matiger']['archive_sha256']}` | 仓库声明 Apache-2.0；原始玩家记录的再分发范围未单独核实 |",
        f"| FightPredictor 原始 ZIP | `{sources['fight_predictor']['archive']}` | `{sources['fight_predictor']['archive_sha256']}` | 固定树无 LICENSE；使用和再分发未知 |",
        f"| runlogger 原始 JSONL | `{RUNLOGGER_RAW.relative_to(ROOT).as_posix()}` | `{sources['runlogger']['raw_sha256']}` | 来源仓库 MIT；示例数据的单独再分发限制未声明 |",
        f"| runlogger 源码 ZIP | `{RUNLOGGER_ARCHIVE.relative_to(ROOT).as_posix()}` | `{audit['source_metadata']['runlogger_archive']['sha256']}` | 固定提交源码证据 |",
        f"| GameStateConverter.java | `{audit['source_metadata']['runlogger_source_files']['GameStateConverter.java']['path']}` | `{audit['source_metadata']['runlogger_source_files']['GameStateConverter.java']['sha256']}` | 字段语义证据 |",
        f"| FightPredictor main.py | `{audit['source_metadata']['predictor_source_files']['main.py']['path']}` | `{audit['source_metadata']['predictor_source_files']['main.py']['sha256']}` | 派生字段语义证据 |",
        "",
        "### MaT1g3R A20 summary",
        "",
        f"- 精英事件：{sources['matiger']['elite_by_encounter']}；楼层：{sources['matiger']['elite_by_floor']}；来源构建：{sources['matiger']['source_builds']}；进阶：{sources['matiger']['ascensions']}。",
        f"- `path_per_floor` 为 `E` 的事件 {sources['matiger']['path_symbol_counts'].get('E', 0)} 条，`?`/未知 {sum(value for key, value in sources['matiger']['path_symbol_counts'].items() if key != 'E')} 条；路径未知不能放行。",
        f"- 有 {sources['matiger']['same_floor_green_key_observation_count']} 条事件的 `green_key_taken_log` 恰好等于该精英楼层；这只作为钥匙日志观察，不恢复燃烧强化。其余精英不能因为“没有同楼层钥匙”就设为普通。",
        "- 这只是来源自身的 summary：`master_deck` 是终局字段，不能直接冒充入口牌组；当时遗物计数、药水槽位和完整前缀也没有在单条摘要中直接记录。但这不是 A 的永久阻塞：通过完整历史前缀可以恢复玩家内容；药水在获得/使用/丢弃顺序已证实时可使用 canonical inventory 槽位；敌人、手牌、牌堆和隐藏 RNG 可由 A 的版本化环境 seed 重采样。",
        "- 当前仍拒绝的原因是 `PREFIX_HISTORY_REQUIRED_FOR_A_DERIVATION`（来源索引自身没有完整前缀）、`BURNING_ELITE_FLAG_AND_STRENGTHENING_TYPE_UNRECORDED`；7 条路径符号矛盾/未知另加 `ELITE_LABEL_AND_PATH_SYMBOL_CONFLICT_OR_UNKNOWN`。这不是把 summary 判定为永远不可恢复。",
        "",
        "### FightPredictor / Slay-I",
        "",
        f"- 原始 `.run`：590 文件，198 个 Ironclad；其中 197 个 A20、1 个 A0。第一幕精英事件 465 条，全部来自 A20，Gremlin Nob/Lagavulin/3 Sentries 分别为 {sources['fight_predictor']['elite_by_encounter']}。",
        f"- 该仓库 `out/` 另有 {sources['fight_predictor']['derived_outputs']['row_count']} 条派生 fight row（Ironclad {sources['fight_predictor']['derived_outputs']['rows_by_character'].get('IRONCLAD', 0)}，Ironclad 第一幕精英 {sources['fight_predictor']['derived_outputs']['ironclad_act1_elite_row_count']}）。这只能作为分布/预测器研究数据，不能当作完整初态库；派生行没有 run ID，且字段不含金币、药水库存、燃烧标志和 B 牌区。",
        f"- 465 条中 `path_per_floor=E` 为 {sources['fight_predictor']['path_symbol_counts'].get('E', 0)} 条，另有 {sum(value for key, value in sources['fight_predictor']['path_symbol_counts'].items() if key != 'E')} 条精英名称与路径符号不一致或未知；矛盾不修补。",
        "- 该固定提交的 README 声称数据来自 Spire Logs/Jorbs，并声称训练超过 325,000 fights；本审计没有把这种声明升级为保留逐 run 入口证据。固定树中没有 LICENSE，使用/再分发限制未知。",
        "- 当前不准入的原因仍是缺少可验证的完整历史前缀/入口时点与 burning/modifier；药水槽和隐藏随机状态本身不是永久拒绝条件，但该来源没有足够历史证据把它们安全推导出来。",
        "",
        "### colinking/runlogger 真实 B 快照",
        "",
        *markdown_b_candidate(audit["evidence_complete_b_candidates"][0]).splitlines(),
        "",
        "- B 的 `discard_pile`、`exhaust_pile`、`limbo` 缺键由 `GameStateConverter.java` 的“仅非空才写入”逻辑证明为空；遗物缺 `counter` 由“仅 counter > -1 才写入”解释，未当作未知或凭空补值。",
        "- 精英/燃烧证据：记录器没有直接 burning 字段。该具体 run 的 `state:run.unlocks.final_act=false`，锁定版本 `setEmeraldElite` 在 `Settings.isFinalActAvailable=false` 时提前返回，因此该 run 不可能生成燃烧精英；这不是对其他 run 的外推。强化类型因此为 `not_applicable`，而不是猜测一个数值。",
        "- 入口 A 不能由此 B 倒填：第 49 行快照紧跟 `action:select_map`，已存在 `combat_state`、手牌和敌人。记录器没有 pre-entry map-node modifier、输入队列、实例 ID 和 RNG 完整恢复。",
        "",
        "### B 快照字段逐项边界",
        "",
        "- 直接记录：`state:floor` 的 floor、room_type、HP/maxHP、gold、完整 deck 字符串、relics、potions、`combat_state.monsters`、draw_pile、hand、player.energy；地图动作还直接给出 `select_map` 的 symbol/x/y。",
        "- 依据序列化源码恢复：空 discard/exhaust/limbo、空 player/monster powers、零 block；这些字段只在非空/大于零时写入。缺失遗物 counter 表示序列化器未写出 `counter > -1`，不等于擅自设为未知计数 0。",
        "- 仍缺失的可见动态字段：直接 `hasEmeraldKey`/burning flag/强化类型、卡牌当前费用和名称以外的每副本运行时属性，以及该快照没有出现的正向意图伤害/段数字段。卡牌名称中的 `+` 只证明该显示字符串，不等于完整 CardInstance。",
        "- 继续执行所需内部状态：`InputState`、ActionQueue/CardQueue、CardInstance ID 与动态值、后端牌堆顺序、敌人 move/history/miscInfo、遗物 bit/data、药水容量/计数、RNG stream/counter。故该 B 是可见快照研究证据，不是可继续执行的完整状态。",
        "",
        "## A/B 入口与字段审计",
        "",
        "| 来源 | 入口 A | 入口 B | burning / 强化 | 当前接口结论 |",
        "|---|---|---|---|---|",
        "| MaT1g3R `.run` | 来源自身未直接记录；可由通过审查的历史前缀派生，但本轮未完成；0 | 不可用 | 每场 `unknown`；green key 不足 | 0 |",
        "| FightPredictor | 摘要/派生；理论上需另有完整前缀，本来源未证明；0 | 不可用 | 每场 `unknown`；路径矛盾保留 | 0 |",
        "| runlogger | 不可用；0 | 1 个可见字段完整，internal unproven | 该 A0 run `ordinary=true/burning=false` 有不可生成条件 | B 接口待实现；0 |",
        "",
        "## 与前缀扩展逐场对齐",
        "",
        f"前缀候选文件中共有 {alignment['prefix_elite_row_count']} 条精英行：{alignment['source_index_matched_row_count']} 条按 `raw_sha256 + floor + encounter_label` 与来源索引精确匹配，未匹配/歧义 {alignment['source_index_unmatched_or_ambiguous_row_count']} 条。前缀 agent 有 {alignment['prefix_raw_research_candidate_count']} 条 payload/研究候选声称恢复玩家内容和历史链，另外 {alignment['prefix_elite_row_count'] - alignment['prefix_raw_research_candidate_count']} 条没有完整 candidate；前者仍受 P2 复核约束。前缀 agent 声称 `evidence_complete` {alignment['prefix_evidence_complete_claim_count']} 条、`backend_admissible` {alignment['prefix_backend_admissible_claim_count']} 条；后者全部按燃烧闸门撤回。所有 {alignment['burning_unknown_count']} 条前缀精英的 burning/强化仍为 unknown，目标房间明确确认 {alignment['room_confirmed_count']} 条，路径矛盾/未知 {alignment['room_path_conflict_or_unknown_count']} 条。逐行完整字段见 `reference/public-elite-sources/prefix-elite-crosswalk.json`，并在下表保留 source path、raw SHA、source seed、楼层和最终缺失项。",
        "",
        "前缀内容/历史列表示前缀 agent 的事实声称，不等于主审最终准入；`声称已恢复（待 P1/P2）` 表示候选 payload 和链存在，P2 事件/药水审计仍需先修复。burning/强化列全部为 `unknown`；A0 B 的 `final_act=false` 证明不外推到这些 A20 summary。",
        "",
        *render_prefix_focus_details(audit["prefix_elite_crosswalk"]),
        *render_prefix_crosswalk_rows(audit["prefix_elite_crosswalk"]),
        "",
        "## 去重与偏差补充价值",
        "",
        "- MaT1g3R 203 个文件按 `play_id + seed_played + raw SHA` 连通分量去重为 157 个 run 组；FightPredictor 590 个文件中的 Ironclad 198 组，第一幕精英覆盖 195 组；runlogger 1 组。跨 MaT1g3R/FightPredictor 的 play_id、seed、raw SHA 交集均为 0。",
        f"- 去重后本轮精英来源共 {counts['unique_source_run_groups']} 个外部 run 组；其中与当前 99 场同源的 MaT1g3R 组 {counts['current_baseline_overlap_run_groups']} 个，但由于它们没有产生新的 A/后端候选，净增仍为 0。",
        "- 偏差价值：MaT1g3R 提供 2022 年 A20 的 425 条 Act 1 精英事件，FightPredictor 提供 2018--2019 年多构建/多进阶摘要及大量派生 fight row；它们适合作为后续记录器设计的目标覆盖和分布诊断，不足以直接进入当前完整初态库。runlogger 只提供 A0 单局 B 样本，不能代表 A20。",
        "",
        "## 无效来源与检索边界",
        "",
        "- 只含胜负、终局牌组、Spire Logs 统计网页或预测器派生 row 的来源均未作为完整初态候选；保留固定仓库/文件作为淘汰证据。",
        "- 定向检索了 `runlogger / Serialization Mod / combat_state / elite`、公开详细战斗日志，以及 Spire Logs 原始下载入口；SearXNG 对第二组精确查询无结果，Tavily/Doubao 主要重复命中 runlogger、MaT1g3R 和预测器，未得到第二个可下载的 A20 精英 B 快照源。按任务边界在两条无效路径后停止泛搜，不宣称穷尽互联网。",
        "- 预测器仓库的原始数据声明来自 Spire Logs/Jorbs，但没有固定的 Spire Logs 原始包、逐 run 许可证和入口快照 schema，故标为声明/待审而非完整来源。",
        "",
        "## 最小缺失字段与主 agent 决策",
        "",
        "如果要把真实精英加入当前 A 库，记录器至少要在地图节点进入战斗前或同一不可分割事务中写出：",
        "",
        "1. `character`、原始 `ascension`、STS build、act/floor、room type、map node 坐标和 `hasEmeraldKey`/燃烧标志；燃烧时记录实际强化类型或可复核的强化字段。",
        "2. 该时点的完整 master deck 副本/升级、HP/maxHP、gold、遗物及动态计数、药水槽位/容量；所有不支持内容原样保留。",
        "3. 若输出 B，则同时保存初始化后的 hand/draw/discard/exhaust/limbo、energy/block、敌人 HP/intent/powers，以及继续运行所需 queue、CardInstance、内部牌序和 RNG 依赖；若只输出 A，必须明确由版本化环境 seed 重新采样并设置 `exact_historical_replay=false`。",
        "4. 记录器版本、游戏版本、完整 mod 清单、原始文件 SHA256、许可/再分发限制和 run/play identity。",
        "",
        "主 agent 需要决定：是否另建 B 输入接口；是否把该 1 条 A0 B 快照仅作为诊断夹具；以及是否实现一个带 pre-entry hook + `hasEmeraldKey`/燃烧 modifier 字段的版本锁定 Serialization Mod fork。以上决定都不在本任务中自动修改。",
        "",
        "## 复现与新增文件",
        "",
        "```powershell",
        "python scripts/audit-public-elite-sources.py",
        "python -m pytest -q tests/test_public_elite_sources.py",
        "git diff --check",
        "```",
        "脚本读取固定 ignored reference 输入并重写两个报告 JSON/Markdown；不下载未知数据，不修改正式 manifest。",
        "",
        "新增/本任务维护文件：",
        "",
        "- `scripts/audit-public-elite-sources.py`：独立解析器、哈希校验、去重和报告生成。",
        "- `tests/test_public_elite_sources.py`：JSONL/B 快照、条件省略、摘要 unknown、去重和 A/B 接口边界测试。",
        "- `docs/public-elite-source-report.md`：本报告。",
        "- `docs/public-elite-source-candidates.json`：逐摘要事件和逐 B 候选机器索引。",
        "- `reference/public-elite-sources/`：固定 runlogger/predictor 原始包、源码证据、B 原始快照证据及 `prefix-elite-crosswalk.json`，均为 ignored reference。",
        "",
        "## 来源链接",
        "",
        f"- [runlogger 固定 README](https://github.com/colinking/runlogger/blob/{RUNLOGGER_COMMIT}/README.md)；[GameStateConverter.java](https://github.com/colinking/runlogger/blob/{RUNLOGGER_COMMIT}/src/main/java/serializationmod/GameStateConverter.java)；[示例 JSONL](https://raw.githubusercontent.com/colinking/runlogger/{RUNLOGGER_COMMIT}/runs/ironclad_1706139943.json)；[LICENSE](https://raw.githubusercontent.com/colinking/runlogger/{RUNLOGGER_COMMIT}/LICENSE)。",
        f"- [MaT1g3R/Slay-the-Spire-data 固定提交](https://github.com/MaT1g3R/Slay-the-Spire-data/tree/{MATIGER_COMMIT})。",
        f"- [SlayTheSpireFightPredictor 固定提交](https://github.com/alexdriedger/SlayTheSpireFightPredictor/tree/{PREDICTOR_COMMIT})；其 [README](https://github.com/alexdriedger/SlayTheSpireFightPredictor/blob/{PREDICTOR_COMMIT}/README.md) 仅作为来源声明证据。",
        "- 本地精确机制证据：`reference/sts1-decompiled/m2-entry-a/abstract-dungeon.txt:1342-1347`、`abstract-player.txt:5246-5252`；仅用于规格争议仲裁，不复制进模拟器。",
        "",
    ]
    return "\n".join(lines)


def write_outputs(audit: dict[str, Any]) -> None:
    """写入任务指定的机器索引、报告和 ignored 原始证据。"""

    CANDIDATE_OUTPUT.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    REPORT_OUTPUT.write_text(render_report(audit), encoding="utf-8")
    PREFIX_CROSSWALK_OUTPUT.write_text(
        json.dumps(
            {
                "schema": "public-prefix-elite-crosswalk-v1",
                "audit_date": AUDIT_DATE,
                "source_prefix_candidates": str(PREFIX_CANDIDATES.relative_to(ROOT)).replace("\\", "/"),
                "source_elite_candidates": str(CANDIDATE_OUTPUT.relative_to(ROOT)).replace("\\", "/"),
                "summary": audit["prefix_alignment"],
                "rows": audit["prefix_elite_crosswalk"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    evidence = {
        "schema": "runlogger-elite-raw-evidence-v1",
        "source": {
            "path": str(RUNLOGGER_RAW.relative_to(ROOT)).replace("\\", "/"),
            "sha256": audit["sources"]["runlogger"]["raw_sha256"],
            "source_url": audit["sources"]["runlogger"]["source_url"],
            "commit": RUNLOGGER_COMMIT,
        },
        "run_state": audit["runlogger_run_state"],
        "elite_snapshots": audit["runlogger_raw_evidence"],
        "field_semantics": audit["sources"]["runlogger"]["field_semantics_source"],
    }
    EVIDENCE_OUTPUT.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    """命令行入口。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="只执行审计并打印计数，不重写任务输出文件",
    )
    args = parser.parse_args(argv)
    audit = build_audit()
    if not args.no_write:
        write_outputs(audit)
    print(json.dumps(audit["counts"], ensure_ascii=False, sort_keys=True))
    for name, source in audit["sources"].items():
        print(
            f"{name}: raw={source.get('raw_file_count', source.get('raw_file_count_in_archive'))} "
            f"groups={source.get('independent_run_groups')} elite={source.get('elite_event_count', source.get('elite_b_snapshot_count'))}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
