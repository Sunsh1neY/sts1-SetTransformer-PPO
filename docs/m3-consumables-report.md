# M3 药水与遗物实际效果验收

日期：2026-09-12。独占测试文件：`tests/test_public_consumables.py`。实际执行28项全部通过，耗时0.24秒；无失败或跳过。

本轮只添加测试和本报告，未改C++、构建配置或既有测试。验证扩展SHA-256：`4E61DF0BAE90CC8899F5E18B0CB2ACC8E5D32F9EC650E4E51D592CE61FE8B48B`。

## 验证方法与证据边界

全部使用公开规范观测和动作mask调用独立PublicBattleEnv。构造scene显式标为diagnostic，seed813000位于训练/诊断范围；人工场景仅用于机制测试，不加入真实训练集。断言实际HP、格挡、伤害、牌堆数量、power变更、合法动作、退出奖励；没有只校验potency标签或重新调用同一公式自证。

机制数值依据已存在的`docs/relic-potion-backend-audit.md`正版JAR定点预审和锁定后端`src/combat/BattleContext.cpp`的drinkPotion/initRelics、`src/combat/Player.cpp`的回血/属性/回合处理，以及当前新适配器的单次胜利出口约定。本轮没有重新反编译全部药水/遗物，也不宣称这些测试构成与正版完整轨迹等价证明。

## 中央15种直接药水全部有实际覆盖

| 药水 | 实际断言 |
|---|---|
| Weak Potion | 两敌只给指定目标3层Weak；JawWorm下一次真实伤害降为原伤害×0.75向下取整 |
| FearPotion | 两敌只给指定目标3层Vulnerable；Strike实际造成9而非6伤害 |
| Block Potion | 立即12格挡并实际抵挡JawWorm攻击 |
| Strength Potion | Strength+2，Strike实际8伤害，回合后保留 |
| Dexterity Potion | Dexterity+2，Defend实际7格挡，回合后保留 |
| SpeedPotion | Dexterity+5和LoseDexterity5；Defend实际10格挡；回合末两状态清除 |
| Ancient Potion | Artifact1真实抵消Flex的LoseStrength，消耗Artifact后Strength2跨回合保留 |
| Energy Potion | 从3能量增加到5 |
| Swift Potion | 手牌5→8，抽牌堆5→2；没有生成额外卡 |
| Fruit Juice | 受伤/满血均增加当前和最大HP5；与BB组合退出HP71/max85，奖励使用85作分母 |
| Explosive Potion | 两只敌人各实际失去10HP |
| Regen Potion | Regen5，首回合末实际治疗5并剩4层 |
| HeartOfIron | Metallicize6在真实敌人攻击前提供6格挡 |
| EssenceOfSteel | PlatedArmor4实际挡伤；受到未格挡攻击后掉1层 |
| LiquidBronze | Thorns3，在受到JawWorm攻击时对敌人实际反伤3 |

每次喝药还共同验证原药水槽变空、其5个动作位全部关闭。不存在保留药水却重复触发的测试漏洞。

## 中央8种开场遗物全部有实际覆盖

| 遗物 | 实际断言 |
|---|---|
| Anchor | 开场10格挡；下一玩家回合没有再次获得 |
| Lantern | 开场4能量；下一回合恢复标准3，未重复+1 |
| Blood Vial | 入场60→62HP；下一回合不再次治疗 |
| Bag of Preparation | 初次抽7张；随后正常回合只抽5张 |
| Vajra | 开场Strength1，Strike实际7伤害 |
| Oddly Smooth Stone | 开场Dexterity1，Defend实际6格挡 |
| Bronze Scales | Thorns3，实际受到攻击后敌人失去3HP |
| Burning Blood | 相同无伤击杀过程，无遗物退出60HP、有遗物退出66HP；奖励分别读取实际退出HP。终局再次step被拒，重复读取observation不重复回血 |

新增联合测试：FruitJuice先将HP60/max80变65/max85，随后无伤击杀和BB治疗，最终HP71/max85，奖励为`1+0.5*71/85`，避免仍使用入口最大HP作为奖励分母。

## 复现

```powershell
python -m pytest -q tests/test_public_consumables.py
```

这28项证明当前直接药水和8遗物在列出的实际路径上符合预期，不扩大药水/遗物白名单，不解除二次选择、动态跨战斗counter、随机生成、SacredBark、SmokeBomb等延期条件。完整M3/M4/M5状态和全仓回归由主审统一记录。
