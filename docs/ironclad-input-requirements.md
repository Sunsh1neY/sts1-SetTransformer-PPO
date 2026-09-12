# Ironclad 全卡输入与动作新增需求汇总

日期：2026-09-12。性质：当前源码静态审计、公开入口抽查与未来接口建议；不是扩卡准入、机制验收或训练启动。逐卡覆盖见 [150 版本审计表](ironclad-input-audit.md)。

**快照边界补记（13:13，Asia/Shanghai）**：本轮起始工作树为空；审计进行中另一路写入了 `sts/env/comparison.py`、`sts/env/comparison-contract.json`、`sts/models/comparison.py` 与生成脚本。已只读检查：新草稿包含共享逐牌编码、MLP/Set网络、66位输出和容量切段包装，不应再称“工作区不存在新模型实现”。下文I6/I7和差异表中的“旧模型/旧collector”明确指起始已提交路径；I10记录新增草稿。其完整集成、训练、恢复及容量证明不在本次验收内，本次没有修改这些文件。

## 1. 结论与适用边界

支持全部战士卡牌需要同时补齐内容注册、公开状态、动态实例语义和多阶段动作；只增加 card_id 或扩大 Set token 数不足以完成扩展。当前 35 类战士牌仅开放 **69 个基础/升级版本**：True Grit 只开放基础版；另有 5 类辅助牌。因此相对于 75 类、150 个战士版本，尚有 **40 类、81 个版本未准入**。这与“模型已验收69版本”不同：起始MLP和 PPO 路径仍接旧 minimal 输入，新M3草稿的验收状态见上述快照补记。

现有语义可复用的部分包括四区逐牌记录、整数升级次数、类型、费用已知标记、伤害与格挡、逐目标伤害、状态字典、回合出牌计数、敌人公开历史、遗物和药水记录以及66位mask。多数直接伤害、格挡、抽牌和数值状态效果不需要新实体类型；但需要新增卡牌分支、严格字段字典和模型编码。

本报告保持 comparison-battle-v1 冻结范围：27种中途卡组、75run、第一幕A20、五种遭遇、两套配置。用户本轮确定双方逐牌表示、相同信息与容量、各2次独立正式训练、相同环境交互步数，正式训练与评估累计30分钟；这些是后续实施约束，本次不消耗正式训练预算。卡牌实体容量截断仍是设计项，不把下文建议当成已批准的新终止规则。

全75卡在现有遗物/药水子集下的支持，与“支持全游戏所有遗物、药水、无色牌及跨角色牌”是不同范围。本报告覆盖前者的必要依赖，并为后者列出条件性接口需求，不默认扩展所有内容。

## 2. 现有实现位置与证据等级

以下定位使用文件和函数名，避免历史补丁行号漂移。逐卡表另附当前结算case行号。

| 编号 | 现有实现位置 | 本次核对内容与局限 |
|---|---|---|
| I1 | `sts/env/public-battle-contract.json` | 35战士、5辅助、8遗物、15药水；True Grit max_upgrade=0；66动作；初始牌≤96、512动作、每动作生成界15、累计实体界7776。该界仅适用当前闭包。 |
| I2 | `third_party/sts_lightspeed/bindings/public-battle-env.cpp` 的 `cardRow/pileRows/observeJson` | cardRow只处理已登记卡；其他卡抛错。非手牌排序，cost=0且cost_known=false，但base_cost仍输出c.cost。玩家状态循环不是全状态语义正确性的证明。 |
| I3 | 同文件 `verifyDecision/actionMask/step/resetScene` | 非终局只接受PLAYER_NORMAL；出现CARD_SELECT直接拒绝。手牌、药水、结束回合可寻址，不能选择弃牌/消耗堆卡。入口限制卡种和升级。 |
| I4 | `sts/env/public_battle.py` 的 `normalize_observation/reset/step` | 依中央表映射项目ID，拒绝未知卡/升级/旧mask；再次排序非手牌；不提供选择句柄、公开牌顶记忆或跨阶段事务。隐藏字段检查不等于所有已导出字段都已完成可见性证明。 |
| I5 | `sts/env/real_deck.py`、`sts/env/real-deck-batch.json` | 固定来源分组、配置与采样；加载绑定中央契约hash。扩卡不能静默改旧契约，使冻结批次失效。 |
| I6 | `sts/env/wrappers.py` 的 `_prepare`，`sts/models/mlp.py` | 仍导入旧lightspeed/registry，牌特征为card_id/location/target_kind/upgraded及cost，非手牌容量10；MLP head仍取旧ACTION_COUNT=31；没有public语义张量路径。`TokenWrapper`存在不等于Set网络已实现。 |
| I7 | `sts/train/ppo.py` 的 `RolloutCollector`、MLP checkpoint函数 | collector仍构造FlattenWrapper(LightspeedBattleEnv)，按旧遭遇reset；GAE已有终止/截断区分，但public配置、66动作、可变候选和新checkpoint未接入。 |
| I8 | `third_party/sts_lightspeed/src/combat/{BattleContext,Actions,CardInstance,CardManager,Player}.cpp` 及对应头文件 | 上游实现来源，75个case存在只证明静态入口；不是正版一致性或项目入口行为通过。 |
| I9 | `third_party/sts_lightspeed/src/sim/search/Action.cpp` 的单/多选合法性与执行函数 | 上游已有CARD_SELECT及选择helper；其索引不能直接用于经过公开排序的牌堆。 |
| I10 | 本轮并发新增的 `sts/env/comparison.py`、`sts/env/comparison-contract.json`、`sts/models/comparison.py`、`scripts/prepare-comparison-contract.py` | 13:13静态快照：schema为comparison-battle-v2，实体64、切段阈值57、生成余量8、10手牌＋64非手牌布局；encode逐字段校验，MLP/Set共享编码，手牌输出50＋其他16。仅确认草稿代码存在，不批准这些容量数字、不宣称PPO/checkpoint迁移通过；R01–R11全卡扩展缺口仍在。 |

