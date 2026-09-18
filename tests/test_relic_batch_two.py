"""Second-batch expectations derived from the local original-game audit."""
import json

import pytest
import torch

from sts.env.ironclad import CONTRACT
from sts.env.relics import RelicEnv
from sts.env.relic_state import BY_NAME, DIMENSION
from sts.models.apath import APathActorCritic, batch_samples, encode
from sts.train.apath import bind_route, plain_route, sample_digest
from test_relic_state import scene, play

BATCH = ['Bag of Marbles', 'Red Mask', 'Clockwork Souvenir', 'Preserved Insect',
         "Slaver's Collar", 'Black Blood', 'Meat on the Bone', 'Orichalcum']
ACT12 = [n for n, act in CONTRACT['scope']['encounter_acts'].items() if act <= 2]


def start(relics=(), *, encounter='JAW_WORM', hp=70, max_hp=80, deck=None, max_actions=512):
    s = scene(relics, deck=deck, encounter=encounter)
    s['act'] = CONTRACT['scope']['encounter_acts'][encounter]
    s['floor'] = 1 if s['act'] == 1 else 18
    s['player'].update(hp=hp, max_hp=max_hp)
    env = RelicEnv(max_actions=max_actions)
    return env, env.reset(s, 100123, diagnostic=True), s


def status(entity, name):
    return entity['statuses'].get(name, 0)


@pytest.mark.parametrize('relic,power', [('Bag of Marbles', 'Vulnerable'), ('Red Mask', 'Weak')])
def test_opening_enemy_debuff_duration_artifact_and_no_repeat(relic, power):
    env, o, _ = start([relic])
    assert status(o['enemies'][0], power) == 1
    if relic == 'Bag of Marbles':
        before = o['enemies'][0]['hp']
        o = play(env, o)[0]
        assert before - o['enemies'][0]['hp'] == 9
    else:
        _, base, _ = start()
        assert o['enemies'][0]['intent_damage'] == int(base['enemies'][0]['intent_damage'] * .75)
    o = env.step(50)[0]
    assert status(o['enemies'][0], power) == 0
    o = env.step(50)[0]
    assert status(o['enemies'][0], power) == 0
    _, o, _ = start([relic], encounter='THREE_SENTRIES')
    assert all(status(m, power) == 0 and status(m, 'Artifact') == 0 for m in o['enemies'] if m['present'])


def test_clockwork_blocks_one_real_debuff_without_reapplication():
    env, o, _ = start(['Clockwork Souvenir'], deck=['Flex'] * 10)
    assert status(o['player'], 'Artifact') == 1
    o = play(env, o, 'Flex')[0]
    assert status(o['player'], 'Artifact') == 0
    assert status(o['player'], 'Strength') == 2
    assert status(o['player'], 'Lose Strength') == 0
    o = env.step(50)[0]
    assert status(o['player'], 'Artifact') == 0 and status(o['player'], 'Strength') == 2
    o = play(env, o, 'Flex')[0]
    assert status(o['player'], 'Lose Strength') == 2
    o = env.step(50)[0]
    assert status(o['player'], 'Strength') == 2


@pytest.mark.parametrize('encounter,elite,boss', [
    ('JAW_WORM',False,False), ('GREMLIN_NOB',True,False),
    ('THREE_SENTRIES',True,False), ('THE_GUARDIAN',False,True),
    ('SNECKO',False,False), ('BOOK_OF_STABBING',True,False),
    ('GREMLIN_LEADER',True,False), ('COLLECTOR',False,True),
    ('COLOSSEUM_EVENT_NOBS',False,False), ('LAGAVULIN_EVENT',False,False)])
def test_insect_and_collar_encounter_conditions(encounter, elite, boss):
    _, baseline, _ = start(encounter=encounter)
    env, o, _ = start(['Preserved Insect', "Slaver's Collar"], encounter=encounter)
    assert o['player']['energy'] == baseline['player']['energy'] + int(elite or boss)
    for m, b in zip(o['enemies'], baseline['enemies']):
        assert m['max_hp'] == b['max_hp']
        assert m['hp'] == (min(b['hp'], int(b['max_hp'] * .75)) if elite and b['present'] else b['hp'])
    o = env.step(50)[0]
    assert o['player']['energy'] == 3 + int(elite or boss)
    # Reset must not carry elite energy into a subsequent ordinary battle.
    ordinary = scene(['Preserved Insect', "Slaver's Collar"])
    assert env.reset(ordinary, 100124, diagnostic=True)['player']['energy'] == 3


