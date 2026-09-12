# 公开 run 事件/商店历史前缀扩展报告

日期：2026-09-12。任务范围是从固定公开 Ironclad run 中恢复被第一幕事件（`?`）或商店（`$`）前缀挡住的战斗入口。本文是研究候选交付，不把候选回填现有 manifest，也不宣布正式环境、训练或评估完成。

## 结论

本轮确实增加了可复现的研究候选，并得到 19 条按当前后端内容契约可接入的扩展候选。19 条全部来自事件前缀；商店前缀有完整研究候选，但没有一条同时落入当前 35 类卡、8 件遗物、15 种直接药水和遭遇内容范围。此前被错误放行的两场精英已因缺少燃烧状态证据撤回到研究层。

| 层级 | 场景数 | 独立 run 组 | 含义 |
|---|---:|---:|---|
| 原始可定位前缀后战斗记录 | 629 | 104 | 第一幕中存在更早事件/商店房的战斗行；包含拒绝行，不等于状态已恢复 |
| 原始可研究候选 | 198 | 91 | 牌组、遗物、药水和入口指标可形成候选对象，但可能含动态状态或后端不支持内容 |
| 证据完整候选 | 96 | 54 | 前缀摘要可唯一应用，入口字段完整，当前状态没有未证明动态遗物/永久牌值，精英还必须有燃烧状态证据 |
| 当前后端可接入候选 | 19 | 14 | 证据完整且内容通过当前 `public-battle-contract.json` 的静态范围筛选；已做开发随机/规则探针，尚未并入正式 manifest |

相对现有 99 条候选，净新增按场景 ID 去重为：原始可研究 198 条、证据完整 96 条、当前后端可接入 19 条。按 run 关联组去重时，三层分别涉及 91、54、14 组；其中相对于原 75 组，真正新增的独立 run 组分别为 33、22、1 组。很多新增战斗属于现有 75 个 run 的更后楼层，因此“新增场景数”和“新增独立 run 数”不能混写。

629 条前缀后目标行中，96 条已经证据完整，102 条能保留一个带状态或入口证据阻塞的候选对象，431 条因前缀/入口/目标字段阻塞而没有完整候选对象。三类都保留在 JSON 的 `scenes` 数组中，不能把 431 条当作成功场景，也不能把 102 条当作证据完整。

## 输入、固定来源与证据

脚本读取四类既有输入：`AGENTS.md` 规定的权威顺序，`spec-v6.md`、`docs/decisions.md`、`docs/mechanics.md`、`docs/learning-path-v2.md`，现有审计/manifest/index，以及 `reference/public-run-corpus/` 中的固定原始归档和记录器源码。本轮没有修改这些输入，也没有新增联网下载。

| 输入 | 固定身份 | SHA-256 |
|---|---|---|
| `reference/public-run-corpus/matiger-fixed.zip` | `MaT1g3R/Slay-the-Spire-data` commit `097aaf3564c2247835162d267cbc7c55d2c9039e`，9,838,209 bytes | `0b21c5fe489ac0980131d0dd14350efdf1c68f180488b6d2072ae0e81cea565e` |
| `reference/public-run-corpus/run-history-plus-2022.zip` | `modargo/RunHistoryPlus` commit `99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b` | `4272eb2dec27d613f356bfa0f2df21358cef9a00a5fda54de3db76a177425cf3` |
| `reference/public-run-corpus/run-history-plus.zip` | `modargo/RunHistoryPlus` commit `8d482facdcebf8a018743ac27005c21b52165863` | `c0636b186b2930308a0f288b77bc4af94d50f5b296e7a6b0d2cd02647f283269` |
| `docs/m2-corpus-index.json` | 本轮输入 index | `0bf3f90ff2f916b792c9abc0b75d3c547ea5e7679849b64a6e62305c39b69357` |
| `docs/m2-public-scene-manifest.json` | 原 99 条当前范围 manifest 输入 | `fdc06a7c786a27d10505d4cb6e95ffa0bfda1cf27dbcf9bcc33f202ce575f437` |
| `sts/env/public-battle-contract.json` | 当前后端静态支持范围输入，`public-battle-v1` | `cc29dad191bd560d6b4f03d048387ba2a1a41d19bb08b1ea3891dcf618e4bea5` |

