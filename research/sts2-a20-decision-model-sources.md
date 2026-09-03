# 证据日志：《杀戮尖塔 2》A20 自动化决策模型技术方案研究

- 检索日期：2026-08-30（所有 URL 于当日核验，标注 ✅ 为本次实际抓取/读取过原文）
- 用途：支撑 `research/sts2-a20-decision-model.md` 的全部引用
- 可信度：高 = 官方/一手（论文原文、官方博客、GitHub 仓库原文）；中 = 权威媒体报道、社区高赞指南；低 = 论坛发言、二手转述

---

## 簇 A：STS2 游戏现状与难度体系

- [A1] ✅ STS2 于 2026-03-06 在 Steam 开启抢先体验，采用 Godot 引擎（Mega Crit 官方展示页）— Godot Engine Showcase "Slay the Spire 2" — https://godotengine.org/showcase/slay-the-spire-2/ — 2026-03 — 高 — "by Mega Crit | March 2026 (Early Access)…AN EVER-CHANGING SPIRE…A NEW AND RETURNING CAST OF CHARACTERS"
- [A2] ✅ STS2 只有序号 1–10 共 10 级进阶（初代为 20 级），部分初代难度（降最大 HP、不利事件、A17-19 强化敌招）被合并或移除 — Untapped.gg《Slay the Spire 2 Ascensions Guide》 — https://sts2.untapped.gg/en/guides/ascensions-list-best-strategies — 2026 — 高 — "There are 10 Ascension levels in Slay the Spire 2. The original game had 20."
- [A3] ✅ A10=双 Boss（Act 3 结尾打两个 Boss）；需先通关三幕解锁进阶 — Untapped.gg 同上 + TheGamer 解锁指南 — https://www.thegamer.com/slay-the-spire-2-ascensions-levels-modifiers-how-to-unlock-explained-guide — 2026 — 中 — "Ascension 10: Double Boss – Fight two bosses at the end of Act 3."
- [A4] ✅ 官方 Spire Stats：社区累计 2.4 亿局，60.5M 胜 / 179.5M 负；A0 平均胜率 16%（STS1 为 9%）；最高难度 A10 胜率约 17%（STS1 A20 仅 3%）— Mega Crit 官方 Neowsletter 2026-05-22 — https://www.megacrit.com/news/2026-5-22-neowsletter-issue-22 — 2026-05 — 高（一手）
- [A5] STS2 EA 内容：5 名可玩角色（铁甲战士、静默猎手、故障机器人 + 新角色亡灵缚者 Necrobinder、储君/摄政王 Regent），观者移除；附魔系统、交替关卡、四人合作 — 17173 综合报道（转述多家外媒） — http://news.17173.com/content/03022026/182528723.shtml — 2026-03 — 中
- [A6] STS2 发售日在线峰值超 57 万、好评率约 97%、销量约 300 万份 — TapTap 社区动态转述（k73 也载） — https://www.taptap.cn/app/638939/topic?page=4 — 2026-03 — 中（两处中文源互证，原始出处应为 SteamDB/官方）
- [A7] 高手基线：有视频作者声称 A10 Ironclad 胜率 85%（"95% is doable"）— YouTube "How I'm Winning 85% of My A10 Ironclad Runs" — https://www.youtube.com/watch?v=hyt7Dr5rn2Y — 2026-04 — 低~中（自述，未独立验证）
- [A8] STS1 完美打法胜率估计：Ironclad ≥75%、Silent ≥60%、Defect ≥65%、Watcher ≥96%；A20 心脏局全职业 >50% — ForgottenArbiter《Is Every Game of Slay the Spire Winnable?》 — https://forgottenarbiter.github.io/Is-Every-Seed-Winnable — 2020 — 中（领域专家推断，非实测）

## 簇 B：STS2 Mod/接入生态（RL 环境可行性）

