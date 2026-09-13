"""敌人药水扩展的机制及边界回归，夹具是人工诊断配置。"""
import numpy as np
import pytest
from sts.env.enemy_potion import EnemyPotionBattleEnv, PUBLIC_CONTRACT


def start(encounter='CULTIST', potion=None, deck=None, hp=80, ascension=0, budget=100):
    scene = dict(entry_timing='pre_combat_initialization', initialization_phase='before_destination_room_entry',
                 act=1, floor=17 if encounter in ['SLIME_BOSS','THE_GUARDIAN','HEXAGHOST'] else 8,
                 character='IRONCLAD', ascension=ascension, player=dict(hp=hp,max_hp=max(80,hp),gold=0),
                 deck=deck or ['Strike_R']*10, relics=[], potions=[potion]+[None]*(1 if ascension>=11 else 2),
                 encounter=encounter,burning_elite=False)
    env=EnemyPotionBattleEnv(budget)
    return env,env.reset(scene,813000,diagnostic=True)


def cards(obs):
    return sum((obs[k] for k in ['hand','draw_pile','discard_pile','exhaust_pile']),[])


@pytest.mark.parametrize('encounter', PUBLIC_CONTRACT['encounters'][:20])
@pytest.mark.parametrize('ascension',[0,20])
def test_all_encounters_complete_without_lost_observation(encounter,ascension):
    env,obs=start(encounter,deck=['Defend_R']*10,hp=500,ascension=ascension,budget=35)
    for _ in range(35):
        assert len(obs['enemies'])==5
        assert len(cards(obs))>=10
        obs,reward,term,trunc,info=env.step(50)
        if term or trunc:
            assert not(term and trunc)
            assert reward==0 or (encounter=="LOOTER" and term)
            if reward>0: break
            assert obs['player']['hp']>0 if trunc else obs['player']['hp']==0
            break
    else: pytest.fail('预算未终止采集')


def test_fire_target_and_victory():
    env,obs=start('TWO_LOUSE','Fire Potion')
    hp=obs['enemies'][1]['hp']; other=obs['enemies'][0]['hp']
    obs,*_=env.step(52)
    assert obs['enemies'][1]['hp']==max(0,hp-20)
    assert obs['enemies'][0]['hp']==other
    assert not obs['action_mask'][52]


def test_blood_potion_correct_percentage():
    env,obs=start(potion='Blood Potion',hp=40)
    obs,*_=env.step(51)
    assert obs['player']['hp']==56
    assert not obs['potions'][0]['present']


def test_flex_expires_and_cultist_grows():
    env,obs=start(potion='SteroidPotion')
    obs,*_=env.step(51)
    assert obs['player']['statuses']['Strength']==5
    obs,*_=env.step(50)
    assert obs['player']['statuses'].get('Strength',0)==0
    env,obs=start(potion='CultistPotion')
    obs,*_=env.step(51)
    assert obs['player']['statuses']['Ritual']==1
    obs,*_=env.step(50)
    assert obs['player']['statuses']['Strength']==1


def test_fairy_passive_revives_before_terminal():
    env,obs=start('JAW_WORM','FairyPotion',hp=1)
    assert not obs['action_mask'][51:56].any()
    obs,r,t,x,_=env.step(50)
    assert not t and not x and r==0
    assert obs['player']['hp']==24
    assert not obs['potions'][0]['present']


def test_slime_boss_generates_five_at_a20():
    env,obs=start('SLIME_BOSS',ascension=20)
    obs,r,t,x,_=env.step(50)
    assert len([c for c in cards(obs) if c['name']=='Slimed'])==5
    assert not t and not x


def test_guardian_shift_and_sharp_hide_visible():
    env,obs=start('THE_GUARDIAN',deck=['Bludgeon']*10,hp=500)
    before=obs['enemies'][0]['statuses']['Mode Shift']
    obs,*_=env.step(0)
    assert obs['enemies'][0]['intent_kind']=='BUFF'
    assert before<=32
    obs,*_=env.step(50)
    assert obs['enemies'][0]['statuses']['Sharp Hide']==3
    obs,*_=env.step(0)
    assert obs['player']['hp']==497


def test_hexaghost_divider_depends_on_current_hp():
    env,obs=start('HEXAGHOST',hp=60)
    obs,*_=env.step(50)
    assert obs['enemies'][0]['intent_damage']==6
    assert obs['enemies'][0]['intent_hits']==6
    obs,*_=env.step(50)
    assert obs['player']['hp']==24


