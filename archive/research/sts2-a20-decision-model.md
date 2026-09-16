# 《杀戮尖塔 2》A20 自动化决策模型技术方案：STORM 深度研究报告

> 研究对象：`spec.txt` 所述"两阶段 BC+RL、动态动作掩码、单步 Set-Transformer、多场景共享主干"的 STS2 自动化决策模型方案
> 研究方法：STORM 多视角研究（视角发现 → 多视角提问 → 联网取证 → 大纲 → 分节写作 → 评审修订）
> 证据日志：`research/sts2-a20-decision-model-sources.md`（本文引用 [n] 与其对应）
> 检索与核验日期：2026-08-30

---

## 60 秒摘要

方案整体**方向正确、文献根基扎实**：BC 预训练 + PPO/KL 微调、softmax 前动作掩码、实体集合编码、按场景分头，每一项都有权威文献或成熟工程先例支撑，且 STS2 的 Mod 生态（STS2MCP 等）已经证明了"外部程序完整打一局"的技术可行性。但研究发现了**一个必须先修正的目标定义错误和四个高风险盲区**：

1. **STS2 没有 A20**。续作进阶只有 10 级，最高难度是 A10（双 Boss）[2][3][4]。目标应改为"STS2 A10"。
2. **最大的学术风险不在战斗，而在非战斗决策的信用分配**：选牌/路线/商店不设局部奖励、纯靠下游 TD 反传的设计，要跨越一局数百个决策点的距离，梯度信号可能弱到不可用；相邻领域证据（DouZero 用整局结算的 Deep Monte-Carlo 绕开 bootstrap）提示了替代路径 [36]。
3. **最大的工程风险是吞吐**：现有全部 STS2 智能体项目都"带窗口实时游玩"，无人验证过 headless + 多开采样的吞吐 [9][21]；这是方案成立的先决条件，应最先做 1-2 天的 spike 验证。
4. **BC 数据来源被低估**："高水平玩家对局日志"没有现成公开数据集；可行来源是 mod 导出的 run 记录（STS2Saves / AnalyticsTelemetry / spirescope）加高手第一方数据，获取成本应显式列入计划 [17][18][19]。
5. **环境非平稳性**：EA 阶段平衡补丁频繁（v0.99→v0.109，7 月大补丁重做核心卡），策略会被持续"撤梯子"；必须锁定游戏版本训练、并接受定期重训的成本 [5][6]。

---

## 五个关键发现（按可靠性排序）

**发现 1【可靠性：高，官方一手数据】目标难度是 A10 而非 A20，且 A10 的基准胜率已知。**
Mega Crit 官方 Neowsletter 公布：STS2 社区累计 2.4 亿局，A0 平均胜率 16%，最高难度 A10 约 17%（对照 STS1：A0 为 9%、A20 仅 3%）[4]。Untapped.gg 与 TheGamer 的独立指南一致确认 STS2 进阶等级为 1–10，A10 效果是"Act 3 结尾双 Boss" [2][3]。**对 spec 的直接修正**：所有"A20"表述应替换为"A10"；同时"击败 A10"的隐含难度低于 STS1 A20（STS1 A20 全体局胜率约 3% vs STS2 A10 约 17%，且 STS2 的 A10 存在幸存者偏差——只有打得好的人才会去打 A10 [42]），方案里程碑应以 A10 双 Boss 击杀为最终验收。

**发现 2【可靠性：高，一手仓库 + 同行评审论文】"外部程序完整打一局 STS2"已被证明，但没人做到"高速"。**
Gennadiyev/STS2MCP（473 star）实现了 mod 侧暴露状态与动作（localhost REST API + 可选 MCP），支持单人/合作、菜单与大厅控制、带可选 seed 的角色选择，实测适配 v0.103.2 [9]；AlayaLab 的 AgenticSTS 论文（arXiv:2607.02255）复现并系统化地用它做了 LLM 智能体基准 [20][21]。但**所有公开项目都是带窗口、实时速度运行**——没有任何公开工作验证过 headless + 跳动画 + 多实例并行的采样吞吐（证据空白，详见证据日志簇 F5）。spec 第 7 节（headless + 解锁帧率 + 多进程采样）是方案成立与否的第一道闸门，而它是四个证据空白之首。

