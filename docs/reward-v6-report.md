# v6 双任务奖励迁移报告

日期：2026-09-08。裁定：D27。执行规格：[`spec-v6.md`](../spec-v6.md)。

## 1. 结论

仓库已从 v5 的单一“战斗胜利加剩余 HP”表述迁移为两个正式任务：

- 当前 `battle/minimal-v1/battle_reward_v1` 已接入真实 C++ 战斗环境、Python 适配、PPO 采集/恢复、评估、元数据和确定性测试；
- 未来 `run/run_reward_v1` 已定义最终通关才得1的奖励、任务版本、成功谓词和数据边界，但完整 RunEnv 不在当前排期且尚未实现；
- v6 基线固定 `gamma=1`、`beta=0`。同一任务内 MLP-PPO、Set-PPO、DT 共用逐步奖励和完整真实 RTG；battle 与 run 不混标、不直接排名。

本轮没有启动长时间训练、完整爬塔开发或大规模新数据生成。

## 2. 实现落点

| 层 | 改动 |
|---|---|
| C++ 奖励产生点 | 保留首次战斗胜利 `1+0.5*h_exit`；任何真终局的退出 HP 非法时明确报错，不再以 `max(1,max_hp)` 静默掩盖 |
| Python 共享契约 | 新增 `sts/rewards.py`，统一 battle/run 公式、版本字段、真实 RTG、兼容检查与可验证重算入口 |
| 环境 info | 增加 `task_type`、`task_spec_id`、`reward_version`、`task_outcome`、`termination_reason`、`battle_won/run_won`、`reward_base/reward_train` 等；不进入模型观测 |
| PPO/GAE | rollout 显式保存 `terminated`、`truncated`、episode 边界和 reset 前最终观测；真终止不自举，截断自举但不跨 reset |
| 配置/checkpoint | `configs/ppo-minimal.yaml` 与新 checkpoint 保存 v6 契约；恢复时逐字段拒绝任务或奖励版本漂移；v5 checkpoint 不静默续训 |
| 评估 | battle 同时报综合回报、胜率、获胜条件下平均退出 HP 比例和超时；没有胜利时条件 HP 为 `null` |
| 数据工具 | 新增 `scripts/audit-reward-data.py`，用原 seed 与动作序列确定性重放旧 battle 数据；共享 API 可从完整可验证字段重算逐步 reward/RTG |
| 规格检查 | 新增 `scripts/check-spec-v6.py`，检查章节、当前入口、本地链接、关键契约词和不可变评估 seed 哈希 |

## 3. v5 → v6 差异

1. `win` 拆为 `battle_won` 与 `run_won`；普通战斗胜利不再可被解释为完整通关。
2. battle 的0.5从“以后默认按需校准一次”改为 `battle_reward_v1` 固定参数；改变必须创建新奖励版本。
3. run 只在首次最终通关时奖励1，不累计战斗、HP、构筑、金币或每幕奖金；缺少版本化成功谓词时拒绝正式训练。
4. `terminated`、`truncated`、rollout buffer 尾和异常轨迹分别处理；自动 reset 必须保留旧 episode 最终观测。
5. DT 的真实 RTG 先按完整真终止 episode 计算再切窗口；未恢复到终局的外部截断轨迹不伪造成失败0。
6. 势能塑形默认关闭；未来研究保持的是固定起点下策略排序，不把累计数值完全相等写成一般结论。

## 4. 验证结果

| 检查 | 结果 | 边界 |
|---|---|---|
| C++ 扩展重建 | 通过 | `IroncladBattleEnv import OK`；仅有上游 CMake deprecation warning |
| 修复消费者兼容后的完整回归 | **278 passed，0 failed，0 skipped** | 未重新执行一万配置正式性能验收 |
| 旧 S3 数据确定性重放 | **19,881 episode，0 failure** | 19,852 胜、29 负、0 硬超时；三份文件全部数值兼容 `battle_reward_v1` |
| 本轮 Python 静态检查 | `All checks passed!` | Ruff 仅检查本轮新增/修改的 Python 文件；不借机清理无关历史 lint |
| Python 字节码编译 | 通过 | `sts`、`scripts`、`tests` |
| v6 文档检查 | `PASS` | 735 行规格、11 个当前入口、本地链接、契约词和 seed 哈希 |
| 评估 seed | 哈希不变 | `38a093486535aa529d54ebfcfd535e67fe043daff8286b5740b5766a6131af9c` |

第一次完整回归曾出现3个失败：旧诊断夹具缺 `max_hp`，四路径工具把新增字符串 info 强制转成整数。两处消费者契约修复后完整回归通过；首次失败没有被隐去。

R1–R14 的完成边界：

- 已有环境/数学/数据实现验证：R1–R3、R4 的终局再次 `step()`、R8–R12、R14；
- 仅共享契约/最小状态机验证：R5–R7，因为完整 RunEnv 尚未实现；
- R10 的外部截断已验证 GAE 数值和 collector 的最终观测保存路径，但正式 battle 环境当前不产生外部截断；
- R13 已验证三类模型必须消费同一共享 reward/RTG 契约；Set-PPO 与 DT 尚未按原排期实现，不能称端到端通过；
- R4 的终局状态反序列化分支未验证，因为当前 C++ 后端没有通用战斗状态反序列化 API。

## 5. 数据与 checkpoint 影响

审计了：

- `runs/ppo-minimal-s3-20260908/episodes.jsonl`：4,032 条；
- `runs/ppo-minimal-s3-20260908-resumed/episodes.jsonl`：15,797 条；
- `runs/ppo-s3-cli-smoke/episodes.jsonl`：52 条。

三份旧数据均通过逐条重放，说明原公式和 HP 结算时点与 `battle_reward_v1` 数值兼容，因此不制造数值变化、不改写旧文件。旧 metadata 没有 v6 任务/奖励字段，继续作为 v5 历史产物；如生成新数据版本，应由重放结果写入新文件并保留旧版。缺少后续整局结果，所以全部 `eligible_as_run_labels=false`。

新 PPO checkpoint 格式升为 trainer version 2 并保存完整奖励契约。v5 checkpoint 的恢复训练会明确拒绝；若未来显式 warm start，须记录来源并在新任务重新评估。

## 6. 复现命令

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-lightspeed.ps1
python -X utf8 -m pytest -q
python -X utf8 scripts/audit-reward-data.py --output build/reward-v6-data-audit.json
python -X utf8 scripts/check-spec-v6.py
python -X utf8 -m compileall -q sts scripts tests
```

Ruff 本轮文件、文档检查和 `compileall` 均已通过；历史仓库范围若另有既存 lint 项，不与本轮变更混报为奖励验收失败。
