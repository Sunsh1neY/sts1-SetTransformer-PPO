"""lightspeed C++ 战斗适配器的最小接口测试。"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest


_BUILD_DIR = Path(__file__).parents[1] / "third_party" / "sts_lightspeed" / "build"
if str(_BUILD_DIR) not in sys.path:
    sys.path.insert(0, str(_BUILD_DIR))

try:
    import slaythespire
except ImportError as exc:  # 本地未构建扩展时保留其余 Python 测试可运行
    slaythespire = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


pytestmark = pytest.mark.skipif(
    slaythespire is None,
    reason=f"C++ 扩展尚未构建: {_IMPORT_ERROR}",
)


def _global(observation):
    return getattr(observation, "global")


def _new_env(max_turns=50):
    return slaythespire.IroncladBattleEnv(max_turns=max_turns)


def _reset(env):
    return env.reset(142, slaythespire.MonsterEncounter.JAW_WORM, 0)


def _rows(values, fields):
    width = len(fields)
    return [dict(zip(fields, values[i:i + width])) for i in range(0, len(values), width)]


def _hand(observation):
    return _rows(observation.hand, slaythespire.HAND_FEATURES)


def _enemies(observation):
    return _rows(observation.enemies, slaythespire.ENEMY_FEATURES)


def _player(observation):
    return dict(zip(slaythespire.GLOBAL_FEATURES, _global(observation)))


def _attack_action(observation):
    attacks = {int(slaythespire.CardId.STRIKE_RED), int(slaythespire.CardId.BASH)}
    return next((action for action, legal in enumerate(observation.action_mask[:-1])
                 if legal and _hand(observation)[action // 3]["card_id"] in attacks), None)


def test_reset_is_deterministic():
    env = _new_env()
    first = _reset(env)
    first_mask = env.action_mask()
    second = _reset(env)
    second_mask = env.action_mask()

    assert first.hand == second.hand
    assert first.enemies == second.enemies
    assert _global(first) == _global(second)
    assert first.hand_mask == second.hand_mask
    assert first.enemy_mask == second.enemy_mask
    assert first_mask == second_mask
    assert len(first_mask) == 31
    assert any(first_mask)


def test_same_actions_produce_same_snapshots():
    actions = [0, 1, 2, 30]
    env_a = _new_env()
    env_b = _new_env()
    _reset(env_a)
    _reset(env_b)

    for action in actions:
        if not env_a.action_mask()[action]:
            continue
        result_a = env_a.step(action)
        result_b = env_b.step(action)
        assert result_a.observation.hand == result_b.observation.hand
        assert result_a.observation.enemies == result_b.observation.enemies
        assert _global(result_a.observation) == _global(result_b.observation)
        assert result_a.reward == result_b.reward
        assert result_a.terminated == result_b.terminated
        assert result_a.truncated == result_b.truncated
        assert result_a.info == result_b.info
        if result_a.terminated or result_a.truncated:
            break


def test_action_mask_matches_legality_and_rejects_invalid_action():
    env = _new_env()
    _reset(env)
    mask = env.action_mask()
    assert all(isinstance(value, bool) for value in mask)

    with pytest.raises((ValueError, IndexError, RuntimeError)):
        env.step(-1)
    with pytest.raises((ValueError, IndexError, RuntimeError)):
        env.step(31)

    legal_action = next(index for index, allowed in enumerate(mask) if allowed)
    result = env.step(legal_action)
    assert math.isfinite(result.reward)
    assert len(result.observation.action_mask) == 31


def test_max_turns_is_a_terminal_loss_and_reset_clears_timeout():
    env = _new_env(max_turns=1)
    _reset(env)
    assert env.action_mask()[30]
    result = env.step(30)
    assert result.terminated is True
    assert result.truncated is False
    assert result.info["timeout"] == 1
    assert result.reward == 0
    assert all(value is False for value in env.action_mask())
    with pytest.raises(RuntimeError, match="finished"):
        env.step(30)
    obs = _reset(env)
    action = next(i for i, legal in enumerate(obs.action_mask[:-1]) if legal)
    result = env.step(action)
    assert result.terminated is False
    assert result.info["timeout"] == 0


def test_reward_is_finite_and_gamma_is_exposed():
    env = slaythespire.IroncladBattleEnv(max_turns=50, gamma=1)
    _reset(env)
    assert env.gamma == 1
    action = next(index for index, allowed in enumerate(env.action_mask()) if allowed)
    result = env.step(action)
    assert math.isfinite(result.reward)
    assert isinstance(result.info["ai_rng"], int)
    assert isinstance(result.info["monster_hp_rng"], int)


@pytest.mark.parametrize("gamma", [0.9, 0, -1, float("nan"), float("inf")])
def test_discount_cannot_silently_change_the_score(gamma):
    with pytest.raises(ValueError, match="gamma must be 1"):
        slaythespire.IroncladBattleEnv(gamma=gamma)


def test_reset_rejects_encounters_without_a_verified_observation():
    env = _new_env()
    with pytest.raises(ValueError, match="outside the minimal"):
        env.reset(142, slaythespire.MonsterEncounter.GREMLIN_GANG, 0)
    with pytest.raises(ValueError, match="ascension 0"):
        env.reset(142, slaythespire.MonsterEncounter.JAW_WORM, 1)


def test_defend_has_one_action_while_attacks_keep_both_targets():
    env = _new_env()
    obs = env.reset(142, slaythespire.MonsterEncounter.TWO_LOUSE, 0)
    defend_slots = []
    attack_slots = []
    for slot, card in enumerate(_hand(obs)):
        if not obs.hand_mask[slot]:
            continue
        targets = obs.action_mask[slot * 3:slot * 3 + 3]
        if card["card_id"] == int(slaythespire.CardId.DEFEND_RED):
            defend_slots.append(slot)
            assert targets == [True, False, False]
        else:
            attack_slots.append(slot)
            assert targets == [True, True, False]
    assert defend_slots and attack_slots
    with pytest.raises(ValueError, match="not legal"):
        env.step(defend_slots[0] * 3 + 1)
    assert env.observation().hand == obs.hand
    result = env.step(defend_slots[0] * 3)
    assert _player(result.observation)["block"] == 5
    assert _player(result.observation)["energy"] == 2


@pytest.mark.parametrize("seed", [100000, 100001, 100002])
def test_winning_return_equals_the_terminal_score(seed):
    env = _new_env()
    obs = env.reset(seed, slaythespire.MonsterEncounter.CULTIST, 0)
    rewards = []
    for _ in range(250):
        action = _attack_action(obs)
        if action is None:
            action = next(i for i, legal in enumerate(obs.action_mask) if legal)
        result = env.step(action)
        rewards.append(result.reward)
        obs = result.observation
        if result.terminated or result.truncated:
            break
    else:
        pytest.fail("战斗未在有限步数内结束")
    assert result.terminated and not result.truncated
    assert result.info["timeout"] == 0
    assert result.info["player_hp"] > 0
    assert _player(obs)["total_enemy_hp"] == 0
    expected = 1 + 0.5 * result.info["player_hp"] / result.info["player_max_hp"]
    assert rewards[:-1] == [0] * (len(rewards) - 1)
    assert sum(rewards) == pytest.approx(expected)
    with pytest.raises(RuntimeError, match="finished"):
        env.step(30)


@pytest.mark.parametrize("deal_damage", [False, True])
@pytest.mark.parametrize("max_turns", [1, 50])
def test_loss_and_timeout_have_zero_return_regardless_of_damage(deal_damage, max_turns):
    env = _new_env(max_turns=max_turns)
    obs = env.reset(100000, slaythespire.MonsterEncounter.CULTIST, 0)
    rewards = []
    if deal_damage:
        action = _attack_action(obs)
        assert action is not None
        result = env.step(action)
        rewards.append(result.reward)
        assert _player(result.observation)["total_enemy_hp"] < _player(obs)["total_enemy_hp"]
    for _ in range(50):
        result = env.step(30)
        rewards.append(result.reward)
        if result.terminated or result.truncated:
            break
    else:
        pytest.fail("失败或超时未结束战斗")
    assert result.terminated and not result.truncated
    assert result.info["timeout"] == (1 if max_turns == 1 else 0)
    if max_turns == 50:
        assert result.info["player_hp"] <= 0
    assert rewards == [0] * len(rewards)


def test_card_costs_and_current_cultist_status_are_visible():
    env = _new_env()
    obs = env.reset(100000, slaythespire.MonsterEncounter.CULTIST, 0)
    for slot, card in enumerate(_hand(obs)):
        if obs.hand_mask[slot]:
            assert card["cost"] == (2 if card["card_id"] == int(slaythespire.CardId.BASH) else 1)
    enemy = _enemies(obs)[0]
    assert enemy["intent"] == int(slaythespire.BattleIntent.BUFF)
    assert enemy["intent_damage"] == enemy["intent_hits"] == 0
    assert enemy["ritual"] == enemy["curl_up"] == 0
    obs = env.step(30).observation
    enemy = _enemies(obs)[0]
    assert enemy["ritual"] == 3
    assert enemy["curl_up"] == 0
    assert enemy["intent"] == int(slaythespire.BattleIntent.ATTACK)
    assert enemy["intent_damage"] == 6
    assert enemy["intent_hits"] == 1
    hp_before = _player(obs)["hp"]
    obs = env.step(30).observation
    assert hp_before - _player(obs)["hp"] == 6
    assert _enemies(obs)[0]["strength"] == 3
    assert _enemies(obs)[0]["intent_damage"] == 9


def test_louse_curl_up_disappears_after_an_attack():
    env = _new_env()
    obs = env.reset(100000, slaythespire.MonsterEncounter.TWO_LOUSE, 0)
    enemy = _enemies(obs)[0]
    assert enemy["curl_up"] > 0
    action = _attack_action(obs)
    assert action is not None and action % 3 == 0
    after = _enemies(env.step(action).observation)[0]
    assert after["hp"] < enemy["hp"]
    assert after["curl_up"] == 0
    assert after["block"] == enemy["curl_up"]


def test_player_weak_is_visible_and_explains_reduced_strike_damage():
    # 从正常 reset/step 找到吐网场景，不添加仅供测试使用的内部状态修改接口。
    env = _new_env()
    for seed in range(100000, 100064):
        obs = env.reset(seed, slaythespire.MonsterEncounter.TWO_LOUSE, 0)
        if not any(e["intent"] == int(slaythespire.BattleIntent.DEBUFF) for e in _enemies(obs)):
            continue
        obs = env.step(30).observation
        slot = next((i for i, card in enumerate(_hand(obs))
                     if obs.hand_mask[i] and card["card_id"] == int(slaythespire.CardId.STRIKE_RED)), None)
        if slot is not None:
            break
    else:
        pytest.fail("未找到吐网后可打出打击的固定种子场景")
    assert _player(obs)["weak"] > 0
    assert _player(obs)["vulnerable"] == _player(obs)["strength"] == 0
    enemy_hp = _enemies(obs)[0]["hp"]
    result = env.step(slot * 3)
    assert enemy_hp - _enemies(result.observation)[0]["hp"] == 4


def test_bash_exposes_vulnerable_in_the_observation():
    env = _new_env()
    for seed in range(100000, 100016):
        obs = env.reset(seed, slaythespire.MonsterEncounter.CULTIST, 0)
        slot = next((i for i, card in enumerate(_hand(obs))
                     if obs.hand_mask[i] and card["card_id"] == int(slaythespire.CardId.BASH)), None)
        if slot is not None:
            break
    else:
        pytest.fail("未找到初始手牌中的痛击")
    result = env.step(slot * 3)
    assert _enemies(result.observation)[0]["vulnerable"] == 2
