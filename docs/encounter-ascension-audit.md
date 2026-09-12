# Act 1 遭遇、进阶与容量预审报告

日期：2026-09-11
任务：并行任务 B，供主审与 M2 使用
状态：预审完成，等待主审；不是正式白名单、M4 验收或规格裁定

## 0. 结论先行

1. 当前正式绑定仍只执行 A0 的 `Jaw Worm`、`Cultist`、`Two Louse`。`reset` 对其它遭遇和任何非 0 进阶直接拒绝；这次只对这三个遭遇做了只读探针，未启动扩展遭遇。
2. 锁定后端的遭遇枚举和 `MonsterGroup` 确实包含本任务要求的 Act 1 普通遭遇及三个精英，但“源码有 case”不等于绑定可执行、观测可表达或动作可寻址。
3. 当前动作目标只有 `0,1,2`。`Gremlin Gang` 静态创建 4 个敌人，`Lots of Slimes` 创建 5 个敌人；它们分别会产生目标索引 3、4，不能在现有 31 位动作协议下开放。5 行敌人观测不是 5 个可选目标。
4. `Large Slime` 的分裂会把原槽位替换为一个中型史莱姆，并在相邻槽位放入第二个中型史莱姆；当前源码路径的最大可达槽位为 1，不能用“初始只有一个敌人”跳过分裂后的核验。
5. 扩展遭遇的当前绑定观测不完整：`visibleIntent` 只覆盖最小三遭遇中已列出的内部招式；Artifact、Asleep、Metallicize、Enrage、Spore Cloud、Thievery、Gremlin Wizard 的充能等状态没有进入现有敌人字段。扩展 reset 即使解除白名单，也会在观测阶段遇到未知意图或未知卡牌错误。
6. 状态牌容量不能沿用当前 `pile_capacity=10`。Sentry 的 Bolt、Large/Medium Slime 的攻击会持续生成 Dazed/Slimed；默认 `maxTurns=50` 下仅三只 Sentry 的 Dazed 就可能达到 A0 的 150 张、A18 的 225 张（未计初始牌和其它生成），而可配置的 `maxTurns` 没有被限制为 50，跨配置不存在有限上界。
7. 静态审计发现两个需主审确认的实现风险：Red Slaver 的 `usedEntangle` 读取 `miscInfo`，但当前相关结算分支未发现写入；Gremlin 小怪的 `escapeNext` 也未发现写入，因而其通用逃跑分支在当前源码中疑似不可达。二者均不据此直接裁定正版差异，先列为阻塞核查项。
8. 本报告没有开放任何遭遇、修改正式环境/共享规格、修改决策或周计划、启动训练、提交代码或运行扩展测试。

证据标签：

- **静态**：读取当前工作区源码、绑定、规格或既有本地一手材料所得；不等于运行通过。
- **探针**：本次只读执行得到的当前 A0 绑定结果。
- **未运行**：建议的扩展场景、进阶两侧测试和完整战斗测试本次没有执行。
- **[未核实]**：本报告没有足够的一手游戏行为证据，不能把后端实现当成正版规则。

## 1. 基线、来源与证据边界

### 1.1 工作区基线

| 项 | 本次记录 |
|---|---|
| 主仓库 `HEAD` | `80d2340983f1f0a5eb5f6dee159760302a83940f` |
| `origin/main` | `80d2340983f1f0a5eb5f6dee159760302a83940f` |
| `sts_lightspeed` 上游提交 | `7476a81954020087da31d41d16fddf475746ec2d` |
| 上游子目录状态 | 保留已有 `bindings/` 本地改动、`pybind11` 子模块状态和 `build/`；本任务未触碰 |
| 正版 JAR | `E:\SteamLibrary\steamapps\common\SlayTheSpire\desktop-1.0.jar` |
| 正版 JAR SHA-256 | `cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673` |

本次关键文件指纹如下。它们用于主审复核时发现并行变更；报告中的行号均对应这些文件在本次读取时的内容。

| 文件 | SHA-256 |
|---|---|
| `third_party/sts_lightspeed/src/combat/MonsterGroup.cpp` | `731210F6DBD82C269AD07980513117D8076409B32329C34122FA6934D6C5FA46` |
| `third_party/sts_lightspeed/src/combat/Monster.cpp` | `D135A27D9C3F4DFC422C113A1C5DFEEA315CFE4EB896DA9D865843D4EC256039` |
| `third_party/sts_lightspeed/src/combat/MonsterSpecific.cpp` | `50A6178312EC0EE5F6268DF687E6A9EFBF6BA314736905F37F9336606601CAED` |
| `third_party/sts_lightspeed/src/combat/MonsterMoveDamage.cpp` | `0BBF8C1D76081B4D8E0627EC008F260744EE82FE2F4E3FFFBB69566BA7FE1786` |
| `third_party/sts_lightspeed/bindings/bindings-util.cpp` | `BA1F3110DC87A2C356895A5826D26E3507AF83265DF9F2482F662D16D512E6F2` |
| `third_party/sts_lightspeed/bindings/slaythespire.h` | `4C0A8B10B8FFE292D630772440F207F3197BFF90B90AAB78D3C803A87FBE39B8` |
| `third_party/sts_lightspeed/include/constants/MonsterEncounters.h` | `5363596BA4D216BF635C1F8D6066E180712C590529210D6264746B877E27BCCE` |
| `third_party/sts_lightspeed/include/combat/MonsterGroup.h` | `1034779FBFCDF36E68FF269C81512AA9CA858BEE556FB7AF5578103820D36258` |
| `third_party/sts_lightspeed/include/combat/Monster.h` | `0D81FDB6FD8B205DDC72AC035859AFB2514D4EFE102D2D849916BEC035DE4765` |
| `third_party/sts_lightspeed/include/combat/BattleContext.h` | `FE9739837AB5AF88E5052CEBB6FC278749F60F59412F000439C7CC71C4BD1CEF` |
| `third_party/sts_lightspeed/include/combat/CardManager.h` | `899431C5F1F921CB66C590BC15ECD605F5E497D733FBAF0A9679DE9321D7CAC2` |

