"""六类选择牌真实候选、续跑、跨区域与公开顶牌。"""
import pytest
from test_ironclad_dynamics import start,play,rows
from test_ironclad_direct import upgraded
from sts.env.entities import encode_observation,collate
from sts.models.entities import UnifiedEntityActorCritic


def choose(env,obs,name):
    assert obs['decision']['phase']=='SELECT_CARD'
    sample=encode_observation(obs)
    distribution,_=UnifiedEntityActorCritic().distribution(collate([sample]))
    assert distribution.probs.isfinite().all()
    index=next(i for i,c in enumerate(obs['decision']['selection']['candidates']) if c['name']==name)
    return env.step(sample.routes[index])[0]


@pytest.mark.parametrize('up',[False,True])
def test_armaments_single_or_all_upgrade_without_fake_selection(up):
    env,obs=start([upgraded('Armaments',up),'Strike_R','Defend_R','Sentinel','Wound'])
    obs=play(env,obs,'Armaments')
    if up:assert obs['decision']['phase']=='NORMAL'
    else:obs=choose(env,obs,'Strike_R')
    assert obs['player']['block']==5
    assert next(c for c in obs['hand'] if c['name']=='Strike_R')['upgrade_count']==1
    assert next(c for c in obs['hand'] if c['name']=='Defend_R')['upgrade_count']==int(up)


@pytest.mark.parametrize('up',[False,True])
def test_burning_pact_selects_sentinel_then_draws(up):
    env,obs=start([upgraded('Burning Pact',up),'Sentinel','Strike_R','Defend_R','Wound'])
    energy=obs['player']['energy'];obs=play(env,obs,'Burning Pact')
    assert obs['resolving'][0]['name']=='Burning Pact'
    obs=choose(env,obs,'Sentinel')
    assert obs['player']['energy']==energy-1+2
    assert any(c['name']=='Sentinel' for c in obs['exhaust_pile'])
    assert obs['decision']['phase']=='NORMAL'


@pytest.mark.parametrize('up',[False,True])
def test_dual_wield_copies_selected_instance_and_preserves_upgrade(up):
    env,obs=start([upgraded('Dual Wield',up),'Rampage+1','Strike_R','Defend_R','Wound'])
    obs=play(env,obs,'Dual Wield');obs=choose(env,obs,'Rampage')
    cards=rows(obs,'Rampage')
    assert len(cards)==(3 if up else 2)
    assert all(c['upgrade_count']==1 for c in cards)


@pytest.mark.parametrize('up',[False,True])
def test_exhume_cross_zone_candidates_and_returns_selected(up):
    env,obs=start([upgraded('Exhume',up),'Second Wind','Wound','Dazed','Strike_R'])
    obs=play(env,obs,'Second Wind')
    # Exhume也是非攻击被耗尽；先用另一张Exhume夹具，避免依赖非法手牌。
    assert any(c['name']=='Exhume' for c in obs['exhaust_pile'])
    env,obs=start([upgraded('Exhume',up),'Intimidate','Seeing Red','Strike_R','Strike_R'])
    obs=play(env,obs,'Intimidate');obs=play(env,obs,'Seeing Red');obs=play(env,obs,'Exhume')
    assert obs['decision']['selection']['candidate_zone']=='exhaust_pile'
    obs=choose(env,obs,'Intimidate')
    assert any(c['name']=='Intimidate' for c in obs['hand'])
    assert any(c['name']=='Exhume' for c in obs['exhaust_pile'])


@pytest.mark.parametrize('up',[False,True])
def test_headbutt_cross_zone_known_top_then_draw_clears(up):
    env,obs=start([upgraded('Headbutt',up),'Strike_R','Defend_R','Pommel Strike','Seeing Red'])
    obs=play(env,obs,'Seeing Red');obs=play(env,obs,'Defend_R');obs=play(env,obs,'Strike_R');obs=play(env,obs,'Headbutt')
    assert obs['decision']['selection']['candidate_zone']=='discard_pile'
    obs=choose(env,obs,'Defend_R')
    marked=[c for c in obs['draw_pile'] if c.get('known_top',False)]
    assert len(marked)==1 and marked[0]['name']=='Defend_R'
    obs=play(env,obs,'Pommel Strike')
    assert not any(c.get('known_top',False) for c in obs['draw_pile'])
    assert any(c['name']=='Defend_R' for c in obs['hand'])


@pytest.mark.parametrize('up',[False,True])
def test_warcry_marks_only_selected_top_and_source_exhausts(up):
    env,obs=start([upgraded('Warcry',up),'Strike_R','Defend_R','Sentinel','Wound'])
    obs=play(env,obs,'Warcry');obs=choose(env,obs,'Sentinel')
    assert [c['name'] for c in obs['draw_pile'] if c.get('known_top',False)]==['Sentinel']
    assert any(c['name']=='Warcry' for c in obs['exhaust_pile'])
    encode_observation(obs)
