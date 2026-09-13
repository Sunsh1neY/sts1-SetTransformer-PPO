# STS RL Agent 项目方案 v6

修订日期：2026-09-08。变更登记：[决策日志 D27](docs/decisions.md)。

> **文档状态：当前唯一执行依据。** 以 v5 为底稿合并 D27 的双任务奖励、终止、自举、数据和版本契约；v5 冻结为历史方案。
> `spec-v4.md` 及更早版本继续保留历史。完整 run 的奖励目标已在本版定义，但地图、事件、构筑与 RunEnv 集成仍不进入当前排期，不能据此宣称完整爬塔已实现。
> 学习目标与方法见 [学习路径 v2](docs/learning-path-v2.md)，旧 `学习路径.md` 为历史存档；执行排期与止损分别以本文 §9 / §10 为准。v6 不重置项目起算日、预算和 Gate。

本版重点：把正式目标拆成 `battle` 与 `run` 两个任务；当前独立战斗继续使用 `battle_reward_v1`，未来完整爬塔只在最终通关时使用 `run_reward_v1`。同一任务内 MLP-PPO、Set-PPO 与 DT 共用逐步奖励和真实 RTG；两个任务不混标、不直接排名。v5 的接口容量、训练闭环、排期、Gate 与评估 seed 均保留。

---

## 0. 项目定位

### 0.1 真实目标

**通过工程实践理解主流 Transformer 技术原理。** 游戏是载体，不是目的；不服务于留学申请或导师匹配。

具体到可验证的理解目标：

- 手写 QKV 投影、multi-head attention、attention pooling，并能解释每个张量形状的来源；
- 理解 padding mask 与 causal mask 是同一机制的两种掩码形状；
- 理解置换不变编码（Set Transformer）与自回归序列建模（Decision Transformer）各自的适用边界；
- 能说清"下一 token 预测"如何等价于"下一步决策"，以及 return-conditioning 在其中多做了什么。

### 0.2 交付物


## 2026-09-12 输入v3执行补记

按用户裁定与决策日志，当前统一实体输入改为115维卡牌、无目标伤害预览关系、保留后端格挡预览；取消466张主动截断，保留资源/后端保护。费用、顶牌与奖励待办以docs/entity-input-v3-contract.md为准。旧版本结果不改名，无新增正式长训授权。

## 2026-09-13 全战士卡牌工程验收补记

按用户限定范围完成75类150基础/升级版本；正式训练、全敌人药水与完整run不在本次结论内。依据docs/decisions.md及docs/ironclad-full-cards-report.md；旧实验保持冻结，奖励与评估种子不变。
