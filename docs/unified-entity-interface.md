# 统一实体接口：提供给敌人/药水扩展任务

日期：2026-09-12。以[架构契约](unified-entity-architecture.md)为共享实现依据。本任务负责实体编码/模型/候选接口；另一任务负责新增敌人和药水的结算、字段可见性及合法性证明。不要改写冻结的public/comparison契约来开放新内容。

## 实体记录

五种类型分别编码投影到同一宽度。字段应完整且使用公开语义；未知值要有known标记，不能把未知当0。当前适配器消费具名观测，下列记录各自对应一张token；字段/词表由统一实体契约版本固定，新增字段须更新契约和测试，未知字段立即拒绝，不静默忽略。

| 类型 | 当前语义字段 | 外部映射 |
|---|---|---|
| CARD | name/card_id/整数upgrade_count、类型、hand/draw/discard/exhaust/resolving/offer区域、印刷/战斗/有效费用及known/来源、伤害/格挡/magic/hits、耗尽/保留/以太/免费/Strike与实例成长 | 牌区位置和后台对象ID只供动作路由；damage_by_target转实体间边 |
| ENEMY | name、present/targetable、HP/maxHP/block、intent_kind/damage/hits、具名公开statuses、已有public_history | 原敌人槽位→token索引，槽位数值不编码 |
| POTION | name/potion_id、present、公开potency、target_kind | 实际药水槽→token索引；空槽省略，总容量在玩家token |
| RELIC | name/relic_id、公开counter及known | 每件一token；新计数/触发字段须显式扩schema |
| PLAYER_GLOBAL | 玩家HP/maxHP/block/energy/energy_per_turn、回合/进阶、已出牌/攻击/技能数、公开statuses、Combust失血、药水总容量、决策阶段与选择任务/数量 | 唯一玩家token，不包含敌人/药水/遗物的展平数据 |

后端内部moveHistory、miscInfo、RNG、种子、uniqueId、牌序与槽位编号不得进入任何语义字段或模型tensor。输入词表包含某个名字不代表后端已经准入该内容。

## 模型输入与候选接口

`sts.env.entities.encode_observation(obs)`计划输出EntitySample：实际token记录、公开关系边、Candidate序列及单独routes。`collate(samples)`只输出模型tensor，不携带routes或decision_id。

Candidate的source/target是当前sample内token引用，缺省为-1；这些是gather路由，不作为数值特征。每项含kind和环境提供的legal。模型输出与候选顺序一一对应；选定候选后由调用者读取sample.routes[index]回送环境。不能用模型推断legal代替环境mask。

有目标药水使用POTION_TARGET，绑定瓶子实体和真实目标ENEMY。无目标药水用POTION_SELF、target=-1。目标位变动时同步外部引用；不能把目标列当作选牌列表。

二次选择使用独立SELECT_CARD阶段：提供selection_kind、candidate_zone、完整逐实例candidates、candidate_mask、min/max_choices和当前公开来源。持有牌候选引用现有CARD，不额外复制token；新生成的offer是独立CARD、offer区域，生命周期到该选择结束。尚未实现的多选/确认、药水丢弃与替换不得借用现有动作偷偷表达，必须登记新kind及测试。

True Grit+首先验证单选。来源卡暂停时在resolving区域；后续药水若已从库存移除但仍在选择中，提供其公开的resolving来源记录并扩充适配器，不暴露整个内部队列。只有真实暂停点形成transition，强制唯一选择和内部随机目标由环境执行。

## mask、资源和版本责任

- entity_valid只标动态padding；candidate_valid标补齐候选；legal来自环境。三者不能混用。无目标动作的target=-1必须单独处理，不能误取最后一个token。
- 敌人/药水数量按实际存在记录构造；当前后端5敌/3预留药水路由仍需适配器检查，动态模型不代表后端扩容。
- 新机制影响生成/回收/自动打出/暂停时，必须重审累计ID、当前/resolving/offer实体和原子动作余量；当前80版本容量hash不能自动沿用。
- 接入需提供：新字段与可见性依据、实体与目标映射、legal来源、选择来源/数量/生命周期、异常与终止处理、内容/后端hash及真实行为测试。
- 冻结四组旧PPO不重命名，不回填为新模型成绩。新编码或机制变化都要求新的恢复契约；活动环境恢复仍须完整重放验证。
