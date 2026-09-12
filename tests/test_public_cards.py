"""中等卡牌按独立机制预期验证，不使用历史场景作为人工训练数据。"""
from collections import Counter

import numpy as np
import pytest

from sts.env.public_battle import PublicBattleEnv, PUBLIC_CONTRACT


def scene(deck, *, encounter="CULTIST", potions=None, relics=None):
    return {
        "entry_timing": "pre_combat_initialization", "initialization_phase": "before_destination_room_entry",
        "act": 1, "floor": 1, "character": "IRONCLAD", "ascension": 0,
        "player": {"hp": 60, "max_hp": 80, "gold": 99}, "deck": deck,
        "relics": [] if relics is None else relics,
        "potions": [None, None, None] if potions is None else potions, "encounter": encounter,
    }


def start(deck, **kwargs):
    env = PublicBattleEnv()
    observation = env.reset(scene(deck, **kwargs), 810000, diagnostic=True)
    return env, observation


def play(env, obs, name, target=0):
    index = next(i for i, card in enumerate(obs["hand"]) if card["name"] == name)
    action = index * 5 + target
    assert obs["action_mask"][action], (name, action)
    return env.step(action)[0]


def status(entity, name):
    norm = lambda text: "".join(c.lower() for c in text if c.isalnum())
    return next((value for key, value in entity["statuses"].items() if norm(key) == norm(name)), 0)


def entities(obs):
    return Counter(c["name"] for key in ("hand", "draw_pile", "discard_pile", "exhaust_pile") for c in obs[key])


@pytest.mark.parametrize("name,base,up,hits_base,hits_up", [
    ("Strike_R",6,9,1,1),("Bash",8,10,1,1),("Bludgeon",32,42,1,1),
    ("Cleave",8,11,1,1),("Clothesline",12,14,1,1),("Twin Strike",5,7,2,2),
    ("Thunderclap",4,7,1,1),("Uppercut",13,13,1,1),("Heavy Blade",14,14,1,1),
    ("Pommel Strike",9,10,1,1),("Dropkick",5,8,1,1),("Carnage",20,28,1,1),
    ("Pummel",2,2,4,5),("Wild Strike",12,17,1,1),("Reckless Charge",7,10,1,1),
    ("Immolate",21,28,1,1),
])
@pytest.mark.parametrize("upgrade", [False, True])
def test_attack_damage_matches_effect_not_only_preview(name, base, up, hits_base, hits_up, upgrade):
    env, obs = start([name + ("+1" if upgrade else "")] * 10)
    damage, hits = (up, hits_up) if upgrade else (base, hits_base)
    initial_hp = obs["enemies"][0]["hp"]
    card = obs["hand"][0]
    assert card["damage_by_target"][0] == damage and card["hits"] == hits
    after = play(env, obs, name)
    assert after["enemies"][0]["hp"] == max(0, initial_hp - damage * hits)


@pytest.mark.parametrize("name,base,up", [
    ("Defend_R",5,8),("Shrug It Off",8,11),("Ghostly Armor",10,13),
    ("Impervious",30,40),("Sentinel",5,8),("Flame Barrier",12,16),("Power Through",15,20),
])
@pytest.mark.parametrize("upgrade", [False, True])
def test_block_effect_and_preview(name, base, up, upgrade):
    env, obs = start([name + ("+1" if upgrade else "")] * 10)
    expected = up if upgrade else base
    assert obs["hand"][0]["block"] == expected
    after = play(env, obs, name)
    assert after["player"]["block"] == expected


@pytest.mark.parametrize("upgrade", [False, True])
def test_heavy_blade_strength_multiplier_is_not_double_counted(upgrade):
    env, obs = start(["Heavy Blade" + ("+1" if upgrade else "")] * 5, potions=["Strength Potion", None, None])
    obs = env.step(51)[0]
    assert status(obs["player"], "Strength") == 2
    expected = 14 + (5 if upgrade else 3) * 2
    assert obs["hand"][0]["damage_by_target"][0] == expected
    hp = obs["enemies"][0]["hp"]
    assert play(env, obs, "Heavy Blade")["enemies"][0]["hp"] == hp - expected


@pytest.mark.parametrize("name,generated,count", [("Wild Strike","Wound",1),("Reckless Charge","Dazed",1),("Immolate","Burn",1),("Power Through","Wound",2)])
def test_generated_cards_remain_in_complete_observation(name, generated, count):
    env, obs = start([name] * 10)
    before = sum(entities(obs).values())
    after = play(env, obs, name)
    assert entities(after)[generated] == count
    assert sum(entities(after).values()) == before + count


