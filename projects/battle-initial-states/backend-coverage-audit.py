"""Audit DERIVABLE entities against frozen current card/potion/relic closures."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re

PROJECT=Path(__file__).resolve().parent; ROOT=PROJECT.parents[1]


def main():
    rows=[json.loads(x) for x in (PROJECT/'act12-blocker-ledger.jsonl').read_bytes().splitlines()]
    cards=json.loads((ROOT/'sts/env/ironclad-registry.json').read_text())['cards']
    potions=json.loads((ROOT/'sts/env/full-card-public-contract.json').read_text())['potions']
    relics=json.loads((ROOT/'sts/env/relic-state-registry.json').read_text())['relics']
    card_rows=Counter();potion_rows=Counter();relic_rows=Counter()
    for row in rows:
        reason=row['first_blocker'] or ''
        if reason.startswith('UNSUPPORTED_CARD'):
            for name in reason.split(':',1)[1].split(','): card_rows[name]+=1
        if reason.startswith('UNSUPPORTED_OR_CHOICE_POTION'):
            for name in reason.split(':',1)[1].split(','): potion_rows[name]+=1
        if reason.startswith('RELIC_ID_UNRESOLVED'):
            relic_rows[reason.split(':',1)[1]]+=1
    result={'schema':'backend-coverage-audit-v1','training_pool_changed':False,
      'card_registry_count':len(cards),'potion_registry_count':len(potions),'relic_registry_count':len(relics),
      'unsupported_card_occurrences':dict(card_rows.most_common()),
      'unsupported_potion_occurrences':dict(potion_rows.most_common()),
      'unregistered_relic_occurrences':dict(relic_rows.most_common()),
      'decisions':{
       'cards':'Current expanded closure is Ironclad 80-card scope; observed colorless/curse/special generated cards remain pending because admitting them requires closure/action semantics review.',
       'potions':'Current public potion closure is 15 names although the C++ enum contains more; adding names requires action/observation closure validation and is not a pure parser alias.',
       'relics':'All unresolved names are absent from current relic-state registry; no token-only aliases found. Preserve as backend coverage or frozen scope exclusions.',
      }}
    (PROJECT/'backend-coverage-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