字段时点和语义采用以下一手记录器证据；文件 SHA、行号和用途也写入 ignored 的 `reference/public-prefix-expansion/source-evidence.json`。

| 证据 | 读取内容 | 本轮如何使用 |
|---|---|---|
| `ShopContentsRunHistoryPatch.java:135-147` | `nextRoomTransition` 中读取当前商店的剩余卡、遗物、药水列表 | 只把 `shop_contents` 当作商店存在和离店时剩余内容；购买历史使用 `items_purchased` 与 `item_purchase_floors`，不要求已购买品还在剩余列表 |
| `MultipleCardRewardsRunHistoryPatch.java:38-62` | 记录器把同楼层、同 picked/not_picked 的重复卡牌选择视为异常并去重 | 同样采用“完整 JSON 完全相同才去重”；不同选择绝不拼接 |
| `PotionRunHistoryPatch.java:94-128,227-231` | 每层创建药水使用列表，收集 potion ID | 库存按获得/使用/丢弃多重集核算，不声称恢复原槽位 |
| `PotionUseAddLoggingSubscriber.java:10-19` | 使用记录发生在 post-use | 同层新获得后使用且无法排序时拒绝，不用净库存倒推时序 |
| `NeowBonusRunHistoryPatch.java:185-311` | Neow 记录升级前 metricID、增删/变形卡、遗物及数值变化 | 初态继续沿用既有 `M2C-02`；不使用最终 `master_deck` |

`current_hp_per_floor[floor-2]` 的入口边界语义沿用 `docs/m2-corpus-report.md` 的 M2C-03：它是上一层边界指标，不读取本场战后值。事件摘要中的 `damage_healed`、`damage_taken`、最大 HP 和金币变化全部原样保留为证据，但不拿理论计算替换该入口指标。卡牌/遗物/药水/遭遇及卡牌 `max_upgrade` 的静态可接入判断由 `sts/env/public-battle-contract.json` 读取；脚本不再维护第二份后端支持集合。

## 原审计拒绝原因与重叠

原 index 的逐场 blocker 统计如下；完整逐 key 结果和每组首次阻塞楼层在候选 JSON 的 `original_blocker_analysis.original_index_blockers` 中。`后续战斗` 是该组从首次出现该 blocker 的战斗楼层开始仍被挡住的战斗行数，不是新的可恢复数量。

| 原 blocker | 场景行 | 独立 run 组 | 后续战斗行 |
|---|---:|---:|---:|
| `PREFIX_UNPROVEN:ROOM_HISTORY_PENDING:?` | 474 | 77 | 474 |
| `PREFIX_UNPROVEN:ROOM_HISTORY_PENDING:$` | 155 | 27 | 155 |
| `PREFIX_UNPROVEN:RELIC_HISTORY_PENDING` | 224 | 34 | 224 |
| `PREFIX_UNPROVEN:POTION_AUTO_USE_OR_GENERATION_PENDING` | 54 | 8 | 54 |
| `PREFIX_UNPROVEN:NEOW_EFFECT_PENDING:BOSS_RELIC/NONE` | 42 | 5 | 42 |
| `PREFIX_UNPROVEN:NEOW_EFFECT_PENDING:THREE_ENEMY_KILL/NONE` | 40 | 6 | 40 |
| `BURNING_ELITE_MODIFIER_UNRECORDED` | 388 | 146 | 680 |
| `ENTRY_ROOM_OR_MULTIPLE_COMBATS_PENDING` | 14 | 14 | 39 |

这张表不能按列相加。原审计在一个 run 的首个无法恢复前缀处停止，所以“观察到的首 blocker 组”会被前缀顺序人为分开；原始房间出现情况则明显重叠：第一幕含事件房的组 148，含商店房的组 121，同时含两者的组 113。因此事件/商店原始房间不能用 148+121 推导独立 run 数。本轮同时输出了 `observed_first_blocker_group_overlap_matrix` 和 `raw_prefix_room_presence_overlap`，避免把原因重叠误算成增量。

