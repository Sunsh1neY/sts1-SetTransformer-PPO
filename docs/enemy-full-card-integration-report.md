# 非铜球敌人与全卡接口首批集成报告

日期：2026-09-13。工作树C:/Users/19091/Desktop/sts2-enemy-potion。单agent执行；不修改原全卡/主工作树。本批不是全部22遭遇收口。

## 实际准入边界

| 入口 | 范围 | 本批新增 |
|---|---|---|
| EnemyPotionBattleEnv | 原独立35牌闭包、A0..20、35遭遇 | MAW、TRANSIENT |
| IroncladEnv | 共享75类战士牌基础/升级、A20、8遭遇 | 在全卡旧5遭遇基础上新增MAW、TRANSIENT、SNECKO |
| 共享统一模型 | CARD115；ENEMY771原始分类/数值输入，经类型投影后仍64宽 | 三位置原始意图编号与有效性接入；已批准状态词表复用 |

两个入口有不同准入范围，不能把独立35遭遇全部宣称已接上全卡。跨入口新增不同遭遇共3个；其余原待审遭遇未自动开放。铜球关系与区域未实施，时间吞噬者按用户最新选择暂缓。

## 实现与来源

- 引入全卡2325d55已验收的ironclad/selection/entities实现、注册表和模型；来源文件哈希见enemy-full-card-source-manifest.json。没有另写Transformer、PPO或选择协议。
- 后端新增integrated-card-env独立绑定，保留冻结public绑定与契约。公共规范化复制为full_card_public仅供新入口，原public_battle不改。共享后端卡牌机制补丁相对原冻结基础叠加，队列保留本分支已有显式溢出保护。
- 三位置编号按类别one-hot连接共享线性投影，等价于分位置可学习类别embedding；不把编号大小当机制数值。移除旧两次意图类别输入，保留公开计数。不新增关系维度，edges仍为[N,N,0]。
- 集成契约ironclad-enemy-integration-v1，观测ironclad-enemy-observation-v1，模型unified-enemy-entity-set-v1；旧checkpoint不当作精确恢复。本批未建立或验证新checkpoint恢复流程。
- 巨口仅复用全局回合和当前伤害/段数；倏忽魔保留Fading/Shifting及实时力量；自然消失后不生成有效敌人token，外部预算截断不是胜利。
- 异蛇使用共享即时费用、known/scope/移区规则；Confused按公开布尔状态导出，混乱意图依据正版为STRONG_DEBUFF，不复用C探针错误的普通DEBUFF映射。

## 真实交互验证

- 双发+打击：倏忽魔承受两次真实伤害，力量立即下降、意图伤害实时更新，打击只按实际单次手动支付。
- 头槌：在巨口场景中进入共享SELECT_CARD，生成真实候选；提交路由后返回NORMAL，公开顶牌标记正确。
- 异蛇：三seed下随机费用与实际付款一致，离手后即时费用unknown，编码不补零伪装已知。
- 模型：上述真实选择经过前向/反向；ENEMY投影有梯度，实体置换保持动作对应与value，动态padding不改变原样本输出。属于结构/接口验证，不是学习收益证明。
- 巨口/倏忽魔14项独立专项覆盖A0、A1、A2、A16、A17、A20、状态/伤害/自然结束/外部截断；不是极端压力测试。

## 测试记录

- 接入共享代码及异蛇后，相关回归345 passed，12.09秒，0失败/跳过。
- 随后新增padding不变性测试，全卡专项8 passed，2.43秒。该8项包含前一轮已有专项，不与345直接相加当作单次完整回归。
- 75类×基础/升级×3敌人，共450局人工随机候选诊断；7225 transition、58次选择、449自然终止、1次32步外部截断、0异常。覆盖每个版本配置，不意味着每张牌每种效果都在每局实际触发，更不等于穷举组合。
- 诊断文件reference/enemy-full-card-20260913.json，SHA256=103cca2ab0c3ac5a678a9b3d14135bde2438a2d09a3fbfc120fd6a5f68d9095c。原始运行文件按规则忽略，不覆盖旧实验。
- 本地构建与契约指纹加载通过。共享全卡原目录保持干净；冻结四文件哈希核验、补丁正反检查在收尾执行。不重新做极端容量测试。

## 尚未准入与下一步

- 时间吞噬者：正版Ripple是DEFEND_DEBUFF，原词表缺失；用户选择暂缓，不加入近似类型或生产白名单。
- 铜球：关系方案等待用户外部讨论，不加入AUTOMATON或stasis区域。
- 其余召唤/复活、阶段、几何体等继续需要逐项机制及公开接口验收；phase虽获批准，本批尚未导出。
- 已批准battle_exit出口尚未落地；团块/盗贼不能凭后端探针当作完整环境交付。
- 药水范围保持各入口既有范围；未做正式PPO、完整RunEnv、push或主分支合并。

## 复现

```powershell
python -X utf8 scripts/regenerate-enemy-potion-patch.py
./scripts/build-enemy-potion.ps1 -Python python -Jobs 1
python -X utf8 -m pytest -q tests/test_enemy_full_card_integration.py tests/test_enemy_maw_transient.py
python -X utf8 scripts/diagnose-enemy-full-card.py --output reference/enemy-full-card-new-run.json
```

源码增量统一保存在patches/lightspeed-enemy-potion.patch；生成头通过generate-enemy-potion-contract.py和generate-ironclad-contract.py重建，不依赖worker隐藏目录。

收尾实际核验：冻结四文件及共享来源文件SHA未变，全卡工作树干净；新后端契约指纹匹配；增量补丁正向/反向检查通过，spec检查PASS。改动尚未提交，未推送或合并。
