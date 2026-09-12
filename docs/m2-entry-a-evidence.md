# M2 原生入口 A 定点证据与第二轮收口结果

日期：2026-09-11。第二轮修复已由主审直接完成；M2仍未完成，不进入M3。

## 结论

本地12份summary复审后，1份得到 `rule_constructible_source_unverified`：在已核实的标准初始化规则下，能列出完整的首场玩家入场构造；来源历史版本/mod是否满足这些规则尚未证明。其余11份为具体规则尚未核验，不再统一因缺敌人意图/HP/实例而排除。

这不是“原局初态已完全还原”，也不是正式reset已经可运行。详细JSONL的两个B候选仍为内部状态未证明；不能把它们的post-init血量/计数直接用于A再次初始化。

## 来源身份

- 固定来源：MaT1g3R/Slay-the-Spire-data，commit `097aaf3564c2247835162d267cbc7c55d2c9039e`。
- 仓库路径：`runs/panacea-ironclad-sample/1663026387.run`；本地 `reference/public-run-audit/matiger/sample-007.run`。
- 原始SHA-256：`7e8901fc7979f1f8846a42b765ae0d773f0155adf1b688524d9a93d9e00cf10e`。
- play_id：`ee3e27cd-57fd-48ad-ab25-b4fd810fef7e`；source seed：`431906119610756110`；build_version：`2022-03-07`；IRONCLAD/A20。
- 首个damage_taken：floor=1、enemies=Cultist；path_per_floor[0]=M；is_daily/is_trial/is_endless均为false。
- 完整候选及逐字段审计由脚本生成到 `docs/m2-summary-reconstruction.json` 的对应行 `a_evidence`，不手工维护第二份JSON。

## 规则证据

以下为一手本地证据，可信度A（直接源码/正版字节码），核验日期2026-09-11。只证明锁定规则，不跨越证明历史来源版本一致。

| 编号 | 定位 | 实际支持的结论 |
|---|---|---|
| M2A-01 | `third_party/sts_lightspeed/src/game/GameContext.cpp:476`，initPlayer | A10添加AscendersBane；Ironclad基础Strike×5、Defend×4、Bash×1、Burning Blood；A14最大HP75；A6当前HP按最大HP的0.9四舍五入 |
| M2A-02 | `reference/sts1-decompiled/m2-entry-a/ironclad.txt:109`，getStartingRelics/getStartingDeck/getLoadout/getAscensionMaxHPLoss；`abstract-dungeon.txt:7396`，dungeonTransitionSetup | 正版基础配置和先减最大HP再按90%取整的顺序与本候选规则一致，75×0.9=67.5取68，不使用Python银行家舍入 |
| M2A-03 | `GameContext.cpp:66`；`reference/sts1-decompiled/m2-entry-a/abstract-player.txt:343`，构造函数 | 初始药水为空；A11起从3槽减至2槽。它不是Potion Belt的更大容量场景 |
| M2A-04 | `GameContext.cpp:2236`及`:2330`，chooseNeowOption；`reference/sts1-decompiled/m2-entry-a/neow-reward.txt:1014` | NONE没有代价，HUNDRED_GOLD增加100金币；与源日志goldGained=100及其余变化为空/0一致 |
| M2A-05 | `third_party/sts_lightspeed/src/combat/BattleContext.cpp:21`，init；`src/combat/MonsterGroup.cpp:226` | 敌人初始化、牌区初始化、遗物开场、能量和队列执行由后端完成；CULTIST生成器存在。源记录没有初始意图不是A构造的阻碍 |

后端锁定commit：`7476a81954020087da31d41d16fddf475746ec2d`。本轮未修改它。
正版核查使用 `E:/SteamLibrary/steamapps/common/SlayTheSpire/desktop-1.0.jar`，
SHA-256 `CFAD868AC8D65A88E71A0BF096FB09F78811E553EFFE0787C5309A655E081673`。
按D13，仅为HP取整/初始化时点/药水容量争议运行javap；产物在ignored reference，未复制到模拟器。

## sample-007 逐字段结论

下表中derived-with-evidence均以“来源采用上述标准规则”为条件；该条件尚未认证。

