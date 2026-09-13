"""共享模型交接测试：只测实体与路由，不建立第二套编码器。"""
import pytest
from sts.env.enemy_potion_entities import EnemyPotionEntityView
from test_enemy_potion import start


def test_dynamic_entities_and_reordering_keep_target_identity():
    env,obs=start('TWO_LOUSE','Fire Potion')
    view=EnemyPotionEntityView();view.reset();data=view.update(obs)
    assert len(data['enemy_entities'])==2 and len(data['potion_entities'])==1
    target=data['enemy_entities'][1]['reference']
    source=data['potion_entities'][0]['reference']
    data['enemy_entities'].reverse()
    action=view.resolve_potion(source,target,revision=data['revision'])
    assert action==52
    for entity in data['enemy_entities']+data['potion_entities']:
        assert not {'slot','reference','seed','rng','unique_id'} & entity['features'].keys()
    after,*_=env.step(action);updated=view.update(after)
    assert len(updated['potion_entities'])==0
    assert target not in [e['reference'] for e in updated['enemy_entities']]
    with pytest.raises(ValueError):view.resolve_potion(source,target,revision=data['revision'])
    with pytest.raises(ValueError):view.resolve_potion(source,target,revision=updated['revision'])


def test_split_invalidates_parent_reference():
    env,obs=start('SLIME_BOSS',deck=['Bludgeon']*10,hp=500)
    view=EnemyPotionEntityView();view.reset();old=view.update(obs)
    parent=old['enemy_entities'][0]['reference']
    for _ in range(3):
        slot=next(i for i,c in enumerate(obs['hand']) if c['name']=='Bludgeon')
        obs,*_=env.step(slot*5);view.update(obs)
        obs,*_=env.step(50);data=view.update(obs)
    assert len(data['enemy_entities'])==2
    assert parent not in [e['reference'] for e in data['enemy_entities']]
    assert len(set(data['routing']['enemy_target_references'].values()))==2


def test_passive_fairy_and_reset_references():
    env,obs=start('JAW_WORM','FairyPotion',hp=1)
    view=EnemyPotionEntityView();view.reset();old=view.update(obs)
    assert old['routing']['legal_potion_actions']==[]
    assert old['potion_entities'][0]['features']['activation']=='passive_on_lethal_damage'
    after,*_=env.step(50);assert view.update(after)['potion_entities']==[]
    view.reset();new=view.update(obs)
    assert old['enemy_entities'][0]['reference']!=new['enemy_entities'][0]['reference']


def test_hidden_fields_are_rejected():
    env,obs=start()
    obs['enemies'][0]['future_intent']='ATTACK'
    with pytest.raises(ValueError):EnemyPotionEntityView().update(obs)


@pytest.mark.parametrize('encounter', ['CULTIST', 'HEXAGHOST', 'JAW_WORM'])
def test_three_intents_shift_at_enemy_turn_and_reset(encounter):
    env, obs = start(encounter, hp=500)
    first = obs['enemies'][0]['intent_history']
    assert obs['enemies'][0]['intent_history_valid'] == [True, False, False]
    assert first[1:] == [0, 0]
    obs, *_ = env.step(50)
    second = obs['enemies'][0]['intent_history']
    assert second[1:] == [first[0], 0]
    obs, *_ = env.step(50)
    third = obs['enemies'][0]['intent_history']
    if encounter == 'CULTIST':
        # 固定攻击使用NoOpRollMove，不重新设置意图；直接导出保留这一语义。
        assert third == second
        assert obs['enemies'][0]['intent_history_valid'] == [True, True, False]
    else:
        assert third[1:] == second[:2]
        assert obs['enemies'][0]['intent_history_valid'] == [True, True, True]
    view = EnemyPotionEntityView(); view.reset()
    features = view.update(obs)['enemy_entities'][0]['features']
    assert features['intent_history'] == third
    _, reset = start(encounter, hp=500)
    assert reset['enemies'][0]['intent_history_valid'] == [True, False, False]


def test_player_action_does_not_advance_intent_history():
    env, obs = start('CULTIST', deck=['Defend_R']*10)
    before = obs['enemies'][0]['intent_history'][:]
    obs, *_ = env.step(0)
    assert obs['enemies'][0]['intent_history'] == before
    assert all(e['intent_history_valid'] == [False]*3 for e in obs['enemies'][1:])


def test_split_replacement_does_not_inherit_parent_intents():
    env, obs = start('SLIME_BOSS', deck=['Bludgeon']*10, hp=500)
    for _ in range(3):
        slot = next(i for i,c in enumerate(obs['hand']) if c['name']=='Bludgeon')
        obs, *_ = env.step(slot*5)
        obs, *_ = env.step(50)
    assert all(e['intent_history_valid'] == [True, False, False]
               for e in obs['enemies'] if e['targetable'])


@pytest.mark.parametrize('case', ['length', 'mask', 'negative'])
def test_malformed_intent_history_is_rejected(case):
    from sts.env.enemy_potion import normalize_observation
    _, obs = start()
    obs['action_mask'] = obs['action_mask'].tolist()
    enemy = obs['enemies'][0]
    if case == 'length':
        enemy['intent_history'].pop()
    elif case == 'mask':
        enemy['intent_history_valid'][0] = False
    else:
        enemy['intent_history'][0] = -1
    with pytest.raises(ValueError, match='意图'):
        normalize_observation(obs)


def test_horde_initialization_placeholder_is_not_history():
    from test_act23_enemies import start as start_act23
    _, obs = start_act23('JAW_WORM_HORDE', 0)
    assert all(e['intent_history_valid'] == [True, False, False]
               for e in obs['enemies'] if e['present'])


def test_split_intent_overwrite_preserves_backend_history_tail():
    env, obs = start('SLIME_BOSS', deck=['Bludgeon']*10, hp=500)
    obs, *_ = env.step(50)
    original = obs['enemies'][0]['intent_history'][:]
    for _ in range(3):
        slot = next(i for i,c in enumerate(obs['hand']) if c['name']=='Bludgeon')
        obs, *_ = env.step(slot*5)
        if obs['enemies'][0]['hp'] <= obs['enemies'][0]['max_hp']//2:
            break
        obs, *_ = env.step(50)
        original = obs['enemies'][0]['intent_history'][:]
    final = obs['enemies'][0]['intent_history']
    assert final[0] != original[0]
    assert final[1:] == original[1:]
