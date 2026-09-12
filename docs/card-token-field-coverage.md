> 2026-09-13最终收尾：CARD仍115维，统一接口v4/模型v4。同一公开结算上下文进入动作头与价值头；价值端按有效候选均值汇总，空候选取零。B05真实路径证明字段来源，尚无完整输入碰撞证明。+100保留资源异常，不作为升级终点。最终证据以docs/card-token-final-review.md为准，下面较早阶段数字保留历史身份。

# 卡牌 token 全字段反向覆盖审计

日期：2026-09-13。对象是当前统一实体输入 v3 的 CARD token，不是64维投影后的隐表示。编码入口为 sts/env/entities.py:61-79，模型投影和动作头为 sts/models/entities.py:50-110。

## 1. 结论先行

CARD token 的实际宽度是 115，全部为 float32。数值字段只做除法缩放，不做 [0,1] 裁剪；one-hot 维度只表达有效类别，不按类别编号缩放。卡牌身份不是隐藏实例 ID，区域、动态数值和候选引用共同区分同名重复牌。

当前反向覆盖结论：

- 75 类 Ironclad 的150个基础/升级版本，以及5张辅助牌，都有稳定身份和真实 reset/encode 入口。
- 当前实例动态状态中，Rampage 的累计增伤、Searing Blow 的多次升级、Blood for Blood 的战斗费用、Corruption 的有效耗尽、Headbutt/Warcry 的已知顶牌均有字段或区域/全局状态承载。
- target damage preview 原始字段仍为兼容输入的一部分，但没有进入 115 维，也没有进入统一模型动作评分。
- card_id、card_type、target_kind、cost_kind、is_strike、all_enemies、ethereal、exhaust 等不少字段可由卡牌身份和升级静态字典推出；保留它们是模型便利特征，不是信息缺口。
- 当前发现的反向问题：AscendersBane 的 cost_kind 错误；Searing Blow +100 的升级边界在后端过滤中错误；自动/重复打出暂停上下文不在 CARD/PLAYER_GLOBAL 输入；消耗堆跨回合临时费用恢复是后端状态缺陷。详细问题见逐卡表和合并评审。

## 2. 实际编码顺序

| 索引范围 | 内容 | 维数 |
|---|---|---:|
| 0–9 | upgrade_count、base_cost、damage、block、base_block、magic、hits、combat_damage_bonus、pay_cost、recovery_cost | 10 |
| 10–17 | all_enemies、ethereal、exhaust、free_to_play_once、retain、is_strike、effective_exhaust、known_top | 8 |
| 18–98 | card_id=0..80 的身份 one-hot | 81 |
| 99–103 | card_type=ATTACK/SKILL/POWER/STATUS/CURSE | 5 |
| 104–105 | target_kind=NO_TARGET/ENEMY | 2 |
| 106–108 | cost_kind=ENERGY/X/UNPLAYABLE | 3 |
| 109–114 | region=hand/draw_pile/discard_pile/exhaust_pile/resolving/offer | 6 |
| 合计 | CARD | 115 |

所有行的归一化结果最后转为 numpy.float32；没有隐式把整数类别塞入数值字段。

## 3. 数值字段（0–9）

