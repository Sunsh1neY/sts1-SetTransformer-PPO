"""治疗、致死、随机多段及自动耗尽的真实战斗验收。"""
import pytest
from sts.env.ironclad import IroncladEnv
from sts.env.entities import encode_observation, collate
from sts.models.entities import UnifiedEntityActorCritic
from test_ironclad_dynamics import start,play
from test_ironclad_expansion import scene
from test_ironclad_direct import upgraded


@pytest.mark.parametrize('up',[False,True])
@pytest.mark.parametrize('missing',[2,25])
def test_reaper_heals_actual_multi_enemy_hp_loss_with_max_hp_cap(up,missing):
    candidate=scene([upgraded('Reaper',up),*['Strike_R']*4]);candidate.update(encounter='EXORDIUM_THUGS',relics=[])
    candidate['player']['hp']=75-missing
    env=IroncladEnv();obs=env.reset(candidate,982501,diagnostic=True)
    before=sum(e['hp'] for e in obs['enemies']);hp=obs['player']['hp'];maximum=obs['player']['max_hp']
    obs=play(env,obs,'Reaper')
    loss=before-sum(e['hp'] for e in obs['enemies'])
    assert loss==2*(5 if up else 4)
    assert obs['player']['hp']==min(maximum,hp+loss)
    assert any(c['name']=='Reaper' for c in obs['exhaust_pile'])


@pytest.mark.parametrize('up',[False,True])
def test_reaper_does_not_heal_damage_absorbed_by_block(up):
    env,obs=start([upgraded('Reaper',up),*['Strike_R']*4])
    hp=obs['player']['hp'];enemyhp=obs['enemies'][0]['hp']
    obs=play(env,obs,'Reaper')
    assert obs['enemies'][0]['hp']==enemyhp and obs['player']['hp']==hp


@pytest.mark.parametrize('up',[False,True])
def test_feed_nonfatal_has_no_max_hp_gain(up):
    env,obs=start([upgraded('Feed',up),*['Strike_R']*4])
    maximum=obs['player']['max_hp'];obs=play(env,obs,'Feed')
    assert obs['player']['max_hp']==maximum
    assert any(c['name']=='Feed' for c in obs['exhaust_pile'])


@pytest.mark.parametrize('up',[False,True])
def test_feed_fatal_grows_max_hp_and_uses_existing_reward(up):
    candidate=scene([upgraded('Feed',up),*['Strike_R']*4]);candidate['relics']=[]
    env=IroncladEnv();obs=env.reset(candidate,982502,diagnostic=True)
    original=obs['player']['max_hp'];damage=12 if up else 10
    for _ in range(40):
        feed=next((i for i,c in enumerate(obs['hand']) if c['name']=='Feed'),None)
        if obs['enemies'][0]['hp']+obs['enemies'][0]['block']<=damage and feed is not None and obs['action_mask'][feed*5]:
            obs,reward,terminated,truncated,_=env.step(feed*5)
            assert terminated and not truncated
            assert obs['player']['max_hp']==original+(4 if up else 3)
            assert reward==pytest.approx(1+.5*obs['player']['hp']/obs['player']['max_hp'])
            break
        strike=next((i for i,c in enumerate(obs['hand']) if c['name']=='Strike_R' and obs['action_mask'][i*5] and obs['enemies'][0]['hp']>6),None)
        obs=env.step(strike*5 if strike is not None and obs['enemies'][0]['hp']>damage else 50)[0]
    else: raise AssertionError('未完成真实Feed致死路径')


@pytest.mark.parametrize('up',[False,True])
def test_sword_boomerang_random_targets_are_not_policy_choices(up):
    candidate=scene([upgraded('Sword Boomerang',up),*['Strike_R']*4]);candidate.update(encounter='EXORDIUM_THUGS',relics=[])
    env=IroncladEnv();obs=env.reset(candidate,982503,diagnostic=True)
    slot=next(i for i,c in enumerate(obs['hand']) if c['name']=='Sword Boomerang')
    assert obs['hand'][slot]['target_kind']=='NO_TARGET'
    assert obs['action_mask'][slot*5:slot*5+5].tolist()==[True,False,False,False,False]
    before=sum(e['hp']+e['block'] for e in obs['enemies']);obs=play(env,obs,'Sword Boomerang')
    assert before-sum(e['hp']+e['block'] for e in obs['enemies'])==3*(4 if up else 3)


@pytest.mark.parametrize('name',['Second Wind','Sever Soul'])
@pytest.mark.parametrize('up',[False,True])
def test_automatic_exhaust_triggers_sentinel_and_feel_no_pain(name,up):
    env,obs=start([upgraded(name,up),'Feel No Pain','Sentinel','Wound','Strike_R'])
    obs=play(env,obs,'Feel No Pain');energy=obs['player']['energy']
    obs=play(env,obs,name)
    assert obs['decision']['phase']=='NORMAL'
    assert {c['name'] for c in obs['exhaust_pile']}=={'Sentinel','Wound'}
    assert obs['player']['energy']==energy-(1 if name=='Second Wind' else 2)+2
    assert obs['player']['block']==6+(2*(7 if up else 5) if name=='Second Wind' else 0)
    assert any(c['name']=='Strike_R' for c in obs['hand'])
    assert any(c['name']==name for c in obs['discard_pile'])


@pytest.mark.parametrize('up',[False,True])
def test_second_wind_empty_nonattack_set_gives_no_block(up):
    env,obs=start([upgraded('Second Wind',up),*['Strike_R']*4]);obs=play(env,obs,'Second Wind')
    assert obs['player']['block']==0 and not obs['exhaust_pile']


@pytest.mark.parametrize('name',['Feed','Reaper','Sword Boomerang','Second Wind','Sever Soul'])
@pytest.mark.parametrize('up',[False,True])
def test_new_versions_encode_into_unified_model(name,up):
    _,obs=start([upgraded(name,up),*['Strike_R']*4])
    distribution,value=UnifiedEntityActorCritic().distribution(collate([encode_observation(obs)]))
    assert distribution.probs.isfinite().all() and value.isfinite().all()
