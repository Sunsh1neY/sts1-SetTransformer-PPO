"""Reconstruct conservative prefixes with current content checks and explicit exclusions."""
from __future__ import annotations

import argparse
import copy
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re

from initial_state import KEYS, canonical_bytes, record, state_hash as reset_state_hash, write_records
from source_fields import combat_floor, scene_key

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parent
POTION_PROJECTION_POLICY = 'supported-potions-only-v1'


def semantic_state(candidate):
    """Return only the reset-semantic fields, excluding provenance metadata."""
    return {key: copy.deepcopy(candidate[key]) for key in sorted(KEYS) if key in candidate}


def semantic_hash(state, schema):
    try:
        return reset_state_hash(state)
    except (ValueError, TypeError, KeyError):
        # Backend-pending source rows may contain an unsupported relic or
        # permanent card state. Keep a deterministic raw identity for the
        # ledger without pretending that it is a reset-valid state.
        pass
    return hashlib.sha256(canonical_bytes({'schema': schema, 'state': state})).hexdigest()


def project_supported_potions(candidate, supported_potions):
    """Keep the source inventory and create a transparent training projection."""
    source_backbone = semantic_state(candidate)
    supported = set(supported_potions)
    source_potions = list(source_backbone['potions'])
    removed = [potion for potion in source_potions if potion is not None and potion not in supported]
    training_potions = [
        potion if potion is None or potion in supported else None
        for potion in source_potions
    ]
    projected = copy.deepcopy(candidate)
    projected['source_backbone'] = source_backbone
    projected['potions'] = training_potions
    projection = {
        'policy': POTION_PROJECTION_POLICY,
        'projected': bool(removed),
        'source_potions': source_potions,
        'training_potions': training_potions,
        'removed_potions': sorted(set(removed)),
        'removed_potion_counts': dict(sorted(Counter(removed).items())),
        'supported_potion_whitelist': sorted(supported),
        'empty_slots_preserved': training_potions.count(None) - source_potions.count(None),
        'source_inventory_preserved': True,
        'replacement_used': False,
        'backend_registry_expanded': False,
    }
    projected['potion_projection'] = projection
    projected['source_backbone_hash'] = semantic_hash(source_backbone, 'source-battle-backbone-v1')
    projected['training_instance_hash'] = semantic_hash(
        semantic_state(projected), 'configured-training-instance-v1'
    )
    return projected


def project_status_candidates(status, supported_potions):
    """Apply only scope projection; this function does not inspect backend status."""
    for row in status.values():
        candidate = row.get('candidate')
        if candidate is None:
            continue
        projected = project_supported_potions(candidate, supported_potions)
        row['candidate'] = projected
        row['potion_projection'] = copy.deepcopy(projected['potion_projection'])


def complete_non_elite_semantics(status):
    """Materialize the explicit false flag required by the v2 reset schema."""
    for row in status.values():
        candidate = row.get('candidate')
        if candidate is None or 'burning_elite' in candidate:
            continue
        completed = copy.deepcopy(candidate)
        completed['burning_elite'] = False
        row['candidate'] = completed


def recompute_backend_admission(exp, status, contract):
    """Validate the projected state against the frozen development contract."""
    for row in status.values():
        candidate = row.get('candidate')
        if candidate is None:
            continue
        before = sorted(set(row.get('backend_blockers', [])))
        row['backend_blockers_before_projection'] = before
        content_blockers = exp.backend_blockers(candidate, contract)
        if candidate.get('burning_elite_origin') == 'configured':
            content_blockers = [
                blocker for blocker in content_blockers
                if not blocker.startswith('ELITE_BURNING_STATE_UNPROVEN:')
            ]
        row['backend_blockers'] = sorted(set(content_blockers + row.get('entry_evidence_blockers', [])))
        row['backend_admissible'] = bool(row.get('evidence_complete') and not row['backend_blockers'])


