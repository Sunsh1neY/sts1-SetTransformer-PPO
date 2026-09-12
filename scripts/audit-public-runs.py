"""下载并审计公开 STS1 run 数据，生成 M2 战斗初态证据。"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import ssl
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


AUDIT_SCHEMA_VERSION = "m2-public-run-audit-v2"
PUBLIC_RUN_REPOSITORY = "MaT1g3R/Slay-the-Spire-data"
PUBLIC_RUN_COMMIT = "097aaf3564c2247835162d267cbc7c55d2c9039e"
RUNLOGGER_REPOSITORY = "colinking/runlogger"
RUNLOGGER_COMMIT = "02679f51c19c7a8d26da618ec0377faa390f347f"
RUNLOGGER_EXAMPLE_PATH = "runs/ironclad_1706139943.json"
ARCHIVE_METADATA_URL = "https://archive.org/metadata/slay-the-data.-7z"
ARCHIVE_ITEM_URL = "https://archive.org/details/slay-the-data.-7z"
GITHUB_API = "https://api.github.com"
USER_AGENT = "sts-rl-field-audit/1.0"

SUMMARY_FIELDS = (
    "character_chosen",
    "ascension_level",
    "build_version",
    "master_deck",
    "relics",
    "current_hp_per_floor",
    "max_hp_per_floor",
    "damage_taken",
    "path_per_floor",
    "card_choices",
    "event_choices",
    "campfire_choices",
)

INSTRUMENTATION_MODS = {
    "CommunicationMod",
    "SerializationMod",
    "runlogger",
}

# 这里只用于发现“本 run 曾经出现过计数”的动态遗物。没有列出的遗物不能被
# 自动认为没有计数；契约仍要求保留原始字段并在未知时拒绝正式纳入。
KNOWN_DYNAMIC_RELICS = {
    "NeowsBlessing",
    "StoneCalendar",
    "InkBottle",
    "Nunchaku",
    "Pen Nib",
    "Shuriken",
    "Kunai",
    "Ornamental Fan",
    "Gambling Chip",
    "Centennial Puzzle",
    "The Boot",
    "Self Forming Clay",
    "Tingsha",
    "Letter Opener",
    "Sundial",
}

ENCOUNTER_GROUPS = {
    ("Cultist",): {"scenario_id": "cultist", "backend_id": "CULTIST"},
    ("JawWorm",): {"scenario_id": "jaw-worm", "backend_id": "JAW_WORM"},
    ("FuzzyLouseDefensive", "FuzzyLouseNormal"): {
        "scenario_id": "two-louse",
        "backend_id": "TWO_LOUSE",
    },
    ("FuzzyLouseNormal", "FuzzyLouseDefensive"): {
        "scenario_id": "two-louse",
        "backend_id": "TWO_LOUSE",
    },
}

CARD_PATTERN = re.compile(r"^(?P<name>.+?)(?:\+(?P<upgrades>[1-9][0-9]*))?$")

# 这是 M2 审计使用的最小语义注册表，不是 M3 正式后端 registry。未列入的
# 实体仍保留原文，但不能被审计工具默认为可运行。
AUDIT_CARD_REGISTRY: dict[str, dict[str, Any]] = {
    "Strike_R": {
        "registry_id": 3,
        "canonical_name": "Strike",
        "target_kind": "ENEMY",
        "dynamic_semantics": "fixed_damage",
        "generation": None,
    },
    "Defend_R": {
        "registry_id": 2,
        "canonical_name": "Defend",
        "target_kind": "NO_TARGET",
        "dynamic_semantics": "fixed_block",
        "generation": None,
    },
    "Bash": {
        "registry_id": 1,
        "canonical_name": "Bash",
        "target_kind": "ENEMY",
        "dynamic_semantics": "damage_and_vulnerable",
        "generation": None,
    },
    "Anger": {
        "registry_id": 4,
        "canonical_name": "Anger",
        "target_kind": "ENEMY",
        "dynamic_semantics": "damage_and_discard_copy",
        "generation": {"zone": "discard", "copies_per_play": 1},
    },
}

AUDIT_RELIC_REGISTRY: dict[str, dict[str, Any]] = {
    "Burning Blood": {
        "registry_id": 1,
        "counter_semantics": "not_applicable",
        "parameters": [],
        "runtime_status": "exit_heal_and_reward_timing_pending",
    },
    # runlogger 的来源字符串是 NeowsBlessing；后端实际枚举为 NEOWS_LAMENT。
    "NeowsBlessing": {
        "registry_id": 2,
        "backend_id": "NEOWS_LAMENT",
        "counter_semantics": "source_combat_charge; decrement_point_pending",
        "parameters": ["remaining_charges"],
        "runtime_status": "counter_source_present_but_hook_pending",
    },
    "StoneCalendar": {
        "registry_id": 3,
        "counter_semantics": "source_counter; trigger_threshold_and_timing_pending",
        "parameters": ["counter"],
        "runtime_status": "counter_source_present_but_hook_pending",
    },
}

AUDIT_POTION_REGISTRY: dict[str, dict[str, Any]] = {
    # 当前公开候选只有 null 空槽；非空类型仅记录为观察到但未批准。
    "BloodPotion": {
        "registry_id": 1,
        "target_kind": "NO_TARGET",
        "parameter_semantics": "potency_and_sacred_bark_branch_pending",
        "formal_status": "observed_deferred",
    },
    "Weak Potion": {
        "registry_id": 2,
        "target_kind": "ENEMY",
        "parameter_semantics": "weak_amount_and_duration_pending",
        "formal_status": "observed_deferred",
    },
}

AUDIT_MONSTER_REGISTRY: dict[str, dict[str, Any]] = {
    "Cultist": {"registry_id": 1, "semantic_status": "known_id_pending_full_runtime"},
    "JawWorm": {"registry_id": 2, "semantic_status": "known_id_pending_full_runtime"},
    "AcidSlime_S": {"registry_id": 3, "semantic_status": "observed_deferred"},
    "SpikeSlime_M": {"registry_id": 4, "semantic_status": "observed_deferred"},
    "GremlinNob": {"registry_id": 5, "semantic_status": "observed_deferred"},
    "AcidSlime_M": {"registry_id": 6, "semantic_status": "observed_deferred"},
    "Looter": {"registry_id": 7, "semantic_status": "observed_deferred"},
    "SlaverRed": {"registry_id": 8, "semantic_status": "observed_deferred"},
    "SlimeBoss": {"registry_id": 9, "semantic_status": "observed_deferred"},
}

AUDIT_STATUS_REGISTRY: dict[str, dict[str, Any]] = {
    "Strength": {"registry_id": 1, "parameter": "amount"},
    "Vulnerable": {"registry_id": 2, "parameter": "remaining_turns"},
    "Weak": {"registry_id": 3, "parameter": "remaining_turns"},
    "Artifact": {"registry_id": 4, "parameter": "charges"},
    "Ritual": {"registry_id": 5, "parameter": "amount"},
    "Thievery": {"registry_id": 6, "parameter": "amount"},
    "Split": {"registry_id": 7, "parameter": "amount"},
    "Anger": {"registry_id": 8, "parameter": "amount"},
}

KNOWN_INTENTS = {"ATTACK", "ATTACK_DEBUFF", "ATTACK_DEFEND", "BUFF", "DEBUFF", "STRONG_DEBUFF", "DEFEND_BUFF"}
ATTACK_INTENTS = {"ATTACK", "ATTACK_DEBUFF", "ATTACK_DEFEND"}
MAX_AUDIT_HAND = 10
MAX_AUDIT_ENEMIES = 5
MAX_AUDIT_POTION_SLOTS = 3
MAX_AUDIT_FLOOR = 100
MAX_AUDIT_ENERGY = 20
MAX_AUDIT_DECK_ENTITIES = 100
REGISTERED_SOURCE_STS_VERSIONS = {"12-18-2022"}


def fetch(
    url: str,
    *,
    timeout: int = 40,
    attempts: int = 4,
    sleeper: Callable[[float], None] = time.sleep,
) -> bytes:
    """使用默认证书校验获取 HTTPS 内容，并对瞬时 EOF/超时重试。"""

    if attempts < 1:
        raise ValueError("attempts 必须为正整数")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    context = ssl.create_default_context()
    errors: list[str] = []
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout, context=context) as response:
                status = getattr(response, "status", None)
                if status is not None and not 200 <= int(status) < 300:
                    raise RuntimeError(f"HTTP 状态码 {status}")
                content = response.read()
                if not content:
                    raise RuntimeError("响应为空")
                return content
        except HTTPError as exc:
            errors.append(f"HTTP {exc.code}: {exc.reason}")
            # 4xx 通常是稳定的请求错误；429 和 5xx 仍允许重试。
            if 400 <= exc.code < 500 and exc.code != 429:
                break
        except (OSError, URLError, TimeoutError, RuntimeError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
        if attempt + 1 < attempts:
            sleeper(min(2.0**attempt, 8.0))
    detail = "; ".join(errors) if errors else "未知错误"
    raise RuntimeError(f"HTTPS 获取失败：{url}；尝试{attempts}次；{detail}")


def sha256_bytes(content: bytes) -> str:
    """返回原始字节的 SHA-256。"""

    return hashlib.sha256(content).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    """用稳定 JSON 编码计算证据索引哈希。"""

    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")
    )


def strict_integer(
    value: Any,
    field: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """只接受有限整数，拒绝布尔值、浮点、NaN、无穷和隐式截断。"""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} 必须为有限整数")
    if minimum is not None and value < minimum:
        raise ValueError(f"{field} 小于最小值 {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} 大于最大值 {maximum}")
    return value


def numeric_field_status(value: Any) -> str:
    """用于汇总来源的数值编码审计；summary 常把整数写成浮点。"""

    if isinstance(value, bool):
        return "invalid_boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return "integral_float_source_encoding"
    return "invalid_or_non_finite"


def write_json(path: Path, value: Any) -> None:
    """写入供审核者直接阅读的 UTF-8 JSON。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_json(content: bytes, source: str) -> dict[str, Any]:
    """解析并校验公开样本的 JSON 根节点。"""

    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source} 不是合法 JSON：{exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{source} 的 JSON 根节点必须是对象")
    return value


def parse_jsonl(content: bytes, source: str) -> list[dict[str, Any]]:
    """解析逐行 JSON；保留空行错误上下文但允许末尾换行。"""

    records: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(content.decode("utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source} 第{line_number}行不是合法 JSON：{exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{source} 第{line_number}行根节点必须是对象")
        value["_source_line"] = line_number
        records.append(value)
    if not records:
        raise ValueError(f"{source} 没有 JSON 记录")
    return records


def dataset_key(path: str) -> str:
    """从公开仓库路径取数据集名，用于可复现分层抽样。"""

    parts = path.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0] == "runs":
        return parts[1]
    return parts[0]


def select_sample_paths(paths: Iterable[str], limit: int) -> list[str]:
    """按数据集分层、按字典序轮询选取；不称为随机或代表性抽样。"""

    normalized = sorted(set(paths))
    if not normalized:
        raise ValueError("没有发现 Ironclad .run 文件")
    if not 1 <= limit <= 100:
        raise ValueError("小样本审计数量必须为1到100")

    groups: dict[str, list[str]] = defaultdict(list)
    for path in normalized:
        groups[dataset_key(path)].append(path)
    ordered_groups = sorted(groups)
    chosen: list[str] = []
    cursor = {key: 0 for key in ordered_groups}
    while len(chosen) < min(limit, len(normalized)):
        progressed = False
        for key in ordered_groups:
            index = cursor[key]
            if index >= len(groups[key]):
                continue
            chosen.append(groups[key][index])
            cursor[key] += 1
            progressed = True
            if len(chosen) == limit:
                break
        if not progressed:
            break
    return chosen


def run_group_key(character: Any, source_seed: Any, source_id: str) -> str:
    """把同一整局及其不同记录绑定到同一个泄漏检查组。"""

    if source_seed not in (None, ""):
        # 有来源 seed 时不把数据集名称拼入 key，避免同一局在 summary 与
        # detailed source 中被错误拆成两个组；缺 seed 才保留 source_id 以减少误合并。
        return f"seed:{character}:{source_seed}"
    return f"{source_id}:missing-seed:{character}"


def assign_group_split(group_keys: Iterable[str]) -> dict[str, str]:
    """按整局组做固定哈希划分；重复组直接报错，防止场景泄漏。"""

    unique = list(group_keys)
    if len(set(unique)) != len(unique):
        raise ValueError("同一 run group 不能重复出现在待划分组列表")
    assignments: dict[str, str] = {}
    for group_key in sorted(unique):
        bucket = int(hashlib.sha256(group_key.encode("utf-8")).hexdigest()[:8], 16) % 100
        if bucket < 80:
            split = "train"
        elif bucket < 90:
            split = "dev"
        else:
            split = "reserved-eval"
        assignments[group_key] = split
    return assignments


def parse_card_instance(value: Any, field: str) -> dict[str, Any]:
    """解析名称末尾的升级次数；没有 UUID 时保留源顺序作为临时实例序号。"""

    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} 必须是非空卡牌字符串")
    if value.endswith("+"):
        raise ValueError(f"{field} 的升级标记不完整：{value!r}")
    match = CARD_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(f"{field} 的卡牌升级格式无法解析：{value!r}")
    registry = AUDIT_CARD_REGISTRY.get(match.group("name"))
    return {
        "raw": value,
        "name": match.group("name"),
        "upgrade_count": int(match.group("upgrades") or 0),
        "upgrade_count_known": True,
        "registry_id": registry["registry_id"] if registry else None,
        "semantic_status": "registered" if registry else "unknown",
    }


