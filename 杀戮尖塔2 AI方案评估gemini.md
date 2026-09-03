# **《杀戮尖塔 2》A20 自动化决策系统技术方案的多视角评估与第一性原理重构研究报告**

## **1\. 互补专业视角的选择及其系统性拆解**

在评估《杀戮尖塔 2》（Slay the Spire 2, STS2）高进阶（Ascension 20, A20）自动化决策模型的技术路线时，依赖单一的学术或工程范式极易陷入局部最优。为了构建兼具泛化能力与严密算杀能力的决策系统，本报告挑选了三种在理论基础、决策粒度与求解范式上完全互补的专业视角进行系统拆解。

### **1.1 三种互补视角的选择依据**

三种专业视角的设计遵循了控制论、博弈论与运筹学的互补原则：

> 1. **深度强化学习与连续价值表征视角（Deep RL & Credit Assignment Perspective）**：该视角将游戏视为高维状态空间下的马尔可夫决策过程，关注长时序环境下的隐性积累价值与端到端状态表征1。其存在必要性在于 STS2 的卡组构筑与路线选择具有极长的时间跨度（Macro Horizon），必须依赖价值函数进行跨回合的信用分配1。  
> 2. **博弈树搜索与符号规划视角（Game Tree Search & Symbolic Planning Perspective）**：该视角将单回合战斗视为局部规则透明的组合优化与期望博弈问题2。其存在必要性在于微观战斗的数值算杀对精度要求极高，传统神经网络的泛化误差可能导致关键回合计算失误，而树搜索能够提供 100% 确定性的最优算杀2。  
> 3. **复杂系统运筹与概率组合优化视角（Operations Research & Complex Systems Perspective）**：该视角将游戏全程重构为随机环境下的动态资源分配与协同度优化问题3。其存在必要性在于卡组构筑并非单纯的动作映射，而是对抗随机性（RNG）的风险投资组合管理，需要精细度量卡牌间的涌现协同效应与应对未来关卡的短板矩阵3。

### **1.2 视角一：深度强化学习与连续价值表征**

#### **问题重新定义**

深度强化学习视角将 STS2 A20 求解重构为一个非平稳概率分布下的超长时序隐马尔可夫决策过程1。核心矛盾在于如何在一个状态空间高度稀疏、随机采样方差极大的环境里，完成非战斗决策（选牌、购买、删牌、走位）对终局通关胜率的梯度归因1。

#### **推荐解决路径**

主张采用基于自监督实体表征（Entity Representation）的分层离线/在线混合强化学习1。微观层使用大容量 Transformer 编码全局状态1，宏观层利用对比学习（Contrastive Learning）构建卡组-环境匹配度高维隐空间7。通过在大规模人类专家日志上进行隐策略抽取，随后使用带有保守价值估计（CQL/IQL）的无模式 RL 进行微调，避免策略偏离1。

#### **其他视角易忽略的风险**

过度信任神经网络在微观计算上的逼近能力，忽略了“微观计算脆弱性”。在 A20 难度下，即使全局价值估计精准，一旦网络在特定回合将出牌顺序打错（如未先打出削弱牌即打出伤害牌），极易引发连锁崩溃，导致整个 Episode 失败3。

#### **改变判断的新证据**

若实验数据证明，基于自监督表征的 TD-Error 在无人工辅助奖励重塑（Reward Shaping）的条件下，反向传播超过 200 个决策步后梯度完全衰减或发散，无法使选牌策略收敛1。

### **1.3 视角二：博弈树搜索与符号规划**

#### **问题重新定义**

博弈树搜索视角将 STS2 的微观战斗定义为显式状态转移图上的期望极大化（Expectimax）博弈求解问题3。核心矛盾并非去“学习”某种模糊的战斗直觉，而是在分支因子极其庞大的组合动作空间中，如何利用剪枝技术在有限计算预算内搜索到全局最优出牌序列2。

#### **推荐解决路径**

主张剥离战斗内的神经网络控制权，建立极速 C++/Native 游戏逻辑仿真器3。战斗环节全面采用期望蒙特卡洛树搜索（Expectimax MCTS）或 Alpha-Beta 启发式剪枝搜索2。神经网络仅作为树节点展开时的先验概率估计器（Prior Evaluator）与状态价值截断函数，严格保证出牌的数值精准度3。

#### **其他视角易忽略的风险**

忽略了宏观状态空间的维度灾难与未知事件拓扑的深层不可预测性3。树搜索在微观单场战斗中表现完美，但在跨关卡的选牌与路线规划上，由于隐藏信息（抽牌堆未知洗牌顺序、未揭示地图节点事件）的存在，会导致搜索树深度被无限拉长，引发指数级计算爆炸2。

#### **改变判断的新证据**

若 STS2 原生引擎的状态拷贝（State Cloning）与回退（Rollback）性能存在物理瓶颈，导致模拟器单次状态转移耗时超过 ![][image1]，使得 MCTS 在实战限制内无法展开足够的搜索节点1。

### **1.4 视角三：复杂系统运筹与概率组合优化**

#### **问题重新定义**

运筹学视角将 STS2 定义为一个在极端不确定性约束下的动态资产组合（Portfolio）管理问题3。卡牌、遗物、药水与生命值均为具备不同波动率与收益率的资产3。问题的本质在于如何使当前资产组合的“功能完备度”动态匹配后续地图节点的“测试压力矩阵”3。

#### **推荐解决路径**

