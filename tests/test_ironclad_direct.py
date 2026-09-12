"""直接效果七类牌逐版本真实结算、状态关联与新实体编码。"""
import pytest
from sts.env.entities import encode_observation, collate
from sts.env.ironclad import IroncladEnv
from sts.models.entities import UnifiedEntityActorCritic
from test_ironclad_dynamics import start, play, rows
from test_ironclad_expansion import scene

NAMES = ['Clash','Hemokinesis','Bloodletting','Intimidate','Limit Break','Offering','Shockwave']


def upgraded(name, up):
    return name + ('+1' if up else '')


@pytest.mark.parametrize('up',[False, True])
def test_clash_mask_rejects_nonattacks_then_accepts_after_skill_play(up):
    env, obs = start([upgraded('Clash',up),'Defend_R',*['Strike_R']*3])
    slot = next(i for i,c in enumerate(obs['hand']) if c['name']=='Clash')
    assert not obs['action_mask'][slot*5:slot*5+5].any()
    obs=play(env,obs,'Defend_R')
    enemy=obs['enemies'][0];before=enemy['hp']+enemy['block']
    obs=play(env,obs,'Clash')
    assert before-obs['enemies'][0]['hp']-obs['enemies'][0]['block']==(18 if up else 14)


@pytest.mark.parametrize('name,hp_loss,energy_gain',[('Bloodletting',3,2),('Offering',6,2),('Hemokinesis',2,-1)])
@pytest.mark.parametrize('up',[False,True])
def test_self_loss_energy_and_blood_for_blood_event(name,hp_loss,energy_gain,up):
    env,obs=start([upgraded(name,up),'Blood for Blood',*['Strike_R']*3])
    hp,energy=obs['player']['hp'],obs['player']['energy']
    obs=play(env,obs,name)
    assert obs['player']['hp']==hp-hp_loss
    assert obs['player']['energy']==energy+(3 if name=='Bloodletting' and up else energy_gain)
    assert rows(obs,'Blood for Blood')[0]['base_cost']==3
    assert (any(c['name']==name for c in obs['exhaust_pile']))==(name=='Offering')


@pytest.mark.parametrize('up',[False,True])
def test_hemokinesis_attack_damage_and_export(up):
    env,obs=start([upgraded('Hemokinesis',up),*['Strike_R']*4])
    card=next(c for c in obs['hand'] if c['name']=='Hemokinesis')
    assert card['damage']==(20 if up else 15) and card['magic']==2
    before=obs['enemies'][0]['hp']+obs['enemies'][0]['block']
    obs=play(env,obs,'Hemokinesis')
    assert before-obs['enemies'][0]['hp']-obs['enemies'][0]['block']==card['damage']


@pytest.mark.parametrize('name,base,plus',[('Intimidate',1,2),('Shockwave',3,5)])
@pytest.mark.parametrize('up',[False,True])
def test_all_enemy_debuffs_and_exhaust(name,base,plus,up):
    candidate=scene([upgraded(name,up),*['Strike_R']*4]);candidate.update(encounter='EXORDIUM_THUGS',relics=[])
    env=IroncladEnv();obs=env.reset(candidate,982301,diagnostic=True)
    obs=play(env,obs,name)
    for enemy in obs['enemies']:
        if enemy['present']:
            assert enemy['statuses']['Weak']==(plus if up else base)
            if name=='Shockwave': assert enemy['statuses']['Vulnerable']==(plus if up else base)
    assert any(c['name']==name for c in obs['exhaust_pile'])


@pytest.mark.parametrize('up',[False,True])
def test_shockwave_artifact_consumes_first_debuff_only(up):
    candidate=scene([upgraded('Shockwave',up),*['Strike_R']*4]);candidate.update(encounter='THREE_SENTRIES',relics=[])
    env=IroncladEnv();obs=env.reset(candidate,982302,diagnostic=True)
    obs=play(env,obs,'Shockwave')
    for enemy in obs['enemies']:
        if enemy['present']:
            assert not enemy['statuses'].get('Artifact',0)
            assert not enemy['statuses'].get('Weak',0)
            assert enemy['statuses']['Vulnerable']==(5 if up else 3)


@pytest.mark.parametrize('up',[False,True])
def test_limit_break_strength_doubles_and_upgrade_removes_exhaust(up):
    env,obs=start([upgraded('Limit Break',up),'Flex',*['Strike_R']*3])
    obs=play(env,obs,'Flex');obs=play(env,obs,'Limit Break')
    assert obs['player']['statuses']['Strength']==4
    assert any(c['name']=='Limit Break' for c in obs['discard_pile' if up else 'exhaust_pile'])
    obs=env.step(50)[0]
    assert obs['player']['statuses']['Strength']==2


@pytest.mark.parametrize('up',[False,True])
@pytest.mark.parametrize('no_draw',[False,True])
def test_offering_draw_count_and_no_draw(up,no_draw):
    candidate=scene([upgraded('Offering',up),'Battle Trance',*['Strike_R']*10]);candidate.update(encounter='LAGAVULIN',relics=[])
    env=IroncladEnv()
    for seed in range(982310,982410):
        obs=env.reset(candidate,seed,diagnostic=True)
        if {'Offering','Battle Trance'} <= {c['name'] for c in obs['hand']}: break
    else: raise AssertionError('未找到公开初始手牌夹具')
    if no_draw: obs=play(env,obs,'Battle Trance')
    before=len(obs['hand']);hp=obs['player']['hp']
    obs=play(env,obs,'Offering')
    assert len(obs['hand'])==min(10,before-1+(0 if no_draw else 5 if up else 3))
    assert obs['player']['hp']==hp-6


@pytest.mark.parametrize('name',NAMES)
@pytest.mark.parametrize('up',[False,True])
def test_every_new_version_reaches_unified_model(name,up):
    _,obs=start([upgraded(name,up),*['Strike_R']*4])
    model=UnifiedEntityActorCritic();distribution,value=model.distribution(collate([encode_observation(obs)]))
    assert distribution.probs.isfinite().all() and value.isfinite().all()
