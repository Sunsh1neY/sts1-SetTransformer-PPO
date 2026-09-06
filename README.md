# STS RL Agent

Headless《杀戮尖塔 1》Ironclad 战斗环境 + A/B 两族模型对照（Set Transformer + PPO vs Decision Transformer）。正式训练后端为 lightspeed C++，Python 模拟器保留教学与验证用途。真实目标：通过工程实践理解 Transformer 原理，游戏是载体。

**唯一执行依据：[`spec-v4.md`](spec-v4.md)**（2026-09-01 定稿）。`spec-v3.md` 及更早版本为冻结愿景，仅供对照。

> 目录名 `sts2` 是 v3 时代（STS2 方案研究）的历史遗留，不改名；实际规格来源是 STS1。

## 当前状态（最小切片基础环境）

- 正式后端：`sts_lightspeed` C++，当前只开放 A0 的 Jaw Worm、Cultist、双虱遭遇。Python 模拟器保留教学及局部回归用途。
- 运行接口：项目包入口 `LightspeedBattleEnv.reset/step/action_mask/observation`，内部复用 C++ `IroncladBattleEnv`。动作编号为 `slot * 3 + target`，30 为结束回合，无目标卡只使用目标 0。
- 基础奖励：非终局 0；胜利 `1 + 0.5 * 剩余HP / 最大HP`；失败及硬超时 0。当前不实现势能整形，训练及 DT 累计回报使用 γ=1（D18/D20）。
- 硬超时是任务内失败：返回 `terminated=true`、`truncated=false`、`info.timeout=1`，训练时不继续自举。
- 已确认模型设计：选牌保留实体与动作的对应关系（D17）；状态只使用玩家可见信息（D19）。模型代码按原排期实现。
- 当前输入协议已迁移为 D24 逐牌实体 V2：四区卡牌记录使用稳定注册 ID、location、升级与费用 known/valid 语义；Flatten/Token 共用同一准备路径，模型 embedding 仍按原排期实现。
- 现有真实游戏日志用于有限字段校准。当前不扩日志工具，缺少的字段明确记为未验证；后续更大范围测试发现差异后再处理（D20）。此状态不代表所有游戏机制已被证明正确。
- `eval_seeds.json` 已固定；环境主 RNG 为 xorshift128+，洗牌临时使用 Java LCG，详见 [机制规格](docs/mechanics.md)。

裁定与边界见 [决策日志](docs/decisions.md)；冻结的旧研究文档不作为实现依据。

当前进度：Week 4 与 D24 实体迁移已收口，Week 5–6 的 M1 卡表来源与候选范围审计已
开始，任务拆解见 [Week 5–6 计划](docs/week-5-6-plan.md)。

2026-09-06 D24 实体版本机验收：**146 项测试全部通过**；四条路径各以 10000 个唯一训练配置重复三轮，异常、非法动作、硬超时与奖励契约错误均为 0，60 场完整轨迹重放一致。raw / dict / Flatten / Token 完整路径单核中位数约为 14702 / 5882 / 3841 / 3790 steps/s，均超过 Gate 1 的 2000 门槛。详见 [实体基础验收报告](docs/entity-foundation-report.md)。这些结果验证当前切片，不代表与真实游戏全部机制等价。

## 评估种子

- 评估 seed ∈ [0, 1000)，训练 seed ≥ 100000，`eval_seeds.json` 提交后**不可变**。
- `eval_seeds.json` sha256：`38a093486535aa529d54ebfcfd535e67fe043daff8286b5740b5766a6131af9c`
- 重新生成（应字节级一致，哈希不变）：`python scripts/make_eval_seeds.py`

## 快速开始

```bash
pip install -e ".[dev]"
python -m pytest
```

Python 测试可独立运行。正式后端的测试需要先构建 C++ 扩展；未构建时会显示跳过，不能把跳过当作后端通过验收。

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

- 每个 run 必须落盘：git commit hash / 完整配置 / 随机种子 / `eval_seeds.json` 哈希（spec-v4 §8.1）。
- 每个 run 记录 `eval_seeds.json` 的 sha256，保证跨周结论可比。
- 决策变更先登记 `docs/decisions.md`；结算规格修订先登记 `docs/mechanics.md` 文末变更记录。
