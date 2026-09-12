# 公开派生战斗环境与M5工程验收

日期：2026-09-12。主审直接整合三个subagent并完成实测。已经进入M5，规则基线实现与当前范围集成通过；本报告不宣布正式Gate 2、PPO收益或完整中等档学习管线完成。

## 本轮交付与实际状态

| 工作 | 工程证据 | 保留边界 |
|---|---|---|
| M2首批派生场景与契约 | 来源策略`public-derived-standard-v1`；99完整内容场景/75run；中央JSON动作、注册表、容量和版本；实际99场均可执行 | 历史mod/行为等价仍unverified；研究划分不等于正式训练/评估；真实场景只覆盖22个初态卡类和6普通遭遇 |
| M3原生接口、卡牌与状态 | 35类Ironclad＋5辅助牌、8遗物、15直接药水；独立C++/Python语义接口；卡牌93测试、药水遗物28测试通过 | 新MLP/Set张量桥接、模型头/轨迹迁移与扩展环境从头PPO短诊断未做；不能用接口通过替代学习管线通过 |
| M4遭遇工程 | 14普通＋3精英，A0/A20随机/规则共136机制诊断；46专测通过；分裂/5目标/死槽/意图/终止与截断区分 | 精英是真实规则的显式诊断夹具，现公开数据没有已准入精英初态；不当作真实精英分布或正式胜率 |
| M5规则基线 | 纯规范观测评分器及66动作runner；27单测通过；修复后二进制上99真实派生场景规则/随机各一次均自然终止，无异常 | 一阶启发式，不证明最优；未进行M6正式配对CI和M8 Gate |

完整仓库回归：**566 passed in 11.75s**，无失败或跳过。旧minimal-v1测试包含在内。原实验文档和checkpoint未回填为新结果。

## 当前可执行契约

唯一机器契约：`sts/env/public-battle-contract.json`。`scripts/generate-public-contract.py`生成C++常量，已接入标准构建脚本。旧M2研究提案中的固定状态8行、固定牌堆10、50回合新任务等不作为本次实际接口。

- 环境：`PublicBattleEnv`；旧`IroncladBattleEnv`/`LightspeedBattleEnv`及31动作接口独立保留。
- 来源：公开记录中的实际内容/前缀＋明确锁定标准规则派生；不称历史精确回放，未知修饰/计数/前缀仍整场拒绝。
- 入口A：`pre_combat_initialization`，阶段`before_destination_room_entry`；牌组、HP/maxHP/gold、进阶/楼层、完整遗物及药水、遭遇必须明确。当前遗物子集无目的普通/精英房间额外独立入口效果，其开战效果只执行一次。B快照不能直接转A。
- 规范观测：`public-observation-v1`，hand及完整draw/discard/exhaust、player、enemies、potions、relics、action_mask。卡牌项目ID按中央表映射，保留每个副本/升级；非手牌按可见字段排序。伤害预览为每目标每段已修正值，格挡预览已修正；不重复加力量/易伤。
- 状态：具名powers字典，完整保留公开状态；敌方Strength直接读取当前公开数值。`public_history`仅从实际已执行的公开意图计数，区别蓄力/睡眠历史，不暴露monster miscInfo/moveHistory。`player.turn`为后端从0开始的回合索引，不冒充源字段。
- 动作：0–49=`hand_slot*5+target`，50结束回合，51–65=`51+potion_slot*5+target`；无目标只开target0，敌方目标只开可寻址行。3药水预留行不等于A20拥有3槽；A20实际2槽。
- 来源metadata、环境seed只进info。模型/规则不读env/info/RNG、内部实例ID、真实抽牌顺序或未来意图。wrapper对隐藏字段与未知schema明确拒绝。
- 新观测不直接喂入旧31动作MLP/TokenWrapper或旧checkpoint。还未完成的新模型编码迁移需要独立验收。

## 容量与终止

实际后端三牌堆为vector；手牌10、临时limbo10、master deck96和int16临时ID是不同约束。编译期开启64张fixed-list选项时，新adapter直接拒绝构建。

当前白名单不含自动打牌/复制药水/二次选择生成。一次玩家出牌最多创建2张状态牌；一次结束回合至多5个敌人、每个最多3张，统一单decision上界15。外部采集预算1–512动作，因而：

`96 + 512 × 15 = 7776 < 32767`。

