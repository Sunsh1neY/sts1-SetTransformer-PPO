# 遗物与药水后端预审报告

日期：2026-09-11  
角色：并行预审 agent，供主审与 M2 使用  
工作区：C:/Users/19091/Desktop/sts2  
性质：静态审计 + 不改代码的构造探针；不是正式白名单、不是 Gate 验收，也不是“整个遗物/药水系统已支持”的结论。

## 1. 结论先行

当前锁定的 sts_lightspeed 后端内部确实包含较完整的遗物、药水枚举、持有结构和若干战斗钩子；但当前正式 IroncladBattleEnv 只暴露 A0 三遭遇、三类基础卡、31 位卡牌/结束回合动作和基础卡牌观测。遗物、药水目前不能作为正式环境的可注入、可观察、可行动状态。

最重要的边界：

1. GameContext 构造 Ironclad 时实际持有 BURNING_BLOOD(data=0)，不是“无遗物”。不改代码的构造探针已确认这一点。
2. BattleObservation 没有遗物、遗物计数、药水槽位、药水容量或药水类型字段；Python GameContext 绑定只读出 relic 列表，也没有 potion 属性或 reset 注入接口。证据：bindings/slaythespire.cpp:87-153；patches/lightspeed-battle-env.patch:421-473；sts/env/lightspeed.py:306-413。
3. 当前正式动作 mask 只有 31 个位置，step() 只把动作解成卡牌或结束回合；后端虽然另有 ActionType::POTION、单卡选择和多卡选择编码，但它们不在 IroncladBattleEnv 的动作协议内。证据：patches/lightspeed-battle-env.patch:144-160,266-297；third_party/sts_lightspeed/src/sim/search/Action.cpp:226-249,421-465。
4. BattleContext::exitBattle(GameContext&) 才负责战后药水同步、遗物计数回写、Burning Blood 治疗和 regainControl()；当前 adapter 的 step() 没有调用该出口。探针在 seed 100000 的 Jaw Worm 场景中得到胜利 player_hp=69、reward=1.43125；若随后执行后端已有的 Burning Blood 战后治疗，退出 HP 应为75、battle reward 应为1.46875。该问题影响奖励时点，需主审裁定，不能自行修复。
5. 已发现三项高风险问题：
   - adapter 未走 exitBattle，所以战后遗物效果、Neow's Lament 计数递减、遗物计数和药水/RNG/HP 回写均不在正式环境路径中；
   - 正版 JAR 的 PenNib.class 显示阈值常量10，而当前后端攻击钩子在 penNibCounter==9 时触发，存在从0计数时提前一张牌触发的疑似 off-by-one；
   - 战斗内 Blood Potion 的 Sacred Bark 分支为 hasBark ? 20 : 40，而战斗外同一后端路径为 hasBark ? 0.40 : 0.20，方向相反，疑似明确实现缺陷。
6. 本次基线回归 tests/test_cpp_env.py + tests/test_lightspeed_adapter.py 为 52 passed；这些测试覆盖当前基础 adapter，不覆盖 relic/potion 注入、药水动作、选择闭包或战后遗物回写，不能升级为本任务通过。

建议先锁定 reset/观测/动作/二次选择/容量/版本契约，再按“战后出口与基础战斗遗物 → 无二次选择药水 → 计数遗物 → 选择型药水与生成闭包”分批实施。当前不批准任何遗物或药水进入正式训练/评估白名单。

## 2. 证据等级与快照

### 2.1 证据约定

- [静态]：读取当前工作树源码、补丁、绑定或现有测试；证明调用链存在，不证明运行时每个分支都通过。
- [探针]：使用已有构建扩展的公开构造/reset/step 接口，不改源码、不启动训练、不创建新测试入口。
- [正版-JAR]：本机正版 STS1 desktop-1.0.jar 的类文件路径、方法名、常量池/字节码定点读取；证明正版类的入口和局部数值，不替代行为对拍。
- [未运行]：当前接口无法安全执行，或本任务明确不修改正式环境，因此只给出测试场景和预期证据。
- [未核实]：当前证据不足；不把枚举、注释、单个分支或上游宣称写成行为通过。

### 2.2 版本与工作树快照

| 对象 | 快照 |
|---|---|
| 根仓库 HEAD | 80d2340983f1f0a5eb5f6dee159760302a83940f |
| 后端 checkout | 7476a81954020087da31d41d16fddf475746ec2d，与 scripts/lightspeed-lock.json 一致 |
| 后端当前工作树 | bindings/bindings-util.cpp、bindings/slaythespire.cpp、bindings/slaythespire.h 有未提交修改；pybind11 子模块/工作树和 build/ 也有本地状态。不能只用上游 commit 代替当前 adapter 文件哈希。 |
| 正版 JAR | E:/SteamLibrary/steamapps/common/SlayTheSpire/desktop-1.0.jar；bytes 365086855；SHA-256 cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673 |
| 正式环境/规格变更 | 无。本次没有修改 C++、Python、绑定、规格、决策或周计划；没有启动 PPO。 |
| 探针文件 | 无；只使用内联 Python/ZipFile/已有扩展，不创建 reference/relic-potion-audit/ 空目录。 |

