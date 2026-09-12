# M2 可实施契约与完整场景闭包复审

日期：2026-09-12。独立子任务读取 AGENTS、spec-v6、decisions、M1候选、批量索引、M2真实初态契约、reset预审及锁定后端。本文为具体实施建议，未经主审登记不覆盖规格；没有构建、训练或改动旧环境。

## 完整场景筛选的实际结果

离线探针：`reference/implementation-contract/closure-probe.py`；逐场 ID 与统计：同目录 `closure-results.json`。每一层均保留整副卡组、原进阶、遗物及药水；筛选不依胜负或模型表现。

| 层级 | 场景 / 独立run | 卡牌实体类别 | 普通遭遇类别 | 最大初始牌数 | 最大遗物数 |
|---|---:|---:|---:|---:|---:|
| M1 35类＋进阶之灾的完整牌组 | 103 / 75 | 24 | 7 | 14 | 2 |
| 再要求药水无主动二次选择、无随机卡牌生成 | 99 / 75 | 23 | 6 | 14 | 2 |
| 再延期四类生成卡 | 93 / 72 | 19 | 6 | 14 | 2 |
| 再延期会生成Slimed的Small Slimes | 72 / 58 | 18 | 5 | 14 | 2 |

99场包括 Cultist27、JawWorm16、TwoLouse32、SmallSlimes22、TwoFungiBeasts1、Looter1；研究划分73/24/2。这些是闭包候选，不是已验收机制或正式实验划分。只有2场reserved-eval，不能声称中等档代表性。

该批实际药水仅 Swift Potion、HeartOfIron、Explosive Potion、FearPotion、Fruit Juice；遗物为 Burning Blood、Lantern、Blood Vial、Bronze Scales、Bag of Preparation。均需行为验收。Fruit Juice会改最大HP及奖励分母，必须测试，不能当作无作用药水。BloodPotion的分支疑点不影响此99场，因为不存在该药水。

35类虽然在候选总库覆盖29类，但完整牌组交集只留下23种Ironclad类＋进阶之灾；再限制药水后只剩22种Ironclad类。不能用“库里出现过29类”宣称完整场景覆盖29类。M3的30–40类目标需补真实前缀或审计更多兼容牌，不应把上述72/99场先行批次当作目标缩减。

## 后端容量：64不是当前实际牌堆上限

- `include/combat/CardManager.h:24`：手牌10、limbo10；draw/discard/exhaust默认vector。
- `include/sts_common.h:12` 的 `sts_card_manager_use_fixed_list` 当前注释。只有启用该宏时，三堆各受64限制；构建仍应核实没有编译参数重新定义宏。
- `include/game/Deck.h:27`：master deck使用fixed_list，硬上限96。reset须在填充前拒绝大于96。
- `include/combat/CardInstance.h:28`：uniqueId为int16；`src/combat/CardManager.cpp:97,104,119` 创建临时牌时窄化nextUniqueCardId。vector不等于无限安全，必须在溢出前停机或统一迁移所有相关ID类型。
- limbo是结束回合临时保留区（BattleContext.cpp约2470–2573）。它不能固定当作另一个额外10张永久区重复计数。只在队列静止决策点导出；未结束的队列不能伪装正常obs。
- 生成卡可以反复打出；敌人也可以反复产生Slimed/Dazed。50回合不能单独限制同回合零费循环次数。没有动作预算或实体资源停止条件时不存在已证明有限总牌量。

建议语义层直接保留变长牌堆。模型固定张量若容量不足，不能删掉后才置truncated：此时最后观测已经不可表示，无法正确自举。可选可实施路径：动态pad至实际批次最大长度；或基于该批已核实的单步最大生成量，在下一动作执行前预留容量，外部停止在最后完整可编码的观测。后者必须保存外部停止原因与原观测，并避免制造一个未执行动作的假transition。初始scene超过容量直接拒绝，与运行中外部截断分开。

## 最小接口与动作

新增独立 `PublicBattleEnv`，旧 `IroncladBattleEnv`、31动作、schema2不修改。接口为：

