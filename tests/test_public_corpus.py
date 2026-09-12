"""公开场景库的边界、牌组重建、库存与跨组泄漏测试。"""
import copy
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/audit-public-corpus.py"
SPEC = importlib.util.spec_from_file_location("public_corpus", SCRIPT)
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


def run_data():
    return {
        "character_chosen": "IRONCLAD", "ascension_level": 20,
        "is_daily": False, "is_trial": False, "is_endless": False,
        "build_version": "2022-12-18", "play_id": "a", "seed_played": "100",
        "neow_bonus": "HUNDRED_GOLD", "neow_cost": "NONE",
        "neow_bonus_log": {"cardsRemoved": [], "cardsTransformed": [], "cardsObtained": [],
            "cardsUpgraded": [], "relicsObtained": [], "maxHpLost": 0, "maxHpGained": 0,
            "damageTaken": 0, "goldLost": 0, "goldGained": 100},
        "damage_taken": [{"floor": 1, "enemies": "Cultist"}, {"floor": 2, "enemies": "Jaw Worm"}],
        "path_per_floor": ["M", "M"],
        "current_hp_per_floor": [61, 44], "max_hp_per_floor": [75, 75], "gold_per_floor": [210, 223],
        "card_choices": [{"floor": 1, "picked": "Cleave"}, {"floor": 2, "picked": "Anger"}],
        "event_choices": [], "campfire_choices": [], "items_purged_floors": [], "item_purchase_floors": [],
        "relics_obtained": [], "potions_obtained": [{"floor": 1, "key": "Weak Potion"}],
        "potions_obtained_alchemize": [[], []], "potions_obtained_entropic_brew": [[], []],
        "potion_use_per_floor": [[], []], "potion_discard_per_floor": [[], []],
    }


def scenes(run):
    identity = {"group_id": "g", "research_split": "train", "source_path": "s", "raw_sha256": "h"}
    return C.reconstruct_run(run, identity, C.catalog())


@pytest.mark.parametrize("value", [{}, None, "", [None, {"id": "custom"}], [False]])
def test_card_modifiers_reject_every_scene(value):
    r = run_data()
    r["basemod:card_modifiers"] = value
    assert all(s["candidate"] is None and "SOURCE_CARD_MODIFIERS_UNRESOLVED" in s["blockers"] for s in scenes(r))


def test_modifier_evidence_does_not_claim_historical_equivalence():
    r = run_data()
    for value, expected in [(None, "absent_unverified"), ([None] * 11, "all_null_at_recorded_endpoint")]:
        if value is not None:
            r["basemod:card_modifiers"] = value
        row = scenes(r)[0]
        assert row["candidate"] and row["card_modifier_evidence"] == expected
        assert row["historical_rules_equivalence"] == "unverified"
        assert row["derived_data_admission_status"] == "admitted_backend_pending"


def test_bad_modifier_alias_rejects_whole_group_and_identity_is_order_stable():
    a, b = run_data(), run_data()
    b["basemod:card_modifiers"] = [{}]
    records = [{"source_path": "a", "raw_sha256": "a", "run": a}, {"source_path": "b", "raw_sha256": "b", "run": b}]
    first = C.group_records(records)[0]
    second = C.group_records(list(reversed(records)))[0]
    assert first["group_id"] == second["group_id"] and first["research_split"] == second["research_split"]
    assert first["card_modifier_group_rejected"]
    assert all(s["candidate"] is None for s in C.reconstruct_run(a, first, C.catalog()))


def test_second_battle_contains_prior_reward_and_prior_exit_hp_only():
    first, second = scenes(run_data())
    a, b = first["candidate"], second["candidate"]
    assert a["player"]["hp"] == 68 and "Cleave" not in a["deck"]
    assert a["potions"] == [None, None]
    assert b["player"] == {"hp": 61, "max_hp": 75, "gold": 210}
    assert "Cleave" in b["deck"] and "Anger" not in b["deck"]
    assert b["potions"] == ["Weak Potion", None]
    assert b["environment_replay_seed"] is None
    assert second["formal_eligibility"] == "audit-only"


def test_neow_transform_consumes_original_cards_and_keeps_results():
    r = run_data()
    r["neow_bonus"] = "TRANSFORM_TWO_CARDS"
    r["neow_bonus_log"].update(goldGained=0, cardsTransformed=["Strike_R", "Defend_R"], cardsObtained=["Cleave", "Bludgeon"])
    state = C.initial_state(r)
    assert state["deck"]["Strike_R"] == 4 and state["deck"]["Defend_R"] == 3
    assert state["deck"]["Cleave"] == state["deck"]["Bludgeon"] == 1
    assert state["deck"].total() == 11


def test_neow_choice_floor_zero_is_not_lost_or_duplicated():
    r = run_data()
    r["neow_bonus"] = "THREE_RARE_CARDS"
    r["neow_bonus_log"]["goldGained"] = 0
    r["card_choices"].insert(0, {"floor": 0, "picked": "Immolate"})
    assert C.initial_state(r)["deck"]["Immolate"] == 1
    r["neow_bonus_log"]["cardsObtained"] = ["Immolate"]
    with pytest.raises(ValueError, match="DELTA_CONTRADICTION"):
        C.initial_state(r)


def test_neow_upgrade_replaces_one_instance():
    r = run_data()
    r["neow_bonus"] = "UPGRADE_CARD"
    r["neow_bonus_log"].update(goldGained=0, cardsUpgraded=["Strike_R"])
    state = C.initial_state(r)
    assert state["deck"]["Strike_R"] == 4 and state["deck"]["Strike_R+1"] == 1
    assert state["deck"].total() == 11


