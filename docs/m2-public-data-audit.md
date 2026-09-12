# M2 公开战斗初态数据审计

日期：2026-09-11。状态：第二轮主审直接修复完成，M2仍有明确缺口，暂不通过。本文只报告公开数据
可获取性、字段证据和初态重建边界，不批准正式训练分布，不修改正式环境，不启动
PPO，也不进入 M3。

2026-09-12更新：本文件保留12份小样本和JSONL审计过程；最新全库扩样结果见
`docs/m2-corpus-report.md`、`docs/m2-corpus-index.json`。全库已清点157个独立Ironclad run，
第一幕有257个规则可构造但来源未正式认证的候选，不再以单场可行性作为数据阶段目标。

## 1. 结论先行

本轮得到一条可供后续实现的真实公开详细 run：`colinking/runlogger` 的历史
Serialization Mod JSONL 示例。该 run 的 7 个战斗楼层都有战斗入口快照；其中
floor 1 的 Cultist 和 floor 3 的 Jaw Worm 通过结构、数值、牌区和已登记实体检查，
但只能标为 `visible_entry_verified_internal_state_unproven`。它们仍不能直接运行于
当前后端，因为当前 `reset` 没有牌组/遗物/药水/任意战斗状态注入接口，且来源 run
含未独立核实的 `superfastmode` mod。

本轮没有得到足以宣称“公开总体分布”的详细日志集合：

- `MaT1g3R/Slay-the-Spire-data` 的12个独立 `.run` 样本经A规则审计，1个首场在标准规则下可构造、来源兼容未认证；
  其余11个仍有具体规则缺口。它们均未正式准入，但不再统一断言无法构造。
- Archive 的 `SlayTheData.7z` 元数据声明约29 GiB、超过7700万局，但本轮不默认
  下载整库，也没有获得可随机读取的成员文件；不能把其规模或描述当作字段已核验。
- 详细 JSONL 只有1个独立 run，而且没有 `state:game_over`；7个场景证明字段抽取
  可行，不证明版本覆盖、玩家群体分布或训练/评估代表性。

因此本轮的准确状态是：

| 项目 | 状态 |
|---|---|
| 可见入口字段已核验、内部状态未证明 | 2 个，`visible_entry_verified_internal_state_unproven` |
| 当前正式后端可直接 reset | 0 个；缺少状态注入，留给 M3 |
| 内部状态可继续运行已证明 | 0 个 |
| 详细日志中被排除的战斗入口 | 5 个 |
| `.run` summary 未正式准入 | 12 个；其中1个规则可构造、来源未认证，11个规则缺口 |
| 是否构成正式训练白名单 | 否 |
| 是否进入 PPO on-policy trajectory | 否 |
| 是否改变 `eval_seeds.json` | 否 |

## 2. 来源、固定版本与许可边界

### 2.1 `MaT1g3R/Slay-the-Spire-data`

