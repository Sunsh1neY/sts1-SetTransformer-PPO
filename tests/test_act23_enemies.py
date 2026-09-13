"""第二、三幕可准入批次：真实后端转移、公开状态及资源边界。"""
import json
from pathlib import Path
import numpy as np
import pytest
from sts.env.enemy_potion import EnemyPotionBattleEnv, PUBLIC_CONTRACT
from sts.env.enemy_potion_entities import EnemyPotionEntityView

NEW=[n for n in PUBLIC_CONTRACT['encounters'] if PUBLIC_CONTRACT['encounter_acts'][n]>1]


def scene(name,asc=0,hp=500,deck=None):
    act=PUBLIC_CONTRACT['encounter_acts'][name]
    return dict(entry_timing='pre_combat_initialization',initialization_phase='before_destination_room_entry',
        act=act,floor=act*17-5,character='IRONCLAD',ascension=asc,player=dict(hp=hp,max_hp=hp,gold=0),
        deck=deck or ['Strike_R']*5+['Defend_R']*4+['Bash'],relics=[],potions=[None]*(2 if asc>=11 else 3),
        encounter=name,burning_elite=False)


def start(name,asc=0,deck=None,seed=850000,budget=64):
    env=EnemyPotionBattleEnv(budget)
    return env,env.reset(scene(name,asc,deck=deck),seed,diagnostic=True)


def count(obs,name=None):
    return sum(1 for k in ['hand','draw_pile','discard_pile','exhaust_pile'] for c in obs[k] if name is None or c['name']==name)


@pytest.mark.parametrize('name',NEW)
@pytest.mark.parametrize('asc',[0,20])
@pytest.mark.parametrize('policy',['end','random'])
def test_new_encounters_keep_complete_observation_and_legal_routes(name,asc,policy):
    env,obs=start(name,asc)
    view=EnemyPotionEntityView();view.reset()
    rng=np.random.default_rng(12)
    for _ in range(64):
        data=view.update(obs)
        assert len(data['enemy_entities'])==sum(e['targetable'] for e in obs['enemies'])
        assert len(data['potion_entities'])==0
        assert count(obs)>=10
        before=count(obs)
        action=50 if policy=='end' else int(rng.choice(np.flatnonzero(obs['action_mask'])))
        obs,r,t,x,info=env.step(action)
        assert count(obs)-before<=15
        if t or x:
            assert not(t and x)
            assert r==0 if x else (r==0 or 1<=r<=1.5)
            assert info['task_outcome']=='ongoing' if x else info['task_outcome'] in ('victory','defeat')
            break
    else: pytest.fail('未在预算内形成完整停止点')


@pytest.mark.parametrize('asc,block',[ (0,65),(20,75)])
def test_spheric_guardian_retains_block_and_public_barricade(asc,block):
    env,obs=start('SPHERIC_GUARDIAN',asc)
    e=obs['enemies'][0]
    assert e['block']==40 and e['statuses']['Barricade']==1 and e['statuses']['Artifact']==3
    obs,*_=env.step(50)
    assert obs['enemies'][0]['block']==block
    assert obs['enemies'][0]['intent_kind']=='ATTACK_DEBUFF'
    obs,*_=env.step(50)
    assert obs['player']['statuses']['Frail']>0


def test_chosen_hex_generates_one_dazed_after_skill():
    env,obs=start('CHOSEN',20,deck=['Defend_R']*10)
    assert obs['enemies'][0]['intent_kind']=='STRONG_DEBUFF'
    obs,*_=env.step(50)
    assert obs['player']['statuses']['Hex']==1
    old=count(obs,'Dazed');obs,*_=env.step(0)
    assert count(obs,'Dazed')==old+1


def test_snake_plant_malleable_grows_and_resets():
    env,obs=start('SNAKE_PLANT',deck=['Strike_R']*10)
    assert obs['enemies'][0]['statuses']['Malleable']==3
    hp=obs['enemies'][0]['hp'];obs,*_=env.step(0)
    assert obs['enemies'][0]['hp']==hp-6
    assert obs['enemies'][0]['block']==3
    assert obs['enemies'][0]['statuses']['Malleable']==4
    obs,*_=env.step(0)
    assert obs['enemies'][0]['statuses']['Malleable']==5
    obs,*_=env.step(50)
    assert obs['enemies'][0]['statuses']['Malleable']==3


def test_shelled_parasite_plate_reduces_after_unblocked_hit():
    env,obs=start('SHELL_PARASITE',deck=['Bludgeon']*10)
    assert obs['enemies'][0]['statuses']['Plated Armor']==14
    hp=obs['enemies'][0]['hp'];obs,*_=env.step(0)
    assert obs['enemies'][0]['hp']==hp-18
    assert obs['enemies'][0]['statuses']['Plated Armor']==13


@pytest.mark.parametrize('asc,amount',[(0,3),(20,5)])
def test_orb_walker_strength_and_two_burns(asc,amount):
    for seed in range(850000,850020):
        env,obs=start('ORB_WALKER',asc,seed=seed)
        if obs['enemies'][0]['intent_kind']=='ATTACK_DEBUFF':break
    else:pytest.fail('指定seed范围未覆盖激光')
    assert obs['enemies'][0]['statuses']['Generic Strength Up']==amount
    obs,*_=env.step(50)
    assert count(obs,'Burn')==2
    assert obs['enemies'][0]['statuses']['Strength']==amount