建立结构化的卡组协同与短板评估模型3。放弃端到端模型直接输出选牌动作的模式，改为构建卡组需求特征拓扑（如单体爆发、群体清理、启动速度、防守线、特定 Debuff 解答）3。选牌与商店决策转化为求解满足后续 BOSS 与精英怪压力测试约束下的边际效益最大化问题3。

#### **其他视角易忽略的风险**

忽略了复杂卡牌规则间非线性涌现效应（Emergent Synergies）的建模难度3。人为设定的指标矩阵难以完全涵盖罕见遗物与特殊卡牌产生的质变组合（如特定无限流构筑），导致策略陷入规则制定者的认知局限中3。

#### **改变判断的新证据**

若实证表明 STS2 频繁的版本迭代（如 Early Access 阶段的数值微调与新卡引入）导致静态拓扑矩阵的维护开销超越了重新训练一个端到端 RL 模型的成本7。

## **2\. 跨视角辩证质询与冲突根源剖析**

通过将三种视角置于同一辩论场域中进行交叉质询，可以精确定位技术路线中的共识区与本质分歧。

### **2.1 共同认可的事实**

各专业视角在以下底层事实与架构设计上达成高度一致：

> 1. **分层控制的必要性**：所有视角一致承认，STS2 的微观战斗（Micro-Combat Execution）与宏观决策（Macro-Strategy Deck Building）在时间尺度、决策频率及随机性结构上存在数量级差异，盲目使用统一架构进行端到端求解是不贴切的2。  
> 2. **原方案中无局部奖励宏观 TD 传导机制的失效**：三种视角均指出，原技术方案中“非战斗环节不设局部奖励，完全依赖下游战斗与通关结果通过 TD-Error 反向传播”的设想极易导致梯度消失或噪声淹没，无法有效指导 Act 1 阶段的选牌1。  
> 3. **微观战斗的局部可算性**：在特定回合手牌及敌人意图给定的前提下，单回合内的最优出牌顺序本质上是一个确定性或高概率的数学规划问题，无需引入过多的离散探索噪声2。

### **2.2 真正的分歧**

三种视角的本质冲突体现在对控制权分配与隐空间表达力的信任度上：

* **分歧一：微观战斗执行的控制权分配** 深度强化学习视角主张由神经网络直接输出离散动作，通过动态动作掩码（Action Masking）保证合法性1；而树搜索视角坚持必须由搜索算法（Expectimax MCTS）掌控出牌序列的终极决策权，网络仅作为搜索的辅助评估器3。  
* **分歧二：非战斗决策价值的表征形态** 强化学习视角主张使用隐空间神经网络向量自发学习卡组价值1；运筹学视角主张将卡组能力显式解耦为结构化的维度矩阵（如输出、防守、启动、续航）进行线性或非线性运筹匹配3。

### **2.3 分歧背后的底层假设对比**

为了清晰呈现各视角背后的思维模式差异，下表汇总了三者的底层假设、求解工具与局限性：

| 评估维度 | 深度强化学习视角 | 博弈树搜索视角 | 复杂系统运筹视角 |
| :---- | :---- | :---- | :---- |
| **底层假设** | 高维连续隐空间能够自适应吸收所有隐性卡牌协同与复杂时序依赖1。 | 游戏微观规则可无开销拷贝，有限深度的树前瞻优于归纳偏置3。 | 专家经验可被结构化为完备的维度需求矩阵，且评估函数具备可加性3。 |
| **求解工具** | Transformer, PPO/SAC, 离线 RL (CQL), 动态掩码1。 | Expectimax MCTS, C++ 极速模拟器, 启发式剪枝2。 | 动态规划, 风险方差控制, 凸优化与评估矩阵3。 |
| **计算瓶颈** | 采样效率极低，超长时序信用分配困难1。 | 树展开的分支爆炸，依赖极高性能的状态深拷贝2。 | 难以应对未知的涌现协同与规则质变3。 |
| **容错机制** | 依赖软策略分布（Soft Policy）维持探索。 | 依赖搜索树深度消除近视缺陷（Short-sightedness）3。 | 依赖安全边际（Safety Margin）与硬性约束。 |

## **3\. 视角综合与全局推荐方案**

在充分吸收三维视角的质询结论后，系统抛弃了原方案中“单模型共享 Backbone \+ 全局端到端 RL”的盲目架构1，重构为分层解耦的“策略引导 Expectimax 搜索 \+ 隐式协同匹配评估”综合技术方案。

### **3.1 综合推荐方案架构**

该方案在物理与逻辑上划分为两个高度独立但数据互通的模块：

> 1. **微观战斗引擎：策略网络引导的 Expectimax MCTS（Policy-Guided Expectimax MCTS）**  
   * **架构设计**：微观战斗决策放弃完全依赖端到端网络推理1。战斗中，由一个轻量级 Set-Transformer 策略网络输出候选动作的 Prior 概率分布，随后交由原生编译的 C\# / Native 极速模拟器进行深度为 3\~5 步的 Expectimax 蒙特卡洛树搜索2。  
   * **作用机制**：期望节点（Chance Nodes）负责处理抽牌堆未知的概率分布，决策节点（Decision Nodes）选择累积期望收益最高的出牌序列2。搜索过程由策略网络引导剪枝，确保在 ![][image2] 内完成极高精度的死局搜杀与伤害化计算3。  
