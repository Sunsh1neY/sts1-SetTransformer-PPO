"""FlattenWrapper 与 TokenWrapper 的同源、换位和信息边界测试。"""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from sts import Encounter, FlattenWrapper, LightspeedBattleEnv, TokenWrapper
from sts.env.wrappers import (
    CARD_TO_INDEX,
    ENEMY_ENCODED_DIM,
    FLAT_DIM,
    FLAT_LAYOUT,
    GLOBAL_ENCODED_DIM,
    HAND_ENCODED_DIM,
    PILE_ENCODED_DIM,
    TOKEN_COUNT,
)


def _copy_observation(observation):
    return {key: value.copy() if isinstance(value, np.ndarray) else deepcopy(value)
            for key, value in observation.items()}


def _segment(features, name):
    _, start, end = next(item for item in FLAT_LAYOUT if item[0] == name)
    return features[start:end]


def _assert_wrapped_equal(first, second):
    assert set(first) == set(second)
    for key in first:
        assert np.array_equal(first[key], second[key]), key


def test_wrapper_shapes_dtypes_and_traceable_flat_layout():
    env = LightspeedBattleEnv()
    source = env.reset(100000, Encounter.TWO_LOUSE)
    flat = FlattenWrapper(env).transform(source)
    tokens = TokenWrapper(env).transform(source)

    assert flat["features"].shape == (FLAT_DIM,) == (182,)
    assert flat["features"].dtype == np.float32
    assert flat["action_mask"].shape == (31,)
    assert flat["action_mask"].dtype == np.bool_
    assert tokens["hand"].shape == (10, HAND_ENCODED_DIM) == (10, 5)
    assert tokens["enemies"].shape == (5, ENEMY_ENCODED_DIM) == (5, 20)
    assert tokens["global"].shape == (1, GLOBAL_ENCODED_DIM) == (1, 11)
    assert tokens["draw_pile"].shape == (1, PILE_ENCODED_DIM) == (1, 3)
    assert tokens["discard_pile"].shape == (1, PILE_ENCODED_DIM) == (1, 3)
    assert tokens["token_mask"].shape == (TOKEN_COUNT,) == (18,)
    assert tokens["hand"].dtype == np.float32
    assert tokens["enemies"].dtype == np.float32
    assert tokens["global"].dtype == np.float32
    assert tokens["draw_pile"].dtype == np.float32
    assert tokens["discard_pile"].dtype == np.float32
    assert tokens["token_mask"].dtype == np.bool_

    assert np.array_equal(
        _segment(flat["features"], "hand"),
        tokens["hand"].ravel(),
    )
    assert np.array_equal(
        _segment(flat["features"], "enemies"),
        tokens["enemies"].ravel(),
    )
    assert np.array_equal(
        _segment(flat["features"], "global"),
        tokens["global"].ravel(),
    )
    assert np.array_equal(
        _segment(flat["features"], "draw_pile"),
        tokens["draw_pile"].ravel(),
    )
    assert np.array_equal(
        _segment(flat["features"], "discard_pile"),
        tokens["discard_pile"].ravel(),
    )
    assert np.array_equal(
        _segment(flat["features"], "hand_mask"),
        tokens["hand_mask"].astype(np.float32),
    )
    assert np.array_equal(
        _segment(flat["features"], "enemy_mask"),
        tokens["enemy_mask"].astype(np.float32),
    )
    assert np.array_equal(flat["action_mask"], tokens["action_mask"])
    assert np.array_equal(tokens["global"].ravel(), source["global"].astype(np.float32))
    assert np.array_equal(
        tokens["draw_pile"].ravel(),
        source["draw_pile"].astype(np.float32),
    )
    assert np.array_equal(
        tokens["discard_pile"].ravel(),
        source["discard_pile"].astype(np.float32),
    )
    for slot in np.flatnonzero(source["hand_mask"]):
        assert tokens["hand"][slot, -2] == source["hand"][slot, 1]
        assert tokens["hand"][slot, -1] == source["hand"][slot, 2]
    for target in np.flatnonzero(source["enemy_mask"]):
        assert np.array_equal(
            tokens["enemies"][target, 4:10],
            source["enemies"][target, 1:7].astype(np.float32),
        )
        assert np.array_equal(
            tokens["enemies"][target, 16:20],
            source["enemies"][target, 8:12].astype(np.float32),
        )