**发现 3【可靠性：高，同行评审文献】方法组件几乎都有直接文献支撑，其中动作掩码的做法有明确的对错之分。**
Huang & Ontañón 对策略梯度下的非法动作掩码做了系统分析：**在 softmax 之前对 logits 掩码**（masked policy gradient）是合法且更优的；掩码后仍用原始分布计算梯度（naive masking）则策略梯度有偏 [28]。这一做法在 StarCraft II、DOTA 2 等大型项目中广泛使用 [29]。Set Transformer / DeepSets 为"异构实体集合"编码提供了置换不变的普适逼近基础 [30][31]——但有一个 spec 未提及的理论细节：sum-pooling 型普适逼近存在已知反例条件（Wagstaff 2019），设计时不应对集合聚合的性质过度自信 [31]。

**发现 4【可靠性：中，社区一手自述 + 负证据】STS1 十年历史中，"训练式 RL"从未公开成功过，而"规则 AI"与"LLM 智能体"的天花板都有实测数据。**
STS1 首个随机种子通关的 AI 是纯启发式规则（2019），三职业胜率仅 5–10%，作者明确指出其"不知道任何敌人与能力效果" [25]；社区规则 bot bottled_ai 最好的策略（Watcher 专用）52% [26]。GPT-4 智能体（The Communicator，经 spirecomm/CommunicationMod 接入）成为 2024 年同行评审论文（Bateni et al., FDG，被引 27）[24][27]。STS2 上的 LLM 智能体基准显示：5 个前沿模型配置在 A0 全部 0 胜，而技能库（结构化策略知识）能把胜率从 3/10 提到 6/10 [21][22]。**这组数据对方案是双刃剑**：它说明该游戏的策略空间确实需要超越启发式的智能（支持做 RL 的动机），也说明"从零学会打"极其困难（BC 先验不是锦上添花，而是必需品）。

**发现 5【可靠性：中，工程文档 + 推断】环境工程的关键短板是"动画等待"与"多实例"而非"读状态"。**
Godot 官方文档确认 `--headless` 禁用全部渲染但引擎逻辑照常处理，`render_loop_enabled=false` 同样保留逻辑更新 [39]；dedicated-server 导出模式可在构建期剥离渲染/音频资源 [40]；已知限制是节点与资源仍在内存、依赖 viewport/音频的子系统需 dummy 驱动 [41]。STS2 侧，动画耗时已有社区答案：内置 Fast Mode 设置、SpeedX mod（最高 20 倍速，"40 分钟对局近半时间在动画"）、InstantMode（近乎瞬时）[14][15]。把这三件事拼起来（headless + 跳过动画 + N 实例），技术栈没有根本障碍，但**组合后的真实吞吐必须实测**——这是 spec 第 7 节从"设想"变成"方案"所缺的一步。

---

## 1. 研究视角与方法

本研究围绕方案八个组成部分，从六个 grounding 到真实来源的视角展开提问：

| 视角 | 代表来源 | 核心关切 |
|---|---|---|
| Mod/环境工程师 | STS2MCP 作者、KitLib 作者、社区 Mod 指南 [9][10][13] | 状态读取、动作注入、headless、加速、多开 |
| 游戏机制/数据研究者 | Mega Crit 官方统计、ForgottenArbiter [4][8] | 难度基线、完美打法上界、数据可得性 |
| 深度 RL 方法论学者 | Huang & Ontañón、Lee et al.、Schulman、Hester、Zha [28][30][32][34][36] | 掩码正确性、集合编码、BC→RL 稳定性、奖励设计 |
| LLM 智能体研究者 | AgenticSTS、Bateni et al. [21][22][27] | 无训练路线的对照与基准 |
| 社区怀疑者 | ForgottenArbiter 的 STS1 启发式 AI、Reddit 玩家 [25][42] | 策略复杂度、胜率统计口径 |
| 运营/生态观察者 | Mega Crit 补丁节奏、mod 政策 [5][6] | 环境非平稳性、合规 |

