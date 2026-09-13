# E1 动态实例与状态实战探针

核验日期：2026-09-12。范围：五类牌的基础/升级、当前限定遭遇与旧内容关联；不是任意复制/选牌链或所有正版组合的等价证明。

## 一手依据与实现定位

- [S1] 高，既有正版静态核验：`docs/ironclad-card-audit.md` 对应五行及 `docs/ironclad-input-audit.md`。本轮重新校验正版JAR SHA-256为 `cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673`，与既有审计一致；未重跑正版进程或重新反编译全部卡牌。
- [S2] 高，当前实现：`third_party/sts_lightspeed/src/combat/BattleContext.cpp` 的具名卡牌分支、`CardInstance.cpp::tookDamage/updateCost`、`CardManager.cpp::onBuffCorruption/resetAttributesAtEndOfTurn`、`Player.cpp::applyEndOfTurnPowers`。后端一手源码证明实现行为，不单独证明正版一致。
- [S3] 本轮实际执行：`tests/test_ironclad_dynamics.py`，通过真实reset、合法出牌、结束回合、药水动作触发，不向玩家或卡实例注入隐藏字段。

| 卡牌 | 具名信息与实际断言 | 后续未关闭组合 |
|---|---|---|
| Rampage / +1 | 基础伤害8、每次该实例增长5/8；另一张同名牌不增长；移入弃牌并重抽后保留；Strength只修饰预览，不覆盖实例增伤 | Double Tap重放、复制实例及更长生成链 |
| Blood for Blood / +1 | 印刷费4/3、伤害18/22；一次Burn失2HP仅降1费；多个独立失血事件逐次降费并在0停止；非手牌战斗修改费保留 | Armaments升级时保留折扣、Dual Wield复制费用、临时免费跨区记忆 |
| Barricade / +1 | 费用3/2；布尔状态导出不查不存在的statusMap项；普通格挡和Metallicize回合末格挡均保留至下回合 | 更复杂Juggernaut/多次格挡链 |
| Corruption / +1 | 费用3/2；技能当下有效费0并耗尽；Sentinel与Feel No Pain耗尽触发正确；下一回合重抽技能继续免费 | Dark Embrace、Exhume及自动播放链 |
| Combust / +1 | 每层5/7伤害与1失血分别累加；两层失2HP；对敌伤害先过已有格挡；合并失血动作令Blood for Blood降费一次 | Rupture及无敌人/玩家死亡更复杂队列、复制Power后的数值界 |

## 费用语义纠正

原public字段`base_cost`承载的是`CardInstance.cost`，即战斗修改后的费用。首轮探针误把它当印刷费，导致Corruption两版本测试失败。源码确认`onBuffCorruption`对四区技能执行战斗费用修改；没有为迎合错误预期修改后端规则。

扩展新增`printed_cost`；`effective_cost`仅在手牌由当下规则计算，必须结合`effective_cost_known`和`cost_kind`解释。`cost_scope`区分COMBAT、TURN、POWER、ONCE及UNKNOWN。非手牌当下有效费仍未知，不用数值0伪造免费；其公开战斗费仍在`base_cost`中。尚未核验的跨区临时费用记忆继续留待选牌/生成阶段，不因此宣布R02关闭。

## 版本及容量

独立`ironclad-registry-v1`包含原40项目条目及五个新条目；40类缺失牌统一按名称排序预留ID，已实现条目使用对应固定ID，未实现内容仍拒绝。C++编译时嵌入注册表和扩展契约hash；Python实例化检查hash，避免新输入误接旧二进制。

观测升级为`ironclad-observation-v2`，Set编码升级为`ironclad-set-encoding-v2`。基础逐牌编码单独使用扩展注册表，复用旧Set的QKV实现；不再用旧卡表验证新增牌，也不把新增牌伪装成旧ID。原比较模型和训练文件不改。

五类探针不生成卡，也不新增复制/回收/选牌路径，现有每动作15生成ID上界仍适用这个有限内容集合。512动作限制使单张Rampage增伤最多4096；初始96张限制不可回收Power的Combust失血计数最多96。该论证不覆盖后续Havoc、Double Tap、Exhume等。Set目前64位置超过即拒绝，正常容量采集截断在下一小步实现；当前不批准正式扩展训练。
