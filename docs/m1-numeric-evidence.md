# M1 原十张卡数值证据补充

日期：2026-09-11  
状态：M1 证据材料；不是正式 reset 白名单，不开放卡牌，不修改后端、训练代码或权威决策文档。

本材料只补齐 Week 5–6 计划所称的原十张卡：Bash、Anger、Cleave、Shrug It Off、True Grit、Inflame、Demon Form、Spot Weakness、Whirlwind、Power Through。全卡报告和 `m1-candidate-batches.md` 仍然是候选方案；扩展卡行为测试仍未执行。

## 1. 证据指纹与方法

| 项目 | 值 |
|---|---|
| 正版文件 | `E:\SteamLibrary\steamapps\common\SlayTheSpire\desktop-1.0.jar` |
| JAR SHA-256 | `cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673` |
| JAR 内文本 | `localization/eng/cards.json`，大小 62,159 bytes，CRC32 `6a4eaa79` |
| 后端 commit | `7476a81954020087da31d41d16fddf475746ec2d` |
| 后端实际构建 | `third_party/sts_lightspeed/build/slaythespire.cp313-win_amd64.pyd`，SHA-256 `a4b1745d79d848354da8783416d4728a8aec255d359e93687c62cd1ef9d16fbf` |
| 核验时间 | 2026-09-11 |

正版 class 的 `<init>` JVM 偏移 11 是传给 `AbstractCard.<init>` 的基础费用；随后写入的 `baseDamage`、`baseBlock`、`baseMagicNumber` 是基础值；`upgrade()` 中 `upgradeDamage/upgradeBlock/upgradeMagicNumber` 的整数参数是升级增量。最终值按基础值加升级增量计算，特殊升级在表中单列。

本轮用标准 ZIP/JVM classfile 解析读取上述 class entry，并输出构造器/升级方法的指令偏移；没有把社区 wiki 或 HF 快照作为数值真相。`cards.json` 只提供同一正版文件中的效果文本和升级文本，占位符数值由 class 证据填入。

## 2. 原十张数值表

`D`=伤害，`B`=格挡，`M`=卡面 magic number；`→` 表示升级后最终值。`ALL` 与 `SELF_AND_ENEMY` 是正版目标语义；它们不代表玩家一定要额外选择敌人。

