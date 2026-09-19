"""Owner-approved special relics: real backend decision-boundary checks."""
import pytest
from test_relic_batch_two import start, status
from test_relic_state import play
from sts.models.apath import encode


def test_pyramid_retains_cards_and_caps_hand():
    env, o, _ = start(['Runic Pyramid'], deck=['Defend_R']*8+['Defend_R+1']*7)
    initial = [c['upgrade_count'] for c in o['hand']]
    o = env.step(50)[0]
    assert len(o['hand']) == 10
    assert all(sum(c['upgrade_count']==u for c in o['hand']) >= initial.count(u) for u in initial)
    assert o['player']['energy'] == 3
    o = env.step(50)[0]
    assert len(o['hand']) == 10
    assert len(o['draw_pile']) == 5
    assert encode(o).routes


def test_pyramid_does_not_retain_ethereal_cards():
    env, o, _ = start(['Runic Pyramid'], deck=['Ghostly Armor']*15)
    initial = [c['upgrade_count'] for c in o['hand']]
    o = env.step(50)[0]
    assert len(o['exhaust_pile']) == len(initial)
    assert len(o['hand']) == 5



def test_top_draws_after_empty_hand_and_reshuffles():
    env, o, _ = start(['Unceasing Top'], deck=['Flex']*5)
    for _ in range(5):
        o = play(env, o, 'Flex')[0]
    assert len(o['hand']) == 1
    assert len(o['draw_pile']) == 4
    assert len(o['discard_pile']) == 0
    assert o['player']['energy'] == 3
    o = play(env, o, 'Flex')[0]
    assert len(o['hand']) == 1 and len(o['draw_pile']) == 3


def test_top_respects_no_draw_and_resets_next_turn():
    env, o, _ = start(['Unceasing Top'], deck=['Battle Trance']*10)
    o = play(env, o, 'Battle Trance')[0]
    assert status(o['player'], 'No Draw') == 1
    while o['hand']:
        o = play(env, o, 'Battle Trance')[0]
    assert not o['hand'] and len(o['draw_pile']) == 2
    o = env.step(50)[0]
    assert len(o['hand']) == 5 and status(o['player'], 'No Draw') == 0


def test_snecko_draw_and_cost_visibility():
    env, o, _ = start(['Snecko Eye'], deck=['Defend_R']*20)
    for turn in range(3):
        assert len(o['hand']) == 7
        costs = [c['effective_cost'] for c in o['hand']]
        assert all(c['effective_cost_known'] for c in o['hand'])
        assert all(0 <= cost <= 3 for cost in costs)
        assert any(cost != 1 for cost in costs)
        for region in ('draw_pile', 'discard_pile', 'exhaust_pile'):
            assert all(not c['effective_cost_known'] for c in o[region])
        assert encode(o).routes
        o = env.step(50)[0]


def test_snecko_confusion_precedes_clockwork_artifact():
    for relics in (['Snecko Eye','Clockwork Souvenir'], ['Clockwork Souvenir','Snecko Eye']):
        _, o, _ = start(relics, deck=['Defend_R']*20)
        assert status(o['player'], 'Confused') == 1
        assert status(o['player'], 'Artifact') == 1
        assert len(o['hand']) == 7


def test_choker_manual_limit_energy_and_turn_reset():
    env, o, _ = start(['Velvet Choker','Bag of Preparation'], deck=['Flex']*15)
    assert o['player']['energy'] == 4
    for count in range(1, 7):
        o = play(env, o, 'Flex')[0]
        assert o['player']['cards_played_this_turn'] == count
    assert len(o['hand']) == 1
    assert not any(o['action_mask'][:50])
    assert o['action_mask'][50]
    o = env.step(50)[0]
    assert o['player']['cards_played_this_turn'] == 0
    assert o['player']['energy'] == 4
    assert any(o['action_mask'][:50])


