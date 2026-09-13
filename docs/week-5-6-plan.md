# Week 5–6：中等档、规则基线与配对评估

> 2026-09-12最新收口：固定comparison-battle-v2范围的M3编码/模型头/采集轨迹/恢复已完成，MLP/Set各两组GPU训练及开发对照通过学习改善标准，总训练评估18分17秒。见[本轮训练报告](comparison-ppo-report.md)。旧“模型迁移尚未完成”条目为早期状态；全卡扩展、正式Gate与学习理解不自动勾选。后续扩展只推进Set。

> 2026-09-12 路线修订：当前训练起点采用[真实卡组驱动的战斗训练计划](real-deck-training-plan.md)。真实完整卡组来自公开记录，其余战斗条件自主配置；本文旧历史入场还原要求仅适用于旧来源策略，不再作为新训练场景前置条件。原 M 编号、排期和 Gate 保留，新增工作状态以新计划为准。

修订日期：2026-09-08。执行依据：`spec-v6.md` §4、§6、§9、§10，及
`docs/decisions.md`。本计划从 D24 逐牌实体版验收通过后开始；依 D25，先在锁定的
`minimal-v1` 上完成有限 PPO+MLP 冒烟，再继续中等档代码扩容。这个前置检查不提前
训练 Set Transformer，也不替代中等档 Gate 3。

## 1. 两周出口

工程出口是 Gate 2：在锁定的中等档环境中，规则 Agent 与随机 Agent 使用相同评估
seed 做配对比较，D27 `battle_reward_v1` 综合回报差 bootstrap 95% 置信区间下界大于 0。无论是否通过，都必须报告
分桶结果、效应量、失败模式与回报分布；失败时按 §10 回查 Gate 1，不延长排期。

学习出口是能解释三件事：为什么配对 seed 能降低比较噪声，为什么规则策略不能读取
环境隐藏状态，以及为什么“更高平均回报”仍需置信区间和分桶诊断。

## 2. 当前起点与已发现约束

- D24 实体版已通过：完整回归 146 项，四路径 10000 配置稳定，最慢 Token 路径约
  3790 steps/s。见 `docs/entity-foundation-report.md`。
- 锁定的 `sts_lightspeed` 提交 `7476a819...` 自述覆盖全部 Ironclad 卡与敌人，本地
  源码也存在对应枚举和结算分支；这只证明上游宣称与代码入口存在，不替代本项目逐项
  接口、可见字段和回归验收。
- 当前项目适配器只允许 A0 的三种最小遭遇，并固定初始卡组；中等档必须显式扩 reset
  配置、观测字段、注册表与测试，不能只解除白名单。
- 当前动作是 31 位 `slot * 3 + target`。需要二次选择手牌或牌堆对象的卡不能直接纳入，
  除非先登记并实现动作语法扩展。为控制范围，第一批候选优先选择只有敌方目标、全体
  目标或无目标结算的卡。
- 目标容量也属于动作语法：31 位只支持 `target=0,1,2`，观测有 5 行敌人不代表能选择
  第 4、5 个敌人。锁定后端 `MonsterGroup.cpp` 的 Gremlin Gang 会创建 4 个敌人，
  Lots of Slimes 创建 5 个；这两项候选暂不开放。其他遭遇还须审计分裂/召唤后的最大
  目标索引；若需纳入，先登记目标容量和动作版本迁移，再同步模型、mask 与轨迹格式。
- D24 当前 `pile_capacity=10` 只适合 10 张最小牌组。中等档若使用更大固定牌组或产生
  Wound/Dazed，必须先确定最大牌组与生成上界，再显式升 schema；不得静默截断。

## 3. 来源裁定前的核验结果

Hugging Face `t22000t/slay-the-spire-1-cards` 可用于发现候选卡和读取统一字段，但当前
快照的 `provenance.json` 中 `sts_game_version=null`、`spire_archive_snapshot=null`。
因此它暂不作为本项目的数值真相，只作辅助目录；其 regex 衍生字段也须回到原始文本
或一手来源核对。

本机正版 `desktop-1.0.jar` sha256 为
`cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673`。已直接读取其中
`localization/eng/cards.json`，原十张候选卡的 class 构造器/升级方法与文本键定位已补入
`docs/m1-numeric-evidence.md`。JAR 本地化仍用 `!D!/!B!/!M!` 占位，数值以同一 JAR
class 方法常量为依据；这完成 M1 来源证据补充，不等于扩展卡行为验收。

