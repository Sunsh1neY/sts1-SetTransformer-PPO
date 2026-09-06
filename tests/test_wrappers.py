"""V2 双 wrapper 的同源、位置、容量和信息边界测试。"""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from sts import Encounter, FlattenWrapper, LightspeedBattleEnv, TokenWrapper
from sts.env.registry import (
    DEFAULT_CARD_REGISTRY,
    CardDefinition,
    CardLocation,
    CardRegistry,
    TargetKind,
)
from sts.env.wrappers import (
    CARD_CAPACITY,
    CARD_CATEGORICAL_DIM,
    CARD_NUMERIC_DIM,
    ENEMY_ENCODED_DIM,
    FLAT_DIM,
    GLOBAL_ENCODED_DIM,
    MAX_ENEMIES,
    MAX_HAND,
    PILE_CAPACITY,
)


def _copy_observation(observation):
    return deepcopy(observation)


def _assert_wrapped_equal(first, second):
    assert set(first) == set(second)
    for key in first:
        assert np.array_equal(first[key], second[key]), key


def _reshape_flat(flat):
    return {
        "card_categorical": flat["card_categorical"].reshape(
            CARD_CAPACITY, CARD_CATEGORICAL_DIM
        ),
        "card_numeric": flat["card_numeric"].reshape(
            CARD_CAPACITY, CARD_NUMERIC_DIM
        ),
        "card_numeric_known": flat["card_numeric_known"].reshape(
            CARD_CAPACITY, CARD_NUMERIC_DIM
        ),
        "card_valid": flat["card_valid"],
        "enemy_features": flat["enemy_features"].reshape(
            MAX_ENEMIES, ENEMY_ENCODED_DIM
        ),
        "enemy_mask": flat["enemy_mask"],
        "global": flat["global"].reshape(1, GLOBAL_ENCODED_DIM),
        "action_mask": flat["action_mask"],
    }


def test_双输入_shape_dtype_及允许事实完全相同():
    env = LightspeedBattleEnv()
    source = env.reset(100000, Encounter.TWO_LOUSE)
    flat = FlattenWrapper(env).transform(source)
    tokens = TokenWrapper(env).transform(source)

    assert flat["card_categorical"].shape == (80,)
    assert flat["card_numeric"].shape == (20,)
    assert flat["card_numeric_known"].shape == (20,)
    assert flat["card_valid"].shape == (20,)
    assert flat["enemy_features"].shape == (100,)
    assert flat["enemy_mask"].shape == (5,)
    assert flat["global"].shape == (13,)
    assert flat["action_mask"].shape == (31,)
    assert FLAT_DIM == 258

    assert tokens["card_categorical"].shape == (20, 4)
    assert tokens["card_numeric"].shape == (20, 1)
    assert tokens["card_numeric_known"].shape == (20, 1)
    assert tokens["card_valid"].shape == (20,)
    assert tokens["enemy_features"].shape == (5, 20)
    assert tokens["enemy_mask"].shape == (5,)
    assert tokens["global"].shape == (1, 13)
    assert tokens["action_mask"].shape == (31,)

    assert flat["card_categorical"].dtype == tokens["card_categorical"].dtype == np.int64
    assert flat["card_numeric"].dtype == tokens["card_numeric"].dtype == np.float32
    for key in ("card_numeric_known", "card_valid", "enemy_mask", "action_mask"):
        assert flat[key].dtype == tokens[key].dtype == np.bool_
    assert flat["enemy_features"].dtype == tokens["enemy_features"].dtype == np.float32
    assert flat["global"].dtype == tokens["global"].dtype == np.float32
    _assert_wrapped_equal(_reshape_flat(flat), tokens)


def test_前十行保留手牌槽位_后十行按区域拼接():
    env = LightspeedBattleEnv()
    source = env.reset(100000, Encounter.TWO_LOUSE)
    tokens = TokenWrapper(env).transform(source)

    assert tokens["card_valid"][:5].all()
    assert not tokens["card_valid"][5:MAX_HAND].any()
    assert tokens["card_valid"][MAX_HAND:MAX_HAND + 5].all()
    assert not tokens["card_valid"][MAX_HAND + 5:].any()
    assert tokens["card_categorical"][:5, 1].tolist() == [int(CardLocation.HAND)] * 5
    assert tokens["card_categorical"][MAX_HAND:MAX_HAND + 5, 1].tolist() == [
        int(CardLocation.DRAW)
    ] * 5
    assert tokens["card_categorical"][~tokens["card_valid"]].sum() == 0
    assert tokens["card_numeric"][~tokens["card_valid"]].sum() == 0.0


def test_已知零费用与padding由known和valid区分():
    env = LightspeedBattleEnv()
    source = _copy_observation(env.reset(100000, Encounter.TWO_LOUSE))
    source["hand"][0]["cost"] = 0
    tokens = TokenWrapper(env).transform(source)

    assert tokens["card_numeric"][0, 0] == 0.0
    assert tokens["card_numeric_known"][0, 0]
    assert tokens["card_valid"][0]
    assert tokens["card_numeric"][MAX_HAND + 5, 0] == 0.0
    assert not tokens["card_numeric_known"][MAX_HAND + 5, 0]
    assert not tokens["card_valid"][MAX_HAND + 5]