| 索引 | 字段、类型、公式 | 精确定义、零值与不适用 | 来源、变更和适用区域 | 对应机制与可达例子 | 可推出性、重复/缺陷判断 |
|---:|---|---|---|---|---|
| 0 | upgrade_count；float32；原值/5 | 非负升级次数。0 是未升级或 Searing Blow+0，不是缺失；当前普通卡有效值0/1，Searing可到100；没有通用 N/A | cardRow 的 getUpgradeCount；升级、Armaments、Apotheosis 等改变；六个牌区都可带实例值 | 真实 reset/encode 150/150；Searing +0/+1/+2/+5/+100 分别0/1/2/5/100 | 普通卡可由 ID+升级静态推出；Searing 是实例递增状态，不能删掉。/5 只是缩放，+100 的 token 值20.0合法 |
| 1 | base_cost；float32；原值/4 | 实例战斗基础费用。0 可以是真实0费或动态降至0；-1 是 X，-2/-3 是不可打出费用原值，不是 padding | cardRow 的 c.cost；Blood for Blood、Corruption、临时/战斗改费和升级改变；所有区域 | BFB 自伤后4→3→0；Whirlwind=-1；Wound=-2；AscendersBane=-3 | 不可只看数值，必须和 cost_kind 联读。当前 AscendersBane 的 cost_kind 错误会污染 PC |
| 2 | damage；float32；原值/50 | 当前 cardRow 的基础/实例伤害值；0 表示本次卡牌没有基础伤害，或 Body Slam 当前 block为0；不表示目标预览 | cardRow 按卡牌、升级、实例成长和公开计数计算；六区 | Rampage D=8+CB；Perfected Strike 含当前 Strike 计数；Searing+100 D=5362；Body Slam随玩家block | 目标伤害、护甲和每段实际结果不放入该字段；与 G/敌人 token 联合决定。Rampage 与 CB有可解释冗余 |
| 3 | block；float32；原值/50 | 后端计算后的卡牌格挡预览。0 表示无格挡效果或动态值为0；不表示玩家当前 block为0 | cardRow 的 resolvedBlock；受 Dexterity/Frail等公开状态影响；所有区域 | Defend B5/B8、Iron Wave B5/B7、Power Through B15/B20；真实 Dex 场景可达 | 不是实际事件结算；保留是用户批准的后端预览便利特征。Entrench使用当前block参数而非2倍结果 |
| 4 | base_block；float32；原值/50 | 卡牌格挡原始参数。0 表示无原始格挡；Entrench 的参数是当前玩家block，不是缺失 | cardRow 的 block 变量；升级、玩家block和牌面机制；所有区域 | Defend基础5、升级8；Entrench在玩家block=10时 BB=10 | 对普通牌可由 ID+升级推出；保留可区分后端 preview 与牌面参数 |
| 5 | magic；float32；原值/10 | 卡牌具名主参数。0 表示该字段没有单一主参数，不代表无所有效果；同一个值按 card_id/upgrade 解读 | cardRow switch；所有区域，出牌后不保存隐藏 queue | Bash Vulnerable2/3、Offering抽3/5、Flame Barrier反伤4/6、Dual Wield复制1/2 | 明确是按卡牌解释的便利特征，不是通用多效果 DSL；对 Offering等多效果不能把 M 当完整效果说明。用户已接受本轮不引入通用多效果编码 |
| 6 | hits；float32；原值/5 | 固定基础段数；默认1。X卡不预测执行次数，Whirlwind当前仍为1占位；0不是当前有效卡牌行 | cardRow switch；升级改变固定段数；所有区域 | Twin Strike=2、Pummel=4/5、Sword Boomerang=3/4、Whirlwind=1占位 | X实际命中由能量和后端处理；与 cost_kind= X 联读。当前0值只属于人工非法编码 |
| 7 | combat_damage_bonus；float32；原值/50 | 当前只表示 Rampage 实例累计增伤；0 表示无成长或非 Rampage，不是隐藏字段 | cardRow 只对 Rampage读 specialData；出牌、复制、双发、跨区改变；所有区域 | Rampage 基础首见0，打出后+5；升级每次+8；Dual Wield复制保留 | 对 Rampage，D 已包含 CB，故可由 D 和静态8部分推出；保留是显式实例语义，禁止模型再把两者相加 |
| 8 | pay_cost；float32；原值/4 | 手牌 ENERGY 为当前支付费用；非手牌 ENERGY 为印刷费用；X/UNPLAYABLE 固定0占位。0可是真实0费，也可仅是类别占位 | sts/env/entities.py:68-70 重算；出牌/费用变化/区域变化时变化 | Infernal Blade生成的普通攻击手牌当前PC=0；Whirlwind和Wound为0；非手牌普通Defend PC=1 | 必须联读 cost_kind 和区域；不是直接复制 raw cost。非手牌不会把隐藏 costForTurn送入 PC |
| 9 | recovery_cost；float32；原值/4 | 本回合费用在一次免费覆盖前的公开值。当前手牌缺省使用 raw cost，非手牌有显式值时使用它，否则回退 base_cost；不能把它误读为目标伤害 | cardRow 在非手牌 c.costForTurn != c.cost 时提供；card_features在 hand 使用当前 raw cost，在非hand使用显式/BC回退；回合结束后后端重置手牌/弃牌/抽牌的 costForTurn | 免费一次夹具：raw cost2/effective0/FP=true时RC=2；Infernal生成牌本回合raw cost0、scope=TURN时RC=0，回合边界后回到base cost | 当前文字对“本回合临时费”和“下回合恢复值”的边界仍容易误读；实际下一回合恢复由实例状态和下一观测显示，不由 RC 单独预测。未来临时费用必须显式验证，不能用回退伪造未知值 |

