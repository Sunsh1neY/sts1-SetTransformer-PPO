# D25 S5 最小可学习检查点冻结

日期：2026-09-11。依据：spec-v6.md §9.1，D25/D27，S4预登记。

## 冻结对象与结论

冻结S4的A/B/C三组全部产物，不挑选最好的一组。环境为battle/minimal-v1，Flatten V2、MLP、31动作masked PPO；每组262144步，参数和seed见configs/ppo-s4-a.yaml、ppo-s4-b.yaml、ppo-s4-c.yaml。

三组第224轮快照均成功恢复并执行到第256轮：32轮算法指标逐值一致（吞吐不参与），轨迹与原日志尾段一致，最终checkpoint所有内容递归相等，包括模型、优化器、采样/洗牌/Torch RNG、收集器状态和元数据。最终300局开发评估JSON也完全一致。

| 组 | 恢复轮数 | 重放完整局数 | 最终checkpoint文件SHA256 |
|---|---:|---:|---|
| A | 32 | 2341 | 7e6c73d68669914a410536984a5fc2c24cd0e9e8a971d4fc70396c683f6ff78e |
| B | 32 | 2318 | 42f7274ca46170c4a378c80499bb744c2ed8c68269bf2453efd829b9a8b9667f |
| C | 32 | 2304 | d3309cfffe8adad468bd61d040527cc702d6d0b36b151e41f24986b4a55e76f9 |

这些重放局不计为新训练样本。原run未修改；验证输出在runs/ppo-s5-verification-20260911/verification.json。
完整回归278 passed、0 failed、0 skipped；两个S5脚本Ruff通过。S4结果见ppo-s4-report.md，末轮EV负值仍保留诊断。

## 后端指纹差异核验

- 历史S3元数据：后端e55552b105755889b1130967420f37591cc6e74433fcac370d8218ff7bda4ec9，适配补丁619d7d1c00ec4fd9c1e1499d9a3b37d84d8b98f01cc932d68f61be07ce2e7a6e。
- 当前S4三组：后端a4b1745d79d848354da8783416d4728a8aec255d359e93687c62cd1ef9d16fbf，适配补丁dfe95d2bbd93300932d187c969b6b6ea9aa4a4783da4169b1b32bd1160cb878c。
- 项目提交fba803b→96e66e4的补丁差异明确增加D27 rewardForStep(terminal, won)终止判断、退出HP合法性校验，并将WIN_HP_LAMBDA改名ALPHA_HP，系数仍为0.5。二进制修改时间为2026-09-08 17:43:57，晚于S3训练。
- 上游HEAD仍为7476a81954020087da31d41d16fddf475746ec2d；json和pybind11子模块分别匹配锁文件。当前三个适配源文件的Git blob均匹配登记补丁目标：af78f733a11901e3f6858726f5c02a144149ff1e、32dd4eda223aa5e0252345341be9d7dfa95ddba2、03a7b1e3fe06c11c7f4eb2f2e462d2a528082050；补丁反向检查通过。
- 因此指纹变化有明确的D27源码版本变更对应，不是无记录的上游漂移。本次不声称旧、新二进制相同，也未做旧二进制全轨迹等价验证或可复现编译验证。

## 本地归档与复现

冻结包：runs/ppo-s5-freeze-20260911/ppo-minimal-s5.zip；外部收据receipt.json记录包SHA256、文件数和代码提交。
包内s5-file-manifest.json逐文件记录SHA256，归档完成后逐项读回校验。
内容包括三组原始运行（source.zip、配置、逐局数据、TensorBoard、全部checkpoint、评估及元数据）、当前项目源码和文档、锁定上游及子模块源码、实际pyd/DLL和构建配置、S5验证证据。

S4三组训练时的精确源码归档SHA256均为f7f677e0fa69a487a31d2ed0bf503a714731c040d00af2303ad1c21884697ad7。该快照是训练时源码依据，S5提交新增验收工具与报告，不改训练算法。

在独立目录解压并核对清单后，准备与metadata.json一致的Windows Python 3.13及依赖，安装项目，再使用包内后端；不要为恢复旧checkpoint而无条件重建并覆盖pyd。跨平台运行及全新机器安装未验证，Python解释器、Python包和MSYS2工具链未打包。

```powershell
python -X utf8 scripts/verify-ppo-s5.py --output runs/ppo-s5-reverify
python scripts/run-ppo-minimal.py --config configs/ppo-s4-a.yaml --resume runs/ppo-s4-a-20260911/checkpoint-0224.pt --output-dir runs/ppo-s4-a-replay
```

输出目录必须不存在；A可换成B/C对应路径。前一命令验证三组恢复和评估；后一命令只执行A剩余预算，不增加原预算。

工程结论：S1–S5最小闭环完成。下一工程点为M1候选卡数值核验，再M2容量契约；不代表中等档、Gate 2/3或Set Transformer完成。S5用户理解尚待独立复盘。
