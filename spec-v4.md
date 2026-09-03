

> **文档状态**：本文档为当前唯一执行依据。
> `spec-v3.md` 已冻结为长期愿景文档，不再更新，其目标（STS2 / A10 / 完整 run）不进入本项目排期。
> `学习路径.md` 的方法论部分继续有效，排期部分被本文档 §10 取代。

---

## 0. 项目定位

### 0.1 真实目标

**通过工程实践理解主流 Transformer 技术原理。** 游戏是载体，不是目的；不服务于留学申请或导师匹配。

具体到可验证的理解目标：

- 手写 QKV 投影、multi-head attention、attention pooling，并能解释每个张量形状的来源；
- 理解 padding mask 与 causal mask 是同一机制的两种掩码形状；
- 理解置换不变编码（Set Transformer）与自回归序列建模（Decision Transformer）各自的适用边界；
- 能说清"下一 token 预测"如何等价于"下一步决策"，以及 return-conditioning 在其中多做了什么。

### 0.2 交付物

1. 可复现的 headless STS1 Ironclad 战斗模拟器（Python），带结算顺序单元测试与真实日志回放对拍；
2. 随机策略、规则策略两条基线；
3. A 阶段：Set Transformer 状态编码器 + PPO；MLP vs Set Transformer 配对对照实验；
4. B 阶段：Decision Transformer 离线自回归动作预测；
5. A/B 两族模型在同一任务、同一评估集上的对照分析报告；
6. 完整实验记录与一键复现脚本。

### 0.3 明确非目标

不做，且不在项目中途重新讨论：

- STS2（生态不完善，无高质量对局来源，EA 版本漂移）；
- 反编译游戏二进制；
- Ascension 难度爬坡（A5 / A10）；
- 完整 run（地图、商店、营火、事件）；
- 遗物、药水、卡牌升级；
- Expectimax / Beam Search 搜索轨道；
- 卡组-地图双塔评估器；
- PBT、80/20 历史对手池、风格统计量辅助奖励；
- KL 锚定退火（前提是大规模人类 BC 策略，本项目不具备）；
- 真实游戏桥接作为训练通道。

---

## 1. 硬约束

| 项 | 值 |
|---|---|
| 起始 | 2026-09-01 |
| 出发 | 2027-02 初 |
| 自然周 | 约 22 周 |
| 扣除 | 旅游 1.5 周、行前准备 1 周、缓冲 1.5 周 |
| 有效周 | **18 周** |
| 周工时 | **30 小时** |
| 总预算 | **540 小时** |

> v3 假设的 40 小时 × 26 周 = 1040 小时，是本预算的两倍。凡从 v3 继承的排期数字一律无效。

---

## 2. 已裁定决策

| # | 决策点 | 裁定 |
|---|---|---|
| 1 | 时间预算 | 18 周 / 30 小时每周 / 540 小时 |
| 2 | 环境来源 | 自写 Python 模拟器，规格用 **STS1**，`runlogger` 日志作正确性 oracle |
| 3 | 技术中心 | 路线 C：先 A（Set Transformer + PPO）→ 后 B（Decision Transformer），**两者对照即产出** |
| 4 | 机制范围 | 分两步：第 1-4 周最小切片，第 5 周起扩至中等档；不做完整 Act 1 |
| 5 | 观测/动作表示 | 环境返回结构化 dict；`FlattenWrapper` 与 `TokenWrapper` 同源派生；动作扁平 `(槽位, 目标)` + mask |
| 6 | v3 处置 | 冻结为愿景文档，继承设计约定，放弃规模主张 |
| 7 | 奖励 | 胜负 + 剩余血量连续回报，加 potential-based 回合惩罚；A/B 共用同一标量 |
| 8 | 评估协议 | 1000 隔离种子、按遭遇类型分桶、配对 bootstrap 95% CI、附效应量 |
| 9 | 正确性验证 | 单元测试 + 日志回放对拍；`sts_lightspeed` 差分测试为 stretch |
| 10 | 工具链 | CleanRL 单文件 PPO 起点、Set Transformer 手写、YAML + dataclass、W&B 或 TensorBoard |
| 11 | 止损 | 日历闸门 + 指标门槛，谁先触发算谁；降级路径预先写死 |