### 1.2 正版来源与锁定后端分开

正版一手材料使用本机正版 JAR 及已有 D13 定点查阅产物：

- `reference/decomp/com/megacrit/cardcrawl/monsters/exordium/Cultist.java`：确认正版 Cultist 的首个 `Incantation`、A2 Ritual 数值、A7 HP 区间以及 A17 的额外 Ritual 增量。
- `reference/decomp/com/megacrit/cardcrawl/monsters/exordium/LouseNormal.java` 与 `LouseDefensive.java`：确认两类 Louse 的 A2 bite roll、A7 HP、A7/A17 Curl Up 区间、A17 行动约束和 Grow 增量。
- 本次没有生成新的反编译文件。其它扩展遭遇的正版精确行动和状态可见性仍标为 **[未核实]**；JAR 中存在相应 class entry 只证明文件存在，不能替代行为证据。

锁定后端实际行为以 `third_party/sts_lightspeed` 为准；它是训练环境行为来源，不是正版一手来源。已有规格也明确要求“上游枚举/注释/分支存在”不得替代接口、可见字段和回归验收。

## 2. 当前模拟器完整调用链

### 2.1 初始化与执行

静态调用链如下：

```text
IroncladBattleEnv.reset
  -> GameContext(CharacterClass::IRONCLAD, seed, ascension)
  -> BattleContext::init(gc, encounter)
  -> MonsterGroup::init
       -> createMonsters / createMonster
       -> 对每个已创建槽位 rollMove
       -> 对每个已创建槽位 preBattleAction
  -> CardManager::init / relic / energy / executeActions

IroncladBattleEnv.step(action)
  -> Action(slot, target) 或 END_TURN
  -> Action::execute
  -> BattleContext::executeActions
       -> action queue
       -> card queue
       -> monsterTurnIdx 顺序执行 MonsterGroup::doMonsterTurn
       -> afterMonsterTurns / end-of-round powers / 下一回合
  -> makeObservation / reward / info
```

对应证据：

- 绑定 `reset` 的 ascension/encounter 拒绝和 `BattleContext::init` 调用：`third_party/sts_lightspeed/bindings/bindings-util.cpp:241-256`。
- `BattleContext::init` 的 RNG、进阶、怪物初始化、牌堆初始化和第一次 `executeActions`：`third_party/sts_lightspeed/src/combat/BattleContext.cpp:21-77`。
- `MonsterGroup::init` 明确先 `rollMove`、后 `preBattleAction`：`third_party/sts_lightspeed/src/combat/MonsterGroup.cpp:76-88`。
- 动作解码、合法性检查、`Action::execute` 和重新进入 `executeActions`：`bindings/bindings-util.cpp:381-410`、`src/sim/search/Action.cpp:421-465`。
- action queue、card queue、怪物回合、回合末状态和玩家下一回合：`BattleContext.cpp:721-823`、`:2107-2215`。

### 2.2 当前观测与容量事实

- `IroncladBattleEnv::MAX_ENEMIES=5`、`MAX_HAND=10`、`ACTION_COUNT=31`：`bindings/slaythespire.h:93-124`。
- 敌人导出循环最多读 `monsterCount` 行，但行数截到 `MAX_ENEMIES`：`bindings-util.cpp:282-331`。
- 动作目标解码为 `action / 3` 与 `action % 3`，所以目标列固定为 0、1、2：`bindings-util.cpp:259-275`。
- 当前 `visibleIntent` 仅覆盖 Jaw Worm、Cultist、红/绿 Louse 的攻击、攻防、增益和减益招式；其它招式走 `unsupported intent`：`bindings-util.cpp:57-80`。
- 当前敌人字段只有 `monster_id,hp,max_hp,block,strength,vulnerable,weak,intent,intent_damage,intent_hits,curl_up,ritual`：`bindings/slaythespire.h:22-42`；`enemyFeature` 实际只填这些字段：`bindings-util.cpp:82-103`。
- Python wrapper 的 `PILE_CAPACITY=10`，非手牌三堆合计超出即报错而不是截断：`sts/env/wrappers.py:23-33,256-280`。这不是扩展状态牌的容量证明。

## 3. Act 1 遭遇映射与可达状态

`MonsterEncounters.h:12-34` 定义枚举，Act 1 pool 位于 `MonsterEncounters.h:159-187`；`MonsterGroup::createMonsters` 的实际 case 位于 `MonsterGroup.cpp:97-474`。以下“最大目标索引”是全过程槽位索引，不是存活敌人数。

