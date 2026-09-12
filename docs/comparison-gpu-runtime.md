# 固定环境PPO的GPU运行环境

日期：2026-09-12。已实际安装并验证CUDA运算。

- GPU：NVIDIA GeForce RTX 3060 Laptop GPU，6GB显存。
- NVIDIA驱动：560.81；nvidia-smi报告CUDA支持12.6。
- 独立Python入口：`.venv-gpu/Scripts/python.exe`，基于原Python3.13建立，保留原CPU环境。
- PyTorch：`2.6.0+cu126`。未更新GPU驱动或修改系统代理。
- wheel：`torch-2.6.0+cu126-cp313-cp313-win_amd64.whl`。
- 官方索引SHA256：`a1ce724eb9813fcd05b99cb8b652b2d02f447caba65f1469abd7d50af5e5323f`；下载文件实测一致。

官方源单连接慢，分段尝试后改由阿里云PyTorch镜像取得同一wheel，并按PyTorch官方索引的SHA256校验后安装。原始wheel和分段下载脚本留在ignored reference中，不提交大文件。

安装方式：先`python -m venv --system-site-packages .venv-gpu`，再用该环境的Python安装已校验wheel：

```powershell
.venv-gpu/Scripts/python.exe -m pip install --no-deps --ignore-installed reference/torch-2.6.0+cu126-cp313-cp313-win_amd64.whl
```

CUDA实际验证：`torch.cuda.is_available()`为True，设备名称正确，512×512 CUDA矩阵运算成功。原CPU运行时仍可用，GPU进程必须使用上面的独立Python入口。

## 已执行的预检

```powershell
.venv-gpu/Scripts/python.exe scripts/run-comparison-ppo.py preflight --output runs/comparison-preflight-20260912-gpu-v1 --device cuda
```

每种模型测4轮，随后保存/恢复并分别继续1轮，模型权重逐项完全一致。

| 模型 | 第2–4轮耗时（秒/512步） | 预检峰值CUDA分配 |
|---|---|---:|
| MLP | 1.143 / 1.042 / 1.035 | 101605888字节 |
| Set | 1.440 / 1.583 / 1.392 | 132204544字节 |

首次调用包括CUDA初始化，不用它估计稳定吞吐。该值是资源预检，不保证每一轮耗时相同。训练中环境模拟仍在CPU运行，神经网络前向、反向和优化器在GPU运行。

预检冻结每组138轮×512=70656个transition；MLP/Set各两组。正式运行入口：

```powershell
.venv-gpu/Scripts/python.exe scripts/run-comparison-ppo.py run --plan runs/comparison-preflight-20260912-gpu-v1/plan.json --output runs/comparison-ppo-20260912-gpu-v1
```

以上目录已用于本次运行，脚本拒绝覆盖。正式结果以对应summary.json及docs/comparison-ppo-report.md为准，不以预检成功代替训练通过。
