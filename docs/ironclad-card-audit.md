# Ironclad 全卡兼容性审计（M1 范围扩展）

审计日期：2026-09-11（当日复核修订；证据见 §10）  
工作区：`C:\Users\19091\Desktop\sts2`  
审计对象：STS1 Ironclad，正版 JAR 与锁定 `sts_lightspeed` 战斗后端  
报告性质：只记录 M1 候选审计与收口状态；不批准正式卡表，不修改 30–40 类目标、训练代码、后端或正式白名单。状态同步不等于开放卡牌或完成 M2。

## 1. 结论先行

- 正版 JAR `com/megacrit/cardcrawl/cards/red/` 有 **75 个 Ironclad 卡牌类**：32 Attack、29 Skill、14 Power。基础牌 `Strike_Red`、`Defend_Red`、`Bash` 也包含在 75 个类中。
- 75/75 类均能映射到锁定后端 `CardId`，75/75 类均出现在后端的 Attack、Skill 或 Power 结算入口；这只是“上游有枚举/代码入口”，不是项目接口可用，更不是行为验收。
- 当前 Python `CardRegistry` 只有 Bash、Defend、Strike 3 类，**72 类未注册**。当前 reset 仍只生成固定十张初始牌，所有升级版也没有正式 reset 入口。
- 当前动作是 31 位 `slot * 3 + target`：每个手牌槽位只有目标列 0、1、2，30 为结束回合。二次选择手牌/牌堆、以及间接打出后进入选择屏的卡，不能由当前 Python wrapper 完整表达。
- 本次逐卡结论（按 150 个“卡牌版本”计）：A 6 个、B 123 个、C 16 个、D 5 个。A 仅表示未发现接口阻塞，可进入后续实现与验收候选；**A 不表示已实现或验收通过**。
- 已静态发现的正版—后端差异包括：升级版 Disarm 的减力量数值、Iron Wave 的格挡计算调用，以及 Fiend Fire 的动作队列计数风险。它们在报告中单列，不能用“后端有 case”掩盖。

### 1.1 结论字母的本报告解释

| 结论 | 本报告含义 |
|---|---|
| A | 当前动作/观测语法没有新增结构性阻塞；仍需注册、配置和行为验收。 |
| B | 需要补注册、观测、动态字段、容量契约或后端结算校准；不必先迁移动作协议。 |
| C | 需要动作协议迁移，例如二次选牌、或间接效果可能打开选择阶段。 |
| D | 来源或行为存在尚未裁定的冲突/未核实差异，暂不把它作为候选。 |

## 2. 审计依据与可复现指纹

### 2.1 文档依据

已先读取并按要求采用以下权威顺序：

1. `AGENTS.md`
2. `spec-v6.md`
3. `docs/decisions.md`
4. `docs/mechanics.md`
5. `docs/learning-path-v2.md`
6. `docs/week-5-6-plan.md`

本报告遵守的关键边界来自 `spec-v6.md` §4.1、§4.2、§4.3.1、§9、§10，以及 `docs/week-5-6-plan.md` §2、§4、§5：当前 30–40 类只是目标，不是白名单；需要二次选择的卡不能让后端自动代选；容量必须先证明上界；超过容量必须拒绝而不是静默截断。

### 2.2 正版游戏文件

| 项目 | 值 |
|---|---|
| 文件 | `E:\SteamLibrary\steamapps\common\SlayTheSpire\desktop-1.0.jar` |
| SHA-256 | `cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673` |
| 文件大小 | 365,086,855 bytes |
| 本机文件时间 | 2024-03-07 12:32:48 |
| JAR 内版本信息 | `build.properties` 只有 `distributor=steam`；具体游戏补丁版本字符串未查明 |
| 数值/语义入口 | `com/megacrit/cardcrawl/cards/red/<Class>.class` 的 `<init>`、`upgrade()`、`use()`；`localization/eng/cards.json` 的卡牌文本 |

正版数值来自 JAR class 的构造器/升级方法常量；效果语义来自同一 JAR 的 class 与 `localization/eng/cards.json`。本轮没有把 HF/wiki 当作唯一数值来源，也没有用反编译产物替代正版 class 证据。

### 2.3 锁定后端与项目适配层

| 项目 | 值 |
|---|---|
| 工作区 HEAD | `80d2340` |
| 上游仓库 | `https://github.com/gamerpuppy/sts_lightspeed` |
| 锁定/实际上游 commit | `7476a81954020087da31d41d16fddf475746ec2d` |
| 锁定 pybind11 commit | `a2e59f0e7065404b44dfe92a28aca47ba1378dc4` |
| 适配补丁 | `patches/lightspeed-battle-env.patch`，SHA-256 `dfe95d2bbd93300932d187c969b6b6ea9aa4a4783da4169b1b32bd1160cb878c` |
| 当前扩展 | `third_party/sts_lightspeed/build/slaythespire.cp313-win_amd64.pyd`，SHA-256 `a4b1745d79d848354da8783416d4728a8aec255d359e93687c62cd1ef9d16fbf` |
| 适配器 | `sts/env/lightspeed.py`、`sts/env/registry.py`、`sts/env/wrappers.py` |

上游 checkout 当前有适配补丁造成的 `bindings/*.cpp`、`bindings/*.h` 和 `pybind11` 工作树改动，以及 ignored build 目录；本报告以这份实际 patched checkout 的源码和扩展为准，不把干净上游 commit 误写成当前运行代码。

### 2.4 实际运行的验证

本轮实际运行：

- `python -m pytest -q tests/test_lightspeed_adapter.py tests/test_cpp_env.py tests/test_wrappers.py tests/test_masked_policy.py`：**89 passed，0 failed**。
- `python scripts/check-spec-v6.py`：**PASS**。
- 当前扩展 probe：确认 `CARD_FEATURES`、`ENEMY_FEATURES`、`GLOBAL_FEATURES`，确认 registry 3 类、registry hash `c5f1a63e6bc3ac914b6aa5c748f46a7aec92c5bc35c46289dd262b1899e6b9aa`，以及 seed `100000` 双虱初态四区计数 `5/5/0/0`。
- 只读静态覆盖脚本：正版 JAR 75 类 → 后端枚举 **75/75**；正版 JAR 75 类 → `useAttackCard`、`useSkillCard`、`usePowerCard` **75/75**。

