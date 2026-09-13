"""数据预检必须传播来源关联，不得把开发关联样本重新分到训练侧。"""
from pathlib import Path
import runpy

AUDIT = runpy.run_path(str(Path(__file__).parents[1] / 'scripts/audit-a-path-data.py'))


def row(identifier, group, content, split='train', tokens=()):
    return dict(id=identifier, group_id=group, content_hash=content, old_split=split,
                identity_tokens=list(tokens), origin='fixture', cards=[content])


def test_transitive_run_seed_and_duplicate_content_propagate_development():
    rows = [row('a', 'run1', 'deck1', 'development'), row('b', 'run1', 'deck2'),
            row('c', 'run2', 'deck2', tokens=['seed:42']),
            row('d', 'run3', 'deck3', tokens=['seed:42']), row('e', 'run4', 'deck4')]
    result = AUDIT['summarize'](rows)
    assert result['totals']['development_anchor']['rows'] == 4
    assert result['totals']['train_eligible_pending_admission']['rows'] == 1
    assert result == AUDIT['summarize'](list(reversed(rows)))


def test_current_audit_does_not_claim_registry_candidates_are_formal_admission():
    report = AUDIT['audit']()
    assert report['formal_admission'] is False
    assert report['final_registry_eligible_count'] + report['final_registry_rejected_count'] == 157
    assert any('PERMANENT_CARD_VALUE_UNRECORDED:RitualDagger' in r['blockers'] for r in report['final_rejected'])
    for name in ('old_batch', 'with_final_candidates'):
        partitions = report[name]['components']
        train = {x for g in partitions if g['disposition'].startswith('train') for x in g['row_ids']}
        dev = {x for g in partitions if g['disposition'] == 'development_anchor' for x in g['row_ids']}
        assert not train & dev
