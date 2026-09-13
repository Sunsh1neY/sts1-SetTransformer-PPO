# 敌人续批分发状态

日期：2026-09-13。负责人：R。此表只记录本任务 22 个待审遭遇，不把已有 33 个开发准入遭遇重新计数。A/B/C/D worktree 由 R 准备，当前没有自动启动其它 agent。

## 总体检查点

| 检查点 | 状态 | 证据或限制 |
|---|---|---|
| 共同源码基线 | 已整理 | EP3 成果源 `8f3d3c7...`；共同代码/文档基线为 `29013d334c8ad6adeceea00dc29d442067bb982b`，主工作树 dirty 成果已单独记录 |
| 后端补丁链 | 已验证 | 锁定后端 → 基础补丁 → 敌人增量补丁正向、逆向均可复现 |
| 独立干净构建 | 已验证 | `sts2-enemy-baseline-backend` / `sts2-enemy-baseline-build`，契约指纹导入通过 |
| A/B/C/D worktree | 已创建 | 四个目录均从 `29013d334c...` 创建，随后快进到 R 的文档交接提交；路径和后端指纹见下表 |
| 全卡共享接口 | 已只读核对 | 当前为 `unified-entity-interface-v4`；旧 handoff v1 哈希已刷新，尚未接入敌人生产入口 |
| 字段审批 | 待用户批准 | 具体包见 `docs/enemy-field-approval.md`；等待不视为批准 |
| 奖励 | 冻结 | 继续使用 `battle_reward_v1`，不增加金币、诅咒、掉落或辅助奖励 |
| 药水审计 | 暂停 | 不扩充药水白名单，不以药水结果代替敌人审核 |
| 正式训练 / push / 主分支合并 | 未执行 | 本任务不启动这些动作 |

## 已创建的隔离目录

| 组 | 创建时顶层 HEAD | 分支 | 后端 HEAD | `json` | `pybind11` | build 目录 | build 状态 |
|---|---|---|---|---|---|---|---|
| A | `29013d334c8ad6adeceea00dc29d442067bb982b` | `codex/enemy-a` | `7476a81954020087da31d41d16fddf475746ec2d` | `0b345b20c888f7dc8888485768e4bf9a6be29de0` | `a2e59f0e7065404b44dfe92a28aca47ba1378dc4` | `C:/Users/19091/Desktop/sts2-enemy-a/third_party/sts_lightspeed/build` | 已建立，未编译 |
| B | `29013d334c8ad6adeceea00dc29d442067bb982b` | `codex/enemy-b` | `7476a81954020087da31d41d16fddf475746ec2d` | `0b345b20c888f7dc8888485768e4bf9a6be29de0` | `a2e59f0e7065404b44dfe92a28aca47ba1378dc4` | `C:/Users/19091/Desktop/sts2-enemy-b/third_party/sts_lightspeed/build` | 已建立，未编译 |
| C | `29013d334c8ad6adeceea00dc29d442067bb982b` | `codex/enemy-c` | `7476a81954020087da31d41d16fddf475746ec2d` | `0b345b20c888f7dc8888485768e4bf9a6be29de0` | `a2e59f0e7065404b44dfe92a28aca47ba1378dc4` | `C:/Users/19091/Desktop/sts2-enemy-c/third_party/sts_lightspeed/build` | 已建立，未编译 |
| D | `29013d334c8ad6adeceea00dc29d442067bb982b` | `codex/enemy-d` | `7476a81954020087da31d41d16fddf475746ec2d` | `0b345b20c888f7dc8888485768e4bf9a6be29de0` | `a2e59f0e7065404b44dfe92a28aca47ba1378dc4` | `C:/Users/19091/Desktop/sts2-enemy-d/third_party/sts_lightspeed/build` | 已建立，未编译 |

