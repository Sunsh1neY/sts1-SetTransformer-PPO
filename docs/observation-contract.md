# 观测与动作接口契约（Week 4 / T1）

本文固定正式 C++ 后端到后续 Python wrapper 的输入边界。权威依据为
`spec-v4.md` §4、D16、D17、D19、D21；后续实现若改变字段、语义或信息边界，
须先更新决策日志。

## 1. 分层边界

数据只沿下面的单向边界流动：

```text
C++ 内部状态
  ↓ 仅选择玩家当前可见信息
规范观测 dict（T2，固定 shape / dtype，并清零无效行）
  ├─→ FlattenWrapper（T3，确定性一维特征）
  └─→ TokenWrapper（T3，确定性的分类型实体特征与 mask）
         ↓
      模型内可训练的类型专用投影 → [n_token, d_model]
```

`seed`、各 RNG 状态或计数、抽牌堆实际顺序和未来随机结果只可进入复现或
调试记录，不得进入规范观测 dict 或任一 wrapper。`info` 不是观测，禁止整体拼接。

## 2. 规范观测 dict

T2 必须从扩展暴露的 `HAND_FEATURES`、`ENEMY_FEATURES`、`PILE_FEATURES`、`GLOBAL_FEATURES`
核对字段顺序，不依赖上游枚举值的大小或自行重排。转换结果必须拥有自己的
NumPy 缓冲区；后续 `step` 不得修改已保存的旧观测。

| key | shape | dtype | `True` / 有效性的含义 |
|---|---:|---|---|
| `hand` | `[10, 3]` | `np.int32` | 行顺序就是当前手牌槽位顺序 |
| `enemies` | `[5, 12]` | `np.int32` | 行顺序就是后端敌人目标顺序 |
| `draw_pile` | `[3]` | `np.int32` | Bash、Defend、Strike 的无序张数 |
| `discard_pile` | `[3]` | `np.int32` | Bash、Defend、Strike 的无序张数 |
| `global` | `[11]` | `np.int32` | 当前时刻的定长公开量 |
| `hand_mask` | `[10]` | `np.bool_` | `True` 表示该手牌行有效 |
| `enemy_mask` | `[5]` | `np.bool_` | `True` 表示该敌人当前可作为实体/目标 |
| `action_mask` | `[31]` | `np.bool_` | `True` 表示环境允许立即执行该动作 |

规范化时必须把 `hand_mask=False` 和 `enemy_mask=False` 对应的整行清零，不能
相信上游残留值。FlattenWrapper 与 TokenWrapper 只能读取这份清零后的同源数据。
死亡敌人和未使用的补齐位置都按无效行处理；原物理行位置仍保留，以免目标编号
错位。

### 2.1 `hand` 字段

| 顺序 | 字段 | 含义 | 类型 | 可见性依据 |
|---:|---|---|---|---|
| 0 | `card_id` | 卡牌语义类别；不是槽位号 | 类别 | D19 必需信息 |
| 1 | `upgraded` | 是否升级，0/1 | 二值类别 | D19 卡牌可见语义；当前 A0 卡组不升级 |
| 2 | `cost` | 本回合当前费用 | 离散数值 | D19 明确要求当前费用 |

`card_id` 的具体整数只用于查表。本次构建中 `104=DEFEND_RED`、
`321=STRIKE_RED`、`25=BASH`；wrapper 不得把这些数值的大小当作连续强弱关系。

### 2.2 `enemies` 字段

