# 卡牌 token 稳定版本合并评审

日期：2026-09-13。审计对象是 C:\Users\19091\Desktop\sts2-full-card 当前分支 codex/ironclad-full-expansion 的 75 类 Ironclad、150 个基础/升级版本、5 张辅助牌及其统一实体输入/动作联合接口。

## 1. 最终结论

结论：修复列出的阻塞项后可合并。

这里的“合并”只表示在已声明的第一幕 A20、5个遭遇、当前8类遗物/15类药水、battle 开发环境和已接受的 token 简化下，完成当前输入/动作/资源边界的工程合并。它不表示：

- 形式化证明 token 与整个 STS1 实现等价；
- 75类卡牌的所有组合已经穷举；
- 正式 PPO、策略学习、泛化或完整 run 已验收；
- 新敌人、新药水、全部遗物、无色牌或任意真实卡组已经支持。

当前 938 项回归通过、300 局逐版本集成和50局组合集成都不能绕过下面的4个已确认阻塞项。另有自动/重复打出暂停上下文缺口，须按推荐方案共同裁定后才可把“完整模型输入覆盖”写成合并结论。

## 2. 当前版本事实与验收证据

| 项目 | 结果 | 证据 |
|---|---|---|
| 75类/150版本台账 | 150行，75个唯一卡名；expanded_admitted=150；legacy_admitted=69 | sts/env/ironclad-expansion-coverage.json；scripts/check-ironclad-expansion.py |
| 统一卡牌 token | 115维；0–9数值、10–17布尔、18–98身份、99–114类别/区域 | sts/models/unified-entity-contract.json；sts/env/entities.py:61-79 |
| 普通动作/选择动作 | 66位普通动作；NORMAL + 当前单选阶段；6种真实单选任务 | sts/env/ironclad.py:23-120；third_party/sts_lightspeed/bindings/public-battle-env.cpp:289-590 |
| 输入置换/路由 | 实体、候选 source/target 和公开 route 分离；置换与手牌/敌人重排测试通过 | tests/test_unified_entities.py:40-56,127-164；tests/test_selection_routing.py:21-65 |
| 已知顶牌 | Headbutt/Warcry真实路径只保留一张 KT，抽走/洗牌清除 | tests/test_ironclad_selection_cards.py:63-82；CardManager.cpp:216-254,336-341 |
| 150版本入口 | 本审计 R150 探针 150/150 reset+encode；类型 ATTACK64、SKILL58、POWER28 | 本文件第8节命令记录 |
| 辅助牌入口 | RAUX 5/5 编码；发现 AscendersBane cost_kind错误 | 本审计第7节探针 |
| 回归 | 938 passed in 34.44s | 本审计实际执行 python -m pytest -q |
| 既有工程集成 | 300局/6665 transition/66选牌；50局/1232 transition/59选牌；异常和截断均0 | runs/all-ironclad-20260913-final/integration.json、combinations.json |
| 正式训练 | 未批准、未启动 | sts/env/ironclad-expansion-contract.json:training_admitted=false |

## 3. 阻止合并的问题

### B01：临时费用实例进入消耗堆后跨回合不恢复

| 项目 | 审计结论 |
|---|---|
| 对应卡牌/字段 | Infernal Blade 生成的攻击牌；costForTurn、BC、PC、RC、region=exhaust/hand；影响 Pummel、Feed、Fiend Fire、Reaper 等固有耗尽攻击及 Exhume |
| 实现位置 | Actions.cpp:571-577 将生成牌 costForTurn 设为0；CardManager.cpp:384-396 只重置 hand/discard/draw；BattleContext.cpp:3013-3020 取回消耗牌时原样复制 |
| 实证 | Infernal Blade→生成 Pummel→本回合0费打出并耗尽→结束回合→Exhume选择 Pummel；返回手牌仍 cost=0、base_cost=1、cost_scope=TURN |
| 影响 | 下一回合合法性与支付费用错误；模型如实编码错误后端状态但无法修复它；复制/取回价值也错误 |
| 建议 | 在回合边界重置未来仍可被 Exhume 取回的耗尽实例的本回合费用；明确 FP 与临时 costForTurn 的优先级；补完整逐实例链测试 |
| 兼容影响 | 新后端 hash；CARD115可不变，但运行契约/采集证据/checkpoint指纹变化，旧 checkpoint不能声称精确续训 |

