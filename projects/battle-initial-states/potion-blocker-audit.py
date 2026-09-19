"""Split potion-related DERIVABLE blockers using the actual run fields."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

PROJECT=Path(__file__).resolve().parent


def subtype(reason: str) -> str:
    if reason.startswith('UNSUPPORTED_OR_CHOICE_POTION'):
        return 'backend_potion_registry_pending'
    if reason.startswith(('POTION_ACCOUNTING_OVERFLOW','SHOP_POTION_CAPACITY_UNRESOLVED')) or 'Potion Belt' in reason:
        return 'capacity_or_potion_belt_pending'
    if reason.startswith(('EVENT_POTION_ID_MISSING','POTION_OBTAIN_LOG_MISSING','POTION_FLOOR_LOG_MISSING')):
        return 'source_potion_identity_missing'
    if reason.startswith(('POTION_ACCOUNTING_UNDERFLOW','POTION_WITHIN_FLOOR_ORDER','POTION_AUTO_USE_OR_GENERATION')):
        return 'inventory_delta_or_order_rule_pending'
    return 'other_potion_related'


def main():
    rows=[json.loads(x) for x in (PROJECT/'act12-blocker-ledger.jsonl').read_bytes().splitlines()]
    priority=json.loads((PROJECT/'blocker-priority.json').read_text(encoding='utf-8'))
    by_reason={x['reason_code']:x for x in priority['first_blocker_distribution']}
    groups=defaultdict(lambda:{'rows':0,'source_groups':set(),'reasons':set(),'release':0,'examples':[]})
    for row in rows:
        reason=row['first_blocker']
        if not reason or not any(token in reason for token in ('POTION','Potion Belt')):
            continue
        key=subtype(reason); item=groups[key];item['rows']+=1;item['source_groups'].add(row['source_group']);item['reasons'].add(reason)
        if len(item['examples'])<5:item['examples'].append(row['scene_id'])
    output=[]
    for key,item in groups.items():
        item['source_groups']=len(item['source_groups']);item['reasons']=sorted(item['reasons'])
        item['estimated_downstream_rows_released']=sum(by_reason.get(r,{}).get('estimated_downstream_rows_released',0) for r in item['reasons'])
        item['source_field_presence']='present_or_explicitly_absent_in_run_ledger'
        output.append({'subtype':key,**item})
    output.sort(key=lambda x:-x['estimated_downstream_rows_released'])
    report={'schema':'potion-blocker-audit-v1','scope':'first blockers in current Act 1/2 ledger; suffix rows overlap',
            'subtypes':output,'notes':[
                'Unsupported potion names are source-known inventory identities but current backend/registry coverage pending.',
                'A missing event potion identity is SOURCE_REQUIRED only when the final inventory cannot be uniquely determined.',
                'Canonical inventory slots do not claim historical slot positions.',
            ]}
    (PROJECT/'potion-blocker-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