def test_choker_counts_automatic_havoc_chain():
    env, o, _ = start(['Velvet Choker'], deck=['Havoc+1']*20)
    o = play(env, o, 'Havoc')[0]
    assert o['player']['cards_played_this_turn'] == 6
    assert not any(o['action_mask'][:50])


def test_choker_counts_double_tap_replay():
    env, o, _ = start(['Velvet Choker','Bag of Preparation'], deck=['Double Tap']*5+['Strike_R']*5)
    o = play(env, o, 'Double Tap')[0]
    o = play(env, o, 'Strike_R')[0]
    assert o['player']['cards_played_this_turn'] == 3


@pytest.mark.parametrize('relics,artifact,loss', [
    (['Mutagenic Strength'],0,3),
    (['Mutagenic Strength','Clockwork Souvenir'],0,0),
    (['Clockwork Souvenir','Mutagenic Strength'],1,3)])
def test_mutagenic_strength_acquisition_order_and_expiry(relics, artifact, loss):
    env, o, _ = start(relics, deck=['Defend_R']*15)
    assert status(o['player'],'Strength') == 3
    assert status(o['player'],'Artifact') == artifact
    assert status(o['player'],'Lose Strength') == loss
    o = env.step(50)[0]
    assert status(o['player'],'Strength') == (3 if artifact else 3-loss)
    assert status(o['player'],'Lose Strength') == 0
    o = env.step(50)[0]
    assert status(o['player'],'Strength') == (3 if artifact else 3-loss)


def pellets(o):
    return next(r for r in o['relics'] if r['name']=='Orange Pellets')['state']['played_types']


def test_pellets_three_bits_trigger_and_next_turn_reset():
    env, o, _ = start(['Orange Pellets','Mutagenic Strength','Bag of Preparation'],
                      deck=['Anger']*3+['Flex']*3+['Inflame']*3)
    assert not any(pellets(o).values())
    o=play(env,o,'Anger')[0]
    assert pellets(o)==dict(attack_played=True,skill_played=False,power_played=False)
    o=play(env,o,'Flex')[0]
    assert status(o['player'],'Lose Strength')==5
    assert pellets(o)==dict(attack_played=True,skill_played=True,power_played=False)
    o=play(env,o,'Inflame')[0]
    assert status(o['player'],'Lose Strength')==0
    assert not any(pellets(o).values())
    assert encode(o).routes
    o=play(env,o,'Anger')[0]
    assert pellets(o)['attack_played']
    o=env.step(50)[0]
    assert not any(pellets(o).values())
    assert status(o['player'],'Strength')==7


@pytest.mark.parametrize('encounter', ['JAW_WORM','LAGAVULIN','THREE_SENTRIES','GREMLIN_LEADER'])
def test_dome_hides_plans_and_records_only_executed_actions(encounter):
    env, o, _ = start(['Runic Dome'], encounter=encounter, deck=['Defend_R']*20)
    base, visible, _ = start(encounter=encounter, deck=['Defend_R']*20)
    assert o['player']['energy'] == 4
    for m in o['enemies']:
        assert m['intent_history'] == [0,0,0]
        assert m['intent_history_valid'] == [False]*3
    for turn in range(2):
        for m in o['enemies']:
            assert m['intent_damage']==m['intent_hits']==0
            assert m['intent_kind'] in ('UNKNOWN','NONE')
        previous=[m['intent_history'][0] for m in visible['enemies']]
        o=env.step(50)[0]; visible=base.step(50)[0]
        for i,m in enumerate(o['enemies']):
            if m['present'] and m['public_history']['completed_enemy_turns']:
                assert m['intent_history'][0]==previous[i]
        assert encode(o).routes


def test_frozen_eye_positions_predict_next_draw_without_hidden_costs():
    env, o, _ = start(['Frozen Eye'], deck=['Defend_R']*8+['Strike_R']*8+['Flex']*4)
    for _ in range(2):
        pile=sorted(o['draw_pile'],key=lambda c:c['draw_position'])
        assert [c['draw_position'] for c in pile] == list(range(len(pile)))
        assert all(c['draw_position_known'] and not c['effective_cost_known'] for c in pile)
        predicted=[(c['name'],c['upgrade_count']) for c in pile[:5]]
        o=env.step(50)[0]
        assert [(c['name'],c['upgrade_count']) for c in o['hand']]==predicted
        assert all(not c['draw_position_known'] and c['draw_position'] is None for c in o['hand'])
        assert encode(o).routes