来源编号沿用“可信度＋核验日期”的登记方式：

- [S1] 高，一手本机正版，2026-09-12：`E:/SteamLibrary/steamapps/common/SlayTheSpire/desktop-1.0.jar`；重新核对75个red类、英文cards.json及文件SHA256。逐卡数值采用已有M1的构造器/upgrade/use审计，本次不声称重新执行150次正版字节码数值核验。完整hash见逐卡表。
- [S2] 高，一手当前实现，2026-09-12：I1–I9当前工作树源码；是“当前代码是什么”的依据，不能替代正版机制依据。当前HEAD、关键文件hash见逐卡表。
- [S3] 项目既有一手核验记录，核验日期2026-09-11：[原审计](ironclad-card-audit.md)、[复核](ironclad-card-audit-review.md)、[候选批次](m1-candidate-batches.md)、[十卡数值](m1-numeric-evidence.md)。只继承数值/规则证据及未关闭争议，不继承其中已经过时的31动作、3牌registry等“当前”描述。
- [S4] 项目当前冻结与开发集成记录，2026-09-12：[对照边界](mlp-set-comparison-boundary.md)、[M3报告](real-deck-m3-report.md)、`docs/decisions.md`末尾裁定。540局为既有报告证据，本次没有重跑，也不升级为全卡测试。

## 3. 新增需求台账

表中“必需”指对应扩展被开放时必须解决，不表示本轮MLP立即扩展。逐卡表引用R编号；未准入版本统一依赖R01，所有模型接入统一依赖R12。