来源等级暂定：

1. 本机锁定正版 JAR：一手，负责游戏语义与后续定点数值仲裁；反编译只按 D13 定点
   查阅，产物留在 `reference/` 且不入库。
2. 锁定 `sts_lightspeed` 源码：正式模拟器实际行为依据，负责确定当前训练环境会怎样
   结算；它不是正版游戏的一手来源。
3. Hugging Face 与公开 wiki：候选发现和交叉检查，冲突时不能覆盖前两项。

本次联网检索按 cross-search 流程使用 SearXNG 与 Tavily；Doubao 工具当前不可用。

M2 公开数据审计（2026-09-11）已补充：固定 `MaT1g3R/Slay-the-Spire-data`
提交 `097aaf3564c2247835162d267cbc7c55d2c9039e`，按数据集分层、路径字典序轮询
审计12个 `.run`；另固定 `colinking/runlogger` 提交
`02679f51c19c7a8d26da618ec0377faa390f347f` 的1个公开 Serialization Mod JSONL 示例。
结果是1个summary首场按标准规则可构造但来源未认证、11个有具体规则缺口；均未形成正式场景；详细日志有7个入口快照，
其中2个结构/可见字段已核验但内部状态未证明，5个因动态遗物计数、升级字符串或实体语义
歧义排除。原始文件在
`reference/public-run-audit/`，精简索引与哈希在 `docs/m2-evidence-index.json`、
`docs/m2-scene-candidates.json`、`docs/m2-exclusions.json`。Archive 只核验元数据，
不默认下载约29 GiB压缩包；该结果是小样本可行性证据，不是总体代表性证据。

## 4. 任务清单

| 状态 | 任务 | 工程产物 | 完成标准 |
|---|---|---|---|
| [x] | M0 最小切片 PPO+MLP 冒烟 | S1–S5工程完成，见 `docs/ppo-s5-freeze.md` | 三组开发CI通过，恢复验证与本地冻结完成；不宣称 Gate 3 |
| [x] | M1 核实卡表来源并筛第一批候选 | 75 类/150 版本全卡审计、原十张数值定位、35 类候选/排除表 | 候选方案收口；不是正式白名单，不包含扩展卡行为验收 |
| [x] | M2 定义首批中等档 reset 与容量契约 | 公开数据审计、A/B 重建索引、场景/排除索引、`docs/m2-real-battle-contract.md`、R1–R5 修复报告 | 首批派生策略/完整场景/语义与生成容量契约已实施并复核；99场可运行。更大分布与正式评估另验 |
| [~] | M3 扩卡与状态观测 | 35类＋5辅助牌、C++/Python语义接口；93卡牌及28消耗品测试通过 | 机制工程通过；新MLP/Set张量桥接/轨迹迁移和从头PPO短诊断未完成 |
| [x] | M4 扩 Act 1 遭遇与精英工程 | 14普通＋3精英；46专测/136机制诊断通过 | 工程通过；真实精英初态和更大真实分布仍不足 |
| [x] | M5 实现规则 Agent | 规则/随机66位接口与runner；27专测，99场规则集成通过 | 只读规范观测/mask；当前范围工程通过，不等于Gate或独立理解验收 |
| [ ] | M6 实现配对评估 | `sts/eval/protocol.py`、`scripts/run_eval.py` | seed 配对、bootstrap CI、分桶、run 元数据落盘 |
| [ ] | M7 审计 v6 奖励兼容与指标分表 | battle 综合回报/胜率/获胜条件HP及版本记录 | `battle_reward_v1` 固定0.5，不再默认校准；改变须新建奖励版本，run 不混入本表 |
| [ ] | M8 Gate 2 收口 | `docs/gate-2.md` | 规则 vs 随机的配对 CI 与失败分析完整 |

## 5. M1 第一批候选框架

候选池目标为 30–40 个 Ironclad 可用类别，不等于单局牌组塞入 30–40 张。M1 的现有
来源记录保留，但 M2–M4 暂停到 M0 完成。最终数量须在
数值与动作语法审计后锁定。先以以下机制簇筛选：