| pool/索引 | 遭遇与后端实际初始槽位 | 初始最大索引 | 分裂/召唤后的最大索引 | 当前预审状态 |
|---|---|---:|---:|---|
| Weak/0 | `CULTIST` → Cultist 在槽 0 | 0 | 0 | 深查；当前可执行 A0 |
| Weak/1 | `JAW_WORM` → Jaw Worm 在槽 0 | 0 | 0 | 深查；当前可执行 A0 |
| Weak/2 | `TWO_LOUSE` → 随 `miscRng` 各 roll 一只红/绿 Louse，槽 0、1 | 1 | 1 | 深查；当前可执行 A0 |
| Weak/3 | `SMALL_SLIMES` → 随机为 Spike Slime S + Acid Slime M，或 Acid Slime S + Spike Slime M，槽 0、1 | 1 | 1 | 深查；绑定未开放 |
| Strong/0 | `GREMLIN_GANG` → 从 8 个 Gremlin 候选无放回取 4 个，槽 0–3 | 3 | 3 | 深查但动作容量阻塞；不开放 |
| Strong/1 | `LOTS_OF_SLIMES` → 3 个 Spike Slime S + 2 个 Acid Slime S 无放回排列，槽 0–4 | 4 | 4 | 深查但动作容量阻塞；不开放 |
| Strong/2 | `RED_SLAVER` → Red Slaver 槽 0 | 0 | 0 | 深查；绑定未开放 |
| Strong/3 | `EXORDIUM_THUGS` → `createWeakWildlife` + `createStrongHumanoid`，槽 0、1；各自还有随机类型 | 1 | 1（代表静态路径） | 组合待查，不由代表类型推断通过 |
| Strong/4 | `EXORDIUM_WILDLIFE` → `createStrongWildlife` + `createWeakWildlife`，槽 0、1；各自还有随机类型 | 1 | 1（代表静态路径） | 组合待查，不由代表类型推断通过 |
| Strong/5 | `BLUE_SLAVER` → Blue Slaver 槽 0 | 0 | 0 | 深查；绑定未开放 |
| Strong/6 | `LOOTER` → Looter 槽 0；逃跑后仍保留该槽位但不可 target | 0 | 0 | 深查；绑定未开放 |
| Strong/7 | `LARGE_SLIME` → Acid Slime L 或 Spike Slime L 随机，槽 0 | 0 | 1；槽 0 被替换、槽 1 新建 | 深查；绑定未开放 |
| Strong/8 | `THREE_LOUSE` → 3 次 `getLouse`，槽 0–2 | 2 | 2 | 组合待查；目标容量上可表达 |
| Strong/9 | `TWO_FUNGI_BEASTS` → Fungi Beast 槽 0、1 | 1 | 1 | 深查；绑定未开放 |
| Elite/0 | `GREMLIN_NOB` → 槽 0 | 0 | 0 | 深查；绑定未开放 |
| Elite/1 | `LAGAVULIN` → 槽 0，并在建组时设置 `ASLEEP` | 0 | 0 | 深查；绑定未开放 |
| Elite/2 | `THREE_SENTRIES` → Sentry 槽 0、1、2 | 2 | 2 | 深查；绑定未开放 |

### 3.1 空槽、死亡与槽位复用

- `MonsterGroup::doMonsterTurn` 按 `monsterTurnIdx` 访问原槽位；死亡/逃跑槽位不会被压缩：`MonsterGroup.cpp:571-589`。
- `enemy_mask[i]` 使用 `monster.isTargetable()`，死亡、半死亡和逃跑会变为不可 target；未使用的行则保持零值：`bindings-util.cpp:294-317`、`Monster.cpp:241-255`。
- 普通死亡只递减 `monstersAlive`，不重排 `arr`：`Monster.cpp:283-325`。
- Looter 的 `Escape` 设置 `isEscapingB` 并递减 `monstersAlive`，但不复用槽位：`MonsterSpecific.cpp:897-909`。
- Large Slime 分裂显式使用 `placeIdx` 与 `placeIdx+1`，重置前者、写入后者，随后增加 `monsterCount`：`MonsterSpecific.cpp:3342-3367`。因此它是“原槽位替换 + 相邻槽位新增”，不是把两个活敌人重新编号。
- 当前动作目标只能到 2；因此 `Gremlin Gang` 的槽 3、`Lots of Slimes` 的槽 3/4 即使在 5 行观测内，也无法由玩家动作选择。此结论与 `spec-v6.md:237-256` 的容量规则一致。

## 4. 详查遭遇的行动、状态与实现依赖

精确攻击基础值集中在 `MonsterMoveDamage.cpp`；行动副作用和随机约束在 `MonsterSpecific.cpp`。以下是静态后端结论，不是正版全机制通过结论。

### 4.1 普通遭遇