def parse_card_list(values: Any, field: str) -> list[dict[str, Any]]:
    """解析一组卡牌并保留重复牌和源顺序。"""

    if not isinstance(values, list):
        raise ValueError(f"{field} 必须是数组")
    result = []
    for index, value in enumerate(values):
        card = parse_card_instance(value, f"{field}[{index}]")
        card["source_ordinal"] = index
        result.append(card)
    return result


def safe_parse_card_list(
    values: Any,
    field: str,
    reasons: list[str],
) -> tuple[list[dict[str, Any]], str | None, list[Any]]:
    """审计场景时保留原始卡牌，避免一个歧义字段中止整份报告。"""

    raw_values = list(values) if isinstance(values, list) else []
    try:
        return parse_card_list(values, field), None, raw_values
    except ValueError as exc:
        if "升级标记不完整" in str(exc) or "升级格式" in str(exc):
            reasons.append("UPGRADE_FORMAT_AMBIGUOUS")
        else:
            reasons.append("PILE_CARD_FIELD_INVALID")
        return [], str(exc), raw_values


def parse_relics(values: Any, field: str = "relics") -> list[dict[str, Any]]:
    """保留遗物 ID 和原始计数；省略计数绝不补成 0。"""

    if not isinstance(values, list):
        raise ValueError(f"{field} 必须是数组")
    result = []
    seen: set[str] = set()
    for index, value in enumerate(values):
        if not isinstance(value, dict) or not isinstance(value.get("id"), str):
            raise ValueError(f"{field}[{index}] 必须含字符串 id")
        relic_id = value["id"]
        if relic_id in seen:
            raise ValueError(f"{field} 出现重复遗物 {relic_id!r}")
        seen.add(relic_id)
        has_counter = "counter" in value
        counter = value.get("counter")
        if has_counter:
            counter = strict_integer(counter, f"{field}[{index}].counter", minimum=0)
        registry = AUDIT_RELIC_REGISTRY.get(relic_id)
        result.append(
            {
                "id": relic_id,
                "registry_id": registry["registry_id"] if registry else None,
                "backend_id": registry.get("backend_id") if registry else None,
                "semantic_status": "registered" if registry else "unknown",
                "counter": counter if has_counter else None,
                "counter_recorded": has_counter,
                "raw": dict(value),
            }
        )
    return result


def parse_potions(values: Any, field: str = "potions") -> list[str | None]:
    """校验药水槽位，不把缺少整个数组误当作空槽。"""

    if not isinstance(values, list) or not values:
        raise ValueError(f"{field} 必须是非空数组")
    result: list[str | None] = []
    for index, value in enumerate(values):
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{field}[{index}] 必须是字符串或 null")
        result.append(value)
    return result


def power_map(values: Any, field: str) -> dict[str, int]:
    """把日志中的 powers 转成便于审计的映射，同时拒绝重复 ID。"""

    if values is None:
        return {}
    if not isinstance(values, list):
        raise ValueError(f"{field} 必须是数组")
    result: dict[str, int] = {}
    for index, value in enumerate(values):
        if not isinstance(value, dict) or not isinstance(value.get("id"), str):
            raise ValueError(f"{field}[{index}] 必须含字符串 id")
        if value["id"] in result:
            raise ValueError(f"{field} 出现重复 power {value['id']!r}")
        amount = strict_integer(value.get("amount"), f"{field}[{index}].amount")
        result[value["id"]] = amount
    return result


def normalize_monsters(values: Any, field: str = "combat_state.monsters") -> list[dict[str, Any]]:
    """提取战斗入口的敌人状态；缺少 HP/意图字段时拒绝场景。"""

    if not isinstance(values, list) or not values:
        raise ValueError(f"{field} 必须是非空数组")
    result = []
    for index, monster in enumerate(values):
        prefix = f"{field}[{index}]"
        if not isinstance(monster, dict) or not isinstance(monster.get("id"), str):
            raise ValueError(f"{prefix} 必须含字符串 id")
        hp_current = strict_integer(monster.get("hp_current"), f"{prefix}.hp_current", minimum=0)
        hp_max = strict_integer(monster.get("hp_max"), f"{prefix}.hp_max", minimum=1)
        if hp_current > hp_max:
            raise ValueError(f"{prefix}.hp_current 不能大于 hp_max")
        if monster.get("is_gone"):
            raise ValueError(f"{prefix} 在战斗入口已标记 is_gone")
        if not isinstance(monster.get("intent"), str):
            raise ValueError(f"{prefix}.intent 缺失；无法还原玩家可见意图")
        block = strict_integer(monster.get("block", 0), f"{prefix}.block", minimum=0)
        intent_damage = strict_integer(monster.get("damage", 0), f"{prefix}.damage", minimum=0)
        intent_hits = strict_integer(monster.get("hits", 1), f"{prefix}.hits", minimum=1)
        result.append(
            {
                "id": monster["id"],
                "registry_id": AUDIT_MONSTER_REGISTRY.get(monster["id"], {}).get("registry_id"),
                "semantic_status": AUDIT_MONSTER_REGISTRY.get(monster["id"], {}).get("semantic_status", "unknown"),
                "hp_current": hp_current,
                "hp_max": hp_max,
                # Serialization Mod 仅在大于0时写出 block/damage；缺失不能在
                # 原始证据中伪造成“游戏直接记录了0”，单独保存记录标志。
                "block": block,
                "block_recorded": "block" in monster,
                "intent": monster["intent"],
                "intent_damage": intent_damage,
                "intent_damage_recorded": "damage" in monster,
                "intent_hits": intent_hits,
                "intent_hits_recorded": "hits" in monster,
                "powers": power_map(monster.get("powers"), f"{prefix}.powers"),
                "powers_recorded": "powers" in monster,
                "raw": dict(monster),
            }
        )
    return result


def normalize_deck_history(records: list[dict[str, Any]], before_line: int) -> dict[str, Any]:
    """用连续 floor 快照和中间 action 做保守的增删/升级历史审计。"""

    snapshots: list[tuple[int, list[str]]] = []
    for record in records:
        if record.get("_type") != "state:floor" or record.get("_source_line", 0) > before_line:
            continue
        deck = record.get("deck")
        if isinstance(deck, list) and all(isinstance(card, str) for card in deck):
            snapshots.append((int(record["_source_line"]), list(deck)))

    actions = [
        record.get("_type", "")
        for record in records
        if record.get("_source_line", 0) < before_line and str(record.get("_type", "")).startswith("action:")
    ]
    mutations = Counter()
    upgrade_transitions = 0
    for (_, before), (_, after) in zip(snapshots, snapshots[1:]):
        before_counter = Counter(before)
        after_counter = Counter(after)
        for card, count in (after_counter - before_counter).items():
            mutations["added"] += count
            if "+" in card:
                upgrade_transitions += count
        for card, count in (before_counter - after_counter).items():
            mutations["removed"] += count
            if "+" in card:
                upgrade_transitions += count
    return {
        "status": "partial",
        "snapshot_count_before_entry": len(snapshots),
        "mutation_counts_from_snapshot_diffs": dict(sorted(mutations.items())),
        "upgrade_transition_count_upper_bound": upgrade_transitions,
        "action_counts_before_entry": dict(sorted(Counter(actions).items())),
        "instance_identity": "名称+升级次数+源顺序；没有游戏 UUID",
        "limitation": "当前条目快照可直接使用；完整因果历史、变形来源和每张牌 UUID 未公开记录",
    }


def dynamic_counter_ids(records: list[dict[str, Any]]) -> set[str]:
    """收集本 run 中至少一次显式记录过计数的遗物 ID。"""

    result: set[str] = set()
    for record in records:
        if record.get("_type") != "state:floor":
            continue
        try:
            relics = parse_relics(record.get("relics", []))
        except ValueError:
            continue
        result.update(relic["id"] for relic in relics if relic["counter_recorded"])
    return result


def classify_mods(run_state: dict[str, Any]) -> dict[str, Any]:
    """分开记录日志框架与未核实的游戏性 mod。"""

    mods = run_state.get("mods", {})
    if not isinstance(mods, dict):
        return {
            "recorded": mods,
            "instrumentation": [],
            "review_required": ["<mods 字段格式异常>"],
        }
    names = sorted(str(name) for name in mods)
    return {
        "recorded": {name: mods[name] for name in names},
        "instrumentation": sorted(name for name in names if name in INSTRUMENTATION_MODS),
        "review_required": sorted(name for name in names if name not in INSTRUMENTATION_MODS),
    }


def encounter_info(monsters: list[dict[str, Any]]) -> dict[str, Any]:
    """保留原始敌人 ID，并在整组匹配时给出锁定后端枚举。"""

    ids = tuple(monster["id"] for monster in monsters)
    known = ENCOUNTER_GROUPS.get(ids)
    return {
        "monster_ids": list(ids),
        "scenario_id": known["scenario_id"] if known else None,
        "backend_encounter": known["backend_id"] if known else None,
        "group_match": "exact" if known else "unregistered",
    }


def raw_card_base_name(value: Any) -> str | None:
    """尽量取得未解析卡牌的基础名称，仅用于报告未知字段。"""

    if not isinstance(value, str) or not value:
        return None
    return value[:-1] if value.endswith("+") else value.split("+", 1)[0]


