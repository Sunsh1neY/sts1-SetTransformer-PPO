> 2026-09-12实施更新：当前首批已执行契约以 `sts/env/public-battle-contract.json` 和
> `docs/public-battle-implementation.md` 为准。本文下列内容保留为早期研究提案；其中50回合新硬上限、
> 固定B0 shape等没有被直接实施。实际采用独立66动作、完整变长语义牌堆与外部动作预算。

# M2 真实公开战斗初态契约

日期：2026-09-11。状态：第二轮主审已修订；本文是尚未锁定的研究契约，M2仍未完成。
优先原生入口A；来源规则兼容、正式内容/容量和数据划分未完成前，不作为M3完整实现契约。`docs/m2-battle-contract.md` 保留为撤销的人工15张牌组
机制诊断历史，不能被本契约当作正式训练分布。

本文依据 `spec-v6.md`、`docs/decisions.md`、锁定的
`sts_lightspeed` commit `7476a81954020087da31d41d16fddf475746ec2d`，以及真实公开
场景索引 `docs/m2-scene-candidates.json`。M2 的实际数据证据见
`docs/m2-public-data-audit.md`。

2026-09-12批量A增补：`docs/m2-corpus-index.json`保存257个规则候选、118个run。
该批A使用 `initialization_phase=before_destination_room_entry`，前层HP/gold指标的时点先于
目的房间onEnterRoom；未来后端需执行一次房间入口与战斗初始化。药水槽位采用
`canonical-inventory-slots-v1`，不声称原槽位回放。此为独立研究输入，不能直接套用后文B0
容量或把候选直接当作M3批准批次。来源兼容、整副卡组/遗物/药水动作闭包及容量仍需逐场验收。

## 1. 契约身份与不变边界

### 1.1 两个环境不能混用

| 项目 | `minimal-v1`（现行正式环境） | `public-battle-v1`（本 M2 契约，待 M3） |
|---|---|---|
| 初态 | 固定 Strike×5、Defend×4、Bash×1 | 来自公开玩家 pre-init 构造或有完整证明的 post-init snapshot |
| 版本 | observation schema 2、registry 1、现行 action 31 | reset schema 1、observation schema 3、registry 2、action schema 2（提案锁定值，尚未实现） |
| reset | `seed + encounter + ascension` | 显式 `BattleScene` + 独立 environment replay seed |
| 遭遇 | A0 的 Jaw Worm、Cultist、Two Louse | 逐场景登记；首批只有真实索引中的 Cultist/Jaw Worm 候选，后续批次另审 |
| 手续 | 当前 C++ 自行初始化、洗牌、抽牌 | `post_combat_initialization_after_initial_draw` 场景必须恢复已结算状态，不重复触发开战效果 |
| 模型结论 | 旧 checkpoint/旧 PPO 结果只属于 minimal-v1 | 新 schema、shape、registry、action、奖励任务元数据不兼容时明确拒绝加载 |

本表新环境列只是待完善的研究输入；在 M3 完成前，不能用解除 Python 白名单或补零把
它变成可运行环境。`minimal-v1` 的代码、回归、checkpoint 和 `eval_seeds.json`
保持原样。

### 1.2 版本和哈希字段

M3 必须集中生成并保存以下字段，不允许在 C++、wrapper、模型和 runner 中分别写
常数：

```text
contract_id              = "public-battle-v1"
reset_schema_version     = 1
observation_schema       = 3
card_registry_version    = 2
action_schema_version    = 2
trajectory_schema        = "public-battle-trajectory-v1"
scene_serialization      = "battle-scene-v1"
field_order_hash         = SHA-256(固定字段顺序的 canonical JSON)
capacity_manifest_hash   = SHA-256(本场景容量清单的 canonical JSON)
registry_hash             = SHA-256(固定 registry 条目的 canonical JSON)
```

这里的 `observation_schema=3`、`registry=2` 和 `action_schema=2` 是新公开战斗
契约的预登记值，不表示当前 Python/C++ 已经实现。旧环境仍读取自己的 schema 2、
registry 1 和31动作；迁移必须用完整元数据比较，不因 tensor shape 偶然相同而放行。

### 1.3 首批稳定注册项与动态语义

以下是本轮真实候选实际用到、可供 M3 建立稳定表的条目。数字 ID 是命名空间内的
项目 ID，不是直接复用 C++ 枚举值；每个命名空间单独计算 hash。

