# reference/ —— 仲裁用参考资料（不入库）

> 本目录被 `.gitignore` 排除。定位见 `docs/decisions.md` D13：反编译源码**只作争议仲裁**，
> 不得照抄进模拟器（保住差分测试独立性），不得提交进 git（反编译产物版权归 Mega Crit，
> 本地查阅无风险，公开分发侵权）。

## sts1-decompiled/（待生成）

反编译 STS1 全量 Java 源码，放这里。**只在规格争议时定点查阅**（升级阶梯：
wiki → lightspeed 源码 → 反编译 Java → runlogger 日志兜底，见 decisions.md D13）。

生成方法（约 10 分钟，一次性）：

1. 下载 jadx：https://github.com/skylot/jadx/releases （下 `jadx-x.x.x.zip` 解压即可，无需安装）
2. 游戏本体位置（2026-09-03 确认）：`E:\SteamLibrary\steamapps\common\SlayTheSpire\desktop-1.0.jar`
3. 命令：

   ```bash
   <jadx解压目录>/bin/jadx -d reference/sts1-decompiled \
       "E:\SteamLibrary\steamapps\common\SlayTheSpire\desktop-1.0.jar"
   ```

4. 仲裁时的常用入口（第 3 周后按需补充）：
   - 伤害计算：`com.megacrit.cardcrawl.cards.AbstractCard` 的 `calculateCardDamage` / `applyPowers`
   - 回合循环：`com.megacrit.cardcrawl.rooms.AbstractBattle` / `MonsterGroup`
   - 状态效果递减：`com.megacrit.cardcrawl.powers.AbstractPower` 与各 Power 子类
   - RNG 结构：`com.megacrit.cardcrawl.dungeons.AbstractDungeon` 的 `generateSeeds()`
   - 卡牌数值：`com.megacrit.cardcrawl.cards.red`（Strike/Defend/Bash 在此）

## 已就位的本地依赖

| 目录 | 内容 | 锁定版本 |
|---|---|---|
| `../third_party/sts_lightspeed` | STS1 战斗机制 C++ 重实现 + pybind11（日常差分 oracle，U4/U6） | commit `7476a81`（2026-09-03 浅克隆） |
