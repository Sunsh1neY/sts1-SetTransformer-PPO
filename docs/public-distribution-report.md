# 公开派生战斗场景选择偏差与扩容优先级

日期：2026-09-12。分析脚本：`scripts/analyze-public-coverage.py`。本报告只做离线量化和实施建议，不修改正式环境、manifest、`eval_seeds.json`，不训练 PPO，也不运行正式保留集评估。

## 结论先行

固定公开库为 **203 个原始文件 / 157 个独立 run**，第一幕有 **1282 条战斗记录**。其中 257 条可按 `public-derived-standard-v1` 形成完整入口 A 候选，当前内容准入 **99 场 / 75 个 run**。本任务没有实现新场景，所以相对原99场的实际净新增为 **0**。

当前准入过程明显丢失的不是单一卡牌频次，而是四个分布维度：

- 楼层：当前99场只在 floor 1–5；完整第一幕记录有 floor 6–14 的战斗，但证据完整候选没有一场超过 floor 5。
- 遭遇层级：第一幕记录有 425 条精英战斗，当前99场为 0；普通遭遇也只保留 6 个标签。
- 构筑内容：规则候选有 72 个初始卡类、160 个入口牌组多重集、18 个带升级场景；当前99场只有 22 个卡类、27 个多重集、7 个升级场景。
- 消耗品/玩家来源：候选非空药水比例为 75/257，当前99场为 7/99；四个来源路径标签的当前 run 选择率为 42%–100%，且没有玩家身份字段，不能解释为总体玩家分布。

卡牌实现不能补回 floor 6–14、精英和未知事件/商店前缀；这些必须先解决来源证据闭包。另一方面，在证据完整的257条候选内，单独支持 `Anger` 虽有较高潜在收益，但 M1 已登记复制路径延期；因此建议把“完整场景收益”和“动作/容量风险”同时报告，不按卡牌出现次数或策略胜率决定。

## 分母、权重与四层比较

A 层以独立 run 为单位；B/C/D 层以战斗场景行（`scene_id`）为单位。逐场描述统计中每行权重为 `1/N`；run 平衡统计在同一层内让每个 `group_id` 的总权重为1，再除以独立 run 数。这是防止同一 run 多楼层放大，不是对全体玩家总体的统计加权。

| 层 | 单位 | 分母 | 独立 run | 入口 A 完整字段 | 场景权重 |
|---|---|---:|---:|---:|---:|
| A 固定公开库 | run | 203 原始文件去重 | 157 | 118/157 个首战行 | run `1/157`；关联战斗行另算 |
| B 第一幕全部战斗 | scene | 1282 | 157 | 257/1282 | `1/1282` |
| C 规则候选 | scene | 257 | 118 | 257/257 | `1/257` |
| D 当前可执行 | scene | 99 | 75 | 99/99 | `1/99` |

A 层的“入口 A 完整字段”是每个 run 的第一条第一幕战斗行是否有 candidate；不是把一个后期候选牌组复制到整个 run。B 层缺失行的入口卡组、升级、HP/maxHP/gold、遗物和药水均保持未知。脚本的 `final_master_deck_used=false` 是硬约束。
按任务要求单列三种候选分母：原始可研究战斗候选 **1282 场/157 run**；证据完整规则候选 **257 场/118 run**；当前后端可接入 **99 场/75 run**。

### 楼层选择偏差（逐场计数 + 当前保留比例）

