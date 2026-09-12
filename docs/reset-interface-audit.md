
# 初态重建边界与 reset 接口迁移预审报告

日期：2026-09-11
任务：并行预审任务 C，供主审与 M2 使用
报告性质：预审核查意见，不是正式 reset 白名单、M2 验收、Gate 结论或实现批准

## 0. 结论先行

1. reset 必须分成两个不同入口。
   - 入口 A 是开战初始化前的 GameContext。后端只调用一次 BattleContext::init，由后端完成怪物生成、初始意图、洗牌、开战效果、首轮抽牌和能量初始化。
   - 入口 B 是开战效果和首轮抽牌已经完成后的第一决策点。它应恢复一个可以继续运行的 BattleContext 快照，不能再次调用 BattleContext::init。
2. 缺手牌或敌人意图不必然使公开日志完全不可用。若日志在明确时点提供了完整的入口 A 状态，可以用新的环境复跑 seed 重新采样隐藏洗牌和怪物内部随机，并标为“真实构筑和入场状态驱动的重新模拟”。这不是原局精确回放。
3. 若日志只有最终 master_deck、逐层 HP 和最终遗物/药水历史，则当前可验证字段不足以形成 A 或 B，不能补默认值。尤其不能把最终 master_deck 当作中间战斗的入口牌组，也不能把缺失遗物计数或药水库存当成 0/空槽。
4. 当前正式绑定只有 reset(seed, encounter, ascension=0)，固定 Ironclad 初始牌组、A0、三个遭遇；没有自定义 GameContext 注入、B 快照注入、药水库存或卡牌选择状态入口。
5. 当前公开数据审计的有限结果是：固定提交中选择了 12 个汇总 .run，全部 not_reconstructable；1 个详细 JSONL 产生 7 个战斗快照，其中 2 个字段层面可重建但仍是 reconstructable_but_backend_pending。它们不是当前可运行场景、正式白名单或精确回放。
6. 当前动作和 shape 契约散落在 C++ binding、Python 环境、registry、双 wrapper、MLP、Agent/runner、T5 轨迹和 PPO 中。最小迁移是新增带 environment_config_id 的集中契约，让容量、动作宽度、字段哈希、轨迹和 checkpoint 版本从它校验派生；旧 minimal-v1 保持独立。
7. 五目标动作的具体编号由主 M2 最终裁定，本报告不创建竞争动作版本。
8. 本报告没有修改正式环境、共享规格、决策日志、周计划、M2 文件、eval_seeds.json 或模型，没有启动训练，也没有提交/推送。完成后等待主审。

## 1. 审计范围、快照和证据等级

### 1.1 已读取的项目约束

已读取 AGENTS.md、spec-v6.md、docs/decisions.md、docs/m1-candidate-batches.md、docs/m2-agent-prompt.md，并检查 docs/observation-contract.md、现有 M2 人工场景诊断文档、锁定后端、绑定补丁、Python wrapper/model/Agent/PPO 和公开样本审计产物。

当前执行依据仍是 spec-v6.md > docs/decisions.md > docs/mechanics.md > docs/learning-path-v2.md。M1 候选表和 docs/m2-battle-contract.md 不能单独批准真实 reset 分布；后者明确标注为人工诊断契约，正式分布已撤销。

### 1.2 工作树和后端快照

| 项 | 本次记录 |
|---|---|
| 主仓库 HEAD | 80d2340983f1f0a5eb5f6dee159760302a83940f |
| 锁定 sts_lightspeed 上游提交 | 7476a81954020087da31d41d16fddf475746ec2d |
| 适配补丁 | patches/lightspeed-battle-env.patch；SHA-256 DFE95D2BBD93300932D187C969B6B6EA9AA4A4783DA4169B1B32BD1160CB878C |
| 当前构建扩展 | third_party/sts_lightspeed/build/slaythespire.cp313-win_amd64.pyd；SHA-256 A4B1745D79D848354DA8783416D4728A8AEC255D359E93687C62CD1EF9D16FBF |
| 上游 patch 状态 | git apply --reverse --check 通过；补丁当前已应用于本地 ignored 上游工作树 |

本次读取时工作树已有并行未提交改动，包括 AGENTS.md、spec-v6.md、docs/decisions.md、docs/week-5-6-plan.md、M1/M2 文档、公开审计脚本/测试、公开样本索引和其它并行提示文件。它们均被保留；本报告不把并行目录状态当成稳定基线。

关键 Python 消费者快照如下，主审可用同一命令重新计算：

| 文件 | SHA-256 |
|---|---|
| sts/env/lightspeed.py | 24301D513FBFB7286950CD375130D6DE7A54D6F131C86CBDDC38899C25194964 |
| sts/env/registry.py | FDCA8498EAC93CF80CB6BCED58CF7D88D49B13AAB77BD4D6FC61398CDC30B5B3 |
| sts/env/wrappers.py | 本次终端输出截断，未写入截断值 |
| sts/models/mlp.py | 2EB9FEDFD8D1FE44AD974070CE83539613FE5733000115F6CE91FCE6376EE540 |
| sts/agents/masked_policy.py | 4B338F1C5D690EFCCEE8A9BC4B419057486B9F5FDCDA9DBF94BC41294F6E3E13 |
| sts/agents/episode_runner.py | C82A712D2CF4402F1A80BDBCEFB0B8EB78F03AE6B0017C81D91C7883883547B4 |
| sts/train/ppo.py | DEF98CADEB3434F35E999CEBF9D1979C60237CDF16A3DE056858C0434E7F3B4C |
| sts/train/recording.py | F03AA17FD305F8705BC0C61FA366756FF008B8054B768666EF4C7DA9064CFF2C |

复核命令：

    Get-FileHash sts/env/lightspeed.py,sts/env/registry.py,sts/env/wrappers.py,sts/models/mlp.py,sts/agents/masked_policy.py,sts/agents/episode_runner.py,sts/train/ppo.py,sts/train/recording.py -Algorithm SHA256

### 1.3 证据等级

- 静态：读取当前锁定上游源码、补丁、Python 代码和文档；不等于运行通过。
- 正版一手定点：本机正版 JAR，SHA-256 为 CFAD868AC8D65A88E71A0BF096FB09F78811E553EFFE0787C5309A655E081673；只用于说明游戏侧局部字段/时点，不复制进实现。
- 实际探针：直接导入当前已构建 pyd 得到的 A0 输出；只验证现状。
- 数据审计：读取并复核并行 M2 已生成的公开样本 JSON；不是本任务重新下载或扩大样本。
- 未运行计划：本报告提出但当前正式接口不能执行的测试，明确标为未运行。
- [未核实]：现有代码或日志不足以证明正版行为、字段可见性或时点含义。

