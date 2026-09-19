"""Inventory the locked upstream catalog; occurrence is not behavior evidence."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'third_party/sts_lightspeed'
SOURCE = BACKEND / 'include/constants/Relics.h'


def main():
    text = SOURCE.read_text(encoding='utf-8')
    def array(name):
        body = re.search(r'\b' + name + r'\[\]\s*\{(.*?)\};', text, re.S).group(1)
        return re.findall(r'"([^"]+)"', body)
    enums, names = array('relicEnumNames'), array('relicNames')
    assert len(enums) == len(names)
    registry = json.loads((ROOT / 'sts/env/relic-state-registry.json').read_bytes())
    normalize = lambda name: re.sub('[^a-z0-9]', '', name.lower())
    registered = {normalize(r['name']): r for r in registry['relics']}
    # Resolve adapter spelling aliases without changing stable public identities.
    adapter = (BACKEND / 'bindings/integrated-card-env.cpp').read_text(encoding='utf-8')
    for public_name, enum in re.findall(r'if \(counters && name == "([^"]+)"\) return R::(\w+);', adapter):
        if normalize(public_name) in registered:
            registered[normalize(enum)] = registered[normalize(public_name)]
    review = {'FROZEN_EYE': 'visibility', 'RUNIC_DOME': 'visibility',
              'GAMBLING_CHIP': 'selection', 'NILRYS_CODEX': 'selection_and_generation',
              'POTION_BELT': 'capacity', 'BOTTLED_FLAME': 'card_binding',
              'BOTTLED_LIGHTNING': 'card_binding', 'BOTTLED_TORNADO': 'card_binding'}
    files = [p for folder in ('src', 'include') for p in (BACKEND / folder).rglob('*')
             if p.suffix in {'.h', '.cpp'} and p != SOURCE]
    texts = [(p.relative_to(BACKEND).as_posix(), p.read_text(encoding='utf-8')) for p in files]
    rows = []
    for enum, name in zip(enums, names):
        if enum == 'INVALID':
            continue
        definition = registered.get(normalize(enum))
        refs = []
        pattern = re.compile(r'\b(?:R|RelicId)::' + enum + r'\b')
        for path, body in texts:
            lines = [i for i, line in enumerate(body.splitlines(), 1) if pattern.search(line)]
            if lines:
                refs.append(dict(path=path, lines=lines))
        rows.append(dict(upstream_enum=enum, upstream_name=name,
            implementation_status='diagnostic_tested' if definition else 'not_imported',
            public_state=({'counter': definition['counter'], 'played_types': ['attack_played','skill_played','power_played']} if enum == 'ORANGE_PELLETS' else definition['counter']) if definition else 'pending',
            training_admitted=bool(definition and definition['training_admitted']),
            owner_review=review.get(enum), source_occurrences=refs,
            original_game_behavior_verification='pending',
            behavior_test=('tests/test_relic_remaining.py' if definition['id']>33 else 'tests/test_relic_batch_three.py' if definition['id']>22 else 'tests/test_relic_batch_two.py' if definition['id']>14 else 'tests/test_relic_state.py') if definition else None))
    result = dict(schema='relic-audit-ledger-v1', upstream_commit=json.loads(
        (ROOT / 'scripts/lightspeed-lock.json').read_bytes())['commit'],
        catalog_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        evidence_boundary='Static upstream occurrences plus scoped simulator tests; not original-game parity or a complete mechanism audit.',
        original_game_catalog_comparison='pending', relics=rows)
    output = ROOT / 'docs/evidence/relic-audit-ledger.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'{len(rows)} upstream relics inventoried; {sum(r["implementation_status"] == "diagnostic_tested" for r in rows)} scoped imports')


if __name__ == '__main__':
    main()
