# 公开分布扩展第二轮主审

日期：2026-09-12。审核返工代码、实际交付JSON、报告及跨任务集成。不修改正式manifest或业务实现。

## 裁定

整体尚未通过。前缀旧三项缺陷在当前固定样本上的修复通过，但保留一个精英静态准入边界问题；精英交付未用最终前缀重跑；分布分析器无法正确消费另两份实际交付，尚无最终合并统计。

当前前缀输入SHA256：`d4f5ff6d0177855b3a8ddea9d6080c5361adcb462f07c7d79dc4d11b58a02d09`。

## P1：分布分析器忽略真实前缀schema的拒绝字段

位置：`scripts/analyze-public-coverage.py:1725`、`:1771`。

实际前缀输出使用`evidence_complete`、`evidence_blockers`、`state_evidence_blockers`、`backend_blockers`和`backend_admissible`。分析器没有正确映射这些字段，反而在存在candidate时推测来源/目标完整。

主审传入真实前缀文件及其正确SHA256，输出`entry_evidence_complete=392`；原257与新增96证据完整场景不重叠，应为353。39个不应标完整的场景被升格。输出互斥状态计数仍是旧99/1025/158，与其布尔完整数量又不一致。

必须为版本化前缀schema显式适配，保留全部否定证据。缺少证据不能用“有candidate”推定通过。用真实交付文件做集成测试，检查353完整候选、19新增静态候选及其全部阻塞、状态一致性；不要仅测自造的别名字段。

## P1：分布脚本不能读取实际精英交付文件

位置：`scripts/analyze-public-coverage.py:1495`、`:1926`。

主审同时传入`docs/public-prefix-expansion-candidates.json`与`docs/public-elite-source-candidates.json`及各自正确SHA256，脚本抛出`ValueError: 外部候选文件没有可识别的场景记录列表`。

需对精英交付的实际schema提供明确适配，区分摘要、交叉表和B快照，避免重复计数或把B拼入A。若只支持独立crosswalk文件，应明确CLI合同、交接路径并验证其绑定的前缀版本；不能让用户自行猜文件格式。

## P2：前缀静态闸门把burning_elite=true当作后端已支持

位置：`scripts/expand-public-prefixes.py:257`、`:661`。

将一个当前合法普通候选的encounter改为GREMLIN_NOB、burning_elite设true，`backend_blockers`返回空列表；但原生后端`public-battle-env.cpp:319`明确拒绝所有燃烧强化。精英证据函数也只检查布尔值，不要求true时提供强化类型，并接受未证明逐场语义的run级同名字段。

当前固定样本没有该字段，所以这不影响当前96/19计数。修复需把来源完整和后端支持分开：true且无强化证据不能称完整；即便强化证据完整，在当前后端仍须标不支持。未知字段不能仅凭名称推定其楼层/房间语义。补true/false/unknown及字段作用域测试。

## P2：精英报告仍使用返工前的前缀数量

`docs/public-elite-source-report.md`仍写前缀声称53条完整、2条静态放行；当前最终前缀中精英的这两个数都为0。若用于历史对照必须明确标成历史快照，同时另提供最终交叉审计和输入SHA256。当前报告未完成这一交接，不能作为最新合并分析输入已收口的证据。

## 本轮通过的验证

- 三任务定向测试：37 passed in 10.73s。
- 前缀全量测试重建得到198研究候选、96证据完整、19静态通过；原99场一致性通过。
- 旧两场错误精英及其余未知精英现在有明确阻塞。
- 事件药水核算和缺必要效果字段的旧缺陷已有回归覆盖。
- 主审再次原样运行19场，随机/规则共38次全部自然终止，无异常或截断。
- 当前19场仍为14个run，新增独立run为1；没有新增第6层以后或精英覆盖。

探针仅做开发运行验证，未建立正式准入。第二轮运行结果使用了原`reference/public-expansion-review-probe.json`路径并覆盖该探针输出；第一轮两场精英失败的结论仍保存在第一轮审核报告中。

## 收口顺序

1. 前缀agent补精英true及字段语义边界并冻结最终候选。
2. 精英agent用最终前缀重跑交叉表，保存输入SHA256；历史结论与当前结论分开。
3. 分布agent为两种实际schema适配，运行真实三方集成；恢复正确拒绝状态，再生成新的覆盖和依赖收益报告。
4. 主审复验后再接入新manifest。当前正式可执行库仍为99场，不能把353证据候选或潜在118静态支持场景混成正式准入数量。

本轮仅新增审核报告和ignored审计输出，未修改正式环境、manifest、eval_seeds.json，未训练、commit/push。
