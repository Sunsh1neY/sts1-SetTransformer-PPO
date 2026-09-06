# Week 5–6：中等档、规则基线与配对评估

修订日期：2026-09-06。执行依据：`spec-v4.md` §4、§6、§9、§10，及
`docs/decisions.md`。本计划从 D24 逐牌实体版验收通过后开始，不提前实现 PPO。

## 1. 两周出口

工程出口是 Gate 2：在锁定的中等档环境中，规则 Agent 与随机 Agent 使用相同评估
seed 做配对比较，胜率差 bootstrap 置信区间下界大于 0。无论是否通过，都必须报告
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
- D24 当前 `pile_capacity=10` 只适合 10 张最小牌组。中等档若使用更大固定牌组或产生
  Wound/Dazed，必须先确定最大牌组与生成上界，再显式升 schema；不得静默截断。

## 3. 来源裁定前的核验结果

Hugging Face `t22000t/slay-the-spire-1-cards` 可用于发现候选卡和读取统一字段，但当前
快照的 `provenance.json` 中 `sts_game_version=null`、`spire_archive_snapshot=null`。
因此它暂不作为本项目的数值真相，只作辅助目录；其 regex 衍生字段也须回到原始文本
或一手来源核对。

本机正版 `desktop-1.0.jar` sha256 为
`cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673`。已直接读取其中
`localization/eng/cards.json`，抽查 10 张候选卡的效果语义：Bash、Anger、Cleave、
Shrug It Off、True Grit、Inflame、Demon Form、Spot Weakness、Whirlwind、Power
Through。语义与 HF 描述及锁定后端入口一致；但 JAR 本地化用 `!D!/!B!/!M!` 占位，
本轮尚未完成数值抽查，不能把 U3 标为销账。

来源等级暂定：

1. 本机锁定正版 JAR：一手，负责游戏语义与后续定点数值仲裁；反编译只按 D13 定点
   查阅，产物留在 `reference/` 且不入库。
2. 锁定 `sts_lightspeed` 源码：正式模拟器实际行为依据，负责确定当前训练环境会怎样
   结算；它不是正版游戏的一手来源。
3. Hugging Face 与公开 wiki：候选发现和交叉检查，冲突时不能覆盖前两项。

本次联网检索按 cross-search 流程使用 SearXNG 与 Tavily；Doubao 工具当前不可用。

## 4. 任务清单

| 状态 | 任务 | 工程产物 | 完成标准 |
|---|---|---|---|
| [~] | M1 核实卡表来源并筛第一批候选 | 来源记录、10 张数值抽查、候选/排除表 | U3 在决策日志销账；每张候选动作语法可表达 |
| [ ] | M2 定义中等档 reset 配置 | `configs/env_medium.yaml`、配置校验 | seed/牌组/遭遇显式，拒绝范围外输入 |
| [ ] | M3 扩卡与状态观测 | registry、C++ 导出、wrapper、回归 | 30–40 类可用；Strength 等可见字段不遗漏 |
| [ ] | M4 扩 Act 1 遭遇与精英 | 遭遇白名单、意图映射、测试 | 约 10 种普通遭遇 + 3 精英可完成战斗 |
| [ ] | M5 实现规则 Agent | `sts/agents/rule_agent.py` 与测试 | 只读规范观测和 mask；无隐藏状态或规则旁路 |
| [ ] | M6 实现配对评估 | `sts/eval/protocol.py`、`scripts/run_eval.py` | seed 配对、bootstrap CI、分桶、run 元数据落盘 |
| [ ] | M7 校准并锁死血量系数 | 回报分布与 D25 或确认记录 | 只允许本阶段校准一次，之后 A/B 共用 |
| [ ] | M8 Gate 2 收口 | `docs/gate-2.md` | 规则 vs 随机的配对 CI 与失败分析完整 |

## 5. M1 第一批候选框架

候选池目标为 30–40 个 Ironclad 可用类别，不等于单局牌组塞入 30–40 张。最终数量须在
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

M1 下一步是从正版 JAR 定点取得上述 10 张卡的 base cost / damage / block / magic
number，与 HF 原始记录及锁定后端常量逐项对表；冲突单列。随后按“现有 31 位动作能否
完整表达”筛选 30–40 张正式候选，并在 `docs/decisions.md` 登记来源和卡表边界后，才
开始 M2/M3 代码扩容。