def test_非手牌费用未知但卡牌仍然有效():
    env = LightspeedBattleEnv()
    tokens = TokenWrapper(env).reset(100000, Encounter.TWO_LOUSE)

    rows = slice(MAX_HAND, MAX_HAND + 5)
    assert tokens["card_valid"][rows].all()
    assert not tokens["card_numeric_known"][rows].any()
    assert tokens["card_numeric"][rows].sum() == 0.0


def test_第四类合成卡只扩注册数据即可经过双路径四个区域():
    registry = CardRegistry(
        (*DEFAULT_CARD_REGISTRY.entries,
         CardDefinition(4, 999999, "Synthetic Probe", TargetKind.ENEMY)),
        version=2,
    )
    env = LightspeedBattleEnv(registry=registry)
    source = _copy_observation(env.reset(100000, Encounter.TWO_LOUSE))
    source["hand"][0] = {
        "card_id": 4,
        "location": int(CardLocation.HAND),
        "upgraded": True,
        "cost": 2,
        "cost_known": True,
        "target_kind": int(TargetKind.ENEMY),
    }
    for key, location in (
        ("draw_pile", CardLocation.DRAW),
        ("discard_pile", CardLocation.DISCARD),
        ("exhaust_pile", CardLocation.EXHAUST),
    ):
        source[key].append({
            "card_id": 4,
            "location": int(location),
            "upgraded": False,
            "cost": 0,
            "cost_known": False,
            "target_kind": int(TargetKind.ENEMY),
        })
    source["global"][5:9] = [
        len(source["hand"]),
        len(source["draw_pile"]),
        len(source["discard_pile"]),
        len(source["exhaust_pile"]),
    ]

    flat = FlattenWrapper(env).transform(source)
    tokens = TokenWrapper(env).transform(source)

    _assert_wrapped_equal(_reshape_flat(flat), tokens)
    valid_rows = tokens["card_categorical"][tokens["card_valid"]]
    probe_rows = valid_rows[valid_rows[:, 0] == 4]
    assert probe_rows[:, 1].tolist() == [
        int(CardLocation.HAND),
        int(CardLocation.DRAW),
        int(CardLocation.DISCARD),
        int(CardLocation.EXHAUST),
    ]
    assert probe_rows[:, 2].tolist() == [int(TargetKind.ENEMY)] * 4


def test_相同卡牌没有槽位号特征():
    env = LightspeedBattleEnv()
    source = _copy_observation(env.reset(100000, Encounter.TWO_LOUSE))
    source["hand"][1] = deepcopy(source["hand"][0])
    tokens = TokenWrapper(env).transform(source)

    assert np.array_equal(tokens["card_categorical"][0], tokens["card_categorical"][1])
    assert np.array_equal(tokens["card_numeric"][0], tokens["card_numeric"][1])


def test_手牌换位只移动实体行和对应动作块():
    env = LightspeedBattleEnv()
    source_a = _copy_observation(env.reset(100000, Encounter.TWO_LOUSE))
    source_a["action_mask"][:] = False
    source_a["action_mask"][0:3] = [True, False, False]
    source_a["action_mask"][3:6] = [False, True, False]
    source_a["action_mask"][30] = True

    source_b = _copy_observation(source_a)
    source_b["hand"][0], source_b["hand"][1] = source_b["hand"][1], source_b["hand"][0]
    source_b["action_mask"][0:3] = source_a["action_mask"][3:6]
    source_b["action_mask"][3:6] = source_a["action_mask"][0:3]

    tokens_a = TokenWrapper(env).transform(source_a)
    tokens_b = TokenWrapper(env).transform(source_b)
    assert np.array_equal(tokens_b["card_categorical"][0], tokens_a["card_categorical"][1])
    assert np.array_equal(tokens_b["card_categorical"][1], tokens_a["card_categorical"][0])
    assert np.array_equal(tokens_b["card_categorical"][2:], tokens_a["card_categorical"][2:])
    assert np.array_equal(tokens_b["action_mask"][0:3], tokens_a["action_mask"][3:6])
    assert np.array_equal(tokens_b["action_mask"][3:6], tokens_a["action_mask"][0:3])


