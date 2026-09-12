# Ironclad 全卡审计复核

状态更新：原报告现已按本文件修订，正版字节码也已定点核查；原十张数值定位补充见 `m1-numeric-evidence.md`，最新裁定与来源见原报告 §10。以下保留首次复核时的问题描述作为修改缘由；Ghostly Armor、Whirlwind 的疑问已在 §10 收口，其他运行时验收仍待完成。候选分批建议见 `m1-candidate-batches.md`。

复核日期：2026-09-11。对象：`docs/ironclad-card-audit.md`。本轮为关键静态证据抽查，不是全卡行为验收；没有重跑原报告所述 89 项测试，也没有重新核验全部正版 class 数值。原报告保留供对照。

## 结论

原报告及补充材料可以作为 M1 候选目录、问题线索和来源证据，仍不能作为正式白名单或后端修复依据。行为与接口验收不因 M1 收口而完成。

## 必须修订的结论

1. **Heavy Blade 倍率误报。** `third_party/sts_lightspeed/src/combat/BattleContext.cpp:1054` 分支先加入基础版 2 倍、升级版 4 倍力量，随后调用 `calculateCardDamage`；该函数在同文件 `:2671` 起的实现还会加入一次力量。因此该调用链合计为 3/5 倍，与报告列出的正版目标一致。不能据此修后端为局部 3/5 倍，否则会重复增加力量。这里只撤销该静态缺陷结论，不宣称全行为已通过。

2. **Whirlwind 的 X 选择要求缺少证据。** 上游 `third_party/sts_lightspeed/src/sim/search/Action.cpp:433` 创建 `CardQueueItem` 时传入当前 `bc.player.energy`；`BattleContext.cpp:1178` 起使用 `energyOnUse`。内部保存 X 数值不能证明玩家需要额外选择 X。必须核验正版 use/action 与 binding 的能量传递、零能量合法性、免费出牌，再裁定是否迁移动作协议；目前不能以“缺 X 输出”确定归 C。

3. **Ghostly Armor 升级语义与所引后端不一致。** `third_party/sts_lightspeed/include/constants/Cards.h:466` 起的 `isCardEthereal` 对该卡无条件返回 true，并没有升级移除 Ethereal 的分支。原报告却写升级后非 Ethereal 且未列冲突。需要重新核查正版 upgrade 方法，修正语义或显式登记差异。

4. **Infernal Blade 漏掉生成卡的动作依赖。** `third_party/sts_lightspeed/src/combat/Actions.cpp:571` 起按攻击类型随机生成；`third_party/sts_lightspeed/include/constants/CardPools.h:152` 的攻击候选含 Headbutt，而原报告也已判 Headbutt 需要弃牌堆选择。不能仅补全部类别注册和容量就认为无动作阻塞。须证明实际生成池及所有可达效果均获支持；缩减生成池属于规则变化，不能静默实施。

5. **Inflame 的新增活动状态要求没有被证明。** `BattleContext.cpp:1559` 起直接增加 Strength，当前输入已有 Strength。不能仅因卡牌类型是 Power，就要求再增加同名活动层。应检查是否存在影响未来转移、而当前字段不能区分的状态，再决定新增字段。card type 等可由固定 card_id 推出的静态属性，也应区分便利特征与必需信息。

6. **覆盖表存在文字自相矛盾。** 原报告 §4.2 同时写 reset 已含 Strike/Defend/Bash 和“75 类都不能从当前正式 reset 进入训练”。后一句应改为“尚不能任意配置全部 75 类；当前只有三类基础牌进入固定 reset”。

## 仍值得保留的风险线索

- Disarm 分支确实固定传入 -2（`BattleContext.cpp:1281`），报告所列升级差异仍需正版证据与定点行为测试收口。
- Iron Wave 确实嵌套调用两次 `calculateCardBlock`（`:1075`），值得针对 Dexterity/Frail 场景验证；不能将尚未运行的验证写成实际对拍结果。
- 二次选牌、动态卡牌属性、持久状态、生成牌容量等审计方向有用，但每项依赖应绑定实际白名单和可达场景，不应无条件扩大实现范围。

## 下一步

先修订上述条目并补正版方法定位和关键调用链证据，再重算分类；随后锁定目标候选及机制批次，按决策日志流程进入 M2 容量与配置契约。当前不修改后端、不扩正式白名单、不启动训练。

## M1 收口补记（2026-09-11）

- M1 已收口为候选方案阶段：75 类/150 版本全卡审计、A6/B123/C16/D5 分类、35 类候选批次以及原十张正版数值定位均已形成材料。
- “收口”不等于“开放”：正式 reset、registry、白名单、扩展卡基础/升级行为测试和 M2 契约均未完成。
- 后续执行点是 M2 的固定牌组、容量、观测和版本契约；其具体值尚未在本文件中锁定。