## 事件与商店前缀闸门

### 事件

固定库第一幕共有 308 个事件房，全部有匹配 `event_choices`；其中 2 个楼层各有三条完全相同的 JSON 记录，0 个非完全相同重复。脚本只应用一次完全相同的结果，因此没有把同一事件当成三次卡牌/遗物变化。

事件结构闸门结果：282 个楼层的摘要满足本轮显式 allowlist，26 个楼层拒绝或待定。事件分支现在和 M/E/R/T、商店一样调用逐层药水账本；缺 `potions_obtained`、生成、使用或丢弃数组时不再默认为空。

- 允许的记录变化包括明确的金币/HP/最大 HP变化，以及摘要明确列出的卡牌移除、升级、变形、获得和遗物获得/移除；`Living Wall`、`Transmorgrifier`、`Shining Light`、`The Cleric`、`Purifier` 等均按逐条记录应用。
- 事件结果使用按结果定义的必要字段和数量：`Living Wall/Grow` 必须有且仅有 1 张 `cards_upgraded`；`Living Wall/Change` 和 `Transmorgrifier/Transformed` 必须各有 1 张来源牌及 1 张结果牌；遗物结果必须有且仅有 1 个明确 `relics_obtained`；`Shining Light/Entered Light` 必须有 2 张升级牌。缺字段、数量为 0、数量超出或出现未声明的非空效果都会拒绝。
- 明确无效果的 `Leave`、`Ignored`、`Searched '0' times`、`Bought 0 Potions` 允许省略空的效果列表，但仍核验已出现的列表必须为空；这与有实际效果的结果缺字段不是同一状态。
- `The Woman in Blue` 买 1/3 瓶、`Lab` 的随机药水和 `WeMeetAgain` 交药水没有药水 ID，拒绝；买 0 瓶才是无状态变化的允许结果。
- `Wheel of Change/Relic` 没有记录具体遗物 ID，拒绝。
- `Dead Adventurer` 的搜索战斗、`Mushrooms` 的事件内战斗，以及任何事件楼层同时出现 `card_choices` 的 14 个楼层，拒绝为时序/嵌套战斗不唯一；不把卡牌奖励直接塞到事件前或事件后。
- 历史完整 mod/行为等价仍为 `unverified`；allowlist 是 `public-derived-standard-v1` 下的保守规则派生，不是历史精确回放。

### 精英入口证据

`Gremlin Nob`、`Lagavulin` 和 `3 Sentries` 属于当前契约支持的精英遭遇，但精英入口还必须有公开记录明确给出 `burning_elite`。当前固定 run schema 没有该字段；`green_key_taken_log` 只能证明钥匙记录，不能反推本场是否燃烧精英，因此不补 `false`。

本次重建保留了 63 条含精英的原始研究候选，但 63 条全部带 `ELITE_BURNING_STATE_UNPROVEN`，没有一条进入证据完整层。修复前的 149 条证据完整候选中有 53 条精英，扣除后当前证据完整层为 96 条；原来静态层的两场 `Gremlin Nob`：`run-group:53c16194b16286bd892d:floor-7:combat-0` 和 `run-group:f2672b82929351d73ae6:floor-6:combat-0` 现在均保留完整内容、`burning_elite: null` 和明确阻塞，不再送入最终运行探针。

### 商店

固定库第一幕共有 145 个商店房，全部有唯一 `shop_contents` 行，未发现缺失或重复。`items_purchased` 与 `item_purchase_floors`、`items_purged` 与 `items_purged_floors` 在当前 203 个原始文件中逐项长度对齐；脚本仍在运行时对每个目标楼层重新核验，缺失/错位立即拒绝。

商店结构闸门结果是 142 个结构上可解析楼层、2 个 `Whetstone` 随机升级目标缺失、1 个 `DollysMirror` 复制目标缺失。`Orrery` 是例外：若存在完整的五条同层 `card_choices`，保留这五条选择；它本身仍是当前后端不支持的遗物。商店剩余内容不被当成购买前库存，已购买品从剩余列表消失是预期时点差异。

