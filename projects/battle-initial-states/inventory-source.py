"""Inventory the pinned small corpus without reconstruction or environment reset."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path):
    spec = importlib.util.spec_from_file_location("pinned_corpus_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_inventory(archive, backend_root):
    audit = load_module(ROOT / "scripts/audit-public-corpus.py")
    records = audit.load_records(archive.read_bytes())  # Verifies the pinned ZIP hash.
    groups = audit.group_records(records)
    membership = {alias: group['group_id'] for group in groups for alias in group['aliases']}
    fields = sorted(set().union(*(g['run'].keys() for g in groups)))
    field_counts = {}
    for field in fields:
        types = Counter(type(g['run'][field]).__name__ for g in groups if field in g['run'])
        field_counts[field] = {
            'present_groups': sum(field in g['run'] for g in groups),
            'null_groups': sum(field in g['run'] and g['run'][field] is None for g in groups),
            'empty_list_groups': sum(g['run'].get(field) == [] for g in groups),
            'value_types': dict(sorted(types.items())),
        }
    source_groups = []
    for group in groups:
        run = group['run']
        source_groups.append({
            'source_group': group['group_id'], 'aliases': group['aliases'],
            'representative': group['source_path'], 'raw_sha256': group['raw_sha256'],
            'conflicting_variants': group['conflicting_variants'],
            'source_build': run.get('build_version'), 'ascension': run.get('ascension_level'),
            'card_modifier_evidence': audit.card_modifier_evidence(run),
            'combat_records': [{'floor': row.get('floor'), 'encounter_label': row.get('enemies')}
                               for row in run.get('damage_taken', [])],
            'available_fields': sorted(run),
        })
    hashes = {}
    for relative in (
        'scripts/audit-public-corpus.py', 'scripts/expand-public-prefixes.py',
        'sts/env/relic-state-registry.json', 'sts/env/ironclad-expansion-contract.json',
        'sts/env/ironclad-registry.json', 'sts/env/full-card-public-contract.json',
        'sts/env/a-path-training-pool.json', 'eval_seeds.json',
        'sts/env/relics.py', 'sts/env/apath.py', 'sts/models/apath.py',
        'sts/env/relic_card_state.py', 'sts/env/relic_state.py',
        'sts/battle_reward_v2.py', 'patches/lightspeed-relic-state.patch',
        'projects/battle-initial-states/inventory-source.py',
    ):
        path = ROOT / relative
        hashes[relative] = digest(path)
    binaries = sorted((backend_root / 'build').glob('slaythespire*.pyd'))
    if len(binaries) != 1:
        raise ValueError('Expected exactly one explicit backend binary')
    evidence = json.loads((ROOT / 'docs/evidence/main-integration-2026-09-19.json').read_text())
    return {
        'schema': 'initial-state-source-inventory-v1',
        'scope': 'source inventory only; field presence is not historical state recoverability',
        'repository_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source': {'commit': audit.COMMIT, 'path': str(archive.resolve()),
                   'sha256': digest(archive), 'bytes': archive.stat().st_size},
        'implementation_hashes': hashes,
        'backend': {'path': str(binaries[0].resolve()), 'sha256': digest(binaries[0]),
                    'reset_source_sha256': digest(backend_root / 'bindings/integrated-card-env.cpp')},
        'prior_integration_evidence': {'path': 'docs/evidence/main-integration-2026-09-19.json',
                                      'sha256': digest(ROOT / 'docs/evidence/main-integration-2026-09-19.json'),
                                      'recorded_schema': evidence.get('schema'), 'rerun': False},
        'counts': {'ironclad_files': len(records), 'connected_source_groups': len(groups),
                   'duplicate_files': len(records)-len(groups),
                   'conflicting_groups': sum(g['conflicting_variants'] for g in groups),
                   'combat_records': sum(len(g['combat_records']) for g in source_groups),
                   'ascension_groups': dict(sorted(Counter(str(g['ascension']) for g in source_groups).items()))},
        'field_presence': field_counts,
        'files': [{'path': r['source_path'], 'sha256': r['raw_sha256'],
                   'source_group': membership[r['source_path']]} for r in records],
        'groups': source_groups,
        'training_admitted': False, 'canonical_schema_decision': 'owner-approved-v2',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--backend-root', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=PROJECT / 'source-inventory.json')
    args = parser.parse_args()
    result = build_inventory(args.archive, args.backend_root)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result['counts'], indent=2))


if __name__ == '__main__':
    main()
