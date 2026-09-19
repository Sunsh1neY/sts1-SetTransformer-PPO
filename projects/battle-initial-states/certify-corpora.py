"""Check lineage, frozen bytes and runtime evidence; seal diagnostic A-v2."""
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path

from initial_state import read_records

PROJECT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('versions', PROJECT/'version-corpora.py')
versions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(versions)


def audit():
    v1, v2 = (PROJECT/'corpora'/v for v in ('a-v1','a-v2'))
    versions.verify(v1)
    manifest = versions.verify(v2)
    assert versions.sha(v1/'manifest.json') == manifest['parent_manifest_sha256']
    old = {r['state_hash']: r for r in read_records(v1/'states.jsonl')}
    new = {r['state_hash']: r for r in read_records(v2/'states.jsonl')}
    delta = {r['state_hash']: r for r in read_records(v2/'additions.jsonl')}
    lineage = [json.loads(line) for line in (v2/'lineage.jsonl').read_bytes().splitlines()]
    assert len(new) == len(old)+len(delta) == manifest['state_count']
    assert set(new) == set(old) | set(delta)
    assert not set(old) & set(delta)
    assert all(new[k] == r for k,r in old.items())
    assert all(new[k] == r for k,r in delta.items())
    assert {x['state_hash'] for x in lineage} == set(delta)
    for item in lineage:
        child, parent = delta[item['state_hash']], old[item['parent_state_hash']]
        assert child['source_backbone'] == parent['source_backbone']
        for field in ('component','partition','origins'):
            assert child['provenance'][field] == parent['provenance'][field]
        changed = {k for k in child['state'] if child['state'][k] != parent['state'][k]}
        allowed = {'act2-low-hp': {'player'}, 'entry-counter': {'relics'}, 'rare-combination': {'deck','relics'}}[item['category']]
        assert changed <= allowed
        if item['category'] == 'act2-low-hp':
            assert child['state']['act'] == 2
            assert child['state']['player']['hp']/child['state']['player']['max_hp'] <= .25
            assert all(child['state']['player'][k] == parent['state']['player'][k] for k in ('max_hp','gold'))
        if item['category'] == 'rare-combination':
            assert Counter(parent['state']['deck']) + Counter(item['parameters']['added_cards']) == Counter(child['state']['deck'])
        assert child['training_admitted'] is False
    partitions = defaultdict(set)
    for row in new.values():
        partitions[row['provenance']['component']].add(row['provenance']['partition'])
    assert all(len(v)==1 for v in partitions.values())
    runtime = json.loads((v2/'validation/runtime-report.json').read_text())
    assert runtime['hashes']['additions.jsonl'] == versions.sha(v2/'additions.jsonl')
    assert not runtime['failures']
    assert {r['state_hash'] for r in runtime['initial_state_checks']} == set(delta)
    assert runtime['optimizer_updates'] == 0 and runtime['training_admitted'] is False
    def profile(rows):
        rs = list(rows)
        return {
            'states':len(rs), 'act2':sum(r['state']['act']==2 for r in rs),
            'act2_low_hp':sum(r['state']['act']==2 and r['state']['player']['hp']/r['state']['player']['max_hp']<=.25 for r in rs),
            'partitions':dict(Counter(r['provenance']['partition'] for r in rs)),
            'counter_values':{n:sorted({rel['counter'] for r in rs for rel in r['state']['relics'] if isinstance(rel,dict) and rel['name']==n}) for n in versions.COUNTERS},
            'combo_support':{label:{part:{'states':len(subset := [r for r in rs if r['provenance']['partition']==part and set(cards)<={c.split('+')[0] for c in r['state']['deck']}]),
                                           'components':len({r['provenance']['component'] for r in subset})}
                                    for part in ('audit-train','audit-dev','audit-holdout')} for label,cards in versions.COMBOS.items()},
        }
    result = {'baseline': profile(old.values()), 'augmented':profile(new.values()),
              'lineage_checks':'passed', 'baseline_unchanged':True, 'cross_partition_components':0,
              'runtime_new_states':runtime['counts'], 'training_admitted':False,
              'interpretation':'Synthetic variants add conditional coverage, not independent historical sources or SAB generalization evidence.'}
    report_path = v2/'validation/coverage-and-integrity.json'
    if manifest['status'] == 'frozen-diagnostic':
        assert json.loads(report_path.read_text()) == result
        print('Frozen A-v1/A-v2 verification passed')
        return result
    versions.save(report_path,result)
    manifest['status'] = 'frozen-diagnostic'
    manifest['runtime_evidence'] = {'baseline':'../a-v1/runtime-report.json', 'delta':'validation/runtime-report.json',
                                    'scope':'All delta states reset/forward/step; representative full episodes only.'}
    for file in ('validation/coverage-and-integrity.json','validation/runtime-report.json','validation/runtime-manifest.json'):
        manifest['files'][file] = {'sha256': versions.sha(v2/file)}
    versions.save(v2/'manifest.json',manifest)
    versions.verify(v2)
    print(json.dumps(result,indent=2))
    return result


if __name__ == '__main__':
    audit()