商店购买会增加完整的卡牌副本/升级、遗物或药水；商店 purge 会移除记录中指定的卡牌副本。遇到 `DollysMirror`、`War Paint`、`Whetstone`、`Bottled Flame/Lightning/Tornado` 或改变药水容量的 `Potion Belt`，缺少目标牌、随机升级目标或容量时不构造完整入口。所有原始 item 仍在失败证据中保留，没有删除以凑当前后端范围。

在能够沿完整前缀走到失败点的场景中，实际应用失败计数为：`RELIC_HISTORY_PENDING` 127、`POTION_AUTO_USE_OR_GENERATION_PENDING` 10、`POTION_WITHIN_FLOOR_ORDER_PENDING` 2、`Lab/Got Potions` 3、`The Woman in Blue` 买 3 瓶 1、买 1 瓶 1、`WeMeetAgain/Gave Potion` 1。它们是逐次前缀尝试计数，不能相加为独立 run 或新增场景；商店的 3 个二次选择阻塞由全库结构闸门单独发现，部分在更早动态遗物阻塞之后才会被看见。

## 新增候选和相对 99 场的变化

下面的 `净新增场景` 均按完整 `scene_id` 与原 99 条比较；`新增 run 组`是新候选组减去原 75 组，不是候选涉及组总数。多重集和遗物/药水组合是集合变化，不能与场景数相加。

| 层级 | 净新增场景 | 候选涉及组 | 新增独立组 | 新楼层 | 新遭遇 | 新卡组多重集 | 并集卡组多重集 | 新遗物/药水组合 | 并集遗物/药水组合 |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|
| 原始可研究 | 198 | 91 | 33 | 6,7,8,10,11 | 3 Louse、3 Sentries、Blue Slaver、Exordium Thugs、Exordium Wildlife、Gremlin Gang、Gremlin Nob、Lagavulin、Large Slime、Lots of Slimes、Red Slaver | 184 | 211 | 107 | 117 |
| 证据完整 | 96 | 54 | 22 | 6,7,8 | 3 Louse、Blue Slaver、Exordium Thugs、Exordium Wildlife、Gremlin Gang、Large Slime、Lots of Slimes、Red Slaver | 88 | 115 | 40 | 50 |
| 当前后端可接入 | 19 | 14 | 1 | 无新增（仍为1–5） | 无新增（仍为原6种普通遭遇） | 16 | 43 | 6 | 16 |

原 99 条的基线是 27 个卡组多重集、10 个遗物/药水组合、楼层 1–5 和 6 种普通遭遇。当前后端层的 19 条都是事件前缀，没有商店层新增；因此“商店已能产生 27 条证据完整候选”与“商店当前后端可接入为 0”同时成立。精英和第 6 层以上的新增只存在于原始研究层，不应从静态后端层推导出来。

按恢复收益排序，脚本的 `prefix_ranking` 为：事件先于商店。事件有 163 条原始可研究、79 条证据完整、19 条当前后端可接入；商店有 79、27、0 条。两类有重叠：原始候选重叠 44 条，证据完整重叠 10 条，当前后端重叠 0 条，不能把两个 ranking 行直接相加。

## 当前后端层的 19 条场景索引

以下只是便于主 agent 审核的短索引；每一条的完整 `player`、牌组副本/升级、遗物、药水、入口时点、源 SHA 和逐层 `prefix_evidence_chain` 都在 `docs/public-prefix-expansion-candidates.json` 的 `scenes` 数组中。没有从表中省略任何不支持实体。

