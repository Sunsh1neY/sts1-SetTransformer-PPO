"""只读核对A路径来源关联及候选规模；不修改旧划分或批准正式训练。"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def summarize(rows):
    parents = list(range(len(rows)))

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    seen = {}
    for i, row in enumerate(rows):
        for key in [f"run:{row['group_id']}", f"content:{row['content_hash']}", *row['identity_tokens']]:
            if key in seen:
                parents[root(i)] = root(seen[key])
            else:
                seen[key] = i
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[root(i)].append(row)
    result = []
    for members in groups.values():
        # 历史开发身份不可进入新训练侧；与其关联的数据整体保留开发身份。
        dev = any(row['old_split'] == 'development' for row in members)
        result.append({
            'group_id': hashlib.sha256(canonical(sorted(row['id'] for row in members))).hexdigest(),
            'disposition': 'development_anchor' if dev else 'train_eligible_pending_admission',
            'rows': len(members), 'runs': len({r['group_id'] for r in members}),
            'contents': len({r['content_hash'] for r in members}),
            'origins': dict(Counter(r['origin'] for r in members)),
            'old_splits': dict(Counter(r['old_split'] for r in members)),
            'row_ids': sorted(r['id'] for r in members),
        })
    totals = {}
    for disposition in ('development_anchor', 'train_eligible_pending_admission'):
        selected = [r for r in result if r['disposition'] == disposition]
        totals[disposition] = {key: sum(g[key] for g in selected) for key in ('rows', 'runs', 'contents')}
        totals[disposition]['origins'] = dict(sum((Counter(g['origins']) for g in selected), Counter()))
        selected_ids = {identifier for g in selected for identifier in g['row_ids']}
        versions = {card for row in rows if row['id'] in selected_ids for card in row['cards']}
        totals[disposition]['card_versions'] = len(versions)
        totals[disposition]['card_names'] = len({card.split('+')[0] for card in versions})
    return {'components': sorted(result, key=lambda g: g['group_id']), 'totals': totals}


def audit():
    paths = ['sts/env/real-deck-batch.json', 'docs/real-deck-manifest.json',
             'sts/env/ironclad-registry.json', 'eval_seeds.json']
    batch, manifest, registry = [json.loads((ROOT / p).read_bytes()) for p in paths[:3]]
    identity = {d['group_id']: d['source_identity_tokens'] for d in manifest['decks']}
    missing = sorted({r['group_id'] for r in batch['decks']} - identity.keys())
    if missing:
        raise ValueError(f'来源身份关联不完整：{missing}')
    names = {r['name']: r['max_upgrade'] for r in registry['cards']}

    def row(identifier, group, cards, origin, old_split):
        return dict(id=identifier, group_id=group, cards=cards,
                    content_hash=hashlib.sha256(canonical(sorted(cards))).hexdigest(),
                    identity_tokens=identity[group], origin=origin, old_split=old_split)

    old = [row(d['deck_id'], d['group_id'], d['deck'], 'intermediate', d['split']) for d in batch['decks']]
    final, rejected = [], []
    for deck in manifest['decks']:
        blockers = list(deck['extraction_blockers'])
        cards = []
        for card in deck['cards']:
            name, upgrade = card['name'], card['upgrade_level']
            if name not in names:
                blockers.append(f'UNSUPPORTED_CARD:{name}')
            elif not 0 <= upgrade <= names[name]:
                blockers.append(f'UNSUPPORTED_UPGRADE:{name}+{upgrade}')
            cards.append(name + (f'+{upgrade}' if upgrade else ''))
        if len(cards) != deck['card_count']:
            blockers.append('INCOMPLETE_CARD_COUNT')
        if blockers:
            rejected.append({'id': deck['deck_id'], 'blockers': sorted(set(blockers))})
        else:
            final.append(row(deck['deck_id'], deck['group_id'], cards, 'final-configured-candidate', 'unassigned'))
    return {
        'schema': 'a-path-data-preflight-v1', 'formal_admission': False,
        'source_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        'policy': '同run、来源身份token（含seed）、完整卡组多重集连通；历史开发身份向关联组传播；不创建未见保留集',
        'old_batch': summarize(old), 'with_final_candidates': summarize(old + final),
        'final_registry_eligible_count': len(final), 'final_registry_rejected_count': len(rejected),
        'final_rejected': rejected,
        'limitations': ['最终卡组只是新配置战斗候选，不是历史战斗入口；尚未reset/资源验收',
                       '未删牌、未补造永久实例值；未修改旧数据或eval_seeds；未进行训练'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit()
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('final_registry_eligible_count', 'final_registry_rejected_count')}, ensure_ascii=False))
    for key in ('old_batch', 'with_final_candidates'):
        print(key, json.dumps(report[key]['totals'], ensure_ascii=False))