## 4. 布尔字段（10–17）

| 索引 | 字段、编码 | 精确定义、零值与不适用 | 来源、变更和适用区域 | 对应机制与可达例子 | 可推出性、重复/缺陷判断 |
|---:|---|---|---|---|---|
| 10 | all_enemies；false=0/true=1 | true 表示该牌规则作用于所有敌人；false包括单体、随机目标和非伤害牌；不等于 target_kind | cardRow switch静态生成；六区 | Cleave、Immolate、Reaper、Thunderclap、Whirlwind、Intimidate、Shockwave为true；Bash为false | 可由 ID+升级推出；保留使 AOE 语义显式。random 与 AOE 的差别不能只靠本字段，但 ID已区分 |
| 11 | ethereal；false=0/true=1 | true表示回合末若仍在手牌会自动耗尽；false不表示一定进弃牌堆 | CardInstance::isEthereal；区域/回合边界改变结果 | Carnage、Ghostly Armor、Dazed、AscendersBane为true；Bash为false | 与 exhaust严格分开；Ethereal不是固有 EX。静态可由 ID+升级推出 |
| 12 | exhaust；false=0/true=1 | 卡牌固有打出后耗尽；false可仍因Ethereal、Corruption或外部效果耗尽 | CardInstance::doesExhaust；打出版本和区域 | Feed、Fiend Fire、Pummel、Reaper、Disarm、Exhume、Sentinel等为true；Dazed为false | 与 effective_exhaust 联读；固有属性可由ID+升级推出 |
| 13 | free_to_play_once；false=0/true=1 | 实例的一次免费标志。false不是支付费用0；true也不表示X实际支付 | CardInstance::freeToPlayOnce；按效果/复制/出牌清除；六区 | 当前75卡及8遗物真实范围只验证false；true需Forethought/Mummified Hand等范围外路径或人工构造 | 字段是动态保留位；当前真实true不可达/未验证，不能把自动播放 item.freeToPlay 偷换成此字段 |
| 14 | retain；false=0/true=1 | 实例在回合末保留；false走普通 discard/ethereal 处理；不表示牌面自带保留 | CardInstance::retain；外部效果或未来牌可改；六区 | 当前75 Ironclad牌没有已核验的真实 retain=true 路径；false在所有R150/RAUX中可达 | current范围只证明false；不能因字段存在宣称保留机制已接通。需要范围外牌/遗物才补行为 |
| 15 | is_strike；false=0/true=1 | STS Strike计数类别，不是名称字符串包含判断；false为其他牌 | CardInstance::isStrikeCard；ID静态；所有区域 | Strike_R、Perfected Strike、Pommel Strike、Twin Strike、Wild Strike为true；Bash为false | 可由ID推出；Perfected Strike需要它联合区域/实体集合。保留可减少模型从ID学规则的负担 |
| 16 | effective_exhaust；false=0/true=1 | 当前实际打出会耗尽，包括固有EX或 Corruption 作用于 Skill；Ethereal另由ET表达 | cardRow 固有 EX 或玩家 Corruption；区域和玩家状态变化 | 普通 Defend false；Corruption激活后手牌Defend true；Limit Break+ false | 不能用 exhaust替代；当前字段正确区分静态和条件性耗尽 |
| 17 | known_top；false=0/true=1 | true只表示玩家由公开Headbutt/Warcry事件知道它是抽牌堆第一张；false表示未知或非顶牌；不表示该卡一定不在牌堆 | CardManager knownTopId转bool；选顶、抽走、洗牌、随机插入清除；只允许 draw_pile | Headbutt/Warcry后1张true，抽走后全false；R150普通场景全false | 不能由 card_id/区域推出；是公开记忆位。当前真实路径已验证，不能读取隐藏牌序 |

