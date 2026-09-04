"""伤害计算与结算原语（mechanics.md §4）。

规格裁定（§4 注）：每步乘法后立即 floor；Vulnerable 先于 Weak 计算；
力量最先加入。Vuln/Weak 乘法先后在最小切片内不可被日志区分（无同时生效来源），
第二档入库前须经反编译仲裁（decisions.md D13/U7）。
"""

import math


def compute_attack_damage(
    base: int,
    attacker_strength: int,
    attacker_weak_turns: int,
    target_vulnerable_turns: int,
) -> int:
    """§4 攻击伤害公式，按编号顺序执行。"""
    base += attacker_strength  # §4.2 力量最先加（负亦然）
    if target_vulnerable_turns > 0:  # §4.3
        base = math.floor(base * 1.5)
    if attacker_weak_turns > 0:  # §4.4
        base = math.floor(base * 0.75)
    return max(0, base)  # §4.5


def deal_damage(target, amount: int) -> int:
    """§4.6 结算到目标：先扣 block，余量扣 HP。返回实际扣减的 HP。"""
    absorbed = min(target.block, amount)
    target.block -= absorbed
    hp_loss = amount - absorbed
    target.hp -= hp_loss
    return hp_loss
