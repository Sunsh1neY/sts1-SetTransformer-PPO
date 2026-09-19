"""Freeze A-v1 and build a bounded, deterministic diagnostic A-v2 delta."""
import argparse
import copy
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from initial_state import canonical_bytes, record, read_records, write_records, state_hash

PROJECT = Path(__file__).resolve().parent
ROOT = PROJECT.parents[1]
CORPORA = PROJECT / 'corpora'
COUNTERS = ('Pen Nib', 'Nunchaku', 'Happy Flower', 'Incense Burner', 'Ink Bottle', 'Sundial')
COMBOS = {
    'block-retention': ('Barricade', 'Body Slam', 'Entrench'),
    'self-damage': ('Rupture', 'Hemokinesis'),
    'strength-payoff': ('Inflame', 'Heavy Blade', 'Limit Break'),
    'dropkick': ('Dropkick', 'Thunderclap'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_bytes(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2).encode('utf-8') + b'\n')


def freeze():
    target = CORPORA / 'a-v1'
    if target.exists():
        verify(target)
        return
    source = read_records(PROJECT / 'pilot-states.jsonl')
    if len(source) != 1377:
        raise ValueError('A-v1 requires the reviewed 1377-state snapshot')
    files = {'states.jsonl': 'pilot-states.jsonl',
             'legacy-admitted-a-corpus.jsonl': 'admitted-a-corpus.jsonl',
             'runtime-report.json': 'runtime-report.json', 'runtime-manifest.json': 'runtime-manifest.json',
             'coverage.json': 'a-corpus-coverage.json', 'coverage.md': 'a-corpus-coverage.md',
             'source-inventory.json': 'source-inventory.json', 'admission.json': 'a-corpus-admission.json',
             'initial_state.py': 'initial_state.py', 'validate-runtime.py': 'validate-runtime.py',
             'analyze-a-coverage.py': 'analyze-a-coverage.py'}
    target.mkdir(parents=True)
    for dest, src in files.items():
        (target / dest).write_bytes((PROJECT / src).read_bytes())
    save(target/'manifest.json', {
        'corpus_version': 'a-v1', 'status': 'frozen', 'canonical_state_schema': 'battle-initial-state-v2',
        'state_count': len(source), 'training_admitted': False,
        'legacy_wrapper_note': 'Original v1-labeled wrapper retained verbatim as historical evidence; consume states.jsonl with v2 schema.',
        'files': {dest: {'sha256': sha(target/dest), 'source': src} for dest, src in files.items()},
    })
    verify(target)


def verify(target):
    manifest = json.loads((target/'manifest.json').read_text(encoding='utf-8'))
    for file, evidence in manifest['files'].items():
        if sha(target/file) != evidence['sha256']:
            raise ValueError('Frozen artifact changed: '+str(target/file))
    return manifest


def build():
    baseline = CORPORA/'a-v1'
    verify(baseline)
    target = CORPORA/'a-v2'
    if target.exists():
        raise ValueError('A-v2 already exists; refusing to overwrite versioned data')
    parents = read_records(baseline/'states.jsonl')
    parents.sort(key=lambda r: r['state_hash'])
    registry = {r['name']: r for r in json.loads((ROOT/'sts/env/relic-state-registry.json').read_text())['relics']}
    additions, lineage, skipped = [], [], Counter()
    seen = {r['state_hash'] for r in parents}

    def add(parent, scene, category, parameters):
        h = state_hash(scene)
        if h in seen:
            skipped[category] += 1
            return
        provenance = copy.deepcopy(parent['provenance'])
        provenance['augmentation'] = {'parent_state_hash': parent['state_hash'],
                                    'parent_corpus': 'a-v1', 'synthetic': True}
        evidence = copy.deepcopy(parent['evidence'])
        evidence['augmentation'] = {'category': category, 'parameters': parameters,
                                    'historical_replay': False, 'parent_state_hash': parent['state_hash']}
        evidence['training_instance_hash'] = h
        child = record(scene, provenance, evidence, source_backbone=parent['source_backbone'])
        changed = [k for k in scene if scene[k] != parent['state'][k]]
        lineage.append({'state_hash': h, 'parent_state_hash': parent['state_hash'], 'category': category,
                        'parameters': parameters, 'changed_fields': changed,
                        'partition': provenance['partition'], 'component': provenance['component']})
        seen.add(h)
        additions.append(child)

    # One parent per connected component among Act 2 entries; two exact HP bands.
    selected_components = set()
    for parent in parents:
        if parent['state']['act'] != 2 or parent['provenance']['component'] in selected_components:
            continue
        selected_components.add(parent['provenance']['component'])
        for percent in (10, 25):
            scene = copy.deepcopy(parent['state'])
            scene['player']['hp'] = max(1, scene['player']['max_hp']*percent//100)
            add(parent, scene, 'act2-low-hp', {'hp_percent_floor': percent})

    # Enumerate the six audited independent periodic counters; no unknown coupling.
    for relic in COUNTERS:
        rule = registry[relic]['counter']
        assert rule['scope'] == 'across_combats'
        for part in ('audit-train', 'audit-dev', 'audit-holdout'):
            chosen = []
            components = set()
            for parent in parents:
                if parent['provenance']['partition'] != part:
                    continue
                if not any(isinstance(r, dict) and r['name'] == relic for r in parent['state']['relics']):
                    continue
                component = parent['provenance']['component']
                if component not in components:
                    chosen.append(parent)
                    components.add(component)
                if len(chosen) == 2:
                    break
            for parent in chosen:
                for value in range(rule['min'], rule['max']+1):
                    scene = copy.deepcopy(parent['state'])
                    next(r for r in scene['relics'] if isinstance(r,dict) and r['name']==relic)['counter'] = value
                    add(parent, scene, 'entry-counter', {'relic': relic, 'counter': value})

    # Controlled card additions, preserving every existing card/relic and binding.
    # Select Act 2 parent components only; never synthesize historical provenance.
    for label, cards in COMBOS.items():
        for part in ('audit-train', 'audit-dev', 'audit-holdout'):
            components = set()
            for parent in parents:
                if parent['state']['act'] != 2 or parent['provenance']['partition'] != part:
                    continue
                if parent['provenance']['component'] in components:
                    continue
                scene = copy.deepcopy(parent['state'])
                present = {c.split('+')[0] for c in scene['deck']}
                added = [c for c in cards if c not in present]
                if not added:
                    continue
                scene['deck'].extend(added)
                add(parent, scene, 'rare-combination', {'probe': label, 'added_cards': added})
                components.add(parent['provenance']['component'])
                if len(components) == 3:
                    break

    target.mkdir(parents=True)
    write_records(target/'additions.jsonl', additions)
    write_records(target/'states.jsonl', sorted(parents+additions, key=lambda r:r['state_hash']))
    (target/'lineage.jsonl').write_bytes(b''.join(canonical_bytes(r)+b'\n' for r in lineage))
    save(target/'generation-policy.json', {
        'policy': 'bounded-coverage-augmentation-v1', 'randomness': 'none; sorted hashes and explicit strata',
        'low_hp': 'Act 2, one parent per connected component, floor(max_hp*0.10) and floor(max_hp*0.25), minimum 1',
        'counter': 'Enumerate legal values of six registered independent periodic counters, at most two parent components per partition and identity; retain zero baseline, deduplicate unchanged states.',
        'counter_identities': COUNTERS, 'rare_combinations': COMBOS,
        'rare_parent_rule': 'At most three distinct Act 2 parent components per partition and combination; append only missing base identities at upgrade zero.',
        'split_rule': 'Inherit parent partition and connected component; augmentation is not an independent source.',
        'distribution_note': 'No sampler weights are assigned. Uniform sampling of combined states changes family/source exposure.',
        'deferred': ['burning elites', 'SAB generalization corpus', 'formal training admission'],
    })
    save(target/'manifest.json', {
        'corpus_version': 'a-v2', 'status': 'generated-pending-runtime', 'canonical_state_schema': 'battle-initial-state-v2',
        'parent_version': 'a-v1', 'parent_manifest_sha256': sha(baseline/'manifest.json'),
        'baseline_states': len(parents), 'additional_states': len(additions), 'state_count': len(parents)+len(additions),
        'categories': dict(Counter(r['category'] for r in lineage)), 'duplicates_skipped': dict(skipped),
        'training_admitted': False, 'generator_sha256': sha(Path(__file__)),
        'files': {p: {'sha256': sha(target/p)} for p in ('states.jsonl','additions.jsonl','lineage.jsonl','generation-policy.json')},
    })
    verify(target)
    print((target/'manifest.json').read_text())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('freeze', 'build', 'verify'))
    args = parser.parse_args()
    if args.command == 'freeze': freeze()
    elif args.command == 'build': build()
    else:
        for version in ('a-v1', 'a-v2'):
            print(version, verify(CORPORA/version)['state_count'])
