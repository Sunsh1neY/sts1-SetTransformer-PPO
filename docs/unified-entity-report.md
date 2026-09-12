# 统一实体架构交付与验证报告

日期：2026-09-12。结论：共享统一实体编码、模型、候选动作、资源采集入口及限定恢复契约已实现；不是新的正式PPO训练结果，也不是75类全卡机制完成。

## 当前实现

| 项目 | 交付状态 |
|---|---|
| 主模型 | `sts.models.entities.UnifiedEntityActorCritic`，unified-entity-set-v1 |
| 共享输入/动作接口 | `sts.env.entities`，unified-entity-interface-v2 |
| 模型配置 | 2层、64宽、4头、FF128、GELU、pre-LN双残差、最终LayerNorm、dropout0；120194参数 |
| 实体 | 每牌/敌人/药水/遗物一token，玩家及全局一token；全部共同参与每层自注意力 |
| 字段投影维度 | CARD122、ENEMY196、POTION21、RELIC10、PLAYER_GLOBAL198，分别投影到64 |
| 公开关系 | 卡牌→实际敌人的伤害预览与known，转为注意力关系bias及目标动作特征，不编码槽位列 |
| 动作 | 逐候选结合源、目标、全体上下文评分；普通出牌/药水/结束回合及SELECT_CARD；环境legal先于softmax |
| 动态输入 | 依据实际token/候选数构造；批内补齐至实际最大长度，独立实体、候选及legal mask |
| 新采集入口 | `sts.env.entitycollection.UnifiedEntityCollectionEnv`，替代主线中的旧64张包装 |
| 真实选择 | True Grit+暂停、单选、续跑；公开resolving卡保留，0/1候选自动处理 |
| 恢复 | `sts.train.entitycheckpoint`，无活动环境更新边界的FP32模型、单组Adam、Torch RNG；严格指纹检查 |

共享字段、实体类型、mask、目标引用和跨任务接入要求见[接口说明](unified-entity-interface.md)，架构选择及先登记后实现的配置见[架构契约](unified-entity-architecture.md)。新增敌人/药水机制仍由另一任务负责。

张量流程：实际实体先形成`[B,N,64]`；两层注意力的Q/K/V各为`[B,4,N,16]`。公开关系为`[B,N,N,2]`。候选引用gather对应实体，形成`[B,A,204]`，输出`[B,A]`动作分数及`[B]`价值。N和A均来自本批实际长度，模型参数不依赖固定牌数。

## 验证结果

- 最新全仓回归：**798 passed，29.01秒，0失败、0跳过**。规格、80/150版本台账、7个冻结文件hash及后端增量补丁检查通过。
- 实体测试覆盖：96张卡、五类实体共同注意力、动态padding、全实体置换、候选置换、真实手牌/敌人槽位重排、目标关系保留、合法性、未知/隐藏字段拒绝及所有类型投影的有限非零梯度。
- 配置测试实际运行3层/48宽/6头/FF96，确认模块可堆叠和配置。该配置只作接口测试，不是额外训练对照。
- True Grit+测试覆盖指定Sentinel耗尽与增能量、Corruption＋Feel No Pain触发、来源卡移区、0/1候选、过期/重复引用、选择点动作预算截断，暂停状态不漏resolving卡。
- 资源测试使用真实Sentry生成，把卡数量推至新466触发阈值以上；最终完整状态在480卡实体资源界内可编码。没有依靠截掉卡牌通过测试。
- 共享offer/来源药水测试验证CARD offer与POTION resolving生命周期、来源引用和候选mask。这是纯接口夹具，**不表示新药水机制已实现**。
- checkpoint测试验证恢复后的下一次采样、loss、全部权重和Adam状态逐值一致；旧模型格式、字段/内容/代码漂移、数值运行设置变化及半精度隐式转换均拒绝。

## 小规模采集与恢复诊断

最终可复现入口：

```powershell
Set-Location C:\Users\19091\Desktop\sts2-full-card
.\.venv\Scripts\python.exe scripts/diagnose-unified-entities.py --output runs/unified-entity-new-probe --steps 64
```

此命令拒绝已有输出目录，最多64条采集transition。小场景有一次合法准备动作，先进入真实选牌暂停点再采样；准备动作不当作PPO策略样本。

本轮最终报告：[report.json](../runs/unified-entity-u4-accepted-20260912/report.json)。

| 指标 | 最终实测 |
|---|---|
| 采集transition | 64，另外3次准备动作；实际67次env.step |
| 起始片段 | 5个，使用5张与96张受控卡组交替 |
| 真实选牌transition | 5 |
| 最大有效token | 103 |
| 动态批次 | `[64,103]` |
| 自然终止 | 0 |
| 截断 | 5：4次动作预算，1次诊断步数预算 |
| 更新验证 | 一次PPO更新后保存；下一次更新与恢复重放的结果逐值一致 |
| 用时 | 4.11秒，包含采集、编码、更新及保存/恢复；不是正式吞吐基准 |

