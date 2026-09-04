"""最小切片卡表（mechanics.md §5）。

结算顺序（§5）：扣能量 → 卡牌离开手牌 → 结算效果 → 置入弃牌堆；
Bash 先伤害后施加 Vulnerable（自身伤害不吃自上的易伤，T16/T17）。
卡面数值为社区共识值，`[未核实]`，第 3 周对拍时逐一确认。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CardDef:
    card_id: str
    cost: int
    is_attack: bool
    damage: int = 0
    block: int = 0
    vulnerable: int = 0  # 命中后施加的 Vulnerable 层数


CARD_DEFS: dict[str, CardDef] = {
    "strike": CardDef("strike", cost=1, is_attack=True, damage=6),
    "defend": CardDef("defend", cost=1, is_attack=False, block=5),
    "bash": CardDef("bash", cost=2, is_attack=True, damage=8, vulnerable=2),
}


def starter_deck() -> list[str]:
    """Ironclad 初始卡组，固定构建顺序：Strike×5 → Defend×4 → Bash×1（§2.2）。

    列表尾 = 牌库顶（§0），故洗牌前 Bash 位于牌库顶。
    """
    return ["strike"] * 5 + ["defend"] * 4 + ["bash"]