def audit_entity_semantics(
    *,
    deck_raw: list[Any],
    pile_raw: dict[str, list[Any]],
    relics: list[dict[str, Any]],
    potions: list[str | None],
    monsters: list[dict[str, Any]],
    player_powers: dict[str, int],
) -> tuple[dict[str, Any], list[str]]:
    """区分已登记、仅观察到但未批准和完全未知的实体语义。"""

    reasons: list[str] = []
    card_names = {
        raw_card_base_name(value)
        for value in [*deck_raw, *(item for values in pile_raw.values() for item in values)]
    }
    card_names.discard(None)
    known_cards = sorted(name for name in card_names if name in AUDIT_CARD_REGISTRY)
    unknown_cards = sorted(name for name in card_names if name not in AUDIT_CARD_REGISTRY)
    if unknown_cards:
        reasons.append("UNKNOWN_ENTITY_OR_SEMANTICS")

    relic_names = sorted(relic["id"] for relic in relics)
    known_relics = sorted(name for name in relic_names if name in AUDIT_RELIC_REGISTRY)
    unknown_relics = sorted(name for name in relic_names if name not in AUDIT_RELIC_REGISTRY)
    if unknown_relics:
        reasons.append("UNKNOWN_ENTITY_OR_SEMANTICS")

    potion_names = sorted({name for name in potions if name is not None})
    known_potions = sorted(name for name in potion_names if name in AUDIT_POTION_REGISTRY)
    unknown_potions = sorted(name for name in potion_names if name not in AUDIT_POTION_REGISTRY)
    deferred_potions = sorted(
        name for name in known_potions if AUDIT_POTION_REGISTRY[name]["formal_status"] != "approved"
    )
    if unknown_potions:
        reasons.append("UNKNOWN_ENTITY_OR_SEMANTICS")
    if deferred_potions:
        reasons.append("UNAPPROVED_ENTITY_SEMANTICS")

    monster_names = sorted(monster["id"] for monster in monsters)
    known_monsters = sorted(name for name in monster_names if name in AUDIT_MONSTER_REGISTRY)
    unknown_monsters = sorted(name for name in monster_names if name not in AUDIT_MONSTER_REGISTRY)
    if unknown_monsters:
        reasons.append("UNKNOWN_ENTITY_OR_SEMANTICS")

    power_names = sorted(set(player_powers))
    for monster in monsters:
        power_names.extend(monster["powers"])
    power_names = sorted(set(power_names))
    known_statuses = sorted(name for name in power_names if name in AUDIT_STATUS_REGISTRY)
    unknown_statuses = sorted(name for name in power_names if name not in AUDIT_STATUS_REGISTRY)
    if unknown_statuses:
        reasons.append("UNKNOWN_ENTITY_OR_SEMANTICS")

    semantics = {
        "cards": {
            "known": known_cards,
            "unknown": unknown_cards,
            "dynamic_dependencies": {
                name: {
                    "dynamic_semantics": AUDIT_CARD_REGISTRY[name]["dynamic_semantics"],
                    "generation": AUDIT_CARD_REGISTRY[name]["generation"],
                }
                for name in known_cards
            },
        },
        "relics": {
            "known": known_relics,
            "unknown": unknown_relics,
            "counter_semantics": {
                name: AUDIT_RELIC_REGISTRY[name]["counter_semantics"]
                for name in known_relics
            },
        },
        "potions": {
            "known_observed": known_potions,
            "deferred": deferred_potions,
            "unknown": unknown_potions,
        },
        "monsters": {
            "known": known_monsters,
            "unknown": unknown_monsters,
        },
        "statuses": {
            "known": known_statuses,
            "unknown": unknown_statuses,
            "parameters": {
                name: AUDIT_STATUS_REGISTRY[name]["parameter"]
                for name in known_statuses
            },
        },
        "encounter_registration": "checked separately from individual monster IDs",
    }
    return semantics, sorted(set(reasons))


def validate_scene_ranges(
    *,
    floor_state: dict[str, Any],
    combat: dict[str, Any],
    deck: list[dict[str, Any]],
    piles: dict[str, list[dict[str, Any]]],
    relics: list[dict[str, Any]],
    potions: list[str | None],
    monsters: list[dict[str, Any]],
) -> tuple[list[str], dict[str, str]]:
    """严格检查场景数值、实体数量和已声明输入容量。"""

    reasons: list[str] = []
    checks: dict[str, str] = {}

    def check(value: Any, field: str, *, minimum: int | None = None, maximum: int | None = None) -> None:
        try:
            strict_integer(value, field, minimum=minimum, maximum=maximum)
        except ValueError:
            reasons.append("INVALID_FINITE_INTEGER_OR_RANGE")
            checks[field] = "failed"
        else:
            checks[field] = "passed"

    check(floor_state.get("floor"), "floor", minimum=0, maximum=MAX_AUDIT_FLOOR)
    hp = floor_state.get("hp_current")
    hp_max = floor_state.get("hp_max")
    check(hp, "player.hp", minimum=0)
    check(hp_max, "player.max_hp", minimum=1)
    if isinstance(hp, int) and not isinstance(hp, bool) and isinstance(hp_max, int) and not isinstance(hp_max, bool):
        if hp > hp_max:
            reasons.append("HP_EXCEEDS_MAX_HP")
            checks["player.hp_le_max_hp"] = "failed"
        else:
            checks["player.hp_le_max_hp"] = "passed"

    player = combat.get("player") if isinstance(combat, dict) else None
    energy = player.get("energy") if isinstance(player, dict) else None
    check(energy, "player.energy", minimum=0, maximum=MAX_AUDIT_ENERGY)
    if isinstance(player, dict) and "block" in player:
        check(player.get("block"), "player.block", minimum=0)

    if len(deck) > MAX_AUDIT_DECK_ENTITIES:
        reasons.append("DECK_CAPACITY_UNPROVEN")
    if len(piles.get("hand", [])) > MAX_AUDIT_HAND:
        reasons.append("HAND_CAPACITY_EXCEEDED")
    non_hand_count = sum(
        len(piles.get(name, [])) for name in ("draw", "discard", "exhaust", "limbo")
    )
    if non_hand_count > MAX_AUDIT_HAND:
        reasons.append("PILE_CAPACITY_EXCEEDED")
    if len(potions) > MAX_AUDIT_POTION_SLOTS:
        reasons.append("POTION_CAPACITY_UNSUPPORTED")
    if len(monsters) > MAX_AUDIT_ENEMIES:
        reasons.append("ENEMY_CAPACITY_EXCEEDED")

    for index, relic in enumerate(relics):
        if relic["counter_recorded"]:
            check(relic["counter"], f"relics[{index}].counter", minimum=0)
    for index, monster in enumerate(monsters):
        if monster["hp_current"] > monster["hp_max"]:
            reasons.append("MONSTER_HP_EXCEEDS_MAX_HP")
            checks[f"monsters[{index}].hp_le_max_hp"] = "failed"
        else:
            checks[f"monsters[{index}].hp_le_max_hp"] = "passed"
        if monster["intent"] in ATTACK_INTENTS and not monster["intent_damage_recorded"]:
            reasons.append("ATTACK_INTENT_DAMAGE_MISSING")
    return sorted(set(reasons)), checks


def validate_pile_consistency(
    *,
    floor_state: dict[str, Any],
    deck: list[dict[str, Any]],
    pile_records: dict[str, list[dict[str, Any]]],
    pile_errors: dict[str, str | None],
) -> tuple[list[str], dict[str, Any]]:
    """检查 post-init 入口的牌区关系，并把生成牌路径单独报告。"""

    if any(pile_errors.values()) or not deck:
        return [], {"status": "skipped_parse_failure"}
    deck_values = [card["raw"] for card in deck]
    pile_values = [
        card["raw"]
        for name in ("hand", "draw", "discard", "exhaust", "limbo")
        for card in pile_records[name]
    ]
    missing = list((Counter(deck_values) - Counter(pile_values)).elements())
    extra = list((Counter(pile_values) - Counter(deck_values)).elements())
    reasons: list[str] = []
    if missing:
        reasons.append("PILE_MISSING_DECK_CARDS")
        if floor_state.get("floor") == 1 and len(deck_values) == 10:
            reasons.append("FIRST_BATTLE_BASE_DECK_MISMATCH")
    if extra:
        # 生成的状态牌/临时牌可以使“牌区总量 > master deck”合法，但在
        # 入口需要进一步证明生成来源和容量，不能直接视为守恒通过。
        generated_names = {"Wound", "Dazed", "Slimed", "Burn", "Void"}
        if all(raw_card_base_name(value) in generated_names for value in extra):
            reasons.append("GENERATED_ENTITY_AT_ENTRY_UNPROVEN")
        else:
            reasons.append("PILE_CONTAINS_UNDECLARED_CARDS")
    return sorted(set(reasons)), {
        "status": "checked",
        "deck_count": len(deck_values),
        "pile_count": len(pile_values),
        "missing_deck_cards": missing,
        "extra_pile_cards": extra,
        "multiset_equal": not missing and not extra,
        "rule": "post-init first-decision snapshot must account for every card; generation/removal paths require explicit mechanism evidence",
    }


def internal_state_audit(
    *,
    pile_records: dict[str, list[dict[str, Any]]],
    monsters: list[dict[str, Any]],
    relics: list[dict[str, Any]],
    potions: list[str | None],
    combat: dict[str, Any],
    run_state: dict[str, Any],
) -> dict[str, Any]:
    """列出 post-init 继续运行所需的内部字段和具体重采样策略。"""

    return {
        "status": "unproven",
        "constructible": False,
        "required_for_continuation": [
            "input_state=PLAYER_NORMAL、outcome=UNDECIDED、actionQueue/cardQueue为空",
            "CardInstance.uniqueId、升级次数、specialData、costForTurn、freeToPlayOnce、retain、bottle关系",
            "draw/discard/exhaust/limbo的后端顺序；规范观测仍须隐藏非手牌顺序",
            "Monster moveHistory[0/1]、当前move、miscInfo、status bits、targetable/dead/half-dead",
            "玩家完整战斗status、遗物bitset/data/counter/order、药水capacity/count/slot IDs",
            "各RNG stream及counter，至少包括敌人AI、怪物HP、洗牌、card random、misc、potion",
        ],
        "recorded_at_entry": {
            "hand": bool(pile_records.get("hand")),
            "draw_pile": bool(pile_records.get("draw")),
            "discard_pile": bool(pile_records.get("discard")),
            "exhaust_pile": bool(pile_records.get("exhaust")),
            "limbo": bool(pile_records.get("limbo")),
            "enemy_public_fields": bool(monsters),
            "relic_ids_and_some_counters": bool(relics),
            "potion_slots": bool(potions),
            "control_state": False,
            "hidden_rng_streams": False,
            "card_dynamic_values": False,
            "monster_internal_history": False,
        },
        "missing_or_unproven": [
            "source snapshot未记录InputState/queue为空的证明",
            "source snapshot未记录完整CardInstance动态值和后端uniqueId",
            "source snapshot未记录monster move/history/miscInfo及全部状态位",
            "source snapshot未记录完整遗物bit/data回写和药水count/capacity来源",
            "source snapshot未记录完整RNG stream/counter",
        ],
        "resampling_policy": {
            "policy_id": "public-battle-a-resample-v1",
            "mode": "优先原生入口A；B转A必须另附HP/counter/开战效果的逐字段逆向证据，当前两个B候选不具备该证据",
            "development_seed": "100000 + (int(SHA256(scene_id)前8位,16) mod 900000)",
            "evaluation_seed": "仅使用已提交且不可变的eval_seeds.json；本轮不分配",
            "restore_directly": [
                "source deck multiset及已解析upgrade/dynamic字段",
                "source player HP/maxHP",
                "source relic IDs与已知counter",
                "source potion slots（若容量规则已核验）",
                "source encounter group、ascension和game version",
            ],
            "resample_explicitly": [
                "shuffle/draw order、enemy HP roll、initial move和敌人隐藏misc",
                "future RNG streams/counters、new CardInstance uniqueId",
            ],
            "never_fill_with_zero": [
                "dynamic relic counter",
                "missing potion inventory/capacity",
                "card specialData/costForTurn",
                "monster move history/status bit",
            ],
            "exact_historical_replay": False,
        },
        "run_context": {
            "source_seed": run_state.get("seed"),
            "game_version": run_state.get("versions"),
            "source_mods": classify_mods(run_state),
        },
    }