| 顺序 | 字段 | 含义 | 类型 | 可见性依据 |
|---:|---|---|---|---|
| 0 | `monster_id` | 敌人语义类别 | 类别 | D19 当前敌人身份 |
| 1 | `hp` | 当前生命 | 离散数值 | D19 双方血量 |
| 2 | `max_hp` | 最大生命 | 离散数值 | D19 双方血量 |
| 3 | `block` | 当前格挡 | 离散数值 | D19 可见状态 |
| 4 | `strength` | 力量层数 | 离散数值 | D19 可见 buff/debuff |
| 5 | `vulnerable` | 易伤持续量 | 离散数值 | D19 可见 buff/debuff |
| 6 | `weak` | 虚弱持续量 | 离散数值 | D19 可见 buff/debuff |
| 7 | `intent` | 当前显示意图的语义类别 | 类别 | D19；不是内部招式 ID |
| 8 | `intent_damage` | 当前显示的单次伤害 | 离散数值 | D19；精确显示口径 `[未核实]` |
| 9 | `intent_hits` | 当前显示的攻击次数 | 离散数值 | D19；精确显示口径 `[未核实]` |
| 10 | `curl_up` | 蜷身状态量 | 离散数值 | D19 可见状态；数值显示口径 `[未核实]` |
| 11 | `ritual` | 仪式状态量 | 离散数值 | D19 可见状态；数值显示口径 `[未核实]` |

当前 `intent` 映射为 `0=NONE, 1=ATTACK, 2=ATTACK_DEFEND,
3=DEFEND_BUFF, 4=BUFF, 5=DEBUFF`。这也是类别查表输入，不能按数值距离解释。

### 2.3 `global` 字段

| 顺序 | 字段 | 含义 | 类型 | 可见性依据 |
|---:|---|---|---|---|
| 0 | `hp` | 玩家当前生命 | 离散数值 | D19 |
| 1 | `max_hp` | 玩家最大生命 | 离散数值 | D19 |
| 2 | `block` | 玩家当前格挡 | 离散数值 | D19 |
| 3 | `energy` | 当前能量 | 离散数值 | D19 |
| 4 | `turn` | 当前战斗回合计数 | 离散数值 | `spec-v4.md` §4.2；显示口径 `[未核实]` |
| 5 | `draw_count` | 抽牌堆张数，不含顺序 | 离散数值 | D19 允许公开堆信息；显示口径 `[未核实]` |
| 6 | `discard_count` | 弃牌堆张数，不含顺序 | 离散数值 | D19 允许公开堆信息；显示口径 `[未核实]` |
| 7 | `total_enemy_hp` | 有效敌人当前生命之和 | 派生数值 | 仅由本观测敌人 HP 派生，不增加隐藏信息 |
| 8 | `strength` | 玩家力量层数 | 离散数值 | D19 |
| 9 | `vulnerable` | 玩家易伤持续量 | 离散数值 | D19 |
| 10 | `weak` | 玩家虚弱持续量 | 离散数值 | D19；不得遗漏 |

## 3. 动作编号与实体位置

动作空间固定为 31，不随敌人物理缓冲的 5 行扩成 51：

```text
0..29: action = hand_slot * 3 + target
30:    end_turn
```

其中 `hand_slot = action // 3`，`target = action % 3`。手牌槽位按后端当前手牌
数组（抽牌顺序）分配；槽位号不写进卡牌 token 特征，但动作头必须保持实体行与
输出编号的对应关系。目标 0、1、2 对应敌人物理行 0、1、2；当前最小切片最多
两个敌人，因此目标 2 恒由环境 mask 为非法。敌人物理行 3、4 没有动作编号。

无目标牌只允许 `target=0`，避免三个编号表达同一个动作。wrapper 不重算
合法性，只携带环境给出的 `action_mask`；终局观测的 31 个动作全部为 `False`，
终局后再次 `step` 必须报错。

## 4. 真实观测样例

来源：提交 `d2ff442` 加当前未提交的 Week 4 计划，训练范围 seed `100000`，
`TWO_LOUSE`，A0；命令见本文末尾。原始 Python 返回的是一维 `list[int]` / 
`list[bool]`，下表按扩展暴露的宽度 reshape，仅省略全零补齐行。

```text
hand [10,3]
slot  card_id  upgraded  cost  valid
0     104      0         1     True    # Defend
1     104      0         1     True    # Defend
2     321      0         1     True    # Strike
3     321      0         1     True    # Strike
4     321      0         1     True    # Strike
5..9  0        0         0     False

enemies [5,12]
target  monster_id hp max_hp block str vuln weak intent dmg hits curl_up ritual valid
0       37         12 12     0     0   0    0    1      6   1    6       0      True
1       23         13 13     0     0   0    0    1      6   1    7       0      True
2..4    0          0  0      0     0   0    0    0      0   0    0       0      False

global [11]
hp max_hp block energy turn draw_count discard_count total_enemy_hp str vuln weak
80 80     0     3      0    5          0             25             0   0    0

draw_pile / discard_pile [3]
字段顺序                    bash_count defend_count strike_count
draw_pile                   1          2            2
discard_pile                0          0            0

action_mask=True 的索引
[0, 3, 6, 7, 9, 10, 12, 13, 30]
```