---

## 3. 从 v3 继承的设计约定

以下与项目规模无关，全部保留：

**状态编码**

- 类型化专用 MLP 投影：卡牌、敌人、玩家各走独立小 MLP 投影到统一 `d_model`；
- 注入 `entity_type_embedding` 与 `location_embedding`（手牌 / 抽牌堆 / 弃牌堆 / 消耗堆）；
- **卡牌语义特征替代手牌索引**——索引每回合含义漂移，是已知陷阱；
- 全局池化用 attention pooling (PMA)，不用裸 sum-pooling；
- **seed 不进状态编码**，只保留给环境复现，防学到伪相关。

**动作与掩码**

- 合法动作列表由环境直接给出，模型不猜合法性；
- 掩码在 softmax **之前**施加，非法 logits 置 `-inf`，梯度用掩码后分布计算（naive masking 有偏）；
- 单场战斗超过 N 回合判负的环境侧硬超时，防死锁轨迹污染数据。

**奖励**

- 回合惩罚用 potential-based shaping，保证不扭曲最优策略；
- 监控主动送死率，防奖励黑客。

**原则**

- 接口质量是学习成败的一级因素（NLE 复盘教训）。观测/动作参数化写错，后面所有算法工作都在错误物理里优化。

**反面教材（CombatSolver 三条）**

1. 手写评估权重系统性低估长线收益 → 禁止密集手写 shaping；
2. 深度截断处的价值质量决定成败；
3. 特定流派搜索空间爆炸 → 本项目不做搜索，自动规避。

---

## 4. 环境规格

### 4.1 机制范围

**第一档（第 1-4 周，最小切片）**

- Ironclad 初始卡组：Strike ×5、Defend ×4、Bash ×1
- 敌人 3 种：Jaw Worm、Cultist、Louses（多目标）
- 状态效果：Block、Vulnerable、Weak
- 机制：能量、抽牌、弃牌、洗牌、回合结算

**第二档（第 5 周起，中等档）**

- Ironclad 常见卡 30-40 张（含力量体系，如 Inflame、Demon Form 类长线卡）
- Act 1 敌人约 10 种 + 精英战
- 状态效果补：Strength、Dexterity、Poison、Thorns、Artifact
- 不含：遗物、药水、卡牌升级

> 卡表可以 HuggingFace `t22000t/slay-the-spire-1-cards` 为起点（带 damage / block / status effects 字段）。
> **未核实**：第三方整理的衍生数据，必须抽查 5-10 张卡与游戏内数值比对后再采用。

### 4.2 观测

```python
obs = {
    "hand":        [n_hand,  D_card],    # 变长，每张牌一个 token
    "enemies":     [n_enemy, D_enemy],   # 变长，每个敌人一个 token
    "global":      [D_global],           # 定长：能量、堆计数、玩家 HP/block/buff、回合数
    "hand_mask":   [n_hand],             # padding 掩码
    "enemy_mask":  [n_enemy],
    "action_mask": [A],                  # 合法动作掩码
}
```

两个 wrapper 从同一份 dict 派生，保证 MLP 与 Transformer 的特征同源，对照实验才干净：

- `FlattenWrapper` → `[D_flat]`，给 MLP 基线
- `TokenWrapper` → `[n_token, d_model]` + mask，给 Set Transformer

### 4.3 动作

扁平化 `(hand_slot, target)` 组合 + mask：

```
A = max_hand * max_target + 1     # 末位 = end_turn
```

不用 factored 双头（选卡头 + 目标头），原因：无目标卡的条件依赖在 PPO 里容易出微妙 bug，在 DT 里要预测多 token。扁平 + mask 让 DT 的 action 天然是单个离散 token，与 next-token prediction 完全对齐。

**关键约定**：动作索引指向**手牌槽位**，槽位分配必须确定（按抽牌顺序），否则 replay 与 oracle 对拍失败。这与 §3 的"卡牌语义替代索引"不冲突——token **特征**用语义（绝不编码槽位号），动作**输出索引**指槽位。

