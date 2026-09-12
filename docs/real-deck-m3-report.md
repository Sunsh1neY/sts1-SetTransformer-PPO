# 真实卡组配置批次：M3入口与集成报告

日期：2026-09-12。准备工作已达到进入M3开发的条件；M3模型与训练迁移尚未完成。

## 范围与实际交付

直接复用旧清单中已经验收的中途完整卡组，99来源场景去除同run同卡组重复后得到92条、75run、27种不同卡组。未删除任何卡牌，未把中途卡组标为最终卡组。最终卡组库保持独立，不宣称其缺牌问题已经解决。

`scripts/prepare-real-deck-batch.py`生成`sts/env/real-deck-batch.json`，冻结来源、完整卡组、65run训练侧/10run开发侧、两套条件、五种遭遇及哈希。920个来源组合对应270个不同卡组内容组合；4种卡组内容跨训练/开发侧，未见卡组泛化不在本批证据范围。

`sts/env/real_deck.py`提供冻结批次加载、配置场景构建、来源校验及按run优先均匀采样。`PublicBattleEnv.reset`增加新来源策略的正式分支，不调用diagnostic模式；开发卡组不能作为train，当前没有正式保留评估集，evaluation用途明确拒绝。

新条件明确配置HP、遗物、药水、怪物与非火精英，不需要历史火精英或库存证明。卡牌、后端、奖励和66位动作保持现有已验证机制；本轮未重新编译或修改C++。

## 实际运行

命令：`python scripts/diagnose-real-deck-batch.py`。

覆盖全部27种卡组×2套条件×5遭遇；每个组合随机和规则使用相同环境seed，从940000开始。来源元数据只进info，不进入策略观测。

| 策略 | 局数 | 自然终止 | 异常 | 截断 | 胜局 | 平均回报 |
|---|---:|---:|---:|---:|---:|---:|
| 随机 | 270 | 270 | 0 | 0 | 43 | 0.1919012346 |
| 规则 | 270 | 270 | 0 | 0 | 224 | 1.0329629630 |

这是开发集成检查，没有正式CI，不作为Gate2或模型对照结论。代表性卡组按内容去重取一条来源用于穷举诊断；不是正式训练的run均匀采样分布。

逐场结果及脚本/批次哈希：`reference/real-deck-integration.json`。冻结批次payload SHA256：`22f66b7e319c8db3588b74cb862b5ace853b27d0b57b0fe00615a774a430ba78`。

## 验证与剩余工作

`python -m pytest -q tests/test_real_deck_batch.py tests/test_public_battle.py tests/test_public_runner.py tests/test_rule_agent.py tests/test_real_decks.py`：64 passed。

覆盖冻结批次重建一致性、修改卡组后即使重算候选哈希也拒绝、来源划分限制、独立seed可复现、元数据隔离、采样复现以及旧公开入口回归。`check-spec-v6.py`和`git diff --check`通过；未运行全仓套件，本轮相关检查及540局集成已完成。

用户已要求冻结MLP与Set对照环境，具体边界见`mlp-set-comparison-boundary.md`。后续只推进该范围内的MLP/Set共同数值编码、模型头、rollout与checkpoint迁移及短训。正式评估协议仍须在训练前冻结；后续扩展环境只推进Set，不扩大本轮MLP范围。

未启动PPO、未改eval_seeds.json、未commit/push。