> 2. **宏观评估引擎：对比拓扑卡组匹配网络（Deck-Environment Contrastive Matcher）**  
   * **架构设计**：非战斗环节（选牌、地图路线、商店购买、营火）彻底剥离战斗内 TD-Error 反向传播1。构建独立的双塔评估网络：卡组拓扑塔（Encoder 提取当前卡组与遗物特征）与路线图谱塔（Encoder 提取后续地图节点与 BOSS 风险特征）1。  
   * **作用机制**：评估网络基于大规模 self-play 对局日志，通过对比学习预训练，直接输出当前卡组在当前地图拓扑下的生存概率期望 ![][image3]3。选牌时，算法遍历所有候选卡牌，选择能使组合生存期望 ![][image4] 增量最大化的卡牌。

### **3.2 方案实施的四维控制指标**

#### **适用条件**

* STS2 无头（Headless）运行 Mod 能够提供原生的内存级状态深拷贝（State Deep Copy）接口，且单步骤状态恢复耗时控制在 ![][image5] 以内1。  
* 具备分布式采样能力，能够生成不少于 100 万局完整 A20 进阶对局的日志数据1。

#### **最大风险**

* **状态拷贝耗时过大导致的搜索瘫痪**：若 STS2 的底层对象依赖关系过于复杂，导致 C\# 模拟器在执行 Expectimax 树展开时频繁触发垃圾回收（GC）或内存拷贝延迟，微观搜索引擎将无法在实时预算内完成计算，迫使系统退化为纯神经网络推理1。

#### **退出条件**

* 在完成第一阶段验证时，若策略引导的 Expectimax MCTS 在单步决策上的平均延迟超过 ![][image6]，且微观战斗的平均失血量未能显著低于人类专家 Baseline；  
* 或者宏观卡组匹配网络对 Act 通关结果的 ROC-AUC 预测准确率低于 0.65，则立即终止该架构并重新评估。

#### **第一步行动**

* **开发并 Benchmarking 原生 C\# 状态深拷贝模拟器**：在不依赖 Python 端交互的前提下，直接在 STS2 Mod 框架内实现纯 C\# 内存状态回退机制，实测单回合 Expectimax 搜索 1,000 个节点所需的时间开销1。

## **4\. 第一性原理的底层解耦与基元分析**

为确保技术方案从物理本质出发而非沿袭经验惯性，本章节抛弃所有现成的 RL 或 AI 范式，将 STS2 系统解耦为最底层的物理事实与数学约束。

### **4.1 确认无法绕开的基本事实**

> 1. **微观战斗规则的可计算性**：在特定回合内，玩家手牌、能量、 Buff 状态以及敌人的已知意图均处于确定性的离散逻辑中3。状态转移方程 ![][image7] 的微观部分是 100% 可知的3。  
> 2. **系统熵增与死亡不可逆性**：游戏为单次生命周期模式（Permadeath），生命值（HP）在非营火节点极难恢复，任何微观决策的严重失误都会造成不可逆的累积伤害3。  
> 3. **信息不透明性的递进结构**：抽牌堆序列存在局部伪随机性，地图未揭示节点与后续奖励池存在全局随机性2。  
> 4. **动作空间的非连续性与条件依赖**：动作空间并非固定维度的连续向量，其合法性依赖于绝对规则（如能量是否足够、目标是否存活），且动作的先后顺序会导致非交换性结果（![][image8]）1。

### **4.2 习惯性接受但未经验证的假设**

> 1. **“端到端强化学习是解决复杂棋牌决策的最佳范式”**：  
   * *反思*：这一假设源自 AlphaZero 在围棋上的成功，但围棋是完全信息且无随机性的平稳博弈，而 STS2 包含极强的非平稳卡组构筑与随机采样2。将选牌与出牌强行纳入一个端到端网络极度低效1。  
> 2. **“可以通过行为克隆（BC）获得高质量的先验策略”**：  
   * *反思*：人类高水平玩家的日志充满了直觉决策与特定偏好噪声，且 A20 进阶下的容错空间极狭窄，简单克隆人类动作可能导致模型继承人类的系统性认知偏见1。  
> 3. **“不设中间奖励的 TD-Error 反向传播能够自发收敛出构筑策略”**：  
   * *反思*：选牌决策与其最终检验节点（BOSS 战）隔着数百个时序步，无指导的信用分配在数学上收敛极慢1。

### **4.3 真正想实现的目标**

在 STS2 A20 进阶难度（及随机种子未知）的条件下，构建一个能够自我演化的自动化 Agent，实现**全职业整体通关胜率（Win Rate）的极大化**1，而非追求单回合伤害输出最高或局域得分最高2。

### **4.4 现实中的资源与约束**

* **算力与推理时间约束**：实时对局要求 Agent 单次出牌决策时间不超过 ![][image6]13。  
* **通信与仿真吞吐约束**：通过 IPC/共享内存实现 Python 与 Godot/C\# 游戏进程通信时，进程间序列化（Serialization）开销可能成为吞吐量瓶颈1。  
* **游戏引擎黑盒约束**：STS2 源码逻辑中大量复杂的 Buff 回调机制极难用纯 Python 重写，必须依赖原生 C\# 运行环境进行状态推演1。

## **5\. 路径重构与表面修补诊断**

基于第一性原理推导，对原始技术方案进行深度诊断，彻底剔除其中的修补性逻辑，并推导出底层重构路径。

### **5.1 原技术方案表面修补部分诊断**

原始方案在面对复杂决策瓶颈时，采用了多项仅能治标而无法治本的修补手段：