未运行：任何扩展卡或升级版的逐卡行为测试、扩展后双 wrapper 回归、容量上界验收、训练、短训、正式评估。现有 89 项通过只覆盖当前最小环境与接口契约，不能升级为全卡行为通过。

## 3. 当前接口审计基线

### 3.1 动作协议

- `sts/env/lightspeed.py:54-56` 与补丁 `patches/lightspeed-battle-env.patch:443-445`：`MAX_HAND=10`、`MAX_ENEMIES=5`、`ACTION_COUNT=31`。
- `patches/lightspeed-battle-env.patch:144-160`：只枚举 `handIdx = action // 3`、`targetIdx = action % 3`；无目标牌只允许目标列 0；后端 5 行敌人观测不等于动作可选择第 4、5 个敌人。
- `sts/env/actions.py:10-51`：教学 Python 层同样只有 3 个目标列；它不是正式 C++ 训练通道，但说明项目统一动作语义仍是 31 位。
- `third_party/sts_lightspeed/src/sim/search/Action.cpp:104-249`：上游内部其实有 `SINGLE_CARD_SELECT`、`MULTI_CARD_SELECT` 等动作类型；当前 Python binding 的 31 位 `IroncladBattleEnv.step()` 没有把这些动作类型暴露给模型。

因此，`Armaments`、`Burning Pact`、`Dual Wield`、`Exhume`、`Headbutt`、`Warcry` 等不能由当前 31 位动作完整表达；Whirlwind 的 X 由能量决定，不需要玩家额外选择数值。后端内部有选择 helper 不等于项目 wrapper 可用。

### 3.2 观测与注册

- C++ 卡牌原始字段只有 `backend_card_id/location/upgraded/cost/cost_known`：补丁 `:392-403`，Python 白名单 `sts/env/lightspeed.py:23-81`。
- Python `CardObservation` 只有 `card_id/location/upgraded/cost/cost_known/target_kind`：`sts/env/lightspeed.py:59-67`。
- 项目注册表 `sts/env/registry.py:109-113` 当前只有：Bash backend 25、Defend_Red backend 104、Strike_Red backend 321。
- `sts/env/wrappers.py:26-27` 的卡牌类别只有 `card_id/location/target_kind/upgraded` 和 `cost`；没有 card type、damage/block/magic number、主动 Power、Artifact、动态 specialData、每张卡的战斗内升级次数等字段。
- C++ 补丁 `:203-215` 的 global 只有 HP、Block、Energy、回合、四区计数、敌人总 HP、Strength、Vulnerable、Weak。玩家的 Barricade、Corruption、Rage、Rupture 等活动状态以及敌方 Artifact 不在当前规范输入。
- `docs/decisions.md:131-138` 的信息边界仍然有效：只能使用玩家可见信息；不能用 `info`、seed、RNG 或完整内部牌序补洞。

### 3.3 容量

- 手牌：后端 `CardManager::MAX_HAND_SIZE=10`，`third_party/sts_lightspeed/include/combat/CardManager.h:24-41`。
- 后端牌堆：当前 CMake 没有启用 `sts_card_manager_use_fixed_list`，实际 `CardManager` 使用 vector；即使头文件保留 `MAX_GROUP_SIZE=64`，也不能把它当作本次运行时的生成容量契约。
- wrapper：`PILE_CAPACITY=10`，`sts/env/wrappers.py:23-25`；`_prepare()` 在 `:244-279` 对三类非手牌区域合计超 10 直接报错，未静默截断。
- 因此，固定十张无生成牌组的四区总量可证明不超过 10；含 Anger、Wound、Dazed、Burn、随机攻击或复制的卡，必须先给出“最大执行次数 × 每次生成量”的证明，并同步状态/registry/capacity 版本。一次 probe 成功不构成容量验收。

### 3.4 证据等级

| 标记 | 意义 |
|---|---|
| E1 | 上游有枚举、费用/目标表和结算 `case`；静态入口存在。定位见逐卡的 `B:<行号>`。 |
| E2 | 当前项目 registry、binding、wrapper 可以传递该卡。现在只有 3 个基础类部分满足。 |
| E3 | 本轮实际行为测试覆盖到该卡的该版本。当前 E3 只覆盖最小三张牌的基础版；扩展卡和全部升级版均为“未运行”。 |

## 4. 全卡覆盖清单与遗漏项

### 4.1 正版 JAR 的 75 类清单

**Attack（32）**：

Anger、Bash、Blood for Blood、Bludgeon、Body Slam、Carnage、Clash、Cleave、Clothesline、Dropkick、Feed、Fiend Fire、Headbutt、Heavy Blade、Hemokinesis、Immolate、Iron Wave、Perfected Strike、Pommel Strike、Pummel、Rampage、Reaper、Reckless Charge、Searing Blow、Sever Soul、Strike、Sword Boomerang、Thunderclap、Twin Strike、Uppercut、Whirlwind、Wild Strike。

**Skill（29）**：

Armaments、Battle Trance、Bloodletting、Burning Pact、Defend、Disarm、Double Tap、Dual Wield、Entrench、Exhume、Flame Barrier、Flex、Ghostly Armor、Havoc、Impervious、Infernal Blade、Intimidate、Limit Break、Offering、Power Through、Rage、Second Wind、Seeing Red、Sentinel、Shockwave、Shrug It Off、Spot Weakness、True Grit、Warcry。

**Power（14）**：

Barricade、Berserk、Brutality、Combust、Corruption、Dark Embrace、Demon Form、Evolve、Feel No Pain、Fire Breathing、Inflame、Juggernaut、Metallicize、Rupture。

### 4.2 遗漏项

- 正版 JAR → 锁定后端 `CardId`：无遗漏，75/75。
- 正版 JAR → 后端三类结算入口：无遗漏，75/75。
- 正版 JAR → 当前 `DEFAULT_CARD_REGISTRY`：仅 Bash、Defend、Strike 3/75；**遗漏 72 类**：除这三张外的全部卡。
- 正版 JAR → 当前 reset 的实际牌组：仅 Strike×5、Defend×4、Bash×1；当前只有上述三类基础牌进入固定 reset，尚不能任意配置全部 75 类。
- 当前动作协议可直接表达的“单次出牌动作”不等于卡牌可用：二次选择、X 费执行正确性、选择屏闭包、动态状态、生成牌和容量仍需单独过批次验收。

## 5. 逐卡审计

### 5.1 表内符号

