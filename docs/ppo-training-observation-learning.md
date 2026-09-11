# PPO 训练过程观察学习记录

日期：2026-09-11
范围：`ppo-minimal-s3-20260908` 与续训段；本记录只记录本次教学，不改变训练规格、checkpoint 或跨任务 memory。

## 1. 范围与非目标

- 学习 TensorBoard 横轴、训练曲线、固定局面动作概率和开发集评估的证据边界。
- 训练对象是 STS1 Ironclad 的 `battle/minimal-v1` 单初始化开发训练。
- 不把本次结果写成 S4 多初始化稳定性、S5 冻结、Gate 3 或中等环境结论。
- 不重新训练、不调参、不启动 S4。

## 2. 工具与工程证据

| 项目 | 结果 | 证据 |
|---|---|---|
| TensorBoard | 已启动并验证页面加载；当前服务需在继续教学前重新启动 | `http://127.0.0.1:6006`；历史 PID 为 `30132` |
| 训练曲线 | 已核对合并后的唯一 iteration `1..256` | 原始段取 `1..32`，续训段取 `33..256` |
| 固定状态诊断 | 已完成 | [ppo-fixed-state-diagnostic.py](../scripts/ppo-fixed-state-diagnostic.py) |
| 固定状态输出 | 已完成 | `runs/ppo-training-observation-20260910/fixed-state-probabilities.json` |
| mask/概率检查 | 已通过 | 同一 mask；合法概率和接近 1；非法概率为 0 |
| 独立开发评估 | 已核对 | 原始 `diagnostic-before.json` 与续训 `diagnostic-after.json` |

固定局面为开发 seed `900000`、`jaw-worm` 初始状态：Ironclad HP `80/80`、能量 `3`，Jaw Worm HP `41/41`，合法动作 6 个。Bash 概率从第 32 轮 `22.6%` 变为第 128 轮 `50.8%`、第 256 轮 `64.7%`；这只证明该状态的策略偏好改变，不单独证明 Bash 长期最优。

## 3. 用户学习记录

记录格式为“问题 → 用户原答 → 验证结果 → 用户修正 → 待补缺口”；不把 agent 解释冒充用户原答。

### 3.1 TensorBoard 基础

- 问题：`Step=32768` 表示什么？`mean_return` 是什么？
- 用户原答：`Step = 32768 更可能表示动作步数，这是最多的次数；mean_return代表平均值`。
- 验证结果：正确。每轮 `8×128=1024` 个 transition；`32768/1024=32`。`mean_return` 是当前 rollout 内已完成 episode 的回报均值，不是历史累计均值。
- 待补缺口：需要独立说清一个 Step、一次 PPO 更新和 Adam 更新的对应关系。

- 问题：4 个合法动作等概率时 entropy 如何变化？
- 用户原答：`1.4 entropy越大 概率越分散`。
- 验证结果：正确，`ln(4)=1.386`；entropy 越大表示分布越分散，但不等于策略更好。

### 3.2 训练结果与固定状态

- 问题：为什么还要看胜率和 reward？
- 用户原答：`mean_return 和血量有关`。
- 验证结果：正确。battle 胜利 reward 为 `1+0.5×剩余HP/最大HP`；胜率达到 100% 后，剩余 HP 仍能区分策略质量。

- 问题：训练规模是多少？
- 用户原答：`一共有256轮 8x128x256对吧`。
- 验证结果：正确：256 个 rollout batch、262144 个 transition；每轮 4 minibatch×4 epoch，共 16 次 Adam 更新。

### 3.3 PPO 更新概念

- 问题：ratio 与 clipping 如何变化？
- 用户原答：`ratio0.4/0.25；clipped ratio 1.2；不会`。
- 验证结果：正确。ratio 为 `1.6`，clipped ratio 为 `1.2`；clip 不会把最终概率硬限制为 `0.30`。
- 待补缺口：暂不把 PPO 数学下钻作为本轮网页学习的前置条件；若继续 C 阶段，再独立验收 logits、mask、概率和抽样动作的区别。

## 4. 当前理解结论

- 已有证据：用户能辨认 Step、mean_return、entropy，理解 reward 与剩余血量的关系，也能计算 PPO ratio/clipping。
- 尚未独立验收：横轴与更新次数的完整表述；新状态下 logits/mask/概率/抽样动作链；训练批、300 局开发评估和多初始化证据的完整区分；负 explained variance 的可验证诊断方向。
- 工程证据与理解证据分开：脚本运行通过不等于用户已经掌握概念。

## 5. 收尾验收问题

用户独立回答后，补入“用户原答”和“用户修正”，再将本轮学习标记为完成：

1. 一个 TensorBoard Step 点与一次 PPO 更新、一次 Adam 更新分别是什么关系？
2. 对一个新状态，logits、action mask、概率和最终抽样动作分别处在哪一步？
3. 为什么 entropy 下降、胜率 100%、loss 很小都不能单独证明最优？
4. 训练批回报、300 局配对开发评估、多初始化证据有什么区别？
5. 对负 explained variance，提出一个可执行的诊断方向，而不是直接断言 Critic 失效。