四个目录均含同一生成契约头 `bindings/enemy-potion-config.h`，SHA256 为 `11c3f8cc7641eef2320130a5f8cdd5fe4a2088f64eab916f4ba4ca03d7980bd1`。没有启动任何 agent；这些目录只作为分发隔离边界，等待用户字段裁决和后续人工安排。

## 22 个遭遇逐项表

“reset拒绝”是当前唯一可报告的实际运行结果：既有白名单拒绝测试覆盖这些条目。它证明当前未开放，不证明机制正确或错误；每个条目的机制测试、公开字段对拍和自然终止仍为未完成。

| # | 组 | 遭遇 | 当前状态 | 本轮实际结果 | 主要依赖 | 待裁决 / 准入条件 |
|---:|---|---|---|---|---|---|
| 1 | A | `THREE_BYRDS` | 未准入，reset拒绝 | 只有静态风险记录；无机制运行 | Flight、坠落/眩晕、恢复飞行；A字段包 | 批准Flight语义并完成多段攻击、伤害预览和目标mask对拍 |
| 2 | A | `CHOSEN_AND_BYRDS` | 未准入，reset拒绝 | 未运行；依赖被拣选者已准入证据 | `THREE_BYRDS`全部依赖；组合目标路由 | 飞鸟字段和组合终局完整通过 |
| 3 | A | `THREE_SHAPES` | 未准入，reset拒绝 | 未运行；无机制通过数字 | Exploder/Repulsor/Spiker公开状态、自毁和状态牌生成 | 仅加入真实出现的状态值；自爆/自毁中途终局通过 |
| 4 | A | `FOUR_SHAPES` | 未准入，reset拒绝 | 未运行 | 三/四目标合法mask和容量边界 | 不做极端容量工程；常规四目标路径无越界并自然结束 |
| 5 | A | `SPHERE_AND_TWO_SHAPES` | 未准入，reset拒绝 | 未运行；依赖Spheric Guardian已有开发证据 | 形状机制、组合中途终局、目标重排 | 形状字段与本体/同伴路由对拍通过 |
| 6 | A | `GIANT_HEAD` | 未准入，reset拒绝 | 未运行；正版count/阈值仍需定点核验 | Slow语义、count初值/高进阶时点、伤害公式 | 批准Slow表示并完成相邻阈值时序对拍 |
| 7 | A | `NEMESIS` | 未准入，reset拒绝 | 未运行；无实体轮换尚未证明 | Intangible、隐身/出现时点、持续性与终局 | 批准公开Intangible语义并证明无实体时观测和mask |
| 8 | A | `DONU_AND_DECA` | 未准入，reset拒绝 | 未运行；双Boss仅静态枚举 | 两个独立实体、互相强化/格挡、A19护甲 | 双Boss单体死亡后的合法目标、终局与状态更新通过 |
| 9 | B | `GREMLIN_LEADER` | 未准入，reset拒绝 | 未运行；无召唤机制结果 | 公共生命周期、召唤集合、首领死亡清理 | 批准生命周期/路由方案后完成召唤和清理对拍 |
| 10 | B | `REPTOMANCER` | 未准入，reset拒绝 | 未运行 | 匕首召唤、同槽替换、匕首自毁 | 新实例引用不继承；首领/匕首终局通过 |
| 11 | B | `THREE_DARKLINGS` | 未准入，reset拒绝 | 未运行 | 倒地保留token、targetable分离、复活计时 | 批准present/targetable和生命周期路由；未全倒不得终局 |
| 12 | B | `COLLECTOR` | 未准入，reset拒绝 | 未运行 | 火炬头召唤/替换、首领死亡后的随从集合 | 召唤对象不丢失；全体死亡才正常结束 |
| 13 | B | `AWAKENED_ONE` | 未准入，reset拒绝 | 未运行 | 两阶段复活、能力牌触发、阶段字段 | 批准阶段表示；首阶段死亡不提前奖励，复活后引用更新 |
| 14 | C | `SNECKO` | 未准入，reset拒绝 | 未运行；全卡接口未接入 | 共享CARD费用实例、Confused、费用有效期 | 复用共享费用字段，不建第二套卡牌协议 |
| 15 | C | `WRITHING_MASS` | 未准入，reset拒绝 | 未运行 | 反应换意图、Reactive/Malleable、永久加牌出口 | 批准战后变化输出边界；当前战斗和战后变化分开验证 |
| 16 | C | `AUTOMATON` | 未准入，reset拒绝 | 未运行 | B生命周期；Stasis具体卡牌区域；共享选择/卡牌接口 | 用户在`stasis`区域与`resolving`复用方案中裁决其一 |
| 17 | C | `TIME_EATER` | 未准入，reset拒绝 | 未运行 | 共享卡牌计数、Time Warp、强制结束回合、半血处理 | 保持66路由/现有候选协议；12牌边界和阶段回复实测通过 |
| 18 | D | `BOOK_OF_STABBING` | 未准入，reset拒绝 | 未运行；固定15生成上界不能沿用 | 多段次数增长、Wound生成、常规队列保护 | 只在常规路径验证；真实资源错误必须原样报告 |
| 19 | D | `MAW` | 未准入，reset拒绝 | 未运行；不做极端长战斗工程 | 回合增长攻击、现有turn/intent预览、队列边界 | 不新增成长推导字段；常规自然终止和异常处理通过 |
| 20 | D | `TWO_THIEVES` | 未准入，reset拒绝 | 未运行；没有伪造击杀证据 | 逃跑等价移除、目标mask、金币实际变化 | 不新增逃跑原因；用户裁决战后金币输出是否需要 |
| 21 | D | `TRANSIENT` | 未准入，reset拒绝 | 未运行 | Fading倒计时、当轮伤害、自然消失终局 | 批准Fading状态表示并证明消失是正常battle终局 |
| 22 | D | `CHAMP` | 未准入，reset拒绝 | 未运行 | 半血阶段转换、清减益、后续行为/回复 | 与B共用阶段语义决策；转换不提前奖励，后续行为通过 |