| 命名空间 | 稳定 ID | 来源名称/别名 | 参数含义 | 当前状态 |
|---|---:|---|---|---|
| card | 1 | `Bash` | `damage`、`vulnerable_turns`；均为入口可见动态值 | ID/目标已登记，行为待测 |
| card | 2 | `Defend_R` → Defend | `block`；`target_kind=NO_TARGET` | ID/目标已登记，行为待测 |
| card | 3 | `Strike_R` → Strike | `damage`；`target_kind=ENEMY` | ID/目标已登记，行为待测 |
| card | 4 | `Anger` | `damage`；每次出牌向 discard 生成1张副本 | 真实候选观察到；生成和容量待证 |
| relic | 1 | `Burning Blood` | 无 counter；战斗胜利后治疗6的 exit hook | 默认持有已确认，formal exit 未接通 |
| relic | 2 | `NeowsBlessing` → `NEOWS_LAMENT` | `remaining_charges`；递减时点待证 | 候选有 counter；语义/出口待测 |
| relic | 3 | `StoneCalendar` | `counter`；触发阈值和时点待证 | 候选有 counter；待测 |
| potion | 0 | 空槽 `null` | `present=false`；不生成动作 | `public-b0-core` 唯一批准槽状态 |
| potion | 1 | `BloodPotion` | potency/战斗与战外 Sacred Bark 分支待证 | 只在排除场景观察到，延期 |
| potion | 2 | `Weak Potion` | `weak_amount`、`duration`、敌人目标 | 只在排除场景观察到，延期 |
| monster | 1 | `Cultist` | HP、intent、intent_damage/hits、可见 powers | 候选 ID 已登记，完整运行待测 |
| monster | 2 | `JawWorm` | HP、intent、intent_damage/hits、可见 powers | 候选 ID 已登记，完整运行待测 |
| status | 1 | Strength | `amount` | 固定字段，未扩展行为 |
| status | 2 | Vulnerable | `remaining_turns` | 固定字段，未扩展行为 |
| status | 3 | Weak | `remaining_turns` | 固定字段，未扩展行为 |
| status | 4 | Artifact | `charges` | 预登记，当前候选未出现 |
| status | 5 | Ritual | `amount`/首次跳过历史 | 预登记，需敌人状态测试 |

未列入表的卡、遗物、药水、状态、敌人或意图不能映射到 PAD 或“未知但可运行”。
它们必须保留原始名称并进入 `UNKNOWN_ENTITY_OR_SEMANTICS`、延期或排除清单。卡牌
动态值不是泛化的 `int32[4]`：字段名、是否适用、known mask 和来源必须逐项登记。

## 2. BattleScene reset 输入

### 2.1 按 entry_timing 分支校验

两种输入互斥。当前研究优先 A，B 保留为将来的完整恢复路径。以下要求优先于后文旧B表格/shape提案，不能用统一必填表强迫A伪造piles或敌人意图。

| 字段组 | A：pre_combat_initialization | B：post_combat_initialization_after_initial_draw |
|---|---|---|
| 共同来源 | source path/hash、run group、source seed/version、character、ascension、floor/act、entry_timing | 相同 |
| 玩家 | 入场HP/maxHP、gold；每项 recorded 或 derived-with-evidence | 同时点HP/maxHP/gold、block/energy/powers及动态标志 |
| 卡牌 | 完整入场多重集/升级/必要永久动态值；普通同名未升级牌不需要历史UUID | 完整战斗实例、动态值、各牌区及后端所需顺序 |
| 遗物/药水 | 完整遗物清单及适用counter、药水槽/容量；不适用counter写null+not_applicable | 完整已结算状态，恢复后不再触发开战效果 |
| 敌人 | 已注册遭遇生成器、房间种类/燃烧精英条件、原进阶 | 同时点HP、意图及move/history/misc等内部状态 |
| piles/energy/block/powers/queues | 输入中不提供，后端初始化一次并生成 | 必须按同一快照恢复；不能重新初始化 |
| already_resolved_effects | 可以为空；本候选只有标准run开局及Neow完成，不含battle初始化 | 精确列出已完成的战斗开场效果与初始抽牌 |
| environment_replay_seed | 审计候选为null；运行前按训练/评估协议分配 | 同样分配，但不能取代未知非随机内部字段 |

A的具体字段候选位于 `m2-summary-reconstruction.json` 的 `a_evidence.candidate_scene`；
来源真实性尚未核验，因此保留audit-only。A20的AscendersBane、11张牌和2槽药水不套用
B0的10张牌/3槽容量；后续需自己的registry和容量迁移，当前不批准实现。

禁止直接B→A：必须证明HP、Neow等counter以及开战增删牌/遗物效果如何回到开战前。
现有两个B候选没有该逆向证据。A重采样的RNG由独立环境seed初始化，具体各流的构造顺序
由锁定后端规定；不使用历史source seed，不暗示原局精确回放。

### 2.1-B B分支的必填顶层字段

每个场景是一个完整 JSON 对象；缺一字段即拒绝，不使用隐式默认值。

