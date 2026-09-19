"""Profile the frozen diagnostic A corpus without loading or changing the backend."""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import statistics

from initial_state import state_hash

PROJECT = Path(__file__).resolve().parent
ROOT = PROJECT.parents[1]
ELITES = {'GREMLIN_NOB', 'LAGAVULIN', 'THREE_SENTRIES', 'SLAVERS',
          'GREMLIN_LEADER', 'BOOK_OF_STABBING', 'COLOSSEUM_EVENT_SLAVERS', 'COLOSSEUM_EVENT_NOBS'}
BOSSES = {'SLIME_BOSS', 'THE_GUARDIAN', 'HEXAGHOST', 'AUTOMATON', 'COLLECTOR', 'CHAMP'}
# Presence probes are overlapping diagnostic combinations, not deck archetype labels.
PROBES = {
    'exhaust-engine': [{'Corruption'}, {'Feel No Pain', 'Dark Embrace'}],
    'strength-payoff': [{'Inflame', 'Demon Form', 'Spot Weakness'}, {'Heavy Blade', 'Pummel', 'Sword Boomerang', 'Reaper'}],
    'block-retention-payoff': [{'Barricade'}, {'Body Slam', 'Entrench'}],
    'status-payoff': [{'Evolve', 'Fire Breathing'}, {'Wild Strike', 'Power Through', 'Reckless Charge', 'Immolate'}],
    'self-damage-payoff': [{'Rupture'}, {'Hemokinesis', 'Bloodletting', 'Combust', 'Brutality', 'Offering'}],
    'dropkick-weak': [{'Dropkick'}, {'Bash', 'Uppercut', 'Thunderclap'}],
}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def name(value):
    return value['name'] if isinstance(value, dict) else value


def base(card):
    return card.split('+')[0]


def hp_band(state):
    ratio = state['player']['hp'] / state['player']['max_hp']
    return '<=25%' if ratio <= .25 else '25-50%' if ratio <= .5 else '50-75%' if ratio <= .75 else '>75%'


def kind(encounter):
    return 'boss' if encounter in BOSSES else 'elite' if encounter in ELITES else 'event' if 'EVENT' in encounter else 'normal'


