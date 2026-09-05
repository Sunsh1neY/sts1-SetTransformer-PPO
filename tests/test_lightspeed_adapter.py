"""正式后端 Python 薄包装的接口与信息边界测试。"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from sts import Encounter, LightspeedBattleEnv
from sts.env.lightspeed import (
    ACTION_COUNT,
    ENEMY_FEATURES,
    GLOBAL_FEATURES,
    HAND_FEATURES,
    MAX_ENEMIES,
    MAX_HAND,
    PILE_FEATURES,
    _check_backend_layout,
    _observation_to_dict,
)


EXPECTED_KEYS = {
    "hand",
    "enemies",
    "draw_pile",
    "discard_pile",
    "global",
    "hand_mask",
    "enemy_mask",
    "action_mask",
}


def _assert_observation_contract(observation):
    assert set(observation) == EXPECTED_KEYS
    assert observation["hand"].shape == (MAX_HAND, len(HAND_FEATURES))
    assert observation["enemies"].shape == (MAX_ENEMIES, len(ENEMY_FEATURES))
    assert observation["draw_pile"].shape == (len(PILE_FEATURES),)
    assert observation["discard_pile"].shape == (len(PILE_FEATURES),)
    assert observation["global"].shape == (len(GLOBAL_FEATURES),)
    assert observation["hand_mask"].shape == (MAX_HAND,)
    assert observation["enemy_mask"].shape == (MAX_ENEMIES,)
    assert observation["action_mask"].shape == (ACTION_COUNT,)
    assert observation["hand"].dtype == np.int32
    assert observation["enemies"].dtype == np.int32
    assert observation["draw_pile"].dtype == np.int32
    assert observation["discard_pile"].dtype == np.int32
    assert observation["global"].dtype == np.int32
    assert observation["hand_mask"].dtype == np.bool_
    assert observation["enemy_mask"].dtype == np.bool_
    assert observation["action_mask"].dtype == np.bool_


@pytest.mark.parametrize("encounter", list(Encounter))
def test_package_entry_runs_all_minimal_encounters(encounter):
    env = LightspeedBattleEnv()
    observation = env.reset(100000, encounter)
    _assert_observation_contract(observation)
    assert np.array_equal(observation["action_mask"], env.action_mask())

    action = int(np.flatnonzero(observation["action_mask"])[0])
    next_observation, reward, terminated, truncated, info = env.step(action)
    _assert_observation_contract(next_observation)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)
    assert "shuffle_rng" in info
    assert not EXPECTED_KEYS.intersection(info)


def test_observation_snapshot_is_independent_across_steps():
    env = LightspeedBattleEnv()
    before = env.reset(100000, Encounter.TWO_LOUSE)
    saved = {key: value.copy() for key, value in before.items()}

    action = int(np.flatnonzero(before["action_mask"])[0])
    after, *_ = env.step(action)

    for key in EXPECTED_KEYS:
        assert np.array_equal(before[key], saved[key])
        assert not np.shares_memory(before[key], after[key])


def test_invalid_entity_rows_are_canonicalized_to_zero():
    hand = np.full((MAX_HAND, len(HAND_FEATURES)), 7, dtype=np.int32)
    enemies = np.full((MAX_ENEMIES, len(ENEMY_FEATURES)), 9, dtype=np.int32)
    raw = SimpleNamespace(
        hand=hand.ravel().tolist(),
        enemies=enemies.ravel().tolist(),
        draw_pile=[1, 2, 2],
        discard_pile=[0, 0, 0],
        hand_mask=[True, False, *([True] * 8)],
        enemy_mask=[False, True, True, True, True],
        action_mask=[False] * ACTION_COUNT,
    )
    setattr(raw, "global", [1] * len(GLOBAL_FEATURES))

    observation = _observation_to_dict(raw)

    assert np.all(observation["hand"][1] == 0)
    assert np.all(observation["enemies"][0] == 0)
    assert np.all(observation["hand"][0] == 7)
    assert np.all(observation["enemies"][1] == 9)


def test_backend_field_drift_is_rejected():
    backend = SimpleNamespace(
        HAND_FEATURES=["cost", "card_id", "upgraded"],
        ENEMY_FEATURES=ENEMY_FEATURES,
        PILE_FEATURES=PILE_FEATURES,
        GLOBAL_FEATURES=GLOBAL_FEATURES,
    )
    with pytest.raises(RuntimeError, match="HAND_FEATURES 已漂移"):
        _check_backend_layout(backend)


@pytest.mark.parametrize("encounter", list(Encounter))
def test_visible_card_counts_are_conserved_through_trajectory(encounter):
    env = LightspeedBattleEnv(max_turns=10)
    observation = env.reset(100000, encounter)
    card_ids = (25, 104, 321)

    for _ in range(100):
        hand_counts = np.array([
            np.count_nonzero(
                observation["hand"][observation["hand_mask"], 0] == card_id
            )
            for card_id in card_ids
        ])
        total_counts = (
            hand_counts
            + observation["draw_pile"]
            + observation["discard_pile"]
        )
        assert total_counts.tolist() == [1, 4, 5]
        assert observation["draw_pile"].sum() == observation["global"][5]
        assert observation["discard_pile"].sum() == observation["global"][6]

        legal = np.flatnonzero(observation["action_mask"])
        if legal.size == 0:
            break
        observation, _, terminated, truncated, _ = env.step(int(legal[0]))
        if terminated or truncated:
            continue
    else:
        pytest.fail("轨迹未在预期步数内结束")


@pytest.mark.parametrize("encounter", list(Encounter))
def test_adapter_preserves_raw_trajectory(encounter):
    wrapped = LightspeedBattleEnv(max_turns=10)
    backend = wrapped._backend
    raw = backend.IroncladBattleEnv(max_turns=10)
    backend_encounter = wrapped._backend_encounter(encounter)

    wrapped_observation = wrapped.reset(100001, encounter)
    raw_observation = raw.reset(100001, backend_encounter, 0)
    raw_dict = _observation_to_dict(raw_observation)
    for key in EXPECTED_KEYS:
        assert np.array_equal(wrapped_observation[key], raw_dict[key])

    for _ in range(100):
        action = int(np.flatnonzero(wrapped_observation["action_mask"])[0])
        wrapped_result = wrapped.step(action)
        raw_result = raw.step(action)
        wrapped_observation, reward, terminated, truncated, info = wrapped_result
        raw_dict = _observation_to_dict(raw_result.observation)

        for key in EXPECTED_KEYS:
            assert np.array_equal(wrapped_observation[key], raw_dict[key])
        assert reward == raw_result.reward
        assert terminated == raw_result.terminated
        assert truncated == raw_result.truncated
        assert info == raw_result.info
        if terminated or truncated:
            break
    else:
        pytest.fail("轨迹未在预期步数内结束")


def test_terminal_observation_stops_sampling_and_step():
    env = LightspeedBattleEnv(max_turns=1)
    observation = env.reset(100000, Encounter.CULTIST)
    assert observation["action_mask"][30]

    observation, reward, terminated, truncated, info = env.step(30)

    assert reward == 0.0
    assert terminated is True
    assert truncated is False
    assert info["timeout"] == 1
    assert not observation["action_mask"].any()
    assert not env.action_mask().any()
    with pytest.raises(RuntimeError, match="finished"):
        env.step(30)


def test_unknown_encounter_is_rejected_before_backend_call():
    env = LightspeedBattleEnv()
    with pytest.raises(ValueError, match="未知遭遇"):
        env.reset(100000, "gremlin-gang")
