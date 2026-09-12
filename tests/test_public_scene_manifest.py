"""完整场景筛选、分组与文件完整性验证。"""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("scene_manifest", ROOT / "scripts/build-public-scene-manifest.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def fixture_index():
    # 使用实际审计输出作为反例底稿，不复制简化场景来绕过来源字段。
    data = json.loads((ROOT / "docs/m2-corpus-index.json").read_text(encoding="utf-8"))
    row = next(s for s in data["scenes"] if s["candidate"] and set(s["candidate"]["deck"]) <= {"Strike_R", "Defend_R", "Bash", "AscendersBane"} and not any(s["candidate"]["potions"]))
    data["scenes"] = [copy.deepcopy(row)]
    data["groups"] = [g for g in data["groups"] if g["group_id"] == row["group_id"]]
    return data


@pytest.mark.parametrize("field,value", [("deck", "Unknown Card"), ("deck", "True Grit+1"), ("potions", "Discovery"), ("relics", "Unknown Relic")])
def test_unknown_or_choice_entity_defers_whole_unmodified_scene(field, value):
    data = fixture_index()
    data["scenes"][0]["candidate"][field].append(value)
    original = copy.deepcopy(data)
    result = M.build_manifest(data, "test")
    row = result["scenes"][0]
    assert row["implementation_batch_status"] == "whole_scene_deferred"
    assert row["candidate"] == original["scenes"][0]["candidate"]
    assert data == original


def test_group_split_and_duplicate_scene_are_rejected():
    data = fixture_index()
    data["scenes"][0]["research_split"] = "injected"
    with pytest.raises(ValueError, match="GROUP_SPLIT"):
        M.build_manifest(data, "test")
    data = fixture_index()
    data["scenes"].append(copy.deepcopy(data["scenes"][0]))
    with pytest.raises(ValueError, match="DUPLICATE_SCENE"):
        M.build_manifest(data, "test")


def test_hashes_seed_boundary_and_generated_closure():
    data = fixture_index()
    data["scenes"][0]["candidate"]["deck"].append("Power Through")
    result = M.build_manifest(data, "test")
    row = result["scenes"][0]
    assert row["scene_id"] == data["scenes"][0]["scene_id"]
    assert "Wound" in row["entity_closure"]["generated_cards"]
    assert row["candidate_sha256"] == M.C.sha(M.C.canonical(row["candidate"]))
    digest = result.pop("manifest_payload_sha256")
    assert digest == M.C.sha(M.C.canonical(result))
    assert "never-model-input" in result["source_seed_policy"]
    assert not result["formal_training_ready"] and not result["formal_evaluation_ready"]


def test_real_input_output_hashes_and_tamper_rejection():
    raw = (ROOT / "docs/m2-corpus-index.json").read_bytes()
    data = json.loads(raw)
    corpus = (ROOT / "reference/public-run-corpus/corpus.json").read_bytes()
    assert M.validate_index(data, raw, corpus) == M.C.sha(raw)
    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        M.validate_index(data, raw, corpus + b" ")
    broken = copy.deepcopy(data)
    broken["summary"]["formal_candidate_count"] = 999
    with pytest.raises(ValueError, match="CONTENT_MISMATCH"):
        M.validate_index(broken, raw, corpus)