## 5. 身份 one-hot（18–98）

18 是保留零位。有效卡身份从19开始，映射关系严格按 unified-entity-contract.json 的 cards 顺序；每个有效卡 token恰有一个身份位为1，其他身份位为0。身份位0不是 padding：padding由 entity_valid 独立表达。R150/RAUX已实际覆盖全部1–80身份。

| 索引 | one-hot值 | 语义与可达依据 | 反向用途与风险 |
|---:|---|---|---|
| 18 | card_id=0 | 保留值；当前合法卡不使用，不能代表未知卡 | 全零保留位；不能把未知卡静默映射到此位 |
| 19 | card_id=1 / Bash | Bash各版本真实 reset/encode | ID恢复固定伤害/减益；与UC区分升级 |
| 20 | card_id=2 / Defend_R | Defend_R各版本真实 reset/encode | ID恢复技能/格挡语义 |
| 21 | card_id=3 / Strike_R | Strike_R各版本真实 reset/encode | ID恢复Strike类别和攻击语义 |
| 22 | card_id=4 / Battle Trance | R150 | ID恢复抽牌/No Draw固定效果 |
| 23 | card_id=5 / Bludgeon | R150 | ID恢复高伤害攻击 |
| 24 | card_id=6 / Body Slam | R150 | ID恢复动态 D=player block |
| 25 | card_id=7 / Carnage | R150 | ID恢复 Ethereal攻击 |
| 26 | card_id=8 / Cleave | R150 | ID恢复 AOE攻击 |
| 27 | card_id=9 / Clothesline | R150 | ID恢复 Weak攻击 |
| 28 | card_id=10 / Demon Form | R150 | ID恢复回合力量能力 |
| 29 | card_id=11 / Dropkick | R150 | ID恢复 Vulnerable条件效果 |
| 30 | card_id=12 / Entrench | R150 | ID恢复当前block翻倍 |
| 31 | card_id=13 / Feel No Pain | R150 | ID恢复耗尽触发block |
| 32 | card_id=14 / Flame Barrier | R150 | ID恢复block/反伤双效果 |
| 33 | card_id=15 / Flex | R150 | ID恢复Strength与Lose Strength |
| 34 | card_id=16 / Ghostly Armor | R150 | ID恢复Ethereal格挡 |
| 35 | card_id=17 / Heavy Blade | R150 | ID恢复Strength倍率M |
| 36 | card_id=18 / Immolate | R150 | ID恢复AOE与Burn生成 |
| 37 | card_id=19 / Impervious | R150 | ID恢复高格挡耗尽 |
| 38 | card_id=20 / Inflame | R150 | ID恢复力量增量 |
| 39 | card_id=21 / Metallicize | R150 | ID恢复回合末格挡 |
| 40 | card_id=22 / Pommel Strike | R150 | ID恢复Strike/抽牌 |
| 41 | card_id=23 / Power Through | R150 | ID恢复格挡/Wound生成 |
| 42 | card_id=24 / Pummel | R150 | ID恢复固定多段耗尽；生成跨回合受B01 |
| 43 | card_id=25 / Rage | R150 | ID恢复每Attack格挡 |
| 44 | card_id=26 / Reckless Charge | R150 | ID恢复Dazed生成 |
| 45 | card_id=27 / Seeing Red | R150 | ID恢复能量/耗尽 |
| 46 | card_id=28 / Sentinel | R150 | ID恢复被耗尽能量 |
| 47 | card_id=29 / Shrug It Off | R150 | ID恢复格挡/抽牌 |
| 48 | card_id=30 / Spot Weakness | R150 | ID恢复目标意图条件 |
| 49 | card_id=31 / Thunderclap | R150 | ID恢复AOE/易伤 |
| 50 | card_id=32 / True Grit | R150 | ID恢复随机或单选耗尽 |
| 51 | card_id=33 / Twin Strike | R150 | ID恢复Strike固定双段 |
| 52 | card_id=34 / Uppercut | R150 | ID恢复双减益；M按ID解读 |
| 53 | card_id=35 / Wild Strike | R150 | ID恢复Strike/Wound生成 |
| 54 | card_id=36 / AscendersBane | RAUX | 当前 cost_kind错误，见BLOCK-B04 |
| 55 | card_id=37 / Wound | RAUX | ID区分Status/UNPLAYABLE；Havoc丢失见B02 |
| 56 | card_id=38 / Dazed | RAUX | ID区分Status/ET/UNPLAYABLE |
| 57 | card_id=39 / Burn | RAUX | ID区分Status/回合末伤害 |
| 58 | card_id=40 / Slimed | RAUX | ID区分可打出Status/EX |
| 59 | card_id=41 / Anger | R150 | ID恢复生成同升级Anger |
| 60 | card_id=42 / Armaments | R150 | ID恢复单选/全手牌升级 |
| 61 | card_id=43 / Barricade | R150 | ID恢复PLAYER_GLOBAL布尔状态 |
| 62 | card_id=44 / Berserk | R150 | ID恢复脆弱/能量能力 |
| 63 | card_id=45 / Blood for Blood | R150 | ID恢复每HP loss降费 |
| 64 | card_id=46 / Bloodletting | R150 | ID恢复自伤/能量 |
| 65 | card_id=47 / Brutality | R150 | ID恢复回合自伤/升级Innate |
| 66 | card_id=48 / Burning Pact | R150 | ID恢复单选耗尽/抽牌 |
| 67 | card_id=49 / Clash | R150 | ID恢复全Attack合法性 |
| 68 | card_id=50 / Combust | R150 | ID恢复回合末AOE与自伤 |
| 69 | card_id=51 / Corruption | R150 | ID恢复技能费用/耗尽修改 |
| 70 | card_id=52 / Dark Embrace | R150 | ID恢复耗尽抽牌 |
| 71 | card_id=53 / Disarm | R150 | ID恢复目标减力/耗尽 |
| 72 | card_id=54 / Double Tap | R150 | ID恢复重复攻击及队列风险 |
| 73 | card_id=55 / Dual Wield | R150 | ID恢复复制候选/数量 |
| 74 | card_id=56 / Evolve | R150 | ID恢复Status抽牌 |
| 75 | card_id=57 / Exhume | R150 | ID恢复消耗堆单选 |
| 76 | card_id=58 / Feed | R150 | ID恢复致死maxHP/耗尽 |
| 77 | card_id=59 / Fiend Fire | R150 | ID恢复手牌快照耗尽/多段 |
| 78 | card_id=60 / Fire Breathing | R150 | ID恢复Status/Curse抽取触发 |
| 79 | card_id=61 / Havoc | R150 | ID恢复顶牌自动打出；B02/B05 |
| 80 | card_id=62 / Headbutt | R150 | ID恢复攻击后弃牌单选/KT |
| 81 | card_id=63 / Hemokinesis | R150 | ID恢复自伤/攻击 |
| 82 | card_id=64 / Infernal Blade | R150 | ID恢复随机攻击生成；B01关联 |
| 83 | card_id=65 / Intimidate | R150 | ID恢复AOE Weak耗尽 |
| 84 | card_id=66 / Iron Wave | R150 | ID恢复双效果 |
| 85 | card_id=67 / Juggernaut | R150 | ID恢复格挡触发随机攻击 |
| 86 | card_id=68 / Limit Break | R150 | ID恢复Strength倍增及版本耗尽差异 |
| 87 | card_id=69 / Offering | R150 | ID恢复自伤/能量/抽牌三效果 |
| 88 | card_id=70 / Perfected Strike | R150 | ID恢复Strike计数公式 |
| 89 | card_id=71 / Rampage | R150 | ID恢复实例CB增长 |
| 90 | card_id=72 / Reaper | R150 | ID恢复AOE/实际治疗 |
| 91 | card_id=73 / Rupture | R150 | ID恢复卡牌自伤触发力量 |
| 92 | card_id=74 / Searing Blow | R150 | ID恢复UC多次升级公式；+100边界B03 |
| 93 | card_id=75 / Second Wind | R150 | ID恢复非Attack自动耗尽 |
| 94 | card_id=76 / Sever Soul | R150 | ID恢复非Attack耗尽后攻击 |
| 95 | card_id=77 / Shockwave | R150 | ID恢复AOE双减益耗尽 |
| 96 | card_id=78 / Sword Boomerang | R150 | ID恢复随机多段 |
| 97 | card_id=79 / Warcry | R150 | ID恢复抽牌/置顶单选/KT |
| 98 | card_id=80 / Whirlwind | R150 | ID恢复X/AOE；H=1不代表X=1 |

