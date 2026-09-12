"""批量审计公开Ironclad第一幕初态；来源准入与规则重建分别记录。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import math
from pathlib import Path
import re
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "097aaf3564c2247835162d267cbc7c55d2c9039e"
ZIP_SHA = "0b21c5fe489ac0980131d0dd14350efdf1c68f180488b6d2072ae0e81cea565e"
SCHEMA = "public-corpus-audit-v2"
SOURCE_ADMISSION_POLICY = "public-derived-standard-v1"
SOURCE_URL = f"https://github.com/MaT1g3R/Slay-the-Spire-data/tree/{COMMIT}"
BASE = ["Strike_R"] * 5 + ["Defend_R"] * 4 + ["Bash"]
CHOICE_BONUSES = {"THREE_CARDS", "THREE_RARE_CARDS", "RANDOM_COLORLESS", "RANDOM_COLORLESS_2"}
BONUSES = CHOICE_BONUSES | {"HUNDRED_GOLD", "TWO_FIFTY_GOLD", "TEN_PERCENT_HP_BONUS", "TWENTY_PERCENT_HP_BONUS", "REMOVE_CARD", "REMOVE_TWO", "TRANSFORM_CARD", "TRANSFORM_TWO_CARDS", "UPGRADE_CARD", "ONE_RANDOM_RARE_CARD", "RANDOM_COMMON_RELIC", "ONE_RARE_RELIC"}
COSTS = {"NONE", "NO_GOLD", "PERCENT_DAMAGE", "TEN_PERCENT_HP_LOSS", "CURSE"}
# 仅列已核查不需要跨战斗计数/选牌绑定的开场遗物；不是行为白名单。
RESET_RELICS = {"Burning Blood", "Lantern", "Anchor", "Bag of Preparation", "Vajra", "Oddly Smooth Stone", "Blood Vial", "Bronze Scales"}
PERSISTENT_CARDS = {"RitualDagger", "Genetic Algorithm"}
M1_CARDS = set("Strike_R|Defend_R|Bash|Bludgeon|Cleave|Clothesline|Twin Strike|Thunderclap|Uppercut|Body Slam|Entrench|Heavy Blade|Spot Weakness|Inflame|Pommel Strike|Shrug It Off|Dropkick|Carnage|Ghostly Armor|Impervious|Pummel|Seeing Red|Sentinel|True Grit|Battle Trance|Flex|Metallicize|Demon Form|Rage|Flame Barrier|Feel No Pain|Wild Strike|Reckless Charge|Power Through|Immolate".split("|"))
ENCOUNTERS = {
    "Cultist": "CULTIST", "Jaw Worm": "JAW_WORM", "2 Louse": "TWO_LOUSE",
    "Small Slimes": "SMALL_SLIMES", "Blue Slaver": "BLUE_SLAVER", "Red Slaver": "RED_SLAVER",
    "Looter": "LOOTER", "Large Slime": "LARGE_SLIME", "3 Louse": "THREE_LOUSE",
    "2 Fungi Beasts": "TWO_FUNGI_BEASTS", "Exordium Wildlife": "EXORDIUM_WILDLIFE",
    "Exordium Thugs": "EXORDIUM_THUGS", "Gremlin Gang": "GREMLIN_GANG", "Lots of Slimes": "LOTS_OF_SLIMES",
    "Gremlin Nob": "GREMLIN_NOB", "Lagavulin": "LAGAVULIN", "3 Sentries": "THREE_SENTRIES",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def number(value):
    """summary允许整值浮点；拒绝bool、非有限数、字符串和小数截断。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or int(value) != value:
        raise ValueError("数字必须为有限整数")
    return int(value)


def strings(value):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError("缺少字符串数组")
    return value


def rows_at(run, key, floor):
    rows = run.get(key)
    if not isinstance(rows, list):
        raise ValueError(f"缺少{key}")
    selected = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{key}行格式错误")
        if number(row.get("floor")) == floor:
            selected.append(row)
    return selected