| 字段 | 类型/枚举 | 规则 |
|---|---|---|
| `scene_id` | 非空字符串 | 稳定指向精简场景索引；不得用数组下标代替 |
| `source` | 对象 | `source_id`、公开 URL、原始文件 SHA-256、run 标识、source line |
| `source_run_group` | 非空字符串 | 整局分组键；同一 run 的全部楼层共用 |
| `character` | 枚举 | 当前只允许 `IRONCLAD` |
| `source_seed` | 字符串 | 公开数据来源标识，只能进 provenance，不得直接作为环境 seed |
| `environment_replay_seed` | 无符号64位整数 | 单独产生；训练必须 ≥100000，评估必须 ∈[0,1000)；场景索引未分配前为 null |
| `ascension` | 0–20 整数 | 保留原值并分桶；A20 不得降写成 A0 |
| `game_version` | 非空字符串 | 例如 `12-18-2022`；与后端版本的机制一致性需另证 |
| `encounter` | `EncounterSpec` | 原始敌人组、锁定后端枚举（若已注册）、顺序和目标容量 |
| `entry_timing` | 枚举 | 只能是 `pre_combat_initialization` 或 `post_combat_initialization_after_initial_draw` |
| `player` | `PlayerEntry` | HP、最大HP、block、energy、可见状态 |
| `deck` | `CardInstance[]` | 入口牌组，不得使用最终 `master_deck` 替代 |
| `piles` | `PileEntry` | hand/draw/discard/exhaust/limbo；重复牌逐张保留 |
| `relics` | `RelicEntry[]` | ID、counter、counter_known、可见参数逐项保留 |
| `potions` | `PotionSlot[]` | 固定槽位顺序、容量、类型和可用/需目标属性 |
| `already_resolved_effects` | 非空枚举集 | 明确列出开战效果、初始抽牌和已结算触发，防止 reset 重复执行 |
| `capacity_manifest` | 对象 | 本场景使用的手牌/牌堆/敌人/目标/药水/遗物/状态容量与推导依据 |

`source` 还必须包含 `raw_sha256` 与 `source_line`；找不到原始公开字节时场景只能
进入不可重建清单。原始 source seed 与后续模拟器 seed 分开存储，不能以相同字符串
或相同数字自动复用。

输入校验下界也属于契约：`0 <= hp <= max_hp`、`max_hp > 0`、
`0 <= energy <= 20`、`0 <= floor <= 100`、`0 <= block`；敌人同样满足
`0 <= hp <= max_hp`、`max_hp > 0`、`0 <= block`，攻击意图必须有已记录的
`intent_damage`。这些是拒绝非法/不完整 snapshot 的边界，不是对未来游戏机制的
容量证明。

### 2.2 入口时点规则

B分支的时点是（不适用于A）：

> 战斗初始化完成，所有开战效果完成，初始手牌已经抽取，玩家尚未执行本场第一个动作。

在这个模式下：

1. `deck` 是该时点的完整牌组；`hand`、`draw`、`discard`、`exhaust`、`limbo`
   是该时点的实体分区；
2. 玩家和敌人的可见 powers、HP、block、显示意图和正数意图伤害必须来自同一
   snapshot；
3. reset 恢复 snapshot 后不得再次洗牌、抽初始手牌、触发 Neow/遗物/开战卡牌效果；
4. 若只有战斗前数据，必须明确标成 `pre_combat_initialization`，由后端执行一次
   开战序列；不能把战斗前字段和战斗后牌堆混拼；
5. 时点不明、入口前后混杂、动态遗物 counter 缺失或升级次数不可解析时拒绝；不
   通过写 `0`、删除遗物、删除状态牌或让后端重新随机来“修复”。

当前公开 JSONL 的两个候选都属于 post-init 入口；没有独立 pre-init snapshot，且
   完整 RNG counter 不在该示例中。因此它们可以作为“恢复已结算初态”的候选，但不能
   宣称从 run 开始到该战斗的逐步精确复盘。

### 2.3 类型定义

以下是 M3 应实现的语义层结构；具体 tensor 由它派生，不能反过来删字段。

