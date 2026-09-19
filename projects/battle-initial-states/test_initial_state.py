"""Semantic identity regressions for current initial-state requirements."""
import copy
import pytest
from initial_state import normalize, record, read_records, reset_payload, state_hash, write_records


def scene():
    return dict(character='IRONCLAD', ascension=20, act=1, floor=4,
                entry_timing='pre_combat_initialization',
                initialization_phase='before_destination_room_entry',
                player=dict(hp=65, max_hp=80, gold=99),
                deck=['Strike_R', 'Bash', 'Strike_R+1'],
                relics=['Burning Blood', {'name': 'Bottled Flame', 'card_index': 2}],
                potions=[None, None], encounter='JAW_WORM', burning_elite=False)


def test_bound_deck_permutation_invariance_and_different_binding():
    a = scene(); b = copy.deepcopy(a)
    b['deck'] = [a['deck'][2], a['deck'][0], a['deck'][1]]
    b['relics'][1]['card_index'] = 0
    assert normalize(a) == normalize(b)
    b['relics'][1]['card_index'] = 1
    assert state_hash(a) != state_hash(b)


def test_indistinguishable_copy_binding_is_equivalent():
    a = scene(); a['deck'] = ['Strike_R']*3
    b = copy.deepcopy(a); b['relics'][1]['card_index'] = 0
    assert state_hash(a) == state_hash(b)


@pytest.mark.parametrize('field', ['hp', 'max_hp', 'gold'])
def test_player_semantics_change_identity(field):
    a = scene(); b = copy.deepcopy(a); b['player'][field] += 1
    assert state_hash(a) != state_hash(b)


def test_order_counter_and_potion_slots_are_semantic():
    a = scene(); a['relics'] = ['Mutagenic Strength', 'Clockwork Souvenir', {'name':'Pen Nib','counter':8}]
    b = copy.deepcopy(a); b['relics'].reverse()
    assert state_hash(a) != state_hash(b)
    b = copy.deepcopy(a); b['relics'][-1]['counter'] = 9
    assert state_hash(a) != state_hash(b)
    a['potions'] = ['Fire Potion', None]; b = copy.deepcopy(a); b['potions'].reverse()
    assert state_hash(a) != state_hash(b)


def test_roundtrip_and_provenance_separation(tmp_path):
    a = record(scene(), {'source_seed':12}, {'confidence':'rule-derived'})
    b = record(scene(), {'source_seed':34}, {'confidence':'diagnostic'})
    assert a['state_hash'] == b['state_hash']
    path = tmp_path/'states.jsonl'; write_records(path,[a,b])
    assert read_records(path) == [a,b]
    assert reset_payload(a) == normalize(scene())
    assert 'source_seed' not in reset_payload(a)
    a['state']['player']['gold'] += 1
    with pytest.raises(ValueError, match='tampered'):
        write_records(path,[a])


def test_record_keeps_source_backbone_separate_from_projected_training_state():
    source = scene()
    source['potions'] = ['PowerPotion', None]
    projected = copy.deepcopy(source)
    projected['potions'] = [None, None]
    row = record(projected, {'source_seed': 12}, {'potion_projection': {'projected': True}},
                 source_backbone=source)
    assert row['state']['potions'] == [None, None]
    assert row['source_backbone']['potions'] == ['PowerPotion', None]
    assert row['source_backbone_hash'] != row['state_hash']


@pytest.mark.parametrize('change', [
    lambda s:s.update(environment_seed=100123),
    lambda s:s['player'].pop('gold'),
    lambda s:s['player'].update(hp=True),
    lambda s:s.update(deck=[{'name':'RitualDagger','misc':40}]),
    lambda s:s.update(burning_elite=None),
    lambda s:s.update(relics=['Bottled Flame']),
    lambda s:s.update(relics=[{'name':'Bottled Flame','card_index':99}]),
    lambda s:s.update(relics=[{'name':'Pen Nib'}]),
    lambda s:s.update(relics=['Pen Nib']),
    lambda s:s.update(relics=[{'name':'Pen Nib','counter':10}]),
    lambda s:s.update(relics=[{'name':'Burning Blood','counter':0}]),
    lambda s:s.update(deck=['RitualDagger']),
])
def test_missing_or_unknown_semantics_rejected(change):
    value = scene(); change(value)
    with pytest.raises(ValueError): normalize(value)
