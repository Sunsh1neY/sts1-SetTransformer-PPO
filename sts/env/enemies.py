"""敌人规格与 AI（mechanics.md §7 / §9）。

`[未核实]` 项（第 3 周日志反推校准，实现先取最简约定）：
- HP / 咬伤 roll 的区间约定取「双闭区间」：lo + nextInt(hi - lo + 1)；
- 洗牌用 Collections.shuffle 语义的 Fisher-Yates（本模块不涉及，见 combat.py）；
- Jaw Worm 固定首行动 Chomp **消耗一次** enemy_ai（§1 约定）；
- Cultist 行动表全固定，不消耗 enemy_ai；
- Louse 首行动与其后行动同概率表（75% Bite / 25% 特殊技）；
- 概率带映射：nextInt(100) → 区间分段，游戏内实际映射待对拍反推；
- 下一意图在其行动结算后立即 roll（游戏真实时机待对拍）。
"""

from sts.env.rng import CombatRNG
from sts.env.state import EnemyState

# 遭遇配置（§9）：生成顺序 = 动作目标索引顺序
ENCOUNTERS: dict[str, list[tuple[str, str, int, int]]] = {
    # (kind, 显示名, HP 下限, HP 上限)
    "jaw_worm": [("jaw_worm", "Jaw Worm", 40, 44)],
    "cultist": [("cultist", "Cultist", 48, 54)],
    "louses": [("louse_red", "Red Louse", 10, 15), ("louse_green", "Green Louse", 11, 17)],
}

# 固定伤害意图的基础值（§7，[未核实]）；bite 取实例的 bite_damage
INTENT_BASE_DAMAGE = {"chomp": 11, "thrash": 7, "dark_strike": 6}


def spawn_encounter(encounter: str, rng: CombatRNG) -> list[EnemyState]:
    """§2.4：按遭遇配置顺序实例化；HP 依序 roll；Louse 咬伤定值同时 roll。"""
    enemies: list[EnemyState] = []
    for kind, name, lo, hi in ENCOUNTERS[encounter]:
        hp = lo + rng.enemy_roll.next_int(hi - lo + 1)  # [未核实] 双闭区间约定
        enemy = EnemyState(kind=kind, name=name, hp=hp, hp_max=hp)
        if kind in ("louse_red", "louse_green"):
            enemy.bite_damage = 5 + rng.enemy_roll.next_int(3)  # 5-7，[未核实]
        enemies.append(enemy)
    return enemies


def roll_initial_intent(enemy: EnemyState, rng: CombatRNG) -> None:
    """§2.5：按生成顺序决定初始意图。"""
    if enemy.kind == "jaw_worm":
        rng.enemy_ai.next_int(100)  # 固定首行动仍消耗一次（§1 约定，[未核实]）
        enemy.intent = "chomp"
    elif enemy.kind == "cultist":
        enemy.intent = "incantation"  # 全固定，不消耗（[未核实]）
    else:  # louse：75% Bite / 25% 特殊技（[未核实]）
        enemy.intent = "bite" if rng.enemy_ai.next_int(100) < 75 else _louse_special(enemy)


def roll_next_intent(enemy: EnemyState, rng: CombatRNG) -> None:
    """下一意图（[未核实] 时机：实现选在其行动结算后立即 roll）。"""
    if enemy.kind == "cultist":
        enemy.intent = "dark_strike"  # 此后每回合 Dark Strike（§7）
    elif enemy.kind == "jaw_worm":
        n = rng.enemy_ai.next_int(100)  # 45% Thrash / 30% Bellow / 25% Chomp，[未核实]
        if n < 45:
            enemy.intent = "thrash"
        elif n < 75:
            enemy.intent = "bellow"
        else:
            enemy.intent = "chomp"
    else:  # louse（[未核实]）
        enemy.intent = "bite" if rng.enemy_ai.next_int(100) < 75 else _louse_special(enemy)


def _louse_special(enemy: EnemyState) -> str:
    return "grow" if enemy.kind == "louse_red" else "spit_web"