## 6. 用户收尾作答（2026-09-11）

### 6.1 横轴与更新

- 用户原答：`一次step是一个过程包括了sprnexts 一次PPO更新在一个minibatch的一个epoch 一次Adam更新是一次backward的向量法和学习率的更新`。
- 验证结果：后半段方向正确，但需修正术语。TensorBoard 的一个 `Step` 是累计环境 transition 的横轴值，不是单个状态转移；本配置中每个 PPO iteration 收集 `8×128=1024` 个 transition，再做 `4 minibatch×4 epoch=16` 次 Adam 参数更新。一次 Adam 更新对应一次 loss backward、梯度裁剪和 `optimizer.step()`。

### 6.2 logits、mask、概率和抽样

- 用户原答：`logits是h线性后的logits mask是掩码非法动作 概率是masksoftmax 抽样动作是根据概率来抽动作`。
- 验证结果：基本正确。Actor 先输出 logits；环境提供合法动作 mask；mask 在 softmax 前把非法动作屏蔽；得到合法动作概率；PPO 采样器按该分布抽取动作。mask 不是模型猜出的合法性，且 mask 后非法动作概率为 0。

### 6.3 指标不能单独证明最优

- 用户原答：`可能收敛到次好方案`。
- 验证结果：方向正确但不完整。entropy 下降可能是探索减少或过早集中；胜率 100% 可能已经饱和而无法区分剩余 HP；loss 很小可能只是学习率接近 0 或代理目标变化小。三者都必须结合 reward、独立评估和不同初始化证据。

### 6.4 尚待用户独立复述

- 训练批回报、300 局配对开发评估、多初始化证据的区别。
- 负 explained variance 的一个可验证诊断方向。

## 7. Agent 详细讲解补充

### 7.1 三种证据的区别

#### 训练批回报

训练批回报是某一次 PPO iteration 采集 rollout 时的即时统计。当前配置每次采集
`8×128=1024` 个 transition；其中有多少局在这 128 步内结束是不固定的，只有已完成
episode 才进入 `mean_return` 和 `win_rate`。例如第 256 轮有 76 个完成 episode，
`mean_return=1.4336`、`win_rate=1.0`。

它的用途是监控训练过程和生成更新数据，特点是每轮更换状态分布、会有噪声，不能当作
固定测试集成绩，也不能直接代表所有历史对局的平均表现。

#### 300 局配对开发评估

这是训练前后分别运行固定的 300 局开发配置：Jaw Worm、Cultist、Two Louse 各 100 局。
评估阶段不更新参数，使用 `eval/no_grad`；before 和 after 使用相同开发种子，并把模型与
随机策略配对比较。这样可以回答“这一份最终 checkpoint 在固定开发集上是否比随机策略好”。

本次最终结果为平均回报 `1.4396`、胜率 `100%`；随机策略为平均回报 `1.1775`、胜率
`89.3%`；配对回报差的 95% CI 为 `[0.2198, 0.3086]`。这支持本次单初始化开发集上的
改善，但不是正式 eval，也不是跨训练初始化的稳定性证明。

#### 多初始化证据

多初始化是完整重复训练流程，而不是把同一次训练从 256 轮延长：预先登记多组不同的
model/sampling/shuffle seed，保持预算、环境、奖励和评估配置一致；每组都保存最终模型，
再比较各组的开发结果、分桶指标、均值、差异和置信区间。

它回答的是“换一个随机初始化，PPO 是否仍然有效”。本次只有一组初始化，所以即使 256
轮和 300 局配对 CI 通过，也不能声称 S4 稳定性或 Gate 3 通过。

### 7.2 负 explained variance 的具体诊断

当前实现使用：

```text
EV = 1 - Var(returns - old_values) / Var(returns)
```

`returns` 是本轮 rollout 根据 GAE 计算出的 value target，`old_values` 是采样和更新前
Critic 对同一批观测的预测。EV 为负表示当前预测残差的方差比一个简单的常数基线还大，
但不自动证明 Critic 代码失效。

一个可执行的第一诊断方向是逐 iteration 同时记录并比较：

```text
Var(returns)
Var(returns - old_values)
mean(old_values), mean(returns)
有效样本数、终止样本数、按遭遇分桶的 EV
```

然后按以下顺序核对：

1. 若 `Var(returns)` 很小，EV 的比值会非常敏感，先不能作强结论。
2. 若 target 方差正常但残差方差长期更大，再检查 `returns` 与 `old_values` 是否对齐。
3. 检查 GAE 的终止 mask：真正终止不自举；rollout 外部截断用 reset 前最终观测自举；
   episode reset 后的新局不能串入前一局的优势递推。
4. 若数学与边界均正确，再将问题缩小为 Critic 学习能力、目标噪声或状态分布变化，并用
   固定小样本/独立目标继续验证。

本次观测到的 EV 在第 1、32、128、256 轮约为 `-0.73、-0.17、-1.13、-0.26`；
这些数值是诊断线索，不是已经完成的原因定位。
