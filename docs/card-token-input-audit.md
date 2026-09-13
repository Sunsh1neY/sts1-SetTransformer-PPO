> 2026-09-12修订：下文为v2输入/v1模型的历史说明。当前实施以 [输入v3契约](entity-input-v3-contract.md) 为准；115维卡牌、无伤害预览关系、取消466牌数截断。

# 当前卡牌token输入与剩余卡牌阻塞审计

2026-09-12。审计对象：独立worktree `sts2-full-card`，实现基线 `be7dd10`，`unified-entity-interface-v2` / `unified-entity-set-v1`。截图仅用作“分组—对象—暂未加入原因”的呈现参考，不代表已验证其他任务的敌人实现。本次只新增审计及核对脚本，不改模型、后端、运行契约或启动训练。

## 1. 实际输入是什么

每张真实卡牌各有一个 **122维float32原始语义向量**。经卡牌专用Linear(122,64)加CARD类型嵌入，成为64维token；与敌人、药水、遗物、玩家全局token共同经过2层、4头、FF128的Transformer。64维隐表示由学习决定，不能给每个隐维固定命名。重复卡逐张保留；无位置编码；padding有效性由独立mask提供。

| 原始索引（0起） | 维数 | 意义 |
|---|---:|---|
| 0–10 | 11 | 升级次数、战斗基础费用、当前费用、伤害基值、格挡预览、格挡基值、magic、段数、实例增伤、印刷费用、有效费用 |
| 11–19 | 9 | 费用已知、全体、虚无、固有耗尽、一次免费、保留、Strike类别、有效耗尽、有效费用已知 |
| 20–100 | 81 | 卡牌种类one-hot，索引=20+语义ID；0保留，1–80为75战士+5辅助的计划词表 |
| 101–105 | 5 | ATTACK、SKILL、POWER、STATUS、CURSE |
| 106–107 | 2 | NO_TARGET、ENEMY |
| 108–110 | 3 | ENERGY、X、UNPLAYABLE |
| 111–115 | 5 | UNKNOWN、COMBAT、TURN、POWER、ONCE费用范围 |
| 116–121 | 6 | hand、draw_pile、discard_pile、exhaust_pile、resolving、offer |

逐个索引、卡名、数值缩放详见 [122维字典](card-token-dimensions.md)。词表覆盖不代表准入：当前登记 **40类战士80版本**，剩35类70版本；5辅助不计入75类。卡牌ID既不区分重复实例，也不单独区分升级版；升级次数由第0维提供。

实现链：`bindings/public-battle-env.cpp::cardRow`产生公开行 → `sts/env/ironclad.py::normalize_ironclad`与public规范化 → `sts/env/entities.py::card_features/encode_observation/collate` → `sts/models/entities.py::encode_entities/forward`。在本worktree的 `third_party/sts_lightspeed/` 下读取binding；可提交补丁位于 `patches/lightspeed-ironclad-expansion.patch`。

## 2. 新增维度为了哪些卡牌

比较基准为冻结 `sts/models/comparison.py`：旧输入29维连续/分类特征，另有卡牌ID输入；旧身份不是新增信息。不能简单称为“新增93个机制维度”。

| 变化 | 当前索引 | 对应卡牌/关系 | 已有证据与限制 |
|---|---|---|---|
| 实例累计增伤 | 8 | Rampage基础/+；未来Double Tap、复制/移区 | 当前不同Rampage实例增长、Strength与预览分离有机制测试；复制与双发尚未验收 |
| 印刷费用、有效费用及已知位 | 9、10、19 | Blood for Blood、Corruption；未来Infernal Blade、Havoc、Whirlwind；敌人异蛇、改费药水 | 当前失血降费、技能免费和印刷费用分离已测；X、随机费用及多重改费仍有缺口 |
| Strike类别 | 17 | Perfected Strike；Strike_R、Pommel Strike、Twin Strike、Wild Strike等参与计数 | 属性已导出；Perfected Strike本身尚未准入，计数区域与结算仍待验证 |
| 有效耗尽 | 18 | Corruption及所有技能，Sentinel、Feel No Pain、True Grit+；未来Havoc | 当前Corruption技能耗尽链已测；不能代表未来自动打出上下文的所有耗尽规则 |
| 费用类别 | 108–110 | Whirlwind、不可打出的状态/诅咒、普通能量卡 | 词表已有；Whirlwind未准入，effective_cost当前夹零逻辑不提供X能量快照 |
| 费用作用范围 | 111–115 | Blood for Blood、Corruption、未来生成零费及异蛇 | 当前基于手牌与数值差异选择一个标签，无法表达同时叠加的多个改费来源/期限 |
| resolving区域 | 120 | True Grit+；未来Burning Pact、Armaments、跨区选牌及Havoc嵌套 | True Grit+真实暂停保持来源牌，选择后继续结算已测；复杂来源尚未接入 |
| offer区域 | 121 | 未来药水生成候选等；不等于Infernal Blade需要玩家选生成结果 | 合成接口夹具已测；无真实新药水准入证据 |
| 身份词表扩大及one-hot化 | 20–100 | 所有75类战士及5辅助 | 身份表示方式替代旧embedding入口；只有80战士版本已验收 |
| 目标标志改成2维one-hot | 106–107 | 所有玩家选敌卡与无目标卡 | 原有1维目标标志的信息重编码，不是新游戏机制 |
| 缩放变化 | 0、1、2 | 升级与费用 | 升级除1→除5，费用除3→除4；不是裁剪，也不是升级上限5 |

