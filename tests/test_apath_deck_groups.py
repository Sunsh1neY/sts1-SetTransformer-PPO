"""分组提案的稳定语义与来源隔离检查；不验收正式采集。"""
from pathlib import Path
import runpy

MODULE = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/propose-a-path-deck-groups.py'))
classify = MODULE['classify']
STARTER = ['AscendersBane', 'Bash', *['Strike_R']*5, *['Defend_R']*4]


def test_single_scaling_card_and_actual_pair_are_distinct():
    assert classify(STARTER + ['Demon Form'])['group'] == 'simple'
    assert classify(STARTER + ['Demon Form', 'Heavy Blade'])['group'] == 'transition'
    assert classify(STARTER + ['Offering'])['families'] == {}
    assert not classify(STARTER + ['Offering'])['resource_dense']


def test_three_element_exhaust_and_multiple_families():
    for cards in (['Corruption', 'Feel No Pain', 'Burning Pact'],
                  ['Dark Embrace', 'Feel No Pain', 'True Grit'],
                  ['Juggernaut', 'Feel No Pain', 'Sever Soul']):
        assert classify(STARTER + cards)['group'] == 'combo'
    assert classify(STARTER + ['Demon Form', 'Heavy Blade', 'Limit Break'])['engines']


def test_permutation_upgrade_and_final_origin_do_not_drive_grouping():
    cards = STARTER + ['Body Slam', 'Anger']
    a = classify(cards)
    b = classify(list(reversed(cards)))
    assert a == b and a['group'] == 'simple'
    # 升级版本保留在台账；结构标签不以是否升级代替组合规则。
    assert classify([c+'+1' if c != 'AscendersBane' else c for c in cards]) == a


def test_eligible_inventory_mass_balance_and_transition_proposal():
    result = MODULE['build']()
    rows = result['contents']
    assert len(rows) == 74 and sum(len(r['sources']) for r in rows) == 139
    assert len({r['content_id'] for r in rows}) == len(rows)
    assert result['training_pool_frozen'] is False
    assert {r['group'] for r in rows} == set(MODULE['LABELS'])
    train = [r for r in rows if r['split'] == 'train_candidate']
    dev = [r for r in rows if r['split'] == 'development']
    assert not ({r['component_id'] for r in train} & {r['component_id'] for r in dev})
    assert all(classify(r['cards'])['group'] == r['group'] for r in rows)
    # 仅核对提案算术，不能声称实际采集已经达到此份额。
    proposal = result['proposal']
    assert sum(proposal['persistent_env_slots'].values()) == 8
    for group, slots in proposal['persistent_env_slots'].items():
        assert slots / 8 == proposal['transition_weights'][group]
    assert all({s['origin'] for s in r['sources']} == {'intermediate'} for r in train if r['group'] == 'simple')
    assert any(any(s['origin'] == 'final' for s in r['sources']) for r in dev if r['group'] == 'simple')
