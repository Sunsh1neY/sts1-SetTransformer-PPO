> 2026-09-13最终收尾：CARD仍115维，统一接口v4/模型v4。同一公开结算上下文进入动作头与价值头；价值端按有效候选均值汇总，空候选取零。B05真实路径证明字段来源，尚无完整输入碰撞证明。+100保留资源异常，不作为升级终点。最终证据以docs/card-token-final-review.md为准，下面较早阶段数字保留历史身份。

# 75类战士卡牌工程验收

2026-09-13（跨日完成）。范围为STS1 Ironclad的75类、150个基础/升级版本，另含当前五类辅助牌；只针对当前五遭遇、A20、现有遗物/药水的battle开发环境。不是任意真实卡组、所有敌人、全无色牌或完整run验收。

## 2026-09-13合并前修复复核

- B01已修：消耗堆实例在回合边界复用现有`costForTurn`恢复规则；同回合取回仍为临时0费，跨回合取回恢复原实例费用，支付、合法mask和token一致。
- B02已修：Havoc自动顶牌不可执行时，带`exhaustOnUse`的实例进入既有耗尽触发链；Wound、Dazed、Burn、AscendersBane和条件不满足Clash的牌区多重集不再静默丢失。未将mask改成结算替代，也未把内部错误伪装成战斗失败。
- B03按用户裁定处理：+100仍可构造并按原公式编码；`canUpgrade`不再把+100交给Armaments再次升级。+100之后直接越界仍是已知工程资源边界，不是本轮合并阻塞或被擅自改写的正版规则终点。
- B04已修：先判X费用，再将负费用不可主动打出牌归为`UNPLAYABLE`；CARD 115维布局不变，非手牌`pay_cost=0`为类别占位。
- B05已核验并最小补充：普通CARD token未改变；SELECT_CARD额外提供公开`resolution_context`，只含来源模式、来源强制耗尽和待重复选择数量，并以候选上下文进入动作评分器。未导出完整队列、内部ID、RNG或隐藏牌序。接口/模型版本因此升级，旧checkpoint不作精确恢复。

## 接入与修复

- 共享输入v3/Set-v2：115维卡牌、全实体注意力、候选实体路由，移除目标伤害预览、保留后端格挡；非手牌按印刷费用展示，临时恢复费用作为公开实例属性保留。
- 六类单选：Armaments、Dual Wield、EXHAUST_ONE、Exhume、Headbutt、Warcry；Burning Pact复用EXHAUST_ONE。零/单候选由已有游戏机制自动处理；Armaments+全手牌升级不制造选择。候选后端索引与排序后的公开实体严格分离。
- Headbutt/Warcry公开置顶只记一张，抽走或随机插牌/洗牌后清除，不读隐藏牌序。Havoc自动打出True Grit+可继续暂停选择。
- 关闭已发现差异：Brutality未触发Rupture；Armaments+错误升级状态牌；Disarm升级仍减2；Iron Wave格挡重复修饰；Fiend Fire随机耗尽会错误选择抽到的新牌；指定耗尽helper错误使用旧索引；Combust仍活动时无牌提前判败；Searing Blow初始多次升级遗漏misc计数。
- Searing Blow支持+0至+100（伤害12至5362），测试+0/+1/+2/+5/+100，超限明确拒绝；不承诺无限升级。Rampage增伤和Double Tap、复制的其他组合按测试矩阵，非全组合穷尽。
- Infernal Blade复用原28张攻击生成池，没有缩池；池来源为锁定后端CardPools.h::CombatTypeCardPool。所有池内卡均已准入；具体可达性测试见tests/test_ironclad_final_cards.py。

## 资源与奖励契约

统一实体采集不再因达到466张而截断，也不再假设每decision最多生成15张。保留总512实体/注意力预算、当前96张入口准入、128/512等显式动作预算和完整观测处理；卡牌实例分配在32766前检查，动作队列50项、卡牌队列10项在写入前检查。队列和结算资源超限抛异常，不打印隐藏seed、不伪装战败。力量/格挡超过1000000视为数值资源异常，防止连乘后溢出；这是实现边界而非正版数值上限。

旧卡牌Set的历史collector仍保留旧生成证明，完整全卡主线使用UnifiedEntityCollectionEnv。新增机制以后应继续审查队列/数值边界，不能把当前验收解释为任意长度连锁无限安全。

奖励保持battle_reward_v1、gamma1、beta0；Feed仅按实际结算改变HP/maxHP，不额外加分。长期养成收益仍列为未来Decision Agent/Run任务奖励待修改项，必须独立奖励版本与数据契约。

## 验收记录

分批证据：tests/test_ironclad_direct.py、test_ironclad_direct_chain.py、test_ironclad_powers.py、test_ironclad_selection_cards.py、test_ironclad_final_cards.py及原白名单回归。150条逐版本准入和证据路径见sts/env/ironclad-expansion-coverage.json。

可直接审阅的75行表见[全卡完成表](ironclad-full-card-coverage.md)。当前源码和后端二进制将随最终提交打包为runs/all-ironclad-20260913-final/source-and-backend.zip，并记录逐文件SHA256清单；Python环境、被忽略的正版仲裁资料及历史语料不包含在包内，不能把该包称作全依赖安装包。

首次全版本受控集成：150版本×随机/规则两策略，300局、6665transition、66次真实选牌，全部自然结束，0截断、0异常；报告runs/all-ironclad-20260912/integration-1.json。该版本之后还添加数值资源保护，最终复测与checkpoint结果记于实施日志。

最终二进制复测：全仓938 passed in 33.66s。全版本300局仍为6665transition、66次选择；另有10种具名组合×5遭遇共50局、1232transition、59次选择。两项合计350局全部自然终止、0截断、0异常；最终报告分别为runs/all-ironclad-20260913-final/integration.json与combinations.json。

全卡输入模型诊断：64transition，5片段，7次选择；大场景包含全部75类牌，最多103实体，动态batch64×103；1自然终止、4预算截断；参数119602。PPO反向有限，保存并恢复后下一次动作采样、loss与参数更新一致。报告及update-1.pt位于runs/all-ironclad-20260913-final/model；3.197秒为工程诊断用时，不是正式训练成绩。容量/奖励/schema冻结检查与后端补丁反向校验通过。

这不是胜率提升或正式训练结果；300局不穷尽卡牌组合。最终模型恢复只验CPU/FP32无活动环境更新边界，不宣称恢复活动战斗、隐藏队列、跨机器或GPU位级一致。旧四组MLP/Set和U4/U6诊断均保留历史身份，不能直接恢复为本次后端。

## 交付后的剩余范围

其他任务新增敌人/药水合并后，需要重新对拍Feed资格、复活/逃跑、飞行与多段、随机改费、药水生成/选择及相关容量。正式扩展训练场景分布、正式训练预算、泛化与长期收益评价都未由本次工程验收代替。
