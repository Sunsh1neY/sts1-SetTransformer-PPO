"""能力状态与抽牌、自伤、格挡、耗尽触发链。"""
import pytest
from test_ironclad_dynamics import start,play
from test_ironclad_direct import upgraded
from sts.env.entities import encode_observation,collate
from sts.models.entities import UnifiedEntityActorCritic


@pytest.mark.parametrize('up',[False,True])
def test_berserk_next_turn_energy_and_artifact(up):
    env,obs=start([upgraded('Berserk',up),*['Strike_R']*4],['Ancient Potion',None])
    obs=env.step(51)[0];energy=obs['player']['energy'];obs=play(env,obs,'Berserk')
    assert obs['player']['energy']==energy and obs['player']['energy_per_turn']==4
    assert not obs['player']['statuses'].get('Vulnerable',0)
    obs=env.step(50)[0];assert obs['player']['energy']==4


@pytest.mark.parametrize('up',[False,True])
def test_brutality_turn_loss_triggers_rupture_and_blood_cost(up):
    env,obs=start([upgraded('Brutality',up),'Rupture','Blood for Blood','Strike_R','Strike_R'])
    obs=play(env,obs,'Rupture');obs=play(env,obs,'Brutality');hp=obs['player']['hp']
    obs=env.step(50)[0]
    assert obs['player']['hp']==hp-1 and obs['player']['statuses']['Strength']==1
    assert next(c for c in obs['hand'] if c['name']=='Blood for Blood')['base_cost']==3


@pytest.mark.parametrize('up',[False,True])
def test_dark_embrace_exhaust_draw_and_no_draw(up):
    env,obs=start([upgraded('Dark Embrace',up),'True Grit+1','Sentinel','Strike_R','Battle Trance'])
    obs=play(env,obs,'Dark Embrace');obs=play(env,obs,'True Grit')
    sample=encode_observation(obs);chosen=next(i for i,c in enumerate(obs['decision']['selection']['candidates']) if c['name']=='Sentinel')
    before=len(obs['hand']);obs=env.step(sample.routes[chosen])[0]
    # 消耗后抽牌会从弃牌堆洗回刚打出的能力以外的牌；空抽牌堆可无牌可抽。
    assert obs['player']['statuses']['Dark Embrace']==1
    assert any(c['name']=='Sentinel' for c in obs['exhaust_pile'])
    assert len(obs['hand'])>=before-1


@pytest.mark.parametrize('up',[False,True])
def test_fire_breathing_status_draw_damages_enemy(up):
    env,obs=start([upgraded('Fire Breathing',up),'Wound','Wound','Strike_R','Strike_R'])
    obs=play(env,obs,'Fire Breathing');before=obs['enemies'][0]['hp']+obs['enemies'][0]['block']
    obs=env.step(50)[0]
    # Lagavulin仍睡眠，本轮两张Wound触发两次，首次伤害先穿过8格挡。
    assert before-obs['enemies'][0]['hp']-obs['enemies'][0]['block']==2*(10 if up else 6)


@pytest.mark.parametrize('up',[False,True])
def test_juggernaut_each_block_gain_and_potion(up):
    env,obs=start([upgraded('Juggernaut',up),'Defend_R',*['Strike_R']*3],['Block Potion',None])
    obs=play(env,obs,'Juggernaut');before=obs['enemies'][0]['hp']+obs['enemies'][0]['block']
    obs=play(env,obs,'Defend_R');obs=env.step(51)[0]
    assert before-obs['enemies'][0]['hp']-obs['enemies'][0]['block']==2*(7 if up else 5)


@pytest.mark.parametrize('up',[False,True])
def test_rupture_offering_loss_event_once(up):
    env,obs=start([upgraded('Rupture',up),'Offering',*['Strike_R']*3])
    obs=play(env,obs,'Rupture');obs=play(env,obs,'Offering')
    assert obs['player']['statuses']['Strength']==(2 if up else 1)


@pytest.mark.parametrize('name,status,base,plus',[
 ('Brutality','Brutality',1,1),('Dark Embrace','Dark Embrace',1,1),('Evolve','Evolve',1,2),
 ('Fire Breathing','Fire Breathing',6,10),('Juggernaut','Juggernaut',5,7),('Rupture','Rupture',1,2)])
@pytest.mark.parametrize('up',[False,True])
def test_power_exports_active_value_and_encodes(name,status,base,plus,up):
    env,obs=start([upgraded(name,up),*['Strike_R']*4]);obs=play(env,obs,name)
    assert obs['player']['statuses'][status]==(plus if up else base)
    distribution,value=UnifiedEntityActorCritic().distribution(collate([encode_observation(obs)]))
    assert distribution.probs.isfinite().all() and value.isfinite().all()


@pytest.mark.parametrize('up',[False,True])
def test_evolve_draws_extra_for_each_status(up):
    from test_ironclad_expansion import scene
    from sts.env.ironclad import IroncladEnv
    candidate=scene([upgraded('Evolve',up)]+['Wound']*5+['Strike_R']*6)
    candidate.update(encounter='LAGAVULIN',relics=[])
    env=IroncladEnv()
    for seed in range(984000,984100):
        obs=env.reset(candidate,seed,diagnostic=True)
        if any(c['name']=='Evolve' for c in obs['hand']):break
    obs=play(env,obs,'Evolve');obs=env.step(50)[0]
    wounds=sum(c['name']=='Wound' for c in obs['hand'])
    assert wounds>0
    assert len(obs['hand'])==min(10,5+wounds*(2 if up else 1))
