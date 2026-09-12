"""真实卡组完整性、负证据和实际来源集成检查。"""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("real_decks", ROOT / "scripts/extract-real-decks.py")
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)
CONTRACT = json.loads(D.CONTRACT.read_text(encoding="utf-8"))
KNOWN = D.CORPUS.catalog()["CardId"]


def group(deck):
    return {"group_id": "g", "source_path": "a.run", "raw_sha256": "h", "aliases": ["a.run"],
            "identity_tokens": ["play_id:a"], "run": {"master_deck": deck}}


def test_preserve_duplicates_upgrades_and_no_history_dependency():
    g = group(["Strike_R", "Strike_R", "Bash+1"])
    a = D.extract_group(g, CONTRACT, KNOWN)
    assert a["extraction_status"] == "complete"
    assert a["backend_content_status"] == "supported"
    assert len(a["cards"]) == 3 and a["cards"][2]["upgrade_level"] == 1
    g["run"].update({"event_choices": None, "burning_elite": True, "relics": ["unknown"],
                      "potion_use_per_floor": "broken", "current_hp_per_floor": None})
    assert D.extract_group(g, CONTRACT, KNOWN) == a
    g["run"]["master_deck"].reverse()
    assert D.extract_group(g, CONTRACT, KNOWN)["deck_content_sha256"] == a["deck_content_sha256"]
    g["run"]["master_deck"].pop()
    assert D.extract_group(g, CONTRACT, KNOWN)["deck_content_sha256"] != a["deck_content_sha256"]


@pytest.mark.parametrize("card", [None, {}, "Bash+", "Bash+0", "Bash+2", "Bash+-1", " Bash", ""])
def test_invalid_card_never_silently_disappears(card):
    a = D.extract_group(group(["Bash", card]), CONTRACT, KNOWN)
    assert a["extraction_status"] == "rejected"
    assert a["raw_deck"] == ["Bash", card]
    assert a["deck_content_sha256"] is None


def test_backend_contract_is_authority_and_blocked_cards_are_preserved():
    g = group(["Anger", "True Grit+1"])
    a = D.extract_group(g, CONTRACT, KNOWN)
    assert a["extraction_status"] == "complete"
    assert a["backend_blockers"] == ["UNSUPPORTED_CARD:Anger", "UNSUPPORTED_UPGRADE:True Grit+1"]
    contract = copy.deepcopy(CONTRACT)
    contract["cards"].append({"name": "Anger", "max_upgrade": 1})
    next(c for c in contract["cards"] if c["name"] == "True Grit")["max_upgrade"] = 1
    assert D.extract_group(g, contract, KNOWN)["backend_content_status"] == "supported"
    assert a["raw_deck"] == g["run"]["master_deck"]


@pytest.mark.parametrize("flag", ["conflicting_variants", "card_modifier_group_rejected"])
def test_group_negative_evidence_cannot_be_promoted(flag):
    g = group(["Bash"])
    g[flag] = True
    assert D.extract_group(g, CONTRACT, KNOWN)["extraction_status"] == "rejected"


def test_permanent_value_unknown_and_capacity():
    a = D.extract_group(group(["RitualDagger"]), CONTRACT, KNOWN)
    assert "PERMANENT_CARD_VALUE_UNRECORDED:RitualDagger" in a["extraction_blockers"]
    a = D.extract_group(group(["Bash"] * 97), CONTRACT, KNOWN)
    assert a["card_count"] == 97
    assert a["backend_blockers"] == ["INITIAL_DECK_CAPACITY_EXCEEDED"]


def test_actual_archive_roundtrip_groups_and_manifest():
    archive = ROOT / "reference/public-run-corpus/matiger-fixed.zip"
    if not archive.exists():
        pytest.skip("本地固定公开语料未下载")
    records = D.CORPUS.load_records(archive.read_bytes())
    actual = D.build(records, CONTRACT, KNOWN)
    saved = json.loads((ROOT / "docs/real-deck-manifest.json").read_text(encoding="utf-8"))
    assert actual == {k: v for k, v in saved.items() if k != "inputs"}
    by_path = {r["source_path"]: r for r in records}
    aliases = set()
    for row in actual["decks"]:
        source = by_path[row["source_path"]]
        assert row["raw_deck"] == source["run"]["master_deck"]
        assert row["raw_sha256"] == source["raw_sha256"]
        assert row["split"] == "unassigned" and row["runtime_status"] == "not_run"
        assert not aliases.intersection(row["source_aliases"])
        aliases.update(row["source_aliases"])
        if row["extraction_status"] == "complete":
            reconstructed = [c["name"] + (f"+{c['upgrade_level']}" if c["upgrade_level"] else "") for c in row["cards"]]
            assert reconstructed == row["raw_deck"]
    assert aliases == set(by_path)
    s = actual["summary"]
    assert s["run_groups"] == s["complete"]["run_groups"] + s["extraction_rejected"]
    assert s["run_groups"] == 157 and s["raw_files"] == 203
    assert s["complete"]["unique_decks"] == 146
    assert s["backend_supported"]["run_groups"] == 0


def test_shared_identity_duplicates_do_not_inflate_card_groups():
    def record(path, raw_sha, play_id, seed):
        return {"source_path": path, "raw_sha256": raw_sha,
                "run": {"master_deck": ["Bash"], "play_id": play_id, "seed_played": seed}}
    records = [record("a", "h1", "p1", "s1"), record("b", "h1", "p1", "s1"),
               record("c", "h2", "p2", "s2")]
    result = D.build(records, CONTRACT, KNOWN)
    assert result["summary"]["run_groups"] == 2
    assert result["summary"]["complete"]["unique_decks"] == 1
    records.append(record("d", "h3", "p1", "s2"))
    result = D.build(records, CONTRACT, KNOWN)
    assert result["summary"]["run_groups"] == 1
    assert result["summary"]["extraction_rejected"] == 1
