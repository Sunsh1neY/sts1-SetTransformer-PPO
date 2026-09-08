"""D25 S2：真实轨迹标签、反捷径样本及失败诊断的回归测试。"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import replace

import numpy as np
import pytest
import torch

from sts import Encounter, FlattenWrapper, LightspeedBattleEnv
from sts.env.wrappers import CARD_CAPACITY
from sts.models.overfit import (
    OverfitConfig,
    collect_dataset,
    serialize_dataset,
    swapped_sample,
    train_overfit,
    validate_dataset,
)


@pytest.fixture(scope="module")
def dataset():
    """全组共用确定性采样结果；破坏性测试自行复制。"""

    return collect_dataset(OverfitConfig())


def test_s2_默认采样和序列化可逐字节复现(dataset):
    expected = serialize_dataset(*dataset)
    repeated = serialize_dataset(*collect_dataset(OverfitConfig()))

    assert repeated == expected


def test_s2_原样本均衡且捷径基线无法达到门槛(dataset):
    samples, pairs, episodes = dataset
    config = OverfitConfig()
    originals = [sample for sample in samples if sample["augmentation"] is None]
    stats = validate_dataset(samples, pairs)

    assert len(episodes) == 24
    assert len(originals) == 48
    assert Counter(sample["encounter"] for sample in originals) == {
        encounter.value: 16 for encounter in Encounter
    }
    assert len(pairs) >= 6
    assert all(sample["observation"]["action_mask"].sum() >= 2 for sample in samples)
    assert stats["mask_only_max_accuracy"] < 0.95 < config.min_accuracy
    assert stats["majority_action_accuracy"] < config.min_accuracy
    assert stats["constant_value_mse"] > config.max_value_mse
    assert stats["return_min"] == 0.0
    assert stats["return_unique"] > 2


def test_s2_逐局重放确认动作观测及真实gamma1回报来源(dataset):
    samples, _, episodes = dataset
    originals = [sample for sample in samples if sample["augmentation"] is None]
    episode_lookup = {
        (episode["env_seed"], episode["agent_seed"], episode["encounter"]): episode
        for episode in episodes
    }
    original_lookup = {
        (sample["env_seed"], sample["agent_seed"], sample["encounter"], sample["step"]): sample
        for sample in originals
    }
    checked_originals = 0
    for episode in episodes:
        env = FlattenWrapper(LightspeedBattleEnv())
        observation = env.reset(episode["env_seed"], Encounter(episode["encounter"]))
        assert env.gamma == 1.0
        assert episode["env_seed"] >= 100_000
        assert episode["agent_seed"] >= 100_000
        assert len(episode["actions"]) == len(episode["rewards"])
        for step, action in enumerate(episode["actions"]):
            key = (episode["env_seed"], episode["agent_seed"], episode["encounter"], step)
            if key in original_lookup:
                original = original_lookup[key]
                assert original["action"] == action
                assert original["observation"].keys() == observation.keys()
                for field in observation:
                    np.testing.assert_array_equal(original["observation"][field], observation[field])
                checked_originals += 1
            observation, reward, terminated, truncated, info = env.step(action)
            assert reward == episode["rewards"][step]
            assert (terminated or truncated) == (step == len(episode["actions"]) - 1)
        assert terminated == episode["terminated"]
        assert truncated == episode["truncated"]
        assert (info["outcome"] == 1) == episode["won"]
        assert all(reward == 0.0 for reward in episode["rewards"][:-1])
        expected = 1 + 0.5 * info["player_hp"] / info["player_max_hp"] if episode["won"] else 0.0
        assert sum(episode["rewards"]) == pytest.approx(expected)

    assert checked_originals == 48
    # 增广样本保留原轨迹 provenance 和回报；动作标签由换位路由单独检查。
    for sample in samples:
        episode = episode_lookup[(sample["env_seed"], sample["agent_seed"], sample["encounter"])]
        assert 0 <= sample["step"] < len(episode["actions"])
        assert sample["return_to_go"] == pytest.approx(sum(episode["rewards"][sample["step"]:]))


def test_s2_换位配对同mask不同动作且不污染原观测(dataset):
    samples, pairs, _ = dataset
    for first, second in pairs:
        original, augmented = samples[first], samples[second]
        before = deepcopy(original)
        actual = swapped_sample(original)
        assert actual is not None
        assert actual["action"] == augmented["action"] != original["action"]
        assert actual["return_to_go"] == original["return_to_go"]
        np.testing.assert_array_equal(actual["observation"]["action_mask"], original["observation"]["action_mask"])
        source_slot, destination_slot = actual["augmentation"]["swap_hand_slots"]
        assert actual["action"] == destination_slot * 3 + original["action"] % 3
        assert source_slot == original["action"] // 3
        assert actual["observation"]["action_mask"][actual["action"]]
        for field in original["observation"]:
            np.testing.assert_array_equal(original["observation"][field], before["observation"][field])
            np.testing.assert_array_equal(actual["observation"][field], augmented["observation"][field])
            assert not np.shares_memory(actual["observation"][field], original["observation"][field])
            if field in {"card_categorical", "card_numeric", "card_numeric_known", "card_valid"}:
                expected = original["observation"][field].reshape(CARD_CAPACITY, -1).copy()
                expected[[source_slot, destination_slot]] = expected[[destination_slot, source_slot]]
                np.testing.assert_array_equal(actual["observation"][field].reshape(CARD_CAPACITY, -1), expected)
            else:
                np.testing.assert_array_equal(actual["observation"][field], original["observation"][field])


@pytest.mark.parametrize("field", ["env_seed_start", "agent_seed_start", "selection_seed"])
@pytest.mark.parametrize("seed", [0, 999, 99_999])
def test_s2_拒绝评估或保留区间seed(field, seed):
    with pytest.raises(ValueError, match="seed >= 100000"):
        OverfitConfig(**{field: seed})


@pytest.mark.parametrize("bad_action", [-1, 31, None])
def test_s2_拒绝非法动作标签(dataset, bad_action):
    samples, pairs, _ = deepcopy(dataset)
    if bad_action is None:
        bad_action = int(np.flatnonzero(~samples[0]["observation"]["action_mask"])[0])
    samples[0]["action"] = bad_action
    with pytest.raises(ValueError):
        validate_dataset(samples, pairs)


def test_s2_拒绝重复观测和没有换位对(dataset):
    samples, pairs, _ = dataset
    with pytest.raises(ValueError, match="重复观测"):
        validate_dataset([*samples, deepcopy(samples[0])], pairs)
    with pytest.raises(ValueError, match="同 mask 不同动作对"):
        validate_dataset(samples, [])


def test_s2_拒绝只有一个合法动作的无选择样本(dataset):
    samples, pairs, _ = deepcopy(dataset)
    mask = samples[0]["observation"]["action_mask"]
    mask[:] = False
    mask[samples[0]["action"]] = True
    with pytest.raises(ValueError, match="至少两个合法动作"):
        validate_dataset(samples, pairs)


def test_s2_短训没有崩溃仍不能被误记为通过(dataset):
    samples, pairs, _ = dataset
    config = replace(OverfitConfig(), updates=5, log_every=5)
    previous_threads = torch.get_num_threads()
    try:
        torch.set_num_threads(1)
        _, result = train_overfit(samples, pairs, config, model_seed=500_000)
    finally:
        torch.set_num_threads(previous_threads)

    assert [point["update"] for point in result["history"]] == [0, 5]
    assert result["checks"]["gradients_finite"]
    assert result["checks"]["illegal_probability_zero"]
    assert all(
        np.isfinite(point[metric])
        for point in result["history"]
        for metric in ("policy_loss", "value_mse", "accuracy", "swap_pair_accuracy")
    )
    assert not result["passed"]
    assert not all(result["checks"].values())