def capacity_audit(
    *,
    deck: list[dict[str, Any]],
    piles: dict[str, list[dict[str, Any]]],
    relics: list[dict[str, Any]],
    potions: list[str | None],
    monsters: list[dict[str, Any]],
) -> dict[str, Any]:
    """输出实际数量与批次容量；不把样本最大值冒充全过程上界。"""

    non_hand = sum(len(piles.get(name, [])) for name in ("draw", "discard", "exhaust", "limbo"))
    targetable = sum(1 for monster in monsters if not monster.get("raw", {}).get("is_gone"))
    return {
        "hand": {"actual": len(piles.get("hand", [])), "contract_max": MAX_AUDIT_HAND},
        "non_hand_including_limbo": {"actual": non_hand, "contract_max": MAX_AUDIT_HAND},
        "card_entities_total": {"actual": len(piles.get("hand", [])) + non_hand, "rule": "hand + one combined non-hand capacity"},
        "deck_snapshot": {"actual": len(deck), "sample_only": True},
        "enemy_observation_rows": {"actual": len(monsters), "contract_max": MAX_AUDIT_ENEMIES},
        "targetable_enemy_count": {"actual": targetable, "action_contract_max": 5},
        "relics": {
            "actual": len(relics),
            "public_b0_core_max": 2,
            "status": "within_public_b0_core" if len(relics) <= 2 else "requires_separate_batch_profile",
        },
        "potions": {
            "actual": len(potions),
            "public_b0_core_max": MAX_AUDIT_POTION_SLOTS,
            "status": "within_public_b0_core" if len(potions) <= MAX_AUDIT_POTION_SLOTS else "requires_capacity_migration",
        },
        "status_feature_width": 5,
        "warning": "实际数量不是生成/分裂/召唤全过程上界；每批仍需按机制路径证明或拒绝",
    }


BASE_IRONCLAD_DECK = [
    "Strike_R",
    "Strike_R",
    "Strike_R",
    "Strike_R",
    "Strike_R",
    "Defend_R",
    "Defend_R",
    "Defend_R",
    "Defend_R",
    "Bash",
]


def _summary_floor(value: Any, field: str) -> int:
    """读取 summary 的楼层；保留整数浮点这一来源编码事实。"""

    if isinstance(value, bool):
        raise ValueError(f"{field} 不能是布尔值")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    raise ValueError(f"{field} 不是有限楼层整数")


def _valid_string_list(value: Any, field: str) -> tuple[list[str], str | None]:
    """读取 summary 中的字符串数组并保留缺失/类型错误。"""

    if value is None:
        return [], f"{field} 缺失"
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        return [], f"{field} 必须是非空字符串项数组"
    return list(value), None


def _apply_deck_delta(base: list[str], log: dict[str, Any]) -> dict[str, Any]:
    """只按 Neow 明确记录的增删尝试构造入口牌组，不读取最终 master_deck。"""

    deck = Counter(base)
    reasons: list[str] = []
    fields: dict[str, list[str]] = {}
    for key in ("cardsRemoved", "cardsTransformed", "cardsObtained", "cardsUpgraded"):
        values, error = _valid_string_list(log.get(key), f"neow_bonus_log.{key}")
        if error:
            reasons.append("NEOW_CHANGE_LOG_INVALID")
            fields[key] = []
        else:
            fields[key] = values

    removed = fields["cardsRemoved"] + fields["cardsTransformed"]
    for card in removed:
        if deck[card] <= 0:
            reasons.append("NEOW_REMOVAL_SOURCE_NOT_IN_BASE_DECK")
        else:
            deck[card] -= 1
    for card in fields["cardsObtained"]:
        deck[card] += 1

    upgrade_targets = Counter(fields["cardsUpgraded"])
    upgrade_result: list[str] = []
    for card, count in sorted(upgrade_targets.items()):
        if deck[card] < count:
            reasons.append("NEOW_UPGRADE_SOURCE_NOT_IN_RECONSTRUCTED_DECK")
        upgrade_result.extend([f"{card}+1"] * count)
    for raw in list(deck):
        if deck[raw] <= 0:
            del deck[raw]
    reconstructed = sorted(deck.elements())
    # 这里的升级结果只记录为“待绑定到同名实例”的提示，不能把重复牌映射成
    # 某个具体 UUID；只要有升级，就把实例身份标为部分可证。
    return {
        "status": "candidate_multiset" if not reasons else "failed",
        "base_deck_rule": "Ironclad starter deck；ascension>=10 另加 AscendersBane",
        "base_deck": base,
        "delta_fields": fields,
        "reconstructed_unupgraded_multiset": reconstructed,
        "upgrade_targets_without_uuid": upgrade_result,
        "instance_identity": "同名重复牌无 UUID；升级目标只能按多重集记录",
        "reason_codes": sorted(set(reasons)),
    }


def audit_summary_early_reconstruction(
    run: dict[str, Any], path: str, raw_hash: str,
) -> dict[str, Any]:
    """分别审计A规则构造和来源真实性；B缺字段不阻止A初始化。"""
    reasons: list[str] = []
    b_reasons = ["B_HAND_PILES_MISSING", "B_ENEMY_INTENT_MISSING", "B_CONTROL_STATE_MISSING"]
    damage_rows = run.get("damage_taken")
    first = damage_rows[0] if isinstance(damage_rows, list) and damage_rows else None
    floor = None
    if not isinstance(first, dict):
        reasons.append("NO_EARLY_COMBAT_ROW")
        first = None
    else:
        try:
            floor = _summary_floor(first.get("floor"), "damage_taken[0].floor")
        except ValueError:
            reasons.append("EARLY_COMBAT_FLOOR_INVALID")
    if floor != 1:
        reasons.append("PRE_FIRST_BATTLE_HISTORY_NOT_PROVEN")
    ascension = None
    try:
        ascension = _summary_floor(run.get("ascension_level"), "ascension_level")
        if not 0 <= ascension <= 20:
            raise ValueError("进阶超范围")
    except ValueError:
        reasons.append("ASCENSION_MISSING_OR_INVALID")
        ascension = None
    if run.get("character_chosen") != "IRONCLAD":
        reasons.append("STARTER_DECK_RULE_NOT_VERIFIED_FOR_RUN")
    if not isinstance(run.get("build_version"), str) or not run["build_version"]:
        reasons.append("SOURCE_BUILD_MISSING")
    if not isinstance(run.get("seed_played"), (str, int)) or isinstance(run.get("seed_played"), bool) or str(run["seed_played"]) == "":
        reasons.append("SOURCE_SEED_MISSING_OR_INVALID")
    # 这些是来源记录的标准模式约束，不能用缺失或0代替显式false。
    for key in ("is_daily", "is_trial", "is_endless"):
        if run.get(key) is not False:
            reasons.append("STANDARD_RUN_MODE_NOT_ESTABLISHED")
    path_rows = run.get("path_per_floor")
    if not isinstance(path_rows, list) or not path_rows or path_rows[0] != "M":
        reasons.append("FIRST_ROOM_NOT_NORMAL_MONSTER")

    base = list(BASE_IRONCLAD_DECK)
    if ascension is not None and ascension >= 10:
        base.append("AscendersBane")
    log = run.get("neow_bonus_log")
    deck = _apply_deck_delta(base, log) if isinstance(log, dict) else {
        "status": "missing", "reason_codes": ["NEOW_CHANGE_LOG_MISSING"]}
    reasons.extend(deck["reason_codes"])
    bonus, cost = run.get("neow_bonus"), run.get("neow_cost")
    # 首个规则证据仅覆盖金币奖励；其它奖励保留实际日志，不猜变形/选择时序。
    supported_neow = bonus == "HUNDRED_GOLD" and cost == "NONE"
    if not supported_neow:
        reasons.append("NEOW_EFFECT_RULE_NOT_YET_VERIFIED")
    expected_log = {
        "cardsObtained": [], "cardsUpgraded": [], "cardsRemoved": [],
        "cardsTransformed": [], "relicsObtained": [], "maxHpGained": 0,
        "goldGained": 100, "damageTaken": 0, "goldLost": 0, "maxHpLost": 0,
    }
    log_matches = isinstance(log, dict) and all(
        key in log and type(log[key]) is type(value) and log[key] == value
        for key, value in expected_log.items())
    if supported_neow and not log_matches:
        reasons.append("NEOW_LOG_MISSING_OR_CONTRADICTS_RULE")

    early: dict[str, list[Any]] = {}
    for key in ("card_choices", "event_choices", "campfire_choices", "relics_obtained", "potions_obtained"):
        rows = run.get(key)
        early[key] = []
        if not isinstance(rows, list):
            reasons.append("ENTRY_HISTORY_MISSING_OR_INVALID")
            continue
        for row in rows:
            try:
                row_floor = _summary_floor(row.get("floor"), key + ".floor")
            except (ValueError, AttributeError):
                reasons.append("ENTRY_HISTORY_MISSING_OR_INVALID")
                continue
            if floor is not None and row_floor <= floor:
                early[key].append(row)
                # 首层普通战斗的拿牌/药水奖励在战后，不加入pre-init。
                # 首层事件/营火或floor<=0的获取则与本窄规则矛盾。
                if row_floor < 1 or key in ("event_choices", "campfire_choices"):
                    reasons.append("PRE_ENTRY_MUTATION_UNPROVEN")
    for key in ("items_purged_floors", "item_purchase_floors"):
        values = run.get(key)
        if not isinstance(values, list):
            reasons.append("ENTRY_HISTORY_MISSING_OR_INVALID")
            continue
        for value in values:
            try:
                if _summary_floor(value, key) <= 1:
                    reasons.append("PRE_ENTRY_MUTATION_UNPROVEN")
            except ValueError:
                reasons.append("ENTRY_HISTORY_MISSING_OR_INVALID")

    rule_ready = supported_neow and log_matches and ascension is not None
    max_hp = (75 if ascension >= 14 else 80) if ascension is not None else None
    hp = (math.floor(max_hp * 0.9 + 0.5) if ascension >= 6 else max_hp) if max_hp is not None else None
    evidence_ref = "docs/m2-entry-a-evidence.md"
    hp_evidence = {
        "status": "derived-with-evidence" if rule_ready else "unknown",
        "hp_current": hp if rule_ready else None, "hp_max": max_hp if rule_ready else None,
        "evidence": evidence_ref + "#规则证据",
        "floor_metrics_not_used_as_entry": {key: run.get(key, [])[:1] for key in
            ("current_hp_per_floor", "max_hp_per_floor") if isinstance(run.get(key, []), list)},
    }
    if not rule_ready:
        reasons.append("PLAYER_ENTRY_HP_DERIVATION_UNPROVEN")
    relic_evidence = {
        "status": "derived-with-evidence" if rule_ready else "unknown",
        "entries": [{"id": "Burning Blood", "counter": None, "counter_semantics": "not_applicable"}] if rule_ready else None,
        "neow_relics_obtained": log.get("relicsObtained") if isinstance(log, dict) else None,
        "evidence": evidence_ref + "#规则证据",
    }
    if not rule_ready:
        reasons.append("RELIC_ENTRY_SEMANTICS_UNPROVEN")
    potion_evidence = {
        "status": "derived-with-evidence" if rule_ready else "unknown",
        "slots": [None] * (2 if ascension >= 11 else 3) if rule_ready else None,
        "obtained_rows_before_or_at_floor": early["potions_obtained"],
        "evidence": evidence_ref + "#规则证据",
    }
    if not rule_ready:
        reasons.append("POTION_ENTRY_DERIVATION_UNPROVEN")
    label = first.get("enemies") if first else None
    mapping = {"Cultist": "CULTIST", "Jaw Worm": "JAW_WORM", "2 Louse": "TWO_LOUSE"}
    encounter = {
        "status": "resampled-by-policy" if label in mapping else "unknown",
        "label": label, "backend_id": mapping.get(label),
        "generated_fields": ["monster_hp", "initial_intent", "instance_ids", "move_history", "slot_order"],
        "policy": "public-battle-a-resample-v1", "evidence": evidence_ref + "#规则证据",
    }
    if label not in mapping:
        reasons.append("ENCOUNTER_GENERATOR_NOT_REGISTERED")

    reasons = sorted(set(reasons))
    # .run本身不能认证历史二进制/mod；绝不因调用者写一个verified字段就放行。
    provenance_blockers = ["SOURCE_RULESET_COMPATIBILITY_UNVERIFIED", "SOURCE_MOD_MANIFEST_UNAVAILABLE"]
    a_status = "rule_constructible_source_unverified" if not reasons else "partial_reconstruction_attempt"
    scene = None
    if not reasons:
        scene = {
            "scene_id": "summary-a:" + str(run.get("play_id") or raw_hash[:16]) + ":floor-1",
            "entry_timing": "pre_combat_initialization",
            "source_path": path, "raw_sha256": raw_hash,
            "source_run_group": run_group_key("IRONCLAD", str(run.get("seed_played")), path),
            "source_seed": run.get("seed_played"), "source_build_version": run.get("build_version"),
            "environment_replay_seed": None, "character": "IRONCLAD", "ascension": ascension,
            "floor": 1, "act": 1, "room_kind": "MONSTER", "burning_elite": False,
            "player": {"hp_current": hp, "hp_max": max_hp, "gold": 199},
            "deck": base, "relics": relic_evidence["entries"], "potions": potion_evidence["slots"],
            "encounter": encounter, "battle_initialization": "execute_once",
            "already_resolved_effects": ["standard_run_start", "neow_hundred_gold"],
            "generated_by_backend": ["energy", "block", "powers", "piles", "queues", "card_instance_ids", "monster_state", "rng_streams"],
            "evidence": evidence_ref, "formal_eligibility": "audit-only",
            "source_compatibility": "unverified", "exact_historical_replay": False,
        }
    a = {
        "status": a_status, "rule_constructible": not reasons,
        "first_combat": {"row": first, "source": "damage_taken[0]", "floor": floor},
        "starting_bonus": {"bonus": bonus, "cost": cost, "log": log},
        "deck": deck, "hp": hp_evidence, "relics": relic_evidence,
        "potions": potion_evidence, "encounter": encounter,
        "early_history": early, "missing_or_ambiguous": reasons,
        "source_evidence_blockers": provenance_blockers,
        "candidate_scene": scene,
    }
    return {
        "status": a_status if not reasons else "not_reconstructable_from_summary",
        "formal_candidate": False,
        "reason_codes": sorted(set(reasons + provenance_blockers)),
        "attempted_modes": {
            "A_pre_combat_initialization": a,
            "B_post_combat_initialization_after_initial_draw": {
                "status": "not_available", "missing_or_ambiguous": b_reasons},
        },
        "source_run_id": run.get("play_id") or path.rsplit("/", 1)[-1].removesuffix(".run"),
        "source_seed": run.get("seed_played"), "raw_sha256": raw_hash,
        "note": "规则构造与来源真实性分开；B缺手牌/意图不排除A。正式准入仍需版本/mod、内容、后端和分组验收。",
    }


