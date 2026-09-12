"""消耗和虚无须影响真实牌堆/触发器，不能只有观测标记。"""

import pytest

from sts.env.public_battle import PublicBattleEnv


def start(deck):
    env = PublicBattleEnv()
    scene = {
        "entry_timing": "pre_combat_initialization",
        "initialization_phase": "before_destination_room_entry",
        "act": 1, "floor": 1, "character": "IRONCLAD", "ascension": 0,
        "player": {"hp": 60, "max_hp": 80, "gold": 99},
        "deck": deck, "relics": [], "potions": [None, None, None], "encounter": "CULTIST",
    }
    return env, env.reset(scene, 811000, diagnostic=True)


def play(env, obs, name):
    slot = next(i for i, c in enumerate(obs["hand"]) if c["name"] == name)
    assert obs["action_mask"][slot * 5]
    return env.step(slot * 5)[0]


@pytest.mark.parametrize("metric", ["Carnage", "Carnage+1", "Ghostly Armor", "Ghostly Armor+1", "AscendersBane", "Dazed"])
def test_ethereal_hand_exhausts_at_end_of_turn_including_upgraded_armor(metric):
    env, obs = start([metric] * 5)
    assert all(card["ethereal"] for card in obs["hand"])
    # 虚无不是打出时的消耗标记。
    assert all(not card["exhaust"] for card in obs["hand"])
    after = env.step(50)[0]
    assert len(after["exhaust_pile"]) == 5
    assert after["hand"] == [] and after["discard_pile"] == []


@pytest.mark.parametrize("metric", ["Pummel", "Pummel+1", "Impervious", "Impervious+1", "Slimed"])
def test_self_exhaust_card_moves_to_real_exhaust_pile(metric):
    env, obs = start([metric] * 5)
    assert all(card["exhaust"] for card in obs["hand"])
    after = play(env, obs, metric.split("+")[0])
    assert len(after["exhaust_pile"]) == 1
    assert after["exhaust_pile"][0]["name"] == metric.split("+")[0]


@pytest.mark.parametrize("upgrade", [False, True])
def test_seeing_red_exhaust_dispatches_feel_no_pain(upgrade):
    env, obs = start(["Feel No Pain", "Seeing Red" + ("+1" if upgrade else ""), "Defend_R", "Defend_R", "Defend_R"])
    obs = play(env, obs, "Feel No Pain")
    seeing = next(card for card in obs["hand"] if card["name"] == "Seeing Red")
    assert seeing["exhaust"] and not seeing["ethereal"]
    after = play(env, obs, "Seeing Red")
    assert after["player"]["energy"] == (4 if upgrade else 3)
    assert after["player"]["block"] == 3
    assert [card["name"] for card in after["exhaust_pile"]] == ["Seeing Red"]


def test_ordinary_skill_does_not_trigger_exhaust_power():
    env, obs = start(["Feel No Pain", "Defend_R", "Defend_R", "Defend_R", "Defend_R"])
    obs = play(env, obs, "Feel No Pain")
    after = play(env, obs, "Defend_R")
    assert after["player"]["block"] == 5
    assert after["exhaust_pile"] == []