关键源码 SHA-256（均为本次审计时工作树内容，显示前12位）：

| 文件 | SHA-256 | 关键位置 |
|---|---|---|
| third_party/sts_lightspeed/include/constants/RelicPools.h | 555ccae8fc64 | Ironclad 130 个池条目 |
| third_party/sts_lightspeed/include/constants/Relics.h | 092473d34e95 | RelicId、名称、等级 |
| third_party/sts_lightspeed/include/constants/Potions.h | d16d41c0b950 | Potion、池、目标类型 |
| third_party/sts_lightspeed/src/game/GameContext.cpp | aad9fcf6db5a | reset 前后持有、Neow、容量、战后层 |
| third_party/sts_lightspeed/src/combat/BattleContext.cpp | a7b99e59d63d | init、战斗钩子、药水、exit |
| third_party/sts_lightspeed/src/combat/Player.cpp | cd586b936932 | 受伤、死亡、回合遗物、Pen Nib |
| third_party/sts_lightspeed/src/sim/search/Action.cpp | 63b606612575 | 药水动作/选择动作编码和合法性 |
| third_party/sts_lightspeed/bindings/bindings-util.cpp | ba1f3110dc87 | BattleObservation、reset/step |
| third_party/sts_lightspeed/bindings/slaythespire.cpp | 1edda59cc0c5 | Python 公开绑定 |
| patches/lightspeed-battle-env.patch | dfe95d2bbd93 | 当前正式 adapter 的补丁来源 |
| sts/env/lightspeed.py | 24301d513fbf | Python 白名单观测/动作薄包装 |

## 3. 覆盖索引：枚举、池、持有结构和选择类型

### 3.1 枚举与 Ironclad 可达来源

| 对象 | 当前后端事实 | 证据与边界 |
|---|---|---|
| 遗物枚举 | RelicId 共181个枚举值：INVALID之外包含180个具体/特殊名称；战斗中、战斗结束、战斗开始、战斗外条目共用一个枚举。 | include/constants/Relics.h:12-202。枚举存在不等于行为完成。 |
| Ironclad 遗物池 | common33、uncommon30、rare28、boss22、shop17，共130个池条目，当前解析无重复；另有 starter BURNING_BLOOD，Neow路径可直接得到 NEOWS_LAMENT。 | include/constants/RelicPools.h:21-32；GameContext.cpp:2315-2317,2325-2327,2345-2347。130是池来源覆盖，不是正式 reset 白名单。 |
| 药水枚举 | 共44个枚举值：INVALID、EMPTY_POTION_SLOT加42个具体药水。FLEX_POTION注释对应游戏代码 SteroidPotion；FAIRY_POTION、LIQUID_MEMORIES、ENTROPIC_BREW均为实际后端ID。 | include/constants/Potions.h:12-67,69-163。 |
| 药水随机池 | 每个角色33个位置；Ironclad池含本报告深查的10种药水。 | include/constants/Potions.h:235-247。随机池可达不代表正式环境可注入或可行动。 |
| Neow's Lament命名 | 后端实际 ID 是 RelicId::NEOWS_LAMENT，正版类文件是 com/megacrit/cardcrawl/relics/NeowsLament.class。 | Relics.h:133-150；正版JAR类路径；GameContext.cpp:1373-1375,2325-2327。 |
| 目标类型 | potionRequiresTarget()仅把Fear、Fire、Poison、Weak标为需要敌人目标；本任务深查清单中只有Fire Potion需要目标。Explosive是全敌人效果，其余列出的基础药水无敌人目标。 | Potions.h:263-274；实际动作合法性另见 Action.cpp:66-102。 |
| 卡牌/药水选择类型 | InputState已有 CHOOSE_STANCE_ACTION、CHOOSE_ENTROPIC_BREW_DISCARD_POTIONS、CARD_SELECT；CardSelectTask已有 LIQUID_MEMORIES_POTION。 | InputState.h:10-54；CardSelectInfo.h:14-75。选择状态未进入正式31位动作协议。 |

### 3.2 持有、计数和容量

