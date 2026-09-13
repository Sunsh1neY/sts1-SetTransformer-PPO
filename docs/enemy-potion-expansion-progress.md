# 敌人与药水扩展交付记录

日期：2026-09-12。独立worktree：`C:/Users/19091/.codex/worktrees/7f84/sts2`。本次交付EP0/EP1和统一实体EP2交接层，正式训练未准入。原冻结MLP/Set对照报告只读核对为complete、各2次；本分支未修改或重新标注这些结果。

## 实际实现

- 独立C++ `EnemyPotionBattleEnv`、Python `sts.env.enemy_potion`、中央契约与增量补丁。旧public/minimal入口及基础补丁不替换。新入口只接受显式development诊断场景，正式来源/训练仍需主集成。
- 第一幕14普通＋3精英继承，新增Slime Boss、The Guardian、Hexaghost，共20遭遇。Boss房间/floor17、意图、守护者Mode Shift/Sharp Hide观测已接入。
- 继承15药水；新增Fire Potion、SteroidPotion、CultistPotion、Blood Potion、FairyPotion共5种。血药在独立入口修正20%治疗；仙灵被动触发且无主动合法动作。
- 六火亡魂Inferno：正版BurnIncreaseAction确认升级抽/弃牌堆Burn，并加入3张Burn+。锁定后端原分支遗漏该效果；新开关只在独立入口启用修复，旧入口保持原行为。独立观测登记Burn+，耗尽牌堆不被错误升级。
- 变长敌人/药水实体视图与引用路由。特征、动作槽位、引用、revision分开；消耗/死亡/分裂/reset使旧引用失效。没有实现另一套Transformer或PPO，详情见实体接口文档与JSON样例。
- 队列资源检查：独立入口启用ActionQueue50/CardQueue10的写入前溢出拒绝，关闭assert的构建也不静默覆盖队列。后端或观测异常使Python包装器失效，要求重新reset；非法mask动作在执行前拒绝，环境保持可用。

## 测试证据

- 针对性Python回归最终统计在本文件末节更新。前一次为213 passed、0失败、0跳过，覆盖新增机制/实体路由、旧15药水逐步同场对照、旧公开遭遇和minimal适配器。
- 合成诊断120局，A0/A20×20遭遇×3药水配置；2453 transition，77胜/43败、0截断、0异常、0未完成。最大实体50，观测到的最大单步净增长6；此数不是静态最大生成证明。随机策略及完整动作列表在被忽略reference/enemy-potion-diagnostic.json，不是人类真实卡组分布或PPO收益。
- 单独预算测试确认最终完整观测及合法mask保留、reward0且ongoing；没有把截断标为失败。史莱姆分裂不终止，子体目标合法；仙灵救命后继续战斗；六火亡魂按公开HP形成Divider伤害，Inferno后Burn+数量与数值断言通过。
- 首轮43通过/4失败：两项盗贼逃跑断言错误（现有battle契约视敌人全部离场为胜利），两项Burn+注册缺口；后续190通过/3失败是固定手牌槽测试误打Slimed、回合从0计数和错误假定自动添加AscendersBane，已改用真实牌名路由与实际入口语义。未修改既有测试断言。
- 没有执行全仓回归、GPU训练、正式Gate或共享Set编码器测试；独立worktree未复制全仓被忽略历史夹具。

## 容量与准入

动态token不等于无资源上限。当前手牌10、目标5、药水3，非手牌vector完整保留。初态最多96实例，外部最多512动作；累计实例ID受int16范围约束。

本批重新审计：旧支持卡单动作至多2新卡；直接药水不生成卡；史莱姆Boss一次5 Slimed，分裂后至多4只Slime各至多3（12）；六火亡魂一次Inferno3、Sear至多2；守护者0；其余原第一幕最坏5敌各3（15）保守覆盖。采用15上界，96＋512×15＝7776＜32767。当前normal行动不含自动打牌、选牌/复制生成或敌人复活，该证明不得迁移到这些新内容。Power离开牌区不回收累计ID，净实体增长不能代替分配计数证明。C++保留累计ID上界检查，额外结算队列在写入前检查。

