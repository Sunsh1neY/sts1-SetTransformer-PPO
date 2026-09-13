# STS A 路径实施任务书 v1

> 裁定日期：2026-09-13  
> 适用项目：`Sunsh1neY/sts1-SetTransformer-PPO`  
> 状态：待 Agent 在用户本地工作区实施；本文不是已完成代码或训练的报告。  
> 核心裁定：**策略内部先选择操作来源，再条件化选择敌人目标；参数选齐后只执行一次 `env.step`。保留共享 Set Transformer 与 PMA。**

## 0. 先读：本轮到底交付什么

本轮完成的是一条可验收的工程闭环：

**现有实体观测与合法候选 → Set 编码器 → 两阶段 Pointer 策略 + PMA Critic → A 路径完整动作 → PPO → 测试、诊断、受限训练与评估。**

不能只写设计方案、只定义网络类，或者只用随机张量跑通 forward 后宣布完成。也不能为了推进本轮，重新开发整个游戏环境、先训练地图决策 Agent，或等待海量 `.run` 数据。

本包包含：

- 本实施任务书：算法、接口、执行顺序、测试和边界。
- `codex-astra-agent-prompt.md`：直接交给执行 Agent 的任务提示词。
- `a-path-acceptance-cases.json`：人工构造的数值验收夹具；不是自然游戏初态或训练数据。
- `verify-a-path-math.py`：独立数学核验脚本；不是项目策略或训练器的替代实现。

### 0.1 证据边界与本地优先

编写时通过 GitHub 连接器核对的远端 `main`：

```text
0d68033d2b2fb7a042d33343b863af7c3e818967
提交日期：2026-09-12
提交说明：Implement public battle environment and document M1–M5 progress
```

直接阅读了 `AGENTS.md`、`sts/train/ppo.py`、`sts/models/mlp.py`、`docs/public-battle-implementation.md` 等。没有在用户笔记本上运行项目或验证 CUDA 性能。[R1–R5]

该远端快照里的 PPO 仍显式绑定 `MlpActorCritic`、`FlatBatch`、`FlattenWrapper(LightspeedBattleEnv)` 和 minimal reward contract；公开扩展环境报告也把新模型/张量/训练迁移列为未完成。因此，**不能把本任务理解成“仅换一下 softmax”**。[R2–R5]

用户已说明本地环境和 token 支持范围比这个远端快照更广。Agent 必须读取本地最新代码、未提交改动和现行机器契约，保留已完成的第一/第二幕、卡牌、诅咒、药水与选择机制。**不得回滚至本文引用的旧远端范围，也不得仅凭用户描述把未实测接口标为通过。**

事实冲突处理：

1. 现存实现状态由本地代码、测试和实际运行证据决定。
2. 设计目标由本轮用户明确选择的 A 路径决定。
3. 旧文档中冲突的动作头裁定，先登记到 `docs/decisions.md`，再对现行规格作最小修订；不要私自把整份规格升级成一个新大版本。
4. 保留奖励、可见信息、评估隔离、旧检查点和既有环境行为约束。
5. 不执行 `git reset --hard`、`git clean`、强制 checkout、删除未提交文件或强制推送；本任务不授权自动 commit/push。

## 1. 已锁定设计：不再重新选择 A/B

| 编号 | 本轮必须保留的决定 |
|---|---|
| D-A1 | 来源选择和目标选择发生在策略内部，不人为新增“等待敌人目标”的环境 transition。 |
| D-A2 | 第一阶段把具体出牌、具体药水及当阶段合法特殊动作放入**同一个**分布。 |
| D-A3 | 第一阶段按操作语义使用可学习 task Query，读取上下文化实体。不是每张卡一个 Query 参数。 |
| D-A4 | 第二阶段由**已选中的来源实体**生成 Query，对合法敌人 Key 打分并归一化。牌和药水复用目标评分机制。 |
| D-A5 | 两个动作评分头在 logits 后进入概率计算，不再在头内增加 `softmax(QKᵀ)V` 信息聚合。共享编码器和 PMA 仍正常使用注意力的 V。 |
| D-A6 | 保留 PMA：全局表示供 Critic，以及结束回合、确认、跳过等特殊动作评分。 |
| D-A7 | 输入已有阶段/效果上下文时直接复用，不为“强化阶段信息”再强制增加一个重复的 c 网络。 |
| D-A8 | 无目标操作的目标概率是 1，目标 log probability 和目标熵为 0；不能借敌人 0 充当语义上的无目标。 |
| D-A9 | PPO 对完整动作使用一次联合 ratio、一次 clipping；不是两条 transition，也不是两个独立 clipped loss。 |
| D-A10 | 真正结算后产生的耗尽、弃牌、取牌或随机候选选择，继续走环境已有的新决策状态。A 路径不把这些真实阶段吞成一个巨型动作。 |

**明确作废：**把所有完整候选用 `z(r,i,j)=b(r,i)+t(i,j)` 直接做一次全局 softmax，作为本轮实际采样策略。那是一种不同的归一化方式，不是本轮 A 路径。

**不是本轮结论：**新增一层共享 Transformer 一定比原来更强。默认先保持已有合格主干；只有本地尚无合格 Set 主干时，使用第 10 节的小型默认值。不凭“训练更充分”无条件加层。

## 2. 范围与不做事项

### 2.1 本轮应完成

