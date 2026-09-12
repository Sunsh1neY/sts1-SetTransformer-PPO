> 2026-09-13最终收尾：CARD仍115维，统一接口v4/模型v4。同一公开结算上下文进入动作头与价值头；价值端按有效候选均值汇总，空候选取零。B05真实路径证明字段来源，尚无完整输入碰撞证明。+100保留资源异常，不作为升级终点。最终证据以docs/card-token-final-review.md为准，下面较早阶段数字保留历史身份。

# 卡牌 token 逐卡逐字段双向输入覆盖审计

日期：2026-09-13。审计工作区：C:\Users\19091\Desktop\sts2-full-card。

## 1. 结论先行

本审计不把“75 类、150 版本已登记”当成输入充分性证明，而是把每个卡牌版本放回实际的：

registry → reset/config → C++ cardRow → Python normalize → card_features → 统一实体模型 → 合法候选/mask → route → 后端结算

链条中检查。

当前 75 类、150 个基础/升级版本均能进入扩展开发入口并编码；统一实体卡牌 token 为 115 维，五类实体共同进入 UnifiedEntityActorCritic。但是当前不能作为稳定版本直接合并。本审计确认了四个当前范围内的阻塞项：

1. Infernal Blade 生成的本回合临时 0 费且固有耗尽卡，跨回合经 Exhume 取回后仍为 0 费。
2. Havoc 自动打出不可打出的 Wound 时，卡从抽牌堆弹出后没有进入弃牌堆或消耗堆，造成静默实体丢失；Dazed、Burn、AscendersBane 和部分 Clash 路径同类。
3. Searing Blow+100 虽被声明为可编码范围，Armaments 的升级过滤仍将它视为可升级，执行时触发资源边界异常。
4. 辅助牌 AscendersBane 的 cost=-3 被 cardRow 错分为 ENERGY，而不是 UNPLAYABLE；非手牌 token 会因此产生负 pay_cost。

Havoc/Double Tap 造成暂停选牌时，当前 token 还没有表达 CardQueueItem 的自动打出、重复打出、强制耗尽和待续选牌上下文。这是已确认的字段缺口；最小公开语义和是否纳入当前 MDP 需要共同裁定，见合并评审中的 B05/Q03。已有自动选牌轨迹只证明路由能跑通，不证明每个暂停点的决策上下文完整。

本文件把输入覆盖结论和行为证据等级分开。OK-I 不表示正版数学等价；B 证据不表示所有组合已经穷尽。

## 2. 审计快照、范围与证据等级

| 项目 | 当前事实 |
|---|---|
| 工作区 | C:\Users\19091\Desktop\sts2-full-card |
| 分支 / HEAD | codex/ironclad-full-expansion / b0dc8e3c0e236a8e7c6415e89a03b8646ad2fdac |
| 上游后端 | third_party/sts_lightspeed 基线 7476a81954020087da31d41d16fddf475746ec2d，使用当前工作区增量补丁构建 |
| 实际扩展二进制 | third_party/sts_lightspeed/build/slaythespire.cp313-win_amd64.pyd，SHA-256 17ac436364a4cd47e0bc0793e65bf6c036236ceb4302547b0ed43c8effce7f97 |
| 统一输入 / 模型 | unified-entity-interface-v3 / unified-entity-set-v2；CARD 115 维；2 层、64 宽、4 头、FF128、无位置编码 |
| 扩展运行契约 | ironclad-expansion-contract-v1，ironclad-observation-v4，普通动作66位，支持 NORMAL 与当前单选阶段 |
| 牌表 | 80 个 token 身份：75 类 Ironclad + 5 类辅助牌；75 类的150个基础/升级版本均为 expanded_admitted=true |
| 训练状态 | training_admitted=false；本审计不批准正式 PPO |
| 当前范围 | 第一幕、A20、JAW_WORM / EXORDIUM_THUGS / GREMLIN_NOB / LAGAVULIN / THREE_SENTRIES、8类遗物、15类药水 |
| 范围排除 | 任意真实卡组、全遗物药水、全部敌人、全无色牌、offer 生成机制、完整 run、正式训练 |
| 工作树保护 | 原训练工作区 C:\Users\19091\Desktop\sts2 未写入；本次只新增三个指定报告 |

证据标记：

- S2：当前工作树源码、JSON 契约或补丁的静态核验。
- R150：本审计执行的真实扩展 reset、normalize、encode_observation 探针；150/150，无失败。只证明入口/编码，不打出卡牌。
- RAUX：五张辅助牌的真实扩展 reset 与编码探针。
- B-LEG：tests/test_ironclad_expansion.py 的继承版本和旧范围对拍。
- B-DYN：tests/test_ironclad_dynamics.py 的动态实例、费用、Power 探针。
- B-DIR：tests/test_ironclad_direct.py 的直接效果、自伤、Artifact、治疗和随机目标探针。
- B-CHAIN：tests/test_ironclad_direct_chain.py 的治疗、致死、自动耗尽和多段探针。
- B-SEL：tests/test_ironclad_selection_cards.py、tests/test_true_grit_selection.py 的真实单选、跨区路由与顶牌探针。
- B-FNL：tests/test_ironclad_final_cards.py 的最后十类、Searing、Havoc、Double Tap、Infernal 和终止边界探针。
- B-POW：tests/test_ironclad_powers.py 的能力、回合边界、抽牌和触发链探针。
- F938：本次实际执行 python -m pytest -q，938 passed；测试总数不是覆盖论证。
- I300/I50：已有工程集成产物 runs/all-ironclad-20260913-final/integration.json 与 combinations.json；分别300/50局，无异常/截断，不是正式训练。
- Q：本审计新增只读定向探针；输出摘要在第7节。
- U：未验证或只能由源码推断，不得写成已确认运行正确。

机制的一手依据 S1 是本机正版 STS1 JAR：E:\SteamLibrary\steamapps\common\SlayTheSpire\desktop-1.0.jar，SHA-256 为 cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673。该 JAR 的 Ironclad 构造器、upgrade/use 和英文 cards.json 数值/文本定位继承自既有 M1 审计；本轮没有重新执行150个正版 class 的字节码对拍。凡只有当前 C++ 分支或有限测试支持、没有一手行为对拍的行，均保留 EVID 或 U，不把当前后端 case 当作正版等价证明。

## 3. 共同字段与动作缩写

精确索引见反向字段覆盖表。这里使用：

UC=upgrade_count，BC=base_cost，D=damage，BLK=block，BB=base_block，M=magic，H=hits，CB=combat_damage_bonus，PC=pay_cost，RC=recovery_cost；AE=all_enemies，ET=ethereal，EX=exhaust，FP=free_to_play_once，RT=retain，ST=is_strike，EE=effective_exhaust，KT=known_top。

动作缩写：

- N-T：普通阶段 PLAY_TARGET，route 为 hand_slot × 5 + enemy_index。
- N-S：普通阶段 PLAY_SELF，route 为 hand_slot × 5；无目标 AOE、随机目标和自效果不新增玩家目标动作。
- SEL(k/z)：SELECT_CARD，选择种类 k、候选区 z；后端索引和一次性 decision_id 只保存在模型外 route。
- AUTO：由环境推进的随机目标、自动耗尽、自动打出或生成，不伪造成策略动作。
- N-T→SEL：先执行普通出牌，再在同一真实结算链形成选牌 transition。

覆盖结论：

- OK-I：当前公开事实在卡牌 token、其他实体 token、玩家/敌人/药水/遗物 token 或合法候选中有表达；目标伤害预览按接受约束不进入模型。
- OK-S：输入事实有表达，当前单选路由可表达；自动/重复打出暂停另附 B05。
- DESIGN：明确接受的简化，例如用 ID 恢复固定多效果、magic 按卡牌解释、X 不预测命中次数。
- BLOCK-B01 至 BLOCK-B04：本审计确认的当前范围阻塞项。
- EVID：没有发现 token 缺字段，但该版本的关键结算或组合只有源码/入口/有限测试证据。
- OUT：契约保留但当前范围不实际产生，或属于另一个任务/完整 run。

## 4. 75 类、150 个版本逐项审计

每个基础版和升级版均单列。扩展准入表示当前开发环境可 reset/编码/路由；不表示 training_admitted，也不表示所有组合通过。

### 4.1 Attack（32 类，64 版本）