> 1. **动态动作掩码（Dynamic Action Masking）的局限**  
   * *原设计*：将非法动作 Logits 强行置为 ![][image9]1。  
   * *底层诊断*：这仅解决了“动作合法性”的硬约束1，完全没有解决“动作组合爆炸”的问题。在手牌较多且能量充足的回合，合规动作排列组合数量仍呈阶乘级增长，网络在无引导状态下依然在盲目探索。  
> 2. **纯马尔可夫单步 Set-Transformer 的信息割裂**  
   * *原设计*：抛弃时序因果掩码，试图靠“显式编码出牌数、遗物计数器”来满足马尔可夫性1。  
   * *底层诊断*：人为抽取的特征无法完全覆盖动态系统中的隐性时序状态（如抽牌堆洗牌循环分布、过去数回合的伤害积压）。这种强行截断时间维度的做法破坏了状态空间的完整性。  
> 3. **BC-to-RL 中 KL 散度的“锚定陷阱”**  
   * *原设计*：通过 $\\mathcal{L} \= \\mathcal{L}*{PPO} \- \\beta \\cdot D*{KL}(\\pi\_\\theta |

| \\pi\_{BC})$ 限制策略偏离1。 \* *底层诊断*：这是为了防止强化学习微调初期策略崩塌的修补手段1。但在 A20 难度下，最优策略常常是反直觉的极值决策，KL 散度惩罚会像“缰绳”一样将模型锁定在亚优（Suboptimal）的人类策略范畴内，阻碍超人类策略的涌现。

### **5.2 从基本事实重新推导出的新路径**

剔除上述表面修补逻辑后，从基本事实推导出的新路径完全立足于“状态确定性分割”与“评价矩阵自监督学习”。

#### **1\. 微观层面：图搜索与神经网络先验融合（Search-Prior Fusion）**

放弃试图训练一个“会算杀的神经网络”的设想1。战斗中直接将当前局势转化为状态拓扑图，由 C\# 原生 Expectimax 引擎执行死节点剪枝与爆牌/伤害推演3。神经网络退化为极小型的“ Prior-Net ”，仅在搜索树节点展开时提供Top-K概率动作建议，从根本上解决算杀失误问题3。

#### **2\. 宏观层面：卡组-图谱特征对齐与概率预测（Deck-Map Contrastive Matching）**

选牌、营火与商店决策不再作为 RL 的动作输出1。系统将选牌重构为“求解增量价值函数”：  
![][image10]  
价值网络 ![][image4] 不通过在线 RL 学习，而是通过对数百万局 Self-Play 模拟数据的终局通关结果进行自监督对比学习训练7。这种方法避开了时序信用分配的难题1，使得选牌决策在数学上等价于寻找收益最大化的组合解7。

### **5.3 新路径成立的前提与验证步骤**

为确保新路径的工程落地性，需要逐级验证其物理前提：

#### **路径成立的前提条件**

> 1. **C\# 模拟器原生的内存回溯机制**：STS2 引擎能够实现极速的状态 Deep-Clone，且不产生严重的内存泄露与 GC 停顿1。  
> 2. **宏观特征表示的解耦完备性**：卡组拓扑网络与地图风险拓扑网络能够在隐空间中精确表征“卡牌协同”与“敌人机制对抗”7。

#### **验证新路径的第一步**

新路径验证路线：  
\[第一步：模拟器性能与搜杀精准度验证\] ──\> \[第二步：宏观评估网络自监督训练\] ──\> \[第三步：双层解耦 Agent 实战部署\]

* **第一步的具体实施内容**： 编写一个纯粹的 C\# Mod 评测模块，在没有 Python RL 进程介入的无头模式下，针对 Ironclad（战士）职业的基础牌组，运行纯 Expectimax 搜杀算法3。  
* **第一步的具体验证标准**：  
  在预设的 50 个 Act 1 常规战斗残局中：  
  1. 单回合搜杀平均耗时小于 ![][image11]；  
  2. 搜杀策略的平均战后剩余血量较纯随机动作或简单启发式规则提升 40% 以上；  
  3. 内存消耗维持在常数级别，无不断上升的 GC 停顿。

该步骤成功后，方可启动宏观双塔评估网络的构建与数据集采集7，确保整体工程演进建立在坚实的物理事实与可验证的基础之上。

#### **Works cited**

