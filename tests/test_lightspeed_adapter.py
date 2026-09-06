"""正式后端 Python 薄包装的接口与信息边界测试。"""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from sts import Encounter, LightspeedBattleEnv
from sts.env.lightspeed import (
    ACTION_COUNT,
    CARD_FEATURES,
    ENEMY_FEATURES,
    GLOBAL_FEATURES,
    MAX_ENEMIES,
    MAX_HAND,
    _check_backend_layout,
    _observation_to_dict,
)
from sts.env.registry import CardLocation


EXPECTED_KEYS = {
    "hand",
    "enemies",
    "draw_pile",
    "discard_pile",
    "exhaust_pile",
    "global",
    "enemy_mask",
    "action_mask",
}


def _assert_observation_contract(observation):
    assert set(observation) == EXPECTED_KEYS
    assert 0 <= len(observation["hand"]) <= MAX_HAND
    assert observation["enemies"].shape == (MAX_ENEMIES, len(ENEMY_FEATURES))
    assert all(isinstance(observation[key], list) for key in (
        "hand", "draw_pile", "discard_pile", "exhaust_pile",
    ))
    for key in ("hand", "draw_pile", "discard_pile", "exhaust_pile"):
        for card in observation[key]:
            assert set(card) == {
                "card_id", "location", "upgraded", "cost", "cost_known", "target_kind",
            }
            assert isinstance(card["card_id"], int)
            assert isinstance(card["location"], int)
            assert isinstance(card["upgraded"], bool)
            assert isinstance(card["cost"], int)
            assert isinstance(card["cost_known"], bool)
            assert isinstance(card["target_kind"], int)
    assert observation["global"].shape == (len(GLOBAL_FEATURES),)
    assert observation["enemy_mask"].shape == (MAX_ENEMIES,)
    assert observation["action_mask"].shape == (ACTION_COUNT,)
    assert observation["enemies"].dtype == np.int32
    assert observation["global"].dtype == np.int32
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
    saved = deepcopy(before)

    action = int(np.flatnonzero(before["action_mask"])[0])
    after, *_ = env.step(action)

    for key in EXPECTED_KEYS:
        if isinstance(before[key], np.ndarray):
            assert np.array_equal(before[key], saved[key])
            assert not np.shares_memory(before[key], after[key])
        else:
            assert before[key] == saved[key]
            assert before[key] is not after[key]


def test_raw_card_records_are_validated_and_invalid_enemy_rows_are_zeroed():
    hand = np.zeros((MAX_HAND, len(CARD_FEATURES)), dtype=np.int32)
    hand[0] = [25, int(CardLocation.HAND), 0, 2, 1]
    enemies = np.full((MAX_ENEMIES, len(ENEMY_FEATURES)), 9, dtype=np.int32)
    raw = SimpleNamespace(
        hand=hand.ravel().tolist(),
        enemies=enemies.ravel().tolist(),
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        hand_mask=[True, *([False] * 9)],
        enemy_mask=[False] * MAX_ENEMIES,
        action_mask=[False] * ACTION_COUNT,
    )
    global_values = [0] * len(GLOBAL_FEATURES)
    global_values[5] = 1
    setattr(raw, "global", global_values)

    observation = _observation_to_dict(raw)

    assert observation["hand"] == [{
        "card_id": 1,
        "location": int(CardLocation.HAND),
        "upgraded": False,
        "cost": 2,
        "cost_known": True,
        "target_kind": 2,
    }]
    assert np.all(observation["enemies"][0] == 0)

    raw.hand[0] = 999999
    with pytest.raises(ValueError, match="未登记"):
        _observation_to_dict(raw)


def test_backend_field_drift_is_rejected():
    backend = SimpleNamespace(
        CARD_FEATURES=["location", "backend_card_id", "upgraded", "cost", "cost_known"],
        ENEMY_FEATURES=ENEMY_FEATURES,
        GLOBAL_FEATURES=GLOBAL_FEATURES,
    )
    with pytest.raises(RuntimeError, match="CARD_FEATURES 已漂移"):
        _check_backend_layout(backend)


@pytest.mark.parametrize("encounter", list(Encounter))
def test_visible_card_counts_are_conserved_through_trajectory(encounter):
    env = LightspeedBattleEnv(max_turns=10)
    observation = env.reset(100000, encounter)
    card_ids = (1, 2, 3)

    for _ in range(100):
        all_cards = [
            *observation["hand"],
            *observation["draw_pile"],
            *observation["discard_pile"],
            *observation["exhaust_pile"],
        ]
        total_counts = np.array([
            sum(card["card_id"] == card_id for card in all_cards)
            for card_id in card_ids
        ])
        assert total_counts.tolist() == [1, 4, 5]
        player = dict(zip(GLOBAL_FEATURES, observation["global"]))
        assert len(observation["hand"]) == player["hand_count"]
        assert len(observation["draw_pile"]) == player["draw_count"]
        assert len(observation["discard_pile"]) == player["discard_count"]
        assert len(observation["exhaust_pile"]) == player["exhaust_count"]

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
        if isinstance(wrapped_observation[key], np.ndarray):
            assert np.array_equal(wrapped_observation[key], raw_dict[key])
        else:
            assert wrapped_observation[key] == raw_dict[key]

    for _ in range(100):
        action = int(np.flatnonzero(wrapped_observation["action_mask"])[0])
        wrapped_result = wrapped.step(action)
        raw_result = raw.step(action)
        wrapped_observation, reward, terminated, truncated, info = wrapped_result
        raw_dict = _observation_to_dict(raw_result.observation)

        for key in EXPECTED_KEYS:
            if isinstance(wrapped_observation[key], np.ndarray):
                assert np.array_equal(wrapped_observation[key], raw_dict[key])
            else:
                assert wrapped_observation[key] == raw_dict[key]
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