这个上界同时在中央契约与C++静态断言中保存，运行时检查累计生成量。它不意味着任意后续生成机制可以自动纳入，也不意味着旧MLP固定牌堆10可以复用。

预算在动作实际执行后检查。自然胜负优先；仍未结束才返回truncated，保留完整最终观测和原MDP合法动作供自举。runner停止，不能继续step。没有新增“512步游戏判负”，也没有溢出后丢牌再补一个残缺final observation。

## 三处实测驱动的机制修复

1. **Seeing Red耗尽缺项**：能量变化正确，但打出后进弃牌堆。正版构造exhaust=true，升级只改费用；在`Cards.h::doesCardExhaust`补SEEING_RED，不在adapter补牌。实际耗尽与FeelNoPain触发测试通过。
2. **Red Slaver重复Entangle**：高HP机制夹具在多个分离回合反复被束缚，证明不是同一状态持续显示。正版takeTurn设usedEntangle，锁定后端未写miscInfo；已补标志。相关Stab阈值50同时改为正版55。两个seed各30轮回归均只一次Entangle。
3. **敌人力量观测遗漏**：该后端Strength不依赖普通状态bit，原枚举检查会漏。新adapter直接导出非零Strength，Cultist Ritual首次跳增与后续预告伤害/实际伤害测试通过。

另修复协议边界：无计数遗物counter=null应被规则策略接受；负费用状态牌只在mask全false时允许；模糊Bash+和不支持升级整体拒绝。

定点来源及前后轨迹分别见`docs/m3-native-adapter-report.md`、`docs/m3-consumables-report.md`、`docs/m4-public-encounter-report.md`。反编译产物仅留ignored reference。

## 修复后99场集成结果

两策略每场使用相同环境seed `910000 + 场景索引`，随机策略独立seed。此处是研究集成检查，未计算正式CI，不使用eval_seeds.json作为反复调试集。

| 策略 | 正常终止 | 异常/截断 | 获胜 | 平均回报 | 动作数 |
|---|---:|---:|---:|---:|---:|
| 随机 | 99 | 0/0 | 72 | 0.9470939659 | 1637 |
| 规则 | 99 | 0/0 | 99 | 1.4133867245 | 914 |

这批主要是第一幕早期普通战斗；同一run的多个楼层也相关。不能把99/99推广到精英、全部构筑或总体泛化。M6仍需锁正式评估协议与按run关联组处理统计，不把本表直接当作Gate。

逐场记录：`reference/public-scene-integration.json`，由`diagnose-public-scenes.py`生成并记录manifest/config/脚本/扩展哈希。早先M5子agent报告的915动作对应修复前二进制；最终以本节914动作为准。

## 构建与复现

```powershell
./scripts/build-lightspeed.ps1 -Jobs 3
python scripts/diagnose-public-scenes.py
python scripts/diagnose-public-encounters.py
python -m pytest -q
python -X utf8 scripts/check-spec-v6.py
git diff --check
```

后端全部新增文件、生成常量、SeeingRed/RedSlaver修复已进入`patches/lightspeed-battle-env.patch`，不是只留在ignored third_party。补丁完整反向检查通过；标准build-lightspeed.ps1实际执行完成，minimal/public导入均通过；最终包装/策略增补复核43项通过。上游commit与依赖锁仍相同，补丁/二进制指纹已改变。

最终扩展SHA256：`4e61df0bae90cc8899f5e18b0cb2acc8e5d32f9ec650e4e51d592ce61fe8b48b`。
本轮补丁SHA256：`fe8168a3cbfa5595fefa7e9bf205ea9db0dc017096ac4809120feb8d8896c9aa`。
旧冻结实验的原指纹仍保留；严格恢复原实验应使用其原补丁/构建，不把新指纹静默写回旧checkpoint记录。

## 仍未做

- public观测到MLP/Set的张量/模型头/checkpoint/训练轨迹迁移，以及该环境从头PPO短诊断；M3学习管线不得标为完成。
- 更多事件/商店前缀和动态遗物；真实精英初态/燃烧强化数据。当前99场并未达到整套中等分布的代表性。
- M6正式配对评估、M7奖励/指标分表审计、M8 Gate 2。
- 用户对M2–M5原理的独立理解验收。本轮是工程推进，不自动记作学习掌握。

未commit/push，未启动新的PPO训练。
