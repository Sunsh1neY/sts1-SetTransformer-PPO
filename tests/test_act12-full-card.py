"""第一、二幕统一全卡入口：完整决策、Boss、事件与路由生命周期。"""
import random
from pathlib import Path

import pytest
import torch

from sts.env.entities import FEATURE_DIMS, collate, encode_observation
from sts.env.ironclad import CONTRACT, IroncladEnv
from sts.models.entities import UnifiedEntityActorCritic

ACTS = CONTRACT['scope']['encounter_acts']
BOSSES = {'SLIME_BOSS', 'THE_GUARDIAN', 'HEXAGHOST', 'AUTOMATON', 'COLLECTOR', 'CHAMP'}
ENCOUNTERS = [name for name in CONTRACT['scope']['encounters'] if ACTS[name] in (1, 2)]


def scene(name, deck=None, hp=80):
    act = ACTS[name]
    return dict(entry_timing='pre_combat_initialization',
                initialization_phase='before_destination_room_entry',
                act=act, floor=17 * act if name in BOSSES else 8 + 17 * (act - 1),
                character='IRONCLAD', ascension=20,
                player=dict(hp=hp, max_hp=hp, gold=100),
                deck=deck or ['Strike_R'] * 3 + ['Defend_R'] * 3 +
                    ['Bash', 'Headbutt', 'True Grit+1', 'Seeing Red'],
                relics=[], potions=[None, None], encounter=name, burning_elite=False)


def start(name, deck=None, hp=80, budget=128, seed=891000):
    env = IroncladEnv(budget)
    return env, env.reset(scene(name, deck, hp), seed, diagnostic=True)


def play(env, obs, name, target=0):
    index = next(i for i, card in enumerate(obs['hand']) if card['name'] == name)
    assert obs['action_mask'][5 * index + target]
    return env.step(dict(kind='NORMAL', snapshot=obs['routing']['snapshot'], action=5 * index + target))


def cards(obs):
    return [card for zone in ('hand', 'draw_pile', 'discard_pile', 'exhaust_pile', 'resolving') for card in obs[zone]]


def test_scope_matches_locked_backend_act12_catalog():
    root = Path(__file__).resolve().parents[1]
    source = (root / 'third_party/sts_lightspeed/include/constants/MonsterEncounters.h').read_text()
    enum = source.split('enum class MonsterEncounter', 1)[1].split('};', 1)[0]
    act1 = enum.split('// Act 1 Weak', 1)[1].split('// Act 2', 1)[0]
    act2 = enum.split('// Act 2', 1)[1].split('// Act 3', 1)[0]
    names = lambda text: {name.strip() for name in text.split(',') if name.strip()}
    assert len(names(act1)) == 20 and len(names(act2)) == 19
    assert {name for name in ENCOUNTERS if ACTS[name] == 1} == names(act1) | {'MUSHROOMS_EVENT', 'LAGAVULIN_EVENT'}
    assert {name for name in ENCOUNTERS if ACTS[name] == 2} == names(act2) | {
        'COLOSSEUM_EVENT_SLAVERS', 'COLOSSEUM_EVENT_NOBS', 'MASKED_BANDITS_EVENT'}
    assert set(ACTS) == set(CONTRACT['scope']['encounters'])
    assert len(ENCOUNTERS) == 44 and not CONTRACT['training_admitted']
    assert FEATURE_DIMS['CARD'] == 116 and FEATURE_DIMS['ENEMY'] == 774


@pytest.mark.parametrize('name', ENCOUNTERS)
@pytest.mark.parametrize('seed', [891000, 891001])
def test_all_act12_full_card_episodes_reach_real_terminal(name, seed):
    env, obs = start(name, seed=seed)
    rng = random.Random(seed)
    for _ in range(128):
        sample = encode_observation(obs)
        collate([sample])
        routes = [route for route, candidate in zip(sample.routes, sample.candidates) if candidate.legal]
        assert routes
        obs, reward, terminated, truncated, info = env.step(rng.choice(routes))
        if terminated or truncated:
            encode_observation(obs)
            assert terminated and not truncated
            assert 'battle_exit' in info and not any(enemy['present'] for enemy in obs['enemies'])
            assert reward == (1 + 0.5 * obs['player']['hp'] / obs['player']['max_hp'] if reward > 0 else 0)
            with pytest.raises(RuntimeError):
                env.step(50)
            return
    pytest.fail('完整决策诊断未结算')


@pytest.mark.parametrize('name', ['SLIME_BOSS', 'THE_GUARDIAN', 'HEXAGHOST', 'MASKED_BANDITS_EVENT'])
def test_wrong_act_or_floor_rejected_by_real_backend(name):
    config = scene(name)
    config['act'] = 3
    with pytest.raises(ValueError, match='幕、楼层'):
        IroncladEnv().reset(config, 891000, diagnostic=True)
    config = scene(name)
    config['floor'] = 46
    with pytest.raises(ValueError, match='幕、楼层'):
        IroncladEnv().reset(config, 891000, diagnostic=True)