def audit_summary_run(run: dict[str, Any], path: str, raw_hash: str) -> dict[str, Any]:
    """审计逐层 .run：同时尝试入口 A，不能只因缺 B 字段统一判死。"""

    missing = [field for field in SUMMARY_FIELDS if field not in run]
    damage_rows = run.get("damage_taken") if isinstance(run.get("damage_taken"), list) else []
    encounters = Counter(
        str(row.get("enemies"))
        for row in damage_rows
        if isinstance(row, dict) and row.get("enemies") is not None
    )
    source_seed = run.get("seed_played")
    source_run_id = run.get("play_id") or path.rsplit("/", 1)[-1].removesuffix(".run")
    reconstruction = audit_summary_early_reconstruction(run, path, raw_hash)
    return {
        "source_kind": "github-run-summary",
        "source_path": path,
        "source_run_id": source_run_id,
        "group_key": run_group_key(run.get("character_chosen"), source_seed, "matiger"),
        "source_seed": source_seed,
        "character": run.get("character_chosen"),
        "ascension": run.get("ascension_level"),
        "build_version": run.get("build_version"),
        "victory": run.get("victory"),
        "floor_reached": run.get("floor_reached"),
        "encounters_from_damage_taken": dict(sorted(encounters.items())),
        "field_presence": {field: field in run for field in SUMMARY_FIELDS},
        "missing_fields": missing,
        "raw_sha256": raw_hash,
        "reconstruction": reconstruction,
    }