| 编号 | 卡牌与版本、准入 | 机制与决策需求 | 自身 token 字段 | 外部公开依赖 | 动态实例、区域、时序 | 动作表达 | 覆盖结论 | 核验依据 |
|---|---|---|---|---|---|---|---|---|
| A01 | Anger 基础；扩展开发准入 | 费0，D6；打出后生成1张 Anger | UC0、D6、M1、PC/RC、ATTACK/ENEMY | 目标敌人、Strength/Weak/Vulnerable、手牌/弃牌堆 | 生成牌同为基础版，进入弃牌堆；重复牌独立 | N-T；生成 AUTO | OK-I / EVID | S2:C-A BattleContext.cpp:968-971、C-F public-battle-env.cpp:191-200；R150；B-FNL |
| A01+ | Anger+1；扩展开发准入 | 费0，D8；生成1张 Anger+1 | UC1、D8、M1、PC/RC、ATTACK/ENEMY | 同基础；后续攻击与弃牌内容 | 生成副本保留升级，不把源牌槽号写入 token | N-T；生成 AUTO | OK-I / EVID | S2:C-A:968-971；R150；B-FNL |
| A02 | Bash 基础；扩展开发准入 | 费2，D8，目标 Vulnerable 2 | UC0、D8、M2、PC/RC、ATTACK/ENEMY | 目标敌人 Artifact、Vulnerable、力量与伤害修饰 | 出牌后源牌进入弃牌；易伤由敌 token 体现 | N-T | OK-I / EVID | S2:C-A:973-977、C-F:204-206；R150；B-LEG；F938 |
| A02+ | Bash+1；扩展开发准入 | 费2，D10，目标 Vulnerable 3 | UC1、D10、M3、PC/RC、ATTACK/ENEMY | 同基础；Artifact 可阻止减益 | 区分升级值，不依赖隐藏升级布尔 | N-T | OK-I / EVID | S2:C-A:973-977、C-F:204-206；R150；B-LEG；F938 |
| A03 | Blood for Blood 基础；扩展开发准入 | 费4，D18；本战斗每次失HP事件费用-1 | UC0、BC4、D18、PC/RC、ATTACK/ENEMY | 玩家 HP、自伤来源结果、BFB 各实例费用、Rupture/Strength | cost/costForTurn 随每次失HP下降并跨手牌/牌堆保留；耗尽后不再更新 | N-T；费用由 mask/PC 表达 | OK-I / EVID | S2:C-A:988-990、C-D CardInstance.cpp:177-184；R150；B-DYN/B-DIR |
| A03+ | Blood for Blood+1；扩展开发准入 | 费3，D22；同一降费规则 | UC1、BC3、D22、PC/RC、ATTACK/ENEMY | 同基础，需区分每实例而非按名称聚合 | 升级后印刷费3，战斗费用仍可降至0；重复实例独立 | N-T | OK-I / EVID | S2:C-A:988-990、C-F:201-203；R150；B-DYN/B-DIR |
| A04 | Bludgeon 基础；扩展开发准入 | 费3，D32，单体攻击 | UC0、BC3、D32、PC/RC、ATTACK/ENEMY | 目标敌人、力量和敌方减伤 | 无动态卡值 | N-T | OK-I / EVID | S2:C-A:992-994；R150；B-LEG；F938 |
| A04+ | Bludgeon+1；扩展开发准入 | 费3，D42，单体攻击 | UC1、BC3、D42、PC/RC、ATTACK/ENEMY | 同基础 | 只改变静态伤害 | N-T | OK-I / EVID | S2:C-A:992-994、C-F:207-208；R150；B-LEG；F938 |
| A05 | Body Slam 基础；扩展开发准入 | 费1，D=当前玩家格挡 | UC0、BC1、D=玩家当前 BLK、PC/RC | 玩家 block、Dexterity/Frail、敌方状态 | D 每个决策点随玩家 block 更新；无目标伤害预览进入模型 | N-T | OK-I / EVID | S2:C-A:984-986、C-F:213；R150；B-LEG |
| A05+ | Body Slam+1；扩展开发准入 | 费0，D=当前玩家格挡 | UC1、BC0、D=玩家当前 BLK、PC/RC | 同基础 | 升级只改变费用，动态 D 仍来自当前 block | N-T | OK-I / EVID | S2:C-A:984-986；R150；F938 |
| A06 | Carnage 基础；扩展开发准入 | 费2，D20，Ethereal | UC0、BC2、D20、ET=true、EX=false | 回合结束、玩家状态和敌人目标 | Ethereal 在回合末自动耗尽；不是固有 EX，不能混写 | N-T；回合末 AUTO | OK-I / EVID | S2:C-A:996-998、C-F:222、C-END BattleContext.cpp:2485-2489；R150；F938 |
| A06+ | Carnage+1；扩展开发准入 | 费2，D28，仍 Ethereal | UC1、BC2、D28、ET=true | 同基础 | 升级不能清除 ET；区域迁移由 AUTO 完成 | N-T；回合末 AUTO | OK-I / EVID | S2:C-A:996-998；R150；F938 |
| A07 | Clash 基础；扩展开发准入 | 费0，D14；只有手牌全为 Attack 才能打出 | UC0、D14、PC、ATTACK/ENEMY | 全部手牌的 card_type、合法 mask | 合法性随手牌变化；不需要隐藏历史 | N-T；mask 由环境判定 | OK-I / EVID | S2:C-A:1000-1002、C-D CardInstance.cpp:262-300；R150；B-DIR |
| A07+ | Clash+1；扩展开发准入 | 费0，D18；同一手牌类型条件 | UC1、D18、PC、ATTACK/ENEMY | 同基础 | 升级只改变 D；Havoc 自动路径另见 B02 | N-T | OK-I + B02 / EVID | S2:C-A:1000-1002、C-D:262-300；R150；B-DIR；Q |
| A08 | Cleave 基础；扩展开发准入 | 费1，AOE D8 | UC0、D8、AE=true、PC/RC、ATTACK/NO_TARGET | 所有 present/targetable 敌人、力量与伤害状态 | 不产生玩家逐目标选择；敌人死亡由后端推进 | N-S；AOE AUTO | OK-I / EVID | S2:C-A:1004-1007、C-F:208-209；R150；I300/I50 |
| A08+ | Cleave+1；扩展开发准入 | 费1，AOE D11 | UC1、D11、AE=true | 同基础 | 升级只改每目标基础伤害 | N-S；AOE AUTO | OK-I / EVID | S2:C-A:1004-1007；R150；F938 |
| A09 | Clothesline 基础；扩展开发准入 | 费2，D12，施加 Weak2 | UC0、D12、M2、PC/RC、ATTACK/ENEMY | 目标 Artifact/Weak、敌人 token | Weak 层数在敌 token，卡牌不保存隐藏计数 | N-T | OK-I / EVID | S2:C-A:1010-1013；R150；B-LEG；F938 |
| A09+ | Clothesline+1；扩展开发准入 | 费2，D14，Weak3 | UC1、D14、M3、PC/RC | 同基础 | 升级改变 D 与 Weak | N-T | OK-I / EVID | S2:C-A:1010-1013、C-F:209；R150；F938 |
| A10 | Dropkick 基础；扩展开发准入 | 费1，D5；目标 Vulnerable 时额外能量与抽1 | UC0、D5、M1、PC/RC、ATTACK/ENEMY | 目标 Vulnerable、No Draw、玩家能量/牌区 | 条件触发由后端按当前目标执行 | N-T；额外效果 AUTO | OK-I / EVID | S2:C-A:1021-1023、C-D Actions.cpp:1036-1047；R150；F938 |
| A10+ | Dropkick+1；扩展开发准入 | 费1，D8；同条件 | UC1、D8、M1、PC/RC、ATTACK/ENEMY | 同基础 | 只改变 D | N-T | OK-I / EVID | S2:C-A:1021-1023；R150；F938 |
| A11 | Feed 基础；扩展开发准入 | 费1，D10；致死且非 Minion/半死/Regrow 特殊条件时 maxHP+3，固有 Exhaust | UC0、D10、M3、EX=true、EE=true、PC/RC | 敌人 HP、block、Minion/half-dead/Regrow，玩家 HP/maxHP | 致死资格由后端判定；maxHP 结果进入 PLAYER_GLOBAL；源牌进入 EX | N-T；致死成长 AUTO | OK-I / EVID | S2:C-A:1025-1027、C-D Actions.cpp:1071-1089；R150；B-CHAIN |
| A11+ | Feed+1；扩展开发准入 | 费1，D12；致死 maxHP+4 | UC1、D12、M4、EX/EE=true | 同基础 | 只改变 D 与成长值；当前无额外 battle reward | N-T；AUTO | OK-I / EVID | S2:C-A:1025-1027、C-D:1071-1089；R150；B-CHAIN |
| A12 | Fiend Fire 基础；扩展开发准入 | 费2，固有 Exhaust；手牌每张 D7 | UC0、D7、EX/EE=true、PC/RC | 结算前完整手牌、Feel No Pain、Dark Embrace、Sentinel、敌人目标 | 后端先固定原手牌快照再逐张攻击/耗尽；不能把新抽牌混入快照 | N-T；耗尽 AUTO | OK-I / EVID | S2:C-A:1029-1031、C-D Actions.cpp:1092-1100；R150；B-FNL/B-POW |
| A12+ | Fiend Fire+1；扩展开发准入 | 费2；手牌每张 D10 | UC1、D10、EX/EE=true | 同基础 | 升级不改变手牌快照规则；与 Double Tap/Corruption 组合仍非穷尽证明 | N-T；AUTO | OK-I / EVID | S2:C-A:1029-1031、C-D:1092-1100；R150；B-FNL |
| A13 | Headbutt 基础；扩展开发准入 | 费1，D9；再从弃牌堆选1张置抽牌堆顶 | UC0、D9、PC/RC、ATTACK/ENEMY | 弃牌堆逐实例、敌人目标、已知顶牌 | 选中卡跨 discard→draw；KT 只标公开确定的第一张，抽走/洗牌清除 | N-T→SEL(HEADBUTT/discard) | OK-S；自动/重复路径附 B05 | S2:C-A:1042-1045、C-R public-battle-env.cpp:500-526；R150；B-SEL |
| A13+ | Headbutt+1；扩展开发准入 | 费1，D12；同一弃牌选择 | UC1、D12、PC/RC、ATTACK/ENEMY | 同基础 | KT 生命周期同基础；候选不合并重复牌 | N-T→SEL(HEADBUTT/discard) | OK-S；附 B05 | S2:C-A:1042-1045；R150；B-SEL |
| A14 | Heavy Blade 基础；扩展开发准入 | 费2，D14；Strength 总倍率3 | UC0、D14、M3、PC/RC、ATTACK/ENEMY | 玩家 Strength、敌人状态和目标 | 后端先加2×Strength再通用伤害函数加1×，合计3×；D为基础值 | N-T | OK-I / EVID | S2:C-A:1047-1051、C-F:215；R150；B-LEG/B-DYN |
| A14+ | Heavy Blade+1；扩展开发准入 | 费2，D14；Strength 总倍率5 | UC1、D14、M5、PC/RC | 同基础，负 Strength 也需保留 | 后端先加4×再通用函数加1×；M 是静态提示 | N-T | OK-I / EVID | S2:C-A:1047-1051；R150；F938 |
| A15 | Hemokinesis 基础；扩展开发准入 | 费1、失2HP、D15 | UC0、D15、M2、PC/RC、ATTACK/ENEMY | 玩家 HP、Rupture、BFB 费用、目标 | 自伤动作先于攻击；HP loss 由 PLAYER_GLOBAL 结果表达 | N-T；自伤 AUTO | OK-I / EVID | S2:C-A:1054-1059；R150；B-DIR |
| A15+ | Hemokinesis+1；扩展开发准入 | 费1、失2HP、D20 | UC1、D20、M2、PC/RC | 同基础 | 仅 D 变20，自伤仍2 | N-T | OK-I / EVID | S2:C-A:1054-1059；R150；B-DIR |
| A16 | Immolate 基础；扩展开发准入 | 费2，AOE D21；弃牌堆生成 Burn | UC0、D21、M1、AE=true、PC/RC | Burn token、敌人集合、Fire Breathing/Evolve | Burn 新实例进入 discard；生成非策略选择 | N-S；生成 AUTO | OK-I / EVID | S2:C-A:1061-1065；R150；F938 |
| A16+ | Immolate+1；扩展开发准入 | 费2，AOE D28；生成 Burn | UC1、D28、M1、AE=true | 同基础 | 升级只改变 D | N-S；AUTO | OK-I / EVID | S2:C-A:1061-1065；R150；F938 |
| A17 | Iron Wave 基础；扩展开发准入 | 费1，获得B5并D5 | UC0、D5、BLK5、BB5、PC/RC、ATTACK/ENEMY | 玩家 Dex、当前 block、目标 | 后端已修复重复 calculateCardBlock；D/BLK 不进入目标预览 | N-T；效果顺序 AUTO | OK-I / EVID | S2:C-A:1068-1071、C-F:196；R150；B-FNL |
| A17+ | Iron Wave+1；扩展开发准入 | 费1，获得B7并D7 | UC1、D7、BLK7、BB7、PC/RC | 同基础 | 升级同时改变伤害和格挡；Dex 只应用一次 | N-T | OK-I / EVID | S2:C-A:1068-1071；R150；B-FNL |
| A18 | Perfected Strike 基础；扩展开发准入 | 费2，D=6+2×当前 active Strike 数量 | UC0、D动态、M2、ST=true、PC/RC | 所有当前未耗尽 CARD token 的 ST、区域、玩家/敌人状态 | 后端 strikeCount 随生成、复制、耗尽更新；卡牌 D 输出当前公开动态值 | N-T | OK-I / EVID | S2:C-A:1080-1085、C-F:192、C-D Cards.h:512-531；R150；B-FNL |
| A18+ | Perfected Strike+1；扩展开发准入 | 费2，D=6+3×当前 active Strike 数量 | UC1、D动态、M3、ST=true | 同基础 | 升级只改变倍率；逐牌 token 可重算但不要求模型手算 | N-T | OK-I / EVID | S2:C-A:1080-1085；R150；B-FNL |
| A19 | Pommel Strike 基础；扩展开发准入 | 费1，D9，抽1 | UC0、D9、M1、ST=true、PC/RC | No Draw、牌区数量、敌人目标 | 抽牌可能洗牌；后端 AUTO，不公开隐藏顺序 | N-T；抽牌 AUTO | OK-I / EVID | S2:C-A:1088-1091；R150；F938 |
| A19+ | Pommel Strike+1；扩展开发准入 | 费1，D10，抽2 | UC1、D10、M2、ST=true | 同基础 | 升级改变 D/抽牌数 | N-T；AUTO | OK-I / EVID | S2:C-A:1088-1091；R150；F938 |
| A20 | Pummel 基础；扩展开发准入 | 费1，D2×4，固有 Exhaust | UC0、D2、H4、EX/EE=true、PC/RC、ATTACK/ENEMY | 目标、Strength、敌人状态、Exhaust triggers | 多次攻击同目标；生成后跨回合取回受 BLOCK-B01 | N-T；H 段数 AUTO | OK-I + BLOCK-B01 | S2:C-A:1093-1099、C-F:224；R150；B-FNL；Q |
| A20+ | Pummel+1；扩展开发准入 | 费1，D2×5，固有 Exhaust | UC1、D2、H5、EX/EE=true | 同基础 | 作为 Infernal Blade 生成牌时跨回合 Exhume 仍受 B01 | N-T；AUTO | BLOCK-B01（生成实例）；其他输入 OK | S2:C-A:1093-1099；R150；B-FNL；Q |
| A21 | Rampage 基础；扩展开发准入 | 费1，D8；每次该实例打出后 CB+5 | UC0、D=8+CB、M5、CB、PC/RC | Strength、目标、Double Tap、复制/牌区多重集 | 每个实例独立 specialData；复制保留 CB；双发第二击用更新值 | N-T；重复 AUTO | OK-I / EVID | S2:C-A:1102-1111、C-F:200；R150；B-DYN/B-FNL |
| A21+ | Rampage+1；扩展开发准入 | 费1，D8；每次 CB+8 | UC1、D=8+CB、M8、CB | 同基础 | 复制、Double Tap 与重复打出保持实例差异 | N-T；AUTO | OK-I / EVID | S2:C-A:1102-1111；R150；B-DYN/B-FNL |
| A22 | Reaper 基础；扩展开发准入 | 费2，AOE D4；按实际未格挡伤害治疗，固有 Exhaust | UC0、D4、AE=true、EX/EE=true、PC/RC | 敌人 HP/block、玩家 HP/maxHP | 治疗由后端实际未格挡伤害计算；不把名义 D 当治疗预览 | N-S；治疗/耗尽 AUTO | OK-I / EVID | S2:C-A:1114-1117、C-D:1129-1150；R150；B-CHAIN |
| A22+ | Reaper+1；扩展开发准入 | 费2，AOE D5；同治疗 | UC1、D5、AE=true、EX/EE=true | 同基础 | 多敌实际未格挡总量进入后端结果和玩家 HP | N-S；AUTO | OK-I / EVID | S2:C-A:1114-1117；R150；B-CHAIN |
| A23 | Reckless Charge 基础；扩展开发准入 | 费0，D7；抽牌堆加入 Dazed | UC0、D7、M1、PC/RC、ATTACK/ENEMY | Dazed token、牌堆、No Draw、目标 | 生成 Dazed 新实例；后续 Ethereal/状态触发 AUTO | N-T；生成 AUTO | OK-I / EVID | S2:C-A:1120-1123；R150；B-POW/F938 |
| A23+ | Reckless Charge+1；扩展开发准入 | 费0，D10；生成 Dazed | UC1、D10、M1 | 同基础 | 升级只改 D；Dazed 无升级 | N-T；AUTO | OK-I / EVID | S2:C-A:1120-1123；R150；F938 |
| A24 | Searing Blow 基础（+0）；扩展开发准入 | 费2，D12；支持多次升级公式 | UC0、BC2、D12、PC/RC、ATTACK/ENEMY | Strength、目标、Armaments | specialData=0 与 UC 同步；无隐藏 ID | N-T | OK-I / EVID | S2:C-A:1129-1133、C-D CardInstance.cpp:48-58,139-175；R150；B-FNL |
| A24+ | Searing Blow+1；扩展开发准入 | 费2，D16；12+1×(1+7)/2 | UC1、D16、PC/RC | 同基础 | +1 是正常升级版；多次升级按同一实例递增 | N-T | OK-I / EVID | S2:C-A:1129-1133；R150；B-FNL |
| A25 | Sever Soul 基础；扩展开发准入 | 费2，手牌全部非 Attack 耗尽，D16 | UC0、D16、PC/RC、ATTACK/ENEMY | 全手牌 card_type、Feel No Pain、Sentinel、Dark Embrace | 自动选择非 Attack；源牌不因该效果固有耗尽 | N-T；非攻击耗尽 AUTO | OK-I / EVID | S2:C-A:1136-1139、C-D:1200-1209；R150；B-CHAIN |
| A25+ | Sever Soul+1；扩展开发准入 | 费2，自动耗尽非 Attack，D22 | UC1、D22、PC/RC | 同基础 | 仅 D 改变，耗尽集合规则不变 | N-T；AUTO | OK-I / EVID | S2:C-A:1136-1139；R150；B-CHAIN |
| A26 | Strike_R 基础；扩展开发准入 | 费1，D6 | UC0、D6、ST=true、PC/RC、ATTACK/ENEMY | 目标、力量、敌人状态 | 普通重复牌独立；ST 参与 Perfected Strike | N-T | OK-I / EVID | S2:C-A:960-966、C-F:204-206；R150；B-LEG |
| A26+ | Strike_R+1；扩展开发准入 | 费1，D9 | UC1、D9、ST=true | 同基础 | 升级只改 D | N-T | OK-I / EVID | S2:C-A:960-966；R150；B-LEG |
| A27 | Sword Boomerang 基础；扩展开发准入 | 费1，随机敌人 D3×3 | UC0、D3、H3、PC/RC、ATTACK/NO_TARGET | 所有敌人；随机 RNG 不进入 token | H 是固定段数；随机目标 AUTO，不给策略选敌 | N-S；随机段 AUTO | OK-I / EVID | S2:C-A:1145-1149、C-D:1211-1221；R150；B-CHAIN |
| A27+ | Sword Boomerang+1；扩展开发准入 | 费1，随机敌人 D3×4 | UC1、D3、H4、PC/RC、ATTACK/NO_TARGET | 同基础 | 升级只增加随机段数 | N-S；AUTO | OK-I / EVID | S2:C-A:1145-1149；R150；B-CHAIN |
| A28 | Thunderclap 基础；扩展开发准入 | 费1，AOE D4，Vulnerable1 | UC0、D4、M1、AE=true、PC/RC、ATTACK/NO_TARGET | 敌人 Artifact/Vulnerable、全部敌人 | 伤害与易伤顺序由 AUTO；不增加目标动作 | N-S | OK-I / EVID | S2:C-A:1151-1155；R150；B-DIR |
| A28+ | Thunderclap+1；扩展开发准入 | 费1，AOE D7，Vulnerable1 | UC1、D7、M1、AE=true | 同基础 | 升级只改 D | N-S | OK-I / EVID | S2:C-A:1151-1155；R150；F938 |
| A29 | Twin Strike 基础；扩展开发准入 | 费1，D5×2 | UC0、D5、H2、ST=true、PC/RC、ATTACK/ENEMY | 目标、Strength、敌人状态 | 固定双段；不把段数交给玩家 | N-T；H AUTO | OK-I / EVID | S2:C-A:1158-1162；R150；F938 |
| A29+ | Twin Strike+1；扩展开发准入 | 费1，D7×2 | UC1、D7、H2、ST=true | 同基础 | 只改每段 D | N-T；AUTO | OK-I / EVID | S2:C-A:1158-1162；R150；F938 |
| A30 | Uppercut 基础；扩展开发准入 | 费2，D13，Weak/Vulnerable各1 | UC0、D13、M1、PC/RC、ATTACK/ENEMY | 目标 Artifact/Weak/Vulnerable | M=1 按 ID 解读为两种减益各一层；非通用效果向量 | N-T | DESIGN / EVID | S2:C-A:1165-1169；R150；Q generated output |
| A30+ | Uppercut+1；扩展开发准入 | 费2，D13，Weak/Vulnerable各2 | UC1、D13、M2、PC/RC、ATTACK/ENEMY | 同基础 | M=2 按 ID 解读为两种减益各2层 | N-T | DESIGN / EVID | S2:C-A:1165-1169；R150；F938 |
| A31 | Whirlwind 基础；X，AOE D5×X | UC0、BC=-1、D5、H1占位、AE=true、cost_kind=X | 玩家 energy、X 执行快照、敌人集合 | X 支付/命中次数/扣能量由后端；H 不是假预测 | N-S；X AUTO | OK-I / EVID | S2:C-A:1171-1177、C-F:194；R150；B-FNL |
| A31+ | Whirlwind+1；X，AOE D8×X | UC1、BC=-1、D8、H1占位、AE=true | 同基础 | 仅每段 D 改变 | N-S；AUTO | OK-I / EVID | S2:C-A:1171-1177；R150；B-FNL |
| A32 | Wild Strike 基础；扩展开发准入 | 费1，D12；抽牌堆加入 Wound | UC0、D12、M1、ST=true、PC/RC、ATTACK/ENEMY | Wound token、牌堆、目标、No Draw | 生成 Wound 进入 draw；后续状态由 AUTO | N-T；生成 AUTO | OK-I / EVID | S2:C-A:1180-1183；R150；B-POW/F938 |
| A32+ | Wild Strike+1；扩展开发准入 | 费1，D17；生成 Wound | UC1、D17、M1、ST=true | 同基础 | 升级只改 D；Wound 无升级 | N-T；AUTO | OK-I / EVID | S2:C-A:1180-1183；R150；F938 |

