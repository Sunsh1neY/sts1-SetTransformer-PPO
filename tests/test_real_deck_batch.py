"""新来源策略正式入口、配置完整性与开发隔离验证。"""
import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from sts.env.public_battle import PublicBattleEnv, _canonical
from sts.env.real_deck import configured_scene, load_batch, sample_scene


def scene(split="train"):
    batch = load_batch()
    row = next(r for r in batch["decks"] if r["split"] == split)
    return configured_scene(batch, row["deck_id"], "wounded-equipped", "GREMLIN_NOB")


def test_reset_real_source_without_diagnostic_and_repeatable():
    s = scene()
    env = PublicBattleEnv(max_actions=1)
    a = env.reset(s, 960000, purpose="train")
    b = env.reset(s, 960000, purpose="train")
    np.testing.assert_array_equal(a.pop("action_mask"), b.pop("action_mask"))
    assert a == b
    assert a["player"]["hp"] == 45
    assert "source_path" not in a and "source_admission_policy" not in a
    action = int(np.flatnonzero(env.action_mask())[0])
    _, _, terminated, truncated, info = env.step(action)
    assert terminated or truncated
    assert info["scene_kind"] == "real-deck-configured"
    assert info["source_admission_policy"] == "real-deck-configured-battle-v1"


def test_new_source_rejects_mutation_even_with_rehashed_candidate():
    import hashlib
    s = scene()
    s["candidate"]["deck"].pop()
    s["candidate_sha256"] = hashlib.sha256(_canonical(s["candidate"])).hexdigest()
    with pytest.raises(ValueError, match="冻结批次"):
        PublicBattleEnv().reset(s, 960000)


def test_split_and_formal_evaluation_guard():
    with pytest.raises(ValueError, match="开发卡组"):
        PublicBattleEnv().reset(scene("development"), 960000, purpose="train")
    with pytest.raises(ValueError, match="保留评估"):
        PublicBattleEnv().reset(scene(), 42, purpose="evaluation")


def test_rebuild_and_source_decks_unchanged():
    path = Path(__file__).parents[1] / "scripts/prepare-real-deck-batch.py"
    spec = importlib.util.spec_from_file_location("prepare_batch", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.build() == load_batch()
    batch = load_batch()
    assert batch["summary"]["unique_decks"] == 27
    assert batch["common"]["burning_elite"] is False
    groups = {}
    for row in batch["decks"]:
        assert groups.setdefault(row["group_id"], row["split"]) == row["split"]


def test_sampler_reproducible_and_split_safe():
    batch = load_batch()
    a, b = np.random.default_rng(123), np.random.default_rng(123)
    for _ in range(50):
        x = sample_scene(batch, a)
        assert x == sample_scene(batch, b)
        assert x["research_split"] == "train"


def test_bad_batch_hash_rejected(tmp_path):
    batch = copy.deepcopy(load_batch())
    batch["common"]["burning_elite"] = True
    path = tmp_path / "batch.json"
    path.write_text(json.dumps(batch), encoding="utf-8")
    with pytest.raises(ValueError, match="整体哈希"):
        load_batch(path)
