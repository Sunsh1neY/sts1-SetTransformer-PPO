"""按完整卡组内容生成分组提案；不创建训练池，不改准入或原划分。"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'a-path-deck-grouping-proposal-v1'
BASE = {'Strike_R', 'Defend_R', 'Bash', 'AscendersBane'}
EXHAUST = {'Corruption', 'Second Wind', 'Fiend Fire', 'Burning Pact', 'True Grit', 'Sever Soul', 'Havoc'}
EXHAUST_PAYOFF = {'Feel No Pain', 'Dark Embrace', 'Sentinel'}
STATUS_SOURCE = {'Power Through', 'Wild Strike', 'Reckless Charge', 'Immolate'}
STATUS_PAYOFF = {'Evolve', 'Fire Breathing'}
BLOCK = {'Impervious', 'Power Through', 'Flame Barrier', 'Entrench', 'Barricade'}
STRENGTH = {'Inflame', 'Spot Weakness', 'Demon Form', 'Flex'}
STRENGTH_PAYOFF = {'Limit Break', 'Heavy Blade', 'Sword Boomerang', 'Pummel', 'Twin Strike', 'Whirlwind', 'Fiend Fire', 'Reaper'}
SELF_DAMAGE = {'Offering', 'Bloodletting', 'Hemokinesis', 'Brutality', 'Combust'}
SELF_PAYOFF = {'Rupture', 'Blood for Blood'}
DRAW = {'Offering', 'Battle Trance', 'Pommel Strike', 'Shrug It Off', 'Burning Pact', 'Warcry', 'Brutality'}
ENERGY = {'Offering', 'Bloodletting', 'Seeing Red', 'Berserk'}
LABELS = {'simple': '基础与单牌主导', 'transition': '过渡与局部配合', 'combo': '多机制组合'}


def classify(cards):
    counts = Counter(card.split('+')[0] for card in cards)
    names = set(counts)
    if not cards:
        raise ValueError('不能给空卡组分类')
    pairs = {}

    def register(key, left, right):
        a, b = sorted(names & left), sorted(names & right)
        if a and b:
            pairs[key] = {'source': a, 'payoff': b}

    register('exhaust', EXHAUST, EXHAUST_PAYOFF)
    register('status', STATUS_SOURCE, STATUS_PAYOFF)
    register('block_to_damage', BLOCK, {'Body Slam'})
    if {'Barricade', 'Entrench'} <= names:
        pairs.setdefault('block_to_damage', {'source': ['Barricade'], 'payoff': ['Entrench']})
    if 'Juggernaut' in names and names & {'Feel No Pain', 'Rage', 'Metallicize'}:
        previous = pairs.setdefault('block_to_damage', {'source': [], 'payoff': []})
        previous['source'] = sorted(set(previous['source']) | (names & {'Feel No Pain', 'Rage', 'Metallicize'}))
        previous['payoff'] = sorted(set(previous['payoff']) | {'Juggernaut'})
    register('strength', STRENGTH, STRENGTH_PAYOFF)
    register('self_damage', SELF_DAMAGE, SELF_PAYOFF)
    register('vulnerable_draw_energy', {'Bash', 'Uppercut', 'Shockwave', 'Thunderclap'}, {'Dropkick'})
    draw_count = sum(counts[x] for x in DRAW)
    energy_count = sum(counts[x] for x in ENERGY)
    # 抽牌/能量密度只作资源标签，不把Offering单牌同时具备两种功能算成组合。
    resource_dense = draw_count >= 3 and energy_count >= 2 and len(names & (DRAW | ENERGY)) >= 3
    engines = []
    if 'Corruption' in names and names & EXHAUST_PAYOFF and len(names & (EXHAUST | EXHAUST_PAYOFF)) >= 3:
        engines.append('corruption_exhaust_chain')
    if {'Feel No Pain', 'Dark Embrace'} <= names and names & EXHAUST:
        engines.append('exhaust_draw_block_chain')
    if {'Barricade', 'Entrench'} <= names and ('Body Slam' in names or sum(counts[x] for x in BLOCK - {'Barricade', 'Entrench'}) >= 2):
        engines.append('block_retention_scaling')
    if 'Limit Break' in names and names & STRENGTH and names & (STRENGTH_PAYOFF - {'Limit Break'}):
        engines.append('strength_scaling_payoff')
    base_count = sum(counts[x] for x in BASE)
    extra_count = len(cards) - base_count
    if len(pairs) >= 2 or engines or (resource_dense and pairs):
        group, reason = 'combo', '至少两类明确配合，或登记的三要素组合链，或抽牌能量密集且至少一类配合'
    elif base_count / len(cards) >= .6 and extra_count <= 3 and not pairs:
        group, reason = 'simple', '起始骨架至少60%、额外牌至多3张、没有登记的成对组合'
    else:
        group, reason = 'transition', '不满足简单组，且尚未达到多机制组合规则'
    return {'group': group, 'group_label': LABELS[group], 'reason': reason,
            'card_count': len(cards), 'base_count': base_count, 'base_fraction': base_count / len(cards),
            'extra_count': extra_count, 'families': pairs, 'engines': engines,
            'draw_copies': draw_count, 'energy_copies': energy_count, 'resource_dense': resource_dense}


def build():
    audit = runpy.run_path(str(ROOT / 'scripts/audit-a-path-data.py'))['audit']()
    saved = json.loads((ROOT / 'docs/a-path-data-preflight.json').read_bytes())
    if saved != audit:
        raise ValueError('原数据预检已经漂移，须先核查而非套用旧划分')
    batch = json.loads((ROOT / 'sts/env/real-deck-batch.json').read_bytes())
    manifest = json.loads((ROOT / 'docs/real-deck-manifest.json').read_bytes())
    lookup = {d['deck_id']: {'cards': d['deck'], 'origin': 'intermediate', 'run': d['group_id']} for d in batch['decks']}
    lookup.update({d['deck_id']: {'cards': [c['name'] + (f"+{c['upgrade_level']}" if c['upgrade_level'] else '') for c in d['cards']],
                               'origin': 'final', 'run': d['group_id']} for d in manifest['decks']})
    contents = {}
    for component in audit['with_final_candidates']['components']:
        split = 'train_candidate' if component['disposition'].startswith('train') else 'development'
        for identifier in component['row_ids']:
            row = lookup[identifier]
            cards = tuple(sorted(row['cards']))
            content_id = hashlib.sha256(json.dumps(cards, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
            if content_id not in contents:
                contents[content_id] = dict(content_id=content_id, split=split, component_id=component['group_id'],
                    cards=list(cards), composition=dict(sorted(Counter(cards).items())), sources=[], **classify(cards))
            target = contents[content_id]
            if target['split'] != split or target['component_id'] != component['group_id']:
                raise ValueError('重复内容跨划分或跨关联组')
            target['sources'].append({'id': identifier, 'origin': row['origin'], 'run': row['run']})
    summary = []
    for split in ('train_candidate', 'development'):
        for group in LABELS:
            rows = [r for r in contents.values() if r['split'] == split and r['group'] == group]
            origin_contents = Counter()
            for row in rows:
                origin_contents.update({s['origin'] for s in row['sources']})
            summary.append(dict(split=split, group=group, label=LABELS[group], contents=len(rows),
                source_rows=sum(len(r['sources']) for r in rows),
                runs=len({s['run'] for r in rows for s in r['sources']}),
                components=len({r['component_id'] for r in rows}),
                origin_contents=dict(origin_contents),
                card_count_range=[min((r['card_count'] for r in rows), default=0), max((r['card_count'] for r in rows), default=0)],
                combo_family_counts=dict(Counter(k for r in rows for k in r['families'])),
                resource_dense_contents=sum(r['resource_dense'] for r in rows)))
    result = dict(schema=VERSION, status='proposal_awaiting_user_review', training_pool_frozen=False,
        source_sha256=audit['source_sha256'], summary=summary,
        proposal={'transition_weights': {'simple': .5, 'transition': .25, 'combo': .25},
                  'persistent_env_slots': {'simple': 4, 'transition': 2, 'combo': 2},
                  'final_source_transition_cap': .5, 'rollout_steps_per_slot': 128,
                  'sampling_unit': '固定组环境槽保证真实transition份额；组内reset时完整内容均匀，再选来源记录、配置和遭遇',
                  'group_labels_are_policy_inputs': False},
        limitations=['内容标签是可审核的工程分层，不是真实难度、胜率或无限循环证明',
                     '来源完整保留，选择阶段不改组，不用训练结果重新分组',
                     '最终卡组尚未reset/资源准入；冻结前逐项复核，缺组时不自动将份额转给最终卡组'],
        contents=sorted(contents.values(), key=lambda r: (r['split'], r['group'], r['content_id'])))
    return result


if __name__ == '__main__':
    result = build()
    target = ROOT / 'docs/a-path-deck-grouping-proposal.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# A路径逐卡组内容分组台账（提案）', '',
             '来源为静态准入候选，不是冻结训练池。每行是一种完整卡组多重集；升级和副本保留。', '',
             '分类只用卡组内容；来源阶段和历史划分不参与内容分类。完整来源ID、关联组及字段见a-path-deck-grouping-proposal.json。', '']
    for split in ('train_candidate', 'development'):
        lines += ['## ' + ('训练候选' if split == 'train_candidate' else '历史开发侧'), '']
        for group, label in LABELS.items():
            lines += ['### ' + label, '', '| 内容ID | 张数 | 起始骨架 | 已识别配合/组合链 | 完整牌组 |', '|---|---:|---:|---|---|']
            for row in result['contents']:
                if row['split'] != split or row['group'] != group:
                    continue
                cards = '；'.join(f'{name}×{count}' for name, count in row['composition'].items())
                reasons = '、'.join([*row['families'], *row['engines']]) or '未触发登记配合规则'
                if row['resource_dense']:
                    reasons += '；抽牌/能量密集'
                lines.append(f"| {row['content_id'][:12]} | {row['card_count']} | {row['base_fraction']:.1%} | {reasons} | {cards} |")
            lines.append('')
    (ROOT / 'docs/a-path-deck-grouping-ledger.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2))