目前只有完整原始字典和实体交接层的开发准入；统一实体Set的动态batch内存预算、训练collector、候选动作、checkpoint迁移和完整真实卡组闭包仍由主集成验收。这里没有继承原五遭遇8张余量或固定64模型行数。

## 未准入与依赖

Ironclad池33药水逐项状态在sts/env/enemy-potion-coverage.json：20已实现（15继承＋5新增），13未准入。七种选择药水Attack/Skill/Power/Colorless/Elixir/Gambler's Brew/Liquid Memories依赖全卡候选和选择接口；Snecko Oil依赖临时费用；Blessing of the Forge、Duplication、Distilled Chaos依赖升级/重复/自动打牌完整闭包；Entropic Brew依赖药水生成、弃药与槽位生命周期；Smoke Bomb需逃跑结果契约，不得伪装击杀胜利。

其余幕与事件遭遇已按后端枚举全部列入台账但不开放：第二幕召唤/Stasis、第三幕复活/多阶段/反应状态、第四幕多段上限等都需公开状态、动作/生命周期及容量独立核查。跨战斗药水库存、Fruit Juice永久最大HP、回血效果的run持久化、奖励掉落/逃跑控制流没有RunEnv集成；仅当前battle效果不能宣称完整爬塔。

## 主集成所需文件处理

- 独立文件可审核拣入：enemy-potion Python/JSON、实体视图、测试、构建/诊断脚本、文档和增量patch。
- 共享差异必须人工审核：增量patch中的CMakeLists、bindings/slaythespire.cpp注册、BattleContext独立开关、MonsterSpecific Inferno、ActionQueue/CardQueue保护。与全卡增量patch可能邻接冲突，禁止互相覆盖。
- 本分支Python包装暂时沿用public结构的独立副本；主集成应将药水/敌人能力和实体路由接入全卡公共normalization/候选层，不替换全卡动态费用字段，不把本副本当作第二套全卡协议。
- 当前引用生命周期不能处理同槽同种在一个动作内重新生成；依赖内容拒绝，主集成需稳定生命周期事件后开放。
- 源码/构建指纹与统一模型保存格式待主集成。旧eval_seeds/public/真实批次/基础补丁哈希见enemy-potion-frozen-hashes.json，交付前重新核对。

## 复现

在本worktree运行：

```powershell
./scripts/build-enemy-potion.ps1 -Python python -Jobs 1
python -X utf8 -m pytest -q tests/test_enemy_potion.py tests/test_enemy_potion_entities.py tests/test_public_consumables.py tests/test_public_encounters.py tests/test_public_battle.py tests/test_cpp_env.py tests/test_lightspeed_adapter.py
python -X utf8 scripts/diagnose-enemy-potion.py
python -X utf8 scripts/check-spec-v6.py
git -C third_party/sts_lightspeed apply --reverse --check ../../patches/lightspeed-enemy-potion.patch
```

正版定点证据：EPE01，一手本机正版JAR，核验2026-09-12，SHA256 cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673（本轮重新计算一致）。Hexaghost.takeTurn/BurnIncreaseAction.update、SlimeBoss/TheGuardian及5药水类的class哈希在enemy-potion-evidence.json；仲裁文件只保留reference，不提交、不照抄正版源码。上游证据EPE02为锁定7476a81954020087da31d41d16fddf475746ec2d与基础补丁的实现核验，不能替代全机制正版逐动作对拍。

## 本批最终复核

- 2026-09-12最终Python回归：213 passed，3.79秒，0失败/0跳过；其中本批新增71项（67机制/边界/继承对照＋4实体路由），其余142项为既有针对性回归。
- 独立构建入口导入成功；增量补丁对基础补丁后的暂存树正向检查、对当前源码反向检查均通过。
- `./scripts/check-enemy-potion-capacity.ps1`：4项Release队列满载写入前拒绝检查通过。最初独立链接只带CardQueue.cpp缺少CardInstance符号，后改为链接正式构建的全部src对象；不伪造后端桩函数。
- 加入队列保护后重跑120局，仍77胜/43败、0截断/异常，2453步；诊断文件SHA256为652b631eb4c55ae2b3631bedf679b4f809c31c1768f323e1395fb00aa3f88613。
- eval_seeds.json、旧public契约、真实批次、基础后端补丁哈希均未变；规格检查PASS。没有写入Desktop/sts2或sts2-full-card，没有合并/提交/push，没有启动PPO或GPU任务。
- EP0/EP1/EP2本批交付完成；EP3–EP5与完整药水/其余幕/统一模型正式训练未完成，按依赖台账推进。请主集成审核共享文件增量和实体接口，不能将213回归等同于全仓或全机制正版对拍。