这不是把 RC 误解为“下一回合费用”的字段问题。当前 v3 的 RC 是一次免费覆盖前的本回合值；B01 是实例状态跨区域/回合实际没有恢复。

### B02：Havoc 自动打出不可用顶牌时静默丢牌

| 项目 | 审计结论 |
|---|---|
| 对应卡牌/字段 | Havoc 基础/+1；Wound、Dazed、Burn、AscendersBane；手牌条件不满足时也可能影响 Clash |
| 实现位置 | BattleContext.cpp:1330-1332 调用 PlayTopCard；2508-2522 先 popFromDrawPile；820-861 只有 canUse为真才 useCard，没有失败回收分支；CardInstance.cpp:302-333 对不可打出 Status/Curse 返回 false |
| 实证 | Warcry 将 Wound 置顶后执行 Havoc；前四区8张卡，之后7张；Wound不在 hand/draw/discard/exhaust |
| 影响 | 违反不能静默丢实体；影响牌堆多重集、Fire Breathing/Evolve触发、容量统计及 Havoc 依赖 |
| 建议 | 先用一手机制依据确定自动打出但不可用牌的正确终点，再进入明确 discard/exhaust 或抛出可追溯异常；不能仅隐藏 mask或伪装战败 |
| 兼容影响 | 后端行为与 hash变化；需 Havoc×辅助牌/Clash回归；输入维度可保持不变 |

### B03：Searing Blow+100 的升级过滤越界

| 项目 | 审计结论 |
|---|---|
| 对应卡牌/字段 | Searing Blow upgrade_count=100；Armaments基础/升级的候选和全手牌升级 |
| 实现位置 | CardInstance.cpp:56-60 的 canUpgrade对 Searing Blow只检查ID；144-148 的 upgrade在 specialData>=100抛异常；Actions.cpp:678-698、901-907使用该判断 |
| 实证 | Searing Blow+100 + Armaments+1执行时触发 Searing Blow升级资源边界100；Armaments基础选择+100也触发 |
| 影响 | 声明范围内合法输入在另一张准入卡的正常效果中崩溃；不能当作超出+100的普通异常 |
| 建议 | 保留 registry max_upgrade=100 和 +0…+100公式；让+100成为不可再升级终端，即 canUpgrade=false；补基础/升级 Armaments、自动升级、选择和满手牌测试 |
| 兼容影响 | CARD115/词表可不变，但后端代码 hash变化；旧 checkpoint需重新绑定/验收 |

公式 D(n)=12+n(n+7)/2；+100为5362，UC token=20.0，数值没有裁剪或溢出。阻塞点是过滤与执行边界不一致，不是归一化大于1。

### B04：AscendersBane 的 cost_kind 和非手牌 pay_cost错误

| 项目 | 审计结论 |
|---|---|
| 对应卡牌/字段 | 辅助牌 AscendersBane；base_cost=-3、printed_cost=-3、cost_kind、pay_cost |
| 实现位置 | bindings/public-battle-env.cpp:275 使用 c.cost==-2才标记 UNPLAYABLE；entities.py:68-79 对 ENERGY非手牌使用 printed_cost |
| 实证 | RAUX真实 reset/encode输出 AscendersBane cost=-3、cost_kind=ENERGY；其非手牌 token会把-3作为PC，而不是不可打出0占位 |
| 影响 | 反向字段语义错误；模型会看到 CURSE但类别像普通 ENERGY，非手牌PC为负；辅助链输入解释不稳定 |
| 建议 | cost_kind先判 isXCost，再将所有 c.cost<0的非X实例标为 UNPLAYABLE；补辅助四区、普通mask、Havoc顶牌和状态抽牌测试 |
| 兼容影响 | 维度和词表可不变，但 CARD token实际值变化；需新的后端/输入指纹和 checkpoint复验 |

## 4. 需要共同约定的问题

### B05/Q03：自动/重复打出暂停上下文的最小公开边界

这是一个已确认的字段缺口，但本轮没有把“所有其他公开标量完全相等”的碰撞 witness写成已验证事实，因此不把未经碰撞搜索的部分写成既成运行 Bug。

