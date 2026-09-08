# AGENTS.md — STS RL Agent 工作区

## 工作区性质

- 当前为 **STS RL Agent 执行工作区**，唯一执行依据是 `spec-v6.md`（2026-09-08 双任务奖励修订；不重置原排期）：锁定的 `sts_lightspeed` C++ headless STS1 Ironclad 战斗后端（Python 保留教学/规范层） → 随机/规则两条基线 → A 阶段 Set Transformer + PPO → B 阶段 Decision Transformer，A/B 对照即产出。真实目标：通过工程实践理解 Transformer 原理，游戏是载体。
- 全部文档与代码注释用中文；文件名用英文小写 kebab-case。
- 目录名 `sts2` 是 v3 时代（STS2 方案研究）的历史遗留，不改名；实际规格来源是 **STS1**。
- 排期与止损以 `spec-v6.md` §9/§10 为准；学习目标与方法见 `docs/learning-path-v2.md`，`学习路径.md` 为旧版历史存档。

## 文档层级（权威顺序）

| 文件 | 地位 |
|---|---|
| `spec-v6.md` | **当前唯一执行依据**（2026-09-08 双任务奖励修订；不重置原排期），改动须先过 `docs/decisions.md` 登记 |
| `docs/decisions.md` | 决策日志：裁定 / 理由 / 推翻条件；推翻既有决策必须先在此登记 |
| `docs/mechanics.md` | 结算顺序书面规格，`tests/test_ordering.py` 的唯一依据；与日志对拍冲突时以日志为准并修订本文档 |
| `docs/learning-path-v2.md` | 学习目标、三种思维、双环推进与理解验收方法；不覆盖 v6 的执行范围、排期和 Gate |
| `学习路径.md` | v1 历史存档，已由学习路径 v2 重写替代 |
| `spec-v5.md` / `spec-v4.md` | 冻结历史方案；历史验收仍保留当时出处 |
| `spec-v3.md` / `spec-v2.md` / `spec.txt` | 冻结愿景稿（STS2 / A10 / 完整 run 不进入本项目排期），仅供对照，勿据此实现 |
| `research/` | v3 时代 STORM 研究报告与项目尽调，随 v3 冻结 |
| `docs/report.md` | 第 17-18 周产出，尚不存在 |

## 执行红线（继承自 v4、由 spec-v6 维护，勿翻案）

- `eval_seeds.json` 提交后**不可变**；评估 seed ∈ [0, 1000)，训练 seed ≥ 100000；每个 run 记录其 sha256。
- seed 不进状态编码，只保留给环境复现。
- 动作索引指向手牌槽位（槽位按抽牌顺序确定分配）；token 特征只用语义，绝不编码槽位号。
- 合法动作列表由环境直接给出，模型不猜合法性；掩码在 softmax 之前施加，梯度用掩码后分布计算。
- 同一任务内 MLP-PPO、Set-PPO 与 DT 必须使用同一逐步 reward、γ 和完整真实 RTG；`battle_reward_v1` 与 `run_reward_v1` 不得混用，改动须新建奖励版本并从可验证字段重算数据。
- 当前 `battle` 首次胜利奖励为 `1+0.5*h_exit`；未来 `run` 仅首次最终通关得1。普通战斗胜利不得终止全局 run；完整 RunEnv 未实现时拒绝正式 run 训练。
- 真终止不自举；外部截断使用 reset 前最终观测自举但 GAE 不跨 reset。异常轨迹不伪造成失败0；v6 基线固定 β=0。
- Gate 触发即执行预写死的降级路径（§10），不当场重新谈判；任何单一问题连续 3 天无进展，按 §10.3 元规则强制停下换方向。
- 第 17-18 周不写新功能。
- 反编译源码只作规格争议仲裁（D13），不得照抄进模拟器；产物放 `reference/`（gitignore）不入库。
- 仓库骨架按周生长：不预建空文件与空目录（掩盖进度）。

## 文档与事实规范

- 事实主张（游戏机制数值、论文结论）须有一手来源；尚未核实的事实显式标注 `[未核实]`（v6 附 B，按证据持续销账）。
- 引用登记沿用 `research/sts2-a20-decision-model-sources.md` 的编号日志格式（可信度等级 + 核验日期）。

## v3 时代历史裁定（随 spec-v3 冻结，不再指导执行）

以下条目在新排期中均不生效，与 spec-v6 冲突时一律以 v6 为准：A10 目标（非 A20）、M0-M4 里程碑顺序、反编译 sts2.dll 主路线、v1→v2 五处结构性变更、卡组-地图双塔评估器、KL 锚定退火、AlphaStar Unplugged 精读待办。
