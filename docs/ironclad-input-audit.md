# Ironclad 全卡牌输入审计表（75类／150版本）

日期：2026-09-12。配套交付：[新增需求、交互闭包与接口差异](ironclad-input-requirements.md)。

快照补记：审计期间另一路新增了comparison编码/MLP/Set/容量包装草稿，13:13静态复核情况见配套报告I10。表中准入结论针对未改变的public中央契约；旧模型路径结论不代表新增草稿不存在，也不构成草稿运行验收。

## 1. 判读方式与本次证据

每个基础版与升级版各占一行。**“可表达”仅指该版本在当前已准入内容闭包内，本牌直接决策需求有公开语义载体；不是模型已接入，也不是全卡组合行为通过。** “未准入”表示当前正式入口拒绝该版本；即使表内没有新增结构字段，也仍必须补注册、cardRow数值分支和行为验收。

R01–R12定义、I1–I9实现位置、S1–S4来源等级见配套汇总。每个未准入版本统一依赖R01；全部150版本接入模型统一依赖R12。表中“专项缺口”列出额外需求，关联列列出未来组合依赖。已有状态字典可复用不表示所有新状态已安全导出。

基础/升级效果来自已有M1数值核验记录（S3）；本次逐卡重新核对当前注册和源码入口，并对输入需求重新分类。没有沿用旧A/B/C/D分类，也没有把旧报告的3牌registry或31动作当作当前public接口。Searing Blow的“升级”行同时指出+1与后续多次升级的差别。

当前登记35类战士中的34类开放基础/升级，True Grit只开放基础，共69版本；40类和True Grit+共81版本未准入。当前5辅助牌为AscendersBane/Wound/Dazed/Burn/Slimed，属于关联输入，不计入75类战士。

审计HEAD：`0d68033d2b2fb7a042d33343b863af7c3e818967`。本轮起始工作树git status为空。正版JAR SHA256：`cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673`。本次本机JAR直接确认75个red类，逐一对应表内75个名称，75个英文卡片文本键及75个当前后端case；具体补丁发行字符串仍未查明。

卡表各行“S3:行号”为旧审计的数值/语义证据；“I8:行号”为本次BattleContext.cpp结算入口。每行共同实现位置是I1（准入）、I2 cardRow（公开属性）、I3（动作）、I4（规范化）；专项位置见R台账。

## 2. 逐版本审计