- [B1] ✅ STS2MCP：mod 暴露游戏状态与动作，经 localhost REST API + 可选 MCP server；支持单人与合作、完整菜单/大厅控制、可选 seed 的角色选择、结束画面处理；实测版本 v0.103.2；473 stars/91 forks — GitHub Gennadiyev/STS2MCP README — https://github.com/Gennadiyev/STS2MCP — 2026（持续更新）— 高（一手）
- [B2] 社区 STS2 Early Access Mod Guide（doctornoodlearms）：mod 为 C# 静态类入口 + `[ModInitializer("ModLoaded")]` 特性加载；`--nomods` 启动参数存在 — Reddit r/slaythespire 与 r/SlayTheSpire2 两帖 — https://www.reddit.com/r/slaythespire/comments/1rm5gvg/sts2_early_access_mod_guide/ — 2026-03 — 中（一手教程，两帖互证）
- [B3] ✅ ModTemplate-StS2 wiki："Slay the Spire 2 is written in C# using the Godot game engine and is highly moddable" — GitHub Alchyr/ModTemplate-StS2 — https://github.com/Alchyr/ModTemplate-StS2/wiki — 2026 — 高（一手）
- [B4] 示例 mod 工程（Godot 4.5.1 .NET 构建，游戏 v0.99+）— GitHub jiegec/STS2FirstMod — https://github.com/jiegec/STS2FirstMod — 2026 — 高（一手）
- [B5] KitLib / STS2-DevMode：游戏内工具箱，含作弊、Harmony 分析/Hook、MCP bridge — GitHub WRXinYue/STS2-DevMode CHANGELOG — https://github.com/WRXinYue/STS2-DevMode/blob/main/CHANGELOG.md — 2026-08 — 高（一手）；Nexus 页 https://www.nexusmods.com/slaythespire2/mods/418
- [B6] spire-codex：反编译 STS2 以生成 API 的项目 — GitHub ptrlrd/spire-codex — https://github.com/ptrlrd/spire-codex — 2026 — 中（一手仓库，成熟度未知）
- [B7] AgenticSTS 论文列举的 STS2 接入生态：STS2MCP、HermesBridge、AI-Spire、CharTyr 等 — arXiv:2607.02255 HTML 全文 — https://arxiv.org/html/2607.02255v1 — 2026 — 高
- [B8] 动画/速度瓶颈与对策：游戏内置 Fast Mode（设置项）；Nexus 有 SpeedX（最高 20 倍速，"40 分钟对局近半时间在动画"）与 InstantMode（几乎瞬时）mod — Nexus SpeedX 页 https://www.nexusmods.com/slaythespire2/mods/91 ；InstantMode https://www.nexusmods.com/slaythespire2/mods/56 — 2026-03/07 — 中（一手 mod 页）
- [B9] 本地 LLM（RTX 4090 上的 27B 模型）经 STS2MCP REST API 自主游玩 STS2 — Reddit r/slaythespire — https://www.reddit.com/r/slaythespire/comments/1s3psrr/i_built_an_ai_agent_that_plays_sts2_autonomously/ — 2026-03 — 中

## 簇 C：对局数据来源（行为克隆素材）

- [C1] ✅ 官方运营数据：2.4 亿局聚合统计（见 A4）——说明游戏侧存在 run 统计通道 — Mega Crit Neowsletter — https://www.megacrit.com/news/2026-5-22-neowsletter-issue-22 — 高
- [C2] STS2Saves mod：导出单帧快照或整局归档到磁盘，恢复前自动建回滚副本 — Nexus https://www.nexusmods.com/slaythespire2/mods/459 — 2026-06 — 中
- [C3] AnalyticsTelemetry mod：只读 run/战斗分析，输出 append-only NDJSON 会话日志 + 游戏内 Analytics 面板 — Nexus https://www.nexusmods.com/slaythespire2/mods/479 — 2026-04 — 中
- [C4] spirescope：local-first 伴侣应用——卡牌/遗物查询、deck 分析、实时 run 跟踪、run 历史、社区 meta — GitHub thequantumfalcon/spirescope — https://github.com/thequantumfalcon/spirescope — 2026-03 — 中
- [C5] AgenticSTS 发布了 Silent A0 的可复现基准与对局轨迹数据集（HF Dataset；代码 Apache-2.0，mod AGPL-3.0，Python 3.12+/.NET 9）— GitHub AlayaLab/AgenticSTS — https://github.com/AlayaLab/AgenticSTS — 2026 — 高

