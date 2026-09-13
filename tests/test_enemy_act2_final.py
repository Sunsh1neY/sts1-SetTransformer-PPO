"""剩余八遭遇真实入口、生命周期、关系融合与全卡共享路由。"""
import copy
import random
import pytest
import torch
from sts.env.ironclad import IroncladEnv
from sts.env.entities import encode_observation,collate
from sts.models.entities import UnifiedEntityActorCritic

NAMES=['THREE_BYRDS','CHOSEN_AND_BYRDS','TWO_THIEVES','GREMLIN_LEADER','AUTOMATON','COLLECTOR','CHAMP','MASKED_BANDITS_EVENT']

def start(name,deck=None,hp=500,seed=870000,budget=128,potions=None):
    scene=dict(entry_timing='pre_combat_initialization',initialization_phase='before_destination_room_entry',
        act=2,floor=34 if name in ['AUTOMATON','COLLECTOR','CHAMP'] else 29,character='IRONCLAD',ascension=20,
        player=dict(hp=hp,max_hp=hp,gold=100),deck=deck or ['Strike_R']*3+['Defend_R']*3+['Bash','Pommel Strike','Headbutt','True Grit'],
        relics=[],potions=potions or [None,None],encounter=name,burning_elite=False)
    env=IroncladEnv(budget);return env,env.reset(scene,seed,diagnostic=True)

@pytest.mark.parametrize('name',NAMES)
@pytest.mark.parametrize('seed',[870000,870001,870002])
def test_random_full_card_trace(name,seed):
    env,obs=start(name,hp=80,seed=seed)
    rng=random.Random(seed)
    for _ in range(128):
        sample=encode_observation(obs);collate([sample])
        actions=[r for r,c in zip(sample.routes,sample.candidates) if c.legal]
        assert actions
        obs,reward,term,trunc,info=env.step(rng.choice(actions))
        if term or trunc:
            encode_observation(obs)
            assert term and not trunc
            assert 'battle_exit' in info
            assert not any(e['present'] for e in obs['enemies'])
            return
    pytest.fail('未结算')


def held_state(seed=870000):
    env,obs=start('AUTOMATON',['Bludgeon']*3+['Impervious']*3+['Bash','Strike_R','Defend_R','Headbutt'],seed=seed)
    for _ in range(8):
        if len(obs['relations'])==2:return env,obs
        obs,*_=env.step(50)
    pytest.fail('两只铜球未扣牌')


def test_two_orbs_stasis_identity_only_and_shared_b_fusion():
    env,obs=held_state()
    assert len(obs['stasis'])==2
    assert all(set(c)=={'name'} for c in obs['stasis'])
    sample=encode_observation(obs);batch=collate([sample]);model=UnifiedEntityActorCritic().eval()
    assert (batch['held_card_index']>=0).sum()==2
    initial=model(batch)
    no_rel={**batch,'held_card_index':torch.full_like(batch['held_card_index'],-1)}
    zero=model(no_rel)
    torch.testing.assert_close(initial[0],zero[0]);torch.testing.assert_close(initial[1],zero[1])
    torch.nn.init.normal_(model.holds_fusion.weight,std=.1)
    scores,value=model(batch)
    perm=sample.permuted(list(reversed(range(len(sample.tokens)))))
    ps,pv=model(collate([perm]))
    torch.testing.assert_close(scores,ps,atol=1e-5,rtol=1e-5);torch.testing.assert_close(value,pv,atol=1e-5,rtol=1e-5)
    for actor in [True,False]:
        model.zero_grad();s,v=model(batch)
        loss=s.softmax(-1)[0,0] if actor else v.sum()
        loss.backward()
        assert model.holds_fusion.weight.grad.abs().sum()>0
    bad=copy.deepcopy(obs);bad['relations'][1]=bad['relations'][0]
    with pytest.raises(ValueError,match='冲突'):encode_observation(bad)


def test_old_snapshot_action_is_rejected():
    env,obs=start('GREMLIN_LEADER')
    sample=encode_observation(obs);old=next(r for r,c in zip(sample.routes,sample.candidates) if c.legal)
    env.step(50)
    with pytest.raises(ValueError,match='过期'):env.step(old)


