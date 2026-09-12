> 最终收尾版本：模型unified-entity-set-v4，接口v4，CARD115；公开上下文同时进入动作头和价值头。下文F1–F5测试数字属于该阶段历史，最终复核见文末及card-token-final-review.md。

# 全卡 token 与结算接口修复报告

日期：2026-09-13

工作区：`C:\Users\19091\Desktop\sts2-full-card`
分支：`codex/ironclad-full-expansion`
范围：第一幕 A20、JAW_WORM / EXORDIUM_THUGS / GREMLIN_NOB / LAGAVULIN / THREE_SENTRIES、当前8类遗物/15类药水、75类 Ironclad 的150个基础/升级版本及5张辅助牌。正式训练、完整run、新敌人/新药水和任意真实卡组仍不在范围内。

## 最终结论

**可合并**，仅针对上面声明的工程范围。

B01、B02、B04已修复并通过定向行为/编码验证；B03按用户裁定保留+100资源边界，不再作为本轮合并阻塞；B05已用最小公开结算上下文接入候选动作评分器，未扩充普通CARD token。完整CPU回归、契约检查、补丁重放检查和短时模型/恢复诊断均已通过。

“可合并”不表示正版STS1形式化等价、75类所有组合穷举、正式PPO或泛化通过；旧实验和旧checkpoint也没有被改名为修复后结果。

## 1. 各审计问题

### B01：临时费用跨回合恢复

修复前反例是：`Infernal Blade → 生成临时0费攻击牌 → 打出并进入消耗堆 → 结束回合 → Exhume`，取回后仍为0费。修复位于：

- `third_party/sts_lightspeed/src/combat/CardManager.cpp:384-400`：回合边界对`hand/discard/draw/exhaust`统一调用已有`setCostForTurn(c.cost)`；该setter继续保留X费用等负哨兵，不把一次免费效果、持续实例费用和临时回合费用统一清零。
- 取回路径仍为`BattleContext.cpp:3021`附近的`chooseExhumeCard`，没有另造隐藏费用字段。

证据：

- `tests/test_card_token_fixes.py::test_b01_same_turn_exhume_keeps_temporary_zero_cost_and_payment`：同回合取回仍为0费，实际出牌不扣该费用。
- `tests/test_card_token_fixes.py::test_b01_cross_turn_exhume_restores_cost_and_mask_payment`：跨回合取回恢复1费，合法mask开放，实际支付扣1能量。

### B02：Havoc不可执行顶牌静默丢失

修复前，`Warcry`把Wound等牌公开置顶后执行Havoc，顶牌被`popFromDrawPile`移出；`canUse`为假时既没有耗尽也没有回收。

修复位于`third_party/sts_lightspeed/src/combat/BattleContext.cpp:861-863`：自动牌不可执行且`item.exhaustOnUse`为真时调用既有`triggerAndMoveToExhaustPile`。因此实体会进入消耗堆，并按现有耗尽触发时点运行Feel No Pain等效果；没有改mask来掩盖，也没有把异常伪装成战斗失败。

证据：

- `test_b02_havoc_unusable_top_card_is_not_lost`覆盖Wound、Dazed、Burn、AscendersBane和条件不满足的Clash，四区多重集总数保持1且最终在消耗堆。
- `test_b02_havoc_exhaust_trigger_runs_for_unusable_wound`验证Wound的耗尽触发增加格挡。

这关闭的是当前Havoc范围内的生命周期缺陷，不宣称所有Mayhem/药水/遗物自动打出组合已穷举。

### B03：Searing Blow +100（最终复核修正）

撤销F3的canUpgrade额外过滤及对应测试。+100不是规则上的不可升级终点；继续升级触及后端资源保护时明确抛异常。正常升级公式不变，此极端工程限制按用户裁定不作为合并阻塞。

### B04：AscendersBane费用分类

修复位于`third_party/sts_lightspeed/bindings/public-battle-env.cpp:275`：先判`isXCost()`，再将负费用实例归`UNPLAYABLE`，否则归`ENERGY`。CARD 115维布局不变，X/不可打出牌的`pay_cost`仍用0作类别占位。

`test_b04_ascenders_bane_is_unplayable_in_every_card_region`验证手牌、抽牌堆、弃牌堆和消耗堆的token均为不可打出类别、pay_cost为0；普通动作mask没有因此把卡牌变成可打出动作。

### B05：暂停结算与动作评分

#### 现有输入核验（证据边界修正）

真实路径对照了：

- 手动`Headbutt`选择；
- `Double Tap → Headbutt`的第一次和后续重复选择；
- `Havoc → Headbutt`自动打出并强制耗尽来源牌。

