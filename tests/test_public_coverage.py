"""公开场景覆盖分析的离线回归。"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/analyze-public-coverage.py"
SPEC = importlib.util.spec_from_file_location("public_coverage_analysis", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run_analysis():
    return MODULE.analyze(
        index_path=ROOT / "docs/m2-corpus-index.json",
        manifest_path=ROOT / "docs/m2-public-scene-manifest.json",
        contract_path=ROOT / "sts/env/public-battle-contract.json",
        implementation_report_path=ROOT / "docs/public-battle-implementation.md",
        integration_path=ROOT / "reference/public-scene-integration.json",
    )


def by_value(items):
    return {item["value"]: item for item in items}


def base_documents():
    index, _ = MODULE.read_json(ROOT / "docs/m2-corpus-index.json")
    manifest, _ = MODULE.read_json(ROOT / "docs/m2-public-scene-manifest.json")
    return index, manifest


def scene_with(predicate):
    index, _ = base_documents()
    return next(scene for scene in index["scenes"] if predicate(scene))


def manifest_scene(scene_id):
    _, manifest = base_documents()
    return next(scene for scene in manifest["scenes"] if scene["scene_id"] == scene_id)


def external_record(scene, *, candidate=None, **values):
    record = {
        "scene_id": scene["scene_id"],
        "group_id": "external-label-do-not-trust",
        "source_path": scene["source_path"],
        "raw_sha256": scene["raw_sha256"],
        "source_seed": scene["source_seed"],
        "floor": scene["floor"],
        "encounter_label": scene["encounter_label"],
        "target_battle_record_present": True,
    }
    if candidate is not None:
        record["candidate"] = copy.deepcopy(candidate)
    record.update(values)
    return record


def test_four_layer_denominators_and_weights_are_explicit():
    analysis, priorities, graph = run_analysis()
    counts = analysis["layer_counts"]
    assert counts["all_independent_runs"] == {
        "raw_file_count": 203,
        "independent_run_count": 157,
        "linked_act1_combat_row_count": 1282,
    }
    assert counts["all_act1_combat_rows"]["scene_count"] == 1282
    assert counts["all_act1_combat_rows"]["independent_run_count"] == 157
    assert counts["rule_constructible_candidates"] == {
        "scene_count": 257,
        "independent_run_count": 118,
    }
    assert counts["current_99_executable"]["scene_count"] == 99
    assert counts["current_99_executable"]["independent_run_count"] == 75
    assert counts["current_99_executable"]["actual_net_new_scene_count_vs_original_99"] == 0
    assert analysis["candidate_counts"]["raw_researchable_combat_rows"]["scene_count"] == 1282
    assert analysis["candidate_counts"]["evidence_complete_rule_candidates"]["scene_count"] == 257
    assert analysis["candidate_counts"]["current_backend_accessible_scenes"]["scene_count"] == 99
    assert analysis["layers"]["all_act1_combat_rows"]["weights"]["scene_weight"] == 1 / 1282
    assert analysis["layers"]["current_99_executable"]["weights"]["scene_weight"] == 1 / 99
    assert priorities["baseline"]["actual_net_new_scene_count_vs_baseline_99"] == 0
    assert graph["scene_count"] == 1282


def test_floor_and_encounter_selection_bias_is_not_hidden():
    analysis, _, _ = run_analysis()
    all_layer = analysis["layers"]["all_act1_combat_rows"]
    current_layer = analysis["layers"]["current_99_executable"]
    all_floor = by_value(all_layer["distributions"]["floor"])
    current_floor = by_value(current_layer["distributions"]["floor"])
    assert set(all_floor) == {1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14}
    assert set(current_floor) == {1, 2, 3, 4, 5}
    assert sum(item["scene_count"] for item in current_floor.values()) == 99
    assert current_floor[1]["scene_count"] == 75
    assert current_floor[5]["scene_count"] == 1
    assert all_floor[6]["scene_count"] == 80
    assert all_floor[14]["scene_count"] == 130

    all_encounter = by_value(all_layer["distributions"]["encounter_label"])
    current_encounter = by_value(current_layer["distributions"]["encounter_label"])
    assert len(all_encounter) == 18
    assert len(current_encounter) == 6
    assert by_value(all_layer["distributions"]["encounter_tier"])["elite"]["scene_count"] == 425
    assert by_value(current_layer["distributions"]["encounter_tier"]).get("elite", {"scene_count": 0})["scene_count"] == 0
    assert "3 Louse" not in current_encounter


def test_entry_fields_are_missing_independently_and_final_deck_is_not_used():
    analysis, _, _ = run_analysis()
    for layer_id, expected in {
        "all_independent_runs": (118, 157),
        "all_act1_combat_rows": (257, 1282),
        "rule_constructible_candidates": (257, 257),
        "current_99_executable": (99, 99),
    }.items():
        availability = analysis["layers"][layer_id]["entry"]["field_availability"]
        assert (availability["feature_row_count"], availability["denominator_row_count"]) == expected
        assert availability["final_master_deck_used"] is False
        for field in MODULE.ENTRY_FIELD_NAMES:
            assert availability["fields"][field]["available_row_count"] == expected[0]

    b_missing = analysis["layers"]["all_act1_combat_rows"]["entry"]["field_availability"]["missing_reason_counts"]
    assert sum(item["row_count"] for item in b_missing) == 1025
    a_missing = analysis["layers"]["all_independent_runs"]["entry"]["field_availability"]["missing_reason_counts"]
    assert sum(item["row_count"] for item in a_missing) == 39
    assert analysis["policies"]["final_master_deck_used"] is False


def test_content_stats_preserve_multisets_upgrades_relics_and_potions():
    analysis, _, _ = run_analysis()
    candidate_stats = analysis["layers"]["rule_constructible_candidates"]["entry"]["stats"]
    current_stats = analysis["layers"]["current_99_executable"]["entry"]["stats"]
    assert candidate_stats["denominator"] == 257
    assert candidate_stats["deck"]["unique_multiset_count"] == 160
    assert candidate_stats["deck"]["unique_initial_card_class_count"] == 72
    assert candidate_stats["deck"]["upgraded_scene_count"] == 18
    assert candidate_stats["relics"]["unique_class_count"] == 5
    assert candidate_stats["potions"]["nonempty_scene_count"] == 75
    assert candidate_stats["potions"]["unique_class_count"] == 27
    assert current_stats["denominator"] == 99
    assert current_stats["deck"]["unique_multiset_count"] == 27
    assert current_stats["deck"]["unique_initial_card_class_count"] == 22
    assert current_stats["deck"]["upgraded_scene_count"] == 7
    assert current_stats["potions"]["nonempty_scene_count"] == 7
    assert current_stats["potions"]["unique_class_count"] == 5
    assert current_stats["potions"]["nonempty_scene_share"] == 7 / 99


def test_group_dedup_and_development_touch_boundary_are_explicit():
    analysis, _, _ = run_analysis()
    dedup = analysis["cross_source_dedup_audit"]
    assert dedup["raw_file_count"] == 203
    assert dedup["independent_run_count"] == 157
    assert dedup["duplicate_alias_file_count"] == 46
    assert dedup["conflicting_groups"] == 0
    assert dedup["groups_with_multiple_aliases"] == 46
    assert dedup["cross_collection_alias_groups"] == 0
    assert dedup["play_id_duplicate_across_groups"] is False
    assert analysis["backend_integration"]["status"] == "development_integration_only"
    assert analysis["backend_integration"]["current_scene_ids_all_completed"] is True
    assert analysis["sampling_plan"]["current_99_touched_by_development_integration"] is True
    assert "reserved-eval" in analysis["sampling_plan"]["reserved_eval_warning"]


def test_blocker_overlap_and_yield_dedup_are_non_additive():
    analysis, priorities, graph = run_analysis()
    summary = graph["summary"]
    assert summary["current_executable_scene_count"] == 99
    assert summary["source_or_prefix_incomplete_scene_count"] == 1025
    assert summary["evidence_complete_content_blocked_scene_count"] == 158
    inventory = {item["category"]: item for item in summary["dependency_category_inventory"]}
    assert inventory["capacity_action_protocol"]["scene_count"] == 0
    assert inventory["secondary_choice_or_copy_generation"]["scene_count"] == 0
    assert analysis["candidate_yields"]["content_overlap_scene_count"] == 73
    assert analysis["candidate_yields"]["content_card_and_potion_overlap_scene_count"] == 26
    singles = {tuple(item["support_atoms"]): item for item in analysis["candidate_yields"]["single_implementation_items"]}
    assert singles[("card:Anger",)]["exact_single_dependency_scene_count"] == 8
    assert singles[("card:Anger",)]["potential_scene_count_containing_atom"] == 23
    assert singles[("potion:PowerPotion",)]["exact_single_dependency_scene_count"] == 3
    assert singles[("potion:PowerPotion",)]["potential_scene_count_containing_atom"] == 7
    joint = next(
        item
        for item in analysis["candidate_yields"]["minimal_joint_dependencies"]
        if tuple(item["support_atoms"]) == ("card:Hemokinesis", "card:Shockwave")
    )
    assert joint["scene_count"] == 3
    assert joint["support_closure_scene_count"] == 13
    assert joint["minimal_independent_run_count"] == 1
    # 不允许把每个 blocker 的场景数直接相加成场景收益。
    assert summary["overlap_warning"]
    assert priorities["ordering"]["not_used"]


def test_priority_batches_are_concrete_and_do_not_claim_implementation():
    analysis, priorities, _ = run_analysis()
    batches = {batch["id"]: batch for batch in priorities["recommended_batches"]}
    assert set(batches) == {"direct-state-cards", "hand-copy-secondary", "direct-generated-potions"}
    assert batches["direct-state-cards"]["projected_complete_scene_gain"]["scene_count"] == 17
    assert batches["hand-copy-secondary"]["projected_complete_scene_gain"]["scene_count"] == 20
    assert batches["direct-generated-potions"]["projected_complete_scene_gain"]["scene_count"] == 4
    for batch in batches.values():
        gain = batch["projected_complete_scene_gain"]
        assert len(gain["scene_ids"]) == gain["scene_count"]
        assert batch["not_actual_implementation"] is True
        assert batch["uses_policy_outcome"] is False
        assert gain["selection_by_policy_outcome"] is False
    assert priorities["mandatory_source_evidence_gate"]["potential_only"] is True
    assert priorities["mandatory_source_evidence_gate"]["definite_complete_scene_gain"] == 0
    assert analysis["layer_counts"]["current_99_executable"]["actual_net_new_scene_count_vs_original_99"] == 0


def test_external_same_scene_and_alias_merge_does_not_duplicate_runs():
    index, manifest = base_documents()
    old = next(scene for scene in manifest["scenes"] if scene["content_admission_status"] == "accepted")
    old_source = next(scene for scene in index["scenes"] if scene["scene_id"] == old["scene_id"])
    duplicate = external_record(
        old_source,
        candidate=old["candidate"],
        source_prefix_complete=True,
        target_battle_evidence_complete=True,
        static_content_passed=True,
        actual_run_verified=True,
        formal_manifest=False,
    )
    merged = MODULE.merge_external_inputs(
        index["scenes"],
        manifest["scenes"],
        index["groups"],
        [{"kind": "prefix_candidates", "data": [duplicate]}],
    )
    assert merged["summary"]["merged_scene_count"] == 1282
    assert merged["summary"]["same_scene_duplicate_record_count"] >= 1
    assert merged["summary"]["content_conflict_scene_count"] == 0
    assert merged["summary"]["merged_resolved_run_count"] == 157
    merged_old = next(row for row in merged["scene_rows"] if row["scene_id"] == old["scene_id"])
    assert merged_old["canonical_run_id"] == old["group_id"]
    assert merged_old["entry_evidence_complete"] is True
    assert merged_old["formal_manifest"] is False

    normal_by_group = {}
    for scene in index["scenes"]:
        if scene["encounter_label"] not in MODULE.ELITE_ENCOUNTERS:
            normal_by_group.setdefault(scene["group_id"], []).append(scene)
    normal_rows = next(
        rows
        for rows in normal_by_group.values()
        if len(rows) >= 2
    )
    normal_rows = sorted(normal_rows, key=lambda item: item["floor"])[:2]
    assert normal_rows[0]["floor"] != normal_rows[1]["floor"]
    alias_records = [
        external_record(
            scene,
            scene_id=f"different-group-label:floor-{scene['floor']}:combat-0",
            group_id=f"different-group-{scene['floor']}",
            candidate=None,
            target_battle_record_present=True,
        )
        for scene in normal_rows
    ]
    merged_aliases = MODULE.merge_external_inputs(
        index["scenes"],
        manifest["scenes"],
        index["groups"],
        [{"kind": "prefix_candidates", "data": alias_records}],
    )
    alias_run_ids = {
        row["canonical_run_id"]
        for row in merged_aliases["scene_rows"]
        if row["scene_id"] in {scene["scene_id"] for scene in normal_rows}
    }
    assert len(alias_run_ids) == 1
    assert merged_aliases["summary"]["merged_resolved_run_count"] == 157


def test_external_content_conflict_is_preserved_and_blocks_entry():
    index, manifest = base_documents()
    old = next(scene for scene in manifest["scenes"] if scene["content_admission_status"] == "accepted")
    old_source = next(scene for scene in index["scenes"] if scene["scene_id"] == old["scene_id"])
    conflicting_candidate = copy.deepcopy(old["candidate"])
    conflicting_candidate["deck"] = list(conflicting_candidate["deck"][:-1]) + ["Cleave"]
    conflict = external_record(
        old_source,
        candidate=conflicting_candidate,
        source_prefix_complete=True,
        target_battle_evidence_complete=True,
        static_content_passed=True,
    )
    merged = MODULE.merge_external_inputs(
        index["scenes"],
        manifest["scenes"],
        index["groups"],
        [{"kind": "prefix_candidates", "data": [conflict]}],
    )
    row = next(item for item in merged["scene_rows"] if item["scene_id"] == old["scene_id"])
    assert merged["summary"]["content_conflict_scene_count"] >= 1
    assert row["content_conflict"] is True
    assert len(row["candidate_variants"]) == 2
    assert row["entry_evidence_complete"] is False
    assert row["primary_state"] == "conflict_rejected"


def test_unknown_burning_elite_never_enters_definite_gain():
    index, manifest = base_documents()
    elite = next(scene for scene in index["scenes"] if scene["encounter_label"] == "Gremlin Nob")
    template = next(scene for scene in manifest["scenes"] if scene["content_admission_status"] == "accepted")
    record = external_record(
        elite,
        candidate=template["candidate"],
        source_prefix_complete=True,
        target_battle_evidence_complete=True,
        static_content_passed=True,
        # 故意不提供 burning_elite；未知值必须阻断。
    )
    merged = MODULE.merge_external_inputs(
        index["scenes"],
        manifest["scenes"],
        index["groups"],
        [{"kind": "prefix_candidates", "data": [record]}],
    )
    row = next(item for item in merged["scene_rows"] if item["scene_id"] == elite["scene_id"])
    assert "BURNING_ELITE_MODIFIER_UNRECORDED" in row["source_blockers"]
    assert row["entry_evidence_complete"] is False
    assert row["static_content_passed"] is False
    assert row["primary_state"] != "static_content_passed"
    assert not any(
        item["scene_id"] == elite["scene_id"]
        for item in merged["new_scene_rows"]
        if item.get("entry_evidence_complete")
    )


def test_state_lattice_separates_target_incomplete_static_runtime_and_formal():
    index, manifest = base_documents()
    normal = next(
        scene
        for scene in index["scenes"]
        if scene["candidate"] is None and scene["encounter_label"] not in MODULE.ELITE_ENCOUNTERS
    )
    template = next(scene for scene in manifest["scenes"] if scene["content_admission_status"] == "accepted")
    target_pending = external_record(
        normal,
        candidate=template["candidate"],
        source_prefix_complete=True,
        target_battle_evidence_complete=False,
        static_content_status="pending",
        target_battle_status="snapshot_only",
    )
    verified = external_record(
        normal,
        candidate=template["candidate"],
        source_prefix_complete=True,
        target_battle_evidence_complete=True,
        static_content_status="passed",
        actual_run_verified=True,
        formal_manifest=False,
    )
    pending_merge = MODULE.merge_external_inputs(
        index["scenes"],
        manifest["scenes"],
        index["groups"],
        [{"kind": "prefix_candidates", "data": [target_pending]}],
    )
    pending = next(item for item in pending_merge["scene_rows"] if item["scene_id"] == normal["scene_id"])
    assert pending["entry_evidence_complete"] is False
    assert pending["primary_state"] == "entry_content_prefix_recoverable_target_incomplete"

    verified_merge = MODULE.merge_external_inputs(
        index["scenes"],
        manifest["scenes"],
        index["groups"],
        [{"kind": "prefix_candidates", "data": [verified]}],
    )
    verified_row = next(item for item in verified_merge["scene_rows"] if item["scene_id"] == normal["scene_id"])
    assert verified_row["entry_evidence_complete"] is True
    assert verified_row["static_content_passed"] is True
    assert verified_row["actual_run_verified"] is True
    assert verified_row["formal_manifest"] is False
    assert verified_row["primary_state"] == "actual_run_verified"


def test_external_hash_gate_keeps_final_statistics_pending_until_both_inputs_arrive(tmp_path):
    prefix = tmp_path / "prefix.json"
    prefix.write_text("[]\n", encoding="utf-8")
    actual_hash = MODULE.sha256_bytes(prefix.read_bytes())
    analysis, priorities, _ = MODULE.analyze(
        index_path=ROOT / "docs/m2-corpus-index.json",
        manifest_path=ROOT / "docs/m2-public-scene-manifest.json",
        contract_path=ROOT / "sts/env/public-battle-contract.json",
        implementation_report_path=ROOT / "docs/public-battle-implementation.md",
        integration_path=ROOT / "reference/public-scene-integration.json",
        prefix_candidates_path=prefix,
        prefix_sha256=actual_hash,
        elite_audit_path=None,
    )
    assert analysis["external_merge"]["final_statistics_ready"] is False
    assert "ELITE_AUDIT_INPUT_MISSING" in analysis["external_merge"]["final_statistics_blockers"]
    assert "expanded" not in analysis
    assert priorities["mode"] == "baseline_with_external_inputs_pending"
    assert analysis["layer_counts"]["current_99_executable"]["actual_net_new_scene_count_vs_original_99"] == 0


def test_dynamic_priority_mode_uses_merged_input_and_not_old_fixed_batches(tmp_path):
    prefix = tmp_path / "prefix.json"
    elite = tmp_path / "elite.json"
    prefix.write_text("[]\n", encoding="utf-8")
    elite.write_text("[]\n", encoding="utf-8")
    prefix_hash = MODULE.sha256_bytes(prefix.read_bytes())
    elite_hash = MODULE.sha256_bytes(elite.read_bytes())
    analysis, priorities, _ = MODULE.analyze(
        index_path=ROOT / "docs/m2-corpus-index.json",
        manifest_path=ROOT / "docs/m2-public-scene-manifest.json",
        contract_path=ROOT / "sts/env/public-battle-contract.json",
        implementation_report_path=ROOT / "docs/public-battle-implementation.md",
        integration_path=ROOT / "reference/public-scene-integration.json",
        prefix_candidates_path=prefix,
        prefix_sha256=prefix_hash,
        elite_audit_path=elite,
        elite_sha256=elite_hash,
    )
    assert analysis["external_merge"]["final_statistics_ready"] is True
    assert analysis["expanded"]["counts"]["merged_entry_evidence_complete_scene_count"] == 257
    assert analysis["expanded"]["counts"]["current_99_scene_count_unchanged"] == 99
    assert priorities["mode"] == "expanded_dynamic"
    assert priorities["recommended_batches"]
    assert all(batch["id"].startswith("dynamic-") for batch in priorities["recommended_batches"])
    assert priorities["ordering"]["not_used"]


def test_script_output_is_deterministic(tmp_path):
    analysis, priorities, graph = run_analysis()
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(
        json.dumps(
            {"analysis": analysis, "priorities": priorities, "graph": graph},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    analysis2, priorities2, graph2 = run_analysis()
    second.write_text(
        json.dumps(
            {"analysis": analysis2, "priorities": priorities2, "graph": graph2},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    assert first.read_bytes() == second.read_bytes()
