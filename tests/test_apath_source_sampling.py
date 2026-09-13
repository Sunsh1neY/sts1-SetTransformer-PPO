"""来源均匀开局提案的概率质量、去重与状态计数验收。"""
from fractions import Fraction
from pathlib import Path
import runpy

MODULE = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/audit-a-path-source-sampling.py'))


def row(source, deck, group='simple'):
    return {'component_id': source, 'content_id': deck, 'group': group}


def test_more_records_and_states_cannot_increase_source_probability():
    rows = [row('a', 'd1'), row('b', 'd2'), row('b', 'd3'), row('b', 'd4')]
    _, weights = MODULE['weights_by_source'](rows)
    assert sum(w['probability'] for w in weights if w['component_id'] == 'a') == Fraction(1, 2)
    assert sum(w['probability'] for w in weights if w['component_id'] == 'b') == Fraction(1, 2)
    assert [w['probability'] for w in weights if w['component_id'] == 'b'] == [Fraction(1, 6)] * 3
    _, repeated = MODULE['weights_by_source'](rows + [row('b', 'd2')]*20)
    assert repeated == weights


def test_structure_labels_do_not_change_formal_probabilities():
    rows = [row('a', 'd1'), row('b', 'd2')]
    _, a = MODULE['weights_by_source'](rows)
    _, b = MODULE['weights_by_source']([{**r, 'group': 'combo'} for r in reversed(rows)])
    assert [(r['content_id'], r['probability']) for r in a] == [(r['content_id'], r['probability']) for r in b]


def test_current_candidates_exact_probability_and_initial_config_mass():
    report = MODULE['audit']()
    assert report['independent_source_groups'] == 33
    assert report['original_runs'] == 36
    assert report['unique_decks'] == 39
    assert report['unique_initial_configurations'] == 390
    assert report['runtime_admitted_initial_state_count'] is None
    assert not report['formal_training_started'] and not report['training_pool_frozen']
    assert {r['group']: Fraction(r['initial_probability_exact']) for r in report['group_summary']} == {
        'simple': Fraction(13, 66), 'transition': Fraction(7, 33), 'compositional': Fraction(13, 22)}
    assert sum(Fraction(r['probability_exact']) for r in report['initial_configurations']) == 1
    assert {Fraction(r['probability_exact']) for r in report['source_group_opportunities']} == {Fraction(1, 33)}
