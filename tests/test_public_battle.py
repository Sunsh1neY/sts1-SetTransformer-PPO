"""新语义包装的信息边界、来源完整性和控制参数回归。"""
import copy
import json

import numpy as np
import pytest

from sts.env.public_battle import PublicBattleEnv, load_scene_manifest, normalize_observation


def test_manifest_loads_whole_scenes_and_preserves_sources():
    metadata, scenes = load_scene_manifest()
    assert len(scenes) == 99
    assert len({s["group_id"] for s in scenes}) == 75
    assert metadata["source_admission_policy"] == "public-derived-standard-v1"
    assert all(s["candidate"] and not s["content_blockers"] for s in scenes)


@pytest.mark.parametrize("seed", [-1, 0, 999, 1000, 99999, 2**64, True, 100000.5])
def test_development_seed_domain_rejects_invalid_or_eval_seeds(seed):
    _, scenes = load_scene_manifest()
    with pytest.raises((ValueError, TypeError)):
        PublicBattleEnv().reset(scenes[0], seed)


def test_source_metadata_never_appears_in_policy_observation():
    _, scenes = load_scene_manifest()
    env = PublicBattleEnv(max_actions=1)
    obs = env.reset(scenes[0], 830000)
    assert "source_seed" not in obs and "group_id" not in obs and "environment_seed" not in obs
    after, _, _, _, info = env.step(int(np.flatnonzero(obs["action_mask"])[0]))
    assert info["source_seed"] == scenes[0]["source_seed"]
    assert info["environment_seed"] == 830000
    assert "source_seed" not in after


def test_changed_candidate_is_rejected_even_if_marked_accepted():
    _, scenes = load_scene_manifest()
    bad = copy.deepcopy(scenes[0])
    bad["candidate"]["player"]["hp"] -= 1
    with pytest.raises(ValueError, match="哈希"):
        PublicBattleEnv().reset(bad, 830000)


def test_manifest_global_tampering_is_rejected(tmp_path):
    metadata, _ = load_scene_manifest()
    raw = json.loads(open(metadata["path"], encoding="utf-8").read())
    raw["split_status"] = "formal"
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="整体哈希"):
        load_scene_manifest(path)


def test_nonhand_permutation_does_not_change_normalized_observation():
    _, scenes = load_scene_manifest()
    env = PublicBattleEnv()
    env.reset(scenes[0], 830000)
    raw = json.loads(env._env.observation())
    shuffled = copy.deepcopy(raw)
    shuffled["draw_pile"].reverse()
    a, b = normalize_observation(raw), normalize_observation(shuffled)
    assert a["draw_pile"] == b["draw_pile"]
    assert a["hand"] == b["hand"]
    np.testing.assert_array_equal(a["action_mask"], b["action_mask"])


def test_hidden_backend_field_cannot_enter_observation():
    _, scenes = load_scene_manifest()
    env = PublicBattleEnv()
    env.reset(scenes[0], 830000)
    raw = json.loads(env._env.observation())
    raw["enemies"][0]["move_history"] = [1, 2]
    with pytest.raises(ValueError, match="隐藏字段"):
        normalize_observation(raw)


def test_diagnostic_scene_requires_character_and_act():
    _, scenes = load_scene_manifest()
    candidate = copy.deepcopy(scenes[0]["candidate"])
    candidate.pop("act")
    with pytest.raises(ValueError, match="必填"):
        PublicBattleEnv().reset(candidate, 830000, diagnostic=True)


def test_old_action_shape_cannot_be_accepted_as_public_protocol():
    _, scenes = load_scene_manifest()
    env = PublicBattleEnv()
    env.reset(scenes[0], 830000)
    raw = json.loads(env._env.observation())
    raw["action_mask"] = raw["action_mask"][:31]
    with pytest.raises(ValueError, match="66"):
        normalize_observation(raw)