| 遭遇 | 行动/随机条件与非攻击语义 | 状态、生成牌、分裂和容量 | 当前接口依赖/缺口 |
|---|---|---|---|
| Jaw Worm | 首次 `CHOMP`；之后 roll<25 倾向 Chomp，25–54 为 Thrash，≥55 为 Bellow，并受最近两次招式和额外 `randomBoolean` 约束：`MonsterSpecific.cpp:2450-2491`。Chomp=11/A2+12；Thrash=7；Bellow 力量为 A0/A1=3、A2–A16=4、A17+=5，给 block 6，A17+为 9：`MonsterSpecific.cpp:850-867`、`MonsterMoveDamage.cpp:95-96`。 | 单槽，无生成牌、无分裂。Thrash/Bellow block 会在敌方回合开始按通用规则清除。 | 当前 `visibleIntent` 已覆盖三种语义；当前 A0 探针初始 intent 为攻击、`intent_damage=11`，过一次结束回合后静态观察到 `DEFEND_BUFF`。 |
| Cultist | 首次固定 `INCANTATION`，之后 `DARK_STRIKE`，无随机行动：`MonsterSpecific.cpp:2280-2287`。Dark Strike=6；Ritual 为 A0/A1=3、A2–A16=4、A17+=5：`MonsterSpecific.cpp:676-686`。回合末刚施加的 Ritual 跳过一次增长，之后每回合加力量：`Monster.cpp:69-77`。 | 单槽，无生成牌。Ritual 当前已导出。 | 当前 A0 探针初始为增益，结束回合后为攻击6、Ritual=3；与既有正版定点材料及后端结算一致。 |
| Two Louse | 每只由 `getLouse` 独立随机为 Red/Green。Green 的 Bite 或 Spit Web，Red 的 Bite 或 Grow；roll<25 与最近两次同招式约束，A17 改变限制：`MonsterSpecific.cpp:2313-2328,2583-2598`。Bite 每场 roll 保存于 `miscInfo`，A0/A1=5–7，A2+=6–8；Green Web=Weak2，Red Grow=A0–A16 +3、A17+ +4：`Monster.cpp:114-122`、`MonsterSpecific.cpp:744-752,1005-1013`、`MonsterMoveDamage.cpp:81,119`。 | 槽 0/1，无分裂、召唤或状态牌。每只 pre-battle 加 Curl Up：A0–A6 3–7，A7–A16 4–8，A17+ 9–12：`MonsterSpecific.cpp:293-308`。 | 当前 A0 探针得到红/绿两槽、各自 Bite intent 和 Curl Up；已有正版 Louse 定点材料覆盖 A2/A7/A17 边界。 |
| Small Slimes | 槽 0/1 的 S/M 组合随机。Acid S 在 A17 前随机 Tackle/Lick，A17 起固定 Lick；Spike S 固定 Tackle。Acid/Spike M 在 roll 和最近两次招式约束下在攻击、Lick 之间切换：`MonsterSpecific.cpp:1889-2044,2769-2835`。 | Acid M 的 Corrosive Spit 生成 Slimed×1；Spike M 的 Flame Tackle 生成 Slimed×1：`MonsterSpecific.cpp:373-389,1172-1183`。没有分裂。 | 需要注册 Slimed、扩大牌堆容量，并把 Lick/Flame/Corrosive 等非最小意图映射成观测语义；当前绑定会在 reset 被拒绝，不能记通过。 |
| Blue Slaver | Rake / Stab；初始和后续按 roll≥40、最近两次 Stab、Rake 连用限制选择：`MonsterSpecific.cpp:2046-2057`。Rake=7/A2+8 并施加 Weak A0–A16=1、A17+=2；Stab=12/A2+13：`MonsterSpecific.cpp:440-453`、`MonsterMoveDamage.cpp:32-33`。 | 单槽，无状态牌、无分裂。 | 需要新增 `ATTACK_DEBUFF` 类别或等价玩家可见语义；当前 `visibleIntent` 不接受。 |
| Red Slaver | 首次固定 Stab；之后可能 Entangle（无攻击）、Scrape（攻击+Vulnerable）、Stab：`MonsterSpecific.cpp:2773-2795`。Scrape=8/A2+9，Vulnerable A0–A16=1、A17+=2；Stab=13/A2+14：`MonsterSpecific.cpp:1017-1031`、`MonsterMoveDamage.cpp:121-122`。 | 单槽，无状态牌、无分裂。 | **静态风险**：`getMoveForRoll` 以 `miscInfo` 判断 `usedEntangle`，但当前 `RED_SLAVER_ENTANGLE` 结算分支只施加 Entangled 和 RollMove，没有写 `miscInfo=1`；全源码搜索未发现 Red Slaver 的其它写入。需主审用正版/定点测试确认后再修，不能按“有 Entangle case”放行。 |
| Looter | 初始化后固定 Mug；第一次 Mug 后仍 Mug，第二次 Mug 以 50/50 选择 Smoke Bomb 或 Lunge；Smoke 后 Escape，Lunge 偷金并攻击后 Smoke：`MonsterSpecific.cpp:2501-2503,897-940`。Mug=10/A2+11，Lunge=12/A2+14，初始 Thievery=15，A17+=20：`MonsterSpecific.cpp:233-236`、`MonsterMoveDamage.cpp:101-102`。 | Escape 是非攻击/逃跑意图，槽 0 不复用；无状态牌。 | 需要表达偷金、Smoke、Escape 等当前接口没有的意图/可见状态；当前绑定会拒绝未知意图。 |
| Large Slime | 初始化随机 Acid Slime L 或 Spike Slime L。Acid L 在攻击、Lick、Corrosive Spit、Split 间按 roll 和最近两次约束选择；Spike L 在 Flame Tackle/Lick 间选择，A17 改变 Lick 连用限制：`MonsterSpecific.cpp:1976-2044,2799-2818`。 | Acid L Corrosive Spit 生成 Slimed×2；Spike L Flame Tackle 生成 Slimed×2；HP≤maxHP/2 时 `onHpLost` 把意图改成 Split：`Monster.cpp:499-518`、`MonsterSpecific.cpp:353-371,1185-1200`。Split 把槽0换成两个中型史莱姆，槽1新增。 | 必须测试阈值两侧、Split 前后、目标槽位、Slimed 累积和新中型史莱姆的后续意图；当前目标容量虽能表达 0/1，但牌堆和意图不能。 |
| Two Fungi Beasts | 两个 Fungi Beast 的 Bite/Grow 由 roll<60 和最近两次 Bite/Grow 约束选择：`MonsterSpecific.cpp:2294-2310`。Bite=6；Grow 使力量 A0/A1=3、A2–A16=4、A17+=5：`MonsterSpecific.cpp:691-701`、`MonsterMoveDamage.cpp:72`。 | pre-battle 添加 Spore Cloud；源码在**非最后一只**死亡时施加 Vulnerable×2，最后一只会先因战斗胜利提前返回：`MonsterSpecific.cpp:182-184`、`Monster.cpp:283-301`。无状态牌、无分裂。 | 当前敌人字段不导出 Spore Cloud；需先核验其正版可见性及模型是否必须知道“死亡后效果”，不能只导出 Fungi 的 `monster_id` 就声明字段完整。 |
| Gremlin Gang | 4 个随机 Gremlin，类型可为 Mad/Sneaky/Fat/Shield/Wizard。Mad/Sneaky/Fat 主要为攻击；Shield 初始 Protect（给随机敌人 block），敌人只剩一个时转 Shield Bash；Wizard 初始 Charging，第三次充能后 Ultimate Blast：`MonsterSpecific.cpp:641-673,774-789,1071-1085,2289-2291,2436-2439,2505-2507,2697-2699,2745-2747`。 | Mad pre-battle Angry（A0–A16=1，A17+=2）；Fat A17+ Smash 额外 Frail；Shield/Wizard 的内部状态和非攻击 intent 未导出。当前 `escapeNext` 没有写入点，通用逃跑路径疑似不可达：`Monster.h:44-48`、全源码搜索结果。 | 4 槽导致目标3越界；死亡后保留空槽，不压缩。必须延期到目标容量/动作版本、所有 Gremlin 意图与状态、逃跑语义定完。 |
| Lots of Slimes | 5 个随机小型史莱姆，Acid S/Spike S 的行动分别由 Lick/Tackle 路径执行；Spike S 固定 Tackle，Acid S 在 A17 改变为固定 Lick：`MonsterGroup.cpp:137-155`、`MonsterSpecific.cpp:1889-1901,2769-2771`。 | 没有大史莱姆 Split；当前小型行动不生成 Slimed。5 槽导致目标3、4越界；死亡槽不复用。 | 即便行为简单，也不能因小怪无分裂而开放；先解决五目标动作协议或从正式范围排除。 |

