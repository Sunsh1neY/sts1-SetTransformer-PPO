# M4 公开战斗后端遭遇诊断

日期：2026-09-12。本文区分新增后端工程机制诊断和真实公开场景覆盖；没有把替换遭遇的夹具加入真实manifest。

## 范围与实际第一轮结果

`scripts/diagnose-public-encounters.py` 从内容准入场景取一份完整candidate，保留牌组、HP、遗物与药水库存，显式替换遭遇/进阶并记录 `mechanism-diagnostic`。所有精英显式 `burning_elite=false`。A0额外追加规则所需第三空药水槽，保留来源已有库存；这是诊断覆盖，不是A0历史玩家初态。

第一轮随机诊断包含14种普通遭遇和3种精英，各A0/A20、seed710000。初始A0夹具因只有2药水槽被后端正确拒绝，17失败；修正诊断夹具显式第三空槽后，40项测试通过、规则重放1项暂未执行。失败及修正没有被归因于游戏规则或通过删除真实内容解决。

已实际观察：

- `LOTS_OF_SLIMES` 5个可寻址目标；66动作mask与目标容量一致。
- `LARGE_SLIME` seed710000的大型尖刺史莱姆从1个目标分裂到2个；A0继续打死一个，死槽保留且不可寻址，随后自然胜利。A20同seed也经历分裂。
- 所有轨迹检查五行敌人、公开意图与伤害/次数、死槽和未出现目标不能被针对；策略仅读取规范观测和合法mask。
- 外部 `max_actions=1` 用结束回合触发 `truncated=true,terminated=false,reward=0`，终局后继续step明确拒绝。自然胜利/死亡使用terminated，二者不同时为真。
- 精英缺少燃烧标志、true或非bool被拒绝，不默认为普通精英。

第一轮随机trace保留 `reference/public-encounter-diagnostics/random-first.json`。同seed重放仅验证确定性，不增加独立样本数。

## 实际发现并定点修复的Red Slaver缺陷

普通短局很早结束，未暴露重复Entangle。按主审授权另设高HP诊断夹具（HP/maxHP=30000，只为延长观测，不改怪物参数），连续结束回合30次。

修复前A20、seed710000在turn10/14/18/22/27多次新出现Entangled=1，中间turn11/15/19/23已清除；seed710001也重复。这证明不是同一次状态持续显示。原公开trace保留于 `reference/public-encounter-diagnostics/red-slaver-end-turn.json`，不能覆盖该修复前证据。

按D13只核查本地正版JAR类 `com.megacrit.cardcrawl.monsters.exordium.SlaverRed`，使用javap输出保存在 `reference/public-encounter-diagnostics/slaver-red-javap.txt`；未复制反编译实现。

本轮重新计算正版JAR SHA256：`CFAD868AC8D65A88E71A0BF096FB09F78811E553EFFE0787C5309A655E081673`，与既有锁定值一致。

| 编号 | 正版字节码证据 | 后端对应修复 |
|---|---|---|
| M4E-01，可信度A，2026-09-12 | `takeTurn` 偏移169–171：设置usedEntangle=true；`getMove` 偏移32–35：已用时跳过Entangle分支 | `MonsterSpecific.cpp` 的 `RED_SLAVER_ENTANGLE` 执行分支加入miscInfo=1，后续原有选招使用该字段 |
| M4E-02，可信度A，2026-09-12 | `getMove` 偏移51为bipush55，53为if_icmplt94；此前还有usedEntangle与非连续两次Stab条件 | 同文件RedSlaver的已缠绕后Stab阈值由50改55；边界含义为roll54不进入该分支、55可进入（其余条件满足时） |

只修改上述两个相关hunk，不更改旧minimal-v1三遭遇数值。新版测试追加两个seed各30轮的Entangle只使用一次回归；阈值具体54/55边界目前由正版字节码与对应源码定点对照证明，没有把普通轨迹采样冒充阈值穷举测试。

另增加Cultist A0/A20的精确观察断言：开场Ritual后首次不增力量、下一轮Strength分别3/5、公开下一击伤害分别9/11，用于核查适配器的Strength导出修复。

## 验收边界

主线程统一重建后的本轮最终验证：

- `python -m pytest -q tests/test_public_encounters.py`：46项通过、0失败、0跳过。
- `python -X utf8 scripts/diagnose-public-encounters.py`：136诊断通过、0异常。范围为17遭遇×A0/A20×随机/规则×seed710000/710001，各组合实际执行一次；测试中的固定seed重复只作回归，不增加样本数。
- 136场全部自然终止，无预算截断，其中76场奖励大于0；此混合机制夹具计数不是正式胜率估计、不是规则优于随机结论，也不是Gate证据。外部截断由独立1动作预算测试验证。
- 修复后RedSlaver30轮公开trace分别只出现一次缠绕意图：seed710000在turn9，710001在turn1。保存为 `reference/public-encounter-diagnostics/red-slaver-after-fix.json`，修复前文件保留。
- Cultist A0/A20 Ritual跳增、Strength及预告伤害一致回归通过，验证了新适配器Strength导出修复。
- 二进制SHA256：`4e61df0bae90cc8899f5e18b0cb2acc8e5d32f9ec650e4e51d592ce61fe8b48b`。完整诊断的contract、script、backend哈希与公开轨迹保存在 `reference/public-encounter-diagnostics/diagnosis.json`。

未运行训练，未由本子任务执行全仓回归或提交推送。M4的17类遭遇接口工程诊断已完成上述明确范围，是否将整体里程碑收口由主审结合真实数据覆盖与剩余机制证据裁定。

M4不能只靠这些机制夹具宣布真实分布完成：当前99场真实内容准入候选只有6类普通遭遇、没有真实精英初态；燃烧精英来源信息仍是缺口。14普通/3精英工程覆盖与真实初态来源覆盖必须分别报告。
