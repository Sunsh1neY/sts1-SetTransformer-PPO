# 当前敌人token字段说明（观测v3 / 实体v2）

这里是机制分支交付给共享编码器的语义记录，尚未接入共享Transformer训练。全卡任务负责类别embedding、数值归一化、同宽投影和动态补齐。

| 字段 | 当前实际含义 |
|---|---|
| entity_type | 敌人类型标识 |
| name | 敌人身份，分类编码 |
| hp / max_hp / block | 当前血量、最大血量、当前格挡 |
| intent_kind | 当前公开意图类别 |
| intent_damage / intent_hits | 当前预览每段伤害与段数；格挡另列，不是最终掉血预测 |
| statuses | 当前已导出的公开状态键值，布尔状态为1 |
| intent_history[3] | 当前、前次设置、再前次设置的后端招式编号，分类编码 |
| intent_history_valid[3] | 编号位置有效性；不是敌人实体的padding mask |
| public_history.completed_enemy_turns | 已观察完成的敌方回合计数，原有字段，本次保留 |
| public_history.sleep_turns_observed | 乐加维林已观察睡眠回合计数，原有字段，本次保留 |
| public_history.charge_turns_observed | 地精巫师已观察蓄力计数，原有字段，本次保留 |

回合数/进阶等级属于玩家与全局token，不重复为巨口计算成长量。reference、目标槽、revision只供动作路由。无效/死亡实体当前不进入实体列表；复活怪物仍需生命周期接口，不因本次历史接口自动准入。

## 特殊状态针对哪些敌人

| 状态字段 | 当前用途与对应敌人 |
|---|---|
| Angry | 愤怒地精，受到攻击后的增力机制 |
| Curl Up | 红/绿虱虫，蜷缩可获得的格挡 |
| Enrage | 地精大块头，玩家使用技能触发增力 |
| Ritual | 邪教徒，仪式的回合增力层数 |
| Spore Cloud | 真菌兽，死亡孢子云效果 |
| Thievery | 抢劫者，偷金币额度；不代表完整跨战斗经济接口 |
| Mode Shift | 守护者，模式转换的剩余伤害计数 |
| Sharp Hide | 守护者，防御模式的攻击反伤 |
| Asleep / Metallicize | 乐加维林，睡眠状态与金属化层数；金属化也用于其它获得该状态的敌人 |
| Plated Armor | 带壳寄生怪，当前多层护甲层数及破甲交互 |
| Malleable | 蛇花，当前适应性格挡量 |
| Generic Strength Up | 圆球行者，每回合增力数值 |
| Barricade | 圆球守护者，保留格挡状态 |
| Artifact | 哨卫、圆球守护者等，当前人工制品层数 |
| Strength / Weak / Vulnerable | 通用力量、虚弱、易伤；不是逐怪专属字段 |
| Regen | 导出器已有通用再生支持；复活Boss未准入，不能视为其机制已完成 |

这些状态放在同一个statuses容器中，不是每种敌人各加一个顶层输入列。共享编码器需要为状态建立统一词表。

## 已确认但尚未落地的字段

- 通用phase字段尚未实现。守护者目前通过Mode Shift/Sharp Hide表达公开模式；未来已公开且不可由当前状态恢复的阶段需要逐怪补充。
- 异鸟尚未准入，Flight字段尚未导出；本次不添加额外伤害减免倍率。
- 两种旧历史类别字段已由三位置编号替代；既有睡眠/蓄力计数暂保留，并未完成“所有计数是否冗余”的移除审查。

## 历史边界与共享依赖

后端数组从两格扩到三格；选招代码仍读取原前两格，第三格只作观测。史莱姆受伤切换分裂会直接覆盖当前格而不移动历史，保留后端原语义。三大颚虫初始化写入DARKLING_REGROW作为选招占位，该记录不是实际意图，独立导出将该占位归零并mask。除此之外不开展逐怪编号映射审计。原始编号的公开性尚未完整核验。

词表与后端源文件SHA记录见enemy-intent-vocabulary.json。共享任务需要接收观测v3/实体v2、三个有位置区别的类别embedding、历史有效性mask及状态词表；不能直接用旧checkpoint宣称兼容。

更新时点注意：邪教徒等固定行动使用NoOpRollMove时不移动数组，不能将三个位置解释成连续三个回合。当前专项及相关回归317通过；新版真实样例见enemy-intent-example-v3.json。
