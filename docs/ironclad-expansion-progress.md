# 全卡扩展实施记录

每个小里程碑独立提交；提交号由 `git log -- docs/ironclad-expansion-progress.md` 查得，避免记录自身提交号造成循环。未列为通过的阶段保持未完成。

## E2a：直接效果七类（2026-09-12）

- Clash、Hemokinesis、Bloodletting、Intimidate、Limit Break、Offering、Shockwave基础/+接入注册、C++公开导出与统一实体模型；当前94/150版本。旧public白名单未扩展。
- 36项定向测试通过：Clash非攻击手牌限制、自伤与Blood for Blood事件、实际攻击、全体减益、Artifact先消耗Weak、Limit Break与Flex到期、Offering抽牌及No Draw、14版本新模型前向。
- 数值与机制依据为docs/ironclad-card-audit.md对应七牌行及本地后端真实分支；没有照抄正版代码。此批不生成新实体、不增加选择或自动打出，现每decision15增长检查仍适用；重建后更新注册/二进制指纹。旧U4/U6checkpoint保持历史身份，当前指纹变化拒绝精确恢复。
- 生成补丁已保存到patches/lightspeed-ironclad-expansion.patch。治疗/随机/自动耗尽继续下一小批；不宣称94版本全部组合穷尽。

## U6b：实施简化输入v3与资源保护（2026-09-12）

- U6a已提交75d102d，先登记用户裁定。随后实现115维卡牌输入、set-v2模型：移除伤害关系bias/评分输入，保留格挡、实例增伤与费用恢复信息；新增已知顶牌字段和严格区域/唯一性检查。
- 取消统一实体466张主动截断，保留资源、编号和当前内容生成保护；真实哨卫场景越过旧阈值仍继续。加入collate_chunks按注意力资源拆批。旧MLP/卡牌Set采集契约不变。
- `pytest -q`：802 passed in 72.73s，零失败；115维生成字典对拍、check-spec-v6、覆盖检查通过（80/150准入，7冻结文件）。16步工程采集与下一次更新恢复一致；无正式长训。
- 实施与限制见docs/entity-input-v3-contract.md：顶牌当前为输入接口验收，真实置顶/跨区选牌仍未准入；非手牌恢复费用的未来完整导出仍需随机制实施；长期收益奖励明确登记待修改，当前reward不变。
- 首次本地变更脚本遇Windows默认GBK解码错误，统一UTF-8后修复；旧字典生成器不适配新字段曾失败，已更新并对拍通过，不计为机制缺陷。

## U5审计：卡牌逐维输入及协作阻塞（2026-09-12）

- 应用户要求参照敌人阻塞分组整理 [卡牌输入审计](card-token-input-audit.md) 与 [122维逐维字典](card-token-dimensions.md)。区分122维原始输入、64维学习表示、关系特征、全局状态及模型外路由；列出剩35类70版本的互斥分组。
- 明确新增字段对应Rampage/Blood for Blood/Corruption/True Grit+与未来牌的需求；登记C1费用/公开记忆、C2连锁资源、C3目标生命周期、C4可选多效果编码建议，尚未据此修改接口契约。
- `python scripts/audit-card-token.py`：122维顺序与实际编码对拍通过；三组针对性测试 `test_unified_entities.py`、`test_ironclad_dynamics.py`、`test_true_grit_selection.py` 共55 passed in 4.30s；覆盖检查150目标、80扩展准入、69旧准入、7冻结文件通过。
- 本轮仅新增审计文档、生成核对脚本和本记录；无后端/模型修改，无训练，无全仓重跑；不将静态风险或合成接口夹具当成真实机制验收。

## E0a：隔离版本与覆盖台账（2026-09-12）

- 基线：独立目录 `sts2-full-card`，分支 `codex/ironclad-full-expansion`，起始快照 `50b756e`。原对照报告在检查时仍为 running；F0最终冻结与同步未完成。
- 用户授权独立开发并行，已登记决策与规格增补；不启动额外训练。
- 新建独立扩展契约与150版本覆盖台账，81个缺失版本逐项分配E2–E6；35类69版本继承状态与扩展接口验收分开。新接口初始验收0/150，不代表旧接口失效。
- 冻结7个文件哈希：旧public/对照/真实批次契约、对照模型及训练实现、旧后端补丁和eval_seeds。新后端修改使用增量补丁。
- 验证：`python scripts/check-ironclad-expansion.py` 检查150唯一版本、批次分配、证据路径和冻结哈希；`python scripts/check-spec-v6.py` 检查规格。
- 未完成：E0中的F0最终冻结；E1–E7尚待实施。50–90小时为原估算，本小步不足以重估全量工期。