def test_spire_growth_constricted_is_visible_and_deals_damage():
    env,obs=start('SPIRE_GROWTH',20)
    assert obs['enemies'][0]['intent_kind']=='STRONG_DEBUFF'
    obs,*_=env.step(50)
    assert obs['player']['statuses']['Constricted']==12
    hp=obs['player']['hp'];damage=obs['enemies'][0]['intent_damage']*obs['enemies'][0]['intent_hits']
    obs,*_=env.step(50)
    assert obs['player']['hp']==hp-damage-12


@pytest.mark.parametrize('asc,wounds',[(0,1),(20,3)])
def test_slavers_taskmaster_generates_expected_wounds(asc,wounds):
    env,obs=start('SLAVERS',asc)
    assert sum(e['targetable'] for e in obs['enemies'])==3
    obs,*_=env.step(50)
    assert count(obs,'Wound')==wounds


@pytest.mark.parametrize('field,value',[('act',1),('floor',8),('burning_elite',True)])
def test_invalid_act_floor_and_burning_elite_rejected(field,value):
    payload=scene('SLAVERS');payload[field]=value
    with pytest.raises(ValueError):EnemyPotionBattleEnv().reset(payload,850000,diagnostic=True)


@pytest.mark.parametrize('entry',[e for e in json.loads((Path(__file__).parents[1]/'docs/act23-enemy-audit.json').read_text(encoding='utf-8'))['entries'] if e['review_required']])
def test_special_enemies_wait_for_review(entry):
    payload=scene('ORB_WALKER');payload.update(encounter=entry['encounter'],act=entry['act'],floor=entry['act']*17-5)
    with pytest.raises(ValueError,match='白名单'):EnemyPotionBattleEnv().reset(payload,850000,diagnostic=True)


def test_centurion_defends_actual_healer_target():
    for seed in range(850000,850100):
        env,obs=start('CENTURION_AND_HEALER',seed=seed)
        if obs['enemies'][0]['intent_kind']=='DEFEND':break
    else:pytest.fail('未覆盖百夫长援护')
    obs,*_=env.step(50)
    assert obs['enemies'][1]['block']==15
    assert obs['enemies'][0]['block']==0


def test_healer_recovers_real_missing_hp():
    env,obs=start('CENTURION_AND_HEALER',deck=['Bludgeon']*10)
    maximum=obs['enemies'][1]['max_hp']
    obs,*_=env.step(1)
    assert obs['enemies'][1]['hp']==maximum-32
    recovered=False
    for _ in range(5):
        before=obs['enemies'][1]['hp']
        obs,*_=env.step(50)
        if obs['enemies'][1]['hp']>before:
            assert obs['enemies'][1]['hp']==min(maximum,before+16)
            recovered=True;break
    assert recovered


def test_shelled_parasite_suck_heals_only_actual_unblocked_damage():
    for seed in range(850000,850100):
        env,obs=start('SHELL_PARASITE',seed=seed,deck=['Bludgeon']*10)
        if obs['enemies'][0]['intent_kind']=='ATTACK_BUFF':break
    else:pytest.fail('未覆盖寄生虫吸血')
    obs,*_=env.step(0);hp=obs['enemies'][0]['hp'];player=obs['player']['hp']
    obs,*_=env.step(50)
    assert obs['enemies'][0]['hp']==hp+10
    assert obs['player']['hp']==player-10


def test_duplicate_species_targets_remain_distinct():
    env,obs=start('THREE_CULTIST',deck=['Strike_R']*10)
    old=[e['hp'] for e in obs['enemies'][:3]]
    view=EnemyPotionEntityView();view.reset();data=view.update(obs)
    assert len(set(data['routing']['enemy_target_references'].values()))==3
    obs,*_=env.step(1)
    assert [e['hp'] for e in obs['enemies'][:3]]==[old[0],old[1]-6,old[2]]


def test_shelled_parasite_plate_break_stuns_without_death():
    env,obs=start('SHELL_PARASITE',deck=['Pummel']*40)
    stunned=False
    for _ in range(8):
        for _ in range(3):
            slot=next((i for i,c in enumerate(obs['hand']) if c['name']=='Pummel' and obs['action_mask'][i*5]),None)
            if slot is None:break
            obs,r,t,x,_=env.step(slot*5)
            assert not t and not x
            if obs['enemies'][0]['statuses'].get('Plated Armor',0)==0:
                assert obs['enemies'][0]['hp']>0
                assert obs['enemies'][0]['intent_kind']=='STUN'
                hp=obs['player']['hp'];obs,*_=env.step(50)
                assert obs['player']['hp']==hp
                # 正版眩晕分支设置动作后仍执行RollMoveAction，恢复意图重新抽取。
                assert obs['enemies'][0]['intent_kind'] in ('ATTACK','ATTACK_BUFF','ATTACK_DEBUFF')
                stunned=True;break
        if stunned:break
        obs,*_=env.step(50)
    assert stunned
