# M2 R1–R5 修复交付报告

日期：2026-09-11。状态：按 `docs/m2-review-and-repair.md` 完成修复，M2 仍暂不通过，
等待主审复核；不进入 M3。

本轮只修改公开数据审计、审计测试、M2 契约和必要的 `spec-v6.md`/`docs/decisions.md`/
`docs/week-5-6-plan.md` 同步。没有修改三个并行预审报告、正式环境、模型、
`eval_seeds.json`，没有启动 PPO，没有 commit/push。

## 1. R1：解析、可见字段和可继续运行分层

### 已修复

`scripts/audit-public-runs.py` 新增并接入：

- `strict_integer()`：拒绝布尔、浮点、NaN、无穷和隐式 `int()` 截断；
- HP/最大HP关系、energy `0–20`、floor `0–100`、手牌10、合并非手牌10、敌人5、
  药水3等输入范围检查；
- 敌人 HP、block、damage、hits 和 relic counter 的非负/关系检查；攻击意图缺
  damage 不再默认为有效；
- post-init 入口牌区多重集检查。`draw_pile` 因序列化器省略空数组可以解码为空，但
  deck 中的牌不能因此消失；
- card/relic/potion/monster/status/intent 的最小审计 registry。未知实体保留原始值，
  进入排除码，不映射 PAD；
- `validation_status` 五个独立维度：

  ```text
  structure_parse_status
  visible_entry_status
  internal_state_status
  version_mod_status
  backend_status
  ```

当前两个原候选不再叫 `reconstructable_but_backend_pending`，而是：

```text
status = visible_entry_verified_internal_state_unproven
structure_parse_status = parseable
visible_entry_status = verified
internal_state_status = unproven
backend_status = pending-m3-state-injection
formal_eligibility = audit-only
```

### 反例测试

使用本地 `reference/public-run-audit/runlogger/ironclad_1706139943.jsonl`，不改原文件：

| 变异 | 修复后结果 |
|---|---|
| 首个场景 `hp_current=-50` | `excluded`；`INVALID_FINITE_INTEGER_OR_RANGE` |
| 删除首个场景5张 `draw_pile` | `excluded`；`PILE_MISSING_DECK_CARDS`、`FIRST_BATTLE_BASE_DECK_MISMATCH` |
| 加入 `UNKNOWN_AUDIT_RELIC` | `excluded`；`UNKNOWN_ENTITY_OR_SEMANTICS` |
| 使用未知 encounter 但保留合法 HP/intent 形状 | `excluded`；`ENCOUNTER_NOT_REGISTERED` |
| 使用 `Searing Blow+2` | 保留原卡并解析升级次数，但 `excluded`；未知动态语义 |
| 攻击 intent 缺 damage | `excluded`；`ATTACK_INTENT_DAMAGE_MISSING` |
| 4 个药水槽 | `excluded`；`POTION_CAPACITY_UNSUPPORTED` |
| 未登记游戏版本 | `excluded`；`VERSION_UNREGISTERED_OR_INCOMPATIBLE` |

## 2. R2：`.run` 入口 A/B 双路径审计

`audit_summary_early_reconstruction()` 不再把 summary 直接固定成一个“缺 hand/intent”
结论，而是分别尝试：

- **入口 A**：读取首个 `damage_taken` 战斗行、角色/进阶/版本、Neow 起始奖励和
  `neow_bonus_log`，按基础牌组尝试增删/变形/升级多重集构造；检查早期 card choice、
  event、campfire、逐层 HP、遗物获取/最终 relic stats、药水获取/使用历史和遭遇 label；
- **入口 B**：单独记录 `B_HAND_PILES_MISSING`、`B_ENEMY_INTENT_MISSING`、
  `B_CONTROL_STATE_MISSING`，只阻止 post-init snapshot，不反推 A 永远不可用。

本地12个 summary 的结果：

```text
A_pre_combat_initialization.status = partial_reconstruction_attempt: 12/12
B_post_combat_initialization_after_initial_draw.status = not_available: 12/12
formal_candidate = false: 12/12
```

每个 summary 的具体 reason code 已写入
`reference/public-run-audit/audit.json`、[docs/m2-summary-reconstruction.json](C:/Users/19091/Desktop/sts2/docs/m2-summary-reconstruction.json)
和 `docs/m2-exclusions.json`。共同缺口为：
`HP_ENTRY_TIMING_UNKNOWN`、`RELIC_ENTRY_COUNTER_MISSING`、
`POTION_ENTRY_INVENTORY_MISSING`、`ENCOUNTER_INSTANCE_STATE_MISSING`，以及部分早期
牌/事件时点的 `EARLY_DECK_MUTATION_TIMING_AMBIGUOUS`。因此当前结论是“12份均完成
A 尝试但没有一份形成正式 A 场景”，不是“所有 summary 格式永久不可用”。

## 3. R3：post-init 内部状态审计

每个详细场景现在包含 `internal_state_audit`，明确列出继续运行所需但不能因模型不可见
而删除的字段：

- `InputState=PLAYER_NORMAL`、`outcome`、action/card queue 为空；
- CardInstance uniqueId、specialData、costForTurn、freeToPlayOnce、retain、bottle；
- draw/discard/exhaust/limbo 的后端顺序；
- monster move/history、当前 move、miscInfo、status bits、targetable/dead/half-dead；
- 玩家 status、遗物 bit/data/counter/order、药水 count/capacity/slot；
- AI、monster HP、shuffle、card random、misc、potion RNG stream/counter。

当前真实两个场景均记录：

```text
internal_state_status = unproven
constructible = false
exact_historical_replay = false
```