## E1a：独立后端入口与具名动态字段（2026-09-12）

- 新增 C++ `IroncladExpandedBattleEnv` 和 Python `sts.env.ironclad.IroncladEnv`；旧Public入口的schema与字段不变。Python旧包装仅抽取可覆写规范化方法。
- 新观测明确 NORMAL 阶段、无选择对象；新增实例增伤、Strike类别、费用类别、有效耗尽及Combust失血字段。旧内容以外仍拒绝，正式训练/旧数据自动迁移仍关闭。
- Barricade/Corruption的布尔导出分支已实现；Rampage增伤读取具名值。对应牌尚未准入，因此这些路径只记实现、未通过实战机制验收，不宣称R02/R03关闭。当前不导出非手牌临时费用或隐藏ID。
- 后端差异保存 `patches/lightspeed-ironclad-expansion.patch`，基础补丁不变；构建脚本新增显式ExtraPatch参数，不传参数仍走旧流程。
- 标准独立构建通过：`./scripts/build-lightspeed.ps1 -Python ./.venv/Scripts/python.exe -Jobs 1 -ExtraPatch ./patches/lightspeed-ironclad-expansion.patch`。全新本地CMake缓存，单编译任务，无GPU训练。
- `python -m pytest -q tests/test_ironclad_expansion.py tests/test_public_battle.py tests/test_real_deck_batch.py`：98 passed，5.14秒。新增76项，其中69个继承版本逐动作对照新旧入口，检查完整四区、mask、奖励、终止与截断final_obs。其余验证语义可辨识、隐藏字段拒绝、未验收卡及训练拒绝。
- 扩展接口继承准入69/150，新增准入0/81。此对照证明适配器不改变旧行为，不是对正版150版本的独立机制校准。
- E1未完成：费用有效期、真实动态/状态组合、候选路由和全卡容量证明；E2–E7未完成。下一小步把新增语义接入独立Set编码并验证输出与梯度。

## E1b：新增语义接入Set与模型边界验证（2026-09-12）

- 独立 `sts.models.ironclad` 复用冻结ComparisonActorCritic的QKV/SAB/PMA结构，仅提供Set，扩展逐牌输入6维、全局输入1维。原比较模型与训练源码哈希不变。新增语义不只停留在JSON输出。
- 同名不同实例属性保留独立行；基础字段与增量字段按相同排序对齐。当前模型沿用64位置作为继承内容开发边界，超过容量明确拒绝；这不是全卡生成/截断证明。选择阶段仍拒绝，尚无候选头。
- 首轮模型探针3项失败：重复引用夹具触发逐项删除副作用，已改为独立字典记录；另外两项测试误用未mask的forward输出，已按模型distribution接口检查合法概率与置换不变性。未修改旧模型来迁就测试。
- 复测 `python -m pytest -q tests/test_ironclad_model.py tests/test_comparison_training.py`：13 passed，7.72秒。覆盖新增各字段进入数值输入、重复实例对应、非手牌置换下合法概率/价值不变、mask、有限梯度、同版权重逐值恢复、旧维度权重拒绝和容量拒绝。
- 权重恢复测试不等于PPO collector/optimizer/RNG精确续训；后者在E3/E7接入多阶段轨迹后验收。测试内旧比较trainer的小规模更新为原有回归，不是新正式训练；未占用原30分钟正式训练预算。
- 当前准入仍69/150，新增0/81；E1整体尚未完成。下一步是E1c的费用有效期、状态实战探针与容量/候选路由，之后才可按E2批次开放新牌。

## 第一批集成复核（2026-09-12）

- 提交链：E0a `cb5aebd`；E1a `9743671`；E1b `1e0a08b`。这三个小里程碑完成，不代表E0/F0或E1整体已完成。
- 首次完整回归：696 passed、7 failed、9 errors、1 skipped；定位到独立worktree未复制被忽略的历史夹具。两份语料补齐后仍缺记录器源码与历史集成记录，继续复制必要输入；没有修改旧测试断言。
- 共复制112个历史测试输入，位于新目录reference，逐文件哈希在 `reference/expansion-test-inputs.json`；这些是历史夹具，不冒称本次新集成成绩，不提交公开语料及仲裁源码。
- 最终 `python -m pytest -q`：713 passed，25.73秒，0失败、0跳过；`python scripts/check-ironclad-expansion.py` 与 `python scripts/check-spec-v6.py` 通过；增量后端补丁反向适用检查通过。
- 对原目录起始快照200文件复核，内容均未变；冻结7项哈希不变。后续只读看到原对照报告status=complete且有4组结果；没有由本工作流停止进程，也没有据此替代原对照工作流的恢复与统计验收，F0仍待正式同步。
- 下一工作点：先完成E1c真实费用/状态探针及阶段/容量安全设计；按证据更新接口版本，进入E2时逐卡逐版本开放并记录行为测试。75类/150版本目标不降级，当前仅69版本继承准入，81新增版本仍待实现与验收。选择阶段、公开置顶记忆、生成闭包、多阶段PPO与checkpoint迁移均未完成。