当前代码事实：

- CardQueueItem 还有 energyOnUse、freeToPlay、autoplay、purgeOnUse、exhaustOnUse（include/combat/CardQueue.h:20-31）。
- 选牌暂停只通过 bindings/public-battle-env.cpp:359-369 导出 curCardQueueItem.card 为 resolving CARD；entities.py:242-289 只把来源卡、候选卡、selection_kind 和公开玩家/敌人状态送入模型。
- Havoc→Headbutt/True Grit+ 的自动来源和 Double Tap→Headbutt 的重复队列都是真实可达；Double Tap路径第一次选牌后仍会出现第二次同类选择，而 current status已为0。
- 当前输入没有 pending replay/choice数量、来源是手动/自动/重复、源牌是否强制耗尽或公开 X快照等字段。

为什么与决策相关：同一个 HEADBUTT选择中，选择某张牌会先改变抽牌堆顶；若另一个 Headbutt已在队列中，之后还会立即发生第二次选择。Havoc的源牌还可能因 queue 的 exhaustOnUse进入消耗堆，手动打出则通常进入弃牌堆。仅依赖单步 CARD token和已消耗的 Double Tap status不能稳定表达待续队列。

推荐方案：

1. 增加有限、公开、具名的 resolution_context，至少包含 manual/autoplay/replay来源、源牌强制耗尽标记、公开 X/费用快照、待处理玩家选择的数量/种类。
2. 不导出内部 queue ID、uniqueId、RNG、完整队列或隐藏牌序。
3. 用 Headbutt、Warcry、True Grit+、Burning Pact、Dual Wield、Exhume、Armaments及 Havoc/Double Tap组合做成对状态探针，验证候选选择后的下一暂停和源牌去向。

如果明确接受当前 Set/PPO的部分可观测简化，可以不加字段，但必须把它登记为新的设计边界；在该裁定前，不应把 B05相关暂停状态称为输入充分。

版本影响：若新增字段进入 PLAYER_GLOBAL或resolving token，需新输入契约/模型版本、更新115维布局或明确不扩维的编码方案、新 checkpoint指纹和从头/显式迁移策略。旧模型不能直接恢复。

### D01：权威文档的当前状态互相滞后

这是已确认的文档事实不一致，不是单独的运行时字段丢失：

- 当前 decisions.md:525-527 与 ironclad-full-cards-report.md:22-34 宣布75类/150版本工程准入完成。
- entity-input-v3-contract.md:25-34 仍写“跨区选牌未准入”、Headbutt/Warcry真实顶牌尚未进入、当前仍使用旧466/15生成描述。
- unified-entity-interface.md 与 unified-entity-report.md 中仍保留80/150、CARD122、目标关系边和“仅True Grit+真实选择”等较早阶段描述。
- 当前实现实际为 CARD115、零宽关系、6种单选任务和全150扩展准入；training_admitted仍为false。

推荐在合并前补一份最终状态段或修订旧段，明确当前实现、历史状态、共享接口扩展点和正式训练状态四者。这个同步不应偷偷改模型或契约；若只做文档同步，不需要新模型版本，但能避免按过时的466/80/122描述启动训练。

## 5. 可后续改进

| 项目 | 当前判断 | 建议 |
|---|---|---|
| damage 与 combat_damage_bonus | Rampage的D已包含CB，二者存在可解释冗余 | 保留当前显式实例字段；在模型/学习记录中说明不能相加。后续若删除需新输入版本 |
| card_id派生字段 | card_type、target_kind、cost_kind、is_strike、AE、ET、EX大多可由ID+升级推出 | 当前保留为 typed convenience feature；不要因冗余误判为错误 |
| magic含义 | 同一维按卡牌解释，不能独立描述 Offering/Flame Barrier等多效果 | 遵守本轮不引入通用多效果；未来显式效果向量另建版本 |
| FP/RT真实true | 当前75卡/8遗物范围只真实覆盖false；字段为共享接口保留 | 不把范围外路径补成当前证据；未来开放相关牌/遗物时增加真实探针 |
| offer实体 | 当前只在 tests/test_unified_entities.py:230-248接口夹具出现 | 新药水/Discovery另行准入；不把offer夹具算全卡行为 |
| 逐版本行为证据 | R150证明入口/编码，F938证明回归；部分卡只有有限机制/组合测试 | 若要声明机制级全卡验收，建立逐版本行为矩阵；当前不把测试总数当充分性 |
| recovery_cost缺省规则 | 当前本回合语义可由raw cost/BC/RC得到，但缺少临时费、一次免费、区域移动统一专测 | 追加字段语义成对测试；目前不单独升级为B类缺陷 |