- 数值：`费` 为基础费用；`D` 伤害；`B` 格挡；`M` 卡面 magic number；`→` 表示升级后值。动态值写公式。
- 动作：`T` 单一敌方目标；`N` 无玩家目标，当前协议用 `target=0`；`S` 二次选择；`X` X 费能量结算（不是玩家数值选择）；`R` 后端内部随机；`I` 间接打出后可能出现额外动作阶段。
- 观测：`V0` 当前字段原则上足够；`V1` 缺玩家/敌方持久状态或 Artifact；`V2` 缺 card type、Strike 计数或动态 specialData；`V3` 依赖生成牌/升级次数/牌堆构成扩展。
- 容量：`K0` 无生成；`K1` 只移动/抽取/消耗固定牌；`K2` 固定生成或复制，须证明上界；`K3` 随机/间接生成或可重复复制，当前无上界证明。
- 每行 `结论（基/升）` 分别给出基础版与升级版；`E2`、`E3` 的“否”不是说后端没有代码，而是说当前项目接口/测试没有完成。

### 5.2 Attack

| 英文标识 / 名称 | 正版基础版 | 正版升级版 | 动作 / 观测 / 容量 | 原版与后端差异；当前支持证据 | 阻塞 / 建议批次 | 结论（基/升） |
|---|---|---|---|---|---|---|
| `ANGER` / Anger | 费0；D6；打出后向弃牌堆加 1 张 Anger | 费0；D8；同语义 | T；V0；K2，重复生成上界未证明 | 结算 `BattleContext.cpp:975-978`；E1；E2 否；E3 未运行 | REG、CAP；生成牌批次 | B / B |
| `BASH` / Bash | 费2；D8；Vulnerable 2 | 费2；D10；Vulnerable 3 | T；V0；K0 | `BattleContext.cpp:980-984`；E1；E2 部分；E3 基础版已由 C++ 环境测试间接覆盖，升级未运行 | 仅需正式升级 reset 与升级回归 | A / A |
| `BLOOD_FOR_BLOOD` / Blood for Blood | 费4；D18；每次本战斗失 HP 后费用降低 1 | 费3；D22；同语义 | T；V0（手牌当前费）；K0 | `BattleContext.cpp:995-997`；成本 `Cards.h:792-793`；E1；E2 否；E3 未运行 | REG；动态费用回归 | B / B |
| `BLUDGEON` / Bludgeon | 费3；D32 | 费3；D42 | T；V0；K0 | `BattleContext.cpp:999-1001`；E1；E2 否；E3 未运行 | REG | B / B |
| `BODY_SLAM` / Body Slam | 费1；D=当前 Block | 费0；D=当前 Block | T；需 Block，V0；K0 | `BattleContext.cpp:991-993`；成本 `Cards.h:803-808`；E1；E2 否；E3 未运行 | REG；需验证升级费用与当前 Block 同步 | B / B |
| `CARNAGE` / Carnage | 费2；Ethereal；D20 | 费2；Ethereal；D28 | T；V0；K1（Ethereal 回合末进入消耗堆） | `BattleContext.cpp:1003-1005`；`Cards.h:466-484`；E1；E2 否；E3 未运行 | REG、EXHAUST；需开放消耗堆 | B / B |
| `CLASH` / Clash | 费0；仅当手牌全为 Attack 可出；D14 | 费0；D18 | T；手牌 card type 需可查，V2；K0 | `CardInstance.cpp:260-267,295-298`、`BattleContext.cpp:1007-1009`；E1；E2 否；E3 未运行 | REG、OBS（card type） | B / B |
| `CLEAVE` / Cleave | 费1；ALL；全体 D8 | 费1；全体 D11 | N；V0；K0 | `BattleContext.cpp:1011-1015`；E1；E2 否；E3 未运行 | REG；`ALL_ENEMY` 被当前 target_kind 折叠为 N，但 card_id 仍需注册 | B / B |
| `CLOTHESLINE` / Clothesline | 费2；D12；Weak 2 | 费2；D14；Weak 3 | T；V1（敌方 Artifact 缺失）；K0 | `BattleContext.cpp:1017-1020`；E1；E2 否；E3 未运行 | REG、OBS（Artifact） | B / B |
| `DROPKICK` / Dropkick | 费1；D5；若目标 Vulnerable，+1 能量并抽1 | 费1；D8；同语义 | T；敌方 Vulnerable 已有，V0；K0 | `BattleContext.cpp:1028-1030`、`Actions.cpp:1035-1046`；E1；E2 否；E3 未运行 | REG | B / B |
| `FEED` / Feed | 费1；D10；Fatal 时 Max HP +3；Exhaust | 费1；D12；Max HP +4；Exhaust | T；V0；K1 | `BattleContext.cpp:1032-1034`、`Actions.cpp:1070-1088`；E1；E2 否；E3 未运行 | REG、EXHAUST；Fatal/Max HP 回归 | B / B |
| `FIEND_FIRE` / Fiend Fire | 费2；Exhaust 手牌；每张 D7 | 费2；每张 D10 | T；自动耗尽，无二次选择；V0；K1 | `BattleContext.cpp:1036-1038`、`Actions.cpp:1091-1100`；静态上游入口存在，但攻击/耗尽数量依赖出牌移除时序；E1；E2 否；E3 未运行 | 结算时序需定点行为测试；容量/耗尽回归 | D / D |
| `HEADBUTT` / Headbutt | 费1；D9；把弃牌堆 1 张放到抽牌堆顶 | 费1；D12；同语义 | T+S（选择弃牌）；V3；K1 | `BattleContext.cpp:1049-1052`、`Actions.cpp:811-821`、`BattleContext.cpp:3038-3044`；E1；E2 否；E3 未运行 | ACT、REG；需要牌堆选择动作 | C / C |
| `HEAVY_BLADE` / Heavy Blade | 费2；D14；Strength 按 3 倍影响 | 费2；D14；Strength 按 5 倍影响 | T；需 Strength，V0；K0 | `BattleContext.cpp:1054-1059`；正版 JAR `HeavyBlade.class` 为 M3→5；后端先加 `(up ? 4 : 2) * Strength`，再经 `calculateCardDamage` 加一次力量，合计 3/5 倍；原倍率缺陷结论撤销；E1；E2 否；E3 未运行 | REG；力量/Weak/Vulnerable 组合回归 | B / B |
| `HEMOKINESIS` / Hemokinesis | 费1；失2 HP；D15 | 费1；失2 HP；D20 | T；HP/自伤交互，V1；K0 | `BattleContext.cpp:1061-1066`；E1；E2 否；E3 未运行 | REG、OBS（Rupture 等自伤状态） | B / B |
| `IMMOLATE` / Immolate | 费2；全体 D21；弃牌堆加 Burn | 费2；全体 D28；同语义 | N；V0；K2；Burn 需注册，重复生成上界未证明 | `BattleContext.cpp:1068-1073`；E1；E2 否；E3 未运行 | REG、CAP；状态牌批次 | B / B |
| `IRON_WAVE` / Iron Wave | 费1；B5+D5 | 费1；B7+D7 | T；Block/Strength，V0；K0 | `BattleContext.cpp:1075-1078`；后端对 Block 调用了两次 `calculateCardBlock`，有 Dexterity 时可能与正版不符；E1；E2 否；E3 未运行 | 后端结算疑点，先做 Dexterity 对拍 | D / D |
| `PERFECTED_STRIKE` / Perfected Strike | 费2；D6 + 2×所有名称含 Strike 的牌 | 费2；D6 + 3×上述数量 | T；需要 Strike 计数/全牌可见类别，V2；K0 | `BattleContext.cpp:1087-1092`；`Cards.h:512-531`；E1；E2 否；E3 未运行 | REG、OBS（Strike 元数据/计数） | B / B |
| `POMMEL_STRIKE` / Pommel Strike | 费1；D9；抽1 | 费1；D10；抽2 | T；V0；K1 | `BattleContext.cpp:1095-1098`；E1；E2 否；E3 未运行 | REG、CAP（抽牌/手牌） | B / B |
| `PUMMEL` / Pummel | 费1；D2×4；Exhaust | 费1；D2×5；Exhaust | T；V0；K1 | `BattleContext.cpp:1100-1107`；E1；E2 否；E3 未运行 | REG、EXHAUST | B / B |
| `RAMPAGE` / Rampage | 费1；D8；本战斗每次打出后该牌伤害 +5 | 费1；D8；每次 +8 | T；需每张卡的 combat specialData，V2；K0 | `BattleContext.cpp:1109-1118`、`CardInstance.cpp:89-99`；E1；E2 否；E3 未运行 | REG、OBS（specialData） | B / B |
| `REAPER` / Reaper | 费2；全体 D4；按未格挡伤害治疗；Exhaust | 费2；全体 D5；同语义 | N；V0；K1 | `BattleContext.cpp:1121-1125`、`Actions.cpp:1130-1151`；E1；E2 否；E3 未运行 | REG、EXHAUST | B / B |
| `RECKLESS_CHARGE` / Reckless Charge | 费0；D7；抽牌堆加入 Dazed | 费0；D10；同语义 | T；V0；K2；Dazed 需注册/上界 | `BattleContext.cpp:1127-1130`；E1；E2 否；E3 未运行 | REG、CAP | B / B |
| `SEARING_BLOW` / Searing Blow | 费2；D12；可无限升级 | 费2；第 n 次升级 D=`12+n(n+7)/2`（1次16、2次21、3次27…） | T；`upgraded: bool` 不足以表达次数，V2；K0 | `BattleContext.cpp:1136-1140`；`CardInstance.cpp:17-20,48-58,138-173`；E1；E2 否；E3 未运行 | REG、OBS（specialData/升级次数） | B / B |
| `SEVER_SOUL` / Sever Soul | 费2；Exhaust 手牌非 Attack；D16 | 费2；D22 | T；自动选择非攻击牌；V0+card type；K1 | `BattleContext.cpp:1143-1146`、`Actions.cpp:1201-1209`；E1；E2 否；E3 未运行 | REG、OBS（card type）、EXHAUST | B / B |
| `STRIKE_RED` / Strike | 费1；D6 | 费1；D9 | T；V0；K0 | `BattleContext.cpp:967-973`；E1；E2 部分；E3 基础版已覆盖，升级未运行 | 正式升级 reset 与回归 | A / A |
| `SWORD_BOOMERANG` / Sword Boomerang | 费1；随机敌人 D3×3 | 费1；随机敌人 D3×4 | R/N；无玩家选敌；V0；K0 | `BattleContext.cpp:1152-1156`、`Actions.cpp:1212-1222`；E1；E2 否；E3 未运行 | REG；`ALL_ENEMY`/随机语义需注册元数据 | B / B |
| `THUNDERCLAP` / Thunderclap | 费1；全体 D4，并 Vulnerable 1 | 费1；全体 D7，并 Vulnerable 1 | N；V1（Artifact 缺失）；K0 | `BattleContext.cpp:1158-1163`；E1；E2 否；E3 未运行 | REG、OBS（Artifact） | B / B |
| `TWIN_STRIKE` / Twin Strike | 费1；D5×2 | 费1；D7×2 | T；V0；K0 | `BattleContext.cpp:1165-1169`；E1；E2 否；E3 未运行 | REG | B / B |
| `UPPERCUT` / Uppercut | 费2；D13；Weak/Vulnerable 各1 | 费2；D13；Weak/Vulnerable 各2 | T；V1（Artifact 缺失）；K0 | `BattleContext.cpp:1172-1176`；E1；E2 否；E3 未运行 | REG、OBS（Artifact） | B / B |
| `WHIRLWIND` / Whirlwind | X 费；全体 D5×X | X 费；全体 D8×X | X+N；当前动作不需新增 X 选择，需验能量快照/免费出牌；V0；K0 | `Cards.h:684-701`、`BattleContext.cpp:1178-1185`、`Actions.cpp:1233-1259`；E1；E2 否；E3 未运行 | REG；X 费合法性与能量结算回归 | B / B |
| `WILD_STRIKE` / Wild Strike | 费1；D12；抽牌堆加入 Wound | 费1；D17；同语义 | T；V0；K2；Wound 需注册/上界 | `BattleContext.cpp:1187-1190`；E1；E2 否；E3 未运行 | REG、CAP | B / B |