## E1c：五类动态/状态卡实战探针与独立卡表（2026-09-12）

- 实现Rampage、Blood for Blood、Barricade、Corruption、Combust各基础/升级；逐实例、状态、费用以及与Strength/Burn/Metallicize/Feel No Pain/Sentinel的关联断言通过。证据、范围和未关闭组合见 docs/ironclad-dynamic-probes.md。
- 引入独立注册表，保留旧40项目ID，新卡不再受旧白名单或旧编码器卡表限制。C++新增构建指纹并由Python检查；观测v2、Set编码v2，新增印刷费与当下有效费/known/来源字段。
- 首轮两个Corruption断言失败：错误地将旧base_cost当作印刷费；源码核验其为战斗修改费，修正测试并分别保留印刷费，未改后端结算。其他探针通过。
- 标准增量构建通过；针对新增机制/继承入口/新旧模型的回归121项通过（正式训练未启动）。
- 准入从69增至79/150，新增10/81版本通过当前范围验收；这五类的选牌/复制关联仍依赖后续阶段，E1/E4/E5整体均不宣称完成。
- 当前容量证明仅覆盖旧内容加五类不生成卡探针；下一步加入在完整决策点切段的独立采集包装，拒绝超初始容量，不丢final_obs实体。

## E1d：完整决策点容量采集与受控集成（2026-09-12）

- E1c提交为 `3533207`。本小步新增 `sts.env.ironclad_collection.IroncladCollectionEnv` 和独立容量契约，64实体/50阈值/15余量，初始<=49、最大512动作。超界初态整副拒绝，不删牌。注册表或运行契约变化时必须重做证明。
- C++单独导出累计分配计数用于info；Power从四区消失不回收ID。每步检查实际分配增长，完整结算后才截断，保存原合法mask；同时记录决策、出牌、回合结束及药水次数，选择次数当前为0。
- 6项容量专测通过：真实Power Through由49到51实体切段、最终观测完整编码；真实Set最终价值传入既有GAE，验证自举且不跨reset；两预算同时触发、Power数量与累计ID区别、reset失败失效、内容hash漂移拒绝。
- `python scripts/diagnose-ironclad-expansion.py --output reference/ironclad-integration-e1d.json`：100局、1919个transition，99自然结束、1容量截断、0异常/非法动作，随机策略19胜；最大52实体，耗时5.56秒。夹具为五类×两版本×五遭遇×两配置，明确为合成受控卡组，不是人类真实卡组或学习收益证据。
- 唯一截断为Rampage夹具的Three Sentries，原因external_card_capacity；截断不计作失败。每个过程状态及最终状态都执行Set编码完整性检查。原始种子/动作轨迹、代码/后端/契约指纹已落在上述被忽略报告；报告SHA256为 `a4492e11d80cc7cdc6501b53d65d1c9b2ec2557f9a9cab5cf8af50c21b26600e`。
- 最终全仓 `python -m pytest -q`：751 passed，25.02秒，0失败/0跳过；规格及覆盖台账检查通过，冻结7项哈希不变。标准增量构建与补丁反向适用检查通过。
- 原目录只读核对发现6份文档相对初始化快照已有更新：AGENTS.md、spec-v6.md、docs/decisions.md、docs/comparison-m3-training.md、docs/real-deck-training-plan.md、docs/week-5-6-plan.md；本工作流未写这些原目录文件，未覆盖或自动合并。原AGENTS已记录对照收口与4份checkpoint恢复，扩展分支F0最终归档同步仍单独处理。
- 当前79/150版本，余71版本；E1中的阶段路由/公开记忆与更多费用语义仍未完成，本次不宣称E1或全卡完成。下一步进入真实选牌阶段接口骨架和路由验证，保持多候选不自动代选，随后推进E2/E3及剩余批次。正式扩展PPO/checkpoint迁移仍待后续。

## E1e：独立单选候选与一次性路由（2026-09-12）