| 编号 | 对应卡牌/关联 | 当前位置与缺失 | 建议表达、影响与验收依据 |
|---|---|---|---|
| R01 内容与静态语义 | 全部未登记40类、True Grit+；生成卡闭包 | I1/I2/I4入口及cardRow拒绝；不能靠ID新增一行就运行 | 版本化扩充卡表、升级范围和语义计算；登记抽牌数、自伤量、触发类型等多效果语义，或用card_id＋upgrade_count无损查静态字典。单一magic不是所有效果的统一含义。静态可推导属性是便利特征，不强制重复加字段。S1/S3逐卡数值与I8逐分支核对。 |
| R02 动态实例与费用 | Rampage、Blood for Blood、Searing Blow、Armaments、Dual Wield、Infernal Blade；Corruption、Havoc、Whirlwind | I2未读Rampage.specialData；upgrade_count已有但入口仅0/1；非手牌costForTurn被隐藏；doesExhaust仅为卡片固有属性 | 显式combat_damage_bonus或完整当前伤害及其增长语义；整数upgrade_count可复用但须放宽有界准入；区分基础费用、战斗修改费、当前回合有效费、X/不可打出费用种类、免费标记及生效期限。Corruption的内部-9不得当普通负能量。复制/移区/升级后动态值继承必须测试。未知费用不补零为事实；审清可见性后有known标记地输出。不得直接输出无语义specialData或uniqueId。 |
| R03 状态语义与延迟效果 | Barricade、Corruption、Combust、Berserk、Brutality、Double Tap、Dark Embrace、Evolve、Fire Breathing、Juggernaut、Rupture；已有Flex/Rage等 | I2通用循环复用状态字典；I8 Player::buff中Barricade/Corruption只设bit，getStatusRuntime会statusMap.at；Combust失血另在combustHpLoss | 对布尔/数值/剩余次数/回合期限分类导出；Barricade/Corruption用明确bool，避免数值map异常；Combust同时表达伤害总量和每回合失血量。Double Tap剩余触发次数、Berserk与energy_per_turn关系、状态过期时机需验证，不把通用字典当已覆盖。Inflame只需Strength，无须再造Inflame层。 |
| R04 决策阶段与单选对象 | Armaments基础、Burning Pact、Dual Wield、Exhume、Headbutt、Warcry、True Grit+ | I3禁止CARD_SELECT；I9已有helper但未绑定；66位无对象出口 | 新增phase、selection_kind、source_card语义、candidate_zone、候选逐实例列表、candidate_mask、所需数量和可确认条件；动作SELECT_CARD(候选引用)。弃牌/消耗堆可超过10，不套用手牌10槽。Exhume排除Exhume；Armaments仅可升级；Dual Wield仅Attack/Power。空候选/唯一候选自动处理必须与正版一致，不能自动代选多个合法对象。 |
| R05 实体对应与公开区域 | 上述选牌、复制、所有重复牌；Perfected Strike、Fiend Fire、Havoc | I2/I4非手牌按公开字段排序，没选择映射；四区不含暂停结算中的正在打出牌 | 在适配器保存“本次观测候选位置→后端对象”映射和decision_id；语义token不含隐藏实例ID或手牌槽位编号。候选引用只作动作路由。相同名称但不同动态值分别保留；完全相同牌也不合并。只有暂停阶段确有公开的正在结算牌时新增resolving实体/区域，不能把内部全部队列或牌序曝光；容量计算仍覆盖内部存活对象。 |
| R06 公开历史与已知牌序 | Headbutt、Warcry→Havoc/所有抽牌；Perfected Strike；临时费用记忆 | I2/I4只保留无序牌堆；敌人已有有限public_history，玩家无牌顶记忆 | 维护由玩家已见动作产生的known_top序列/部分顺序约束，记录移顶、已知抽取、洗牌失效；随机插入后不得继续假装原牌仍必定第一张。不得读取实际隐藏顶牌来补字段。Perfected Strike优先由有效区域及is_strike字典推导计数，排除消耗堆，并核验正在结算牌计入时点；不是另加完整出牌历史。卡牌公开动态值已足够时不强制RNN/全历史。 |
| R07 间接打出与复制闭包 | Havoc、Double Tap、Infernal Blade→Headbutt等；Dual Wield复制动态牌 | I8有autoplay/freeToPlay/energyOnUse/purge等队列上下文；I3拒绝额外决策 | 环境执行随机目标和自动结算；只把实际需要玩家选择的暂停点交给策略。phase上下文包括公开来源、强制消耗、复制/自动打出语义及公开X快照（确有决策时）；不让玩家选择内部随机结果。Havoc×所有可达卡、Double Tap×Headbutt/Fiend Fire/Rampage/Whirlwind必须闭包核验。Infernal Blade不能缩减生成池绕过Headbutt。 |
| R08 生成与容量、采集切段 | Anger、Dual Wield、Infernal Blade、Immolate、Power Through、Reckless Charge、Wild Strike；连锁复制/抽耗 | I1/I3只证明当前每动作15与7776；新增效果后无通用上界 | 重新证明单个外部动作直到下个合法决策点的生成界及累计ID上界；活跃实体数与累计nextUniqueCardId分开计数。阈值截断应留出最坏原子动作余量，不在超出容量后丢牌，不在无合法决策的半队列处强行截断。最终观测必须完整可编码、自举，且GAE不跨reset；无限连锁/后端异常不能标正常失败或无损截断。 |
| R09 目标与效果种类 | Sword Boomerang、Whirlwind、Juggernaut、Reaper、Feed、Fiend Fire、Perfected Strike | I2 damage_by_target固定5列、hits默认1；target_kind仅ENEMY/NO_TARGET；当前分支不含这些卡 | 固定游戏规则可由ID恢复随机/全体/多段/实际HP伤害治疗/致死增最大HP；必要时显式target_mode、hit_count_mode、effect_kind供编码。随机目标不增加玩家选敌动作；Whirlwind不增加玩家X选择。Feed须核验Minion/半死/可触发Fatal条件，若扩怪物则增加对应公开状态；Reaper不能把名义伤害当实际治疗。 |
| R10 遗物、药水与额外实体（条件性） | 见第5节；所有卡均可受适用修饰 | I2遗物counter一律null；parseRelic只8类、药水只15类；无抽选候选、药水丢弃出口 | 在当前8/15子集可复用记录；扩充时加入公开计数/本回合已触发标记、动态potency/可用槽。选择药水可能需要offer实体或多选阶段；补生成/奖励获取时的丢弃药水出口。按实际可达闭包注册无色/诅咒/状态牌，不以“全75战士”宣称其他内容自动支持。 |
| R11 机制差异与证据阻断 | Disarm+、Iron Wave、Fiend Fire、Dual Wield、Exhume、Combust、Rampage×Double Tap | I8仍见Disarm固定-2、Iron Wave双重calculateCardBlock；其他路径有队列/复制注释或独立状态 | 前两项是当前静态差异定位；其余是需行为仲裁的风险，不把TODO直接当已证实Bug。逐项做正版定点证据＋基础/升级＋组合回归；输入完整不能修复错误转移。未关闭前不得写“全卡语义通过”。 |
| R12 双模型、PPO与版本 | 本轮所有公开字段；未来Set选择/扩容 | I6/I7仍旧输入、31head、旧collector与checkpoint | 本轮先接共享数值字典、known/valid/type mask、逐牌布局、66动作；冻结词表/归一化/容量并测吞吐。Set实体输出保留到手牌×目标/药水×目标的路由，池化只作上下文/价值。未来扩展用候选打分头支持选择，保存每步phase/候选映射/旧logprob/mask及final_obs。checkpoint绑定环境/动作/观测/内容/容量/编码/后端/奖励/批次hash；旧权重拒绝直接恢复，显式迁移另留记录。 |