1. 本地现状核验与文档冲突收口。
2. 完整公开实体输入与合法候选之间的映射适配；复用既有实现。
3. 共享 Set 编码器、PMA、任务 Pointer、条件目标 Pointer、特殊动作头及 Critic 的可训练实现。
4. A 路径的采样、历史动作重新评估、精确熵、可视化联合概率与版本契约。
5. PPO collector/batching/update/checkpoint 在新模型与实际环境上的迁移。
6. 结构、梯度、置换、边界、回放、续训测试。
7. 现有可信初态池的版本化接入、吞吐诊断、受限学习实验和分层评估报告。
8. 面向用户的实际样例讲解：显示两个分布、联合 log probability、一次 env.step 和一次更新。

### 2.2 本轮不做

- 不训练地图/构筑/商店的第二个 RL Agent；不实现完整 RunEnv 或 DT。
- 不自动下载大型 `.run` 归档、不购买云算力、不启动无限时长的训练/搜索。
- 不为了覆盖更多机制删除场景里的牌/药水/遗物，也不把未知内部状态补零。
- 不改变 `battle_reward_v1` / `run_reward_v1`、gamma、奖励累计和退出 HP 时点；不新增药水惩罚或耗尽奖励。
- 不把现有环境计步改成鼠标点击次数，不重置外部预算含义。
- 不替换已有关系表示、怪物机制或候选生成器，除非实测发现阻塞本轮的具体错误；修复须单独记录。
- 不给当前未支持的选择机制“假接入”或静默禁用后宣称全卡支持。
- 不将旧 MLP checkpoint 伪装成新策略的可恢复 checkpoint。

## 3. 最终架构

```text
规范公开观测：牌/敌人/药水/遗物/玩家/阶段/公开效果上下文
                              ↓
                   类型投影 + 共享 Set Transformer
                              ↓
                   上下文化实体表示 H=[h₁,...,hₙ]
                              │
                ┌─────────────┴──────────────┐
                │                            │
     任务 Query → 当前来源实体             PMA(H) → g
                ↓                            │
     具体牌/药水/选牌对象的 logits      ┌─────┴──────┐
                │                     │            │
                └────加入特殊动作 logits       Critic V(s)
                              ↓
                第一阶段统一 masked softmax
                              ↓
                     采样来源操作 u
                              ↓
             需要敌人目标？ ── 否 → 目标项为常数0
                    │是
          所选 h_source → Q；敌人表示 → K
                    ↓
             条件目标 masked softmax
                    ↓
                采样目标 j
                    ↓
          编码完整动作 a，调用一次 env.step(a)
```

每个决策的两个阶段复用同一份 `H`。为了计算精确熵，可以从该 `H` 批量计算所有合法来源的目标 logits；这不增加环境步骤，也不意味着回到全局联合 logits 评分。

### 3.1 表示完整性

`h_i(s)` 必须是上下文化实体，不是孤立的卡 ID embedding。全局状态、当前决策阶段和必要的公开效果来源必须有路径影响候选表示和 PMA。复用已存在的全局/阶段 token 或已有编码路径，不能一边删除上下文路径，一边假设 task Query 自己知道场面。

同一副牌的多个副本保留多个实体；动作引用的是具体副本。语义相同不等于可以自动合并概率或删除重复候选。

不加表示数组位置的绝对位置编码。不使用 seed、隐藏牌序、RNG、未来意图或内部实例编号作为神经网络语义特征。允许在纯路由层保留不进入网络的引用/映射，以便正确执行动作。

当已有公开关系、目标伤害预览等以 pair 特征保存时，检查它们是否已经通过允许的输入路径参与编码。不得在从旧头迁移时静默丢掉有效信息；不能把 raw slot ID 塞进向量替代关系。

## 4. 两阶段策略的数学契约

本节公式是本任务选择的设计；它们不是现成论文替本项目作出的性能保证。[S1–S4]

### 4.1 第一阶段候选和评分

第一阶段一个候选记为 `u=(operation_kind, source_ref)`；特殊动作采用独立的 `special_kind`。例如：

```text
PLAY_CARD(card_A)
PLAY_CARD(card_B)
USE_POTION(potion_P)
END_TURN
```

需要两个敌人目标的 card_A 在第一阶段仍然只有一个来源候选，不复制两次。

任务 Query 参数：

\[
q_r\in\mathbb R^d,\quad r\in\{\text{play, use_potion, exhaust_select, discard_select, retrieve_select, ...}\}.
\]

普通实体来源评分：

\[
b_u=\frac{q_{r(u)}^\top W_K^{\mathrm{entity}}h_{i(u)}(s)}{\sqrt d}.
\]

`q_r` 是共享于同类操作、可学习的参数；`h_i(s)` 随状态变化。不同操作类别的 logits 汇入同一个列表后归一化，不能各自 softmax 后直接拼起来，也不新增“先决定卡牌还是药水”的额外阶段。

特殊动作评分与价值：

\[
g=\operatorname{PMA}(H),\quad b_{\mathrm{special},k}=w_k^\top g+\beta_k,
\quad V(s)=\operatorname{MLP}_V(g).
\]

第一阶段概率：

\[
p_1(u\mid s)=\operatorname{maskedSoftmax}_{\mathcal U(s)}(b)_u.
\]

特殊动作仅在环境明确提供为合法候选时出现。不能为了方便，在目标选择或耗尽阶段凭空开放结束回合。

### 4.2 第二阶段：选中来源后，选择它的合法敌人目标