### 5.3 Skill

| 英文标识 / 名称 | 正版基础版 | 正版升级版 | 动作 / 观测 / 容量 | 原版与后端差异；当前支持证据 | 阻塞 / 建议批次 | 结论（基/升） |
|---|---|---|---|---|---|---|
| `ARMAMENTS` / Armaments | 费1；B5；选择手牌 1 张，本战斗升级 | 费1；B5；本战斗升级全部手牌 | 基 S；升 N；V3；K0 | `BattleContext.cpp:1217-1224`、`Actions.cpp:678-700`；E1；E2 否；E3 未运行 | 基 ACT；升 REG/OBS；需选择屏动作 | C / B |
| `BATTLE_TRANCE` / Battle Trance | 费0；抽3；本回合禁止额外抽牌 | 费0；抽4；同语义 | N；V1（NoDraw 状态未观测）；K1 | `BattleContext.cpp:1238-1241`；E1；E2 否；E3 未运行 | REG、OBS（NoDraw） | B / B |
| `BLOODLETTING` / Bloodletting | 费0；失3 HP；+2 能量 | 费0；失3 HP；+3 能量 | N；V1（自伤触发状态未观测）；K0 | `BattleContext.cpp:1251-1254`；E1；E2 否；E3 未运行 | REG、OBS | B / B |
| `BURNING_PACT` / Burning Pact | 费1；选择并 Exhaust 1 张；抽2 | 费1；选择并 Exhaust 1 张；抽3 | S；V3；K1 | `BattleContext.cpp:1256-1259`、`Actions.cpp:824-835`；E1；E2 否；E3 未运行 | ACT、REG；手牌选择 | C / C |
| `DEFEND_RED` / Defend | 费1；B5 | 费1；B8 | N；V0；K0 | `BattleContext.cpp:1210-1215`；E1；E2 部分；E3 基础版已覆盖，升级未运行 | 正式升级 reset 与回归 | A / A |
| `DISARM` / Disarm | 费1；敌人 Strength -2；Exhaust | 费1；敌人 Strength -3；Exhaust | T；V1（Artifact/敌方力量已有部分）；K1 | `BattleContext.cpp:1281-1283`；正版 JAR `Disarm.class` M2→3，但后端分支固定传 `-2`，升级未生效；E1；E2 否；E3 未运行 | 后端升级行为冲突、REG、EXHAUST | B / D |
| `DOUBLE_TAP` / Double Tap | 费1；本回合下一张 Attack 打两次 | 费1；本回合接下来 2 张 Attack 各打两次 | N；V1（Double Tap 活动层数未观测）；K0 | `BattleContext.cpp:1290-1292`；E1；E2 否；E3 未运行 | REG、OBS | B / B |
| `DUAL_WIELD` / Dual Wield | 费1；选择 Attack 或 Power，复制 1 张入手牌 | 费1；选择 Attack 或 Power，复制 2 张 | S；V3；K2/K3（复制与手牌满时转弃牌） | `BattleContext.cpp:1294-1296`、`Actions.cpp:701-752`、`BattleContext.cpp:2936-2984`；代码注释明确标有 buggy；E1；E2 否；E3 未运行 | ACT、CAP、后端 helper 待回归 | C / C |
| `ENTRENCH` / Entrench | 费2；Block 翻倍 | 费1；Block 翻倍 | N；需当前 Block，V0；K0 | `BattleContext.cpp:1302-1304`；成本 `Cards.h:799-801`；E1；E2 否；E3 未运行 | REG | B / B |
| `EXHUME` / Exhume | 费1；选择消耗堆 1 张入手；Exhaust | 费0；同语义 | S；V3；K1 | `BattleContext.cpp:1306-1308`、`Actions.cpp:755-781`、`BattleContext.cpp:3020-3027`；helper 注释称 selected card 行为仍有 bug 风险；E1；E2 否；E3 未运行 | ACT、REG、EXHAUST；需消耗堆选择 | C / C |
| `FLAME_BARRIER` / Flame Barrier | 费2；B12；本回合受攻击反伤4 | 费2；B16；反伤6 | N；V1（Flame Barrier 活动状态未观测）；K0 | `BattleContext.cpp:1319-1322`；E1；E2 否；E3 未运行 | REG、OBS | B / B |
| `FLEX` / Flex | 费0；Str+2，本回合末 -2 | 费0；Str+4，本回合末 -4 | N；V1（Lose Strength 延迟状态未观测）；K0 | `BattleContext.cpp:1324-1327`；E1；E2 否；E3 未运行 | REG、OBS | B / B |
| `GHOSTLY_ARMOR` / Ghostly Armor | 费1；Ethereal；B10 | 费1；仍 Ethereal；B13 | N；V0；K1 | `BattleContext.cpp:1329-1331`、`Cards.h:466-484`；E1；E2 否；E3 未运行 | REG、EXHAUST/消耗堆 | B / B |
| `HAVOC` / Havoc | 费1；打出抽牌堆顶牌并 Exhaust | 费0；同语义 | N+I+R；顶牌顺序对玩家隐藏；顶牌若需二次选择会打开未暴露的选择阶段；V3；K1/K3 | `BattleContext.cpp:1337-1339`、`BattleContext.cpp:2515-2529`；后端随机传 target 并 autoplay；E1；E2 否；E3 未运行 | ACT、REG；需要保证间接卡集合动作闭包 | C / C |
| `IMPERVIOUS` / Impervious | 费2；B30；Exhaust | 费2；B40；Exhaust | N；V0；K1 | `BattleContext.cpp:1355-1357`；E1；E2 否；E3 未运行 | REG、EXHAUST | B / B |
| `INFERNAL_BLADE` / Infernal Blade | 费1；随机 Attack 入手，本回合费0；Exhaust | 费0；同语义 | N+R；随机攻击可能为 Headbutt，后续需要弃牌堆选择；V3；K2 | `BattleContext.cpp:1359-1361`、`Actions.cpp:571-577`；E1；E2 否；E3 未运行 | ACT（生成卡闭包）、REG（实际生成池全部类别）、CAP | C / C |
| `INTIMIDATE` / Intimidate | 费0；全体 Weak1；Exhaust | 费0；全体 Weak2；Exhaust | N；V1（敌方 Artifact 未观测）；K1 | `BattleContext.cpp:1363-1365`；E1；E2 否；E3 未运行 | REG、OBS、EXHAUST | B / B |
| `LIMIT_BREAK` / Limit Break | 费1；Strength 翻倍；Exhaust | 费1；Strength 翻倍；不 Exhaust | N；V0/V1（Strength 有，exhaust 语义可查）；K1 | `BattleContext.cpp:1376-1378`；`Cards.h:616-624` 说明基础版才 Exhaust；E1；E2 否；E3 未运行 | REG、OBS（Strength 及动态 Power） | B / B |
| `OFFERING` / Offering | 费0；失6 HP；+2 能量；抽3；Exhaust | 费0；失6 HP；+2 能量；抽5；Exhaust | N；V1；K1 | `BattleContext.cpp:1392-1396`；E1；E2 否；E3 未运行 | REG、OBS、EXHAUST | B / B |
| `POWER_THROUGH` / Power Through | 费1；手牌加 2 Wound；B15 | 费1；手牌加 2 Wound；B20 | N；V0；K2；Wound 注册与重复上界未证明 | `BattleContext.cpp:1407-1410`、`Actions.cpp:227-236`；E1；E2 否；E3 未运行 | REG、CAP；状态牌批次 | B / B |
| `RAGE` / Rage | 费0；本回合每打 Attack 得 B3 | 费0；本回合每打 Attack 得 B5 | N；V1（Rage 活动层数未观测）；K0 | `BattleContext.cpp:1416-1418`；E1；E2 否；E3 未运行 | REG、OBS | B / B |
| `SECOND_WIND` / Second Wind | 费1；Exhaust 手牌全部非 Attack，每张 B5 | 费1；每张 B7 | N；需要手牌 card type，V2；K1 | `BattleContext.cpp:1428-1430`、`Actions.cpp:1179-1198`；E1；E2 否；E3 未运行 | REG、OBS、EXHAUST | B / B |
| `SEEING_RED` / Seeing Red | 费1；+2 能量；Exhaust | 费0；+2 能量；Exhaust | N；V0；K1 | `BattleContext.cpp:1432-1434`；成本 `Cards.h:803-808`；E1；E2 否；E3 未运行 | REG、EXHAUST | B / B |
| `SENTINEL` / Sentinel | 费1；B5；若被 Exhaust，+2 能量 | 费1；B8；+3 能量 | N；V0；K1 | `BattleContext.cpp:1436-1438`、`CardInstance.cpp:207-213`；E1；E2 否；E3 未运行 | REG、EXHAUST、触发回归 | B / B |
| `SHOCKWAVE` / Shockwave | 费2；全体 Weak/Vulnerable 3；Exhaust | 费2；全体 Weak/Vulnerable 5；Exhaust | N；V1（Artifact 未观测）；K1 | `BattleContext.cpp:1440-1443`；E1；E2 否；E3 未运行 | REG、OBS、EXHAUST | B / B |
| `SHRUG_IT_OFF` / Shrug It Off | 费1；B8；抽1 | 费1；B11；抽1 | N；V0；K1 | `BattleContext.cpp:1445-1448`；E1；E2 否；E3 未运行 | REG、CAP | B / B |
| `SPOT_WEAKNESS` / Spot Weakness | 费1；若敌方意图攻击，Str+3 | 费1；Str+4 | T；需敌方可见意图，V0；K0 | `BattleContext.cpp:1450-1452`、`Actions.cpp:1225-1230`；E1；E2 否；E3 未运行 | REG；当前 intent 类别可表达攻击判断，但需扩卡回归 | B / B |
| `TRUE_GRIT` / True Grit | 费1；B7；随机 Exhaust 1 张 | 费1；B9；玩家选择 Exhaust 1 张 | 基 N+R；升 N+S；V3；K1 | `BattleContext.cpp:1482-1489`、`Actions.cpp:354-365,824-835`；E1；E2 否；E3 未运行 | 升级版 ACT；基础版需随机耗尽回归 | B / C |
| `WARCRY` / Warcry | 费0；抽1；选择手牌放抽牌堆顶；Exhaust | 费0；抽2；选择手牌放顶；Exhaust | S；V3；K1 | `BattleContext.cpp:1495-1498`、`Actions.cpp:872-887`、`BattleContext.cpp:3050-3056`；E1；E2 否；E3 未运行 | ACT、REG；手牌选择 | C / C |