检索使用 searxng / tavily / doubao 三引擎并行，中文事实用 doubao、英文技术内容用 tavily/searxng；关键事实要求 ≥2 独立来源或一手来源；4 个后台深检索子代理因基础设施故障全部失败，改由主会话完成全部取证（详见证据日志的检索局限声明）。

---

## 2. 目标定义：先修一个"地基级"错误

### 2.1 STS2 的难度阶梯止于 A10

spec 全文以"A20"为目标。这是 STS1 的难度概念；STS2 重新设计了进阶系统：**共 10 级**，每级一个独立修饰符（精英更频繁、古神只回复 80%、金币 -25%、药水槽 -1……），全部叠加，A10 为"Act 3 结尾双 Boss" [2][3]。中文社区资料同样以"进阶 10/A10"为最高难度表述 [5]。

**修订建议**：
- 目标改写为"STS2 Ascension 10（任意角色，先 Ironclad）随机种子获胜"。
- 沿用 spec 的两阶段路线不变，但验收指标量化为：A10 胜率、A5 胜率（中间里程碑）、A0 胜率（回归基线）。
- 注意 STS2 有 5 名可玩角色（铁甲战士、静默猎手、故障机器人、亡灵缚者、储君）[5]，spec 的实体编码方案（卡牌/遗物/敌人 token 化）天然支持多角色，但 BC 数据与 RL 训练应先收敛到单角色，避免早期多任务干扰（见 §4.4）。

### 2.2 难度基线：A10 到底有多难

官方口径的 A10 胜率约 17%，但这是**全体 A10 对局**的均值，含幸存者偏差——只有玩家觉得自己够强才会开 A10 [4][42]。可用的参照系：
- A0 人类均值 16%（官方，与 AgenticSTS 论文引用的开发者口径一致 [21][22]）；
- A10 人类均值 ≈17%（官方，偏向上修正）[4]；
- 顶尖玩家自述 A10 Ironclad 可达 85% [7]；
- STS1 对照：完美打法 A20 心脏局估计 >50%（专家推断）[8]，而实际启发式 AI 只有 5–10% [25]。

**推论**：A10 是一个"人类认真玩就能显著超越 17%"的目标，RL + BC 方案超越全体均值并不夸张；真正的问题是学习效率（见 §5）。

---

## 3. 环境接入（spec §7 逐条核对）

### 3.1 状态读取与动作注入：已被证明

spec 要求"环境实时提取当前所有绝对合法的动作列表"。STS1 的 CommunicationMod 早已给出成熟范式：状态稳定时推送完整 JSON（含 seed、抽牌堆构成、敌人意图、`is_playable` 标记），命令集 `play/end/key/click/wait/state`，外部进程经 stdin/stdout 闭环 [23]。STS2 侧 STS2MCP 把同样的能力搬到了 REST API + MCP 上 [9]。**合法动作列表不需要模型猜测**——STS1 的 JSON 里每张手牌自带 `is_playable`/`has_target` 字段 [23]，STS2MCP 的状态接口同理（游戏 UI 本身就依赖这一信息）。spec 的"动态动作掩码"在环境侧是现成的。

### 3.2 Headless 与加速：组件齐备，组合未验证

- Godot 官方支持 `--headless`（禁渲染与窗口管理，引擎逻辑照跑）与 `render_loop_enabled=false` [39]；dedicated server 导出模式从构建期剥离渲染/音频 [40]；坑位已知：依赖 viewport/音频的节点需要 dummy 驱动，节点与资源仍驻内存 [41]。
- STS2 是 C#/.NET 的 Godot 4.5.x 工程，社区 mod 通过 `[ModInitializer]` 入口加载，编译工作流有公开模板 [10][11][12]。
- 动画瓶颈的社区解法已存在：Fast Mode（内置）、SpeedX（≤20 倍速）、InstantMode（近乎瞬时）[14][15]。RL 环境不应满足于 20 倍速——正确做法是在 mod 内拦截/短路动画协程与 `await` 延迟，让战斗逻辑同步结算，再配合 headless。

**待验证清单（建议最先做，1–2 天 spike）**：
1. STS2 当前版本在 `--headless` 下能否完成完整一局（特别验证：卡牌动画资源加载、UI 依赖节点、Steam SDK 初始化）；
2. mod 内短路动画/延时后，单实例每秒能跑多少决策点、多少局；
3. 多实例（8–64 进程）并行的吞吐扩展性与内存占用；
4. 版本锁定与存档隔离（每实例独立 profile，避免互踩）。