| 层 | 当前结构 | 可见性/风险 |
|---|---|---|
| GameContext遗物 | RelicContainer::relics是 vector<RelicInstance>；每个实例为 {RelicId id,int data}；另有 relicBits0/1/2 三个64位bitset。 | data承载Neow、Pen Nib、Happy Flower等计数；getRelicValueRef找不到ID时退回 relics[0].data。RelicContainer.h:16-43；Game.cpp:14-92。 |
| BattleContext药水 | potionCount、potionCapacity、array<Potion,5> potions；A0默认3，A11及以上默认2，Potion Belt再加2，数组上限5。 | BattleContext.h:83-85；GameContext.h:226-230；GameContext.cpp:62-67,202-215,1423-1427。槽位/容量没有正式观测字段。 |
| Player遗物位 | Player只有relicBits0/1，没有relicBits2；BattleContext::initRelics也只复制GameContext的bits0/1。 | Player.h:61-63,444-468；BattleContext.cpp:80-82。ID≥128的后续 player.hasRelic 钩子存在容量风险。 |
| Player动态遗物计数 | happyFlowerCounter、incenseBurnerCounter、inkBottleCounter、inserterCounter、nunchakuCounter、penNibCounter、sundialCounter等保存在Player。 | Player.h:64-83；BattleContext.cpp:521-561只对部分字段在出口回写。 |
| Python公开层 | GameContext.relics是只读copy；没有 GameContext.potions、potionCapacity、obtainRelic、obtainPotion、BattleContext或potion action的公开绑定。 | bindings/slaythespire.cpp:87-153,691-872。当前不具备不改正式代码的真实初态注入入口。 |

## 4. 锁定后端完整调用链

    IroncladBattleEnv.reset
      -> GameContext(Ironclad, seed, ascension)
           -> initRelics() / initPlayer()
           -> Ironclad starter: Burning Blood + 10张基础牌
           -> potionCapacity / empty potion array
      -> floor=1, curRoom=MONSTER, info.encounter=...
      -> BattleContext::init(GameContext, encounter)
           -> copy HP/gold/potions/potionCapacity/RNG
           -> MonsterGroup::init
           -> CardManager::init
           -> initRelics(gc)
           -> initial energy + executeActions()
      -> BattleObservation / 31位 action_mask

    IroncladBattleEnv.step(action 0..30)
      -> 当前mask只枚举 CARD + END_TURN
      -> search::Action::execute(BattleContext)
      -> executeActions()
           -> card use / damage / death / turn / start-of-turn / end-of-turn hooks
      -> 直接读取BattleContext的terminal outcome、HP、reward、observation

    上游BattleSimulator/ConsoleSimulator的出口
      -> BattleContext::exitBattle(GameContext)
           -> sync potionCount/potions/RNG/HP/gold
           -> updateRelicsOnExit()
           -> updateCardsOnExit()
           -> regainControl()/afterBattle()

### 4.1 reset到开战

- GameContext构造函数初始化整局RNG、生成怪物列表、调用initRelics()和initPlayer()，然后设置A0默认药水容量3、清空槽位并进入Neow屏幕，见 GameContext.cpp:35-72。
- initPlayer()的Ironclad分支设置初始HP、调用obtainRelic(BURNING_BLOOD)，加入Strike×5、Defend×4、Bash，见 GameContext.cpp:477-490。
- adapter为当前战斗把floorNum=1、curRoom=MONSTER、info.encounter写入GameContext，然后直接调用bc_.init(*gc_, encounter)，见 patches/lightspeed-battle-env.patch:126-142。
- BattleContext::init()拷贝gc.curHp/maxHp/gold、药水计数/容量/槽位和RNG，初始化怪物与卡牌，再调用initRelics(gc)和executeActions()，见 BattleContext.cpp:21-77。

### 4.2 开战与回合钩子

BattleContext::initRelics先复制GameContext的遗物bitset，再按gc.relics.relics的vector顺序把遗物分配到battle-start/pre-draw/post-draw队列或直接执行；注释也承认当前没有按正版获得顺序排序，见 BattleContext.cpp:79-120。

- 直接开战状态：Anchor、Vajra、Pen Nib、Neow's Lament、Happy Flower的计数初始化等在 BattleContext.cpp:148-196,226-300,358-360。
- 开战抽牌：Bag of Preparation追加DrawCards(2)，在基础DrawCards(cardDrawPerTurn)后执行，见 BattleContext.cpp:391-430。
- 回合开始：Happy Flower在Player::applyStartOfTurnRelics计数，三次时加能量，见 Player.cpp:490-527。
- 出牌：Pen Nib在攻击卡hook中计数，状态进入calculateCardDamage后使伤害乘2，并在攻击hook中移除，见 BattleContext.cpp:1655-1703,2671-2703。
- 受伤/死亡：Fairy Potion和Sacred Bark在Player::wouldDie中处理，见 Player.cpp:323-346。这条路径是自动触发，不是玩家主动喝药动作。

### 4.3 战后与状态同步

BattleContext::exitBattle会先处理特定战斗后效果，再同步药水、RNG、HP、gold，随后回写遗物计数和卡牌状态，见 BattleContext.cpp:459-519。其中 updateRelicsOnExit：

- Neow's Lament data>0时减1，见 BattleContext.cpp:540-544；
- Happy Flower、Pen Nib等计数写回GameContext，见 BattleContext.cpp:521-561；
- Burning Blood胜利时 g.playerHeal(6)，Black Blood为12，见 BattleContext.cpp:569-585。