| floor | B 全部战斗 | C 候选 | D 当前99 | D/B | D run平衡share |
|---|---|---|---|---|---|
| 1 | 157 | 118 | 75 | 47.77% | 86.93% |
| 2 | 93 | 73 | 18 | 19.35% | 10.93% |
| 3 | 92 | 39 | 4 | 4.35% | 1.60% |
| 4 | 97 | 19 | 1 | 1.03% | 0.27% |
| 5 | 89 | 8 | 1 | 1.12% | 0.27% |
| 6 | 80 | 0 | 0 | 0.00% | 0.00% |
| 7 | 92 | 0 | 0 | 0.00% | 0.00% |
| 8 | 91 | 0 | 0 | 0.00% | 0.00% |
| 10 | 90 | 0 | 0 | 0.00% | 0.00% |
| 11 | 90 | 0 | 0 | 0.00% | 0.00% |
| 12 | 88 | 0 | 0 | 0.00% | 0.00% |
| 13 | 93 | 0 | 0 | 0.00% | 0.00% |
| 14 | 130 | 0 | 0 | 0.00% | 0.00% |

### 遭遇选择偏差（精英/未知事件不折算为普通）

| 遭遇 | B 全部战斗 | C 候选 | D 当前99 | D/B |
|---|---|---|---|---|
| 2 Fungi Beasts | 50 | 6 | 1 | 2.00% |
| 2 Louse | 121 | 66 | 32 | 26.45% |
| 3 Louse | 41 | 3 | 0 | 0.00% |
| 3 Sentries | 151 | 0 | 0 | 0.00% |
| Blue Slaver | 49 | 2 | 0 | 0.00% |
| Cultist | 124 | 64 | 27 | 21.77% |
| Exordium Thugs | 39 | 1 | 0 | 0.00% |
| Exordium Wildlife | 40 | 3 | 0 | 0.00% |
| Gremlin Gang | 24 | 1 | 0 | 0.00% |
| Gremlin Nob | 134 | 0 | 0 | 0.00% |
| Jaw Worm | 108 | 46 | 16 | 14.81% |
| Lagavulin | 140 | 0 | 0 | 0.00% |
| Large Slime | 47 | 1 | 0 | 0.00% |
| Looter | 45 | 5 | 1 | 2.22% |
| Lots of Slimes | 16 | 2 | 0 | 0.00% |
| Red Slaver | 29 | 3 | 0 | 0.00% |
| Small Slimes | 117 | 54 | 22 | 18.80% |
| The Mushroom Lair | 7 | 0 | 0 | 0.00% |

### 遭遇层级总量

| 层级 | B 全部战斗 | C 候选 | D 当前99 |
|---|---|---|---|
| normal | 850 | 257 | 99 |
| elite | 425 | 0 | 0 |
| unknown_or_event | 7 | 0 | 0 |

### 来源路径标签与 run 选择率

| source_collection（路径标签） | A 全部run | C候选run | C/A | D当前run | D/A |
|---|---|---|---|---|---|
| 200-rotating-sample | 50 | 37 | 74.00% | 21 | 42.00% |
| chegs | 46 | 35 | 76.09% | 20 | 43.48% |
| lose-all-gold-max-hp-sample | 10 | 10 | 100.00% | 10 | 100.00% |
| panacea-ironclad-sample | 51 | 36 | 70.59% | 24 | 47.06% |

这里没有把 `source_collection` 命名成玩家。固定公开库只提供路径标签；`player_identity_field_available=false`。例如 `lose-all-gold-max-hp-sample` 的当前选择率为100%，其余三个路径标签约42%–47%，这是准入流程的选择结果，不是玩家总体比例。

### 来源 build 选择偏差

| build | A 全部run | B 全部战斗行 | C候选行 | D当前99 | D/B |
|---|---|---|---|---|---|
| 2022-03-07 | 27 | 224 | 38 | 14 | 6.25% |
| 2022-10-04 | 58 | 477 | 94 | 38 | 7.97% |
| 2022-12-01 | 13 | 102 | 21 | 7 | 6.86% |
| 2022-12-18 | 59 | 479 | 104 | 40 | 8.35% |

进阶/角色维度：固定公开库的来源筛选角色为 IRONCLAD；A 层进阶为 A20:157 run，B/C/D 均继承同一来源进阶字段，没有观察到较低进阶。因此当前99场不能支持跨进阶泛化。