### 5.4 Power

| 英文标识 / 名称 | 正版基础版 | 正版升级版 | 动作 / 观测 / 容量 | 原版与后端差异；当前支持证据 | 阻塞 / 建议批次 | 结论（基/升） |
|---|---|---|---|---|---|---|
| `BARRICADE` / Barricade | 费3；Block 不在回合开始移除 | 费2；同语义 | N；V1（Barricade 活动状态缺失）；K0 | `BattleContext.cpp:1518-1520`；成本 `Cards.h:782-784`；E1；E2 否；E3 未运行 | REG、OBS（Block 持久性） | B / B |
| `BERSERK` / Berserk | 费0；Vulnerable 2；下回合起每回合 +1 能量 | 费0；Vulnerable 1；同语义 | N；V1（energy-per-turn 缺失）；K0 | `BattleContext.cpp:1522-1525`；E1；E2 否；E3 未运行 | REG、OBS | B / B |
| `BRUTALITY` / Brutality | 费0；每回合开始失1 HP、抽1 | 费0；升级后 Innate，再同语义 | N；V1（活动 Power 缺失）；K1 | `BattleContext.cpp:1527-1529`；`Cards.h:486-505` 支持升级 Innate；E1；E2 否；E3 未运行 | REG、OBS | B / B |
| `COMBUST` / Combust | 费1；回合末失1 HP，全体 D5 | 费1；全体 D7 | N；V1；K0 | `BattleContext.cpp:1535-1537`、`Player.cpp:363-370`；Player 代码含 stack 行为 TODO；E1；E2 否；E3 未运行 | REG、OBS、后端 end-turn 回归 | B / B |
| `CORRUPTION` / Corruption | 费3；Skills 费0，打出后 Exhaust | 费2；同语义 | N；V1（Corruption 活动状态缺失，但手牌当前 cost 可见）；K1 | `BattleContext.cpp:1531-1533`、`CardInstance.cpp:341-343`、`CardManager.cpp:414-417`；E1；E2 否；E3 未运行 | REG、OBS、EXHAUST | B / B |
| `DARK_EMBRACE` / Dark Embrace | 费2；每张牌 Exhaust 时抽1 | 费1；同语义 | N；V1；K1 | `BattleContext.cpp:1543-1545`；E1；E2 否；E3 未运行 | REG、OBS、EXHAUST | B / B |
| `DEMON_FORM` / Demon Form | 费3；回合开始 Str+2 | 费3；回合开始 Str+3 | N；V1（Demon Form 活动层数缺失）；K0 | `BattleContext.cpp:1539-1541`；E1；E2 否；E3 未运行 | REG、OBS | B / B |
| `EVOLVE` / Evolve | 费1；抽到 Status 时再抽1 | 费1；再抽2 | N；V1；K1 | `BattleContext.cpp:1547-1549`、`CardManager.cpp:397-425`；E1；E2 否；E3 未运行 | REG、OBS、状态抽牌回归 | B / B |
| `FEEL_NO_PAIN` / Feel No Pain | 费1；每张牌 Exhaust 得 B3 | 费1；每张得 B4 | N；V1；K1 | `BattleContext.cpp:1551-1553`；E1；E2 否；E3 未运行 | REG、OBS、EXHAUST | B / B |
| `FIRE_BREATHING` / Fire Breathing | 费1；抽到 Status/Curse 时全体 D6 | 费1；全体 D10 | N；V1；K0 | `BattleContext.cpp:1555-1557`、`CardManager.cpp:397-435`；E1；E2 否；E3 未运行 | REG、OBS（状态/诅咒触发） | B / B |
| `INFLAME` / Inflame | 费1；Str+2 | 费1；Str+3 | N；当前 Strength 已有，V0；没有额外同名持久状态需求证据；K0 | `BattleContext.cpp:1559-1561`；E1；E2 否；E3 未运行 | REG；力量增量回归 | B / B |
| `JUGGERNAUT` / Juggernaut | 费2；每次获得 Block，随机敌人 D5 | 费2；随机敌人 D7 | N；V1；K0 | `BattleContext.cpp:1563-1565`、`Player.cpp:68-79`；E1；E2 否；E3 未运行 | REG、OBS（Power 活动层） | B / B |
| `METALLICIZE` / Metallicize | 费1；回合末 B3 | 费1；回合末 B4 | N；V1；K0 | `BattleContext.cpp:1575-1577`、`Player.cpp` end-turn power 分支；E1；E2 否；E3 未运行 | REG、OBS | B / B |
| `RUPTURE` / Rupture | 费1；从卡牌失 HP 时 Str+1 | 费1；Str+2 | N；V1（Rupture 活动层/自伤来源缺失）；K0 | `BattleContext.cpp:1583-1585`、`Player.cpp:283-285`；E1；E2 否；E3 未运行 | REG、OBS | B / B |