def main():
    inputs = [PROJECT / p for p in ('admitted-a-corpus.jsonl', 'pilot-states.jsonl',
              'candidate-ledger.jsonl', 'runtime-report.json', 'a-corpus-admission.json')]
    inputs += [ROOT / 'sts/env' / p for p in ('ironclad-registry.json', 'relic-state-registry.json',
               'ironclad-expansion-contract.json', 'full-card-public-contract.json')]
    fingerprints = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    corpus, pilot, ledger = (rows(p) for p in inputs[:3])
    runtime, admission = load(inputs[3]), load(inputs[4])
    assert len(corpus) == 1377 == admission['state_count']
    assert digest(inputs[0]) == admission['artifact_sha256']
    assert digest(inputs[3]) == admission['runtime_report_sha256']
    hashes = {r['state_hash'] for r in corpus}
    assert len(hashes) == len(corpus)
    assert hashes == {r['state_hash'] for r in pilot} == {r['state_hash'] for r in runtime['initial_state_checks']}
    assert not runtime['failures']
    for r in corpus:
        assert state_hash(r['state']) == r['state_hash']
        assert state_hash(r['source_backbone']) == r['source_backbone_hash']
        assert all(r['state'][k] == r['source_backbone'][k] for k in r['state'] if k != 'potions')
        assert not r['admission']['training_pool_admitted']
    def groups(r):
        return {o['source_group'] for o in r['provenance']['origins']}
    all_groups = set().union(*(groups(r) for r in corpus))
    group_states = {g: [r for r in corpus if g in groups(r)] for g in all_groups}
    def profile(selected):
        gs = set().union(*(groups(r) for r in selected)) if selected else set()
        return {'states': len(selected), 'pct': round(100 * len(selected)/len(corpus), 2),
                'source_groups': len(gs), 'components': len({r['provenance']['component'] for r in selected}),
                'equal_group_pct': round(100 * sum(sum(g in groups(r) for r in selected)/len(group_states[g]) for g in all_groups)/len(all_groups), 2)}
    def categorical(fn):
        buckets = defaultdict(list)
        for r in corpus:
            buckets[str(fn(r))].append(r)
        return {k: profile(v) for k, v in sorted(buckets.items())}
    def quantiles(values):
        return {'min': min(values), 'p25': statistics.quantiles(values, n=4)[0],
                'median': statistics.median(values), 'p75': statistics.quantiles(values, n=4)[2], 'max': max(values)}
    dimensions = {
        'act': lambda r: r['state']['act'], 'floor': lambda r: r['state']['floor'],
        'ascension': lambda r: r['state']['ascension'], 'encounter': lambda r: r['state']['encounter'],
        'encounter_kind': lambda r: kind(r['state']['encounter']), 'hp_band': lambda r: hp_band(r['state']),
        'act_hp': lambda r: f"{r['state']['act']} / {hp_band(r['state'])}",
        'act_kind': lambda r: f"{r['state']['act']} / {kind(r['state']['encounter'])}",
        'potion_occupancy': lambda r: sum(p is not None for p in r['state']['potions']),
        'source_potion_occupancy': lambda r: sum(p is not None for p in r['source_backbone']['potions']),
        'potion_transition': lambda r: f"{sum(p is not None for p in r['source_backbone']['potions'])}->{sum(p is not None for p in r['state']['potions'])}",
        'partition': lambda r: r['provenance']['partition'],
        'partition_act': lambda r: f"{r['provenance']['partition']} / {r['state']['act']}",
        'burning_elite': lambda r: r['state']['burning_elite'],
    }
    distributions = {k: categorical(fn) for k, fn in dimensions.items()}
    card_names = {c['name'] for c in load(inputs[5])['cards']}
    relic_names = {c['name'] for c in load(inputs[6])['relics']}
    encounter_names = set(load(inputs[7])['scope']['encounters'])
    potion_names = {c['name'] for c in load(inputs[8])['potions']}
    cards, relics, potions = {}, {}, {}
    for universe, target, field in ((card_names, cards, 'deck'), (relic_names, relics, 'relics'), (potion_names, potions, 'potions')):
        observed = {base(name(v)) for r in corpus for v in r['state'][field] if v is not None}
        for n in sorted(universe | observed):
            subset = [r for r in corpus if n in {base(name(v)) for v in r['state'][field] if v is not None}]
            target[n] = profile(subset)
            target[n]['acts'] = dict(Counter(r['state']['act'] for r in subset))
            target[n]['encounters'] = len({r['state']['encounter'] for r in subset})
            if field == 'deck':
                target[n]['copies'] = sum(sum(base(c) == n for c in r['state']['deck']) for r in subset)
                target[n]['upgraded_states'] = sum(any(base(c) == n and '+' in c for c in r['state']['deck']) for r in subset)
    probes = {label: profile([r for r in corpus if all(set(map(base, r['state']['deck'])) & choice for choice in choices)])
              for label, choices in PROBES.items()}
    interactions = {f'{e} / {band}': profile([r for r in corpus if r['state']['encounter'] == e and hp_band(r['state']) == band])
                    for e in sorted(set(distributions['encounter'])) for band in ('<=25%', '25-50%', '50-75%', '>75%')}
    group_partitions, component_partitions = defaultdict(set), defaultdict(set)
    for r in corpus:
        for g in groups(r):
            group_partitions[g].add(r['provenance']['partition'])
        component_partitions[r['provenance']['component']].add(r['provenance']['partition'])
    raw = [r for r in ledger if 1 <= r['floor'] <= 34]
    retention = {}
    for act in (1, 2):
        selection = [r for r in raw if (r['floor'] - 1)//17 + 1 == act]
        accepted = [r for r in selection if r.get('backend_admissible') and r.get('state_hash') in hashes]
        retention[str(act)] = {'raw_occurrences': len(selection), 'validated_occurrences': len(accepted),
                              'retention_pct': round(100*len(accepted)/len(selection), 2)}
    deck_ids = Counter(tuple(sorted(r['state']['deck'])) for r in corpus)
    components = Counter(r['provenance']['component'] for r in corpus)
    configs = Counter(f for r in corpus for f in r['reconstruction']['configurable_fields'])
    result = {
        'schema': 'a-corpus-coverage-analysis-v1', 'input_sha256': fingerprints,
        'scope': 'Frozen 1377 diagnostic states; no backend execution, pool admission, or training.',
        'grain': {'canonical_states': len(corpus), 'origin_occurrences': sum(len(r['provenance']['origins']) for r in corpus),
                  'all_origin_source_groups': len(all_groups), 'primary_source_groups': len({r['provenance']['source_group'] for r in corpus}),
                  'connected_components': len(components), 'cross_source_canonical_states': sum(len(groups(r)) > 1 for r in corpus),
                  'distinct_deck_multisets_with_upgrades': len(deck_ids),
                  'distinct_deck_encounter_pairs': len({(tuple(sorted(r['state']['deck'])), r['state']['encounter']) for r in corpus}),
                  'largest_component_states': max(components.values()), 'top10_component_states': sum(v for _,v in components.most_common(10))},
        'quality': {'hashes_and_runtime_join_verified': True,
                    'source_groups_crossing_partitions': sum(len(v)>1 for v in group_partitions.values()),
                    'components_crossing_partitions': sum(len(v)>1 for v in component_partitions.values()),
                    'wrapper_schemas': dict(Counter(r['schema'] for r in corpus)),
                    'canonical_record_schemas': dict(Counter(r['schema'] for r in pilot)),
                    'historical_certification': dict(Counter(r['provenance']['source_certification'] for r in corpus))},
        'distributions': distributions, 'retention_by_act': retention,
        'numeric': {'hp_ratio': quantiles([r['state']['player']['hp']/r['state']['player']['max_hp'] for r in corpus]),
                    'deck_size': quantiles([len(r['state']['deck']) for r in corpus]),
                    'upgraded_copies': quantiles([sum('+' in c for c in r['state']['deck']) for r in corpus]),
                    'states_per_source_group': quantiles([len(v) for v in group_states.values()])},
        'cards': cards, 'relics': relics, 'potions': potions,
        'missing_registered_encounters': sorted(encounter_names - set(distributions['encounter'])),
        'registered_encounter_denominator_note': 'Expansion registry includes encounters outside Act 1/2; absence is not automatically an in-scope gap.',
        'configured_fields': dict(configs), 'projected_states': sum(r['potion_projection']['projected'] for r in corpus),
        'combo_probe_rules': {k: [sorted(v) for v in choices] for k, choices in PROBES.items()},
        'combo_probes': probes, 'encounter_hp_cells': interactions,
        'combo_partition_counts': {label: dict(Counter(r['provenance']['partition'] for r in corpus if all(set(map(base, r['state']['deck'])) & choice for choice in choices))) for label, choices in PROBES.items()},
        'partition_encounter_counts': {part: dict(Counter(r['state']['encounter'] for r in corpus if r['provenance']['partition']==part)) for part in distributions['partition']},
        'persistent_relic_values': {n: dict(Counter(str(v['counter']) for r in corpus for v in r['state']['relics'] if isinstance(v,dict) and v['name']==n and 'counter' in v)) for n in relics if any(isinstance(v,dict) and v['name']==n and 'counter' in v for r in corpus for v in r['state']['relics'])},
        'runtime_scope': {'reset_checked_states': runtime['counts']['states_checked'], 'full_rollout_states': len({r['state_hash'] for r in runtime['episodes']}), 'episodes': len(runtime['episodes'])},
    }
    assert all(digest(p) == fingerprints[str(p.relative_to(ROOT))] for p in inputs)
    (PROJECT/'a-corpus-coverage.json').write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)+'\n', encoding='utf-8')
    lines = ['# A corpus coverage analysis', '', 'Date: 2026-09-19. Frozen diagnostic corpus; no formal training admission.', '',
             '## Findings and implications', '',
             '- Broad identity coverage is present: 39 encounter identities, including six ordinary elites and six bosses; 74 observed card identities, 118 relic identities and all 15 supported potion identities. Identity presence is not sufficient coverage of interactions.',
             '- Act 1 has 1,004 states and Act 2 has 373. Act 2 retains only 373/1,161 raw combat occurrences (32.13%), versus 1,041/1,430 (72.80%) in Act 1. This is reconstruction/admission selection, not evidence that Act 2 is naturally rare.',
             '- Act 2 accounts for 27.09% of states but 17.45% under equal-source-group weighting. Existing source weighting would emphasize early fights more than the unweighted table suggests.',
             '- Only 24 states have HP at or below 25%, including four Act 2 states. Of the 156 observed-encounter by HP-band cells, 37 are empty. These are empirical coverage gaps, not claims that every combination should occur naturally.',
             '- Potion projection affects 792 states. Empty inventories increase from 283 to 787; 504 previously nonempty inventories become empty. The projected corpus cannot establish historical potion-availability behavior.',
             '- Combination probes have narrow independent support: Barricade plus Body Slam/Entrench has five states from one source group; Rupture plus a listed self-damage card has four from one group. Repeated states within those runs cannot support held-out-source generalization for those combinations.',
             '- Persistent counter coverage is concentrated: Happy Flower, Incense Burner, Ink Bottle, Nunchaku, Pen Nib and Sundial appear only at zero in these entry states. Their identity counts do not cover alternative entry-counter phases.',
             '- The 134-state audit holdout has only seven connected components. No group/component crosses partitions, but the holdout offers limited independent-source coverage.',
             '- Searing Blow and Thunderclap are absent. Burn, Dazed, Slimed and Wound are also absent from entry master decks; their absence is not evidence that combat-generated status handling is absent.',
             '- All 395 elite entries have a configured burning-elite field, and all 1,377 states have burning_elite=false. Burning-elite conditions are therefore absent.',
             '- Holdout has 31 Act 2 states from five connected components. Five observed encounters are absent from holdout: CENTURION_AND_HEALER, CHAMP, CHOSEN_AND_BYRDS, LOTS_OF_SLIMES and TWO_THIEVES. Block-retention and self-damage probes occur only in audit-train; the Dropkick probe is also absent from holdout.', '',
             '## Recommended bounded next steps', '',
             '1. Use these frozen states for a source-component-separated baseline only with explicit Act, HP, encounter and projection strata. The analysis does not establish training sufficiency or learning performance.',
             '2. Inspect existing holdout support for rare combinations before assigning evaluation claims. Do not split the same source component to manufacture train/test examples.',
             '3. Prioritize low-HP Act 2, rare combination independence, persistent counter phases and scarce Act 2 bosses in any future coverage decision. No state generation or backend expansion is performed here.',
             '4. Resolve the v1 wrapper versus v2 canonical-schema label before a later consumer integration; preserve this frozen corpus during analysis.', '',
             '## Definitions and evidence', '',
             'State counts use distinct canonical state hashes. Source coverage uses every provenance origin, not only the primary origin. Equal-group percentages first select an observed source group uniformly, then a state within it; this is a descriptive sensitivity analysis, not a changed sampler. Connected components remain the split boundary.', '',
             'All input hashes, canonical state hashes and the runtime-state join were checked. Historical rules equivalence remains unverified. The corpus wrapper labels records v1 while canonical pilot records and hashing use v2; this naming inconsistency is recorded, not repaired by this analysis.', '',
             '## Grain', '', '```json', json.dumps(result['grain'], indent=2), '```', '',
             '## Coverage tables', '']
    for title, table in {**distributions, 'Combination presence probes (overlapping; not archetype certification)': probes}.items():
        lines += [f'### {title}', '', '| Value | States | State % | Source groups | Components | Equal-group % |', '|---|---:|---:|---:|---:|---:|']
        lines += [f"| {k} | {v['states']} | {v['pct']} | {v['source_groups']} | {v['components']} | {v['equal_group_pct']} |" for k,v in table.items()]
        lines += ['']
    for title, table in [('Cards',cards), ('Relics',relics), ('Supported potions',potions)]:
        lines += [f'## {title}', '', '| Identity | States | Source groups | Encounter identities | Upgraded states |', '|---|---:|---:|---:|---:|']
        lines += [f"| {k} | {v['states']} | {v['source_groups']} | {v['encounters']} | {v.get('upgraded_states', 'N/A')} |" for k,v in sorted(table.items(), key=lambda kv:(kv[1]['states'],kv[0]))]
        lines += ['']
    lines += ['## Interpretation limits', '',
              '- Card/relic presence and combination probes do not demonstrate learned use or successful synergy execution.',
              '- Floors without combat entries are not automatically coverage defects; no denominator of all possible game states is claimed.',
              '- Registry absence is a development-scope comparison; the expansion encounter registry includes out-of-scope encounters.',
              '- Configured fields and potion projection alter the training instance distribution; counts remain separate in the JSON.',
              '- Full episode evidence covers a representative subset only; reset validation is broader.', '',
              '## Reproduction', '', '`python -B projects/battle-initial-states/analyze-a-coverage.py`', '',
              'Detailed cross-tabs, retention denominators, probe rules, numeric summaries and immutable input fingerprints: [a-corpus-coverage.json](a-corpus-coverage.json).', '']
    (PROJECT/'a-corpus-coverage.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('grain','quality','retention_by_act','numeric','configured_fields','combo_probes','missing_registered_encounters')}, indent=2))


if __name__ == '__main__':
    main()