当前adapter的step()在selected.execute(bc_)后只做超时、terminal、reward、observation、info，未调用bc_.exitBattle(*gc_)，见 patches/lightspeed-battle-env.patch:266-297。上游BattleSimulator::exitBattle和搜索Agent才明确调用该出口，见 third_party/sts_lightspeed/src/sim/BattleSimulator.cpp:33-41、src/sim/search/ScumSearchAgent2.cpp:42。

## 5. 正版一手JAR定点证据

本节只说明本机正版JAR的类级/字节码级事实；“正版类存在”不等于锁定C++已行为等价。JAR SHA-256已在§2.2记录。

### 5.1 遗物类

| 正版类文件 | JAR定点入口/局部常量 | 对照含义 |
|---|---|---|
| relics/BurningBlood.class | onVictory()；常量池整数6；引用 AbstractDungeon、AbstractPlayer.heal | 正版战斗胜利后治疗6；C++有同值出口分支，但formal adapter未走出口。 |
| relics/NeowsLament.class | atBattleStart()、setCounter(int)；引用 AbstractMonster.currentHealth、healthBarUpdatedEvent | 正版是战斗开始对怪物HP的一次性效果并有计数；C++ ID/初始data/出口递减路径存在。 |
| relics/Anchor.class | atBattleStart()；常量10；引用 GainBlockAction | 正版开战格挡10；C++直接 player.block += 10。 |
| relics/Vajra.class | atBattleStart()；常量1；引用 StrengthPower | 正版开战力量1；C++直接buff Strength 1。 |
| relics/PenNib.class | onUseCard(...)、atBattleStart()；常量10；引用 PenNibPower | 正版以10为计数阈值；C++当前attack hook在counter==9触发，需主审定点复核。 |
| relics/HappyFlower.class | atTurnStart()；常量3、1；引用 GainEnergyAction | 正版每三次回合开始加1能量；C++有对应计数器和回写。 |
| relics/BagOfPreparation.class | atBattleStart()；常量2；引用 DrawCardAction | 正版开战额外抽2；C++有对应额外抽牌。 |
| relics/PotionBelt.class | onEquip()；引用 AbstractPlayer.potionSlots、AbstractPlayer.potions、PotionSlot | 正版改变药水槽；C++ GameContext容量加2并初始化新增空槽。 |
| relics/SacredBark.class | onEquip()；引用 AbstractPotion与玩家药水容器 | 正版是药水效果修饰；C++使用hasBark分支，但Blood Potion战斗分支方向与战外分支相反。 |
| relics/Sozu.class | onEquip()、onUnequip()；引用 EnergyManager.energyMaster | 正版改变能量上限/禁止药水获取；C++开战能量+1，Game/Battle两层obtainPotion拒绝。 |

### 5.2 药水类与正版局部数值

getPotency()的JAR字节码定点读取给出以下基础值；这些是正版类的局部数值证据，不代表当前C++已覆盖目标/选择/容量闭包。

| 正版类 / 后端ID | JAR getPotency/use证据 | C++对照 |
|---|---|---|
| FirePotion / FIRE_POTION | getPotency()为20；use()引用DamageAction | BattleContext.cpp:2340-2342为20，Sacred Bark分支40；potionRequiresTarget为真。 |
| ExplosivePotion / EXPLOSIVE_POTION | use()引用DamageAllEnemiesAction | BattleContext.cpp:2330-2333为全敌10，Bark为20。 |
| BlockPotion / BLOCK_POTION | getPotency()为12；use()引用GainBlockAction | BattleContext.cpp:2263-2265为12/24。 |
| StrengthPotion / STRENGTH_POTION | getPotency()为2；use()引用StrengthPower | BattleContext.cpp:2416-2418为2/4。 |
| DexterityPotion / DEXTERITY_POTION | getPotency()为2；use()引用DexterityPower | BattleContext.cpp:2290-2292为2/4；正式global没有Dexterity字段。 |
| EnergyPotion / ENERGY_POTION | getPotency()为2；use()引用GainEnergyAction | BattleContext.cpp:2310-2312为2/4。 |
| SwiftPotion / SWIFT_POTION | getPotency()为3；use()引用DrawCardAction | BattleContext.cpp:2420-2422为抽3/6。 |
| FairyPotion / FAIRY_POTION | getPotency()为30；canUse()返回false；use()引用heal/destroy | Player.cpp:323-335在致死时自动消耗并按30%/60% max HP治疗；不能作为主动drink action。 |
| LiquidMemories / LIQUID_MEMORIES | getPotency()为1；use()引用BetterDiscardPileToHandAction | BattleContext.cpp:2373-2375进入LIQUID_MEMORIES_POTION选择状态，Bark时取2张，并把选中卡本回合费用置0。 |
| EntropicBrew / ENTROPIC_BREW | use()引用returnRandomPotion、ObtainPotionAction、potionSlots；canUse()检查槽位/房间状态 | BattleContext.cpp:2314-2320按capacity生成随机药水并调用obtainPotion；当前正式观测/动作无法表达结果。 |