## EP2b：桌面迁移、构建指纹与共享接口复核

当前工作路径已迁移为 `C:/Users/19091/Desktop/sts2-enemy-potion`，分支 `codex/enemy-potion-expansion`；开头的旧路径是本批早期工作位置。Git登记已指向新路径，231关键文件迁移哈希全部一致。原应用占用目录保留为非活动备份，`.git`入口已改名为`.git-before-desktop-move`。

构建脚本已增加CMake源目录核验：旧缓存移至当前目录的build-before-desktop-move，再配置桌面路径。新增模块属性enemy_potion_contract_sha256，与Python中央契约逐字节SHA核对；缺失或不匹配时在分配环境前拒绝，避免迁移后误用旧后端。原public/minimal入口不要求新指纹。

全卡共享接口已有统一实体模型及单选EXHAUST_ONE。本次只读静态审计发现：3 Boss名称、Mode Shift/Sharp Hide词表已齐；5新增药水尚缺，原15药水ID无冲突。新增activation/potency_unit需由共享编码器增加维度及版本；共享编码器保留present的不可选敌人，本分支视图省略非targetable实体，需要统一生命周期规则。不能把本分支缺少全卡动态字段的旧卡牌观测补零后冒称ironclad-observation-v4。

审计命令：`python -X utf8 scripts/audit-enemy-potion-shared.py --shared-root C:/Users/19091/Desktop/sts2-full-card`；输出docs/enemy-potion-shared-handoff.json，记录读取时的共享契约/编码器SHA。没有导入或运行共享模型，没有写入全卡目录。当前药水支持仍20/33，本批没有将13依赖项改标已完成。

EP2b最终验证：桌面新路径重新编译并实际加载本目录slaythespire.cp313-win_amd64.pyd；215项Python回归通过（新增2项指纹缺失/错误拒绝），4项Release队列检查通过，规格检查PASS。120局诊断仍77胜/43败、0截断/异常。基础补丁、旧public/真实批次与eval_seeds四项冻结哈希不变。增量补丁反向适用检查通过，未提交/合并/启动PPO。

## 第二、三幕敌人批次完成（药水审计暂停）

用户已明确暂停药水审计。本轮完成35个第二/三幕遭遇的准入筛查，实际加入第二幕10＋第三幕3共13遭遇，其余22保持用户审核、reset拒绝。详情及完整名称/风险表在docs/act23-enemy-review.md，机器台账在docs/act23-enemy-audit.json。

新增92专项测试，连同原独立/公开/minimal针对性回归共307项通过；4项Release队列检查通过。312局空药水合成诊断5726步，36胜/276败、0截断/异常。加入9种新敌人身份及组合遭遇；独立入口总33种遭遇，药水仍20/33。

独立契约/观测升级v2，正确校验幕/楼层/遭遇与房间；新增护甲、适应性、回合增力、壁垒等公开状态以及STUN/STRONG_DEBUFF/ATTACK_BUFF意图。修正Hex布尔导出，不修改旧public/minimal。巨人头颅等特殊机制仍未准入，完整RunEnv/统一模型正式训练未实现。冻结哈希、增量补丁正反适用、规格检查通过，未提交/合并/启动训练。

### EP3 三位置意图接口验收（2026-09-12）