def test_neow_logged_damage_and_max_hp_changes_apply_in_order():
    r = run_data()
    r["neow_bonus"] = "TWENTY_PERCENT_HP_BONUS"
    r["neow_cost"] = "PERCENT_DAMAGE"
    r["neow_bonus_log"].update(goldGained=0, damageTaken=18, maxHpGained=14)
    state = C.initial_state(r)
    assert (state["hp"], state["max_hp"]) == (64, 89)


@pytest.mark.parametrize("value", [True, float("inf"), float("nan"), 2.5, "20"])
def test_non_integer_source_numbers_rejected(value):
    with pytest.raises(ValueError):
        C.number(value)


def test_event_between_combats_blocks_later_reconstruction():
    r = run_data()
    r["path_per_floor"] = ["M", "?", "M"]
    r["damage_taken"][1]["floor"] = 3
    result = scenes(r)
    assert result[0]["candidate"]
    assert result[1]["candidate"] is None
    assert any("ROOM_HISTORY_PENDING:?" in b for b in result[1]["blockers"])


def test_unknown_relic_does_not_get_removed_to_make_scene_pass():
    r = run_data()
    r["relics_obtained"] = [{"floor": 1, "key": "Pen Nib"}]
    result = scenes(r)
    assert result[0]["candidate"]
    assert result[1]["candidate"] is None
    assert "RELIC_COUNTER_OR_HOOK_PENDING:Pen Nib" in result[1]["blockers"]


def test_automatic_fairy_consumption_is_not_assumed_logged():
    r = run_data()
    r["potions_obtained"][0]["key"] = "FairyPotion"
    assert scenes(r)[1]["candidate"] is None


def test_potion_underflow_is_rejected():
    r = run_data()
    r["potion_use_per_floor"][0] = ["BloodPotion"]
    assert any("POTION_WITHIN_FLOOR_ORDER_PENDING" in b for b in scenes(r)[1]["blockers"])


def test_potion_capacity_and_missing_log_are_rejected():
    r = run_data()
    r["potions_obtained"] *= 3
    assert scenes(r)[1]["candidate"] is None
    r = run_data()
    r.pop("potion_discard_per_floor")
    assert scenes(r)[1]["candidate"] is None


def test_elite_burning_modifier_not_inferred_from_key_acquisition():
    r = run_data()
    r["path_per_floor"][1] = "E"
    r["damage_taken"][1]["enemies"] = "Gremlin Nob"
    r["green_key_taken_log"] = 2
    assert "BURNING_ELITE_MODIFIER_UNRECORDED" in scenes(r)[1]["blockers"]


def test_final_deck_and_future_rewards_do_not_change_earlier_scene():
    r = run_data()
    before = scenes(r)[1]["candidate"]
    r["master_deck"] = ["Unknown"]
    r["card_choices"].append({"floor": 10, "picked": "Unknown"})
    assert scenes(r)[1]["candidate"] == before


def record(path, play_id, seed, digest):
    return {"source_path": path, "raw_sha256": digest,
            "run": {"play_id": play_id, "seed_played": seed, "character_chosen": "IRONCLAD"}}


def test_duplicate_aliases_do_not_increase_run_count_or_change_split():
    r = record("a", "p", "s", "h")
    first = C.group_records([r])[0]
    second = C.group_records([r, {**r, "source_path": "b"}])[0]
    assert first["group_id"] == second["group_id"]
    assert first["research_split"] == second["research_split"]
    assert second["aliases"] == ["a", "b"] and not second["conflicting_variants"]


def test_identity_grouping_is_transitive_and_order_independent():
    records = [record("a", "p1", "s1", "h1"), record("b", "p1", "s2", "h2"), record("c", "p2", "s2", "h3")]
    a, b = C.group_records(records), C.group_records(list(reversed(records)))
    assert len(a) == len(b) == 1 and a[0]["group_id"] == b[0]["group_id"]
    assert a[0]["conflicting_variants"]


def test_pinned_archive_rejects_tampering_before_parse():
    with pytest.raises(ValueError, match="哈希"):
        C.load_records(b"not-a-zip")


@pytest.mark.parametrize("key", ["build_version", "seed_played", "event_choices"])
def test_initial_source_fields_cannot_be_defaulted(key):
    r = run_data()
    r.pop(key)
    assert all(s["candidate"] is None for s in scenes(r))


def test_normal_card_multiple_upgrade_suffix_rejected():
    with pytest.raises(ValueError, match="升级"):
        C.card_base("Strike_R+2")
    assert C.card_base("Searing Blow+6") == "Searing Blow"


def test_same_floor_reward_does_not_make_earlier_combat_potion_use_possible():
    r = run_data()
    r["potion_use_per_floor"][0] = ["Weak Potion"]
    assert any("POTION_WITHIN_FLOOR_ORDER_PENDING" in b for b in scenes(r)[1]["blockers"])


def test_missing_combat_floor_is_not_silently_dropped():
    r = run_data()
    r["damage_taken"][0].pop("floor")
    with pytest.raises(ValueError, match="楼层"):
        scenes(r)


def test_neow_cannot_remove_a_card_not_in_the_deck():
    r = run_data()
    r["neow_bonus"] = "REMOVE_CARD"
    r["neow_bonus_log"].update(goldGained=0, cardsRemoved=["Cleave"])
    assert all(s["candidate"] is None for s in scenes(r))
