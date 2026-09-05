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
- 现有真实游戏日志用于有限字段校准。当前不扩日志工具，缺少的字段明确记为未验证；后续更大范围测试发现差异后再处理（D20）。此状态不代表所有游戏机制已被证明正确。
- `eval_seeds.json` 已固定；环境主 RNG 为 xorshift128+，洗牌临时使用 Java LCG，详见 [机制规格](docs/mechanics.md)。

裁定与边界见 [决策日志](docs/decisions.md)；冻结的旧研究文档不作为实现依据。

2026-09-05 本机验收：**128 项测试全部通过**；新版 C++ 环境 10000 场随机战斗无崩溃、无非法动作异常、无硬超时，60 场完整轨迹重放一致。单进程约 11.7 万步/秒；两条 wrapper 已接通统一 31 维 Agent 决策接口并通过三遭遇终局测试。这些结果验证基础运行，不代表与真实游戏全部机制等价。完整 wrapper 路径的稳定性与性能留到 Week 4 T5 单独验收。

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

观测按固定宽度存储，字段顺序由扩展的 `HAND_FEATURES`、`ENEMY_FEATURES`、`PILE_FEATURES`、`GLOBAL_FEATURES` 给出；手牌和敌人使用对应 mask 区分有效项，抽牌堆和弃牌堆只提供无序卡牌计数，不泄露抽牌顺序。seed 和 RNG 计数只留在复现信息中。

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

规范观测仅含 `hand/enemies/draw_pile/discard_pile/global/hand_mask/enemy_mask/action_mask`；字段、shape、dtype 与信息边界见 [观测接口契约](docs/observation-contract.md)。`info` 只供复现和调试，不进入模型。

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
