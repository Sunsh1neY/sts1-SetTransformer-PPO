# 卡牌token逐维字典

2026-09-12；由 `scripts/audit-card-token.py` 从当前契约生成并对拍实际 `card_features`。索引从0开始；数值只除以尺度，不裁剪到[0,1]。所有122维为float32。身份是卡牌种类，不是隐藏实例ID。

| 索引 | 字段/类别 | 含义 | 编码 |
|---|---|---|---|
| 0 | `upgrade_count` | 升级次数；Searing Blow未来多次升级仍需验数值边界 | 原值/5 |
| 1 | `base_cost` | 实例战斗基础费用c.cost；Blood for Blood/Corruption可能改写，非印刷费用 | 原值/4 |
| 2 | `cost` | 手牌c.costForTurn；非手牌填0且cost_known=false，不等于免费 | 原值/4 |
| 3 | `damage` | 卡牌伤害基值；Rampage含实例增伤、Body Slam取当前格挡；不是最终扣血 | 原值/50 |
| 4 | `block` | 当前格挡预览；受敏捷/脆弱修正，Entrench专用分支取当前格挡 | 原值/50 |
| 5 | `base_block` | 格挡修正前基值；Entrench同样取当前格挡 | 原值/50 |
| 6 | `magic` | 依卡名解释的效果参数；如Bash易伤、Pommel Strike抽牌、Combust伤害；不是统一效果字典 | 原值/10 |
| 7 | `hits` | 攻击段数；非攻击也默认1，不可当成必定攻击 | 原值/5 |
| 8 | `combat_damage_bonus` | Rampage实例累计增伤；其他当前牌填0，不是所有增伤总和 | 原值/50 |
| 9 | `printed_cost` | 按卡名和是否升级查得的印刷费用；可含X/不可打出的负哨兵 | 原值/4 |
| 10 | `effective_cost` | 当前手牌有效支付费用；非手牌填0；尚不能作为未来Whirlwind的X消耗快照 | 原值/4 |
| 11 | `cost_known` | 手牌当前费用已知 | false=0，true=1 |
| 12 | `all_enemies` | 全体敌人效果标志（当前具名导出） | false=0，true=1 |
| 13 | `ethereal` | 回合末未打出会虚无耗尽 | false=0，true=1 |
| 14 | `exhaust` | 固有打出耗尽属性 | false=0，true=1 |
| 15 | `free_to_play_once` | 一次免费标记 | false=0，true=1 |
| 16 | `retain` | 实例保留标记 | false=0，true=1 |
| 17 | `is_strike` | 是否属于Strike类别；Perfected Strike未来计数使用 | false=0，true=1 |
| 18 | `effective_exhaust` | 固有耗尽或Corruption使技能耗尽；不含未来所有自动打出语境 | false=0，true=1 |
| 19 | `effective_cost_known` | 有效支付费用是否已知 | false=0，true=1 |
| 20 | `card_id=0` | 保留0；当前合法卡不使用，也不代表padding或未知卡 | 身份one-hot |
| 21 | `card_id=1` | Bash | 身份one-hot |
| 22 | `card_id=2` | Defend_R | 身份one-hot |
| 23 | `card_id=3` | Strike_R | 身份one-hot |
| 24 | `card_id=4` | Battle Trance | 身份one-hot |
| 25 | `card_id=5` | Bludgeon | 身份one-hot |
| 26 | `card_id=6` | Body Slam | 身份one-hot |
| 27 | `card_id=7` | Carnage | 身份one-hot |
| 28 | `card_id=8` | Cleave | 身份one-hot |
| 29 | `card_id=9` | Clothesline | 身份one-hot |
| 30 | `card_id=10` | Demon Form | 身份one-hot |
| 31 | `card_id=11` | Dropkick | 身份one-hot |
| 32 | `card_id=12` | Entrench | 身份one-hot |
| 33 | `card_id=13` | Feel No Pain | 身份one-hot |
| 34 | `card_id=14` | Flame Barrier | 身份one-hot |
| 35 | `card_id=15` | Flex | 身份one-hot |
| 36 | `card_id=16` | Ghostly Armor | 身份one-hot |
| 37 | `card_id=17` | Heavy Blade | 身份one-hot |
| 38 | `card_id=18` | Immolate | 身份one-hot |
| 39 | `card_id=19` | Impervious | 身份one-hot |
| 40 | `card_id=20` | Inflame | 身份one-hot |
| 41 | `card_id=21` | Metallicize | 身份one-hot |
| 42 | `card_id=22` | Pommel Strike | 身份one-hot |
| 43 | `card_id=23` | Power Through | 身份one-hot |
| 44 | `card_id=24` | Pummel | 身份one-hot |
| 45 | `card_id=25` | Rage | 身份one-hot |
| 46 | `card_id=26` | Reckless Charge | 身份one-hot |
| 47 | `card_id=27` | Seeing Red | 身份one-hot |
| 48 | `card_id=28` | Sentinel | 身份one-hot |
| 49 | `card_id=29` | Shrug It Off | 身份one-hot |
| 50 | `card_id=30` | Spot Weakness | 身份one-hot |
| 51 | `card_id=31` | Thunderclap | 身份one-hot |
| 52 | `card_id=32` | True Grit | 身份one-hot |
| 53 | `card_id=33` | Twin Strike | 身份one-hot |
| 54 | `card_id=34` | Uppercut | 身份one-hot |
| 55 | `card_id=35` | Wild Strike | 身份one-hot |
| 56 | `card_id=36` | AscendersBane | 身份one-hot |
| 57 | `card_id=37` | Wound | 身份one-hot |
| 58 | `card_id=38` | Dazed | 身份one-hot |
| 59 | `card_id=39` | Burn | 身份one-hot |
| 60 | `card_id=40` | Slimed | 身份one-hot |
| 61 | `card_id=41` | Anger | 身份one-hot |
| 62 | `card_id=42` | Armaments | 身份one-hot |
| 63 | `card_id=43` | Barricade | 身份one-hot |
| 64 | `card_id=44` | Berserk | 身份one-hot |
| 65 | `card_id=45` | Blood for Blood | 身份one-hot |
| 66 | `card_id=46` | Bloodletting | 身份one-hot |
| 67 | `card_id=47` | Brutality | 身份one-hot |
| 68 | `card_id=48` | Burning Pact | 身份one-hot |
| 69 | `card_id=49` | Clash | 身份one-hot |
| 70 | `card_id=50` | Combust | 身份one-hot |
| 71 | `card_id=51` | Corruption | 身份one-hot |
| 72 | `card_id=52` | Dark Embrace | 身份one-hot |
| 73 | `card_id=53` | Disarm | 身份one-hot |
| 74 | `card_id=54` | Double Tap | 身份one-hot |
| 75 | `card_id=55` | Dual Wield | 身份one-hot |
| 76 | `card_id=56` | Evolve | 身份one-hot |
| 77 | `card_id=57` | Exhume | 身份one-hot |
| 78 | `card_id=58` | Feed | 身份one-hot |
| 79 | `card_id=59` | Fiend Fire | 身份one-hot |
| 80 | `card_id=60` | Fire Breathing | 身份one-hot |
| 81 | `card_id=61` | Havoc | 身份one-hot |
| 82 | `card_id=62` | Headbutt | 身份one-hot |
| 83 | `card_id=63` | Hemokinesis | 身份one-hot |
| 84 | `card_id=64` | Infernal Blade | 身份one-hot |
| 85 | `card_id=65` | Intimidate | 身份one-hot |
| 86 | `card_id=66` | Iron Wave | 身份one-hot |
| 87 | `card_id=67` | Juggernaut | 身份one-hot |
| 88 | `card_id=68` | Limit Break | 身份one-hot |
| 89 | `card_id=69` | Offering | 身份one-hot |
| 90 | `card_id=70` | Perfected Strike | 身份one-hot |
| 91 | `card_id=71` | Rampage | 身份one-hot |
| 92 | `card_id=72` | Reaper | 身份one-hot |
| 93 | `card_id=73` | Rupture | 身份one-hot |
| 94 | `card_id=74` | Searing Blow | 身份one-hot |
| 95 | `card_id=75` | Second Wind | 身份one-hot |
| 96 | `card_id=76` | Sever Soul | 身份one-hot |
| 97 | `card_id=77` | Shockwave | 身份one-hot |
| 98 | `card_id=78` | Sword Boomerang | 身份one-hot |
| 99 | `card_id=79` | Warcry | 身份one-hot |
| 100 | `card_id=80` | Whirlwind | 身份one-hot |
| 101 | `card_type=ATTACK` | 攻击/技能/能力/状态/诅咒分类 | one-hot |
| 102 | `card_type=SKILL` | 攻击/技能/能力/状态/诅咒分类 | one-hot |
| 103 | `card_type=POWER` | 攻击/技能/能力/状态/诅咒分类 | one-hot |
| 104 | `card_type=STATUS` | 攻击/技能/能力/状态/诅咒分类 | one-hot |
| 105 | `card_type=CURSE` | 攻击/技能/能力/状态/诅咒分类 | one-hot |
| 106 | `target_kind=NO_TARGET` | 是否由玩家选敌人；无目标也可以是AOE或随机目标 | one-hot |
| 107 | `target_kind=ENEMY` | 是否由玩家选敌人；无目标也可以是AOE或随机目标 | one-hot |
| 108 | `cost_kind=ENERGY` | 普通能量/X费用/不可打出 | one-hot |
| 109 | `cost_kind=X` | 普通能量/X费用/不可打出 | one-hot |
| 110 | `cost_kind=UNPLAYABLE` | 普通能量/X费用/不可打出 | one-hot |
| 111 | `cost_scope=UNKNOWN` | 未知/战斗基础/本回合改费/Corruption/一次免费；单标签优先级，非完整多效果栈 | one-hot |
| 112 | `cost_scope=COMBAT` | 未知/战斗基础/本回合改费/Corruption/一次免费；单标签优先级，非完整多效果栈 | one-hot |
| 113 | `cost_scope=TURN` | 未知/战斗基础/本回合改费/Corruption/一次免费；单标签优先级，非完整多效果栈 | one-hot |
| 114 | `cost_scope=POWER` | 未知/战斗基础/本回合改费/Corruption/一次免费；单标签优先级，非完整多效果栈 | one-hot |
| 115 | `cost_scope=ONCE` | 未知/战斗基础/本回合改费/Corruption/一次免费；单标签优先级，非完整多效果栈 | one-hot |
| 116 | `region=hand` | 手牌/抽牌堆/弃牌堆/消耗堆/结算中/生成候选区 | one-hot |
| 117 | `region=draw_pile` | 手牌/抽牌堆/弃牌堆/消耗堆/结算中/生成候选区 | one-hot |
| 118 | `region=discard_pile` | 手牌/抽牌堆/弃牌堆/消耗堆/结算中/生成候选区 | one-hot |
| 119 | `region=exhaust_pile` | 手牌/抽牌堆/弃牌堆/消耗堆/结算中/生成候选区 | one-hot |
| 120 | `region=resolving` | 手牌/抽牌堆/弃牌堆/消耗堆/结算中/生成候选区 | one-hot |
| 121 | `region=offer` | 手牌/抽牌堆/弃牌堆/消耗堆/结算中/生成候选区 | one-hot |