```text
CardLocation    = PAD(0) | HAND(1) | DRAW(2) | DISCARD(3) | EXHAUST(4) | LIMBO(5)
TargetKind      = PAD(0) | NO_TARGET(1) | ENEMY(2) | ALL_ENEMY(3)
                 | SELF(4) | SELF_AND_ENEMY(5)
                 | HAND_CARD_SELECT(6) | PILE_CARD_SELECT(7)

CardInstance = {
  card_id:       int32,       # registry 稳定 ID；PAD 不能表示真实卡
  location:      CardLocation,
  upgraded:      bool,        # 必须与 upgrade_count > 0 一致
  upgrade_count: uint8,
  cost:          int16,
  cost_known:    bool,
  target_kind:   TargetKind,
  visible_values: {
    damage: int32,
    block: int32,
    vulnerable_turns: int32,
    copy_count: int32,
    x_cost: int32,
  },
  value_known: {damage: bool, block: bool, vulnerable_turns: bool,
                copy_count: bool, x_cost: bool},
}

RelicEntry = {
  relic_id:      int32,
  counter:       int32,
  counter_known: bool,
  active:        bool,
}

PotionSlot = {
  slot:          uint8,
  potion_id:     int32,       # 空槽使用 EMPTY=0，不能与未知类型混淆
  present:       bool,
  target_kind:   NO_TARGET(0) | ENEMY(1) | ALL_ENEMY(2),
  secondary_selection: NONE(0) | HAND_CARD(1) | PILE_CARD(2) | OTHER(3),
}

# `public-b0-core` 固定状态 registry 顺序：
# (Strength, Vulnerable, Weak, Artifact, Ritual)。
StatusVector = {
  amount:        int32[5],
  amount_known:  bool[5],
  duration:      int32[5],
  duration_known: bool[5],
}

PlayerEntry = {
  hp: int32, max_hp: int32, block: int32, energy: int32, turn: int32,
  statuses: StatusVector,
}

EnemyEntry = {
  monster_id: int32,
  hp: int32, max_hp: int32, block: int32,
  statuses: StatusVector,
  intent: NONE(0) | ATTACK(1) | ATTACK_DEFEND(2) | DEFEND_BUFF(3) | BUFF(4) | DEBUFF(5),
  intent_damage: int32,
  intent_hits: int32,
  targetable: bool,
}
```

`StatusVector` 的五个位置必须覆盖 `public-b0-core` 已预登记的
Strength/Vulnerable/Weak/Artifact/Ritual；每个位置的 amount/duration 含义固定，
没有“任意 status_id 数组”可以绕过注册。Dexterity、Poison、Thorns、Metallicize、
NoDraw、临时 Strength 等后续状态需要新的 status registry/字段审计和 schema 迁移，
不能借本批五个位置默认为0。没有实际影响的静态卡牌数值可来自固定 registry，但
动态值、升级次数和 `cost_for_turn` 不能遗漏。

## 3. 观测字段与信息边界

### 3.1 模型可见观测

公开 scene 中的 source 标识、source seed、RNG、隐藏牌序和真实历史动作不进入模型。
模型观测仍由四个语义列表和一个全局对象组成：

- **手牌**：按真实抽牌顺序分配槽位；槽位号只用于动作索引，不写入卡牌语义特征。
- **非手牌**：draw/discard/exhaust/limbo 按公开语义排序为无序多重集；隐藏顺序
  可以供后端复现研究，但不得进入模型。
- **敌人**：固定 `enemy_observation_capacity` 行，保留 `monster_id`、HP、最大HP、
  block、可见状态、意图类别、意图伤害/hits、targetable；不放内部 move ID 或未来
  招式/RNG。
- **全局**：HP、最大HP、block、energy、turn、`turn_budget_remaining`、四区数量、
  total enemy HP，以及 `StatusVector` 的五个固定位置。字段顺序由 `field_order_hash`
  锁定；预算字段只用于任务硬上限，不等同于游戏失败标签。
- **遗物**：只编码已批准的稳定 ID 和本 registry 明确规定的 counter。`Burning Blood`
  没有 counter；`NeowsBlessing` 的 counter 是来源 charge；`StoneCalendar` 的
  counter 语义尚待行为核验。未知或缺失动态参数时整个场景拒绝，不把缺失变成0。
- **药水**：槽位顺序、稳定 potion ID、目标类型和二次选择类型。`public-b0-core`
  只有 `EMPTY=0`，因此没有可用药水 action；非空 potion 必须在独立 potion registry
  给出 potency/target/生成/选择参数后才能开放，不能只添加观测字段。

当前公开审计的详细场景中，牌堆顺序虽被日志导出，但玩家模型只消费规范化无序
实体；这同时满足复现和 D19 信息边界。

### 3.2 当前批次新增信息

| 新信息 | 来源证据 | M2 处理 |
|---|---|---|
| 入口牌组与重复牌 | JSONL `state:floor.deck` | 逐实例保存；最终 `.run master_deck` 不可替代 |
| 升级次数 | 部分字符串后缀 | `+n` 可解析；`Name+` 无次数即排除 |
| 入口遗物及 counter | JSONL `state:floor.relics` | 计数直接保留；动态遗物缺计数即排除 |
| 药水槽位 | JSONL `state:floor.potions` | B直接保留槽位；A可由已证标准开局+Neow规则推导，来源兼容另审 |
| 战斗玩家/敌人状态 | JSONL `combat_state` | HP、能量、意图、powers 等同一 snapshot 审计 |
| 进阶和版本 | `state:run`/`.run` | 原值记录并分桶，不降级 |
| 开战已结算标志 | 入口锚点 | reset 禁止二次触发；pre-init 不足时排除 |