def audit_scene(
    *,
    records: list[dict[str, Any]],
    run_state: dict[str, Any],
    floor_state: dict[str, Any],
    predecessor: dict[str, Any] | None,
    dynamic_ids: set[str],
    source_id: str,
    source_url: str,
    raw_hash: str,
) -> dict[str, Any]:
    """把一个战斗入口快照转为机器可读场景，并保守处理缺失字段。"""

    reasons: list[str] = []
    combat = floor_state.get("combat_state")
    try:
        deck = parse_card_list(floor_state.get("deck"), "state:floor.deck")
    except ValueError as exc:
        deck = []
        if "升级标记不完整" in str(exc) or "升级格式" in str(exc):
            reasons.append("UPGRADE_FORMAT_AMBIGUOUS")
        else:
            reasons.append("DECK_FIELD_INVALID")
        deck_error = str(exc)
    else:
        deck_error = None
    deck_raw_values = list(floor_state.get("deck", [])) if isinstance(floor_state.get("deck"), list) else []
    if not deck:
        reasons.append("DECK_EMPTY_OR_MISSING")
    try:
        potions = parse_potions(floor_state.get("potions"))
    except ValueError as exc:
        potions = []
        reasons.append("POTION_INVENTORY_MISSING_OR_INVALID")
        potion_error = str(exc)
    else:
        potion_error = None
    try:
        relics = parse_relics(floor_state.get("relics"))
    except ValueError as exc:
        relics = []
        reasons.append("RELIC_STATE_MISSING_OR_INVALID")
        relic_error = str(exc)
    else:
        relic_error = None
    relic_raw_values = list(floor_state.get("relics", [])) if isinstance(floor_state.get("relics"), list) else []
    if not isinstance(combat, dict):
        reasons.append("COMBAT_STATE_MISSING")
        combat = {}
    try:
        monsters = normalize_monsters(combat.get("monsters"))
    except ValueError:
        monsters = []
        reasons.append("MONSTER_STATE_MISSING_OR_INVALID")
    monster_raw_values = list(combat.get("monsters", [])) if isinstance(combat.get("monsters"), list) else []
    player = combat.get("player")
    if not isinstance(player, dict) or isinstance(player.get("energy"), bool) or not isinstance(player.get("energy"), int):
        reasons.append("PLAYER_ENERGY_MISSING_OR_INVALID")
        player = {}
    hp = floor_state.get("hp_current")
    hp_max = floor_state.get("hp_max")
    if isinstance(hp, bool) or not isinstance(hp, int) or isinstance(hp_max, bool) or not isinstance(hp_max, int):
        reasons.append("PLAYER_HP_MISSING_OR_INVALID")
    if not isinstance(floor_state.get("floor"), (int, float)):
        reasons.append("FLOOR_MISSING_OR_INVALID")
    if not isinstance(floor_state.get("room_type"), str) or "MonsterRoom" not in floor_state.get("room_type", ""):
        reasons.append("ROOM_TYPE_NOT_COMBAT")
    if predecessor is None or predecessor.get("_type") != "action:select_map":
        reasons.append("ENTRY_TIMING_AMBIGUOUS")

    pile_records: dict[str, list[dict[str, Any]]] = {}
    pile_errors: dict[str, str | None] = {}
    pile_raw: dict[str, list[Any]] = {}
    for pile_name, source_key in (
        ("hand", "hand"),
        ("draw", "draw_pile"),
        ("discard", "discard_pile"),
        ("exhaust", "exhaust_pile"),
        ("limbo", "limbo"),
    ):
        parsed, error, raw_values = safe_parse_card_list(
            combat.get(source_key, []),
            f"combat_state.{source_key}",
            reasons,
        )
        pile_records[pile_name] = parsed
        pile_errors[pile_name] = error
        pile_raw[pile_name] = raw_values

    range_reasons, range_checks = validate_scene_ranges(
        floor_state=floor_state,
        combat=combat,
        deck=deck,
        piles=pile_records,
        relics=relics,
        potions=potions,
        monsters=monsters,
    )
    reasons.extend(range_reasons)
    consistency_reasons, pile_consistency = validate_pile_consistency(
        floor_state=floor_state,
        deck=deck,
        pile_records=pile_records,
        pile_errors=pile_errors,
    )
    reasons.extend(consistency_reasons)
    player_powers = {}
    if isinstance(player, dict):
        try:
            player_powers = power_map(player.get("powers"), "combat_state.player.powers")
        except ValueError:
            reasons.append("PLAYER_POWER_FIELD_INVALID")
    entity_semantics, entity_reasons = audit_entity_semantics(
        deck_raw=deck_raw_values,
        pile_raw=pile_raw,
        relics=relics,
        potions=potions,
        monsters=monsters,
        player_powers=player_powers,
    )
    reasons.extend(entity_reasons)
    if monsters and encounter_info(monsters)["group_match"] != "exact":
        reasons.append("ENCOUNTER_NOT_REGISTERED")
    if any(monster.get("intent") not in KNOWN_INTENTS for monster in monsters):
        reasons.append("UNKNOWN_INTENT_SEMANTICS")

    for relic in relics:
        if relic["id"] in dynamic_ids and not relic["counter_recorded"]:
            reasons.append("DYNAMIC_RELIC_COUNTER_MISSING")
    # 已知动态遗物即使从未在本 run 其他楼层出现过，也不能把省略字段默认为0。
    for relic in relics:
        if relic["id"] in KNOWN_DYNAMIC_RELICS and not relic["counter_recorded"]:
            if "DYNAMIC_RELIC_COUNTER_MISSING" not in reasons:
                reasons.append("DYNAMIC_RELIC_COUNTER_MISSING")

    mods = classify_mods(run_state)
    if mods["review_required"]:
        mod_note = "存在未核实的非日志 mod；进入正式训练前需独立确认不改变游戏性"
    else:
        mod_note = "仅记录到日志/通信框架 mod"
    source_version = run_state.get("versions", {}).get("sts") if isinstance(run_state.get("versions"), dict) else None
    if source_version not in REGISTERED_SOURCE_STS_VERSIONS:
        reasons.append("VERSION_UNREGISTERED_OR_INCOMPATIBLE")

    source_seed = run_state.get("seed")
    run_group = run_group_key(run_state.get("class"), source_seed, source_id)
    encounter = encounter_info(monsters) if monsters else {
        "monster_ids": [], "scenario_id": None, "backend_encounter": None, "group_match": "invalid"
    }
    entry_line_value = floor_state.get("_source_line", 0)
    entry_line = entry_line_value if isinstance(entry_line_value, int) and not isinstance(entry_line_value, bool) else 0
    scene_id = f"{source_id}:{source_seed}:floor-{floor_state.get('floor')}:line-{entry_line}"
    structural_codes = {
        "DECK_FIELD_INVALID",
        "DECK_EMPTY_OR_MISSING",
        "POTION_INVENTORY_MISSING_OR_INVALID",
        "RELIC_STATE_MISSING_OR_INVALID",
        "COMBAT_STATE_MISSING",
        "MONSTER_STATE_MISSING_OR_INVALID",
        "PLAYER_ENERGY_MISSING_OR_INVALID",
        "PLAYER_HP_MISSING_OR_INVALID",
        "FLOOR_MISSING_OR_INVALID",
        "ENTRY_TIMING_AMBIGUOUS",
        "UPGRADE_FORMAT_AMBIGUOUS",
        "PILE_CARD_FIELD_INVALID",
        "INVALID_FINITE_INTEGER_OR_RANGE",
        "HP_EXCEEDS_MAX_HP",
        "MONSTER_HP_EXCEEDS_MAX_HP",
        "HAND_CAPACITY_EXCEEDED",
        "PILE_CAPACITY_EXCEEDED",
        "POTION_CAPACITY_UNSUPPORTED",
        "ENEMY_CAPACITY_EXCEEDED",
        "DECK_CAPACITY_UNPROVEN",
        "PILE_MISSING_DECK_CARDS",
        "FIRST_BATTLE_BASE_DECK_MISMATCH",
        "GENERATED_ENTITY_AT_ENTRY_UNPROVEN",
        "PILE_CONTAINS_UNDECLARED_CARDS",
        "RELIC_STATE_MISSING_OR_INVALID",
        "DYNAMIC_RELIC_COUNTER_MISSING",
        "ATTACK_INTENT_DAMAGE_MISSING",
        "PLAYER_POWER_FIELD_INVALID",
        "VERSION_UNREGISTERED_OR_INCOMPATIBLE",
        "ROOM_TYPE_NOT_COMBAT",
    }
    visible_codes = {
        "UNKNOWN_ENTITY_OR_SEMANTICS",
        "UNAPPROVED_ENTITY_SEMANTICS",
        "ENCOUNTER_NOT_REGISTERED",
        "UNKNOWN_INTENT_SEMANTICS",
    }
    if reasons:
        status = "excluded"
    else:
        status = "visible_entry_verified_internal_state_unproven"
    if not reasons:
        structure_status = "parseable"
        visible_status = "verified"
    else:
        structure_status = "invalid" if set(reasons) & structural_codes else "parseable"
        visible_status = "unverified" if set(reasons) & visible_codes else "verified"
    internal_audit = internal_state_audit(
        pile_records=pile_records,
        monsters=monsters,
        relics=relics,
        potions=potions,
        combat=combat,
        run_state=run_state,
    )
    capacity = capacity_audit(
        deck=deck,
        piles=pile_records,
        relics=relics,
        potions=potions,
        monsters=monsters,
    )
    scene = {
        "scene_id": scene_id,
        "floor": int(floor_state["floor"]) if isinstance(floor_state.get("floor"), (int, float)) else None,
        "room_type": floor_state.get("room_type"),
        "status": status,
        "formal_eligibility": "audit-only",
        "validation_status": {
            "structure_parse_status": structure_status,
            "visible_entry_status": visible_status,
            "internal_state_status": internal_audit["status"],
            "version_mod_status": "pending_review" if mods["review_required"] else "recorded_not_equivalent",
            "backend_status": "pending-m3-state-injection",
            "structural_reason_codes": sorted(set(reasons) & structural_codes),
            "visible_reason_codes": sorted(set(reasons) & visible_codes),
        },
        "backend_status": "pending-m3-state-injection",
        "group_key": run_group,
        "split": "audit-only",
        "source": {
            "source_id": source_id,
            "source_url": source_url,
            "raw_sha256": raw_hash,
            "source_run_id": source_seed,
            "floor": int(floor_state["floor"]) if isinstance(floor_state.get("floor"), (int, float)) else None,
            "source_line": entry_line,
            "predecessor": predecessor,
        },
        "run": {
            "character": run_state.get("class"),
            "source_seed": source_seed,
            "environment_replay_seed": None,
            "seed_policy": "source seed is provenance only; assign a separate training/eval seed after group split",
            "ascension": run_state.get("ascension", run_state.get("ascension_level")),
            "versions": run_state.get("versions"),
            "mods": mods,
            "log_completion": "state:game_over" in {record.get("_type") for record in records},
        },
        "entry_timing": {
            "canonical": "post_combat_initialization_after_initial_draw",
            "pre_initialization_snapshot_available": False,
            "source_anchor": "first state:floor combat_state after action:select_map for this floor",
            "effect_rule": "reset must inject the already-resolved snapshot and must not repeat start-of-combat/start-of-turn effects",
            "control_state": "not_recorded; must be PLAYER_NORMAL with empty action/card queue before continuation",
            "turn": {"value": 1, "recorded": False, "evidence": "first combat entry after map selection; source does not emit turn"},
        },
        "player": {
            "hp_current": hp if isinstance(hp, int) and not isinstance(hp, bool) else None,
            "hp_max": hp_max if isinstance(hp_max, int) and not isinstance(hp_max, bool) else None,
            "energy": player["energy"] if isinstance(player.get("energy"), int) and not isinstance(player.get("energy"), bool) else None,
            "block": player.get("block", 0),
            "block_recorded": "block" in player,
            "block_evidence": "direct when serializer field present; omitted means serializer condition, not arbitrary fill",
            "turn": 1,
            "turn_recorded": False,
            "powers": player_powers,
            "powers_recorded": isinstance(player, dict) and "powers" in player,
            "raw": dict(player),
        },
        "deck": {
            "instances": deck,
            "count": len(deck),
            "raw_values_on_parse_failure": deck_raw_values,
            "source": "state:floor.deck",
            "identity": "名称+升级次数+源顺序；重复牌没有游戏 UUID",
            "history": normalize_deck_history(records, entry_line),
            "parse_error": deck_error,
        },
        "piles": {
            "hand": pile_records["hand"],
            "draw": pile_records["draw"],
            "discard": pile_records["discard"],
            "exhaust": pile_records["exhaust"],
            "limbo": pile_records["limbo"],
            "parse_errors": pile_errors,
            "raw_values_on_parse_failure": pile_raw,
            "draw_order_recorded_by_logger": isinstance(combat, dict) and "draw_pile" in combat,
            "model_policy": "非手牌只向模型提供规范化无序多重集；源顺序可供后端复跑但不得进入模型",
        },
        "relics": relics,
        "raw_relics_on_parse_failure": relic_raw_values,
        "potions": {
            "slots": potions,
            "capacity": len(potions),
            "source": "state:floor.potions",
            "parse_error": potion_error,
        },
        "encounter": encounter,
        "raw_monsters_on_parse_failure": monster_raw_values,
        "entity_semantics": entity_semantics,
        "pile_consistency": pile_consistency,
        "range_checks": range_checks,
        "internal_state_audit": internal_audit,
        "capacity_audit": capacity,
        "hidden_state": {
            "rng_counters_recorded": False,
            "future_rng_policy": "重新采样",
            "exact_historical_replay": False,
            "reason": "该日志快照没有可供锁定后端直接恢复的完整 RNG stream/counter；这不影响记录入口牌堆快照，但不能宣称逐步复盘",
        },
        "field_evidence": {
            "deck_at_entry": "direct_record",
            "per_card_upgrade_count_at_entry": "direct_record_from_name_suffix",
            "upgrade_add_remove_transform_history": "partial_or_ambiguous",
            "hp_and_max_hp": "direct_record",
            "floor_and_room": "direct_record",
            "encounter_group": "direct_record_from_monster_ids",
            "enemy_hp_and_intent": "direct_record",
            "enemy_and_player_powers": "direct_record_when_serializer_field_present",
            "omitted_zero_block_or_damage": "serializer_conditional_field; not an assumed game default",
            "relic_ids": "direct_record",
            "relic_counters": "direct_if_present; missing is ambiguous and blocks candidate",
            "potion_slots": "direct_record",
            "pre_initialization_state": "missing",
            "hidden_rng": "missing",
        },
        "quality_flags": {
            "reason_codes": sorted(set(reasons)),
            "mod_note": mod_note,
            "mod_review_required": bool(mods["review_required"]),
        },
    }
    if relic_error:
        scene["relics_error"] = relic_error
    return scene


def audit_runlogger_log(
    content: bytes,
    *,
    source_id: str,
    source_url: str,
    raw_hash: str,
) -> dict[str, Any]:
    """审计一个公开 JSONL 日志并抽取每楼层第一个战斗快照。"""

    records = parse_jsonl(content, source_url)
    run_state = records[0]
    if run_state.get("_type") != "state:run":
        raise ValueError("runlogger 日志第一条必须是 state:run")
    if not isinstance(run_state.get("class"), str) or not isinstance(run_state.get("seed"), str):
        raise ValueError("state:run 缺少 class 或 seed")
    if "ascension" not in run_state and "ascension_level" not in run_state:
        raise ValueError("state:run 缺少 ascension/ascension_level")
    if not isinstance(run_state.get("versions"), dict) or not isinstance(run_state["versions"].get("sts"), str):
        raise ValueError("state:run 缺少 versions；版本边界不能猜测")

    dynamic_ids = dynamic_counter_ids(records)
    scenes: list[dict[str, Any]] = []
    seen_floors: set[Any] = set()
    current_act: int | None = None
    for index, record in enumerate(records):
        if record.get("_type") == "state:act":
            current_act = int(record["act"]) if isinstance(record.get("act"), (int, float)) else None
        if record.get("_type") != "state:floor" or "combat_state" not in record:
            continue
        floor = record.get("floor")
        if floor in seen_floors:
            continue
        seen_floors.add(floor)
        predecessor = records[index - 1] if index > 0 else None
        scene = audit_scene(
            records=records,
            run_state=run_state,
            floor_state=record,
            predecessor=predecessor,
            dynamic_ids=dynamic_ids,
            source_id=source_id,
            source_url=source_url,
            raw_hash=raw_hash,
        )
        scene["act"] = current_act
        scenes.append(scene)

    type_counts = Counter(str(record.get("_type")) for record in records)
    return {
        "source_kind": "github-runlogger-jsonl",
        "source_id": source_id,
        "source_url": source_url,
        "raw_sha256": raw_hash,
        "record_count": len(records),
        "record_type_counts": dict(sorted(type_counts.items())),
        "run": {
            "character": run_state.get("class"),
            "source_seed": run_state.get("seed"),
            "ascension": run_state.get("ascension", run_state.get("ascension_level")),
            "versions": run_state.get("versions"),
            "mods": classify_mods(run_state),
            "has_game_over": any(record.get("_type") == "state:game_over" for record in records),
            "group_key": run_group_key(run_state.get("class"), run_state.get("seed"), source_id),
        },
        "field_semantics_source": {
            "format_document": f"https://raw.githubusercontent.com/{RUNLOGGER_REPOSITORY}/{RUNLOGGER_COMMIT}/README.md",
            "serializer_source": f"https://github.com/{RUNLOGGER_REPOSITORY}/blob/{RUNLOGGER_COMMIT}/src/main/java/serializationmod/GameStateConverter.java",
            "conditional_fields": [
                "combat_state.draw_pile/discard_pile/exhaust_pile/hand/limbo only emitted when non-empty",
                "player.block only emitted when >0",
                "monster.damage only emitted when >0",
                "relic.counter only emitted when >-1",
            ],
        },
        "scene_count": len(scenes),
        "visible_entry_verified_scene_count": sum(
            scene["validation_status"]["visible_entry_status"] == "verified"
            for scene in scenes
        ),
        "internal_state_constructible_scene_count": sum(
            scene["validation_status"]["internal_state_status"] == "constructible"
            for scene in scenes
        ),
        "backend_supported_scene_count": sum(
            scene["validation_status"]["backend_status"] == "current_supported"
            for scene in scenes
        ),
        "scenes": scenes,
    }


