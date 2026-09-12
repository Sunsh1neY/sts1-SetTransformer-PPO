# M1 修订候选与 M2 前置要求

日期：2026-09-11。依据：spec-v6、D25/D26 和修订后的全卡审计。此表为实施候选，不是正式 reset 白名单。M1 候选方案与原十张数值证据已收口；不据此启动训练。

M1 收口证据：`docs/m1-numeric-evidence.md`。该材料完成来源定位，不代表扩展卡行为测试、registry、reset 或正式白名单完成。

## 建议核心候选：35 类

为了让每批故障可定位，按新增机制依赖分组；基础版与升级版分别验收。

| 批次 | 候选 | 类数 | 先决条件 |
|---|---|---|---|
| 0 既有基础 | Strike、Defend、Bash | 3 | 保留旧范围；升级配置需新增验收 |
| 1 直接攻防 | Bludgeon、Cleave、Clothesline、Twin Strike、Thunderclap、Uppercut、Body Slam、Entrench、Heavy Blade、Spot Weakness、Inflame | 11 | 数值、目标类型、力量/格挡/意图和减益；Artifact 依遭遇白名单决定必须暴露的字段；Heavy Blade 倍率误报已撤销 |
| 2 固定牌量内移动与消耗 | Pommel Strike、Shrug It Off、Dropkick、Carnage、Ghostly Armor、Impervious、Pummel、Seeing Red、Sentinel、True Grit（仅基础版） | 10 | 抽牌、满手牌、虚无、消耗及触发时序；True Grit 升级不在本批 |
| 3 显式回合状态 | Battle Trance、Flex、Metallicize、Demon Form、Rage、Flame Barrier、Feel No Pain | 7 | NoDraw、临时力量回收、持续能力层数与到期时点；输入字段必须描述当前玩家可见状态 |
| 4 受控生成 | Wild Strike、Reckless Charge、Power Through、Immolate | 4 | Wound/Dazed/Burn 辅助类别、生成次数与容量证明、状态牌行为 |

35 是可选卡类别数；生成的状态牌另计注册类别，不混进该目标。单局牌组张数由 M2 另定，不能等同于 35。

若后续数值或行为审计失败，候选仍可延期；不得为凑数量掩盖缺陷。第 4 批若无法证明容量边界，先延期并登记替代方案，不能随意设置很大数组充当证明。

## 暂不纳入核心候选

- 需要主动二次选择的卡，以及 Infernal Blade 等会生成这些卡的路径：先解决完整动作表达，不能静默缩小原生成池。
- Disarm 升级、Iron Wave、Fiend Fire：保留差异或风险，先完成定点行为核验。
- Whirlwind：撤销“需要 X 选择”的排除理由，作为备选；先验零能量、能量快照和免费出牌。
- Rampage、Searing Blow：需要每张卡动态数值/升级次数契约。
- Anger、复制路径：重复生成上界未证明。

## M2 开始实施前要锁定的契约

1. **配置**：每批明确卡牌版本白名单、固定牌组及遭遇；状态牌和间接生成牌也要做可达性检查。选择型升级牌不能借战斗内升级绕过白名单。
2. **容量**：手牌、敌人观测行、可寻址目标、非手牌实体总量分别定义；从实际配置与生成次数推导上界。当前目标列维持三个，分裂/召唤超过范围的遭遇不纳入。
3. **观测**：列出当前局面下影响未来转移的玩家可见字段；静态卡牌属性可由注册表导出，不要求重复输入。隐藏牌序、RNG 和 seed 不进入模型。
4. **版本**：集中声明字段顺序、类别表、shape 与输入/动作/序列化版本；同步 binding、双 wrapper、模型和 checkpoint 校验。旧权重能加载不意味着允许复用旧评估结论。
5. **验收**：按机制验证数值与结算，再跑受影响接口和旧最小范围回归；满足 D25 后按固定预算从头短训，每批使用相同诊断条件。

## M1 收口后的待完成

扩展卡基础/升级行为测试尚未执行；全卡报告中除原十张补充材料外的数值仍沿用原审计记录，不能因此声明全卡已复验。正式候选批准、固定牌组、M2 容量/观测/版本契约尚未完成。
