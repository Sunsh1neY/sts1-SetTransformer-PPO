# STS RL Agent

Headless《杀戮尖塔 1》Ironclad 战斗环境 + A/B 两族模型对照（Set Transformer + PPO vs Decision Transformer）。正式训练后端为 lightspeed C++，Python 模拟器保留教学与验证用途。真实目标：通过工程实践理解 Transformer 原理，游戏是载体。

**唯一执行依据：[`spec-v6.md`](spec-v6.md)**（2026-09-08 双任务奖励修订，D27）。`spec-v5.md` 及更早版本已冻结为历史方案，仅供对照。

**学习入口：[《STS RL 学习路径 v2》](docs/learning-path-v2.md)**：这个项目应学到什么、各阶段怎样验证理解，以及现在从哪里开始。

> 目录名 `sts2` 是 v3 时代（STS2 方案研究）的历史遗留，不改名；实际规格来源是 STS1。

## 当前统一扩展环境（2026-09-14）

全卡开发入口 `sts.env.ironclad.IroncladEnv` 已覆盖 Ironclad 75 类/150 版本、第一幕 20 个常规遭遇与 2 个事件变体、第二幕 19 个常规遭遇与 3 个事件战斗，均为 A20 单场战斗。第一、二幕共 44 个遭遇；另保留已有第三幕 MAW/TRANSIENT。接口与实测边界见 [第一、二幕整合报告](docs/act12-main-integration-report.md)，逐遭遇和逐版本结果见 [证据索引](docs/act12-main-integration-evidence.json)。

统一扩展用 `scripts/build-enemy-potion.ps1 -Python python -Jobs 1` 构建，以 `IroncladEnv.reset(scene, seed, diagnostic=True)` 进入。构建会核对运行指纹；旧后端不能只靠合并 Python 文件获得全卡支持。本次是环境工程验收，正式训练准入仍关闭；原五遭遇采集器和 A 路径训练范围保持各自版本。

## 冻结的最小切片基础环境

- 正式后端：`sts_lightspeed` C++，当前只开放 A0 的 Jaw Worm、Cultist、双虱遭遇。Python 模拟器保留教学及局部回归用途。
- 运行接口：项目包入口 `LightspeedBattleEnv.reset/step/action_mask/observation`，内部复用 C++ `IroncladBattleEnv`。动作编号为 `slot * 3 + target`，30 为结束回合，无目标卡只使用目标 0。
- 当前是独立战斗任务 `battle/minimal-v1/battle_reward_v1`：非终局 0；首次胜利 `1 + 0.5 * 退出HP / 最大HP`；失败及硬超时 0，γ=1、β=0。未来完整爬塔使用独立的 `run_reward_v1`，只在首次最终通关时得1；普通战斗胜利不能标成 run 通关（D27）。
- 硬超时是任务内失败：返回 `terminated=true`、`truncated=false`、`info.timeout=1`，训练时不继续自举。
- PPO 采样显式区分真终止与外部截断；外部截断用 reset 前最终观测自举但 GAE 不跨 reset。完整 RunEnv 尚未实现，当前只完成 run 奖励和版本契约，不能启动正式 run 训练。
- 已确认模型设计：Set/DT选牌保留实体与动作的对应关系（D17）；状态只使用玩家可见信息（D19）。当前已实现D25最小切片MLP。
- 当前输入协议已迁移为 D24 逐牌实体 V2：四区卡牌记录使用稳定注册 ID、location、升级与费用 known/valid 语义；Flatten/Token 共用同一准备路径，MLP内类别embedding与固定数值缩放已接入。
- 现有真实游戏日志用于有限字段校准。当前不扩日志工具，缺少的字段明确记为未验证；后续更大范围测试发现差异后再处理（D20）。此状态不代表所有游戏机制已被证明正确。
- `eval_seeds.json` 已固定；环境主 RNG 为 xorshift128+，洗牌临时使用 Java LCG，详见 [机制规格](docs/mechanics.md)。

裁定与边界见 [决策日志](docs/decisions.md)；冻结的旧研究文档不作为实现依据。

当前进度：Week 4 与 D24 实体迁移已收口；依 D25，Week 5–6 先在锁定的最小切片完成
PPO+MLP 冒烟，再按机制批次扩中等档。S1/S2/S3工程已完成：首轮PPO训练262144步，
300局开发诊断中平均回报1.4396对随机1.1775，配对差值CI为正；详见
[PPO首轮报告](docs/ppo-minimal-report.md)。下一步是S4多初始化验证，再做S5冻结。
M1 卡表来源审计已有初步记录，扩容实现暂不启动。
任务拆解见 [MLP 冒烟计划](docs/mlp-smoke-plan.md)与
[Week 5–6 计划](docs/week-5-6-plan.md)。

2026-09-06 D24 实体版本机验收：**146 项测试全部通过**；四条路径各以 10000 个唯一训练配置重复三轮，异常、非法动作、硬超时与奖励契约错误均为 0，60 场完整轨迹重放一致。raw / dict / Flatten / Token 完整路径单核中位数约为 14702 / 5882 / 3841 / 3790 steps/s，均超过 Gate 1 的 2000 门槛。D25 S1 接入 MLP 模型契约后，完整回归为 **150 项通过，0 失败，0 跳过**。详见 [实体基础验收报告](docs/entity-foundation-report.md)。这些结果验证当前切片与模型基础接口，不代表策略已经学会或与真实游戏全部机制等价。

2026-09-08 的 v5 历史完整回归为 **259通过，0失败，0跳过**；PPO已有单初始化学习证据，尚未验证跨初始化稳健性。v6 奖励迁移的最新验证见 [v6 奖励报告](docs/reward-v6-report.md)；环境扩建、完整 RunEnv、Set和DT仍在后续阶段。