| 卡牌 | 版本与效果（S3） | 当前public入口/直接信息 | 专项缺口 | 输入与动作需求 | 组合影响 | 核验定位 |
|---|---|---|---|---|---|---|
| Anger (`ANGER`) | 基础：费0；D6；打出后向弃牌堆加 1 张 Anger | 未准入；统一需R01 | R08 | 实例伤害/升级、弃牌区与生成后的独立副本；复制不能合并同名牌 | 敌方修饰与Double Tap可放大生成次数 | [S3:152](ironclad-card-audit.md#5-逐卡审计)；I8:975 |
| Anger (`ANGER`) | 升级：费0；D8；同语义 | 未准入；统一需R01 | R08 | 实例伤害/升级、弃牌区与生成后的独立副本；复制不能合并同名牌 | 敌方修饰与Double Tap可放大生成次数 | [S3:152](ironclad-card-audit.md#5-逐卡审计)；I8:975 |
| Bash (`BASH`) | 基础：费2；D8；Vulnerable 2 | 可表达；已准入 | — | 当前damage/magic、逐目标伤害、敌方Vulnerable/Artifact足以表达本牌直接需求 | Artifact与多段减益消耗顺序仍归后端 | [S3:153](ironclad-card-audit.md#5-逐卡审计)；I8:980 |
| Bash (`BASH`) | 升级：费2；D10；Vulnerable 3 | 可表达；已准入 | — | 当前damage/magic、逐目标伤害、敌方Vulnerable/Artifact足以表达本牌直接需求 | Artifact与多段减益消耗顺序仍归后端 | [S3:153](ironclad-card-audit.md#5-逐卡审计)；I8:980 |
| Blood for Blood (`BLOOD_FOR_BLOOD`) | 基础：费4；D18；每次本战斗失 HP 后费用降低 1 | 未准入；统一需R01 | R02 | 需各实例战斗费用及当前回合有效费；现有base_cost有载体但须核验更新/非手牌可见性 | 任何失HP路径、复制、升级、Corruption之外的免费打出；无需重复增加完整失血历史 | [S3:154](ironclad-card-audit.md#5-逐卡审计)；I8:995 |
| Blood for Blood (`BLOOD_FOR_BLOOD`) | 升级：费3；D22；同语义 | 未准入；统一需R01 | R02 | 需各实例战斗费用及当前回合有效费；现有base_cost有载体但须核验更新/非手牌可见性 | 任何失HP路径、复制、升级、Corruption之外的免费打出；无需重复增加完整失血历史 | [S3:154](ironclad-card-audit.md#5-逐卡审计)；I8:995 |
| Bludgeon (`BLUDGEON`) | 基础：费3；D32 | 可表达；已准入 | — | 固定伤害和目标修饰已有字段，升级只变伤害 | Strength/Weak/Vulnerable与免费出牌复用现有状态 | [S3:155](ironclad-card-audit.md#5-逐卡审计)；I8:999 |
| Bludgeon (`BLUDGEON`) | 升级：费3；D42 | 可表达；已准入 | — | 固定伤害和目标修饰已有字段，升级只变伤害 | Strength/Weak/Vulnerable与免费出牌复用现有状态 | [S3:155](ironclad-card-audit.md#5-逐卡审计)；I8:999 |
| Body Slam (`BODY_SLAM`) | 基础：费1；D=当前 Block | 可表达；已准入 | — | 当前block、升级费用及damage_by_target已有载体 | Barricade/Entrench/Feel No Pain改变block，未来依R03 | [S3:156](ironclad-card-audit.md#5-逐卡审计)；I8:991 |
| Body Slam (`BODY_SLAM`) | 升级：费0；D=当前 Block | 可表达；已准入 | — | 当前block、升级费用及damage_by_target已有载体 | Barricade/Entrench/Feel No Pain改变block，未来依R03 | [S3:156](ironclad-card-audit.md#5-逐卡审计)；I8:991 |
| Carnage (`CARNAGE`) | 基础：费2；Ethereal；D20 | 可表达；已准入 | — | damage、ethereal及四区移动已有载体；升级仍虚无 | 回合末消耗会触发Feel No Pain/Dark Embrace | [S3:157](ironclad-card-audit.md#5-逐卡审计)；I8:1003 |
| Carnage (`CARNAGE`) | 升级：费2；Ethereal；D28 | 可表达；已准入 | — | damage、ethereal及四区移动已有载体；升级仍虚无 | 回合末消耗会触发Feel No Pain/Dark Embrace | [S3:157](ironclad-card-audit.md#5-逐卡审计)；I8:1003 |
| Clash (`CLASH`) | 基础：费0；仅当手牌全为 Attack 可出；D14 | 未准入；统一需R01 | — | 全部手牌逐实例card_type及环境mask可表达限制；无需新历史 | 状态/诅咒牌和Corruption耗尽会改变能否打出 | [S3:158](ironclad-card-audit.md#5-逐卡审计)；I8:1007 |
| Clash (`CLASH`) | 升级：费0；D18 | 未准入；统一需R01 | — | 全部手牌逐实例card_type及环境mask可表达限制；无需新历史 | 状态/诅咒牌和Corruption耗尽会改变能否打出 | [S3:158](ironclad-card-audit.md#5-逐卡审计)；I8:1007 |
| Cleave (`CLEAVE`) | 基础：费1；ALL；全体 D8 | 可表达；已准入 | — | 全体标记和逐目标伤害已有载体，升级改伤害 | 每个敌人的状态不同，不能只保留全体平均伤害 | [S3:159](ironclad-card-audit.md#5-逐卡审计)；I8:1011 |
| Cleave (`CLEAVE`) | 升级：费1；全体 D11 | 可表达；已准入 | — | 全体标记和逐目标伤害已有载体，升级改伤害 | 每个敌人的状态不同，不能只保留全体平均伤害 | [S3:159](ironclad-card-audit.md#5-逐卡审计)；I8:1011 |
| Clothesline (`CLOTHESLINE`) | 基础：费2；D12；Weak 2 | 可表达；已准入 | — | damage/magic、敌方Weak/Artifact已有 | Artifact阻断减益但不阻断直接攻击的语义需区分 | [S3:160](ironclad-card-audit.md#5-逐卡审计)；I8:1017 |
| Clothesline (`CLOTHESLINE`) | 升级：费2；D14；Weak 3 | 可表达；已准入 | — | damage/magic、敌方Weak/Artifact已有 | Artifact阻断减益但不阻断直接攻击的语义需区分 | [S3:160](ironclad-card-audit.md#5-逐卡审计)；I8:1017 |
| Dropkick (`DROPKICK`) | 基础：费1；D5；若目标 Vulnerable，+1 能量并抽1 | 可表达；已准入 | — | 目标Vulnerable、energy、NoDraw和牌堆已有；固定奖励可由ID恢复 | NoDraw下抽牌失败不等于能量也失败；循环影响R08 | [S3:161](ironclad-card-audit.md#5-逐卡审计)；I8:1028 |
| Dropkick (`DROPKICK`) | 升级：费1；D8；同语义 | 可表达；已准入 | — | 目标Vulnerable、energy、NoDraw和牌堆已有；固定奖励可由ID恢复 | NoDraw下抽牌失败不等于能量也失败；循环影响R08 | [S3:161](ironclad-card-audit.md#5-逐卡审计)；I8:1028 |
| Feed (`FEED`) | 基础：费1；D10；Fatal 时 Max HP +3；Exhaust | 未准入；统一需R01 | R09 | HP/max_hp与敌方HP已有；补本牌Fatal语义和有效目标条件 | Minion/半死等在扩怪物时补公开状态；max_hp改变终局奖励分母 | [S3:162](ironclad-card-audit.md#5-逐卡审计)；I8:1032 |
| Feed (`FEED`) | 升级：费1；D12；Max HP +4；Exhaust | 未准入；统一需R01 | R09 | HP/max_hp与敌方HP已有；补本牌Fatal语义和有效目标条件 | Minion/半死等在扩怪物时补公开状态；max_hp改变终局奖励分母 | [S3:162](ironclad-card-audit.md#5-逐卡审计)；I8:1032 |
| Fiend Fire (`FIEND_FIRE`) | 基础：费2；Exhaust 手牌；每张 D7 | 未准入；统一需R01 | R09,R11 | 需当次耗尽手牌集合和命中数量语义，不能沿用hits=1 | 与Dark Embrace/Sentinel/Feel No Pain/Double Tap的耗尽快照和队列次序待验 | [S3:163](ironclad-card-audit.md#5-逐卡审计)；I8:1036 |
| Fiend Fire (`FIEND_FIRE`) | 升级：费2；每张 D10 | 未准入；统一需R01 | R09,R11 | 需当次耗尽手牌集合和命中数量语义，不能沿用hits=1 | 与Dark Embrace/Sentinel/Feel No Pain/Double Tap的耗尽快照和队列次序待验 | [S3:163](ironclad-card-audit.md#5-逐卡审计)；I8:1036 |
| Headbutt (`HEADBUTT`) | 基础：费1；D9；把弃牌堆 1 张放到抽牌堆顶 | 未准入；统一需R01 | R04,R05,R06 | 弃牌逐实例候选、选择路由、已知置顶记忆；先攻击后选牌 | 重复牌、击杀终局、Double Tap两次选择和Havoc关联 | [S3:164](ironclad-card-audit.md#5-逐卡审计)；I8:1049 |
| Headbutt (`HEADBUTT`) | 升级：费1；D12；同语义 | 未准入；统一需R01 | R04,R05,R06 | 弃牌逐实例候选、选择路由、已知置顶记忆；先攻击后选牌 | 重复牌、击杀终局、Double Tap两次选择和Havoc关联 | [S3:164](ironclad-card-audit.md#5-逐卡审计)；I8:1049 |
| Heavy Blade (`HEAVY_BLADE`) | 基础：费2；D14；Strength 按 3 倍影响 | 可表达；已准入 | — | Strength、magic倍率与逐目标伤害已有；基础3倍升级5倍 | 不可再次把力量乘入已修饰伤害，负力量组合待验 | [S3:165](ironclad-card-audit.md#5-逐卡审计)；I8:1054 |
| Heavy Blade (`HEAVY_BLADE`) | 升级：费2；D14；Strength 按 5 倍影响 | 可表达；已准入 | — | Strength、magic倍率与逐目标伤害已有；基础3倍升级5倍 | 不可再次把力量乘入已修饰伤害，负力量组合待验 | [S3:165](ironclad-card-audit.md#5-逐卡审计)；I8:1054 |
| Hemokinesis (`HEMOKINESIS`) | 基础：费1；失2 HP；D15 | 未准入；统一需R01 | — | HP、固定自伤量语义和damage可用已有载体扩分支 | Rupture/Blood for Blood反应由结果状态表达，不能把失HP当格挡可吸收伤害 | [S3:166](ironclad-card-audit.md#5-逐卡审计)；I8:1061 |
| Hemokinesis (`HEMOKINESIS`) | 升级：费1；失2 HP；D20 | 未准入；统一需R01 | — | HP、固定自伤量语义和damage可用已有载体扩分支 | Rupture/Blood for Blood反应由结果状态表达，不能把失HP当格挡可吸收伤害 | [S3:166](ironclad-card-audit.md#5-逐卡审计)；I8:1061 |
| Immolate (`IMMOLATE`) | 基础：费2；全体 D21；弃牌堆加 Burn | 可表达；已准入 | — | 全体伤害、Burn逐实例及弃牌堆已有 | Burn与Rupture/Blood for Blood/Evolve/Fire Breathing相联；扩展连锁依R08 | [S3:167](ironclad-card-audit.md#5-逐卡审计)；I8:1068 |
| Immolate (`IMMOLATE`) | 升级：费2；全体 D28；同语义 | 可表达；已准入 | — | 全体伤害、Burn逐实例及弃牌堆已有 | Burn与Rupture/Blood for Blood/Evolve/Fire Breathing相联；扩展连锁依R08 | [S3:167](ironclad-card-audit.md#5-逐卡审计)；I8:1068 |
| Iron Wave (`IRON_WAVE`) | 基础：费1；B5+D5 | 未准入；统一需R01 | R11 | 格挡/伤害/逐目标字段均可复用，无新实体 | 当前后端重复calculateCardBlock；Dexterity/Frail会暴露差异 | [S3:168](ironclad-card-audit.md#5-逐卡审计)；I8:1075 |
| Iron Wave (`IRON_WAVE`) | 升级：费1；B7+D7 | 未准入；统一需R01 | R11 | 格挡/伤害/逐目标字段均可复用，无新实体 | 当前后端重复calculateCardBlock；Dexterity/Frail会暴露差异 | [S3:168](ironclad-card-audit.md#5-逐卡审计)；I8:1075 |
| Perfected Strike (`PERFECTED_STRIKE`) | 基础：费2；D6 + 2×所有名称含 Strike 的牌 | 未准入；统一需R01 | R06,R09 | 新增分支计算有效Strike数；可由牌区＋静态is_strike推导而非盲目数四区 | 消耗牌排除；当前打出牌计入时点、生成/复制Strike和暂停阶段须核验 | [S3:169](ironclad-card-audit.md#5-逐卡审计)；I8:1087 |
| Perfected Strike (`PERFECTED_STRIKE`) | 升级：费2；D6 + 3×上述数量 | 未准入；统一需R01 | R06,R09 | 新增分支计算有效Strike数；可由牌区＋静态is_strike推导而非盲目数四区 | 消耗牌排除；当前打出牌计入时点、生成/复制Strike和暂停阶段须核验 | [S3:169](ironclad-card-audit.md#5-逐卡审计)；I8:1087 |
| Pommel Strike (`POMMEL_STRIKE`) | 基础：费1；D9；抽1 | 可表达；已准入 | — | damage/magic、NoDraw、手牌及抽弃堆已有 | 升级抽2；状态牌抽取链可能继续触发 | [S3:170](ironclad-card-audit.md#5-逐卡审计)；I8:1095 |
| Pommel Strike (`POMMEL_STRIKE`) | 升级：费1；D10；抽2 | 可表达；已准入 | — | damage/magic、NoDraw、手牌及抽弃堆已有 | 升级抽2；状态牌抽取链可能继续触发 | [S3:170](ironclad-card-audit.md#5-逐卡审计)；I8:1095 |
| Pummel (`PUMMEL`) | 基础：费1；D2×4；Exhaust | 可表达；已准入 | — | 逐段damage、hits、固有exhaust已有 | 每段触发敌方反应，多段总伤害不等于一次乘法结算 | [S3:171](ironclad-card-audit.md#5-逐卡审计)；I8:1100 |
| Pummel (`PUMMEL`) | 升级：费1；D2×5；Exhaust | 可表达；已准入 | — | 逐段damage、hits、固有exhaust已有 | 每段触发敌方反应，多段总伤害不等于一次乘法结算 | [S3:171](ironclad-card-audit.md#5-逐卡审计)；I8:1100 |
| Rampage (`RAMPAGE`) | 基础：费1；D8；本战斗每次打出后该牌伤害 +5 | 未准入；统一需R01 | R02,R07,R11 | 未导出的逐实例specialData须转命名增伤/当前伤害；基础增长5升级8 | Double Tap第二次伤害快照与Dual Wield复制增伤继承待验；同名不同增伤分别表示 | [S3:172](ironclad-card-audit.md#5-逐卡审计)；I8:1109 |
| Rampage (`RAMPAGE`) | 升级：费1；D8；每次 +8 | 未准入；统一需R01 | R02,R07,R11 | 未导出的逐实例specialData须转命名增伤/当前伤害；基础增长5升级8 | Double Tap第二次伤害快照与Dual Wield复制增伤继承待验；同名不同增伤分别表示 | [S3:172](ironclad-card-audit.md#5-逐卡审计)；I8:1109 |
| Reaper (`REAPER`) | 基础：费2；全体 D4；按未格挡伤害治疗；Exhaust | 未准入；统一需R01 | R09 | 全体伤害/HP/max_hp可复用；补按实际未格挡伤害治疗语义 | 敌方block/过量伤害、治疗修饰及战斗出口不能用名义damage替代 | [S3:173](ironclad-card-audit.md#5-逐卡审计)；I8:1121 |
| Reaper (`REAPER`) | 升级：费2；全体 D5；同语义 | 未准入；统一需R01 | R09 | 全体伤害/HP/max_hp可复用；补按实际未格挡伤害治疗语义 | 敌方block/过量伤害、治疗修饰及战斗出口不能用名义damage替代 | [S3:173](ironclad-card-audit.md#5-逐卡审计)；I8:1121 |
| Reckless Charge (`RECKLESS_CHARGE`) | 基础：费0；D7；抽牌堆加入 Dazed | 可表达；已准入 | — | 伤害、Dazed独立实例和抽牌堆已有 | 随机插入不能泄露插入位置；与Evolve/Fire Breathing及R06记忆失效相联 | [S3:174](ironclad-card-audit.md#5-逐卡审计)；I8:1127 |
| Reckless Charge (`RECKLESS_CHARGE`) | 升级：费0；D10；同语义 | 可表达；已准入 | — | 伤害、Dazed独立实例和抽牌堆已有 | 随机插入不能泄露插入位置；与Evolve/Fire Breathing及R06记忆失效相联 | [S3:174](ironclad-card-audit.md#5-逐卡审计)；I8:1127 |
| Searing Blow (`SEARING_BLOW`) | 基础：费2；D12；可无限升级 | 未准入；统一需R01 | R02 | upgrade_count整数已存在；需多次升级入口和对应伤害计算 | Armaments战斗内反复升级、复制升级数；+1不是可无限升级范围的全部验收 | [S3:175](ironclad-card-audit.md#5-逐卡审计)；I8:1136 |
| Searing Blow (`SEARING_BLOW`) | 升级：费2；第 n 次升级 D=`12+n(n+7)/2`（1次16、2次21、3次27…） | 未准入；统一需R01 | R02 | upgrade_count整数已存在；需多次升级入口和对应伤害计算 | Armaments战斗内反复升级、复制升级数；+1不是可无限升级范围的全部验收 | [S3:175](ironclad-card-audit.md#5-逐卡审计)；I8:1136 |
| Sever Soul (`SEVER_SOUL`) | 基础：费2；Exhaust 手牌非 Attack；D16 | 未准入；统一需R01 | — | 手牌card_type、逐实例、固有exhaust与damage载体可复用 | 自动耗尽非Attack，无需玩家选择；触发链依R03/R07 | [S3:176](ironclad-card-audit.md#5-逐卡审计)；I8:1143 |
| Sever Soul (`SEVER_SOUL`) | 升级：费2；D22 | 未准入；统一需R01 | — | 手牌card_type、逐实例、固有exhaust与damage载体可复用 | 自动耗尽非Attack，无需玩家选择；触发链依R03/R07 | [S3:176](ironclad-card-audit.md#5-逐卡审计)；I8:1143 |
| Strike (`STRIKE_RED`) | 基础：费1；D6 | 可表达；已准入 | — | 已有伤害/升级/目标语义 | Perfected Strike计数与复制/消耗区域相关 | [S3:177](ironclad-card-audit.md#5-逐卡审计)；I8:967 |
| Strike (`STRIKE_RED`) | 升级：费1；D9 | 可表达；已准入 | — | 已有伤害/升级/目标语义 | Perfected Strike计数与复制/消耗区域相关 | [S3:177](ironclad-card-audit.md#5-逐卡审计)；I8:967 |
| Sword Boomerang (`SWORD_BOOMERANG`) | 基础：费1；随机敌人 D3×3 | 未准入；统一需R01 | R09 | 需随机目标模式和固定段数3/4；逐目标预览不是未来随机结果 | 无玩家选敌，死亡后各段目标处理由环境执行 | [S3:178](ironclad-card-audit.md#5-逐卡审计)；I8:1152 |
| Sword Boomerang (`SWORD_BOOMERANG`) | 升级：费1；随机敌人 D3×4 | 未准入；统一需R01 | R09 | 需随机目标模式和固定段数3/4；逐目标预览不是未来随机结果 | 无玩家选敌，死亡后各段目标处理由环境执行 | [S3:178](ironclad-card-audit.md#5-逐卡审计)；I8:1152 |
| Thunderclap (`THUNDERCLAP`) | 基础：费1；全体 D4，并 Vulnerable 1 | 可表达；已准入 | — | 全体伤害、Vulnerable/Artifact已有 | 每个敌人的Artifact独立结算 | [S3:179](ironclad-card-audit.md#5-逐卡审计)；I8:1158 |
| Thunderclap (`THUNDERCLAP`) | 升级：费1；全体 D7，并 Vulnerable 1 | 可表达；已准入 | — | 全体伤害、Vulnerable/Artifact已有 | 每个敌人的Artifact独立结算 | [S3:179](ironclad-card-audit.md#5-逐卡审计)；I8:1158 |
| Twin Strike (`TWIN_STRIKE`) | 基础：费1；D5×2 | 可表达；已准入 | — | hits=2与逐段damage已有 | Strength和敌方每次受击状态影响各段 | [S3:180](ironclad-card-audit.md#5-逐卡审计)；I8:1165 |
| Twin Strike (`TWIN_STRIKE`) | 升级：费1；D7×2 | 可表达；已准入 | — | hits=2与逐段damage已有 | Strength和敌方每次受击状态影响各段 | [S3:180](ironclad-card-audit.md#5-逐卡审计)；I8:1165 |
| Uppercut (`UPPERCUT`) | 基础：费2；D13；Weak/Vulnerable 各1 | 可表达；已准入 | — | damage/magic、Weak/Vulnerable/Artifact已有 | 两个减益的顺序影响仅一层Artifact场景 | [S3:181](ironclad-card-audit.md#5-逐卡审计)；I8:1172 |
| Uppercut (`UPPERCUT`) | 升级：费2；D13；Weak/Vulnerable 各2 | 可表达；已准入 | — | damage/magic、Weak/Vulnerable/Artifact已有 | 两个减益的顺序影响仅一层Artifact场景 | [S3:181](ironclad-card-audit.md#5-逐卡审计)；I8:1172 |
| Whirlwind (`WHIRLWIND`) | 基础：X 费；全体 D5×X | 未准入；统一需R01 | R02,R07,R09 | X费用种类、当前能量和执行X快照；伤害5/8及动态命中次数 | 不增加X数值选择；免费/Havoc/Double Tap及未来Chemical X分开验 | [S3:182](ironclad-card-audit.md#5-逐卡审计)；I8:1178 |
| Whirlwind (`WHIRLWIND`) | 升级：X 费；全体 D8×X | 未准入；统一需R01 | R02,R07,R09 | X费用种类、当前能量和执行X快照；伤害5/8及动态命中次数 | 不增加X数值选择；免费/Havoc/Double Tap及未来Chemical X分开验 | [S3:182](ironclad-card-audit.md#5-逐卡审计)；I8:1178 |
| Wild Strike (`WILD_STRIKE`) | 基础：费1；D12；抽牌堆加入 Wound | 可表达；已准入 | — | 伤害、Wound独立实例与抽牌堆已有 | 随机插入与状态抽牌链、已知顶牌记忆相联 | [S3:183](ironclad-card-audit.md#5-逐卡审计)；I8:1187 |
| Wild Strike (`WILD_STRIKE`) | 升级：费1；D17；同语义 | 可表达；已准入 | — | 伤害、Wound独立实例与抽牌堆已有 | 随机插入与状态抽牌链、已知顶牌记忆相联 | [S3:183](ironclad-card-audit.md#5-逐卡审计)；I8:1187 |
| Armaments (`ARMAMENTS`) | 基础：费1；B5；选择手牌 1 张，本战斗升级 | 未准入；统一需R01 | R02,R04,R05 | 基础需手牌可升级候选；升级自动升级全手牌；动态upgrade_count/费用同步 | 排除不可升级卡；Searing Blow可多次升级；升级版不增加选牌动作 | [S3:189](ironclad-card-audit.md#5-逐卡审计)；I8:1217 |
| Armaments (`ARMAMENTS`) | 升级：费1；B5；本战斗升级全部手牌 | 未准入；统一需R01 | R02（无单选） | 基础需手牌可升级候选；升级自动升级全手牌；动态upgrade_count/费用同步 | 排除不可升级卡；Searing Blow可多次升级；升级版不增加选牌动作 | [S3:189](ironclad-card-audit.md#5-逐卡审计)；I8:1217 |
| Battle Trance (`BATTLE_TRANCE`) | 基础：费0；抽3；本回合禁止额外抽牌 | 可表达；已准入 | — | magic抽牌数、NoDraw布尔、牌堆已有 | 后续Dark Embrace/Evolve/Swift Potion的抽牌被阻止而其他效果仍可发生 | [S3:190](ironclad-card-audit.md#5-逐卡审计)；I8:1238 |
| Battle Trance (`BATTLE_TRANCE`) | 升级：费0；抽4；同语义 | 可表达；已准入 | — | magic抽牌数、NoDraw布尔、牌堆已有 | 后续Dark Embrace/Evolve/Swift Potion的抽牌被阻止而其他效果仍可发生 | [S3:190](ironclad-card-audit.md#5-逐卡审计)；I8:1238 |
| Bloodletting (`BLOODLETTING`) | 基础：费0；失3 HP；+2 能量 | 未准入；统一需R01 | — | HP/energy已有，静态自伤和能量量可由ID/升级恢复 | Rupture/Blood for Blood及HP不足导致终局的中断次序 | [S3:191](ironclad-card-audit.md#5-逐卡审计)；I8:1251 |
| Bloodletting (`BLOODLETTING`) | 升级：费0；失3 HP；+3 能量 | 未准入；统一需R01 | — | HP/energy已有，静态自伤和能量量可由ID/升级恢复 | Rupture/Blood for Blood及HP不足导致终局的中断次序 | [S3:191](ironclad-card-audit.md#5-逐卡审计)；I8:1251 |
| Burning Pact (`BURNING_PACT`) | 基础：费1；选择并 Exhaust 1 张；抽2 | 未准入；统一需R01 | R04,R05 | 手牌逐实例消耗选择、抽牌数量；选择后的触发链 | Sentinel/Feel No Pain/Dark Embrace/NoDraw及空手牌退化路径 | [S3:192](ironclad-card-audit.md#5-逐卡审计)；I8:1256 |
| Burning Pact (`BURNING_PACT`) | 升级：费1；选择并 Exhaust 1 张；抽3 | 未准入；统一需R01 | R04,R05 | 手牌逐实例消耗选择、抽牌数量；选择后的触发链 | Sentinel/Feel No Pain/Dark Embrace/NoDraw及空手牌退化路径 | [S3:192](ironclad-card-audit.md#5-逐卡审计)；I8:1256 |
| Defend (`DEFEND_RED`) | 基础：费1；B5 | 可表达；已准入 | — | block/base_block、升级与Dexterity/Frail已有 | Juggernaut/Corruption属于组合新增依赖 | [S3:193](ironclad-card-audit.md#5-逐卡审计)；I8:1210 |
| Defend (`DEFEND_RED`) | 升级：费1；B8 | 可表达；已准入 | — | block/base_block、升级与Dexterity/Frail已有 | Juggernaut/Corruption属于组合新增依赖 | [S3:193](ironclad-card-audit.md#5-逐卡审计)；I8:1210 |
| Disarm (`DISARM`) | 基础：费1；敌人 Strength -2；Exhaust | 未准入；统一需R01 | —（升级差异见下一行） | 有符号敌Strength、Artifact与固有exhaust已有；需新增本牌分支 | 基础-2，升级正版-3但当前后端固定-2；基础也需新入口行为验收 | [S3:194](ironclad-card-audit.md#5-逐卡审计)；I8:1281 |
| Disarm (`DISARM`) | 升级：费1；敌人 Strength -3；Exhaust | 未准入；统一需R01 | R11 | 有符号敌Strength、Artifact与固有exhaust已有；需新增本牌分支 | 基础-2，升级正版-3但当前后端固定-2；基础也需新入口行为验收 | [S3:194](ironclad-card-audit.md#5-逐卡审计)；I8:1281 |
| Double Tap (`DOUBLE_TAP`) | 基础：费1；本回合下一张 Attack 打两次 | 未准入；统一需R01 | R03,R07 | 剩余可双打Attack次数/期限可用状态容器，但须注册其语义 | Headbutt二次选择、Rampage增长、Fiend Fire和Whirlwind快照；不是新增第二次玩家出牌 | [S3:195](ironclad-card-audit.md#5-逐卡审计)；I8:1290 |
| Double Tap (`DOUBLE_TAP`) | 升级：费1；本回合接下来 2 张 Attack 各打两次 | 未准入；统一需R01 | R03,R07 | 剩余可双打Attack次数/期限可用状态容器，但须注册其语义 | Headbutt二次选择、Rampage增长、Fiend Fire和Whirlwind快照；不是新增第二次玩家出牌 | [S3:195](ironclad-card-audit.md#5-逐卡审计)；I8:1290 |
| Dual Wield (`DUAL_WIELD`) | 基础：费1；选择 Attack 或 Power，复制 1 张入手牌 | 未准入；统一需R01 | R02,R04,R05,R07,R08,R11 | 可复制Attack/Power候选、复制数量1/2、新实例和属性继承 | 手满溢入弃牌，动态费用/伤害/升级、对象重排及后端helper待验 | [S3:196](ironclad-card-audit.md#5-逐卡审计)；I8:1294 |
| Dual Wield (`DUAL_WIELD`) | 升级：费1；选择 Attack 或 Power，复制 2 张 | 未准入；统一需R01 | R02,R04,R05,R07,R08,R11 | 可复制Attack/Power候选、复制数量1/2、新实例和属性继承 | 手满溢入弃牌，动态费用/伤害/升级、对象重排及后端helper待验 | [S3:196](ironclad-card-audit.md#5-逐卡审计)；I8:1294 |
| Entrench (`ENTRENCH`) | 基础：费2；Block 翻倍 | 可表达；已准入 | — | 当前block及升级费用已有；翻倍不是普通受Dexterity加成的B值 | Barricade保留与Juggernaut获得格挡触发需要分别建模 | [S3:197](ironclad-card-audit.md#5-逐卡审计)；I8:1302 |
| Entrench (`ENTRENCH`) | 升级：费1；Block 翻倍 | 可表达；已准入 | — | 当前block及升级费用已有；翻倍不是普通受Dexterity加成的B值 | Barricade保留与Juggernaut获得格挡触发需要分别建模 | [S3:197](ironclad-card-audit.md#5-逐卡审计)；I8:1302 |
| Exhume (`EXHUME`) | 基础：费1；选择消耗堆 1 张入手；Exhaust | 未准入；统一需R01 | R04,R05,R11 | 消耗堆逐实例候选及禁选Exhume、回手与动态属性继承 | 满手牌/唯一候选/Corruption回手费用；不能直接用排序后索引调用后端 | [S3:198](ironclad-card-audit.md#5-逐卡审计)；I8:1306 |
| Exhume (`EXHUME`) | 升级：费0；同语义 | 未准入；统一需R01 | R04,R05,R11 | 消耗堆逐实例候选及禁选Exhume、回手与动态属性继承 | 满手牌/唯一候选/Corruption回手费用；不能直接用排序后索引调用后端 | [S3:198](ironclad-card-audit.md#5-逐卡审计)；I8:1306 |
| Flame Barrier (`FLAME_BARRIER`) | 基础：费2；B12；本回合受攻击反伤4 | 可表达；已准入 | — | block与FlameBarrier活动值已有 | 与Bronze Scales/Liquid Bronze反伤层关联；多段受击逐段触发 | [S3:199](ironclad-card-audit.md#5-逐卡审计)；I8:1319 |
| Flame Barrier (`FLAME_BARRIER`) | 升级：费2；B16；反伤6 | 可表达；已准入 | — | block与FlameBarrier活动值已有 | 与Bronze Scales/Liquid Bronze反伤层关联；多段受击逐段触发 | [S3:199](ironclad-card-audit.md#5-逐卡审计)；I8:1319 |
| Flex (`FLEX`) | 基础：费0；Str+2，本回合末 -2 | 可表达；已准入 | — | Strength和LoseStrength已有；升级改数值 | Ancient Potion的Artifact可能改变延迟减力量，不能只看当前Strength | [S3:200](ironclad-card-audit.md#5-逐卡审计)；I8:1324 |
| Flex (`FLEX`) | 升级：费0；Str+4，本回合末 -4 | 可表达；已准入 | — | Strength和LoseStrength已有；升级改数值 | Ancient Potion的Artifact可能改变延迟减力量，不能只看当前Strength | [S3:200](ironclad-card-audit.md#5-逐卡审计)；I8:1324 |
| Ghostly Armor (`GHOSTLY_ARMOR`) | 基础：费1；Ethereal；B10 | 可表达；已准入 | — | block和ethereal已有；基础升级均虚无 | 升级只加格挡，不移除虚无；回合末耗尽触发相关状态 | [S3:201](ironclad-card-audit.md#5-逐卡审计)；I8:1329 |
| Ghostly Armor (`GHOSTLY_ARMOR`) | 升级：费1；仍 Ethereal；B13 | 可表达；已准入 | — | block和ethereal已有；基础升级均虚无 | 升级只加格挡，不移除虚无；回合末耗尽触发相关状态 | [S3:201](ironclad-card-audit.md#5-逐卡审计)；I8:1329 |
| Havoc (`HAVOC`) | 基础：费1；打出抽牌堆顶牌并 Exhaust | 未准入；统一需R01 | R05,R06,R07,R08 | 正常出牌后自动顶牌执行，需公开置顶记忆和实际可达选择阶段闭包 | 随机目标非玩家动作；免费/强制消耗/X/生成/选择卡、空抽牌洗牌全部核验 | [S3:202](ironclad-card-audit.md#5-逐卡审计)；I8:1337 |
| Havoc (`HAVOC`) | 升级：费0；同语义 | 未准入；统一需R01 | R05,R06,R07,R08 | 正常出牌后自动顶牌执行，需公开置顶记忆和实际可达选择阶段闭包 | 随机目标非玩家动作；免费/强制消耗/X/生成/选择卡、空抽牌洗牌全部核验 | [S3:202](ironclad-card-audit.md#5-逐卡审计)；I8:1337 |
| Impervious (`IMPERVIOUS`) | 基础：费2；B30；Exhaust | 可表达；已准入 | — | block、固有exhaust及四区已有 | 耗尽链与格挡触发可共同发生 | [S3:203](ironclad-card-audit.md#5-逐卡审计)；I8:1355 |
| Impervious (`IMPERVIOUS`) | 升级：费2；B40；Exhaust | 可表达；已准入 | — | block、固有exhaust及四区已有 | 耗尽链与格挡触发可共同发生 | [S3:203](ironclad-card-audit.md#5-逐卡审计)；I8:1355 |
| Infernal Blade (`INFERNAL_BLADE`) | 基础：费1；随机 Attack 入手，本回合费0；Exhaust | 未准入；统一需R01 | R02,R07,R08 | 随机Attack生成池、独立实例、本回合费0/到期恢复 | 可生成Headbutt等未准入攻击；不能改池绕过动作闭包 | [S3:204](ironclad-card-audit.md#5-逐卡审计)；I8:1359 |
| Infernal Blade (`INFERNAL_BLADE`) | 升级：费0；同语义 | 未准入；统一需R01 | R02,R07,R08 | 随机Attack生成池、独立实例、本回合费0/到期恢复 | 可生成Headbutt等未准入攻击；不能改池绕过动作闭包 | [S3:204](ironclad-card-audit.md#5-逐卡审计)；I8:1359 |
| Intimidate (`INTIMIDATE`) | 基础：费0；全体 Weak1；Exhaust | 未准入；统一需R01 | — | 全体Weak与Artifact已有容器，升级改层数 | 全体非玩家单目标，不增加动作列 | [S3:205](ironclad-card-audit.md#5-逐卡审计)；I8:1363 |
| Intimidate (`INTIMIDATE`) | 升级：费0；全体 Weak2；Exhaust | 未准入；统一需R01 | — | 全体Weak与Artifact已有容器，升级改层数 | 全体非玩家单目标，不增加动作列 | [S3:205](ironclad-card-audit.md#5-逐卡审计)；I8:1363 |
| Limit Break (`LIMIT_BREAK`) | 基础：费1；Strength 翻倍；Exhaust | 未准入；统一需R01 | — | 有符号Strength、固有exhaust可复用；升级改不耗尽 | 与Flex临时力量、Artifact及负力量翻倍的结算待验 | [S3:206](ironclad-card-audit.md#5-逐卡审计)；I8:1376 |
| Limit Break (`LIMIT_BREAK`) | 升级：费1；Strength 翻倍；不 Exhaust | 未准入；统一需R01 | — | 有符号Strength、固有exhaust可复用；升级改不耗尽 | 与Flex临时力量、Artifact及负力量翻倍的结算待验 | [S3:206](ironclad-card-audit.md#5-逐卡审计)；I8:1376 |
| Offering (`OFFERING`) | 基础：费0；失6 HP；+2 能量；抽3；Exhaust | 未准入；统一需R01 | — | HP/energy/NoDraw及牌区已有；magic单值不足作通用多效果说明 | 固定自伤6、能量2、抽3/5由静态字典恢复；Rupture/Blood for Blood链 | [S3:207](ironclad-card-audit.md#5-逐卡审计)；I8:1392 |
| Offering (`OFFERING`) | 升级：费0；失6 HP；+2 能量；抽5；Exhaust | 未准入；统一需R01 | — | HP/energy/NoDraw及牌区已有；magic单值不足作通用多效果说明 | 固定自伤6、能量2、抽3/5由静态字典恢复；Rupture/Blood for Blood链 | [S3:207](ironclad-card-audit.md#5-逐卡审计)；I8:1392 |
| Power Through (`POWER_THROUGH`) | 基础：费1；手牌加 2 Wound；B15 | 可表达；已准入 | — | block、生成2个Wound及手牌/溢出区域已有 | 重复Wound独立占位，耗尽/状态抽牌关联；新增组合需R08 | [S3:208](ironclad-card-audit.md#5-逐卡审计)；I8:1407 |
| Power Through (`POWER_THROUGH`) | 升级：费1；手牌加 2 Wound；B20 | 可表达；已准入 | — | block、生成2个Wound及手牌/溢出区域已有 | 重复Wound独立占位，耗尽/状态抽牌关联；新增组合需R08 | [S3:208](ironclad-card-audit.md#5-逐卡审计)；I8:1407 |
| Rage (`RAGE`) | 基础：费0；本回合每打 Attack 得 B3 | 可表达；已准入 | — | Rage活动值、当前block与攻击计数已有 | 只把触发后的block计为结果不足以表示下一张攻击效果，活动状态必须保留 | [S3:209](ironclad-card-audit.md#5-逐卡审计)；I8:1416 |
| Rage (`RAGE`) | 升级：费0；本回合每打 Attack 得 B5 | 可表达；已准入 | — | Rage活动值、当前block与攻击计数已有 | 只把触发后的block计为结果不足以表示下一张攻击效果，活动状态必须保留 | [S3:209](ironclad-card-audit.md#5-逐卡审计)；I8:1416 |
| Second Wind (`SECOND_WIND`) | 基础：费1；Exhaust 手牌全部非 Attack，每张 B5 | 未准入；统一需R01 | — | 手牌非Attack多重集及每牌格挡5/7可复用字段与字典 | 自动耗尽，无需多选；Feel No Pain/Dark Embrace/Juggernaut每次触发待验 | [S3:210](ironclad-card-audit.md#5-逐卡审计)；I8:1428 |
| Second Wind (`SECOND_WIND`) | 升级：费1；每张 B7 | 未准入；统一需R01 | — | 手牌非Attack多重集及每牌格挡5/7可复用字段与字典 | 自动耗尽，无需多选；Feel No Pain/Dark Embrace/Juggernaut每次触发待验 | [S3:210](ironclad-card-audit.md#5-逐卡审计)；I8:1428 |
| Seeing Red (`SEEING_RED`) | 基础：费1；+2 能量；Exhaust | 可表达；已准入 | — | cost/energy/固有exhaust已有，升级改费用 | 已有修复耗尽的证据不自动覆盖未来Corruption/双发组合 | [S3:211](ironclad-card-audit.md#5-逐卡审计)；I8:1432 |
| Seeing Red (`SEEING_RED`) | 升级：费0；+2 能量；Exhaust | 可表达；已准入 | — | cost/energy/固有exhaust已有，升级改费用 | 已有修复耗尽的证据不自动覆盖未来Corruption/双发组合 | [S3:211](ironclad-card-audit.md#5-逐卡审计)；I8:1432 |
| Sentinel (`SENTINEL`) | 基础：费1；B5；若被 Exhaust，+2 能量 | 可表达；已准入 | — | block、静态耗尽获能量量与四区已有 | 卡本身不是打出即耗尽；True Grit/Fiend Fire/Corruption可触发被耗尽获能量 | [S3:212](ironclad-card-audit.md#5-逐卡审计)；I8:1436 |
| Sentinel (`SENTINEL`) | 升级：费1；B8；+3 能量 | 可表达；已准入 | — | block、静态耗尽获能量量与四区已有 | 卡本身不是打出即耗尽；True Grit/Fiend Fire/Corruption可触发被耗尽获能量 | [S3:212](ironclad-card-audit.md#5-逐卡审计)；I8:1436 |
| Shockwave (`SHOCKWAVE`) | 基础：费2；全体 Weak/Vulnerable 3；Exhaust | 未准入；统一需R01 | — | 全体Weak/Vulnerable、Artifact及exhaust可复用 | 层数3/5与双减益先后顺序待验 | [S3:213](ironclad-card-audit.md#5-逐卡审计)；I8:1440 |
| Shockwave (`SHOCKWAVE`) | 升级：费2；全体 Weak/Vulnerable 5；Exhaust | 未准入；统一需R01 | — | 全体Weak/Vulnerable、Artifact及exhaust可复用 | 层数3/5与双减益先后顺序待验 | [S3:213](ironclad-card-audit.md#5-逐卡审计)；I8:1440 |
| Shrug It Off (`SHRUG_IT_OFF`) | 基础：费1；B8；抽1 | 可表达；已准入 | — | block和抽1、NoDraw及牌区已有 | Dexterity/Frail、NoDraw与Juggernaut关联 | [S3:214](ironclad-card-audit.md#5-逐卡审计)；I8:1445 |
| Shrug It Off (`SHRUG_IT_OFF`) | 升级：费1；B11；抽1 | 可表达；已准入 | — | block和抽1、NoDraw及牌区已有 | Dexterity/Frail、NoDraw与Juggernaut关联 | [S3:214](ironclad-card-audit.md#5-逐卡审计)；I8:1445 |
| Spot Weakness (`SPOT_WEAKNESS`) | 基础：费1；若敌方意图攻击，Str+3 | 可表达；已准入 | — | 敌人攻击意图、Strength及magic已有 | 必须保留所选敌人对应关系，不能仅以全场是否有人攻击替代 | [S3:215](ironclad-card-audit.md#5-逐卡审计)；I8:1450 |
| Spot Weakness (`SPOT_WEAKNESS`) | 升级：费1；Str+4 | 可表达；已准入 | — | 敌人攻击意图、Strength及magic已有 | 必须保留所选敌人对应关系，不能仅以全场是否有人攻击替代 | [S3:215](ironclad-card-audit.md#5-逐卡审计)；I8:1450 |
| True Grit (`TRUE_GRIT`) | 基础：费1；B7；随机 Exhaust 1 张 | 可表达；已准入 | — | 基础随机耗尽已可表达；升级需手牌选择且block=9 | 现cardRow固定block=7且入口max_upgrade=0，不能只开放升级而不补分支/动作 | [S3:216](ironclad-card-audit.md#5-逐卡审计)；I8:1482 |
| True Grit (`TRUE_GRIT`) | 升级：费1；B9；玩家选择 Exhaust 1 张 | 未准入；统一需R01 | R04,R05 | 基础随机耗尽已可表达；升级需手牌选择且block=9 | 现cardRow固定block=7且入口max_upgrade=0，不能只开放升级而不补分支/动作 | [S3:216](ironclad-card-audit.md#5-逐卡审计)；I8:1482 |
| Warcry (`WARCRY`) | 基础：费0；抽1；选择手牌放抽牌堆顶；Exhaust | 未准入；统一需R01 | R04,R05,R06 | 抽1/2后选择手牌置顶；候选必须取抽牌完成后的状态 | NoDraw下仍处理后续置顶；已知牌顶、满手牌及耗尽链 | [S3:217](ironclad-card-audit.md#5-逐卡审计)；I8:1495 |
| Warcry (`WARCRY`) | 升级：费0；抽2；选择手牌放顶；Exhaust | 未准入；统一需R01 | R04,R05,R06 | 抽1/2后选择手牌置顶；候选必须取抽牌完成后的状态 | NoDraw下仍处理后续置顶；已知牌顶、满手牌及耗尽链 | [S3:217](ironclad-card-audit.md#5-逐卡审计)；I8:1495 |
| Barricade (`BARRICADE`) | 基础：费3；Block 不在回合开始移除 | 未准入；统一需R01 | R03 | block和布尔活动状态；通用导出对bit-only状态不安全 | 不用额外Barricade实体；布尔开启后回合边界格挡保留 | [S3:223](ironclad-card-audit.md#5-逐卡审计)；I8:1518 |
| Barricade (`BARRICADE`) | 升级：费2；同语义 | 未准入；统一需R01 | R03 | block和布尔活动状态；通用导出对bit-only状态不安全 | 不用额外Barricade实体；布尔开启后回合边界格挡保留 | [S3:223](ironclad-card-audit.md#5-逐卡审计)；I8:1518 |
| Berserk (`BERSERK`) | 基础：费0；Vulnerable 2；下回合起每回合 +1 能量 | 未准入；统一需R01 | R03 | Vulnerable、每回合能量及Berserk活动状态的语义映射 | 基础脆弱2升级1，Artifact与生效回合需验证 | [S3:224](ironclad-card-audit.md#5-逐卡审计)；I8:1522 |
| Berserk (`BERSERK`) | 升级：费0；Vulnerable 1；同语义 | 未准入；统一需R01 | R03 | Vulnerable、每回合能量及Berserk活动状态的语义映射 | 基础脆弱2升级1，Artifact与生效回合需验证 | [S3:224](ironclad-card-audit.md#5-逐卡审计)；I8:1522 |
| Brutality (`BRUTALITY`) | 基础：费0；每回合开始失1 HP、抽1 | 未准入；统一需R01 | R03 | Brutality层数、HP/抽牌语义；Innate可由ID＋upgrade_count恢复 | 升级固有影响初始手牌；Rupture/Blood for Blood/NoDraw关联 | [S3:225](ironclad-card-audit.md#5-逐卡审计)；I8:1527 |
| Brutality (`BRUTALITY`) | 升级：费0；升级后 Innate，再同语义 | 未准入；统一需R01 | R03 | Brutality层数、HP/抽牌语义；Innate可由ID＋upgrade_count恢复 | 升级固有影响初始手牌；Rupture/Blood for Blood/NoDraw关联 | [S3:225](ironclad-card-audit.md#5-逐卡审计)；I8:1527 |
| Combust (`COMBUST`) | 基础：费1；回合末失1 HP，全体 D5 | 未准入；统一需R01 | R03,R11 | Combust伤害总量之外必须输出combustHpLoss语义字段 | 混合基础/升级多次叠加、Rupture触发及玩家/敌死亡中断待验 | [S3:226](ironclad-card-audit.md#5-逐卡审计)；I8:1535 |
| Combust (`COMBUST`) | 升级：费1；全体 D7 | 未准入；统一需R01 | R03,R11 | Combust伤害总量之外必须输出combustHpLoss语义字段 | 混合基础/升级多次叠加、Rupture触发及玩家/敌死亡中断待验 | [S3:226](ironclad-card-audit.md#5-逐卡审计)；I8:1535 |
| Corruption (`CORRUPTION`) | 基础：费3；Skills 费0，打出后 Exhaust | 未准入；统一需R01 | R02,R03 | 布尔活动状态、Skill有效费与条件性打出耗尽 | bit-only导出问题；卡固有exhaust不能代表Corruption生效后的实际行为 | [S3:227](ironclad-card-audit.md#5-逐卡审计)；I8:1531 |
| Corruption (`CORRUPTION`) | 升级：费2；同语义 | 未准入；统一需R01 | R02,R03 | 布尔活动状态、Skill有效费与条件性打出耗尽 | bit-only导出问题；卡固有exhaust不能代表Corruption生效后的实际行为 | [S3:227](ironclad-card-audit.md#5-逐卡审计)；I8:1531 |
| Dark Embrace (`DARK_EMBRACE`) | 基础：费2；每张牌 Exhaust 时抽1 | 未准入；统一需R01 | R03 | DarkEmbrace层数与每次耗尽抽牌语义 | NoDraw、Evolve、Fiend Fire与满手牌链；四区和候选暂停边界相关 | [S3:228](ironclad-card-audit.md#5-逐卡审计)；I8:1543 |
| Dark Embrace (`DARK_EMBRACE`) | 升级：费1；同语义 | 未准入；统一需R01 | R03 | DarkEmbrace层数与每次耗尽抽牌语义 | NoDraw、Evolve、Fiend Fire与满手牌链；四区和候选暂停边界相关 | [S3:228](ironclad-card-audit.md#5-逐卡审计)；I8:1543 |
| Demon Form (`DEMON_FORM`) | 基础：费3；回合开始 Str+2 | 可表达；已准入 | — | DemonForm层数、Strength和回合已有 | 升级只改每回合增量，不能把当前力量代替活动层 | [S3:229](ironclad-card-audit.md#5-逐卡审计)；I8:1539 |
| Demon Form (`DEMON_FORM`) | 升级：费3；回合开始 Str+3 | 可表达；已准入 | — | DemonForm层数、Strength和回合已有 | 升级只改每回合增量，不能把当前力量代替活动层 | [S3:229](ironclad-card-audit.md#5-逐卡审计)；I8:1539 |
| Evolve (`EVOLVE`) | 基础：费1；抽到 Status 时再抽1 | 未准入；统一需R01 | R03 | Evolve抽牌层数、Status类型和NoDraw | 状态牌抽牌链依赖每张实体；Curse不等于Status | [S3:230](ironclad-card-audit.md#5-逐卡审计)；I8:1547 |
| Evolve (`EVOLVE`) | 升级：费1；再抽2 | 未准入；统一需R01 | R03 | Evolve抽牌层数、Status类型和NoDraw | 状态牌抽牌链依赖每张实体；Curse不等于Status | [S3:230](ironclad-card-audit.md#5-逐卡审计)；I8:1547 |
| Feel No Pain (`FEEL_NO_PAIN`) | 基础：费1；每张牌 Exhaust 得 B3 | 可表达；已准入 | — | FeelNoPain活动层和block、逐牌耗尽已有 | 每张耗尽分别触发，不能仅看最终消耗堆计数差 | [S3:231](ironclad-card-audit.md#5-逐卡审计)；I8:1551 |
| Feel No Pain (`FEEL_NO_PAIN`) | 升级：费1；每张得 B4 | 可表达；已准入 | — | FeelNoPain活动层和block、逐牌耗尽已有 | 每张耗尽分别触发，不能仅看最终消耗堆计数差 | [S3:231](ironclad-card-audit.md#5-逐卡审计)；I8:1551 |
| Fire Breathing (`FIRE_BREATHING`) | 基础：费1；抽到 Status/Curse 时全体 D6 | 未准入；统一需R01 | R03 | FireBreathing伤害层、Status/Curse区分及抽取触发 | 是抽到触发，不是打出触发；辅助诅咒不能漏 | [S3:232](ironclad-card-audit.md#5-逐卡审计)；I8:1555 |
| Fire Breathing (`FIRE_BREATHING`) | 升级：费1；全体 D10 | 未准入；统一需R01 | R03 | FireBreathing伤害层、Status/Curse区分及抽取触发 | 是抽到触发，不是打出触发；辅助诅咒不能漏 | [S3:232](ironclad-card-audit.md#5-逐卡审计)；I8:1555 |
| Inflame (`INFLAME`) | 基础：费1；Str+2 | 可表达；已准入 | — | 已有Strength即可，升级2→3由静态语义表达 | 没有另加Inflame持久层的必要证据 | [S3:233](ironclad-card-audit.md#5-逐卡审计)；I8:1559 |
| Inflame (`INFLAME`) | 升级：费1；Str+3 | 可表达；已准入 | — | 已有Strength即可，升级2→3由静态语义表达 | 没有另加Inflame持久层的必要证据 | [S3:233](ironclad-card-audit.md#5-逐卡审计)；I8:1559 |
| Juggernaut (`JUGGERNAUT`) | 基础：费2；每次获得 Block，随机敌人 D5 | 未准入；统一需R01 | R03,R09 | Juggernaut层与每次获得格挡触发、随机敌目标语义 | Rage/Feel No Pain/Metallicize/Block Potion逐次触发，不让策略选随机目标 | [S3:234](ironclad-card-audit.md#5-逐卡审计)；I8:1563 |
| Juggernaut (`JUGGERNAUT`) | 升级：费2；随机敌人 D7 | 未准入；统一需R01 | R03,R09 | Juggernaut层与每次获得格挡触发、随机敌目标语义 | Rage/Feel No Pain/Metallicize/Block Potion逐次触发，不让策略选随机目标 | [S3:234](ironclad-card-audit.md#5-逐卡审计)；I8:1563 |
| Metallicize (`METALLICIZE`) | 基础：费1；回合末 B3 | 可表达；已准入 | — | Metallicize层、block和回合已有 | 回合末格挡与Barricade/Juggernaut及敌行动时序相关 | [S3:235](ironclad-card-audit.md#5-逐卡审计)；I8:1575 |
| Metallicize (`METALLICIZE`) | 升级：费1；回合末 B4 | 可表达；已准入 | — | Metallicize层、block和回合已有 | 回合末格挡与Barricade/Juggernaut及敌行动时序相关 | [S3:235](ironclad-card-audit.md#5-逐卡审计)；I8:1575 |
| Rupture (`RUPTURE`) | 基础：费1；从卡牌失 HP 时 Str+1 | 未准入；统一需R01 | R03 | Rupture层及卡牌失HP触发语义，结果Strength可复用 | 不需要默认加入全部伤害历史；自伤与敌方攻击须由后端区分 | [S3:236](ironclad-card-audit.md#5-逐卡审计)；I8:1583 |
| Rupture (`RUPTURE`) | 升级：费1；Str+2 | 未准入；统一需R01 | R03 | Rupture层及卡牌失HP触发语义，结果Strength可复用 | 不需要默认加入全部伤害历史；自伤与敌方攻击须由后端区分 | [S3:236](ironclad-card-audit.md#5-逐卡审计)；I8:1583 |

## 3. 覆盖统计与重点版本差异

| 检查项 | 结果 |
|---|---|
| 独立卡牌类／版本行 | 75／150；每类恰有基础和升级各1行 |
| 当前后端结算入口／本次对应正版类／文本键 | 75／75／75；静态存在性，不是运行验收 |
| 当前public准入版本 | 69；其余81明确标为未准入 |
| Armaments | 基础需手牌单选；升级全手牌升级，不需要新单选出口 |
| True Grit | 基础随机；升级改主动选牌，同时B7→9；当前仅基础准入 |
| Limit Break | 升级取消固有消耗；不因此新增交互阶段 |
| Brutality | 升级增加Innate；可由ID/升级字典恢复，不必新历史 |
| Searing Blow | 已有整数upgrade_count载体；准入与多次升级伤害未实现 |
| Ghostly Armor | 两版均Ethereal，不能沿用已撤销的“升级移除虚无”说法 |
| Whirlwind | 两版X均由能量/执行上下文决定，不增加玩家X选择 |
| Disarm | 基础与升级需分开：当前后端升级仍固定-2的静态差异未关闭 |

## 4. 可复核源码指纹

| 文件 | SHA256 |
|---|---|
| `sts/env/public-battle-contract.json` | `cc29dad191bd560d6b4f03d048387ba2a1a41d19bb08b1ea3891dcf618e4bea5` |
| `sts/env/public_battle.py` | `8fdc06240bd59168f1b0b0551643002eacbaed2f03cf5e9fbb463c1dbf84f8a6` |
| `sts/env/real_deck.py` | `881141c38eba470c9dc2a02bc64e2ca30cee883238187c94619e0198d11abe0a` |
| `sts/env/real-deck-batch.json` | `59c837a108ae7275c61a187dd3bc19e190953a15ac8fe2d7f5bbb37c5fc0acfe` |
| `sts/env/wrappers.py` | `113f81e4ec741325d1dc56e809ebc018b172fca3006c1c3f0bdf29621fe426b4` |
| `sts/models/mlp.py` | `2eb9fedfd8d1fe44ad974070ce83539613fe5733000115f6ce91fce6376ee540` |
| `sts/train/ppo.py` | `def98cadeb3434f35e999cebf9d1979c60237cdf16a3de056858c0434e7f3b4c` |
| `third_party/sts_lightspeed/bindings/public-battle-env.cpp` | `231a0cbb981368f64f7b68721bddfb8896a0a315280278bd3ccd114dddd79c82` |
| `third_party/sts_lightspeed/src/combat/BattleContext.cpp` | `a7b99e59d63d95d6d46115f007ceceef81d71e337e00a9ef2affe4f660eeb35d` |

本次结构验证与公开入口检查的具体结果将记在下面；完整本地清点证据位于被忽略的 `reference/ironclad-input-audit-evidence.json`。正版内容未复制进模拟器，反编译源码未入库。

## 5. 本次验证记录

- 覆盖清点通过：75个唯一卡名、150行，基础/升级各1行；75/75正版red类、75/75英文卡片文本键、75/75当前后端结算case对应；中央契约准入69版本、未准入81版本。清点脚本断言通过。
- `python -m pytest -q tests/test_public_battle.py tests/test_real_deck_batch.py`：**22 passed in 0.70s**。仅覆盖现有公开包装与冻结批次，不证明未来全卡行为或并发新增comparison草稿通过。
- `python scripts/check-spec-v6.py`：**PASS**。`git diff --check`通过；新文档另外检查表格列数、需求编号、相对链接和尾部空白。
- 未运行：全75卡逐版本行为测试、全部组合测试、全仓回归、并发新增comparison模型/采集验收、PPO训练、正式评估、旧checkpoint到新架构迁移。
- 旧报告540局与566测试等数字仅作为既有记录引用，没有在本轮重跑。静态风险与已证实运行失败分别标记；本轮没有把后端TODO自动判为运行Bug。
- 本轮仅交付审计文档；完成检查时工作区另有并发新增comparison文件和`.gitignore`变动，未覆盖或回退。未commit/push。