### 入口内容字段统计（只在实际有 candidate 的入口 A 行上计算）

| 层/入口字段分母 | 牌组大小分布 | 多重集数 | 升级场景 | 初始卡类 | 遗物类 | 非空药水 | 药水类 |
|---|---|---|---|---|---|---|---|
| A 首战 candidate 118 | 9:6, 10:1, 11:79, 12:31, 13:1 | 50 | 6 | 48 | 5 | 0/118 (0.00%) | 0 |
| B 有 candidate 257/1282 | 9:8, 10:4, 11:84, 12:89, 13:42, 14:22, 15:6, 16:2 | 160 | 18 | 72 | 5 | 75/257 (29.18%) | 27 |
| C 规则候选 257 | 9:8, 10:4, 11:84, 12:89, 13:42, 14:22, 15:6, 16:2 | 160 | 18 | 72 | 5 | 75/257 (29.18%) | 27 |
| D 当前99 | 9:8, 10:2, 11:64, 12:20, 13:4, 14:1 | 27 | 7 | 22 | 5 | 7/99 (7.07%) | 5 |

B 的 `1025/1282` 行没有入口 A candidate，因此不能用 `.run` 的最终 `master_deck` 补齐；A 首战 candidate 118 行的药水全为空是楼层/时点事实，不代表整个公开库没有药水。C 的完整候选非空药水为 `75/257=29.18%`，D 为 `7/99=7.07%`。C 的完整入口遗物仍只有5类，说明在当前证据完整候选中没有确定的新增遗物类；更多遗物收益只能列为来源缺口潜在收益。

## 逐场依赖图与失败原因

依赖图在 `reference/public-distribution/dependency-graph.json` 保存了全部 **1282** 个 scene_id。每场保留原始 `source_blockers`、manifest `content_blockers`、原子依赖和类别组合。当前状态是：99 场可执行，158 场来源/入口证据完整但内容受阻，1025 场来源/前缀仍不完整。类别频次非可加，重叠 blocker 不分别计收益。

### 依赖类别组合（前12项）

| 类别组合 | 场景数 | 是否可加 |
|---|---|---|
| source_prefix | 428 | 是（不可加） |
| burning_elite_modifier + source_prefix | 271 | 是（不可加） |
| relic_counter_hook + source_prefix | 137 | 是（不可加） |
| card_upgrade_support | 128 | 是（不可加） |
| burning_elite_modifier + relic_counter_hook + source_prefix | 87 | 是（不可加） |
| relic_counter_hook | 30 | 是（不可加） |
| potion_inventory_or_generation + source_prefix | 28 | 是（不可加） |
| card_upgrade_support + potion_choice_support | 26 | 是（不可加） |
| burning_elite_modifier + potion_inventory_or_generation + source_prefix | 24 | 是（不可加） |
| entry_type + source_prefix | 7 | 是（不可加） |
| burning_elite_modifier | 6 | 是（不可加） |
| potion_choice_support | 4 | 是（不可加） |

### 来源原始 blocker（前12项）

| 原始 blocker | 场景数 |
|---|---|
| PREFIX_UNPROVEN:ROOM_HISTORY_PENDING:? | 474 |
| BURNING_ELITE_MODIFIER_UNRECORDED | 388 |
| PREFIX_UNPROVEN:RELIC_HISTORY_PENDING | 224 |
| PREFIX_UNPROVEN:ROOM_HISTORY_PENDING:$ | 155 |
| PREFIX_UNPROVEN:POTION_AUTO_USE_OR_GENERATION_PENDING | 54 |
| PREFIX_UNPROVEN:NEOW_EFFECT_PENDING:BOSS_RELIC/NONE | 42 |
| PREFIX_UNPROVEN:NEOW_EFFECT_PENDING:THREE_ENEMY_KILL/NONE | 40 |
| RELIC_COUNTER_OR_HOOK_PENDING:Old Coin | 25 |
| RELIC_COUNTER_OR_HOOK_PENDING:Dead Branch | 19 |
| RELIC_COUNTER_OR_HOOK_PENDING:Tiny Chest | 17 |
| RELIC_COUNTER_OR_HOOK_PENDING:Bird Faced Urn | 15 |
| ENTRY_ROOM_OR_MULTIPLE_COMBATS_PENDING | 14 |