def test_thieves_escape_removes_entities_and_reports_real_gold():
    env,obs=start('TWO_THIEVES',['Defend_R']*5)
    for _ in range(8):
        obs,reward,term,trunc,info=env.step(50)
        if term:break
    assert term and not trunc and reward>0
    assert info['battle_exit']['gold_delta']<0
    assert not any(e['present'] for e in obs['enemies'])
    assert not obs['relations']


def test_byrd_four_attacks_stun_without_extra_multiplier_feature():
    env,obs=start('THREE_BYRDS',['Pummel+1']*5)
    hp=obs['enemies'][0]['hp'];obs,*_=env.step(0)
    enemy=obs['enemies'][0]
    assert enemy['intent_kind']=='STUN'
    assert enemy['statuses'].get('Flight',0)==0
    assert hp-enemy['hp']==5
    for _ in range(3):obs,*_=env.step(50)
    assert obs['enemies'][0]['statuses']['Flight']==4
    assert not any('multiplier' in k for k in enemy)
    encode_observation(obs)


def strike_target(env,obs,index):
    action=next((i*5+index for i,c in enumerate(obs['hand']) if c['name']=='Bludgeon' and obs['action_mask'][i*5+index]),None)
    if action is None:return env.step(50)
    return env.step(action)

@pytest.mark.parametrize('name,boss',[('GREMLIN_LEADER','GREMLIN_LEADER'),('COLLECTOR','THE_COLLECTOR'),('AUTOMATON','BRONZE_AUTOMATON')])
def test_boss_victory_cleans_minions_relations_and_routes(name,boss):
    env,obs=start(name,['Bludgeon+1']*10,hp=2000)
    initial=next(e for e in obs['enemies'] if e['name']==boss)['hp']
    for _ in range(100):
        target=next(i for i,e in enumerate(obs['enemies']) if e['name']==boss)
        obs,reward,term,trunc,info=strike_target(env,obs,target)
        encode_observation(obs)
        if term:break
    assert term and not trunc and reward>0
    assert not any(e['present'] for e in obs['enemies'])
    assert not obs['stasis'] and not obs['relations']
    assert info['battle_exit']['deck_changes']==[]
    assert not any(obs['action_mask'])

@pytest.mark.parametrize('name',['GREMLIN_LEADER','COLLECTOR'])
def test_resummoned_same_slot_has_new_reference_and_empty_history(name):
    env,obs=start(name,['Bludgeon+1']*10,hp=2000)
    leader='GREMLIN_LEADER' if name=='GREMLIN_LEADER' else 'THE_COLLECTOR'
    removed={};replaced=False
    for _ in range(60):
        for i,old in removed.items():
            ref=obs['routing']['enemy_refs'][i]
            if ref is not None and ref!=old:
                assert obs['enemies'][i]['public_history']['completed_enemy_turns']==0
                replaced=True;break
        if replaced:break
        target=next((i for i,e in enumerate(obs['enemies']) if e['targetable'] and e['name']!=leader),None)
        if target is None:obs,*_=env.step(50);continue
        ref=obs['routing']['enemy_refs'][target]
        obs,reward,term,trunc,info=strike_target(env,obs,target)
        if not obs['enemies'][target]['present']:removed[target]=ref
        assert not term and not trunc
        encode_observation(obs)
    assert replaced


def test_champ_phase_changes_after_anger_and_history_is_natural():
    env,obs=start('CHAMP',['Bludgeon+1']*10,hp=2000)
    assert obs['enemies'][0]['phase']=='PHASE_1'
    for _ in range(80):
        prev=obs['enemies'][0]
        if prev['phase']=='PHASE_2':
            assert prev['hp']>0
            assert prev['statuses']['Strength']>=12
            assert any(prev['intent_history_valid'][1:])
            break
        if prev['hp']<=prev['max_hp']//2:obs,*_=env.step(50)
        else:obs,*_=strike_target(env,obs,0)
        encode_observation(obs)
    else:pytest.fail('第一勇士未进入公开第二阶段')