## 2. 正版材料与锁定后端边界

### 2.1 正版一手定点材料

以下材料来自本机正版 JAR 的定点反编译，只作争议定位；不能复制为模拟器实现。

- reference/sts1-decompiled/com/megacrit/cardcrawl/cards/CardGroup.java:911-936：正版初始化牌堆先复制 master deck、shuffle，再把 innate/bottled 卡放到牌堆顶方向，并在超过手牌上限时安排额外抽牌。
- reference/decomp/com/megacrit/cardcrawl/monsters/exordium/Cultist.java:52-62,76-104,141-148：Cultist 构造时建立 HP/攻击资料，首次 getMove 设置 Incantation，后续设置攻击；Ritual 在 takeTurn 中加入动作。
- reference/decomp/com/megacrit/cardcrawl/monsters/exordium/LouseNormal.java:45-68,124-148 与 LouseDefensive.java:48-71,127-151：红/绿 Louse 的 HP、bite、开战 Curl Up 和行动约束位于不同阶段。
- reference/decomp/com/megacrit/cardcrawl/powers/RitualPower.java:19-54：敌方 Ritual 有 skipFirst 内部历史，首次回合末不立即增加力量，随后才增加。
- reference/sts1-decompiled/com/megacrit/cardcrawl/screens/DrawPileViewScreen.java:217-229、DiscardPileViewScreen.java:213-220：游戏可以查看当前牌堆内容；无 Frozen Eye 时牌堆查看界面会排序显示。该证据支持“内容可见、真实抽牌顺序另行处理”，不支持把界面排序当作后端抽牌顺序。

这些材料证明的是正版侧的局部行为。正式训练环境怎样执行，仍以锁定的 sts_lightspeed 调用链和项目契约为准；二者不混写成全机制等价。

### 2.2 当前锁定后端调用链

    IroncladBattleEnv.reset(seed, encounter, ascension)
      -> new GameContext(IRONCLAD, seed, ascension)
      -> 覆盖 gc.floorNum=1、gc.curRoom=MONSTER、gc.info.encounter
      -> bc_=BattleContext()
      -> BattleContext::init(gc, encounter)
           -> 初始化 BattleContext 标志/RNG/药水/玩家 HP
           -> MonsterGroup::init
                -> createMonsters / Monster::construct
                -> 对每个敌人 rollMove
                -> 对每个敌人 preBattleAction
           -> 计算 cardDrawPerTurn
           -> CardManager::init
                -> 洗牌、innate/bottled 重排、建立 CardInstance
           -> BattleContext::initRelics
                -> 开战前遗物效果与动作队列
                -> 首轮抽牌、开战遗物效果、抽牌后效果
           -> 增加初始能量
           -> executeActions() 直到 PLAYER_NORMAL 或终局
      -> makeObservation()

    IroncladBattleEnv.step(action)
      -> 31 位动作解码为 CARD(hand slot,target) 或 END_TURN
      -> Action::execute
      -> BattleContext::executeActions
      -> makeObservation/reward/info

代码依据：

- 当前 Python 绑定的入口和字段：patches/lightspeed-battle-env.patch:116-141,167-216,266-297；应用后的文件对应 third_party/sts_lightspeed/bindings/bindings-util.cpp:231-360。
- BattleContext::init：third_party/sts_lightspeed/src/combat/BattleContext.cpp:17-77。
- MonsterGroup::init 先 rollMove 后 preBattleAction：third_party/sts_lightspeed/src/combat/MonsterGroup.cpp:76-89。
- CardManager::init：third_party/sts_lightspeed/src/combat/CardManager.cpp:15-69。
- action queue/card queue 直到玩家可决策：third_party/sts_lightspeed/src/combat/BattleContext.cpp:721-824。

## 3. 入口 A/B 字段与时点对照

### 3.1 入口 A：开战前 GameContext

入口 A 定义为：已经选定遭遇、尚未进入 BattleContext::init；此时没有本场 hand、draw_pile、敌人实例或当前显示意图。

| 字段族 | A 的内容 | 当前后端使用方式 | 属性 |
|---|---|---|---|
| 身份/版本 | character、游戏/后端版本、act、floorNum、curRoom、encounter、ascension | GameContext 字段见 include/game/GameContext.h:194-231；BattleContext::init 读取 seed/floor/encounter/ascension，地图检查读取 map/curMapNode/act | 必需；版本不匹配拒绝 |
| 环境种子 | gc.seed；精确复盘还需各 RNG 状态/计数 | BattleContext.cpp:24-34 用 seed+floor 初始化 aiRng、monsterHpRng、shuffleRng、cardRandomRng，继承 miscRng、potionRng | 可复跑，但 source seed 不等于精确复现 |
| 玩家持久状态 | curHp、maxHp、gold | BattleContext.cpp:49-55 复制到 bc.player | HP/maxHP 影响状态和 battle reward；gold 影响盗金等行为 |
| 牌组 | 牌实例 ID、升级/必要 misc 动态值、牌组顺序、bottle 索引 | CardManager.cpp:23-63 读取 gc.deck.cards 与 gc.deck.bottleIdxs | 牌序和动态值要完整；隐藏洗牌可重新采样 |
| 遗物 | 每个遗物 ID、data/counter、顺序；RelicContainer bitset | BattleContext.cpp:80-92 先复制 bitset，再按遗物列表安排触发 | 缺关键计数不能补 0 |
| 药水 | 完整槽位数组、potionCount、potionCapacity、容量来源 | BattleContext.cpp:49-51 复制；GameContext.cpp:200-215 展示 save loader 容量规则 | 缺库存或容量来源拒绝 |
| 地图/前房间 | map、当前节点、lastRoom、燃烧精英信息等 | BattleContext.cpp:58-60 检查燃烧精英；initRelics 读取 curRoom/lastRoom | 不一定进 Agent，但影响初始化 |
| RNG 精确状态 | 所有相关 stream 状态/counter | GameContext.h:157-173 列出多条流；SaveFile.h:85-145 保存多个 seed counter | exact replay 必需；重模拟可换环境复跑 seed |