### 内容 blocker（前12项）

| 内容 blocker | 场景数 |
|---|---|
| UNSUPPORTED_CARD:Anger | 10 |
| UNSUPPORTED_CARD:Hemokinesis | 9 |
| UNSUPPORTED_OR_CHOICE_POTION:PowerPotion | 7 |
| UNSUPPORTED_CARD:Secret Weapon | 6 |
| UNSUPPORTED_CARD:Shockwave | 6 |
| UNSUPPORTED_CARD:Fiend Fire | 5 |
| UNSUPPORTED_CARD:Headbutt | 5 |
| UNSUPPORTED_CARD:Intimidate | 5 |
| UNSUPPORTED_CARD:Perfected Strike | 5 |
| UNSUPPORTED_OR_CHOICE_POTION:GamblersBrew | 5 |
| UNSUPPORTED_CARD:Double Tap,Second Wind | 4 |
| UNSUPPORTED_CARD:Feed | 4 |

其中证据完整候选的内容阻塞有 `154` 场涉及卡牌/升级类别，`30` 场涉及药水范围，`26` 场同时有卡牌和药水 blocker；同时有多个 blocker 的场景保留完整依赖集合。来源不完整的场景不因“识别到卡名”而进入内容收益计算。当前依赖图没有把尚未被数据证明的容量或二次选择强行添加到场景 blocker；它们在下一批建议中作为实现前置验收项单列。
依赖类别清单中 `capacity_action_protocol` 与 `secondary_choice_or_copy_generation` 当前均为0条结构化数据 blocker；0只表示索引没有把它们写成已知来源阻塞，不表示后端已经支持，必须在相关批次验收时显式证明。

## 证据完整候选的确定收益排序

C 层257场是唯一可计算“实现内容后确定打开多少完整场景”的分母；D 当前99场先从C中扣除。单项实现只统计 blocker 原子集合恰好为该单项的场景；联合收益要求一整个依赖集合都被支持。以下收益都是 projected，尚未实现，不是当前净新增。

### 单个原子实现项（按独立可解锁完整场景数排序，前20）

| 实现项 | 仅此依赖的场景 | 包含联合依赖的潜在场景 | 新增run | 新增遭遇 |
|---|---|---|---|---|
| card:Anger | 8 | 23 | 3 | — |
| card:Headbutt | 5 | 18 | 0 | — |
| card:Hemokinesis | 5 | 12 | 1 | — |
| card:Shockwave | 5 | 14 | 0 | Red Slaver |
| card:Feed | 4 | 7 | 3 | — |
| card:Fiend Fire | 4 | 13 | 4 | — |
| card:Infernal Blade | 4 | 5 | 1 | — |
| card:Intimidate | 4 | 7 | 1 | — |
| card:Iron Wave | 4 | 8 | 0 | — |
| card:Perfected Strike | 4 | 13 | 0 | — |
| card:Armaments | 3 | 7 | 0 | Exordium Wildlife |
| card:Corruption | 3 | 6 | 2 | — |
| card:Offering | 3 | 3 | 2 | — |
| card:Secret Weapon | 3 | 6 | 2 | — |
| card:Trip | 3 | 7 | 2 | — |
| card:Violence | 3 | 5 | 1 | — |
| potion:PowerPotion | 3 | 7 | 0 | Exordium Wildlife |
| card:Double Tap | 2 | 6 | 1 | — |
| card:Parasite | 2 | 5 | 1 | — |
| card:Bandage Up | 1 | 1 | 1 | — |