| 英文标识 / 名称 | 正版基础版 | 正版升级版 | JAR class 定位 | 正版文本键与语义 | 锁定后端定位及静态对照 |
|---|---|---|---|---|---|
| `BASH` / Bash | 费2；D8；M2 Vulnerable | 费2；D10；M3 Vulnerable | `red/Bash.class`：`<init>@11` 费2，`@34` `baseDamage=8`，`@40` `baseMagicNumber=2`；`upgrade@12` `upgradeDamage(2)`，`@18` `upgradeMagicNumber(1)`；目标 `ENEMY@27` | `cards.json` 键 `Bash`：Deal damage；Apply Vulnerable | `BattleContext.cpp:980-984` 使用 D8→10、Vulnerable 2→3；`Cards.h:760-780` 费用组；静态数值一致；E1 有，E2 仅当前 registry，E3 升级未运行 |
| `ANGER` / Anger | 费0；D6；弃牌堆加 1 张 Anger | 费0；D8；同语义 | `red/Anger.class`：`<init>@11` 费0，`@34` `baseDamage=6`；`upgrade@12` `upgradeDamage(2)`；目标 `ENEMY@27` | `cards.json` 键 `Anger`：Deal damage；Add a copy into discard | `BattleContext.cpp:975-978` 使用 D6→8 并生成副本；`Cards.h:705-743` 费用组；静态数值一致；E1 有，E2 无，E3 未运行 |
| `CLEAVE` / Cleave | 费1；ALL；D8 | 费1；ALL；D11 | `red/Cleave.class`：`<init>@11` 费1，`@34` `baseDamage=8`，`@40` `isMultiDamage=true`；`upgrade@12` `upgradeDamage(3)`；目标 `ALL_ENEMY@27` | `cards.json` 键 `Cleave`：Deal damage to ALL enemies | `BattleContext.cpp:1011-1015` 使用 D8→11；`Cards.h:705-780` 费用组；静态数值一致；E1 有，E2 无，E3 未运行 |
| `SHRUG_IT_OFF` / Shrug It Off | 费1；B8；抽1 | 费1；B11；抽1 | `red/ShrugItOff.class`：`<init>@11` 费1，`@34` `baseBlock=8`；`upgrade@12` `upgradeBlock(3)`；目标 `SELF@27` | `cards.json` 键 `Shrug It Off`：Gain Block；Draw 1 | `BattleContext.cpp:1445-1448` 使用 B8→11、Draw1；`Cards.h:745-758` 费用组；静态数值一致；E1 有，E2 无，E3 未运行 |
| `TRUE_GRIT` / True Grit | 费1；B7；随机 Exhaust 1 张 | 费1；B9；玩家选择 Exhaust 1 张 | `red/TrueGrit.class`：`<init>@11` 费1，`@34` `baseBlock=7`；`upgrade@12` `upgradeBlock(2)`，`@20-26` 改用 `UPGRADE_DESCRIPTION`；目标 `SELF@27` | `cards.json` 键 `True Grit`：基础版随机 Exhaust；升级版选择 Exhaust | `BattleContext.cpp:1482-1489`、`Actions.cpp:354-365,824-835`；B7→9 数值一致，选择方式确实改变；E1 有，E2 无，E3 未运行 |
| `INFLAME` / Inflame | 费1；M2 Strength | 费1；M3 Strength | `red/Inflame.class`：`<init>@11` 费1，`@34` `baseMagicNumber=2`；`upgrade@12` `upgradeMagicNumber(1)`；目标 `SELF@27` | `cards.json` 键 `Inflame`：Gain Strength | `BattleContext.cpp:1559-1561` 直接增加 Strength 2→3；`Cards.h:705-743` 费用组；后端没有凭空新增另一活动层；E1 有，E2 无，E3 未运行 |
| `DEMON_FORM` / Demon Form | 费3；M2：每回合开始 Strength+2 | 费3；M3：每回合开始 Strength+3 | `red/DemonForm.class`：`<init>@11` 费3，`@34` `baseMagicNumber=2`；`upgrade@12` `upgradeMagicNumber(1)`；目标 `NONE@27` | `cards.json` 键 `Demon Form`：At the start of your turn, gain Strength | `BattleContext.cpp:1539-1541` 使用 Strength 2→3；`Cards.h:786-790` 费用组；静态数值一致；E1 有，E2 无，E3 未运行 |
| `SPOT_WEAKNESS` / Spot Weakness | 费1；若意图攻击，M3 Strength | 费1；若意图攻击，M4 Strength | `red/SpotWeakness.class`：`<init>@11` 费1，`@34` `baseMagicNumber=3`；`upgrade@12` `upgradeMagicNumber(1)`；目标 `SELF_AND_ENEMY@27` | `cards.json` 键 `Spot Weakness`：If enemy intends to attack, gain Strength | `BattleContext.cpp:1450-1452`、`Actions.cpp:1225-1230` 使用 Strength 3→4 并检查攻击意图；`Cards.h:673-680` 目标映射；静态数值一致；E1 有，E2 无，E3 未运行 |
| `WHIRLWIND` / Whirlwind | 费X；ALL；D5×X | 费X；ALL；D8×X | `red/Whirlwind.class`：`<init>@11` 费-1，`@34` `baseDamage=5`，`@40` `isMultiDamage=true`；`upgrade@12` `upgradeDamage(3)`；目标 `ALL_ENEMY@27` | `cards.json` 键 `Whirlwind`：Deal damage to ALL enemies X times | `BattleContext.cpp:1178-1185`、`Actions.cpp:1233-1259` 使用 `energyOnUse`；`reference/sts1-decompiled/m1-review/Whirlwind.txt` 与 `WhirlwindAction.txt` 的定点记录表明由能量传递 X，没有玩家另选 X 阶段；E1 有，E2 无，零能量/免费出牌 E3 未运行 |
| `POWER_THROUGH` / Power Through | 费1；B15；手牌加 2 Wound | 费1；B20；手牌加 2 Wound | `red/PowerThrough.class`：`<init>@11` 费1，`@34` `baseBlock=15`，`@40-47` 预览 Wound；`upgrade@12` `upgradeBlock(5)`；目标 `SELF@27` | `cards.json` 键 `Power Through`：Add 2 Wounds into hand；Gain Block | `BattleContext.cpp:1407-1410` 使用 B15→20、固定 2 张 Wound；`Actions.cpp:227-236` 生成卡入手牌；静态数值一致；E1 有，E2 无，E3 未运行 |

## 3. 数值核验结果与边界

- 10/10 卡的基础费用、基础主要数值、升级差异和目标/文本键均已给出可复核的 JAR entry 与 JVM 偏移。
- 10/10 的锁定后端结算入口均已定位。除现有报告另列的后端风险外，本表没有把静态一致写成 runtime 行为通过。
- `Whirlwind` 的本轮结论是“X 由后端从能量传入，不能据此要求新增玩家 X 选择动作”；零能量合法性、免费出牌和能量快照仍待行为测试。
- `Power Through` 的 Wound 是可达生成类别；本材料只核实固定每次生成 2 张，不证明 50 回合/任意卡组下的非手牌容量上界。
- `True Grit` 升级版由随机 Exhaust 改为玩家主动选择；当前 Python 31 位动作没有选择屏动作，因此不能因数值证据完成而开放。
- 当前 registry 仍只有 Bash、Defend、Strike；数值证据完成不等于卡牌注册、观测、容量或行为验收完成。
- 本材料不修改 `docs/decisions.md` 的 U3 状态；是否销账、是否批准候选，仍需按决策日志流程登记并经过候选行为收口。

## 4. 证据等级

| 项目 | 状态 |
|---|---|
| 正版 class 数值与升级差异 | 已核验，JAR 一手文件；10/10 有 method/offset 定位 |
| 正版文本语义 | 已核验，JAR `localization/eng/cards.json` |
| 锁定后端静态常量/结算入口 | 已定位；不等于行为等价 |
| 当前项目接口可用 | 仅 Bash/Defend/Strike 的部分基础链路；其余未注册 |
| 原十张扩展行为测试 | 未执行 |
| M2 固定牌组、容量与观测契约 | 未锁定 |
