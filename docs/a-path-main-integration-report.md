# A 路径合入 main 与主线验收

日期：2026-09-14。依据决策 I5，用户明确 A 路径为当前及后续主要方向，要求合入 main。

## 结果与真实调用链

从已归档提交 `2f3beb94433a159106934a6459eebdc4bcf5c421` 合并模型、Agent、独立采集池和 PPO 工程。保留 main 已验收的全卡、一二幕环境修复；合并前 main 为 `e967255`。仅决策日志和规格追加段落发生冲突，双方历史记录均保留，最新执行口径为 I5。

```text
scripts/run-a-path-ppo.py
→ sts.train.apath.APathTrainer
→ sts.env.apath.APathEnv
→ sts.env.ironclad.IroncladEnv / sts.env.full_card_public.PublicBattleEnv
→ slaythespire.IroncladExpandedBattleEnv（当前 main 的 C++ 后端）
→ 公开观测 → sts.models.apath.encode / batch_samples
→ APathActorCritic → 两阶段联合分布 → 带快照凭据的动作路由
→ APathEnv.step → rollout → GAE → 联合 PPO → 下一轮采集
```

交互 Agent 为 `sts.agents.apath.APathAgent`。当前模型 261,506 个参数：四层 SAB、64 维、4 头、FF128、单 seed PMA、来源/特殊动作分布及来源条件目标分布，联合 log-prob 和精确联合熵。原 `run-unified-ppo.py` 的固定 66 动作分类头保留历史身份，不是后续主入口。

## 合并修复与数据边界

- A 路径池原本绑定旧运行契约和卡牌注册表，直接合并会因指纹不匹配拒绝运行。现绑定 main 已验收版本，同时更新来源注册表哈希、重算池内容哈希。
- 原池与新池仅四个顶层项改变：`runtime_contract_hash`、`registry_hash`、`source_hashes`、`payload_sha256`。全部卡组、来源关联、条件、遭遇、采样策略、资源边界和历史验收记录相同。
- 数据审计、分组提案、来源采样审计重新计算后，变化仅为来源注册表哈希；卡组划分和所有统计一致。原审计哈希不是通过放宽校验绕过的。
- 修复数学金标准夹具在 Windows 默认 GBK 下读取 UTF-8 JSON 失败的问题；未改夹具数值。
- A 路径分支原有的 `collate(allow_empty_candidates=True)` 随分支合入，用于无动作终局的价值计算；默认调用行为不变。模型信息字段、奖励、评估种子均未改变。

训练仍为 39 个卡组、33 个来源组、两条件、五遭遇，共 390 个训练初始配置；来源组均匀、组内卡组均匀，条件与遭遇均匀，环境 seed 独立。内容分组仅作诊断，PPO 全局 shuffle。不把全卡诊断入口的 44 个一二幕遭遇自动纳入训练。

池内 `runtime_report_sha256` 及 780 局统计仍指向历史准入证据，不能当作新后端重跑结果。本轮新后端证据见下表与独立 JSON。

## 实际验证

| 验证 | 结果 |
|---|---|
| A 路径定向 CPU | 34 passed，1 个 CUDA 用例另行执行 |
| 完整 CPU 回归 | 1,379 passed，1 deselected（CUDA），69.56 秒，无失败、无跳过 |
| 独立 C++ 状态夹具 | 1 passed，2.14 秒 |
| CUDA 更新与精确恢复 | 1 passed，4 个非 CUDA 用例未选，18.80 秒 |
| 390 个注册训练初态 | 全部完成真实 reset、模型前向、合法路由 step 和下一观测编码 |
| 最终池来源哈希补齐后 | 4 项 CPU 训练/恢复用例再次通过，4.98 秒 |

训练用例实际执行 PPO 更新，检查参数改变、保存后活动环境重放，以及恢复后的下一次更新参数和 rollout 逐值一致；二次选牌中间状态保存后重新绑定有效路由凭据。CUDA 亦验证下一更新一致性。390 配置检查只做单步，不冒充完整 episode 或学习效果验收。

CPU/CUDA 和完整回归在池的运行契约已绑定新后端后执行；随后只补齐来源注册表元数据并重算池哈希，再运行最终池 CPU 恢复和 390 配置验证。此元数据修正不改变采样或游戏结算。

机器可读证据见 [a-path-main-integration-evidence.json](a-path-main-integration-evidence.json)。本地详细日志为 `reference/a-path-main-focused.log`、`a-path-main-cpu-regression.log`、`a-path-main-cpp-regression.log`、`a-path-main-cuda-regression.log`、`a-path-main-final-pool.log`。

## 历史产物与后续工作

归档原件及 Git bundle 未改写；原检查点继续绑定原源码、池和后端，不放宽 `APathTrainer.load` 的指纹检查。本次合入代码并完成短工程闭环，没有新开四小时训练、重训旧初始化或声明策略收益。

后续默认从当前 A 路径推进。扩大一二幕训练池仍须单独确认分布、来源与容量证据；正式训练预算、开发评估、Gate 和泛化另行验收。恢复历史产物见 [归档说明](desktop-repo-cleanup-2026-09-14.md)。