### 4.2 三个精英

| 精英 | 初始化、行动与状态 | 生成牌/槽位 | 观测依赖 |
|---|---|---|---|
| Gremlin Nob | 首次固定 Bellow，之后 A0–A17 以 roll<33 或两次 Rush 约束在 Rush/Skull Bash 间选择；A18 起采用固定的 Rush/Skull Bash 约束：`MonsterSpecific.cpp:2402-2433`。Rush=14/A3+16，Skull Bash=6/A3+8；Bellow 施加 Enrage A0–A17=2、A18+=3：`MonsterSpecific.cpp:754-770`、`MonsterMoveDamage.cpp:85-86`。玩家每次用牌时 `BattleContext.cpp:1812-1818` 会把 Enrage 转成 Strength。 | 槽0，无牌生成。 | 当前意图映射不支持 Bellow/Rush/Skull；Enrage 的当前层数也没有单独字段，只能在 Strength 更新后间接看到。需测试技能牌/攻击牌混合、A3 和 A18 两侧。 |
| Lagavulin | 创建后设置 Asleep，再 roll 初始 Sleep；Sleep 阶段不攻击，受伤后移除 Asleep 并移除 8 点 Metallicize。醒后 Attack 连续两次后 Siphon Soul，再回 Attack；Attack=18/A3+20，Siphon 对玩家 Strength/Dexterity 各 -1，A18+各 -2：`MonsterGroup.cpp:293-296`、`Monster.cpp:442-452`、`MonsterSpecific.cpp:869-895`、`MonsterMoveDamage.cpp:98`。 | 槽0，无牌生成。pre-battle Asleep 时加 Metallicize8 和 block8：`MonsterSpecific.cpp:286-291`。 | 当前字段没有 Asleep、Metallicize、玩家 Dexterity、Siphon/睡眠 intent；必须先补可见语义和醒来边界测试。 |
| Three Sentries | 3 个槽0/1/2，各 pre-battle Artifact=1；首次意图按槽位奇偶：0、2 为 Bolt，1 为 Beam；之后 Beam→Bolt、Bolt→Beam，确定性交替：`MonsterSpecific.cpp:311-313,2642-2651`、`MonsterSpecific.cpp:1033-1045`。Beam=9/A3+10；Bolt 不攻击，生成 Dazed×2，A18+为×3：`MonsterMoveDamage.cpp:132`、`MonsterSpecific.cpp:1041-1045`。 | 槽位最大索引2，动作目标容量刚好够；每只死亡留下空槽，不重排。Dazed 会随回合持续增加。 | 当前 `artifact` 不在 `ENEMY_FEATURES`，Bolt/Beam 也会触发未知 intent；牌堆导出只接受三种基础牌，遇到 Dazed 将失败。 |

## 5. 进阶 A0–A20：后端分支、玩家初态与等价区间

这里将“正版规则应有的进阶”与“当前后端代码分支”分开。正版当前只有 Cultist/Louse 的 D13 定点材料在本地核验；其余行是后端静态审计，不能写成正版已对拍。

### 5.1 后端/接口总表