- 基础与直接攻防：Bash、Strike、Defend、Anger、Body Slam、Clash、Cleave、
  Clothesline、Heavy Blade、Iron Wave、Perfected Strike、Pommel Strike、Shrug It
  Off、Sword Boomerang、Thunderclap、Twin Strike、Wild Strike。
- 抽牌、能量与消耗：Battle Trance、Bloodletting、Havoc、True Grit、Seeing Red、
  Second Wind、Sever Soul。
- 状态与多段/全体：Intimidate、Power Through、Pummel、Reckless Charge、Shockwave、
  Uppercut、Whirlwind。
- 力量与长期效果：Inflame、Spot Weakness、Demon Form、Metallicize、Combust、Evolve、
  Feel No Pain、Fire Breathing、Rage。

这份列表是审计候选，不是已裁定正式卡表。Armaments、Burning Pact、Headbutt、Dual
Wield 等需要显式二次选择的卡先列入排除/延期表；若 30–40 目标无法在现有动作语法下
合理达到，再先登记动作协议变更，而不是在后端自动替玩家选目标。

## 6. 建议遭遇候选

在现有 Cultist、Jaw Worm、Two Louse 基础上，优先审计 Act 1 的 Small Slimes、Blue
Slaver、Red Slaver、Looter、Large Slime、Two Fungi Beasts，以及 Gremlin Gang / Lots
of Slimes / Exordium Thugs / Exordium Wildlife 中的代表性多敌遭遇；精英固定审计 Gremlin
Nob、Lagavulin、Three Sentries。

最终普通遭遇取约 10 种，选择标准是：覆盖单敌/多敌、debuff、状态牌、强度成长和
Artifact 等差异，同时不让同类组合数量挤占实现时间。不能仅因上游枚举存在就开放。

## 7. 下一执行点

2026-09-11：M0/S1–S5工程已完成，三初始化及冻结记录见`docs/ppo-s4-report.md`、`docs/ppo-s5-freeze.md`。
M1 已收口，M2 公开数据审计与 R1–R5 修复契约已交付，第二轮主审后仍有来源兼容/正式容量/分组缺口；解决前不开始
M3 代码扩容，不开放正式白名单，不启动扩展卡行为测试或训练。

旧 M2 人工15张牌组仅保留为机制诊断历史，见 `docs/m2-battle-contract.md`；正式公开初态审计、场景索引和 `public-battle-v1` 契约见 `docs/m2-public-data-audit.md` 与 `docs/m2-real-battle-contract.md`。具体版本/注册表、C++ 状态注入和后续机制批次仍留给 M3 以后。

2026-09-11 用户修订：M2 正式训练/评估初态改从公开玩家对局筛选重建；先审计公开数据小样本，再定场景清单和容量。人工15张牌组仅作机制诊断，不能代替真实分布。详见 decisions.md 最新M2记录。

M2 工程交付已完成并等待主审审核：审计工具、真实原始证据、机器可读场景/排除清单、公开初态契约及授权范围同步已落盘。主审确认前不进入 M3，不修改正式环境/模型，不启动 PPO，不修改 `eval_seeds.json`。

第二轮定点结果：原生A优先；sample-007首层在标准规则下可构造，来源版本/mod兼容仍未证明。
其余11个summary保留具体Neow/遭遇等缺口，2个详细B场景内部恢复未证明。M2不收口，证据见
`docs/m2-entry-a-evidence.md`；不将仅4类起始牌和1个run视为中等环境正式分布。

2026-09-12批量场景库：扫描固定仓库全部.run后按角色筛选203份，关联去重157个run；
第一幕1282场中257个A规则候选，来自118个run，包含160种卡组多重集、72类牌、14普通遭遇、
5遗物和27药水。研究预划分无泄漏；正式准入仍为0。接下来按已有场景的来源兼容、事件/商店前缀、
遗物/药水状态和完整内容闭包推进，不能用单场多seed代替。详见 `docs/m2-corpus-report.md`。

2026-09-12主审并行实施最新状态：已进入M5并完成规则基线工程首验。完整仓库566项通过；
修复后二进制99派生场景随机/规则各一次无异常，规则99胜、随机72胜，仅开发集成不作Gate。
本页早期“等待M2后不得实施M3”段落保留历史，当前以最新decisions并行裁定及
`docs/public-battle-implementation.md`为准。M3新的张量/训练迁移仍未完成，M6–M8尚未开始。