## 4. 动作契约：五目标与药水

### 4.1 `action_schema=2` 的完整编号

新公开战斗动作空间预登记为 `ACTION_COUNT=66`：

```text
0..49    = CARD(slot, target)       = slot * 5 + target
50       = END_TURN
51..65   = POTION(potion_slot, target) = 51 + potion_slot * 5 + target
```

其中 `slot=0..9`，`potion_slot=0..2`，`target=0..4`。规则如下：

- `target=0` 对 `NO_TARGET` 卡表示“无目标”，对 `ENEMY` 卡表示敌人行0；两者
  的 `TargetKind`/mask 语义不同，不能合并；
- `ENEMY` 卡或需敌人目标的药水只能寻址 `[0,4]` 中存在且 targetable 的敌人；
  不存在的行 mask 为 false，不能重排目标来躲容量错误；
- `ALL_ENEMY`、`SELF`、`SELF_AND_ENEMY` 只有在正版/锁定后端调用链逐项核验后才
  开放；不需要选择的全体效果仍使用 target=0 并由语义区分；
- `END_TURN=50` 的 mask 规则沿用真实战斗阶段；终局后整条 mask 为 false；
- 药水 action 只有槽位存在且 `secondary_selection=NONE` 时才可能为 true。需敌人
  目标的药水使用上述五个 target；无目标药水只允许 target=0；
- 药水或卡牌若要求选一张手牌、牌堆牌、生成卡或任意数量对象，当前 66 位动作
  没有完整语法，全部延期，mask 为 false。不能让后端自动选第一张或随机代选。

66 只是新协议的编号预留，不代表本轮所有药水已经批准。`public-b0-core` 的药水
registry 只有 `EMPTY=0`，因此15个 POTION 编号全部为 false；`BloodPotion`、
`Weak Potion` 以及 `Potion Belt`/A11 造成的容量变化必须整体排除或另建配置。若
真实场景含一个当前不支持的药水、卡牌选择、生成卡或容量，整个场景不进入该批，
不能仅将那一项 mask 掉后继续称作匹配。

### 4.2 二次选择的延期条件

以下内容没有被本契约静默纳入：True Grit 升级版、Armaments、Burning Pact、
Headbutt、Dual Wield、Exhume、Liquid Memories，以及需要选择牌的药水。批准它们
之前必须登记新的选择 token/动作序列、状态机、mask、轨迹和 checkpoint 迁移；只
增大 `ACTION_COUNT` 或让后端代选不算完整语法。

## 5. 容量契约与可证明首批

容量以每一批 `capacity_manifest` 声明；超容量立即返回结构化错误，不截断、不丢实体、
不把目标重编号为可用范围。

### 5.1 `public-b0-core` 的实际证明

本批只接入真实索引中的以下一条公开场景：

```text
scene_id: runlogger-example-ironclad-1706139943:1VKGN2DPUYVCJ:floor-1:line-11
character: IRONCLAD
ascension: 0
encounter: Cultist
deck: Strike_R×5, Defend_R×4, Bash×1
relics: Burning Blood, NeowsBlessing(counter=2)
potions: 3 empty slots
```

该场景入口有5张手牌、5张抽牌、总牌数10，且本批卡牌/遗物没有已批准的牌量生成、
分裂或召唤路径。故可证明：

| 容量项 | `public-b0-core` 值 | 证明/拒绝规则 |
|---|---:|---|
| `hand_capacity` | 10 | 当前后端上限；入口和本批路径均不得出现第11张 |
| `enemy_observation_capacity` | 5 | 物理观测行；本批实际最大敌人数1 |
| `target_capacity` | 5 | 新动作语法；本批实际最大可寻址目标1，行1–4 mask=false |
| `pile_capacity` | 10 | 初始总牌数10；只移动区域，不生成牌，四区合计≤10 |
| `relic_capacity` | 2 | 本批唯一场景实际有2件遗物；超过则拒绝而非丢遗物 |
| `potion_capacity` | 3 | 真实 JSONL 槽位数组长度为3；超过/缺失拒绝 |
| `status_feature_width` | 5 | 固定为 Strength/Vulnerable/Weak/Artifact/Ritual；新状态需新 registry/schema |
| `action_count` | 66 | 50卡动作+结束回合+15药水动作 |

`limbo` 不单独增加 shape：它属于唯一的 `pile_capacity` 合计，且第一决策点出现
非空 limbo 即拒绝，因为说明控制队列尚未清空。这个证明只适用于
`public-b0-core`。它不能外推到包含 Anger、Power Through、Wound/Dazed、复制、
分裂、召唤、改变手牌上限或非空药水动作的场景。

