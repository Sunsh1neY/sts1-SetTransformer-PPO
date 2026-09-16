# 证据日志：相关项目调研（sts2-related-projects-survey 姊妹篇）

- 检索日期：2026-08-31（所有 URL 于当日核验，标注 ✅ 为实际抓取/读取过原文）
- 用途：支撑 `research/sts2-related-projects-survey.md` 的全部引用（本文档编号 [n] 不与 STORM 报告的 `sts2-a20-decision-model-sources.md` 互通）
- 可信度：高 = 官方/一手（论文原文、官方博客、GitHub 仓库原文）；中 = 权威媒体报道、社区高赞指南；低 = 论坛发言、二手转述

---

## 簇 C1：STS1/STS2 社区项目现状

- [1] ✅ zhiyue/sts2-rl-agent：STS2 RL 智能体，架构 = 纯 Python headless 战斗模拟器（对拍反编译 C# 源码验证）+ Gymnasium 环境 + MaskablePPO（SB3）+ C# 桥接 mod（Harmony hook + TCP JSON，仅用于真机验证）。项目规模：133 个源文件约 5 万行、408 个测试函数；内容覆盖 577 卡 / 260 状态 / 121 怪 / 290 遗物 / 63 药水 / 5 角色；吞吐 ~1,200 战斗/秒、~28,000 步/秒；观测 131 维、动作空间 61/100；训练后 PPO 在 Act 1 Ironclad 胜率 ~92%；52 stars / 25 forks / 628 commits — GitHub README — https://github.com/zhiyue/sts2-rl-agent — 2026-08 核验 — 高（一手）
- [2] ✅ 同项目 RESEARCH.md 技术笔记：① `sts2.dll` 无代码混淆，ILSpy 反编译得 ~3,300 个可读 C# 文件；GDRE Tools 提取 .pck 得 ~9,947 个资源文件；② 关键教训（引 decapitate-the-spire 作者）：直连游戏做 RL 训练不可行（受渲染帧率限制），必须用 headless 模拟器达到每秒数千局；③ STS1 先例项目表：decapitate-the-spire（Python）、conquer-the-spire（C++）、MiniStS（AAAI/AIIDE 2024）、Miles Oram C++ 重制；④ 动作空间超过 ~1,400 时可能有数值精度问题；推荐 Invalid Action Masking 论文（arXiv:2006.14171）；⑤ spire-codex 已提供结构化 JSON：576 卡 / 111 怪 / 87 遭遇 / 260 状态 / 289 遗物 / 5 角色 / 63 药水 / 66 事件（含费用、伤害、招式、升级增量等字段），可直接下载 — https://raw.githubusercontent.com/zhiyue/sts2-rl-agent/main/RESEARCH.md — 2026-08 核验 — 高（一手）
- [3] ✅ Torch1230/CombatSolver（战斗路线求解器）：C#/.NET 9/Godot mod，Beam Search 跨回合战斗求解器。原理 = 发牌稳定后在主线程捕获战斗根状态，后台对派生模拟分支做搜索（推进卡牌/牌堆/RNG/怪物 AI/药水/遗物/跨回合效果），预测与实机执行严格分离。预算预设：低 5s/60s 与 1,200/6,000 节点、中（默认）8s/120s 与 2,400/12,000 节点、高 12s/180s 与 5,000/25,000、极高 20s/300s 与 10,000/50,000；内存 6-16 GB；≥4 逻辑核默认 4 路并行。当前稳定版 0.22.1，适配 STS2 v0.111.0；模拟核心基于 hotwords123 的 Random Foreseer 重构（获授权）。求解目标优先级：生存 > 确认胜利 > 整场战损 > 药水消耗 > 主动卖血 > 敌方剩余状态 — GitHub README — https://github.com/Torch1230/CombatSolver — 2026-08 核验 — 高（一手）
- [4] CombatSolver 实测短板（上线三天社区反馈 + 作者自述，B 站视频 17.5 万播放）：BOSS 战长线组合误判（如黑拥流少算 30+ 血）、能力牌铺垫收益系统性低估（作者承认"奖励函数和权重没写好"）、储君印牌流搜索空间爆炸（"非常难计算的场景"）；覆盖 3035 项仍在滚动适配 — 什么值得买社区评测文章（综合 B 站评论区与 GitHub 文档）— https://post.m.smzdm.com/p/a3mdl86d/ — 2026-08 — 中
- [5] GitHub topic `slay-the-spire-2` 生态扫描：其余项目均为 LLM/规则型小型 harness（IanCoolidge0/vakuu 1 star 端到端 agentic harness、IT-BillDeng/agent-sts2-realgame 1 star LLM 评估 harness、Faultline6008/STS2-ai-agent 0 star 规则引擎+LLM 管线、ryanrinkel/BLANKthespire AI 生成卡牌 mod 等），无第二个 RL 训练项目 — https://github.com/topics/slay-the-spire-2?l=python — 2026-08 核验 — 中（一手页面，成熟度低）
- [6] CharTyr STS2 Agent 0.5.2（2026-04-10，3DM 页 6226 浏览/17998 安装计数）：游戏状态与操作暴露为本地 HTTP API + MCP 服务器包装 — 3DMGAME MOD 站 — https://mod.3dmgame.com/mod/252771 — 2026-08 核验 — 中（补充 STORM 报告 [B7] 的版本与日期信息）