### 4.2 Skill（29 类，58 版本）

| 编号 | 卡牌与版本、准入 | 机制与决策需求 | 自身 token 字段 | 外部公开依赖 | 动态实例、区域、时序 | 动作表达 | 覆盖结论 | 核验依据 |
|---|---|---|---|---|---|---|---|---|
| S01 | Armaments 基础；扩展开发准入 | 费1，B5；选择1张可升级手牌 | UC0、BLK5、BB5、M0、PC/RC | 手牌每个实例的 UC/type；候选合法性 | 只升级选中实例；Searing Blow 的 UC 会递增 | N-S→SEL(ARMAMENTS/hand) | OK-S；+100 附 BLOCK-B03 | S2:C-S BattleContext.cpp:1210-1217、C-D Actions.cpp:678-698；R150；B-SEL |
| S01+ | Armaments+1；扩展开发准入 | 费1，B5；自动升级全部可升级手牌 | UC1、BLK5、BB5、M0、PC/RC | 全手牌逐实例 canUpgrade | 不制造选牌；但 canUpgrade 对 Searing+100 错误为真并抛异常 | N-S；全手牌 AUTO | BLOCK-B03；其他输入 OK | S2:C-S:1210-1217、C-D:901-907；R150；B-SEL；Q |
| S02 | Battle Trance 基础；扩展开发准入 | 费0，抽3并设 No Draw | UC0、M3、PC/RC | No Draw、牌区、手牌容量 | 抽牌 AUTO；源牌进入 discard | N-S；AUTO | OK-I / EVID | S2:C-S:1231-1234；R150；B-POW |
| S02+ | Battle Trance+1；扩展开发准入 | 费0，抽4并设 No Draw | UC1、M4、PC/RC | 同基础 | 只改变抽牌数 | N-S；AUTO | OK-I / EVID | S2:C-S:1231-1234；R150；F938 |
| S03 | Bloodletting 基础；扩展开发准入 | 费0，失3HP，+2能量 | UC0、M2、PC/RC、SKILL/NO_TARGET | 玩家 HP/energy、Rupture、BFB | 自伤触发 BFB/Rupture；结果公开 | N-S；AUTO | OK-I / EVID | S2:C-S:1244-1247；R150；B-DIR/B-POW |
| S03+ | Bloodletting+1；扩展开发准入 | 费0，失3HP，+3能量 | UC1、M3、PC/RC | 同基础 | 只改变能量 | N-S | OK-I / EVID | S2:C-S:1244-1247；R150；B-DIR |
| S04 | Burning Pact 基础；扩展开发准入 | 费1，选择耗尽1张并抽2 | UC0、M2、PC/RC | 手牌逐实例、Feel No Pain/Sentinel/Dark Embrace | hand→exhaust；抽牌可能改变 hand | N-S→SEL(EXHAUST_ONE/hand) | OK-S；Havoc/重复暂停附 B05 | S2:C-S:1249-1252、C-D:824-837；R150；B-SEL |
| S04+ | Burning Pact+1；扩展开发准入 | 费1，选择耗尽1张并抽3 | UC1、M3、PC/RC | 同基础 | 升级只改变抽牌量 | N-S→SEL(EXHAUST_ONE/hand) | OK-S；附 B05 | S2:C-S:1249-1252；R150；B-SEL |
| S05 | Defend_R 基础；扩展开发准入 | 费1，B5 | UC0、BLK5、BB5、PC/RC、SKILL/NO_TARGET | 玩家 Dex/Frail、当前 block | 无动态卡实例；源牌 discard | N-S | OK-I / EVID | S2:C-S:1202-1208；R150；B-LEG |
| S05+ | Defend_R+1；扩展开发准入 | 费1，B8 | UC1、BLK8、BB8、PC/RC | 同基础 | 升级只改 B | N-S | OK-I / EVID | S2:C-S:1202-1208；R150；B-LEG |
| S06 | Disarm 基础；扩展开发准入 | 费1，目标 Strength-2，Exhaust | UC0、M2、EX/EE=true、PC/RC、SKILL/ENEMY | 目标敌人 Strength/Artifact | 源牌进入 EX；目标减力在敌 token | N-T；减益 AUTO | OK-I / EVID | S2:C-S:1274-1276；R150；B-FNL |
| S06+ | Disarm+1；扩展开发准入 | 费1，目标 Strength-3，Exhaust | UC1、M3、EX/EE=true | 同基础 | 升级分支已改为 -3；不能与基础合并 | N-T | OK-I / EVID | S2:C-S:1274-1276；R150；B-FNL |
| S07 | Double Tap 基础；扩展开发准入 | 费1，本回合下一张 Attack 重复1次 | UC0、M1、PC/RC、SKILL/NO_TARGET | PLAYER_GLOBAL Double Tap 剩余次数、攻击计数 | 重复动作在 CardQueue；若重复牌产生选择，附 B05 | N-S；后续 AUTO | OK-I + B05 / EVID | S2:C-S:1283-1285、C-D:1600-1621；R150；B-FNL；Q |
| S07+ | Double Tap+1；扩展开发准入 | 费1，本回合接下来2张 Attack各重复 | UC1、M2、PC/RC | 同基础 | 待队列不公开，status 只剩余计数 | N-S；AUTO/可能 SEL | OK-I + B05 / EVID | S2:C-S:1283-1285、C-D:1613-1616；R150；B-FNL |
| S08 | Dual Wield 基础；扩展开发准入 | 费1，选 Attack/Power，复制1张 | UC0、M1、PC/RC、SKILL/NO_TARGET | 手牌 type、UC/CB/BC/FP/RT、容量 | 复制保留公开实例属性，分配新 ID；满手牌转 discard | N-S→SEL(DUAL_WIELD/hand) | OK-S；自动/重复暂停附 B05 | S2:C-S:1287-1289、C-D:701-753,2929-2975；R150；B-SEL/B-FNL |
| S08+ | Dual Wield+1；扩展开发准入 | 费1，复制2张 | UC1、M2、PC/RC | 同基础 | 两个副本逐实例保留；容量受保护 | N-S→SEL(DUAL_WIELD/hand) | OK-S；附 B05 | S2:C-S:1287-1289、C-D:2929-2975；R150；B-SEL |
| S09 | Entrench 基础；扩展开发准入 | 费2，当前 Block 翻倍 | UC0、BC2、BLK=当前 block、BB=当前 block、PC/RC | PLAYER_GLOBAL block、Dex/Frail、Barricade | BLK 是后端输入参数，不是结果2×预览；结果更新 global | N-S；AUTO | DESIGN / EVID | S2:C-S:1295-1297、C-D:1065-1069；R150；F938 |
| S09+ | Entrench+1；扩展开发准入 | 费1，当前 Block 翻倍 | UC1、BC1、BLK=当前 block、BB=当前 block | 同基础 | 只改变费用 | N-S | DESIGN / EVID | S2:C-S:1295-1297；R150；F938 |
| S10 | Exhume 基础；扩展开发准入 | 费1，选消耗堆1张回手，Exhaust | UC0、M1、EX/EE=true、PC/RC | exhaust_pile 逐实例、排除 Exhume、手牌容量 | exhaust→hand；实例费用/CB/UC原样保留；受 B01 | N-S→SEL(EXHUME/exhaust_pile) | OK-S + BLOCK-B01 | S2:C-S:1299-1301、C-D:755-781,3013-3020；R150；B-SEL；Q |
| S10+ | Exhume+1；扩展开发准入 | 费0，选消耗堆1张回手，Exhaust | UC1、M1、EX/EE=true、PC/RC | 同基础 | 被取回临时费用卡仍受 B01 | N-S→SEL(EXHUME/exhaust_pile) | OK-S + BLOCK-B01 | S2:C-S:1299-1301；R150；B-SEL；Q |
| S11 | Flame Barrier 基础；扩展开发准入 | 费2，B12，受击反伤4 | UC0、BLK12、BB12、M4、PC/RC | 玩家 Flame Barrier、Dex、敌人攻击 | 触发状态在 PLAYER_GLOBAL；回合边界清除 | N-S；AUTO | OK-I / EVID | S2:C-S:1312-1315、C-P:1548-1550；R150；B-POW |
| S11+ | Flame Barrier+1；扩展开发准入 | 费2，B16，反伤6 | UC1、BLK16、BB16、M6、PC/RC | 同基础 | 升级改变 block/反伤 | N-S | OK-I / EVID | S2:C-S:1312-1315、C-P:1548-1550；R150；F938 |
| S12 | Flex 基础；扩展开发准入 | 费0，Strength+2，本回合末-2 | UC0、M2、PC/RC | Strength、Lose Strength、回合 | 延迟减力由 PLAYER_GLOBAL 状态表达 | N-S；AUTO | OK-I / EVID | S2:C-S:1317-1319、C-P:396-404；R150；B-POW |
| S12+ | Flex+1；扩展开发准入 | 费0，Strength+4，本回合末-4 | UC1、M4、PC/RC | 同基础 | 升级改变两项数值 | N-S | OK-I / EVID | S2:C-S:1317-1319；R150；B-POW |
| S13 | Ghostly Armor 基础；扩展开发准入 | 费1，B10，Ethereal | UC0、BLK10、BB10、ET=true、PC/RC | 回合边界、Dex/Frail | hand→exhaust at end turn；不是固有 EX | N-S；AUTO | OK-I / EVID | S2:C-S:1322-1324、C-F:222；R150；B-LEG |
| S13+ | Ghostly Armor+1；扩展开发准入 | 费1，B13，仍 Ethereal | UC1、BLK13、BB13、ET=true | 同基础 | 升级不能去掉 ET | N-S；AUTO | OK-I / EVID | S2:C-S:1322-1324；R150；F938 |
| S14 | Havoc 基础；扩展开发准入 | 费1，自动打出抽牌堆顶牌并 Exhaust | UC0、M1、PC/RC、SKILL/NO_TARGET | draw_pile 多重集、KT、自动卡合法性/队列 | top→结算→EX；不可使用 top 会静默丢失；暂停缺 B05 | N-S；AUTO，可能 SEL | BLOCK-B02；暂停附 B05 | S2:C-S:1330-1332、C-D:2508-2522；R150；B-FNL；Q |
| S14+ | Havoc+1；扩展开发准入 | 费0，自动打出顶牌并 Exhaust | UC1、M1、PC/RC | 同基础 | 升级只改费用；B02/B05同样适用 | N-S；AUTO/可能 SEL | BLOCK-B02 + B05 | S2:C-S:1330-1332；R150；B-FNL；Q |
| S15 | Impervious 基础；扩展开发准入 | 费2，B30，Exhaust | UC0、BLK30、BB30、EX/EE=true、PC/RC | 玩家 Dex/Frail、block | 源牌进入 EX | N-S | OK-I / EVID | S2:C-S:1348-1350；R150；F938 |
| S15+ | Impervious+1；扩展开发准入 | 费2，B40，Exhaust | UC1、BLK40、BB40、EX/EE=true | 同基础 | 升级只改 block | N-S | OK-I / EVID | S2:C-S:1348-1350；R150；F938 |
| S16 | Infernal Blade 基础；扩展开发准入 | 费1，随机 Attack 入手，本回合0费，Exhaust | UC0、M1、PC/RC、SKILL/NO_TARGET | 随机28张 Attack 的 ID/type/target、hand容量 | 生成牌未升级、costForTurn=0；固有耗尽牌被 Exhume 跨回合取回受 B01 | N-S；生成 AUTO，之后可能 N-T→SEL | BLOCK-B01；生成闭包输入 OK | S2:C-S:1352-1354、C-D:571-577；R150；B-FNL；Q |
| S16+ | Infernal Blade+1；扩展开发准入 | 费0，随机 Attack 入手，本回合0费，Exhaust | UC1、BC0、M1、PC/RC | 同基础 | 生成牌仍未升级；B01不因源牌升级而消失 | N-S；AUTO/可能 SEL | BLOCK-B01 | S2:C-S:1352-1354；R150；B-FNL；Q |
| S17 | Intimidate 基础；扩展开发准入 | 费0，AOE Weak1，Exhaust | UC0、M1、AE=true、EX/EE=true、PC/RC | 敌人 Artifact/Weak、敌人集合 | 源牌进入 EX | N-S | OK-I / EVID | S2:C-S:1356-1358；R150；B-DIR |
| S17+ | Intimidate+1；扩展开发准入 | 费0，AOE Weak2，Exhaust | UC1、M2、AE=true、EX/EE=true | 同基础 | 升级改变 Weak | N-S | OK-I / EVID | S2:C-S:1356-1358；R150；B-DIR |
| S18 | Limit Break 基础；扩展开发准入 | 费1，Strength 翻倍，Exhaust | UC0、M2、EX/EE=true、PC/RC | Strength、负力量、Flex/Artifact | 基础源牌 EX；结果 Strength 公开 | N-S | OK-I / EVID | S2:C-S:1369-1371、C-D:1123-1127；R150；B-DIR |
| S18+ | Limit Break+1；扩展开发准入 | 费1，Strength 翻倍，不 Exhaust | UC1、M2、EX=false、EE=false、PC/RC | 同基础 | 版本差异只在源牌去向 | N-S | OK-I / EVID | S2:C-S:1369-1371、C-F:202；R150；B-DIR |
| S19 | Offering 基础；扩展开发准入 | 费0，失6HP，+2能量，抽3，Exhaust | UC0、M3、EX/EE=true、PC/RC | HP/energy/NoDraw、牌区、Rupture/BFB | 三个固定效果由 ID+M 解读；源牌 EX | N-S；AUTO | DESIGN / EVID | S2:C-S:1385-1389；R150；B-DIR/B-POW |
| S19+ | Offering+1；扩展开发准入 | 费0，失6HP，+2能量，抽5，Exhaust | UC1、M5、EX/EE=true、PC/RC | 同基础 | 升级只改变抽牌数 | N-S；AUTO | DESIGN / EVID | S2:C-S:1385-1389；R150；B-DIR |
| S20 | Power Through 基础；扩展开发准入 | 费1，B15，手牌加入2 Wound | UC0、BLK15、BB15、M2、PC/RC | Wound、hand/discard容量、Feel No Pain/Dark Embrace/Evolve/Fire Breathing | 满手牌时进入 discard；不静默丢弃 | N-S；生成 AUTO | OK-I / EVID | S2:C-S:1406-1410、C-D:227-236；R150；B-POW |
| S20+ | Power Through+1；扩展开发准入 | 费1，B20，加入2 Wound | UC1、BLK20、BB20、M2 | 同基础 | 升级只改变 block | N-S；AUTO | OK-I / EVID | S2:C-S:1406-1410；R150；F938 |
| S21 | Rage 基础；扩展开发准入 | 费0，本回合每打 Attack 得B3 | UC0、M3、PC/RC | Rage层数、attacks_played、玩家 block | 每次攻击触发，回合末清除 | N-S；AUTO | OK-I / EVID | S2:C-S:1416-1418、C-P:1636-1638；R150；B-POW |
| S21+ | Rage+1；扩展开发准入 | 费0，每次得B5 | UC1、M5、PC/RC | 同基础 | 升级改变每次 block | N-S | OK-I / EVID | S2:C-S:1416-1418；R150；F938 |
| S22 | Second Wind 基础；扩展开发准入 | 费1，耗尽手牌全部非 Attack，每张B5 | UC0、BLK5、BB5、PC/RC、SKILL/NO_TARGET | 手牌逐实例 card_type、Feel No Pain/Sentinel/Dark Embrace | 自动按类型筛选；逐牌触发 | N-S；AUTO | OK-I / EVID | S2:C-S:1420-1423、C-D:1178-1197；R150；B-CHAIN |
| S22+ | Second Wind+1；扩展开发准入 | 费1，每张B7 | UC1、BLK7、BB7、PC/RC | 同基础 | 只改变每张 block | N-S；AUTO | OK-I / EVID | S2:C-S:1420-1423；R150；B-CHAIN |
| S23 | Seeing Red 基础；扩展开发准入 | 费1，+2能量，Exhaust | UC0、M2、EX/EE=true、PC/RC | 玩家 energy、源牌 EX | 无额外选择 | N-S | OK-I / EVID | S2:C-S:1425-1427；R150；B-LEG |
| S23+ | Seeing Red+1；扩展开发准入 | 费0，+2能量，Exhaust | UC1、BC0、M2、EX/EE=true | 同基础 | 升级只改费用 | N-S | OK-I / EVID | S2:C-S:1425-1427；R150；F938 |
| S24 | Sentinel 基础；扩展开发准入 | 费1，B5；被耗尽时+2能量 | UC0、BLK5、BB5、M2、PC/RC | Sentinel实例、EX触发、energy | 不固有耗尽；被 EX 时触发 | N-S；触发 AUTO | OK-I / EVID | S2:C-S:1429-1431、C-D:209-214；R150；B-CHAIN/B-SEL |
| S24+ | Sentinel+1；扩展开发准入 | 费1，B8；被耗尽时+3能量 | UC1、BLK8、BB8、M3 | 同基础 | 升级改变 block/耗尽能量 | N-S | OK-I / EVID | S2:C-S:1429-1431；R150；B-CHAIN |
| S25 | Shockwave 基础；扩展开发准入 | 费2，AOE Weak/Vulnerable3，Exhaust | UC0、M3、AE=true、EX/EE=true、PC/RC | 敌人 Artifact/Weak/Vulnerable | 逐敌处理；源牌 EX | N-S；AUTO | OK-I / EVID | S2:C-S:1433-1436；R150；B-DIR |
| S25+ | Shockwave+1；扩展开发准入 | 费2，AOE Weak/Vulnerable5，Exhaust | UC1、M5、AE=true、EX/EE=true | 同基础 | 升级改变两种减益层数 | N-S | OK-I / EVID | S2:C-S:1433-1436；R150；B-DIR |
| S26 | Shrug It Off 基础；扩展开发准入 | 费1，B8，抽1 | UC0、BLK8、BB8、M1、PC/RC | NoDraw、牌区、玩家 Dex | 抽牌/洗牌 AUTO；源牌 discard | N-S | OK-I / EVID | S2:C-S:1438-1441；R150；B-LEG |
| S26+ | Shrug It Off+1；扩展开发准入 | 费1，B11，抽1 | UC1、BLK11、BB11、M1、PC/RC | 同基础 | 升级只改 block | N-S | OK-I / EVID | S2:C-S:1438-1441；R150；F938 |
| S27 | Spot Weakness 基础；扩展开发准入 | 费1；目标意图为 Attack 时 Str+3 | UC0、M3、PC/RC、SKILL/ENEMY | 选中敌人 intent、Artifact、玩家 Strength | 目标对应关系保留；触发 AUTO | N-T | OK-I / EVID | S2:C-S:1443-1445、C-D:1224-1229；R150；B-POW |
| S27+ | Spot Weakness+1；扩展开发准入 | 费1；条件成立 Str+4 | UC1、M4、PC/RC | 同基础 | 升级改变 Strength 增量 | N-T | OK-I / EVID | S2:C-S:1443-1445；R150；F938 |
| S28 | True Grit 基础；扩展开发准入 | 费1，B7，随机耗尽1张 | UC0、BLK7、BB7、M1、PC/RC | 手牌、Feel No Pain/Sentinel、随机结果 | 源牌 discard；随机耗尽 AUTO | N-S；AUTO | OK-I / EVID | S2:C-S:1475-1482、C-D:354-365；R150；B-LEG/B-SEL |
| S28+ | True Grit+1；扩展开发准入 | 费1，B9，玩家选耗尽1张 | UC1、BLK9、BB9、M1、PC/RC | 手牌逐实例候选、合法 mask | source resolving，选中 hand→exhaust，source discard；Havoc附 B05 | N-S→SEL(EXHAUST_ONE/hand) | OK-S；附 B05 | S2:C-S:1475-1482、C-R public-battle-env.cpp:500-526；R150；B-SEL |
| S29 | Warcry 基础；扩展开发准入 | 费0，抽1后选手牌置 draw 顶，Exhaust | UC0、M1、EX/EE=true、PC/RC、SKILL/NO_TARGET | 手牌、NoDraw、KT、牌区 | source EX；选中 hand→draw；只保留一个 KT | N-S→SEL(WARCRY/hand) | OK-S；重复/自动暂停附 B05 | S2:C-S:1488-1491、C-D:872-887；R150；B-SEL |
| S29+ | Warcry+1；扩展开发准入 | 费0，抽2后选手牌置顶，Exhaust | UC1、M2、EX/EE=true | 同基础 | 升级只改变抽牌数；KT生命周期相同 | N-S→SEL(WARCRY/hand) | OK-S；附 B05 | S2:C-S:1488-1491；R150；B-SEL |