> 1. spec.txt  
> 2. Creating an AI for Slay the Spire \- Kai Brewer-Krebs, [https://www.toypiper.com/creating-an-ai-for-slay-the-spire/](https://www.toypiper.com/creating-an-ai-for-slay-the-spire/)  
> 3. How possible is a slay the spire AI (full on reinforcement learning), [https://www.reddit.com/r/slaythespire/comments/1nlr2dl/how\_possible\_is\_a\_slay\_the\_spire\_ai\_full\_on/](https://www.reddit.com/r/slaythespire/comments/1nlr2dl/how_possible_is_a_slay_the_spire_ai_full_on/)  
> 4. Week 3 : The Card Game \- AI Playtesting, [https://aiplaytesting.github.io/blogs/week3/](https://aiplaytesting.github.io/blogs/week3/)  
> 5. From Top-Down Workflows to Bottom-Up Skill Evolution \- arXiv, [https://arxiv.org/html/2505.17673v1](https://arxiv.org/html/2505.17673v1)  
> 6. Progress on slay the spire machine learning project : r/slaythespire, [https://www.reddit.com/r/slaythespire/comments/1uttqbf/progress\_on\_slay\_the\_spire\_machine\_learning/](https://www.reddit.com/r/slaythespire/comments/1uttqbf/progress_on_slay_the_spire_machine_learning/)  
> 7. Slay the Spire on the Hub: a six-dataset bundle for deckbuilding AI/ML, [https://huggingface.co/blog/t22000t/slay-the-spire-ai-collection](https://huggingface.co/blog/t22000t/slay-the-spire-ai-collection)  
> 8. Rethinking Agent Design: From Top-Down Workflows to Bottom-Up, [https://www.alphaxiv.org/abs/2505.17673v1](https://www.alphaxiv.org/abs/2505.17673v1)  
> 9. GitHub \- ifree/MCPTheSpire: A Slay the Spire mod that enables AI, [https://github.com/ifree/MCPTheSpire](https://github.com/ifree/MCPTheSpire)  
> 10. Large Language Models and Games: A Survey and Roadmap \- arXiv, [https://arxiv.org/html/2402.18659v2](https://arxiv.org/html/2402.18659v2)  
> 11. arXiv:2504.15313v1 \[cs.AI\] 20 Apr 2025, [https://arxiv.org/pdf/2504.15313](https://arxiv.org/pdf/2504.15313)  
> 12. LLM Game Rule Understanding Through Out-of-Distribution Fine, [https://ojs.aaai.org/index.php/AIIDE/article/download/36804/38942/40881](https://ojs.aaai.org/index.php/AIIDE/article/download/36804/38942/40881)  
> 13. How LLMs are Shaping the Future of Virtual Reality \- arXiv, [https://arxiv.org/html/2508.00737v2](https://arxiv.org/html/2508.00737v2)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADQAAAAZCAYAAAB+Sg0DAAAB/klEQVR4Xu2WzytFQRTHj1ASkQULP8pGFmxY2ym2yhZlpcjOSlkoio0QomRBUkqIFXo2ivwoC5QoC2Vh6Q/gfJsZ78x5915Pej317qe+efM9M3PP8WbOfUQxMTExucQI64N1zCpVsTDaWL2sPDvG32FWw/eMLHHP6refkRQKa0mGQ+lgfSotejOyQBeZRCTdrHflBYGCxlnTrEFWvh/ODjdWkiYyRVYqX4OCoH8FEj9XXpX1f0pWFlQsA5ZO1izrlLVH5jhPsa5Yk3YOPBzTFzL3WFNE5l4jH1yNJVaJN0MRVdCQ8jUoJsGaY9WyHljLIl7G6iGT7C3rUMRwpNcDvAUxBsjDNR2AojJaEB7gaCWzrlB4ePi29RuFf2K9euGdsS7FuJxS7/c8ZbCgILBuX4xlQRJ46KbaexJjrMW6Tfs5LaIKwjvmt2CdTD6qIJl8mDdGyT2hXT+cyjOlFoQXIxaj24VRQGaOPCIgrCCdaLqeo5q1SmbvPhXzmGG9Kq+dzEJ5GWvIdBwHuhrmbAkP6CL/UhBOyooYA+SrPQ8kiSQqhHfAWhNjlzw0IPxr8huAawroeI6oI4fTIdlRnjv68hkbZH4MRNJMZiHeGWivQef0iDVB/ub4BvEfvWM9ktmjTsSx3xuZb+zCxl2SP3m4BvDR1RLWg0YpJiYmJif5AhHXlOcMwnszAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAZCAYAAABOxhwiAAAB5klEQVR4Xu2WwStEURTGj1AWUhR2zMbCTlKsrYQFxdLCTpEVWVmiKLJhYSFlocRKVpaERKGIKNlY2Ch/AOfr3jPv3Dt3zIiZ2dxffc2c79x357w357z3iCKRSKRQbLGqVdzB2lCxUMc6ZX2wxrxcSfjy9Moqc1YQtbPelD/OukvSpQEFLLIWWA1eDgyyPll9no+T7Pa8onLmGx5XZIpMef4D68TziooUXu64CdJCjZ6P4+CDEdY665zMvGCvNTInPW3XwNtmPbJGradpIZPDnnusGzedyQvrntXKWiK3l0E+hWNwZ2x8SMlwYx94ywFvysagmXWp4kpK9s4KFtTa77Jpf5LOq3CAPOIjVr3yb62PkxPQZvsqHmLtqhg8e3FOdsgt6LeFtykPYB0K9T09Wz1kjp2k7C2bk1Uym6Rs/B+F+zeAkIf5kN+CQnOQ5oLMogrlSeFSAP6yUOFoAX0lpXB/XajIkCfgmSEXRbecA34Y92g9jNIqcjIrNu5KrzDguDkV/6XwCcrc/yngpRlmDahYhhMPJKGKtck6UB4GDeuQE35qFfyzGsTaQ+H+k/idVeN5DvNk3j+kbWbddJpj1jUlrdSkcrgj4FUBfYpPufL4hCf9G/JwLArvJXMrhgd1UiQSiRScbyGRlQtHVA8oAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIQAAAAaCAYAAAB2KPSUAAAE80lEQVR4Xu2aS4sdVRCAS6IYTNQY0aCgXhGCuhAfiA+QzEJIQAO6iJssIm40DzQLUcSNKKKIIBIQEaL4CAyKCpIEDYGJC0lk1IWiIRBxEMGFGyE/QM+X6qKrK6f79u2Ze+cm6Q+K6T7V9/R5VNWpc3pEenpasirJf0keiYqe84/LkpxKclGSA0meqKp7zjceD/e7w31PT09PN8g9PoqFGe4sxLjOXfd0Z2uSB2LhqLwvmkB6ebDyhOYUXk9uESHnOBkLAy8l+TPJLUluSnI8yfYkv7tnppFvpdr/dVX1Gfwt1ecvrKrHyqxUna0zNLxpQheSrIyFjt+SXBULHS+LDmzknyTvxcIp5JIk30jeYTzPJ/lM9Lnlgne/HgtHxaw5x5ZC6phJMhcLHXgIdV8ZFaKDd28snEI2JNkk2o9ngs5YneQpUSOfD7pJ8qxoO5sceCg/Sd4gLpDmyAG/iA5YHeioe01UiBrEJENqVz4UnXD6QZu5jhwRnQSe2VVVTRTa8EmSV6JiFCzMxY5+Ls1LgXl/kzUSAXiG/OHqoDtbIC8AHAcZlKrTED2uldL4r6mqJw7t+CsWjgLWREcGruzGJG+5+xy3Sz6yRGJiyv2w5GxawNhxGDDH2ViqT0fRd4trIkmb8Rg3LM+LagcdpAKfMLWxMNbMYUuKsVPONIyzYbnA24gA8IJou3043ueuyR+OuvvlhHbmlulWmKfb2ke2fF+proWBORYLW7BH9H13REXiC1Fdl3pvFV2azKOXAssfwBzH6ieK2jhNQ/7goS2dozCWRAXW+bmqupa3pX7iqOfNWFhg78MQcxB16uodBnUupUFY/gAD0XafKO4PlaqpyR+MRRkEmFf+KHrQ1Aa8gSQrB2G2zlsGou9j/c0xLQbh8wewnQbC2Yofp2nJH4wlMQiEvKAthFDWzRwMJJEmt7P4TnRZMhhY6sHLiDpce4OgHib6NSnbd4Xo8sDRN/XdVpR7g/hXtE/binvPjNQbpIFRPxTKbJxinbR5PpTZ8vd0kk9F6yLiPCk6drTbzmFo/0HRSfxZyiN9dnn0EyeZFT2iti/SdZjhcqDWGV64EAuHwGTXeQWN3i+qv6cooxMcWftEDBakusPxEYKDFr/bsfdRvyVNDPCq4toM4nrRRDYHyTP1MIE3BB3cL/p+nuE9GKnBxPtE+g0pn2XieNZ7Js/6wzfuOb4HjMKMl389oB8wkKpDUJ+/f1T0dLiO9VI/L635QHQvPSq8OK6bK6S6Y8Grvxc9piYMR6jDn4F4g+AvSehmJ+YBOTCIP0Qnri4xxjDxVCKI30KOA/oSDcTuSarNIABj+iHJDmk2CMvB6mA3lPvmNBH2Jnk1Fo4InfNbJG8QRAefnFqojEZkYBAMLM/xTFNoJV8a99F5k0H45W1Oyk8EZgB3iTpbNAgiAAafg+hD9Lg7KiYFHt9krW14OMk7xTVbOepj4NaKrvN48qWF/sviL1HncHHNb24WnXw8nmh3eZLnRAcnl8dgTBjysDxiMbD+c57DF0iuaYfdX5zksSRfi/bzK9FcA4iItJt+bBA1CMbElkXGJrdlBwxrIRZOGtZqnyR2gWXGPIeBi5PIBDNwHiaT33SZ1F+l2+/GCX20TwV+abUI4ccoB46BQXRZ+pecj6X/Z5dxEZeMHERHcqeecxyiBjsZ5MWg6+np6ZkA/wNYhRtAdvAU8wAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAZCAYAAADXPsWXAAAAzUlEQVR4XmNgoAOYBcSy6IKkgJNAPAWInwOxGpocUeASA6pGkIG6SPxBDuYB8X807IKiAsJHlt+KKo0AIMk76IJIwBKIJ6ALogOYLbjAO3QBbOAcA25DmoDYGF0QG1jNADGEB02cD4j3oInhBM0MEEMU0MTPAjErmhhOkMMAMcQASQykGZT4iAYWDBBDQqB8UQaIN0DeIRqIM0AMmQjlg6IbFKAkAS4GiCHrgDgeiANQpYkHIEMeMJAYDugAluBICgd0cJqBjHAYBYMVAAAmTys7o3iDCQAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADQAAAAZCAYAAAB+Sg0DAAABuUlEQVR4Xu2WwStFURDGx0JJRBYUNjayoPAfKMVW2QllZWFrpewoK0koJQuyUaJYITaKSNlYURbKwtIfwHzNOb258+65bkrv1ju/+nr3fHPPuTPvnTP3EUUikUg1Mc/6Yl2wGk0sD0OsXmtWimfWjLuuISlssBQOMsG6Z3079SfDlWGMJBnNOOvTeFm0UYEKenTSYOsgwVbjhyhUQUjk1ng+wRHjhwgVNMpaY12zTki28wrrgbXs7oG3yXojOceWOpJzjfVxNLZYDYk7DFkFzRk/RKigJtYkSbJPrDMVw5beS/E21BhgXRTtQVEVKwjg4Yck8R7lXzqvS3k3JE3G00xyj2adClSQBh66qfVe1BhzMe/AXeciq6Ap44f4a0E6+ZC3SDLX6zgZLueVygvqJpmc90WZpyCbaF7P08HaIXnOtIklWGW9G2+YZKI+jJ0kHSeN/yoI626rMUC+1kuAJJFMi/JOWbtqXE+ln3xW+Z52ktiADVD2lsPu0BwZz39RtcrbJ/kzkEkfyUS8M9Be0/bpOWuJkoujaWDenZJfB+Dzg6Rz+ZhP8jcPxwA+utqV86AFikQikarkB/kbi5SCljXnAAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADgAAAAZCAYAAABkdu2NAAACGElEQVR4Xu1WwSvEQRR+cnEgUSiFdXGicHKWUE7K2cFJkZuDK7m4yEXJwU1KSXKgHBwIKSUhxUXKwUX5A3jfzrzd9xszu5tl12G++tqZ730zv32/eTO/IYqIiIiI+F1UMTddUaGeecZ8Z046MQE8s8wP5hGzJhkuPWqZe2T+0CdzOxnOoJf5yqyw/SnmXTachngmbB9ezAv9XyCU4CiZPzri6PD3q77PM8Z8c7SyIZTgFZlYytEfmKe2nSK/p9PqjY5eFoQShA42Ofq51QGsnM+DPvQhMiW7ROalrDErmavMC+YxZffrIPOWeUjmXHCxTGZOOQswd0EoJsFp23Y9kiDiSLCFTMniAFpXvhnr22LWOZqgjXnJbFcaXlhJElywbdejExTIuAaldVhtX2lS3rKy2M/oV2ccRD1UogTnbNv1hBJ8VH1AfEjK1WTOYTIH2T0lV7FgFJNgvhIdV1quBPV4n9ZlNeEzZT9deRFK8Im+Pwi4IXOSAigVn0dKT68MEgQ1fMn4NAHKVKoG+7kghBKUU6vP0VEui7aNt+jzDFhdv+WfJogqecmG0+j2aEFgsh1XJHNUb1DyAMCVDH59jIsHMQH60DVylWiz0tDWmmwDfTPCRQM3sSCw1BiE7w6+RyCuW9BcnDCvmStk4q3JcBrwIAYPvLsqJs+S58jqoGqwl6DhF32fhgRxPZy3Y8EDioiIiIj4A3wBNgOyQYecRRYAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIoAAAAaCAYAAABo4cQnAAAER0lEQVR4Xu2a3atNQRTAl1Dy/VGUcK+SByE8iKd7kyJKHjzKLVGKRHjwRKR8lSQlkYQS8UQRiiJ0pSSKiKQ8eFH+AObX7Llnzjp79t7nnH3uPY751Yq91ux998ysWbPW7CMSiUQikUgkEolE/iumGTmilW3OPSNjtLJZRhl5Y+RPIicS/auBFp3LHbF9vqINCeONPNNKxW6pjB2yz8gwIw/9RkPADyMjtbJRFhv5LdZZHOvFdviwp+tEThq5a6RfbH/TYLD9sdF8M7JV6XaKfd4mpR9sZhh5b2ShNtQLXk+HpmqD4aeR+VrZYbjJPGBks7JBn5GrWulxTsL20LgONiwCnL0pNkh4JX3Sig5joti+dyu9o0fsYpmrDR7cv0orE0LjOtiskPx+5HJabIdmaYNhr1Z0GDgCfSeqpsGWlDXZY8Xab2lDwi6tGCLYNi8bOa8N9YC30VmEPGW/lJj8tClEANdnXzTovmulwr8fx5ptZHhVi+bZIjYPIvoTGahm0t43C7bXD1pZL9eldtCOV7UYfJ5I7TtlCe3rhb07q5rhuS+0UkE41++CbPcbNQHz4OcXXWKfz6Kuh0Vi72sKVsAxqe4onlsmk4xM0MoMaMvZRVGp59mOz2JDcgjG4ZFWptArdsX741dWfsc8UJk5XF712tMVoRRH0bDKeOg4pScMj1Y6x1KtSNghdhDpMBPaTtBHwnkaLv+4qQ059IgtR7nXz33Y0rd510WgCuM5OIdjbaLTxxYjJDvKMPYNO0poz1om9qEMloOEKOtFcIgsWGHt5CiUrfRxujYkuGODkKOslvDRQVol+VbqL5W5R4/57USvKxgclBQiRLfUvlMhGIhQeHRJE8w08lLsqS17Jf9Po2xHaXWO4hLaLLCHchQcKNQfogdRBYgAjBnP4t95rlEBuIcEWetcNHFlOc8lar8T60hpNLz1uBvTSkOcZLl37cqrlZ5OU7ajtBpKxSIVTagNKz3tgM6dyFL9OFj9aUnzRsl2cvIQP6ItEdveRTIcw8GchdICaLjqIUHiG8cvqZyhTE6udcbeI7Uv8kCsJzv5qK71wLSboxC+s0I1hM5RGAcchT7t8fQXxK7sdZ4OiABp+clFqUTEtEnm2J2/Q7FBlL8mtu0CsU7Tl7TLSwvcQj+lDUU4k/zLSxwUO7mHkmsNfyTrReBfiygMOHlGFqETTb6N8aEQeo08NnJf0g8tIS8/Yez8fNCH+VgjlW9N7ABczxlokZ+f0E/mr0sbyoZJdiHwhm/w+BcchXcnSkwR6yhUCnmwvYS+5RTFRSWiit7qqWh0HlIvnK7jDPTHRRmffiNftbIVHDXyxchzbfAIOYo+BQ0l0K3G5WQIk3+p2pwJUcWt6EbgpwYkmWkVFjYieTMQ4XjOWW2QEr8el0XaHtxOsJLJv3CUp8qWR5HfozQCjsMkt5JSf48SyYdtM/7CLRKJRBriL+35H7Rm3/oZAAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAI8AAAAaCAYAAACOyA9jAAADXUlEQVR4Xu2Yz8sNURjHH6Ekv39G+bFA+bFgQazcpEjehaKUhQ1SRIlkSwqJJUnebERKFhYS7yXJW0JRSimSsrBR/gCer3POO2eee2bmnLn3zis9n/p273xn7pkz3/vMmXOGSFEURVEURVEURVGa5DBrkTQVJYZX0lCUGE6SjjpKDcawnktTUWI4y5ojTaWa+6zHrH328ydrae6IdNqsh6wTrCusX6wJuSOKWUPm+D2sT6xLrEe5I3rLODLXXZd+5LeMTAb/dH4fWIPe9nHWb9ZEz0sF7S2QJvNNGgG+kzk/HiMAfyy2L44cUY/zZNqJFQoghn7l90yaFJffdupPfh1MIdPwas/bab0QCymu+lEAIa6SOWcRaB/nlnMPeOiXD+6qC6wZwi8C/Z5boC8Bb/bfX5WTkt9GMv1dIncEQH47pEnV+YEXFJcfaLE2SzOWNnVe6D3We+HhmAf2c5LYF+KuNCwIeYs0PXAX4+5a73nzyZx3pucN2U/cXT/I3G112cDaJc1IYvJD0d5gjbXbw2SKqAzkF8q5Kr/lZPpTlR/68NT6eK9VC/xY/tHwzggPoNOxxfNSGpatrFXStCBktH+ZsiEXHLW+A38CttfabVz8Ryput4qYR0ERMflhBIGHxxlAAciCkyC/edKk6vxukmm7LD+f2sWDIsCP/eFssvUwWZtl5UgpnkFKn/PgUYH2/bsG4KXdE/v9gP30HymnWG9Yiz0vRK/nPCn5TaXsD8X14ZgykF/qnAf5YUSRx4Tyc6AftYoH4Mf+MIjh1F0YRgB/fpNSPKBN2WrrNFWvFtzEzp8/uDnFQTLnDY2IaDdUqFVsYn2VZiIp+TleU9xj1l9txeZ3jczqylGVX1fFc46yCr/OOkKmQXRSLl1Ti6cOt1h3WNNZK1nvyExm97NuU2d48BByHT6TmTB2Q0p+4BBrtzR7iBsNY/PrqngATriNsmEVJ2iN7M1oongAVk8tyr+ww/Z4bxvgLkdI7vsKb18VmIdgotwLYvPDaLPOft/r7+gDLarOD3RdPLE0VTwx4O6FsLoYIPOSblruiHIwwW4SjI7HyDxe0V+3WhxtGikenMTXcH53o7i5kS/5LC8Dy3IUXVO49z6+3AR2tMAKUfZJieCtNBRFURRF+W/5A7kV71Re6PwxAAAAAElFTkSuQmCC>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAZCAYAAAC2JufVAAABDUlEQVR4Xu2UMWpCQRCGJ4VgI4hNCvUGacTGAwhpU5gLiJ2tddpEESRlvEMOkCpYCqYVBCsbC5uAB9D/f7sr+4ZXWKxgMR988GZ2i9nZ2SdiGIZhGDEPcAZ3cA5L+eULr/AP/sCKWksKCzjBAezBfx+P1Z4jfIty7/A5ipPyAkdR3BJXFC2LK+gDLqM9hN39VblkbHQCNMUVdYBbbxF9WNXJAE/Ek1wr9wc+o++YobjCVrCh1gKPsKuTKeBgF8HrCdfIeWKseYIdnUwBX1MRC3Hd2osrbJ1fzviWfNeTwfmZRjE7wiv+8jEHnQ+BhfGXUfN5vr6J/74JdXFXFK6qnV/O4PyErlEOuWEYd8UZ+8U187rZGhkAAAAASUVORK5CYII=>

[image10]: <data:image/png;base64,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>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAZCAYAAABOxhwiAAAB60lEQVR4Xu2WwSvEQRTHn6QccFBSDrjIxUEu3JSTKKVcHSilyIlcXVwcSIriIOUiUUpKcSMkCqWIkouDi/IH8L5m3v7evh3sxu5pPvVt933n/Wbfzr6ZWaJIJBLJF8WsddYHa59Vnj6copJ1wnpjDZuxglPBemAV+XiB3BcYTGU4WlgvlOSNsG6T4cJzyNox3hO54qXIXtY7q1sSPMjpMF7BwGqjgCblzXuv2ceXPq6XBM8d69h4BaOaNWS8NXKF1vgY7yHkak69D/pZS6wzVhm5fbNI7ktP+BzZS/esAe9pGsiNYc4t1nX68O+gLV5VnE3h2LiTPt5jrXgf7QZvNuCN+xjUsS5UXELJ3FmBAvDAjPKyKRxgHPEBq0r5N97H3ALabFvFfaxNFYNHE/8ITooN4+VauOwNAXko1HqQ0Enu2TFyLZUTWKkpa9L/FK6L/M7D/pDPgkL7IAO0hj6721mN/j1+slDhaAG9klK4zQsVGfIE3BmyKLrlMsBl0mO8ZXKnA5gjN0lbMvwFNvG0iv9S+Chlzo+j2nopcKnon0dLKGWtsnaVJ5sYY8JPrXJuPMTaQ+H2JsbJhps9iFxAVqEdfcS6ouSCqlVjOBGeyfUpXmXl8QpP+jfk4VkU3kXub4XU0EqRSCSSdz4BpnKZnE5Vgs8AAAAASUVORK5CYII=>