GameContext 构造器还会初始化 RNG、地图、遭遇池、遗物池、角色初始牌组、遗物、HP、药水容量和 Neow 状态：third_party/sts_lightspeed/src/game/GameContext.cpp:35-72,429-523。当前 reset 只创建默认构造器并固定覆盖 floor/room/encounter：patches/lightspeed-battle-env.patch:126-141；没有自定义牌组、遗物计数或药水注入。

### 3.2 入口 B：第一决策点 BattleContext

入口 B 定义为：BattleContext::init 完成，executeActions 返回 InputState::PLAYER_NORMAL，outcome=UNDECIDED，没有尚未处理的 action/card queue；此时才交给 Agent 第一个动作。

| 字段族 | 当前可见内容 | 产生路径 | 内部依赖缺口 |
|---|---|---|---|
| 玩家核心 | HP/maxHP、block、energy、turn、四区数量、总敌方 HP、Strength/Vulnerable/Weak | bindings-util.cpp:318-331 | 其它 power、stance、orb、每回合计数、cardDrawPerTurn 未完整导出 |
| 手牌 | 槽位顺序、backend card ID、location、upgraded、costForTurn、known | bindings-util.cpp:297-305 | uniqueId、specialData、freeToPlayOnce、retain 未导出 |
| 三个非手牌区 | 内容按公开字段排序；不把真实顺序送进规范 Python 观测 | bindings-util.cpp:25-54,306-308 | 后端抽牌仍依赖 vector 顺序；hidden order 未形成恢复契约 |
| 敌人 | 物理槽位、ID、HP/maxHP、block、Strength、Vulnerable、Weak、语义 intent、伤害/次数、Curl Up、Ritual | bindings-util.cpp:82-105 | moveHistory[1]、miscInfo、status bits、unique powers、spawn/escape/half-dead |
| 遗物/药水 | 当前 Observation 不包含 | 后端仍有 bc.potions 和 relic bits；BattleObservation 不返回 | Agent 既不能观察也不能使用药水 |
| 控制状态 | 正常 B 应是 PLAYER_NORMAL，action mask 非空；终局全 False | bindings-util.cpp:259-275 | InputState/cardSelectInfo 不暴露，不能表达 pending choice |
| 隐藏随机 | info 可含 counter，但不进模型 | bindings-util.cpp:247-264；Python step 规范化 | 没有完整 stream state 时不能恢复 exact continuation |

### 3.3 BattleContext::init 的确定顺序

1. 清理终局/回合标志、队列、debug 标志，写入 seed/floor/encounter。
2. 初始化 battle RNG：aiRng、monsterHpRng、shuffleRng、cardRandomRng 来自 seed+floor；miscRng、potionRng 从 GameContext 继承。
3. 复制 ascension、药水计数/容量/槽位和玩家 HP/maxHP/gold。
4. MonsterGroup::init 创建敌人；Monster::construct 做 HP 和部分 miscInfo roll：Monster.cpp:109-135；每个敌人 rollMove，用 aiRng.random(99) 并更新 moveHistory[0/1]：Monster.cpp:629-641；然后执行 preBattleAction：MonsterSpecific.cpp:131-333。Louse Curl Up 就在此阶段消耗 monsterHpRng。
5. 设置基础抽牌 5，并根据 Snecko Eye/Ring of the Serpent 调整：BattleContext.cpp:62-68。
6. CardManager::init 用 gc.deck 建立 CardInstance，使用 shuffleRng.randomLong 加 Java LCG shuffle，处理 innate/bottled：CardManager.cpp:23-69。
7. initRelics 复制 relic bits，安排 pre-draw、base draw 后和抽牌后效果：BattleContext.cpp:80-92,367-453。效果可能生成临时卡、改变 HP/能量/状态、额外抽牌、施加敌方 debuff，或打开选择状态。
8. 执行 player.energy += player.energyPerTurn，并调用 executeActions：BattleContext.cpp:71-77。executeActions 处理完队列/卡队列后才置为 PLAYER_NORMAL：:748-823。
9. binding 从稳定 B 状态选取允许公开字段，生成 mask 和返回 Python。

因此 A 到 B 不是简单地“把 A 字段加上 hand/enemy”。A 的 relic.data、lastRoom、room、ascension、deck bottle/upgrade、map/burning-elite 可能在第 4 到第 8 步改变 B；如果日志已经是 B，必须记录这些效果已消费。

### 3.4 静态实现风险

BattleContext::init 复制了 curHp/maxHp/gold，但没有看到 player.cc = gc.cc：BattleContext.cpp:49-55。后续随机卡/药水生成使用 player.cc，例如 BattleContext.cpp:2314-2318,2823-2825 和 Actions.cpp:550-567。当前正式入口固定 Ironclad 且 CharacterClass::IRONCLAD=0，现状探针不会暴露问题；多角色或含随机生成卡/药水的扩展 reset 不能依靠零初始化偶然正确。

## 4. 汇总日志能否使用

### 4.1 必要条件不是二元的“有/无手牌”

| 目标 | 最低时点 | 必须可验证字段 | 缺失后的处理 |
|---|---|---|---|
| A 驱动重新模拟 | BattleContext::init 之前 | 角色/版本、ascension、act/floor/room/encounter、当时牌组实例和升级/动态值、玩家 HP/maxHP、遗物 ID+计数、药水槽位+容量、影响初始化的地图/前房间字段 | 可不需要 hand/intent；后端重新生成，但只能叫重新模拟 |
| B 直接恢复 | PLAYER_NORMAL 第一决策点 | 身份/版本、玩家可见状态、手牌槽位和费用、三堆内容、敌人实体顺序/HP/公开状态/显示意图、未来相关遗物/药水、控制状态稳定 | 有完整 A 可退回 A；否则缺字段拒绝 |
| 原局精确回放 | A 或 B | 还需完整 RNG state/counter、真实牌堆顺序、敌人 move history/unique state、CardInstance 动态值和稳定版本 | 不能用重新模拟冒充 |

隐藏洗牌、敌人 HP/意图 roll、Louse 颜色/Curl Up 等可在 A 模式由 environment replay seed 重新生成，但必须同时保留 source_run_id、source_floor、source_state_timing、environment_replay_seed、resampling policy 和 exact_historical_replay=false。源 run seed 与模拟器复跑 seed 分开；当前 battle 随机还依赖 floorNum。

### 4.2 当前汇总 .run 结果

并行 M2 审计固定 MaT1g3R/Slay-the-Spire-data 提交 097aaf3564c2247835162d267cbc7c55d2c9039e，扫描 157 个 Ironclad .run，按数据集分层、路径字典序轮询选择 12 个，不按胜负筛选，也不称随机或代表性抽样。12 个独立 run 全为 A20，版本为 2022-03-07 6 个、2022-12-18 6 个。