@pytest.mark.parametrize("upgrade", [False, True])
def test_body_slam_and_entrench_use_current_block(upgrade):
    env, obs = start(["Defend_R", "Entrench" + ("+1" if upgrade else ""), "Body Slam+1", "Defend_R", "Defend_R"])
    obs = play(env, obs, "Defend_R")
    obs = play(env, obs, "Entrench")
    assert obs["player"]["block"] == 10
    hp = obs["enemies"][0]["hp"]
    obs = play(env, obs, "Body Slam")
    assert obs["enemies"][0]["hp"] == hp - 10


@pytest.mark.parametrize("upgrade", [False, True])
def test_battle_trance_prevents_second_draw_in_same_turn(upgrade):
    env, obs = start(["Battle Trance" + ("+1" if upgrade else "")] * 20)
    obs = play(env, obs, "Battle Trance")
    assert len(obs["hand"]) == (8 if upgrade else 7)
    assert status(obs["player"], "No Draw") == 1
    expected = len(obs["hand"]) - 1
    assert len(play(env, obs, "Battle Trance")["hand"]) == expected


@pytest.mark.parametrize("name,status_name,base,up", [("Inflame","Strength",2,3),("Flex","Strength",2,4),("Demon Form","Demon Form",2,3),("Metallicize","Metallicize",3,4),("Feel No Pain","Feel No Pain",3,4),("Rage","Rage",3,5)])
@pytest.mark.parametrize("upgrade", [False, True])
def test_visible_power_amounts(name, status_name, base, up, upgrade):
    env, obs = start([name + ("+1" if upgrade else "")] * 5)
    after = play(env, obs, name)
    assert status(after["player"], status_name) == (up if upgrade else base)


@pytest.mark.parametrize("upgrade", [False, True])
def test_seeing_red_energy_gain(upgrade):
    env, obs = start(["Seeing Red" + ("+1" if upgrade else "")] * 5)
    after = play(env, obs, "Seeing Red")
    assert after["player"]["energy"] == (5 if upgrade else 4)
    assert len(after["exhaust_pile"]) == 1


@pytest.mark.parametrize("upgrade", [False, True])
def test_spot_weakness_uses_visible_attack_condition(upgrade):
    card = "Spot Weakness" + ("+1" if upgrade else "")
    env, obs = start([card] * 5, encounter="JAW_WORM")
    assert obs["enemies"][0]["intent_damage"] > 0
    assert status(play(env, obs, "Spot Weakness")["player"], "Strength") == (4 if upgrade else 3)
    env, obs = start([card] * 5)
    assert status(play(env, obs, "Spot Weakness")["player"], "Strength") == 0


def test_true_grit_exhausts_sentinel_and_triggers_energy():
    env, obs = start(["True Grit"] + ["Sentinel"] * 4)
    after = play(env, obs, "True Grit")
    assert after["player"]["block"] == 7
    assert after["player"]["energy"] == 4
    assert [c["name"] for c in after["exhaust_pile"]] == ["Sentinel"]


def test_feel_no_pain_exhaust_interaction():
    env, obs = start(["Feel No Pain", "True Grit", "Defend_R", "Defend_R", "Defend_R"])
    obs = play(env, obs, "Feel No Pain")
    obs = play(env, obs, "True Grit")
    assert obs["player"]["block"] == 10


def test_rage_attack_and_flex_expiry():
    env, obs = start(["Rage", "Flex", "Strike_R", "Defend_R", "Defend_R"])
    obs = play(env, obs, "Rage")
    obs = play(env, obs, "Flex")
    obs = play(env, obs, "Strike_R")
    assert obs["player"]["block"] == 3
    obs = env.step(50)[0]
    assert status(obs["player"], "Strength") == 0


def test_demon_form_next_turn_gain():
    env, obs = start(["Demon Form"] * 5)
    obs = play(env, obs, "Demon Form")
    obs = env.step(50)[0]
    assert status(obs["player"], "Strength") == 2


def test_unknown_choice_and_ambiguous_upgrade_are_rejected():
    for card in ("Headbutt", "True Grit+1", "Bash+", "Burn+1", "Unknown"):
        with pytest.raises((ValueError, RuntimeError)):
            start([card] * 5)


def test_budget_returns_complete_final_state_and_stops_further_steps():
    env = PublicBattleEnv(max_actions=1)
    obs = env.reset(scene(["Defend_R"] * 5), 810000, diagnostic=True)
    after, reward, terminated, truncated, info = env.step(0)
    assert truncated and not terminated and reward == 0
    assert sum(entities(after).values()) == 5 and after["action_mask"].any()
    assert info["truncation_reason"] == "external_action_budget"
    with pytest.raises(RuntimeError):
        env.step(50)


def test_public_contract_has_35_playable_classes_and_five_auxiliary():
    assert len(PUBLIC_CONTRACT["cards"]) == 40
    assert PUBLIC_CONTRACT["capacity"]["max_card_entities_bound"] < 32767
