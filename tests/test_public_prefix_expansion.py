"""公开事件/商店前缀扩展的真实数据、证据边界和拒绝路径测试。"""
from __future__ import annotations

import copy
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/expand-public-prefixes.py"
SPEC = importlib.util.spec_from_file_location("public_prefix_expansion", SCRIPT)
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


@pytest.fixture(scope="module")
def result():
    index = json.loads((ROOT / "docs/m2-corpus-index.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "docs/m2-public-scene-manifest.json").read_text(encoding="utf-8"))
    return M.build_result(
        index, manifest,
        (ROOT / "reference/public-run-corpus/corpus.json").read_bytes(),
        (ROOT / "reference/public-run-corpus/matiger-fixed.zip").read_bytes(),
    )


def test_real_counts_keep_three_admission_layers_separate(result):
    summary = result["summary"]
    assert summary["source_raw_ironclad_files"] == 203
    assert summary["source_independent_run_groups"] == 157
    assert summary["original_manifest_scene_count"] == 99
    assert summary["raw_located_prefix_target_rows"] == 629
    assert summary["raw_research_candidate_count"] == 198
    assert summary["evidence_complete_candidate_count"] == 96
    assert summary["backend_admissible_candidate_count"] == 19
    assert summary["raw_research_candidate_count"] >= summary["evidence_complete_candidate_count"]
    assert summary["evidence_complete_candidate_count"] >= summary["backend_admissible_candidate_count"]
    assert summary["backend_admissible_candidate_count"] > 0
    assert summary["raw_research_candidate_run_groups"] == 91
    assert summary["evidence_complete_candidate_run_groups"] == 54
    assert summary["backend_admissible_candidate_run_groups"] == 14


def test_elite_burning_state_is_required_and_not_defaulted(result):
    elite_labels = {"Gremlin Nob", "Lagavulin", "3 Sentries"}
    elite_rows = [
        row for row in result["scenes"]
        if row["candidate"] is not None and row["encounter_label"] in elite_labels
    ]
    assert len(elite_rows) == 63
    assert not [row for row in elite_rows if row["evidence_complete"]]
    assert all(
        "ELITE_BURNING_STATE_UNPROVEN:" + row["candidate"]["encounter"]
        in row["evidence_blockers"]
        for row in elite_rows
    )
    blocked_ids = {
        "run-group:53c16194b16286bd892d:floor-7:combat-0",
        "run-group:f2672b82929351d73ae6:floor-6:combat-0",
    }
    by_id = {row["scene_id"]: row for row in result["scenes"]}
    assert blocked_ids <= by_id.keys()
    assert all(not by_id[scene_id]["backend_admissible"] for scene_id in blocked_ids)
    assert all(by_id[scene_id]["candidate"].get("burning_elite") is None for scene_id in blocked_ids)
    assert result["summary"]["evidence_complete_candidate_count"] == sum(
        row["evidence_complete"] for row in result["scenes"]
    )
    assert result["summary"]["backend_admissible_candidate_count"] == sum(
        row["backend_admissible"] for row in result["scenes"]
    )


def test_entry_a_and_source_seed_boundaries_are_explicit(result):
    assert result["entry_timing"] == "pre_combat_initialization / before_destination_room_entry"
    assert result["master_deck_used"] is False
    for row in result["scenes"]:
        if row["candidate"] is None:
            continue
        candidate = row["candidate"]
        assert candidate["entry_timing"] == "pre_combat_initialization"
        assert candidate["initialization_phase"] == "before_destination_room_entry"
        assert candidate["environment_replay_seed"] is None
        assert candidate["exact_historical_replay"] is False
        assert row["source_seed"] is not None


def test_original_99_candidates_are_unchanged(result):
    check = result["original_manifest_consistency"]
    assert check["passed"]
    assert check["original_manifest_accepted_scenes"] == 99
    assert check["matched_and_equal"] == 99
    assert check["missing_scene_ids"] == []
    assert check["candidate_mismatches"] == []


def test_real_event_and_shop_success_and_rejection_cases_are_present(result):
    events = result["prefix_gate_analysis"]["event"]
    shops = result["prefix_gate_analysis"]["shop"]
    assert events["outcome_counts"]["STRUCTURALLY_RESOLVED"] == 282
    assert events["outcome_counts"]["EVENT_CARD_REWARD_SAME_FLOOR_ORDER_UNRESOLVED"] == 14
    assert shops["outcome_counts"]["STRUCTURALLY_RESOLVED"] == 142
    assert shops["outcome_counts"]["SHOP_CARD_SELECTION_MISSING"] == 1
    assert shops["outcome_counts"]["SHOP_RANDOM_UPGRADE_TARGET_MISSING"] == 2
    assert "EVENT_CARD_REWARD_SAME_FLOOR_ORDER_UNRESOLVED" in result["examples"]["structural_prefix_rejection_examples"]
    assert "SHOP_CARD_SELECTION_MISSING" in result["examples"]["structural_prefix_rejection_examples"]
    assert "EVENT_POTION_ID_MISSING" in result["examples"]["rejection_examples"]

    successful = [row for row in result["scenes"] if row["evidence_complete"]]
    assert successful
    assert any("event" in row["prefix_types"] for row in successful)
    assert any("shop" in row["prefix_types"] for row in successful)


def test_exact_duplicate_event_rows_are_applied_once_from_real_run():
    records = M.AUDIT.load_records((ROOT / "reference/public-run-corpus/matiger-fixed.zip").read_bytes())
    groups = M.AUDIT.group_records(records)
    group = next(group for group in groups if group["source_path"].endswith("1663982308.run"))
    # 该真实run在floor 5还有一个未恢复的Lab事件；这里隔离测试floor 8重复
    # 日志的去重语义，不把那个独立阻塞误当成重复事件已执行。
    state = {"deck": Counter(), "relics": [], "potions": Counter(), "capacity": 2}
    detail = M.validate_event_and_apply(group["run"], state, 8)
    assert detail["duplicate_rows_removed"] == 2
    assert state["deck"]["Feed"] == 1


def test_repeated_card_upgrade_and_remove_preserve_multiset_semantics():
    state = {
        "deck": Counter(["Strike_R", "Strike_R", "Bash"]),
        "relics": [], "potions": Counter(), "capacity": 2,
    }
    event = {
        "floor": 1, "event_name": "Living Wall", "player_choice": "Grow",
        "damage_healed": 0, "damage_taken": 0, "gold_gain": 0, "gold_loss": 0,
        "max_hp_gain": 0, "max_hp_loss": 0, "cards_upgraded": ["Bash"],
    }
    run = {
        "event_choices": [event], "card_choices": [],
        "potions_obtained": [], "potions_obtained_alchemize": [[]],
        "potions_obtained_entropic_brew": [[]], "potion_use_per_floor": [[]],
        "potion_discard_per_floor": [[]],
    }
    M.validate_event_and_apply(run, state, 1)
    assert state["deck"]["Strike_R"] == 2
    assert state["deck"]["Bash"] == 0
    assert state["deck"]["Bash+1"] == 1

    state = {
        "deck": Counter(["Strike_R", "Strike_R", "Bash"]),
        "relics": [], "potions": Counter(), "capacity": 2,
    }
    event = dict(event, player_choice="Forget", cards_upgraded=[], cards_removed=["Strike_R"])
    M.validate_event_and_apply(run | {"event_choices": [event]}, state, 1)
    assert state["deck"]["Strike_R"] == 1


def test_nonidentical_same_floor_event_rows_and_same_floor_reward_are_rejected():
    base = {
        "floor": 1, "event_name": "Living Wall", "player_choice": "Grow",
        "damage_healed": 0, "damage_taken": 0, "gold_gain": 0, "gold_loss": 0,
        "max_hp_gain": 0, "max_hp_loss": 0,
    }
    run = {"event_choices": [base, dict(base, player_choice="Forget")], "card_choices": []}
    assert M.structural_event_reason(run, 1) == "EVENT_TIMING_AMBIGUOUS_NONIDENTICAL"
    state = {"deck": Counter(["Bash"]), "relics": [], "potions": Counter(), "capacity": 2}
    with pytest.raises(ValueError, match="EVENT_TIMING_AMBIGUOUS_NONIDENTICAL"):
        M.validate_event_and_apply(run, state, 1)

    run = {"event_choices": [base], "card_choices": [{"floor": 1, "picked": "Cleave"}]}
    assert M.structural_event_reason(run, 1) == "EVENT_CARD_REWARD_SAME_FLOOR_ORDER_UNRESOLVED"


def test_event_potion_ledger_consumes_same_floor_use_and_rejects_missing_or_wrong_logs():
    records = M.AUDIT.load_records((ROOT / "reference/public-run-corpus/matiger-fixed.zip").read_bytes())
    group = next(group for group in M.AUDIT.group_records(records) if group["source_path"].endswith("1667161552.run"))
    run = copy.deepcopy(group["run"])
    floor = 2
    run["potion_use_per_floor"][floor - 1] = ["Fruit Juice"]
    state = {
        "deck": Counter(["Bash"]), "relics": [],
        "potions": Counter(["Fruit Juice"]), "capacity": 2,
    }
    M.validate_event_and_apply(run, state, floor)
    assert state["potions"] == Counter()

    obtained_and_discarded = copy.deepcopy(group["run"])
    obtained_and_discarded["potions_obtained"] = [{"floor": floor, "key": "Swift Potion"}]
    obtained_and_discarded["potion_discard_per_floor"][floor - 1] = ["Swift Potion"]
    state = {"deck": Counter(["Bash"]), "relics": [], "potions": Counter(), "capacity": 2}
    M.validate_event_and_apply(obtained_and_discarded, state, floor)
    assert state["potions"] == Counter()

    missing = copy.deepcopy(group["run"])
    missing.pop("potion_discard_per_floor")
    state = {"deck": Counter(["Bash"]), "relics": [], "potions": Counter(), "capacity": 2}
    with pytest.raises(ValueError, match="POTION_FLOOR_LOG_MISSING_OR_INVALID"):
        M.validate_event_and_apply(missing, state, floor)

    wrong = copy.deepcopy(group["run"])
    wrong["potion_use_per_floor"][floor - 1] = ["SpeedPotion"]
    state = {
        "deck": Counter(["Bash"]), "relics": [],
        "potions": Counter(["Fruit Juice"]), "capacity": 2,
    }
    with pytest.raises(ValueError, match="POTION_WITHIN_FLOOR_ORDER_PENDING"):
        M.validate_event_and_apply(wrong, state, floor)

    generated = copy.deepcopy(group["run"])
    generated["potions_obtained_alchemize"][floor - 1] = ["Swift Potion"]
    state = {"deck": Counter(["Bash"]), "relics": [], "potions": Counter(), "capacity": 2}
    with pytest.raises(ValueError, match="POTION_AUTO_USE_OR_GENERATION_PENDING"):
        M.validate_event_and_apply(generated, state, floor)


def test_event_effectful_outcomes_require_their_recorded_effect_fields():
    records = M.AUDIT.load_records((ROOT / "reference/public-run-corpus/matiger-fixed.zip").read_bytes())
    groups = M.AUDIT.group_records(records)

    living_group = next(group for group in groups if group["source_path"].endswith("1667161552.run"))
    living_run = copy.deepcopy(living_group["run"])
    grow = next(row for row in living_run["event_choices"] if row.get("event_name") == "Living Wall")
    grow.pop("cards_upgraded")
    living_run["event_choices"] = [grow]
    assert M.structural_event_reason(living_run, int(grow["floor"])) == (
        "EVENT_REQUIRED_EFFECT_FIELD_MISSING:cards_upgraded"
    )
    state = {"deck": Counter(["Carnage"]), "relics": [], "potions": Counter(), "capacity": 2}
    with pytest.raises(ValueError, match="EVENT_REQUIRED_EFFECT_FIELD_MISSING:cards_upgraded"):
        M.validate_event_and_apply(living_run, state, int(grow["floor"]))

    transformed_group = next(
        group for group in groups
        if any(row.get("event_name") == "Transmorgrifier" for row in group["run"].get("event_choices", []))
    )
    transformed_run = copy.deepcopy(transformed_group["run"])
    transformed = next(row for row in transformed_run["event_choices"] if row.get("event_name") == "Transmorgrifier")
    transformed.pop("cards_obtained")
    transformed_run["event_choices"] = [transformed]
    assert M.structural_event_reason(transformed_run, int(transformed["floor"])) == (
        "EVENT_REQUIRED_EFFECT_FIELD_MISSING:cards_obtained"
    )

    relic_group = next(
        group for group in groups
        if any(row.get("event_name") == "Golden Idol" for row in group["run"].get("event_choices", []))
    )
    relic_run = copy.deepcopy(relic_group["run"])
    relic_event = next(row for row in relic_run["event_choices"] if row.get("event_name") == "Golden Idol")
    relic_event.pop("relics_obtained")
    relic_run["event_choices"] = [relic_event]
    assert "EVENT_REQUIRED_EFFECT_FIELD_MISSING:relics_obtained" == M.structural_event_reason(
        relic_run, int(relic_event["floor"])
    )

    # 明确无效果的结果仍可省略空列表，不能把所有事件都机械要求六类列表。
    no_effect_group = next(
        group for group in groups
        if any(
            row.get("event_name") == "Liars Game" and row.get("player_choice") == "Ignored"
            for row in group["run"].get("event_choices", [])
        )
    )
    no_effect_run = copy.deepcopy(no_effect_group["run"])
    no_effect = next(
        row for row in no_effect_run["event_choices"]
        if row.get("event_name") == "Liars Game" and row.get("player_choice") == "Ignored"
    )
    no_effect_run["event_choices"] = [no_effect]
    state = {"deck": Counter(), "relics": [], "potions": Counter(), "capacity": 2}
    M.validate_event_and_apply(no_effect_run, state, int(no_effect["floor"]))


def test_real_shop_transactions_add_full_content_and_do_not_use_remaining_shop_contents():
    records = M.AUDIT.load_records((ROOT / "reference/public-run-corpus/matiger-fixed.zip").read_bytes())
    groups = M.AUDIT.group_records(records)
    group = next(group for group in groups if group["source_path"].endswith("1670211901.run"))
    state = M.AUDIT.initial_state(group["run"])
    M.AUDIT.advance_floor(group["run"], state, 1)
    detail = M.validate_shop_and_apply(group["run"], state, 2, M.AUDIT.catalog())
    assert [item for _, item in [(x["floor"], x["item"]) for x in detail["purchases"]]] == [
        "Explosive Potion", "PanicButton"
    ]
    assert state["deck"]["PanicButton"] == 1
    assert state["potions"]["Explosive Potion"] == 1
    # 购买品已经从离店时的shop_contents列表消失，不能要求它仍出现在剩余库存中。
    remaining = detail["shop_contents"]["cards"] + detail["shop_contents"]["relics"] + detail["shop_contents"]["potions"]
    assert "PanicButton" not in remaining


def test_missing_logs_and_secondary_selection_are_not_defaulted(result):
    records = M.AUDIT.load_records((ROOT / "reference/public-run-corpus/matiger-fixed.zip").read_bytes())
    groups = M.AUDIT.group_records(records)
    group = next(group for group in groups if group["source_path"].endswith("1671231414.run"))
    run = copy.deepcopy(group["run"])
    run["shop_contents"] = []
    assert M.structural_shop_reason(run, 12, M.AUDIT.catalog()) == "SHOP_LOG_MISSING_OR_DUPLICATE"
    run = copy.deepcopy(group["run"])
    assert M.structural_shop_reason(run, 12, M.AUDIT.catalog()) == "SHOP_CARD_SELECTION_MISSING"
    event_group = next(group for group in groups if group["source_path"].endswith("1663019150.run"))
    run = copy.deepcopy(event_group["run"])
    run["event_choices"] = []
    assert M.structural_event_reason(run, 4) == "EVENT_LOG_MISSING"
    assert result["summary"]["failure_group_counts"]["POTION_AUTO_USE_OR_GENERATION_PENDING"] == 10


def test_unsupported_entities_are_retained_with_all_blockers(result):
    rows = [row for row in result["scenes"] if row["candidate"] is not None and row["backend_blockers"]]
    assert rows
    found_unsupported = False
    for row in rows:
        candidate = row["candidate"]
        card_bases = {M.AUDIT.card_base(card) for card in candidate["deck"]}
        potions = {potion for potion in candidate["potions"] if potion is not None}
        relics = set(candidate["relics"])
        for blocker in row["backend_blockers"]:
            if blocker.startswith("UNSUPPORTED_CARD:"):
                found_unsupported = True
                assert set(blocker.split(":", 1)[1].split(",")) <= card_bases
            elif blocker.startswith("UNSUPPORTED_RELIC:"):
                found_unsupported = True
                assert set(blocker.split(":", 1)[1].split(",")) <= relics
            elif blocker.startswith("UNSUPPORTED_OR_CHOICE_POTION:"):
                found_unsupported = True
                assert set(blocker.split(":", 1)[1].split(",")) <= potions
    assert found_unsupported


def test_master_deck_mutation_does_not_change_reconstruction():
    records = M.AUDIT.load_records((ROOT / "reference/public-run-corpus/matiger-fixed.zip").read_bytes())
    group = next(group for group in M.AUDIT.group_records(records) if group["source_path"].endswith("1667161552.run"))
    counters: Counter[str] = Counter()
    failure_groups: defaultdict[str, set[str]] = defaultdict(set)
    before, status, _ = M.expand_group(group, M.AUDIT.catalog(), counters, failure_groups)
    changed = copy.deepcopy(group)
    changed["run"]["master_deck"] = ["Invented Card", "Invented Card"]
    counters = Counter()
    failure_groups = defaultdict(set)
    after, _, _ = M.expand_group(changed, M.AUDIT.catalog(), counters, failure_groups)
    before_map = {row["scene_id"]: row["candidate"] for row in before}
    after_map = {row["scene_id"]: row["candidate"] for row in after}
    assert before_map and before_map == after_map
    assert status


def test_six_priority_cards_are_tracked_without_relaxing_admission(result):
    tracking = result["special_card_tracking"]
    assert set(tracking) == {"Dropkick", "Entrench", "Rage", "Sentinel", "Thunderclap", "True Grit"}
    expected_runs = {"Dropkick": 6, "Entrench": 2, "Rage": 8, "Sentinel": 1, "Thunderclap": 1, "True Grit": 1}
    for card, count in expected_runs.items():
        assert tracking[card]["runs_with_act1_pick"] == count
        assert isinstance(tracking[card]["failure_reasons"], dict)
    assert tracking["Dropkick"]["later_battles_after_pick"] == 12
    assert tracking["Rage"]["later_battles_backend_admissible"] == 0


def test_source_hashes_and_fixed_archive_policy_are_recorded(result):
    assert result["source_archive_sha256"] == M.AUDIT.ZIP_SHA
    assert result["source_evidence"]["fixed_archives"][0]["sha256"] == M.AUDIT.ZIP_SHA
    assert result["source_evidence"]["input_files"][0]["path"] == "docs/m2-corpus-index.json"
    assert result["source_evidence"]["input_files"][-1]["path"] == "sts/env/public-battle-contract.json"
    assert result["contract_id"] == "public-battle-v1"
    assert result["reconstruction_policy"]["backend_support_source"].startswith("sts/env/public-battle-contract.json")
    assert result["reconstruction_policy"]["historical_rules_equivalence"] == "unverified"
    assert result["reconstruction_policy"]["do_not_delete_or_replace_source_content"] is True


def test_contract_controls_upgrade_and_content_support_without_a_second_allowlist():
    contract = M.load_contract()
    candidate = {
        "deck": ["Bash+2", "Dropkick"], "relics": [],
        "potions": [None, None], "encounter": "CULTIST",
    }
    blockers = M.backend_blockers(candidate, contract)
    assert "UNSUPPORTED_CARD_UPGRADE:Bash+2:max=1" in blockers
    assert not any(blocker.startswith("UNSUPPORTED_CARD:Dropkick") for blocker in blockers)
    altered = copy.deepcopy(contract)
    altered["cards"] = [item for item in altered["cards"] if item["name"] != "Dropkick"]
    assert "UNSUPPORTED_CARD:Dropkick" in M.backend_blockers(candidate, altered)
