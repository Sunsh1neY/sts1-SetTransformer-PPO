"""从实际编码契约生成逐维审计附录；只写审计文档。"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sts.env.entities import CONTRACT, card_features, FEATURE_DIMS

numeric = [
    "升级次数；Searing Blow未来多次升级仍需验数值边界",
    "实例战斗基础费用c.cost；Blood for Blood/Corruption可能改写，非印刷费用",
    "手牌c.costForTurn；非手牌填0且cost_known=false，不等于免费",
    "卡牌伤害基值；Rampage含实例增伤、Body Slam取当前格挡；不是最终扣血",
    "当前格挡预览；受敏捷/脆弱修正，Entrench专用分支取当前格挡",
    "格挡修正前基值；Entrench同样取当前格挡",
    "依卡名解释的效果参数；如Bash易伤、Pommel Strike抽牌、Combust伤害；不是统一效果字典",
    "攻击段数；非攻击也默认1，不可当成必定攻击",
    "Rampage实例累计增伤；其他当前牌填0，不是所有增伤总和",
    "按卡名和是否升级查得的印刷费用；可含X/不可打出的负哨兵",
    "当前手牌有效支付费用；非手牌填0；尚不能作为未来Whirlwind的X消耗快照",
]
flags = ["手牌当前费用已知", "全体敌人效果标志（当前具名导出）", "回合末未打出会虚无耗尽", "固有打出耗尽属性", "一次免费标记", "实例保留标记", "是否属于Strike类别；Perfected Strike未来计数使用", "固有耗尽或Corruption使技能耗尽；不含未来所有自动打出语境", "有效支付费用是否已知"]
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
    ('cost_scope', ['UNKNOWN','COMBAT','TURN','POWER','ONCE'], '未知/战斗基础/本回合改费/Corruption/一次免费；单标签优先级，非完整多效果栈'),
    ('region', CONTRACT['regions'], '手牌/抽牌堆/弃牌堆/消耗堆/结算中/生成候选区'),
]:
    for choice in choices:
        add(f'{key}={choice}', label, 'one-hot')
assert len(rows) == FEATURE_DIMS['CARD'] == 122
# 用实际card_features检查逐个分类值和数值顺序，不只检查JSON维数。
from sts.env.selection import CARD_FIELDS
card = {k: False for k in CARD_FIELDS}
card.update(name='Bash', card_id=1, card_type='ATTACK', target_kind='ENEMY', cost_kind='ENERGY', cost_scope='COMBAT', damage_by_target=[0]*5)
for i, (key, scale) in enumerate(CONTRACT['card_numeric_scales'].items()):
    card[key] = scale * (i + 1)
for key in CONTRACT['card_boolean_fields']:
    card[key] = True
encoded = card_features(card, 'hand')
assert encoded[:11] == list(range(1, 12)) and encoded[11:20] == [1.0]*9
assert [i for i in range(20,122) if encoded[i]] == [21,101,107,108,112,116]
path = ROOT / 'docs/card-token-dimensions.md'
path.write_text('# 卡牌token逐维字典\n\n2026-09-12；由 `scripts/audit-card-token.py` 从当前契约生成并对拍实际 `card_features`。索引从0开始；数值只除以尺度，不裁剪到[0,1]。所有122维为float32。身份是卡牌种类，不是隐藏实例ID。\n\n| 索引 | 字段/类别 | 含义 | 编码 |\n|---|---|---|---|\n' + ''.join(f'| {i} | `{n}` | {m} | {e} |\n' for i,n,m,e in rows), encoding='utf-8')
print('122维顺序与实际编码对拍通过；写入docs/card-token-dimensions.md')