| 进阶区间或阈值 | 后端实际分支 | 对本任务影响 | 状态 |
|---|---|---|---|
| A0–A1 | 目标敌人的多数战斗分支在代码中相同；但绑定 `reset` 只接受 A0 | 只能作为静态等价区间，不能称 A1 已支持 | 静态，未运行 |
| A2 | Louse bite 由5–7变6–8；Jaw/Slime/Blue/Red等多种攻击提高；Cultist Ritual 由3变4；中型/小型史莱姆、Slaver等均有 A2 攻击分支 | 影响全部深查普通遭遇；必须逐机制核验 | 静态；Cultist/Louse 有正版定点支持 |
| A3 | 三精英的相关攻击提高：Nob Rush/Skull、Lagavulin Attack、Sentry Beam；`MonsterMoveDamage.cpp:11-13,85-86,98,132` | 三精英必须做 A2/A3 两侧 | 静态，未运行 |
| A4 | 主要是 Boss 攻击/部分 Boss 初始化 | 不影响本报告三个精英；若把 Act 1 Boss 纳入，另行审计 | 静态，范围外 |
| A5 | `GameContext::transitionToAct` 的跨幕回血规则变化 | 不改变 Act 1 standalone reset；完整 RunEnv 未实现 | 静态，范围外 |
| A6 | Ironclad 初始当前 HP 变为 maxHP 的 90%：`GameContext.cpp:522` | 影响战斗初态和 battle reward 的出口 HP | 静态，当前绑定因 A0 gate 不可注入 |
| A7 | 普通 hallway 怪物使用高 HP 区间；Louse Curl Up 变为4–8；Louse 行动约束也变化 | Jaw/Cultist/Louse/Slime/Slaver/Fungi/Gremlin 等均需检查 HP 区间 | 静态；Louse 有正版定点支持 |
| A8 | 精英使用高 HP 区间：Nob/Lagavulin/Sentry 在 `MonsterSpecific.cpp:91-102` | 三精英必须做 A7/A8 两侧 | 静态，未运行 |
| A9 | Boss 高 HP，且部分 Boss 行为阈值 | 不影响三个精英；不据此宣布 Act 1 Boss | 静态，范围外 |
| A10 | Ironclad 初始牌组加入 `ASCENDERS_BANE`：`GameContext.cpp:477-481` | 当前 `visiblePileCards` 只接受 Bash/Defend/Strike，直接移除 ascension gate 会在观测阶段失败 | 静态阻塞 |
| A11 | 药水容量由3变2：`GameContext.cpp:66` | 当前 31 动作协议、观测和 binding 没有药水字段/动作；不能称 A11 已表达 | 静态阻塞 |
| A12 | 卡牌奖励升级概率变化：`Game.cpp:386-398` | 不是当前 standalone battle 初态；公开初态重建时需保留原始难度 | 静态，范围外 |
| A13 | Boss 金币奖励变化：`GameContext.cpp:1953-1959` | 不影响本任务三精英/普通战斗 | 静态，范围外 |
| A14 | Ironclad maxHP 80→75；同时 A6+仍按90%取当前 HP：`GameContext.cpp:479-522` | 影响战斗初态、出口 HP 比率和容量/恢复推导 | 静态，当前绑定不可注入 |
| A15 | 一次性事件池及不利事件分支变化：`GameContext.cpp:54-60,2441` | 完整 Run/事件范围，不是当前战斗 reset | 静态，范围外 |
| A16 | 商店价格/相关商店分支变化：`Shop.cpp:17` | 当前战斗不涉及商店 | 静态，范围外 |
| A17 | Louse Curl Up 9–12；Louse Grow +4；Cultist Ritual 取5；Jaw Bellow strength取5/block9；Blue Rake Weak2；Red Scrape Vulnerable2；Slime/Louse/Slaver 行动约束改变；Gremlin 若为 Mad/Fat 也有状态变化；Looter Thievery20 | 这是普通遭遇的高影响阈值；必须逐遭遇验证意图、状态和牌生成 | 静态；Louse/Cultist 有正版定点支持 |
| A18 | Nob 行动约束和 Enrage3；Lagavulin Siphon 各-2；Sentry Bolt Dazed3：`MonsterSpecific.cpp:338-347,756-769,881-885,1041-1045` | 三精英必须做 A17/A18 两侧；Sentry 牌堆容量直接变化 | 静态，未运行 |
| A19 | 主要影响 Boss/高阶其它敌人（例如 Invincible/部分 Boss 牌生成），本报告目标遭遇无直接分支 | 不能因后端全局存在 A19 分支而称 Act 1 通过 | 静态，范围外/待全链审计 |
| A20 | `GameContext` 仅在 Act 3 增加第二 Boss：`GameContext.cpp:595-597`；完整地图/Run 未接入 | 不影响 Act 1 普通/三个精英 standalone | 静态，范围外 |

### 5.2 当前 reset 不能通过“解锁参数”获得 A1–A20

即使将 `bindings-util.cpp:242-244` 的 A0 拒绝去掉，至少还会遇到以下契约问题：

1. A10 的 Ascender's Bane 不在当前卡牌观察白名单，`visiblePileCards` 会拒绝未知卡。
2. A11 的药水容量没有对应观测、动作和序列化字段；容量数值存在于 `BattleContext`，但不代表 Agent 可以正确使用药水。
3. A6/A14 的初始 HP 可进入 global，但 reward/场景契约需要记录真实 ascension 与初态版本，不能把旧 A0 轨迹混标。
4. A17/A18 需要扩展意图、状态牌和敌人状态字段；当前 `BattleIntent` 枚举虽然有 6 个大类，但 `visibleIntent` 没有覆盖扩展招式。

因此“理论等价区间”只用于设计测试分桶，不是支持声明。

## 6. 容量论证与缺口

### 6.1 敌人目标容量

| 项 | 当前事实 | 结论 |
|---|---|---|
| 观测行 | 5 行 | 只能容纳静态实体记录，不能自动增加动作目标 |
| 动作目标 | 3 列，0/1/2 | `Gremlin Gang` 的槽3、`Lots of Slimes` 的槽3/4 不可寻址 |
| Large Slime | 槽0→槽0/1 | 在当前目标容量内，但必须测试替换、相邻新增和 Split 后行动 |
| Three Sentries | 槽0/1/2 | 边界刚好可寻址；中间死亡后不能重排目标编号 |
| 死亡/逃跑 | `enemy_mask=false`，槽位保留 | 需要测试“空槽不复用、后续行动不读错索引” |
| 51 动作迁移 | `10*5+1` 只是规格中的示例 | 本报告不批准；需同步 C++、mask、wrapper、模型、checkpoint 和轨迹版本 |

### 6.2 状态牌容量

当前 `CardManager` 的 `MAX_GROUP_SIZE=64` 只在可选 fixed-list 配置下有意义；默认声明的 draw/discard/exhaust 也可能是 `std::vector`：`include/combat/CardManager.h:22-42`。这不是 Python 输入契约，且 `CardManager` 没有把生成上界传给 wrapper。

可直接推导的压力来源：

- Three Sentries：每个 Bolt 生成 Dazed×2（A0–A17）或×3（A18+）。初始槽位 0/2 首次 Bolt、槽位1首次 Beam，50 个怪物回合内每只可约 25 次 Bolt；三只合计最多 150/225 张 Dazed，假设都未被消耗。
- Large/Medium Slime：Acid/Spike 的相关攻击每次生成 Slimed；Large Split 后两个中型继续行动，不能只按起始一只大史莱姆计算。
- 生成牌可以在弃牌堆持续存在；`Actions::MakeTempCardInDiscard` 逐张 push，`CardManager.cpp:103-116` 没有把总量压回初始牌数。
- `maxTurns` 构造参数只要求正数，默认值为50，但没有把所有可能配置限制在50。因此跨配置不能给出有限统一上界；若把50写进契约，也必须明确它是环境任务终止，而不是正版战斗自然失败。