## 簇 D：STS1 先例（历史参照）

- [D1] ✅ CommunicationMod（STS1）：外部进程经 stdin/stdout 控制游戏；状态稳定时发送 JSON 游戏状态；命令 `play/end/key/click/wait/state`；状态含 seed、draw_pile（可见构成）、enemy intent 等 — GitHub ForgottenArbiter/CommunicationMod — https://github.com/ForgottenArbiter/CommunicationMod — 2019–2023 — 高（一手）
- [D2] spirecomm：通过 CommunicationMod 接口化 STS 的 Python 包 + 简单 AI — GitHub ForgottenArbiter/spirecomm — https://github.com/ForgottenArbiter/spirecomm — 高（一手）
- [D3] 首个能在随机种子下通关 STS1 的 AI（启发式规则，非学习）：三职业均能赢；百余局胜率 Silent 5–6%、Ironclad 7–8%、Defect ~10%；作者强调"AI 不知道任何敌人/能力效果" — ForgottenArbiter YouTube "AI Defeats Slay the Spire"（2019-05-16）— https://www.youtube.com/watch?v=obtg0tredJg — 中（一手视频自述）；视频描述提及配合 SuperFastMode mod 加速
- [D4] bottled_ai：纯手写规则 bot，最好策略为 Watcher 52% 胜率（依赖 CommunicationMod，外部进程 10s 超时机制）— GitHub xaved88/bottled_ai — https://github.com/xaved88/bottled_ai — 中（一手 README）
- [D5] 同行评审的 LLM-plays-STS 论文："Large Language Models as Game-Playing Agents in Slay the Spire"（Bateni et al., 2024，FDG/ACM，被引 27），经 spirecomm+CommunicationMod 接入 — ACM DL — https://dl.acm.org/doi/fullHtml/10.1145/3649921.3650013 — 高
- [D6] STS2 上的 LLM 智能体现状（对照路线）：AgenticSTS（arXiv:2607.02255）——5 个前沿 LLM 配置在 A0 全部 0 胜（AGI-Eval 榜单），开发者口径人类 A0 胜率 16%；五层有界记忆（L5 技能库开启后 10 局 3 胜→6 胜）；累计式 prompt 的对手 96% 时间损失在模型延迟 — 见 E1；媒体报道 — the-decoder — https://the-decoder.com/ai-agents-win-at-slay-the-spire-2-after-researchers-replace-growing-chat-logs-with-structured-memory — 2026 — 高/中
- [D7] STS1 时代无训练式 RL bot 的公开成功案例：搜索 "Slay the Spire reinforcement learning" 未发现公开的训练 RL 项目达到高进阶（检索空白，负证据）— 本次检索 — 2026-08-30 — 低（检索局限性）

## 簇 E：方法论文献（架构 / 掩码 / BC→RL / 奖励）