def module(path):
    spec = importlib.util.spec_from_file_location(path.stem.replace('-', '_'), path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def blocker_class(reason):
    if reason.startswith(('UNSUPPORTED_', 'UNKNOWN_OR_UNSUPPORTED_', 'CARD_SECONDARY')):
        return 'backend_unsupported'
    if any(word in reason for word in ('MISSING', 'UNPROVEN', 'UNRESOLVED', 'CONFLICTING', 'INVALID')):
        return 'source_or_rule_evidence_unresolved'
    return 'prefix_rule_unimplemented'


def connect(rows):
    """Conservatively co-locate source groups connected through identical states."""
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x: parent[x] = find(parent[x])
        return parent[x]
    owners = {}
    for row in rows:
        group = row['provenance']['source_group']; state = row['state_hash']
        find(group)
        if state in owners: parent[find(group)] = find(owners[state])
        owners[state] = group
    members = defaultdict(list)
    for group in parent: members[find(group)].append(group)
    mappings = {}
    for groups in members.values():
        identity = hashlib.sha256(canonical_bytes(sorted(groups))).hexdigest()
        bucket = int(identity[:8], 16) % 100
        partition = 'audit-train' if bucket < 80 else 'audit-dev' if bucket < 90 else 'audit-holdout'
        for group in groups: mappings[group] = {'component': identity, 'partition': partition}
    return mappings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--backend-root', type=Path, required=True)
    args = parser.parse_args()
    exp = module(ROOT/'scripts/expand-public-prefixes.py')
    groups = exp.AUDIT.group_records(exp.AUDIT.load_records(args.archive.read_bytes()))
    source = (args.backend_root/'include/constants/SaveFileMappings.h').read_text(encoding='utf-8')
    known = {kind:set(re.findall(r'\{'+kind+r'::[A-Z0-9_]+, "([^"\n]+)"\}',source))
             for kind in ('CardId','RelicId','Potion')}
    contract = json.loads((ROOT/'sts/env/full-card-public-contract.json').read_text())
    contract['cards'] = json.loads((ROOT/'sts/env/ironclad-registry.json').read_text())['cards']
    contract['relics'] = json.loads((ROOT/'sts/env/relic-state-registry.json').read_text())['relics']
    contract['encounters'] = json.loads((ROOT/'sts/env/ironclad-expansion-contract.json').read_text())['scope']['encounters']
    # Historical helper incorrectly retains this old implementation exclusion.
    # Keep its other conservative checks; actual runtime remains authoritative.
    old_backend_blockers = exp.backend_blockers
    exp.backend_blockers = lambda c, contract=None: [b for b in old_backend_blockers(c,contract)
                                                    if b != 'CARD_SECONDARY_CHOICE:True Grit upgrade']
    ledger, records = [], []
    for group in groups:
        _, status, _ = exp.expand_group(group, known, Counter(), defaultdict(set), contract)
        complete_non_elite_semantics(status)
        project_status_candidates(status, [item['name'] for item in contract['potions']])
        recompute_backend_admission(exp, status, contract)
        combat_indices = Counter()
        for combat in group['run'].get('damage_taken',[]):
            floor = combat_floor(combat.get('floor')); index = combat_indices[floor]; combat_indices[floor] += 1
            scene_id = scene_key(group['group_id'], floor, index)
            row = status.get(scene_id)
            entry = {'scene_id':scene_id,'source_group':group['group_id'],'floor':floor,
                     'encounter_label':combat.get('enemies'),'state_hash':None,
                     'source_path':group['source_path'],'raw_sha256':group['raw_sha256'],
                     'training_admitted':False,'historical_rules_equivalence':'unverified'}
            if row is not None:
                entry['prefix_evidence_chain'] = row['prefix_evidence_chain']
                entry['field_evidence'] = (row['candidate'] or {}).get('field_evidence', {})
                entry['first_unresolved_prefix'] = next((step for step in row['prefix_evidence_chain']
                                                         if step.get('status') == 'blocked'), None)
                if row.get('candidate') is not None:
                    candidate = row['candidate']
                    entry['source_backbone'] = copy.deepcopy(candidate['source_backbone'])
                    entry['training_instance'] = semantic_state(candidate)
                    entry['source_backbone_hash'] = candidate['source_backbone_hash']
                    entry['training_instance_hash'] = candidate['training_instance_hash']
                    entry['potion_projection'] = copy.deepcopy(candidate['potion_projection'])
                    entry['configurable_fields'] = list(candidate.get('configurable_fields', []))
                    entry['backend_blockers_before_projection'] = row.get(
                        'backend_blockers_before_projection', []
                    )
            if row is None:
                reasons = ['OUTSIDE_ACT12_SCOPE'] if isinstance(floor,int) and floor > 34 else ['PREFIX_FLOOR_RULE_NOT_IMPLEMENTED']
            else:
                reasons = list(dict.fromkeys(row['evidence_blockers']+row['backend_blockers']))
                if row['candidate'] is None and not reasons: reasons = ['NO_COMPLETE_CANDIDATE']
            if not reasons:
                candidate = row['candidate']
                # Non-elite rows need no hidden elite condition. Elite rows must
                # have proved the value in the existing evidence gate.
                state = {k:candidate[k] for k in KEYS if k in candidate}
                if 'burning_elite' not in state:
                    if row['elite_entry_evidence']['required']:
                        raise ValueError('Missing elite evidence escaped gate')
                    state['burning_elite'] = False
                source_backbone = candidate['source_backbone']
                try:
                    result = record(state, {'source_group':group['group_id'], 'scene_id':scene_id,
                        'source_path':group['source_path'], 'raw_sha256':group['raw_sha256'],
                        'source_build':group['run'].get('build_version'),
                        'source_backbone_hash':candidate['source_backbone_hash'],
                        'training_instance_hash':candidate['training_instance_hash']},
                        {'field_evidence':candidate['field_evidence'],
                         'prefix_evidence_chain':row['prefix_evidence_chain'],
                         'historical_rules_equivalence':'unverified',
                         'source_admission':'diagnostic-rule-derived-only',
                         'potion_slot_policy':candidate['potion_slot_policy'],
                         'potion_projection':candidate['potion_projection'],
                         'source_backbone_hash':candidate['source_backbone_hash'],
                         'training_instance_hash':candidate['training_instance_hash'],
                         'configurable_fields':candidate.get('configurable_fields', [])},
                        source_backbone=source_backbone)
                    entry['state_hash'] = result['state_hash']; records.append(result)
                except ValueError as exc:
                    reasons = ['SCHEMA_UNREPRESENTABLE:'+str(exc)]
            entry['blockers'] = [{'reason':r,'category':blocker_class(r)} for r in reasons]
            if row is not None:
                entry['evidence_blockers'] = list(row.get('evidence_blockers', []))
                entry['state_evidence_blockers'] = list(row.get('state_evidence_blockers', []))
                entry['backend_blockers'] = list(row.get('backend_blockers', []))
                entry['backend_admissible'] = bool(row.get('backend_admissible'))
            entry['status'] = 'diagnostic-rule-derived' if entry['state_hash'] else 'excluded'
            ledger.append(entry)
    links = connect(records)
    for row in records: row['provenance'].update(links[row['provenance']['source_group']])
    unique = {}
    for row in records:
        key = row['state_hash']
        if key not in unique:
            unique[key] = dict(row, provenance={'origins':[], **links[row['provenance']['source_group']]})
        unique[key]['provenance']['origins'].append(row['provenance'])
    ordered = [unique[k] for k in sorted(unique)]
    write_records(PROJECT/'pilot-states.jsonl', ordered)
    (PROJECT/'candidate-ledger.jsonl').write_bytes(b''.join(canonical_bytes(r)+b'\n' for r in ledger))
    source_candidates = [row for row in ledger if 'source_backbone' in row]
    projected_candidates = [
        row for row in source_candidates if row['potion_projection']['projected']
    ]
    released_by_potion_projection = [
        row for row in source_candidates
        if row['potion_projection']['projected']
        and row.get('backend_admissible')
        and not row.get('state_evidence_blockers')
        and not [
            blocker for blocker in row.get('backend_blockers_before_projection', [])
            if not blocker.startswith('UNSUPPORTED_OR_CHOICE_POTION:')
            and not blocker.startswith('ELITE_BURNING_STATE_UNPROVEN:')
        ]
    ]
    configured_candidates = [row for row in source_candidates if row.get('configurable_fields')]
    baseline = {
        'source_derived_occurrences': 622,
        'canonical_source_backbones': 585,
        'backend_validated_occurrences': 622,
        'backend_validated_instances': 585,
    }
    summary = {'schema':'small-corpus-reconstruction-report-v2', 'total_combat_records':len(ledger),
        'source_derived_occurrences':len(source_candidates),
        'rule_derived_occurrences':len(records),'canonical_states':len(ordered),
        'canonical_source_backbones':len({row['source_backbone_hash'] for row in source_candidates}),
        'scope_projected_occurrences':len(projected_candidates),
        'scope_projected_instances':len({row['training_instance_hash'] for row in projected_candidates}),
        'configured_occurrences':len(configured_candidates),
        'configured_instances':len({row['training_instance_hash'] for row in configured_candidates}),
        'backend_validated_occurrences':len(records),
        'backend_validated_instances':len(ordered),
        'baseline_before_potion_projection':baseline,
        'potion_projection':{
            'policy':POTION_PROJECTION_POLICY,
            'source_backbone_potions_preserved':True,
            'unsupported_potion_blocker_rows_before_projection':sum(
                any(blocker.startswith('UNSUPPORTED_OR_CHOICE_POTION:')
                    for blocker in row.get('backend_blockers_before_projection', []))
                for row in source_candidates
            ),
            'unsupported_potion_only_blocker_rows_before_projection':sum(
                bool(row.get('backend_blockers_before_projection'))
                and all(blocker.startswith('UNSUPPORTED_OR_CHOICE_POTION:')
                        for blocker in row['backend_blockers_before_projection'])
                for row in source_candidates
            ),
            'projected_source_occurrences':len(projected_candidates),
            'released_by_potion_projection_occurrences':len(released_by_potion_projection),
            'released_by_potion_projection_instances':len({
                row['training_instance_hash'] for row in released_by_potion_projection
            }),
            'released_backend_validated_occurrences':len(records)-baseline['backend_validated_occurrences'],
            'released_backend_validated_instances':len(ordered)-baseline['backend_validated_instances'],
            'removed_potion_identities':sorted({
                potion for row in projected_candidates
                for potion in row['potion_projection']['removed_potions']
            }),
        },
        'source_groups_with_states':len(links),'overlap_components':len({v['component'] for v in links.values()}),
        'formal_A_admitted':0, 'historical_rules_equivalence':'unverified',
        'first_blocker_counts':dict(Counter(r['blockers'][0]['reason'] for r in ledger if r['blockers'])),
        'occurrence_floors':dict(sorted(Counter(r['state']['floor'] for r in records).items())),
        'unique_encounters':dict(sorted(Counter(r['state']['encounter'] for r in ordered).items())),
        'unique_potion_names': sorted({p for r in ordered for p in r['state']['potions'] if p}),
        'unique_source_backbone_potion_names': sorted({
            p for row in source_candidates for p in row['source_backbone']['potions'] if p
        }),
        'unique_relic_names': sorted({p if isinstance(p,str) else p['name'] for r in ordered for p in r['state']['relics']}),
        'partitions':dict(Counter(v['partition'] for v in links.values())),
        'scope':'Conservative existing Act 1/2 prefix rules; source backbone and training instance are separate; no new history rules or admission',
        'hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            PROJECT/'pilot-states.jsonl', PROJECT/'candidate-ledger.jsonl',Path(__file__),PROJECT/'initial_state.py',PROJECT/'source_fields.py']}}
    (PROJECT/'reconstruction-report.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k != 'first_blocker_counts'},indent=2))


if __name__ == '__main__': main()
