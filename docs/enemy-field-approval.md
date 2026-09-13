# 敌人续批字段审批包

日期：2026-09-13。提交人：R。状态：**待用户批准**。

本文只申请字段语义、公开性边界、更新时间和共享接口影响，不批准实现、白名单准入或正式训练。批准前可以继续查源、构造不改生产接口的诊断夹具、修复与字段无关的测试；不能改变生产 schema、状态词表、region 词表、候选协议或模型输入。

## 共同约束

- 继续使用 `battle_reward_v1`、γ=1、`alpha_hp=0.5`、β=0；金币、诅咒、掉落和逃跑不进入奖励。
- 敌人三位置意图仍是当前/前次设置/再前次设置；不是已执行历史，不导出隐藏 RNG、`miscInfo`、内部实例号或未来随机序列。
- 槽位和实例引用只用于路由。模型读取语义特征；同槽同名的新实例不能继承旧引用。
- `present` 表示实体仍属于当前战斗，`targetable` 单独表示当前是否可作为合法目标。倒地待复活实体若仍属于战斗，保留实体记录但把 `targetable=false`；彻底死亡或逃跑才移除。
- 当前 22 个遭遇没有可用的正式运行观测样例，因为 reset 仍被白名单拒绝。下文把“当前例子”分为已有 v3 观测结构、锁定后端静态路径和 `[待运行]`，不把静态路径写成机制通过。

## A 组：飞行、几何体、无实体和双 Boss

### A-1：Flight

涉及：`THREE_BYRDS`、`CHOSEN_AND_BYRDS`。

当前结构例子是 `enemy` 已有 `name/hp/max_hp/block/intent_kind/intent_damage/intent_hits/statuses`；本分支没有运行两种异鸟遭遇，生产 `monsterStatuses` 也没有导出 `Flight`。锁定后端的 `Monster::preBattleAction` 对 `BYRD` 设置 `MS::FLIGHT`，这只是实现线索，异鸟公开图标、初值、按攻击段数的减少、坠落和重飞时点仍需一手来源及实战核验。

拟议字段：复用现有 `enemy.statuses` 容器，增加已核验的 `Flight: int` 语义；值为当前公开层数，层数为零时清空该键。不增加飞行减伤倍率、隐藏阶段或未来意图字段。攻击结算每个公开观察点之后更新；坠落后清空，重新飞行并完成后重新写入。`targetable` 仍独立由合法动作决定。

已有输入能否表达：`intent_damage/hits` 不能表达飞行层数和坠落时点；单靠 `targetable` 也不能区分可选性和飞行状态。共享 v4 已有 `Flight` 状态词表，因此若公开性核验通过，预计是状态值的生产接入，不新增词表取值，但会改变 ENEMY 实际输入内容并触发新指纹。

最小替代方案：在不把飞行作为正式观测的情况下拒绝两种异鸟遭遇；不把减伤倍率或 `targetable=false` 当作替代。推荐批准“现有 statuses 容器 + 数值 Flight + 独立 targetable”。

### A-2：Slow 与大脑袋倒计时

涉及：`GIANT_HEAD`。

当前 `turn`、当前意图和伤害预览已有；22 遭遇未运行。锁定后端 `GIANT_HEAD` 初始化存在 `MS::SLOW` 路径，但生产导出未写该状态；正版 `count` 初值、A18 开战减一、固定回合阈值和伤害公式仍是定点复核项。

拟议字段：复用 `enemy.statuses["Slow"]: int`，只表示玩家当前可见的 Slow 层数。每次造成会改变该层数的公开结算完成后更新；按来源确认的清除点清空。不增加 `growth`、阈值预测或“下一次伤害”字段；全局 `turn` 继续是唯一回合输入。

已有输入能否表达：`turn` 可以帮助模型使用当前回合，但不能恢复一个独立可见的 Slow 状态及其清空时点。共享 v4 已有 `Slow` 词表。推荐批准字段形状，同时把初值和更新时点列为 A 组机制验收前置条件；若来源不支持某一显示语义，则该键保持不导出并拒绝该遭遇。

