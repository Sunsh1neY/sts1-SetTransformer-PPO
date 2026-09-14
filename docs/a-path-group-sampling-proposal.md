# A路径initial-state采样与PPO shuffle修订提案

最新授权（2026-09-14）：用户要求直接启动四小时正式训练，可跳过独立32k smoke；I4替代下文的暂停/待审核状态。中性来源组采样与全局shuffle方案保留，正式注册池为sts/env/a-path-training-pool.json。下文保留设计与数学口径。

2026-09-14，修订v2，等待用户审核。三组内容分类和逐卡组台账保留。撤销正式训练50/25/25、8环境绑定4/2/2、PPO minibatch32/16/16及最终来源50%上限；这些方案未曾用于训练。四小时正式训练、可选诊断和正式训练池冻结均未启动。

## 冻结comparison协议核查

当前是comparison完成后的Set-only新扩展，不是在重跑被冻结的MLP/Set对照。

依据：

- docs/mlp-set-comparison-boundary.md第1节冻结“先均匀抽来源run，再均匀抽组内卡组、条件、遭遇”；第4节明确对照后冻结MLP、扩展只推进Set并独立报告。
- docs/comparison-m3-training.md记录原comparison-battle-v1内容范围保留，实际运行身份因容量协议升为comparison-battle-v2。
- docs/comparison-ppo-report.md记录MLP/Set各2初始化对照已完成。
- sts/env/comparison-contract.json实际schema为comparison-battle-v2；sts/env/real_deck.py的sample_scene仍实现原run均匀采样。原数据80条训练记录/65run的协议没有改写。
- 当前A路径已更换动作参数化、扩展输入、集成后端并拟接入最终卡组，依决策I0进入新任务。不能把本轮新来源划分、初态池或结果回填旧comparison，也不能凭新Set与旧MLP分数宣称纯架构优势。

因此，新任务另设a-path-source-group-uniform-v1（仍为提案），同时保留旧comparison代码、数据、checkpoint及采样协议。若今后复跑comparison，必须切回其锁定版本与原采样协议，而不是使用本提案。

## Initial-state sampler：只按来源与可准入状态抽样

1. 先均匀抽一个独立来源关联组。当前按已知同run、关联seed及重复完整内容合并为33组，包含36个原始run；不是从42条来源记录均匀抽样。这里的独立是已知关联规则下的去相关，不保证不存在未知关联。
2. 在该来源组内均匀抽一个去重后的完整initial-state/deck模板。当前27组各1种deck、6组各2种；同deck的重复来源记录仅用于溯源，不作为额外抽样票。
3. 再均匀抽condition，然后均匀抽encounter。当前是原有2套条件、5个遭遇；正式准入后若某状态可用集合不同，必须重算机会表，不能静默把原概率套上去。
4. 每次reset从独立环境seed RNG流抽新environment seed，与来源选择RNG、动作采样RNG、PPO shuffle RNG分离。环境seed属于已登记训练空间（≥100000且排除开发/保留评估seed），不使用源run原seed，不用记录编号或连续游标代替独立抽样。记录实际seed，并检测、重抽已使用seed碰撞；每个初始化使用独立可恢复RNG流。
5. 8个环境都调用同一个sampler，每次真实结束或外部截断后的reset重新抽样，没有固定内容组绑定。组标签只用于统计，不进策略输入，也不决定采样权重。

若共有G个来源组，第g组有m_g个去重deck，则当前每个配置的概率为：

P(g, deck, condition, encounter) = 1/G × 1/m_g × 1/2 × 1/5。

一个来源记录10个不同状态，仍只拿到1/G的开局机会，各状态平分该机会；一个状态重复登记10次也不增加概率。组内多个原始run已经按关联规则合并，不再因为别名或重复run另加一层票数。

## 当前候选规模与unique initial state口径

| 指标 | 数量 | 含义 |
|---|---:|---|
| train独立source group | 33 | 已知关联规则下的来源组件 |
| 原始source run | 36 | 尚未合并身份前的run数，不作为本sampler首层单位 |
| 来源deck记录 | 42 | 包含重复内容的溯源条目 |
| unique deck | 39 | 完整卡组多重集；升级和副本全部保留 |
| unique initial configuration | 390 | 39 deck × 2 condition × 5 encounter，完整配置内容哈希去重 |
| 带来源记录的配置组合 | 420 | 42×2×5，不当作420个独立初态 |
| 运行时已正式准入initial state | 未完成验收 | 390是配置候选，不是390个已通过reset的状态或390份精确观测快照 |

环境seed不计入390，也不能通过无限换seed虚增unique state数。相同配置在不同seed下产生不同初始牌序/敌人随机性，这属于该配置的采样分布。尚未做最终卡组reset与容量验收，正式数量需验收后重新报告。

## 中性sampler下的自然比例和机会

下表全部以每1000次reset为单位，是精确概率的期望换算，不是每1000条transition，也不是实际采集结果。

| 内容组 | unique deck | 涉及source group | 自然开局概率 | 本组reset期望 | 每deck平均reset机会 | 每相关source group产生本组reset的平均机会 |
|---|---:|---:|---:|---:|---:|---:|
| simple | 10 | 9 | 13/66 = 19.6970% | 196.97 | 19.70 | 21.89 |
| transition | 8 | 8 | 7/33 = 21.2121% | 212.12 | 26.52 | 26.52 |
| compositional | 21 | 21 | 13/22 = 59.0909% | 590.91 | 28.14 | 28.14 |