### 3.3 吞吐量级外推（供计划参考，非结论）

一局 STS 大约数百个决策点（AgenticSTS 称 STS2 一局需要"hundreds of tactical and strategic decisions" [21]）。相邻领域参照：DouZero 在 4-GPU 服务器上用 45 个并行 actor，训练数天达到人类水平 [36]。若 STS2 单实例（headless + 跳动画）做到 0.5–2 局/秒，则 32 实例 ≈ 16–64 局/秒 ≈ 每日 10⁶ 量级局——与 DouZero 的采样规模同量级或更大。**该数字完全建立在未验证的单实例吞吐假设上**，spike 结果出来前不应写入任何资源计划。

### 3.4 环境非平稳性：EA 的代价

STS2 处于活跃平衡期：0.99→0.109（2026-08）包含储君核心卡重做、全职业数值/稀有度调整 [5][6]。对 RL 环境这是根本性扰动：**任何模型在补丁后都可能"失明"**。缓解：锁定版本训练；每个版本重建评估基线；把"升版本重训"列为常设成本。此外官方 mod 支持仍处"社区逆向 + 官方默许"状态（早期无正式 API 文档，0.99+ 曾破坏 mod 兼容 [12]），接口需按可废弃抽象设计。

---

## 4. 模型架构（spec §3/§4/§5 逐条核对）

### 4.1 单步马尔可夫 + 完备显式编码：理论上站得住，有两个补充点

spec 假设"仅当前单步状态 + 全显式编码"足够。这个判断在 STS 类游戏里**基本成立**：游戏信息对玩家近乎全可见（牌堆构成、敌人意图、遗物计数），抽牌顺序随机且独立于策略——这属于"环境随机性"而非"部分可观测"，单帧状态（含各牌堆构成）在理论上足以定义最优策略。STS1 CommunicationMod 的 JSON 状态甚至直接暴露 seed [23]，环境侧无信息壁垒。

两个补充点：
1. **随机种子**：STS1 状态里有 seed [23]。若把 seed 也喂给模型，BC 阶段可能学到"预测随机数"的伪相关；建议状态编码时**剔除 seed 或用种子哈希位置无关化**，同时保留 seed 供环境复现。
2. **"本局历史"类状态**：如本回合已出牌数、本战斗累计效果——spec 已列（§3"完备特征输入"），方向正确；实现时需要一次"哪些效果依赖历史"的全量审计（STS1 的先例：延持、本回合力量等），STS2 新机制（亡灵缚者的墓地资源、储君的辉星/铸造值）也应纳入实体清单。

### 4.2 Set Transformer 实体编码：合适，注意两点

把 ~40–60 个异构实体 token（卡牌/敌人/玩家/遗物/地图节点）经类型化 MLP 投影 + 类型/位置嵌入后做 self-attention，与 Set Transformer 的设计动机精确吻合（置换不变、集合大小可变、ISAB 控制复杂度）[30]。文献提醒：
- self-attention 本身（无位置编码）即置换不变 [31]，spec"无 1D 位置编码"的选择正确；
- 但 sum/mean 池化聚合的普适性有已知反例条件 [31]——若在主干上做全局池化出 value head，优先用 attention pooling（PMA，Set Transformer 自带组件）而非裸求和；
- **地图是有序/结构化对象**，不是集合：路径选择依赖拓扑与序列。建议地图节点保留 spec 的 token 化，但额外注入"邻接结构"信息（如把当前可选的 2–3 条边上的节点 token 显式标注路径层号），或给地图头单独一个轻量序列编码。spec 的 Location_Embedding 能承载部分语义，但"哪条路径通向哪个 Boss"这类拓扑关系，纯集合注意力学起来会很贵。

### 4.3 多场景共享主干：合理，警惕负迁移

共享底层实体编码器 + 按场景路由专用决策头，与 AlphaStar 的"共享表征 + 结构化动作头"思路同源 [35]。文献与经验均支持"底层共享、顶层分头"；风险是多任务负迁移（战斗头主导梯度时，低频场景如商店/事件可能学不好）。缓解：按场景采样配比、per-head 的 BC 预训练损失权重、训练早期冻结主干只调头（详见 §6）。