例如动作 `10 = 3 * 3 + 1` 表示槽位 3 的 Strike 攻击目标 1。动作 `3` 表示
槽位 1 的 Defend 使用规范目标 0；`4`、`5` 虽能算出编号，但必须为非法。
样例中没有 seed 或 RNG 字段；执行一步后的 `info` 可以含复现计数，但仍不得进模型。

复现命令：

```powershell
python -c "import sys; sys.path.insert(0, r'third_party/sts_lightspeed/build'); import slaythespire as s; e=s.IroncladBattleEnv(); o=e.reset(100000,s.MonsterEncounter.TWO_LOUSE,0); print(s.HAND_FEATURES, o.hand, o.hand_mask); print(s.ENEMY_FEATURES, o.enemies, o.enemy_mask); print(s.PILE_FEATURES, o.draw_pile, o.discard_pile); print(s.GLOBAL_FEATURES, getattr(o,'global')); print([i for i,x in enumerate(o.action_mask) if x])"
```

## 5. 后续 Python 接口

T2 已由项目包入口 `from sts import Encounter, LightspeedBattleEnv` 实现。薄适配器
保持简单且不引入 Gym 依赖：

- `reset(seed, encounter, ascension=0) -> observation_dict`
- `step(action) -> (observation_dict, reward, terminated, truncated, info)`
- `observation() -> observation_dict`
- `action_mask() -> np.ndarray[bool]`，内容与当前观测中的同名字段一致

`reward` 为有限 `float`，两个终止标志为 `bool`，`info` 为仅供调试/复现的
新 dict。任务硬超时返回 `terminated=True, truncated=False, info["timeout"]=1`；
普通非终局两者均为 `False`。T3 的两个 wrapper 均包装这份接口，不直接读取
C++ 对象或 `info`。

TokenWrapper 的确定性输出保留卡牌、敌人、两种牌堆和全局分组及实体 mask；它本身
不含可训练参数。类型专用类别 embedding 与数值投影属于模型编码器，并在那里
合并成 `[n_token, d_model]`。这一边界避免固定或随机投影混入数据准备，也保证
同一规范观测可供 MLP 与 Set Transformer 对照。

## 6. 双 wrapper 编码契约（Week 4 / T3）

两条路径共同调用 `sts/env/wrappers.py` 的确定性实体编码。当前最小切片的类别
使用 one-hot，类别顺序固定如下：

| 原字段 | 类别顺序 |
|---|---|
| `card_id` | Bash(25)、Defend(104)、Strike(321) |
| `monster_id` | Cultist(14)、Green Louse(23)、Jaw Worm(28)、Red Louse(37) |
| `intent` | NONE(0)、ATTACK(1)、ATTACK_DEFEND(2)、DEFEND_BUFF(3)、BUFF(4)、DEBUFF(5) |

类别编号只负责查表，不把整数大小输入模型。当前机制范围外的有效类别直接报错，
扩容时必须显式更新类别表和测试。`upgraded` 与其余公开数值原样转为 `float32`；
本周不做缩放，也不使用训练集或固定评估集拟合统计量。以后若增加缩放，须同时
作用于两条路径并更新本文档。

### 6.1 FlattenWrapper

返回 `features: float32[182]` 和单独的 `action_mask: bool[31]`。一维特征布局：

| 切片 | 来源 | shape 展开前 |
|---:|---|---:|
| `[0:50]` | 10 个手牌实体 | `[10, 5]` |
| `[50:150]` | 5 个敌人实体 | `[5, 20]` |
| `[150:161]` | 全局公开量 | `[11]` |
| `[161:164]` | 抽牌堆 Bash / Defend / Strike 计数 | `[3]` |
| `[164:167]` | 弃牌堆 Bash / Defend / Strike 计数 | `[3]` |
| `[167:177]` | 手牌 mask | `[10]` |
| `[177:182]` | 敌人 mask | `[5]` |