- 核对后端SINGLE_CARD_SELECT的16位牌区索引与多选10位集合编码的区别。新增SelectionRouter，公开语义与私有索引/凭据分离；跨区排序同步路由，重复卡不合并，凭据拒绝跨环境、过期和重复消费。
- 候选使用封闭语义字段白名单；错误发布、reset或消费使旧路由失效。组件不推断合法性、不自动代选，也不将强制唯一选择制造为策略步骤。完整边界及checkpoint重放注意事项见docs/ironclad-selection-protocol.md。
- 15项路由测试通过；连同继承入口/容量回归97项通过（6.24秒），覆盖台账及7项冻结哈希检查通过。
- 尚未接入真实CARD_SELECT、Set候选头或PPO；运行时准入仍79/150。下一小步用True Grit+接通真实暂停/选择/续跑，再推进跨区卡牌。

## U1／E1f：True Grit+真实单选与resolving完整性（2026-09-12）

- 用户转向统一实体后，先提交U0架构/接口文档 `d8a513b`。此前E1e路由组件提交为 `6e7bb40`。停止为旧卡牌Set新增选择头，真实机制与路由继续复用。
- C++接通EXHAUST_ONE的真实暂停、合法候选索引与SINGLE_CARD_SELECT续跑；Python用一次性SelectionRouter接受具名动作，普通66动作不借用目标列选牌。
- 实测True Grit+暂停时已离开四区，尚未完成最终移区；新增公开resolving卡实体，仅导出当前已知来源，不dump队列或隐藏ID。观测升级v4，Python规范化与资源计数包含第五区；旧Public字段/白名单不变。
- 实战测试验证格挡9、指定Sentinel增能量、True Grit最终移区、0/1候选自动处理、Corruption＋Feel No Pain两次耗尽触发、选择点预算截断完整性、过期与重复提交。6项专测通过；相关机制/旧编码/容量回归124项通过。
- 当前准入80/150，仍仅EXHAUST_ONE真实阶段。其他跨区任务、公开置顶记忆和完整PPO恢复未完成；统一实体模型实现与验证另按U2–U4登记。

## U2／U3：统一实体编码、候选评分与动态模型（2026-09-12）

- U1提交 `bf51099`。实现统一实体契约、EntitySample/Candidate接口与动态collate；五种实体各自语义投影/类型embedding后共同进入2层64宽4头注意力，FF128，最终LayerNorm。公开目标预览转实体关系边，不再把5个敌人槽列塞进卡牌token。
- 所有动作结合源实体、目标实体、全体上下文评分；无目标的-1引用单独处理，所有true环境动作位必须有唯一route，选择候选引用已有实体，路由凭据不进入tensor。
- 15项统一模型测试通过（3.00秒）：96张牌、动态padding、全实体与候选置换、真实手牌/敌人槽位重排、全类型注意力关联、关系信息、字段可见性、环境mask、资源拒绝、可配置3层48宽6头、终局只算value，以及全部5类投影的有限非零梯度。6项真实选择测试另通过，合计19项首验后再补2项槽位对拍。
- 原比较模型/训练文件继续冻结；旧卡牌Set模块仅保留兼容回归，不能编码resolving选择状态，不作为新主架构。尚未执行新的正式PPO，也未宣称统一架构学习效果。

## U4：资源采集、共享药水来源接口与精确更新恢复（2026-09-12）

- U2/U3提交 `a572d16`。用户中途再次要求继续，沿统一实体方向收口，没有恢复旧卡牌Set主线或启动正式长训。
- 新主采集入口支持96初始牌、480卡实体/466阈值/15余量，并校验统一接口与真实后端二进制hash。真实Sentry压力测试超过旧64张并在新边界完整截断。
- 接口v2增加offer与resolving药水生命周期、选择来源引用；POTION21维、PLAYER_GLOBAL198维，其余CARD122/ENEMY196/RELIC10。这些是共享表示，不是新增药水效果实现。
- checkpoint绑定代码/词表/内容/奖励/资源/后端及数值运行设置，限定CPU实测FP32、单组Adam、Torch RNG、无活动环境更新边界；拒绝旧格式、精度隐式转换或配置漂移。完整活动局/队列/采集器恢复仍未实现。
- 最终全仓798 passed，29.01秒，0失败/0跳过；7个冻结文件hash、台账、规格与后端补丁检查通过。
- 最终64条采集transition（另有3次准备动作，共67次env.step），5个截断片段，5次真实选牌，最大103 token，动态batch64×103，120194参数；一次更新后保存，恢复后的下一次采样/loss/权重/Adam更新逐值一致。诊断4.11秒，不是吞吐基准或学习收益。
- 最新报告与checkpoint位于runs/unified-entity-u4-accepted-20260912；早期开发探针保留但不作为当前恢复包。完整替代关系、复用/重测边界及交接见docs/unified-entity-report.md。
- 全卡目标仍未结束：当前80/150，剩余70。R11后续还需对拍无可用牌时持续伤害能力与后端提前败北判定（本轮只静态定位，不计修复）；不把单卡准入升级为所有组合保证。