### 5.2 生成、分裂、召唤和外部截断

- `Anger` 会增加弃牌堆实体；公开 floor 3 候选因此单列为 `public-b0-jaw`，在
  生成次数和 `pile_capacity` 证明、行为测试完成前不批准。不能把它当作无生成的
  11张牌场景。
- `Power Through`、Wild Strike、Reckless Charge、Immolate 等状态牌生成路径需
  把生成类别、每次生成数量、最多触发次数和四区总量一起证明；只写一个更大的数组
  不构成证明。
- 分裂/召唤须给出初始及动态最大敌人行和最大可寻址目标。当前 31动作只支持三
  目标，66动作才预留五目标；Gremlin Gang、Lots of Slimes 和任何超过5目标的
  场景在新 action/schema 完成前延期。
- 本契约不新增“为容量方便的外部截断”。任务版本明确为
  `task_spec_id=public-battle-v1`、`termination_rule_version=battle-hard-limit-v1`、
  `max_turns=50`；`turn_budget_remaining=max(0, 50-turn+1)` 必须进入全局观测，
  定义为“包含当前玩家决策回合在内的剩余回合数”。第50回合最后
  一个真实动作先结算胜负；仍未结束才返回
  `terminated=true,truncated=false,termination_reason=task_hard_limit,reward=0`，
  不自举。若数据采集器在50回合前主动停止，必须返回
  `terminated=false,truncated=true,termination_reason=external_limit`，保留 reset
  前最终观测并按 v6 规则自举，不能改写为任务失败。

### 5.3 R5 预审依赖：战后出口和疑似机制差异

本节整合三个预审报告的实际依赖；它们不是本轮已确认的行为缺陷，也不修改
`battle_reward_v1`。

| 依赖 | 当前静态事实 | 对本契约的处理 | 主审/后续测试 |
|---|---|---|---|
| `Burning Blood` | `GameContext(Ironclad)` 默认持有 `BURNING_BLOOD(data=0)`；其胜利治疗6位于 `BattleContext::updateRelicsOnExit` | post-init 场景必须记录 relic；M3 若接入正式战斗出口，必须明确 exit hook 与 reward/observation 同一时点 | 先验证 `exitBattle` 是否纳入 formal adapter；不回填旧 reward |
| `BattleContext::exitBattle` | 当前 adapter `step` 未调用它；上游出口还同步药水、RNG、HP、gold、遗物计数和 `afterBattle` | reset/scene 契约把“出口同步已执行”作为独立状态，不把 source snapshot 的可见 HP 写成 h_exit | 对同一胜利轨迹比较出口前/后 HP、reward、遗物计数；该测试当前接口不能运行 |
| `NeowsLament` | 后端实际 ID 为 `NEOWS_LAMENT`；counter 在 exit 递减，开战可能把敌人 HP 设为1 | source alias `NeowsBlessing` 必须映射并保留 charges；counter 递减点未核验时场景 pending/拒绝 | 连续三/四场、开战一次性效果和 exit 回写测试 |
| Pen Nib | 预审发现正版阈值10与当前 C++ `counter==9` 触发的疑点 | 不在 M2 改代码或判定缺陷；契约要求 counter 语义和计数基准进入 registry | 8/9/10次攻击、多段攻击、队列执行顺序；需要正式可注入 API |
| Sacred Bark/Blood Potion | 预审报告指出战斗与战外 Blood Potion 分支方向疑似不一致 | `BloodPotion` 保持 observed-deferred；不通过 contract 更改数值 | 有/无 Bark 的战斗与战外矩阵，结果待证 |
| Red Slaver/miscInfo | 预审列为意图、`miscInfo` 和 usedEntangle 依赖 | 未注册 Red Slaver 的完整 intent/misc 时整体不批准 | 首次 Entangle、Scrape、后续行动和 misc 状态测试 |

`h_exit` 的定义继续服从 v6 §4.4.2：最后动作、连锁效果和已实现的战斗结束效果
全部结算后的 HP。当前 M2 只登记这个待核对点；没有调用 `exitBattle`、没有修改
reward，也没有把“理论上的治疗6”写入现有候选场景。

## 6. 分批支持矩阵

“真实候选数”是审计结果，不是静态候选池数量；0 表示本轮没有合格场景，不能用
人工牌组补数。