def card_base(card):
    if not isinstance(card, str):
        raise ValueError("卡牌ID不是字符串")
    match = re.fullmatch(r"(.+?)(?:\+([1-9][0-9]*))?", card)
    if not match or card.endswith("+"):
        raise ValueError("卡牌升级格式不完整")
    if match.group(2) and int(match.group(2)) > 1 and match.group(1) != "Searing Blow":
        raise ValueError("普通卡重复升级次数非法")
    return match.group(1)


def remove_card(deck, card):
    if deck[card] <= 0:
        raise ValueError(f"移除不存在的牌:{card}")
    deck[card] -= 1
    if not deck[card]:
        del deck[card]


def upgrade_card(deck, card):
    # 记录器在upgrade之前记录metricID；同名普通副本可按多重集替换。
    base = card_base(card)
    old = int(card.rsplit("+", 1)[1]) if re.search(r"\+[1-9][0-9]*$", card) else 0
    if old and base != "Searing Blow":
        raise ValueError("普通卡不能重复升级")
    remove_card(deck, card)
    deck[f"{base}+{old + 1}"] += 1


def initial_state(run):
    asc = number(run.get("ascension_level"))
    if not 0 <= asc <= 20 or run.get("character_chosen") != "IRONCLAD":
        raise ValueError("角色/进阶错误")
    if any(run.get(k) is not False for k in ("is_daily", "is_trial", "is_endless")):
        raise ValueError("标准模式未证明")
    if not isinstance(run.get("build_version"), str) or not run["build_version"]:
        raise ValueError("SOURCE_BUILD_MISSING")
    if not isinstance(run.get("seed_played"), (str, int)) or isinstance(run.get("seed_played"), bool) or not str(run["seed_played"]):
        raise ValueError("SOURCE_SEED_MISSING")
    if rows_at(run, "event_choices", 0) or rows_at(run, "campfire_choices", 0):
        raise ValueError("PRE_NEOW_HISTORY_AMBIGUOUS")
    bonus, cost = run.get("neow_bonus"), run.get("neow_cost")
    if bonus not in BONUSES or cost not in COSTS:
        raise ValueError("NEOW_EFFECT_PENDING:" + str(bonus) + "/" + str(cost))
    log = run.get("neow_bonus_log")
    if not isinstance(log, dict):
        raise ValueError("NEOW_LOG_MISSING")
    fields = {k: strings(log.get(k)) for k in ("cardsRemoved", "cardsTransformed", "cardsObtained", "cardsUpgraded", "relicsObtained")}
    values = {k: number(log.get(k)) for k in ("maxHpLost", "maxHpGained", "damageTaken", "goldLost", "goldGained")}
    if any(v < 0 for v in values.values()):
        raise ValueError("负Neow变化")
    expected_remove = {"REMOVE_CARD": 1, "REMOVE_TWO": 2}.get(bonus, 0)
    expected_transform = {"TRANSFORM_CARD": 1, "TRANSFORM_TWO_CARDS": 2}.get(bonus, 0)
    if len(fields["cardsRemoved"]) != expected_remove or len(fields["cardsTransformed"]) != expected_transform or len(fields["cardsUpgraded"]) != (1 if bonus == "UPGRADE_CARD" else 0):
        raise ValueError("NEOW_CARD_DELTA_CONTRADICTION")
    if len(fields["relicsObtained"]) != (1 if bonus in {"ONE_RARE_RELIC", "RANDOM_COMMON_RELIC"} else 0):
        raise ValueError("NEOW_RELIC_DELTA_CONTRADICTION")
    obtained_count = expected_transform + (1 if bonus == "ONE_RANDOM_RARE_CARD" else 0) + (1 if cost == "CURSE" else 0)
    if len(fields["cardsObtained"]) != obtained_count:
        raise ValueError("NEOW_OBTAIN_DELTA_CONTRADICTION")
    # 具体扣血/最大HP量使用来源实录；核对是否允许该类变化，避免漏日志冒充0。
    for key, enabled in {
        "maxHpLost": cost == "TEN_PERCENT_HP_LOSS", "damageTaken": cost == "PERCENT_DAMAGE",
        "maxHpGained": bonus in {"TEN_PERCENT_HP_BONUS", "TWENTY_PERCENT_HP_BONUS"},
        "goldLost": cost == "NO_GOLD", "goldGained": bonus in {"HUNDRED_GOLD", "TWO_FIFTY_GOLD"},
    }.items():
        if (values[key] > 0) != enabled:
            raise ValueError("NEOW_NUMERIC_DELTA_CONTRADICTION:" + key)
    if values["goldGained"] != {"HUNDRED_GOLD": 100, "TWO_FIFTY_GOLD": 250}.get(bonus, 0):
        raise ValueError("NEOW_GOLD_CONTRADICTION")
    deck = Counter(BASE + (["AscendersBane"] if asc >= 10 else []))
    for card in fields["cardsRemoved"] + fields["cardsTransformed"]:
        remove_card(deck, card)
    deck.update(fields["cardsObtained"])
    for card in fields["cardsUpgraded"]:
        upgrade_card(deck, card)
    choices = rows_at(run, "card_choices", 0)
    if len(choices) != (1 if bonus in CHOICE_BONUSES else 0):
        raise ValueError("NEOW_CHOICE_HISTORY_MISSING_OR_AMBIGUOUS")
    for row in choices:
        picked = row.get("picked")
        if not isinstance(picked, str) or not picked:
            raise ValueError("Neow选牌缺失")
        if picked not in {"SKIP", "Singing Bowl"}:
            deck[picked] += 1
        elif picked == "Singing Bowl":
            raise ValueError("Neow出现未登记碗选择")
    max_hp = 75 if asc >= 14 else 80
    hp = math.floor(max_hp * .9 + .5) if asc >= 6 else max_hp
    max_hp -= values["maxHpLost"]
    hp = min(hp, max_hp) - values["damageTaken"]
    max_hp += values["maxHpGained"]
    hp = min(max_hp, hp + values["maxHpGained"])
    gold = 99 - values["goldLost"] + values["goldGained"]
    if not 0 < hp <= max_hp or gold < 0:
        raise ValueError("Neow后玩家数值非法")
    return {
        "deck": deck, "relics": ["Burning Blood"] + fields["relicsObtained"],
        "potions": Counter(), "capacity": 2 if asc >= 11 else 3,
        "hp": hp, "max_hp": max_hp, "gold": gold, "ascension": asc,
    }


