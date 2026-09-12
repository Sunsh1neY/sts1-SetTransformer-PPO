"""公开精英来源审计器的边界测试。"""

import importlib.util
import io
import json
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts/audit-public-elite-sources.py"
SPEC = importlib.util.spec_from_file_location("public_elite_sources", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(AUDIT)


def summary_group():
    run = {
        "character_chosen": "IRONCLAD",
        "ascension_level": 20,
        "build_version": "2022-12-18",
        "play_id": "p1",
        "seed_played": "s1",
        "path_per_floor": ["M", "M", "M", "M", "M", "E"],
        "green_key_taken_log": 6,
        "damage_taken": [],
    }
    return {
        "group_id": "matiger-run-group:test",
        "canonical": {"source_path": "runs/a.run", "raw_sha256": "h1", "run": run},
        "aliases": ["runs/a.run"],
        "raw_sha256s": ["h1"],
        "identity_tokens": ["play_id:p1", "seed:s1", "sha:h1"],
        "conflicting_variants": False,
    }


def runlogger_state():
    return {
        "_type": "state:floor",
        "floor": 7,
        "room_type": "MonsterRoomElite",
        "deck": ["Strike_R", "Defend_R", "Bash", "Uppercut+1"],
        "hp_current": 70,
        "hp_max": 75,
        "gold": 123,
        "relics": [
            {"id": "Burning Blood"},
            {"id": "NeowsBlessing"},
            {"counter": 1, "id": "StoneCalendar"},
        ],
        "potions": ["Weak Potion", None, None],
        "screen_state": {},
        "combat_state": {
            "draw_pile": ["Defend_R"],
            "hand": ["Bash", "Strike_R"],
            "monsters": [
                {"id": "GremlinNob", "hp_current": 85, "hp_max": 85, "intent": "BUFF"}
            ],
            "player": {"energy": 3},
        },
    }


def test_summary_elite_keeps_burning_unknown_even_when_key_floor_matches():
    group = summary_group()
    event = {"damage": 20, "enemies": "Gremlin Nob", "floor": 6, "turns": 4}
    scene = AUDIT.summary_event_record(
        source_kind="github-run-summary",
        source_url="https://example.invalid/run",
        group=group,
        event_index=0,
        event=event,
    )

    assert scene["burning_evidence"]["ordinary"] is None
    assert scene["burning_evidence"]["burning"] is None
    assert scene["burning_evidence"]["same_floor_key_observation"] is True
    assert "master_deck" in scene["entry_a"]["do_not_substitute"]
    assert scene["entry_a"]["status"] == "not_directly_recorded_derivable_with_verified_prefix"
    assert scene["entry_b"]["status"] == "not_available_in_summary_source"
    assert "BURNING_ELITE_FLAG_AND_STRENGTHENING_TYPE_UNRECORDED" in scene[
        "rejection_reasons"
    ]


def test_runlogger_b_snapshot_keeps_all_content_and_proves_a0_not_burning():
    run_state = {
        "_type": "state:run",
        "class": "IRONCLAD",
        "ascension_level": 0,
        "seed": "TEST-SEED",
        "unlocks": {"final_act": False},
        "versions": {"sts": "12-18-2022"},
    }
    scene = AUDIT.runlogger_scene(
        run_state=run_state,
        floor_state=runlogger_state(),
        predecessor={"_type": "action:select_map", "symbol": "E"},
        source_line=49,
        act=1,
        all_floor_states=[runlogger_state()],
        source_hash="raw-hash",
    )

    assert scene["entry_a"]["status"] == "not_available"
    assert scene["entry_b"]["status"] == "visible_snapshot_complete"
    assert scene["entry_b"]["deck"][-1] == "Uppercut+1"
    assert scene["entry_b"]["relics"][1]["id"] == "NeowsBlessing"
    assert scene["entry_b"]["relics"][2]["counter"] == 1
    assert scene["entry_b"]["potions"] == ["Weak Potion", None, None]
    assert "deck card display strings" in scene["entry_b"]["field_audit"]["direct_recorded"]
    assert "card current cost, per-copy uuid and runtime display attributes beyond name/+ string" in scene[
        "entry_b"
    ]["field_audit"]["visible_dynamic_missing"]
    assert scene["entry_b"]["piles"]["discard_pile"]["items"] == []
    assert (
        scene["entry_b"]["piles"]["discard_pile"]["evidence"]
        == "serializer_conditional_field_absent_proves_empty"
    )
    assert scene["burning_evidence"]["ordinary"] is True
    assert scene["burning_evidence"]["burning"] is False
    assert scene["burning_evidence"]["strengthening_type"] == "not_applicable"
    assert scene["evidence_complete_for_public_B"] is True
    assert scene["current_backend_admissible"] is False
    assert "NeowsBlessing,StoneCalendar" in scene["rejection_reasons"][2]


def test_group_records_deduplicates_aliases_and_preserves_conflicts():
    base = {
        "run": {"play_id": "p", "seed_played": "s"},
        "raw_sha256": "h",
    }
    aliases = [
        {**base, "source_path": "a.run"},
        {**base, "source_path": "b.run"},
    ]
    groups = AUDIT.group_records(aliases, "test")
    assert len(groups) == 1
    assert groups[0]["aliases"] == ["a.run", "b.run"]
    assert not groups[0]["conflicting_variants"]

    conflict = [
        {**base, "source_path": "a.run"},
        {**base, "source_path": "b.run", "raw_sha256": "different"},
    ]
    assert AUDIT.group_records(conflict, "test")[0]["conflicting_variants"]


def test_predictor_derived_rows_are_counted_but_have_no_run_identity():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
        rows = [
            {
                "cards": ["Strike_R"],
                "relics": ["Burning Blood"],
                "max_hp": 75,
                "entering_hp": 60,
                "character": "IRONCLAD",
                "ascension": 20,
                "enemies": "Gremlin Nob",
                "potion_used": False,
                "floor": 7,
                "damage_taken": 12,
            }
        ]
        bundle.writestr(
            "root/out/one.json", json.dumps(rows, ensure_ascii=False)
        )
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as bundle:
        result = AUDIT.count_predictor_outputs(bundle, "root/")

    assert result["row_count"] == 1
    assert result["ironclad_act1_elite_row_count"] == 1
    assert result["sample_row_has_run_identity"] is False


def test_conditional_empty_pile_is_not_unknown_or_guessed():
    result = AUDIT.conditional_pile(
        {}, "discard_pile", source_semantics="serializer_conditional_field_absent_proves_empty"
    )
    assert result == {
        "items": [],
        "evidence": "serializer_conditional_field_absent_proves_empty",
    }


def test_prefix_crosswalk_uses_raw_sha_floor_and_label_not_group_id(tmp_path):
    prefix_file = tmp_path / "prefix.json"
    prefix_file.write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "scene_id": "different-group-format:7",
                        "group_id": "different-group-format",
                        "source_path": "runs/a.run",
                        "raw_sha256": "ABC",
                        "source_seed": "seed",
                        "floor": 7,
                        "encounter_label": "Gremlin Nob",
                        "prefix_touched": True,
                        "prefix_types": ["event"],
                        "raw_research_candidate": True,
                        "evidence_complete": True,
                        "backend_admissible": True,
                        "evidence_blockers": [],
                        "state_evidence_blockers": [],
                        "backend_blockers": [],
                        "prefix_evidence_chain": [{"floor": 1, "status": "applied"}],
                        "candidate": {
                            "potion_slot_policy": "canonical-inventory-slots-v1",
                            "resampling_policy": "public-battle-a-resample-v1",
                            "exact_historical_replay": False,
                            "deck": ["Bash"],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    original = AUDIT.PREFIX_CANDIDATES
    AUDIT.PREFIX_CANDIDATES = prefix_file
    try:
        summary = {
            "candidate_id": "summary-event",
            "source_path": "runs/a.run",
            "raw_sha256": "abc",
            "source_seed": "seed",
            "floor": 7,
            "encounter_label": "Gremlin Nob",
            "source_run_group": "source-group-format",
            "source_run_id": "play",
            "source_url": "https://example.invalid/a.run",
            "burning_evidence": {
                "ordinary": None,
                "burning": None,
                "strengthening_type": None,
                "elite_room_path_symbol": "E",
            },
        }
        rows, stats = AUDIT.build_prefix_crosswalk([summary])
    finally:
        AUDIT.PREFIX_CANDIDATES = original

    assert stats["source_index_matched_row_count"] == 1
    assert rows[0]["source_index_match"]["raw_sha_match"]
    assert rows[0]["source_index_match"]["source_path_match"]
    assert rows[0]["burning_and_strengthening"]["final_burning"] is None
    assert rows[0]["current_backend"]["final_backend_admissible"] is False
    assert rows[0]["final_status"] == "prefix_static_backend_claim_withdrawn_burning_unknown"