def test_slime_boss_goop_and_external_truncation_keep_complete_state():
    env, obs = start('SLIME_BOSS', ['Defend_R'] * 5, budget=1)
    obs, reward, term, trunc, info = env.step(50)
    assert trunc and not term and reward == 0 and 'battle_exit' not in info
    assert sum(card['name'] == 'Slimed' for card in cards(obs)) == 5
    assert any(enemy['present'] for enemy in obs['enemies']) and obs['action_mask'].any()
    encode_observation(obs)


def test_slime_boss_two_splits_replace_routes_and_reset_child_histories():
    env, obs = start('SLIME_BOSS', ['Bludgeon+1'] * 10, hp=500)
    parent = obs['routing']['enemy_refs'][0]
    for _ in range(2):
        obs, *_ = play(env, obs, 'Bludgeon')
        obs, reward, term, trunc, _ = env.step(50)
        assert not term and not trunc and reward == 0
    children = [i for i, enemy in enumerate(obs['enemies']) if enemy['targetable']]
    assert len(children) == 2
    assert parent not in obs['routing']['enemy_refs']
    assert all(obs['enemies'][i]['intent_history_valid'] == [True, False, False] for i in children)
    assert all(obs['enemies'][i]['public_history']['completed_enemy_turns'] == 0 for i in children)
    assert all(obs['action_mask'][i] for i in children)
    encode_observation(obs)
    old_refs = set(ref for ref in obs['routing']['enemy_refs'] if ref is not None)
    obs, *_ = play(env, obs, 'Bludgeon', children[0])
    obs, reward, term, trunc, _ = env.step(50)
    assert not term and not trunc and reward == 0
    assert sum(enemy['targetable'] for enemy in obs['enemies']) == 3
    assert len(set(ref for ref in obs['routing']['enemy_refs'] if ref is not None) - old_refs) == 2
    encode_observation(obs)


def test_guardian_a20_mode_shift_and_sharp_hide_through_full_card_route():
    env, obs = start('THE_GUARDIAN', ['Bludgeon+1'] * 5, hp=500)
    assert obs['enemies'][0]['statuses']['Mode Shift'] == 40
    obs, *_ = play(env, obs, 'Bludgeon')
    assert obs['enemies'][0]['intent_kind'] == 'BUFF'
    obs, *_ = env.step(50)
    assert obs['enemies'][0]['statuses']['Sharp Hide'] == 4
    hp = obs['player']['hp']
    obs, *_ = play(env, obs, 'Bludgeon')
    assert obs['player']['hp'] == hp - 4
    encode_observation(obs)


def test_hexaghost_hp_scaled_divider_and_inferno_upgrade():
    env, obs = start('HEXAGHOST', ['Defend_R'] * 10, hp=1000)
    obs, *_ = env.step(50)
    assert obs['enemies'][0]['intent_damage'] == 84
    assert obs['enemies'][0]['intent_hits'] == 6
    for _ in range(8):
        obs, _, term, trunc, _ = env.step(50)
        assert not term and not trunc
        encode_observation(obs)
    burns = [card for card in cards(obs) if card['name'] == 'Burn']
    assert len(burns) == 9
    assert all(card['upgrade_count'] == 1 and card['magic'] == 4 for card in burns)


def test_act1_event_composition_and_awake_lagavulin():
    _, mushrooms = start('MUSHROOMS_EVENT')
    assert [enemy['name'] for enemy in mushrooms['enemies'] if enemy['present']] == ['FUNGI_BEAST'] * 3
    env, event = start('LAGAVULIN_EVENT')
    _, regular = start('LAGAVULIN')
    assert event['enemies'][0]['intent_kind'] == 'DEBUFF'
    assert event['enemies'][0]['statuses'].get('Asleep', 0) == 0
    assert regular['enemies'][0]['statuses']['Asleep'] == 1
    encode_observation(event)
    event, *_ = env.step(50)
    assert event['player']['statuses']['Strength'] == -2
    assert event['player']['statuses']['Dexterity'] == -2
    assert event['enemies'][0]['intent_damage'] == 20


@pytest.mark.parametrize('name', ['SLIME_BOSS', 'THE_GUARDIAN', 'HEXAGHOST'])
def test_new_boss_full_card_selection_and_shared_model(name):
    env, obs = start(name, ['Seeing Red', 'Defend_R', 'Strike_R', 'Headbutt', 'Double Tap'], hp=500)
    for card in ['Seeing Red', 'Defend_R', 'Strike_R', 'Headbutt']:
        obs, *_ = play(env, obs, card)
    assert obs['decision']['phase'] == 'SELECT_CARD'
    sample = encode_observation(obs)
    model = UnifiedEntityActorCritic().eval()
    with torch.no_grad():
        logits, value = model(collate([sample]))
        reordered, reordered_value = model(collate([sample.permuted(list(reversed(range(len(sample.tokens)))))]))
    torch.testing.assert_close(logits, reordered, atol=1e-5, rtol=1e-5)
    torch.testing.assert_close(value, reordered_value, atol=1e-5, rtol=1e-5)
    assert torch.isfinite(value).all()
    route = next(route for route, candidate in zip(sample.routes, sample.candidates) if candidate.legal)
    obs, *_ = env.step(route)
    assert obs['decision']['phase'] == 'NORMAL'
    encode_observation(obs)
    with pytest.raises((ValueError, RuntimeError), match='过期|失效|引用|选择'):
        env.step(route)
