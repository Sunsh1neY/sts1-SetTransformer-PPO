"""精确枚举来源组均匀的开局机会；只是采样提案审计，不运行环境或PPO。"""
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def weights_by_source(rows):
    """同来源重复记录不增加质量；同来源独特状态越多，各自分得的概率越小。"""
    groups = defaultdict(dict)
    for row in rows:
        groups[row['component_id']][row['content_id']] = row
    if not groups:
        raise ValueError('没有可供审计的来源组')
    result = []
    for group, decks in sorted(groups.items()):
        for identifier, row in sorted(decks.items()):
            p = Fraction(1, len(groups) * len(decks))
            result.append(dict(component_id=group, content_id=identifier, group=row['group'],
                               decks_in_source_group=len(decks), probability=p))
    return groups, result


def audit():
    classification = runpy.run_path(str(ROOT / 'scripts/propose-a-path-deck-groups.py'))['build']()
    saved = json.loads((ROOT / 'docs/a-path-deck-grouping-proposal.json').read_bytes())
    if classification != saved:
        raise ValueError('内容台账漂移，请核查后再报告抽样机会')
    rows = [r for r in classification['contents'] if r['split'] == 'train_candidate']
    groups, weights = weights_by_source(rows)
    batch = json.loads((ROOT / 'sts/env/real-deck-batch.json').read_bytes())
    profiles, encounters = batch['profiles'], batch['encounters']
    state_hashes, weighted_states = set(), []
    by_id = {r['content_id']: r for r in rows}
    for weight in weights:
        row = by_id[weight['content_id']]
        for condition, profile in sorted(profiles.items()):
            for encounter in encounters:
                payload = {**batch['common'], **profile, 'deck': row['cards'], 'encounter': encounter}
                state_id = hashlib.sha256(canonical(payload)).hexdigest()
                state_hashes.add(state_id)
                p = weight['probability'] / len(profiles) / len(encounters)
                weighted_states.append(dict(initial_config_sha256=state_id, component_id=weight['component_id'],
                    content_id=weight['content_id'], condition=condition, encounter=encounter,
                    probability_exact=str(p), probability=float(p)))
    report = []
    for name in ('simple', 'transition', 'combo'):
        selected = [w for w in weights if w['group'] == name]
        probability = sum((w['probability'] for w in selected), Fraction(0))
        touched = {w['component_id'] for w in selected}
        report.append(dict(group='compositional' if name == 'combo' else name,
            unique_decks=len(selected), source_groups_with_this_class=len(touched),
            unique_initial_configs=len(selected)*len(profiles)*len(encounters),
            initial_probability_exact=str(probability), initial_probability=float(probability),
            expected_resets_per_1000=float(probability*1000),
            mean_resets_per_deck_per_1000=float(probability*1000/len(selected)),
            min_resets_per_deck_per_1000=float(min(w['probability'] for w in selected)*1000),
            max_resets_per_deck_per_1000=float(max(w['probability'] for w in selected)*1000),
            mean_class_resets_per_relevant_source_group_per_1000=float(probability*1000/len(touched)),
            total_resets_per_any_source_group_per_1000=1000/len(groups)))
    source_rows = sum(len(r['sources']) for r in rows)
    source_mass = {g: sum((w['probability'] for w in weights if w['component_id']==g), Fraction(0)) for g in groups}
    assert all(p == Fraction(1, len(groups)) for p in source_mass.values())
    assert sum((w['probability'] for w in weights), Fraction(0)) == 1
    assert sum((Fraction(s['probability_exact']) for s in weighted_states), Fraction(0)) == 1
    assert len(weighted_states) == len(state_hashes)
    fingerprints = ['docs/mlp-set-comparison-boundary.md', 'docs/comparison-m3-training.md',
                    'docs/comparison-ppo-report.md', 'sts/env/comparison-contract.json',
                    'sts/env/real-deck-batch.json', 'sts/env/real_deck.py',
                    'eval_seeds.json', 'scripts/propose-a-path-deck-groups.py']
    return dict(schema='a-path-source-group-uniform-audit-v1', status='proposal_awaiting_user_review',
        formal_training_started=False, training_pool_frozen=False,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in fingerprints},
        scope='comparison-battle-v2完成后的Set-only新扩展，不回写冻结对照',
        independent_source_groups=len(groups), original_runs=len({s['run'] for r in rows for s in r['sources']}),
        source_deck_records=source_rows, unique_decks=len(rows),
        unique_initial_configurations=len(state_hashes), provenance_configuration_records=source_rows*len(profiles)*len(encounters),
        registered_condition_count=len(profiles), registered_encounter_count=len(encounters),
        runtime_admitted_initial_state_count=None,
        interpretation=['initial configuration为完整卡组+条件+遭遇及固定入场字段，未计入环境seed；不是已实例化的精确观测快照',
                        '33来源组按已知run/seed/重复内容关联规则去相关，不保证消除未知关联',
                        '每1000次reset的数学期望不是每1000条transition；不预测战斗长度或实际步数份额',
                        '来源组包含多个类别时每组总机会仍相等；相关组数不能跨内容类别相加'],
        group_summary=report,
        deck_opportunities=[{**w, 'probability_exact':str(w['probability']), 'probability':float(w['probability'])} for w in weights],
        source_group_opportunities=[dict(component_id=g, unique_decks=len(ds), probability_exact=str(source_mass[g]),
            probability=float(source_mass[g]), classes=sorted({d['group'] for d in ds.values()})) for g, ds in sorted(groups.items())],
        initial_configurations=weighted_states)


if __name__ == '__main__':
    report = audit()
    (ROOT/'docs/a-path-source-sampling-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'source_sha256','deck_opportunities','source_group_opportunities','initial_configurations'}},ensure_ascii=False,indent=2))