### 4.4 奖励

$$R = \mathbb{1}[\text{win}] \cdot \left(1 + \lambda \cdot \frac{\text{HP}_{\text{剩余}}}{\text{HP}_{\max}}\right) + \sum_t \left(\gamma \Phi(s_{t+1}) - \Phi(s_t)\right)$$

- $\lambda = 0.5$ 起，第 5-6 周按实际回报分布校准一次，**之后锁死**
- $\Phi$ = 敌方总 HP 归一化（或回合数），potential-based 保证最优策略不变
- **A 阶段的 RL reward 与 B 阶段的 DT return 必须是同一标量**。改动则所有离线数据集回报需重算

不用稀疏 ±1 的理由：DT 的 return-conditioning 需要回报有分辨率。只有两档时，条件变量退化，B 阶段等价于普通 BC，核心对照失去意义。

不用密集 shaping 的理由：Inflame 本回合 0 伤害但可能是最优首手，按伤害 shaping 会训出只会 Strike 的 agent，且很晚才会发现问题在奖励而非网络。

---

## 5. 正确性验证

### 5.1 Gate 1 五条门槛（第 4 周末）

1. 过滤后的 `runlogger` 日志片段回放，逐步状态（玩家 HP / block / buff、敌人 HP / buff）**100% 一致**，不接受"大部分匹配"
2. 结算顺序单元测试全过
3. 同一 seed 跑两次，轨迹逐字节相同
4. 随机策略 10000 场不崩、非法动作率 0、硬超时触发率极低
5. 单核吞吐 ≥ 2000 步/秒

### 5.2 日志回放的覆盖面处理

人类日志是完整游戏，含未实现的卡、遗物、药水。**按子集过滤**：只取全程卡牌、敌人、状态效果均落在已实现范围内的战斗片段。最小切片阶段过滤严苛（可能只剩 Act 1 前几场），中等档扩容后可用片段显著增多——验证强度随机制范围一起增长，这是分两步扩容的额外收益。

> **未核实**：`runlogger` 的 `runs/` 目录实际有多少局、覆盖哪些卡，需拉下来统计。
> 已知风险：mod 处于 beta，日志格式可能 breaking change；STS1 自身有可复现性 bug，需配 `determinismfix`。

### 5.3 结算顺序单元测试清单

不测单卡效果（写错立刻可见），专测状态机细节，每条手算期望值：

- Block 在回合开始清零 vs 结算前清零
- 力量加值与易伤倍率的运算顺序（STS 是先加 Strength 再乘 Vulnerable）
- Weak 在回合结束还是回合开始递减
- 抽牌堆空时弃牌堆洗回的时机与 RNG 消耗次数
- 敌人死亡瞬间其意图是否仍生效
- 多目标伤害分配与死亡连锁
- Artifact 抵消 debuff 的优先级

约 20-30 条。这是全项目最值钱的代码——PPO 出问题时它们让你立刻排除环境嫌疑。

### 5.4 差分测试（stretch）

`sts_lightspeed`（C++ + pybind11）作 oracle 做随机动作序列对拍，能覆盖人类日志走不到的状态组合。

**执行规则**：第 2 周花半天试 build，成功即纳入，卡住立即放弃并在 `docs/decisions.md` 记录原因。不允许超过半天。

> **未核实**：其当前 API 表面、构建难度、机制覆盖范围。

---

## 6. 评估协议

### 6.1 种子隔离

- `eval_seeds.json`（1000 个种子）**第 1 周生成并提交进版本控制**
- 训练采样区间与评估区间互斥：评估 `seed < 1000`，训练 `seed >= 100000`
- 每个 run 记录 `eval_seeds.json` 的哈希，保证跨周结论可比

### 6.2 配对比较

同一批 1000 种子上跑全部策略（随机 / 规则 / PPO+MLP / PPO+SetTransformer / DT），每个种子下各策略面对**完全相同**的初始牌序与敌人。

