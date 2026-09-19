"""Aggregate DERIVABLE blockers into actionable reconstruction families."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent


def family(reason: str) -> tuple[str, str, str, str]:
    if reason.startswith('UNSUPPORTED_OR_CHOICE_POTION'):
        return 'POTION_DELTA_UNHANDLED', 'source parser + current potion registry/backend adapter', 'medium', 'medium'
    if reason.startswith('UNSUPPORTED_CARD'):
        return 'BACKEND_COVERAGE_PENDING', 'current card registry/backend closure', 'medium', 'medium'
    if reason.startswith('NEOW_EFFECT_PENDING'):
        return 'NEOW_VARIANT_UNHANDLED', 'source parser + Neow RunState reducer', 'low', 'low'
    if reason.startswith(('EVENT_OUTCOME_NOT_ALLOWLISTED', 'EVENT_CARD_DELTA', 'EVENT_TIMING')):
        return 'EVENT_DELTA_UNHANDLED', 'NormalizedRunEvent + RunState reducer', 'medium', 'medium'
    if reason.startswith(('SHOP_', 'CAMPFIRE_ACTION_PENDING')):
        return 'SHOP_OR_CAMPFIRE_DELTA_UNHANDLED', 'NormalizedRunEvent + persistent reducer', 'medium', 'medium'
    if reason.startswith('UNREGISTERED_SINGING_BOWL'):
        return 'REWARD_SELECTION_DELTA_UNHANDLED', 'card/reward reducer', 'low', 'medium'
    if reason.startswith('RELIC_ID_UNRESOLVED'):
        return 'SOURCE_ALIAS_UNMAPPED', 'source alias adapter + current relic registry', 'low', 'low'
    if reason.startswith('POTION_ACCOUNTING'):
        return 'POTION_DELTA_UNHANDLED', 'potion inventory reducer / capacity adapter', 'medium', 'medium'
    return 'OTHER_DERIVABLE', 'targeted reconstruction rule', 'medium', 'high'


def main() -> None:
    rows = [json.loads(line) for line in (PROJECT / 'act12-blocker-ledger.jsonl').read_bytes().splitlines()]
    priority = json.loads((PROJECT / 'blocker-priority.json').read_text(encoding='utf-8'))
    by_reason = {item['reason_code']: item for item in priority['first_blocker_distribution']}
    grouped = defaultdict(lambda: {'reasons': [], 'combat_rows': 0, 'source_groups': set(), 'release': 0, 'examples': []})
    for row in rows:
        if row['status'] != 'blocked' or row['first_blocker_category'] != 'DERIVABLE':
            continue
        reason = row['first_blocker']; fam, layer, complexity, risk = family(reason)
        item = grouped[fam]
        item['reasons'].append(reason); item['combat_rows'] += 1; item['source_groups'].add(row['source_group'])
        if len(item['examples']) < 5: item['examples'].append(row['scene_id'])
    for fam, item in grouped.items():
        item['reasons'] = sorted(set(item['reasons']))
        item['source_groups'] = len(item['source_groups'])
        item['release'] = sum(by_reason.get(reason, {}).get('estimated_downstream_rows_released', 0) for reason in item['reasons'])
        item['layer'], item['complexity'], item['risk'] = family(item['reasons'][0])[1:]
    cost = {'low': 1, 'medium': 3, 'high': 8}
    records=[]
    for fam,item in grouped.items():
        score=item['release']/cost[item['complexity']]
        records.append({'family':fam,**item,'expected_release_per_cost':score,
                        'recommended_priority':'P0' if score>=30 else 'P1' if score>=10 else 'P2'})
    records.sort(key=lambda x:(-x['expected_release_per_cost'],x['family']))
    report={'schema':'derivable-priority-v1','scope':'Act 1/2 first blockers after configurable-state relaxation',
            'derivable_combat_rows':sum(x['combat_rows'] for x in records),
            'families':records,
            'method':'release is the source-group suffix estimate from blocker-priority; overlapping families are not additive',
            'stop_rule':'stop when high-yield families are exhausted or remaining work is concentrated in high-complexity special mechanisms'}
    (PROJECT/'derivable-priority.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'derivable_combat_rows':report['derivable_combat_rows'],'families':records},ensure_ascii=False,indent=2))


if __name__=='__main__': main()
