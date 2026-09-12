# M5 公开观测规则策略实施报告

日期：2026-09-12。当前结果：规则策略与独立66动作执行层已实现，27项独占测试通过；
99场派生公开场景完成真实后端集成。此报告不声明 M2/M3/M4 通过，也不声明 Gate 2。

## 实现

- `sts/agents/rule_agent.py`：`RuleAgent.decide` 只读规范观测，返回现有
  `AgentDecision` 的66位 one-hot；`score_public_actions` 提供可检查的逐动作分数。
- `sts/agents/public_runner.py`：独立 `PublicRandomAgent`、决定校验和执行循环，
  不修改旧31动作 runner；保留环境真正的 terminated/truncated、最终观测和 info。
- 两个新测试文件：`tests/test_rule_agent.py`、`tests/test_public_runner.py`。

协议为 `schema='public-observation-v1'`，10手牌×5目标、结束回合50、3药水×5目标，
共66动作。合法性只来自环境 mask；遇到矛盾的目标映射、空槽合法动作、未知协议或
未知卡/遗物/药水，明确拒绝整个输入。策略不通过屏蔽某些未知动作继续运行。

手牌 `damage_by_target` 是已经应用公开状态修正的每段伤害，策略不会再加力量或
乘易伤；`block` 同样按已修正预览解释。敌人意图用已修正每段伤害乘段数。
允许不可打状态牌的负费用哨兵，但这种牌必须没有合法打出动作。

类别覆盖明确固定于 M1 的35卡、5辅助状态/诅咒、中央契约中的8遗物及主审给出的
direct15药水。True Grit 升级版拒绝。类名规范化只去空格、标点并转小写；不借模糊
匹配接受未登记名称。公开状态映射中未出现的名称表示该状态不存在；缺整个映射拒绝。

## 评分及局限

规则以有效HP伤害、击杀价值与移除当前敌意图、有限有效格挡为主，再加抽牌、能量、
短期增益价值，扣费用、反伤和生成状态牌等机会成本。状态/能力卡按显式机制分支
估值。平分选最小动作编号，保证同一规范观测稳定复现。随机基线用独立 NumPy RNG。

这是一阶启发式，不进行后端试走或完整时序模拟。多段攻击遇 Curl Up 时不计“确定
击杀”额外价值；其他复杂防护、抽牌后的实际用牌、能力长期收益仍是近似，不能以
当前规则分数证明动作最优。未知机制的拒绝与“已知机制的近似估值”明确分开。

八种遗物只涉及已登记开场/出口/反伤效果；开场增益已在观测中体现，策略无需再加
一次。药水包括 Weak/Regen/EssenceOfSteel/Explosive/Ancient/Fear/LiquidBronze/
Energy/Speed/Dexterity/HeartOfIron/FruitJuice/Block/Strength/Swift，未增加 Fire、
Blood 等不在本批的药水。

## 本轮实际验证

命令：`python -m pytest -q tests/test_rule_agent.py tests/test_public_runner.py`。

结果：27项通过。包括：

- 纯字典决策和输入不变、概率合法、只有结束动作；
- 确定击杀、格挡足够时结束、不重复伤害修正、多敌多段意图；
- Dropkick与NoDraw、随机消耗不读取抽牌顺序、手牌置换的动作对应；
- 负费用状态牌、未知协议/字段/实体、药水空槽、direct15全部有分支；
- 禁止env/info/seed/RNG访问；独立随机流；终止与截断的最终观测保留；
- 非法分布及旧31位输出拒绝。
- 中央8种遗物（含新增Anchor/Vajra/OddlySmoothStone）的不适用计数为null时合法。

## 真实后端集成

独立执行 `load_scene_manifest` 接受的全部99场，每场规则策略一个完整rollout，环境
seed为`910000 + 场景索引`，使用`PublicBattleEnv`默认512外部动作预算。

| 实际指标 | 数值 |
|---|---:|
| 场景数 | 99 |
| 正常终止 | 99 |
| 外部截断 | 0 |
| 异常/非法动作 | 0 |
| 动作总数 | 914 |
| 获胜数 | 99 |
| 平均综合回报 | 1.4133867244603868 |

这批简单普通战斗的100%胜利不代表精英表现、总体泛化或相对随机显著占优。
主审最终追加同场景/同环境seed随机对照：随机72胜、规则99胜，各99场无异常；这只是开发集成，没有正式CI、从头PPO短训或1000种子Gate评估。

逐场结果为ignored文件`reference/public-scene-integration.json`，结果文件SHA256：
`4a767227cca7b2d61606d6559b0b244cd066c5211fb1bcd37767d3ef6a167166`。
本轮manifest SHA256：`fdc06a7c786a27d10505d4cb6e95ffa0bfda1cf27dbcf9bcc33f202ce575f437`。
本轮实际扩展SHA256：`4e61df0bae90cc8899f5e18b0cb2acc8e5d32f9ec650e4e51d592ce61fe8b48b`。
输入包括scene_id和独立环境seed，仅在结果文件中记录，不进入策略观测。

真实集成首次遇到`counter=null`拒绝后已修复；无适用计数的遗物可以为null，非null
仍须有限数值。遗物名单、schema、动作数、结束动作改从中央契约JSON读取；布局
若不再是当前66/50/5则显式拒绝，防止静默漂移。

主审仍应完成新环境每种批准机制、每个遭遇的开发smoke，并记录未覆盖分支。
本轮成功集成不替代 M3/M4 机制验收、M6评估或M8 Gate。

主审最终验收：SeeingRed/RedSlaver/公开状态修复后，卡牌93项、药水遗物28项、遭遇46项与136机制诊断均通过；全仓566项通过。M5在当前支持范围的工程首验通过，M3张量/训练迁移、M6–M8和用户独立理解仍未完成。完整最新状态见 `docs/public-battle-implementation.md`。