这些汇总记录有最终 master_deck、逐层 HP、最终遗物、药水历史、路径和选择，但没有逐楼层战斗入口。审计函数明确写入：

    SUMMARY_ONLY_NO_BATTLE_ENTRY
    FINAL_MASTER_DECK_NOT_ENTRY_DECK
    NO_HAND_DRAW_DISCARD_INTENT_SNAPSHOT

这个判据对当前样本是必要且正确的：最终 master_deck 不能代替某一战斗入口牌组，damage_taken 不能提供每场完整敌人初态。当前结论是 12/12 汇总样本不能生成 A/B 场景，不是断言所有未来汇总格式永久不可用。

### 4.3 当前详细 JSONL 结果

reference/public-run-audit/runlogger/ironclad_1706139943.jsonl 的每层首个战斗快照位于 action:select_map 后的第一个 state:floor，包含：

- state:floor.deck，该层牌组而不是最终牌组；
- combat_state.hand、draw_pile，后续快照可能有 discard/exhaust；
- combat_state.monsters 的 ID、HP/maxHP、当前 intent，部分记录有 damage/hits/powers；
- combat_state.player.energy；
- 该时点的 HP/maxHP、药水槽位和遗物列表；
- run 级角色、源 seed、ascension、版本和 mod。

脚本保留 pre_initialization_snapshot_available=false、hidden_state.rng_counters_recorded=false、exact_historical_replay=false，并将时点标为 post_combat_initialization_after_initial_draw。这个 A/B 分离方向正确：该快照更接近 B，而不是可再次调用 BattleContext::init 的 A。

| 数据 | 当前结果 |
|---|---:|
| 汇总 run | 12；not_reconstructable=12 |
| 详细独立 run | 1；JSONL 231 条记录 |
| 详细战斗快照 | 7 |
| 字段层面可重建但后端待注入 | 2（Cultist、Jaw Worm） |
| 排除的详细快照 | 5 |
| 详细 run 版本 | A0；STS 12-18-2022 |
| 详细 run mod | CommunicationMod、SerializationMod 之外还有 basemod、superfastmode；游戏性影响未核实 |
| 隐藏 RNG | 未记录；可重新采样，不能精确回放 |
| 正式划分 | formal_split_applied=false；audit-only |

两个 B-pending 场景不能直接用于当前 Python 环境：当前 registry 只有三张基础牌，binding 没有 B 注入，详细日志没有完整 RNG/敌人内部历史；也不能进入 PPO on-policy batch。

## 5. 公开样本审计脚本和报告预审

### 5.1 已有的正确边界

当前 scripts/audit-public-runs.py 已包含：

- 固定提交、固定 URL、HTTPS 默认证书校验和重试：:89-123；没有关闭 TLS。
- 按数据集分层、字典序轮询抽样，并明确不称随机/代表性：:192-220。
- 整局 group key 和固定 SHA-256 分桶，重复 group 直接拒绝：:223-247。
- 卡牌重复实例和升级后缀保留；不完整 + 标记显式报错：:250-277。
- 遗物省略计数保留 counter_recorded=false，不默补 0；药水数组缺失不视为空槽：:298-337。
- 敌人缺 HP/intent 时拒绝，block/damage/hits 缺失保留 recorded 标记：:360-397。
- 汇总 .run 不使用最终 master_deck 生成战斗入口：:486-538。
- 详细日志按每层首个战斗快照生成场景，分开 entry_timing、hidden_state 和 field_evidence：:541-749。
- 输出原始样本哈希、source manifest、audit/exclusion/scene index；约 29 GiB archive 只取 metadata：:880-1018,1034-1179。

当前生成物快照：

| 文件 | SHA-256 |
|---|---|
| scripts/audit-public-runs.py | 3B14FDF04050F0406FB7AB78514835072A1CE44A11D35D6AE3AC41BC2E3F8336 |
| reference/public-run-audit/audit.json | 50539B3E9E1DB6A4886C278DC0CA008C39D81C47676A44481FF8567115217B7D |
| reference/public-run-audit/scene-candidates.json | 204AD5445062809D464874A202AEB65F2012C7D79EED41B655AB6FAB9C5E45A7 |
| reference/public-run-audit/exclusions.json | C1442110659A1B7D3F34F9D196878994E8417A8739392C7E9386F668E41C2CE5 |
| reference/public-run-audit/source-manifest.json | 10FF7B89A40B83A40C9776A05CA14B6AE4C89DDF7A4F2140650CD84FF5DCFFBA |
| docs/m2-evidence-index.json | 7033A6CFBFFAE57799E15EC8CCF137FB8EDAFD61484BF63241A012D6166DF2AD |

### 5.2 仍需主审查的缺口

1. audit_scene 的最终状态主要由 reasons 是否为空决定：:648。encounter_info 可返回 scenario_id=None、group_match=unregistered，但没有把未注册遭遇自动加入排除原因：:473-482,641-648。只要其它字段完整，未知敌人可被标为 reconstructable_but_backend_pending。合成探针确认了这一行为。因此字段可解析不等于后端可运行，主 M2 需要独立的 encounter/backend eligibility 层。
2. 缺遗物计数只在 dynamic_ids 或人工 KNOWN_DYNAMIC_RELICS 中命中时阻断：:53-71,626-633。该人工列表不是从全部 RelicInstance/initRelics 行为自动派生的穷举证明，遗漏的行为依赖可能被放过。
3. power_map(None) 返回空字典，只保留 powers_recorded=false：:340-357,688-689，不把缺失玩家/敌人 power 加入 reasons。除非 serializer 语义已经确认缺失就代表空，否则 B 候选仍有关键字段歧义。
4. parse_card_instance 能解析任意 +N：:250-264，但锁定后端普通 Card 只有布尔 upgraded，Searing Blow 还需 misc：Card.cpp:9-14,20-26。合成探针表明 Searing Blow+2 被保留但不排除；正式 map 前必须拒绝或单独编码动态值。
5. B 场景 draw_pile 被标为 logger 记录的顺序，但是否是内部 top-to-bottom 顺序、是否经过 serializer/界面排序仍需固定 logger 版本的一手语义核验。模型侧不应使用该顺序；精确后端恢复才可使用。
6. potions.capacity=len(potions) 是日志数组长度，不自动证明 Potion Belt/进阶容量规则：:712-717。它可作为直接记录，但不能代替环境配置中的容量规则。
7. scene 候选没有验证牌组与 hand/draw/discard/exhaust 的多重集守恒，也没有把 CardInstance.specialData、costForTurn、freeToPlayOnce、retain 纳入 B 恢复检查。
8. tests/test_public_run_audit.py 已覆盖 TLS、抽样、重复分组、缺药水、缺动态计数、升级歧义、时点歧义和基本成功路径；尚未覆盖未知 encounter、缺 powers、+2/Searing Blow、牌堆守恒和 B hidden history。

