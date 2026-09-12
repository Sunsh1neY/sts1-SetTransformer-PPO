# M5 规则策略实施设计与观测依赖

日期：2026-09-12。性质：并行准备交付；M2 尚未通过，本文件不批准 M3/M4 或宣称 M5 完成。
依据：`spec-v6.md` §4/§6、`docs/week-5-6-plan.md`、`docs/m2-real-battle-contract.md` 与本地正式接口。

## 1. 可直接复用的接口

正式接口是 `decide(observation: Mapping[str, Any]) -> AgentDecision`，见
`sts/agents/episode_runner.py`。策略返回完整概率向量与动作编号；runner 只执行动作。
`sts/agents/random_agent.py` 的 `act(env)` 是旧教学接口，不作为新规则 Agent 的模板。

建议实现两层：

1. `RuleAgent` 校验固定的 schema/registry/action 合约并将规范观测转换为只读语义视图。
2. `score_actions(view, registry, action_layout)` 是纯函数；只根据视图与公开静态卡义评分。

核心无需 import 后端、调用环境、试走动作或克隆状态。可在 M2 完成前做独立原型，
但正式模块接入须等待最终 schema。`AgentDecision` 本身支持任意一维宽度；现行
`MaskedRandomAgent`、`decode_agent_decision` 和 MLP 推理仍硬编码 31，动作迁移要联动。
不能只让规则策略输出 66 位再交给旧 runner。

## 2. 当前接口实际有什么

| 项目 | 当前规范内容 | 结论 |
|---|---|---|
| 卡牌实例 | card_id/location/upgraded/cost/cost_known/target_kind | 只有费用动态数值；无 damage/block/magic |
| 玩家 global | HP/maxHP/block/energy/turn/四区数量/总敌HP/Strength/Vulnerable/Weak | 现有力量、易伤、虚弱已导出；Frail/Dexterity 等尚无 |
| 敌人 | ID/HP/maxHP/block/Strength/Vulnerable/Weak/intent/damage/hits/CurlUp/Ritual | 当前只有最小遭遇的意图映射 |
| 非手牌 | 无序多重集；费用未知 | 可统计牌类、剩余攻防与消耗潜力，不可预测下一张 |
| 遗物和药水 | 无规范实体 | 中等场景不能省略 |
| mask | 31 位 bool | 合法性真相；不能用策略自行推断替代 |

`bindings/bindings-util.cpp::enemyFeature` 的 `intent_damage` 已调用
`calculateDamageToPlayer`，表示当前公开状态修正后的单段伤害；`intent_hits` 单独给出
段数。策略估算当前总意图应使用 `damage × hits`，不得再次加敌方力量或乘玩家易伤。
新的导出应保留并记录这一语义；策略只读导出结果，不能调用该 C++ 方法。

现有 registry 只有 Bash/Defend/Strike 与目标类型，没有卡牌数值。最小规则策略可用
经核验的静态卡义表加现有状态估算，但这不等于支持 M1 的 35 类。

## 3. 新 schema 的确切需求

字段可以采用数组或对象，最终顺序由主审锁定；以下是必须能无歧义表达的语义。
所有策略、MLP 和 Set 输入都应从相同规范观测获得这些信息，不为规则策略另开接口。

| 对象 | 必须可表达 | 语义要求 |
|---|---|---|
| 合约 | observation/registry/action 版本和固定哈希 | 可由构造器传入并在外层验配；禁止从 scene_id 猜玩法 |
| 卡牌 | 稳定 ID、升级次数、费用及 known、目标类、实例基础 damage/block/magic 及 known | 静态值可从公开 registry 派生；Rampage/临时改值等必须逐实例表示 |
| 卡牌语义 registry | 攻击/技能/能力/状态/诅咒，段数、全体/随机目标、抽牌/能量、消耗/虚无/生成 | 每个批准类别都具评分分支；未知可行动卡不能静默当0分 |
| 玩家 | HP/maxHP/block/energy/turn/剩余任务回合、可见状态 | 状态含量及计时语义逐项固定，非任意 int[4] |
| 敌人 | HP/block/targetable、已修正单段意图伤害/hits、可见状态 | 保留原行与合法目标映射；无内部 moveID/history/miscInfo |
| 遗物 | 稳定 ID、公开 counter/active 参数 | 含任何会改变当前卡牌收益的已支持效果；不能从后端临时读取 |
| 药水 | 稳定 ID、真实槽位、公开 potency/target/选择语义 | 无目标和指定目标区分；已消耗槽位须更新 |
| mask/action layout | 固定宽度、card/potion/end 解码、目标容量 | 只枚举 mask=true，不自行添加合法动作 |