\[
q_u^{\mathrm{src}}=W_Q^{\mathrm{src}}h_{i(u)}(s),\qquad
k_j^{\mathrm{enemy}}=W_K^{\mathrm{enemy}}h_j(s).
\]

\[
t_{uj}=\frac{(q_u^{\mathrm{src}})^\top k_j^{\mathrm{enemy}}}{\sqrt d},
\qquad
p_2(j\mid s,u)=\operatorname{maskedSoftmax}_{\mathcal T(s,u)}(t_{u,:})_j.
\]

必须使用当前选定来源 `u` 的合法目标 mask，不能使用独立于来源的“所有存活敌人”mask 代替。攻击、对敌技能、对敌药水统一为来源—敌人评分。

不乘 V，不把编码器内部某一层注意力权重直接拿来当动作概率。

无目标操作，或仅有唯一目标的条件分布：概率为 1，目标 log probability 为 0，目标熵为 0。唯一目标分布的策略梯度可以为零，这是正常数学结果，不是漏接梯度。

### 4.3 完整概率、log probability 和 PPO ratio

\[
\pi(a\mid s)=p_1(u\mid s)p_2(j\mid s,u).
\]

\[
\ell(a\mid s)=\log p_1(u\mid s)+\log p_2(j\mid s,u).
\]

\[
\rho=\exp(\ell_{\mathrm{new}}-\ell_{\mathrm{old}}).
\]

PPO 只对这个联合 ratio 做一次 clipping。[S1]

\[
L_\pi=-\operatorname{mean}\{\min(\rho\hat A,\operatorname{clip}(\rho,1-\epsilon,1+\epsilon)\hat A)\}.
\]

严禁：分别 clipping 来源与目标；把两个阶段的 log probability 取平均；只保存目标概率；更新时重新抽来源；使用出牌后的观测；把内部来源选择记成 reward=0 的一条 transition。

### 4.4 为什么不是全局 softmax(b+t)

A 路径联合 log probability 为：

\[
\ell_{u,j}=b_u-\log\sum_v e^{b_v}
+t_{uj}-\log\sum_{k\in\mathcal T(s,u)}e^{t_{uk}}.
\]

最后一项是**该来源自己的条件归一化项**。丢掉它，再对 `b+t` 做全局 softmax，会改变第一阶段来源概率，使目标数和目标分数的行整体偏移影响来源概率。

允许把**正确计算出的联合 log probability**散射回旧完整动作编号空间，供显示、精确熵核验或兼容接口使用。这与旧的 raw `b+t` 全局归一化不同。实际训练采样仍按两个阶段执行。

### 4.5 精确联合熵：首版必须实现

\[
\mathcal H(\pi)=\mathcal H(p_1)
+\sum_{u\in\mathcal U(s)}p_1(u\mid s)\mathcal H(p_2(\cdot\mid s,u)).
\]

无目标来源的第二项为零。对全部合法来源加权；权重使用当前 `p1`，不能 detach，不能替换成旧策略权重。

不能把“历史上选中的那个来源的目标熵”无权重加上来源熵，当成精确联合熵。以原始完整联合概率枚举出的熵作为单测 oracle。自然概率链式分解即可推出此公式；Categorical 计算语义参考 [S4]。

log probability、熵和 ratio 优先 FP32；mask 为零概率的位置不能通过 `0 * (-inf)` 制造 NaN。不能先对全 false 行计算 log_softmax，再指望事后的 where 能修复反向传播。只对有合法目标的有效行计算，其他行明确走常数零分支。

### 4.6 梯度要求

未裁剪分支的梯度包含：

\[
\nabla L_\pi=-\hat A\rho\bigl(\nabla\log p_1(u\mid s)+\nabla\log p_2(j\mid s,u)\bigr).
\]

历史动作索引是常数；从编码结果 gather 出的来源向量不能 detach。目标梯度应经来源 Query、敌人 Key 回到共享编码器。PMA 经 Value loss 和合法特殊动作评分接收梯度。

梯度测试使用非退化夹具：至少两个合法来源，并给选中来源至少两个合法目标。单个候选、唯一目标、clipping 平坦区、零 Advantage、完全对称参数可能产生零梯度，不能把这些情况误判为未连通。

默认 `dropout=0`，不使用 BatchNorm。首次更新之前，相同参数/观测/候选的 `old_logp` 与 `evaluate_actions` 结果必须一致；`model.eval()` 不等于禁止梯度，`no_grad()` 才控制采样图的保留。

## 5. 合法候选、路由与现有环境适配

### 5.1 上游负责合法性，动作头负责概率

不重写游戏规则。适配层从现有合法完整动作/机器契约中得到：

```text
source_candidates
source_mask
target_required[source]
target_mask[source, enemy]
(source, target/NO_TARGET) ↔ complete_env_action
```

来源通常按 `(operation_kind, source_ref, 必要的操作模式)` 分组。如果同一实体存在不同模式，模式必须进组键，不能误合并。

需要目标的来源，只有存在至少一个合法完整目标时才进入第一阶段。来源 target mask 全 false 但仍标为合法，属于适配错误，不允许静默随机选择目标或退回结束回合。

无目标动作有且仅有一条语义路径。环境历史编码使用 target=0 时，只在最后 codec 转换；网络语义仍为 `NO_TARGET`，不是 enemy[0]。

每个合法完整动作必须有唯一分解，分解后的动作也必须全部合法。不同路径若会映射为同一个环境动作，要先做可证明的规范化或明确报错，不能忽略概率相加问题。

