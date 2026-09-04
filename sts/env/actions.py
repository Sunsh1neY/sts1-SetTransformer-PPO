"""动作空间与合法性（mechanics.md §8 / spec-v4 §4.3）。

扁平化 (hand_slot, target) 组合 + 末位 end_turn；合法动作列表与掩码由环境直接
给出，模型不猜（§8.4）；环境拒绝一切非法动作（Gate 1 第 4 条）。
"""

from sts.env.cards import CARD_DEFS
from sts.env.state import CombatState

MAX_HAND = 10
MAX_TARGET = 3
END_TURN = MAX_HAND * MAX_TARGET  # 30，末位
N_ACTIONS = END_TURN + 1


class IllegalMove(Exception):
    """环境拒绝非法动作（§8.5）。"""


def action_index(slot: int, target: int) -> int:
    return slot * MAX_TARGET + target


def decode(action: int) -> tuple[int, int] | None:
    """i < A-1 → (slot, target)；i = A-1 → None（end_turn）。"""
    if action == END_TURN:
        return None
    if not 0 <= action < END_TURN:
        raise IllegalMove(f"动作索引越界：{action}")
    return divmod(action, MAX_TARGET)


def legal_actions(state: CombatState) -> list[int]:
    """§8.3：合法 ⟺ 槽位有牌 且 能量 ≥ 卡费 且 目标合法（攻击卡目标存活；
    无目标卡 target 固定 0）。列表按索引升序，顺序确定（T12 依赖）。"""
    legal: list[int] = []
    for slot, card_id in enumerate(state.hand):
        card = CARD_DEFS[card_id]
        if state.player.energy < card.cost:
            continue
        if card.is_attack:
            for target in range(min(len(state.enemies), MAX_TARGET)):
                if state.enemies[target].alive:
                    legal.append(action_index(slot, target))
        else:
            legal.append(action_index(slot, 0))
    legal.append(END_TURN)
    return legal


def action_mask(state: CombatState) -> list[bool]:
    legal = set(legal_actions(state))
    return [i in legal for i in range(N_ACTIONS)]