- 仓库：[MaT1g3R/Slay-the-Spire-data](https://github.com/MaT1g3R/Slay-the-Spire-data)
- 固定提交：`097aaf3564c2247835162d267cbc7c55d2c9039e`
- 固定提交树中发现的 Ironclad `.run` 文件：157 个
- 本轮样本：12 个，来自 `200-rotating-sample`、`chegs`、
  `lose-all-gold-max-hp-sample`、`panacea-ironclad-sample` 四个数据集各3个
- 独立 run：12 个；全部 `ascension_level=20`
- `build_version`：`2022-03-07` 6 个、`2022-12-18` 6 个
- `victory`：8 个 true、4 个 false；选择规则没有读取或按该字段筛选
- `damage_taken.enemies` 中出现的去重 encounter label：60 个；这是逐层汇总里的
  字符串，不是已经还原的敌人状态
- 仓库声明许可为 Apache-2.0；正式复核仍以固定提交的 `LICENSE` 为准

样本采用“数据集分层、路径字典序轮询”的确定性选择，不是随机抽样，也不是代表性
抽样。完整路径、原始 URL、字节数和 SHA-256 见
`reference/public-run-audit/source-manifest.json`；提交的摘要索引见
`docs/m2-evidence-index.json`。

### 2.2 `colinking/runlogger` 历史详细示例

- 仓库：[colinking/runlogger](https://github.com/colinking/runlogger)
- 固定提交：`02679f51c19c7a8d26da618ec0377faa390f347f`
- 固定示例：`runs/ironclad_1706139943.json`
- [原始 JSONL](https://raw.githubusercontent.com/colinking/runlogger/02679f51c19c7a8d26da618ec0377faa390f347f/runs/ironclad_1706139943.json)
- 文件大小：99,588 bytes；SHA-256：
  `e7e6178e1d4566f1e827c6c917471a7bec736b26d6beb53488bf97e1f3c8cb82`
- 记录数：231；逐行 `_type` 格式；战斗入口楼层：1、3、5、7、12、14、16
- run 元数据：Ironclad、`ascension=0`、`sts=12-18-2022`、source seed
  `1VKGN2DPUYVCJ`
- 日志没有 `state:game_over`，所以它不是完整 run 结束证据
- 固定提交 README 将其称为 Serialization Mod beta；仓库固定提交含 MIT 许可文件，
  但该历史示例的 mod 组合仍需主审确认是否属于可用的非游戏性日志环境

示例 run 记录的 `mods` 包括 `CommunicationMod`、`SerializationMod`、`basemod`
和 `superfastmode`。前三者按名称属于日志/通信框架；`superfastmode` 未在本轮证明
不改变游戏性，所以场景保留 `mod_review_required=true`，不能直接作为正式分布。

### 2.3 Archive 大库

- 项目页：[Slay the Data. 7z](https://archive.org/details/slay-the-data.-7z)
- 元数据端点：[Archive metadata](https://archive.org/metadata/slay-the-data.-7z)
- 本轮优先复用本地元数据，当前原始元数据 SHA-256：
  `cf338fd7e3d9cf8f820aab9f8a7f0ee9f9f85b333f2af665d1046461329b4691`
- `SlayTheData.7z`：29,074,129,887 bytes，MD5
  `54fcd51200ee3f7e43976d9a9726eb9f`
- 元数据的 `licenseurl` 为 null；许可状态未查明
- 未下载压缩包，没有把“超过7700万局”的描述升级为已核验样本统计

## 3. 统一入口时点与字段审计

### 3.1 入口时点

M2 的候选规范时点固定为：

> 战斗已初始化，开战效果已结算，初始手牌已抽取，玩家即将执行本场第一个动作。

在 JSONL 中用“某楼层第一次出现 `state:floor.combat_state`，且紧邻前一条记录为
`action:select_map`”定位。这个锚点把战斗前状态和战斗内第一次出牌后的状态区分开。
若将来只拿到战斗前 snapshot，必须使用另一个显式入口模式；不能把两个时点混在
同一个 reset 输入中。

当前详细示例只提供入口后的 snapshot，没有独立的战斗前 snapshot。因此它不能证明
开战前到开战后的每个触发过程，但可以作为“注入已结算状态”的候选。M3 reset
必须禁止再次执行已包含在 snapshot 中的开战遗物、开战效果和初始抽牌。

### 3.2 字段证据矩阵

| 字段 | `.run` summary | JSONL 入口 snapshot | 结论 |
|---|---|---|---|
| source run 标识/seed | 有 `play_id`、`seed_played` | 有字符串 seed | 只作来源分组，不直接用作模拟器 seed |
| Ironclad/进阶/版本 | 有 | 有 | 记录原值；两种来源版本不能擅自合并 |
| 当前入口牌组 | 只有最终 `master_deck` | `state:floor.deck` 直接记录 | JSONL 可取入口 deck；`.run` 已尝试 A 但不形成正式场景 |
| 重复牌与入口升级 | 最终字符串可能有升级 | 入口字符串可解析部分 `+n` | 只保留重复实例和源序号；无 UUID |
| 添加/移除/变形/升级历史 | 只有不完整的 summary 事件 | 连续 floor snapshot 可做保守 diff | 历史因果为 partial，不用来宣称全 run 精确重建 |
| 当前/最大 HP | 逐层数组，时点依赖字段语义 | 入口 `hp_current`/`hp_max` | JSONL 为直接入口记录；summary 已读取但无法证明 A 时点 |
| 遭遇和敌人数量 | `damage_taken.enemies` 字符串 | 敌人 `id`、HP、意图、部分伤害/状态 | JSONL 可按敌人 ID 建候选；未注册组仍排除 |
| 遗物 ID | 最终列表 | 入口列表，部分带 `counter` | 缺失动态计数不能当0 |
| 遗物触发状态 | 无入口时点 | counter/powers 部分可见 | 省略 counter 的动态遗物场景排除 |
| 药水槽位 | 只有获取/使用历史字段 | 入口 `potions` 数组直接记录 | JSONL 可取容量和槽位；summary 只能列出获取/使用线索 |
| 玩家活动状态 | 无战斗 snapshot | `player.powers`、block、energy 部分记录 | 缺失 hidden state 不能补默认值 |
| 敌人可见意图 | 无 | `intent`、正数伤害和 hits 部分记录 | 意图可审计；未出现的字段按序列化规则标记 |
| 隐藏牌序/RNG | 无 | draw pile 顺序被日志记录，但完整 RNG counter 不在示例入口 | 可保存供后端恢复研究；模型不得读取；未来状态重新采样 |
| 真实玩家动作 | 无逐步动作 | 有 action 记录 | 不作为 PPO on-policy 数据，只作为日志/动作语法证据 |

JSONL 序列化器的固定提交源码明确了条件字段：非空时才写出四区牌堆，玩家 block
仅在大于0时写出，敌人 `damage` 仅在大于0时写出，遗物 counter 仅在大于-1时
写出。见固定提交的
[`GameStateConverter.java`](https://github.com/colinking/runlogger/blob/02679f51c19c7a8d26da618ec0377faa390f347f/src/main/java/serializationmod/GameStateConverter.java)，
约第591–631、695–803行。审计工具同时保留 `*_recorded` 标志；不把序列化器省略
字段写成原始数据直接记录了0。

### 3.3 真实逐字段案例

#### 案例 A：floor 1，Cultist，保留为候选

- 原始记录：JSONL 第11行，`state:floor`，紧邻前一条为 `action:select_map`
- `room_type=MonsterRoom`，`Cultist`，敌人 HP `1/48`，意图 `BUFF`
- 入口牌组10张：手牌5张、抽牌堆5张；重复 Strike/Defend 仍逐张保留
- 玩家 HP `80/80`、energy=3；入口药水为三个空槽
- 遗物：`Burning Blood`；`NeowsBlessing` 的 counter=2 被直接记录
- 状态：结构和可见入口字段已核验；`NeowsBlessing`、控制队列和当前牌组/敌人注入尚未被锁定后端支持
- 状态：`visible_entry_verified_internal_state_unproven`

#### 案例 B：floor 3，Jaw Worm，保留为候选

- 原始记录：JSONL 第25行，紧邻前一条为 `action:select_map`
- `room_type=MonsterRoom`，`JawWorm`，敌人 HP `1/41`，意图 `ATTACK`，damage=11
- 入口牌组11张；手牌5张、抽牌堆6张
- 玩家 HP `80/80`、energy=3；三个药水槽为空
- 遗物 `NeowsBlessing` counter=1、`StoneCalendar` counter=1 均有记录
- 状态：结构和可见入口字段已核验；Anger 生成、`StoneCalendar` 语义和内部状态尚未构建证明
- 状态：`visible_entry_verified_internal_state_unproven`

#### 案例 C：floor 5/7/12/14/16，排除而不修补

- floor 5 起 `NeowsBlessing` 仍出现在遗物列表，但不再带 counter。由于固定提交
  序列化器省略 `counter=-1`，仅凭 JSON 无法判断其动态效果是否已归零；5个场景
  统一标记 `DYNAMIC_RELIC_COUNTER_MISSING`。
- floor 7、12、14、16 的牌堆/手牌出现 `Uppercut+` 或 `Feel No Pain+`。固定
  示例的 `getCardName` 没有把 `timesUpgraded` 写入名称，不能推断升级次数；这些
  场景再加 `UPGRADE_FORMAT_AMBIGUOUS`。
- 工具保留 `raw_values_on_parse_failure`，所以排除不会静默删除这些牌。

## 4. R1–R5 修复证据

| 编号 | 实际修复 | 真实/反例证据 | 状态 |
|---|---|---|---|
| R1 | 严格有限整数、HP关系、能量/楼层/实体容量、牌区多重集、登记实体和分层状态 | 本地 JSONL 的 `HP=-50` → `INVALID_FINITE_INTEGER_OR_RANGE`；删除首层5张抽牌 → `PILE_MISSING_DECK_CARDS` + `FIRST_BATTLE_BASE_DECK_MISMATCH`；未知遗物 → `UNKNOWN_ENTITY_OR_SEMANTICS` | 已修复并测试 |
| R2 | 第二轮改为条件式A规则审计；B缺字段不用于否定A | 1个 `rule_constructible_source_unverified`、11个 `partial_reconstruction_attempt`；来源门槛独立 | 定点修复完成；尚无正式场景 |
| R3 | 两个候选新增内部状态审计、控制队列/卡实例/敌人历史/遗物位/药水容量/RNG 缺口和明确 A 重采样策略 | 两个候选 `internal_state_status=unproven`、`constructible=false`、`exact_historical_replay=false`；不把隐藏状态补0 | 已修复；内部构建未证明 |
| R4 | 首批 registry 明确列出 card/relic/potion/monster/status；B0 relic max改为2；limbo合并唯一 pile capacity；去掉无证明 status_capacity；66动作限定3槽无二次选择子集；区分50回合任务终止与外部截断 | 契约 `public-b0-core` 实际遗物2、状态固定5字段；Potion Belt/非空药水/选择动作整体延期；容量/版本字段写入契约 | 已修复为契约；未实现 |
| R5 | 将 Burning Blood 默认持有、`exitBattle` 未接入、h_exit、Pen Nib、Sacred Bark/Blood Potion、Red Slaver miscInfo列为独立依赖 | 契约新增 R5 表；没有修改 reward、正式 adapter 或并行预审报告 | 已整合；待主审裁定 |

本轮专测共 `23 passed`；完整测试结果和未运行项见第5.1节。测试中的合成夹具只证明
失败路径，真实成功路径来自本地 JSONL；没有用合成数据替代真实候选。

## 5. 可复现数据产物

原始数据只放在 gitignored 的 `reference/public-run-audit/`：

| 文件 | 内容 | SHA/说明 |
|---|---|---|
| `audit.json` | 完整审计、统计、场景、排除和限制 | 由固定来源重新生成 |
| `source-manifest.json` | 固定提交、URL、本地路径、字节数、SHA-256 | 逐文件哈希 |
| `runlogger/ironclad_1706139943.jsonl` | 公开详细 JSONL | `e7e617...c8cb82` |
| `matiger/sample-000.run`–`sample-011.run` | 12个 summary 原样文件 | 详见 manifest |
| `archive/slay-the-data.-7z.metadata.json` | Archive 元数据，不是大库本体 | `cf338f...2b4691` |
| `scene-candidates.json` | 原始根目录下的完整场景索引 | 与提交索引内容对应 |
| `exclusions.json` | summary/场景排除理由与哈希 | 与提交索引内容对应 |

本轮修复后，提交的精简索引：

- `docs/m2-evidence-index.json`：产物路径、来源文件哈希、场景数、分组检查
- `docs/m2-scene-candidates.json`：7个详细入口场景，含真实字段与状态
- `docs/m2-exclusions.json`：12个 summary 排除 + 5个详细场景排除
- `docs/m2-summary-reconstruction.json`：12个 summary 的入口 A/B 尝试结果和逐局缺口

## 5.1 复现命令

在仓库根目录执行。默认在线模式仍可复取固定提交；本轮实际验收优先使用已有
raw 的离线模式：

```powershell
python -X utf8 scripts/audit-public-runs.py --offline --commit 097aaf3564c2247835162d267cbc7c55d2c9039e --limit 12
pytest -q tests/test_public_run_audit.py
python -X utf8 scripts/check-spec-v6.py
git diff --check
pytest -q
```

R1–R5上一轮实际结果：离线审计命令成功复用本地 raw/index；审计专测 `23 passed`；规范检查
`PASS`；`git diff --check` 退出码0（仅有 Windows 行尾提示）；完整 pytest 为
`301 passed`（无失败/跳过）。未运行：PPO 训练、正式评估、扩展环境实现和 M3–M5；
没有修改 `eval_seeds.json`。

精简索引中的 `split` 当前统一为 `audit-only`。工具另实现固定的
`public-run-group-sha256-v1` 检查：先以整局 `group_key` 分组，再按 SHA-256 前8位
mod 100 划 train/dev/reserved-eval；本轮不应用正式划分，不改变 `eval_seeds.json`。
同一整局的多个楼层不能跨组，重复记录和重复 seed 必须在划分前合并。

## 6. 排除原因与实际缺口

| 原因码 | 数量 | 含义 |
|---|---:|---|
| `B_HAND_PILES_MISSING` | 12 | summary 不能形成 post-init B 快照 |
| `B_ENEMY_INTENT_MISSING` | 12 | summary 没有逐场敌人意图 |
| `B_CONTROL_STATE_MISSING` | 12 | summary 没有 PLAYER_NORMAL/队列状态 |
| `NEOW_EFFECT_RULE_NOT_YET_VERIFIED` | 11 | 首批只核验金币奖励，其余Neow效果保留逐场日志等待核验 |
| `PLAYER_ENTRY_HP_DERIVATION_UNPROVEN` | 11 | 对应Neow规则未核验，不能推导HP；不靠战后HP数组替代 |
| `RELIC_ENTRY_SEMANTICS_UNPROVEN` | 11 | 需结合实际Neow效果判断遗物，不再对全部遗物索要counter |
| `POTION_ENTRY_DERIVATION_UNPROVEN` | 11 | 对应开场效果规则尚未证明，不默认空槽 |
| `PRE_ENTRY_MUTATION_UNPROVEN` | 1 | 首层前后变更与窄规则不一致，保留具体原始记录 |
| `ENCOUNTER_GENERATOR_NOT_REGISTERED` | 3 | 本轮未登记Small Slimes生成器，不是缺历史意图 |
| `SOURCE_RULESET_COMPATIBILITY_UNVERIFIED` | 12 | 源历史版本与核查规则兼容未认证 |
| `SOURCE_MOD_MANIFEST_UNAVAILABLE` | 12 | 来源缺完整mod清单；不等于已确认游戏性改变 |
| `DYNAMIC_RELIC_COUNTER_MISSING` | 5 | 动态遗物的计数时点不明，不能补0 |
| `UPGRADE_FORMAT_AMBIGUOUS` | 4 | `Name+` 没有升级次数，不能伪造 `+1` |
| `ENCOUNTER_NOT_REGISTERED` | 5 | 详细场景敌人组没有本轮稳定遭遇 ID |
| `UNKNOWN_ENTITY_OR_SEMANTICS` | 5 | 卡牌/遗物/动态语义不在本轮审计 registry |
| `UNAPPROVED_ENTITY_SEMANTICS` | 3 | 非空药水只观察到，尚未批准其参数/动作闭包 |
| `DECK_EMPTY_OR_MISSING` | 4 | 升级歧义导致牌组无法完整解析 |

还存在不计入原因码但必须留给主审的限制：详细 run 含 `superfastmode`，日志不完整
结束；入口前 snapshot 和完整 RNG stream/counter 缺失；当前后端只接受 A0 三种
遭遇、固定 starter deck，没有任意战斗状态注入。这些限制不通过删除遗物/药水/升级
来规避。

## 7. 可行性结论与下一审核点

数据侧 M2 的有限可行性成立：公开日志能提供真实玩家在具体楼层的牌组、重复牌/部分
升级、HP、敌人/意图、遗物计数和药水槽位，并能定位到“开战效果和初始抽牌之后”的
入口。R1 修复后，工程状态不再把这等同于可继续运行：2个场景的结构和可见入口字段
通过，但内部 BattleContext 可构建性为 `unproven`；当前后端可直接执行场景仍为0。
12个summary中1个在标准规则下可构造A，11个有具体规则缺口，均未形成正式场景；
5个详细场景保持排除。第二轮逐字段证据和最小缺口见 `docs/m2-entry-a-evidence.md`。

主审应重点复核：

1. 公开日志省略 `powers`、`block`、`damage`、`counter` 的序列化语义，不能把字段
   缺失简单视为模型不需要；
2. `turn=1` 是基于入口锚点的推导值，不是源字段；`PLAYER_NORMAL`/action queue 仍未
   由日志证明；
3. `Burning Blood`、`NeowsLament`、`StoneCalendar` 的动态语义和 `exitBattle` 时点；
4. `public-b0-core` 的容量是 hand=10、合并 pile=10、relic=2、potion=3、固定
   status width=5；Anger/生成牌场景不得复用该证明；
5. 仅1个独立详细 run 仍不能产生正式 train/dev/eval；本轮所有场景必须保持
   `audit-only`。

主审应重点核查：

1. `state:floor` 第一次 combat snapshot 是否足以作为“初始抽牌后”统一时点，是否
   需要把 `turn=1` 作为可靠推导字段而非默认值；
2. `NeowsBlessing` counter 和 `superfastmode` 的游戏性影响是否允许在后续批次中
   通过书面证据销账；
3. 仅有名称+升级后缀、没有 UUID 的卡牌实例是否满足 M3 reset 输入，若不满足应
   继续排除而非补升级次数；
4. 当前 `MAX_HAND=10`、`MAX_ENEMIES=5`、`pile_capacity=10` 和31动作是否只能
   保持 minimal-v1，不能被这两个候选直接沿用；
5. 公开 source seed 与未来模拟器复跑 seed 的分离、整局分组以及 `audit-only` 边界
   是否被后续数据管线保留。

第二轮主审修复后仍停留M2；来源规则兼容、正式内容/容量及独立分组未完成，不进入M3。

第二轮主审实际复跑：审计专测37 passed、全量315 passed、规格检查PASS；离线结果为1个A规则构造候选但来源未认证、正式A候选0。输出schema为m2-public-run-audit-v2。完整字段证据见 `docs/m2-entry-a-evidence.md`。