## 3. 不能只检查卡牌向量

- `damage_by_target[5]`已移出卡牌向量，成为卡牌→敌人的2维关系：伤害预览/50、known。候选出牌评分用卡牌token、目标token、全局上下文及关系，保持目标对应；不是把五个敌人槽号塞回卡牌。当前存在敌人的关系known被编码器设为1；这一标志并不证明未来飞行、多段、随机目标等预览都已正确。
- Barricade/Corruption活动状态、Combust伤害总量、单独的 `combust_hp_loss` 在PLAYER_GLOBAL，不新增能力卡残留token。Combust打出前的卡牌magic只是5/7，不能据此推断叠加后失血次数。消耗堆、HP、能量、Strength、No Draw、敌人状态以及遗物/药水实体共同参与决策。
- SELECT_CARD阶段、选择种类、min/max在PLAYER_GLOBAL；可选对象、环境合法mask、来源引用在候选接口。一次性decision_id、手牌/敌人槽位及实际路由在模型外。当前只批准一选一，真实运行只接通True Grit+的EXHAUST_ONE；其他枚举存在不等于实际可用。
- `damage`不是净扣血，`block`不是完整事件模拟，`magic`不是统一效果结构。模型输入中没有另一个完整“技能描述字典”；模型可通过ID区分卡，但需学习ID对应效果。Offering的自伤/能量/抽牌三种效果不能都解释成一个magic值。这属于可学习性/设计选择，不能宣称已有通用多效果编码。
- draw_pile是公开多重集，已移除隐藏顺序。当前没有“玩家先前亲自置顶并仍应知道”的牌顶记忆。缺少这类公开记忆会使Headbutt/Warcry之后的两个不同可知状态坍缩成相同输入。

## 4. 剩余35类的阻塞分组

以下互不重叠，合计35类70版本；默认同时检查基础/+，差异另列。依据当前覆盖账本、旧逐卡审计及现代码静态检查。暂未准入不全是输入缺字段，部分是机制与验收未完成。

| 分组 | 卡牌 | 暂未加入原因 | 是否需要共同协商 |
|---|---|---|---|
| 直接效果与条件，7类 | Bloodletting、Clash、Hemokinesis、Intimidate、Limit Break、Offering、Shockwave | 数值、mask、No Draw/Artifact/自伤触发待验；现字段原则上足够，需补cardRow实际导出及准入。Limit Break+取消耗尽须分别测 | 不需新架构裁定；多效果静态编码是否增加见C4 |
| 致死、治疗与随机段数，3类 | Feed、Reaper、Sword Boomerang | 致死资格、实际治疗、逐段随机目标及中途死亡；攻击预览不能冒充实际结果 | C3：与敌人生命周期/Minion/逃跑/复活及随机目标共同定契约 |
| 自动耗尽，2类 | Second Wind、Sever Soul | 每张耗尽和抽牌/格挡触发顺序；来源牌、快照、空手牌边界。不是玩家多选 | C2仅涉及统一资源证明；可先做具名机制测试 |
| 手牌单选，2类 | Armaments、Burning Pact | 候选过滤、选择后续跑、升级/耗尽抽牌；Armaments+全手牌升级，不新增选择动作 | 复用既定单选，无需再决定是否允许选择 |
| 复制与跨区取牌，2类 | Dual Wield、Exhume | 实例属性继承、满手牌、Exhume候选排除、后端helper验证；当前适配器只真实导出手牌耗尽候选 | C1费用继承；C2生成/循环与分配编号；共享来源路由 |
| 公开置顶，2类 | Headbutt、Warcry | 缺已知牌顶/顺序及失效规则；弃牌/抽后手牌候选尚未接通 | C1：公开记忆语义与编码表示须先确定 |
| 能力触发链，7类 | Berserk、Brutality、Dark Embrace、Evolve、Fire Breathing、Juggernaut、Rupture | 活动状态导出、回合时序、抽牌/自伤/耗尽/格挡连锁；Brutality+初始固有；Berserk能量映射 | C2连锁资源；C3与敌人反应/药水格挡的触发接口；多数不必增卡牌维度 |
| 动态公式、生成与X，4类 | Anger、Perfected Strike、Searing Blow、Whirlwind | 复制属性、Strike计数区域、多次升级整数边界、X执行能量快照；当前字段不是完整实现 | C1费用和X；C2生成/数值边界 |
| 自动/重复打出与生成闭包，3类 | Double Tap、Havoc、Infernal Blade | 自动目标、嵌套选择续跑、实例修改、随机池完整性和生成上界；不能缩池称全卡 | C1上下文生命周期；C2队列与生成；C3目标失效处理 |
| 已知差异风险，3类 | Disarm、Iron Wave、Fiend Fire | 旧审计定位升级减力、格挡修饰、耗尽快照/段数顺序风险；未在本轮复现或修复 | 首先本任务定向复现，不应把程序差异交给用户决定游戏规则 |

