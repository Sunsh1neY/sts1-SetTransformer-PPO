# 第二幕全卡接入首批报告

日期：2026-09-13。工作树：C:/Users/19091/Desktop/sts2-enemy-potion，分支 codex/enemy-potion-expansion。本批不是第二幕全部完成。

## 实际范围

全卡 A20 入口新增13遭遇：SPHERIC_GUARDIAN、CHOSEN、SHELL_PARASITE、SENTRY_AND_SPHERE、SNAKE_PLANT、CENTURION_AND_HEALER、CULTIST_AND_CHOSEN、THREE_CULTIST、SHELLED_PARASITE_AND_FUNGI、SLAVERS、BOOK_OF_STABBING、COLOSSEUM_EVENT_SLAVERS、COLOSSEUM_EVENT_NOBS。

加上此前异蛇，第二幕共14/22遭遇进入全卡开发入口（19常规/精英/Boss加3事件）。全卡跨幕总入口21遭遇；旧独立入口白名单未随本批修改。事件仅模拟各自战斗，不执行事件选择、支付或两战衔接。

## 修复

- 后端白名单改由全卡契约生成，避免 Python 与 C++ 手工清单分叉；同步幕校验和第二幕精英房间类型。契约 integration_revision=2，SHA 随内容更新。
- Hex 是布尔状态，原集成出口读取数值 map 导致 map::at 异常。复用独立敌人出口的布尔语义修复，新增真实妖术生成 Dazed 的回归。
- 扎人的书 A18 以上单刺递增逻辑原在 return 后，不可达。依据本机正版 JAR 核对，在 enemyPotionExpansion 开关内修复；冻结入口保留原行为。证据哈希见 act2-book-evidence.json。
- 未新增 Minion、Painful Stabs、Stasis 冗余 token 特征；没有新增 CARD 字段、关系分支或模型参数。

## 验证

新增 tests/test_enemy_act2_full_card.py 共44项：13遭遇各3条合法候选真实轨迹、2个竞技场组合断言、扎人的书2项伤口与格挡定点、Hex1项真实生成定点。每条随机轨迹每步编码与动态 collate，运行到真实终局；这不是全75卡逐机制或所有组合验收。

最终相关回归运行：389通过、1失败；唯一失败是状态导出夹具编译时 cc1plus 内存分配失败。该测试随后单独重跑1通过。不得写成一次390全通过或游戏轨迹失败0。

此前本批发现过6个 Hex 异常和扎人的书计数缺陷，均已修复并由上述最终运行覆盖。扎人的书首次夹具沿用worker种子但初始牌组不同，初始招式不同；改为本入口实测单刺种子860026，再暴露并修复真实计数缺陷。

增量补丁前向/反向检查与实际编译通过。未正式 PPO、未提交/推送/合并。本批测试不证明训练收益。

## 待完成与边界

第二幕剩余8遭遇：THREE_BYRDS、CHOSEN_AND_BYRDS、TWO_THIEVES、GREMLIN_LEADER、AUTOMATON、COLLECTOR、CHAMP、MASKED_BANDITS_EVENT。

待完成：异鸟多段坠落时序、召唤与同槽新实例路由、第一勇士公开阶段、铜球 stasis 与 B 融合、盗贼金币战后出口、蒙面强盗正式证据与交互。用户审批已收口，不以旧“待审核”标签阻断实施；实际新字段方案仍需具体审批。

第三幕时间吞噬者及 DEFEND_DEBUFF 已获批准，另行实施，不计入第二幕22遭遇。