def test_敌人换位移动目标列_无目标牌仍使用环境列零():
    env = LightspeedBattleEnv()
    source_a = _copy_observation(env.reset(100000, Encounter.TWO_LOUSE))
    enemy_slot = next(
        index for index, card in enumerate(source_a["hand"])
        if card["target_kind"] == int(TargetKind.ENEMY)
    )
    no_target_slot = next(
        index for index, card in enumerate(source_a["hand"])
        if card["target_kind"] == int(TargetKind.NO_TARGET)
    )
    source_a["action_mask"][:] = False
    source_a["action_mask"][enemy_slot * 3:enemy_slot * 3 + 3] = [True, False, False]
    source_a["action_mask"][no_target_slot * 3] = True
    source_a["action_mask"][30] = True

    source_b = _copy_observation(source_a)
    source_b["enemies"][[0, 1]] = source_b["enemies"][[1, 0]]
    source_b["enemy_mask"][[0, 1]] = source_b["enemy_mask"][[1, 0]]
    start = enemy_slot * 3
    source_b["action_mask"][start:start + 3] = [False, True, False]

    tokens_a = TokenWrapper(env).transform(source_a)
    tokens_b = TokenWrapper(env).transform(source_b)
    assert np.array_equal(tokens_b["enemy_features"][0], tokens_a["enemy_features"][1])
    assert np.array_equal(tokens_b["enemy_features"][1], tokens_a["enemy_features"][0])
    assert tokens_a["action_mask"][start:start + 3].tolist() == [True, False, False]
    assert tokens_b["action_mask"][start:start + 3].tolist() == [False, True, False]
    assert tokens_a["action_mask"][no_target_slot * 3]
    assert tokens_b["action_mask"][no_target_slot * 3]


def test_结束回合后location反映卡牌从手牌移入弃牌堆():
    env = LightspeedBattleEnv()
    before = env.reset(100000, Encounter.TWO_LOUSE)
    after, *_ = env.step(30)
    before_tokens = TokenWrapper(env).transform(before)
    after_tokens = TokenWrapper(env).transform(after)

    assert before["global"][5:9].tolist() == [5, 5, 0, 0]
    assert after["global"][5:9].tolist() == [5, 0, 5, 0]
    assert before_tokens["card_categorical"][MAX_HAND:MAX_HAND + 5, 1].tolist() == [2] * 5
    assert after_tokens["card_categorical"][MAX_HAND:MAX_HAND + 5, 1].tolist() == [3] * 5


def test_隐藏调试字段和无效敌人残留不进入输入():
    env = LightspeedBattleEnv()
    source = env.reset(100000, Encounter.TWO_LOUSE)
    changed = _copy_observation(source)
    changed["enemies"][~changed["enemy_mask"]] = 654321
    changed["seed"] = 999999
    changed["draw_order"] = [3, 1, 2]

    _assert_wrapped_equal(
        FlattenWrapper(env).transform(source), FlattenWrapper(env).transform(changed)
    )
    _assert_wrapped_equal(
        TokenWrapper(env).transform(source), TokenWrapper(env).transform(changed)
    )


@pytest.mark.parametrize("wrapper_type", [FlattenWrapper, TokenWrapper])
def test_transform确定且每次返回独立数组(wrapper_type):
    env = LightspeedBattleEnv()
    source = env.reset(100000, Encounter.TWO_LOUSE)
    wrapper = wrapper_type(env)
    first = wrapper.transform(source)
    second = wrapper.transform(source)

    _assert_wrapped_equal(first, second)
    assert all(not np.shares_memory(first[key], second[key]) for key in first)


@pytest.mark.parametrize("wrapper_type", [FlattenWrapper, TokenWrapper])
@pytest.mark.parametrize("encounter", list(Encounter))
def test_wrapper保留环境控制流(wrapper_type, encounter):
    wrapper = wrapper_type(LightspeedBattleEnv(max_turns=2))
    observation = wrapper.reset(100000, encounter)
    action = int(np.flatnonzero(observation["action_mask"])[0])
    next_observation, reward, terminated, truncated, info = wrapper.step(action)

    assert next_observation["action_mask"].shape == (31,)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert "shuffle_rng" in info


@pytest.mark.parametrize("wrapper_type", [FlattenWrapper, TokenWrapper])
def test_未知card_id在写张量前报错(wrapper_type):
    env = LightspeedBattleEnv()
    source = _copy_observation(env.reset(100000, Encounter.TWO_LOUSE))
    source["hand"][0]["card_id"] = 999999

    with pytest.raises(ValueError, match="未知 registry_id"):
        wrapper_type(env).transform(source)


@pytest.mark.parametrize("wrapper_type", [FlattenWrapper, TokenWrapper])
def test_location与所在列表不一致时报错(wrapper_type):
    env = LightspeedBattleEnv()
    source = _copy_observation(env.reset(100000, Encounter.TWO_LOUSE))
    source["draw_pile"][0]["location"] = int(CardLocation.DISCARD)

    with pytest.raises(ValueError, match="location 应为 2"):
        wrapper_type(env).transform(source)


@pytest.mark.parametrize("wrapper_type", [FlattenWrapper, TokenWrapper])
def test_非手牌超过容量时拒绝截断(wrapper_type):
    env = LightspeedBattleEnv()
    source = _copy_observation(env.reset(100000, Encounter.TWO_LOUSE))
    while sum(len(source[key]) for key in ("draw_pile", "discard_pile", "exhaust_pile")) <= PILE_CAPACITY:
        source["draw_pile"].append(deepcopy(source["draw_pile"][0]))
    source["global"][6] = len(source["draw_pile"])

    with pytest.raises(ValueError, match="超过 pile_capacity=10"):
        wrapper_type(env).transform(source)