候选“数组位置”仅作路由，不是动作语义；重复卡牌也不能仅凭 card_id 解码。

### 5.2 已有 31/66 位接口只是适配样例

已核对远端公开环境：牌动作 `hand_slot*5+target`，结束回合 50，药水动作 `51+potion_slot*5+target`。[R4]

这些常数不得硬编码进新通用模型。Agent 使用本地现行中央契约生成适配；保留旧接口的历史回归测试。

A 路径不要求改变完整动作编号，也不要求把外部接口改成 MultiDiscrete。内部策略分解版本与外部 env action schema 可以独立版本化。

### 5.3 真实耗尽、弃牌、取牌和随机候选选择

环境真实返回新的决策状态时，沿用当阶段候选。例如 `EXHAUST_SELECT(card_i)`、`DISCARD_SELECT(card_i)`、`RETRIEVE_SELECT(discard_i)`。

这些可作为当前第一阶段的实体候选；若不需要敌人，则只使用第一阶段概率。已经存在的阶段上下文应包含合法来源区域、效果来源、已选集合、待选数量和确认条件等必要公开信息。

不能用 playable mask 替代 expend/discard/select mask。生成出来、尚不在牌堆里的选择项也要保留其真实选项引用与公开特征，不能伪装为某个手牌槽。

多选机制按本地已存在的环境契约处理，不在本轮擅自把选择序列改成集合原子动作，或反向拆分成更多 transition。本地未支持的机制列为明确缺口；完成其通用模型适配不等于完成环境机制实现。

## 6. 策略接口与一次调用的契约

推荐职责（名称可对应现有代码，不强制另造框架）：

```python
encode(observation_batch) -> EncodedState
build_distribution(encoded, candidate_batch) -> AutoregressiveDistribution
act(observation_batch, candidate_batch, rng) -> PolicyDecision
evaluate_actions(observation_batch, candidate_batch, recorded_actions) -> PolicyEvaluation
value_only(observation_batch) -> Tensor[B]
```

`PolicyDecision` 至少含：完整 env action、所选来源与目标引用/索引、联合 logp、Value。两个分项 logp、来源/目标熵等可作日志字段。

`PolicyEvaluation` 返回 `[B]` 的当前联合 logp、精确联合熵和 Value。禁止 `[B,1]` 与 `[B]` 静默广播，禁止使用 current env observation 替代保存样本。

采样伪代码：

```python
# no_grad；本次决定只编码一次。
encoded = model.encode(obs)
dist = model.build_distribution(encoded, candidates)
u = sample(dist.source_probs, source_rng)
if candidates[u].requires_enemy:
    j = sample(dist.target_probs_for(u), target_rng)
else:
    j = NO_TARGET
complete_action = codec.encode(u, j, candidates)
logp = dist.source_log_prob(u) + dist.target_log_prob_or_zero(u, j)
# 至此不得改变 env/RNG/牌堆/能量。下一行才发生一次环境操作。
next_obs, reward, terminated, truncated, info = env.step(complete_action)
```

更新伪代码：

```python
# 有梯度；动作固定，重新计算编码，不复用旧策略缓存的 embedding。
encoded = model.encode(saved_obs)
dist = model.build_distribution(encoded, saved_candidates)
u, j = codec.decode(recorded_complete_action, saved_candidates)
new_logp = dist.source_log_prob(u) + dist.target_log_prob_or_zero(u, j)
entropy = dist.exact_joint_entropy()
new_value = model.value_from_encoded(encoded)
loss = ppo_loss(new_logp, old_joint_logp, fixed_advantage,
                new_value, old_value, fixed_return_target, entropy)
```

不要仅为了迁移方便，让 `PPOAgent.decide_batch` 继续对完整动作概率执行一次 multinomial 而宣称已实现分阶段采样。完整联合概率可供兼容/测试，但正式采样应显式经过来源和条件目标两步。

## 7. PPO、轨迹与恢复：保持已有时间轴

### 7.1 不能只改网络类

核对并迁移本地与以下远端位置对应的绑定点：[R2–R5]

| 位置 | 已核对风险 | 实施要求 |
|---|---|---|
| `PPOConfig.__post_init__` | 硬性等于 minimal-v1 reward contract | 以显式 task/env factory 接入新任务；保留严格验证，不可删掉验证放行全部环境 |
| `PPOAgent` | 单个 Categorical + CPU multinomial | 接入分阶段采样、显式 RNG、联合 logp |
| `RolloutCollector` | 固定 FlattenWrapper 和三遭遇 seed 调度 | 接入新实体 batch/可信场景 sampler；旧 collector 保留可复现路径 |
| `Rollout.observations` | 固定张量直接 stack | 支持逐状态变长存储，在 minibatch collate 中 padding；不能丢实体 |
| `PPOTrainer` | 固定 MLP、初始化规则依赖 policy_head | 使用模型工厂/显式新 trainer，避免误用 MLP 初始化到 Query/PMA 参数 |
| checkpoint | 旧 MLP load/save、CPU RNG | 新模型类型/策略版本和 CUDA、采样、数据 RNG 状态明确保存 |
| next_values | 直接调用旧模型 forward | 新 `value_only` 不因终局无合法动作而失败 |

### 7.2 必须保存的轨迹信息

每条真实 transition 保存不可变观测快照、可准确恢复的候选/mask/映射、完整动作及分解、`old_joint_logp`、`old_value`、reward、terminated、truncated、episode_id、真实 step_index。