def prefix_array(run, key, floor):
    values = run.get(key)
    if not isinstance(values, list) or len(values) < floor:
        raise ValueError(f"{key}缺少floor{floor}")
    return strings(values[floor - 1])


def advance_floor(run, state, floor):
    """只推进来源规则清楚的M/E/R/T；未知事件和商店使后续前缀不完整。"""
    path = run.get("path_per_floor")
    if not isinstance(path, list) or len(path) < floor:
        raise ValueError("PATH_MISSING")
    kind = path[floor - 1]
    if kind not in {"M", "E", "R", "T"}:
        raise ValueError("ROOM_HISTORY_PENDING:" + str(kind))
    if rows_at(run, "event_choices", floor):
        raise ValueError("EVENT_HISTORY_PENDING")
    for key in ("items_purged_floors", "item_purchase_floors"):
        values = run.get(key)
        if not isinstance(values, list):
            raise ValueError(key + "缺失")
        if floor in [number(v) for v in values]:
            raise ValueError("SHOP_HISTORY_PENDING")
    # 永久卡牌变动无法由普通奖励恢复，避免跨战斗传播未知状态。
    for card in state["deck"]:
        if card_base(card) in PERSISTENT_CARDS:
            raise ValueError("PERSISTENT_CARD_VALUE_MISSING:" + card)
    if set(state["relics"]) - RESET_RELICS:
        raise ValueError("RELIC_HISTORY_PENDING")
    for row in rows_at(run, "card_choices", floor):
        picked = row.get("picked")
        if not isinstance(picked, str) or not picked:
            raise ValueError("CARD_CHOICE_INVALID")
        if picked not in {"SKIP", "Singing Bowl"}:
            state["deck"][picked] += 1
        elif picked == "Singing Bowl":
            raise ValueError("UNREGISTERED_SINGING_BOWL_CHOICE")
    for row in rows_at(run, "campfire_choices", floor):
        if row.get("key") == "SMITH":
            upgrade_card(state["deck"], row.get("data", ""))
        elif row.get("key") != "REST":
            raise ValueError("CAMPFIRE_ACTION_PENDING")
    state["relics"].extend(row["key"] for row in rows_at(run, "relics_obtained", floor))
    # 源记录只提供楼层内分类列表。净库存是可恢复量，原槽位/动作顺序不声称恢复。
    obtained = [row["key"] for row in rows_at(run, "potions_obtained", floor)]
    generated = prefix_array(run, "potions_obtained_alchemize", floor) + prefix_array(run, "potions_obtained_entropic_brew", floor)
    used = prefix_array(run, "potion_use_per_floor", floor)
    discarded = prefix_array(run, "potion_discard_per_floor", floor)
    if generated or any(p in {"FairyPotion", "EntropicBrew"} for p in obtained + used + list(state["potions"])):
        raise ValueError("POTION_AUTO_USE_OR_GENERATION_PENDING")
    if Counter(used) - state["potions"]:
        # 当层才获得又使用的药水需要区分战中与战后可使用时点，不能只验净库存。
        raise ValueError("POTION_WITHIN_FLOOR_ORDER_PENDING")
    inventory = state["potions"] + Counter(obtained)
    for potion in used + discarded:
        if inventory[potion] <= 0:
            raise ValueError("POTION_ACCOUNTING_UNDERFLOW")
        inventory[potion] -= 1
    inventory = +inventory
    if inventory.total() > state["capacity"]:
        raise ValueError("POTION_ACCOUNTING_OVERFLOW")
    state["potions"] = inventory