### 4.3 Power（14 类，28 版本）

| 编号 | 卡牌与版本、准入 | 机制与决策需求 | 自身 token 字段 | 外部公开依赖 | 动态实例、区域、时序 | 动作表达 | 覆盖结论 | 核验依据 |
|---|---|---|---|---|---|---|---|---|
| P01 | Barricade 基础；扩展开发准入 | 费3，Block 不在回合开始清除 | UC0、M1、PC/RC、POWER/NO_TARGET | PLAYER_GLOBAL Barricade、block、回合 | 源牌进入 discard；block 跨回合 | N-S；AUTO | OK-I / EVID | S2:C-P BattleContext.cpp:1511-1513、C-F:321；R150；B-DYN/B-POW |
| P01+ | Barricade+1；扩展开发准入 | 费2，同语义 | UC1、BC2、M1、PC/RC | 同基础 | 升级只改费用 | N-S | OK-I / EVID | S2:C-P:1511-1513；R150；B-DYN |
| P02 | Berserk 基础；扩展开发准入 | 费0，Vulnerable2；后续每回合+1 energy | UC0、M2、PC/RC | PLAYER_GLOBAL Vulnerable、energy_per_turn、Artifact | 施加后下回合能量；脆弱层数公开 | N-S；AUTO | OK-I / EVID | S2:C-P:1515-1518、C-F:324-329；R150；B-POW |
| P02+ | Berserk+1；扩展开发准入 | 费0，Vulnerable1；同能量 | UC1、M1、PC/RC | 同基础 | 升级只改脆弱 | N-S | OK-I / EVID | S2:C-P:1515-1518；R150；B-POW |
| P03 | Brutality 基础；扩展开发准入 | 费0，每回合开始失1HP并抽1 | UC0、M1、PC/RC | Brutality、HP、牌区、Rupture/BFB/NoDraw | start-of-turn 自伤标记 selfDamage；能力源不在牌区 | N-S；回合 AUTO | OK-I / EVID | S2:C-P:1520-1522、C-PLAYER Player.cpp:682-688；R150；B-POW |
| P03+ | Brutality+1；扩展开发准入 | 费0，Innate，仍失1HP/抽1 | UC1、M1、PC/RC | 初始手牌/牌区、Rupture/BFB | Innate 影响 reset 抽牌位置；由 ID+UC 恢复 | N-S；AUTO | DESIGN / EVID | S2:C-P:1520-1522、C-F Cards.h:495-505；R150；B-POW |
| P04 | Combust 基础；扩展开发准入 | 费1，回合末失1HP，AOE D5 | UC0、M5、PC/RC、POWER/NO_TARGET | Combust status、combust_hp_loss、敌人、Rupture | 多张 Combust 的 D 总量与失血次数分别保留；无牌仍可 end turn | N-S；回合 AUTO | OK-I / EVID | S2:C-P:1528-1530、C-END Player.cpp:369-374；R150；B-DYN/B-FNL |
| P04+ | Combust+1；扩展开发准入 | 费1，回合末失1HP，AOE D7 | UC1、M7、PC/RC | 同基础 | 只改 AOE D；combust_hp_loss 仍每实例+1 | N-S；AUTO | OK-I / EVID | S2:C-P:1528-1530；R150；B-DYN/B-FNL |
| P05 | Corruption 基础；扩展开发准入 | 费3；Skills 本战斗0费并 Exhaust | UC0、BC3、M1、PC/RC | 每个 skill 的 type、费用、EX；玩家 Corruption | 后端把已有 skill 战斗费用变0；进入手牌时再次应用 | N-S；后续 Skill AUTO | OK-I / EVID | S2:C-P:1524-1526、C-D:540-574；R150；B-DYN/B-SEL |
| P05+ | Corruption+1；扩展开发准入 | 费2；同语义 | UC1、BC2、M1、PC/RC | 同基础 | 升级只改源牌费用，Skill effective 字段相同 | N-S | OK-I / EVID | S2:C-P:1524-1526；R150；B-DYN |
| P06 | Dark Embrace 基础；扩展开发准入 | 费2；每张牌 Exhaust 时抽1 | UC0、M1、PC/RC | Dark Embrace、NoDraw、所有耗尽来源 | 逐张触发；抽牌可能改变手牌和候选阶段 | N-S；触发 AUTO | OK-I / EVID | S2:C-P:1536-1538、C-D CardInstance.cpp:209-214；R150；B-POW/B-FNL |
| P06+ | Dark Embrace+1；扩展开发准入 | 费1；每张抽1 | UC1、BC1、M1 | 同基础 | 只改费用 | N-S | OK-I / EVID | S2:C-P:1536-1538；R150；B-POW |
| P07 | Demon Form 基础；扩展开发准入 | 费3；每回合开始 Str+2 | UC0、M2、PC/RC | Demon Form、Strength、turn | 当前 Strength 与能力层分别公开 | N-S；回合 AUTO | OK-I / EVID | S2:C-P:1532-1534、C-F:231；R150；B-POW |
| P07+ | Demon Form+1；扩展开发准入 | 费3；每回合 Str+3 | UC1、M3、PC/RC | 同基础 | 升级改变每回合增量 | N-S | OK-I / EVID | S2:C-P:1532-1534；R150；F938 |
| P08 | Evolve 基础；扩展开发准入 | 费1；抽到 Status 时额外抽1 | UC0、M1、PC/RC | Evolve、Wound/Dazed/Burn/Slimed、NoDraw | 触发发生在 draw；不把 Curse 当 Status | N-S；AUTO | OK-I / EVID | S2:C-P:1540-1542、C-D:400-440；R150；B-POW |
| P08+ | Evolve+1；扩展开发准入 | 费1；抽到 Status 时额外抽2 | UC1、M2、PC/RC | 同基础 | 升级改变每张状态额外抽牌数 | N-S | OK-I / EVID | S2:C-P:1540-1542；R150；B-POW |
| P09 | Feel No Pain 基础；扩展开发准入 | 费1；每张 Exhaust 得B3 | UC0、M3、PC/RC | Feel No Pain、block、EX事件 | 逐牌触发，不能从最终消耗堆计数差分 | N-S；AUTO | OK-I / EVID | S2:C-P:1544-1546、C-PLAYER Player.cpp:607-609；R150；B-POW/B-SEL |
| P09+ | Feel No Pain+1；扩展开发准入 | 费1；每张得B4 | UC1、M4、PC/RC | 同基础 | 升级改变每牌 block | N-S | OK-I / EVID | S2:C-P:1544-1546；R150；F938 |
| P10 | Fire Breathing 基础；扩展开发准入 | 费1；抽到 Status/Curse 时 AOE D6 | UC0、M6、PC/RC | Fire Breathing、card_type、敌人集合、状态/诅咒 | 抽到触发，不是打出触发；多次抽牌 AUTO | N-S；AUTO | OK-I / EVID | S2:C-P:1548-1550、C-D:418-440；R150；B-POW |
| P10+ | Fire Breathing+1；扩展开发准入 | 费1；同触发 AOE D10 | UC1、M10、PC/RC | 同基础 | 升级改变 D | N-S | OK-I / EVID | S2:C-P:1548-1550；R150；B-POW |
| P11 | Inflame 基础；扩展开发准入 | 费1，Str+2 | UC0、M2、PC/RC | 玩家 Strength | 结果 Strength 公开；不另造 Inflame 层 | N-S；AUTO | DESIGN / EVID | S2:C-P:1552-1554；R150；B-POW |
| P11+ | Inflame+1；扩展开发准入 | 费1，Str+3 | UC1、M3、PC/RC | 同基础 | 升级改变力量增量 | N-S | DESIGN / EVID | S2:C-P:1552-1554；R150；F938 |
| P12 | Juggernaut 基础；扩展开发准入 | 费2；每次获得 Block 随机敌人D5 | UC0、M5、PC/RC | Juggernaut、block、敌人 targetable | 所有 block 来源、敌人集合、随机 RNG；随机目标不进入动作 | N-S；随机 AUTO | OK-I / EVID | S2:C-P:1556-1558、C-PLAYER Player.cpp:68-79；R150；B-POW |
| P12+ | Juggernaut+1；扩展开发准入 | 费2；每次D7 | UC1、M7、PC/RC | 同基础 | 升级改变每次随机伤害 | N-S；AUTO | OK-I / EVID | S2:C-P:1556-1558；R150；B-POW |
| P13 | Metallicize 基础；扩展开发准入 | 费1，回合末B3 | UC0、M3、PC/RC | Metallicize、block、回合、Barricade/Juggernaut | 回合末 block；无牌仍可能继续战斗 | N-S；回合 AUTO | OK-I / EVID | S2:C-P:1568-1570、C-END BattleContext.cpp:2057-2063；R150；B-FNL/B-POW |
| P13+ | Metallicize+1；扩展开发准入 | 费1，回合末B4 | UC1、M4、PC/RC | 同基础 | 升级改变回合末 block | N-S | OK-I / EVID | S2:C-P:1568-1570；R150；F938 |
| P14 | Rupture 基础；扩展开发准入 | 费1；从卡牌失HP时 Str+1 | UC0、M1、PC/RC | Rupture、Strength、HP、Bloodletting/Hemokinesis/Offering/Brutality/Combust | selfDamage 来源由后端标记；不加入全历史 | N-S；AUTO | OK-I / EVID | S2:C-P:1576-1578、C-PLAYER Player.cpp:278-287；R150；B-POW |
| P14+ | Rupture+1；扩展开发准入 | 费1；同触发 Str+2 | UC1、M2、PC/RC | 同基础 | 升级改变每个自伤事件增量 | N-S | OK-I / EVID | S2:C-P:1576-1578；R150；B-POW |

