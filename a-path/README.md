# STS A 路径任务包

日期：2026-09-13。

## 使用

将ZIP直接解压到项目仓库根目录。它会生成：

```text
agent-tasks/a-path/
├── README.md
├── sts-a-path-implementation-v1.md
├── codex-astra-agent-prompt.md
├── a-path-acceptance-cases.json
├── verify-a-path-math.py
└── math-verification-report.json
```

在Codex中打开这个本地仓库，使用已选择的Astra模型，把 `codex-astra-agent-prompt.md` 中分隔线之后的内容作为新任务发送。

仅使用单独的Markdown文件时，也请保持上述路径，或在提示词中修改任务书与fixture的实际路径。

## 本包是什么

任务书覆盖已选定的A路径：共享Set编码器、保留PMA、任务Query选择来源、来源Pointer选择目标、一次env.step、联合PPO概率、测试、数据边界及受限训练。

第一阶段的出牌、药水、特殊操作共同归一化；第二阶段仅在所选来源的合法目标间归一化。不是旧的 `softmax(b+t)` 联合原始评分，也不是两个环境步骤。

## 数学核验

```bash
python agent-tasks/a-path/verify-a-path-math.py
```

只有Python标准库即可完成概率、熵、归一化和反例核验。安装PyTorch时会额外运行CPU float64自动求导核验。

```bash
python agent-tasks/a-path/verify-a-path-math.py --require-autograd
```

`math-verification-report.json` 是本包独立数学脚本的实际运行结果。它不包含游戏模拟器、GPU训练、用户仓库测试或策略学习结果。

## 证据范围

本包编写时只读核对了公开远端代码，未更改仓库、未在用户电脑训练。远端快照可能落后于本地；Agent必须保留本地已完成机制，再实施任务。完整证据与来源见任务书第0节和第15节。