## 6. 代表遗物逐项预审

状态标记：内部静态可执行只表示C++有调用链；formal env可用还要求reset注入、观测、动作/选择和战后同步同时存在。

| 条目 | 注入必需参数与内部字段 | 当前后端钩子/动态计数 | 观测字段 | 动作/二次选择 | 结论与最小测试 |
|---|---|---|---|---|---|
| Burning Blood | RelicInstance{id,data}，通常data=0。 | starter在GameContext::initPlayer；仅updateRelicsOnExit胜利时治6。 | HP会受影响，但当前adapter的reward/obs在exit前读取。 | 无主动动作。 | 内部出口逻辑存在，formal path未接通。测试：初始HP74，胜利后验证exit后治疗和reward同一时点。 |
| Neow's Lament | data初次由obtainRelic设为3；样本初态必须保留剩余charges。 | initRelics中data>0将所有怪物HP设为1；exit每场减1。 | 敌人HP可见，charges不可见。 | 无主动动作，但跨战斗reset/战后同步必需。 | 内部初始/递减存在；adapter未出口导致charges不递减。连续三场应置1，第四场不置1。 |
| Anchor | 无动态参数。 | Battle init block +=10。 | global block可见。 | 无。 | 开战block=10且不重复；当前无注入入口。 |
| Vajra | 无动态参数。 | Battle init buff Strength 1。 | global strength可见。 | 无。 | 开战strength=1；Strike相对无遗物多1；当前无注入入口。 |
| Pen Nib | data/penNibCounter，必须定义0-based或存储已计数语义。 | init从data恢复；每个攻击计数；触发后加PS::PEN_NIB，伤害乘2，随后移除；exit回写。 | counter/status不在global，伤害结果可见。 | 无主动动作。 | JAR阈值10而C++counter==9，疑似off-by-one。测试8/9/10次攻击及多段攻击。 |
| Happy Flower | data是跨战斗计数。 | init data+1，到3立即加能量并归零；每回合开始再计数，到3加1能量；exit回写。 | energy可见，counter不可见。 | 无。 | 测试data=0/1/2的开战边界和跨战斗回写，确认时点。 |
| Bag of Preparation | 无动态参数。 | atBattleStart追加DrawCards(2)。 | 手牌/抽牌堆数量可见。 | 无。 | 初始抽牌应为7，不是后续每回合+2。 |
| Potion Belt | reset前需输入当前capacity、已有槽位和获取顺序；容量需按Ascension与relic计算。 | GameContext obtainRelic加2并清空新增槽；save path同样加2；BattleContext拷贝。 | 当前无capacity/count/slot。 | 无主动动作，但影响后续potion action。 | A0=5槽、A11=4槽；新增药水填最小空槽，count一致。 |
| Sacred Bark | 只需持有标志，但每种药水需定义修正表。 | drinkPotion逐分支读取hasBark；Fairy death heal 30%→60%。 | 结果部分可见，修正本身不见。 | 无。 | 战斗Blood Potion为Bark?20:40，战外为Bark?40%:20%，疑似缺陷；需矩阵测试。 |
| Sozu | 持有标志和energy per turn。 | Battle init energy+1；Game/Battle obtainPotion直接拒绝。 | energy可见，Sozu/potion failure不可见。 | 无。 | 测试开战energy=4；reward/shop/Entropic/普通获取均不加槽，并审计失败原因。 |

## 7. 代表药水逐项预审

| 药水 | 参数/目标 | 后端效果与动态依赖 | formal状态 | 最小测试 |
|---|---|---|---|---|
| Fire Potion | 一个可攻击敌人目标。 | 消耗槽位后对target 20；Bark 40；敌HP可见。 | 不在公开step动作；无槽位观测。 | targetable enemy HP恰减20/40；错误目标拒绝，不能默认0。 |
| Explosive Potion | 无目标，全体敌人。 | 全体10；Bark20。 | 无动作/槽位/容量。 | 双虱均减10/20，不越界。 |
| Block Potion | 无目标。 | block +12；Bark +24。 | 无动作；block可观察。 | block精确变化，回合结算不重复。 |
| Strength Potion | 无目标。 | Strength +2；Bark +4；global可见。 | 无动作。 | strength=2/4，攻击伤害随之变化。 |
| Dexterity Potion | 无目标。 | Dexterity +2；Bark +4；Player有字段但global无字段。 | 关键可见状态缺失，无动作。 | 除block间接结果外，必须直接核对Dex观测字段。 |
| Energy Potion | 无目标。 | energy +2；Bark +4；global可见。 | 无动作。 | 使用后能量精确变化，不能被recharge错误覆盖。 |
| Swift Potion | 无目标。 | 抽3；Bark抽6；手牌/牌堆可观察。 | 无动作。 | 空手和接近满手牌时验证hand/discard容量边界。 |
| Fairy in a Bottle | 不能主动drink；致死自动触发。 | 消耗第一个Fairy，治疗30% max HP；Bark60%。 | 无槽位观测，无主动动作。 | lethal时不terminal、HP≥1、count--；Mark of Bloom例外。 |
| Liquid Memories | 必须从discard明确选择1张；Bark2张。 | 进入CARD_SELECT，选卡入hand并本回合0费。 | selection不在obs，31动作无discard选择。 | explicit discard index；空discard/满手牌/1或2张；不得自动选。 |
| Entropic Brew | 无敌人目标；按capacity生成随机药水。 | potionRng + returnRandomPotion + obtainPotion；Sozu阻止；不自动饮用。 | 结果不在obs/action。 | 固定RNG验证数量、顺序、重复、Sozu、非递归；当前未运行。 |