合成只读探针的三个结果：

- 未知敌人 ID：status=reconstructable_but_backend_pending，scenario/backend 为 null，reasons 为空。
- 缺 player powers：powers_recorded=false 但 status 仍为 reconstructable_but_backend_pending。
- Searing Blow+2：原始卡牌被保留，但 status 仍为 reconstructable_but_backend_pending。

这些仅是工具行为证据，不是实际数据可用性证据。

### 5.3 建议的分类层级

建议主 M2 保留三层，不合并：

    field_complete_for_A_resimulation
    field_complete_for_B_snapshot_injection
    backend_and_registry_eligible

hidden_rng_missing_but_resampling_allowed 只影响精确性标签，不应单独否定完整 A。missing_relic_counter、missing_potion_inventory、时点不明、动态卡值不明、未注册遭遇和关键 visible power 不明，应阻止正式候选。所有候选仍保持 audit-only，直到 M3 完成后端注入和行为验收。

## 6. 两种 reset 入口的字段契约

本节是预审提出的最小字段集合，不是主 M2 的正式动作/配置裁定。

### 6.1 A 入口 pre_battle

#### 必需字段

    contract:
      environment_config_id
      backend/source version
      schema/registry/action/serialization versions
    identity:
      character
      act, floor, room, encounter
      ascension
    player:
      current_hp, max_hp, gold
    deck:
      ordered card instances: backend_card_id, upgraded/misc/dynamic value
      bottle assignments by stable deck instance/index
    relics:
      ordered instances: relic_id, data/counter, counter applicability
    potions:
      full slot array including explicit empty slots
      potion_count, potion_capacity, capacity_source
    context:
      last_room and map/burning-elite context when consumed by init
    replay:
      source_run_id/floor/timing
      environment_replay_seed
      exactness mode

seed 必须明确是 source provenance 还是 environment replay seed；当前后端公式还消费 floor。A 不应把 hand/enemy 当已结算事实；若同时存在，应选择 B 模式，不能两次初始化。

#### 可再生成字段

- battle RNG 派生的初始洗牌和真实抽牌顺序；
- 敌人随机成员、HP roll、初始意图、Louse bite/Curl Up；只在 encounter 语义和样本证据允许时；
- 没有需要精确匹配的历史动作时，CardInstance.uniqueId 可按固定顺序重新分配；
- 由牌组/遗物/房间/进阶确定的派生 bitset、牌组计数和容量校验值。

每项必须写入“重新采样/派生”状态，不得伪装为原局内部值。

#### 拒绝条件

- 版本/角色/遭遇未注册，ascension 不在配置白名单，房间时点不明确；
- 牌组不是当时入口牌组，缺实例升级/动态值、bottle 关系或存在未知 backend card；
- 遗物 ID 未注册、关键 data/counter 缺失，或药水库存缺失；
- 药水槽位、容量和 Potion Belt/进阶规则矛盾；
- HP/maxHP 非法、牌组容量或生成上界无法证明；
- 开战效果会进入当前 binding 不支持的 CARD_SELECT、多选、stance/toolbox 等状态；
- 调用者要求 exact replay 但没有完整 RNG stream/counter、版本和必要地图/隐藏状态；
- 当前旧 API 收到自定义 A 字段时，不得静默忽略并回退默认牌组。

### 6.2 B 入口 post_init

#### 必需字段

    contract:
      environment_config_id and all schema/capacity/action hashes
    identity:
      character, act, floor, room, encounter, ascension, source version
    player_visible:
      hp, max_hp, block, energy, turn
      included visible powers/status, stance/orb fields if supported
    cards:
      hand in exact slot order
      draw/discard/exhaust contents with upgraded/cost/dynamic values
      card identity needed for future targeting/removal
    enemies:
      physical slot order, id, hp/max_hp, block, visible statuses
      current displayed intent and visible damage/hit count
    potions/relics:
      full future-relevant inventory and dynamic counters
    control:
      input_state=PLAYER_NORMAL, outcome=UNDECIDED
      action_queue/card_queue empty, no pending cardSelectInfo
    hidden_restore:
      exact RNG/order/history, or explicit resampling mode

#### 可再生成字段

- 在 B resampling 模式中，抽牌堆内部顺序可按公开多重集和 environment replay seed 重新排列；
- 敌人 moveHistory[1]、miscInfo、未暴露 unique power/status bit 可重新采样，但当前显示 intent、HP 和公开状态要保持；
- nextUniqueCardId、由卡堆内容派生的计数、action mask 可重算；外部 mask 只能用于一致性检查；
- exact B 中以上 hidden 字段不能重新生成，必须直接恢复。

#### 拒绝条件

- 时点不是第一可决策点，或仍处于 CARD_SELECT/多选/stance/potion choice；
- 缺 hand/pile/enemy/player 核心字段、关键 visible power、动态卡值、遗物计数或药水槽位；
- 数量超过容量、重复记录无法解释、牌堆与牌组/生成牌来源守恒失败；
- 敌人行顺序、死亡/逃跑/半死亡语义与 mask 不一致；
- hidden order/history 缺失但调用者声明 exact replay；
- 未知卡/敌人/遗物/药水，或版本/registry/action hash 不匹配；
- 当前 API 仍只支持 seed/encounter/ascension 时，B 字段必须显式报“不支持 B 注入”，不能偷偷按 A 重跑。

### 6.3 一次性效果与恢复模式

| 效果 | A 模式 | B 模式 |
|---|---|---|
| MonsterGroup::init 构造/rollMove/preBattleAction | 运行一次 | 已发生，不得再运行 |
| CardManager::init 洗牌和建牌 | 运行一次 | 已发生，只恢复 card instances/piles |
| BattleContext::initRelics | 运行一次，按 counter/room/HP 执行 | 已发生，需要保存已执行边界或直接不调用 |
| 首轮抽牌及抽牌后遗物 | 运行一次 | 已发生，hand/piles 是结果 |
| 隐藏洗牌/敌人 roll | A 可复跑 seed 重采样 | B 只能重采样 hidden 部分 |
| uniqueId/specialData | 从 A 牌组实例建立 | B 直接恢复或提供可验证动态值 |