5个截断片段不记作5次失败，不构造完整RTG或训练胜率。结果只证明工程闭环，不证明学习收益、泛化或Gate。开发期间因接口与恢复约束变化保留了数轮更早的短探针；最终交付以accepted目录为准，旧探针不能冒充当前版本恢复包。本次没有新的长时间正式PPO训练。

## 资源与恢复边界

统一模型第一版资源保护为最多512个总token、4096候选、B×heads×N²不超过8388608；不是固定padding，更不是后端无上限。当前80版本的主采集配置为最多96初始牌、480当前卡实体（含resolving）、466触发阈值、15生成余量及512真实决策。累计ID界为7776，低于int16范围。

采集边界绑定当前内容、运行契约、统一输入契约及实际后端二进制hash；新敌人、药水、卡牌或后端修改不能自动沿用旧证明。新生成/复制/回收/选择链仍需各自核验。

恢复首版限定本机已验证的CPU/FP32、相同软件与数值设置。保存模型、单参数组Adam与Torch RNG，不保存活动环境、队列、采集器游标或路由凭据。AMP/GradScaler、跨设备迁移和完整活动局PPO续跑未验收。需要重放选择时必须重新获取当前decision_id，不能重用旧凭据。

恢复前先检查工作树契约，再设置与报告一致的线程数：

```powershell
.\.venv\Scripts\python.exe scripts/check-ironclad-expansion.py
.\.venv\Scripts\python.exe -c "import torch; torch.set_num_threads(1); from sts.train.entitycheckpoint import load_entity_checkpoint; model,opt,meta=load_entity_checkpoint('runs/unified-entity-u4-accepted-20260912/update-1.pt'); print(meta['update_index'],meta['boundary'])"
```

检查点还校验interop线程数、默认dtype、确定性及TF32/cuDNN设置；当前报告记录interop=14。不同数值设置不能被当成精确恢复。仅在这个限定边界内，下一次更新已实际验证逐值一致；不能将其提升为任意机器或完整PPO采集中断恢复保证。

## 旧方案的替代与证据复用

| 旧内容 | 当前处理 | 证据边界 |
|---|---|---|
| 四组旧MLP/卡牌Set正式PPO | 冻结保留，不改名、不回填 | 只证明旧架构在旧环境的实验结果；新模型学习效果必须另行授权并重测 |
| 只有卡牌参与注意力、其他实体展平融合 | 被统一实体主模型替代 | 旧字段可见性与数值证据可复用；新编码/交互/置换需重测，已完成本轮工程测试 |
| 固定64张模型位置及固定输出头 | 动态token与候选评分替代；66整数协议仅保留为当前后端route | 旧环境合法mask可复用；新padding、引用与无目标处理已重测 |
| 旧64/50或比较64/57采集配置 | 保留历史配置；主线用统一实体资源入口 | 原有限内容生成证据经80版本复核后使用；后续内容变化仍必须重验 |
| 卡牌语义与已有机制测试 | 复用并新增resolving/True Grit+ | 当前准入80/150，不能宣称所有组合或75类全部通过 |
| 旧checkpoint及原型裸权重恢复 | 新格式直接拒绝 | 如需warm start须显式迁移；本轮仅验收新模型限定更新边界恢复 |
| GAE与PPO损失函数 | 复用已验证实现 | 新候选轨迹、截断最终状态与新模型更新已作小规模验证；完整训练采集器恢复仍待实现 |

## 交接文件与后续

- 敌人/药水任务优先读取[共享接口](unified-entity-interface.md)和`sts/models/unified-entity-contract.json`；输出真实公开字段、合法候选及来源引用。词表存在不代表机制准入，接口夹具不代表真实药水效果。
- 主入口为`UnifiedEntityActorCritic`、`encode_observation/collate`、`UnifiedEntityCollectionEnv`；旧`sts/models/ironclad.py`与旧采集包装仅保留历史回归，不作为扩展主架构。
- 全卡机制仍为80/150，剩余70版本；跨区选择、已知置顶记忆、更多生成/复制闭包和完整PPO活动环境恢复继续推进。长期训练没有本轮授权。

最终工件为[检查点](../runs/unified-entity-u4-accepted-20260912/update-1.pt)、[源码与后端快照](../runs/unified-entity-u4-accepted-20260912/source-and-backend.zip)及[快照清单](../runs/unified-entity-u4-accepted-20260912/source-and-backend-manifest.json)。快照保留源码原始字节，便于严格指纹恢复；不包含Python环境、正版JAR或被忽略的大语料，完整历史测试仍需要相应依赖与数据。

最终report.json SHA-256：`8dc97cfb21c7a64f6402443e2e680bfb871dedd8e078ad1cff55725e7e1adec3`。检查点SHA-256：`6da9d60448af23374147daab8076e31ab90f99e9f6c671bb344336cdbc332b86`。