身份 one-hot 的“其他位为0”是正常类别互斥，不是缺失。任何有效卡在契约外都应拒绝，不能映射18。

## 6. 类别 one-hot（99–108）

| 索引 | 字段/有效值 | 零值、默认和不适用 | 来源与可达例子 | 可推出性与风险 |
|---:|---|---|---|---|
| 99 | card_type=ATTACK | 0表示该卡不是Attack | Bash、Strike_R、Searing；R150 | 由ID+升级静态推出；用于Clash/Second Wind/Sever Soul |
| 100 | card_type=SKILL | 0表示不是Skill | Defend_R、Burning Pact、Warcry；R150 | 由ID推出；Corruption依据它改变EE |
| 101 | card_type=POWER | 0表示不是Power | Barricade、Combust、Demon Form；R150 | 由ID推出；能力状态结果在PLAYER_GLOBAL |
| 102 | card_type=STATUS | 0表示不是Status | Wound、Dazed、Burn、Slimed；RAUX | 与CURSE严格区分，供Evolve/Fire Breathing |
| 103 | card_type=CURSE | 0表示不是Curse | AscendersBane；RAUX | 可由ID推出；不是UNPLAYABLE的替代字段 |
| 104 | target_kind=NO_TARGET | 0表示需要玩家选敌人；AOE/random也可为NO_TARGET | Cleave、Reaper、Sword Boomerang、Whirlwind；R150 | 由ID+升级推出；不要把NO_TARGET的动作列0误当敌人0 |
| 105 | target_kind=ENEMY | 0表示玩家不选敌人 | Bash、Feed、Headbutt、Spot Weakness；R150 | 用于生成 PLAY_TARGET 候选和敌人引用；随机目标牌不应误标ENEMY |
| 106 | cost_kind=ENERGY | 0表示不是普通能量类 | Bash、Defend、Slimed；主150/RAUX | 由ID+动态cost可大致推出，但必须读取实例；AscendersBane当前错误标此类 |
| 107 | cost_kind=X | 0表示不是X | Whirlwind基础/+1；R150 | 与BC=-1、H占位、能量全量执行联读 |
| 108 | cost_kind=UNPLAYABLE | 0表示不是不可打出 | Wound/Dazed/Burn；RAUX；AscendersBane应属此类 | current cardRow只检查 -2，漏掉 AscendersBane -3，见BLOCK-B04 |