## 6. 基础版与升级版结论不同的卡

以下不是遗漏，而是同一张牌的两个版本确实需要不同处理：

| 卡牌 | 基础版 | 升级版 | 原因 |
|---|---|---|---|
| Armaments | C：玩家选择一张手牌 | B：升级全部手牌，不需要选择 | 升级改变动作语法；后端分别走 `ArmamentsAction` 与 `UpgradeAllCardsInHand`。 |
| True Grit | B：随机 Exhaust | C：玩家选择 Exhaust | 升级把随机选择改成主动选择，不能自动选牌代替。 |
| Limit Break | B：基础版 Exhaust | B：升级版不 Exhaust | 结算动作列不变，但卡牌离开区域语义不同。 |
| Disarm | B：静态数值入口与基础语义一致 | D：正版应减 3 Strength，后端分支仍固定减 2 | 这是后端升级行为冲突，不是动作协议问题。 |
| Whirlwind | B / B | B / B | 两版均由能量确定 X；升级改变每次伤害，不需要额外 X 选择。 |
| Body Slam、Barricade、Corruption、Dark Embrace、Entrench、Exhume、Havoc、Infernal Blade、Seeing Red | B：基础费用/动作 | B：升级费用或 Exhaust 差异 | 当前注册和正式升级 reset 均未接入，但不需要新增选择阶段。 |
| Brutality | B：普通 Power | B：升级后 Innate | `upgraded` 字段能表达该属性，但当前没有升级版正式生成与行为测试。 |
| Ghostly Armor | B：Ethereal | B：仍 Ethereal | 正版 upgrade 只加 3 格挡；两版均需回合末虚无回归。 |