## 6. 范围外

以下问题不在本次合并判断的阻塞范围，但不能从当前结果推断为支持：

- 新敌人、新药水机制、药水丢弃/替换、Discovery/offer生成和多选确认；
- 全部遗物、全无色卡、所有状态/诅咒来源和任意真实卡组；
- 完整 RunEnv、战斗间地图/奖励/营火、run_reward_v1；
- 正式 PPO、正式评估、泛化、长期 Feed最大HP价值；
- free_to_play_once=true、动态 retain、复杂计数遗物、隐藏队列完整恢复；
- 其他后端固定容量、敌人分裂/召唤、复活/逃跑和多幕场景。

## 7. 真正需要用户审核的事项（一次列全）

下面只列会改变合并边界、行为契约或版本兼容性的事项；代码能直接确定的事实已在 B01–B04 中给出推荐，不再交回用户猜测。

1. B01 临时费用回合边界：推荐在回合边界重置可被 Exhume取回的耗尽实例，并补生成→耗尽→跨回合→取回测试。理由是当前路径已实际把0费带入下一回合。
2. B02 Havoc遇到不可用顶牌：推荐按一手机制确定后回收至明确区域，倾向保留并耗尽该顶牌而不是静默丢失；不能用失败0代替。理由是当前已实际丢失 Wound。
3. B03 Searing Blow+100：推荐保留+100支持，把100定义为不可再升级终端并修正 canUpgrade。理由是注册表和当前报告已声明+100，降低范围会丢弃已提供的合法输入。
4. B04 AscendersBane：推荐将负费用非X分类为 UNPLAYABLE，保持 PC=0占位。理由是与v3类别约定一致，且已由实际RAUX输出证明现值错误。
5. B05/Q03 暂停上下文：推荐新增有限 resolution_context，而不是接受未登记的部分可观测简化。理由是 Havoc/Double Tap的待续选择和源牌去向在当前模型输入中没有字段；新增字段会导致新模型/checkpoint版本。
6. D01 文档状态：推荐合并前同步 entity-input-v3-contract、unified-entity-interface/report 与最终全卡报告的当前状态段；保留历史阶段身份，不重写历史测试数字。理由是过时的80/122/466描述会让后续执行误选入口。

在上述事项落地并完成对应回归前，本轮不批准自动合并、不修改生产实现、不启动正式 PPO。

## 8. 复核命令与不变边界

已执行：

    Set-Location C:\Users\19091\Desktop\sts2-full-card
    .\.venv\Scripts\python.exe -m pytest -q
    .\.venv\Scripts\python.exe scripts/check-ironclad-expansion.py
    .\.venv\Scripts\python.exe scripts/check-spec-v6.py

结果为938 passed in 34.44s、台账150/150、规格检查 PASS。此次只在全卡工作区新增三份报告；没有修改 C:\Users\19091\Desktop\sts2，没有覆盖其他任务的修改，没有提交、推送、合并或启动正式训练。

## 2026-09-13修复复核追加

本节不改写上面的审计快照和修复前阻塞证据，只记录用户裁定后的修复状态：

- B01、B02、B04已按定向回归关闭；B03按用户裁定保留+100资源边界，修正Armaments过滤，不再作为本轮合并阻塞。
- B05没有扩充普通CARD token。新增`unified-entity-interface-v4`/`unified-entity-set-v3`的独立`resolution_context`，字段为`source_mode`、`source_will_exhaust`、`pending_replay_count`，并进入候选动作评分器；不导出完整队列、内部实例ID、RNG或隐藏牌序。
- 当前F1/F2/F3和B05定向回归已落盘；完整CPU回归、短时前反向/采集、新checkpoint严格恢复及最终合并报告仍待F5，不把未执行项目写成通过。
