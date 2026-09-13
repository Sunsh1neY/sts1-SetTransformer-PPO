# 全卡扩展单选路由协议

日期：2026-09-12。历史状态：E1e当时仅完成路由组件。后续U1已接通True Grit+，统一实体候选头与小规模采集已验证，当前准入80/150；最新接口与边界见[统一实体报告](unified-entity-report.md)。下文保留E1e的设计依据与当时验收范围。

## 后端核对

[S1] 高，一手锁定后端源码，核验日期2026-09-12：`src/sim/search/Action.cpp` 的`getSelectIdx/isValidSingleCardSelectAction/executeSelectCardAction`和`include/combat/CardSelectInfo.h`。

- 单选取低16位牌区索引；HEADBUTT对应弃牌堆、EXHUME对应消耗堆，不能套用多选的10位集合编码。
- ARMAMENTS、DUAL_WIELD、EXHAUST_ONE和WARCRY对应手牌索引。合法性由后端判断，候选路由不能依据模型预测合法性。
- `Actions.cpp::ChooseExhaustOne`在手牌0张时直接返回，1张时自动处理，超过1张才暂停。接入时只发布真实暂停点，不能为强制动作制造策略transition。
- True Grit+的选择在获得格挡后发生；`BattleContext.cpp::chooseExhaustOneCard`移动选定实例并触发耗尽。待验证内容包括选择后继续结算队列、Sentinel/Feel No Pain、终止中断及动作预算边界。本小步不宣称这些行为已接通。

## 已实现组件

`sts/env/selection.py::SelectionRouter`接受后端筛好的完整合法候选，每项由私有牌区索引和已规范化卡牌语义组成。

输出分为两个独立对象：

- `semantic`：SELECT_CARD阶段、选择任务、候选区域、所需数量、逐实例候选和mask；允许送入未来编码器。
- `routing`：当前decision_id；只用于回送动作，不能送入语义token。

选择动作格式为`{"kind":"SELECT_CARD","decision_id":"当前凭据","candidate_index":公开候选位置}`。`take`返回内部SelectionTarget供后端执行并立即使凭据失效。重复提交、过期、其他环境凭据、越界位置及多余字段拒绝。reset或后端失败时适配器必须invalidate；错误的候选发布也会清除旧决策。

非手牌按完整公开语义排序，私有索引随记录一起重排；完全相同的重复卡仍分别占位置。手牌保留传入顺序。字段采用封闭白名单，防止backend_index、uniqueId、seed及未来意图混入候选token。返回值深复制，调用者不能修改内部路由或候选。

路由凭据使用与游戏/策略RNG独立的会话标识加递增序号。它不构成游戏状态，也不是学习特征。未来checkpoint重放须按语义候选位置重新取得当前凭据，不能重用旧环境会话的decision_id；完整PPO恢复尚未实现。

## 验证与下一接口

`tests/test_selection_routing.py`使用真实环境输出的Rampage记录验证格式，再构造纯路由夹具。15项测试覆盖：不同成长实例、相同重复实例、32个弃牌候选、手牌与16位索引界、过期/跨环境/重复引用、语义与私有索引分离、隐藏字段拒绝、返回对象不可篡改以及发布失败失效。

这些是路由组件测试，不是32张真实弃牌堆下Headbutt行为验收。下一步从C++的真实CARD_SELECT暂停点获取候选和来源语义，将路由与继续结算连接；再接Set候选评分与轨迹记录。旧66个普通动作、当前观测v2、容量证明和checkpoint不在本小步修改。