## 簇 C2：AlphaStar / OpenAI Five 训练管线

- [7] ✅ DeepMind 官方博客：AlphaStar 用 ~97.1 万人类匿名 replay 做模仿学习，初始策略超过 84% 活跃玩家；league 含三类 agent（main agents / main exploiters / league exploiters）；Final 版以 camera interface + APM 限制在 Battle.net 匿名达到宗师（>99.8% 活跃玩家）— https://deepmind.google/blog/alphastar-grandmaster-level-in-starcraft-ii-using-multi-agent-reinforcement-learning — 2026-08 核验 — 高（一手）
- [8] ✅ SCC（ICML 2021，arXiv:2012.13169v3，转述 AlphaStar Nature 论文细节）：AlphaStar 基建 = 每种族 4 个、共 12 个训练 agent，每个 agent 16,000 并发对局采样，learner ~50,000 agent steps/秒，每 agent 约 200 游戏年训练量；league 通过 PFSP 选对手。SCC 自身为缩减复现：1,000 环境、~800 agent steps/秒、30 游戏年。**RL 总损失 = L_PPO + L_entropy + L_KL（KL 相对最终监督策略）**；z-statistic（人类 build order 统计量）作为稠密辅助奖励，独立 value 函数与优势估计，GAE 平衡偏差方差 — https://arxiv.org/html/2012.13169v3 — 2026-08 核验 — 高（一手论文）
- [9] ✅ 同论文 §6.1：**value network warm-up 技巧**——RL 初期 value 输出噪声大导致优势估计不稳，前 50 训练步冻结策略网络、只训 value 头；策略与价值共享 LSTM 前的骨干 — https://arxiv.org/html/2012.13169v3 — 2026-08 核验 — 高（一手论文）
- [10] ✅ The Gradient 技术解读（Yekun Chai）：监督学习三理由——①初始化权重；②保持接近人类行为的探索多样性；③微操防朴素探索（agent 动作概率偏离监督策略即受罚，即 human loss）。RL 阶段用 PBT 自动调超参（学习率、熵成本、LSTM unroll），种群按 episdic reward 排序、底部 20% 用顶部 20% 截断替换 — https://cyk1337.github.io/notes/2019/07/21/RL/DRL/Decipher-AlphaStar-on-StarCraft-II — 2026-08 核验 — 中（高质量技术解读）
- [11] ✅ OpenAI Five 官方博客：大规模 PPO，纯 self-play 从随机权重起步，不用人类数据、不用搜索；256 GPU + 128,000 CPU 核，每天 180 游戏年自对弈；**防策略塌缩：80% 对局打自己、20% 打历史版本**；长时程任务未依赖层级 RL 等新算法 — https://openai.com/index/openai-five — 2026-08 核验 — 高（一手）
- [12] NeurIPS 2023《A Robust and Opponent-Aware League Training Method for StarCraft II》：改进 AlphaStar league（goal-conditioned exploiters + 对手建模），资源少数量级达到超人水平——league 框架轻量化有先例 — https://neurips.cc/virtual/2023/poster/70220 — 2026-08 核验 — 中

## 簇 C3：长局稀疏终局奖励的信用分配