| 字段 | 值或处理 | 证据类别 |
|---|---|---|
| 角色、进阶、楼层、遭遇标签 | IRONCLAD、20、1、Cultist | recorded |
| Neow | HUNDRED_GOLD/NONE；增牌/删牌/变形/升级/获遗物均空；HP变化0 | recorded；日志和所选奖励交叉一致，不代表已证明日志覆盖任意mod |
| 入场卡组 | Strike_R×5、Defend_R×4、Bash×1、AscendersBane×1 | derived-with-evidence，M2A-01/02/04 |
| HP/maxHP | 68/75 | derived-with-evidence；不把current_hp_per_floor[0]=68当作开战前时点证明 |
| gold | 99+100=199 | derived-with-evidence；不用战后gold_per_floor[0]=213 |
| 遗物 | 仅Burning Blood；counter=null、not_applicable | derived-with-evidence；不从最终遗物表倒灌Magic Flower等后来所得遗物 |
| 药水 | 两个空槽 | derived-with-evidence；标准起始空槽且Neow不发药水。floor1获得的Fruit Juice属于该层后续奖励，不能倒灌入战斗开始 |
| 开场卡牌奖励 | floor1 picked=SKIP，不影响pre-init卡组 | recorded；测试另外覆盖战后真的拿Anger也不倒灌 |
| 手牌/牌序/敌人HP/初始意图/实例ID | 从独立environment seed经锁定初始化生成 | resampled-by-policy；不使用source seed |
| energy/block/powers/queues | 初始化一次，由后端产生 | generated-by-backend；不伪造来源字段 |
| 历史规则版本兼容 | 2022-03-07与核查JAR、后端的一致性 | unknown；不是因为日期不同就断言不兼容 |
| source mod完整清单及游戏性影响 | 原summary没有完整清单 | unknown；is_prod=false也不单独证明有游戏性mod |

最小来源证据缺口是“上述标准初始化规则确实适用于该历史run”的版本/mod/记录器证明，
而不是缺少原局敌人意图或要求恢复所有隐藏RNG。源里的战后HP与68相符只能作一致性线索，不能替代该证明。

## 实现与分布边界

- 审计逻辑现在按条件判断，无计数遗物无需counter，A遭遇通过生成器处理；B缺字段只写在B分支。
- 只有HUNDRED_GOLD/NONE的完整一致日志进入这条窄规则。变形、删牌、奖励HP、随机遗物等11个样本仍保留原值和具体未核验项，不假装已穷尽其可重建性。
- 这个A20候选含4类起始牌（含诅咒）、1种遭遇、1件遗物、空药水。它没有达到M3的30–40类卡目标，也不证明非空药水决策可用。
- 当前正式适配器没有该场景的完整协议；A20/AscendersBane、11张牌和2槽容量需独立registry/shape/行为验收，不套用B0的10张牌容量。
- 当前仅1个A候选run，不能构成独立train/dev/eval。formal_candidate=false、audit-only、environment_replay_seed=null保持不变。
- exitBattle/h_exit、旧奖励与既有checkpoint未修改；未开始PPO，未commit/push。

## 复现

```powershell
python -X utf8 scripts/audit-public-runs.py --offline --commit 097aaf3564c2247835162d267cbc7c55d2c9039e --limit 12
python -m pytest -q tests/test_public_run_audit.py
python -m pytest -q
python -X utf8 scripts/check-spec-v6.py
git diff --check
```

本轮新增测试覆盖A规则候选、缺关键玩家来源字段、矛盾Neow日志、A0/A6/A10/A11/A14边界、
拒绝战后奖励/最终牌组倒灌，以及来源未认证不能正式准入。真实12份离线审计与合成测试分开报告。

## 本轮实际验证结果

- 离线复审12份summary、7个B入口：成功；1个A规则候选，正式A候选0，2个B可见字段通过/内部未证明。
- 审计专测：37 passed；完整回归：315 passed，无失败或跳过。
- 规格检查：PASS，749行；git diff --check：退出码0，仅AGENTS.md已有行尾提示。
- 正版JAR SHA-256本轮重新计算，与上列锁定值一致。
- 审计输出schema升至m2-public-run-audit-v2，新增A逐字段证据和构造候选；正式训练协议未改。

下一步有明确顺序：先补这个来源run的历史版本/mod规则兼容证据，或找到有该证据的另一原生A来源；
再扩充真实内容覆盖及独立run分组，锁定容量和实现契约。不能用增加同一场的随机seed代替增加独立run。