## 4. 必须区分的信息与模型便利特征

**不能由当前公开快照恢复的信息**包括未导出的Rampage实例增伤、Combust失血量，以及没有记录的已知置顶历史。前两项可通过命名动态字段解决；后者可维护公开记忆，不应访问隐藏抽牌顺序。Barricade/Corruption则是已有容器的导出语义缺陷，不需要发明另一套Power实体。

可辨识性反例：按现有后端叠加路径，7次基础Combust与5次升级Combust都可累计35伤害，却分别累计7和5的回合失血量；只编码伤害状态不能区分。两张Rampage若独立打出次数不同，也不能只用同一个card_id/upgrade_count表示。Headbutt放顶A与放顶B可以产生相同无序抽牌堆，却有不同的公开已知下一抽。这些是静态构造的需求反例，不是本次已运行的组合测试。

直接需要单选出口的是7类、12版本：Armaments基础、True Grit升级，以及Burning Pact/Dual Wield/Exhume/Headbutt/Warcry各两版。Havoc与Infernal Blade另有间接可达依赖，不能把它们误写为每次打出都必须主动选择；Double Tap亦需检查重放后实际出现的选择点。全75战士本身不要求通用多选，相关药水/遗物开放后才加入对应出口。

**可由静态字典和当前状态推导的信息**包括卡牌类型、是否含Strike、固定自伤量、Innate（例如Brutality+）、升级后的固定抽牌数，以及大多数触发规则。可以显式作为输入便利特征，但不能称它们都是信息缺口。Searing Blow已有整数upgrade_count字段，缺的是入口范围和数值计算；并非仍只有旧bool。

**不能仅看一张牌判断的信息**包括Clash的全部手牌类型、Perfected Strike的有效牌区组成、Fiend Fire/Second Wind/Sever Soul的当时手牌集合、Rupture的卡牌自伤来源以及目标相关伤害。所有这些都要求完整多重集和状态；相同牌不能聚合掉。标准决策点若队列已结算，失血来源通常由规则执行并反映在Strength等结果中，不需额外让模型读取内部伤害日志。暂停决策时才需公开且相关的结算上下文。

`damage_by_target`并非执行结果oracle：随机目标、护甲/多段之间触发、伤害后的治疗和队列顺序仍应由环境推进。未来动态预览必须只依玩家当前可见状态，不预读RNG、抽牌结果或敌人下一意图。

## 5. 卡牌间及遗物/药水关联检查