def catalog():
    source = (ROOT / "third_party/sts_lightspeed/include/constants/SaveFileMappings.h").read_text(encoding="utf-8")
    return {kind: set(re.findall(r"\{" + kind + r'::[A-Z0-9_]+, "([^"\n]+)"\}', source)) for kind in ("CardId", "RelicId", "Potion")}


def card_modifier_evidence(run):
    """只记录来源修饰字段状态；不把缺失或最终全null当作历史无mod证明。"""
    if "basemod:card_modifiers" not in run:
        return "absent_unverified"
    value = run["basemod:card_modifiers"]
    if not isinstance(value, list):
        return "invalid_structure"
    return "all_null_at_recorded_endpoint" if all(x is None for x in value) else "nonempty_unresolved"


def reconstruct_run(run, identity, known):
    combats = run.get("damage_taken")
    if not isinstance(combats, list):
        raise ValueError("damage_taken缺失；不能以0场冒充审计成功")
    combat_by_floor = defaultdict(list)
    for row in combats:
        try:
            f = number(row.get("floor"))
        except (ValueError, AttributeError) as exc:
            raise ValueError("damage_taken包含无法定位楼层的记录") from exc
        if f < 1:
            raise ValueError("战斗楼层必须为正数")
        if 1 <= f <= 15:
            combat_by_floor[f].append(row)
    try:
        state = initial_state(run)
        history_error = None
    except (ValueError, KeyError, TypeError) as exc:
        state = None
        history_error = str(exc)
    output = []
    path = run.get("path_per_floor", [])
    for floor in range(1, max(combat_by_floor, default=0) + 1):
        for index, combat in enumerate(combat_by_floor[floor]):
            modifier_status = card_modifier_evidence(run)
            modifiers_rejected = modifier_status in {"invalid_structure", "nonempty_unresolved"} or identity.get("card_modifier_group_rejected", False)
            blockers = ["SOURCE_CARD_MODIFIERS_UNRESOLVED"] if modifiers_rejected else []
            if history_error:
                blockers.append("PREFIX_UNPROVEN:" + history_error)
            if len(combat_by_floor[floor]) != 1 or not isinstance(path, list) or len(path) < floor or path[floor - 1] not in {"M", "E"}:
                blockers.append("ENTRY_ROOM_OR_MULTIPLE_COMBATS_PENDING")
            encounter = combat.get("enemies")
            if encounter not in ENCOUNTERS:
                blockers.append("ENCOUNTER_GENERATOR_PENDING:" + str(encounter))
            hp = max_hp = gold = None
            if state:
                if floor == 1:
                    hp, max_hp, gold = state["hp"], state["max_hp"], state["gold"]
                else:
                    try:
                        hp, max_hp, gold = [number(run[key][floor - 2]) for key in ("current_hp_per_floor", "max_hp_per_floor", "gold_per_floor")]
                        if not 0 < hp <= max_hp or gold < 0:
                            raise ValueError("非法入口HP/gold")
                    except (ValueError, KeyError, TypeError, IndexError):
                        blockers.append("PREVIOUS_FLOOR_METRIC_MISSING_OR_INVALID")
                unknown_relics = sorted(set(state["relics"]) - RESET_RELICS)
                if unknown_relics:
                    blockers.append("RELIC_COUNTER_OR_HOOK_PENDING:" + ",".join(unknown_relics))
                for card in state["deck"]:
                    try:
                        base = card_base(card)
                    except ValueError:
                        blockers.append("CARD_FORMAT_PENDING:" + card)
                        continue
                    if base not in known["CardId"] or base in PERSISTENT_CARDS:
                        blockers.append("CARD_SEMANTICS_PENDING:" + card)
                for potion in state["potions"]:
                    if potion not in known["Potion"]:
                        blockers.append("POTION_SEMANTICS_PENDING:" + potion)
                # 绿钥匙只记录实际取得楼层；未取得不证明精英不是燃烧精英。
                if isinstance(path, list) and len(path) >= floor and path[floor - 1] == "E":
                    blockers.append("BURNING_ELITE_MODIFIER_UNRECORDED")
            candidate = None
            if not blockers:
                candidate = {
                    "entry_timing": "pre_combat_initialization",
                    "initialization_phase": "before_destination_room_entry",
                    "floor": floor, "act": 1, "character": "IRONCLAD", "ascension": state["ascension"],
                    "player": {"hp": hp, "max_hp": max_hp, "gold": gold},
                    "deck": sorted(state["deck"].elements()), "relics": list(state["relics"]),
                    "potions": sorted(state["potions"].elements()) + [None] * (state["capacity"] - state["potions"].total()),
                    "potion_slot_policy": "canonical-inventory-slots-v1;not-original-slots",
                    "encounter": ENCOUNTERS[encounter], "environment_replay_seed": None,
                    "hp_source": "standard_start_plus_neow_log" if floor == 1 else f"current_hp_per_floor[{floor - 2}] before destination onEnterRoom",
                    "field_evidence": {
                        "deck": "M2C-02;starter+neow_bonus_log+floor0_choice+prior_card_choices+prior_smith",
                        "hp_gold": "M2C-03;Neow推导或前层边界指标；不读取本场战后指标",
                        "relics": "M2C-04;starter+neow+prior_relics_obtained;no_unproven_persistent_counter",
                        "potions": "M2C-05;prior_obtained-use-discard;canonical_inventory_slots",
                        "enemy_and_piles": "M2C-06;resampled_by_backend_not_historical_replay",
                    },
                    "initialize_once": ["room_entry_hooks", "monster_generation", "battle_start_hooks", "draw", "energy", "queues"],
                    "resampling_policy": "public-battle-a-resample-v1", "exact_historical_replay": False,
                }
            output.append({
                "scene_id": identity["group_id"] + f":floor-{floor}:combat-{index}",
                "group_id": identity["group_id"], "research_split": identity["research_split"],
                "source_path": identity["source_path"], "raw_sha256": identity["raw_sha256"],
                "source_build": run.get("build_version"), "source_seed": run.get("seed_played"),
                "floor": floor, "encounter_label": encounter,
                "reconstruction_status": "rule_constructible_source_unverified" if candidate else "partial_or_excluded",
                "blockers": sorted(set(blockers)), "candidate": candidate,
                "formal_eligibility": "audit-only",
                "source_admission_policy": SOURCE_ADMISSION_POLICY,
                "derived_data_admission_status": "admitted_backend_pending" if candidate else "rejected_or_pending",
                "historical_rules_equivalence": "unverified",
                "card_modifier_evidence": modifier_status,
                "backend_status": "pending",
                "admission_blockers": ([] if candidate else ["PLAYER_ENTRY_UNPROVEN_OR_SOURCE_REJECTED"]) + ["BACKEND_CONTENT_AND_CAPACITY_NOT_IMPLEMENTED"],
            })
        if state and not history_error:
            try:
                advance_floor(run, state, floor)
            except (ValueError, KeyError, TypeError) as exc:
                history_error = str(exc)
    return output


