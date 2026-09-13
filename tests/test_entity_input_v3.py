"""用户裁定的费用、顶牌记忆及资源拆批。"""
import copy
import numpy as np
import pytest
from sts.env.entities import CONTRACT, card_features, encode_observation, collate_chunks
from test_unified_entities import observation


def indices():
    fields = list(CONTRACT['card_numeric_scales']) + CONTRACT['card_boolean_fields']
    return {name: i for i, name in enumerate(fields)}


def test_free_payment_and_distinct_recovery_and_nonhand_printed_cost():
    _, obs = observation()
    card = copy.deepcopy(obs['hand'][0])
    card.update(base_cost=2, cost=2, printed_cost=3, effective_cost=0, free_to_play_once=True)
    other = dict(card, cost=1)
    a, b = card_features(card, 'hand'), card_features(other, 'hand')
    ix = indices()
    assert a[ix['pay_cost']] == b[ix['pay_cost']] == 0
    assert a[ix['recovery_cost']] == .5 and b[ix['recovery_cost']] == .25
    assert card_features(card, 'draw_pile')[ix['pay_cost']] == .75
    card['recovery_cost'] = 1
    assert card_features(card, 'draw_pile')[ix['recovery_cost']] == .25


def test_x_category_has_no_predicted_energy_or_hit_override():
    _, obs = observation()
    card = dict(obs['hand'][0], cost_kind='X', printed_cost=-1, effective_cost=7)
    features = card_features(card, 'hand')
    assert features[indices()['pay_cost']] == 0
    assert features[indices()['hits']] == card['hits'] / 5


def test_known_top_is_single_public_card_and_not_a_hand_slot():
    _, obs = observation(12)
    card = obs['draw_pile'][0]
    card['known_top'] = True
    sample = encode_observation(obs)
    ix = indices()['known_top']
    assert sum(t.features[ix] for t in sample.tokens if t.entity_type == 'CARD') == 1
    obs['draw_pile'][1]['known_top'] = True
    with pytest.raises(ValueError, match='一张'):
        encode_observation(obs)
    with pytest.raises(ValueError, match='抽牌堆'):
        card_features(card, 'hand')


def test_resource_split_preserves_every_sample():
    _, obs = observation(96)
    sample = encode_observation(obs)
    batches = list(collate_chunks([sample] * 220))
    assert len(batches) > 1
    assert sum(b['entity_valid'].shape[0] for b in batches) == 220
    assert all(b['edges'].shape[-1] == 0 for b in batches)