2026-09-08 的进度核验、边界修复与后续架构建议见
[项目审核记录](docs/project-audit-2026-09-08.md)，其中区分完整回归、小规模冒烟和历史正式验收。

## 评估种子

- 评估 seed ∈ [0, 1000)，训练 seed ≥ 100000，`eval_seeds.json` 提交后**不可变**。
- `eval_seeds.json` sha256：`38a093486535aa529d54ebfcfd535e67fe043daff8286b5740b5766a6131af9c`
- 重新生成（应字节级一致，哈希不变）：`python scripts/make_eval_seeds.py`

## 快速开始

```bash
pip install -e ".[dev]"
python -m pytest
```

完整测试需要先构建 C++ 扩展。只有 `test_cpp_env.py` 会在缺少扩展时主动跳过；适配器、
wrapper 与模型集成测试仍要求真实后端，不能把跳过当作后端通过验收。尚未构建时，
可以先运行独立的教学与验证工具测试：

```bash
python -m pytest tests/test_ordering.py tests/test_rng.py tests/test_replay.py tests/test_random_agent.py
```

`sts_lightspeed` 构建复现（Windows + MSYS2 mingw64 + Python）：先在 MSYS2 安装工具链。

```bash
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-ninja
```

然后在项目根目录的 PowerShell 中运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-lightspeed.ps1
python -m pytest tests/test_cpp_env.py -q
```

脚本按 [版本锁文件](scripts/lightspeed-lock.json) 拉取上游及 pybind11，应用 [本项目适配器补丁](patches/lightspeed-battle-env.patch)，构建扩展并复制运行时 DLL。重复运行会识别已应用补丁；遇到版本不符或补丁冲突会停止，保留本地改动。可用 `-Python`、`-Toolchain`、`-Jobs` 指定解释器、MSYS2 mingw64 的 bin 目录和并行编译数。本机验证使用 Python 3.13；扩展须用运行测试的同一 Python 构建。

原始 C++ 观测按固定容量导出，Python 规范层转成 `hand/draw_pile/discard_pile/exhaust_pile` 四个逐牌列表；非手牌区域只提供允许公开的无序多重集，不泄露抽牌顺序。手牌槽位行保留动作对应，但槽位号不作为卡牌语义特征。seed 和 RNG 计数只留在复现信息中。

正式 Python 入口：

```python
from sts import (
    Encounter,
    FlattenWrapper,
    LightspeedBattleEnv,
    MaskedRandomAgent,
    TokenWrapper,
    run_episode,
)

env = LightspeedBattleEnv()
observation = env.reset(100000, Encounter.TWO_LOUSE)
action = int(observation["action_mask"].nonzero()[0][0])
observation, reward, terminated, truncated, info = env.step(action)
# info 会记录 task_type/task_spec_id/reward_version、task_outcome、
# termination_reason 与 reward_base/reward_train；这些字段不进入模型观测。

flat_env = FlattenWrapper(LightspeedBattleEnv())
flat_observation = flat_env.reset(100000, Encounter.TWO_LOUSE)

token_env = TokenWrapper(LightspeedBattleEnv())
token_observation = token_env.reset(100000, Encounter.TWO_LOUSE)

# Agent 内部完成概率计算和抽样；接入层不持有 RNG 或游戏规则。
agent = MaskedRandomAgent(seed=20260905)
trace = run_episode(
    token_env,
    agent,
    token_observation,
)
```

规范观测仅含 `hand/enemies/draw_pile/discard_pile/exhaust_pile/global/hand_mask/enemy_mask/action_mask`；字段、shape、dtype 与信息边界见 [观测接口契约](docs/observation-contract.md)。`info` 只供复现和调试，不进入模型。

现有校准工具：

```powershell
python scripts/runlogger_replay.py
python scripts/diff_harness.py 100000 12
```

回放工具读取本机游戏的现有日志；差分工具额外依赖开发用 `build/lightspeed_probe.exe`。这些工具会区分不一致、缺少证据和范围外跳过；不得以“没有可比样本”宣称机制验证通过。正式训练入口使用 C++ 适配器，不依赖此开发探针。

## 约定

- 每个训练 run 必须落盘：commit 与实际源码快照/逐文件哈希、完整配置、任务/奖励/终止版本、环境及各 RNG seed、后端/扩展/数据指纹、`eval_seeds.json` 哈希、曲线和 checkpoint；PPO 另须保存优化器/计数/RNG/进行中任务恢复依据并验证续训一致性（[v6 §8.1](spec-v6.md)）。
- 每个 run 记录 `eval_seeds.json` 的 sha256，保证跨周结论可比。
- 决策变更先登记 `docs/decisions.md`；结算规格修订先登记 `docs/mechanics.md` 文末变更记录。


## 公开派生战斗与规则基线

新接口独立于旧31动作环境。先运行 `./scripts/build-lightspeed.ps1 -Jobs 3`；构建使用中央JSON契约与完整后端补丁。

```python
from sts.env.public_battle import PublicBattleEnv, load_scene_manifest
from sts.agents.rule_agent import RuleAgent
from sts.agents.public_runner import run_public_episode

_, scenes = load_scene_manifest()
env = PublicBattleEnv(max_actions=512)
observation = env.reset(scenes[0], 100000)
trace = run_public_episode(env, RuleAgent(), observation)
print(trace["total_reward"], trace["terminated"], trace["truncated"])
```

`python scripts/diagnose-public-scenes.py`复核99场完整派生场景的随机/规则集成；
`python scripts/diagnose-public-encounters.py`执行显式机制诊断。它们不替代正式Gate评估。
当前工程验收与未完成的新MLP/Set训练迁移见 [公开环境实施报告](docs/public-battle-implementation.md)。