| scene_id | 原始 run | 楼层 | 遭遇 | 前缀 |
|---|---|---:|---|---|
| `run-group:03869ca33f76f9685375:floor-3:combat-0` | `runs/panacea-ironclad-sample/1667161552.run` | 3 | Small Slimes | event |
| `run-group:33c70f66905a836d5918:floor-3:combat-0` | `runs/200-rotating-sample/IRONCLAD/1669685251.run` | 3 | Jaw Worm | event |
| `run-group:33c70f66905a836d5918:floor-4:combat-0` | `runs/200-rotating-sample/IRONCLAD/1669685251.run` | 4 | Cultist | event |
| `run-group:3f59e5d32006abf5ab88:floor-3:combat-0` | `runs/200-rotating-sample/IRONCLAD/1671993683.run` | 3 | Small Slimes | event |
| `run-group:49e4cc1cf19e9a0d2d16:floor-3:combat-0` | `runs/chegs/all/1708651208.run` | 3 | Cultist | event |
| `run-group:53c16194b16286bd892d:floor-3:combat-0` | `runs/lose-all-gold-max-hp-sample/IRONCLAD/1672867344.run` | 3 | Small Slimes | event |
| `run-group:53c16194b16286bd892d:floor-4:combat-0` | `runs/lose-all-gold-max-hp-sample/IRONCLAD/1672867344.run` | 4 | Cultist | event |
| `run-group:53c16194b16286bd892d:floor-5:combat-0` | `runs/lose-all-gold-max-hp-sample/IRONCLAD/1672867344.run` | 5 | 2 Fungi Beasts | event |
| `run-group:5bade670577f01ea1632:floor-3:combat-0` | `runs/panacea-ironclad-sample/1665953909.run` | 3 | Jaw Worm | event |
| `run-group:6ab5ecf45b0a88a64df0:floor-3:combat-0` | `runs/200-rotating-sample/IRONCLAD/1667785731.run` | 3 | Cultist | event |
| `run-group:6ab5ecf45b0a88a64df0:floor-4:combat-0` | `runs/200-rotating-sample/IRONCLAD/1667785731.run` | 4 | 2 Louse | event |
| `run-group:857303c9b035c095e9d4:floor-3:combat-0` | `runs/panacea-ironclad-sample/1666061338.run` | 3 | Jaw Worm | event |
| `run-group:8db27ce2ad907224365f:floor-3:combat-0` | `runs/chegs/all/1708907876.run` | 3 | Jaw Worm | event |
| `run-group:99171439576ecb8a16ea:floor-5:combat-0` | `runs/panacea-ironclad-sample/1667071560.run` | 5 | 2 Fungi Beasts | event |
| `run-group:bb9729c2b5a44461e261:floor-3:combat-0` | `runs/chegs/all/1708040040.run` | 3 | Jaw Worm | event |
| `run-group:bcb873ad5d194f1967a8:floor-4:combat-0` | `runs/chegs/all/1708123581.run` | 4 | Small Slimes | event |
| `run-group:bcb873ad5d194f1967a8:floor-5:combat-0` | `runs/chegs/all/1708123581.run` | 5 | Looter | event |
| `run-group:c141c78420544b641568:floor-4:combat-0` | `runs/panacea-ironclad-sample/1663664431.run` | 4 | 2 Louse | event |
| `run-group:f2672b82929351d73ae6:floor-5:combat-0` | `runs/chegs/all/1708745103.run` | 5 | 2 Fungi Beasts | event |

## 六张重点牌追踪

脚本按关联组去重记录第一幕 `card_choices` 的拿牌记录，再检查拿牌楼层之后的真实 `damage_taken` 战斗行。没有因为牌名在 M1 白名单而放宽事件、商店、药水或动态遗物要求。

| 牌 | 拿牌 run 组 | 拿牌后战斗 | 证据完整战斗 | 当前后端战斗 | 仍在牌组的证据完整战斗 |
|---|---:|---:|---:|---:|---:|
| Dropkick | 6 | 12 | 0 | 0 | 0 |
| Entrench | 2 | 2 | 0 | 0 | 0 |
| Rage | 8 | 15 | 0 | 0 | 0 |
| Sentinel | 1 | 4 | 0 | 0 | 0 |
| Thunderclap | 1 | 2 | 0 | 0 | 0 |
| True Grit | 1 | 0 | 0 | 0 | 0 |