### A-3：Intangible 与天罚的无实体时段

涉及：`NEMESIS`。

当前结构允许 `statuses` 和 `present/targetable`，但未运行天罚；生产导出没有 `Intangible`。锁定后端将天罚攻击后设置 `MS::INTANGIBLE`，后端注释也提示其计时语义需要谨慎对拍。无实体回合的公开持续时点尚未有本批运行证据。

拟议字段：复用 `enemy.statuses["Intangible"]: int`，值为当前可见持续层数；攻击后、回合边界和层数归零后按实际观察点更新或清空。它只表达敌方当前状态，不改变 `intent_damage` 的含义，不新增“隐形中不可攻击”推导字段。无实体期间实体是否保留由 `present`/生命周期规则单独处理。

已有输入能否表达：现有意图和血量不能表达 Intangible；单独使用不可选 mask 会把状态和生命周期混在一起。共享 v4 已有词表。推荐批准字段形状，但天罚只有在来源时序、无实体观测和自然终局全部通过后才能准入。

### A-4：几何体与甜圈双 Boss 的已有状态值

涉及：`THREE_SHAPES`、`FOUR_SHAPES`、`SPHERE_AND_TWO_SHAPES`、`DONU_AND_DECA`。

锁定后端静态路径显示 Spiker 使用 `THORNS`，Donu/Deca 使用 `ARTIFACT`、`STRENGTH`，A19 还会使用 `PLATED_ARMOR`；当前生产 `monsterStatuses` 没有完整导出这些状态中的全部项。Exploder 的“爆炸能力”在后端静态注释中仍标为缺口，不能预先用一个自造状态值掩盖。

拟议字段：不新增顶层字段或新的状态词表取值。只在逐项一手来源和实战确认后，把实际存在的既有 `statuses` 键值按数值/布尔语义导出：`Thorns`、`Artifact`、`Strength`、`Plated Armor` 等。每个实体独立更新；双 Boss 不合并为一个 token，也不把援护对象写入另一个实体的状态。Exploder 若需要新的公开字段，另行提交，不在本包隐含批准。

已有输入能否表达：当前意图可以表达当前招式，但不能替代可见的荆棘、人工制品或护甲层数。`present/targetable` 和每个实体独立路由已经能表达目标归属。推荐批准“只补已有词表中经来源确认的实际状态”，拒绝预先扩充整套状态词表。

## B 组：召唤、复活和稳定实例

### B-1：实体保留和稳定引用

涉及：`GREMLIN_LEADER`、`REPTOMANCER`、`THREE_DARKLINGS`、`COLLECTOR`、`AWAKENED_ONE`，并为 `AUTOMATON` 提供依赖。

当前 `EnemyPotionEntityView` 只把 `present=true且targetable=true` 的敌人放入 `enemy_entities`，而共享 v4 的 ENEMY 语义要求保留 `present`/`targetable` 两个独立字段。当前视图的 `_reference` 只在名字改变时增加 generation，因此同槽同名替换会复用旧引用；这是已定位的生命周期缺口，不以当前测试通过掩盖。

拟议字段与路由规则：

1. 共享 ENEMY 继续使用 `present: bool`、`targetable: bool`；这是已有字段的生产接入，不新增“不可选即 padding”的语义。
2. 对同槽同名替换，增加**路由专用**的单调 `generation`，不进入特征、不进入 tensor、不作为玩家可见编号。generation 由后端生命周期事件或可证明的移除/重新生成边界递增；不能由模型推断。
3. 若一个结算原子动作内发生移除并立即同槽重建，后端必须给适配器一个生命周期事件或新一代标记；仅比较当前名字不够。无法提供时拒绝该召唤/复活路径。

更新时点：每个环境 reset 开启新 epoch；召唤、复活、彻底移除、逃跑和同槽替换后立即更新路由。倒地待复活只改变 `targetable` 和公开生命状态，不清除引用；实体彻底移除才使旧引用失效。

已有输入能否表达：现有敌人 observation 有 `present/targetable`，但当前实体视图没有把二者交给共享模型，也不能保证同名替换。推荐批准上述“已有语义字段 + 路由 generation”；明确不批准把 generation 编码进实体 token。