- [E1] ✅ AgenticSTS: A Bounded-Memory Testbed for Long-Horizon LLM Agents（Cheng et al., 2026；EMNLP 2026 ARR 审稿中）— arXiv — https://arxiv.org/abs/2607.02255 — 高（一手）；正文指出 STS2 "runs require hundreds of tactical and strategic decisions" 且规则可完全文本化
- [E2] ✅ A Closer Look at Invalid Action Masking in Policy Gradient Algorithms（Huang & Ontañón）— arXiv:2006.14171，FLAIRS-35 2022 — https://arxiv.org/abs/2006.14171 — 高 — 结论：对 softmax 前掩码（masked policy gradient）是合法的策略梯度；naive 做法（掩码动作但用原始分布算梯度）有偏
- [E3] 动作掩码在大型商业游戏/调度中的广泛应用佐证（StarCraft II、DOTA 2、网络空间安全 RL 等）— arXiv:2409.10563 — https://arxiv.org/html/2409.10563v1 — 高（二手综述性引用）
- [E4] ✅ Set Transformer: A Framework for Attention-based Permutation-Invariant Neural Networks（Lee et al., ICML 2019）— arXiv:1810.00825 — https://arxiv.org/abs/1810.00825 — 高 — 置换不变集合编码；ISAB 降低集合自注意力复杂度
- [E5] Deep Sets（Zaheer et al., NeurIPS 2017）：置换不变函数的普适逼近基础；self-attention 本身（无位置编码时）即置换不变 — inference.vc 解读（Constable/Moreno） — https://www.inference.vc/deepsets-modeling-permutation-invariance — 中
- [E6] Deep Sets/Set Transformer 普适逼近的"正确条件"限定（sum-pooling 陷阱，Wagstaff et al. 2019）— PMC《Set Norm and Equivariant Skip Connections》 — https://pmc.ncbi.nlm.nih.gov/articles/PMC10465016 — 高
- [E7] ✅ PPO（Schulman et al., 2017）— arXiv:1707.06347 — https://arxiv.org/abs/1707.06347 — 高
- [E8] ✅ GAE（Schulman et al., ICLR 2016）— arXiv:1506.02438 — https://arxiv.org/abs/1506.02438 — 高
- [E9] ✅ Deep Q-learning from Demonstrations（Hester et al., AAAI 2018）：从演示数据启动 RL、混合经验回放 — arXiv:1704.03732 — https://arxiv.org/abs/1704.03732 — 高
- [E10] AlphaStar（Vinyals et al., Nature 2019）：监督学习（人类回放）初始化 + 多智能体联赛 RL 的旗舰先例 — Nature — https://www.nature.com/articles/s41586-019-1724-z — 高（注：URL 为经典权威链接，本次未逐字重抓）
- [E11] ✅ DouZero（Zha et al., ICML 2021）：斗地主 DMC（Deep Monte-Carlo）+ 动作编码 + 分布式 actor-learner，45 actors 于 4-GPU 服务器并行采样，"days of training" 达人类水平；动作空间可达每回合上万合法组合 — alphaXiv 解读 + towardsdatascience + GitHub kwai/DouZero — https://www.alphaxiv.org/abs/2106.06135 / https://github.com/kwai/DouZero / https://towardsdatascience.com/douzero-mastering-doudizhu-with-reinforcement-learning-864363549c6a — 高
- [E12] DouZero 后续：DQN/A3C 在斗地主表现差，DeltaDou（MCTS+RL）计算昂贵 — arXiv:2204.02558 — https://arxiv.org/html/2204.02558v1 — 高
- [E13] 奖励塑形经典理论：potential-based shaping 保证最优策略不变（Ng, Harada & Russell, ICML 1999）— 经典文献，本次未核验在线 URL（谨慎引用其结论而非链接）
- [E14] 自底向上技能演化 LLM 智能体在 STS1（A0）13 层、98.6% 执行率 — arXiv:2505.17673 — https://arxiv.org/html/2505.17673v1 — 高

## 簇 F：Godot 引擎工程（headless / IPC / 吞吐）

