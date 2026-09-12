# M2 批量公开战斗场景库

日期：2026-09-12。本轮完成全库清点、关联去重、第一幕批量规则重建和研究划分。M2正式准入仍未完成，不进入M3或PPO训练。

## 已经得到什么

| 指标 | 实际结果 |
|---|---:|
| 固定仓库中的Ironclad原始文件 | 203 |
| 独立run关联组 | 157 |
| 重复文件副本 | 46；无不同内容的冲突组 |
| 独立run中的全程战斗记录 | 3957 |
| 本轮审计的第一幕第1–15层战斗记录 | 1282 |
| 按已核实规则可构造、来源完整规则未认证的候选 | 257场，118个独立run |
| 首场以后候选 | 139场；整体覆盖第1–5层 |
| 包含非起始牌的候选 | 191场 |
| 含升级牌的候选 | 18场 |
| 不同卡组多重集 | 160种；忽略卡组顺序但保留副本/升级 |
| 候选中的卡牌类别 | 72类，含Ironclad、无色牌和诅咒 |
| 普通遭遇标签 | 14种；精英强化状态未证明，精英尚无完整候选 |
| 遗物类别 | 5种：Burning Blood、Lantern、Blood Vial、Bronze Scales、Bag of Preparation |
| 非空药水场景 | 75场，27种药水 |
| 正式准入场景 | 0；来源兼容、内容/动作闭包和容量/后端实现尚未通过 |

这些数量只描述固定公开库及本轮可重建前缀，不能代表全部玩家。全部157个run均为A20，来源版本分布为2022-03-07×27、2022-10-04×58、2022-12-01×13、2022-12-18×59。不能把它们降成A0；也不能用72类的数据覆盖冒充72类后端行为验收。

原12份审计是方法验证，继续保留在原索引中。本轮独立产物：

- 工具：`scripts/audit-public-corpus.py`；不调用训练器，不改变正式环境。
- 完整候选、逐场排除码、来源别名、研究分组：`docs/m2-corpus-index.json`。
- 数据/记录器固定提交及原始ZIP哈希：`docs/m2-corpus-source-evidence.json`。
- ignored原始归档与全量结果：`reference/public-run-corpus/`。

## 来源与字段证据

可信度A表示直接读取一手仓库或正版字节码；日期均为2026-09-12。以下证据核实字段语义，不能证明所有历史run的完整mod列表。