## 7. 可复用机制依赖与建议开放批次

这些是审计结果给 M2/M3 的建议批次，不是对权威执行规格的修改，也不是正式白名单。

| 批次 | 机制依赖 | 建议先开放的卡 | 必须先验收 |
|---|---|---|---|
| B0 | 当前最小牌、单敌/三目标列、无升级 | Strike、Defend、Bash | 已有基础回归；升级版仍需单独测试。 |
| B1 | 单体攻击/无目标直接结算，无生成、无持久 Power | Bludgeon、Carnage、Clash、Cleave、Clothesline、Dropkick、Twin Strike、Uppercut 等 | registry、card type/target 元数据、升级数值、逐卡行为测试。Iron Wave 先排除到校准后；Heavy Blade 只需正常行为验收。 |
| B2 | 玩家可见 Strength/Block/敌意图，单回合效果 | Body Slam、Heavy Blade（倍率误报已撤销）、Pommel Strike、Entrench、Spot Weakness、Flex、Inflame、Metallicize | Strength、Block、意图、升级值及对照轨迹。 |
| B3 | 抽牌、耗尽、Ethereal、手牌/消耗堆 | Battle Trance、Shrug It Off、Impervious、Sentinel、Pummel、Second Wind、Sever Soul | `hand/draw/discard/exhaust` 容量和 count 一致性；耗尽触发器；不静默丢牌。 |
| B4 | 状态牌/固定生成 | Reckless Charge、Wild Strike、Power Through、Immolate | Dazed/Wound/Burn registry；生成次数上界；pile capacity 版本；状态卡是否玩家可见。 |
| B5 | 选择屏 | Armaments（基础）、Burning Pact、Dual Wield、Exhume、Headbutt、Warcry、True Grit（升级） | 暴露 `SINGLE_CARD_SELECT` 的动作版本；手牌/弃牌/消耗堆候选 mask；轨迹格式与模型头迁移。 |
| B6 | 长期 Power 与回合边界 | Barricade、Demon Form、Corruption、Dark Embrace、Feel No Pain、Fire Breathing、Rage、Rupture 等 | 玩家 Power/energy-per-turn/延迟触发/Artifact 可见字段；不可把 hidden status 直接注入。 |
| B7 | X 费/特殊升级/间接动作闭包 | Whirlwind、Searing Blow、Rampage、Havoc、Infernal Blade | X 费能量传递与合法性；per-card specialData；Havoc/Infernal Blade 可达卡的选择阶段闭包；容量上界。 |

建议批次顺序仍是“来源与动作语法 → 输入/动作/容量契约 → C++ 与规范观测 → 双 wrapper 与旧范围回归 → 从头短训 → 配对诊断”。本报告没有启动后续批次。

