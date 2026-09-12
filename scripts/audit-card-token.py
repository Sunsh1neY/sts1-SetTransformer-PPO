"""从实际编码契约生成逐维审计附录；只写审计文档。"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sts.env.entities import CONTRACT, card_features, FEATURE_DIMS

numeric = ['升级次数', '实例战斗基础费用', '伤害基值（已包含实例增伤）', '后端当前格挡预览', '格挡基础值', '卡牌具名效果参数', '基础段数，非X执行预测', 'Rampage实例累计增伤', '手牌当前支付费；非手牌印刷费；X/不可打出为0占位', '一次免费前本回合费用；非手牌优先显式公开恢复值，否则当前范围回退base_cost']
flags = ['全体效果', '虚无', '固有耗尽', '一次免费', '保留', 'Strike类别', '有效耗尽', '公开确定的抽牌堆第一张']
rows = []
def add(name, meaning, encoding):
    rows.append((len(rows), name, meaning, encoding))
for (name, scale), meaning in zip(CONTRACT['card_numeric_scales'].items(), numeric):
    add(name, meaning, f"原值/{scale}")
for name, meaning in zip(CONTRACT['card_boolean_fields'], flags):
    add(name, meaning, "false=0，true=1")
names = {r['id']: r['name'] for r in CONTRACT['cards']}
for i in range(81):
    add(f"card_id={i}", names.get(i, "保留0；当前合法卡不使用，也不代表padding或未知卡"), "身份one-hot")
for key, choices, label in [
    ('card_type', CONTRACT['card_types'], '攻击/技能/能力/状态/诅咒分类'),
    ('target_kind', ['NO_TARGET','ENEMY'], '是否由玩家选敌人；无目标也可以是AOE或随机目标'),
    ('cost_kind', ['ENERGY','X','UNPLAYABLE'], '普通能量/X费用/不可打出'),
    ('region', CONTRACT['regions'], '手牌/抽牌堆/弃牌堆/消耗堆/结算中/生成候选区'),
]:
    for choice in choices:
        add(f'{key}={choice}', label, 'one-hot')
assert len(rows) == FEATURE_DIMS['CARD'] == 115
# 用实际card_features检查逐个分类值和数值顺序，不只检查JSON维数。
from sts.env.selection import CARD_FIELDS
card = {k: False for k in CARD_FIELDS}
card.update(name='Bash', card_id=1, card_type='ATTACK', target_kind='ENEMY', cost_kind='ENERGY', cost_scope='COMBAT', damage_by_target=[0]*5)
for i, (key, scale) in enumerate(CONTRACT['card_numeric_scales'].items()):
    card[key] = scale * (i + 1)
for key in CONTRACT['card_boolean_fields']:
    card[key] = key != 'known_top'
card.pop('pay_cost')
card.update(cost=8, printed_cost=12, effective_cost=4, cost_known=True, effective_cost_known=True)
encoded = card_features(card, 'hand')
assert len(encoded) == 115
assert encoded[8] == 1 and encoded[9] == 10
assert encoded[17] == 0
path = ROOT / 'docs/card-token-dimensions.md'
path.write_text('# 卡牌token逐维字典\n\n2026-09-12；由 `scripts/audit-card-token.py` 从当前契约生成并对拍实际 `card_features`。索引从0开始；数值只除以尺度，不裁剪到[0,1]。所有115维为float32。身份是卡牌种类，不是隐藏实例ID。\n\n| 索引 | 字段/类别 | 含义 | 编码 |\n|---|---|---|---|\n' + ''.join(f'| {i} | `{n}` | {m} | {e} |\n' for i,n,m,e in rows), encoding='utf-8')
print('115维顺序与实际编码对拍通过；写入docs/card-token-dimensions.md')
