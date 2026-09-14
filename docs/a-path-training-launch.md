# A路径正式训练启动工程记录

> 历史阶段记录：A 路径现已依 I5 合入 main；本文中的旧工作区路径、待实现状态和当时启动记录保留历史身份。当前入口与验收见 [主线整合报告](a-path-main-integration-report.md)。


2026-09-14。最新授权I4：跳过独立32k smoke，在必要工程短预检完成后直接启动四小时受限训练；实际开始后结束当前对话。此文件登记启动依据，不提前声称训练完成或学习改善。

## 采样与数据

- 本轮是comparison-battle-v2完成后的Set-only扩展，不改旧MLP/Set冻结协议。
- train为33个已知来源关联组、36run、39种完整卡组、390个条件/遭遇初态配置；27组各1种deck，6组各2种。当前登记开发来源在组、run和完整内容上均无重叠；未创建新保留集。
- 中性source-group均匀→组内deck均匀→condition均匀→encounter均匀。独立环境seed流，训练空间从10^12开始，开发评估使用95000000附近预登记seed；不读source原seed入模型。
- 正式PPO从完整rollout全局随机排列，minibatch64；无组别配额、无固定env分类绑定。简单/过渡/组合只作诊断与评估标签。
- 正式注册池sts/env/a-path-training-pool.json锁定内容、来源、条件、范围及哈希；新APathEnv严格验证完整登记初态与用途，train不经过diagnostic。旧Ironclad机制入口仍不开放泛化train。

## 真环境与资源证据

39种训练deck×2条件×5遭遇：随机完整合法动作策略390局、未训练A路径390局，均自然终止且有battle_exit，0异常/0截断。前者7801条transition，后者6493条；最大实体数分别87/160，真实选牌159/147步。逐场证据runs/environment-integration/a-path-candidate-runtime.json。

另运行开发侧35种内容×2条件×5遭遇×2seed，共700局随机策略工程检查，详见a-path-development-runtime-check.json。它只证明当前配置的运行路径，不是学习结果或全组合覆盖。

容量沿用已限定原五遭遇的全卡每决策最多15个累计分配增长契约，并逐步动态验证。当前初态最多39卡、512决策，累计上界7719，低于后端int16界；后端队列已有checkedCapacity。新外部资源边界在完整决策后实体达到448时截断，保留完整最终观测并自举；硬边界512，不删除实体。超出增长证明或硬边界立即作为异常停止，不伪造成失败0。

动态padding与显存拆批：逻辑minibatch仍64个全局随机样本，按其实际长度在内部拆微批，按样本数累积梯度并只裁剪一次梯度；不改变该minibatch的样本或分组比例。优势归一化在逻辑minibatch上计算。长样本不会被静默丢弃。

## PPO与恢复

四层SAB64维4头FF128、单seed PMA、两阶段联合logp、一个PPO ratio/clipping、精确熵，FP32/dropout0。8环境×128步，minibatch64，4epochs，LR2.5e-4按每初始化262144步总预算退火，Adam eps1e-5，gamma1、lambda0.95、clip0.2、entropy0.01、value0.5、grad clip0.5。奖励不改。

轨迹保存不可变序列化样本、固定旧logp/Value/Advantage/return、动作分解和终止/截断信息。checkpoint包含模型、优化器、进度、全部采样与shuffle RNG、活动场景和完整动作序列。恢复重放校验公开实体/候选哈希，重新绑定当前snapshot/decision_id；不同代码、后端、数据版本明确拒绝。更新边界快照支持精确续训，故障采集/更新中途快照只作诊断，不冒称可精确恢复。

## 验证

- 全仓CPU回归1277 passed、1 skipped（CPU解释器跳过CUDA）；60.72秒。此轮回归后增加真实选牌恢复断言及修订入口元数据，随后专项复核通过。
- CUDA解释器上CPU/CUDA真实更新、下一更新精确一致、RNG和活动环境重放、真实选牌凭据重绑定共5项通过；最终一次8.00秒。
- 完整8×128 CUDA更新预检通过，记录在apath-full-update-preflight.json；较保守微批16下51.49秒、峰值显存124470784字节。
- 根据实测显存余量改为最多使用完整64微批、超注意力界才拆分；另做64条真实transition与完整minibatch64更新预检通过，8.33秒、峰值151150592字节。以上是工程短预检，不是32k smoke或正式学习结果。
- spec检查通过；正式启动前保存独立本地里程碑，不push。

## 后台执行与交付位置

入口scripts/run-a-path-ppo.py，计划目录runs/a-path-ppo-20260914-v1。实际状态以status.json为准。最多三个初始化，每个最多262144个真实训练transition；四小时包含本轮训练评估，预留评估和保存时间，与步数上限取早者。学习率仍按既定总步数，不因时间提前结束偷偷重新定义预算。

程序保存source-snapshot.zip、每初始化initial/latest/final checkpoint、metrics.jsonl、episodes.jsonl、初始/最终两阶段随机评估，以及随机策略和规则共同切片。评估分别报告三个内容组，规则遇到未覆盖牌/新选择明确标gap，不回退成随机冒称规则。预算不足的评估或初始化明确记录未完成，错误时保存可用快照并停止，不自动延长。

训练日志可直接查看；后台最终写run-report.json和run-report.md。训练实际启动后当前对话结束，不假称后续结果已验收。旧主目录后端仍保留，实际运行在sts2-integration。