动作 mask 不作为状态数值拼入 `features`，而是在动作 logits 上使用；两条模型
路径都以同样方式单独携带它。实体 mask 进入 MLP 特征，使 MLP 与使用 attention
mask 的 Token 路径知道相同的有效实体集合。

### 6.2 TokenWrapper

确定性输出如下；此处尚未产生 `d_model`：

| key | shape | 含义 |
|---|---:|---|
| `hand` | `[10, 5]` | 逐手牌实体特征，保持槽位行顺序 |
| `enemies` | `[5, 20]` | 逐敌人实体特征，保持目标行顺序 |
| `global` | `[1, 11]` | 一个全局 token 的原始数值特征 |
| `draw_pile` | `[1, 3]` | 抽牌堆无序类别计数，位置类型为 draw |
| `discard_pile` | `[1, 3]` | 弃牌堆无序类别计数，位置类型为 discard |
| `hand_mask` | `[10]` | 有效手牌行 |
| `enemy_mask` | `[5]` | 有效敌人行 |
| `token_mask` | `[18]` | 顺序为全局、抽牌堆、弃牌堆、10 个手牌、5 个敌人；前三者恒有效 |
| `action_mask` | `[31]` | 环境给出的合法动作，不由 wrapper 重算 |

卡牌和敌人 token 不含槽位号或目标号；实体行在数组中的位置维护其与动作编号的
对应关系。手牌换位时相应行和动作 mask 的三元块一起换位，全局特征不变；敌人
换位时需要目标的卡牌对应目标列换位。无目标牌的 `target=0` 是规范占位，不代表
敌人 0，因此敌人换位时它仍保持 `target=0`。

本阶段只验证数据转换的换位关系、清零和隐藏信息隔离。动作概率的等变性及价值
不变性必须等模型实现后再验收，不能由 wrapper 测试代替。

## 7. 动作 mask 闭环（Week 4 / T4）

正式 `MaskedRandomAgent` 只读取当前 wrapper 观测里的 `action_mask`。它以 31 个
全零 logits 调用 `masked_softmax`，形成合法动作上的均匀 `probabilities[31]`，
再由 Agent 自己的独立 RNG 抽样，返回原动作编号 `action: int`。概率是抽样前
策略，整数是抽样后这一次的动作，不能混称。one-hot 与整数携带相同的单次离散
动作信息，接口不传冗余 one-hot。策略不调用 `legal_actions`，也不根据能量、
卡牌或敌人字段重算合法性。

`masked_softmax(logits, action_mask)` 的顺序固定为：先排除非法 logit，再只在合法
集合上做数值稳定的 softmax。输出中非法项精确为 0，合法项之和为 1；只有一个
合法动作时该项为 1。非终局全 `False` 无法形成动作分布，显式报错。

通用 `run_episode` 接入层只调用 Agent、校验并把整数原样交给 `env.step`；它
没有 RNG，也不读取游戏字段或重新判断合法性。环境返回
`terminated/truncated` 后，接入层立即停止且不再调用 Agent。终局全 `False` 是
正常环境观测，不虚构结束回合动作。这样随机、规则和未来模型 Agent 都能替换，
而环境及两种 wrapper 无需随 Agent 类型改变。

后续策略计算 log-prob、熵和梯度时，必须使用这个同一的掩码后分布；本周只用
NumPy 验证概率数值，自动微分留到引入 PyTorch 的模型阶段。

可复现闭环样例：环境 seed `100000`、策略 seed `20260905`、`TWO_LOUSE`、A0。
FlattenWrapper 与 TokenWrapper 实际交给后端的动作均为
`[9, 30, 13, 3, 1, 30, 4, 7, 30, 12, 3]`，11 步自然终局，累计奖励
`1.381250023841858`，`terminated=True`、`truncated=False`。逐步测试保存了提交动作前的
环境 mask，并确认每个动作对应项都为 `True`；终局 mask 全 `False`。
