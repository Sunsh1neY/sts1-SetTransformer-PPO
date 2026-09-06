"""Week 4 T5 验收入口的配置、序列化、奖励和小规模闭环测试。"""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from scripts.run_week4_t5 import (
    PATH_NAMES,
    EpisodeConfig,
    _check_reward,
    build_configs,
    replay_trace,
    run_determinism,
    run_path,
    serialize_semantic,
)
from sts import Encounter, LightspeedBattleEnv


def test_正式配置是一万份且三遭遇按约定分配():
    configs = build_configs()

    assert len(configs) == 10_000
    assert len({(item.seed, item.encounter) for item in configs}) == 10_000
    assert configs[0].seed == 100_000
    assert configs[-1].seed == 109_999
    assert min(item.agent_seed for item in configs) >= 100_000
    assert {
        encounter: sum(item.encounter == encounter for item in configs)
        for encounter in Encounter
    } == {
        Encounter.JAW_WORM: 3334,
        Encounter.CULTIST: 3333,
        Encounter.TWO_LOUSE: 3333,
    }


def test_拒绝把评估种子混进t5配置():
    with pytest.raises(ValueError, match="seed >= 100000"):
        build_configs(3, seed_start=999)


def test_规范序列化固定字段顺序dtype与字节序():
    observation = LightspeedBattleEnv().reset(100000, Encounter.TWO_LOUSE)
    reordered = dict(reversed(list(observation.items())))
    payload = serialize_semantic(observation)

    assert payload == serialize_semantic(reordered)
    changed = {key: value.copy() for key, value in observation.items()}
    changed["action_mask"][0] = ~changed["action_mask"][0]
    assert payload != serialize_semantic(changed)
    assert b'"dtype":"<i4"' in payload
    assert b'"dtype":"|b1"' in payload


def test_规范序列化会记录逐牌location和消耗堆():
    observation = LightspeedBattleEnv().reset(100000, Encounter.TWO_LOUSE)
    moved = deepcopy(observation)
    card = moved["draw_pile"].pop(0)
    card["location"] = 3  # DISCARD
    moved["discard_pile"].append(card)
    moved["global"][6:8] = [len(moved["draw_pile"]), len(moved["discard_pile"])]

    assert serialize_semantic(observation) != serialize_semantic(moved)

    without_exhaust = dict(observation)
    del without_exhaust["exhaust_pile"]
    with pytest.raises(KeyError, match="exhaust_pile"):
        serialize_semantic(without_exhaust)


def test_奖励检查落实d18与d20():
    victory = {"outcome": 1, "player_hp": 40, "player_max_hp": 80}
    loss = {"outcome": 2, "player_hp": 0, "player_max_hp": 80}

    assert _check_reward([0.0, 1.25], True, False, victory)
    assert _check_reward([0.0, 0.0], True, False, loss)
    assert not _check_reward([0.1, 1.25], True, False, victory)
    assert not _check_reward([0.0], False, False, loss)
    assert not _check_reward([0.0], True, True, loss)


@pytest.mark.parametrize("path_name", PATH_NAMES)
def test_四路径小规模闭环无异常非法动作超时且奖励合规(path_name):
    configs = build_configs(6)
    result = run_path(path_name, configs)

    assert result.total.episodes == 6
    assert result.total.steps > 0
    assert result.total.exceptions == 0
    assert result.total.illegal_actions == 0
    assert result.total.hard_timeouts == 0
    assert result.total.reward_failures == 0
    assert result.total.elapsed_seconds > 0
    assert result.total.wins + result.total.losses == 6
    assert all(
        bucket.episodes == 2 and bucket.elapsed_seconds > 0
        for bucket in result.by_encounter.values()
    )


def test_四路径相同agent状态产生相同语义轨迹():
    config = EpisodeConfig(0, 100000, Encounter.TWO_LOUSE, 20260905000)
    traces = {name: replay_trace(name, config) for name in PATH_NAMES}
    keys = (
        "step",
        "semantic_observation_sha256",
        "action_mask_hex",
        "action",
        "next_semantic_observation_sha256",
        "next_action_mask_hex",
        "reward_hex",
        "terminated",
        "truncated",
        "info",
    )
    comparable = {
        name: [{key: row[key] for key in keys} for row in trace]
        for name, trace in traces.items()
    }

    assert all(value == comparable["raw-pybind"] for value in comparable.values())


def test_小规模确定性验收包含路径内与跨路径比较():
    result = run_determinism(build_configs(3), count=3)

    assert result["episodes"] == 3
    assert result["encounter_counts"] == {
        "jaw-worm": 1,
        "cultist": 1,
        "two-louse": 1,
    }
    assert result["runs_per_path_episode"] == 2
    assert result["within_path_failures"] == []
    assert result["cross_path_semantic_failures"] == []
    assert result["passed"] is True
