"""Produce semantic coverage for reconstructed and backend-validated states."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent


def base_upgrade(card: str) -> tuple[str, int]:
    if '+' not in card:
        return card, 0
    name, level = card.rsplit('+', 1)
    return name, int(level)


def main() -> None:
    rows = [json.loads(line) for line in (PROJECT / 'pilot-states.jsonl').read_bytes().splitlines()]
    ledger = [json.loads(line) for line in (PROJECT / 'candidate-ledger.jsonl').read_bytes().splitlines()]
    runtime = json.loads((PROJECT / 'runtime-report.json').read_text(encoding='utf-8'))
    checked = {row['state_hash'] for row in runtime['initial_state_checks']}
    target_rows = [row for row in rows if row['state_hash'] in checked]
    all_states = [row['state'] for row in target_rows]
    source_rows = [row for row in ledger if row.get('source_backbone_hash')]
    projected_rows = [row for row in source_rows if row['potion_projection']['projected']]
    card_counts = Counter(); upgrade_counts = Counter(); relic_counts = Counter(); potion_counts = Counter(); encounter_counts = Counter(); floors = Counter(); deck_sizes = Counter(); hp_ratios=[]; relic_combos=Counter(); potion_occupancy=Counter(); deck_encounter=Counter()
    persistent = Counter(); acts = Counter()
    for state in all_states:
        acts[str(state['act'])] += 1; floors[str(state['floor'])] += 1; encounter_counts[state['encounter']] += 1
        deck_sizes[str(len(state['deck']))] += 1
        hp_ratios.append(state['player']['hp'] / state['player']['max_hp'])
        names=[]
        for card in state['deck']:
            base, level = base_upgrade(card); card_counts[base] += 1
            if level: upgrade_counts[f'{base}+{level}'] += 1
        relic_names=[]
        for relic in state['relics']:
            name = relic['name'] if isinstance(relic, dict) else relic; relic_names.append(name); relic_counts[name] += 1
            if isinstance(relic, dict): persistent[name] += 1
        for potion in state['potions']:
            if potion: potion_counts[potion] += 1
        potion_occupancy[str(sum(p is not None for p in state['potions']))] += 1
        relic_combos['|'.join(relic_names)] += 1
        deck_encounter[f'{len(state["deck"])}:{state["encounter"]}'] += 1
    blocked = json.loads((PROJECT / 'blocker-priority.json').read_text(encoding='utf-8'))
    def source_group(provenance):
        return provenance.get('source_group') or (provenance.get('origins') or [{}])[0].get('source_group')
    def backbone_id(state):
        import copy, hashlib
        value = copy.deepcopy(state); value['burning_elite'] = 'CONFIGURABLE'
        relics=[]
        for relic in value['relics']:
            if isinstance(relic,dict) and 'card_index' in relic: relics.append({'name':relic['name'],'card_index':'CONFIGURABLE'})
            elif isinstance(relic,dict) and 'counter' in relic: relics.append({'name':relic['name'],'counter':'CONFIGURABLE'})
            else: relics.append(relic)
        value['relics']=relics
        return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    reconstruction = json.loads((PROJECT / 'reconstruction-report.json').read_text(encoding='utf-8'))
    configured_state_count = sum(1 for row in rows if any(isinstance(relic, dict) for relic in row['state']['relics']))
    configured_field_counts = Counter()
    configured_binding_count = 0
    for row in rows:
        for relic in row['state']['relics']:
            if isinstance(relic, dict):
                configured_field_counts[relic['name']] += 1
                configured_binding_count += int('card_index' in relic)
    result = {
        'schema': 'act12-a-coverage-report-v1',
        'admission_standard': 'backend-validated',
        'source_certified_required': False,
        'raw_act1_act2_combat_rows': 2591,
        'source_derived_occurrence_count': reconstruction['source_derived_occurrences'],
        'reconstructed_occurrence_count': reconstruction['rule_derived_occurrences'],
        'canonical_reconstructed_state_count': len(rows),
        'source_derived_backbone_count': reconstruction['canonical_source_backbones'],
        'scope_projected_occurrence_count': len(projected_rows),
        'scope_projected_instance_count': len({row['training_instance_hash'] for row in projected_rows}),
        'configured_state_count': configured_state_count,
        'configured_field_occurrences': dict(configured_field_counts.most_common()),
        'configured_bottle_binding_occurrences': configured_binding_count,
        'backend_validated_occurrence_count': sum(row.get('state_hash') is not None for row in ledger),
        'backend_validated_state_count': len(target_rows),
        'backend_validated_source_groups': len({source_group(row['provenance']) for row in target_rows}),
        'backend_validated_act_distribution': dict(sorted(acts.items())),
        'floor_distribution': dict(sorted(floors.items(), key=lambda item: int(item[0]))),
        'encounter_distribution': dict(encounter_counts.most_common()),
        'deck_size_distribution': dict(sorted(deck_sizes.items(), key=lambda item: int(item[0]))),
        'card_identity_occurrences': dict(card_counts.most_common()),
        'card_identity_count': len(card_counts),
        'upgrade_occurrences': dict(upgrade_counts.most_common()),
        'upgrade_identity_count': len(upgrade_counts),
        'hp_ratio': {'min': min(hp_ratios), 'max': max(hp_ratios), 'mean': sum(hp_ratios)/len(hp_ratios)},
        'relic_identity_occurrences': dict(relic_counts.most_common()),
        'relic_identity_count': len(relic_counts),
        'relic_persistent_state_occurrences': dict(persistent.most_common()),
        'relic_combination_count': len(relic_combos),
        'top_relic_combinations': dict(relic_combos.most_common(20)),
        'potion_identity_occurrences': dict(potion_counts.most_common()),
        'source_backbone_potion_identity_occurrences': dict(Counter(
            potion for row in source_rows for potion in row['source_backbone']['potions'] if potion
        ).most_common()),
        'removed_unsupported_potion_identities': sorted({
            potion for row in projected_rows
            for potion in row['potion_projection']['removed_potions']
        }),
        'potion_occupancy': dict(sorted(potion_occupancy.items(), key=lambda item: int(item[0]))),
        'deck_encounter_pair_count': len(deck_encounter),
        'top_deck_encounter_pairs': dict(deck_encounter.most_common(30)),
        'interaction_coverage': {
            'relics_with_potions': sum(1 for row in all_states if any(isinstance(r, dict) for r in row['relics']) and any(row['potions'])),
            'nonempty_potions_with_act2': sum(1 for row in all_states if row['act'] == 2 and any(row['potions'])),
            'derived_counter_states': sum(1 for row in all_states if any(isinstance(r, dict) for r in row['relics'])),
            'bottled_relation_states': sum(1 for row in all_states if any((r.get('name') if isinstance(r, dict) else r) in {'Bottled Flame','Bottled Lightning','Bottled Tornado'} for r in row['relics'])),
        },
        'sparse_or_missing': {
            'act2_floors_not_reconstructed': [floor for floor in range(18,35) if str(floor) not in floors],
            'elite_entries': 0,
            'bottled_relation_entries': 0,
            'persistent_counter_identity_count': len(persistent),
            'source_certified_states': 0,
        },
        'blocker_priority_path': 'blocker-priority.json',
        'potion_projection_report_path': 'potion-projection-report.json',
        'runtime_report_path': 'runtime-report.json',
        'formal_training_pool_changed': False,
    }
    (PROJECT / 'act12-coverage-report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('raw_act1_act2_combat_rows','reconstructed_occurrence_count','canonical_reconstructed_state_count','backend_validated_state_count','backend_validated_act_distribution','floor_distribution','encounter_distribution')}, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