另外，已准入Combust仍有“无可用牌时后端提前判败是否遗漏持续伤害”的静态风险（进展日志R11），本轮没有复现实验；80版本准入不能解读为全组合正确。

## 5. 建议共同确定的四项接口

这里是待采纳建议，不在本次静默修改契约；多数卡牌实现无需等待这些问题全部结束。

| 编号 | 建议方案 | 需要协作的具体内容 | 验收案例 |
|---|---|---|---|
| C1 费用、公开记忆及来源 | 费用拆分公开基础值、当前值、各自known、可重叠修饰及期限；已知牌顶用公开rank+known或等价公开关系，禁止后端隐藏牌序；X保留执行时公开快照 | 卡牌任务维护schema；敌人任务提供异蛇费用的真实生命周期；药水任务提供生成/改费/一次免费；共同定义洗牌、抽牌、移区、复制后的失效规则。当前单标签cost_scope不足以自动承载全部情况 | 同名同当前费但恢复时间不同必须可辨；Headbutt置顶→抽取/洗牌后记忆正确；复制保留或重置属性按机制对拍 |
| C2 有限资源和连锁 | 保留动态长度，重新证明每个decision的生成量、队列、实例编号、数值范围；容量截断发生在完整可决策状态 | 与增长多段敌人、状态生成、药水/卡牌复制统一上界；当前每decision15和480卡证明只属旧内容范围，禁止仅更新hash | Anger+双发、抽耗循环、生成状态、多段敌人组合；越界拒绝或完整观测截断，无丢牌 |
| C3 目标、生命周期和预览 | 候选引用有效实体；targetable与present区分；伤害预览明确单段/修饰范围及known语义；随机目标不是策略动作 | 敌人任务定义Minion、倒地、复活、逃跑、替换；卡牌任务处理Feed资格、Reaper实际治疗及多段中途失效；药水沿用同一引用 | 非法目标不出现在合法分布；击杀召唤物/复活敌人；飞行多段递减；反应换意图后重新观测 |
| C4 多效果静态编码 | 近期建议保留ID+现语义以完成机制准入；如希望降低从ID学习效果的负担，再单独加入有类型的效果参数并做新版本对照 | 用户只需在准备新模型版本时确定是否研究显式多效果编码；不必为每张新牌机械新增一维 | Offering自伤/能量/抽牌、Combust伤害/失血分别可解释；变更后重新初始化或明确迁移，不能精确恢复旧架构 |

建议下一步先做直接效果7类和两类手牌单选的机制验收，同时先定C1的数据语义，再进入Headbutt/Warcry/Dual Wield；C2必须在生成/自动打出类开放前关闭。C3应在新敌人与相关卡牌合流前验收。这里没有批准新的长时间PPO训练。

## 6. 核验依据和边界

- 现结构一手依据：`sts/models/unified-entity-contract.json`、`sts/env/entities.py`、`sts/models/entities.py`、当前C++ `cardRow`、`sts/env/ironclad.py`。
- 当前准入：`sts/env/ironclad-expansion-coverage.json`、`sts/env/ironclad-registry.json`；旧机制仲裁证据索引见 `docs/ironclad-input-audit.md`、`docs/ironclad-card-audit.md`。旧报告的69版本是旧public快照，不能作为当前扩展准入数。
- 现有针对性证据：`tests/test_unified_entities.py`、`tests/test_ironclad_dynamics.py`、`tests/test_true_grit_selection.py`；旧798全仓通过是U4历史记录，本审计不将其冒充本轮全仓重跑。
- 运行本次 `scripts/audit-card-token.py` 对拍122维实际编码顺序；针对性复测结果见实施记录。本轮不新增游戏机制，不改变checkpoint指纹绑定的源代码。
