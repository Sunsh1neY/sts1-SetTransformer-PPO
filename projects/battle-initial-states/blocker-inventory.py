"""Build an Act 1/2 first-blocker and repair-priority inventory."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re

PROJECT = Path(__file__).resolve().parent


def category(reason: str) -> str:
    # The four categories describe what is missing from the source-derived
    # backbone, rather than whether an old parser happened to support it.
    if reason.startswith(('POTION_AUTO_USE_OR_GENERATION', 'POTION_WITHIN_FLOOR_ORDER')):
        return 'BACKEND_RANDOM'
    if reason.startswith(('UNSUPPORTED_CARD', 'UNSUPPORTED_OR_CHOICE_POTION', 'RELIC_ID_UNRESOLVED', 'SHOP_', 'EVENT_OUTCOME_NOT_ALLOWLISTED', 'EVENT_CARD_REWARD', 'CAMPFIRE_ACTION_PENDING', 'ROOM_HISTORY_PENDING', 'UNREGISTERED_SINGING_BOWL', 'NEOW_EFFECT_PENDING')):
        return 'DERIVABLE'
    if reason.startswith(('EVENT_POTION_ID_MISSING', 'EVENT_RANDOM_RELIC_ID_MISSING', 'EVENT_ID_OR_CHOICE_MISSING', 'EVENT_TIMING_AMBIGUOUS', 'ENTRY_ROOM_OR_MULTIPLE', 'PERSISTENT_CARD_VALUE_MISSING', 'CARD_SEMANTICS_PENDING', 'PLAYER_ENTRY_UNPROVEN', 'PREFIX_UNPROVEN')):
        return 'SOURCE_REQUIRED'
    if reason.startswith('POTION_ACCOUNTING_OVERFLOW'):
        return 'DERIVABLE'
    if reason.startswith(('RELIC_PERSISTENT_STATE_UNRECOVERABLE', 'RELIC_CARD_RELATION_UNRECOVERABLE', 'ELITE_BURNING_STATE')):
        return 'CONFIGURABLE'
    return 'DERIVABLE'


PRIORITY = {
    'SOURCE_REQUIRED': ('high', 'high'),
    'CONFIGURABLE': ('medium', 'low'),
    'DERIVABLE': ('medium', 'medium'),
    'BACKEND_RANDOM': ('low', 'medium'),
}


def first_reason(row: dict) -> tuple[str, dict | None]:
    chain = row.get('prefix_evidence_chain') or []
    blocked = [item for item in chain if item.get('status') == 'blocked' and item.get('error')]
    if blocked:
        item = blocked[0]
        return str(item['error']), item
    prefixed = [b['reason'][len('PREFIX_UNPROVEN:'):] for b in row.get('blockers', []) if b['reason'].startswith('PREFIX_UNPROVEN:')]
    if prefixed:
        return prefixed[0], None
    blockers = [b['reason'] for b in row.get('blockers', []) if b['reason'] not in {'PLAYER_ENTRY_UNPROVEN_OR_SOURCE_REJECTED'}]
    if blockers:
        return blockers[0], None
    return (row.get('blockers') or [{'reason': 'PLAYER_ENTRY_UNPROVEN_OR_SOURCE_REJECTED'}])[0]['reason'], None


def main() -> None:
    rows = [json.loads(line) for line in (PROJECT / 'candidate-ledger.jsonl').read_bytes().splitlines()]
    target = [row for row in rows if isinstance(row.get('floor'), int) and 1 <= row['floor'] <= 34]
    by_group: defaultdict[str, list[dict]] = defaultdict(list)
    for row in target:
        by_group[row['source_group']].append(row)
    records = []
    for row in target:
        if not row['blockers']:
            status = 'reconstructed'
            reason = None; node = None
        else:
            reason, node = first_reason(row)
            status = 'blocked'
        record = {
            'scene_id': row['scene_id'], 'source_group': row['source_group'], 'source_path': row['source_path'],
            'floor': row['floor'], 'encounter_label': row['encounter_label'], 'state_hash': row['state_hash'],
            'status': status, 'first_blocker': reason,
            'first_blocker_category': category(reason) if reason else None,
            'core_backbone_blocker': bool(reason and category(reason) == 'SOURCE_REQUIRED'),
            'blocker_node': node or {'floor': row['floor'], 'room_kind': 'battle_entry'},
            'all_detected_blockers': row['blockers'],
            'historical_rules_equivalence': 'unverified',
            'source_certification': 'unverified',
        }
        records.append(record)
    groups_first: dict[str, dict] = {}
    for record in records:
        if record['status'] == 'reconstructed':
            continue
        group = record['source_group']
        current = groups_first.get(group)
        if current is None or record['floor'] < current['floor']:
            groups_first[group] = record
    for record in records:
        first = groups_first.get(record['source_group'])
        record['first_blocker_for_source_group'] = None if first is None else first['first_blocker']
        record['downstream_rows_if_first_blocker_fixed'] = 0 if first is None else sum(
            1 for row in by_group[record['source_group']] if row['floor'] >= first['floor']
        )
    blocked = [r for r in records if r['status'] == 'blocked']
    distribution = defaultdict(lambda: {'combat_rows': 0, 'source_groups': set(), 'examples': []})
    for record in blocked:
        key = record['first_blocker']
        item = distribution[key]
        item['combat_rows'] += 1; item['source_groups'].add(record['source_group'])
        if len(item['examples']) < 3: item['examples'].append(record['scene_id'])
    # A repair releases a source-group suffix once, rather than once per row.
    group_records = defaultdict(list)
    for record in records:
        group_records[record['source_group']].append(record)
    group_suffix = defaultdict(lambda: {'reason': None, 'rows': 0})
    for group, group_rows in group_records.items():
        group_blocked = [r for r in group_rows if r['status'] == 'blocked']
        if not group_blocked:
            continue
        first = min(group_blocked, key=lambda r: r['floor'])
        group_suffix[group] = {
            'reason': first['first_blocker'],
            'rows': sum(r['floor'] >= first['floor'] for r in group_rows),
        }
    release_rows = Counter()
    for value in group_suffix.values():
        release_rows[value['reason']] += value['rows']
    priority = []
    for reason, item in distribution.items():
        cat = category(reason); level, risk = PRIORITY[cat]
        priority.append({
            'reason_code': reason, 'category': cat, 'blocked_combat_rows': item['combat_rows'],
            'blocked_source_groups': len(item['source_groups']),
            'estimated_downstream_rows_released': release_rows[reason],
            'priority': level, 'implementation_risk': risk, 'examples': item['examples'],
        })
    priority.sort(key=lambda item: (-item['estimated_downstream_rows_released'], item['reason_code']))
    summary = {
        'schema': 'act12-reconstruction-blocker-inventory-v1',
        'scope': 'combat records with floor 1..34; first blocker is the earliest source/prefix node observed by the current reconstruction chain',
        'raw_act1_act2_combat_rows': len(target),
        'reconstructed_occurrences': sum(r['status'] == 'reconstructed' for r in records),
        'blocked_occurrences': len(blocked),
        'reconstructed_source_groups': len({r['source_group'] for r in records if r['status'] == 'reconstructed'}),
        'blocked_source_groups': len({r['source_group'] for r in blocked}),
        'first_blocker_distribution': priority,
        'category_distribution': {cat: sum(item['blocked_combat_rows'] for item in priority if item['category'] == cat) for cat in sorted({item['category'] for item in priority})},
        'true_source_required_blocked_rows': sum(r['core_backbone_blocker'] for r in blocked),
        'non_source_required_blocked_rows': sum(not r['core_backbone_blocker'] for r in blocked),
        'notes': [
            'The source-certified level is deliberately independent of reconstruction and backend admission.',
            'Downstream estimates are same-source-group rows at or after the first blocker; overlapping mechanisms are not additive.',
            'The ledger preserves all detected blockers, while this table selects the first dependency in the state chain.',
        ],
    }
    (PROJECT / 'act12-blocker-ledger.jsonl').write_bytes(b''.join(json.dumps(r, ensure_ascii=False, sort_keys=True).encode('utf-8') + b'\n' for r in records))
    (PROJECT / 'blocker-priority.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'rows': len(records), 'reconstructed': summary['reconstructed_occurrences'], 'blocked': summary['blocked_occurrences'], 'top': priority[:10]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