### B-2：阶段字段

涉及：`AWAKENED_ONE`、`THREE_DARKLINGS`，并与 `CHAMP` 共享裁决。

当前没有通用 `phase` 字段。小黑倒地和复活可以由 `present=true,targetable=false` 表示一部分状态，但觉醒者复活前后同名、血量重置且后续行为不同，单靠名字和当前意图不能稳定区分阶段。

拟议方案：只为确实需要的实体增加公开 `phase` 字段，先批准最小词表：`PHASE_1`、`REVIVE_PENDING`、`PHASE_2`；`targetable` 仍独立，倒地期间使用 `REVIVE_PENDING` 而不是 padding。普通召唤物不额外携带 phase。字段在阶段转换的公开效果和清理结算完成后更新，reset 时初始化，彻底移除时随实体记录消失。

最小替代方案：暂不增加 phase，利用 `present/targetable/hp/intent/statuses`，无法区分同名复活阶段的条目继续拒绝。推荐批准按遭遇按需增加，而不是预先对所有敌人加入通用 phase；这仍会改变 ENEMY 维度或词表，需在批准后版本化。

## C 组：全卡接口、费用、Stasis 和战后变化

### C-1：异蛇费用

涉及：`SNECKO`。

当前敌人分支只有旧卡牌字段；共享 v4 已有 `effective_cost`、`effective_cost_known`、`cost_scope`、`cost_kind` 和逐实例 CARD token。拟议做法是直接复用这些共享字段：手牌使用实际当前有效费用并标记 known，牌离开手牌后按共享费用可见性规则处理；混乱状态使用现有玩家 `Confused` 状态（若来源确认其公开），不增加敌人专属费用列。

费用在抽入手牌、回合变化、打出/移区和 reset 后按真实公开时点更新；不能用随机 seed 或内部费用队列填充。推荐批准“复用共享 CARD 字段”，同时要求 C 以实际支付、回收和下一回合变化测试完成后才准入。

### C-2：铜球 Stasis 区域方案

涉及：`AUTOMATON`，依赖 B 的实体生命周期。

当前共享 regions 是 `hand/draw_pile/discard_pile/exhaust_pile/resolving/offer`。当前 NORMAL 检查拒绝非空 `resolving`；Stasis 是被敌人捕获、等待首领死亡返还的具体卡牌，直接写作 `resolving` 会把“正在结算”和“被扣押”混为一谈。

请在以下两种方案中批准一项：

| 方案 | 具体语义 | 代价与风险 |
|---|---|---|
| S-1，新增 `stasis` region | CARD 仍复用共享 region 字段；被捕获卡进入 `stasis`，返还时移入后端实际公开区域；路由保存卡牌实体引用，模型不读内部槽位 | 增加一个 region 词表取值，CARD 特征维度和共享契约/模型/checkpoint 指纹变化；需要重跑 region、生命周期、候选和恢复测试 |
| S-2，复用 `resolving` | 保持 region 词表不变，另加已批准的公开卡牌生命周期语义，例如 `captured_by_stasis=true`，并明确允许 NORMAL 下的这种 resolving 卡 | 改变现有 resolving 不为空即拒绝的约束，CARD 字段和阶段校验更复杂，容易把执行队列误当持有卡；必须重写 NORMAL 不变量和恢复边界 |

推荐 S-1。它增加契约版本成本，但语义清楚、不会关闭既有校验来掩盖状态冲突。无论选择哪项，都不增加怪物 token 的“扣牌专属字段”，不新增候选动作，不让模型代选。

### C-3：团块、时间吞噬者和战后出口

涉及：`WRITHING_MASS`、`TIME_EATER`。

团块的当前反应可以由每次动作后的 `intent_kind/damage/hits` 和已有 `Reactive/Malleable` 状态表达；不新增“下一次反应”字段。时间吞噬者的牌数使用已有玩家 `cards_played_this_turn`，强制结束由环境合法动作和结算状态表达；若 `Time Warp` 是公开状态，则复用共享已有词表，不新增计数推导列。两者都要在反应/12牌边界/半血清理完成后立即生成新 observation 和 mask。