def summarize_scenes(scenes: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总场景状态，方便文档引用而不读取原始日志。"""

    status_counts = Counter(scene.get("status") for scene in scenes)
    encounter_counts = Counter(
        scene.get("encounter", {}).get("scenario_id") or "unregistered"
        for scene in scenes
    )
    return {
        "count": len(scenes),
        "status_counts": dict(sorted(status_counts.items())),
        "encounter_counts": dict(sorted(encounter_counts.items())),
        "group_keys": sorted({str(scene.get("group_key")) for scene in scenes}),
    }


def github_tree_from_codeload(
    repository: str,
    commit: str,
    get: Callable[[str], bytes],
) -> tuple[list[str], dict[str, Any]]:
    """在 GitHub API 配额耗尽时，从固定提交 ZIP 的目录索引回退。"""

    url = f"https://codeload.github.com/{repository}/zip/{commit}"
    raw = get(url)
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"固定提交 codeload 响应不是 ZIP：{url}") from exc
    prefix = f"{repository.rsplit('/', 1)[-1]}-{commit}/"
    paths = [
        name[len(prefix):]
        for name in archive.namelist()
        if name.startswith(prefix)
        and not name.endswith("/")
        and name[len(prefix):]
    ]
    if not paths:
        raise RuntimeError(f"固定提交 codeload ZIP 没有可用文件：{url}")
    return sorted(paths), {
        "method": "github-codeload-zip",
        "url": url,
        "sha256": sha256_bytes(raw),
        "bytes": len(raw),
        "path_count": len(paths),
    }


def load_local_evidence(
    root: Path,
    *,
    expected_commit: str,
    limit: int,
) -> dict[str, Any]:
    """读取并校验上一轮生成的本地 raw/manifest，不触网也不信任索引哈希。"""

    manifest_path = root / "source-manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"找不到本地证据 manifest：{manifest_path}")
    manifest_raw = manifest_path.read_bytes()
    manifest = parse_json(manifest_raw, str(manifest_path))
    matiger = manifest.get("sources", {}).get("matiger", {})
    if matiger.get("commit") != expected_commit:
        raise ValueError("本地 evidence 的 MaT1g3R 提交与 --commit 不一致")
    selected_paths = matiger.get("selected_paths")
    if not isinstance(selected_paths, list) or len(selected_paths) != limit:
        raise ValueError("离线重生成要求 --limit 与本地 manifest 的样本数完全一致")
    entries = manifest.get("source_files", [])
    summary_by_path: dict[str, tuple[bytes, dict[str, Any]]] = {}
    runlogger_raw: bytes | None = None
    runlogger_meta: dict[str, Any] | None = None
    for entry in entries:
        local_name = entry.get("local_file")
        if not isinstance(local_name, str):
            raise ValueError("本地 manifest 缺少 local_file")
        local_path = root / local_name
        if not local_path.is_file():
            raise FileNotFoundError(f"本地 evidence 文件不存在：{local_path}")
        raw = local_path.read_bytes()
        actual_hash = sha256_bytes(raw)
        if actual_hash != entry.get("sha256"):
            raise ValueError(f"本地 evidence 哈希不匹配：{local_path}")
        if entry.get("source_kind") == "github-run-summary":
            summary_by_path[entry["source_path"]] = (raw, entry)
        elif entry.get("source_kind") == "github-runlogger-jsonl":
            runlogger_raw = raw
            runlogger_meta = entry
    if runlogger_raw is None or runlogger_meta is None:
        raise ValueError("本地 evidence 缺少 runlogger JSONL")
    if any(path not in summary_by_path for path in selected_paths):
        raise ValueError("本地 evidence 缺少 manifest 中选择的 summary 文件")

    archive = dict(manifest.get("sources", {}).get("archive", {}))
    metadata_name = archive.get("metadata_local_file")
    if isinstance(metadata_name, str):
        metadata_path = root / metadata_name
        if metadata_path.is_file():
            metadata_raw = metadata_path.read_bytes()
            metadata_hash = sha256_bytes(metadata_raw)
            if archive.get("metadata_sha256") != metadata_hash:
                raise ValueError(f"Archive 元数据哈希不匹配：{metadata_path}")
    return {
        "manifest_sha256": sha256_bytes(manifest_raw),
        "all_ironclad_file_count": int(matiger.get("all_ironclad_run_file_count", 0)),
        "selected_paths": selected_paths,
        "summary_by_path": summary_by_path,
        "runlogger_raw": runlogger_raw,
        "runlogger_meta": runlogger_meta,
        "archive": archive,
        "tree_access": {
            "method": "local-source-manifest",
            "manifest": "reference/public-run-audit/source-manifest.json",
            "manifest_sha256": sha256_bytes(manifest_raw),
            "path_count": int(matiger.get("all_ironclad_run_file_count", 0)),
            "api_fallback": None,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=12, help="逐层 .run 小样本数量")
    parser.add_argument("--commit", default=PUBLIC_RUN_COMMIT, help="MaT1g3R 仓库的固定完整提交 SHA")
    parser.add_argument("--output", type=Path, default=Path("reference/public-run-audit"))
    parser.add_argument("--index-dir", type=Path, default=Path("docs"))
    parser.add_argument("--timeout", type=int, default=40)
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--skip-archive-metadata", action="store_true")
    parser.add_argument("--offline", action="store_true", help="只读取已下载的 reference/public-run-audit")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        parser.error("--commit 必须是40位小写完整 SHA，避免跟随可变分支")
    if not 1 <= args.limit <= 100:
        parser.error("小样本审计数量必须为1到100")

    def get(url: str) -> bytes:
        return fetch(url, timeout=args.timeout, attempts=args.attempts)

    args.output.mkdir(parents=True, exist_ok=True)
    offline_evidence = None
    if args.offline:
        offline_evidence = load_local_evidence(
            args.output,
            expected_commit=args.commit,
            limit=args.limit,
        )
        all_run_paths = [f"<local-manifest-path-{index}>" for index in range(offline_evidence["all_ironclad_file_count"])]
        chosen_paths = list(offline_evidence["selected_paths"])
        tree_access = offline_evidence["tree_access"]
    else:
        tree_url = f"{GITHUB_API}/repos/{PUBLIC_RUN_REPOSITORY}/git/trees/{args.commit}?recursive=1"
        tree_access: dict[str, Any]
        try:
            tree_raw = get(tree_url)
            tree = parse_json(tree_raw, tree_url)
            if tree.get("truncated"):
                raise RuntimeError("仓库目录树不完整，拒绝声称完整清点")
            tree_paths = [
                item["path"]
                for item in tree.get("tree", [])
                if item.get("type") == "blob"
            ]
            tree_access = {
                "method": "github-rest-tree-api",
                "url": tree_url,
                "sha256": sha256_bytes(tree_raw),
                "bytes": len(tree_raw),
                "api_fallback": False,
            }
        except (RuntimeError, ValueError) as api_error:
            tree_paths, tree_access = github_tree_from_codeload(
                PUBLIC_RUN_REPOSITORY,
                args.commit,
                get,
            )
            tree_access["api_fallback"] = True
            tree_access["api_error"] = str(api_error)
        all_run_paths = sorted(
            path
            for path in tree_paths
            if str(path).lower().endswith(".run")
            and "ironclad" in str(path).lower()
        )
        chosen_paths = select_sample_paths(all_run_paths, args.limit)

    summary_records: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []
    for index, path in enumerate(chosen_paths):
        if offline_evidence is not None:
            raw, source_entry = offline_evidence["summary_by_path"][path]
            source_url = source_entry["source_url"]
            local_name = source_entry["local_file"]
        else:
            source_url = f"https://raw.githubusercontent.com/{PUBLIC_RUN_REPOSITORY}/{args.commit}/{path}"
            raw = get(source_url)
            local_name = f"matiger/sample-{index:03d}.run"
        run = parse_json(raw, source_url)
        local_path = args.output / local_name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(raw)
        raw_hash = sha256_bytes(raw)
        summary_records.append(audit_summary_run(run, path, raw_hash))
        source_files.append(
            {
                "source_kind": "github-run-summary",
                "source_path": path,
                "source_url": source_url,
                "local_file": local_name,
                "sha256": raw_hash,
                "bytes": len(raw),
            }
        )

    runlogger_url = f"https://raw.githubusercontent.com/{RUNLOGGER_REPOSITORY}/{RUNLOGGER_COMMIT}/{RUNLOGGER_EXAMPLE_PATH}"
    if offline_evidence is not None:
        runlogger_raw = offline_evidence["runlogger_raw"]
        runlogger_url = offline_evidence["runlogger_meta"]["source_url"]
    else:
        runlogger_raw = get(runlogger_url)
    runlogger_hash = sha256_bytes(runlogger_raw)
    runlogger_local_name = "runlogger/ironclad_1706139943.jsonl"
    runlogger_local = args.output / runlogger_local_name
    runlogger_local.parent.mkdir(parents=True, exist_ok=True)
    runlogger_local.write_bytes(runlogger_raw)
    runlogger_audit = audit_runlogger_log(
        runlogger_raw,
        source_id="runlogger-example-ironclad-1706139943",
        source_url=runlogger_url,
        raw_hash=runlogger_hash,
    )
    source_files.append(
        {
            "source_kind": "github-runlogger-jsonl",
            "source_path": RUNLOGGER_EXAMPLE_PATH,
            "source_url": runlogger_url,
            "local_file": runlogger_local_name,
            "sha256": runlogger_hash,
            "bytes": len(runlogger_raw),
        }
    )

    archive: dict[str, Any]
    if offline_evidence is not None:
        archive = dict(offline_evidence["archive"])
        archive["status"] = "local_manifest_reused"
    elif args.skip_archive_metadata:
        archive = {
            "status": "not_fetched_by_flag",
            "item_url": ARCHIVE_ITEM_URL,
            "metadata_url": ARCHIVE_METADATA_URL,
        }
    else:
        try:
            archive_raw = get(ARCHIVE_METADATA_URL)
            archive_path = args.output / "archive/slay-the-data.-7z.metadata.json"
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            archive_path.write_bytes(archive_raw)
            metadata = parse_json(archive_raw, ARCHIVE_METADATA_URL)
            files = metadata.get("files", [])
            archive_file = next((item for item in files if item.get("name") == "SlayTheData.7z"), {})
            archive = {
                "status": "metadata_fetched_not_archive_downloaded",
                "item_url": ARCHIVE_ITEM_URL,
                "metadata_url": ARCHIVE_METADATA_URL,
                "metadata_sha256": sha256_bytes(archive_raw),
                "metadata_local_file": "archive/slay-the-data.-7z.metadata.json",
                "archive_file": {
                    "name": archive_file.get("name"),
                    "bytes": int(archive_file["size"]) if str(archive_file.get("size", "")).isdigit() else archive_file.get("size"),
                    "md5": archive_file.get("md5"),
                    "downloaded": False,
                },
                "reason_not_downloaded": "约29 GiB压缩包；M2小样本审计不默认下载整库，当前未获得可随机取样的本地成员文件",
            }
        except Exception as exc:  # 记录限制，不把失败写成数据不存在
            archive = {
                "status": "metadata_fetch_failed",
                "item_url": ARCHIVE_ITEM_URL,
                "metadata_url": ARCHIVE_METADATA_URL,
                "error": f"{type(exc).__name__}: {exc}",
            }

    scenes = runlogger_audit["scenes"]
    exclusions = [
        {
            "source_kind": "github-run-summary",
            "source_run_id": row["source_run_id"],
            "group_key": row["group_key"],
            "status": "excluded",
            "reason_codes": row["reconstruction"]["reason_codes"],
            "exclusion_scope": "formal-admission",
            "reconstruction_status": row["reconstruction"]["status"],
            "source_path": row["source_path"],
            "raw_sha256": row["raw_sha256"],
        }
        for row in summary_records
    ]
    exclusions.extend(
        {
            "scene_id": scene["scene_id"],
            "source_kind": "github-runlogger-jsonl",
            "group_key": scene["group_key"],
            "status": "excluded",
            "reason_codes": scene["quality_flags"]["reason_codes"],
            "source_line": scene["source"]["source_line"],
            "raw_sha256": scene["source"]["raw_sha256"],
        }
        for scene in scenes
        if scene["status"] == "excluded"
    )
    all_groups = [row["group_key"] for row in summary_records] + [runlogger_audit["run"]["group_key"]]
    split_check = {
        "rule_version": "public-run-group-sha256-v1",
        "rule": "先按整局 group_key 计算 SHA-256 前8位 mod 100，再按 0-79/80-89/90-99 划 train/dev/reserved-eval；本次场景仍 audit-only",
        "unique_group_count": len(set(all_groups)),
        "source_record_count": len(all_groups),
        "duplicate_group_keys_across_sources": sorted(key for key, count in Counter(all_groups).items() if count > 1),
        "assignments": assign_group_split(sorted(set(all_groups))),
        "cross_split_leakage": False,
        "formal_split_applied": False,
    }

    audit = {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "sample_policy": "MaT1g3R 仓库按数据集分层、路径字典序轮询；不按胜负筛选；不是随机或代表性抽样",
        "sources": {
            "matiger": {
                "repository": PUBLIC_RUN_REPOSITORY,
                "commit": args.commit,
                "repository_url": f"https://github.com/{PUBLIC_RUN_REPOSITORY}/tree/{args.commit}",
                "license": "Apache-2.0（固定提交含 LICENSE；需审核者自行复核）",
                "all_ironclad_run_file_count": len(all_run_paths),
                "selected_file_count": len(chosen_paths),
                "selected_paths": chosen_paths,
                "tree_access": tree_access,
            },
            "runlogger": {
                "repository": RUNLOGGER_REPOSITORY,
                "commit": RUNLOGGER_COMMIT,
                "repository_url": f"https://github.com/{RUNLOGGER_REPOSITORY}/tree/{RUNLOGGER_COMMIT}",
                "license": "MIT（固定提交含 LICENSE；示例实际 README 称 Serialization Mod beta）",
                "example_path": RUNLOGGER_EXAMPLE_PATH,
                "example_url": runlogger_url,
                "independent_run_count": 1,
            },
            "archive": archive,
        },
        "summary_sample": {
            "independent_run_count": len({row["group_key"] for row in summary_records}),
            "ascensions": dict(sorted(Counter(str(row["ascension"]) for row in summary_records).items())),
            "versions": dict(sorted(Counter(str(row["build_version"]) for row in summary_records).items())),
            "characters": dict(sorted(Counter(str(row["character"]) for row in summary_records).items())),
            "encounters": dict(sorted(Counter(
                encounter
                for row in summary_records
                for encounter in row["encounters_from_damage_taken"]
            ).items())),
            "reconstruction_status_counts": dict(sorted(Counter(
                row["reconstruction"]["status"] for row in summary_records
            ).items())),
            "reconstruction_reason_counts": dict(sorted(Counter(
                reason
                for row in summary_records
                for reason in row["reconstruction"]["reason_codes"]
            ).items())),
            "rows": summary_records,
        },
        "detailed_sample": {
            "independent_run_count": 1,
            "ascensions": {str(runlogger_audit["run"]["ascension"]): 1},
            "versions": {str(runlogger_audit["run"]["versions"].get("sts")): 1},
            "encounter_groups": dict(sorted(Counter(
                ",".join(scene["encounter"]["monster_ids"])
                for scene in scenes
            ).items())),
            "audit": runlogger_audit,
        },
        "scene_summary": summarize_scenes(scenes),
        "exclusion_summary": dict(sorted(Counter(
            reason
            for item in exclusions
            for reason in item.get("reason_codes", [])
        ).items())),
        "split_check": split_check,
        "source_files": source_files,
        "limitations": [
            "MaT1g3R .run 已尝试入口A重建；入口B仍因 hand/piles/intent/control 缺失不可用，A仍因HP时点、遗物counter、药水库存和遭遇实例缺口不能形成正式场景",
            "Archive 约29 GiB压缩包只核验元数据，没有下载整库或声称其成员字段已验证",
            "详细 JSONL 只有一个公开示例，且没有 state:game_over；可行性不等于总体代表性",
            "详细日志的 hidden RNG/counter 不足以宣称逐步精确复盘；环境应重新分配复跑 seed",
            "场景未写入 PPO on-policy trajectory，当前 status 不是正式训练白名单",
        ],
    }

    scene_index = {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "generated_from": {
            "audit_raw_root": "reference/public-run-audit",
            "audit_sha256": sha256_bytes(canonical_bytes({"scenes": scenes})),
        },
        "scenes": scenes,
    }
    exclusion_index = {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "generated_from": {
            "audit_raw_root": "reference/public-run-audit",
            "audit_sha256": sha256_bytes(canonical_bytes({"exclusions": exclusions})),
        },
        "exclusions": exclusions,
    }
    source_manifest = {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "raw_root": "reference/public-run-audit",
        "source_files": source_files,
        "sources": audit["sources"],
        "raw_data_policy": "原始样本在 gitignored reference；提交只保留本索引、场景/排除清单与审计文档",
    }
    summary_reconstruction_index = {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "raw_root": "reference/public-run-audit",
        "sample_count": len(summary_records),
        "rows": [
            {
                "source_path": row["source_path"],
                "source_run_id": row["source_run_id"],
                "source_seed": row["source_seed"],
                "raw_sha256": row["raw_sha256"],
                "character": row["character"],
                "ascension": row["ascension"],
                "build_version": row["build_version"],
                "reconstruction_status": row["reconstruction"]["status"],
                "formal_candidate": row["reconstruction"]["formal_candidate"],
                "first_combat": row["reconstruction"]["attempted_modes"]["A_pre_combat_initialization"]["first_combat"],
                "a_status": row["reconstruction"]["attempted_modes"]["A_pre_combat_initialization"]["status"],
                "a_evidence": row["reconstruction"]["attempted_modes"]["A_pre_combat_initialization"],
                "a_deck_status": row["reconstruction"]["attempted_modes"]["A_pre_combat_initialization"]["deck"]["status"],
                "a_hp_status": row["reconstruction"]["attempted_modes"]["A_pre_combat_initialization"]["hp"]["status"],
                "a_relic_status": row["reconstruction"]["attempted_modes"]["A_pre_combat_initialization"]["relics"]["status"],
                "a_potion_status": row["reconstruction"]["attempted_modes"]["A_pre_combat_initialization"]["potions"]["status"],
                "a_encounter_status": row["reconstruction"]["attempted_modes"]["A_pre_combat_initialization"]["encounter"]["status"],
                "a_missing_or_ambiguous": row["reconstruction"]["attempted_modes"]["A_pre_combat_initialization"]["missing_or_ambiguous"],
                "b_missing_or_ambiguous": row["reconstruction"]["attempted_modes"]["B_post_combat_initialization_after_initial_draw"]["missing_or_ambiguous"],
            }
            for row in summary_records
        ],
    }

    write_json(args.output / "audit.json", audit)
    write_json(args.output / "scene-candidates.json", scene_index)
    write_json(args.output / "exclusions.json", exclusion_index)
    write_json(args.output / "source-manifest.json", source_manifest)
    write_json(args.output / "summary-reconstruction.json", summary_reconstruction_index)
    write_json(args.index_dir / "m2-scene-candidates.json", scene_index)
    write_json(args.index_dir / "m2-exclusions.json", exclusion_index)
    write_json(args.index_dir / "m2-summary-reconstruction.json", summary_reconstruction_index)
    write_json(
        args.index_dir / "m2-evidence-index.json",
        {
            "audit_schema_version": AUDIT_SCHEMA_VERSION,
            "raw_root": "reference/public-run-audit",
            "raw_manifest": "reference/public-run-audit/source-manifest.json",
            "audit_report": "reference/public-run-audit/audit.json",
            "scene_index": "docs/m2-scene-candidates.json",
            "exclusion_index": "docs/m2-exclusions.json",
            "summary_reconstruction_index": "docs/m2-summary-reconstruction.json",
            "summary_a_rule_constructible_count": sum(
                row["reconstruction"]["attempted_modes"]["A_pre_combat_initialization"]["rule_constructible"]
                for row in summary_records
            ),
            "summary_formal_candidate_count": sum(row["reconstruction"]["formal_candidate"] for row in summary_records),
            "source_files": source_files,
            "scene_count": len(scenes),
            "scene_status_counts": summarize_scenes(scenes)["status_counts"],
            "exclusion_count": len(exclusions),
            "split_check": split_check,
        },
    )

    print(
        json.dumps(
            {
                "audit_schema_version": AUDIT_SCHEMA_VERSION,
                "matiger_all_ironclad_files": len(all_run_paths),
                "matiger_sample_files": len(chosen_paths),
                "runlogger_runs": 1,
                "runlogger_scenes": len(scenes),
                "visible_entry_verified_internal_state_unproven": sum(
                    scene["status"] == "visible_entry_verified_internal_state_unproven"
                    for scene in scenes
                ),
                "internal_state_constructible": sum(
                    scene["validation_status"]["internal_state_status"] == "constructible"
                    for scene in scenes
                ),
                "excluded_scenes_and_summaries": len(exclusions),
                "archive_status": archive["status"],
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
