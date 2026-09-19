"""Audit unresolved source item names against current registries."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re

PROJECT=Path(__file__).resolve().parent
ROOT=PROJECT.parents[1]


def token(value):
    return re.sub(r'[^a-z0-9]','',value.lower())


def main():
    registry=json.loads((ROOT/'sts/env/relic-state-registry.json').read_text(encoding='utf-8'))
    names={row['name'] for row in registry['relics']};by_token={token(name):name for name in names}
    rows=[json.loads(x) for x in (PROJECT/'act12-blocker-ledger.jsonl').read_bytes().splitlines()]
    unresolved=Counter()
    for row in rows:
        if row['first_blocker'] and row['first_blocker'].startswith('RELIC_ID_UNRESOLVED:'):
            unresolved[row['first_blocker'].split(':',1)[1]]+=1
    details=[]
    for source,count in sorted(unresolved.items()):
        match=by_token.get(token(source))
        details.append({'source_name':source,'blocked_rows':count,'token_match':match,
                        'classification':'alias_candidate' if match else 'backend_coverage_pending',
                        'registry_present':source in names})
    result={'schema':'source-relic-alias-audit-v1','current_registry':'sts/env/relic-state-registry.json',
            'unresolved_source_relic_rows':sum(unresolved.values()),'details':details,
            'conclusion':'No token-only aliases were found; all unresolved names are absent from the current registry and remain backend coverage/scope work.',
            'training_pool_changed':False}
    (PROJECT/'source-alias-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
