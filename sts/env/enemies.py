"""敌人规格与 AI（mechanics.md §7 / §9）。

**本模块的随机规格已于第 3 周对拍收口**（lightspeed 源码仲裁 + 差分对拍逐位验证，
见 docs/decisions.md D14 修订与 U6）：

- HP / 咬伤 / Curl Up roll：`random(start, end)` 双闭区间整数（GDX 语义），
  走 enemy_roll 流（游戏 monsterHpRng）；
- Louse 颜色（红/绿）由 misc 流 randomBoolean 决定，两只各 roll 一次（MonsterGroup::getLouse）；
- Curl Up 格挡量在**战斗初始化**时 roll（preBattleAction），不是受击时——受击只启用；
- 意图 roll 统一 `enemy_ai.random_int(99)`（0-99 含端点），`roll < 25` 走特殊技；
- Jaw Worm 后续行动 25/30/45 分带 + lastMove 约束 + 嵌套 randomBoolean(chance)，
  chance 需 float32 化后比较（游戏侧是 float 字面量）；
- 下一意图在敌人行动结算后立即 roll（§3 N2 之后，多怪按生成顺序）。
"""

from sts.env.rng import CombatRNG, _to_float32
from sts.env.state import EnemyState

# 遭遇配置（§9）：生成顺序 = 动作目标索引顺序
# louses 的颜色不在此固定——由 misc 流 roll（见 spawn_encounter）
ENCOUNTERS: dict[str, list[tuple[str, str, int, int]]] = {
    # (kind, 显示名, HP 下限, HP 上限)
    "jaw_worm": [("jaw_worm", "Jaw Worm", 40, 44)],
    "cultist": [("cultist", "Cultist", 48, 54)],
    "louses": [("louse_red", "Red Louse", 10, 15), ("louse_green", "Green Louse", 11, 17)],
}

# 固定伤害意图的基础值（§7）；bite 取实例的 bite_damage
INTENT_BASE_DAMAGE = {"chomp": 11, "thrash": 7, "dark_strike": 6}

# Jaw Worm 嵌套 roll 的概率（lightspeed MonsterSpecific.cpp:2450-2490），float32 语义
_JW_BELLOW_IF_CHOMP = _to_float32(0.5625)
_JW_CHOMP_IF_THRASH2 = _to_float32(0.357)
_JW_CHOMP_IF_BELLOW = _to_float32(0.416)

_LOUSE_HP_RANGE = {"louse_red": (10, 15), "louse_green": (11, 17)}


def spawn_encounter(encounter: str, rng: CombatRNG) -> list[EnemyState]:
    """§2.4：实例化与 HP/咬伤 roll（消耗模式经对拍验证）。

    louses：先 misc 流两只各 roll 一次颜色（True → 红），再逐只 HP + 咬伤；
    其余遭遇：逐只 HP roll。
    """
    enemies: list[EnemyState] = []
    if encounter == "louses":
        for is_red in (rng.misc.random_boolean(), rng.misc.random_boolean()):
            kind = "louse_red" if is_red else "louse_green"
            name, lo, hi = _LOUSE_KIND[kind]
            enemies.append(_spawn_one(kind, name, lo, hi, rng))
        return enemies
    for kind, name, lo, hi in ENCOUNTERS[encounter]:
        enemies.append(_spawn_one(kind, name, lo, hi, rng))
    return enemies


_LOUSE_KIND = {
    kind: (name, lo, hi)
    for kind, name, lo, hi in (e for enc in ENCOUNTERS.values() for e in enc)
    if "louse" in kind
}


def _spawn_one(kind: str, name: str, lo: int, hi: int, rng: CombatRNG) -> EnemyState:
    hp = rng.enemy_roll.random_int_range(lo, hi)
    enemy = EnemyState(kind=kind, name=name, hp=hp, hp_max=hp)
    if kind in ("louse_red", "louse_green"):
        enemy.bite_damage = rng.enemy_roll.random_int_range(5, 7)  # asc<2 区间
    return enemy


def roll_initial_intent(enemy: EnemyState, rng: CombatRNG) -> None:
    """§2.5：初始意图。三遭遇统一消耗一次 enemy_ai（对拍实测 ai=1/2 与之一致）。"""
    roll = rng.enemy_ai.random_int(99)  # rollMove 无条件消耗（Monster::rollMove）
    if enemy.kind == "jaw_worm":
        enemy.intent = "chomp"  # firstTurn 分支
    elif enemy.kind == "cultist":
        enemy.intent = "incantation"  # lastMove(INVALID) 分支
    else:  # louse：roll < 25 → 特殊技；开局无历史，防重复约束不触发
        enemy.intent = _louse_special(enemy) if roll < 25 else "bite"
    enemy.move_history.insert(0, enemy.intent)


def roll_next_intent(enemy: EnemyState, rng: CombatRNG) -> None:
    """下一意图：行动结算后 roll（§3 N2 后），带 lastMove / lastTwoMoves 约束。

    lightspeed getMoveForRoll（MonsterSpecific.cpp:2313/2450/2583）的忠实复刻。
    """
    roll = rng.enemy_ai.random_int(99)
    if enemy.kind == "cultist":
        enemy.intent = "dark_strike"
    elif enemy.kind == "jaw_worm":
        h = enemy.move_history
        if roll < 25:
            if h and h[0] == "chomp":
                enemy.intent = "bellow" if rng.enemy_ai.random_boolean(_JW_BELLOW_IF_CHOMP) else "thrash"
            else:
                enemy.intent = "chomp"
        elif roll < 55:
            if len(h) >= 2 and h[0] == "thrash" and h[1] == "thrash":
                enemy.intent = "chomp" if rng.enemy_ai.random_boolean(_JW_CHOMP_IF_THRASH2) else "bellow"
            else:
                enemy.intent = "thrash"
        else:
            if h and h[0] == "bellow":
                enemy.intent = "chomp" if rng.enemy_ai.random_boolean(_JW_CHOMP_IF_BELLOW) else "thrash"
            else:
                enemy.intent = "bellow"
    else:
        # louse：roll < 25 → 特殊技（最近一次已是特殊技且连续两次则强制咬）；
        # 否则连续两次咬后强制特殊技
        special = _louse_special(enemy)
        h = enemy.move_history
        if roll < 25:
            if len(h) >= 2 and h[0] == special and h[1] == special:
                enemy.intent = "bite"
            else:
                enemy.intent = special
        elif len(h) >= 2 and h[0] == "bite" and h[1] == "bite":
            enemy.intent = special
        else:
            enemy.intent = "bite"
    enemy.move_history.insert(0, enemy.intent)


def roll_curl_up_block(enemy: EnemyState, rng: CombatRNG) -> None:
    """Louse Curl Up 格挡量：**初始化时 roll**（preBattleAction，asc0 区间 3-7），
    受击时启用（§7）。enemy_roll 流消耗顺序：全部 HP/bite 之后、按生成顺序。"""
    enemy.curl_up_block = rng.enemy_roll.random_int_range(3, 7)


def _louse_special(enemy: EnemyState) -> str:
    return "grow" if enemy.kind == "louse_red" else "spit_web"
