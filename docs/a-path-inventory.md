> **Historical navigation notice (2026-09-16):** This is a dated phase record or instruction set, not a current work order. Use the [documentation map](README.md), [spec-v6](../spec-v6.md), and registered amendments for current work. Original commands, paths, budgets and evidence below retain their historical scope.

# A路径实际接口与改动映射

> 历史阶段记录：A 路径现已依 I5 合入 main；本文中的旧工作区路径、待实现状态和当时启动记录保留历史身份。当前入口与验收见 [主线整合报告](a-path-main-integration-report.md)。


2026-09-13。基准main与远端为615cffa，执行工作区sts2-integration，分支codex/a-path-agent。任务书以根目录a-path/sts-a-path-implementation-v1.md为准；原任务包agent-tasks/a-path路径不适用于当前目录。算法裁定见决策I0，当前用户推送授权见a-path-baseline.md。

## 环境与历史模型

统一IroncladEnv继承full_card_public，仍是development机制入口。真实候选含NORMAL快照动作与SELECT_CARD凭据；SELECT_CARD旧target指向结算来源，不是敌人。训练不可调用diagnostic入口冒充正式准入。后端已在本执行目录干净重建，主目录仍保留历史后端。

当前CARD116、ENEMY774、PLAYER_GLOBAL含公开选择阶段；候选额外携带五维结算上下文。holds_card用独立扣牌CARD与不透明引用路由，未知实例字段继续遮罩。旧models/entities.py两层均值池化、models/unified.py四层PMA旧动作头和冻结MLP均保留。

## 本里程碑实现

| 路径 | 实际职责 |
|---|---|
| sts/models/apath.py | 版本a-path-four-sab-pma-pointer-v1；四层SAB64维4头FF128、Pre-LN/GELU/dropout0、单seed PMA；按来源task Query统一归一化，来源条件敌人分布、特殊动作和Value |
| sts/agents/apath.py | act/evaluate_actions/value_only；显式采样RNG；返回历史样本、来源、目标、联合logp、Value与完整路由，不持有环境句柄 |
| sts/env/entities.py | 复用既有严格实体校验；新增可选空候选打包，仅用于终局Value-only，旧调用默认仍拒绝完全空候选 |
| tests/test_apath.py | 数学oracle、真实候选与六种选择、一次编码/推进、历史重评估、换位、扣牌融合、数值边界 |
| scripts/audit-a-path-data.py | 只读关联分组与最终卡组静态候选核查，不重写原批次、不批准训练 |

上下文只追加到PLAYER_GLOBAL类型专用投影；共同注意力使普通来源实体和PMA均可读取，普通CARD特征未加入内部结算流。来源按操作、具体实体和必要模式分组；不同副本独立，同一来源的目标不会重复占据第一阶段。NO_TARGET固定概率1，与enemy0无关。

当前六类真实选择为ARMAMENTS、DUAL_WIELD、EXHAUST_ONE、EXHUME、HEADBUTT、WARCRY；DISCOVERY仅登记接口操作，实际Ironclad仍拒绝；未新增多选/确认机制。

## 尚未实施的迁移

- 正式场景准入、容量证明与采集器：尚未开放train/evaluation入口。
- PPO可复用现有compute_gae及ppo_loss，但新collector、固定rollout、长度分桶/微批次梯度累积尚未实施。
- 当前Agent支持采样RNG往返和历史重评估；不等于模型/优化器/环境/活动轨迹checkpoint。完整重放恢复与CPU/CUDA下一更新一致性待做。
- 数据相关组收缩产生新的训练范围选择，详见a-path-data-decision.md，裁定前不冻结正式数据池。
- 尚未运行真实PPO smoke、受限长训、评估或最终合入main；四小时训练评估预算尚未开始。