## 5. Searing Blow 多次升级专项

当前 ironclad-registry.json 对 Searing Blow 的 max_upgrade=100，普通75×2台账仍只列 upgrade_count=0/1。因此把“基础/+1台账”和额外声明范围分开：

| 状态 | 当前观察 |
|---|---|
| +0 | reset 接受；D=12；UC token=0/5=0 |
| +1 | reset 接受；D=16；UC token=1/5=0.2 |
| +2 | reset 接受；D=21；UC token=0.4 |
| +5 | reset 接受；D=42；UC token=1.0 |
| +100 | reset 接受；D=5362；UC token=20.0，D token=107.24；没有裁剪到1 |
| +101 | 入口明确拒绝；没有 int16/JSON wrap |
| +100 + Armaments / Armaments+ | 真实探针触发 Searing Blow升级资源边界100；canUpgrade 判断没有把100视为终端，见 BLOCK-B03 |

公式在 third_party/sts_lightspeed/src/combat/BattleContext.cpp:1129-1133 与 bindings/public-battle-env.cpp:192-193 为：

 D(n) = 12 + n(n+7)/2。

CardInstance::upgrade() 在 CardInstance.cpp:144-148 对 specialData>=100 抛异常；canUpgrade() 在 CardInstance.cpp:56-60 对所有 Searing Blow 仍返回可升级。推荐保留 +0…+100 的已声明范围，把 +100 视为不可再升级的合法终端；不要把资源边界异常当作正常失败。

