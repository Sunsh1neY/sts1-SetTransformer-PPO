# 复杂战斗 Agent 与 STS 项目调研证据日志

检索日期：2026-09-13
检索方式：SearXNG、Tavily、Doubao 三路交叉搜索；关键论文、官方页面、GitHub 文件和本地项目报告再做正文读取。
用途：支撑 structured-battle-agent-solutions.md 与 sts-project-training-recommendation.md。

可信度分级：

- A：论文原文、官方论文页面、作者/组织官方仓库或当前项目的一手报告。
- B：项目作者 README、可复现代码和结果记录，但未经过同行评审或独立复现。
- C：二手解释、博客或搜索摘要，只用于发现线索，不作为关键结论的唯一依据。

## 一、复杂动作与训练算法

### S01 — AlphaStar Nature 论文

- 来源：[Grandmaster level in StarCraft II using multi-agent reinforcement learning](https://www.nature.com/articles/s41586-019-1724-z)
- 作者/机构：Vinyals et al., DeepMind
- 类型：Nature 2019，一手论文页面
- 可信度：A
- 三引擎命中：SearXNG、Tavily、Doubao
- 支持：AlphaStar 在完整 StarCraft II 上使用人类和 Agent 游戏、持续适应的策略群体；Nature 页面提供 replay、伪代码和架构补充材料入口。

### S02 — DeepMind AlphaStar 官方说明

- 来源：[AlphaStar: Mastering the real-time strategy game StarCraft II](https://deepmind.google/blog/alphastar-mastering-the-real-time-strategy-game-starcraft-ii/)
- 来源：[AlphaStar: Grandmaster level in StarCraft II using multi-agent reinforcement learning](https://deepmind.google/blog/alphastar-grandmaster-level-in-starcraft-ii-using-multi-agent-reinforcement-learning/)
- 类型：DeepMind 官方博客
- 可信度：A
- 三引擎命中：SearXNG、Tavily、Doubao
- 支持：复杂动作空间、Transformer 实体处理、LSTM、自动回归 policy head、pointer network、centralised value baseline、人类 replay 初始化和 league training。

### S03 — AlphaStar 公开论文 PDF

- 来源：[AlphaStar_unformatted.pdf](https://storage.googleapis.com/deepmind-media/research/alphastar/AlphaStar_unformatted.pdf)
- 类型：官方公开论文 PDF
- 可信度：A
- 三引擎命中：SearXNG、Tavily
- 支持：动作由带类型参数的函数组成；动作可选择动作类型、单位、目标和作用时间；动作参数按自回归方式采样；人类 replay 用于监督训练。

### S04 — StarCraft II Learning Environment

- 来源：[StarCraft II: A New Challenge for Reinforcement Learning](https://arxiv.org/abs/1708.04782)
- 类型：原始 SC2LE 论文
- 可信度：A
- 三引擎命中：SearXNG、Tavily
- 支持：SC2 的大状态空间、部分可观测性、结构化动作、延迟信用分配和人类 replay 数据集。

### S05 — PySC2 官方仓库

- 来源：[google-deepmind/pysc2](https://github.com/google-deepmind/pysc2)
- 类型：DeepMind 官方/作者仓库
- 可信度：A
- 三引擎命中：Tavily、SearXNG
- 支持：replay 可以回放观察和动作；replay 与游戏版本相关；API 和人类实际屏幕之间存在观测/坐标差异。

### S06 — AlphaStar Unplugged

- 来源：[AlphaStar Unplugged: Large-Scale Offline Reinforcement Learning](https://arxiv.org/abs/2308.03526)
- 来源：[OpenReview 页面](https://openreview.net/forum?id=Np8Pumfoty)
- 类型：DeepMind 大规模离线 RL 论文/benchmark
- 可信度：A
- 三引擎命中：SearXNG、Tavily、Doubao
- 支持：数百万场人类游戏 replay 派生的离线数据；state-action coverage 是核心挑战；完整离线 API、数据集和评估协议不可由简单 run 摘要替代。

### S07 — Invalid Action Masking

- 来源：[A Closer Look at Invalid Action Masking in Policy Gradient Algorithms](https://arxiv.org/abs/2006.14171)
- 类型：原始论文
- 可信度：A
- 三引擎命中：SearXNG、Tavily
- 支持：当前状态的 invalid action mask 对策略梯度有理论和实验依据；非法动作比例增大时，mask 相比惩罚非法动作更有效。

### S08 — Action Branching

- 来源：[Action Branching Architectures for Deep Reinforcement Learning](https://arxiv.org/abs/1711.08946)
- 来源：[AAAI PDF](https://cdn.aaai.org/ojs/11798/11798-13-15326-1-2-20201228.pdf)
- 类型：原始论文
- 可信度：A
- 三引擎命中：SearXNG、Tavily
- 支持：共享表示后为多个动作维度设置分支，减少高维离散化动作空间的组合输出；同时提示维度之间独立性假设的边界。

### S09 — PPO

- 来源：[Proximal Policy Optimization Algorithms](https://arxiv.org/abs/1707.06347)
- 类型：原始论文
- 可信度：A
- 三引擎命中：SearXNG、Tavily
- 支持：PPO 交替进行环境交互采样和 surrogate objective 优化；允许对采样数据做多个 epoch，但不等同于任意离线 replay。

### S10 — Growing Action Spaces

- 来源：[Growing Action Spaces](https://proceedings.mlr.press/v119/farquhar20a.html)
- 类型：ICML 2020 原始论文页面
- 可信度：A
- 三引擎命中：SearXNG、Tavily
- 支持：通过逐步扩大受限动作空间改善组合探索，并在 StarCraft micromanagement 上验证；使用的是 off-policy 价值方法。

### S11 — Prioritized Level Replay

- 来源：[Prioritized Level Replay](https://proceedings.mlr.press/v139/jiang21b.html)
- 来源：[ICML poster](https://icml.cc/virtual/2021/poster/9283)
- 类型：ICML 2021 原始论文页面
- 可信度：A
- 三引擎命中：SearXNG、Tavily、Doubao
- 支持：保存已有 level/初始配置，根据学习潜力选择重放；不是训练一个高层决策 Agent 来生成所有 level。

### S12 — Reverse Curriculum

- 来源：[Reverse Curriculum Generation for Reinforcement Learning](http://proceedings.mlr.press/v78/florensa17a/florensa17a.pdf)
- 类型：原始论文
- 可信度：A
- 三引擎命中：SearXNG、Tavily
- 支持：从可重置、接近目标的合法状态开始，逐步扩展初始状态分布；前提是环境能可靠恢复这些状态。

### S13 — Decision Transformer

- 来源：[Decision Transformer: Reinforcement Learning via Sequence Modeling](https://arxiv.org/abs/2106.01345)
- 来源：[Meta AI research page](https://ai.meta.com/research/publications/decision-transformer-reinforcement-learning-via-sequence-modeling/)
- 类型：NeurIPS/原始论文
- 可信度：A
- 三引擎命中：WebSearch、Tavily
- 支持：DT 使用 return、past states、past actions 的因果序列预测；要求训练数据具有完整、可对齐的轨迹。

### S14 — DQfD

- 来源：[Deep Q-learning from Demonstrations](https://arxiv.org/abs/1704.03732)
- 来源：[Google Research publication page](https://research.google/pubs/deep-q-learning-from-demonstrations/)
- 类型：AAAI/原始论文
- 可信度：A
- 三引擎命中：WebSearch、Tavily
- 支持：演示数据可以通过监督动作损失和 prioritized replay 帮助离线到在线过渡；它是 DQN 体系，不是把演示数据直接塞进 PPO。

## 二、STS 与游戏项目

### S15 — 公开 STS run 数据仓库 README

- 来源：[MaT1g3R/Slay-the-Spire-data README](https://github.com/MaT1g3R/Slay-the-Spire-data/blob/097aaf3564c2247835162d267cbc7c55d2c9039e/README.md)
- 类型：公开数据仓库作者 README
- 可信度：A
- 三引擎命中：本地 M2 证据 + GitHub 读取；网络搜索作为线索
- 支持：仓库包含多个 run history 数据集，并说明数据来自作者和获许可主播；提供解析和报告生成代码。

### S16 — 公开 .run 原始样本

- 来源：[1663717542.run](https://raw.githubusercontent.com/MaT1g3R/Slay-the-Spire-data/097aaf3564c2247835162d267cbc7c55d2c9039e/runs/panacea-ironclad-sample/1663717542.run)
- 类型：真实公开 run JSON
- 可信度：A
- 支持：可以直接观察 master_deck、card_choices、path_taken、damage_taken、current_hp_per_floor、potion_use_per_floor 等字段；没有逐步战斗 observation/action/reward 序列。

### S17 — RunHistoryPlus Neow/卡牌前缀字段

- 来源：[NeowBonusRunHistoryPatch.java](https://github.com/modargo/RunHistoryPlus/blob/99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b/src/main/java/runhistoryplus/patches/NeowBonusRunHistoryPatch.java)
- 类型：Mod 源码
- 可信度：A
- 支持：Neow、卡牌增删/变形/升级、遗物和 HP/gold 变更的记录方式；说明摘要字段与入口重建仍需时点核对。

### S18 — RunHistoryPlus 药水字段

- 来源：[PotionRunHistoryPatch.java](https://github.com/modargo/RunHistoryPlus/blob/99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b/src/main/java/runhistoryplus/patches/PotionRunHistoryPatch.java)
- 类型：Mod 源码
- 可信度：A
- 支持：药水获得、使用、丢弃按楼层和 ID 记录；不自动证明原始槽位、同层时序和所有隐藏状态。

### S19 — decapitate-the-spire

- 来源：[jahabrewer/decapitate-the-spire](https://github.com/jahabrewer/decapitate-the-spire)
- 来源：[README](https://raw.githubusercontent.com/jahabrewer/decapitate-the-spire/main/README.md)
- 类型：开源 headless STS1 项目
- 可信度：B
- 三引擎命中：SearXNG、Tavily
- 支持：作者曾尝试通过 CommunicationMod 连接真实游戏，发现人类速度不可用于高量训练，随后转向 headless clone；README 明确记录项目未完成和已有 bug。

### S20 — conquer-the-spire

- 来源：[utilForever/conquer-the-spire](https://github.com/utilForever/conquer-the-spire)
- 来源：[README](https://raw.githubusercontent.com/utilForever/conquer-the-spire/master/README.md)
- 类型：开源 C++ STS simulator
- 可信度：B
- 三引擎命中：SearXNG、Tavily
- 支持：C++17、Python/C++ API、卡牌/敌人/遗物/药水/事件以及 RL 项目入口；README 的文档状态为 TBA，不能把功能列表当作正式结果。

### S21 — MiniSTS

- 来源：[iambb5445/MiniSTS](https://github.com/iambb5445/MiniSTS)
- 来源：[README](https://raw.githubusercontent.com/iambb5445/MiniSTS/main/README.md)
- 类型：AIIDE/EXAG 相关简化 headless STS 战斗 testbed
- 可信度：B；论文信息同时见 [EXAG proceedings](https://ceur-ws.org/Vol-3926/)
- 三引擎命中：SearXNG、Tavily
- 支持：以 action、target、status effect 组合定义卡牌；重点是动态规则探索和战斗 testbed，不含完整地图/整局状态。

### S22 — Slay-I

- 来源：[alexdriedger/SlayTheSpireFightPredictor](https://github.com/alexdriedger/SlayTheSpireFightPredictor)
- 来源：[README](https://raw.githubusercontent.com/alexdriedger/SlayTheSpireFightPredictor/master/README.md)
- 类型：STS1 结果预测和卡牌评估项目
- 可信度：B
- 三引擎命中：SearXNG、Tavily
- 支持：作者 README 声称模型使用超过 325,000 场战斗，预测战斗受伤并评估加牌、删牌和升级；它是 value/评估方向，不是直接执行策略。

### S23 — Jialeiv/sts-rl-agent

- 来源：[GitHub repository](https://github.com/Jialeiv/sts-rl-agent)
- 来源：[README](https://raw.githubusercontent.com/Jialeiv/sts-rl-agent/main/README.md)
- 类型：作者开源的 STS1/ sts_lightspeed 混合 Agent
- 可信度：B
- 三引擎命中：SearXNG、Tavily
- 支持：约 100k 参数候选评分网络负责地图、选卡、商店、篝火和事件；战斗使用 MCTS；README 声称公开了六种战斗学习失败实验、50 seed 评估和无置信区间的限制。

### S24 — Jialeiv 项目过程记录

- 来源：[journey.md](https://raw.githubusercontent.com/Jialeiv/sts-rl-agent/main/docs/journey.md)
- 来源：[training-lessons.md](https://raw.githubusercontent.com/Jialeiv/sts-rl-agent/main/docs/training-lessons.md)
- 来源：[evaluation.md](https://raw.githubusercontent.com/Jialeiv/sts-rl-agent/main/docs/evaluation.md)
- 类型：项目作者实验记录
- 可信度：B
- 支持：作者将 reactive non-combat choices 和 multi-step combat planning 分离；小网络容量对照并非 scaling law；继续训练不等同于 held-out 改善；combat 的 MCTS、BC、DAgger、RL、attention 和 value lookahead 结果不能替代完整 AlphaZero 式循环。

### S25 — MiniRTS 两级策略先例

- 来源：[Hierarchical Decision Making by Generating and Following Natural Language Instructions](https://arxiv.org/abs/1906.00744)
- 来源：[Facebook Research minirts](https://github.com/facebookresearch/minirts)
- 来源：[NeurIPS PDF](https://proceedings.neurips.cc/paper/2019/file/7967cc8e3ab559e68cc944c44b1cf3e-Paper.pdf)
- 类型：原始论文和作者代码
- 可信度：A
- 三引擎命中：SearXNG、Tavily
- 支持：高层 instructor 生成高层指令，低层 executor 执行；使用约 76,000 条人类指令—执行对；这是明确的两级策略架构，但不是 Nature，也不是 STS。

## 三、本地 STS 项目一手证据

### P01 — 当前 spec 的动作版本

- 来源：[spec-v6.md](../spec-v6.md) §4.3.1，当前工作区第 247–274 行附近
- 类型：当前项目唯一执行规格
- 可信度：A
- 支持：minimal-v1 的 31 位接口、公用 public-battle-v1 的 66 位 action_schema=2、旧 checkpoint 不直接迁移、二次选择和容量边界必须独立处理。

### P02 — 当前 public battle 实现状态

- 来源：[docs/public-battle-implementation.md](../docs/public-battle-implementation.md) §当前可执行契约、§容量与终止、§仍未做
- 类型：当前项目工程验收报告
- 可信度：A
- 支持：99 个可执行公开派生场景、66 位动作、规则/随机集成和回归证据；public 观测到新 MLP/Set 的迁移与从头 PPO 短诊断仍未完成。

### P03 — 当前公开 corpus 审计

- 来源：[docs/m2-corpus-report.md](../docs/m2-corpus-report.md)
- 类型：当前项目 M2 报告
- 可信度：A
- 支持：203 个原始文件、157 个关联 run 组、1,282 场第一幕战斗审计、257 个规则可构造候选、研究划分 190/46/21、正式准入 0。

### P04 — 当前 M3 public 工程报告

- 来源：[docs/public-battle-implementation.md](../docs/public-battle-implementation.md)
- 类型：当前项目工程报告
- 可信度：A
- 支持：35 类 Ironclad、5 张辅助牌、8 个遗物、15 个直接药水、66 位 Agent、99 场规则/随机集成和 566 项回归。

### P05 — 当前 reward/run 边界

- 来源：[spec-v6.md](../spec-v6.md) §4.4、§7.3、§7.6
- 来源：[docs/reward-v6-report.md](../docs/reward-v6-report.md)
- 类型：当前项目 reward 契约
- 可信度：A
- 支持：battle_reward_v1 与 run_reward_v1 分开；战斗奖励不能改标为整局成功；PPO 的 terminated/truncated/reset 边界必须保留。

### P06 — 当前 RTX 3060 PPO 证据

- 来源：[docs/comparison-ppo-report.md](../docs/comparison-ppo-report.md)
- 来源：[docs/comparison-m3-training.md](../docs/comparison-m3-training.md)
- 类型：当前项目实际训练报告
- 可信度：A
- 支持：RTX 3060 Laptop GPU 上 MLP/Set 各两组、每组 70,656 transition、总训练评估 1,097.41 秒、模型参数量、633 CPU 回归和 15 CUDA 相关测试等。

### P07 — 当前统一实体 Set 配置

- 来源：[docs/unified-set-training.md](../docs/unified-set-training.md)
- 来源：[spec-v6.md](../spec-v6.md) 末尾统一实体架构纠偏条目
- 类型：当前项目预登记训练配置
- 可信度：A
- 支持：逐实体输入、64 维、4 头、4 层 SAB、PMA、动态候选评分；这是实验配置而不是普遍 scaling 结论。

### P08 — 当前 spec 对 AlphaStar/结构化动作的映射

- 来源：[spec-v6.md](../spec-v6.md) §7.4–§7.6
- 类型：当前项目模型契约
- 可信度：A
- 支持：每张手牌、每个目标的独立编码；候选评分；环境 mask；统一分布；PPO 旧 log-prob 和原 action mask 对齐。

### P09 — 当前规格的 offline/DT 边界

- 来源：[spec-v6.md](../spec-v6.md) §4.4.4、§7.3、§9
- 类型：当前项目排期和数据契约
- 可信度：A
- 支持：完整真终止轨迹先计算 RTG 再切窗；外部截断不能伪造成失败 0；离线数据默认来自规则 Agent + ε 噪声；battle 数据不能改标 run 成功。

### P10 — 当前学习路径

- 来源：[docs/learning-path-v2.md](../docs/learning-path-v2.md)
- 类型：当前项目学习目标文档
- 可信度：A
- 支持：动作 mask、实体 Set、DT、数据覆盖和可信实验必须分别理解；模型效果不自动证明理解或泛化。

### P11 — 当前 decisions 中的 Agent/runner 边界

- 来源：[docs/decisions.md](../docs/decisions.md) D23 及后续条目
- 类型：当前项目决策日志
- 可信度：A
- 支持：Agent 形成掩码后概率并选择动作；runner 不持有 RNG、不猜合法性；环境负责 reset/step；候选动作和选择阶段不能用自动选择掩盖。

### P12 — 当前 RNG/公开入口边界

- 来源：[docs/mechanics.md](../docs/mechanics.md) RNG
- 来源：[docs/reset-interface-audit.md](../docs/reset-interface-audit.md)
- 类型：当前项目机制与 reset 审计
- 可信度：A
- 支持：run seed、楼层、整局 RNG 继承和战斗内部状态不能仅由最终牌组或一条 run 摘要重建；source seed、environment seed 和模型输入必须分离。

## 四、研究限制与冲突记录

1. Nature 直接页面在一次 SearXNG 正文读取中触发安全策略阻断；关键内容由官方 Nature 搜索结果、Tavily 提取和 DeepMind 官方 PDF/博客交叉确认。
2. STS 社区项目的训练数字主要是作者自报结果；没有将其当作同行评审结论。
3. public corpus 的 257 个候选和 99 个可执行场景属于当前项目内部证据；“正式准入 0”与“工程场景可执行”是不同状态，不能合并。
4. 公开 .run 的字段能否覆盖某一具体扩展卡或遗物，必须按当前版本和字段时点逐候选审计；本报告没有把全库数量外推为完整机制覆盖。
5. AlphaStar 的算力、数据规模和联赛基础设施与单台 RTX 3060 不可直接比较；只迁移其接口思想，不迁移其性能预期。