@pytest.mark.parametrize('hp,max_hp', [(39,80),(40,80),(41,80),(40,81),(41,81),(75,80),(80,80)])
@pytest.mark.parametrize('relics', [['Black Blood'], ['Meat on the Bone'],
    ['Burning Blood','Meat on the Bone'], ['Meat on the Bone','Burning Blood'],
    ['Black Blood','Meat on the Bone'], ['Meat on the Bone','Black Blood']])
def test_victory_healing_threshold_order_cap_and_reward_once(hp, max_hp, relics):
    env, o, _ = start(relics, hp=hp, max_hp=max_hp, deck=['Searing Blow+10']*10)
    o, reward, term, trunc, info = play(env, o, 'Searing Blow')
    assert term and not trunc and info['battle_won']
    expected = hp
    if 'Meat on the Bone' in relics and hp <= max_hp / 2:
        expected = min(max_hp, expected+12)
    if 'Burning Blood' in relics:
        expected = min(max_hp, expected+6)
    if 'Black Blood' in relics:
        expected = min(max_hp, expected+12)
    assert info['pre_exit_hp'] == hp
    assert info['post_exit_hp'] == info['player_hp'] == o['player']['hp'] == expected
    assert reward == pytest.approx(2+(expected-hp)/max_hp)
    assert info['reward_accounting']['hp_end'] == expected
    with pytest.raises(RuntimeError):
        env.step(50)


def test_burning_blood_no_double_internal_heal_and_no_heal_on_loss_or_truncation():
    env, o, _ = start(['Burning Blood'], hp=40, deck=['Searing Blow+10']*10)
    o, _, _, _, info = play(env, o, 'Searing Blow')
    assert o['player']['hp'] == info['post_exit_hp'] == 46
    for relic in ['Black Blood','Meat on the Bone']:
        env, _, _ = start([relic], hp=1, deck=['Defend_R']*10)
        o, reward, term, trunc, info = env.step(50)
        assert term and not trunc and o['player']['hp'] == 0
        assert reward == pytest.approx(-1/80)
        env, _, _ = start([relic], hp=40, encounter='LAGAVULIN', max_actions=1)
        o, reward, term, trunc, info = env.step(50)
        assert not term and trunc and reward == 0 and 'post_exit_hp' not in info
        assert o['player']['hp'] == 40
    with pytest.raises(ValueError, match='replaces'):
        start(['Burning Blood','Black Blood'])


def test_orichalcum_zero_positive_block_and_metallicize_interaction():
    env, o, _ = start(['Orichalcum'])
    damage = o['enemies'][0]['intent_damage']
    assert damage > 6
    after = env.step(50)[0]
    assert after['player']['hp'] == 70-(damage-6)
    env, o, _ = start(['Orichalcum'], deck=['Defend_R']*10)
    o = play(env,o,'Defend_R')[0]
    assert o['player']['block'] == 5
    assert env.step(50)[0]['player']['hp'] == 70-(damage-5)
    env, o, _ = start(['Orichalcum'], deck=['Metallicize']*10)
    o = play(env,o,'Metallicize')[0]
    assert o['player']['block'] == 0
    assert env.step(50)[0]['player']['hp'] == 70-max(0,damage-9)


@pytest.mark.parametrize('relic', BATCH)
def test_each_second_batch_relic_real_model_forward_and_replay(relic):
    env, o, initial = start([relic])
    sample = encode(o)
    row = next(t.features for t in sample.entities.tokens if t.entity_type=='RELIC')
    assert len(row)==DIMENSION==25 and row[:-3].sum()==1 and not row[-3:].any()
    assert row[BY_NAME[relic]['id']-1]==1
    model=APathActorCritic().eval()
    with torch.no_grad():
        dist,value=model(batch_samples([sample]))
    assert torch.isfinite(value).all() and dist.probs.sum().item()==pytest.approx(1)
    route=next(r for rs in sample.routes for r in rs if r.get('action')==50)
    after=env.step(route)
    saved=json.loads(json.dumps(dict(scene=initial,seed=100123,route=plain_route(route))))
    replay=RelicEnv(); before=replay.reset(saved['scene'],saved['seed'],diagnostic=True)
    recovered=replay.step(bind_route(saved['route'],before))
    assert sample_digest(encode(after[0]))==sample_digest(encode(recovered[0]))
    assert after[1:4]==recovered[1:4]
    assert after[4]['reward_accounting']==recovered[4]['reward_accounting']
    assert not after[4]['training_admitted']


@pytest.mark.parametrize('encounter', ACT12)
@pytest.mark.parametrize('relic', BATCH)
def test_second_batch_full_act12_reset_step_surface(encounter, relic):
    env, o, _ = start([relic],encounter=encounter)
    assert len(o['relics'])==1
    assert encode(o).routes
    o, _, _, _, _=env.step(50)
    assert encode(o).entities.tokens
