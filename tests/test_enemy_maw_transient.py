"""巨口和倏忽魔的独立公开接口验收；不使用worker隐藏诊断入口。"""
import pytest
from test_act23_enemies import scene
from sts.env.enemy_potion import EnemyPotionBattleEnv
from sts.env.enemy_potion_entities import EnemyPotionEntityView


def start(name, asc=0, deck=None, hp=1000):
    env=EnemyPotionBattleEnv(32)
    return env,env.reset(scene(name,asc,hp=hp,deck=deck or ['Defend_R']*10),100000,diagnostic=True)


@pytest.mark.parametrize('asc',[0,1,2,16,17,20])
def test_transient_countdown_natural_exit_and_final_mask(asc):
    env,obs=start('TRANSIENT',asc)
    remaining=6 if asc>=17 else 5
    assert obs['enemies'][0]['statuses']['Fading']==remaining
    assert obs['enemies'][0]['statuses']['Shifting']==1
    view=EnemyPotionEntityView();view.reset()
    for i in range(remaining):
        e=obs['enemies'][0];hp=obs['player']['hp']
        assert e['statuses']['Fading']==remaining-i
        assert e['intent_damage']==(40 if asc>=2 else 30)+i*10
        expected=e['intent_damage']*e['intent_hits']
        obs,reward,term,trunc,info=env.step(50)
        assert obs['player']['hp']==hp-expected
        assert not trunc
        assert term==(i==remaining-1)
        if not term: assert reward==0
    assert info['task_outcome']=='victory'
    assert reward==pytest.approx(1+0.5*obs['player']['hp']/obs['player']['max_hp'])
    assert view.update(obs)['enemy_entities']==[]
    assert not obs['action_mask'].any()


def test_transient_attack_updates_strength_and_preview_without_future_field():
    env,obs=start('TRANSIENT',deck=['Bludgeon']*10)
    e=obs['enemies'][0];before=e['intent_damage'];hp=e['hp']
    obs,*_=env.step(0)
    e=obs['enemies'][0]
    assert e['hp']==hp-32
    assert e['statuses']['Strength']==-32
    assert e['intent_damage']==max(0,before-32)
    old_hp=obs['player']['hp'];obs,*_=env.step(50)
    assert obs['player']['hp']==old_hp
    assert obs['enemies'][0]['statuses'].get('Strength',0)==0


@pytest.mark.parametrize('asc',[0,1,2,16,17,20])
def test_maw_visible_segments_match_payment_and_global_turn(asc):
    env,obs=start('MAW',asc,hp=5000)
    assert obs['enemies'][0]['intent_kind']=='DEBUFF'
    obs,*_=env.step(50)
    assert obs['player']['statuses']['Weak']==(5 if asc>=17 else 3)
    assert obs['player']['statuses']['Frail']==(5 if asc>=17 else 3)
    multi=0
    for _ in range(10):
        e=obs['enemies'][0];hp=obs['player']['hp']
        if e['intent_hits']>1:
            multi+=1
            assert e['intent_hits']==(obs['player']['turn']+2)//2
        expected=e['intent_damage']*e['intent_hits']
        obs,reward,term,trunc,_=env.step(50)
        assert not term and not trunc and reward==0
        assert obs['player']['hp']==hp-expected
    assert multi>0


def test_transient_external_budget_is_not_victory():
    env=EnemyPotionBattleEnv(1)
    obs=env.reset(scene('TRANSIENT',hp=1000),100000,diagnostic=True)
    obs,reward,term,trunc,info=env.step(50)
    assert not term and trunc and reward==0
    assert obs['enemies'][0]['targetable']
    assert info['task_outcome']=='ongoing'
