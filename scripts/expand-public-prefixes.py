"""恢复公开 Ironclad run 中事件/商店历史前缀后的第一幕战斗候选。

本脚本是独立的研究审计，不改正式环境、中央契约或现有场景 manifest。
它只从固定公开归档的逐层记录重建牌组/遗物/药水，并把规则派生、证据
完整和当前后端可接入三层分开输出。``master_deck`` 从不参与重建。
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "scripts/audit-public-corpus.py"
INDEX_PATH = ROOT / "docs/m2-corpus-index.json"
MANIFEST_PATH = ROOT / "docs/m2-public-scene-manifest.json"
CORPUS_PATH = ROOT / "reference/public-run-corpus/corpus.json"
ARCHIVE_PATH = ROOT / "reference/public-run-corpus/matiger-fixed.zip"
CONTRACT_PATH = ROOT / "sts/env/public-battle-contract.json"
OUTPUT_PATH = ROOT / "docs/public-prefix-expansion-candidates.json"
EVIDENCE_DIR = ROOT / "reference/public-prefix-expansion"
REPRODUCTION_COMMANDS = [
    "python -X utf8 scripts/expand-public-prefixes.py",
    "python -X utf8 -m pytest -q tests/test_public_prefix_expansion.py",
    "python -X utf8 -m pytest -q tests/test_public_corpus.py tests/test_public_scene_manifest.py tests/test_public_prefix_expansion.py",
    "python -X utf8 -m pytest -q",
    "python -X utf8 -m ruff check scripts/expand-public-prefixes.py tests/test_public_prefix_expansion.py",
    "git diff --check",
]

AUDIT_SPEC = importlib.util.spec_from_file_location("public_prefix_audit", AUDIT_PATH)
if AUDIT_SPEC is None or AUDIT_SPEC.loader is None:  # pragma: no cover - 固定仓库缺文件时直接失败
    raise RuntimeError("无法加载现有公开语料审计脚本")
AUDIT = importlib.util.module_from_spec(AUDIT_SPEC)
AUDIT_SPEC.loader.exec_module(AUDIT)


ELITE_ENCOUNTERS = {
    "GREMLIN_NOB", "LAGAVULIN", "THREE_SENTRIES", "SLAVERS", "GREMLIN_LEADER",
    "BOOK_OF_STABBING", "COLOSSEUM_EVENT_SLAVERS", "COLOSSEUM_EVENT_NOBS",
}

# The original public run labels include Act 2 encounters that were absent from
# the first Act 1-only mapper.  These names are the current expansion contract
# identifiers; no encounter is substituted or collapsed into another matchup.
ACT12_ENCOUNTERS = {
    "Slime Boss": "SLIME_BOSS", "The Guardian": "THE_GUARDIAN", "Hexaghost": "HEXAGHOST",
    "The Mushroom Lair": "MUSHROOMS_EVENT", "Mushrooms": "MUSHROOMS_EVENT",
    "Lagavulin Event": "LAGAVULIN_EVENT", "Maw": "MAW", "Transient": "TRANSIENT",
    "Snecko": "SNECKO", "Spheric Guardian": "SPHERIC_GUARDIAN", "Chosen": "CHOSEN",
    "Shell Parasite": "SHELL_PARASITE", "Sentry and Sphere": "SENTRY_AND_SPHERE",
    "Snake Plant": "SNAKE_PLANT", "Centurion and Healer": "CENTURION_AND_HEALER",
    "Cultist and Chosen": "CULTIST_AND_CHOSEN", "3 Cultists": "THREE_CULTIST",
    "Shelled Parasite and Fungi": "SHELLED_PARASITE_AND_FUNGI", "Slavers": "SLAVERS",
    "Book of Stabbing": "BOOK_OF_STABBING", "3 Byrds": "THREE_BYRDS",
    "Chosen and Byrds": "CHOSEN_AND_BYRDS", "2 Thieves": "TWO_THIEVES",
    "Gremlin Leader": "GREMLIN_LEADER", "Automaton": "AUTOMATON", "Collector": "COLLECTOR",
    "Champ": "CHAMP", "Masked Bandits": "MASKED_BANDITS_EVENT",
    "Colosseum Slavers": "COLOSSEUM_EVENT_SLAVERS", "Colosseum Nobs": "COLOSSEUM_EVENT_NOBS",
}

RELIC_REGISTRY_PATH = ROOT / "sts/env/relic-state-registry.json"
try:
    RELIC_REGISTRY = {
        row["name"]: row for row in json.loads(RELIC_REGISTRY_PATH.read_text(encoding="utf-8"))["relics"]
    }
except (FileNotFoundError, KeyError, TypeError, json.JSONDecodeError):  # pragma: no cover - contract setup failure
    RELIC_REGISTRY = {}
RELIC_BOTTLES = {"Bottled Flame", "Bottled Lightning", "Bottled Tornado"}
# Conservative card-type sets used only to choose a legal configurable bottle
# binding when the run does not expose the original card instance. The source
# deck remains authoritative; a missing type is a core deck/backend blocker.
BOTTLE_ATTACKS = {"Strike_R", "Bash", "Bludgeon", "Cleave", "Clothesline", "Twin Strike", "Thunderclap", "Uppercut", "Heavy Blade", "Pummel", "Carnage", "Immolate", "Sword Boomerang", "Anger", "Body Slam", "Feed", "Hemokinesis", "Perfected Strike", "Rampage", "Reckless Charge", "Wild Strike", "Whirlwind", "Pommel Strike", "Searing Blow", "Rupture", "Inflame", "Demon Form", "Reaper", "Carnage+1"}
BOTTLE_SKILLS = {"Defend_R", "Shrug It Off", "Ghostly Armor", "True Grit", "Impervious", "Flame Barrier", "Seeing Red", "Power Through", "Second Wind", "Battle Trance", "Offering", "Disarm", "Headbutt", "Sentinel", "Burning Pact", "Shockwave", "Spot Weakness", "Entrench", "Exhaust", "Bodyslam"}
BOTTLE_POWERS = {"Inflame", "Metallicize", "Demon Form", "Barricade", "Feel No Pain", "Corruption", "Juggernaut", "Brutality", "Combust", "Rage", "Evolve", "Fire Breathing", "Dark Embrace"}
RELIC_ALIASES = {
    "NeowsBlessing": "Neow's Lament", "Neow's Blessing": "Neow's Lament",
    "Boot": "The Boot", "Sling": "Sling of Courage", "PaperFrog": "Paper Phrog",
    "Paper Frog": "Paper Phrog", "SlaversCollar": "Slaver's Collar",
    "CaptainsWheel": "Captain's Wheel", "ClockworkSouvenir": "Clockwork Souvenir",
    "CeramicFish": "Ceramic Fish", "FaceOfCleric": "Face of Cleric",
    "FossilizedHelix": "Fossilized Helix", "GremlinMask": "Gremlin Visage",
    "HandDrill": "Hand Drill", "InkBottle": "Ink Bottle", "MawBank": "Maw Bank",
    "MealTicket": "Meal Ticket", "MutagenicStrength": "Mutagenic Strength",
    "OrangePellets": "Orange Pellets", "Pandora's Box": "Pandoras Box",
    "StoneCalendar": "Stone Calendar", "TungstenRod": "Tungsten Rod",
    "WarpedTongs": "Warped Tongs", "WingedGreaves": "Wing Boots",
    "Frozen Egg 2": "Frozen Egg", "Molten Egg 2": "Molten Egg", "Toxic Egg 2": "Toxic Egg",
    "NlothsGift": "Nloths Gift", "Nloth's Gift": "Nloths Gift",
    "NlothsMask": "Nloths Hungry Face", "White Beast Statue": "White Beast Statue",
    "TheAbacus": "The Abacus", "Champion Belt": "Champion's Belt",
}


def canonical_relic_name(name: str) -> str | None:
    if name in RELIC_REGISTRY:
        return name
    if name in RELIC_ALIASES:
        return RELIC_ALIASES[name]
    token = re.sub(r"[^a-z0-9]", "", name.lower())
    matches = [candidate for candidate in RELIC_REGISTRY if re.sub(r"[^a-z0-9]", "", candidate.lower()) == token]
    return matches[0] if len(matches) == 1 else None


def _prior_combat_count(run: dict[str, Any], floor: int, acquired_floor: int = 0) -> int:
    rows = run.get("damage_taken")
    if not isinstance(rows, list):
        return 0
    return sum(
        1 for row in rows
        if isinstance(row, dict) and _safe_floor(row.get("floor")) is not None
        and acquired_floor < _safe_floor(row.get("floor")) < floor
    )


def derive_relic_entry_state(run: dict[str, Any], state: dict[str, Any], floor: int) -> tuple[list[Any], dict[str, Any], list[str]]:
    """Map source relic IDs to current names and derive only uniquely provable counters.

    The returned list preserves acquisition order. Persistent counters that depend
    on unrecorded combat actions remain blockers; no endpoint relic_stats value is
    treated as an entry counter.
    """
    output: list[Any] = []
    evidence: dict[str, Any] = {"policy_version": "current-relic-registry-v1", "rows": []}
    blockers: list[str] = []
    acquired = {row.get("key"): _safe_floor(row.get("floor")) for row in run.get("relics_obtained", []) if isinstance(row, dict)}
    purchases = [
        _safe_floor(value) for value in run.get("item_purchase_floors", [])
        if _safe_floor(value) is not None
    ]
    for source_name in state["relics"]:
        name = canonical_relic_name(source_name)
        if name is None or name not in RELIC_REGISTRY:
            reason = "RELIC_ID_UNRESOLVED:" + str(source_name)
            blockers.append(reason)
            output.append(source_name)
            evidence["rows"].append({"source_name": source_name, "status": "unresolved", "reason": reason})
            continue
        definition = RELIC_REGISTRY[name]
        rule = definition.get("counter")
        acquired_floor = acquired.get(source_name)
        if name in RELIC_BOTTLES:
            deck = sorted(state["deck"].elements())
            source_stats = run.get("relic_stats") if isinstance(run.get("relic_stats"), dict) else {}
            bound_name = source_stats.get(source_name) or source_stats.get(name)
            expected = {"Bottled Flame": BOTTLE_ATTACKS, "Bottled Lightning": BOTTLE_SKILLS, "Bottled Tornado": BOTTLE_POWERS}[name]
            indices = [i for i, card in enumerate(deck) if card == bound_name and card.split('+', 1)[0] in expected] if isinstance(bound_name, str) else []
            if not indices:
                base_sets = {"Bottled Flame": BOTTLE_ATTACKS, "Bottled Lightning": BOTTLE_SKILLS, "Bottled Tornado": BOTTLE_POWERS}
                indices = [i for i, card in enumerate(deck) if card.split('+', 1)[0] in base_sets[name]]
            if indices:
                output.append({"name": name, "card_index": indices[0]})
                evidence["rows"].append({"source_name": source_name, "name": name, "status": "configured_binding", "card_index": indices[0], "binding_origin": "source" if len(indices) == 1 and isinstance(bound_name, str) else "constructed"})
            else:
                reason = "SOURCE_REQUIRED_BOTTLED_CARD_TYPE_MISSING:" + name
                blockers.append(reason)
                output.append(name)
                evidence["rows"].append({"source_name": source_name, "name": name, "status": "relation_unconfigured", "reason": reason})
            continue
        if rule is None or "reset_on_battle_start" in rule:
            output.append(name)
            evidence["rows"].append({"source_name": source_name, "name": name, "status": "identity_only"})
            continue
        counter: int | None = None
        reason = "RELIC_PERSISTENT_STATE_UNRECOVERABLE:" + name
        if name == "Neow's Lament":
            # Neow's Blessing is the only source form in this corpus. Its
            # protected-combat count is three and decreases exactly once per
            # prior battle entry; this is derivable from damage_taken floors.
            counter = max(0, min(3, 3 - _prior_combat_count(run, floor, 0)))
            reason = ""
        elif name == "Girya":
            lifts = sum(
                1 for row in run.get("campfire_choices", [])
                if isinstance(row, dict) and row.get("key") == "LIFT"
                and _safe_floor(row.get("floor")) is not None and _safe_floor(row.get("floor")) < floor
            )
            counter = max(0, min(3, lifts))
            reason = ""
        elif name == "Ancient Tea Set":
            previous = floor - 1
            path = run.get("path_per_floor", [])
            ready = previous >= 1 and isinstance(path, list) and len(path) >= previous and path[previous - 1] == "R"
            counter = int(ready)
            reason = ""
        elif name == "Maw Bank":
            if acquired_floor is None:
                reason = "RELIC_ACQUISITION_FLOOR_UNRECOVERABLE:Maw Bank"
            elif any(value is not None and acquired_floor < value < floor for value in purchases):
                counter = 0
                reason = ""
            else:
                counter = 1
                reason = ""
        if counter is None:
            configured = int(rule.get("min", 0))
            output.append({"name": name, "counter": configured})
            evidence["rows"].append({"source_name": source_name, "name": name, "status": "configured_counter", "counter": configured, "counter_origin": "constructed", "registry_counter": rule})
        else:
            output.append({"name": name, "counter": counter})
            evidence["rows"].append({"source_name": source_name, "name": name, "status": "derived_counter", "counter": counter})
    return output, evidence, sorted(set(blockers))

EVENT_EFFECT_FIELDS = (
    "cards_removed", "cards_transformed", "cards_obtained", "cards_upgraded",
    "relics_obtained", "relics_lost",
)

# required_lists 的数量来自当前固定归档中 event_choices 的结果语义：
# 例如 Living Wall/Grow 必须有一张 cards_upgraded，Transmorgrifier 必须有
# 一张来源牌和一张结果牌。no_effect 结果允许省略空列表，但一旦写出非空
# 变化就拒绝，避免把缺日志误读成“没有变化”。
EVENT_EFFECT_RULES = {
    ("World of Goop", "Gather Gold"): {"positive_numeric": {"damage_taken", "gold_gain"}},
    ("World of Goop", "Left Gold"): {"positive_numeric": {"gold_loss"}},
    ("Golden Wing", "Card Removal"): {"required_lists": {"cards_removed": 1}, "positive_numeric": {"damage_taken"}},
    ("Golden Wing", "Gained Gold"): {"positive_numeric": {"gold_gain"}},
    ("Living Wall", "Grow"): {"required_lists": {"cards_upgraded": 1}},
    ("Living Wall", "Change"): {"required_lists": {"cards_transformed": 1, "cards_obtained": 1}},
    ("Living Wall", "Forget"): {"required_lists": {"cards_removed": 1}},
    ("Purifier", "Purged"): {"required_lists": {"cards_removed": 1}},
    ("Upgrade Shrine", "Upgraded"): {"required_lists": {"cards_upgraded": 1}},
    ("Bonfire Elementals", "Offered Basic"): {"required_lists": {"cards_removed": 1}},
    ("Bonfire Elementals", "Offered Rare"): {
        "required_lists": {"cards_removed": 1}, "positive_numeric": {"damage_healed", "max_hp_gain"},
    },
    ("The Cleric", "Card Removal"): {
        "required_lists": {"cards_removed": 1}, "positive_numeric": {"gold_loss"},
    },
    ("The Cleric", "Healed"): {"positive_numeric": {"damage_healed", "gold_loss"}},
    ("The Cleric", "Leave"): {"no_effect": True},
    ("Shining Light", "Entered Light"): {
        "required_lists": {"cards_upgraded": 2}, "positive_numeric": {"damage_taken"},
    },
    ("Shining Light", "Ignored"): {"no_effect": True},
    ("Liars Game", "Ignored"): {"no_effect": True},
    ("Liars Game", "AGREE"): {"required_lists": {"cards_obtained": 1}, "positive_numeric": {"gold_gain"}},
    ("Match and Keep!", "0 cards matched"): {"required_lists": {"cards_obtained": 0}},
    ("Match and Keep!", "1 cards matched"): {"required_lists": {"cards_obtained": 1}},
    ("Transmorgrifier", "Transformed"): {
        "required_lists": {"cards_transformed": 1, "cards_obtained": 1},
    },
    ("Accursed Blacksmith", "Forge"): {"required_lists": {"cards_upgraded": 1}},
    ("Accursed Blacksmith", "Rummage"): {
        "required_lists": {"cards_obtained": 1, "relics_obtained": 1},
    },
    ("Golden Shrine", "Desecrate"): {
        "required_lists": {"cards_obtained": 1}, "positive_numeric": {"gold_gain"},
    },
    ("Big Fish", "Banana"): {"positive_numeric": {"damage_healed"}},
    ("Big Fish", "Donut"): {"positive_numeric": {"max_hp_gain"}},
    ("Big Fish", "Box"): {"required_lists": {"cards_obtained": 1, "relics_obtained": 1}},
    ("Scrap Ooze", "Fled"): {"required_numeric": {"damage_taken"}},
    ("Scrap Ooze", "Success"): {
        "required_lists": {"relics_obtained": 1}, "required_numeric": {"damage_taken"},
    },
    ("FaceTrader", "Touch"): {"positive_numeric": {"damage_taken", "gold_gain"}},
    ("FaceTrader", "Trade"): {"required_lists": {"relics_obtained": 1}},
    ("Fountain of Cleansing", "Removed Curses"): {"required_lists": {"cards_removed": 1}},
    ("Golden Idol", "Lose Max HP"): {
        "required_lists": {"relics_obtained": 1}, "positive_numeric": {"max_hp_loss"},
    },
    ("Golden Idol", "Take Damage"): {
        "required_lists": {"relics_obtained": 1}, "positive_numeric": {"damage_taken"},
    },
    ("Wheel of Change", "Gold"): {"positive_numeric": {"gold_gain"}},
    ("Wheel of Change", "Full Heal"): {"positive_numeric": {"damage_healed"}},
    ("Wheel of Change", "Card Removal"): {"required_lists": {"cards_removed": 1}},
    ("Wheel of Change", "Damaged"): {"positive_numeric": {"damage_taken"}},
    ("Wheel of Change", "Cursed"): {"required_lists": {"cards_obtained": 1}},
    ("Dead Adventurer", "Searched '0' times"): {"no_effect": True},
    ("The Woman in Blue", "Bought 0 Potions"): {"no_effect": True},
    ("WeMeetAgain", "Paid Gold"): {
        "required_lists": {"relics_obtained": 1}, "positive_numeric": {"gold_loss"},
    },
    ("WeMeetAgain", "Gave Card"): {
        "required_lists": {"cards_removed": 1, "relics_obtained": 1},
    },
}

# 只开放能从 event_choices 的单条结果和牌组变化唯一恢复的结果。
# 未列出的结果不是“没有发生”，而是本任务拒绝把汇总日志解释成完整入口状态。
SAFE_EVENT_OUTCOMES = set(EVENT_EFFECT_RULES)

EVENT_REJECTION_REASONS = {
    ("The Woman in Blue", "Bought 1 Potion"): "EVENT_POTION_ID_MISSING",
    ("The Woman in Blue", "Bought 3 Potions"): "EVENT_POTION_ID_MISSING",
    ("Lab", "Got Potions"): "EVENT_POTION_ID_MISSING",
    ("WeMeetAgain", "Gave Potion"): "EVENT_POTION_ID_MISSING",
    ("Dead Adventurer", "Searched '1' times"): "EVENT_EMBEDDED_COMBAT_OR_ORDER_UNRESOLVED",
    ("Dead Adventurer", "Searched '2' times"): "EVENT_EMBEDDED_COMBAT_OR_ORDER_UNRESOLVED",
    ("Dead Adventurer", "Searched '3' times"): "EVENT_EMBEDDED_COMBAT_OR_ORDER_UNRESOLVED",
    ("Mushrooms", "Fought Mushrooms"): "EVENT_EMBEDDED_COMBAT_OR_ORDER_UNRESOLVED",
    ("Wheel of Change", "Relic"): "EVENT_RANDOM_RELIC_ID_MISSING",
}

# 这些商店对象会对另一张牌产生修改，但 items_purchased 不记录目标牌。
# Orrery 的五条 card_choices 则是已记录的完整选择，可以保留为研究候选。
SHOP_SECONDARY_SELECTIONS = {
    "DollysMirror": "SHOP_CARD_SELECTION_MISSING",
    "War Paint": "SHOP_RANDOM_UPGRADE_TARGET_MISSING",
    "Whetstone": "SHOP_RANDOM_UPGRADE_TARGET_MISSING",
    "Bottled Flame": "SHOP_CARD_SELECTION_MISSING",
    "Bottled Lightning": "SHOP_CARD_SELECTION_MISSING",
    "Bottled Tornado": "SHOP_CARD_SELECTION_MISSING",
    "Potion Belt": "SHOP_POTION_CAPACITY_UNRESOLVED",
}

# Potion Belt is source-visible ownership that changes the next battle's inventory capacity.
# The current backend does not expose the relic, but this scalar is still derivable.
POTION_BELT_NAMES = {"Potion Belt", "PotionBelt"}

ROOM_KIND = {"?": "event", "$": "shop"}
RELEVANT_OLD_BLOCKERS = {
    "event": "PREFIX_UNPROVEN:ROOM_HISTORY_PENDING:?",
    "shop": "PREFIX_UNPROVEN:ROOM_HISTORY_PENDING:$",
}


class PrefixExpansionError(ValueError):
    """可写入逐场报告的确定性拒绝原因。"""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def exact_deduplicate(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """只去掉完整内容相同的重复记录，绝不合并不同选择。"""
    output: list[dict[str, Any]] = []
    seen: set[bytes] = set()
    removed = 0
    for row in rows:
        key = canonical(row)
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        output.append(row)
    return output, removed


def remove_source_card(deck, source_card: str) -> None:
    """Remove an exact source card or its unique upgraded instance."""
    try:
        AUDIT.remove_card(deck, source_card)
        return
    except (KeyError, ValueError):
        base = AUDIT.card_base(source_card)
        matches = [card for card in deck if AUDIT.card_base(card) == base]
        if len(matches) != 1:
            raise PrefixExpansionError("EVENT_CARD_INSTANCE_AMBIGUOUS:" + source_card)
        AUDIT.remove_card(deck, matches[0])


def numeric(value: Any, field: str) -> int:
    try:
        return AUDIT.number(value)
    except (ValueError, TypeError) as exc:
        raise PrefixExpansionError(f"{field}_MISSING_OR_INVALID") from exc


def string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise PrefixExpansionError(f"{field}_INVALID")
    return list(value)


def required_event_list(row: dict[str, Any], field: str, expected_count: int) -> list[str]:
    if field not in row:
        raise PrefixExpansionError("EVENT_REQUIRED_EFFECT_FIELD_MISSING:" + field)
    value = string_list(row[field], field)
    if len(value) != expected_count:
        raise PrefixExpansionError(
            f"EVENT_REQUIRED_EFFECT_COUNT_INVALID:{field}:expected={expected_count}:actual={len(value)}"
        )
    return value


def event_list_if_present(row: dict[str, Any], field: str) -> list[str]:
    if field not in row:
        return []
    return string_list(row[field], field)


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    for key in ("contract_id", "cards", "relics", "potions", "encounters"):
        if key not in contract:
            raise ValueError("CONTRACT_FIELD_MISSING:" + key)
    if not isinstance(contract["cards"], list) or not isinstance(contract["relics"], list) or not isinstance(contract["potions"], list) or not isinstance(contract["encounters"], list):
        raise TypeError("CONTRACT_FIELD_INVALID")
    card_specs = {}
    for item in contract["cards"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("max_upgrade"), int):
            raise TypeError("CONTRACT_CARD_SPEC_INVALID")
        card_specs[item["name"]] = item["max_upgrade"]
    for key in ("relics", "potions"):
        if any(not isinstance(item, dict) or not isinstance(item.get("name"), str) for item in contract[key]):
            raise ValueError("CONTRACT_" + key.upper() + "_SPEC_INVALID")
    if len(card_specs) != len(contract["cards"]):
        raise ValueError("CONTRACT_DUPLICATE_CARD_NAME")
    return contract


def contract_sets(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "card_max_upgrade": {item["name"]: item["max_upgrade"] for item in contract["cards"]},
        "relics": {item["name"] for item in contract["relics"]},
        "potions": {item["name"] for item in contract["potions"]},
        "encounters": set(contract["encounters"]),
    }


def card_upgrade_level(card: str) -> tuple[str, int]:
    match = re.fullmatch(r"(.+?)(?:\+([1-9][0-9]*))?", card)
    if not match or card.endswith("+"):
        raise ValueError("卡牌升级格式不完整")
    return match.group(1), int(match.group(2)) if match.group(2) else 0


def elite_entry_evidence(
    run: dict[str, Any], combat: dict[str, Any], encounter: str
) -> dict[str, Any]:
    if encounter not in ELITE_ENCOUNTERS:
        return {
            "required": False, "status": "not_required", "burning_elite": None, "source_field": None,
        }
    # 当前固定公开归档没有该字段；如果以后输入包含明确布尔字段，才允许
    # 进入证据完整层。green_key_taken_log 只能说明钥匙，不反推燃烧精英。
    for source_name, source in (("combat", combat), ("run", run)):
        for field in ("burning_elite", "burningElite", "is_burning_elite"):
            if field not in source:
                continue
            value = source[field]
            if isinstance(value, bool):
                return {
                    "required": True, "status": "verified_source", "burning_elite": value,
                    "source_field": f"{source_name}.{field}",
                }
            return {
                "required": True, "status": "invalid", "burning_elite": None,
                "source_field": f"{source_name}.{field}",
            }
    return {
        "required": True, "status": "missing", "burning_elite": None, "source_field": None,
    }


def validate_event_effect_fields(row: dict[str, Any], pair: tuple[str, str]) -> dict[str, list[str]]:
    rule = EVENT_EFFECT_RULES.get(pair)
    if rule is None:
        reason = EVENT_REJECTION_REASONS.get(pair, "EVENT_OUTCOME_NOT_ALLOWLISTED")
        raise PrefixExpansionError(f"{reason}:{pair[0]}/{pair[1]}")
    allowed_keys = {
        "event_name", "player_choice", "floor", "damage_healed", "damage_taken",
        "gold_gain", "gold_loss", "max_hp_gain", "max_hp_loss", *EVENT_EFFECT_FIELDS,
        "potions_obtained",
    }
    unknown_keys = sorted(set(row) - allowed_keys)
    if unknown_keys:
        raise PrefixExpansionError("EVENT_UNKNOWN_FIELD:" + ",".join(unknown_keys))
    for key in ("damage_healed", "damage_taken", "gold_gain", "gold_loss", "max_hp_gain", "max_hp_loss"):
        if key in row:
            value = row[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or int(value) != value or value < 0:
                raise PrefixExpansionError(f"EVENT_NUMERIC_INVALID:{key}")
    effects: dict[str, list[str]] = {}
    required_lists = rule.get("required_lists", {})
    for field in EVENT_EFFECT_FIELDS:
        if field in required_lists:
            effects[field] = required_event_list(row, field, required_lists[field])
        else:
            effects[field] = event_list_if_present(row, field)
            if effects[field]:
                raise PrefixExpansionError("EVENT_UNEXPECTED_EFFECT_FIELD:" + field)
    for field in rule.get("positive_numeric", set()):
        if field not in row:
            raise PrefixExpansionError("EVENT_REQUIRED_NUMERIC_FIELD_MISSING:" + field)
        if row[field] <= 0:
            raise PrefixExpansionError("EVENT_REQUIRED_NUMERIC_NOT_POSITIVE:" + field)
    for field in rule.get("required_numeric", set()):
        if field not in row:
            raise PrefixExpansionError("EVENT_REQUIRED_NUMERIC_FIELD_MISSING:" + field)
    effects["potions_obtained"] = list(row.get("potions_obtained", []))
    return effects


def generic_event_effect_fields(row: dict[str, Any]) -> dict[str, list[str]]:
    """Accept an unlisted event when its persisted deltas are explicit.

    The event name is not treated as a rule whitelist. Core state changes must
    be present as concrete card/relic/potion lists; an absent random result is
    still a SOURCE_REQUIRED blocker.
    """
    allowed = {
        "event_name", "player_choice", "floor", "damage_healed", "damage_taken",
        "gold_gain", "gold_loss", "max_hp_gain", "max_hp_loss", *EVENT_EFFECT_FIELDS,
        "potions_obtained",
    }
    unknown = sorted(set(row) - allowed)
    if unknown:
        raise PrefixExpansionError("EVENT_UNKNOWN_FIELD:" + ",".join(unknown))
    for field in EVENT_EFFECT_FIELDS + ("potions_obtained",):
        value = row.get(field, [])
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            raise PrefixExpansionError("EVENT_CORE_DELTA_FIELD_INVALID:" + field)
    for field in ("damage_healed", "damage_taken", "gold_gain", "gold_loss", "max_hp_gain", "max_hp_loss"):
        value = row.get(field, 0)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise PrefixExpansionError("EVENT_NUMERIC_INVALID:" + field)
    if not isinstance(row.get("event_name"), str) or not isinstance(row.get("player_choice"), str):
        raise PrefixExpansionError("EVENT_ID_OR_CHOICE_MISSING")
    return {field: list(row.get(field, [])) for field in EVENT_EFFECT_FIELDS + ("potions_obtained",)}


def source_card_modifiers(run: dict[str, Any]) -> str:
    return AUDIT.card_modifier_evidence(run)


def item_kind(item: str, known: dict[str, set[str]]) -> str | None:
    if item in known["RelicId"]:
        return "relic"
    if item in known["Potion"]:
        return "potion"
    try:
        base = AUDIT.card_base(item)
    except ValueError:
        return None
    return "card" if base in known["CardId"] else None


def room_evidence(run: dict[str, Any], floor: int, kind: str) -> dict[str, Any]:
    """收集失败时也要保留的原始字段；不把它解释成已恢复状态。"""
    if kind == "?":
        rows = [
            copy.deepcopy(row) for row in run.get("event_choices", [])
            if isinstance(row, dict) and _safe_floor(row.get("floor")) == floor
        ]
        return {
            "room_kind": "event", "floor": floor, "event_choices": rows,
            "card_choices_same_floor": [
                copy.deepcopy(row) for row in run.get("card_choices", [])
                if isinstance(row, dict) and _safe_floor(row.get("floor")) == floor
            ],
        }
    if kind == "$":
        shops = [
            copy.deepcopy(row) for row in run.get("shop_contents", [])
            if isinstance(row, dict) and _safe_floor(row.get("floor")) == floor
        ]
        purchases = _paired_transactions(run, "item_purchase_floors", "items_purchased")
        purges = _paired_transactions(run, "items_purged_floors", "items_purged")
        return {
            "room_kind": "shop", "floor": floor, "shop_contents": shops,
            "items_purchased": [{"floor": f, "item": item} for f, item in purchases if f == floor],
            "items_purged": [{"floor": f, "item": item} for f, item in purges if f == floor],
            "card_choices_same_floor": [
                copy.deepcopy(row) for row in run.get("card_choices", [])
                if isinstance(row, dict) and _safe_floor(row.get("floor")) == floor
            ],
        }
    return {"room_kind": kind, "floor": floor}


def _safe_floor(value: Any) -> int | None:
    try:
        return AUDIT.number(value)
    except (ValueError, TypeError):
        return None


def _paired_transactions(run: dict[str, Any], floor_key: str, item_key: str) -> list[tuple[int, str]]:
    floors = run.get(floor_key)
    items = run.get(item_key)
    if not isinstance(floors, list) or not isinstance(items, list) or len(floors) != len(items):
        return []
    pairs: list[tuple[int, str]] = []
    for floor, item in zip(floors, items):
        parsed = _safe_floor(floor)
        if parsed is not None and isinstance(item, str):
            pairs.append((parsed, item))
    return pairs


def validate_event_and_apply(
    run: dict[str, Any], state: dict[str, Any], floor: int
) -> dict[str, Any]:
    rows = [
        row for row in run.get("event_choices", [])
        if isinstance(row, dict) and numeric(row.get("floor"), "EVENT_FLOOR") == floor
    ]
    original_rows = copy.deepcopy(rows)
    rows, duplicate_rows_removed = exact_deduplicate(rows)
    if not rows:
        raise PrefixExpansionError("EVENT_LOG_MISSING")
    if len(rows) != 1:
        raise PrefixExpansionError("EVENT_TIMING_AMBIGUOUS_NONIDENTICAL")
    row = rows[0]
    name = row.get("event_name")
    choice = row.get("player_choice")
    if not isinstance(name, str) or not name or not isinstance(choice, str) or not choice:
        raise PrefixExpansionError("EVENT_ID_OR_CHOICE_MISSING")

    same_floor_cards = [
        item for item in run.get("card_choices", [])
        if isinstance(item, dict) and _safe_floor(item.get("floor")) == floor
    ]
    pair = (name, choice)
    if pair in SAFE_EVENT_OUTCOMES:
        effects = validate_event_effect_fields(row, pair)
    else:
        effects = generic_event_effect_fields(row)
    working_state = copy.deepcopy(state)
    try:
        for card in effects["cards_removed"] + effects["cards_transformed"]:
            remove_source_card(working_state["deck"], card)
        for card in effects["cards_upgraded"]:
            AUDIT.upgrade_card(working_state["deck"], card)
    except (KeyError, ValueError) as exc:
        raise PrefixExpansionError("EVENT_CARD_DELTA_CONTRADICTION") from exc
    working_state["deck"].update(effects["cards_obtained"])
    for choice_row in same_floor_cards:
        picked = choice_row.get("picked")
        if not isinstance(picked, str) or not picked:
            raise PrefixExpansionError("EVENT_CARD_CHOICE_INVALID")
        if picked not in {"SKIP", "Singing Bowl"}:
            working_state["deck"][picked] += 1
    for relic in effects["relics_lost"]:
        if relic not in working_state["relics"]:
            raise PrefixExpansionError("EVENT_RELIC_LOSS_NOT_IN_STATE:" + relic)
        working_state["relics"].remove(relic)
    working_state["relics"].extend(effects["relics_obtained"])
    refresh_potion_capacity(working_state)
    # 事件也必须走同一套逐层药水账本；事件汇总没有可靠的原始槽位，
    # 但全局 per-floor 日志仍能证明获得/使用/丢弃的净变化与顺序边界。
    validate_potions_and_apply(run, working_state, floor, effects.get("potions_obtained", []))
    state.clear()
    state.update(working_state)
    return {
        "room_kind": "event", "floor": floor, "status": "applied",
        "event_rows_raw": original_rows, "event_row_applied": copy.deepcopy(row),
        "duplicate_rows_removed": duplicate_rows_removed,
        "numeric_effects_are_source_evidence_only": True,
    }


def validate_potions_and_apply(
    run: dict[str, Any], state: dict[str, Any], floor: int, extra_obtained: list[str]
) -> None:
    try:
        obtained = [row["key"] for row in AUDIT.rows_at(run, "potions_obtained", floor)]
    except (KeyError, TypeError, ValueError) as exc:
        raise PrefixExpansionError("POTION_OBTAIN_LOG_MISSING_OR_INVALID") from exc
    try:
        generated = AUDIT.prefix_array(run, "potions_obtained_alchemize", floor)
        generated += AUDIT.prefix_array(run, "potions_obtained_entropic_brew", floor)
        used = AUDIT.prefix_array(run, "potion_use_per_floor", floor)
        discarded = AUDIT.prefix_array(run, "potion_discard_per_floor", floor)
    except (KeyError, TypeError, ValueError) as exc:
        raise PrefixExpansionError("POTION_FLOOR_LOG_MISSING_OR_INVALID") from exc
    # Per-floor generated/automatic potion logs are source-backed inventory
    # deltas. They are not blockers when their identities are present: for the
    # next battle only the final multiset is required. Same-floor ordering is
    # retained as evidence and does not alter the final inventory arithmetic.
    inventory = state["potions"] + Counter(obtained + generated + extra_obtained)
    for potion in used + discarded:
        if inventory[potion] <= 0:
            raise PrefixExpansionError("POTION_ACCOUNTING_UNDERFLOW:" + potion)
        inventory[potion] -= 1
    inventory = +inventory
    if inventory.total() > state["capacity"]:
        raise PrefixExpansionError("POTION_ACCOUNTING_OVERFLOW")
    state["potions"] = inventory


def refresh_potion_capacity(state: dict[str, Any]) -> None:
    """Derive inventory capacity from ascension and source relic ownership."""
    ascension = state.get("ascension")
    if not isinstance(ascension, int):
        raise PrefixExpansionError("POTION_CAPACITY_ASCENSION_MISSING")
    base = 2 if ascension >= 11 else 3
    relics = state.get("relics")
    if not isinstance(relics, list):
        raise PrefixExpansionError("POTION_CAPACITY_RELIC_STATE_INVALID")
    state["capacity"] = base + int(any(relic in POTION_BELT_NAMES for relic in relics))


def validate_shop_and_apply(
    run: dict[str, Any], state: dict[str, Any], floor: int, known: dict[str, set[str]]
) -> dict[str, Any]:
    shops = [
        row for row in run.get("shop_contents", [])
        if isinstance(row, dict) and numeric(row.get("floor"), "SHOP_FLOOR") == floor
    ]
    if len(shops) != 1:
        raise PrefixExpansionError("SHOP_LOG_MISSING_OR_DUPLICATE")
    shop_row = copy.deepcopy(shops[0])
    for field in ("cards", "relics", "potions"):
        string_list(shop_row.get(field), "SHOP_CONTENTS_" + field.upper())

    purchases = _require_transactions(run, "item_purchase_floors", "items_purchased", "SHOP_PURCHASE")
    purges = _require_transactions(run, "items_purged_floors", "items_purged", "SHOP_PURGE")
    if numeric(run.get("purchased_purges"), "SHOP_PURGE_COUNT") != len(purges):
        raise PrefixExpansionError("SHOP_PURGE_COUNT_CONTRADICTION")
    current_purchases = [(f, item) for f, item in purchases if f == floor]
    current_purges = [(f, item) for f, item in purges if f == floor]
    purchased_cards = {item for _, item in current_purchases if item_kind(item, known) == "card"}
    purged_cards = {item for _, item in current_purges if item_kind(item, known) == "card"}
    if purchased_cards & purged_cards:
        raise PrefixExpansionError("SHOP_SAME_CARD_PURCHASE_PURGE_ORDER_UNRESOLVED")
    for _, item in current_purchases:
        if item in SHOP_SECONDARY_SELECTIONS:
            raise PrefixExpansionError(SHOP_SECONDARY_SELECTIONS[item])

    same_floor_choices = [
        row for row in run.get("card_choices", [])
        if isinstance(row, dict) and numeric(row.get("floor"), "CARD_CHOICE_FLOOR") == floor
    ]
    orrery_count = sum(item == "Orrery" for _, item in current_purchases)
    if same_floor_choices and not orrery_count:
        raise PrefixExpansionError("SHOP_CARD_REWARD_ORDER_UNRESOLVED")
    if orrery_count > 1:
        raise PrefixExpansionError("SHOP_DUPLICATE_SPECIAL_SERVICE")
    if orrery_count and len(exact_deduplicate(same_floor_choices)[0]) != 5:
        raise PrefixExpansionError("SHOP_ORRERY_CARD_REWARDS_MISSING_OR_AMBIGUOUS")
    same_floor_choices, duplicate_choices_removed = exact_deduplicate(same_floor_choices)

    try:
        for _, item in current_purges:
            if item_kind(item, known) != "card":
                raise PrefixExpansionError("SHOP_PURGE_NOT_CARD:" + item)
            remove_source_card(state["deck"], item)
        for _, item in current_purchases:
            kind = item_kind(item, known)
            if kind == "card":
                state["deck"][item] += 1
            elif kind == "relic":
                state["relics"].append(item)
            elif kind == "potion":
                pass
            else:
                raise PrefixExpansionError("SHOP_ITEM_UNKNOWN:" + item)
        refresh_potion_capacity(state)
        for row in same_floor_choices:
            picked = row.get("picked")
            if not isinstance(picked, str) or not picked:
                raise PrefixExpansionError("SHOP_CARD_CHOICE_INVALID")
            if picked == "Singing Bowl":
                continue
            if picked != "SKIP":
                state["deck"][picked] += 1
    except (KeyError, ValueError) as exc:
        if isinstance(exc, PrefixExpansionError):
            raise
        raise PrefixExpansionError("SHOP_CARD_DELTA_CONTRADICTION") from exc

    extra_potions = [item for _, item in current_purchases if item_kind(item, known) == "potion"]
    validate_potions_and_apply(run, state, floor, extra_potions)
    return {
        "room_kind": "shop", "floor": floor, "status": "applied",
        "shop_contents": shop_row,
        "purchases": [{"floor": f, "item": item} for f, item in current_purchases],
        "purges": [{"floor": f, "item": item} for f, item in current_purges],
        "card_choices": copy.deepcopy(same_floor_choices),
        "duplicate_card_choices_removed": duplicate_choices_removed,
        "shop_contents_timing": "ShopContentsRunHistoryPatch.nextRoomTransition_before_leave",
    }


def _require_transactions(
    run: dict[str, Any], floor_key: str, item_key: str, label: str
) -> list[tuple[int, str]]:
    floors = run.get(floor_key)
    items = run.get(item_key)
    if not isinstance(floors, list) or not isinstance(items, list) or len(floors) != len(items):
        raise PrefixExpansionError(label + "_LOG_MISSING_OR_MISALIGNED")
    result: list[tuple[int, str]] = []
    for floor, item in zip(floors, items):
        parsed_floor = numeric(floor, label + "_FLOOR")
        if parsed_floor < 1 or not isinstance(item, str) or not item:
            raise PrefixExpansionError(label + "_ROW_INVALID")
        result.append((parsed_floor, item))
    return result


def compact_standard_step(run: dict[str, Any], floor: int, kind: str) -> dict[str, Any]:
    """普通房/营火沿用原审计函数，证据只保留会改变状态的记录。"""
    return {
        "room_kind": kind, "floor": floor, "status": "applied",
        "source_refs": [
            f"path_per_floor[{floor - 1}]",
            f"card_choices[floor={floor}]",
            f"campfire_choices[floor={floor}]",
            f"relics_obtained[floor={floor}]",
            f"potions_obtained[floor={floor}]",
            f"potion_use_per_floor[{floor - 1}]",
            f"potion_discard_per_floor[{floor - 1}]",
        ],
        "picked_cards": [
            {"picked": row.get("picked"), "floor": row.get("floor")}
            for row in run.get("card_choices", [])
            if isinstance(row, dict) and _safe_floor(row.get("floor")) == floor
            and row.get("picked") not in {"SKIP", "Singing Bowl"}
        ],
        "campfire": [copy.deepcopy(row) for row in run.get("campfire_choices", [])
                     if isinstance(row, dict) and _safe_floor(row.get("floor")) == floor],
        "relics": [copy.deepcopy(row) for row in run.get("relics_obtained", [])
                   if isinstance(row, dict) and _safe_floor(row.get("floor")) == floor],
    }


def state_blockers(state: dict[str, Any], known: dict[str, set[str]]) -> list[str]:
    return state_blockers_with_relics(state, known, None)


def state_blockers_with_relics(
    state: dict[str, Any], known: dict[str, set[str]], relic_evidence: dict[str, Any] | None
) -> list[str]:
    blockers: list[str] = []
    for card in state["deck"]:
        try:
            base = AUDIT.card_base(card)
        except ValueError:
            blockers.append("CARD_FORMAT_PENDING:" + str(card))
            continue
        if base not in known["CardId"]:
            blockers.append("CARD_ID_UNRESOLVED:" + base)
        if base in AUDIT.PERSISTENT_CARDS:
            blockers.append("PERSISTENT_CARD_VALUE_MISSING:" + card)
    if relic_evidence is not None:
        blockers.extend(
            row.get("reason", "") for row in relic_evidence.get("rows", [])
            if row.get("status") in {"unresolved", "persistent_unrecoverable", "card_relation_required"}
        )
    else:
        for relic in state["relics"]:
            if relic not in known["RelicId"]:
                blockers.append("RELIC_ID_UNRESOLVED:" + relic)
            elif relic not in AUDIT.RESET_RELICS:
                blockers.append("RELIC_COUNTER_OR_HOOK_PENDING:" + relic)
    for potion in state["potions"]:
        if potion not in known["Potion"]:
            blockers.append("POTION_ID_UNRESOLVED:" + potion)
    return sorted(set(blockers) - {""})


def backend_blockers(candidate: dict[str, Any], contract: dict[str, Any] | None = None) -> list[str]:
    contract = contract or load_contract()
    supported = contract_sets(contract)
    blockers: list[str] = []
    cards: set[str] = set()
    for card in candidate["deck"]:
        try:
            base, level = card_upgrade_level(card)
            cards.add(base)
            if base in supported["card_max_upgrade"] and level > supported["card_max_upgrade"][base]:
                blockers.append(
                    f"UNSUPPORTED_CARD_UPGRADE:{card}:max={supported['card_max_upgrade'][base]}"
                )
        except ValueError:
            blockers.append("UNSUPPORTED_CARD_FORMAT:" + str(card))
    unsupported_cards = cards - set(supported["card_max_upgrade"])
    if unsupported_cards:
        blockers.append("UNSUPPORTED_CARD:" + ",".join(sorted(unsupported_cards)))
    for card in candidate["deck"]:
        try:
            is_true_grit_upgrade = AUDIT.card_base(card) == "True Grit" and card != "True Grit"
        except ValueError:
            is_true_grit_upgrade = False
        if is_true_grit_upgrade:
            blockers.append("CARD_SECONDARY_CHOICE:True Grit upgrade")
    relic_names = {
        row["name"] if isinstance(row, dict) else row for row in candidate["relics"]
    }
    unknown_relics = relic_names - set(supported["relics"])
    if unknown_relics:
        blockers.append("UNSUPPORTED_RELIC:" + ",".join(sorted(unknown_relics)))
    unknown_potions = {potion for potion in candidate["potions"] if potion is not None} - set(supported["potions"])
    if unknown_potions:
        blockers.append("UNSUPPORTED_OR_CHOICE_POTION:" + ",".join(sorted(unknown_potions)))
    if candidate["encounter"] not in supported["encounters"]:
        blockers.append("UNKNOWN_OR_UNSUPPORTED_ENCOUNTER:" + candidate["encounter"])
    if (
        candidate["encounter"] in ELITE_ENCOUNTERS
        and ("burning_elite" not in candidate or not isinstance(candidate["burning_elite"], bool))
    ):
        blockers.append("ELITE_BURNING_STATE_UNPROVEN:" + candidate["encounter"])
    return sorted(set(blockers))


def metric_entry(run: dict[str, Any], state: dict[str, Any], floor: int) -> tuple[int, int, int, str]:
    if floor == 1:
        return state["hp"], state["max_hp"], state["gold"], "standard_start_plus_neow_log"
    try:
        hp, max_hp, gold = [
            numeric(run[key][floor - 2], f"{key}[{floor - 2}]")
            for key in ("current_hp_per_floor", "max_hp_per_floor", "gold_per_floor")
        ]
    except (KeyError, IndexError, TypeError) as exc:
        raise PrefixExpansionError("PREVIOUS_FLOOR_METRIC_MISSING_OR_INVALID") from exc
    if not 0 < hp <= max_hp or gold < 0:
        raise PrefixExpansionError("PREVIOUS_FLOOR_METRIC_MISSING_OR_INVALID")
    return hp, max_hp, gold, f"current_hp_per_floor[{floor - 2}] before destination onEnterRoom"


def make_candidate(
    run: dict[str, Any], state: dict[str, Any], floor: int, combat: dict[str, Any], has_prefix: bool,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = contract or load_contract()
    supported = contract_sets(contract)
    hp, max_hp, gold, hp_source = metric_entry(run, state, floor)
    encounter_label = combat.get("enemies")
    encounter = {**AUDIT.ENCOUNTERS, **ACT12_ENCOUNTERS}.get(encounter_label)
    if encounter is None:
        raise PrefixExpansionError("ENCOUNTER_GENERATOR_PENDING:" + str(encounter_label))
    if encounter not in supported["encounters"]:
        raise PrefixExpansionError("ENCOUNTER_NOT_IN_CONTRACT:" + encounter)
    padding = state["capacity"] - state["potions"].total()
    if padding < 0:
        raise PrefixExpansionError("POTION_CAPACITY_UNRESOLVED")
    prefix_suffix = "+resolved_event_or_shop_logs" if has_prefix else ""
    relics, relic_evidence, relic_blockers = derive_relic_entry_state(run, state, floor)
    candidate = {
        "entry_timing": "pre_combat_initialization",
        "initialization_phase": "before_destination_room_entry",
        "floor": floor, "act": 1 if floor <= 17 else 2, "character": "IRONCLAD", "ascension": state["ascension"],
        "player": {"hp": hp, "max_hp": max_hp, "gold": gold},
        "deck": sorted(state["deck"].elements()),
        "relics": relics,
        "relic_state_evidence": relic_evidence,
        "relic_state_blockers": relic_blockers,
        "potions": sorted(state["potions"].elements()) + [None] * padding,
        "potion_slot_policy": "canonical-inventory-slots-v1;not-original-slots",
        "encounter": encounter, "environment_replay_seed": None,
        "hp_source": hp_source,
        "field_evidence": {
            "deck": "M2C-02;starter+neow_bonus_log+floor0_choice+prior_card_choices+prior_smith" + prefix_suffix,
            "hp_gold": "M2C-03;Neow推导或前层边界指标；不读取本场战后指标",
            "relics": "current-relic-registry-v1;identity-only or uniquely derived counter;unresolved state rejects" + prefix_suffix,
            "potions": "M2C-05;prior_obtained-use-discard;canonical_inventory_slots" + prefix_suffix,
            "enemy_and_piles": "M2C-06;resampled_by_backend_not_historical_replay",
        },
        "initialize_once": [
            "room_entry_hooks", "monster_generation", "battle_start_hooks", "draw", "energy", "queues",
        ],
        "resampling_policy": "public-battle-a-resample-v1", "exact_historical_replay": False,
    }
    elite_evidence = elite_entry_evidence(run, combat, encounter)
    if elite_evidence["required"]:
        candidate["burning_elite"] = elite_evidence["burning_elite"]
    return candidate


def _combat_rows(run: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    combats: dict[int, list[dict[str, Any]]] = defaultdict(list)
    rows = run.get("damage_taken")
    if not isinstance(rows, list):
        return combats
    for row in rows:
        if not isinstance(row, dict):
            continue
        floor = _safe_floor(row.get("floor"))
        if floor is not None and 1 <= floor <= 34:
            combats[floor].append(row)
    return combats


def _initial_error(group: dict[str, Any], run: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    try:
        state = AUDIT.initial_state(run)
    except (ValueError, KeyError, TypeError) as exc:
        return None, "PREFIX_UNPROVEN:" + str(exc)
    if group.get("conflicting_variants"):
        return None, "CONFLICTING_SOURCE_VARIANTS"
    if group.get("card_modifier_group_rejected"):
        return None, "SOURCE_CARD_MODIFIERS_UNRESOLVED"
    return state, None


def expand_group(
    group: dict[str, Any], known: dict[str, set[str]], failure_counts: Counter[str], failure_groups: defaultdict[str, set[str]],
    contract: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    contract = contract or load_contract()
    run = group["run"]
    combats = _combat_rows(run)
    if not combats:
        return [], {}, []
    state, history_error = _initial_error(group, run)
    path = run.get("path_per_floor", [])
    has_prefix = False
    history: list[dict[str, Any]] = []
    scene_rows: list[dict[str, Any]] = []
    all_status: dict[str, dict[str, Any]] = {}
    for floor in range(1, max(combats, default=0) + 1):
        for index, combat in enumerate(combats[floor]):
            scene_id = f"{group['group_id']}:floor-{floor}:combat-{index}"
            target_blockers: list[str] = []
            candidate: dict[str, Any] | None = None
            elite_evidence = {
                "required": False, "status": "not_required", "burning_elite": None, "source_field": None,
            }
            if history_error:
                target_blockers.append(history_error)
            if len(combats[floor]) != 1 or not isinstance(path, list) or len(path) < floor or path[floor - 1] not in {"M", "E", "B"}:
                target_blockers.append("ENTRY_ROOM_OR_MULTIPLE_COMBATS_PENDING")
            if state is None:
                target_blockers.append("PLAYER_ENTRY_UNPROVEN_OR_SOURCE_REJECTED")
            elif not target_blockers:
                try:
                    candidate = make_candidate(run, state, floor, combat, has_prefix, contract)
                    elite_evidence = elite_entry_evidence(run, combat, candidate["encounter"])
                except PrefixExpansionError as exc:
                    target_blockers.append(str(exc))
            state_evidence_blockers = (
                state_blockers_with_relics(state, known, candidate.get("relic_state_evidence"))
                + list(candidate.get("relic_state_blockers", []))
                if candidate is not None and state is not None else []
            )
            entry_evidence_blockers = []
            if elite_evidence["status"] == "missing":
                candidate["burning_elite"] = False
                candidate["burning_elite_origin"] = "configured"
                candidate.setdefault("configurable_fields", []).append("burning_elite")
            elif elite_evidence["status"] == "invalid":
                candidate["burning_elite"] = False
                candidate["burning_elite_origin"] = "configured"
                candidate.setdefault("configurable_fields", []).append("burning_elite")
            evidence_blockers = sorted(set(target_blockers + state_evidence_blockers + entry_evidence_blockers))
            content_blockers = backend_blockers(candidate, contract) if candidate is not None else []
            raw_candidate = candidate is not None and not history_error and not target_blockers
            evidence_complete = raw_candidate and not state_evidence_blockers and not entry_evidence_blockers
            backend_ready = evidence_complete and not content_blockers
            row = {
                "scene_id": scene_id, "group_id": group["group_id"], "research_split": group["research_split"],
                "source_path": group["source_path"], "raw_sha256": group["raw_sha256"],
                "source_build": run.get("build_version"), "source_seed": run.get("seed_played"),
                "floor": floor, "encounter_label": combat.get("enemies"),
                "prefix_touched": has_prefix,
                "prefix_types": sorted({step["room_kind"] for step in history if step["room_kind"] in {"event", "shop"}}),
                "candidate": candidate,
                "evidence_blockers": evidence_blockers,
                "state_evidence_blockers": state_evidence_blockers,
                "entry_evidence_blockers": entry_evidence_blockers,
                "elite_entry_evidence": elite_evidence,
                "backend_blockers": sorted(set(content_blockers + entry_evidence_blockers)),
                "raw_research_candidate": raw_candidate,
                "evidence_complete": evidence_complete,
                "backend_admissible": backend_ready,
                "prefix_evidence_chain": copy.deepcopy(history),
                "card_modifier_evidence": source_card_modifiers(run),
                "historical_rules_equivalence": "unverified",
                "formal_eligibility": "audit-only",
            }
            all_status[scene_id] = row
            if has_prefix:
                scene_rows.append(row)
        if floor >= max(combats, default=0) or history_error:
            continue
        kind = path[floor - 1] if isinstance(path, list) and len(path) >= floor else None
        if kind in ROOM_KIND:
            has_prefix = True
            raw_evidence = room_evidence(run, floor, kind)
        else:
            raw_evidence = {"room_kind": kind, "floor": floor}
        if state is None:
            if kind in ROOM_KIND and history_error is None:
                history_error = "PLAYER_ENTRY_UNPROVEN_OR_SOURCE_REJECTED"
                history.append({**raw_evidence, "status": "blocked", "error": history_error})
                failure_counts[history_error] += 1
                failure_groups[history_error].add(group["group_id"])
            continue
        try:
            if kind == "?":
                step = validate_event_and_apply(run, state, floor)
            elif kind == "$":
                step = validate_shop_and_apply(run, state, floor, known)
            elif kind in {"M", "E", "R", "T", "B"}:
                AUDIT.advance_floor(run, state, floor)
                step = compact_standard_step(run, floor, kind)
            elif kind is None:
                # The run-history array reserves the floor immediately after
                # an Act boss for the inter-act transition. It has no room
                # effects; the boss transition was applied at the preceding B.
                step = {"room_kind": "inter_act_boundary", "floor": floor, "status": "applied"}
            else:
                raise PrefixExpansionError("ROOM_HISTORY_PENDING:" + str(kind))
            history.append(step)
        except (PrefixExpansionError, ValueError, KeyError, TypeError) as exc:
            history_error = str(exc)
            failure_counts[history_error] += 1
            failure_groups[history_error].add(group["group_id"])
            history.append({**raw_evidence, "status": "blocked", "error": history_error})
    return scene_rows, all_status, history


def original_blocker_analysis(index: dict[str, Any], groups: list[dict[str, Any]]) -> dict[str, Any]:
    scenes = index.get("scenes", [])
    counts = Counter(blocker for scene in scenes for blocker in scene.get("blockers", []))
    output: dict[str, Any] = {}
    for blocker, scene_count in counts.most_common():
        blocker_scenes = [scene for scene in scenes if blocker in scene.get("blockers", [])]
        by_group: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for scene in blocker_scenes:
            by_group[scene["group_id"]].append(scene)
        downstream = 0
        first_floor_by_group: dict[str, int] = {}
        for group_id, rows in by_group.items():
            first_scene_floor = min(int(row["floor"]) for row in rows)
            first_floor_by_group[group_id] = first_scene_floor
            downstream += sum(
                1 for scene in scenes
                if scene["group_id"] == group_id and int(scene["floor"]) >= first_scene_floor
            )
        output[blocker] = {
            "scene_count": scene_count,
            "independent_run_groups": len(by_group),
            "downstream_combat_rows_from_first_blocked_floor": downstream,
            "first_blocked_combat_floor_by_group": first_floor_by_group,
        }
    relevant_sets = {
        "event_prefix": {scene["group_id"] for scene in scenes if RELEVANT_OLD_BLOCKERS["event"] in scene.get("blockers", [])},
        "shop_prefix": {scene["group_id"] for scene in scenes if RELEVANT_OLD_BLOCKERS["shop"] in scene.get("blockers", [])},
        "dynamic_relic_prefix": {scene["group_id"] for scene in scenes if "PREFIX_UNPROVEN:RELIC_HISTORY_PENDING" in scene.get("blockers", [])},
        "potion_prefix": {scene["group_id"] for scene in scenes if "PREFIX_UNPROVEN:POTION_AUTO_USE_OR_GENERATION_PENDING" in scene.get("blockers", [])},
        "neow_prefix": {scene["group_id"] for scene in scenes if any("PREFIX_UNPROVEN:NEOW_EFFECT_PENDING" in blocker for blocker in scene.get("blockers", []))},
    }
    overlap: dict[str, dict[str, int]] = {}
    for left, left_set in relevant_sets.items():
        overlap[left] = {}
        for right, right_set in relevant_sets.items():
            overlap[left][right] = len(left_set & right_set)
    raw_presence = {
        "event_room": {
            group["group_id"] for group in groups
            if isinstance(group["run"].get("path_per_floor"), list)
            and "?" in group["run"]["path_per_floor"][:15]
        },
        "shop_room": {
            group["group_id"] for group in groups
            if isinstance(group["run"].get("path_per_floor"), list)
            and "$" in group["run"]["path_per_floor"][:15]
        },
    }
    room_observations = {}
    for symbol, label, log_key in (("?", "event", "event_choices"), ("$", "shop", "shop_contents")):
        rooms = []
        missing = duplicate = nonidentical = 0
        log_rows = 0
        for group in groups:
            run = group["run"]
            path = run.get("path_per_floor", [])
            for floor in range(1, min(15, len(path)) + 1):
                if path[floor - 1] != symbol:
                    continue
                rooms.append((group["group_id"], floor))
                matched = [
                    row for row in run.get(log_key, [])
                    if isinstance(row, dict) and _safe_floor(row.get("floor")) == floor
                ]
                log_rows += len(matched)
                if not matched:
                    missing += 1
                if len(matched) > 1:
                    unique = len(exact_deduplicate(matched)[0])
                    duplicate += 1
                    if unique > 1:
                        nonidentical += 1
        room_observations[label] = {
            "room_count": len(rooms), "independent_run_groups": len({group_id for group_id, _ in rooms}),
            "matching_log_rows": log_rows, "rooms_without_matching_log": missing,
            "rooms_with_duplicate_rows": duplicate, "rooms_with_nonidentical_duplicates": nonidentical,
        }
    event_shop_union = relevant_sets["event_prefix"] | relevant_sets["shop_prefix"]
    return {
        "original_index_blockers": output,
        "room_observations": room_observations,
        "observed_first_blocker_group_overlap_matrix": overlap,
        "raw_prefix_room_presence_overlap": {
            "event_groups": len(raw_presence["event_room"]),
            "shop_groups": len(raw_presence["shop_room"]),
            "both_event_and_shop_groups": len(raw_presence["event_room"] & raw_presence["shop_room"]),
        },
        "event_shop_blocker_union": {
            "independent_run_groups": len(event_shop_union),
            "event_groups": len(relevant_sets["event_prefix"]),
            "shop_groups": len(relevant_sets["shop_prefix"]),
        },
    }


def structural_event_reason(run: dict[str, Any], floor: int) -> str | None:
    """只检查事件摘要是否自洽；不读取牌组，因此可发现被前缀错误遮住的真实拒绝。"""
    rows = [
        row for row in run.get("event_choices", [])
        if isinstance(row, dict) and _safe_floor(row.get("floor")) == floor
    ]
    if not rows:
        return "EVENT_LOG_MISSING"
    rows, _ = exact_deduplicate(rows)
    if len(rows) != 1:
        return "EVENT_TIMING_AMBIGUOUS_NONIDENTICAL"
    row = rows[0]
    name, choice = row.get("event_name"), row.get("player_choice")
    if not isinstance(name, str) or not name or not isinstance(choice, str) or not choice:
        return "EVENT_ID_OR_CHOICE_MISSING"
    if any(
        isinstance(item, dict) and _safe_floor(item.get("floor")) == floor
        for item in run.get("card_choices", [])
    ):
        return "EVENT_CARD_REWARD_SAME_FLOOR_ORDER_UNRESOLVED"
    try:
        validate_event_effect_fields(row, (name, choice))
    except PrefixExpansionError as exc:
        return str(exc)
    return None


def structural_shop_reason(run: dict[str, Any], floor: int, known: dict[str, set[str]]) -> str | None:
    shops = [
        row for row in run.get("shop_contents", [])
        if isinstance(row, dict) and _safe_floor(row.get("floor")) == floor
    ]
    if len(shops) != 1:
        return "SHOP_LOG_MISSING_OR_DUPLICATE"
    for key in ("cards", "relics", "potions"):
        value = shops[0].get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            return "SHOP_CONTENTS_INVALID:" + key
    try:
        purchases = _require_transactions(run, "item_purchase_floors", "items_purchased", "SHOP_PURCHASE")
        purges = _require_transactions(run, "items_purged_floors", "items_purged", "SHOP_PURGE")
        if numeric(run.get("purchased_purges"), "SHOP_PURGE_COUNT") != len(purges):
            return "SHOP_PURGE_COUNT_CONTRADICTION"
    except PrefixExpansionError as exc:
        return str(exc)
    current_purchases = [(f, item) for f, item in purchases if f == floor]
    current_purges = [(f, item) for f, item in purges if f == floor]
    for _, item in current_purchases:
        if item in SHOP_SECONDARY_SELECTIONS:
            return SHOP_SECONDARY_SELECTIONS[item]
        if item_kind(item, known) is None:
            return "SHOP_ITEM_UNKNOWN:" + item
    for _, item in current_purges:
        if item_kind(item, known) != "card":
            return "SHOP_PURGE_NOT_CARD:" + item
    choices = [
        row for row in run.get("card_choices", [])
        if isinstance(row, dict) and _safe_floor(row.get("floor")) == floor
    ]
    orrery_count = sum(item == "Orrery" for _, item in current_purchases)
    if choices and not orrery_count:
        return "SHOP_CARD_REWARD_ORDER_UNRESOLVED"
    if orrery_count > 1:
        return "SHOP_DUPLICATE_SPECIAL_SERVICE"
    unique_choices, _ = exact_deduplicate(choices)
    if orrery_count and len(unique_choices) != 5:
        return "SHOP_ORRERY_CARD_REWARDS_MISSING_OR_AMBIGUOUS"
    for row in unique_choices:
        picked = row.get("picked")
        if not isinstance(picked, str) or not picked:
            return "SHOP_CARD_CHOICE_INVALID"
        if picked == "Singing Bowl":
            return "SHOP_UNREGISTERED_SINGING_BOWL"
    return None


def prefix_gate_analysis(groups: list[dict[str, Any]], known: dict[str, set[str]]) -> dict[str, Any]:
    """对所有第一幕事件/商店房做结构闸门审计，避免被更早动态遗物遮住。"""
    result: dict[str, Any] = {}
    for symbol, label in (("?", "event"), ("$", "shop")):
        counts: Counter[str] = Counter()
        group_sets: defaultdict[str, set[str]] = defaultdict(set)
        examples: dict[str, dict[str, Any]] = {}
        total = 0
        for group in groups:
            path = group["run"].get("path_per_floor", [])
            if not isinstance(path, list):
                continue
            for floor in range(1, min(15, len(path)) + 1):
                if path[floor - 1] != symbol:
                    continue
                total += 1
                reason = structural_event_reason(group["run"], floor) if symbol == "?" else structural_shop_reason(group["run"], floor, known)
                reason = reason or "STRUCTURALLY_RESOLVED"
                counts[reason] += 1
                group_sets[reason].add(group["group_id"])
                examples.setdefault(reason, {
                    "source_path": group["source_path"], "group_id": group["group_id"], "floor": floor,
                    "raw_room_evidence": room_evidence(group["run"], floor, symbol),
                })
        result[label] = {
            "room_count": total,
            "outcome_counts": dict(counts.most_common()),
            "outcome_group_counts": {reason: len(group_sets[reason]) for reason in counts},
            "structurally_resolved_room_count": counts.get("STRUCTURALLY_RESOLVED", 0),
            "examples": examples,
        }
    return result


def _tier_rows(rows: list[dict[str, Any]], tier: str) -> list[dict[str, Any]]:
    if tier == "raw_research":
        return [row for row in rows if row["raw_research_candidate"]]
    if tier == "evidence_complete":
        return [row for row in rows if row["evidence_complete"]]
    if tier == "backend_admissible":
        return [row for row in rows if row["backend_admissible"]]
    raise ValueError(tier)


def coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [row for row in rows if row.get("candidate") is not None]
    decks = {tuple(row["candidate"]["deck"]) for row in candidates}
    relic_potions = {
        (tuple(row["candidate"]["relics"]), tuple(row["candidate"]["potions"]))
        for row in candidates
    }
    return {
        "scene_count": len(candidates),
        "independent_run_groups": len({row["group_id"] for row in candidates}),
        "floors": sorted({row["floor"] for row in candidates}),
        "encounters": dict(Counter(row["encounter_label"] for row in candidates).most_common()),
        "card_classes": sorted({AUDIT.card_base(card) for row in candidates for card in row["candidate"]["deck"]}),
        "card_multisets": len(decks),
        "relic_potion_combinations": len(relic_potions),
        "relics": dict(Counter(relic for row in candidates for relic in row["candidate"]["relics"]).most_common()),
        "potions": dict(Counter(
            potion for row in candidates for potion in row["candidate"]["potions"] if potion is not None
        ).most_common()),
        "by_research_split": dict(Counter(row["research_split"] for row in candidates)),
    }


def tier_delta(
    original: list[dict[str, Any]], new_rows: list[dict[str, Any]], tier: str
) -> dict[str, Any]:
    old = coverage(original)
    new = coverage(new_rows)
    old_ids = {row["scene_id"] for row in original}
    new_ids = {row["scene_id"] for row in new_rows}
    old_groups = {row["group_id"] for row in original}
    new_groups = {row["group_id"] for row in new_rows}
    old_decks = {tuple(row["candidate"]["deck"]) for row in original}
    new_decks = {tuple(row["candidate"]["deck"]) for row in new_rows}
    old_relic_potions = {
        (tuple(row["candidate"]["relics"]), tuple(row["candidate"]["potions"]))
        for row in original
    }
    new_relic_potions = {
        (tuple(row["candidate"]["relics"]), tuple(row["candidate"]["potions"]))
        for row in new_rows
    }
    return {
        "tier": tier,
        "baseline_99": old,
        "new_prefix_rows": new,
        "net_new_scene_count": len(new_ids - old_ids),
        "net_new_independent_run_groups": len(new_groups - old_groups),
        "union_scene_count": len(old_ids | new_ids),
        "union_independent_run_groups": len(old_groups | new_groups),
        "new_floors_not_in_baseline": sorted(set(new["floors"]) - set(old["floors"])),
        "new_encounters_not_in_baseline": sorted(set(new["encounters"]) - set(old["encounters"])),
        "new_unique_card_multisets": len(new_decks - old_decks),
        "union_card_multisets": len(old_decks | new_decks),
        "new_unique_relic_potion_combinations": len(new_relic_potions - old_relic_potions),
        "union_relic_potion_combinations": len(old_relic_potions | new_relic_potions),
    }


def prefix_ranking(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranking = []
    for kind in ("event", "shop"):
        raw = [row for row in rows if row["raw_research_candidate"] and kind in row["prefix_types"]]
        selected = [row for row in raw if row["evidence_complete"]]
        backend = [row for row in selected if row["backend_admissible"]]
        ranking.append({
            "prefix_type": kind,
            "raw_research_scenes": len(raw),
            "raw_research_run_groups": len({row["group_id"] for row in raw}),
            "evidence_complete_scenes": len(selected),
            "evidence_complete_run_groups": len({row["group_id"] for row in selected}),
            "backend_admissible_scenes": len(backend),
            "backend_admissible_run_groups": len({row["group_id"] for row in backend}),
            "floors": sorted({row["floor"] for row in selected}),
            "card_multisets": len({tuple(row["candidate"]["deck"]) for row in selected}),
            "unique_card_classes": sorted({
                AUDIT.card_base(card) for row in selected for card in row["candidate"]["deck"]
            }),
            "relic_potion_combinations": len({
                (tuple(row["candidate"]["relics"]), tuple(row["candidate"]["potions"]))
                for row in selected
            }),
            "encounters": sorted({row["encounter_label"] for row in selected}),
        })
    return sorted(ranking, key=lambda row: (
        -row["evidence_complete_scenes"], -row["evidence_complete_run_groups"], row["prefix_type"]
    ))


def special_card_tracking(
    groups: list[dict[str, Any]], all_status: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    tracked = ["Dropkick", "Entrench", "Rage", "Sentinel", "Thunderclap", "True Grit"]
    output: dict[str, Any] = {}
    for card in tracked:
        picks: list[dict[str, Any]] = []
        later_battles = 0
        complete_battles = 0
        backend_battles = 0
        present_battles = 0
        failure_reasons: Counter[str] = Counter()
        for group in groups:
            run = group["run"]
            choice_rows = [
                row for row in run.get("card_choices", [])
                if isinstance(row, dict) and _safe_floor(row.get("floor")) is not None
                and 1 <= _safe_floor(row.get("floor")) <= 15
                and isinstance(row.get("picked"), str)
                and AUDIT.card_base(row["picked"]) == card
            ]
            choice_rows, _ = exact_deduplicate(choice_rows)
            for choice in choice_rows:
                pick_floor = numeric(choice.get("floor"), "CARD_PICK_FLOOR")
                picks.append({
                    "group_id": group["group_id"], "source_path": group["source_path"],
                    "floor": pick_floor, "picked": choice.get("picked"),
                })
                for battle_floor, battles in _combat_rows(run).items():
                    if battle_floor <= pick_floor:
                        continue
                    for index, _ in enumerate(battles):
                        later_battles += 1
                        scene_id = f"{group['group_id']}:floor-{battle_floor}:combat-{index}"
                        row = all_status.get(scene_id)
                        if row is None or not row["evidence_complete"]:
                            for reason in (row or {}).get("evidence_blockers", ["SCENE_STATUS_MISSING"]):
                                failure_reasons[reason] += 1
                            continue
                        complete_battles += 1
                        if row["backend_admissible"]:
                            backend_battles += 1
                        if row["candidate"] and card in {AUDIT.card_base(item) for item in row["candidate"]["deck"]}:
                            present_battles += 1
        output[card] = {
            "pick_records": picks,
            "runs_with_act1_pick": len({item["group_id"] for item in picks}),
            "later_battles_after_pick": later_battles,
            "later_battles_with_evidence_complete_state": complete_battles,
            "later_battles_backend_admissible": backend_battles,
            "later_battles_card_still_present": present_battles,
            "failure_reasons": dict(failure_reasons.most_common()),
        }
    return output


def compare_original_manifest(
    original_manifest: dict[str, Any], all_status: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    original = [
        row for row in original_manifest.get("scenes", [])
        if row.get("content_admission_status") == "accepted" and row.get("candidate") is not None
    ]
    mismatches = []
    missing = []
    for row in original:
        current = all_status.get(row["scene_id"])
        if current is None:
            missing.append(row["scene_id"])
        elif current.get("candidate") != row.get("candidate"):
            mismatches.append({
                "scene_id": row["scene_id"], "original_candidate": row.get("candidate"),
                "expanded_candidate": current.get("candidate"),
            })
    return {
        "original_manifest_accepted_scenes": len(original),
        "matched_and_equal": len(original) - len(missing) - len(mismatches),
        "missing_scene_ids": missing,
        "candidate_mismatches": mismatches,
        "passed": not missing and not mismatches,
    }


def _short_example(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene_id": row["scene_id"], "source_path": row["source_path"], "group_id": row["group_id"],
        "floor": row["floor"], "encounter_label": row["encounter_label"],
        "prefix_types": row["prefix_types"], "evidence_blockers": row["evidence_blockers"],
        "backend_blockers": row["backend_blockers"],
    }


def run_runtime_probe(
    result: dict[str, Any], candidate_file_sha256: str, output_path: Path
) -> dict[str, Any]:
    """只对最终静态可接入候选做开发探针，任何失败逐条保留。"""
    candidates = [row for row in result["scenes"] if row["backend_admissible"]]
    records: list[dict[str, Any]] = []
    try:
        from sts.agents.public_runner import PublicRandomAgent, run_public_episode
        from sts.agents.rule_agent import RuleAgent
        from sts.env.public_battle import PublicBattleEnv
    except (ImportError, ModuleNotFoundError, RuntimeError, OSError) as exc:  # pragma: no cover
        setup_error = f"{type(exc).__name__}: {exc}"
        for index, row in enumerate(candidates):
            for policy in ("random", "rule"):
                records.append({
                    "scene_id": row["scene_id"], "policy": policy, "candidate_index": index,
                    "environment_seed": 930000 + index,
                    "agent_seed": 1930000 + index if policy == "random" else None,
                    "status": "probe_setup_error", "error": setup_error,
                })
    else:
        for index, row in enumerate(candidates):
            for policy in ("random", "rule"):
                environment_seed = 930000 + index
                agent_seed = 1930000 + index if policy == "random" else None
                record = {
                    "scene_id": row["scene_id"], "policy": policy, "candidate_index": index,
                    "environment_seed": environment_seed, "agent_seed": agent_seed,
                }
                try:
                    env = PublicBattleEnv()
                    observation = env.reset(row["candidate"], environment_seed, diagnostic=True)
                    agent = RuleAgent() if policy == "rule" else PublicRandomAgent(agent_seed)
                    trace = run_public_episode(env, agent, observation)
                    record.update({
                        "status": "completed", "terminated": trace["terminated"],
                        "truncated": trace["truncated"], "steps": trace["steps"],
                    })
                except (AssertionError, KeyError, IndexError, OSError, RuntimeError, TypeError, ValueError) as exc:
                    record.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
                records.append(record)
    status_counts = Counter(record["status"] for record in records)
    output = {
        "schema": "public-prefix-runtime-probe-v1",
        "purpose": "review-runtime-probe-not-source-admission",
        "candidate_file_sha256": candidate_file_sha256,
        "script_sha256": sha(Path(__file__).read_bytes()),
        "contract_sha256": sha(CONTRACT_PATH.read_bytes()),
        "reproduction_commands": REPRODUCTION_COMMANDS,
        "seed_policy": {
            "environment_seed_start": 930000, "random_agent_seed_start": 1930000,
            "all_seeds_at_least_100000": True, "eval_seeds_used": False,
        },
        "candidate_count": len(candidates),
        "records": records,
        "summary": {
            "record_count": len(records), "status_counts": dict(status_counts),
            "policy_counts": dict(Counter(record["policy"] for record in records)),
            "failure_records_preserved": sum(
                count for status, count in status_counts.items() if status != "completed"
            ),
        },
    }
    write_json(output_path, output)
    return output


def build_result(
    index: dict[str, Any], manifest: dict[str, Any], corpus_bytes: bytes, archive_bytes: bytes
) -> dict[str, Any]:
    if sha(corpus_bytes) != index.get("corpus_sha256"):
        raise ValueError("CORPUS_FILE_HASH_MISMATCH")
    corpus = json.loads(corpus_bytes)
    if {key: value for key, value in index.items() if key != "corpus_sha256"} != corpus:
        raise ValueError("INDEX_CORPUS_CONTENT_MISMATCH")
    if sha(archive_bytes) != AUDIT.ZIP_SHA:
        raise ValueError("SOURCE_ARCHIVE_HASH_MISMATCH")
    contract = load_contract()
    contract_support = contract_sets(contract)
    records = AUDIT.load_records(archive_bytes)
    groups = AUDIT.group_records(records)
    known = AUDIT.catalog()
    failure_counts: Counter[str] = Counter()
    failure_groups: defaultdict[str, set[str]] = defaultdict(set)
    expansion_scenes: list[dict[str, Any]] = []
    all_status: dict[str, dict[str, Any]] = {}
    for group in groups:
        rows, status, _ = expand_group(group, known, failure_counts, failure_groups, contract)
        expansion_scenes.extend(rows)
        all_status.update(status)
    original = [
        row for row in manifest.get("scenes", [])
        if row.get("content_admission_status") == "accepted" and row.get("candidate") is not None
    ]
    tiers = {
        tier: _tier_rows(expansion_scenes, tier)
        for tier in ("raw_research", "evidence_complete", "backend_admissible")
    }
    original_blockers = original_blocker_analysis(index, groups)
    prefix_gates = prefix_gate_analysis(groups, known)
    source_files = [
        {
            "path": "reference/public-run-corpus/recorder-source/src/main/java/runhistoryplus/patches/ShopContentsRunHistoryPatch.java",
            "claim": "商店内容在nextRoomTransition读取；不等于购买前库存",
            "line_refs": "135-147",
        },
        {
            "path": "reference/public-run-corpus/recorder-source/src/main/java/runhistoryplus/patches/MultipleCardRewardsRunHistoryPatch.java",
            "claim": "同楼层卡牌选择按floor/picked/not_picked去重的来源实现",
            "line_refs": "38-62",
        },
        {
            "path": "reference/public-run-corpus/recorder-source/src/main/java/runhistoryplus/patches/PotionRunHistoryPatch.java",
            "claim": "药水获得/使用/丢弃日志入口",
            "line_refs": "94-128,227-231",
        },
        {
            "path": "reference/public-run-corpus/recorder-source/src/main/java/runhistoryplus/subscribers/PotionUseAddLoggingSubscriber.java",
            "claim": "使用记录发生在post potion use且不保存原槽位",
            "line_refs": "10-19",
        },
        {
            "path": "reference/public-run-corpus/recorder-source/src/main/java/runhistoryplus/patches/NeowBonusRunHistoryPatch.java",
            "claim": "Neow增删/变形/升级/数值记录入口",
            "line_refs": "185-311",
        },
    ]
    source_evidence = {
        "fixed_archives": [
            {"path": "reference/public-run-corpus/matiger-fixed.zip", "sha256": AUDIT.ZIP_SHA, "bytes": len(archive_bytes), "commit": AUDIT.COMMIT},
            {"path": "reference/public-run-corpus/run-history-plus-2022.zip", "sha256": "4272eb2dec27d613f356bfa0f2df21358cef9a00a5fda54de3db76a177425cf3", "commit": "99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b"},
            {"path": "reference/public-run-corpus/run-history-plus.zip", "sha256": "c0636b186b2930308a0f288b77bc4af94d50f5b296e7a6b0d2cd02647f283269", "commit": "8d482facdcebf8a018743ac27005c21b52165863"},
        ],
        "input_files": [
            {"path": "docs/m2-corpus-index.json", "sha256": sha((INDEX_PATH).read_bytes())},
            {"path": "docs/m2-public-scene-manifest.json", "sha256": sha(MANIFEST_PATH.read_bytes())},
            {"path": "reference/public-run-corpus/corpus.json", "sha256": sha(corpus_bytes)},
            {"path": "scripts/audit-public-corpus.py", "sha256": sha(AUDIT_PATH.read_bytes())},
            {"path": "sts/env/public-battle-contract.json", "sha256": sha(CONTRACT_PATH.read_bytes())},
        ],
        "recorder_source_files": [
            {
                "path": source["path"], "sha256": sha((ROOT / source["path"]).read_bytes()),
                "claim": source["claim"], "line_refs": source["line_refs"],
            }
            for source in source_files
        ],
        "existing_evidence_ids": {
            "M2C-02": "docs/m2-corpus-report.md；Neow字段及升级前metricID",
            "M2C-03": "docs/m2-corpus-report.md；前层边界HP/maxHP/gold时点",
            "M2C-04": "docs/m2-corpus-report.md；仅已核查无动态计数遗物",
            "M2C-05": "docs/m2-corpus-report.md；药水使用/丢弃/生成时序边界",
            "M2C-06": "docs/m2-corpus-report.md；遭遇由后端标准规则重新生成",
        },
    }
    examples = {
        "successful_evidence_examples": [_short_example(row) for row in tiers["evidence_complete"][:5]],
        "successful_backend_examples": [_short_example(row) for row in tiers["backend_admissible"][:5]],
        "rejection_examples": {},
        "structural_prefix_rejection_examples": {},
    }
    for reason in (
        "EVENT_CARD_REWARD_SAME_FLOOR_ORDER_UNRESOLVED",
        "EVENT_POTION_ID_MISSING",
        "SHOP_CARD_SELECTION_MISSING",
        "SHOP_RANDOM_UPGRADE_TARGET_MISSING",
        "RELIC_HISTORY_PENDING",
        "POTION_AUTO_USE_OR_GENERATION_PENDING",
    ):
        matched = [
            row for row in expansion_scenes
            if any(reason in blocker for blocker in row["evidence_blockers"])
        ]
        if matched:
            examples["rejection_examples"][reason] = _short_example(matched[0])
    for prefix_type in ("event", "shop"):
        for reason, example in prefix_gates[prefix_type]["examples"].items():
            if reason != "STRUCTURALLY_RESOLVED":
                examples["structural_prefix_rejection_examples"][reason] = example

    result = {
        "schema": "public-prefix-expansion-v1",
        "source_admission_policy": AUDIT.SOURCE_ADMISSION_POLICY,
        "entry_timing": "pre_combat_initialization / before_destination_room_entry",
        "input_index_sha256": sha(INDEX_PATH.read_bytes()),
        "input_manifest_sha256": sha(MANIFEST_PATH.read_bytes()),
        "contract_sha256": sha(CONTRACT_PATH.read_bytes()),
        "contract_id": contract["contract_id"],
        "source_archive_sha256": sha(archive_bytes),
        "script_sha256": sha(Path(__file__).read_bytes()),
        "reproduction_commands": REPRODUCTION_COMMANDS,
        "master_deck_used": False,
        "runtime_probe": {
            "artifact": "reference/public-prefix-expansion/runtime-probe.json",
            "purpose": "final-static-candidates-random-and-rule-development-check",
            "not_formal_evaluation": True,
        },
        "source_evidence": source_evidence,
        "reconstruction_policy": {
            "do_not_delete_or_replace_source_content": True,
            "event_outcome_allowlist": sorted(f"{name}/{choice}" for name, choice in SAFE_EVENT_OUTCOMES),
            "event_exact_duplicate_policy": "only byte-equivalent JSON objects deduplicated; nonidentical rows rejected",
            "shop_transaction_policy": "items_purchased/item_purchase_floors and items_purged/items_purged_floors must align",
            "shop_contents_policy": "remaining contents evidence only; never used as purchase history",
            "shop_secondary_selection_policy": "missing target card/upgrade rejects the prefix",
            "potion_policy": "canonical inventory slots; no original slot claim; same-floor purchase/use rejected",
            "backend_support_source": "sts/env/public-battle-contract.json;cards/relics/potions/encounters and max_upgrade read at runtime",
            "contract_support_counts": {
                "cards": len(contract_support["card_max_upgrade"]),
                "relics": len(contract_support["relics"]),
                "potions": len(contract_support["potions"]),
                "encounters": len(contract_support["encounters"]),
            },
            "historical_rules_equivalence": "unverified",
        },
        "original_blocker_analysis": original_blockers,
        "prefix_gate_analysis": prefix_gates,
        "prefix_ranking": prefix_ranking(expansion_scenes),
        "summary": {
            "source_raw_ironclad_files": len(records),
            "source_independent_run_groups": len(groups),
            "original_manifest_scene_count": len(original),
            "raw_located_prefix_target_rows": len(expansion_scenes),
            "raw_research_candidate_count": len(tiers["raw_research"]),
            "raw_research_candidate_run_groups": len({row["group_id"] for row in tiers["raw_research"]}),
            "evidence_complete_candidate_count": len(tiers["evidence_complete"]),
            "evidence_complete_candidate_run_groups": len({row["group_id"] for row in tiers["evidence_complete"]}),
            "backend_admissible_candidate_count": len(tiers["backend_admissible"]),
            "backend_admissible_candidate_run_groups": len({row["group_id"] for row in tiers["backend_admissible"]}),
            "prefix_target_run_groups": len({row["group_id"] for row in expansion_scenes}),
            "failure_counts": dict(failure_counts.most_common()),
            "failure_group_counts": {reason: len(failure_groups[reason]) for reason in failure_counts},
            "tiers": {tier: coverage(rows) for tier, rows in tiers.items()},
        },
        "net_new_vs_original_99": {
            tier: tier_delta(original, rows, tier)
            for tier, rows in tiers.items()
        },
        "original_manifest_consistency": compare_original_manifest(manifest, all_status),
        "special_card_tracking": special_card_tracking(groups, all_status),
        "examples": examples,
        "scenes": expansion_scenes,
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=INDEX_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    parser.add_argument("--archive", type=Path, default=ARCHIVE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--evidence-dir", type=Path, default=EVIDENCE_DIR)
    args = parser.parse_args(argv)
    index_bytes = args.index.read_bytes()
    result = build_result(
        json.loads(index_bytes), json.loads(args.manifest.read_bytes()),
        args.corpus.read_bytes(), args.archive.read_bytes(),
    )
    write_json(args.output, result)
    evidence_dir = args.evidence_dir
    candidate_file_sha256 = sha(args.output.read_bytes())
    runtime_probe = run_runtime_probe(
        result, candidate_file_sha256, evidence_dir / "runtime-probe.json"
    )
    write_json(evidence_dir / "source-evidence.json", result["source_evidence"])
    write_json(evidence_dir / "prefix-failure-summary.json", {
        "schema": "public-prefix-failure-summary-v1",
        "input_index_sha256": result["input_index_sha256"],
        "failure_counts": result["summary"]["failure_counts"],
        "failure_group_counts": result["summary"]["failure_group_counts"],
        "original_blocker_analysis": result["original_blocker_analysis"],
        "prefix_gate_analysis": result["prefix_gate_analysis"],
        "examples": result["examples"]["rejection_examples"],
        "structural_prefix_rejection_examples": result["examples"]["structural_prefix_rejection_examples"],
    })
    write_json(evidence_dir / "prefix-coverage-summary.json", {
        "schema": "public-prefix-coverage-summary-v1",
        "input_candidate_sha256": sha(args.output.read_bytes()),
        "summary": result["summary"],
        "prefix_gate_analysis": result["prefix_gate_analysis"],
        "prefix_ranking": result["prefix_ranking"],
        "net_new_vs_original_99": result["net_new_vs_original_99"],
        "special_card_tracking": result["special_card_tracking"],
        "original_manifest_consistency": result["original_manifest_consistency"],
        "runtime_probe": runtime_probe["summary"],
    })
    print(json.dumps({"summary": result["summary"], "runtime_probe": runtime_probe["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