### 最小联合依赖组合（前15）

| 联合依赖 | 组合自身场景 | 关联run | 新增run | 新增遭遇 |
|---|---|---|---|---|
| card:Hemokinesis + card:Shockwave | 3 | 1 | 0 | 3 Louse |
| card:Hemokinesis + potion:SkillPotion | 3 | 1 | 1 | Large Slime |
| card:Secret Weapon + potion:GamblersBrew | 3 | 1 | 1 | Red Slaver |
| card:Anger + card:Corruption + card:Shockwave | 2 | 1 | 1 | — |
| card:Anger + card:Fiend Fire | 2 | 1 | 1 | — |
| card:Anger + card:Fiend Fire + card:Parasite | 2 | 1 | 1 | — |
| card:Anger + card:Perfected Strike | 2 | 1 | 0 | Lots of Slimes |
| card:Anger + potion:LiquidMemories | 2 | 1 | 0 | — |
| card:Blood for Blood + card:Headbutt + card:Trip + card:Whirlwind | 2 | 1 | 1 | 3 Louse |
| card:Double Tap + card:Second Wind | 2 | 1 | 1 | — |
| card:Double Tap + card:Second Wind + potion:ElixirPotion | 2 | 1 | 1 | 3 Louse |
| card:Headbutt + card:Sword Boomerang | 2 | 1 | 1 | — |
| card:Reaper + card:Second Wind | 2 | 1 | 1 | — |
| card:Anger + card:Barricade + card:Feed | 1 | 1 | 1 | — |
| card:Anger + card:Feed + potion:AttackPotion | 1 | 1 | 1 | — |

内容 blocker 场景中有 73 场需要至少两个原子依赖，其中 26 场同时需要卡牌和药水。不能把例如 `Anger` 的23场出现、`PowerPotion` 的7场出现直接相加；脚本用 `content_atoms(scene) <= support_atoms` 去重后才计完整收益。

来源缺口的潜在收益另存 `source_potential_yields`，不进入上表的确定收益。当前证据完整候选最高 floor 为5，所以解决卡牌 blocker 的收益在 floor 维度新增仍为0；要新增 floor6–14/精英，必须先通过 source-prefix evidence gate。

## 最多三个下一批建议

以下三项是具体场景集合，不是“多加卡/多找数据”的泛化建议。JSON 中保存了每批全部精确 `scene_ids`、原子依赖和 projected metrics。收益排序与执行顺序分开：收益最高的批次由于当前动作协议不能直接承接，执行时仍需先过契约迁移门槛。

### direct-state-cards

预计完整场景收益：**17 场 / 8 个关联 run**；相对当前99场新增独立 run 2，新增遭遇 3 Louse, Red Slaver，新增 floor 无。

原子依赖：`card:Hemokinesis, card:Intimidate, card:Shockwave`。工程风险：中等：需新增3类卡及数值/升级行为；若三类均为直接动作，当前66位、手牌10、目标5和变长牌堆可维持，但 target_kind 与状态字段必须逐卡核验。

接受条件：逐卡基础/升级/目标/mask/状态回归通过；17个精确 scene_id 全部能以入口A reset 并在随机与规则开发集成中完整终止；不因某一场失败而删除该场卡牌、药水或遗物；失败场景继续留在拒绝索引

本批精确场景 ID 已落盘（共17个）：`reference/public-distribution/priority-scene-ids.json`。

### hand-copy-secondary

预计完整场景收益：**20 场 / 15 个关联 run**；相对当前99场新增独立 run 7，新增遭遇 无，新增 floor 无。

原子依赖：`card:Anger, card:Fiend Fire, card:Headbutt`。工程风险：高：M1 已明确 Anger/复制路径延期；二次选择、手牌多牌消耗、复制实体和动态容量不能由当前66位动作自动代替。