- [F1] ✅ Godot 官方文档（RenderingServer）：`--headless` 禁用全部渲染与窗口管理，RenderingServer 多数函数返回 dummy；`render_loop_enabled=false` 时"引擎逻辑仍在处理"（可 force_draw）— Godot Docs — https://docs.godotengine.org/en/stable/classes/class_renderingserver.html — 高（一手）
- [F2] Dedicated Server 导出模式（构建期剥离渲染/音频资源）与 `--headless`（运行期无显示）应并用；配合 ENetMultiplayerPeer 无需第三方网络库 — Gameye《Godot 4 Dedicated Server Hosting (2026 Guide)》 — https://gameye.com/blog/godot-dedicated-server-hosting — 2026 — 中
- [F3] headless 已知限制：仅禁渲染，节点/资源仍在内存（mesh 等照常加载）；部分功能依赖 viewport/音频需要 dummy driver — Godot Forum（Godot 4.6.2 语境） — https://forum.godotengine.org/t/headless-mode-vs-separate-server-and-client-scenes/138152 — 中
- [F4] `--audio-driver Dummy`、`--display-driver headless` 等命令行驱动选择（headless 即二者简写）— YouTube 教程转述 + Godot Docs — https://www.youtube.com/watch?v=Xtg3qkLe2YA — 低（视频转述，但与官方文档一致）
- [F5] STS2 本体窗口化运行 + STS2MCP 的现实：所有公开 STS2 智能体项目（STS2MCP、AgenticSTS 等）均为"带窗口实时游玩"，无一公开报告 headless/超速训练吞吐 —— 本方案需自行解决的关键空白 — 由 B1/B7/C5 综合推断 — 高（作为"证据空白"记录）

## 矛盾与存疑

1. **"A20" 命名冲突（最关键）**：spec 以 "A20" 为目标难度，但 STS2 最高进阶为 A10（A2/A3/A4 三源一致；官方 Neowsletter 亦以 A10 为最高）。"A20" 是 STS1 的概念。spec 若沿袭旧称，目标定义失效；若指"STS2 的最高难度"，应写作 A10。
2. **官方 mod 支持口径不一**：StratGG 指南（2026-03-29）称 "Mega Crit has expressed interest in mod support but has not committed to a timeline"；但同期社区已发布 mod 指南（B2）、7 月已有创意工坊 mod（TapTap 报道"猫鼠队"601 张卡面）与官方工坊生态。推断：EA 早期无正式 API 文档，社区逆向 + 官方默许并行，API 稳定性风险高（0.99→0.109 已破坏过兼容，jiegec 标注 "Ported to game v0.99+"）。
3. **A10 胜率 17% 的解读**：官方口径是"全体 A10 对局的胜率"，存在幸存者偏差（只有打得好的玩家才打 A10）；Reddit 帖（r/slaythespire 2026-06）明确指出 "stats say around 17% of A10 runs have been wins. That is very much not the same as saying the average player has a 17% win rate"。评估 A10 难度时需区分"全体局均值"与"达标玩家均值"。
4. **STS1 完美胜率估计（A8）与实际 AI 成绩（D3：5–10%）的巨大落差**：说明"游戏可赢"与"AI 能学到赢"之间隔着巨大的策略复杂度鸿沟——这是对本方案最重要的警示性参照。
5. **LLM 智能体基准的人机对比口径**：AgenticSTS 引用的"人类 A0 16%"为开发者口径（与官方 Neowsletter A0 16% 一致 ✅），但其"5 个前沿模型 0 胜"来自 AGI-Eval 第三方榜单，分母混合（论文原文承认 "mixed denominators"），不宜过度解读。
6. **吞吐数据缺失**：未找到任何"STS2/STS1 headless 局/秒"的公开实测数据（F5）；DouZero 的 45 actors/4 GPU 是相邻领域（斗地主，单局决策数远少于 STS）参照。本方案的吞吐估算只能外推，需实验测得。

## 检索局限声明

- 4 个后台深检索子代理因基础设施故障全部失败，本研究改由主会话三引擎（searxng/tavily/doubao）并行检索完成；doubao 中文结果多为游戏媒体二手内容，仅用于事实交叉印证，未作为关键主张的唯一来源。
- 未逐字核验的链接已在条目内标注（E10、E13）。
- 关键事实（A20→A10、官方胜率、STS2MCP 能力、Godot headless 能力）均有 ≥2 独立来源或一手来源支撑。