def test_killing_held_orb_returns_only_its_card():
    env,obs=start('AUTOMATON',['Bludgeon+1']*5+['Impervious']*5,hp=1000)
    for _ in range(8):
        if len(obs['relations'])==2:break
        obs,*_=env.step(50)
    assert len(obs['relations'])==2
    target=next(i for i,e in enumerate(obs['enemies']) if e['name']=='BRONZE_ORB')
    old_ref=obs['routing']['enemy_refs'][target]
    held=next(r['card_ref'] for r in obs['relations'] if r['enemy_ref']==old_ref)
    name=obs['stasis'][obs['routing']['stasis_refs'].index(held)]['name']
    for _ in range(16):
        obs,reward,term,trunc,_=strike_target(env,obs,target)
        if not obs['enemies'][target]['present']:break
        assert not term and not trunc
    assert not obs['enemies'][target]['present']
    assert len(obs['relations'])==1 and old_ref not in [r['enemy_ref'] for r in obs['relations']]
    assert any(c['name']==name for c in obs['hand'])
    encode_observation(obs)


def test_relation_binding_swap_affects_actor_and_critic_and_ref_renaming_does_not():
    env,obs=held_state()
    # 结构夹具：给两张公开扣牌不同身份、给两敌不同HP，不声称该人工交换是游戏可达轨迹。
    obs=copy.deepcopy(obs);obs['stasis'][0]['name']='Bludgeon';obs['stasis'][1]['name']='Impervious'
    sources=[obs['routing']['enemy_refs'].index(r['enemy_ref']) for r in obs['relations']]
    obs['enemies'][sources[0]]['hp']=10;obs['enemies'][sources[1]]['hp']=50
    swapped=copy.deepcopy(obs)
    swapped['relations'][0]['card_ref'],swapped['relations'][1]['card_ref']=swapped['relations'][1]['card_ref'],swapped['relations'][0]['card_ref']
    torch.manual_seed(72);model=UnifiedEntityActorCritic().eval();torch.nn.init.normal_(model.holds_fusion.weight,std=.25)
    a=encode_observation(obs);b=encode_observation(swapped)
    sa,va=model(collate([a]));sb,vb=model(collate([b]))
    assert (sa.softmax(-1)-sb.softmax(-1)).abs().max()>1e-7
    assert (va-vb).abs().max()>1e-7
    renamed=copy.deepcopy(obs)
    mapping={r:'opaque-'+str(i) for i,r in enumerate(obs['routing']['enemy_refs']+obs['routing']['stasis_refs']) if r is not None}
    for key in ['enemy_refs','stasis_refs']:renamed['routing'][key]=[mapping.get(r) for r in renamed['routing'][key]]
    for r in renamed['relations']:
        r['enemy_ref']=mapping[r['enemy_ref']];r['card_ref']=mapping[r['card_ref']]
    sr,vr=model(collate([encode_observation(renamed)]))
    torch.testing.assert_close(sa,sr);torch.testing.assert_close(va,vr)
    _,other=start('CHOSEN',['Strike_R']*25)
    mixed=model(collate([a,encode_observation(other)]))
    torch.testing.assert_close(sa[0],mixed[0][0,:sa.shape[1]],atol=1e-5,rtol=1e-5)
    torch.testing.assert_close(va[0],mixed[1][0],atol=1e-5,rtol=1e-5)


def test_new_model_state_restores_and_old_missing_fusion_is_rejected():
    import io
    _,obs=held_state();batch=collate([encode_observation(obs)])
    model=UnifiedEntityActorCritic().eval();buf=io.BytesIO()
    torch.nn.init.normal_(model.holds_fusion.weight,std=.1)
    torch.save(model.state_dict(),buf);buf.seek(0)
    restored=UnifiedEntityActorCritic().eval();state=torch.load(buf,weights_only=True);restored.load_state_dict(state)
    a=model(batch);b=restored(batch)
    torch.testing.assert_close(a[0],b[0]);torch.testing.assert_close(a[1],b[1])
    del state['holds_fusion.weight']
    with pytest.raises(RuntimeError):restored.load_state_dict(state)