当前 Python wrapper 在非手牌总量超过10时直接抛出 `ValueError`：`sts/env/wrappers.py:276-280`。C++ binding 的 `visiblePileCards` 又只接受 Bash/Defend/Strike：`bindings-util.cpp:25-54`。所以状态牌扩展的必要工作不是简单增加一个注册 ID，还包括：

1. 从固定牌组、敌人行动次数、分裂/生成路径和任务最大回合推导 `pile_capacity`；
2. 让 C++ 观测、registry、双 wrapper、schema/hash 同步接受 Dazed/Slimed 等类别；
3. 对手牌生成、满手牌、抽牌/弃牌/消耗的总量分别给上界和拒绝路径；
4. 在容量不足时显式拒绝配置或场景，不能静默截断、覆盖或映射 PAD。

## 7. 意图与观测扩展建议

以下是给主审/M2 的建议，不是本报告实施内容。

### 7.1 建议的敌人语义层

- 将内部 `MMID` 映射为经过正版可见性核验的语义：`ATTACK`、`ATTACK_DEFEND`、`BUFF`、`DEBUFF` 还不够覆盖 `SPLIT`、`ESCAPE`、`SLEEP`、`CHARGE`、`PROTECT`、`ENTANGLE`、`DAZED` 预告等；应集中维护枚举和字段版本。
- 保留 `intent_damage` 与 `intent_hits`，但只有攻击意图填值；非攻击意图不能用未知或零抹掉语义。
- 对可见且影响未来转移的状态按需新增字段：Artifact、Asleep、Metallicize、Enrage/其可见层数、Spore Cloud、Thievery、Wizard 充能、escaped/half-dead/occupied。每个字段先登记正版可见性，不能把内部可读性当成玩家可见性。
- `enemy_mask` 继续只表达当前可 target；如需要区分“未使用槽、死亡槽、逃跑槽、半死亡槽”，另加语义字段，不重用 mask 造成含义漂移。
- `monster_id` 可作为稳定类别，但不能因为模型知道 `Gremlin_Wizard` 就省略玩家实际看到的充能/意图字段；需按 D19 检查信息边界。

### 7.2 动作和版本建议

- Gremlin Gang / Lots of Slimes 在目标协议变更前保持延期；不要让后端自动把目标3/4折叠到0/1/2。
- 若未来选择五目标，必须新建动作/输入/轨迹版本并同步 `Action::decode`、环境 mask、wrapper、模型头、checkpoint 校验和评估场景；本预审不批准51动作。
- 非本任务的卡牌二次选择仍按 M1/M2 规则延期；遭遇扩容不能借“敌人 case 存在”绕过卡牌动作语法。

## 8. M4 建议覆盖矩阵

以下为建议的首批约十种普通遭遇和三个精英。`建议`不等于白名单；所有“通过”栏均应由未来测试实际产生。

| 建议桶 | 覆盖理由 | 必测场景 | 依赖/当前状态 |
|---|---|---|---|
| Jaw Worm | 单敌、首行动、攻击/格挡/力量成长 | A1/A2、A16/A17；Chomp/Thrash/Bellow；满回合完整战斗 | 当前 A0 可执行；其余未运行 |
| Cultist | 首回合非攻击、Ritual 回合末增长 | A1/A2、A16/A17；Ritual 首次跳增、连续 Dark Strike | 当前 A0 可执行；其余未运行 |
| Two Louse | 双目标、红/绿差异、Curl Up | A1/A2、A6/A7、A16/A17；杀死槽0/1、Web/Grow、Curl Up 一次性结算 | 当前 A0 可执行；其余未运行 |
| Small Slimes | 随机组合、非攻击 Lick、状态牌 | 两种初始组合；Acid/Spike M 攻击；Slimed 生成；A17 行动两侧 | 需 Slimed registry/容量/意图 |
| Blue Slaver | 单敌攻击+Weak | A1/A2、A16/A17；Rake/Stab、意图与 Weak 数值 | 需意图扩展 |
| Red Slaver | 单敌一次性 Entangle 语义 | 首次 Stab；Entangle 两侧；Scrape Vulnerable；核查 `usedEntangle` | 需确认静态风险后再实现 |
| Looter | 盗金、Smoke、Escape/空槽 | Mug 第1/2次、Lunge、Smoke、Escape、金钱和死亡/逃跑 mask | 需非攻击/逃跑意图 |
| Large Slime | 分裂和生成牌 | HP 阈值两侧；Acid/Spike；Split 槽0→0/1；中型继续行动；Slimed 容量 | 目标可表达，但观测/容量未完成 |
| Two Fungi Beasts | 双敌、Strength、死亡触发 | 两只不同死亡顺序；Grow/Bite；Spore Cloud；死后 Vulnerable | 需 Spore Cloud 可见性结论 |
| Three Louse | 三目标边界 | 初始目标0/1/2；杀死中间槽；三体完整战斗 | 目标容量可表达；组合行为未深查 |
| Gremlin Nob | 精英、非攻击 Bellow、Enrage | A2/A3、A17/A18；技能牌触发 Enrage；Rush/Skull 序列 | 需完整 intent/状态字段 |
| Lagavulin | 睡眠、醒来、连续攻击/Siphon | A2/A3、A17/A18；未受伤/受伤唤醒；Metallicize、Siphon | 需 Asleep/Metallicize/Dex 语义 |
| Three Sentries | 三目标边界、Artifact、状态牌增长 | A2/A3、A17/A18；槽奇偶初始意图；Beam/Bolt；Dazed 计数/容量；杀死中间槽 | 目标可表达；Dazed/Artifact/容量阻塞 |

推荐正式首批可考虑前十个普通桶（把 `Three Louse` 作为十号边界桶），但 `Gremlin Gang`、`Lots of Slimes`、`Exordium Thugs`、`Exordium Wildlife` 仍必须在候选索引中保留并标为“待查/延期”，不能从索引中删除后把“十种”写成全 Act 1 覆盖。

## 9. 最小测试清单（本次均未运行）

### 9.1 初始化与目标