```text
reset_scene(scene, environment_seed) -> observation
step(action) -> {observation,reward,terminated,truncated,info}
observation() -> observation
action_mask() -> bool[66]
```

scene只接受入口A：完整deck（source name＋upgrade）、HP/maxHP/gold、ascension、floor、encounter、relic列表与适用counter、药水库存、明确初始化阶段。source seed不传入模型；重模拟身份在元数据保存。禁止将B快照直接填成A。原A20药水容量2；预留3行不表示第三槽可用。

动作0–49为 `hand_slot*5+target`；50结束回合；51–65为 `51+potion_slot*5+target`。无目标卡/药水只开target0；目标型只开实际可选敌人所在行。5行敌人保持后端位置，不按存活数重新压缩。空药水槽和超角色容量槽全部mask=false。未知卡、未知药水或存在二次选择的场景整体拒绝，不以mask掉该实体来冒充完整场景。

初期不增加药水丢弃动作：99场批次不存在战斗中生成/获取药水，丢弃是对未来状态无收益的冗余行为；若后续出现生成/获取机制必须重新审核该判断与动作协议。SmokeBomb逃跑不等于杀敌胜利，另审终止和奖励，目前不纳入。

## 观测字段：直接可实现的语义结构

项目registry应在中央JSON登记 source_name、backend_enum_name、target_kind、升级行为和动态字段。ID按项目稳定表分配，禁止依后端枚举数字大小编码语义；新增条目追加并更新hash。

- `hand[10]`：card_id、upgrade_count、cost、cost_for_turn、free_to_play_once、retain、动态伤害/格挡/特殊数值的具名字段。槽位仅由所在行表达，不加slot特征。
- `draw/discard/exhaust`：同样语义卡行，保留每个副本，按可见语义排序，不暴露uniqueId/真实抽牌顺序。Power离场不凭空补进exhaust。伤害会随目标变化时，不把某一个目标算值写成通用damage；保留base数值和玩家/目标状态供规则agent计算。
- `player`：hp,max_hp,block,energy,energy_per_turn,turn,ascension；具名powers列表（id,amount）与可观察的回合临时效果。NO_DRAW、LOSE_STRENGTH、RAGE、FLAME_BARRIER、DEMON_FORM、METALLICIZE、FEEL_NO_PAIN等不能遗漏。
- `enemies[5]`：present/alive,targetable,id,hp,max_hp,block,intent_kind,intent_damage,intent_hits,powers。CurlUp、Ritual、SporeCloud、Thievery等必须按白名单可达机制加入。后端moveHistory/miscInfo不得原样作为model特征；能由公开行动历史推出的状态另建明确历史字段。
- `relics`：id及具名有效counter；当前5种不需要跨战斗计数，不能因此对未来所有遗物填0。
- `potions[3]`：present,id,target_kind及静态效力注册项，角色实际capacity另给；药水effect如果关联玩家状态由player/powers计算。
- `action_mask`：环境原生66布尔位；metadata/version/hash另存不进token。

建议powers语义列表变长，张量映射为固定已注册状态列，而非无证明的8行power容量。注册状态数是有限类别枚举，有来源和闭包；它与任意“最多同时8个状态”不同。所有可达状态未完成映射之前不要把未知power丢弃。

## 出口与可并行边界

新环境胜利需执行一次exitBattle回写/战后治疗，再用真实退出HP/maxHP算battle_reward_v1；先验证exitBattle后续控制流不会进入完整run。旧环境历史奖励不可回填。Looter逃走结果须显式验证，不能依据“怪物清空”直接认作胜利。

可以并行：M3先实现独立adapter/注册表/完整观测，再按卡机制测试；M4独立核验14普通遭遇和3精英及5目标/分裂/意图，精英数据缺燃烧条件仍属数据阻碍；M5可提前开发仅消费规范obs/mask的规则评分器，并先测合成语义obs。三者均不能提前宣称相应里程碑完成。

当前独立证据是离线闭包统计和源码定位，没有新增后端行为测试。M3/M4收口仍需要实际行为验证、来源派生任务身份锁定、完整目标覆盖与回归。禁止把“C++已有case”当成行为通过。