候选可原样保存，或通过确定性版本化规则从保存的公开观测重建并校验哈希。不能在 PPO 更新时询问正在另一个状态的环境来生成旧 mask。

采集时不保存计算图。保存 raw ID/公开数值/布尔 mask，不能只保存 detached embedding 来训练编码器。变长实体在 CPU 保存，训练时按 minibatch 长度进行 collate。

同一批 rollout 的 Advantage 和 `return_target = old_value + advantage` 固定。注意这里的 GAE/λ-return 训练目标，不等于用于未来 DT 的完整真实 RTG；不得混用字段。

### 7.3 终止、自举和预算

保持已有 `compute_gae` 时间轴：[R2]

\[
\delta_t=r_t+\gamma(1-terminated_t)V_{old}(s_{t+1})-V_{old}(s_t).
\]

GAE 递推不能跨 episode reset；外部截断从 reset 前的最终观测自举；真正终止不自举。buffer 切段正确使用 next_value，不伪造死亡。

内部来源/目标采样不增加 step、不消耗游戏 RNG、不推进回合、不扣能量、不提前更新牌区、不产生额外 Value 目标或外部预算消耗。

实际环境后续出现的耗尽/弃牌等真实选择仍按既有 transition 记录；不要把“每次 env.step”与“每次伤害结算”误认为永远相同。

异常、NaN、未知 schema、无合法动作错误不得转成正常战败零奖励混进训练数据。

### 7.4 RNG 和恢复

来源采样、目标采样使用显式拥有者与可保存 RNG；可用同一 Generator 按固定规则消费，也可分开保存。不得一条路径使用显式 Generator、另一条偷用未记录的全局 RNG。

CUDA/CPU generator 与采样张量设备兼容。恢复保存模型、优化器、调度、计数、数据抽样器、shuffle RNG、torch CPU/CUDA RNG、采样 RNG、环境恢复信息、源码/后端/数据指纹。

环境有可信快照就复用；否则用 scene_id + 初始化 seed + 已执行完整动作序列重放。仅保存 seed 而不保存真实初态场景身份不够。

只在完整环境决策边界保存训练检查点。GPU 位级完全重现无法保证时，单独给出同设备容差依据，不伪造逐位一致结论；CPU 确定性数学与路由测试仍须通过。

## 8. 源码改动建议与文档登记

先定位本地对应实现，有同职责模块就复用。不得先创建一堆空文件掩盖进度。

建议职责拆分：

```text
实体输入/批处理：复用或补齐现有 observation + token batching
候选路由：从公开合法动作到 SourceCandidate / target mask / codec
SetActorCritic：共享编码器 + PMA + task/source-target/special heads
AutoregressiveDistribution：sample / log_prob / exact_entropy / joint_probs
训练接入：现有 PPO math + 模型/环境/场景工厂
测试：独立数学、路由、结构、梯度、真实环境、恢复和学习诊断
```

建议新文档：

```text
docs/a-path-inventory.md
docs/a-path-model-contract.md
docs/a-path-test-report.md
docs/a-path-learning-report.md
configs/ppo-set-a-path-smoke.yaml
configs/ppo-set-a-path-learning.yaml
```

实际 Python 模块遵循本地可导入命名规范，不为文档的 kebab-case 要求破坏 Python import。

在 `docs/decisions.md` 追加本轮完整决定：A 路径；保留 PMA；两阶段归一化；联合 logp/ratio；不改奖励/计步；旧 full-candidate raw `b+t` 方案不作为实际策略。决定编号取本地下一可用值，本文不预占 D 编号。

版本至少区分：`model_architecture_id`、`policy_factorization_version`、`candidate_schema_version`、`task_query_registry_version`、`observation_schema`、`env_action_schema`、reward/termination、data_split_id。

如果环境完整动作 codec 没有改变，不需要仅因内部因子化就升级环境动作编号；但 checkpoint 和策略分布版本必须区分。不兼容加载要明确拒绝，不可凭 tensor shape 相同放行。

## 9. 初态数据：为当前训练服务，不重新开一个大项目

用户要求初态尽量来自自然对局。优先复用已审核的真实入口快照或明确标注的“真实来源、锁定规则派生初态”。PPO 轨迹由当前模型重新采集；历史真人动作不冒充 on-policy 数据。[S1]

编写时远端报告记录 99 个完整内容场景、75 个来源 run，覆盖主要在早期普通战斗；这是历史报告，不是本轮实测数量，更不是第二幕泛化证据。[R4]

Agent 对本地实际数据输出：来源数量、独立 run 数、可执行场景数、牌组/机制/遭遇/幕/进阶覆盖、排除原因与现行准入状态。

划分必须按来源 run/关联 seed/重复内容分组，不能同一 run 的不同楼层跨训练和评估。先划分再生成多 seed 轨迹；同一初态反复换 RNG 不增加构筑来源数量。现有 `eval_seeds.json` 不改，未见来源 run 的测试与“已见初态换 seed”分开报告。

工程和数值夹具可以人工构造，但只能标为 `synthetic_contract_fixture`，不可放入自然分布胜率分母或正式训练场景池。本包 JSON 属于这一类。

来源缺字段时明确排除，不删不支持的遗物、不以最终卡组代替当时卡组、不改进阶来迎合模型。训练池不足时，完成可支持切片的闭环并给出覆盖缺口，不以扩大数据库作为整个动作头任务的无限期前置。

未来的规则控制器采集、补 `.run` 前缀重建、非战斗 RL Agent 只列入后续路线，不作为本轮必须执行项。