失败原因仍写在 JSON 的 `special_card_tracking[*].failure_reasons`：Dropkick 主要被 `The Woman in Blue` 未记录药水 ID、动态遗物和燃烧精英前缀挡住；Entrench/Sentinel 各有 Neow 或入口未证问题；Rage 同时受动态遗物、药水、房间前缀和燃烧精英证据影响；Thunderclap 被动态遗物前缀挡住；True Grit 在本库拿牌后没有更晚的第一幕战斗。拿到牌的记录本身不计为战斗入口。

## 事实、派生与未知边界

### 公开记录事实

- 固定归档有 203 个 Ironclad 文件、157 个关联 run 组；第一幕审计有 1282 个战斗行。
- 事件/商店楼层由 `path_per_floor` 的 `?`/`$` 定位；逐条 event、shop、购买、purge、卡牌选择、药水日志和前层 HP/maxHP/gold 都保留在源归档或本轮证据链。
- 事件摘要有时明确写出卡牌/遗物/数值，有时只写“获得药水”“随机遗物”或同层额外卡牌选择；后者没有被补造。

### 有证据的规则派生

- Neow 和普通 M/E/R/T 前缀沿用现有审计实现；新增事件只应用 allowlist 中的逐项摘要，新增商店只应用对齐的交易数组。
- 事件分支与商店/普通房间统一执行逐层药水获得、使用、丢弃、生成、容量和顺序检查；同层购买/获得后无法证明使用顺序时拒绝，不能把剩余库存倒填为入口。
- 牌组始终按多重集保存，每个升级通过替换一张原副本完成；变形同时移除记录源牌并加入记录结果牌。
- 药水用 canonical inventory slots 表示，`None` 只用于当前容量内的空槽，不声称原始槽位。
- 目标战斗入口是 `pre_combat_initialization` / `before_destination_room_entry`；遭遇、敌人初态、牌堆顺序和 RNG 由后端以后从独立 environment seed 重采样，`exact_historical_replay=false`。
- 内容筛选严格读取当前中央契约中的卡牌、`max_upgrade`、遗物、药水和遭遇；无法支持的牌、遗物、药水仍留在候选对象和 `backend_blockers`，不删除、不改成 PAD、不只 mask 掉。精英另需显式 `burning_elite` 证据。

### 未知或拒绝

- 所有历史完整 mod 清单和行为等价仍未核实；`public-derived-standard-v1` 只代表当前登记的规则派生策略。
- 非 `RESET_RELICS` 遗物的动态计数/钩子未证明，`RitualDagger`/`Genetic Algorithm` 的永久值未证明；这两类只保留原始研究候选或拒绝证据，不进入证据完整层。
- `Gremlin Nob`、`Lagavulin`、`3 Sentries` 的燃烧状态在当前固定 run schema 中没有可核验字段；63 条含精英候选均阻塞，不能用 `green_key_taken_log` 或补 `false` 放行。
- 原始事件/商店的隐藏 RNG、完整牌堆后端顺序、房间内部队列和开战后历史没有被伪造；入口 A 不由 B 快照倒填。
- `shop_contents` 不是购买前快照；商店物品的原始槽位、需要二次选牌的目标和随机升级目标若未记录，拒绝。事件的必要效果字段按结果定义，缺失的升级、变形结果或具体遗物 ID也拒绝。
- 未知 Neow 奖励、Fairy/Entropic/Alchemize、同层无法排序的药水使用、重复或冲突的源记录仍在阻塞项中。

## 交付清单与复现

本任务新增或生成的文件：

- [scripts/expand-public-prefixes.py](../scripts/expand-public-prefixes.py)：独立离线扩展脚本；不写正式环境或既有 manifest。
- [tests/test_public_prefix_expansion.py](../tests/test_public_prefix_expansion.py)：17 条专测，覆盖 P1/P2/P3 和真实运行边界。
- [docs/public-prefix-expansion-candidates.json](public-prefix-expansion-candidates.json)：629 条前缀后目标行、198 个原始可研究候选、96 个证据完整候选和 19 个当前后端静态可接入候选；每个候选保存源 run、SHA、楼层、关联组、入口状态、完整内容和阻塞项。
- `reference/public-prefix-expansion/`（ignored）：`source-evidence.json`、`prefix-failure-summary.json`、`prefix-coverage-summary.json`、`runtime-probe.json`。