接受条件：20个精确 scene_id 的全部原子依赖都通过后才计入新增；部分卡通过不提前入场；choice/生成/容量/恢复/完整观测回归通过，并记录新的输入、动作、序列化版本；从头开发集成不异常终止；不使用规则或PPO胜率选出其中子集

本批精确场景 ID 已落盘（共20个）：`reference/public-distribution/priority-scene-ids.json`。

### direct-generated-potions

预计完整场景收益：**4 场 / 2 个关联 run**；相对当前99场新增独立 run 0，新增遭遇 Exordium Wildlife，新增 floor 无。

原子依赖：`potion:DistilledChaos, potion:PowerPotion`。工程风险：高且收益低：只解除PowerPotion与DistilledChaos可确定打开4场、2个关联组且没有新独立run；其余非空药水多与未支持卡牌重叠。

接受条件：4个精确 scene_id 的药水机制、库存和生成闭包全部通过；开发集成验证自然终止、完整观测和药水 mask；不因成功率筛掉困难药水场景；剩余GamblersBrew/SkillPotion等场景继续按其卡牌联合依赖统计，不冒充本批收益

本批精确场景 ID 已落盘（共4个）：`reference/public-distribution/priority-scene-ids.json`。

### 三批之外的来源证据前置门

这不是一个可以把潜在行立即加入 manifest 的实现批次。当前来源/前缀不完整为 1025 条战斗记录、157 个 run；其中 source/prefix 类别潜在覆盖 989 条，燃烧精英类别潜在覆盖 388 条。它们至少还可能带有其他 blocker，确定收益记为0。

需要主 agent 决策的是：是否先登记并实施来源前缀/事件商店证据闭包，以及是否批准从当前66位动作迁移到可表达二次选择的版本。无论选择什么，都不能删除原始不支持牌/遗物/药水或把它们改成基础牌。

## 关联组、去重与未来抽样

原始文件203个按 `play_id`、`seed_played`、raw SHA连接为157个 group；其中46个重复别名文件、0个冲突组，未发现跨group的 play_id/seed/SHA重复。别名目前都在同一来源集合内，但未来来源仍必须先做完整run连接。

当前99场按场景分布为73 train / 24 dev / 2 reserved-eval，按关联 group 则为60 / 13 / 2；它们全部做过开发集成检查。原 `reserved-eval` 标签只反映历史研究预划分，不能证明这2场仍是未接触保留数据，也不能把当前99场回溯宣称为正式保留集。

未来新来源若用于保留评估，应在策略调试前冻结来源提交、group 去重、入口A、观察/动作/序列化版本、环境 seed 分配和评估清单；split 以完整run为单位，同一run的所有楼层不拆分。训练/开发可在run内按 `1/n_scene` 平衡场景，并在样本足够时按来源、build、floor、遭遇层级/标签做组级分层；这仍不是对全体玩家总体的统计加权。source seed 只用于追溯和分组，不能进模型。

## 来源、复现与边界

公开来源固定提交：`097aaf3564c2247835162d267cbc7c55d2c9039e`；声明的 archive SHA256：`0b21c5fe489ac0980131d0dd14350efdf1c68f180488b6d2072ae0e81cea565e`。输入文件、实现/契约哈希和本地 archive 校验状态写入 `reference/public-distribution/coverage-analysis.json`。入口字段证据沿用 candidate 的 `M2C-02`–`M2C-06` 记录；隐藏敌人/牌堆/RNG 为标准规则重新采样，`exact_historical_replay=false`。

离线复现：

```powershell
python scripts/analyze-public-coverage.py
python -m pytest -q tests/test_public_coverage.py
```

通过/未通过边界：脚本会验证99基线、257候选、66位动作契约、manifest 与 index 的候选对应关系、group/scene 唯一性；集成记录若存在，只验证99场开发集成完成性，不把胜率写入筛选逻辑。来源缺口、历史 mod 等价、正式训练/评估 ready、PPO 学习收益均保持未宣称。