## 10. 3060 起步配置与受限执行预算

以下为工程起点，不是已验证最优配置，也不是收敛或耗时保证。优先保持本地已验收且不冲突的设置，并记录差异。

| 项 | 无现成合格配置时的默认值 |
|---|---|
| d_model / Pointer key dim | 128 / 128 |
| 编码器 | SAB × 2；不无条件加第3层 |
| 注意力 heads / FFN | 4 / 256 |
| PMA | 1 个 learnable seed |
| dropout / 数值精度 | 0 / FP32 |
| num_envs × num_steps | 8 × 128 = 1024 条真实 transition/rollout |
| minibatch | 64，即每 rollout 16 个 minibatch |
| PPO epochs | 4 |
| learning_rate / Adam eps | 2.5e-4 / 1e-5，沿用已核对旧 PPO 起点 |
| gamma / GAE lambda | 1 / 0.95；本轮不修改 |
| clip / entropy / value 系数 | 0.2 / 0.01 / 0.5 |
| max_grad_norm | 0.5 |
| lr schedule | 沿用本地既有规则，并记录具体总预算 |

旧固定切片 MLP 对照若已有冻结契约，继续遵守。不同 observation/环境/训练步数或不同动作头的结果不能仅凭平均分就声称纯粹的“MLP vs Transformer 架构差异”。不强制把 MLP 迁移到所有新增环境。

性能要求：记录真实 token 数与候选数的 P50/P95/P99/max；按 batch 长度 padding，不能把理论最坏上界（旧报告为 7776 个牌实体）当常规 padding 长度。不截断实体，不删除长局。过长样本用长度分桶/更小 minibatch，必要时保留失败样例与明确资源限制。

分开测：环境推进、观测整理/collate、编码器、两阶段采样、PPO 更新、峰值显存/内存。8 个环境不要求 8 个进程；先复用现有执行方式，再据实测优化。

默认受限执行：

- 数值/结构/集成测试：按第 12 节执行。
- 梯度与固定样本诊断：每个既定样本集最多 2000 次小更新；只测试可拟合性，不当真人专家训练。
- 第一轮真实环境 PPO smoke：1 个初始化，总计 32768 条真实 transition。
- smoke 通过且数据/资源无阻塞后：最多 3 个独立初始化，每个累计最多 262144 条 transition。延续 smoke 时保持预先定义的同一学习率总预算；不能把 32768 步退火结束的 checkpoint 静默当作连续 262144 步训练。
- 不做大规模超参搜索。首次学习失败后允许一次有明确诊断依据的修正，额外 smoke 不超过 32768 步，另开实验 ID、披露消耗。
- 到预算时结束本轮并交报告；没有显著提升不等于工程没做，但不能写“训练成功/泛化通过”。

预算只是本轮执行上限，不是训练必须完成的步数。若本地系统资源、已有项目止损规则或数据准入形成更早边界，遵守更严格边界，保存恢复点并交付真实结果；不偷偷换硬件、奖励或初态分布。

## 11. 执行顺序与阶段出口

### M0：核验与登记

读取 AGENTS、现行 spec、decisions、当前模型/训练/codec/输入/数据/测试。记录 HEAD、dirty diff、后端和环境版本。核对 CPU/GPU/显存与实际入口。形成冲突表与最小改动映射，在 decisions 登记本次授权变更。

**出口：**`a-path-inventory.md`，不得只有计划而不继续下一阶段。发现本地已有合格实现时先验收，不重复重构。

### M1：输入和路由

在现有公开观测上建立来源候选、条件目标与完整动作双向映射；保证阶段上下文、实体重排和无目标语义完整。现有可用实体编码尽量复用。

**出口：**codec 双向测试与合法集合双向覆盖通过。

### M2：共享模型与分布

实现/迁移 Set + PMA + task Query + source-target Pointer + special head + Value；完成 sample/evaluate_actions/value_only/exact_entropy。只在这里使用必要的新模块，不引入额外 Actor cross-attention。

**出口：**数值 fixture、梯度、置换、padding 和一次编码测试通过。

### M3：PPO 与记录/恢复迁移

接通新 batch、factory、collector、历史动作重评估、联合 ratio、熵、GAE、checkpoint。旧路径回归不破坏。无目标决策和真正选择阶段必须能混合 batch。

**出口：**一次更新、reset/截断/终止和中断恢复可验证；指标有限。

### M4：真实环境集成与性能诊断

在已有准入场景上跑受限轨迹；对支持的出牌、药水、结束回合、耗尽/弃牌/取牌等建立真实机制样例。未准入机制可以用结构夹具测试接口，但不得冒充真实闭环。

**出口：**完整动作—执行—观测一致，内部目标采样不增加 env.step；报告真实吞吐和显存。

### M5：数据池与训练协议冻结

复用现有可信场景，按 run 分组 train/dev/heldout；冻结奖励/终止/场景与模型配置、训练/评测采样方式，做基线评估。heldout 在选模型/调参完成之前不用于反复诊断。

**出口：**数据与评估 manifest，可说明适用分布；不是“泛化已通过”。

### M6：受限训练与独立评估

执行第 10 节预算，记录每个初始化完整学习曲线、失败与最终 checkpoint。评估随机、现有规则、未训练新模型和训练后模型；旧 MLP 只在可公平比较的冻结切片上加入。

**出口：**学习证据与不确定性报告，不以单个最优 checkpoint 代替全部结果。