def load_records(archive):
    if sha(archive) != ZIP_SHA:
        raise ValueError("固定来源ZIP哈希不匹配")
    z = zipfile.ZipFile(io.BytesIO(archive))
    prefix = f"Slay-the-Spire-data-{COMMIT}/"
    records = []
    for name in sorted(z.namelist()):
        if not name.startswith(prefix) or not name.endswith(".run"):
            continue
        raw = z.read(name)
        run = json.loads(raw)
        if run.get("character_chosen") == "IRONCLAD":
            records.append({"source_path": name[len(prefix):], "raw_sha256": sha(raw), "run": run})
    return records


def group_records(records):
    """按内容、play_id、source seed做传递关联；不按胜负选择。"""
    parent = list(range(len(records)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    owners = {}
    identities = []
    for i, record in enumerate(records):
        r = record["run"]
        keys = ["sha:" + record["raw_sha256"]]
        for key in ("play_id", "seed_played"):
            value = r.get(key)
            if isinstance(value, (int, str)) and not isinstance(value, bool) and str(value):
                keys.append(key + ":" + str(value))
        identities.append(keys)
        for key in keys:
            if key in owners:
                parent[find(i)] = find(owners[key])
            owners[key] = i
    grouped = defaultdict(list)
    for i, record in enumerate(records):
        grouped[find(i)].append((i, record))
    output = []
    for members in grouped.values():
        tokens = sorted({k for i, _ in members for k in identities[i]})
        group_id = "run-group:" + sha(canonical(tokens))[:20]
        bucket = int(sha(group_id.encode())[:8], 16) % 100
        split = "train" if bucket < 80 else "dev" if bucket < 90 else "reserved-eval"
        representative = min((r for _, r in members), key=lambda r: r["source_path"])
        output.append({**representative, "group_id": group_id, "research_split": split,
                       "aliases": sorted(r["source_path"] for _, r in members),
                       "identity_tokens": tokens,
                       "card_modifier_group_rejected": any(card_modifier_evidence(r["run"]) in {"invalid_structure", "nonempty_unresolved"} for _, r in members),
                       "conflicting_variants": len({r["raw_sha256"] for _, r in members}) > 1})
    return sorted(output, key=lambda r: r["group_id"])


def coverage(scenes):
    candidates = [s for s in scenes if s["candidate"]]
    return {
        "scene_count": len(candidates), "independent_groups": len({s["group_id"] for s in candidates}),
        "by_floor": dict(sorted(Counter(s["floor"] for s in candidates).items())),
        "by_encounter": dict(Counter(s["encounter_label"] for s in candidates).most_common()),
        "by_research_split": dict(Counter(s["research_split"] for s in candidates)),
        "card_classes": sorted({card_base(c) for s in candidates for c in s["candidate"]["deck"]}),
        "deck_multisets": len({tuple(s["candidate"]["deck"]) for s in candidates}),
        "relics": dict(Counter(r for s in candidates for r in s["candidate"]["relics"])),
        "potions": dict(Counter(p for s in candidates for p in s["candidate"]["potions"] if p)),
        "nonempty_potion_scenes": sum(any(s["candidate"]["potions"]) for s in candidates),
        "upgraded_card_scenes": sum(any("+" in c for c in s["candidate"]["deck"]) for s in candidates),
        "nonstarter_scenes": sum(any(card_base(c) not in set(BASE + ["AscendersBane"]) for c in s["candidate"]["deck"]) for s in candidates),
        "m1_card_classes_observed": sorted(M1_CARDS & {card_base(c) for s in candidates for c in s["candidate"]["deck"]}),
        "m1_card_classes_missing": sorted(M1_CARDS - {card_base(c) for s in candidates for c in s["candidate"]["deck"]}),
        "m1_plus_ascenders_bane_whole_deck_scenes": sum(
            all(card_base(c) in M1_CARDS | {"AscendersBane"} and c != "True Grit+1" for c in s["candidate"]["deck"])
            for s in candidates
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="缺少缓存时下载固定提交约10MB ZIP")
    parser.add_argument("--archive", type=Path, default=ROOT / "reference/public-run-corpus/matiger-fixed.zip")
    parser.add_argument("--output", type=Path, default=ROOT / "reference/public-run-corpus/corpus.json")
    parser.add_argument("--index", type=Path, default=ROOT / "docs/m2-corpus-index.json")
    args = parser.parse_args(argv)
    if not args.archive.exists():
        if not args.download:
            parser.error("缺少ZIP；使用--download或提供已核验的--archive")
        url = f"https://codeload.github.com/MaT1g3R/Slay-the-Spire-data/zip/{COMMIT}"
        with urllib.request.urlopen(url, timeout=40) as response:
            raw = response.read(32 * 1024 * 1024 + 1)
        if len(raw) > 32 * 1024 * 1024 or sha(raw) != ZIP_SHA:
            raise ValueError("下载超界或哈希不匹配")
        args.archive.parent.mkdir(parents=True, exist_ok=True)
        args.archive.write_bytes(raw)
    records = load_records(args.archive.read_bytes())
    groups = group_records(records)
    known = catalog()
    scenes = []
    for group in groups:
        entries = reconstruct_run(group["run"], group, known)
        if group["conflicting_variants"]:
            for entry in entries:
                entry["candidate"] = None
                entry["blockers"].append("CONFLICTING_SOURCE_VARIANTS")
                entry["reconstruction_status"] = "partial_or_excluded"
                entry["derived_data_admission_status"] = "rejected_or_pending"
        scenes.extend(entries)
    identities = defaultdict(set)
    for g in groups:
        for token in g["identity_tokens"]:
            identities[token].add(g["research_split"])
    no_leak = all(len(splits) == 1 for splits in identities.values())
    assert no_leak
    summary = {
        "raw_ironclad_files": len(records), "independent_run_groups": len(groups),
        "duplicate_alias_files": len(records) - len(groups),
        "conflicting_groups": sum(g["conflicting_variants"] for g in groups),
        "all_run_combat_rows": sum(len(g["run"].get("damage_taken", [])) for g in groups),
        "act1_combat_rows": len(scenes), "rule_candidates": coverage(scenes),
        "formal_candidate_count": 0,
        "derived_data_admitted_count": sum(s["derived_data_admission_status"] == "admitted_backend_pending" for s in scenes),
        "card_modifier_group_rejected_count": sum(g["card_modifier_group_rejected"] for g in groups),
        "source_builds": dict(Counter(g["run"].get("build_version") for g in groups)),
        "ascensions": dict(Counter(str(g["run"].get("ascension_level")) for g in groups)),
        "research_split_groups": dict(Counter(g["research_split"] for g in groups)),
        "split_leak_check_passed": no_leak,
        "blocker_counts": dict(Counter(b for s in scenes for b in s["blockers"]).most_common()),
    }
    missing_cards = summary["rule_candidates"]["m1_card_classes_missing"]
    summary["missing_m1_cards_recorded_act1_rewards"] = {
        card: [
            {"group_id": g["group_id"], "source_path": g["source_path"], "floor": number(row["floor"]), "picked": row["picked"]}
            for g in groups for row in g["run"].get("card_choices", [])
            if 0 <= number(row["floor"]) <= 15 and card_base(row["picked"]) == card
        ] for card in missing_cards
    }
    group_index = [{k: v for k, v in g.items() if k != "run"} for g in groups]
    result = {"schema": SCHEMA, "source_url": SOURCE_URL, "commit": COMMIT, "archive_sha256": ZIP_SHA,
              "source_admission_policy": SOURCE_ADMISSION_POLICY, "historical_rules_equivalence": "unverified",
              "implementation_sha256": sha(Path(__file__).read_bytes()),
              "catalog_sha256": sha((ROOT / "third_party/sts_lightspeed/include/constants/SaveFileMappings.h").read_bytes()),
              "split_policy": "connected-identity-sha256-v1;research-only;80/10/10",
              "summary": summary, "groups": group_index, "scenes": scenes}
    write_json(args.output, result)
    # 索引保留所有候选与排除码；全量原文仅留在ignored ZIP。
    write_json(args.index, {**result, "corpus_sha256": sha(args.output.read_bytes())})
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