def test_category_ids_are_one_hot_not_continuous_magnitudes():
    env = LightspeedBattleEnv()
    source = env.reset(100000, Encounter.TWO_LOUSE)
    tokens = TokenWrapper(env).transform(source)

    for slot in np.flatnonzero(source["hand_mask"]):
        encoded = tokens["hand"][slot, :len(CARD_TO_INDEX)]
        assert encoded.sum() == 1.0
        assert set(encoded) <= {0.0, 1.0}
        assert encoded[CARD_TO_INDEX[int(source["hand"][slot, 0])]] == 1.0


def test_hand_permutation_moves_entities_and_action_blocks_only():
    env = LightspeedBattleEnv()
    source_a = env.reset(100000, Encounter.TWO_LOUSE)
    source_a = _copy_observation(source_a)
    source_a["hand"][0] = [25, 0, 2]  # Bash
    source_a["hand"][1] = [321, 0, 1]  # Strike
    source_a["global"][3] = 1
    source_a["action_mask"][:] = False
    source_a["action_mask"][3:5] = True  # 能量只够槽位 1 的 Strike
    source_a["action_mask"][30] = True

    source_b = _copy_observation(source_a)
    source_b["hand"][[0, 1]] = source_b["hand"][[1, 0]]
    source_b["hand_mask"][[0, 1]] = source_b["hand_mask"][[1, 0]]
    source_b["action_mask"][0:3] = source_a["action_mask"][3:6]
    source_b["action_mask"][3:6] = source_a["action_mask"][0:3]

    token_wrapper = TokenWrapper(env)
    flat_wrapper = FlattenWrapper(env)
    token_a = token_wrapper.transform(source_a)
    token_b = token_wrapper.transform(source_b)
    flat_a = flat_wrapper.transform(source_a)
    flat_b = flat_wrapper.transform(source_b)

    assert np.array_equal(token_b["hand"][0], token_a["hand"][1])
    assert np.array_equal(token_b["hand"][1], token_a["hand"][0])
    assert np.array_equal(token_b["global"], token_a["global"])
    assert np.array_equal(token_b["enemies"], token_a["enemies"])
    assert np.array_equal(token_b["draw_pile"], token_a["draw_pile"])
    assert np.array_equal(token_b["discard_pile"], token_a["discard_pile"])
    assert np.array_equal(token_b["action_mask"][0:3], token_a["action_mask"][3:6])
    assert np.array_equal(token_b["action_mask"][3:6], token_a["action_mask"][0:3])
    assert np.array_equal(
        _segment(flat_b["features"], "global"),
        _segment(flat_a["features"], "global"),
    )
    bash_slot_a = int(np.flatnonzero(token_a["hand"][:, CARD_TO_INDEX[25]])[0])
    bash_slot_b = int(np.flatnonzero(token_b["hand"][:, CARD_TO_INDEX[25]])[0])
    assert (bash_slot_a, bash_slot_b) == (0, 1)
    assert bash_slot_a * 3 == 0
    assert bash_slot_b * 3 == 3


def test_enemy_permutation_moves_target_columns_but_not_no_target_card():
    env = LightspeedBattleEnv()
    source_a = _copy_observation(env.reset(100000, Encounter.JAW_WORM))
    source_a["hand"][0] = [321, 0, 1]  # Strike，需要目标
    source_a["hand"][1] = [104, 0, 1]  # Defend，无目标
    source_a["action_mask"][:] = False
    source_a["action_mask"][0:3] = [True, False, False]
    source_a["action_mask"][3:6] = [True, False, False]
    source_a["action_mask"][30] = True

    source_b = _copy_observation(source_a)
    source_b["enemies"][[0, 1]] = source_b["enemies"][[1, 0]]
    source_b["enemy_mask"][[0, 1]] = source_b["enemy_mask"][[1, 0]]
    source_b["action_mask"][0:3] = [False, True, False]
    # Defend 的 target=0 是无目标牌规范编号，不代表敌人 0，换敌人时保持不变。
    source_b["action_mask"][3:6] = [True, False, False]

    tokens_a = TokenWrapper(env).transform(source_a)
    tokens_b = TokenWrapper(env).transform(source_b)

    assert not tokens_a["enemy_mask"][1]
    assert not tokens_b["enemy_mask"][0]
    assert np.array_equal(tokens_b["enemies"][1], tokens_a["enemies"][0])
    assert tokens_a["action_mask"][0:3].tolist() == [True, False, False]
    assert tokens_b["action_mask"][0:3].tolist() == [False, True, False]
    assert tokens_a["action_mask"][3:6].tolist() == [True, False, False]
    assert tokens_b["action_mask"][3:6].tolist() == [True, False, False]