### M7：收口与用户学习说明

更新 spec/decisions/README 中与本次直接相关的事实。交出变更清单、复现命令、测试/资源/训练/数据证据、剩余缺口，以及一个真实选择样例的逐步解释。

**出口：**清楚区分“结构通过”“真实环境接通”“首次学习”“多初始化稳健”“未见构筑泛化”。不得用前者替代后者。

## 12. 验收矩阵

“测试名”是要求覆盖的语义，不要求机械使用同样文件名。Agent 应将每项映射到本地实际测试和命令。

| ID | 测试 | 必须确认 |
|---|---|---|
| T01 | 第一阶段归一化 | 牌、药水、特殊操作统一 softmax；来源数量不等于牌×敌人数量 |
| T02 | 条件分布归一化 | 每个有目标来源仅对自己的合法目标归一化 |
| T03 | 完整概率 | 枚举所有合法完整动作后总和为1，非法动作概率为0 |
| T04 | 6动作黄金样例 | 与本包 JSON 的联合概率、logp、熵和 ratio 一致 |
| T05 | 无目标 | logp_target=0、H_target=0，不读取敌人0冒充无目标 |
| T06 | 空 mask 边界 | 不允许无合法动作 live state；终局 Value-only 可运行；无NaN前后向 |
| T07 | codec round-trip | 所有合法完整动作唯一分解、原样编码；无非法扩展 |
| T08 | 候选数量不放大来源 | 增加某来源的合法目标时，不重复其第一阶段候选；在固定表示/logits下来源概率不变 |
| T09 | 目标行常数平移 | `t[u,:]+=C` 不改变 p2 或联合概率；能检出错误的全局 b+t 实现 |
| T10 | 历史动作重评估 | 同参数下 act.old_logp == evaluate_actions.logp；update不重新采样 |
| T11 | 联合 PPO clipping | 只对联合ratio裁剪；单独分项裁剪反例必须被测试捕获 |
| T12 | 精确熵 | 链式熵等于完整联合熵；权重不detach；梯度与枚举oracle一致 |
| T13 | 梯度连通 | 来源、目标、task Query、源/敌投影、编码器、PMA/Value分别在非退化样例接收期望梯度 |
| T14 | 目标条件性 | 换来源可改变目标分布；不从未选牌平均Query生成第二阶段 |
| T15 | 牌/药水换位 | 路由同步重排，完整动作分布对应重排；不是固定输出位置记忆 |
| T16 | 敌人换位/死槽 | 目标概率与执行对象正确对应，保持NO_TARGET不变 |
| T17 | PMA与Value不变性 | 输入允许的实体排列改变后，Value保持容差内一致 |
| T18 | 牌堆与生成选项 | hand/draw/discard/exhaust/选项实体按实际合法阶段正确路由 |
| T19 | padding | 增减padding不改变有效概率/Value；batch隔离；布尔mask方向测试 |
| T20 | 输入可见性 | 仅改隐藏RNG/牌序/未来信息不改变输入或策略；内部ID只用于路由 |
| T21 | 一次编码 | 单次来源+目标决策复用H；不为每个候选重复编码 |
| T22 | 一次环境调用 | 目标完成前env不推进/不消费游戏RNG；完整动作只调用一次step |
| T23 | 真正新选择阶段 | 执行后产生选择时，用新状态重新决策，不能用旧H越过已发生结算 |
| T24 | GAE边界 | 真终止、外部截断、buffer边界、reset与旧口径一致 |
| T25 | 固定训练目标 | epoch间旧logp、old_value、Advantage、return_target不变 |
| T26 | 恢复 | 保存/加载后环境、候选、RNG、下个动作与约定容差内更新一致 |
| T27 | 旧路径回归 | 老MLP/minimal/checkpoint仍可按原版本运行；不兼容新格式明确拒绝 |
| T28 | 阶段混合batch | 普通战斗/选牌/无目标/特殊动作可同批评估；shape严格[B] |
| T29 | 采样vs贪心定义 | sequential greedy与joint MAP不等价；工具和报告清楚标注 |
| T30 | 实验数据隔离 | 来源run/关联seed/重复内容不跨划分；eval_seeds哈希未改变 |
| T31 | 数值稳定性 | 非法mask、唯一目标、极端logits、混合长度下前后向均有限 |
| T32 | 实际训练闭环 | 真实初态→真实轨迹→PPO更新→评估→checkpoint可运行，不仅synthetic forward |

确定性 CPU FP32 非退化小样例默认 `atol=1e-6, rtol=1e-5`；不同设备数值差异应单独定容差并说明。可用 FP64 做数学/有限差分测试。不要把一次采样结果相等当作分布置换等变性证明。

### 12.1 评估模式必须写明

主评估采用 A 路径原策略的分阶段随机采样，使用独立评估采样 RNG。可补充分阶段贪心，但不能称其为完整联合 MAP。

例：来源概率 `[0.6,0.4]`；第一来源两个目标 `[0.51,0.49]`，第二来源无目标。分阶段贪心得到 `0.306` 的第一来源动作；完整联合最大概率动作却是第二来源的 `0.4`。本包包含此反例。

### 12.2 训练与评估报告

报告正式平均奖励、胜率、胜利条件下退出 HP、包括失败在内的 HP/结果统计、药水使用、回合/真实transition数、截断/异常/非法动作率、吞吐、显存、KL、clip fraction、熵、Value/Advantage诊断。