## 8. 已验证、未验证、待裁定

### 8.1 已验证

- 正版 JAR 的 75 个 `red/` class 清单及 `cards.json` 语义入口。
- JAR SHA-256、锁定后端 commit、当前 patched checkout 和扩展文件 hash。
- 75/75 JAR 类 → 后端 enum；75/75 JAR 类 → 后端结算 switch 的静态覆盖。
- 当前动作、观测、registry、hand/pile 容量和 unknown backend ID 的拒绝路径。
- 当前最小后端/adapter/wrapper/mask 回归 89 项通过；spec 检查通过。
- Anger、Power Through、Immolate、Reckless Charge、Wild Strike 等生成牌入口已在后端源码中定位；当前 wrapper 超过 10 张非手牌记录会报错而不是截断。
- 二次选择 helper 的实际入口和内部动作类型存在，但没有通过当前 Python 31 位动作导出。

### 8.2 未验证

- 72 个未注册卡的正式 registry/backend ID 映射、wrapper 编码、checkpoint schema 兼容性。
- 所有扩展卡基础版和升级版的 runtime 行为测试；本轮没有把 E1 静态入口写成 E3。
- 每张卡的动作 mask 与升级前后合法动作闭包。
- 生成牌、复制、随机牌、消耗堆和手牌满时的最大容量；`PILE_CAPACITY=10` 不是扩卡后的证明。
- Power、Artifact、NoDraw、Corruption、Rage、Rupture、Barricade、energy-per-turn 等状态字段的玩家可见性和 wrapper 传递。
- 全部升级版从 reset、轨迹记录到模型输入的正式链路；当前 `reset()` 固定初始卡组且不接收升级配置。

### 8.3 待裁定

- Heavy Blade：原倍率差异已撤销；完整调用链合计 3/5 倍，仍待行为回归。
- Disarm 升级：正版升级为减 3 Strength，后端 `BattleContext.cpp:1281-1283` 固定减 2。
- Iron Wave：后端 `BattleContext.cpp:1076` 的双重 `calculateCardBlock` 是否在当前 Dexterity 接入后造成可观察差异。
- Fiend Fire：`Actions.cpp:1091-1100` 在使用卡尚未从手牌移除时按 `cardsInHand` 排队攻击/耗尽，需用最小定点场景确认是否多打一击或多排一次耗尽。
- Havoc：后端 `playTopCardInDrawPile()` 会以 autoplay 和随机目标执行顶牌；顶牌若本身需要二次选择，当前 Python 接口没有选择阶段动作，必须确认正版行为与迁移方案。
- Dual Wield、Exhume 的上游 helper 注释已明确存在 bug/TODO；在行为测试前不能仅凭入口存在裁定为通过。
- 正版 JAR 的具体发行补丁字符串未从 `build.properties` 查明；本报告用完整 JAR hash 作为版本指纹。

## 9. 非目标与文件变更

- 未启动训练、短训、评估或 checkpoint 迁移。
- 未安装依赖，未提交、未 push。
- 未修改训练代码、后端、registry 或正式白名单；本轮只同步 M1 的状态记录，不改变动作、容量或其他执行规则。
- 本次 M1 材料包括本报告与 `docs/m1-numeric-evidence.md`；同步状态的 `spec-v6.md`、`docs/decisions.md`、`AGENTS.md` 和 Week 5–6 计划不等同于正式开放，既有 `reference/` 目录未覆盖。

## 10. 2026-09-11 复核修订与证据

本轮修正 Heavy Blade、Whirlwind、Ghostly Armor、Infernal Blade、Inflame 及 reset 覆盖措辞；原十张卡的数值定位补充见 `docs/m1-numeric-evidence.md`。表内仍沿用原审计者未重新核验的其他数值，不将本轮材料称为全卡行为复验。§2.4 的 89 项测试是原审计记录，本轮没有重跑，也没有新增扩展卡运行时验收。

- [R1] 高（一手、本机正版文件），核验日期 2026-09-11：重新计算 JAR SHA-256，与 §2.2 一致。使用本机 javap 对 GhostlyArmor、Whirlwind、Disarm、Inflame、HeavyBlade 及 WhirlwindAction 作定点字节码查阅；本地输出位于 `reference/sts1-decompiled/m1-review/`，不入库。
- [R2] 高（一手、正版字节码），核验日期 2026-09-11：`GhostlyArmor.<init>` 设置 isEthereal=true，`upgrade()` 仅 upgradeName/upgradeBlock(3)，没有取消虚无；`Whirlwind.use()` 传 energyOnUse，`WhirlwindAction.update()` 读取总能量或 energyOnUse 并按次数结算，没有玩家选 X 阶段。
- [R3] 高（当前后端实际源码），核验日期 2026-09-11：`bindings/bindings-util.cpp:392-397` 构造并执行 CARD 动作，`src/sim/search/Action.cpp:433` 将 player.energy 传给队列项；`src/combat/BattleContext.cpp:1054-1058,2671` 的 Heavy Blade 与通用伤害调用链合计 3/5 倍力量。静态链路不替代零能量、免费出牌等运行时测试。
- [R4] 高（当前后端实际源码），核验日期 2026-09-11：`src/combat/Actions.cpp:571` 与 `include/constants/CardPools.h:152` 表明随机攻击生成依赖含 Headbutt 的池；不能仅注册新类别而忽略后续选择。`BattleContext.cpp:1559` 的 Inflame 直接加 Strength，不需凭空加入另一活动状态。

修订后分类仍只是排查路由。B 类包含注册、观测、容量等不同工作量，不能将所有 B 类一次开放。Disarm 升级、Iron Wave、Fiend Fire 保留待核验；扩展卡全部可达效果和运行时行为尚需逐项验收。原十张来源证据已由 `docs/m1-numeric-evidence.md` 补齐；这不等于扩展卡行为通过或正式开放。

## 11. M1 收口（2026-09-11）

M1 以候选方案阶段收口：全卡 75 类/150 版本审计、A6/B123/C16/D5 分类、35 类候选批次和原十张正版数值证据均已形成。M1 收口不批准任何扩展卡进入正式环境，不改变 30–40 类目标、31 位动作或执行规格。

仍未完成的工作属于后续 M2/M3：扩展卡基础/升级行为测试、正式 registry/reset/白名单、生成牌和容量上界、可见观测字段、版本契约及后续从头短训。M2 的固定牌组、容量和观测契约尚未在本报告中锁定。
