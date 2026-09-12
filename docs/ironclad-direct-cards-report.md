# E2直接效果十二类验收

2026-09-12，独立worktree，统一实体输入v3/模型v2。新增12类24版本，当前52类战士104/150版本；剩23类46版本。旧public仍69版本，旧MLP/Set实验保持冻结。

## 两个小里程碑

| 批次 | 卡牌（基础/+均验收） | 证据 |
|---|---|---|
| E2a，提交0d2b7ad | Clash、Hemokinesis、Bloodletting、Intimidate、Limit Break、Offering、Shockwave | tests/test_ironclad_direct.py，36项；与旧入口/采集/恢复联合121项通过 |
| E2b | Feed、Reaper、Sword Boomerang、Second Wind、Sever Soul | tests/test_ironclad_direct_chain.py，28项 |

准入链包含独立注册表、reset校验、C++cardRow公开数值、普通动作mask、真实结算、新实体模型前向、覆盖账本与回归。没有只开放名称；没有修改基础战斗奖励。数值依据沿用docs/ironclad-card-audit.md各牌的一手仲裁定位与当前BattleContext具名分支。

测试关键边界：Clash手牌类型限制；三个自伤动作触发Blood for Blood一次降费；Shockwave先Weak后Vulnerable与Artifact消耗；Limit Break+不耗尽及Flex临时力量到期；Offering抽3/5与No Draw；Reaper按多敌实际扣血治疗、格挡吸收不治疗及最大HP上限；Feed非致死不成长、致死最大HP+3/+4与原奖励公式；Sword Boomerang玩家不选随机目标且段数3/4；Second Wind/Sever Soul自动耗尽非攻击并触发Sentinel与Feel No Pain，来源牌不误耗尽，Second Wind空集合无格挡。

## 集成与限制

- 全仓 `python -m pytest -q`：866 passed in 31.52s；无失败。check-spec-v6、覆盖检查、冻结7文件、补丁反向校验与diff空白检查通过。
- `scripts/diagnose-direct-cards.py`：12类×2升级状态×2遭遇，共48局、980transition；48自然终止、0截断、0异常。使用Jaw Worm/Exordium Thugs具名受控卡组和随机策略，不是正式强度评估。报告runs/direct-cards-e2-20260912/integration.json。
- 当前后端的16步模型工程诊断：2片段、1次真实True Grit选择、103最大实体、119602参数；下一次更新恢复一致。0自然终止、2预算截断。该诊断检查共享管线，不宣称新12类都被模型实际采样。报告与checkpoint在runs/direct-cards-e2-20260912/model。
- 此批无新实体生成机制，无自动打出/复制/抽耗能力链，原每decision15检查仍覆盖现内容。增长与分配保护保留；途中466截断仍关闭。更新注册与实际后端SHA绑定，不修改旧public契约。
- Feed针对Minion/复活/逃跑敌人的资格、Reaper与未来敌人防御机制、Rupture自伤触发、Dark Embrace耗尽抽牌等组合未在此批验收，随对应内容进入测试矩阵。剩余Disarm/Iron Wave/Fiend Fire差异风险仍待关闭。
- 当前checkpoint随注册和二进制变化产生新指纹，旧U4/U6产物仍属于历史版本。本次不授权或执行正式长时间训练。

后续顺序：能力链与简单手牌单选 → 跨区选择/公开顶牌 → 动态公式/复制 → 自动打出和完整生成池；风险牌最小复现可提前。不会为了开放间接卡缩小真实生成池或自动代选。
