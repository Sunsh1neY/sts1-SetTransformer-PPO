"""Promote reconstructed states that passed the current runtime chain to A corpus.

This is a project corpus artifact only. It does not edit the frozen formal
training pool or launch PPO.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import copy
from pathlib import Path

PROJECT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backbone_id(state: dict) -> str:
    """Collapse only configured dynamic fields; preserve the real backbone."""
    value = copy.deepcopy(state)
    value['burning_elite'] = 'CONFIGURABLE'
    relics = []
    for relic in value['relics']:
        if isinstance(relic, dict) and 'card_index' in relic:
            relics.append({'name': relic['name'], 'card_index': 'CONFIGURABLE'})
        elif isinstance(relic, dict) and 'counter' in relic:
            relics.append({'name': relic['name'], 'counter': 'CONFIGURABLE'})
        else:
            relics.append(relic)
    value['relics'] = relics
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=PROJECT / 'admitted-a-corpus.jsonl')
    args = parser.parse_args()
    states = [json.loads(line) for line in (PROJECT / 'pilot-states.jsonl').read_bytes().splitlines()]
    ledger = [json.loads(line) for line in (PROJECT / 'candidate-ledger.jsonl').read_bytes().splitlines()]
    runtime = json.loads((PROJECT / 'runtime-report.json').read_text(encoding='utf-8'))
    reconstruction = json.loads((PROJECT / 'reconstruction-report.json').read_text(encoding='utf-8'))
    checked = {row['state_hash'] for row in runtime['initial_state_checks']}
    failed = set(runtime['failures'][i]['state_hash'] for i in range(len(runtime['failures'])))
    if failed or len(checked) != len(states):
        raise ValueError(f'Runtime validation is incomplete: states={len(states)} checked={len(checked)} failures={len(failed)}')
    rollout_hashes = {row['state_hash'] for row in runtime['episodes']}
    rows = []
    def source_group(provenance):
        return provenance.get('source_group') or (provenance.get('origins') or [{}])[0].get('source_group')
    for row in states:
        if row['state_hash'] not in checked:
            raise ValueError('State missing runtime evidence: ' + row['state_hash'])
        provenance = dict(row['provenance'])
        group = source_group(provenance)
        if not group:
            raise ValueError('Missing connected source group for ' + row['state_hash'])
        provenance['source_group'] = group
        provenance['source_certification'] = 'unverified'
        provenance['confidence'] = 'backend-validated-reconstruction; historical ruleset provenance unverified'
        bid = row['source_backbone_hash']
        rows.append({
            'schema': 'battle-initial-state-v1',
            'state': row['state'],
            'state_hash': row['state_hash'],
            'backbone_id': bid,
            'source_backbone': row['source_backbone'],
            'source_backbone_hash': row['source_backbone_hash'],
            'training_instance_hash': row['evidence']['training_instance_hash'],
            'potion_projection': row['evidence']['potion_projection'],
            'provenance': provenance,
            'reconstruction': dict(row['evidence'],
                                   status='reconstructed',
                                   exact_historical_replay=False,
                                   source_certification='unverified'),
            'admission': {
                'status': 'backend-validated',
                'formal_a_corpus': True,
                'training_pool_admitted': False,
                'schema_validation': True,
                'backend_reset': True,
                'public_observation': True,
                'token_encoding': True,
                'model_forward': True,
                'legal_action_validation': True,
                'representative_complete_rollout': row['state_hash'] in rollout_hashes,
                'potion_projection': row['evidence']['potion_projection'],
                'runtime_report_sha256': digest(PROJECT / 'runtime-report.json'),
            },
        })
    args.output.write_bytes(b''.join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8') + b'\n' for row in rows))
    result = {
        'schema': 'backend-validated-a-corpus-v1',
        'admission_standard': 'backend-validated',
        'source_certified_required': False,
        'state_count': len(rows),
        'source_derived_occurrences': sum('source_backbone' in r for r in ledger),
        'source_derived_canonical_source_backbone_count': reconstruction['canonical_source_backbones'],
        'scope_projected_occurrence_count': reconstruction['scope_projected_occurrences'],
        'canonical_source_backbone_count': len({r['source_backbone_hash'] for r in rows}),
        'source_backbone_count': len({r['backbone_id'] for r in rows}),
        'scope_projected_instance_count': len({
            r['training_instance_hash'] for r in rows
            if r['potion_projection']['projected']
        }),
        'configured_instance_count': len({
            r['source_backbone_hash'] for r in rows
            if r['reconstruction'].get('configurable_fields')
        }),
        'source_group_count': len({source_group(r['provenance']) for r in rows}),
        'representative_rollout_state_count': len(rollout_hashes),
        'training_pool_admitted': False,
        'artifact_sha256': digest(args.output),
        'runtime_report_sha256': digest(PROJECT / 'runtime-report.json'),
        'provenance_levels': dict(Counter(r['provenance']['source_certification'] for r in rows)),
    }
    (PROJECT / 'a-corpus-admission.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