真实路径验证了来源模式、耗尽标记和已排队重复次数的公开取值。三条路径使用不同卡组/过程，并未证明去掉上下文后的完整实体输入相同；不能把它们当作碰撞反例，也未证明三个字段各自不可替代。保留这三个字段是具名公开流程提示的工程选择。人工成对编码测试只证明动作头/价值头实际接入，不证明真实状态碰撞或学习收益。

#### 最小实现

新增的独立`decision.resolution_context`只有：

| 字段 | 语义 |
|---|---|
| `source_mode` | `MANUAL`、`AUTOPLAY`、`REPLAY` |
| `source_will_exhaust` | 当前公开来源完成结算后是否会强制耗尽 |
| `pending_replay_count` | 已排队重复动作的数量汇总，不发布队列条目 |

具体路径：

- C++ `public-battle-env.cpp:298-309`从当前公开队列语义生成上下文；不导出内部队列、内部实例ID、RNG或隐藏牌序。
- Python `sts/env/ironclad.py:42-43,92`严格接收并保留上下文。
- `sts/env/entities.py:59-67,117-139,235,322-353`把它编码成`Candidate.context`：来源3位one-hot、耗尽标记1位、数量/4 1位；普通CARD token没有新增字段。
- `sts/models/entities.py:51,63,102`将候选上下文拼入`UnifiedEntityActorCritic.action_head`，因此不是只写在日志或info里。

`tests/test_card_token_b05.py`验证三条真实路径的上下文值，并将同一实体候选的上下文替换后确认实际候选logit变化；`tests/test_unified_entities.py`继续验证置换、路由和mask边界。

## 2. 版本、token和checkpoint影响

- CARD token：**不变，仍115维**；`card-token-dimensions.md`中的0–114布局不变。
- 统一接口：`unified-entity-interface-v3` → `unified-entity-interface-v4`。
- 模型：`unified-entity-set-v2` → `unified-entity-set-v3`；动作头输入增加5维候选上下文，当前诊断参数119922。
- 扩展运行契约：`ironclad-expansion-contract-v1` → `v2`；观测`v4` → `v5`；单选动作契约`v1` → `v2`。
- 容量契约已按当前输入/运行契约/后端实际hash重新绑定；实体和动作资源边界没有因B05偷偷放宽。
- 旧checkpoint不能精确恢复。`tests/test_entity_checkpoint.py`与F5诊断验证代码、模型、契约或后端变化会拒绝；本轮没有做隐式warm start或旧权重迁移。

## 3. 里程碑提交

| 里程碑 | commit | 内容 |
|---|---|---|
| F1 | `761f3e5` | 用户裁定登记、实施计划、B01/B02/B03/B04定向反例与修复前基线 |
| F2 | `a86f9df` | B01临时费用恢复、B04费用分类、对应增量补丁和中间验证 |
| F3 | `b8e1fff` | B02 Havoc生命周期、B03 +100过滤、对应构建与定向验证 |
| F4 | `fb9c764` | B05公开结算上下文、模型/接口版本升级、审计/共享文档同步和测试 |
| F5验证 | `eb8db03` | 全仓回归、容量契约重绑、当前契约版本兼容断言和诊断记录 |
| 交付报告 | 本文件所在后续提交 | 本报告及最终交付说明 |

## 4. 验证结果

已通过：

- `python -m pytest -q`：**950 passed in 36.59s**。
- B01–B04定向修复：10 passed；F2阶段只验证B01/B04为3 passed，B02/B03在该中间状态保持失败反例，未混写成通过。
- B05定向：2 passed；统一实体/输入/选择/模型/恢复联合回归54 passed。
- F4后C++/pybind构建：通过；基础补丁加增量补丁在全新worktree正向`git apply --check`通过。
- `scripts/check-ironclad-expansion.py`：150/150、69 legacy、150 expanded。
- `scripts/check-spec-v6.py`：PASS。
- 全卡短时诊断：`runs/card-token-fix-f5-20260913-rerun2`，32 steps、full-card inputs、5次选择、最多103实体、batch `[32,103]`、0自然终止、3次工程截断、119922参数、有限反向、checkpoint保存/加载和下一次更新逐值一致。该结果是工程诊断，不是胜率或正式PPO成绩。

曾出现但已处理的失败：全仓第一次运行有69项旧契约版本硬编码失败；更新测试读取当前契约后重跑为950 passed。F5诊断第一次因容量契约仍绑定旧hash而拒绝采集；按当前实际输入/后端重新绑定容量契约后，第二次诊断通过。这两次失败均已保留为版本/指纹边界证据，没有绕过检查。

未验证或范围外：正版全机制形式化等价、所有卡牌组合穷举、所有自动打出来源、完整活动环境任意中断恢复、跨机器/GPU位级恢复、新敌人/新药水、完整run、正式PPO和泛化评估。

等待用户后续合并安排；本任务没有自动合并或推送。
