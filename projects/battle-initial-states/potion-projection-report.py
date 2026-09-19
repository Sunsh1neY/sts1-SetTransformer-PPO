"""Report source/projection/admission layers after potion scope projection."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
BASELINE = {
    'source_derived_occurrences': 622,
    'canonical_source_backbones': 585,
    'backend_validated_occurrences': 622,
    'backend_validated_instances': 585,
}


def load_jsonl(name: str) -> list[dict]:
    return [json.loads(line) for line in (PROJECT / name).read_bytes().splitlines()]


def reason(row: dict) -> str:
    blockers = row.get('blockers') or []
    if blockers:
        return str(blockers[0].get('reason', 'UNKNOWN_BLOCKER'))
    return 'NO_BLOCKER'


def category(row: dict) -> str:
    if row.get('backend_admissible'):
        return 'NONE'
    candidate = row.get('source_backbone_hash') is not None
    if not candidate:
        value = reason(row)
        if value.startswith(('PLAYER_ENTRY_UNPROVEN', 'ENTRY_ROOM_OR_MULTIPLE',
                             'PERSISTENT_CARD_VALUE_MISSING', 'EVENT_',
                             'PREVIOUS_FLOOR_METRIC', 'SOURCE_')):
            return 'SOURCE_REQUIRED'
        return 'RECONSTRUCTION_PENDING'
    values = [blocker.get('reason', '') for blocker in row.get('blockers', [])]
    if any(value.startswith(('UNSUPPORTED_CARD', 'UNSUPPORTED_RELIC',
                             'RELIC_ID_UNRESOLVED', 'UNKNOWN_OR_UNSUPPORTED_',
                             'UNKNOWN_OR_MISMATCHED_')) for value in values):
        return 'BACKEND_SCOPE_PENDING'
    if any(value.startswith('ELITE_BURNING_STATE_UNPROVEN') for value in values):
        return 'CONFIGURABLE'
    return 'RECONSTRUCTION_PENDING'


def main() -> None:
    ledger = load_jsonl('candidate-ledger.jsonl')
    states = load_jsonl('pilot-states.jsonl')
    runtime = json.loads((PROJECT / 'runtime-report.json').read_text(encoding='utf-8'))
    act12 = [row for row in ledger if isinstance(row.get('floor'), int) and 1 <= row['floor'] <= 34]
    source = [row for row in act12 if row.get('source_backbone_hash')]
    projected = [row for row in source if row['potion_projection']['projected']]
    configured = [row for row in source if row.get('configurable_fields')]
    released = [
        row for row in projected
        if row.get('backend_admissible') and not row.get('state_evidence_blockers')
        and not [
            blocker for blocker in row.get('backend_blockers_before_projection', [])
            if not blocker.startswith('UNSUPPORTED_OR_CHOICE_POTION:')
            and not blocker.startswith('ELITE_BURNING_STATE_UNPROVEN:')
        ]
    ]
    removed_counts = Counter(
        potion for row in projected for potion in row['potion_projection']['removed_potions']
    )
    removed_occurrences = Counter()
    for row in projected:
        removed_occurrences.update(row['potion_projection']['removed_potion_counts'])
    blocker_counts = Counter(category(row) for row in act12)
    remaining_reasons = Counter(
        reason(row) for row in act12 if row.get('blockers') and not row.get('backend_admissible')
    )
    state_acts = Counter(str(row['state']['act']) for row in states)
    source_acts = Counter('act1' if row['floor'] <= 17 else 'act2' for row in source)
    projected_acts = Counter('act1' if row['floor'] <= 17 else 'act2' for row in projected)
    released_acts = Counter('act1' if row['floor'] <= 17 else 'act2' for row in released)
    report = {
        'schema': 'supported-potion-projection-report-v1',
        'policy': 'supported-potions-only-v1',
        'scope': 'Act 1/2 source-derived rows in the pinned small corpus; formal training pool unchanged',
        'baseline_before_projection': BASELINE,
        'source_backbone_vs_training_instance': {
            'source_derived_occurrences': len(source),
            'canonical_source_backbones': len({row['source_backbone_hash'] for row in source}),
            'scope_projected_occurrences': len(projected),
            'scope_projected_instances': len({row['training_instance_hash'] for row in projected}),
            'configured_occurrences': len(configured),
            'configured_instances': len({row['training_instance_hash'] for row in configured}),
            'backend_validated_occurrences': sum(row.get('state_hash') is not None for row in act12),
            'backend_validated_instances': len(states),
        },
        'potion_blockers_before_projection': {
            'rows_with_unsupported_potion_blocker': sum(
                any(value.startswith('UNSUPPORTED_OR_CHOICE_POTION:')
                    for value in row.get('backend_blockers_before_projection', []))
                for row in source
            ),
            'rows_with_only_unsupported_potion_blocker': sum(
                bool(row.get('backend_blockers_before_projection'))
                and all(value.startswith('UNSUPPORTED_OR_CHOICE_POTION:')
                        for value in row['backend_blockers_before_projection'])
                for row in source
            ),
            'by_act': {
                'act1': sum(
                    any(value.startswith('UNSUPPORTED_OR_CHOICE_POTION:')
                        for value in row.get('backend_blockers_before_projection', []))
                    for row in source if row['floor'] <= 17
                ),
                'act2': sum(
                    any(value.startswith('UNSUPPORTED_OR_CHOICE_POTION:')
                        for value in row.get('backend_blockers_before_projection', []))
                    for row in source if row['floor'] >= 18
                ),
            },
        },
        'projection_effect': {
            'released_occurrences': len(released),
            'released_instances': len({row['training_instance_hash'] for row in released}),
            'released_by_act': dict(sorted(released_acts.items())),
            'removed_unsupported_potion_identities': sorted(removed_counts),
            'removed_potion_occurrences_by_identity': dict(sorted(removed_occurrences.items())),
            'source_potion_identity_occurrences': dict(sorted(removed_counts.items())),
            'replacement_used': False,
            'empty_capacity_preserved': True,
            'source_inventory_retained': True,
            'backend_registry_expanded': False,
        },
        'act_distribution': {
            'source_derived_occurrences': dict(sorted(source_acts.items())),
            'scope_projected_occurrences': dict(sorted(projected_acts.items())),
            'backend_validated_canonical_instances': dict(sorted(state_acts.items())),
        },
        'latest_layer_counts': {
            'SOURCE_REQUIRED': blocker_counts['SOURCE_REQUIRED'],
            'RECONSTRUCTION_PENDING': blocker_counts['RECONSTRUCTION_PENDING'],
            'BACKEND_SCOPE_PENDING': blocker_counts['BACKEND_SCOPE_PENDING'],
            'SCOPE_PROJECTABLE': len(projected),
            'CONFIGURABLE': len(configured),
            'BACKEND_RANDOM': 0,
            'NONE_BACKEND_VALIDATED': blocker_counts['NONE'],
        },
        'remaining_first_blocker_reasons': dict(remaining_reasons.most_common()),
        'runtime_validation': runtime['counts'],
        'training_pool_changed': False,
        'training_admitted': False,
    }
    (PROJECT / 'potion-projection-report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