### 4.4 动作结构建议补一条

spec 未写明动作头输出结构。STS 的动作是"选卡 + 选目标 + 选项"的复合动作，建议采用自回归动作头（先场景→再主动作→再目标，逐级条件采样并在每级做掩码），这是 StarCraft II/AlphaStar 与动作掩码文献共同指向的成熟做法 [28][35]；DouZero 的"动作编码"（把每个合法组合编成一个向量打分）是另一条被验证的路 [36]，STS 的复合动作空间用自回归掩码头更自然。

---

## 5. 奖励设计（spec §6）：方案的最大学术风险点

### 5.1 战斗内奖励：可行，但要校准两个量级

- "获胜奖励与战后剩余血量百分比挂钩"——与 STS 社区共识（血是跨局资源）一致，也与 ForgottenArbiter 对"最优打法以掉血衡量决策"的分析框架吻合 [8]。
- "-0.02/回合防拖延"——方向正确，但注意与血量奖励的**相对量级**：若拖延 1 回合的代价（0.02）小于拖延回合可能的掉血收益，智能体可能学会"多苟几回合攒格挡"；反之过大则可能促使无谓冒进。建议把回合惩罚建模为"对血量奖励的贴现替代"，用 potential-based shaping 的形式（以敌方总 HP 或回合数为势函数）保证不扭曲最优策略 [43]。
- **防死锁的兜底**：除了回合惩罚，环境层必须有硬超时（如单战斗 >N 回合判负），否则 10⁶ 量级采样中个别死锁轨迹会污染训练且烧算力。STS1 启发式 AI 曾反复出现"自杀式打牌"（如对尖刺怪放飞刀散弹）[25]——RL 早期策略同样会输出此类动作，掩码挡不住"合法但愚蠢"。

### 5.2 非战斗决策：纯 TD 反传是"理论上纯洁、实践上危险"的选择

spec 规定选牌/路线/商店"不设局部人工规则奖励，完全依赖下游战斗与通关结果的 TD-Error 反向传播"。问题在于**信用分配距离**：一张牌的好坏要等到之后 5–30 场战斗、数百个决策点后才在血量与胜负中显形。PPO + GAE 的优势估计随 λ、γ 衰减 [33]，非战斗决策的梯度信号会非常稀薄；STS1 启发式 AI 的失败模式恰好集中在"选牌/路线评估"上（评估型工具 Slay-I 的预测在长战斗中系统性失真 [25]），说明这些恰是**最需要学习信号**的决策。

文献给出的现实选项（按侵入性排序）：
1. **整局 Deep Monte-Carlo 回报**（DouZero 路线）：不做 bootstrap，用整局最终结果作回报，避免长链 bootstrap 偏差 [36]——可先与 TD 混合（战斗内 TD + 跨战斗 MC）；
2. **potential-based 中间塑形**：以"战斗前后的血量差"作为战斗级势函数（这不违反"不手工设计选牌规则"——它只测量结果，不规定选牌偏好）[43]；
3. **事后评估/离线校验**：每 N 次迭代用固定种子集做整局评估，把 A0/A5 胜率与分段血损作为监控指标（不进梯度，只进人肉决策）。

spec 完全可以保留"无人工选牌规则"的原则，但应**把上述 1、2 写进备选方案**，作为训练停滞时的解锁手段。

### 5.3 宏观里程碑奖励：小心奖励黑客

阶梯里程碑（精英/Act 1/2/3、阵亡扣分）是标准做法，但注意：里程碑奖励若与终局胜利奖励量级失衡，会出现"刷精英怪不推图"或"求快送死换重开"的局部最优。防拖延惩罚（§5.1）+ 阵亡大额负奖励的组合基本可控，仍需在训练监控中专门检查"主动送死率"。

---

## 6. BC→RL 过渡（spec §1/§8）：文献根基最扎实的部分

