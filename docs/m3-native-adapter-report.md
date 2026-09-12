# M3 独立原生适配器实施记录

日期：2026-09-12。当前状态：新增C++实现已交主agent接线构建；尚未以编译或行为结果宣称验收。旧IroncladBattleEnv未修改。

## 新增接口

`third_party/sts_lightspeed/bindings/public-battle-env.h/.cpp`提供`sts::registerPublicBattleEnv(module)`；类`PublicBattleEnv(max_actions=512)`有`reset_scene(scene_json, seed)`、`step(action)`、`observation()`、`action_mask()`。前三个结果为JSON文本，mask为66位布尔列表。JSON契约由root生成的`public-contract-config.h`集中限定容量与实体白名单。

reset只接受入口A及明确的before_destination_room_entry阶段。保留原进阶、完整卡组升级、HP/maxHP/gold、8类开场遗物白名单、15类直接药水及14普通/3精英遭遇。精英必须显式`burning_elite=false`；燃烧强化仍拒绝而不默认为没有。卡牌35类＋5辅助类；TrueGrit升级、未知实体、药水二次选择整场拒绝。

GameContext构造后替换完整deck/relic/potion状态，调用一次BattleContext.init。当前8类遗物无额外目的普通/精英房间入口效果，其开战效果由BattleContext处理。坐标隔离防止随机生成地图上的燃烧精英标记偶然污染请求场景。

## 观测

schema=`public-observation-v1`。手牌保留环境顺序，其余三牌区逐实体保留并按公开JSON字段排序；不含uniqueId/RNG/真实抽牌顺序。非手牌`cost_known=false`，cost0只是缺失占位。5个敌人保持后端索引；3药水行中A11以上实际容量2。statuses使用具名字典；玩家NO_DRAW和ENTANGLED导出布尔1，其他可达powers导出当前数量。怪物CurlUp/Ritual/SporeCloud/Thievery/Enrage/Angry/Asleep等单独导出。

卡行的`damage_by_target`为每段公开状态下的预览，`hits`另乘；`block`是应用Dexterity/Frail后的即时格挡，Entrench表示直接增加当前block。`magic`按卡牌语义解释：例如Bash易伤回合数、PommelStrike抽牌数、HeavyBlade总力量倍率。它不是通用可比较数值。所有字段来自锁定后端规则适配，尚需行为验证。

修订：添加`enemies[].public_history`，只以每次结束回合前已公开的敌人名字/意图和完成后仍存活同一实体构造；包括上一/上上意图、已观察敌人行动轮数、巫师蓄力轮数、睡眠轮数。分裂新实体不继承旧历史；不读取miscInfo或未来随机值。玩家另给当前回合已打卡/攻击/技能数。`turn`为后端0起始回合索引，不冒称原记录turn1。玩家Strength/Dexterity的runtime getter保留负值；敌方Strength不设置statusBits，已改为直接读取具名strength数值，避免漏掉正负力量。模糊`Bash+`和全部辅助类/TrueGrit升级入口均拒绝。

意图类别：NONE、ATTACK、ATTACK_DEFEND、DEFEND_BUFF、BUFF、DEBUFF、ATTACK_DEBUFF、DEFEND、ESCAPE、UNKNOWN、SLEEP；不会把后端move枚举或隐藏历史直接输出。

## 容量与外部截断

max_actions仅允许1..512。主牌组≤96；这组白名单无复制/自动打牌/生成药水。单玩家出牌最多新增2张，结束回合保守按5敌各最多3张计15。因此nextUniqueCardId≤96+512×15=7776，小于int16正边界32767；编译期断言总界，决策点检查实际累计生成量。初始状态不生成新卡类别实体。牌堆使用vector，要求构建未启用`sts_card_manager_use_fixed_list`宏。

外部预算在执行完第N个真实动作后截断；仍导出完整语义观测以及原MDP合法动作供价值自举，step拒绝继续执行已截断实例。该预算不作为任务失败或模型输入；模型固定张量容量策略仍由root实现，不能事后丢牌。

## 奖励与边界

仅新适配器在后端胜利后执行一次当前支持的BurningBlood治疗，再以真实退出HP/maxHP计算battle_reward_v1。没有调用会继续完整run控制流的exitBattle，没有改写旧奖励记录。FruitJuice会修改最大HP，退出分母读取实时值。敌人逃跑采用后端战斗outcome，必须另加Looter逃跑诊断，不据此宣称与击杀完全相同。

## 待独立验收

1. 编译、全真实候选重置与随机合法动作运行；把任何未映射意图/power/队列显式异常销账。
2. 35类基础/升级卡、5辅助类、8遗物、15药水的机制和数值回归，尤其AoE预览、HeavyBlade、Entrench、Artifact/临时属性、BurningBlood/血瓶/FruitJuice。
3. 14普通遭遇最大索引/分裂与3精英诊断；RedSlaverEntangle等原后端已知疑点不能因接口可跑就关闭。
4. 完整观测不泄露隐藏牌序；外部截断final observation可编码且不被当成失败。

本记录不是M3/M4完成报告，后续编译/行为结果由实际输出追加。

## Seeing Red消耗缺项定点修复

主审实际卡牌测试复现：基础/升级SeeingRed能量增加正确，但没有进入exhaust。追查发现CardInstance.doesExhaust委托`include/constants/Cards.h`的doesCardExhaust，后者缺SEEING_RED分支。正版定点javap证据保存于`reference/implementation-contract/seeing-red-javap.txt`：构造字节码33–35把exhaust设true；upgrade字节码7–13只改名字和基础费用到0，不移除消耗。

最小修复仅在Cards.h的无条件消耗分支新增SEEING_RED。没有在adapter补牌或绕开消耗触发链。35类的其余静态消耗标记为Pummel/Impervious；辅助Slimed也消耗。虚无标记Carnage/GhostlyArmor基础与升级均保留，AscendersBane/Dazed也为虚无；虚无不等于打出时消耗。

新增`tests/test_public_card_flags.py`：验证上述虚无的实际回合末牌堆变化、Pummel/Impervious/Slimed实际自消耗、SeeingRed基础与升级的FeelNoPain触发，以及普通Defend不错误触发消耗。测试等待包含Cards.h修复的最终重建，不提前报告通过。