| 编号 | 一手定位 | 支持的具体结论 |
|---|---|---|
| M2C-01 | [数据仓库固定README](https://github.com/MaT1g3R/Slay-the-Spire-data/blob/097aaf3564c2247835162d267cbc7c55d2c9039e/README.md) | 作者描述为自己及经许可的其他主播run，分析流程要求Run History Plus。固定ZIP约9.84MB；逐个解析character字段，而非仅查路径 |
| M2C-02 | [2022记录器Neow补丁](https://github.com/modargo/RunHistoryPlus/blob/99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b/src/main/java/runhistoryplus/patches/NeowBonusRunHistoryPatch.java#L185)，尤其L232–304 | 记录增删/变形卡、升级前metricID、获遗物以及HP/gold变化；升级应替换一个副本而非额外加一张。选牌型Neow还要合并card_choices的floor0结果 |
| M2C-03 | `reference/sts1-decompiled/m2-entry-a/abstract-dungeon.txt:5178`及`:5476`，nextRoomTransition/incrementFloorBasedMetrics | HP/maxHP/gold在旧floor递增前记录，先于目的房间onEnterRoom/onPlayerEntry。第N场可取前层边界数组[N-2]；不能读取[N-1]作为开战前值 |
| M2C-04 | `third_party/sts_lightspeed/src/combat/BattleContext.cpp:84`，initRelics；`:569`，战斗出口；以及GameContext.initPlayer | 仅对已核查无需跨战斗counter/选牌绑定的开场遗物恢复。Pen Nib、Omamori、Tiny Chest等不补0，不从最终relic_stats推断入口状态 |
| M2C-05 | [2022药水日志补丁](https://github.com/modargo/RunHistoryPlus/blob/99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b/src/main/java/runhistoryplus/patches/PotionRunHistoryPatch.java#L100)及[使用日志订阅器](https://github.com/modargo/RunHistoryPlus/blob/99ad7fbb462caaa2eb82ed0fc2151dd2bf2fc48b/src/main/java/runhistoryplus/subscribers/PotionUseAddLoggingSubscriber.java#L12) | 每次nextRoomTransition新增一项；使用/丢弃记录ID，不保存原槽位。库存与原槽位须分开，缺日志拒绝；自动复活/生成/楼层内无法排序的使用不推断 |
| M2C-06 | `third_party/sts_lightspeed/include/constants/MonsterEncounters.h`、`src/combat/MonsterGroup.cpp`及BattleContext.init | 14种普通遭遇有生成器映射；敌人实例/HP/意图及牌序可重新生成，不需要冒充历史精确回放 |
| M2C-07 | `reference/sts1-decompiled/m2-entry-a/campfire-smith-effect.txt:90` | 营火SMITH先记录metricID再upgrade，重建按旧实例替换升级实例 |

Neow补丁和药水补丁的2022固定提交时间为2022-09-08，早于本轮最初研究的2022-09-12 run。另缓存了2025最新版用于对照，**没有用最新版冒充历史安装版本**。这是字段语义已有历史实现的证据，不是历史玩家安装清单的证据。

正版JAR SHA沿用并已在上一轮重新验证：`CFAD868AC8D65A88E71A0BF096FB09F78811E553EFFE0787C5309A655E081673`。本轮只按D13追加营火升级时点定点核查；不把反编译内容复制入模拟器。

检索记录：searxng/tavily/doubao均执行；doubao本次结果多为STS2，未用于STS1事实。searxng正文读取把公共GitHub误判为受限URL，未调整其安全设置，改由GitHub连接器和固定公开ZIP核验。普通版本新闻检索未取得足以认证各历史run完整规则的证据，不据此断言兼容或不兼容。

## 重建流程与拒绝条件

1. 读取固定ZIP中全部.run，按内容中的IRONCLAD筛选。原来路径筛选看到157份，本轮还找到chegs/all下46个副本；它们没有被计成新run。
2. 用raw SHA、play_id、source seed做传递关联分组。同seed、同play_id或重复内容不会跨研究划分；同组内容冲突时整组不能生成完整候选。
3. 根据角色/进阶基础配置、完整Neow日志以及floor0选牌构造初态。支持金币、HP、增删/变形/升级、选牌以及已证开场遗物；奖励数量/类型与日志矛盾则拒绝。BOSS_RELIC、Neow's Lament等复杂路径仍延期。
4. 沿历史前缀应用普通战斗奖励、休息/锻造、已知遗物获取及药水库存变化。首个无法证明的事件/商店/动态机制出现后，后续场景带明确PREFIX_UNPROVEN，不用部分重建状态冒充完整状态。
5. 当前场景在目的房间入口效果和战斗初始化之前。用`entry_timing=pre_combat_initialization`和`initialization_phase=before_destination_room_entry`标记；未来后端必须执行一次房间入口和战斗初始化。不是把旧B快照退回A。
6. 药水以库存多重集重建，运行时采用`canonical-inventory-slots-v1`分配新槽位，不宣称恢复玩家原槽位。缺使用/丢弃日志、库存下溢/溢出、Fairy自动触发、Entropic/Alchemize生成和同层获得又使用而时序未证时整体拒绝。净库存守恒不能单独证明时序合法。
7. 同时校验已知卡ID/升级次数，RitualDagger等缺永久实例值的场景不准入。名称存在于后端目录只证明类别可识别，不证明动作/生成/选择闭包已支持。

每个候选保存source path/raw hash/group/source build/source seed及逐字段证据号。环境seed尚未分配，source seed不进入模型。未知遗物/药水或需要二次选择的内容不能被删除或只mask掉后继续当作原场景。

## 研究划分

划分规则固定为关联组ID的SHA分桶80/10/10，命名`connected-identity-sha256-v1`。实际是确定性分桶，不是保证每个桶精确达到该比例。未按胜负筛样本。

| 范围 | train | dev | reserved-eval |
|---|---:|---:|---:|
| 全部157个run组 | 116 | 24 | 17 |
| 118个有规则候选的run组 | 90 | 19 | 9 |
| 257个规则候选场景 | 190 | 46 | 21 |

别名、重复内容、play_id及source seed的跨组泄漏检查通过。这些均为**研究预划分**，不是正式训练或保留评估；正式评估环境seed仍来自不可变eval_seeds.json。本轮未改该文件，未运行任何模型评估，也没有按评估表现挑选候选。

## 与M1/M3/M4目标的差距

35类M1候选已有29类出现在完整规则候选中；但一个场景只要含任意不支持内容就必须整体延期。因此还另外统计整副卡组闭包：在暂时把必需的AscendersBane作为额外待审类、排除True Grit升级版的前提下，有103场的整副卡组落在M1候选集合中。**103场仍没有通过遗物/药水/动作/容量及来源准入**。

六类暂未进入完整候选的牌并非公开库里没有。其第一幕拿牌记录为：

| 卡牌 | 拿牌记录数/独立run数 |
|---|---:|
| Dropkick | 6/6 |
| Entrench | 2/2 |
| Rage | 8/8 |
| Sentinel | 1/1 |
| Thunderclap | 1/1 |
| True Grit | 1/1 |

每条来源路径/楼层已写入索引`missing_m1_cards_recorded_act1_rewards`。拿牌记录不等于后续战斗可重建，也不保证拿牌后还有目标范围内的战斗。

主要阻碍（计数重叠，不能相加当作总场数）：未知事件前缀474场、精英强化信息缺失388场、动态遗物历史前缀224场、商店前缀155场。源记录green_key_taken_log只能定位取得钥匙，不能证明其余精英不是燃烧精英，更不能猜强化类型。

下一轮应直接针对这些已有来源记录补规则：

1. **来源准入**：取得历史规则/mod兼容证据，或接入有完整来源声明的另一公开库；当前记录器源码只销掉字段语义疑问。不得为非零正式数量而降低标准。
2. **构筑覆盖**：优先恢复上述六类牌所在run的事件/商店前缀，逐事件/逐交易证明增删/升级和遗物效果，而不是继续泛搜同类summary。
3. **完整场景依赖**：按103场整副卡组候选逐场计算遗物/药水/二次选择/生成容量闭包，得到可交给M3实施的批次；不删牌凑35类。
4. **精英**：需要燃烧精英标志及强化来源，或有充分证据排除该条件的真实场景；当前14普通遭遇覆盖不等于M4三个精英已完成。

## 复现与实际验证

```powershell
python -X utf8 scripts/audit-public-corpus.py --download
python -m pytest -q tests/test_public_corpus.py tests/test_public_run_audit.py
python -m pytest -q
python -X utf8 scripts/check-spec-v6.py
git diff --check
```

有缓存时不触网；固定归档哈希不匹配立即拒绝。脚本输出保留实现hash和后端类别映射文件hash。原12份审计脚本仍可独立离线复现。

本轮实际验证：新场景库专测27 passed；完整仓库342 passed，无失败或跳过；规格检查PASS（749行）；git diff --check退出码0，仅AGENTS.md已有行尾提示。全量离线重建成功，corpus/index/脚本hash一致；原13份raw哈希未变。当前没有更改正式环境/模型、奖励、训练入口、checkpoint或eval_seeds.json；未训练、未commit/push。