## 组间依赖顺序

1. R 先提交字段包，审批前只允许源核查、诊断夹具和文档。
2. B 先落公共生命周期和稳定实例路由；其结果作为 C 的召唤物/铜球实体依赖。
3. C 只读接入全卡 v4 的 EntitySample、Candidate、routes 和 CARD region；Stasis区域方案必须先裁决。
4. A、D 在生命周期基础上分别做特殊机制和长短战斗验证；CHAMP阶段字段与B共用一次决策，不分裂出第二套phase。
5. R 串行解决共享文件冲突，逐遭遇复跑受影响旧入口和本批链条，再更新中央白名单。

当前 22 个条目均保持未准入；不存在“等待期间默认通过”的状态。

### 非铜球首批全卡集成更新（2026-09-13）

MAW/TRANSIENT独立公开入口已接；MAW/TRANSIENT/SNECKO全卡A20集成通过，345相关回归及新增padding后的8项专项通过，450局7225步0异常（1次预算截断）。旧表保留历史身份，当前范围以docs/enemy-full-card-integration-report.md为准。时间吞噬者按用户最新选择暂缓，铜球仍暂停。

## 第二幕22遭遇收口（2026-09-13）

剩余8遭遇已完成A20全卡开发接入，第二幕现22/22（含三项事件战斗部分）。B一次关联融合、stasis身份限定观测、三类公开phase、实例引用和终局battle_exit已落实。CARD116、ENEMY774，模型unified-enemy-entity-set-v2；旧模型不可精确续训。

本批434相关回归通过，状态编译夹具另1通过；3300局全卡短程交互53906步、316次选牌、3256自然终止、44外部截断、0异常。未正式训练、未推送/合并。完整范围与证据边界见[第二幕完成报告](act2-completion-report.md)。本文更早的“8遭遇待完成”“铜球暂停”等只保留历史意义。