## 8. 药水使用、丢弃、目标和选择闭包

### 8.1 后端内部已有的药水动作语法

search::ActionType包含POTION，source index是药水槽位，target index同时承担敌人目标和丢弃标记：

- isValidPotionAction要求 PLAYER_NORMAL、槽位0..5、非空；Fairy不能主动喝；目标型药水要求可选敌人，见 Action.cpp:66-102。
- execute在target>5时丢弃，否则调用BattleContext::drinkPotion(source,target)，见 Action.cpp:421-445。
- BattleSimulator也有 drink <slot> [target] 和 discard <slot> 命令，见 BattleSimulator.cpp:107-128,141-187。

这只能证明C++搜索/控制台路径存在，不能当作formal adapter支持。当前formal mask只构造CARD和END_TURN，完全没有POTION分支。Python binding也只公开reset/step/action_mask/observation。

### 8.2 目标合法性和二次选择缺口

- Fire Potion的目标合法性只存在于未公开的ActionType::POTION路径；formal 31位mask没有“药水槽 × 目标”动作空间。
- BattleContext::drinkPotion(int idx,int target=0)带默认target，且先discardPotion再进入效果；没有独立槽位/空槽/目标边界校验。正式动作层不能把它直接暴露给模型。
- Liquid Memories进入CARD_SELECT后，formal makeActionMask的卡牌动作和结束动作都会因inputState != PLAYER_NORMAL失效；没有CardSelectInfo动作。
- 其他后端已有DISCOVERY、CHOOSE_STANCE_ACTION、EXHAUST_MANY等选择状态，说明只加药水槽观测仍不足以形成闭包。
- 不能因为Liquid Memories、生成卡或Entropic Brew难以表达，就让后端自动选第一张卡、第一目标或第一药水。

### 8.3 容量与生成闭包

- GameContext/BattleContext都是5槽数组；容量由A0/A11和Potion Belt共同决定，不能只用初始3作为M2上界。
- Entropic Brew调用obtainPotion，不递归饮用；仍需证明count、slot、Sozu和RNG消耗。
- Liquid Memories不创建新卡，而是把discard已有卡搬回hand并设为本回合0费；依赖discard可见构成、选择动作、手牌容量和后续卡牌结算。
- AttackPotion、SkillPotion、PowerPotion、ColorlessPotion、BlessingOfTheForge等也有discovery/upgrade/生成卡入口；本表未深查不等于已支持。

## 9. minimal-v1默认遗物与奖励HP时点

### 9.1 实际默认初态

直接构造并读取当前扩展：

    GameContext(Ironclad, seed=100000, ascension=0)
    relics = [(BURNING_BLOOD, id=86, data=0)]
    potions = [EMPTY_POTION_SLOT, EMPTY_POTION_SLOT, EMPTY_POTION_SLOT]
    potionCapacity = 3

结果与GameContext.cpp:483-490、RelicPools.h:21-24一致。正式IroncladBattleEnv.reset随后设置floor/room/encounter并调用BattleContext::init，所以minimal-v1真实后端初态至少持有Burning Blood，不能记作空遗物。

### 9.2 Burning Blood是否在minimal-v1生效

分开看两条路径：

- [内部静态] updateRelicsOnExit有胜利治疗6，证明后端作者意图存在。
- [formal adapter探针] 当前step没有调用exitBattle；胜利reward由bc_.player.curHp直接计算。seed100000 Jaw Worm的greedy诊断路径返回terminal HP69、reward1.43125，没有额外6点治疗。

因此当前minimal-v1 formal adapter中，Burning Blood战后生效不能记为通过；至少存在“出口未接入”或“奖励应在出口前读取”的契约冲突。报告不自行改reward，也不自行改正式环境。

### 9.3 待主审确认的HP奖励时点

spec-v6/D27要求HP_exit在最后动作、连锁效果和已实现的战斗结束效果全部结算后读取。当前C++的updateRelicsOnExit把Burning Blood/Black Blood/Meat on the Bone放在exitBattle，而adapter的reward在此之前读取。主审需要明确：