| 关联路径 | 最低输入/动作要求 | 证据与边界 |
|---|---|---|
| Body Slam/Entrench/Barricade＋格挡牌、Rage、Feel No Pain、Metallicize、Juggernaut | 当前block、Dexterity/Frail及活动状态；区分每次获得格挡与最终总格挡；结束回合持留 | I2/I8；Barricade导出须R03修复。 |
| Strength链：Inflame/Flex/Spot Weakness/Limit Break/Demon Form/Rupture＋Heavy Blade/多段攻击 | 有符号Strength、LoseStrength、剩余期限、每段伤害；Weak/Vulnerable/Artifact；负力量不可clamp为0 | 现有状态字段可复用，组合机制未因单卡可表达而验收。 |
| 消耗链：True Grit/Burning Pact/Fiend Fire/Second Wind/Sever Soul/Corruption/Ethereal＋Sentinel/Feel No Pain/Dark Embrace/Exhume | 当前实例类型/区域、耗尽触发状态、选择候选；Dark Embrace带来的抽牌及NoDraw；Exhume选择禁选自身类别 | I8/I9；Fiend Fire耗尽和命中次数的快照时机是R11回归重点。 |
| 状态/诅咒链：Immolate/Power Through/Reckless Charge/Wild Strike/敌人生成＋Evolve/Fire Breathing | Burn/Wound/Dazed等逐实体；区分Status与Curse，抽到触发与回合末触发不同；AscendersBane不因是辅助牌被遗漏 | I1/I8 CardManager::draw；当前5辅助够当前闭包，不等于所有状态/诅咒齐全。 |
| 自伤链：Bloodletting/Hemokinesis/Offering/Brutality/Combust/Burn＋Blood for Blood/Rupture/Reaper/Feed | HP/max_hp、每实例战斗费用、来源相关触发、Combust失血量、实际治疗；战斗出口HP分母随Feed改变 | I8 Player::hpWasLost及各Actions；Rupture触发归后端执行，不能以所有掉血都触发代替。 |
| 置顶/生成/复制链：Headbutt/Warcry→Havoc；Infernal Blade→Headbutt；Double Tap→Headbutt/Rampage/Fiend Fire | R02/R04–R08，保留公开置顶记忆、重复牌动态差异、队列暂停及生成上界 | I8/I9；Havoc的自动播放究竟在哪些正版路径产生玩家选择，须按实际可达路径核验，不笼统让所有自动播放都多一次决策。 |
| 当前遗物：Vajra/Oddly Smooth Stone/Anchor/Lantern/Bag of Preparation/Bronze Scales/Blood Vial/Burning Blood | 现有Strength/Dexterity/block/energy/牌数/Thorns/HP和遗物ID足够承载直接效果；出口治疗已纳入当前reward | I1/I2及当前报告。冻结对照只含其中Burning Blood/Anchor/Vajra，不把8类能力全写为对照覆盖。 |
| 当前药水：Strength/Dexterity/Speed/Ancient/Weak/Fear/Block/Steel/Heart/Regeneration/Liquid Bronze/Energy/Swift/Fruit Juice/Explosive | 药水ID/potency、真实2槽、目标、相关状态及期限；Flex/Speed与Artifact、Swift与NoDraw、Block与Juggernaut等需组合回归 | 15类登记名称以I1为准；本轮配置仅Block/Weak。现有动作已能使用，无须为直接药水增加阶段。 |
| 未来计数或触发遗物：Pen Nib、Nunchaku、Ink Bottle、Happy Flower、Sundial、Necronomicon、Orange Pellets | 公开计数/已用标记/本回合卡类型集合；多段/重放、洗牌次数与抽耗链 | I8 Player.h存在相关数据成员；这些遗物未准入，具体正版触发与可见性仍须逐项核验，不能直接全量dump内部成员。 |
| 未来规则修饰：Chemical X、Snecko Eye、Runic Pyramid、Dead Branch、Charon's Ashes、Medical Kit、Blue Candle、Tungsten Rod、Torii、Magic Flower、Mark of the Bloom | X规则、费用期限、保留、随机生成池、状态/诅咒可打出、自伤/受击来源及治疗修饰的完整规则闭包 | 条件性扩展检查清单，具体支持和全组合行为[未核实]；不属于当前8遗物。它们说明仅75卡词表不足以支持任意装备。 |
| 未来选择/生成药水：Attack/Skill/Power Potion、Liquid Memories、Gambler's Brew、Elixir、Duplication Potion | 牌候选offer、弃牌回收、可变数量选择＋确认、重复打出次数；药水获得/替换才需丢弃出口 | I9有DISCOVERY/LIQUID_MEMORIES/GAMBLE/EXHAUST_MANY路径；全部尚未绑定当前public入口。75战士自身不因此强制要求多选/药水丢弃。 |