def test_padding_residue_and_hidden_debug_values_do_not_change_outputs():
    env = LightspeedBattleEnv()
    source = env.reset(100000, Encounter.TWO_LOUSE)
    changed = _copy_observation(source)
    changed["hand"][~changed["hand_mask"]] = 123456
    changed["enemies"][~changed["enemy_mask"]] = 654321
    changed["seed"] = 999999
    changed["shuffle_rng"] = 888888
    changed["draw_order"] = [321, 25, 104]

    _assert_wrapped_equal(
        FlattenWrapper(env).transform(source),
        FlattenWrapper(env).transform(changed),
    )
    _assert_wrapped_equal(
        TokenWrapper(env).transform(source),
        TokenWrapper(env).transform(changed),
    )


@pytest.mark.parametrize("wrapper_type", [FlattenWrapper, TokenWrapper])
def test_transform_is_deterministic_and_returns_independent_arrays(wrapper_type):
    env = LightspeedBattleEnv()
    source = env.reset(100000, Encounter.TWO_LOUSE)
    wrapper = wrapper_type(env)

    first = wrapper.transform(source)
    second = wrapper.transform(source)

    _assert_wrapped_equal(first, second)
    for key in first:
        assert not np.shares_memory(first[key], second[key])


def test_identical_cards_have_identical_token_features_without_slot_number():
    env = LightspeedBattleEnv()
    source = _copy_observation(env.reset(100000, Encounter.TWO_LOUSE))
    source["hand"][0] = [321, 0, 1]
    source["hand"][1] = [321, 0, 1]

    tokens = TokenWrapper(env).transform(source)

    assert np.array_equal(tokens["hand"][0], tokens["hand"][1])


def test_visible_pile_counts_move_through_both_wrappers():
    env = LightspeedBattleEnv()
    source = env.reset(100000, Encounter.TWO_LOUSE)
    next_source, *_ = env.step(30)

    assert source["draw_pile"].tolist() == [1, 2, 2]
    assert source["discard_pile"].tolist() == [0, 0, 0]
    assert next_source["draw_pile"].tolist() == [0, 0, 0]
    assert next_source["discard_pile"].tolist() == [0, 2, 3]
    assert source["draw_pile"].sum() == source["global"][5]
    assert next_source["discard_pile"].sum() == next_source["global"][6]

    flat = FlattenWrapper(env).transform(next_source)
    tokens = TokenWrapper(env).transform(next_source)
    assert np.array_equal(
        _segment(flat["features"], "draw_pile"),
        tokens["draw_pile"].ravel(),
    )
    assert np.array_equal(
        _segment(flat["features"], "discard_pile"),
        tokens["discard_pile"].ravel(),
    )


@pytest.mark.parametrize("wrapper_type", [FlattenWrapper, TokenWrapper])
@pytest.mark.parametrize("encounter", list(Encounter))
def test_wrapped_environment_preserves_control_flow(wrapper_type, encounter):
    wrapper = wrapper_type(LightspeedBattleEnv(max_turns=2))
    observation = wrapper.reset(100000, encounter)
    action_mask = observation["action_mask"]
    action = int(np.flatnonzero(action_mask)[0])
    next_observation, reward, terminated, truncated, info = wrapper.step(action)

    assert next_observation["action_mask"].shape == (31,)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert "shuffle_rng" in info
    assert "shuffle_rng" not in next_observation


@pytest.mark.parametrize("wrapper_type", [FlattenWrapper, TokenWrapper])
def test_unknown_visible_category_is_rejected(wrapper_type):
    env = LightspeedBattleEnv()
    source = _copy_observation(env.reset(100000, Encounter.TWO_LOUSE))
    source["hand"][0, 0] = 999999

    with pytest.raises(ValueError, match="card_id.*范围外"):
        wrapper_type(env).transform(source)