def test_slime_boss_split_is_not_terminal_and_new_targets_are_legal():
    env,obs=start('SLIME_BOSS',deck=['Bludgeon']*10,hp=500)
    for _ in range(3):
        slot=next(i for i,c in enumerate(obs['hand']) if c['name']=='Bludgeon')
        obs,*_=env.step(slot*5)
        obs,r,t,x,_=env.step(50)
        assert not t and not x and r==0
    living=[i for i,e in enumerate(obs['enemies']) if e['targetable']]
    assert len(living)==2
    assert all(obs['action_mask'][i] for i in living)
    assert all(obs['enemies'][i]['public_history']['completed_enemy_turns']==0 for i in living)
    target=living[0]
    slot=next(i for i,c in enumerate(obs['hand']) if c['name']=='Bludgeon')
    obs,*_=env.step(slot*5+target)
    obs,r,t,x,_=env.step(50)
    assert not t and not x and r==0
    assert sum(e['targetable'] for e in obs['enemies'])==3


def test_hexaghost_inferno_upgrades_and_generates_burns():
    env,obs=start('HEXAGHOST',hp=500,deck=['Defend_R']*10)
    for _ in range(9):
        before=cards(obs)
        obs,r,t,x,_=env.step(50)
        assert not t and not x
    burns=[c for c in cards(obs) if c['name']=='Burn']
    assert len(burns)==6
    assert all(c['upgrade_count']==1 and c['magic']==4 for c in burns)


def test_invalid_action_and_external_budget_preserve_full_final_state():
    env,obs=start('SLIME_BOSS',ascension=20,budget=1)
    with pytest.raises(ValueError): env.step(65)
    after,r,t,x,info=env.step(50)
    assert x and not t and r==0
    assert len(cards(after))==15
    assert after['action_mask'].any()
    assert info['task_outcome']=='ongoing'
    with pytest.raises(RuntimeError): env.step(50)


def test_frozen_public_environment_still_rejects_boss_and_new_potions():
    from sts.env.public_battle import PublicBattleEnv
    for encounter,potion in [('SLIME_BOSS',None),('CULTIST','Blood Potion')]:
        scene=dict(entry_timing='pre_combat_initialization',initialization_phase='before_destination_room_entry',
                   act=1,floor=8,character='IRONCLAD',ascension=0,player=dict(hp=80,max_hp=80,gold=0),
                   deck=['Strike_R']*10,relics=[],potions=[potion,None,None],encounter=encounter)
        with pytest.raises(ValueError): PublicBattleEnv().reset(scene,813000,diagnostic=True)


@pytest.mark.parametrize('potion',PUBLIC_CONTRACT['potions'][:15])
def test_inherited_potions_match_frozen_transition(potion):
    from sts.env.public_battle import PublicBattleEnv
    scene=dict(entry_timing='pre_combat_initialization',initialization_phase='before_destination_room_entry',
               act=1,floor=8,character='IRONCLAD',ascension=0,player=dict(hp=40,max_hp=80,gold=0),
               deck=['Strike_R']*5+['Defend_R']*5,relics=[],potions=[potion['name'],None,None],encounter='CULTIST')
    env=EnemyPotionBattleEnv();old=PublicBattleEnv()
    obs=env.reset(scene,813000,diagnostic=True);reference=old.reset(scene,813000,diagnostic=True)
    for action in [51,50]:
        obs,r,t,x,_=env.step(action);reference,rr,tt,xx,_=old.step(action)
        assert (r,t,x)==(rr,tt,xx)
        assert np.array_equal(obs['action_mask'],reference['action_mask'])
        for key in ['player','potions','hand','draw_pile','discard_pile','exhaust_pile']:
            assert obs[key]==reference[key]
        # v3只改变意图记录表示；逐项比较旧有战斗状态与公开计数。
        from copy import deepcopy
        def comparable(rows):
            result=deepcopy(rows)
            for enemy in result:
                enemy.pop('intent_history',None); enemy.pop('intent_history_valid',None)
                enemy['public_history'].pop('last_intent_kind',None)
                enemy['public_history'].pop('previous_intent_kind',None)
            return result
        assert comparable(obs['enemies'])==comparable(reference['enemies'])


def test_reset_rejects_training_and_invalidates_prior_episode():
    env,obs=start()
    with pytest.raises(ValueError):env.reset({},813000,diagnostic=True,purpose='train')
    with pytest.raises(RuntimeError):env.step(50)


@pytest.mark.parametrize('fingerprint',[None,'stale-backend-contract'])
def test_backend_contract_mismatch_is_rejected_before_allocation(fingerprint):
    from types import SimpleNamespace
    allocated=[]
    backend=SimpleNamespace(EnemyPotionBattleEnv=lambda limit:allocated.append(limit))
    if fingerprint is not None:backend.enemy_potion_contract_sha256=fingerprint
    with pytest.raises(RuntimeError,match='指纹'):
        EnemyPotionBattleEnv(backend=backend)
    assert allocated==[]