## 7. 当前接口迁移审计

### 7.1 bindings 到 checkpoint 的依赖表

| 顺序 | 层 | 文件/符号 | 当前事实 | 迁移依赖 |
|---:|---|---|---|---|
| 1 | C++ binding | patches/lightspeed-battle-env.patch:23-105,116-297；BattleObservation/IroncladBattleEnv | CARD_FEATURES=5、ENEMY_FEATURES=12、GLOBAL_FEATURES=13；MAX_HAND=10、MAX_ENEMIES=5、ACTION_COUNT=31；只输出三种基础牌 | reset mode、输入状态、牌/药水/遗物字段、目标容量、字段哈希、mask |
| 2 | 规范观测 | sts/env/lightspeed.py:23-56,70-82,234-303,306-413 | 再声明字段 tuple、容量和 31 动作；raw pyd reshape/验证 | 从集中契约校验，不保留第二份独立宽度真相 |
| 3 | registry | sts/env/registry.py:12-115 | schema 2、registry 1、PAD=0；只有 Bash/Defend/Strike；TargetKind 只有 NO_TARGET/ENEMY | 新卡/状态牌/药水/目标语义、稳定 ID、content hash |
| 4 | 双 wrapper | sts/env/wrappers.py:23-78,238-333,383-414 | PILE_CAPACITY=10、CARD_CAPACITY=20；Flat/Token 同源；超 10 报错 | 容量、字段、known/valid、intent 编码、变量 pile shape |
| 5 | 模型 | sts/models/mlp.py:109-175,178-239,240-339 | batch shape 依赖容量；policy_head 是 31；target embedding 是 3；checkpoint contract 未含 action/capacity/field hash | 派生模型 config/head，写入环境 config、容量、动作和字段 hash |
| 6 | 单步 Agent | sts/agents/masked_policy.py:14-79、mlp_agent.py:16-51 | probabilities 固定 [31]；Agent 内 mask 后抽样 | 分布宽度、mask 版本、药水/二次选择状态 |
| 7 | runner | sts/agents/episode_runner.py:19-83 | 校验 0..30；runner 不重算游戏规则；EpisodeTrace 只有动作/回报/终止 | 由动作契约校验，轨迹写 config/hash |
| 8 | 轨迹序列化 | scripts/run_week4_t5.py:34-54,341-403,410-455 | SERIALIZATION_VERSION=2；语义字段和 mask/action 单独序列化 | reset mode、场景 ID、字段顺序 hash、容量/动作版本 |
| 9 | PPO 采集 | sts/train/ppo.py:41-123,204-249,317-348 | PPOConfig 固定 minimal-v1；collector 只 reset seed/encounter；active 只存 seed/encounter/actions/reward | 新初态配置、场景 ID、reset mode、完整 metadata |
| 10 | checkpoint | sts/models/mlp.py:342-413、sts/train/ppo.py:424-453 | MLP format 2、PPO trainer 2；检查 schema/registry/scales/backend/reward，但未显式检查 action/capacity/config | 不兼容版本明确拒绝，保存完整契约指纹 |

### 7.2 当前动作语义

当前正式 card action 为：

    0..29 = hand_slot * 3 + target_column
    30    = END_TURN

Python 教学动作层也写死 MAX_TARGET=3、END_TURN=30、N_ACTIONS=31：sts/env/actions.py:10-51。C++ makeActionMask 使用 action/3 和 action%3：bindings-util.cpp:264-275。

- MAX_ENEMIES=5 是观测物理行容量，不是五个可寻址目标。
- TargetKind 在 registry 中区分 NO_TARGET 与 ENEMY，但 no-target 仍使用动作列 0 作为占位；敌人 0 不能与 no-target 混淆。
- 上游 ActionType 已有 POTION、SINGLE_CARD_SELECT、MULTI_CARD_SELECT、END_TURN：include/sim/search/Action.h:24-60；Python IroncladBattleEnv 只导出 31 位 card/end-turn。
- isValidPotionAction 允许 source index 0..5，但 BattleContext::potions 长度为 5，并以 target>5 表示丢弃：src/sim/search/Action.cpp:66-99。该内部接口不能直接成为新 Python 契约。

若主 M2 选择五个可寻址目标，action_count、解码、mask、目标换位、AgentDecision、模型 head、轨迹和 checkpoint 必须一起建立新版本；10*5+1=51 只是容量推导候选，不是本报告批准的动作编号。

### 7.3 最小集中契约

建议新增一个主 M2 可裁定的机器可读契约源，至少包含：

    environment_config_id
    backend_commit / adapter_patch_hash
    reset_modes: pre_battle, post_init
    schema_version / registry_version / registry_hash
    field_order_hash / numeric_encoding_version
    hand_capacity / enemy_observation_capacity / target_capacity
    pile_capacity / potion_slot_capacity
    action_vocab_version / action_count / end_turn representation
    serialization_version / checkpoint_format_version
    allowed cards / encounters / ascension buckets / secondary-input states

建议顺序：

1. 主 M2 先裁定 A/B canonical timing、字段可见性、容量、版本和动作词表。
2. binding 新增显式 reset mode 和输入校验；A 只调用一次 BattleContext::init，B 只恢复稳定 BattleContext。
3. Python 只做 raw binding 到规范 dict 的字段/shape/dtype 校验；registry 承担稳定语义 ID。
4. 双 wrapper 共享同一 contract-derived 预处理。
5. MLP/Set/DT 共用输入契约和数值编码版本；MLP head、AgentDecision、runner 不独立写 31。
6. 轨迹和 checkpoint 保存环境 config、reset mode、场景 ID、字段/动作/容量 hash、backend/patch hash、source/replay seed policy。
7. 先做 reset/观测/mask/容量/版本回归，再做卡/遭遇行为测试，最后才允许从头短训。

旧 minimal-v1 应作为独立配置保留：schema 2、registry 1、PILE_CAPACITY=10、31 动作和现有 MLP checkpoint。新 public-scene 或 medium config 即便使用同一 battle_reward_v1，也不继承旧权重的训练/评估结论。

## 8. 扩展项影响

### 8.1 五敌目标

