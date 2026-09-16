> **Historical navigation notice (2026-09-16):** This is a dated phase record or instruction set, not a current work order. Use the [documentation map](README.md), [spec-v6](../spec-v6.md), and registered amendments for current work. Original commands, paths, budgets and evidence below retain their historical scope.

# S3 PPO来源与实现对照

核验日期：2026-09-08。PPO计算从CleanRL的`cleanrl/ppo.py`改编，保留MIT声明
（`licenses/cleanrl-license.txt`）。唯一上游代码版本：
`fe8d8a03c41a7ef5b523e2e354bd01c363e786bb`；文件SHA256为
`d8dfbb7ac0b21e747b77d6e6673e566db4d6cdacc83bcebcd19cf87ad0e459ae`。
指纹集中保存在`scripts/cleanrl-lock.json`。本地查阅副本位于被忽略的
`third_party/cleanrl-source/ppo.py`。

## 逐段对应

| CleanRL起点 | 本项目`sts/train/ppo.py` | 保留与调整 |
|---|---|---|
| rollout预分配、vector env、action/value | RolloutCollector、PPOAgent | 8个同步环境；结构化FlatBatch；Agent独立RNG；原mask随观测存储 |
| delta和lastgaelam递推 | compute_gae | gamma依D20为1，lambda=0.95；终止与采样切段分开，当前环境外部truncated明确拒绝 |
| logratio、ratio、两个pg_loss取max | ppo_loss | 原算法；只用采样当时的mask重算log-prob；旧数据detach |
| minibatch优势归一化 | ppo_loss | 原算法；每批至少两个样本 |
| value clip取较大平方误差 | ppo_loss | 原算法；value_loss含0.5系数，再乘vf_coef |
| entropy、approx_kl、clipfrac、grad clip | ppo_loss、train_iteration | 原公式，梯度非有限立即报错，指标按所有minibatch汇总 |
| orthogonal初始化、Adam eps、线性学习率衰减 | PPOTrainer | 保留；沿用S2共享MLP主干与embedding，不照搬上游两个独立64维网络 |
| TensorBoard | run-ppo-minimal.py | 记录训练曲线，并保留JSON逐局记录、源码ZIP及配置 |

GAE手算入口在`tests/test_ppo_math.py`。真正终止的transition不使用下一状态value；
采样rollout末尾若战斗未完，仍使用下一状态value。终止后reset出来的新局value不可
计入上一局。函数另区分episode_ends以便测试外部时间截断的数学语义，但当前正式
采集器只接受D20规定的terminated硬超时。

## S3固定运行约定

首轮预算262144个environment transition，8环境×128步rollout，共256次PPO更新。
每次4个epoch×4个minibatch；学习率0.00025线性衰减，Adam eps=1e-5，clip=0.2，
entropy系数0.01，value系数0.5，grad norm上限0.5。配置见`configs/ppo-minimal.yaml`。

环境seed只在[1000000,2000000)逐局分配；初始化600000、策略采样610000、minibatch洗牌
620000独立。训练前后开发诊断使用900000起的300局（三遭遇各100）和独立Agent RNG。
正式eval_seeds.json只记录哈希。动作仍按掩码后分布采样；前后固定同一诊断配置。

checkpoint保存权重、优化器、iteration、配置、采样RNG、minibatch RNG、torch RNG，
以及每个进行中战斗的seed和已执行动作。恢复时重放当前战斗，无需序列化C++私有对象；
独立回归须验证恢复后的下一批轨迹、更新指标和权重与不中断时完全一致。

S3只做一次初始化的训练与开发诊断，判断管线能否学习；S4再做预先约定的多初始化
配对验证，S5冻结代码与配置。当前不以一次开发CI结果声称跨训练seed可靠。

## 来源登记

- PPO-01：A级，一手代码，2026-09-08。[固定提交的ppo.py](https://github.com/vwxyzjn/cleanrl/blob/fe8d8a03c41a7ef5b523e2e354bd01c363e786bb/cleanrl/ppo.py)。由官方仓库读取并核验文件SHA256，算法实现依据。
- PPO-02：A级，作者项目文档，2026-09-08。[CleanRL PPO文档](https://docs.cleanrl.dev/rl-algorithms/ppo/)。SearXNG命中，Tavily提取核对监控量与实现说明；与PPO-01同属作者来源，不计作独立实验复现。
- 检索说明：cross-search使用SearXNG和Tavily；Doubao未提供工具。SearXNG页面读取被其安全策略拒绝，未尝试放宽策略，改用Tavily读取原文。
