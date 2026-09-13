# 敌人/药水公开实体接口交接

状态：`enemy-potion-entities-v2`（观测v3） 为机制分支交接样例；统一编码器、动态batch补齐、模型及候选头由全卡任务负责。本分支不建立另一套模型。入口为 `EnemyPotionEntityView.reset()/update()`。

| 实体 | 可进入token的features | 仅路由字段 |
|---|---|---|
| 敌人 | name、hp、max_hp、block、intent_kind、intent_damage、intent_hits、statuses、public_history、intent_history、intent_history_valid | reference、target列、revision |
| 药水 | name、potency、potency_unit、target_kind、activation | reference、药水槽、normal动作号、revision |

每条记录带entity_type，交由共享编码器建立类型信息与同宽投影。引用文本内含的数字不编码进token。玩家HP/maxHP、能量、回合和状态由主集成放入单个玩家/全局token；这让血药百分比效果与玩家状态通过共同注意力关联。卡牌和遗物token仍由共享任务提供。

敌人intent_history直接复用扩为三格的后端moveHistory编号，按当前/前次设置/再前次设置排序，编号作为类别而非连续数值。setMove向后移位，直接覆盖当前意图保留尾部，因此不是三次实际执行记录。public_history保留已完成回合、睡眠和蓄力观察计数，移除重复的两次意图类型。逐怪编号公开性审计按用户决定暂缓，不宣称全部编号已审核。守护者Mode Shift/Sharp Hide作为当前公开状态导出；六火亡魂当前攻击次数/每击伤害明确导出。没有输出seed、RNG、牌序、隐藏实例号或miscInfo；内部招式编号可能比意图类别更具体，该差异仍待逐怪审计。

有效实体输出变长列表；不存在的药水和第一幕已死亡/逃跑的敌人不占有效token。批次padding只能由共享编码器新增，并产生validity mask。本分支没有64张模型容量，也没有固定长度敌人/药水大向量。

动作路由保留后端5目标列与3预留药水槽，66位normal mask是环境动作协议，不是模型行数。`resolve_potion()`通过source/target引用和revision恢复合法动作，因此实体集合重排不改变目标。药水消耗、敌人分裂替换、reset会使旧引用失效。卡牌目标头可使用`enemy_target_references`将共享卡牌候选与敌人引用连接；卡牌源引用由全卡接口定义。

样例 `enemy-potion-entity-example.json` 来自真实后端两虱虫＋火药水，包含消耗前后实体与路由。测试包含重排后命中同一敌人、药水消耗、仙灵被动复活、史莱姆父实体分裂、reset和隐藏字段拒绝。

边界和共享依赖：

- 当前活动实体规则适用于第一幕及已准入13个第二/三幕遭遇。其余幕同种召唤替换、Darkling复活、Awakened One第二阶段必须有显式公开生命周期及稳定引用事件，不能凭名字匹配直接准入。本视图尚不支持它们。
- Entropic Brew同槽同名再生成需后端生命周期事件，当前无法用两个决策点名称变化完整判别，因此保持拒绝。
- 选牌药水必须复用共享选择阶段、候选reference和多选确认；NORMAL外的阶段当前抛错，不自动代选。
- 统一Set编码需要接入上述statuses/history、药水potency_unit/activation；未做模型输入、梯度或checkpoint验收。
- 药水有效potency仅覆盖当前无Sacred Bark的八遗物白名单。未来效果修饰必须重新核验，不能只复用静态20/30等常量。


第二/三幕续批：独立输入schema现为enemy-potion-observation-v2，新增13种无召唤/复活遭遇适用当前实体视图。新增STRONG_DEBUFF、STUN、ATTACK_BUFF意图及护甲/适应性/回合增力/壁垒、Hex布尔导出。其余22个遭遇等待用户审核，详见act23-enemy-review.md；旧示例和首批说明保留其原验证范围。

更新时点注意：邪教徒等固定行动使用NoOpRollMove时不移动数组，不能将三个位置解释成连续三个回合。当前专项及相关回归317通过；新版真实样例见enemy-intent-example-v3.json。
