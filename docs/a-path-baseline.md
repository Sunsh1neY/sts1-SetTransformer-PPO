> **Historical navigation notice (2026-09-16):** This is a dated phase record or instruction set, not a current work order. Use the [documentation map](README.md), [spec-v6](../spec-v6.md), and registered amendments for current work. Original commands, paths, budgets and evidence below retain their historical scope.

# A路径起点基准

> 历史阶段记录：A 路径现已依 I5 合入 main；本文中的旧工作区路径、待实现状态和当时启动记录保留历史身份。当前入口与验收见 [主线整合报告](a-path-main-integration-report.md)。


2026-09-13。用户追加授权将当前基准提交并推送到origin/main，随后继续A路径。早期文档中的“不push”记录保留其历史身份，本次授权覆盖基准发布。

## 已验收基准

- 环境集成代码及文档基准：fdde4c0；来源及详细证据见environment-integration-report.md和environment-integration-sources.json。
- 前一阶段实际运行完整CPU回归1244项通过，独立C++状态导出夹具1项通过；本次基准发布没有重跑上述测试。
- 150卡牌版本、29个全卡遭遇入口及既有药水、关系、阶段、快照路由和战斗出口已纳入统一环境的限定工程范围。正式训练尚未准入。
- 主目录main的忽略后端仍为历史实验构建；已验收的新后端在sts2-integration。源代码提交不包含本地二进制，重新构建须按环境报告锁定依赖并应用基础补丁和敌人集成增量。

## 后续里程碑

1. A路径模型与动作契约：四层SAB、PMA、两阶段分布、唯一动作映射、历史重评估及数学和真实路由测试。
2. 正式采集与PPO工程：版本化数据准入和容量、不可变轨迹、联合PPO、活动环境恢复、CPU/CUDA预检。
3. 受限训练与评估：按已授权步数和四小时预算，报告所有初始化及适用范围内对照。
4. 最终交付：工程与训练报告、真实决策示例、验收后本地合入main；后续推送范围另据用户授权判断。

每个里程碑报告做了什么、解决了哪些问题、还有什么未完成。已经裁定的架构和预算继续执行；出现新的范围、证据或规格冲突且需要用户裁决时，列出具体问题并等待裁定。

## 明确未完成

sts2-integration中的sts/models/apath.py仅为未测试草稿，不进入本次基准提交。正式采集、PPO闭环、精确恢复、训练及最终主目录后端迁移均待完成。此基准不代表A路径验收通过。