- **监督初始化 + RL** 是 AlphaStar 验证过的路线（人类回放监督学习 → 联赛训练）[35]；**从演示启动 RL、混合演示经验**有 DQfD 的系统研究 [34]。
- spec 的 "PPO + KL(πθ‖π_BC) 惩罚"（冻结的 BC 参照模型）与 RLHF 实践中的 KL 正则同构，是防策略崩塌的成熟手段；实现层面建议：β 从大到小退火、以"与 BC 策略的动作级 KL"为训练健康度监控指标、崩塌时回滚。
- **数据是真正的瓶颈**：spec 假设"高水平玩家对局日志"可得。现实：STS2 没有公开的"高手逐决策对局数据集"。可行拼图：
  - mod 侧导出：STS2Saves（整局归档导出）[17]、AnalyticsTelemetry（NDJSON 会话日志）[18]、spirescope（run 历史与分析）[19]；
  - 高手第一方数据：需要与少量 A10 玩家合作录制（社区已有 85% A10 胜率的公开玩家 [7]）；
  - AgenticSTS 开源了 STS2 对局轨迹数据集与基准 [20]，虽是 LLM 智能体轨迹（质量参差），可作为格式与管线参照。
  - **BC 的价值上限**：STS1 经验表明"模仿普通人"会得到普通胜率；BC 的作用是给 RL 一个"不犯低级错误"的先验，而非直接逼近高手。评估 BC 时应设"BC-only A0 胜率"这一独立指标。
- KL 约束之外，建议同时做 **DQfD 式演示回放池**（BC 数据进 RL 的经验池并设 margin 损失），这比纯 KL 更能防止早期 RL 把 BC 学到的战斗细节忘掉 [34]。

---

## 7. 争议与盲区（多视角交叉后仍无定论的问题）

1. **训练式 RL vs LLM 智能体路线之争**：AgenticSTS 证明"前沿 LLM + 结构化记忆"在 A0 能从 0 胜做到 6/10 [21][22]，且 96% 的时间损失在模型延迟而非控制层 [22]。对"想要一个能打的 STS2 AI"这个目标，两条路线都未到达 A10。训练式方案的优势是推理成本近零、可无限并行、可超越人类演示分布；LLM 路线的优势是零训练基础设施。spec 无需改道，但应在报告/论文语境中引用这条对照基线（前沿模型 A0 全 0 胜是极好的动机论据）。
2. **"单步马尔可夫"的边界**：本报告 §4.1 论证了其合理性，但有一类情况未被 spec 覆盖——**敌人 AI 的内部随机性**（STS 的敌人意图已可见，但意图的下一步选择有隐藏分布）。这不破坏马尔可夫性（属环境随机性），却影响 credit assignment 的方差；若训练中发现战斗决策方差过大，可考虑把"敌人意图序列的历史"作为辅助特征而非结构改动。
3. **多角色与版本演进的长尾成本**：5 角色 × 频繁平衡补丁，意味着"训一个模型"实际是"训 5 个、每个版本重训"。spec 未讨论维护策略；建议按"单角色单版本 → 自动化重训流水线"的顺序建设。
4. **合规与社区生态**：官方对 mod 的态度是"支持使用、禁止直接收费" [6]；研究用途无障碍，但若计划开源发布 bot，需注意 STS2MCP 等先例的许可证实践（AgenticSTS 代码 Apache-2.0、mod 部分 AGPL-3.0 [20]）。
5. **证据空白清单**（本研究无法回答、必须实验测定）：单实例 headless 吞吐；多实例扩展比；mod 在未来版本的存在性；BC 数据的具体获取成本；A10 双 Boss 对"最后一战"信用分配的特殊难度。

---

## 8. 修订后的技术路线建议

把 spec 的 8 节内容重排为一个风险递减的执行序列：

- **M0（1 周）环境 spike**：headless 全局验证 + 动画短路 + 单/多实例吞吐实测 + seed 可控重置。**这是 go/no-go 门**。
- **M1（2–3 周）BC 基线**：单角色（Ironclad）、单版本；数据 = 自录（与高手合作）+ mod 导出；指标 = BC-only A0 胜率与人类对照。
- **M2（4–8 周）RL 战斗内**：先只训战斗场景（其余场景用 BC 策略 + 手写规则兜底），softmax 前掩码、自回归动作头、回合惩罚 + 血量奖励、硬超时。指标 = 固定种子集 A0/A5 战斗血损下降曲线。
- **M3（8+ 周）全场景联训**：解锁选牌/路线/商店头，KL 约束 + 演示回放池；引入 DouZero 式整局 MC 回报作为对照消融 [36]。
- **M4：难度爬坡** A0 → A5 → A10，每档固定种子评估集 + 与官方统计口径对照 [4]。
- **贯穿**：版本锁定与重训流水线；训练健康度仪表盘（KL、熵、送死率、每场景动作分布漂移）。