具体 resampling policy 为 `public-battle-a-resample-v1`：

- 退回入口 A，用完整来源牌组/HP/已知遗物 counter/药水槽/遭遇/进阶驱动后端重新
  初始化；
- 开发 seed 为 `100000 + SHA256(scene_id)前8位 mod 900000`；评估只使用不可变的
  `eval_seeds.json`，本轮不分配；
- 重新采样洗牌/抽牌顺序、敌人 HP roll、初始 move、隐藏 misc、未来 RNG 和新的
  CardInstance uniqueId；
- 动态 relic counter、药水库存/容量、card specialData/costForTurn、monster history
  缺失时绝不补0；
- 结果只能叫“真实构筑和入场状态驱动的重新模拟”，不能叫原局精确回放。

## 4. R4：契约矛盾修复

已更新 [docs/m2-real-battle-contract.md](C:/Users/19091/Desktop/sts2/docs/m2-real-battle-contract.md)：

- 明确首批 card/relic/potion/monster/status registry 与参数含义；`NeowsBlessing`
  明确映射后端 `NEOWS_LAMENT`；非空 `BloodPotion`/`Weak Potion` 只列为观察到但延期；
- `public-b0-core` 遗物容量改为实际2，不再把两件遗物写成容量3；
- limbo 只属于合并的非手牌 `pile_capacity`，不另加 `card_capacity` 或额外 shape；
  第一决策点出现非空 limbo 即拒绝；
- 删除无可达状态证明的 `status_capacity=8`，改为有固定语义的5个状态字段：
  Strength、Vulnerable、Weak、Artifact、Ritual；新增状态必须新 registry/schema；
- 66动作限定为最多3药水槽、无二次选择、已注册子集的预留协议；Potion Belt/A11、
  更大容量、药水生成、卡牌/药水选择整体拒绝或另建迁移，不能只 mask 掉；
- 具体区分 `public-battle-v1` 的50回合任务硬上限与外部采集截断：前者
  `terminated=true,truncated=false,reward=0`，后者 `terminated=false,truncated=true`
  并按 v6 规则自举；
- R5 表记录 `Burning Blood` 默认持有、`exitBattle` 未接入、h_exit、Neow counter、
  Pen Nib、Sacred Bark/Blood Potion、Red Slaver miscInfo 的依赖，禁止本轮改 reward。

## 5. R5：预审整合边界

三个预审报告未被修改，但其依赖已进入决策、规范和契约：

- 当前 formal adapter 没有调用 `BattleContext::exitBattle`，所以不能宣称 Burning
  Blood 治疗、遗物计数、药水/RNG/HP 回写已生效；
- v6 的 `HP_exit` 仍要求最后动作及已实现的战斗结束效果全部结算后读取；h_exit 是否
  包含该出口治疗，等待主审，不回填旧 minimal-v1 结果；
- Pen Nib 的 9/10 计数疑点只登记测试依赖；没有因静态疑点直接改代码；
- Sacred Bark/Blood Potion 战斗/战外分支、Red Slaver miscInfo/意图继续延期；
- 预审报告中的静态枚举、单个调用链或 A0 探针不升级为行为验收。

## 6. 产物、命令与结果

本地 raw 证据根目录：

[C:/Users/19091/Desktop/sts2/reference/public-run-audit](C:/Users/19091/Desktop/sts2/reference/public-run-audit)

精简索引：

- [docs/m2-evidence-index.json](C:/Users/19091/Desktop/sts2/docs/m2-evidence-index.json)
- [docs/m2-scene-candidates.json](C:/Users/19091/Desktop/sts2/docs/m2-scene-candidates.json)
- [docs/m2-exclusions.json](C:/Users/19091/Desktop/sts2/docs/m2-exclusions.json)

优先使用已下载证据的复现命令：

```powershell
cd C:\Users\19091\Desktop\sts2
python -X utf8 scripts/audit-public-runs.py --offline --commit 097aaf3564c2247835162d267cbc7c55d2c9039e --limit 12
pytest -q tests/test_public_run_audit.py
python -X utf8 scripts/check-spec-v6.py
git diff --check
pytest -q
```

本报告写入前已完成的局部结果：

- 真实离线审计命令成功，输出7个详细入口、2个可见字段已核验/内部未证明场景、
  5个排除场景和12个 A/B 双路径 summary 结果；
- 反例命令输出符合 R1 预期；
- 审计专测最终为 `23 passed`；完整仓库测试最终为 `301 passed`，无失败/跳过；
- 13 个 raw source 文件哈希可由 `source-manifest.json` 复核；场景/排除索引由同一
  本地 raw 生成，交叉 split 检查仍为 false。

## 7. 未解决项与主审重点

未解决：

1. 没有任何当前正式后端可直接 `reset` 的公开场景；两个详细场景内部状态仍未证明；
2. 详细公开日志仍只有1个独立 run，不能组成正式 train/dev/eval，也不能证明总体代表性；
3. `state:floor` 不记录 `PLAYER_NORMAL`/队列为空和 source `turn`，当前 `turn=1`
   是入口锚点推导，不是源字段；
4. `superfastmode` 游戏性影响、Neows counter 递减点、StoneCalendar counter 语义、
   upgrade suffix 与 CardInstance UUID 未销账；
5. `exitBattle` 与 h_exit/reward 时点、Pen Nib、Sacred Bark/Blood Potion、Red Slaver
   miscInfo/意图仍未行为确认；
6. Anger/状态牌/分裂/召唤的全过程容量证明仍未形成，不能复用 B0 证明。

主审确认前保持 M2 暂停，不进入 M3。