## 6. 辅助卡牌与共享公开状态补充

5 张辅助牌不计入75类/150版本，但当前统一词表、C++ cardRow 和若干当前卡牌链会产生或依赖它们。

| 辅助牌 | 可达/来源 | 自身 token 与区域语义 | 外部依赖和动作 | 当前结论 |
|---|---|---|---|---|
| AscendersBane | 可作为 A20/诊断初始牌；真实五遭遇不主动生成 | card_id=36、CURSE、ET=true、base_cost=-3；当前 cost_kind 错为 ENERGY | 当前8遗物无 Blue Candle，普通 mask 不给它可打动作；Havoc 顶牌仍可能弹出 | BLOCK-B04：分类只检查 c.cost==-2，应覆盖全部负的不可打出费用，X 先判 |
| Wound | Power Through、Wild Strike、敌人/诊断可产生 | card_id=37、STATUS、base_cost=-2、UNPLAYABLE；逐实例保留 | Evolve/Fire Breathing 抽到时触发；不能普通出牌 | 输入 OK；Havoc 顶牌静默丢失属于 BLOCK-B02 |
| Dazed | Reckless Charge、Three Sentries 等可产生 | card_id=38、STATUS、UNPLAYABLE、ET=true；回合末 AUTO 耗尽 | Evolve/Fire Breathing 与 Ethereal 时序 | 输入 OK；Havoc 顶牌同类风险 B02 |
| Burn | Immolate 可产生；回合末可触发自伤 | card_id=39、STATUS、UNPLAYABLE、M2；回合末触发 | Fire Breathing/Evolve、玩家 HP/Rupture/BFB | 输入 OK；Havoc 顶牌同类风险 B02 |
| Slimed | 词表/后端可编码；当前五遭遇不保证真实产生 | card_id=40、STATUS、费1、EX=true/EE=true | 特殊允许打出，打出后耗尽 | RAUX 已编码；具体敌人生成属于范围外 |