- [13] ✅ DouZero（ICML 2021，PMLR v139）：斗地主是 long horizon + sparse reward 任务（仅终局有非零奖励）；论证 **Monte-Carlo 估计的收敛不受 episode 长度影响**（直接逼近真实目标值），而 Q-learning 需等待后继状态值收敛，长局下极慢；折扣因子 γ=1，目标 = 实际回报 G_t，MSE 损失；MC 高方差由大规模并行 actor（百万级对局）抹平；4×15 卡牌矩阵动作编码可泛化到训练中罕见动作 — http://proceedings.mlr.press/v139/zha21a/zha21a.pdf — 2026-08 核验 — 高（一手论文）
- [14] alphaxiv 解读页（与 [13] 互证）：DMC 完全规避大动作空间下 Q-learning 的过估计偏差；并行化提供稳定梯度信号 — https://www.alphaxiv.org/abs/2106.06135 — 2026-08 核验 — 中
- [15] ✅ toypiper《Creating an AI for Slay the Spire》（STS1 model-free RL 失败复盘，负面教训）：Exordium 一幕作为环境时"episode 太长、奖励太稀疏"；无 replay 系统故拿不到专家数据（作者考虑过写录制 mod 请高手用，"那是另一个项目"）；三条教训：分里程碑、频繁给奖励、重设计动作空间 — https://www.toypiper.com/creating-an-ai-for-slay-the-spire — 2026-08 核验 — 中（一手博客）
- [16] CombatSolver 的奖励权重失效案例（同 [4]）：手写评估函数对能力牌/长线收益系统性低估，作者归因于"奖励函数和权重没写好"——人工设计战斗评估函数的高风险实证 — 中

## 簇 C4：回合制卡牌 RL 的可行规模与算力

- [17] Two-Step RL（arXiv:2311.17305）：多阶段策略卡牌游戏分两阶段训练（构建期/战斗期），RL agent 在 10,000 局随机对局中胜率 78.5%——"构建与战斗分阶段"设计有效性的直接数据点 — https://ar5iv.labs.arxiv.org/html/2311.17305 — 2026-08 核验 — 中（摘要级）
- [18] zhiyue/sts2-rl-agent 的规模数据（同 [1]）：单机 CPU 上 ~1,200 战斗/秒、28,000 步/秒已足够支撑 MaskablePPO 数百万 episode 训练（Act 1 达 92%）；尚未发布整局/高进阶结果 — 高（一手）

## 簇 C5：类肉鸽/长序列游戏 RL 先例

- [19] ✅ NetHack Learning Environment（NLE，NeurIPS 2020）：复杂度与仿真速度兼备的肉鸽 RL 环境，i7 2.9GHz 单核 ~14,400 步/秒；NetHack 单局 >10,000 步、观测空间数千实体、动作空间 >100 组合动作；**NetHack Challenge 中符号、深度 RL、混合方法全部未能通关** — Meta AI 博客 https://ai.meta.com/blog/nethack-learning-environment-to-advance-deep-reinforcement-learning + JOSS 论文 https://openresearchsoftware.metajnl.com/articles/10.5334/jors.444 + GitHub https://github.com/facebookresearch/nle — 2026-08 核验 — 高（一手）
- [20] ✅《Revisiting the NetHack Learning Environment》（ICLR 2026 博文）：复盘发现现有 NLE 实现存在缺陷——游戏大部分内容不可交互或难交互；修正观测空间、动作参数化与度量后，from-scratch RL 取得对基线的实质改进——**环境接口质量（观测/动作参数化）本身是决定学习成败的一级因素** — https://iclr-blogposts.github.io/2026/blog/2026/revisiting-the-nle — 2026-08 核验 — 中

## 簇 C6：LLM 智能体路线边界

- [21] AgenticSTS 细节（arXiv:2607.02255v1，2026-07-02，与 STORM 报告 [20-22] 同源互证）：五槽位"有界记忆契约"（协议/状态+合法动作/规则库/经验摘要/触发式技能库），提示长度恒定 ~5k token（对比历史堆叠法膨胀至 50 万+）。A0 五配置各 10 局：无记忆 3/10 → 加技能库 6/10（Fisher 精确检验 p≈0.37，作者自认样本不足）；爬塔模式：开经验层更新可爬到 A6-A8，冻结版止步 A2-A4；对比实测：STS2MCP 0/5、CharTyr 0/5（A0）；token 效率差 66-90 倍；开源 298 局轨迹 + 冻结库快照 + 统计脚本；跨引擎迁移不稳（Qwen 提升、DeepSeek 反降）— 网易/头条/正软三家中文详述互证 — https://www.163.com/dy/article/L1MCSIL805561FZF.html 等 — 2026-08 核验 — 中（对一手论文的忠实详述）
