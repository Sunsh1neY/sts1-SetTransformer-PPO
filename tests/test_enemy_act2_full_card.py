"""第二幕全卡接入：既有机制与事件组合的真实决策、结算和编码。"""
import random
import pytest
from sts.env.ironclad import IroncladEnv
from sts.env.entities import encode_observation, collate

ENCOUNTERS = ['SPHERIC_GUARDIAN','CHOSEN','SHELL_PARASITE','SENTRY_AND_SPHERE',
 'SNAKE_PLANT','CENTURION_AND_HEALER','CULTIST_AND_CHOSEN','THREE_CULTIST',
 'SHELLED_PARASITE_AND_FUNGI','SLAVERS','BOOK_OF_STABBING','COLOSSEUM_EVENT_SLAVERS','COLOSSEUM_EVENT_NOBS']

def scene(name):
    return dict(entry_timing='pre_combat_initialization',initialization_phase='before_destination_room_entry',
        act=2,floor=29,character='IRONCLAD',ascension=20,player=dict(hp=80,max_hp=80,gold=100),
        deck=['Strike_R']*3+['Defend_R']*3+['Bash','Pommel Strike','Headbutt','True Grit'],
        relics=[],potions=[None,None],encounter=name,burning_elite=False)

@pytest.mark.parametrize('name',ENCOUNTERS)
@pytest.mark.parametrize('seed',[860000,860001,860002])
def test_real_full_card_candidates_until_terminal_or_explicit_budget(name,seed):
    env=IroncladEnv(96)
    obs=env.reset(scene(name),seed,diagnostic=True)
    rng=random.Random(seed)
    for _ in range(96):
        sample=encode_observation(obs)
        collate([sample])
        routes=[r for r,c in zip(sample.routes,sample.candidates) if c.legal]
        assert routes
        obs,reward,terminated,truncated,info=env.step(rng.choice(routes))
        if terminated or truncated:
            encode_observation(obs)
            assert not (terminated and truncated)
            assert terminated, '正常80血诊断应真实结算；超预算须显式调查'
            return
    pytest.fail('无终止也无外部截断')

@pytest.mark.parametrize('name,expected',[
 ('COLOSSEUM_EVENT_SLAVERS',{'BLUE_SLAVER','RED_SLAVER'}),
 ('COLOSSEUM_EVENT_NOBS',{'TASKMASTER','GREMLIN_NOB'})])
def test_event_composition_is_exact(name,expected):
    env=IroncladEnv(16); obs=env.reset(scene(name),860010,diagnostic=True)
    assert {e['name'] for e in obs['enemies'] if e['present']}==expected


def count_wounds(obs):
    return sum(c['name']=='Wound' for zone in ['hand','draw_pile','discard_pile','exhaust_pile','resolving'] for c in obs[zone])

def test_book_a20_each_unblocked_hit_generates_one_real_wound():
    config=scene('BOOK_OF_STABBING');config['player'].update(hp=300,max_hp=300)
    env=IroncladEnv(16);obs=env.reset(config,860026,diagnostic=True)
    assert obs['enemies'][0]['intent_damage']==24
    assert obs['enemies'][0]['intent_hits']==1
    for turn in range(4):
        enemy=obs['enemies'][0];hp=obs['player']['hp'];wounds=count_wounds(obs)
        obs,reward,terminated,truncated,_=env.step(50)
        assert not terminated and not truncated
        assert obs['player']['hp']==hp-enemy['intent_damage']*enemy['intent_hits']
        assert count_wounds(obs)==wounds+enemy['intent_hits']
        assert 'Painful Stabs' not in obs['enemies'][0]['statuses']
        encode_observation(obs)
        if turn==0: assert obs['enemies'][0]['intent_hits']==3

def test_book_full_block_does_not_generate_wound():
    config=scene('BOOK_OF_STABBING');config['deck']=['Impervious']*5
    env=IroncladEnv(8);obs=env.reset(config,100000,diagnostic=True)
    obs,*_=env.step(0);hp=obs['player']['hp'];wounds=count_wounds(obs)
    obs,*_=env.step(50)
    assert obs['player']['hp']==hp and count_wounds(obs)==wounds

def test_hex_boolean_export_and_generated_dazed_remain_encodable():
    config=scene('CHOSEN');config['deck']=['Defend_R']*5
    env=IroncladEnv(8);obs=env.reset(config,860000,diagnostic=True)
    obs,*_=env.step(50)
    assert obs['player']['statuses']['Hex']==1
    obs,*_=env.step(0)
    assert any(c['name']=='Dazed' for c in obs['draw_pile'])
    encode_observation(obs)