---

## 9. 结论

方案的架构选型（实体集合编码、动作掩码、BC→RL+KL）全部踩在文献与工程先例的正确一侧，STS2 的 mod 生态让"环境"这最艰难的一步比一年前容易了一个量级。研究修正了一个目标定义错误（A20→A10），识别出两个必须前置的关键实验（headless 吞吐、BC 数据获取），并给最大风险点（非战斗决策的信用分配）准备了文献支持的备选机制（potential-based 塑形、整局 MC 回报）。若 M0 spike 通过，该方案在"达到并超越 A10 人类平均胜率"这个目标上的可行性是**有条件的肯定**。

---

## 参考文献

（[n] 与正文对应；✅ = 2026-08-30 抓取核验过原文；完整证据与可信度标注见 `research/sts2-a20-decision-model-sources.md`）

1. ✅ Godot Engine Showcase — Slay the Spire 2 — https://godotengine.org/showcase/slay-the-spire-2/
2. ✅ Untapped.gg — Slay the Spire 2 Ascensions Guide — https://sts2.untapped.gg/en/guides/ascensions-list-best-strategies
3. TheGamer — How To Unlock Every Ascension Level In Slay The Spire 2 — https://www.thegamer.com/slay-the-spire-2-ascensions-levels-modifiers-how-to-unlock-explained-guide
4. ✅ Mega Crit — The Neowsletter, May 2026（Spire Stats）— https://www.megacrit.com/news/2026-5-22-neowsletter-issue-22
5. 17173 — 《杀戮尖塔2》新机制、合作模式及职业详解 — http://news.17173.com/content/03022026/182528723.shtml
6. TapTap — STS2 官方论坛动态 / mod 收费政策报道 — https://www.taptap.cn/app/638939/topic?page=4 ; https://www.taptap.cn/moment/789214438661032826
7. YouTube — How I'm Winning 85% of My A10 Ironclad Runs — https://www.youtube.com/watch?v=hyt7Dr5rn2Y
8. ForgottenArbiter — Is Every Game of Slay the Spire Winnable? — https://forgottenarbiter.github.io/Is-Every-Seed-Winnable
9. ✅ GitHub — Gennadiyev/STS2MCP — https://github.com/Gennadiyev/STS2MCP
10. Reddit — STS2 Early Access Mod Guide — https://www.reddit.com/r/slaythespire/comments/1rm5gvg/sts2_early_access_mod_guide/
11. ✅ GitHub — Alchyr/ModTemplate-StS2 Wiki — https://github.com/Alchyr/ModTemplate-StS2/wiki
12. ✅ GitHub — jiegec/STS2FirstMod — https://github.com/jiegec/STS2FirstMod
13. ✅ GitHub — WRXinYue/STS2-DevMode（KitLib）CHANGELOG — https://github.com/WRXinYue/STS2-DevMode/blob/main/CHANGELOG.md （Nexus：https://www.nexusmods.com/slaythespire2/mods/418）
14. Nexus Mods — SpeedX（STS2，≤20x 速度）— https://www.nexusmods.com/slaythespire2/mods/91
15. Nexus Mods — InstantMode（STS2）— https://www.nexusmods.com/slaythespire2/mods/56
16. Reddit — I built an AI agent that plays STS2 autonomously（本地 LLM + STS2MCP）— https://www.reddit.com/r/slaythespire/comments/1s3psrr/i_built_an_ai_agent_that_plays_sts2_autonomously/
17. Nexus Mods — STS2Saves（存档/整局导出）— https://www.nexusmods.com/slaythespire2/mods/459
18. Nexus Mods — AnalyticsTelemetry（NDJSON 对局日志）— https://www.nexusmods.com/slaythespire2/mods/479
19. GitHub — thequantumfalcon/spirescope — https://github.com/thequantumfalcon/spirescope
20. ✅ GitHub — AlayaLab/AgenticSTS — https://github.com/AlayaLab/AgenticSTS
21. ✅ arXiv — AgenticSTS: A Bounded-Memory Testbed for Long-Horizon LLM Agents — https://arxiv.org/abs/2607.02255 （HTML：https://arxiv.org/html/2607.02255v1）
22. the-decoder — AI agents win at Slay the Spire 2…structured memory — https://the-decoder.com/ai-agents-win-at-slay-the-spire-2-after-researchers-replace-growing-chat-logs-with-structured-memory
23. ✅ GitHub — ForgottenArbiter/CommunicationMod — https://github.com/ForgottenArbiter/CommunicationMod
24. ✅ GitHub — ForgottenArbiter/spirecomm — https://github.com/ForgottenArbiter/spirecomm
25. YouTube — ForgottenArbiter, AI Defeats Slay the Spire（2019）— https://www.youtube.com/watch?v=obtg0tredJg
26. GitHub — xaved88/bottled_ai — https://github.com/xaved88/bottled_ai
27. ACM FDG — Bateni et al., Large Language Models as Game-Playing Agents in Slay the Spire（2024）— https://dl.acm.org/doi/fullHtml/10.1145/3649921.3650013
28. ✅ arXiv — Huang & Ontañón, A Closer Look at Invalid Action Masking in Policy Gradient Algorithms — https://arxiv.org/abs/2006.14171
29. arXiv — Applying Action Masking and Curriculum Learning…（应用综述性引用）— https://arxiv.org/html/2409.10563v1
30. ✅ arXiv — Lee et al., Set Transformer（ICML 2019）— https://arxiv.org/abs/1810.00825
31. PMC — Set Norm and Equivariant Skip Connections: Putting the Deep in Deep Sets（含 Wagstaff 2019 限定）— https://pmc.ncbi.nlm.nih.gov/articles/PMC10465016
32. ✅ arXiv — Schulman et al., Proximal Policy Optimization Algorithms — https://arxiv.org/abs/1707.06347
33. ✅ arXiv — Schulman et al., High-Dimensional Continuous Control Using Generalized Advantage Estimation — https://arxiv.org/abs/1506.02438
34. ✅ arXiv — Hester et al., Deep Q-learning from Demonstrations（AAAI 2018）— https://arxiv.org/abs/1704.03732
35. Vinyals et al., Grandmaster level in StarCraft II using multi-agent reinforcement learning, Nature（2019）— https://www.nature.com/articles/s41586-019-1724-z （经典权威链接，本次未重抓）
36. ✅ GitHub/alphaXiv — kwai/DouZero（ICML 2021）；解读 — https://github.com/kwai/DouZero ; https://www.alphaxiv.org/abs/2106.06135 ; https://towardsdatascience.com/douzero-mastering-doudizhu-with-reinforcement-learning-864363549c6a
37. arXiv — Improving DouDizhu AI by Opponent Modeling and Coach-Player… — https://arxiv.org/html/2204.02558v1
38. arXiv — Rethinking Agent Design: From Top-Down Workflows to Bottom-Up Skill Evolution（STS1 LLM 实验）— https://arxiv.org/html/2505.17673v1
39. ✅ Godot Docs — RenderingServer（Headless mode / render_loop_enabled）— https://docs.godotengine.org/en/stable/classes/class_renderingserver.html
40. Gameye — Godot 4 Dedicated Server Hosting (2026 Guide) — https://gameye.com/blog/godot-dedicated-server-hosting
41. Godot Forum — Headless mode vs separate server and client scenes — https://forum.godotengine.org/t/headless-mode-vs-separate-server-and-client-scenes/138152
42. Reddit — I must be fundamentally missing something with Ascension 10（A10 17% 口径讨论）— https://www.reddit.com/r/slaythespire/comments/1ttbuy7/i_must_be_fundamentally_missing_something_with/
43. Ng, Harada & Russell — Policy Invariance under Reward Transformations（ICML 1999）— 经典文献，本次未核验在线 URL