当前有关的玩家公开状态不展平成卡牌 token，而由 PLAYER_GLOBAL token 的具名状态和数字字段承载：Strength、Dexterity、Weak、Vulnerable、Frail、No Draw、Lose Strength；Barricade/Corruption 布尔活动状态；Combust 与独立 combust_hp_loss；以及 Double Tap、Rage、Feel No Pain、Dark Embrace、Evolve、Fire Breathing、Flame Barrier、Juggernaut、Metallicize、Rupture、Brutality、Demon Form 等具名数值状态。

当前8类遗物的直接影响落在这些公开结果中：Anchor/Lantern/Bag of Preparation 影响开局 block/energy/牌区，Vajra/Oddly Smooth Stone/Bronze Scales 影响 Strength/Dexterity/Thorns，Blood Vial 影响 HP，Burning Blood 在胜利出口影响 HP/reward。遗物 token 的 counter=null 当前不是遗漏，因为这8类没有被当前配置用于决策的动态计数；其他计数遗物不在范围内。

当前15类药水的 potion_id/name/potency/target_kind 进入 POTION token，药水使用通过 POTION_SELF/POTION_TARGET 及66位 mask。药水产生的 Strength/Dexterity/block/HP/敌人状态进入相应实体。新药水选择、药水丢弃/替换和 offer 生成不是本任务的当前准入。