1. HP_exit是否包含战后遗物治疗；
2. BattleContext::exitBattle是否是battle task的正式终止钩子；
3. info.player_hp、最终observation、reward是否必须使用同一退出快照；
4. Neow's Lament递减和动态遗物回写是否在同一transition完成。

## 10. 发现的缺口与疑似缺陷

| 优先级 | 项目 | 证据 | 影响 |
|---|---|---|---|
| P0 | formal adapter未调用exitBattle | patch:266-297；出口逻辑BattleContext.cpp:459-592 | 战后效果、遗物计数、药水/RNG/HP同步和afterBattle不在formal path，直接影响reward。 |
| P0 | formal reset无relic/potion注入 | reset仅seed/encounter/ascension，patch:126-142；binding:70-77 | 公开样本的真实遗物/药水初态无法传入。 |
| P0 | formal action/obs没有药水和二次选择 | BattleObservation只有hand/enemies/piles/global/masks；31位mask只卡牌/结束 | 只补字段不能执行Fire、Liquid Memories、Entropic Brew，会死锁或丢状态。 |
| P1 | Pen Nib疑似提前一张触发 | JAR PenNib常量10；C++ counter==9 | 改变伤害、轨迹和reward；需定点测试。 |
| P1 | Sacred Bark下Blood Potion战斗分支反向 | BattleContext.cpp:2268-2271；GameContext.cpp:2183-2187 | 相同药水在战斗/战外执行不同且反向。 |
| P1 | Player relic bitset没有bitset2 | RelicContainer有bits0/1/2；Player只有0/1；init只复制0/1 | ID≥128的runtime player.hasRelic存在容量风险。 |
| P1 | Potion raw API边界弱 | discard无bounds/empty检查；drink默认target=0且先discard | 错误动作可能先丢药水或自动选择目标。 |
| P2 | Potion action丢弃编码与打印约定不一致 | Action.cpp:80-98与299-314 | 新schema必须固定slot/target/discard sentinel。 |
| P2 | 观测缺少Dex等影响未来转移的可见字段 | global 13项，patch:400-403；Player有dexterity/status | Dexterity Potion等效果无法完整解释。 |
| P2 | 现有52项回归没有本任务覆盖 | pytest结果52 passed，但测试是基础reset/card/reward/mask | 只能作为未改动基线。 |

## 11. 按依赖分批的建议

这不是批准范围，只是供主审/M2排序的实现依赖。

| 批次 | 建议范围 | 先决条件 | 不满足时出口 |
|---|---|---|---|
| R0 | 只做reset/状态/版本契约，不开放新机制 | relic registry、RelicInstance.data、potion slot/count/capacity、初态时点、观测白名单、action/selection schema | 继续停在minimal-v1。 |
| R1 | Anchor、Vajra、Bag of Preparation、Happy Flower | 真实初态注入；起始hook时点；Strength/block/energy/hand/draw字段；counter回写 | 只做静态/独立行为测试，不训练。 |
| R2 | Burning Blood、Neow's Lament、Potion Belt、Sozu | 先解决exitBattle、HP reward、Neow charges、容量和Sozu失败信息 | P0未解决时不进正式reward或训练。 |
| R3 | Fire、Explosive、Block、Strength、Dexterity、Energy、Swift、Fairy | potion action grammar、目标mask、Fairy death、容量/消耗、Dex观测 | 只做后端内部测试，formal reset不批准。 |
| R4 | Sacred Bark修正矩阵 | 所有potency表、战斗/战外一致性、Bark/Sozu/Potion Belt组合 | 先单列缺陷。 |
| R5 | Liquid Memories、Entropic Brew及其他生成/选择药水 | CARD_SELECT/discovery/多选语法、hand/discard/slot容量、potion RNG、selection不自动代选 | 不把“能生成”写成“可行动”。 |

## 12. 可直接实现的测试清单

以下是测试设计，不是已经运行的结果；除T-RP-01和T-RP-04探针，其余均因当前正式API缺口标为未运行。