- 观测层已有 5 行，但 binding 的 mask、intent 映射和 enemy encoding 必须能处理物理槽 3/4。
- Gremlin Gang 静态创建 4 个敌人，Lots of Slimes 创建 5 个：MonsterGroup.cpp:97-155；当前 31 动作不能寻址槽 3/4。
- Large Slime 分裂使用原槽位和相邻槽位重建实例：MonsterSpecific.cpp:3342-3367；不能按起始只有一个敌人证明全过程不越界。
- 死亡/逃跑槽位不能压缩重编号；新动作要测试中间槽死亡后 index 保持稳定。

### 8.2 药水目标和无目标

- 后端已有 potionCount/potionCapacity/potions[5] 和 drinkPotion(idx,target=0)：BattleContext.h:83-85,159-162。
- 当前 Python Observation、wrapper、MLP 和 AgentDecision 没有药水字段/动作；POTION 只存在上游内部。
- 必须区分槽位、喝/丢弃、无目标、单敌目标、全体效果、二次选择；不能让 target 0 同时表示无目标和敌人 0。
- 容量受 ascension 影响，save loader 还会因 Potion Belt 增加：GameContext.cpp:200-215；容量必须显式版本化。
- drinkPotion 可能打开 Discovery、stance、multi-select 或弃牌堆选择：BattleContext.cpp:2246-2426。选择语法未接入前，含这些可达路径的场景拒绝。

### 8.3 二次选择

- InputState 明确列出 CARD_SELECT、stance、Toolbox、药水多选等：include/combat/InputState.h:10-54。
- CardSelectInfo 保存 task、pick count、可否零选/任意数量和候选卡：include/combat/CardSelectInfo.h:14-75。
- Action.cpp 可以枚举手牌、弃牌、抽牌堆和消耗堆选择：:126-224,477-550，但当前 Python mask 只覆盖 PLAYER_NORMAL 的 card/end-turn。
- 需要二次选择的卡/药水不能让后端自动代选；要么把完整状态/动作语法纳入新版本，要么延期。

### 8.4 可变牌堆容量

- 后端手牌固定 10；draw/discard/exhaust 在配置上可为 vector 或 fixed-list 64，牌组最大 96：CardManager.h:22-42、Deck.h:25-31。
- 临时牌、状态牌、复制牌、消耗和分裂会使非手牌总数超过初始牌数：CardManager.cpp:87-130,174-185。
- Python 当前把三种非手牌合并为 PILE_CAPACITY=10，超出即拒绝：wrappers.py:257-280。扩容必须从配置、生成路径和任务上限证明上界。
- CARD_CAPACITY、FLAT_LAYOUT、MLP trunk dimension 和 checkpoint shape 都随容量变化；容量变化必须新 config/hash/version。

### 8.5 进阶字段

- ascension 不只是敌人 HP：A10 加 Ascenders' Bane，A14 改 Ironclad maxHP，A6 改当前 HP，A11 改药水容量：GameContext.cpp:66-67,477-523。
- Monster 构造、preBattleAction 和行动按 A2/A3/A7/A8/A17/A18 等阈值改变：Monster.cpp:26-120、MonsterSpecific.cpp:131-333,335-347。
- A10 必须把 Ascenders' Bane 纳入牌组/registry/容量；A11 必须有药水 obs/action；A6/A14 影响初态和 battle reward。
- 当前 binding 明确拒绝非零 ascension：bindings-util.cpp:241-246。不能把 A20 样本默降到 A0。

## 9. 旧 minimal-v1 与 checkpoint 兼容边界

### 9.1 可保持独立的部分

- 旧三类卡的 registry ID、TargetKind、A0 三遭遇和 31 位 card/end-turn 动作可以在旧配置继续使用。
- 旧 minimal-v1 的 pyd、双 wrapper、MLP checkpoint 和 PPO 结果只适用于其保存的 schema/registry/numeric/backend/reward 范围。
- 新配置可复用 battle_reward_v1 定义，但不等于复用旧输入 shape、场景分布或训练结论。

### 9.2 必须拒绝

- PILE_CAPACITY、目标容量、动作数、registry hash、字段顺序或 enemy 类别编码变化；
- reset mode 或 environment_config_id 变化；
- 新增可见动态字段而旧 checkpoint 没有相应输入契约；
- backend/patch/pyd hash 不一致；
- reward/termination/task metadata 不一致；
- 旧 episodes.jsonl/T5 serialization 没有新字段却被当作新 config 轨迹。

load_mlp_checkpoint 当前只比较 schema、registry、数值编码和 scale：sts/models/mlp.py:342-413；PPO load 还检查 trainer version、reward contract、backend hash 和 collector：sts/train/ppo.py:424-453。它尚未把动作/容量/config hash 全部纳入，因此不能把当前 loader 的 shape 加载失败当成充分的版本拒绝设计。

## 10. 可实施验收用例与当前状态

除“实际探针”项外，本节新增用例均未在本任务运行。