失败HP、截断HP、胜利HP不可不加标签混成同一指标；截断不冒充死亡，也不能只统计成功结束局来抬高胜率。

至少按来源run做关联分组统计；多seed同构筑不当作同等数量独立构筑。3个训练初始化各自列结果，不只列最好一条。区间过宽或heldout run太少时明确限制。

指标划分：

- 训练初态、新随机性：执行稳健性。
- 未见来源run初态：新构筑/资源组合泛化。
- 第二幕或新机制独立切片：只有真实覆盖才能报告；不能用第一幕早期结果外推。

随机初始化无法学习、Value误差大、策略塌缩时，优先检查输入/路由/奖励/采样/概率复算；不能未经诊断就改奖励、加层或增加几个数量级训练预算。

## 13. 常见错误清单

- 再写回 `softmax(b_source+t_target)` 作为实际策略。
- 每张攻击牌按敌人数在第一阶段重复出现，导致来源概率被目标数量隐式加权。
- 第一阶段分别对牌和药水softmax，再无门控拼接。
- 第二阶段用独立全局Query，与所选来源没有关系。
- task Query 是可学习参数，却误以为卡的 h 不需要包含当前场景信息。
- 把内部目标选择写进环境时间轴或预算。
- 把无目标动作映射成enemy0后让其目标表征影响分数。
- 只对选中来源计算熵，称为精确联合熵。
- Categorical.sample偷偷使用未保存的全局RNG。
- 采样时train mode dropout，复算时eval mode，导致未更新参数ratio就不是1。
- target来源向量detach，Actor梯度无法训练主干。
- 删除严格reward/版本检查来让旧PPO能接受public环境。
- 把旧flat张量尺寸、固定31/66、7776最坏容量硬编码为新模型输出/常规padding。
- 把人工概率fixture或高HP机制夹具当真实训练初态。
- 只改文档/不跑代码，或只测代码/声称用户已掌握原理。

## 14. 完成交付与停止条件

最终答复必须给出：当前HEAD/本地改动、实际改动文件、完成/未完成任务、实际测试命令和结果、真实训练步数/初始化/资源、数据与评估覆盖、checkpoint/日志/报告路径、剩余阻塞及复现步骤。

所有新增CLI要先实现再验证；可使用现有 `python -m pytest`、构建和检查脚本，但不得把尚未存在的命令写成已成功执行。缺C++扩展/CUDA/本地文件或权限时，说明具体阻塞，完成不依赖该资源的部分；不要用跳过测试替代通过。

遇到未知schema、无法唯一解码动作、合法集合不一致、reward/termination版本冲突、训练/评估泄漏、非有限值时立即停止受影响训练，保存最小复现。可以继续完成不受影响的测试和文档，不以“需确认”为由无限停在计划。

必须区分：

```text
代码已实现 ≠ 结构测试已通过 ≠ 真实环境闭环已通过
≠ PPO已显示学习 ≠ 多初始化稳健 ≠ 完整游戏泛化
```

任务完成不要求证明A比B或比所有动作头更优；要求严格实现本次已选A路径，并诚实呈现有限实验的效果。

## 15. 一手依据与核验位置

以下公开来源核验日期均为 2026-09-13。算法公式之外的本轮实现约束来自用户在本次对话中的裁定；没有把这些裁定包装成论文结论。

### 仓库证据（固定在编写时可见的提交）

- [R1] HEAD 与工作区规则：`https://github.com/Sunsh1neY/sts1-SetTransformer-PPO/blob/0d68033d2b2fb7a042d33343b863af7c3e818967/AGENTS.md`
- [R2] PPOConfig、GAE、PPO loss、Agent：`https://github.com/Sunsh1neY/sts1-SetTransformer-PPO/blob/0d68033d2b2fb7a042d33343b863af7c3e818967/sts/train/ppo.py`，已读取源码1–465行。
- [R3] 同文件的 RolloutCollector、PPOTrainer、恢复：源码231–465行。
- [R4] public 环境、场景和既有工程边界：`https://github.com/Sunsh1neY/sts1-SetTransformer-PPO/blob/0d68033d2b2fb7a042d33343b863af7c3e818967/docs/public-battle-implementation.md`
- [R5] 固定形状 MLP 输入和数值缩放：`https://github.com/Sunsh1neY/sts1-SetTransformer-PPO/blob/0d68033d2b2fb7a042d33343b863af7c3e818967/sts/models/mlp.py`，已读取源码1–235行。

以上是历史快照定位，不约束本地必须回到这些行号或旧实现。

### 算法与实现参考

- [S1] OpenAI Spinning Up，PPO：`https://spinningup.openai.com/en/latest/algorithms/ppo.html`。用于核对完整策略概率比、clip语义、Value与on-policy流程。
- [S2] Lee 等，Set Transformer，ICML 2019：`https://proceedings.mlr.press/v97/lee19d.html`。用于集合交互编码/聚合的背景；不证明本项目某个深度更优。
- [S3] Huang 与 Ontañón，Invalid Action Masking：`https://arxiv.org/html/2006.14171v3`。用于非法动作掩码与策略梯度的兼容性。
- [S4] PyTorch `torch.distributions` 文档：`https://docs.pytorch.org/docs/stable/distributions.html`。安装版本以用户本地环境为准；Agent先核对API，不因网页版本较新而擅自升级依赖。

联合熵分解、目标行平移不变性、联合概率与顺序贪心反例均由本文定义的概率分解直接推导；本包独立脚本提供数值检查，不能替代项目集成测试。
