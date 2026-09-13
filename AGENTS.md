# AGENTS.md — STS RL Agent 工作区

## 工作区性质

- 当前为 **STS RL Agent 执行工作区**，唯一执行依据是 `spec-v6.md`（2026-09-08 双任务奖励修订；不重置原排期）：锁定的 `sts_lightspeed` C++ headless STS1 Ironclad 战斗后端（Python 保留教学/规范层） → 随机/规则两条基线 → A 阶段 Set Transformer + PPO → B 阶段 Decision Transformer，A/B 对照即产出。真实目标：通过工程实践理解 Transformer 原理，游戏是载体。
- 全部文档与代码注释用中文；文件名用英文小写 kebab-case。
- 目录名 `sts2` 是 v3 时代（STS2 方案研究）的历史遗留，不改名；实际规格来源是 **STS1**。
- 排期与止损以 `spec-v6.md` §9/§10 为准；学习目标与方法见 `docs/learning-path-v2.md`，`学习路径.md` 为旧版历史存档。