最终实现/产物 SHA-256：脚本 `ff118c4b81eede4d6de550b748db4983bbfb17cc9dcd39e731d50d0d47b37081`；候选 JSON `d4f5ff6d0177855b3a8ddea9d6080c5361adcb462f07c7d79dc4d11b58a02d09`；runtime probe `6fcffdb1dcbbad71535c562e6b51a061f895e3247a394e2fa35c7317a8af0548`。候选 JSON 顶层同时记录输入 index、manifest、contract、archive 和实现 SHA。

复现命令：

```powershell
python -X utf8 scripts/expand-public-prefixes.py
python -X utf8 -m pytest -q tests/test_public_prefix_expansion.py
python -X utf8 -m pytest -q tests/test_public_corpus.py tests/test_public_scene_manifest.py tests/test_public_prefix_expansion.py
python -X utf8 -m ruff check scripts/expand-public-prefixes.py tests/test_public_prefix_expansion.py
git diff --check
```

运行探针产物为 `reference/public-prefix-expansion/runtime-probe.json`，schema 为 `public-prefix-runtime-probe-v1`。它只读取最终 `backend_admissible=true` 的 19 条候选，环境 seed 从 930000 起，随机 Agent seed 从 1930000 起，均满足开发 seed `>=100000`；随机/规则各 19 次。每条记录保留 reset、终止、截断、步数或异常，不依据胜负筛选，也不触碰 `eval_seeds.json`。

本轮已验证：扩展脚本离线重建成功；专测 17 passed；Ruff 通过；原 99 条候选逐条 99/99 一致；固定归档、index、中央契约哈希校验通过。最终 19 条静态候选共做 38 次开发探针（随机 19、规则 19），38/38 完成、无 reset/step 失败、无截断；失败记录字段仍由探针保留。全仓回归 603 passed，无失败或跳过。没有训练 PPO、没有使用或修改 `eval_seeds.json`、没有运行正式保留集评估、没有把 19 条写入正式 manifest，也没有 commit/push。

## 需要主 agent 决策的事项

1. 是否接受本报告的 19 条“当前后端静态可接入”作为下一轮独立 review 的输入；它们已通过 38 次开发 reset/step 探针，但仍未写入正式 manifest。
2. 是否把 96 条证据完整候选按 `public-derived-standard-v1` 继续保留为研究集；尤其是商店 27 条虽然入口字段完整，但包含当前后端不支持的真实牌/遗物/药水，不能删内容后转为准入。
3. 是否另立任务核验动态遗物计数、Potion Belt 容量、二次选牌目标、事件内战斗和事件药水 ID；这些是当前 19 条之外的主要阻塞，不应在本任务中用默认值补齐。
4. 六张重点牌在本轮修复后均没有进入当前后端层；Rage 仅有的旧静态候选已因燃烧精英证据或其他前缀阻塞撤回。是否继续追踪需要主 agent 先决定前缀/动态状态的证据范围，不能按牌名直接扩大白名单。

## 给主 agent 与 Agent 3 的交接摘要

- 最终候选文件：`docs/public-prefix-expansion-candidates.json`；脚本重建后的 SHA-256、输入 index/manifest/contract SHA-256 和 schema 均在文件顶层。
- 当前实际计数：原始可研究 198 场/91 组，证据完整 96 场/54 组，静态可接入 19 场/14 组；相对原 99 场，静态层净新增 19 场，新增独立 run 组 1 个。
- 最终静态候选运行探针：`reference/public-prefix-expansion/runtime-probe.json`，随机 19 次 + 规则 19 次，共 38 次，全部完成；这是开发探针，不是正式评估或 Gate 结果。
- 仍被燃烧精英证据阻塞：63 条含 `Gremlin Nob`、`Lagavulin` 或 `3 Sentries` 的研究候选全部为 `burning_elite: null`，带 `ELITE_BURNING_STATE_UNPROVEN`；其中主审点名的两场 `run-group:53c16194b16286bd892d:floor-7:combat-0`、`run-group:f2672b82929351d73ae6:floor-6:combat-0` 已不在静态候选。