| 编号 | 用例 | 期望 | 当前状态 |
|---|---|---|---|
| RST-01 | A 单次初始化 | 同一 A 输入只执行一次 preBattleAction、遗物效果、首轮抽牌；一次性计数不重复 | 未运行；当前无 A 注入 |
| RST-02 | B 不重复效果 | 注入已抽牌 B 后，首个动作前 hand/piles/HP/energy/intent 不被再次初始化 | 未运行；当前无 B 注入 |
| RST-03 | reset roundtrip | serialize(A) 或 serialize(B) 后，公开字段、排序、多重集和 mask 一致 | 未运行；当前没有 state snapshot API |
| RST-04 | 同场景同复跑 seed | 同一 A、同一环境复跑 seed、同一 backend/version 得到逐步相同公开观测、mask、reward、termination | 现有 A0 同 seed 实际探针通过；扩展未运行 |
| RST-05 | 不同 seed 隐藏变化 | 不同 seed 可改变隐藏/公开随机结果；不要求每次都不同，但要记录 resampling policy | 扩展未运行 |
| RST-06 | 缺关键字段 | 缺 deck/HP/version、遗物计数、药水、B hand/pile/intent/dynamic value 显式拒绝 | 公开审计合成部分通过；后端未实现 |
| RST-07 | 遗物/药水时点 | A 的 counter/slots 在效果前注入；B 已消费效果不重复；容量一致 | 未运行 |
| RST-08 | enemy history 边界 | 公开 B 相同、moveHistory/miscInfo/RNG 不同的 backend 状态可有不同后续转移；Agent 输入相同 | 未运行；无 hidden 注入构造器 |
| RST-09 | mask 与解码 | 全 Agent mask 与 C++ mask 逐步一致；no-target 不产生 target 1/2；终局全 False | 现有 minimal-v1 有历史回归；本任务未重跑 |
| RST-10 | 五目标最大目标 | 物理槽 0-4、死亡中间槽、分裂/召唤后的最大 index 与动作语法一致；不重编号 | 未运行；动作未裁定 |
| RST-11 | 药水目标 | 目标型/无目标/丢弃/二次选择药水的 mask、解码、槽位消耗和后端调用一致 | 未运行；Python 未暴露药水 |
| RST-12 | 二次选择闭环 | CARD_SELECT/stance/multi-select 不返回空 mask 假装可结束；完整支持或显式拒绝 | 未运行；当前 binding 不支持 |
| RST-13 | 容量上界 | 由牌组、生成/复制/分裂和任务上限推导 hand/pile/enemy/potion 上界；超界先拒绝 | 当前 wrapper 只有 10 的防守性拒绝；扩展未运行 |
| RST-14 | 迁移版本拒绝 | 旧 checkpoint/trajectory 加载新 config/action/capacity/registry/field hash 显式失败 | 新集中契约未实现 |
| RST-15 | 公开候选分类 | 只有完整 A 字段才进入 A-resimulation；B 快照进入 B-pending；不混成 exact replay | 当前脚本已生成标签；缺口见第 5 节 |
| RST-16 | split 泄漏 | 同一整局、重复记录、同源场景和随机复跑不跨 split；source/env seed 分开 | 当前 audit-only group check 无重复；正式 split 未应用 |

当前历史回归、本次 A0 探针和 wrapper 合成测试不能替代 RST-01/02/03/08/10/11/12/13/14。尤其 wrapper 换位测试不能证明 C++ 能从真实 A/B 状态恢复。

## 11. 复现命令、实际探针和未运行项

### 11.1 实际只读命令

    git rev-parse HEAD
    git -C third_party/sts_lightspeed rev-parse HEAD
    git -C third_party/sts_lightspeed apply --reverse --check patches/lightspeed-battle-env.patch
    $env:PYTHONPATH = 'third_party/sts_lightspeed/build;' + ($env:PYTHONPATH ?? '')
    python -X utf8 -c "import slaythespire as s; e=s.IroncladBattleEnv(); o=e.reset(100000,s.MonsterEncounter.TWO_LOUSE,0); print(o.hand,o.enemies,getattr(o,'global'),o.action_mask)"

实际结果：扩展导入成功；A0 seed=100000 的三个遭遇均返回 B；同 seed/同遭遇的 hand/enemy/pile/global/mask 相等。根据当前 binding 的静态拒绝分支，Gremlin Gang 和非零 ascension 不在现有 API 范围；本任务没有重复调用这两个负向案例。探针没有写入正式环境或配置。

### 11.2 公开审计产物复核

    Get-Content -Raw reference/public-run-audit/audit.json | ConvertFrom-Json
    Get-Content -Raw reference/public-run-audit/scene-candidates.json | ConvertFrom-Json
    Get-Content -Raw reference/public-run-audit/exclusions.json | ConvertFrom-Json
    Get-FileHash scripts/audit-public-runs.py,reference/public-run-audit/*.json -Algorithm SHA256

当前输出 audit_schema_version=m2-public-run-audit-v1；汇总 12 条全部排除，详细 7 个场景为 2 个 reconstructable_but_backend_pending 和 5 个 excluded；formal_split_applied=false。本任务没有重新下载 GitHub/Archive，也没有运行 M2 脚本生成新的共享产物。

### 11.3 明确未运行

- 未修改或重建 sts_lightspeed、Python binding、wrapper、模型或 checkpoint。
- 未构造新的 C++ A/B state injection API；未绕过正式 binding 以内部 BattleContext 构造替代 API 证据。
- 未运行 RST-01/02/03/07/08/10/11/12/13/14 的扩展测试。
- 未运行扩展遭遇、A1-A20、药水/遗物/二次选择/生成牌压力验收。
- 未启动 PPO、规则 Agent、Gate 2/3 或训练/评估；未修改 eval_seeds.json。

## 12. 待主审决定事项和明确缺口

1. 选择 canonical reset 时点：真实公开样本优先按 A 重模拟，还是把 detailed logger 的 B 快照作为首批后端注入目标；两者可以并存，但必须不同标签。
2. 裁定 A/B 输入中哪些 hidden state 允许按 environment replay seed 重采样；没有完整 RNG 时不能写 exact replay。
3. 审核公开审计脚本的未注册 encounter、缺 powers、动态遗物穷举、+N 动态卡值、牌组/牌堆守恒和 potion capacity 缺口，再决定两个 B-pending 场景能否进入 M3。
4. 锁定详细样本的版本和 mod 边界；basemod/superfastmode 的游戏性影响目前未查明。
5. 定义 environment_config_id、容量字段、字段 hash、动作 vocabulary 和 serialization version；本报告不分配五目标或药水动作编号。
6. 决定五目标动作是否建立新动作版本；在决定前不能开放目标槽 3/4 的遭遇。
7. 决定二次选择首批完整接入还是延期；不能让后端代选隐藏玩家决策。
8. 为 CardInstance.specialData、多次升级、freeToPlayOnce、retain、enemy move history/miscInfo 和 visible powers 建立“恢复字段 vs Agent 可见字段”双清单。
9. 补齐 checkpoint/轨迹对 action/capacity/config/field hash 的显式校验，保证旧 minimal-v1 独立。
10. 主审确认后再进入实现；本报告不批准任何正式白名单、训练场景或 Gate。

## 13. 交付边界

本文件是本并行任务唯一交付物。已完成：

- 入口 A/B 字段与时点对照、锁定后端初始化顺序和一次性效果风险；
- 汇总日志必要/充分条件、当前公开样本结果和重新模拟与精确回放的边界；
- 公开审计脚本/产物的判据审查和主审缺口；
- 两种 reset 的必需字段、可再生成字段、拒绝条件；
- bindings 到规范观测、registry、双 wrapper、模型、Agent/runner、轨迹/checkpoint 的散落常量和迁移顺序；
- 五目标、药水、二次选择、可变牌堆容量、进阶字段及旧 checkpoint 兼容边界；
- 可实施验收用例、实际/历史/未运行状态和主审待决事项。

没有修改正式环境或共享规格。完成后等待主审。
