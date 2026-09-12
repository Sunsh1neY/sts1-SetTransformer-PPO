"""M2 公开数据审计工具的合成失败路径与成功路径测试。"""

from __future__ import annotations

import importlib.util
import io
import json
import ssl
import zipfile
from pathlib import Path
from urllib.error import URLError

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit-public-runs.py"
SPEC = importlib.util.spec_from_file_location("audit_public_runs", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def _recorded_log(
    *,
    predecessor_type: str = "action:select_map",
    include_potions: bool = True,
    draw: list[str] | None = None,
    relics: list[dict[str, object]] | None = None,
    include_versions: bool = True,
    duplicate_floor_state: bool = False,
) -> bytes:
    """构造小型日志；它只用于验证工具行为，不作为真实数据证据。"""

    run: dict[str, object] = {
        "_type": "state:run",
        "class": "IRONCLAD",
        "seed": "synthetic-seed",
        "ascension": 0,
        "mods": {},
    }
    if include_versions:
        run["versions"] = {"sts": "12-18-2022"}
    floor: dict[str, object] = {
        "_type": "state:floor",
        "floor": 1,
        "room_type": "MonsterRoom",
        "hp_current": 80,
        "hp_max": 80,
        "deck": ["Strike_R", "Defend_R", "Bash"],
        "relics": relics if relics is not None else [{"id": "Burning Blood"}],
        "combat_state": {
            "hand": ["Strike_R"],
            "draw_pile": draw if draw is not None else ["Defend_R", "Bash"],
            "monsters": [
                {
                    "id": "Cultist",
                    "hp_current": 48,
                    "hp_max": 48,
                    "intent": "BUFF",
                }
            ],
            "player": {"energy": 3},
        },
    }
    if include_potions:
        floor["potions"] = [None, None, None]
    records: list[dict[str, object]] = [run, {"_type": predecessor_type}, floor]
    if duplicate_floor_state:
        records.append(dict(floor))
    return "\n".join(json.dumps(record) for record in records).encode("utf-8")


def _audit_log(raw: bytes) -> dict[str, object]:
    return AUDIT.audit_runlogger_log(
        raw,
        source_id="synthetic",
        source_url="https://example.invalid/synthetic.jsonl",
        raw_hash=AUDIT.sha256_bytes(raw),
    )


def test_fetch_retries_and_keeps_certificate_validation(monkeypatch: pytest.MonkeyPatch):
    calls: list[ssl.SSLContext] = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"ok"

    def fake_urlopen(_request, *, timeout, context):
        assert timeout == 3
        calls.append(context)
        if len(calls) == 1:
            raise URLError("temporary EOF")
        return Response()

    monkeypatch.setattr(AUDIT, "urlopen", fake_urlopen)
    assert AUDIT.fetch("https://example.invalid/data", timeout=3, attempts=2, sleeper=lambda _delay: None) == b"ok"
    assert len(calls) == 2
    assert all(context.verify_mode == ssl.CERT_REQUIRED for context in calls)
    assert all(context.check_hostname for context in calls)


def test_select_sample_paths_is_deterministic_stratified_and_not_random():
    paths = [
        "runs/a/3.run",
        "runs/b/2.run",
        "runs/a/1.run",
        "runs/c/1.run",
        "runs/b/1.run",
    ]
    assert AUDIT.select_sample_paths(paths, 5) == [
        "runs/a/1.run",
        "runs/b/1.run",
        "runs/c/1.run",
        "runs/a/3.run",
        "runs/b/2.run",
    ]


def test_duplicate_run_group_is_rejected_before_split():
    with pytest.raises(ValueError, match="run group"):
        AUDIT.assign_group_split(["same-run", "same-run"])


def test_same_source_seed_stays_one_group_across_public_sources():
    assert AUDIT.run_group_key("IRONCLAD", "123", "summary") == AUDIT.run_group_key(
        "IRONCLAD", "123", "detailed"
    )


def test_codeload_fallback_reads_fixed_commit_tree_without_api():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Slay-the-Spire-data-abc/runs/IRONCLAD/a.run", b"{}")
        archive.writestr("Slay-the-Spire-data-abc/README.md", b"readme")

    paths, metadata = AUDIT.github_tree_from_codeload(
        "MaT1g3R/Slay-the-Spire-data",
        "abc",
        lambda _url: buffer.getvalue(),
    )
    assert paths == ["README.md", "runs/IRONCLAD/a.run"]
    assert metadata["method"] == "github-codeload-zip"
    assert metadata["path_count"] == 2


def test_duplicate_floor_records_are_grouped_as_one_scene():
    result = _audit_log(_recorded_log(duplicate_floor_state=True))
    assert result["scene_count"] == 1
    assert result["run"]["group_key"] == "seed:IRONCLAD:synthetic-seed"


def test_missing_summary_fields_are_explicitly_non_reconstructable():
    row = AUDIT.audit_summary_run(
        {"character_chosen": "IRONCLAD"},
        "runs/example.run",
        "hash",
    )
    assert row["reconstruction"]["status"] == "not_reconstructable_from_summary"
    assert "build_version" in row["missing_fields"]
    assert "NO_EARLY_COMBAT_ROW" in row["reconstruction"]["reason_codes"]
    assert "B_HAND_PILES_MISSING" in row["reconstruction"]["attempted_modes"]["B_post_combat_initialization_after_initial_draw"]["missing_or_ambiguous"]


def test_summary_attempts_entry_a_and_keeps_neow_and_hp_evidence():
    run = {
        "character_chosen": "IRONCLAD",
        "ascension_level": 20,
        "build_version": "2022-12-18",
        "seed_played": "source-seed",
        "play_id": "run-id",
        "damage_taken": [{"floor": 1, "enemies": "Cultist", "damage": 2, "turns": 3}],
        "current_hp_per_floor": [70],
        "max_hp_per_floor": [75],
        "neow_bonus": "NONE",
        "neow_cost": "NONE",
        "neow_bonus_log": {
            "cardsObtained": [],
            "cardsUpgraded": [],
            "cardsRemoved": [],
            "cardsTransformed": [],
            "relicsObtained": [],
        },
        "card_choices": [{"floor": 1, "picked": "Strike"}],
        "event_choices": [],
        "campfire_choices": [],
        "relics": ["Burning Blood"],
        "relics_obtained": [],
        "relic_stats": {},
        "potions_obtained": [],
        "potion_use_per_floor": [[]],
    }
    row = AUDIT.audit_summary_run(run, "runs/realistic.run", "hash")
    reconstruction = row["reconstruction"]
    assert reconstruction["attempted_modes"]["A_pre_combat_initialization"]["status"] == "partial_reconstruction_attempt"
    assert reconstruction["attempted_modes"]["A_pre_combat_initialization"]["deck"]["status"] == "candidate_multiset"
    assert reconstruction["attempted_modes"]["A_pre_combat_initialization"]["hp"]["status"] == "unknown"
    assert "SUMMARY_ONLY_NO_BATTLE_ENTRY" not in reconstruction["reason_codes"]


def test_missing_potion_inventory_is_not_treated_as_empty_slots():
    result = _audit_log(_recorded_log(include_potions=False))
    scene = result["scenes"][0]
    assert scene["status"] == "excluded"
    assert "POTION_INVENTORY_MISSING_OR_INVALID" in scene["quality_flags"]["reason_codes"]


def test_negative_player_hp_is_rejected_with_range_reason():
    records = [json.loads(line) for line in _recorded_log().decode().splitlines()]
    records[2]["hp_current"] = -50
    result = _audit_log("\n".join(json.dumps(record) for record in records).encode())
    scene = result["scenes"][0]
    assert scene["status"] == "excluded"
    assert "INVALID_FINITE_INTEGER_OR_RANGE" in scene["quality_flags"]["reason_codes"]


def test_float_encoded_hp_is_rejected_in_scene_snapshot():
    records = [json.loads(line) for line in _recorded_log().decode().splitlines()]
    records[2]["hp_current"] = 80.0
    result = _audit_log("\n".join(json.dumps(record) for record in records).encode())
    scene = result["scenes"][0]
    assert scene["status"] == "excluded"
    assert scene["player"]["hp_current"] is None
    assert "INVALID_FINITE_INTEGER_OR_RANGE" in scene["quality_flags"]["reason_codes"]


def test_missing_draw_card_is_rejected_by_pile_multiset_consistency():
    records = [json.loads(line) for line in _recorded_log().decode().splitlines()]
    records[2]["combat_state"].pop("draw_pile")
    result = _audit_log("\n".join(json.dumps(record) for record in records).encode())
    scene = result["scenes"][0]
    assert scene["status"] == "excluded"
    assert "PILE_MISSING_DECK_CARDS" in scene["quality_flags"]["reason_codes"]


def test_unknown_relic_is_not_only_backend_pending():
    result = _audit_log(
        _recorded_log(relics=[{"id": "UNKNOWN_AUDIT_RELIC"}])
    )
    scene = result["scenes"][0]
    assert scene["status"] == "excluded"
    assert "UNKNOWN_ENTITY_OR_SEMANTICS" in scene["quality_flags"]["reason_codes"]


def test_unregistered_card_dynamic_value_is_rejected_and_retained():
    result = _audit_log(_recorded_log(draw=["Searing Blow+2"]))
    scene = result["scenes"][0]
    assert scene["status"] == "excluded"
    assert "UNKNOWN_ENTITY_OR_SEMANTICS" in scene["quality_flags"]["reason_codes"]
    assert scene["piles"]["draw"][0]["name"] == "Searing Blow"
    assert scene["piles"]["draw"][0]["upgrade_count"] == 2


def test_unknown_encounter_group_is_rejected_even_when_monster_fields_parse():
    records = [json.loads(line) for line in _recorded_log().decode().splitlines()]
    records[2]["combat_state"]["monsters"][0]["id"] = "UnknownMonster"
    result = _audit_log("\n".join(json.dumps(record) for record in records).encode())
    scene = result["scenes"][0]
    assert scene["status"] == "excluded"
    assert "ENCOUNTER_NOT_REGISTERED" in scene["quality_flags"]["reason_codes"]


def test_missing_attack_damage_is_rejected_not_silently_zero():
    records = [json.loads(line) for line in _recorded_log().decode().splitlines()]
    monster = records[2]["combat_state"]["monsters"][0]
    monster["intent"] = "ATTACK"
    result = _audit_log("\n".join(json.dumps(record) for record in records).encode())
    scene = result["scenes"][0]
    assert scene["status"] == "excluded"
    assert "ATTACK_INTENT_DAMAGE_MISSING" in scene["quality_flags"]["reason_codes"]


def test_potion_belt_like_four_slots_are_rejected_by_capacity():
    records = [json.loads(line) for line in _recorded_log().decode().splitlines()]
    records[2]["potions"] = [None, None, None, None]
    result = _audit_log("\n".join(json.dumps(record) for record in records).encode())
    scene = result["scenes"][0]
    assert scene["status"] == "excluded"
    assert "POTION_CAPACITY_UNSUPPORTED" in scene["quality_flags"]["reason_codes"]


def test_unregistered_game_version_is_rejected():
    records = [json.loads(line) for line in _recorded_log().decode().splitlines()]
    records[0]["versions"]["sts"] = "unknown-version"
    result = _audit_log("\n".join(json.dumps(record) for record in records).encode())
    scene = result["scenes"][0]
    assert scene["status"] == "excluded"
    assert "VERSION_UNREGISTERED_OR_INCOMPATIBLE" in scene["quality_flags"]["reason_codes"]


def test_missing_dynamic_relic_counter_is_excluded_without_zero_default():
    result = _audit_log(
        _recorded_log(relics=[{"id": "StoneCalendar"}])
    )
    scene = result["scenes"][0]
    assert scene["status"] == "excluded"
    assert "DYNAMIC_RELIC_COUNTER_MISSING" in scene["quality_flags"]["reason_codes"]
    assert scene["relics"][0]["counter"] is None
    assert scene["relics"][0]["counter_recorded"] is False


def test_upgrade_format_ambiguity_preserves_raw_card_and_excludes_scene():
    raw = _recorded_log(draw=["Uppercut+"])
    result = _audit_log(raw)
    scene = result["scenes"][0]
    assert scene["status"] == "excluded"
    assert "UPGRADE_FORMAT_AMBIGUOUS" in scene["quality_flags"]["reason_codes"]
    assert scene["piles"]["raw_values_on_parse_failure"]["draw"] == ["Uppercut+"]


def test_ambiguous_entry_timing_is_excluded():
    result = _audit_log(_recorded_log(predecessor_type="action:end_turn"))
    assert result["scenes"][0]["status"] == "excluded"
    assert "ENTRY_TIMING_AMBIGUOUS" in result["scenes"][0]["quality_flags"]["reason_codes"]


def test_missing_version_is_rejected_instead_of_guessing():
    with pytest.raises(ValueError, match="versions"):
        _audit_log(_recorded_log(include_versions=False))


def test_realistic_entry_has_reconstructable_fields_but_not_exact_replay_claim():
    result = _audit_log(_recorded_log())
    scene = result["scenes"][0]
    assert scene["status"] == "visible_entry_verified_internal_state_unproven"
    assert scene["validation_status"]["structure_parse_status"] == "parseable"
    assert scene["validation_status"]["visible_entry_status"] == "verified"
    assert scene["validation_status"]["internal_state_status"] == "unproven"
    assert scene["player"]["powers_recorded"] is False
    assert scene["entry_timing"]["pre_initialization_snapshot_available"] is False
    assert scene["hidden_state"]["exact_historical_replay"] is False
    assert scene["run"]["environment_replay_seed"] is None
    assert "Monster moveHistory" in scene["internal_state_audit"]["required_for_continuation"][3]
    assert scene["internal_state_audit"]["resampling_policy"]["exact_historical_replay"] is False


def _gold_first_battle():
    """合成标准首层输入，测试规则推导；不认证真实来源。"""
    return {
        "character_chosen": "IRONCLAD", "ascension_level": 20,
        "build_version": "2022-03-07", "seed_played": "test", "play_id": "test",
        "is_daily": False, "is_trial": False, "is_endless": False,
        "path_per_floor": ["M"],
        "damage_taken": [{"floor": 1, "enemies": "Cultist"}],
        "neow_bonus": "HUNDRED_GOLD", "neow_cost": "NONE",
        "neow_bonus_log": {
            "cardsObtained": [], "cardsUpgraded": [], "cardsRemoved": [],
            "cardsTransformed": [], "relicsObtained": [], "maxHpGained": 0,
            "goldGained": 100, "damageTaken": 0, "goldLost": 0, "maxHpLost": 0,
        },
        "card_choices": [{"floor": 1, "picked": "Anger"}],
        "event_choices": [], "campfire_choices": [], "relics_obtained": [],
        "potions_obtained": [{"floor": 1, "key": "Fruit Juice"}],
        "items_purged_floors": [], "item_purchase_floors": [],
    }


def _summary_a(run):
    return AUDIT.audit_summary_run(run, "synthetic.run", "hash")["reconstruction"]


def test_entry_a_generates_enemy_and_piles_but_does_not_certify_source():
    result = _summary_a(_gold_first_battle())
    a = result["attempted_modes"]["A_pre_combat_initialization"]
    assert a["rule_constructible"] is True
    scene = a["candidate_scene"]
    assert scene["player"] == {"hp_current": 68, "hp_max": 75, "gold": 199}
    assert len(scene["deck"]) == 11 and scene["deck"].count("AscendersBane") == 1
    assert "Anger" not in scene["deck"]
    assert scene["potions"] == [None, None]
    assert scene["relics"][0]["counter_semantics"] == "not_applicable"
    assert "piles" not in scene
    assert scene["encounter"]["status"] == "resampled-by-policy"
    assert a["missing_or_ambiguous"] == []
    assert result["formal_candidate"] is False
    assert "SOURCE_MOD_MANIFEST_UNAVAILABLE" in result["reason_codes"]


@pytest.mark.parametrize("key", ["ascension_level", "neow_bonus_log", "is_trial", "event_choices", "seed_played"])
def test_entry_a_missing_required_source_input_cannot_construct(key):
    run = _gold_first_battle()
    run.pop(key)
    a = _summary_a(run)["attempted_modes"]["A_pre_combat_initialization"]
    assert a["rule_constructible"] is False
    assert a["candidate_scene"] is None


def test_entry_a_contradictory_hp_log_is_not_ignored():
    run = _gold_first_battle()
    run["neow_bonus_log"]["damageTaken"] = 5
    a = _summary_a(run)["attempted_modes"]["A_pre_combat_initialization"]
    assert "NEOW_LOG_MISSING_OR_CONTRADICTS_RULE" in a["missing_or_ambiguous"]
    assert a["hp"]["hp_current"] is None


def test_entry_a_does_not_read_final_deck_hp_or_reward_as_entry():
    run = _gold_first_battle()
    run.update(master_deck=["Unknown"], current_hp_per_floor=[1], max_hp_per_floor=[999], relics=["Unknown"])
    a = _summary_a(run)["attempted_modes"]["A_pre_combat_initialization"]
    assert a["rule_constructible"] is True
    assert a["candidate_scene"]["player"]["hp_current"] == 68


@pytest.mark.parametrize("ascension,hp,max_hp,slots,cards", [(0,80,80,3,10),(6,72,80,3,10),(10,72,80,3,11),(11,72,80,2,11),(14,68,75,2,11)])
def test_entry_a_ascension_thresholds(ascension, hp, max_hp, slots, cards):
    run = _gold_first_battle()
    run["ascension_level"] = ascension
    scene = _summary_a(run)["attempted_modes"]["A_pre_combat_initialization"]["candidate_scene"]
    assert scene["player"]["hp_current"] == hp
    assert scene["player"]["hp_max"] == max_hp
    assert len(scene["potions"]) == slots and len(scene["deck"]) == cards


def test_entry_a_unsupported_neow_preserves_specific_evidence_gap():
    run = _gold_first_battle()
    run["neow_bonus"] = "RANDOM_COMMON_RELIC"
    run["neow_bonus_log"]["relicsObtained"] = ["Pen Nib"]
    a = _summary_a(run)["attempted_modes"]["A_pre_combat_initialization"]
    assert not a["rule_constructible"]
    assert a["relics"]["neow_relics_obtained"] == ["Pen Nib"]
    assert "NEOW_EFFECT_RULE_NOT_YET_VERIFIED" in a["missing_or_ambiguous"]
    assert "ENCOUNTER_INSTANCE_STATE_MISSING" not in a["missing_or_ambiguous"]