def test_zero_initialized_fusion_has_separate_actor_critic_gradients():
    _,obs=held_state();batch=collate([encode_observation(obs)]);model=UnifiedEntityActorCritic().eval()
    for actor in [True,False]:
        model.zero_grad();s,v=model(batch)
        (s.softmax(-1)[0,0] if actor else v.sum()).backward()
        assert model.holds_fusion.weight.grad.abs().sum()>0

def test_stasis_relation_bad_endpoint_and_non_enemy_are_rejected():
    _,obs=held_state();bad=copy.deepcopy(obs);bad['relations'][0]['enemy_ref']='missing'
    with pytest.raises(ValueError):encode_observation(bad)
    sample=encode_observation(obs);source=next(i for i,x in enumerate(sample.tokens) if x.entity_type=='CARD')
    sample.held_card_index[source]=source
    with pytest.raises(ValueError):collate([sample])

def test_external_budget_never_emits_battle_exit():
    env,obs=start('COLLECTOR',budget=1)
    obs,reward,term,trunc,info=env.step(50)
    assert not term and trunc and reward==0
    assert 'battle_exit' not in info
    assert any(obs['action_mask'])
    encode_observation(obs)


def test_full_hand_stasis_return_goes_to_discard_with_existing_potion_action():
    env,obs=start('AUTOMATON',['Bludgeon+1']*10+['Offering']*20+['Strike_R']*5,
        hp=2000,potions=['Explosive Potion',None])
    for _ in range(8):
        if len(obs['relations'])==2:break
        obs,*_=env.step(50)
    assert len(obs['relations'])==2
    target=next(i for i,e in enumerate(obs['enemies']) if e['name']=='BRONZE_ORB')
    ref=obs['routing']['enemy_refs'][target]
    held=next(r['card_ref'] for r in obs['relations'] if r['enemy_ref']==ref)
    name=obs['stasis'][obs['routing']['stasis_refs'].index(held)]['name']
    for _ in range(80):
        hp=obs['enemies'][target]['hp']
        if hp>10:
            card_name='Bludgeon' if hp>42 else 'Strike_R'
            action=next((i*5+target for i,c in enumerate(obs['hand']) if c['name']==card_name and obs['action_mask'][i*5+target]),50)
        elif len(obs['hand'])<10:
            action=next((i*5 for i,c in enumerate(obs['hand']) if c['name']=='Offering' and obs['action_mask'][i*5]),50)
        else:break
        obs,_,term,trunc,_=env.step(action)
        assert not term and not trunc
    else:pytest.fail('未建立满手返牌场景')
    before=sum(c['name']==name for c in obs['discard_pile'])
    obs,*_=env.step(51)
    assert len(obs['hand'])==10
    assert sum(c['name']==name for c in obs['discard_pile'])==before+1
    assert len(obs['relations'])==1
    assert not obs['potions'][0]['present']
    encode_observation(obs)


def test_thieves_killed_return_stolen_gold_once_without_reward_change():
    env,obs=start('TWO_THIEVES',['Bludgeon+1']*10,hp=1000)
    obs,*_=env.step(50)
    for _ in range(20):
        target=next(i for i,e in enumerate(obs['enemies']) if e['targetable'])
        obs,reward,term,trunc,info=strike_target(env,obs,target)
        if term:break
    assert term and not trunc and reward>0
    # 正常战斗中其中一只可能已逃走；金币只收回被击杀者的部分。
    assert -100 < info['battle_exit']['gold_delta'] <= 0
    assert reward==pytest.approx(1+.5*obs['player']['hp']/obs['player']['max_hp'])
    with pytest.raises(RuntimeError):env.step(50)

@pytest.mark.parametrize('name',['THREE_BYRDS','CHOSEN_AND_BYRDS','MASKED_BANDITS_EVENT','CHAMP'])
def test_targeted_winning_trajectory(name):
    env,obs=start(name,['Bludgeon+1']*10,hp=2000,budget=128)
    for _ in range(128):
        target=next(i for i,e in enumerate(obs['enemies']) if e['targetable'])
        obs,reward,term,trunc,info=strike_target(env,obs,target)
        encode_observation(obs)
        if term or trunc:break
    assert term and not trunc and reward>0
    assert not any(obs['action_mask'])