def test_new_observation_has_no_redundant_known_top_or_hidden_order():
    _, o, _ = start([],deck=['Defend_R']*20)
    for region in ('hand','draw_pile','discard_pile','exhaust_pile'):
        assert all('known_top' not in c and c['draw_position'] is None and not c['draw_position_known'] for c in o[region])
    assert encode(o).routes


def test_headbutt_uses_new_draw_position_and_clears_on_draw():
    env,o,_=start([],deck=['Headbutt','Strike_R','Defend_R','Flex','Wound'])
    o=play(env,o,'Strike_R')[0]
    o=play(env,o,'Defend_R')[0]
    o=play(env,o,'Headbutt')[0]
    routes=encode(o).routes
    index=next(i for i,c in enumerate(o['decision']['selection']['candidates']) if c['name']=='Strike_R')
    route=next(r for group in routes for r in group if r.get('candidate_index')==index)
    o=env.step(route)[0]
    known=[c for c in o['draw_pile'] if c['draw_position_known']]
    assert len(known)==1 and known[0]['name']=='Strike_R' and known[0]['draw_position']==0
    o=env.step(50)[0]
    assert not any(c['draw_position_known'] for c in o['hand'])


def bound_card(o, name):
    relation=next(r for r in o['relations'] if r.get('relic_name')==name)
    loc=o['routing']['bound_card_refs'][relation['card_ref']]
    return loc['region'],o[loc['region']][loc['index']]


def test_bottled_flame_exact_instance_and_cross_zone_relation():
    relic=dict(name='Bottled Flame',card_index=9)
    env,o,_=start([relic],deck=['Strike_R']*9+['Strike_R+1']+['Defend_R']*10)
    zone,card=bound_card(o,'Bottled Flame')
    assert zone=='hand' and card['upgrade_count']==1
    index=next(i for i,c in enumerate(o['hand']) if c['upgrade_count']==1)
    o=env.step(index*5)[0]
    zone,card=bound_card(o,'Bottled Flame')
    assert zone=='discard_pile' and card['upgrade_count']==1
    sample=encode(o)
    source=next(i for i,t in enumerate(sample.entities.tokens) if t.entity_type=='RELIC')
    assert sample.entities.tokens[sample.entities.held_card_index[source]].entity_type=='CARD'
    from sts.models.apath import APathActorCritic,batch_samples
    model=APathActorCritic()
    dist,value=model(batch_samples([sample]))
    assert value.isfinite().all() and dist.probs.isfinite().all()
    value.sum().backward()
    assert model.holds_fusion.weight.grad is not None


@pytest.mark.parametrize('relic', ['Bottled Flame',dict(name='Bottled Flame',card_index=-1),dict(name='Bottled Flame',card_index=100),dict(name='Bottled Flame',card_index=True)])
def test_bottle_rejects_missing_or_invalid_instance(relic):
    with pytest.raises((ValueError,TypeError)):
        start([relic])


def test_bottle_rejects_wrong_card_type():
    with pytest.raises(ValueError,match='type mismatch'):
        start([dict(name='Bottled Flame',card_index=0)],deck=['Defend_R']*10)


def test_bound_relation_permutation_and_duplicate_card_identity():
    import numpy as np
    import torch
    from sts.models.apath import APathActorCritic,batch_samples,adapt
    _,o,_=start([dict(name='Bottled Flame',card_index=3)],deck=['Strike_R']*20)
    sample=encode(o)
    assert sum(t.entity_type=='RELIC' and sample.entities.held_card_index[i]>=0 for i,t in enumerate(sample.entities.tokens))==1
    model=APathActorCritic().eval()
    with torch.no_grad():
        d,v=model(batch_samples([sample]))
        shuffled=adapt(sample.entities.permuted(np.random.default_rng(8).permutation(len(sample.entities.tokens))))
        e,w=model(batch_samples([shuffled]))
    assert torch.allclose(v,w,atol=1e-5)
    assert torch.allclose(d.probs,e.probs,atol=1e-5)