| 批次 | 真实候选/观察数 | 卡牌/升级 | 遗物/药水 | 难度/遭遇 | 状态 | M3/M4 依赖与测试 |
|---|---:|---|---|---|---|---|
| `public-b0-core` | 1 个可见入口字段已核验、内部状态未证明场景 | Strike、Defend、Bash，均基础版 | Burning Blood、NeowsBlessing；3空槽 | A0、Cultist | 可作为未来注入 smoke；仍需内部状态和 mod review | reset 注入、counter、post-init 不重复、66 mask、容量拒绝、旧 minimal 回归 |
| `public-b0-jaw` | 1 个可见入口字段已核验、内部状态未证明场景 | 上述+Anger 基础版 | Burning Blood、NeowsBlessing(counter=1)、StoneCalendar(counter=1) | A0、Jaw Worm | 后端待支持；Anger 生成容量未证明，暂不批准 | Anger 生成上界、牌堆容量、逐步实体回归、场景复跑 |
| `public-b1-potion` | 3 个非空药水 snapshot，但均在排除场景 | `BloodPotion`、`Weak Potion` 出现；完整效果未核验 | 槽位可见；无合格非空药水候选 | A0、不同 Act 1 遭遇 | 不纳入当前批 | potion registry、target mask、药水参数、三槽上界、无二次选择测试 |
| `public-b1-upgrade` | 4 个场景出现升级歧义 | `Uppercut+`/`Feel No Pain+` 无次数 | — | — | 排除 | 需要来源输出 upgrade count 或明确只支持 bool 的新契约；不猜 `+1` |
| `public-b1-relic-counter` | 5 个场景缺动态计数 | — | `NeowsBlessing` counter 缺失 | — | 排除 | 逐遗物 counter/active 参数、开战触发时点和重复触发测试 |
| `m3-card-target` | 0 个已批准；M1目标仍30–40类 | M1的35类实施候选按机制批次执行 | 依真实场景 | 保留原进阶 | 目标未缩水 | registry、C++导出、wrapper、动态值、扩展卡行为回归 |
| `m4-encounter-target` | 0 个已实现 | 不改变卡牌白名单 | 目标约10种普通+Gremlin Nob/Lagavulin/Three Sentries | 目标保留，未开放 | 分裂/召唤上界、五目标动作、意图映射、每遭遇回归 |

真实详细run只有1个且A0；summary全部A20，其中1个首场可按标准规则构造A，
来源兼容尚未认证。不能将其降为A0，也不能称难度覆盖已完成。A0/A20 必须在场景清单和评估统计中
分桶报告。

## 7. 迁移联动清单

M3 修改前必须把下面清单作为一个原子迁移登记；本 M2 不提前修改这些实现。

| 层 | 联动位置 | 必须同步 |
|---|---|---|
| C++ reset/状态 | `third_party/sts_lightspeed/bindings/slaythespire.h`、`bindings/slaythespire.cpp`、`bindings/bindings-util.cpp` | `BattleScene` 解析、状态注入、entry timing、牌/遗物/药水 registry、五目标 mask、66动作、超容量异常 |
| Python 薄包装 | `sts/env/lightspeed.py` | reset 签名、Encounter/目标/药水枚举、原始字段校验、schema/hash 元数据；旧 minimal 路径不改标 |
| Registry | `sts/env/registry.py` | 稳定 card/relic/potion/status/monster ID、排序和 registry hash；未知 ID 拒绝 |
| 规范观测 | `sts/env/lightspeed.py` 与共享契约源 | 新字段顺序、known mask、动态值、公开/隐藏边界、shape 派生 |
| 双 wrapper | `sts/env/wrappers.py` | 由同一规范 dict 派生；card/relic/potion/status 容量一致；超容量不截断 |
| 模型 | `sts/models/mlp.py` 及后续 Set encoder | 新输入维度、66 policy head、输入/registry/action hash；旧权重拒绝加载 |
| Agent/runner | `sts/agents/masked_policy.py`、`episode_runner.py`、规则 Agent | card/potion/end-turn 解码、目标语义、二次选择延期、mask 一致性 |
| PPO/轨迹 | `sts/train/ppo.py`、`sts/train/recording.py` | scene/task/reward/termination 元数据、原始观测/mask、66动作；不把玩家历史动作当 on-policy |
| checkpoint | 现有 checkpoint 保存/加载校验 | `contract_id`、schema、registry/action/field/capacity hash、reward/task 版本；不兼容明确拒绝 |
| 评估 | M6 才实现 | 整局 group split、source seed 与环境 seed 分离、A0/A20分桶；`eval_seeds.json` 不变 |

输入 shape 必须从以下顺序派生：

```text
pile_capacity = draw_capacity + discard_capacity + exhaust_capacity + limbo_capacity
card_capacity = hand_capacity + pile_capacity
card_entity_width = 固定 CardInstance 语义字段宽度
enemy_shape = enemy_observation_capacity × EnemyEntry 语义宽度
potion_shape = potion_capacity × PotionSlot 语义宽度
relic_shape = relic_capacity × RelicEntry 语义宽度
global_shape = 固定 GlobalEntry 字段顺序（含 turn_budget_remaining）
action_count = hand_capacity × target_capacity + 1 + potion_capacity × target_capacity
```

