# M2 人工场景诊断契约（正式分布方案已撤销）

日期：2026-09-11。状态：按用户要求，以下人工牌组仅保留机制诊断用途，不再作为正式训练/评估初态分布。正式路线改为公开玩家对局初态，见 decisions.md 的“M2 训练初态改用公开玩家对局来源”。下列15张容量证明也不适用于真实场景池。依据：spec-v6 §4.3.1、D25/D26、M1 候选收口。

## 1. 范围与固定配置

首批配置标识 `medium-b1-v1`，采用 M1 批次 0+1 的 14 类卡，全部基础版；升级版留待单独配置与验收。不使用药水，不增加新遗物，其他初始参数沿用已锁定 minimal-v1。正式运行前须将继承参数值展开写入配置与运行清单，不允许依赖隐式默认值。

每套牌组共 15 张：共同底座为 Strike×5、Defend×4、Bash×1，分别加入下表五张牌，每张一份。

| 牌组标识 | 新增五张牌 | 诊断目的 |
|---|---|---|
| direct | Bludgeon、Cleave、Clothesline、Twin Strike、Uppercut | 单体、多段、全体与减益 |
| strength | Heavy Blade、Spot Weakness、Inflame、Thunderclap、Cleave | 力量与敌方攻击意图 |
| block | Body Slam、Entrench、Inflame、Thunderclap、Twin Strike | 格挡利用与出牌顺序 |

新增并集恰为 M1 第一批的 11 类，连同基础牌共 14 类。这里的配置是实现目标，当前 reset 尚不能执行它们。

遭遇固定 `jaw-worm`、`cultist`、`two-louse`，沿用 A0；本批不增加分裂或召唤敌人。三个牌组与三个遭遇形成九个诊断桶。环境 seed 与牌组/遭遇配置分开记录，不将配置编号当作 seed 输入模型。正式 eval_seeds.json 保持不变；正式评估与开发诊断沿用各自范围，不混用。

## 2. 容量证明

| 契约项 | 首批目标值 | 理由 |
|---|---:|---|
| 手牌槽位 | 10 | 沿用后端手牌上限 |
| 敌人观测行 | 5 | 沿用现有物理行布局 |
| 可寻址敌方目标 | 3 | 保持当前动作协议；本批遭遇最多两个敌人且无生成敌人 |
| 非手牌实体总容量 | 15 | draw+discard+exhaust 的合计上界 |
| 模型卡牌行容量 | 25 | 手牌固定10行 + 非手牌15行，不表示实际存在25张牌 |
| 动作数 | 31 | 10×3+结束回合 |

本批每局初始15张，所选卡与遭遇无生成牌/复制路径，能力牌打出只会减少四区卡牌总量，移动、弃牌和洗牌不增加总量。因此任意决策时刻 hand+draw+discard+exhaust≤15，非手牌合计≤15。该证明只覆盖上述配置，不能外推到 M1 生成牌批次或新遭遇。

配置不在允许范围、未知卡牌、超容量、越界目标均明确拒绝，不截断、不映射到占位卡，不自动代替玩家选牌。旧 minimal-v1 保留原非手牌容量10及原schema，不能用新shape回填旧运行。

## 3. 首批观测字段与模型输入

保留现有公开语义和顺序：

- 卡牌：`card_id, location, upgraded, cost, cost_known, target_kind`。后端原始 backend_card_id 经注册表转换，不作为连续数值输入。
- 敌人：`monster_id, hp, max_hp, block, strength, vulnerable, weak, intent, intent_damage, intent_hits, curl_up, ritual`。
- 全局：`hp, max_hp, block, energy, turn, hand_count, draw_count, discard_count, exhaust_count, total_enemy_hp, strength, vulnerable, weak`。
- 模型卡牌类别列：`card_id, location, target_kind, upgraded`；数值列：`cost`，另带known与valid mask。敌人编码仍为现有20列，全局13列。

首批无需为了 Inflame 新增同名活动状态；当前 Strength 已表达其结果。card type、固定基础数值可由注册表确定，不强制重复输入。Artifact 等仅在新增可达遭遇/机制需要时引入；本批不将未支持状态默认为0来开放其他配置。

非手牌仍按现有契约消除隐藏牌序；seed、RNG、未来结果不进观测。两个 wrapper 必须从同一规范观测派生。按当前布局推导新 FlatInput 长度为25×(4+1+1+1)+5×20+5+13=293；动作mask单独31位。以配置派生shape并校验，禁止另散落硬编码293。

## 4. 注册与版本迁移要求

新配置标识 `medium-b1-v1`；输入schema、注册表版本与哈希必须区别于 minimal-v1。现有三类语义ID保持稳定，其余11类采用附加分配；正式ID表随配置实现一次生成、固定并存哈希，不依赖枚举扫描顺序。

动作语义保持原31位；序列化、checkpoint与轨迹须包含配置标识、schema/registry版本、容量与字段哈希。新旧输入尺寸不兼容时明确拒绝恢复；不补零伪装精确续训。奖励仍为 battle_reward_v1、gamma=1、alpha=0.5、beta=0。

## 5. 实施顺序与验收

1. 将配置、容量、字段顺序和版本汇入一个可校验的契约源；C++与Python读取同一声明或其生成产物，避免维护两套独立真相。
2. 接入显式牌组reset、14类注册和15张非手牌容量；这是后续实现工作，本文没有声称已经可用。
3. 验证非法配置拒绝、牌组精确组成、14类目标与mask、九个桶的计数/shape、两wrapper同源，以及旧checkpoint兼容拒绝。对力量、多段、减益和格挡组合执行有意义的机制测试。
4. 旧 minimal-v1 回归通过后，按D25为该批单独预登记固定预算从头短训，分别报告九桶；不把开发诊断当Gate 2/3。

## 6. 后续M2范围

批次2的抽牌/消耗，批次3的NoDraw、临时力量回收与持续能力，批次4的生成牌，各自需要明确牌组和可达状态/容量证明。尚未定义的批次不继承首批容量上界。完整中等档遭遇目标仍按M4推进，当前三个遭遇只是首批隔离机制影响的设计。