## 7. 区域 one-hot（109–114）

| 索引 | 字段/有效值 | 零值、默认和不适用 | 来源、变更时机和可达例子 | 可推出性与风险 |
|---:|---|---|---|---|
| 109 | region=hand | 0表示卡不在手牌；padding不是hand | C++ cardsInHand；150/150 reset场景、实际出牌后可达 | 与普通 action source 对应；不编码手牌槽号 |
| 110 | region=draw_pile | 0表示不在抽牌堆；未知顺序不是某个位置 | drawPile；150/150及生成Wound/Dazed、Headbutt/Warcry置顶 | 只有 KT 额外表示公开第一张；不能用 token 顺序恢复完整牌序 |
| 111 | region=discard_pile | 0表示不在弃牌堆 | card use/end turn；150/150和Headbutt候选 | 非手牌按公开语义排序；不保留后端位置 |
| 112 | region=exhaust_pile | 0表示不在消耗堆 | 固有EX/Ethereal/选择耗尽；150/150与Exhume候选 | 消耗堆仍是当前实体；B01说明后端动态费用不能因进入此区而被遗忘 |
| 113 | region=resolving | 0表示没有公开暂停中的来源卡 | SELECT_CARD暂停由 observeJson 添加当前来源；True Grit+、Havoc/Headbutt真实路径可达 | 只保留当前公开来源牌，不暴露完整 queue；缺少自动/重复上下文见B05 |
| 114 | region=offer | 0表示不是生成候选区 | 当前真实扩展后端不产 offers；tests/test_unified_entities.py:230-248仅为接口夹具 | 词表保留给未来药水/Discovery；不应当作当前75卡运行证据，且 offer 机制需另建版本 |