理由：STS 战斗的种子间方差极大（抽牌运影响支配性），非配对比较下 1000 局可能检不出真实差异。

### 6.3 分桶

按遭遇类型分层报告。不同敌人对策略要求不同：Jaw Worm 是 race、Cultist 要求快杀、Louses 是多目标分配。总体胜率会把差异平均掉。

多敌人桶是 Set Transformer 最可能显出优势的地方（集合结构真正有意义），也是核心对照最该看的桶。

分桶后每桶约 100-150 局。若某关键桶样本不足，单独加采样。

### 6.4 指标

| 优先级 | 指标 | 说明 |
|---|---|---|
| 主 | 回报均值 | §4.4 的 R，唯一主指标 |
| 次 | 胜率 | |
| 次 | 平均剩余血量 | |
| 次 | 平均回合数 | |
| 断言 | 非法动作率 | **必须恒为 0**，是正确性检查不是优化目标 |

### 6.5 "显著优于"的判定

- 配对 bootstrap 重采样 10000 次，回报差值 95% CI **下界 > 0**
- 不用 t 检验：回报分布双峰（赢/输两簇），正态假设不成立
- **同时报效应量**（Cohen's d 或差值/标准差）。1000 局配对下微小差异也会"显著"，需区分统计显著与实质显著

---

## 7. 模型架构

### 7.1 与经典 Transformer 的 token 对应

| 经典 GPT | A 阶段 Set Transformer | B 阶段 Decision Transformer |
|---|---|---|
| token = subword | token = **实体**：一张手牌 / 一个敌人 / 玩家 | token = 轨迹项：`return-to-go` / `state` / `action` |
| 词表查表 | 卡牌 ID 查表 + 连续特征经类型专用 MLP 投影 | action 走词表查表；return / state 是线性投影，无词表 |
| 位置编码必需 | **故意没有**——置换不变即卖点 | timestep embedding，同一时刻三 token 共享 |
| causal mask | 无，集合内双向全连接（近 BERT encoder） | 有 |
| 预测下一 token | 无自回归目标，编码结果喂 PPO 的 policy / value 头 | 预测 action token，**loss 只在 action 位置** |
| 序列长 = 句长 | = 实体数（小切片 10-15，中等档 40-60） | = timestep × 3 |
| `[CLS]` 池化 | PMA：可学习 seed query 做 attention pooling | 取 state token 位置输出 |

**两者是嵌套关系，不是并列。** B 的每个 `state` token，就是 A 的编码器吃掉 40 个实体 token 后吐出的单一向量。内层无序集合（无位置编码），外层有序序列（causal mask）。这是"先 A 后 B"能省一次重写的根据——A 的编码器整体搬进 B 当 state embedding 层。

**"下一 token 即下一步决策"在 B 里字面精确。** 序列为 `R₀ s₀ a₀ R₁ s₁ a₁ ...`，在 `a_t` 位置做标准 next-token prediction，词表就是动作空间。与 GPT 唯一的差别是条件里多了 `return-to-go`——推理时设高，模型即"假装自己是高手"。

### 7.2 A 阶段

- 编码器：类型化投影 → ISAB × 2 → PMA → `[d_model]`
- 接 PPO 的 policy head（扁平动作 + mask）与 value head
- **手写 QKV、multi-head、ISAB、PMA**，不用 `nn.MultiheadAttention`。mask 加在 softmax 前那一步必须亲手写
- 跑通验证后可换内置版提速（fused kernel），保留手写版作参照实现与测试基准

MLP 基线：同参数量级，吃 `FlattenWrapper` 输出。

### 7.3 B 阶段

- 轨迹序列化 `(R_t, s_t, a_t)` 重复，`s_t` 由 A 的编码器产出
- causal mask + timestep embedding
- 离线监督训练，交叉熵，只在 action 位置算 loss
- 推理时 return-to-go 设为训练集回报的高分位数

**已接受的上限**：训练数据来自规则 agent + ε 噪声，性能上限受生成策略约束。return-conditioning 靠轨迹拼接能超出一部分，但不会大幅超越。**第 16 周不要怀疑这是实现 bug。**