M1 35 类候选至少需要玩家 Strength、临时 Strength 回退、Dexterity/Frail（若场景内容
可产生）、NoDraw、Rage、Metallicize、DemonForm、FlameBarrier、FeelNoPain 等状态；
敌方至少要表达 Weak/Vulnerable/Artifact/Ritual/CurlUp，并按 M4 批次补 Nob 的 Enrage、
Lagavulin 的睡眠/金属化等公开效果。这里只列机制依赖，不批准未核验字段或数值。

动态伤害可以选“实例基础值 + 玩家/敌方状态，规则核心自行近似”或“公开规则计算的
每目标预览值”；若选后者，必须使该值也能由玩家可见信息确定，纳入全体策略输入，
禁止通过试走后端得到隐含未来结果。推荐前者以控制接口范围。

## 4. 可编码的第一版评分规则

以下是启发式设计参数，不是游戏机制真值或最优策略证明；权重在开发集冻结，不能
依正式 1000 seed 调整。第一版避免深搜索，执行一张牌后重新读取真实观测再评分。

对每个合法动作计算以下近似量：

- `H`：对所有目标造成的有效 HP 伤害之和，单目标不超过当前 HP；先扣当前格挡。
- `K`：可由当前公开字段确定击杀的目标数。随机目标攻击不能按最佳分配当作确定击杀。
- `A`：确定击杀移除的当前意图伤害；若效果顺序或防护状态未知，禁止声称确定。
- `B`：新增格挡可吸收的当前剩余伤害，至多 `max(0, I - player_block)`。
- `D`：抽牌收益，按可抽数量、空手牌槽和 NoDraw 限制；不知道具体会抽哪张。
- `E`：净能量收益；不能把结束回合弃掉的无用途能量永久当收益。
- `U`：能力与 debuff 的有限期启发式收益；所有权重必须有独立配置版本。
- `R`：自伤、反伤、消耗有价值手牌、制造状态牌、药水消耗机会成本等可见风险。

初始分数建议 `H + 12*K + 1.25*A + 1.1*B + 3*D + 4*E + U - R - 0.25*cost`。
`END_TURN=0`，负收益动作可低于结束回合。若一个动作能够从公开信息确定立即胜利，
在非致命自伤的前提下优先；若能确定避免本回合致死，则优先于不能避免致死的动作。
这两条优先级只适用于已覆盖的确定效果，不能把近似推算当完整模拟。

确定性版本选最高分，平分选最小合法动作号，并返回所选动作 one-hot；这样同一
规范观测会返回同一决策。以后增加 ε 噪声时，独立 agent RNG 只在合法动作上混合均匀
分布；输出概率必须与实际采样分布一致，不读取环境 RNG。

按机制注册评分分支：