## 8. 原始公开行中存在但不进入115维的字段

当前兼容适配器仍接收旧环境完整卡牌行。下列字段被 CARD_FIELDS 严格校验或用于兼容排序，但 card_features 不放进115维：

| 原始字段 | 当前作用 | 为什么不进入新模型 | 审计结论 |
|---|---|---|---|
| cost | 手牌 raw costForTurn；非手牌为0占位 | 新模型使用 PC/RC/BC 和类别 | 当前语义可用；跨回合状态仍由后端维护 |
| cost_known | 手外即时费用未知标记 | PC按 v3 约定直接表达当前动作展示费 | 不得把它重新拼进模型 |
| printed_cost | ID+升级可恢复的印刷费用 | PC非手牌使用它；模型不需要独立列 | 作为兼容原始字段保留 |
| effective_cost | 手牌当前有效费用 | PC已经承载普通能源支付费，X/UNPLAYABLE由类别区分 | 不进入 tensor，避免重复解释 |
| effective_cost_known | 旧行可见性位 | v3删除独立 known 列；当前 normalize 仍要求旧完整行 | 这是兼容输入，不是115维字段 |
| cost_scope | 旧行费用作用范围 | v3不采用单一 scope 列 | 当前 raw 仍有，模型不读；与 RC/BC语义不得冲突 |
| damage_by_target | 五目标原始伤害预览 | 用户裁定从模型输入/评分删除 | tests/test_unified_entities.py:111-124验证改变该字段不改变模型输出 |

上述“原始字段不进模型”不是静默丢弃：它们要么由ID/新字段替代，要么属于用户明确删除的目标预览。若将兼容适配器改成只输出v3最小行，当前 normalize/card_fields 也必须同步，否则会发生 schema 运行时拒绝。

## 9. 字段可达性与信息安全总结

| 类别 | 当前证据 | 结论 |
|---|---|---|
| 150个主版本身份/基础字段 | R150真实 reset/encode；F938 | 入口和字段布局覆盖通过，不等于每卡行为穷尽 |
| 五张辅助牌身份/基础字段 | RAUX真实 reset/encode | 词表/编码覆盖；AscendersBane cost_kind错误 |
| 数值边界 | Searing +0/+1/+2/+5/+100、X负费用、动态Rampage/BFB | 除 B01/B03 所述后端状态问题外，float32缩放不裁剪；大于1不是错误 |
| 布尔 true/false | AE/ET/EX/ST/EE/KT真实路径；FP/RT当前只真实false | FP/RT true属于当前范围未达/未验证，不得静默推断 |
| 类别有效值 | ATTACK/SKILL/POWER主150；STATUS/CURSE及UNPLAYABLE RAUX；ENERGY/X主150 | cost_kind 的 AscendersBane 例外必须修复 |
| 区域 | hand/draw/discard/exhaust真实；resolving真实选择；offer仅夹具 | offer属于未来范围；resolving不等于完整队列恢复 |
| 隐藏信息 | hidden fields rejected；route/decision_id不进tensor；无位置编码、置换测试通过 | 没有发现槽号、实例ID、seed或隐藏牌序直接进入模型 |
| 输入无法独立推断的机制 | 固定多效果、随机目标、X次数、实际治疗、队列结果 | 由ID+外部实体+环境结算表达；不把这种设计简化误写成缺字段 |

本表与逐卡审计共同支持的合并条件是：先修复 B01–B04，并对 B05 的公开暂停上下文作明确裁定；在此之前不能写“当前完整模型输入已覆盖全部全卡决策状态”。

## 2026-09-13修复复核追加

- CARD 115维实际布局保持不变；B01/B02/B04改变的是后端实例生命周期或类别取值，B03只改变+100的升级过滤。
- B05的自动/重复/强制耗尽差异不进入CARD字段，改由SELECT_CARD的独立`resolution_context`和`Candidate.context`进入动作评分器。该上下文不是实体token，不替代环境mask，也不携带隐藏队列或随机结果。
- 逐卡静态覆盖与本轮F1–F4定向行为证据分开记录；完整CPU回归、恢复和最终合并结论以`docs/card-token-fix-report.md`为准。
