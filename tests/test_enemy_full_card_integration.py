"""共享全卡实现与新敌人的真实交互、候选和统一模型接入。"""
import copy
import pytest
import torch
from sts.env.ironclad import IroncladEnv
from sts.env.entities import encode_observation,collate,FEATURE_DIMS
from sts.models.entities import UnifiedEntityActorCritic


def start(name,deck,seed=850000):
    scene=dict(entry_timing='pre_combat_initialization',initialization_phase='before_destination_room_entry',
      act=2 if name=='SNECKO' else 3,floor=29 if name=='SNECKO' else 46,character='IRONCLAD',ascension=20,player=dict(hp=1000,max_hp=1000,gold=0),
      deck=deck,relics=[],potions=[None,None],encounter=name,burning_elite=False)
    env=IroncladEnv(32)
    return env,env.reset(scene,seed,diagnostic=True)


def play(env,obs,name):
    i=next(i for i,c in enumerate(obs['hand']) if c['name']==name)
    assert obs['action_mask'][i*5]
    return env.step(i*5)[0]


def test_double_tap_strike_updates_transient_real_strength_and_cost():
    env,obs=start('TRANSIENT',['Double Tap','Strike_R','Defend_R','Defend_R','Defend_R'])
    obs=play(env,obs,'Double Tap');energy=obs['player']['energy'];hp=obs['enemies'][0]['hp']
    obs=play(env,obs,'Strike_R')
    assert obs['player']['energy']==energy-1
    assert obs['enemies'][0]['hp']==hp-12
    assert obs['enemies'][0]['statuses']['Strength']==-12
    assert obs['enemies'][0]['intent_damage']==28
    assert obs['player']['cards_played_this_turn']==3
    sample=encode_observation(obs)
    assert sample.edges.shape[-1]==0
    assert FEATURE_DIMS['CARD']==116


def test_headbutt_shared_choice_and_model_permutation_on_maw():
    env,obs=start('MAW',['Seeing Red','Defend_R','Strike_R','Headbutt','Double Tap'])
    for name in ['Seeing Red','Defend_R','Strike_R','Headbutt']:
        obs=play(env,obs,name)
    assert obs['decision']['phase']=='SELECT_CARD'
    sample=encode_observation(obs)
    assert any(c.legal for c in sample.candidates)
    model=UnifiedEntityActorCritic().eval()
    logits,value=model(collate([sample]))
    moved=sample.permuted(list(reversed(range(len(sample.tokens)))))
    moved_logits,moved_value=model(collate([moved]))
    torch.testing.assert_close(logits,moved_logits,atol=1e-5,rtol=1e-5)
    torch.testing.assert_close(value,moved_value,atol=1e-5,rtol=1e-5)
    assert torch.isfinite(value).all()
    (logits[torch.isfinite(logits)].sum()+value.sum()).backward()
    assert model.projections['ENEMY'].weight.grad is not None
    selected=next(route for route,c in zip(sample.routes,sample.candidates) if c.legal)
    obs,*_=env.step(selected)
    assert obs['decision']['phase']=='NORMAL'
    assert any(c.get('known_top',False) for c in obs['draw_pile'])
    encode_observation(obs)


def test_transient_full_card_terminal_and_budget_remain_distinct():
    env,obs=start('TRANSIENT',['Impervious']*5)
    for _ in range(6):
        obs,reward,term,trunc,info=env.step(50)
        encode_observation(obs)
        if term:break
    assert term and not trunc and reward>0
    assert not any(e['present'] for e in obs['enemies'])


def test_malformed_history_does_not_silently_zero_fill():
    _,obs=start('MAW',['Strike_R']*5)
    obs=copy.deepcopy(obs);obs['enemies'][0]['intent_history_valid'][0]=False
    with pytest.raises(ValueError,match='历史'):
        encode_observation(obs)


@pytest.mark.parametrize('seed',[850000,850001,850002])
def test_snecko_shared_effective_cost_and_legal_payment(seed):
    env,obs=start('SNECKO',['Bludgeon']*5+['Defend_R']*5,seed)
    assert obs['enemies'][0]['intent_kind']=='STRONG_DEBUFF'
    obs,*_=env.step(50)
    assert obs['player']['statuses']['Confused']==1
    assert all(c['effective_cost_known'] and 0<=c['effective_cost']<=3 for c in obs['hand'])
    encode_observation(obs)
    seen=set()
    while True:
        legal=[(i,c) for i,c in enumerate(obs['hand']) if obs['action_mask'][i*5]]
        if not legal:break
        i,card=min(legal,key=lambda item:item[1]['effective_cost'])
        energy=obs['player']['energy'];fee=card['effective_cost'];seen.add(fee)
        obs,*_=env.step(i*5)
        assert obs['player']['energy']==energy-fee
        assert all(not c['effective_cost_known'] for c in obs['discard_pile'])
        encode_observation(obs)
    assert seen



def test_dynamic_padding_preserves_existing_sample_policy_and_value():
    _,small=start('MAW',['Strike_R']*5)
    _,large=start('TRANSIENT',['Defend_R']*10)
    first=encode_observation(small);second=encode_observation(large)
    model=UnifiedEntityActorCritic().eval()
    with torch.no_grad():
        logits,value=model(collate([first]))
        batch_logits,batch_value=model(collate([first,second]))
    torch.testing.assert_close(logits[0],batch_logits[0,:len(first.candidates)],atol=1e-5,rtol=1e-5)
    torch.testing.assert_close(value[0],batch_value[0],atol=1e-5,rtol=1e-5)