| 分支 | 计算重点与边界 |
|---|---|
| 单体/多段/全体攻击 | 逐目标扣格挡；多段须考虑 CurlUp/反伤等中途触发，未覆盖时只能近似、不能错误触发确定击杀优先级 |
| Bash/Thunderclap/Uppercut/Clothesline | 先当前伤害，再评 debuff；Artifact 可吃 debuff；不把新易伤应用到此前伤害 |
| BodySlam/Entrench/HeavyBlade | 使用当前 block/Strength 和已核验倍率；不按费用估固定效果 |
| Dropkick | 读取目标打出前易伤；条件成立才加抽牌/能量收益 |
| PommelStrike/ShrugItOff/BattleTrance | 尊重 NoDraw、手牌容量、牌堆总量；BattleTrance 的后续禁抽计入机会成本 |
| Flex/Inflame/DemonForm/SpotWeakness | 力量收益按剩余手牌攻击段数与短期上界；SpotWeakness 看目标可见攻击意图；临时力量不当永久 |
| Rage/FlameBarrier/Metallicize/FeelNoPain | 只按已知本回合或有限后续潜力计值；Metallicize 不当立即格挡，FlameBarrier按敌攻击段数 |
| TrueGrit 基础版 | 随机消耗按公开手牌平均机会成本，不读将要消耗的对象；升级版未有选择动作则整场不准入 |
| Carnage/GhostlyArmor/Impervious/Pummel/SeeingRed/Sentinel | 虚无与消耗在正确阶段计入；Sentinel 普通打出不自动取得被消耗收益 |
| WildStrike/RecklessCharge/PowerThrough/Immolate | 记录生成牌数量及后续抽牌污染；不能只计算即时伤害/格挡 |
| 药水 | 使用真实 potency 与已批准语义；有用治疗至多缺失HP；不能凭药水名称猜二次选择 |

对具有复合时序、随机触发的动作，可保留保守近似分支并明确它是启发式。前提是
所有影响决策的信息已在规范观测中，且整场机制已通过 M3/M4；不要求规则策略解出
完整游戏，但不允许缺字段时假造“状态为0”。

## 5. 必须拒绝的情况

- schema/registry/action 不一致、空合法 mask、非 bool mask、容量不符、非法目标行。
- 可见动态值未知却被评分分支当成必需输入；缺失必需状态字段。
- 新牌/遗物/药水/怪物机制没有注册评分覆盖。允许明确注册“已理解但评分保守”的分支，
  不允许兜底为未知类别套固定分数。
- 多次强化只给 bool 而该卡支持重复升级；未知持续时间被假设永久或1回合。
- 需要二次选择但动作合约没有出口。整个场景应由环境准入拒绝，规则 Agent 不代选。

规则 Agent 永不访问 env/state/battle、原始 BattleScene、seed/source_run_group、
RNG counter、moveHistory、真实抽牌顺序、隐藏下个意图；也不通过 step/clone/序列化
调用窥探结果。局面编号、来源作者和数据划分不得影响动作。

## 6. 关键验收测试

1. 只传普通字典与数组，不提供 env，仍可决策；输入数组和字典前后完全不变。
2. 非法动作概率恒0，合法概率和为1，已选动作合法；只有结束回合时返回结束。
3. 隐藏数据不进入函数接口；两个完全相同规范观测来自不同 seed 时决策相同。
4. 非手牌排序变换不改变决策；手牌置换后语义选择对应迁移（平分策略另行注明）。
5. 简单确定致死攻击优先；低HP目标有格挡时不能错误判杀；双段攻击逐段防护不误算。
6. 多敌攻击时，格挡需求累计所有 `intent_damage × hits`；不重复应用力量/易伤。
7. 已有足够格挡时，不为无额外作用的 Defend 给虚假吸收收益；敌人不攻击时不盲堆格挡。
8. Dropkick 的易伤有/无、Artifact 消除 debuff、SpotWeakness 攻击/非攻击分别改变评分。
9. NoDraw 与满手阻止虚假抽牌收益；牌堆只提供集合，随机结果不影响事前分数。
10. 药水治疗封顶缺失HP，伤害药水映射正确目标；空/已用槽位没有动作概率。
11. 缺字段/未知机制/版本不符明确异常，不能当正常战败、不能悄悄退回随机。
12. M3/M4 通过后，在独立开发场景集完成规则/随机成对 smoke，0非法动作/崩溃，
    覆盖每一批准机制分支；性能差不能以删除困难场景解决。正式 Gate 属于 M6–M8。

## 7. 本轮交付边界

本轮只读检查了正式接口、wrapper、registry、意图导出和 M2 文档，未修改正式代码，
未运行训练，未执行上述尚不存在的规则行为测试。可以直接由主审在锁定契约后把
“语义视图+评分核心+测试”作为单独实现任务；不需要等待全部 M6 评估工具完成。