无论该来源包含哪类卡组，**每个source group的总机会相同：每1000次reset约30.30次（1/33）**。上表最后一列只统计该来源机会中落入对应内容组的部分；一个来源同时有simple和compositional时，两类各分一半。涉及来源组数有重叠，9+8+21不能当作38个独立来源。

单deck机会有两个水平：单deck来源组的deck为每1000次30.30次；双deck来源组中的每deck为15.15次。simple中3种为前者、7种为后者；transition为6种/2种；compositional为18种/3种。对应单个deck+condition+encounter配置的机会再除以10。

当前最终来源占自然开局约80.3030%，这是取消人为组别先验后、当前来源结构导致的结果；不暗加最终来源上限，也不把simple补回50%。来源均匀保护的是每个来源，而不是每个内容类别。真实transition和梯度贡献比例还受策略、战斗长度、选牌次数和优势尺度影响，训练前不能由开局概率推出，需要在后续获批的预检/采集中单独测量并报告。

## PPO minibatch shuffle：与开局抽样独立

- 从8环境×128步得到本轮1024条on-policy transition后，每个PPO epoch对全部1024个索引做一次全局随机排列，再顺序切成64样本minibatch。
- 不按simple/transition/compositional做配额、分层重采样或重加权；不固定32/16/16，不保证单个minibatch的组比例，某个minibatch缺一组是允许的。
- 每个epoch无放回遍历完整rollout；全部4个epoch沿用同一批旧logp、old Value、Advantage和return目标。组标签只用于事后统计。
- 全局排列使用专用shuffle RNG并存入checkpoint。不能因组别变化重新抽历史动作。
- 如为显存拆微批次，只拆已经随机选定的逻辑minibatch，按样本数正确累积梯度；优势归一化基于完整逻辑minibatch。不得为凑长度或组别配额换掉样本、删长卡组或改变loss权重。

本轮尚未实现A路径正式collector/PPO trainer；此前固定配额仅存在提案，未部署。本次撤销的是方案与机器可读配置，不伪称已修复一个运行中的配额采集器。

## 三组仅作分层评估与诊断

逐初始化、逐组报告以下指标；开发侧内容仍为17/5/13种，类别不变。

| 指标 | 报告口径 |
|---|---|
| win rate | 自然胜负、截断和异常数量及分母分别披露；截断不得伪造失败0 |
| return | 原battle_reward_v1及相对同初始化未训练模型的配对变化；截断完整回报未知，保留区间/未定身份，不能剔除后冒称完整结果 |
| exit HP | 全部自然终止局与胜局条件均值分别报告，避免只看幸存者 |
| potion use | 每局次数、类型、条件切片；零库存条件单列 |
| truncation | 次数、比例、原因、最终观测是否完整及自举路径；异常另列 |
| entropy | 精确联合熵、来源熵、来源加权条件目标熵，附合法来源/目标数量；不把候选少导致的低熵直接解释为学习成功 |
| value diagnostics | Value均值、目标均值、偏差、MSE、explained variance；目标方差为0时EV标未定义；bootstrap截断目标与真实完整回报分开 |
| PPO diagnostics | 分组KL、clip fraction、policy/value loss、优势幅度，仅观察，不据此暗改组权重 |

固定评测库中先对条件与seed平均，再按组内独特内容等权汇总，同时另列按新sampler权重得到的辅助汇总。此评估重加权不反馈给训练sampler或PPO。三组主表保留，即使混合平均回报上涨，也不能掩盖simple退化。标签切片和三组总体均不能冒充总体玩家分布；开发组只有4/2/3个来源关联组件，跨组可能相关。

主策略使用两阶段随机采样，对照未训练同模型、完整合法动作均匀随机以及规则可表达切片。报告全部初始化，不挑最好一组；规则未覆盖新选择阶段明确标缺口。未创建未见保留集，eval_seeds.json不改。

## 可选32768 transition simple-heavy诊断

可以保留smoke/curriculum diagnostic候选，但当前不执行。若后续获批，其initial-state sampler可先按50/25/25抽内容组，再在该组按来源组及组内状态抽样；这只是reset概率，不保证transition比例。8个env不绑定组，PPO仍全局随机shuffle。

诊断使用独立实验ID、模型初始化、数据分布版本、seed、checkpoint与报告。不得将诊断收益当正式baseline结果，不得把诊断后权重或优化器静默接入正式baseline。中性baseline须从新初始化开始；若采用其自身的32768步首段，那仍属于中性sampler、计入正式初始化预算，不能与simple-heavy诊断混称。

诊断最多32768 transition不是自动执行或新增资源预算授权。诊断与正式训练的时间/步数分别记账；本轮只修订方案，二者都未启动，四小时正式预算保持暂停。

## 验证、待办和审核点

概率审计脚本audit-a-path-source-sampling.py使用有理数精确求和，枚举390个完整配置哈希；source-group总概率逐组等于1/33，所有deck和配置概率各自合计1。逐deck、逐来源及逐配置机会表见a-path-source-sampling-audit.json。propose-a-path-deck-groups.py只更新采样建议，74种内容的分类、牌组和来源台账保持不变。

当前待审核的是：Set-only新任务使用33个来源关联组均匀的baseline定义，以及initial-state采样与PPO全局shuffle的分离。正式池、准入、训练、四小时计时均未启动。审核通过后仍须先完成reset/容量准入与工程恢复闭环，按实际准入结果重新报告上述规模和比例，再进入正式训练准备。