### 7.4 动作头形态（未决）

先用扁平索引。第 11 周有了 token 编码后评估 pointer head（query 与手牌 token 点积 → softmax），它把动作选择直接绑在卡牌编码上，更干净，但会让 B 的离散 action token 变复杂。届时定。

---

## 8. 工具链

| 组件 | 选择 | 理由 |
|---|---|---|
| PPO | CleanRL 单文件 400 行为起点，逐行读懂再改 | 无抽象层，GAE / advantage norm / value clip / grad clip 全部平铺可见。从零手写的风险是 PPO 对实现细节极度敏感，缺一个 advantage normalization 就训不起来，而你会误以为是架构问题 |
| 不用 SB3 | — | `MaskablePPO` 把 mask 如何进 loss、优势如何算全藏起来；且塞结构化 dict + Set Transformer 会与 `features_extractor` 接口别扭 |
| 架构 | 手写 | 这是学习目标本身。MHA ≈ 30 行、ISAB ≈ 20 行、PMA ≈ 15 行 |
| 配置 | `@dataclass` + `yaml.safe_load` + `argparse` 覆盖 | 约 50 行，透明。不引 Hydra：组合能力强但报错难读，单人 18 周不划算 |
| 记录 | W&B 或 TensorBoard + `runs/<run_id>/config.yaml` | |

### 8.1 每个 run 必须落盘

- git commit hash
- 完整配置
- 随机种子
- `eval_seeds.json` 哈希

理由：会跑几十次实验。三周后回看"12 号为何优于 8 号"，没有 commit hash 就无法重建代码状态，结论作废。

### 8.2 监控量

回报均值、胜率、策略熵、新旧策略 KL（健康度）、explained variance、grad norm、非法动作率（恒 0）、每秒步数。

**策略熵塌陷**与 **explained variance 长期近 0** 是 PPO 故障最早的两个信号。

---

## 9. 18 周排期

| 周 | 主线工程 | 原理下钻 | 出口 |
|---|---|---|---|
| 1 | v4 定稿；仓库骨架；`eval_seeds.json` 生成提交；拉 `runlogger` 摸清格式与 `runs/` 覆盖 | 状态机建模、RNG 与可复现性 | 评估集入版本控制 |
| 2 | 最小切片模拟器；半天试 build `sts_lightspeed`，卡住即弃 | POMDP、动作掩码语义 | 随机策略能打完一场 |
| 3 | 结算顺序单测 20-30 条；日志片段过滤与回放对拍 | 力量/易伤/虚弱的结算代数 | 回放逐步 100% 一致 |
| 4 | 性能优化（去深拷贝）；观测 dict + 双 wrapper；动作掩码 | — | **Gate 1** |
| 5-6 | 扩中等档；规则 agent；评估 harness + 配对 bootstrap；校准并锁死 λ | 分层评估、效应量 | **Gate 2** |
| 7-8 | CleanRL PPO 读懂并接入；MLP 策略；监控面板 | GAE、ratio clipping、mask 下梯度 | 训练跑通不崩 |
| 9-10 | PPO 调参；熵与 explained variance 诊断 | 失败模式：熵塌陷、value 失配 | **Gate 3** |
| 11-12 | 手写 QKV / MHA / ISAB / PMA；接入 PPO | 注意力、置换不变、padding mask | Set Transformer 收敛 |
| 13 | MLP vs Set Transformer 配对对照，分桶报告 | — | **Gate 4** |
| 14 | 规则 agent + ε 噪声生成 20 万条轨迹（多进程 CPU） | 离线数据分布与覆盖 | 数据集落盘 |
| 15-16 | DT：序列化、causal mask、timestep embedding、复用 A 编码器 | 自回归、causal mask、return-conditioning | **Gate 5** |
| 17-18 | 报告、README、复现脚本、代码整理。**不写新功能** | — | 他人可复现 |

### 9.1 排期风险

**第 11-12 周把 Set Transformer 接在已调通的 PPO 上是刻意的。** 先有能训起来的 MLP 基线，换架构出问题时才能确定是架构的事。反序（先上 Transformer）会让你分不清是注意力实现错了还是 PPO 没调好。