| 编号 | 场景 | 必须证明 | 状态 |
|---|---|---|---|
| T-RP-01 | GameContext(Ironclad,A0) | 默认恰为Burning Blood(data=0)，容量3，槽位全空，starter deck10张 | [探针]已通过 |
| T-RP-02 | 注入Anchor/Vajra/Bag/Happy | 注入参数、battle-start时点、一次性/计数边界、obs结果 | [未运行] |
| T-RP-03 | Neow's Lament三场链 | data3→2→1→0；前三场HP=1，第四场不置1；不跨reset丢失 | [未运行] |
| T-RP-04 | Burning Blood reward时点 | 战斗胜利后治疗发生，再以同一HP计算reward/info/terminal obs | [探针]已发现当前不满足，待主审 |
| T-RP-05 | Pen Nib攻击计数 | 8/9/10次攻击的触发张数、下一次倍伤、跨战斗回写 | [未运行] |
| T-RP-06 | Potion Belt + Ascension | A0容量3/5、A11容量2/4；最小空槽写入；count一致 | [未运行] |
| T-RP-07 | Sozu | energy+1；reward/shop/Entropic/普通获取均不加槽；失败可审计 | [未运行] |
| T-RP-08 | Fire target | 只允许targetable enemy；错误目标拒绝；不能默认0 | [未运行] |
| T-RP-09 | Explosive multi-target | 单/双敌均按全体10/20；不越界 | [未运行] |
| T-RP-10 | Potion amount matrix | Block12/24、Strength2/4、Dex2/4、Energy2/4、Swift3/6、Fairy30%/60%、Fire20/40 | [未运行] |
| T-RP-11 | Sacred Bark Blood | 战斗内与战外同一方向，Bark增强而非减弱 | [未运行]；静态已见反向 |
| T-RP-12 | Fairy death | lethal时自动消耗、HP≥1、count--、不terminal；Mark of Bloom例外 | [未运行] |
| T-RP-13 | Liquid Memories | explicit discard index；Bark1/2张；费用0；不得自动选 | [未运行] |
| T-RP-14 | Entropic Brew | 固定RNG验证数量、顺序、重复、Sozu、非递归 | [未运行] |
| T-RP-15 | 后端/adapter一致性 | ActionType::POTION与formal schema的target/discard/selection逐项对齐 | [未运行] |
| T-RP-16 | 观测可见性 | Dex、Artifact、potion inventory、relic counter、selection state逐项核验 | [未运行] |

## 13. 复现命令与结果

### 13.1 只读快照/探针

    git rev-parse HEAD
    git -C third_party/sts_lightspeed rev-parse HEAD
    Get-FileHash -Algorithm SHA256 E:/SteamLibrary/steamapps/common/SlayTheSpire/desktop-1.0.jar

构造与formal observation探针（本次已运行；只读已有build）：

    python -X utf8 -c "import sys; sys.path.insert(0, r'third_party/sts_lightspeed/build'); import slaythespire as s; g=s.GameContext(s.CharacterClass.IRONCLAD, 100000, 0); print([(r.id.name, int(r.id.value), r.data) for r in g.relics]); e=s.IroncladBattleEnv(max_turns=5); o=e.reset(100000, s.MonsterEncounter.JAW_WORM, 0); print(len(o.action_mask), [k for k in dir(o) if 'potion' in k.lower() or 'relic' in k.lower()])"

Burning Blood终局时点探针（本次已运行）：使用固定seed100000的greedy attack/end-turn诊断，输出 terminated=True、player_hp=69、reward=1.431249976158142、timeout=0。该命令没有写文件，也没有启动训练。

### 13.2 基线测试

    python -X utf8 -m pytest -q -p no:cacheprovider tests/test_cpp_env.py tests/test_lightspeed_adapter.py

结果：52 passed in 0.32s。这是当前基础adapter的基线，不含本报告T-RP-02至T-RP-16的扩展行为验收。

## 14. 待主审决定事项与明确缺口

主审至少需要明确：

1. battle_reward_v1的HP_exit是否包含Burning Blood/Black Blood/Meat on the Bone等exitBattle效果；formal adapter是否必须在terminal transition内调用出口。
2. Neow's Lament的data初值、跨战斗消耗时点和公开样本中的剩余charges复原规则。
3. Pen Nib的正版第10次攻击与当前counter==9实现是否一致；先定点复核再修。
4. Sacred Bark的所有药水修正表，尤其Blood Potion战斗/战外方向冲突。
5. relic registry是否保留所有RelicId，以及Player两bitset对ID≥128的处理。
6. reset的relic/potion注入时点：battle init前、开战前、初始抽牌前/后，以及HP、槽位、计数如何恢复。
7. potion action schema：potion_slot、target、discard、no_target、selection_id如何版本化；目标0与无目标不能混淆，丢弃不能复用未定义sentinel。
8. 二次选择统一状态观测和动作grammar；Liquid Memories、Discovery、Stance、Entropic不得由后端代选。
9. 新增字段哪些是玩家可见：至少Dexterity、Artifact、relic counter、potion inventory/capacity、selection state需逐项给出正版时点证据。
10. 公开样本带遗物/药水但formal API无法注入时，场景应记为“初态可重建但后端待支持”，不能删除遗物/药水后仍称原样本支持。

明确缺口：本报告没有修改正式环境、没有扩展Python binding、没有生成共享测试入口、没有执行带遗物/药水的真实运行时行为测试、没有启动训练，也没有宣称M2/M3/Gate完成。后续实现必须先由主审批准契约与分批范围。

## 15. 交接状态

指定报告已完成：docs/relic-potion-backend-audit.md。  
共享规格、决策、周计划、正式环境和模型均未修改。  
本预审到此停止，等待主审独立复核。