这里的 `limbo` 若不进入模型，也必须进入 reset/容量/序列化检查；不能通过不编码
来丢掉实体。任何 shape、动作数或字段顺序改变都产生新 hash 和新 checkpoint 兼容
分支。

## 8. 数据划分与种子契约

### 8.1 组划分

固定规则版本为 `public-run-group-sha256-v1`：

1. 首先以 `source_run_group` 合并同一整局的全部战斗楼层、重复记录和相同 source
   seed；同源变体不能拆开；
2. 对唯一 group key 的 SHA-256 前8位转整数后 mod 100：0–79=`train`，80–89=`dev`，
   90–99=`reserved-eval`；
3. 先划整局，再由组内生成战斗 scene；不按胜负挑选，不把路径等距选择称作随机；
4. 本轮样本过小，所有实际 scene 的 `split` 仍是 `audit-only`，没有正式训练/评估
   划分；`eval_seeds.json` 不变；
5. 工具在重复 group key 出现在待划分列表时直接报错，并在索引记录
   `cross_split_leakage=false` 只有在实际检查后才能填写。

### 8.2 训练与评估 seed

- `source_seed`：公开记录的来源标识，永远不进入模型，也不直接驱动本地环境；
- `environment_replay_seed`：模拟器独立复跑 seed，训练使用 `>=100000`，评估使用
  `[0,1000)`，来源于已登记的场景 split/seed manifest；
- 复跑同一 scene 的 seed 必须记录在 episode/checkpoint 元数据，不能把 scene_id、
  source seed 或配置编号隐式充当 seed；
- 评估 seeds 的文件提交后不可变。新场景评估若需额外 manifest，必须新建版本，
  不覆盖既有评估含义。

## 9. 校验失败协议与验收

reset 必须返回带 `code`、`path`、`expected`、`actual`、`source_ref` 的结构化
`ScenarioValidationError`。至少包括：

```text
MISSING_FIELD
UNKNOWN_CARD_OR_RELIC_OR_POTION_OR_STATUS
VERSION_MISMATCH
FIELD_ORDER_HASH_MISMATCH
ENTRY_TIMING_UNSUPPORTED
EFFECT_ALREADY_RESOLVED_OR_WOULD_REPEAT
UPGRADE_OR_TRANSFORM_AMBIGUOUS
DYNAMIC_RELIC_COUNTER_UNKNOWN
POTION_INVENTORY_UNKNOWN
OVER_HAND_CAPACITY
OVER_PILE_CAPACITY
OVER_RELIC_OR_POTION_CAPACITY
ENEMY_TARGET_CAPACITY_EXCEEDED
SECONDARY_SELECTION_UNSUPPORTED
SOURCE_SEED_REUSED_AS_ENVIRONMENT_SEED
SEED_RANGE_INVALID
RUN_GROUP_SPLIT_LEAKAGE
```

禁止行为：补默认值、裁剪、未知 ID 映射 PAD、把缺失药水当空槽、把历史动作直接
送入 PPO、把失败解析伪造为0回报、把外部截断标为游戏失败、让后端自动替选对象。

M3 最低测试顺序：

1. 先用本轮真实 `public-b0-core` 场景验证成功解析；再验证未知卡、缺药水、缺
   counter、升级歧义、非 `select_map` 入口和版本不兼容均拒绝；
2. 用合成夹具验证重复记录合并、同源 group 泄漏、超手牌/牌堆/目标/药水容量和
   二次选择拒绝；合成夹具只能证明失败路径，不能替代真实场景成功证据；
3. 用已锁定 minimal-v1 的完整回归确认旧路径和旧 checkpoint 没有被新 schema 污染；
4. 只有 C++/wrapper/model/runner 联动实现并通过真实场景恢复、mask、容量和双
   wrapper 同源测试后，才可按 M3/M4 另行登记训练；本契约不启动 PPO。

## 10. 当前交付边界

已交付：公开数据来源固定、原始字节哈希、7个详细入口场景的机器清单、2个真实
可见入口字段已核验但内部状态未证明的场景、5个详细排除场景、summary 的 A/B 双路径
审计、reset/观测/动作/容量/迁移/划分契约和数据审计测试。

未交付：正式 registry、C++ 状态注入、66动作实现、药水/遗物行为实现、30–40类卡
行为验收、约10种普通遭遇和3种精英实现、正式训练/评估分布、M3–M5 代码或 PPO。

第二轮主审后仍停留M2。原生A已有1个标准规则下可构造候选，但来源规则兼容、正式内容/容量与分组未完成；任何未交付项不能由契约文字代替。