**第 14 周的数据质量决定 B 阶段上限。** 若 Gate 2 时规则策略只是勉强赢随机，DT 天花板会很低。届时改用 A 阶段训好的 PPO 策略加噪声生成，质量更高。

**算力不是瓶颈。** 20 万条轨迹 ≈ 600-1000 万 transition，单核几千步/秒、8 核 multiprocessing 下是分钟到小时级，纯 CPU。紧凑 int 数组存储几百 MB 到几 GB。训一个小 DT 在几 GPU-小时内。

---

## 10. 止损与降级

日历闸门与指标门槛，**谁先触发算谁**。降级路径已写死，不留到当时决定。

| 检查点 | 周 | 门槛 | 触发降级则 |
|---|---|---|---|
| Gate 1 环境 | 4 | §5.1 五条全过 | 砍掉中等档扩容，锁定最小切片到项目结束 |
| Gate 2 基线 | 6 | 规则显著优于随机（配对 CI 下界 > 0） | 不降级，但说明状态编码或机制实现有问题，回查 Gate 1 |
| Gate 3 PPO | 10 | PPO+MLP 显著优于随机 | **PPO 出局，A 阶段改 BC + Set Transformer 监督学习**，架构对照保留 |
| Gate 4 对照 | 13 | 对照跑完，**无论结果如何** | 无差异也算通过，如实报告 |
| Gate 5 DT | 16 | DT 不低于生成数据的策略 | 砍掉 return-conditioning 的性能主张，只报实现与分析 |

### 10.1 为什么 Gate 3 是最重要的一行

它的降级路径是"PPO 出局，改监督学习"，不是"再给两周"。这条能救整个项目：Set Transformer vs MLP 的对照在 BC 框架下同样成立，且更干净（监督学习方差小，架构差异更易检出）。核心目标是理解 Transformer，不是证明 PPO 能训起来。**RL 是手段不是目的。**

若 Gate 3 降级：第 11-13 周不受影响；第 14 周数据生成改用规则 agent 而非 PPO 策略。退路是通的。

### 10.2 为什么有"跑完即通过"的门槛

Gate 4 不要求 Set Transformer 赢。若在当前机制范围下 MLP 打平，那是真实结论，附分析（实体数太少、状态维度不足以体现置换不变优势）写进报告即为合格产出，比调参凑出的胜利更有价值。预留"允许失败"的出口，能防止第 14 周开始偷偷调参。

### 10.3 元规则

**任何单一问题连续投入超过 3 天无进展，强制停下写一段**：卡在哪、试过什么、下一步的两个**不同**方向；然后选更不一样的那个。给 debug 死循环用，PPO 调参尤其需要。

### 10.4 第 17-18 周

不设指标门槛，纯保护性预留。**不允许写新功能。** 一个跑得起来但无人能复现的项目，半年后回看等于不存在。

---

## 11. 仓库骨架