当前缺少一个不进入怪物 token 的战后变化出口，无法仅凭敌人 observation 审计团块的永久加牌或盗贼的金币变化。拟议增加终局 `info.battle_exit`，只在战斗终止时出现，内容限定为已实际发生且可验证的 `deck_changes` 和 `gold_delta`；不进入模型输入、不改变 reward、不启动下一场战斗。若用户不批准该出口，则这些持久化效果只能记录为后端内部测试证据，相关遭遇不能取得完整环境审核通过。

## D 组：增长攻击、离场和阶段

### D-1：扎人的书与巨口

涉及：`BOOK_OF_STABBING`、`MAW`。

两者当前公开的 `intent_damage/intent_hits` 可以表示已经结算出的当前预览；全局 `turn` 是公开回合数。拟议**不增加** `growth`、`future_hits` 或队列预测字段；书生成的 Wound 和巨口的实际多段结算必须通过共享 CARD/牌堆观察及后端队列结果验证。任何常规路径发生真实容量错误，保留异常并交 R，不能用截断或伪造失败0绕过。

这项是“无需新增字段”的审批项：请批准复用已有预览和全局回合字段，但不把它理解成批准固定15张生成上界、50队列上界或极端长战斗。

### D-2：双盗贼与倏忽魔

涉及：`TWO_THIEVES`、`TRANSIENT`。

双盗贼使用现有 `intent_kind="ESCAPE"`、`present/targetable` 和实际后端金币状态；不新增逃跑原因，也不调用击杀触发。倏忽魔使用共享已有 `statuses["Fading"]: int`，每个敌方回合结算后更新，消失后移除实体并按正常 battle 终局处理；不新增临时力量推导字段，当前伤害预览必须反映已结算的实际强度。

当前生产导出没有完整 `Fading`/逃跑后的战后出口。请同时裁决 C-3 的 `info.battle_exit` 是否批准；若批准，盗贼只输出实际 `gold_delta`，倏忽魔不生成伪造掉落字段。奖励仍保持 `battle_reward_v1`。

### D-3：第一勇士阶段

涉及：`CHAMP`。

半血转换会清除减益并改变后续行为，单靠当前 HP 在转换后不能区分“尚未触发”和“已完成转换”。拟议复用 B-2 的最小公开 phase 词表，至少包含 `PHASE_1` 与 `PHASE_2`；阈值效果和清理完成后更新，reset 初始化，不能在仅检测 HP 时提前发奖励。若用户不批准 phase，则 CHAMP 保持拒绝，不能借用 `Strength` 或 `intent_kind` 偷渡阶段语义。

## 版本、文件和验收影响

| 提案 | 可能影响 | 不变内容 |
|---|---|---|
| A-1/A-2/A-3/A-4 | 生产 statuses 实际取值；共享契约/模型指纹需要重绑并重测 | 不新增奖励、动作或隐藏信息 |
| B-1 | 实体视图保留 present/token；路由 generation 为非模型字段 | 不把槽位或 generation 编码进特征 |
| B-2/D-3 | ENEMY phase 词表/维度与 checkpoint 契约 | 不改变 targetable、动作协议和奖励 |
| C-1 | 复用 CARD 费用字段，依赖全卡后端入口 | 不新增敌人费用字段、选择协议或PPO |
| C-2 | region 词表、CARD维度、模型/恢复指纹 | 不新增怪物扣牌字段或候选动作 |
| C-3/D-2 | 终局 `info.battle_exit` 结构 | 不进入模型、不启动下一场、不改变奖励 |
| D-1 | 无 schema 变化；只提高机制和资源验收要求 | 不做极端容量工程 |

请用户批准上述字段/接口方案，并明确 C-2 选择 `S-1` 或 `S-2`，以及是否批准 C-3 的 `info.battle_exit`。在得到裁决前，R 会继续维护基线、worktree、补丁、只读源审计和 22 行状态表；不会把等待当作同意。
