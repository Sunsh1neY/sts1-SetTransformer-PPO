> 2026-09-13最终收尾：CARD仍115维，统一接口v4/模型v4。同一公开结算上下文进入动作头与价值头；价值端按有效候选均值汇总，空候选取零。B05真实路径证明字段来源，尚无完整输入碰撞证明。+100保留资源异常，不作为升级终点。最终证据以docs/card-token-final-review.md为准，下面较早阶段数字保留历史身份。

# 统一实体输入v3实施契约

2026-09-13修订：CARD 115维布局保持不变；统一实体接口升级为`unified-entity-interface-v4`，模型为`unified-entity-set-v3`。历史实验和checkpoint保持原身份，旧checkpoint因代码/输入/动作评分契约指纹变化拒绝精确恢复。

- 模型仍为2层/64宽/4头/FF128、无位置编码。删除伤害关系bias与动作头伤害关系输入；动作头保留源、目标、池化上下文、动作类别、引用有效位及独立候选`resolution_context`。
- `resolution_context`只在真实SELECT_CARD暂停出现，不进入普通CARD token。当前字段为`source_mode`（MANUAL/AUTOPLAY/REPLAY）、`source_will_exhaust`和`pending_replay_count`；它们由已经发生的公开队列语义汇总而来，供候选动作评分器使用，不导出队列条目、内部ID、RNG或隐藏牌序。候选上下文归一化为3位来源one-hot、1位耗尽标记和1位数量/4，不改变CARD 115维。
- 费用：pay_cost在手牌为当前支付费用，非手牌为卡牌原始印刷费用（按卡名/升级获取）。这是一项用户指定的展示约定，不在本报告声称已完成正版显示行为对拍。base_cost保留实例战斗基础费用；recovery_cost保留一次免费影响前的本回合费用。当前旧观测仅手牌公开本回合费用，非手牌恢复值回退到公开base_cost；未来临时改费牌必须显式导出公开recovery_cost才能准入，不得用回退冒充完整记忆。X/不可打出类别的pay_cost置0作非数值占位，类别区分含义；X实际消耗、攻击次数、自动打出快照由环境处理，不增加策略动作。
- 删除模型中的cost_known/effective_cost_known、printed_cost独立列、effective_cost独立列、cost_scope。保留free_to_play_once与上述恢复信息。不引入通用多效果编码。
- 保留damage、combat_damage_bonus（damage已经包含该增量，不能再次相加）、base_block、后端block预览；保留公开玩家/敌人状态。伤害预览仍可存在于兼容环境原始行，但不可进入新模型tensor或评分。
- 增加known_top布尔字段，只有公开确定的抽牌堆第一张为true；其他false。连续置顶清除旧标记，抽走/洗牌/不确定变化清除，不恢复第二张记忆。当前准入范围无主动置顶卡，默认全false；跨区选牌动作保持后续工作。不得读取隐藏牌序。
- 取消统一实体采集的466张主动截断；保留512总实体和注意力内存保护、当前后端入口上限、累计编号及每decision生成检查。资源越界报错不伪造战败；过大批次可拆分。新内容必须检查实际后端保护，不能把Set动态输入当成后端无限容量。
- 随机目标/自动耗尽/自动打出由环境推进，只有真实玩家选择才暂停。奖励继续battle_reward_v1，无Feed额外奖励。

## 待修改奖励约束

未来决策Agent/完整流程应重新设计长期最大HP与养成收益评价；当前战斗奖励可能不能体现Feed等牌的长期价值。这是明确待办，不在本轮加奖励或改gamma/RTG；后续必须新奖励版本、独立数据/评估，禁止混用既有轨迹。

## 验收与迁移

必须验证费用差异、非手牌原始费用、X类别、顶牌标记合法性、公开结算上下文进入候选评分且不进入CARD token、伤害预览改变不影响模型、实体置换/候选路由、格挡保留、超过旧466阈值无牌数截断、资源异常、前向反向与严格恢复。旧checkpoint因结构与指纹改变拒绝加载；不声称全卡/完整活动环境恢复，不启动正式长训。

## 当前字段与跨任务接入

115维顺序：0–9为upgrade_count、base_cost、damage、block、base_block、magic、hits、combat_damage_bonus、pay_cost、recovery_cost；10–17为all_enemies、ethereal、exhaust、free_to_play_once、retain、is_strike、effective_exhaust、known_top；18–98身份one-hot；99–103卡类型；104–105目标类别；106–108费用类别；109–114牌区。逐维尺度见card-token-dimensions.md。

兼容适配器仍接收旧环境完整卡牌行；不把旧行中的伤害预览、费用已知位及scope编码进新模型。可额外提供公开的recovery_cost与known_top；这两项目前为共享输入扩展点，尚不代表跨区选牌机制已经准入。known_top仅允许抽牌堆一个实体为true；缺省false。当前已准入牌均无主动置顶，所以真实环境缺省false正确；新增机制负责公开置顶事件和标记清除，并补真实行为测试。

关系容器edges保留零宽末维(N,N,0)，仅兼容实体置换数据结构，不分配伤害关系内容，模型完全不读取它。源/目标引用与普通66位环境动作、SELECT_CARD路由不变。collate_chunks提供按注意力预算拆批接口；现有短诊断使用的小批次可继续collate，尚无正式大型PPO管线自动拆批验收。

## 本轮实施验证

- 输入/模型/采集/恢复针对性26项通过；新增费用、X类别、顶牌和拆批4项通过。
- 16 transition短诊断：2个片段、1次真实选择、最多103实体、批次16×103、119602参数；更新边界保存后下一次更新一致。0自然终止、2外部截断，不是胜率或学习效果评估。
- 诊断文件：runs/unified-entity-v3-20260912/report.json与update-1.pt，均为本地忽略产物；旧U4归档保持不变。
- 后端未修改；当前96张入口范围及每decision15张生成保护仍保留，前者是现采集准入范围，后者绑定当前80版本。取消的是途中466张正常截断。512实体和注意力保护仍可明确拒绝资源超限，不伪装成终局。
