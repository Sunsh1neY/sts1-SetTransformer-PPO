"""单选公开排序与私有对象路由；不冒称真实选牌转移已接通。"""
import copy

import pytest

from sts.env.ironclad import IroncladEnv
from sts.env.selection import SelectionRouter
from test_ironclad_expansion import scene


@pytest.fixture
def card():
    # 取真实规范观测作为记录格式；后续候选组合是路由单元夹具。
    return IroncladEnv().reset(scene(["Rampage"] * 5), 984000, diagnostic=True)["hand"][0]


def action(view, index):
    return {"kind": "SELECT_CARD", "decision_id": view["routing"]["decision_id"], "candidate_index": index}


def test_nonhand_public_sort_preserves_different_instance_targets(card):
    grown = copy.deepcopy(card)
    grown.update(combat_damage_bonus=8, damage=16)
    router = SelectionRouter()
    view = router.publish("EXHUME", [(37, grown), (2, card)])
    index = next(i for i, c in enumerate(view["semantic"]["candidates"]) if c["combat_damage_bonus"] == 8)
    target = router.take(action(view, index))
    assert target.backend_index == 37 and target.zone == "exhaust_pile"
    with pytest.raises(RuntimeError, match="失效"):
        router.take(action(view, index))


def test_equal_duplicates_remain_separate_and_hand_order_is_preserved(card):
    router = SelectionRouter()
    view = router.publish("EXHAUST_ONE", [(4, card), (0, card), (9, card)])
    assert len(view["semantic"]["candidates"]) == 3
    assert view["semantic"]["candidate_mask"] == [True, True, True]
    assert router.take(action(view, 1)).backend_index == 0


def test_discard_selection_is_not_limited_to_ten_positions(card):
    router = SelectionRouter()
    view = router.publish("HEADBUTT", [(i, card) for i in range(32)])
    assert router.take(action(view, 31)).backend_index == 31


def test_old_cross_environment_and_reset_references_are_rejected(card):
    first, other = SelectionRouter(), SelectionRouter()
    old = first.publish("EXHAUST_ONE", [(0, card)])
    second = first.publish("EXHAUST_ONE", [(0, card)])
    foreign = other.publish("EXHAUST_ONE", [(0, card)])
    for view in (old, foreign):
        with pytest.raises(ValueError, match="引用"):
            first.take(action(view, 0))
    first.invalidate()
    with pytest.raises(RuntimeError):
        first.take(action(second, 0))


def test_semantic_view_is_independent_of_tokens_and_private_indices(card):
    a, b = SelectionRouter(), SelectionRouter()
    x = a.publish("EXHUME", [(8, card)])
    y = b.publish("EXHUME", [(31, card)])
    assert x["semantic"] == y["semantic"] and x["routing"] != y["routing"]
    x["semantic"]["candidates"][0]["damage"] = 999
    assert a.snapshot()["semantic"]["candidates"][0]["damage"] == card["damage"]


@pytest.mark.parametrize("key", ["uniqueId", "backend_index", "seed", "future_intent"])
def test_private_fields_cannot_enter_candidate_tokens(card, key):
    router = SelectionRouter()
    card[key] = 1
    with pytest.raises(ValueError, match="隐藏字段"):
        router.publish("EXHAUST_ONE", [(0, card)])


@pytest.mark.parametrize("index", [True, -1, 1, 0.5])
def test_invalid_public_candidate_positions_do_not_select(card, index):
    router = SelectionRouter()
    view = router.publish("EXHAUST_ONE", [(0, card)])
    with pytest.raises((TypeError, ValueError)):
        router.take(action(view, index))
    assert router.take(action(view, 0)).backend_index == 0


def test_failed_candidate_publish_invalidates_previous_decision(card):
    router = SelectionRouter(capacity=2)
    old = router.publish("EXHAUST_ONE", [(0, card)])
    with pytest.raises(ValueError, match="容量"):
        router.publish("HEADBUTT", [(i, card) for i in range(3)])
    with pytest.raises(RuntimeError):
        router.take(action(old, 0))


def test_backend_indices_must_be_unique_and_inside_single_select_encoding(card):
    for candidates in ([(1, card), (1, card)], [(65536, card)], [(10, card)]):
        with pytest.raises(ValueError, match="重复|越界"):
            SelectionRouter().publish("EXHAUST_ONE", candidates)