1. 每个遭遇固定 seed 的初始槽位、`monsterCount`、`monstersAlive`、monster ID 和初始 intent。
2. Three Louse、Three Sentries 的目标0/1/2 mask；杀死中间槽后目标编号不压缩、不复用。
3. Gremlin Gang 目标3、Lots of Slimes 目标3/4 必须被配置契约拒绝，而不是重编号。
4. Large Slime 的 Acid/Spike 两种初态；HP 刚高于、等于、低于 `maxHp/2`；Split 后槽位和 turn index。

### 9.2 行动、状态和完整战斗

1. 每个非攻击意图都要有语义断言：Cultist Incantation、Jaw Bellow、Slime Lick/Split、Red Entangle、Looter Smoke/Escape、Fungi Grow、Nob Bellow、Lagavulin Sleep/Siphon、Sentry Bolt。
2. 多段/命中数断言：本批已有的连续/多段路径与 `intent_hits`，不得把非攻击变成 0/未知。
3. 状态结算：Curl Up 一次性、Ritual 首次跳增、Enrage 每次出牌、Lagavulin 睡眠解除、Sentry Artifact、Fungi 死亡 Vulnerable。
4. 生成牌：Small/Medium/Large Slime 的 Slimed、Three Sentries 的 Dazed，分别在 A0/A18 两侧核对数量、牌堆位置、可见字段和容量拒绝。
5. 完整战斗：每个批准桶至少覆盖胜利、失败、硬超时、所有目标死亡顺序和中途非攻击回合；异常轨迹不能伪造成失败0。

### 9.3 进阶两侧

按机制边界成对测试，而不是盲测21个完整场景：

- A1/A2：Louse bite、普通攻击、Cultist Ritual。
- A2/A3：精英攻击。
- A5/A6：玩家当前 HP。
- A6/A7：普通怪 HP、Louse Curl Up。
- A7/A8：精英 HP。
- A9/A10：Boss HP 与 Ascender's Bane 初始牌组影响。
- A10/A11：牌组与药水容量。
- A13/A14：Ironclad maxHP/出口 HP。
- A16/A17：普通遭遇高阶行动、Louse/Cultist/Slaver/Gremlin/Slime 分支。
- A17/A18：Nob、Lagavulin、Sentry 以及状态牌数量。
- A18/A19、A19/A20：确认这些阈值在目标 Act 1 桶中无漏项；若无影响，记录“等价/范围外”，不写成未测试支持。

## 10. 本次实际探针与未运行项

### 10.1 已运行的只读探针

探针直接导入现有 `third_party/sts_lightspeed/build/slaythespire.cp313-win_amd64.pyd`，没有重建、写入正式环境或修改配置。

- A0 seed `100000` 的 `JAW_WORM`：初始槽0为攻击、伤害11；结束回合后观察到 `DEFEND_BUFF`。
- A0 seed `100000` 的 `CULTIST`：初始槽0为增益；结束回合后观察到攻击6、Ritual=3。
- A0 seed `100000` 的 `TWO_LOUSE`：槽0/1 为红/绿 Louse，均为攻击6，Curl Up 分别为6/7。
- `GREMLIN_GANG` reset：按当前绑定得到 `ValueError: encounter is outside the minimal battle slice`。
- A1 `JAW_WORM` reset：按当前绑定得到 `ValueError: the minimal battle slice supports ascension 0 only`。

这些结果只证明当前 A0 绑定和最小观测路径的现状，不证明扩展机制、正版等价或 A1–A20 支持。

### 10.2 未运行

- 未运行 Gremlin Gang、Lots of Slimes、Small Slimes、Slaver、Looter、Large Slime、Fungi 或三个精英的正式 binding reset。
- 未绕过正式绑定直接构造 C++ `BattleContext` 做扩展战斗；不以“可通过内部构造”替代正式 API 契约。
- 未运行上述第9节测试、pytest 全量、扩展 wrapper 回归、进阶两侧测试、容量压力测试或完整战斗矩阵。
- 未运行训练、PPO、规则 Agent、Gate 2/3，也未修改 `eval_seeds.json`。

## 11. 待主审决定与明确缺口

1. 是否将 `Three Louse` 作为 M4 十个普通桶的边界桶，还是优先保留一个 Exordium 组合；不能用代表组合代替 `Exordium Thugs/Wildlife` 全组合审计。
2. Gremlin Gang/Lots of Slimes 是等待五目标动作迁移，还是明确从当前 M4 批次延期；无论哪种，均需保留原始候选和阻塞理由。
3. Red Slaver `usedEntangle` 是否为锁定后端缺陷；需用正版定点行为与最小静态/动态测试确认后再决定修复，不在本报告内修改。
4. Gremlin 小怪 `escapeNext` 的赋值来源和正版逃跑时点；当前源码未找到写入，需主审决定是否作为后端缺陷登记。
5. 选择新的敌人观测 schema：Artifact、Asleep、Metallicize、Enrage、Spore Cloud、Thievery、充能/保护/逃跑/分裂意图以及 dead/escaped/half-dead 语义如何分字段。
6. 锁定状态牌容量契约：按最大 `maxTurns` 推导、限制 `maxTurns`，或对生成牌采用显式场景上界；不能继续使用10行容量并期待运行时自然通过。
7. 进阶输入是否仍以 standalone battle 为主，还是等 M2 公开初态契约；A6/A10/A11/A14 会同时影响玩家初态、牌组、药水和 reward，不能只把 `ascension` 作为怪物 HP 参数。
8. 对扩展遭遇的正版一手行为核验范围和 D13 查阅点进行登记；本次已有 Cultist/Louse 定点材料，但其它扩展遭遇仍未完成正版行为证据。

### 交付边界

本文件是本并行任务唯一交付物。它提出覆盖、容量、观测和测试建议，但没有开放白名单、没有修改共享规格、没有修改正式环境，也没有把源码存在或本次 A0 探针写成 M4/Gate 通过。