def test_bottled_lightning_tracks_exhausted_skill():
    env,o,_=start([dict(name='Bottled Lightning',card_index=12)],deck=['Defend_R']*12+['Seeing Red'])
    assert bound_card(o,'Bottled Lightning')[0]=='hand'
    o=play(env,o,'Seeing Red')[0]
    zone,card=bound_card(o,'Bottled Lightning')
    assert zone=='exhaust_pile' and card['name']=='Seeing Red'
    assert encode(o).routes


def test_bottled_tornado_power_leaves_card_zones():
    env,o,_=start([dict(name='Bottled Tornado',card_index=12)],deck=['Defend_R']*12+['Inflame'])
    assert bound_card(o,'Bottled Tornado')[0]=='hand'
    o=play(env,o,'Inflame')[0]
    assert status(o['player'],'Strength')==2
    assert not any(r.get('relic_name')=='Bottled Tornado' for r in o['relations'])
    assert encode(o).routes


def test_three_bottles_coexist_with_distinct_exact_instances():
    relics=[dict(name=name,card_index=i) for i,name in enumerate(('Bottled Flame','Bottled Lightning','Bottled Tornado'))]
    _,o,_=start(relics,deck=['Strike_R+1','Defend_R+1','Inflame+1']+['Strike_R']*17)
    for r in relics:
        zone,card=bound_card(o,r['name'])
        assert zone=='hand' and card['upgrade_count']==1
    assert encode(o).routes


BATCH_THREE=['Runic Pyramid','Unceasing Top','Snecko Eye','Velvet Choker',
             'Mutagenic Strength','Orange Pellets','Runic Dome','Frozen Eye',
             'Bottled Flame','Bottled Lightning','Bottled Tornado']


def batch_scene_relic(name):
    if name.startswith('Bottled '):
        return [dict(name=name,card_index={'Bottled Flame':0,'Bottled Lightning':1,'Bottled Tornado':2}[name])]
    return [name]


@pytest.mark.parametrize('name',BATCH_THREE)
def test_each_third_batch_relic_model_and_replay(name):
    import json
    import torch
    from sts.env.relics import RelicEnv
    from sts.models.apath import APathActorCritic,batch_samples
    from sts.train.apath import sample_digest,plain_route,bind_route
    env,o,initial=start(batch_scene_relic(name),deck=['Strike_R','Defend_R','Inflame']+['Defend_R']*12)
    sample=encode(o)
    model=APathActorCritic().eval()
    with torch.no_grad():
        dist,value=model(batch_samples([sample]))
    assert value.isfinite().all() and dist.probs.sum().item()==pytest.approx(1)
    route=next(r for group in sample.routes for r in group if r.get('action')==50)
    after=env.step(route)
    replay=RelicEnv(); before=replay.reset(json.loads(json.dumps(initial)),100123,diagnostic=True)
    recovered=replay.step(bind_route(plain_route(route),before))
    assert sample_digest(encode(after[0]))==sample_digest(encode(recovered[0]))
    assert after[1:4]==recovered[1:4]
    assert after[4]['reward_accounting']==recovered[4]['reward_accounting']
    assert not after[4]['training_admitted']


from test_relic_batch_two import ACT12


@pytest.mark.parametrize('encounter',ACT12)
@pytest.mark.parametrize('name',BATCH_THREE)
def test_third_batch_act12_reset_step_surface(name,encounter):
    env,o,_=start(batch_scene_relic(name),encounter=encounter,deck=['Strike_R','Defend_R','Inflame']+['Defend_R']*12)
    assert encode(o).routes
    o=env.step(50)[0]
    assert encode(o).entities.tokens