## 7. 双向信息区分与实体—动作联合审计

### 7.1 已验证可区分的状态

- 两张 Rampage 的 CB 为0/5/8等不同值时，D 与 CB 分别保留，复制后的实例也能分别选择；见 tests/test_ironclad_dynamics.py:34-45、tests/test_ironclad_final_cards.py:151-157。
- Blood for Blood 的每个实例 BC 可随 HP loss event 下降，升级印刷费由 printed_cost/ID 区分；见 tests/test_ironclad_dynamics.py:47-58、tests/test_ironclad_direct.py:27-36。
- Perfected Strike 的动态 D 和当前 active Strike 的 ST 可见；消耗堆仍保留区域，不能与 active 牌混淆。
- Headbutt/Warcry 选择后的抽牌堆只有一个 KT=true；抽走和洗牌后清除；见 tests/test_ironclad_selection_cards.py:63-82。
- 实体置换同步 Candidate.source/target，route 保留动作身份；见 tests/test_unified_entities.py:40-56,127-164。
- 选择候选在手牌、弃牌堆、消耗堆之间按公开语义排序，后端索引只在模型外 route；见 sts/env/selection.py:52-103 与 tests/test_selection_routing.py:21-65。

### 7.2 已确认的联合接口缺陷

#### B02：Havoc 顶牌不可用时静默丢失实体

构造与真实轨迹：

1. 诊断牌组含 Havoc/Warcry/Wound。
2. 先用 Warcry 将 Wound 公开置于抽牌堆顶。
3. 执行 Havoc。
4. 探针输出：Havoc 前四区卡实体数为8，Havoc 后为7；Wound 不在手牌、抽牌堆、弃牌堆或消耗堆。

实现链为 Havoc → Actions::PlayTopCard（BattleContext.cpp:1330-1332）→ popFromDrawPile（BattleContext.cpp:2508-2522）。如果 c.canUse(..., inAutoplay=true) 为假，playCardQueueItem（BattleContext.cpp:841-861）既不执行 useCard，也不按 item.exhaustOnUse 或失败策略回收该牌。当前 Wound 因 STATUS 且没有 Medical Kit 为假。实际行为是静默丢牌，与资源保护约束冲突。

影响：Havoc 基础/升级、Wound/Dazed/Burn/AscendersBane；Clash 在手牌含非 Attack 时也可能触发同类路径；被 Entangled 等状态阻止的自动攻击需要另测。建议先以一手机制依据确定“自动打出不可用牌”的正确终点，再保证牌至少进入正确 discard/exhaust 或显式异常；不能丢弃也不能伪装成正常战败。

#### B03：Searing Blow+100 被错误判为可升级

实际轨迹：Searing Blow+100 + Armaments+1。Armaments 的 canUpgrade 过滤把该实例放进可升级候选，执行 CardInstance::upgrade 触发 Searing Blow升级资源边界100；Armaments 基础在候选中选择 +100 也触发。

影响：声明范围内的合法输入会在正常全手牌升级/单选时异常；不是模型输入无法表达，而是合法状态被后端错误拒绝。建议 canUpgrade 将 Searing Blow 的 specialData==100 判为 false，并保留 +100 作为可打出的终端版本；补基础/升级 Armaments、自动升级、单选与满手牌回归。

#### B04：AscendersBane 的费用类别错误

实际 RAUX 输出：AscendersBane 的 base_cost=-3、printed_cost=-3、cost_kind=ENERGY。public-battle-env.cpp:275 只把 c.cost==-2 归为 UNPLAYABLE，因此 -3 走普通能量分支；在非手牌区域 card_features（sts/env/entities.py:69-79）会把印刷费 -3 作为 pay_cost，而契约要求不可打出类别用 pay_cost=0 占位并由类别区分。

建议先判 isXCost，再对所有 c.cost<0 的非 X 类归 UNPLAYABLE；补五张辅助牌四区和 Havoc/Fire Breathing/Evolve 相关回归。CARD 115维布局不必改变，但后端/编码指纹和 checkpoint 必须更新。

#### B01：临时费用卡跨回合进入消耗堆后没有恢复

实际轨迹：Infernal Blade 生成 Pummel，输出本回合手牌 cost=0/base_cost=1/cost_scope=TURN；打出 Pummel 进入消耗堆；结束回合后 Exhume 选回。返回手牌仍为 cost=0/base_cost=1/cost_scope=TURN，不是下一回合应有的1费。

实现链为 Actions::InfernalBladeAction（Actions.cpp:571-577）设置 costForTurn=0，CardManager::resetAttributesAtEndOfTurn（CardManager.cpp:384-396）只重置 hand/discard/draw，没有 exhaust，chooseExhumeCard（BattleContext.cpp:3013-3020）原样返回实例。它影响 Pummel、Feed、Fiend Fire、Reaper 等可由 Infernal Blade 生成且固有耗尽的攻击牌。

建议在不把消耗堆的动态值丢弃的前提下，按当前费用契约在回合边界重置可被 Exhume 取回的实例；明确 free_to_play_once 与本回合临时费用的优先级。补“生成→固有耗尽→跨回合→Exhume→普通出牌/mask”的逐实例测试。

### 7.3 高风险但尚未声称同输入碰撞完成的缺口

CardQueueItem 公开结构包含 energyOnUse/freeToPlay/autoplay/purgeOnUse/exhaustOnUse（include/combat/CardQueue.h:20-31）。当前选牌暂停只导出 curCardQueueItem.card 作为 resolving CARD（bindings/public-battle-env.cpp:359-369），统一 token 只看到卡牌字段、区域和 selection_kind。因此以下两个状态类可达且有不同公开后果：

- 手动打出 Headbutt 后的 HEADBUTT 选择：无额外重复队列，源牌普通进入弃牌堆。
- Double Tap → Headbutt 或 Havoc → Headbutt/True Grit+ 的同类选择：已有重复/自动队列，源牌可能强制耗尽，选择完成后还可能再次进入选择。

本审计已运行：

- Double Tap 路径：第一次 HEADBUTT 选择后，完成一次选择仍返回第二个 HEADBUTT 选择；Double Tap status 已为0，当前 player/resolving token 没有 pending-replay 字段。
- Havoc 路径：自动打出 Headbutt 后真实进入 HEADBUTT 选择；resolving 只有 Headbutt 卡牌行。

这足以确认字段缺口和需要共同裁定的 Markov 边界；但本轮没有声称已经穷举出“所有其他公开标量逐项完全相等”的碰撞 witness。推荐新增有限的公开 resolution_context：只表达来源是手动/自动/重复、当前源牌是否会被强制耗尽、公开 X/费用快照和仍待处理的玩家选择数/种类，不暴露 queue 内部 ID、RNG 或完整隐藏队列。若不加入，则必须在契约中明确接受每步 Set/PPO 的部分可观测简化，不能把当前模型称作对这些暂停状态输入充分。

## 8. 核验命令与结果

本次执行过的关键命令：

    Set-Location C:\Users\19091\Desktop\sts2-full-card
    .\.venv\Scripts\python.exe -m pytest -q
    .\.venv\Scripts\python.exe scripts/check-ironclad-expansion.py
    .\.venv\Scripts\python.exe scripts/check-spec-v6.py

结果：

- 全仓：938 passed in 34.44s。
- 扩展账本检查：target_versions=150、legacy_admitted=69、expanded_admitted=150、frozen_files=7。
- 真实逐版本 reset/encode：150/150；ATTACK=64、SKILL=58、POWER=28；target_kind=ENEMY 56、NO_TARGET 94；cost_kind=ENERGY 148、X 2。主版本统计不含五张辅助牌。
- 辅助牌 reset/encode：5/5；另发现 AscendersBane 错误费用类别。
- 既有工程产物：300局逐版本集成 + 50局组合集成，不能代替定向探针，也不能证明组合穷尽。
- 没有启动正式 PPO；没有修改生产实现、输入契约、奖励或评估种子。

## 9. 最终解释

在不忽略四个阻塞项、也不把行为证据过度外推的前提下，75类150版本的“卡牌自身静态字段 + 当前公开状态 + 普通/单选动作语法”已逐版本登记。OK-I/OK-S 的含义是“输入路径存在并能表达当前可观察事实”，不表示所有卡牌组合、正版字节码等价、自动/重复暂停上下文完整、任意装备或完整 run 已支持。

阻塞项和需要共同审核的事项集中列在 docs/card-token-merge-review.md；本文件只记录，不修改实现或契约。

## 2026-09-13修复复核追加

以下状态追加在原逐卡审计之后，原审计中的修复前反例保留为历史证据：

- B01：消耗堆实例跨回合恢复已接入；同回合免费、跨回合原费用、实际支付和合法mask已有成对回归。
- B02：Havoc的不可执行自动顶牌进入耗尽触发链，五类定向牌不再从四区静默丢失；这不等价于所有自动打出机制或所有卡组组合已穷举。
- B03：+100继续可构造，`canUpgrade`过滤与资源边界一致；+100之后的工程资源限制保留为已知限制，不作为本轮阻塞。
- B04：X与负费用不可打出类别先后判定已修；CARD token维度未变。
- B05：普通卡牌字段未新增流程信息。公开暂停上下文进入候选评分器，字段和公开边界见`docs/entity-input-v3-contract.md`；旧输入/模型/checkpoint不作精确恢复。