- 已完成观测v3、实体v2、三位置后端意图编号与有效性校验、词表清单、真实六火亡魂三帧样例。新增10项历史/错误输入测试，相关回归317通过、0失败、0跳过；4项Release队列容量检查通过。补丁相对基础正向校验与当前反向校验通过，4份冻结哈希未变，spec检查通过。
- 首轮142失败/170通过：C++仍输出旧schema，修复为v3。第二轮19失败/298通过：15项旧接口比较需明确排除新增/替换的历史表示，3项负例夹具需将numpy mask转JSON列表，1项邪教徒测试错误假设每回合调用setMove。修正测试的接口投影及真实更新语义，未改写旧冻结观测文件。
- setMove才移动三格，NoOpRollMove不移动；史莱姆直接覆盖当前意图仍不移动尾部。这是后端设置记录，不是逐回合已执行历史。
- 发现三大颚虫初始化DARKLING_REGROW占位：独立导出仅对大颚虫这一非实际意图编号归零并mask，模拟器选招不变；其它特殊编号审计仍延期。
- public_history中的完成回合/睡眠/蓄力计数继续保留；仅删除被三位置编号替代的last_intent_kind/previous_intent_kind。通用phase、Flight及特殊22遭遇未准入。
- 药水未扩审，无PPO训练；尚未接入全卡共享编码器。该任务需要接收v3/v2、分类词表与三个位置的embedding/mask，不允许把旧checkpoint当成兼容。
- 文件：docs/enemy-token-fields.md、docs/enemy-intent-vocabulary.json、docs/enemy-intent-example-v3.json。

### 已批准状态接入，铜球关系暂缓（2026-09-13）

- 已在独立后端导出Flight、Thorns、Slow、Intangible、Fading、Shifting、Reactive、Time Warp；Slow存在且计数0保留，Shifting按布尔值1。契约状态修订1改变SHA，旧模块仍被指纹校验拒绝。共享编码器尚未集成八状态，phase尚未落地；本轮没有新增遭遇白名单。
- 新增test_enemy_status_export.py直接编译生产导出函数，验证八状态值与空状态，属于导出层夹具，不冒充完整敌人机制对拍。相关测试共318通过、0失败/跳过，8.47秒；后端实际构建导入通过、基础冻结四哈希未变、增量补丁反向校验通过。不做极端容量测试或PPO。
- 铜球关系/区域/模型未实施。咨询材料docs/stasis-relation-design-review.md包含实际模型结构、关系事实与公开性待核项、A注意力偏置/B一次融合/C候选上下文/D关系token比较和验收问题，等待用户外部审阅意见。

### 非铜球首批全卡集成更新（2026-09-13）

MAW/TRANSIENT独立公开入口已接；MAW/TRANSIENT/SNECKO全卡A20集成通过，345相关回归及新增padding后的8项专项通过，450局7225步0异常（1次预算截断）。旧表保留历史身份，当前范围以docs/enemy-full-card-integration-report.md为准。时间吞噬者按用户最新选择暂缓，铜球仍暂停。

收尾实际核验：冻结四文件及共享来源文件SHA未变，全卡工作树干净；新后端契约指纹匹配；增量补丁正向/反向检查通过，spec检查PASS。改动尚未提交，未推送或合并。

## 第二幕首批执行结果（2026-09-13）

本批新增13个全卡A20遭遇，第二幕14/22；修复Hex布尔导出和扎人的书高进阶单刺计数。相关回归389通过，唯一编译内存失败项单独重跑1通过。剩余8遭遇及铜球B/阶段/终局出口仍待实施，不等于全部完成。完整证据见[本批报告](act2-full-card-batch-report.md)。Minion不额外导出，审批已收口；旧待决描述仅为历史。

## 第二幕22遭遇收口（2026-09-13）

剩余8遭遇已完成A20全卡开发接入，第二幕现22/22（含三项事件战斗部分）。B一次关联融合、stasis身份限定观测、三类公开phase、实例引用和终局battle_exit已落实。CARD116、ENEMY774，模型unified-enemy-entity-set-v2；旧模型不可精确续训。

本批434相关回归通过，状态编译夹具另1通过；3300局全卡短程交互53906步、316次选牌、3256自然终止、44外部截断、0异常。未正式训练、未推送/合并。完整范围与证据边界见[第二幕完成报告](act2-completion-report.md)。本文更早的“8遭遇待完成”“铜球暂停”等只保留历史意义。