```
sts-rl/
├── README.md
├── pyproject.toml
├── spec-v4.md                  # 本文档，唯一执行依据
├── spec-v3.md                  # 冻结，愿景，不再更新
├── 学习路径.md                  # 方法论有效，排期已被 §9 取代
├── docs/
│   ├── decisions.md            # 决策日志：日期 / 决策 / 理由 / 推翻条件
│   ├── mechanics.md            # 结算顺序规格，单测的书面依据
│   └── report.md               # 第 17-18 周产出
├── configs/
│   ├── env_minimal.yaml
│   ├── env_medium.yaml
│   ├── ppo_mlp.yaml
│   ├── ppo_settransformer.yaml
│   └── dt.yaml
├── eval_seeds.json             # 第 1 周生成，不再改动
├── sts/
│   ├── env/
│   │   ├── state.py            # 战斗状态，避免深拷贝
│   │   ├── cards.py
│   │   ├── enemies.py
│   │   ├── effects.py          # buff/debuff 与递减时机
│   │   ├── combat.py           # 回合结算主循环
│   │   ├── rng.py              # 独立 RNG 流，保证可复现
│   │   ├── actions.py          # 动作枚举与 mask 生成
│   │   └── wrappers.py         # FlattenWrapper / TokenWrapper
│   ├── agents/
│   │   ├── random_agent.py
│   │   └── rule_agent.py       # 兼作 §7.3 数据生成器
│   ├── models/
│   │   ├── attention.py        # 手写 QKV / MHA，A 与 B 共用
│   │   ├── set_transformer.py  # ISAB / PMA
│   │   ├── mlp.py              # 对照基线
│   │   └── decision_transformer.py
│   ├── train/
│   │   ├── ppo.py              # CleanRL 起点
│   │   ├── bc.py               # Gate 3 降级备用
│   │   └── dt_train.py
│   ├── data/
│   │   ├── generate.py         # 多进程 rollout
│   │   └── replay_oracle.py    # runlogger 日志过滤与回放对拍
│   └── eval/
│       ├── protocol.py         # 配对 bootstrap、分桶
│       └── report.py
├── tests/
│   ├── test_ordering.py        # §5.3 的 20-30 条
│   ├── test_determinism.py
│   ├── test_masking.py
│   ├── test_replay.py
│   └── test_attention.py       # 手写 vs nn.MultiheadAttention 数值一致
└── scripts/
    ├── make_eval_seeds.py
    ├── run_eval.py
    └── reproduce_all.sh        # 第 17-18 周
```

---

## 12. 未决事项

留到执行时定，不阻塞开工：

| 事项 | 何时定 | 默认 |
|---|---|---|
| 动作头：扁平索引 vs pointer head | 第 11 周 | 先扁平 |
| W&B vs TensorBoard | 第 7 周首次训练前 | 任选，接口封一层 |
| 中等档卡表来源核实 | 第 5 周 | HF 数据集抽查 5-10 张后决定 |
| `sts_lightspeed` 是否纳入 | 第 2 周 | 半天试 build，卡住即弃 |
| $\lambda$ 终值 | 第 6 周 | 0.5 起，校准后锁死 |

---

## 附 A：工时分配（修正 `学习路径.md` 第 255-260 行）

原表表头 4 列但每行 5 个数值，且四项合计 100% 与默认分配的"文档 10%"矛盾。修正为五列：

| 阶段 | 工程 | 学习 | 实验 | 文档 |
|---|---|---|---|---|
| 环境阶段（1-6 周） | 60% | 20% | 10% | 10% |
| 算法阶段（7-10 周） | 40% | 30% | 25% | 5% |
| 架构阶段（11-13 周） | 30% | 40% | 25% | 5% |
| 离线阶段（14-16 周） | 35% | 30% | 30% | 5% |
| 收尾阶段（17-18 周） | 20% | 0% | 20% | 60% |

## 附 B：本文档未核实的事实

开工后需实测确认，不得当作既定前提：

1. `runlogger` 的 `runs/` 实际局数、卡牌覆盖、当前日志 schema
2. `sts_lightspeed` 的 API、构建难度、机制覆盖
3. HF `t22000t/slay-the-spire-1-cards` 的数值准确性
4. 纯 Python 模拟器实际吞吐（Gate 1 第 5 条以实测为准）
5. `determinismfix` 是否为真实游戏对拍的必需依赖

三点执行说明：

第 1 周先做 `docs/decisions.md` 和 `docs/mechanics.md`，前者记录这次的 12 项裁定和各自的推翻条件，后者是结算顺序的书面规格 —— 单元测试要照着它写，而不是照着代码写，否则测试只会验证你实现了什么，不会验证你实现对了什么。

`sts/models/attention.py` 被 A 和 B 共用是有意的设计。同一份 multi-head attention，A 传 padding mask，B 传 causal mask，你会在代码层面直接看到这两者是同一个机制。`tests/test_attention.py` 拿手写版和 `nn.MultiheadAttention` 对数值，是你验证自己真的写对了的手段。

仓库骨架我列的是目标形态，不用第 1 周全建出来。按周推进时再加文件，空目录和空文件反而会掩盖进度。