后两类的列举是接口压力清单，不是所有遗物/药水机制的穷尽审计；若未来配置声明“任意遗物药水”，必须另行完成完整内容清单和可达闭包审计。

## 6. 当前实现、本轮M3与未来Set的接口差异

| 接口 | 当前实现 | 本轮固定环境M3目标 | 对照后未来Set扩展 |
|---|---|---|---|
| 环境/内容 | public环境35战士＋5辅助；模型仍minimal | comparison-battle-v1，冻结27种卡组和配置 | 新environment/content版本；不能原位替换冻结契约 |
| 卡牌输入 | public具名变长；旧wrapper仅旧字段/小容量 | 双方完整逐牌，相同公开字段和容量，重复状态牌占位 | 继续逐实体，新增动态字段、候选offer及公开resolving状态（需要时） |
| 牌序 | 非手牌排序；无公开置顶记忆 | 保持既有信息边界 | 已知顺序关系另编码；未知真实顺序仍隐藏，Set不能把已知顺序也池化丢掉 |
| 状态/装备 | public字典、遗物counter=null、药水固定3行 | 共享固定特征字典、known/valid mask、类型与归一化 | 可扩词表/类型化状态，具名计数与期限，未知项拒绝 |
| 决策阶段 | 只接受PLAYER_NORMAL | 维持单阶段66位 | NORMAL/SELECT_CARD等版本化阶段；跨区候选变长，必要时多选/确认 |
| 策略输出 | 旧MLP31位；规则/随机66位 | 双方66位，相同mask与编号 | 候选实体打分，路由动作元组；不通过扩大敌人target列冒充选牌 |
| 容量 | 当前闭包累计界7776，初始牌≤96 | 测量吞吐后确定共同模型容量及外部截断契约；初始牌9–14不是全过程界 | 按扩展闭包重新证明原子动作余量与ID范围；Set可变长也有资源上限 |
| PPO交互 | 旧collector；已有截断GAE函数 | 接public reset/场景采样/66动作与完整final_obs | 每次真实玩家选择是独立transition；保存阶段及当时候选，自动随机结果不伪造为策略动作 |
| checkpoint | 旧format_version=2及旧输入契约 | 新模型/词表/布局/环境hash，明确从头训练或显式迁移 | 新输入/动作头重新绑定版本，不能仅strict=False静默加载 |
| 对比预算 | 尚未正式运行本轮双模型 | 各2个初始化、等交互步数、累计30分钟正式训练评估 | 单独报告Set扩展结果，不与旧MLP跨环境直接归因 |

实体截断需要在正式实验前选定：阈值、计数口径、原子动作余量、遇到超界风险的切段位置、最终观测容量、bootstrap以及统计报告方式。本报告没有指定一个未经测量的阈值；也没有把未执行动作的结果猜成final_obs。完整RTG必须来自完整真实轨迹，截断片段不能伪称完整回报标签。

## 7. 可执行的验收顺序

1. **本轮M3**：只迁移冻结环境共享编码、66动作、public采样与checkpoint；用字段差异检查确认无公开字段遗失，再检查吞吐/内存、截断最终状态与恢复。此项不以全75卡扩展为前置条件。
2. **未来输入基础**：关闭R02/R03，逐动态实例对照；新增R04/R05阶段路由，用同名不同增伤/费用、重复消耗堆卡验证选择正确，旧decision_id动作必须拒绝。
3. **未来信息闭包**：为R06构造“无序牌堆相同但已知顶牌不同”的成对历史；洗牌后失效，随机插入后降为不确定，不能访问内部牌顶填值。
4. **未来转移闭包**：核查R07/R11；逐卡基础/升级与相关组合，空/满手牌、空牌堆、负Strength、Artifact、多敌击杀、死亡中断、NoDraw和连锁耗尽。通过单卡不等于组合通过。
5. **未来容量和采集**：覆盖生成、复制、洗牌循环、触发队列、累计ID和动态值数值范围。不能沿用15/7776证明全卡；异常、容量拒绝、正常截断分别统计。

本次验证结果见逐卡表末尾。本次自身只新增两份审计文档与被忽略的本地清点材料；没有修改后端、模型、奖励、评估种子或正式配置，没有启动PPO，没有声明全卡运行验收。工作区并发出现的实现文件由其原工作流负责，不属于本次修改。
