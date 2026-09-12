"""直接药水和开场遗物验证真实转移；人工scene仅用于机制诊断。"""

import pytest

from sts.env.public_battle import PublicBattleEnv


def start(*, potion=None, relics=(), encounter="CULTIST", deck=None, hp=60):
    env = PublicBattleEnv()
    scene = {
        "entry_timing": "pre_combat_initialization", "initialization_phase": "before_destination_room_entry",
        "act": 1, "floor": 1, "character": "IRONCLAD", "ascension": 0,
        "player": {"hp": hp, "max_hp": 80, "gold": 99},
        "deck": list(deck or ["Strike_R"] * 10), "relics": list(relics),
        "potions": [potion, None, None], "encounter": encounter,
    }
    return env, env.reset(scene, 813000, diagnostic=True)


def status(entity, name):
    normalize = lambda x: "".join(c.lower() for c in x if c.isalnum())
    return next((n for k, n in entity["statuses"].items() if normalize(k) == normalize(name)), 0)


def drink(env, obs, target=0):
    assert obs["action_mask"][51 + target]
    after = env.step(51 + target)[0]
    assert not after["potions"][0]["present"]
    assert not any(after["action_mask"][51:56])
    return after


def play(env, obs, name):
    slot = next(i for i, c in enumerate(obs["hand"]) if c["name"] == name)
    assert obs["action_mask"][slot * 5]
    return env.step(slot * 5)


@pytest.mark.parametrize("potion,power", [("Weak Potion", "Weak"), ("FearPotion", "Vulnerable")])
def test_targeted_potion_changes_only_selected_enemy(potion, power):
    env, obs = start(potion=potion, encounter="TWO_LOUSE")
    after = drink(env, obs, target=1)
    assert status(after["enemies"][1], power) == 3
    assert status(after["enemies"][0], power) == 0


def test_weak_potion_reduces_actual_incoming_damage():
    env, obs = start(potion="Weak Potion", encounter="JAW_WORM")
    damage = obs["enemies"][0]["intent_damage"]
    obs = drink(env, obs)
    assert obs["enemies"][0]["intent_damage"] == int(damage * .75)
    after = env.step(50)[0]
    assert after["player"]["hp"] == 60 - int(damage * .75)


def test_fear_potion_modifies_actual_attack_damage():
    env, obs = start(potion="FearPotion")
    before = obs["enemies"][0]["hp"]
    obs = drink(env, obs)
    after = play(env, obs, "Strike_R")[0]
    assert after["enemies"][0]["hp"] == before - 9


def test_block_potion_blocks_real_attack():
    env, obs = start(potion="Block Potion", encounter="JAW_WORM")
    damage = obs["enemies"][0]["intent_damage"]
    obs = drink(env, obs)
    assert obs["player"]["block"] == 12
    assert env.step(50)[0]["player"]["hp"] == 60 - max(0, damage - 12)


def test_strength_potion_modifies_damage_and_persists():
    env, obs = start(potion="Strength Potion")
    before = obs["enemies"][0]["hp"]
    obs = drink(env, obs)
    assert status(obs["player"], "Strength") == 2
    obs = play(env, obs, "Strike_R")[0]
    assert obs["enemies"][0]["hp"] == before - 8
    assert status(env.step(50)[0]["player"], "Strength") == 2


def test_dexterity_potion_modifies_block_and_persists():
    env, obs = start(potion="Dexterity Potion", deck=["Defend_R"] * 10)
    obs = drink(env, obs)
    obs = play(env, obs, "Defend_R")[0]
    assert obs["player"]["block"] == 7
    assert status(env.step(50)[0]["player"], "Dexterity") == 2


def test_speed_potion_temporary_dexterity_expires():
    env, obs = start(potion="SpeedPotion", deck=["Defend_R"] * 10)
    obs = drink(env, obs)
    assert status(obs["player"], "Dexterity") == 5
    assert status(obs["player"], "Lose Dexterity") == 5
    obs = play(env, obs, "Defend_R")[0]
    assert obs["player"]["block"] == 10
    obs = env.step(50)[0]
    assert status(obs["player"], "Dexterity") == 0
    assert status(obs["player"], "Lose Dexterity") == 0


def test_ancient_potion_blocks_flex_attribute_loss():
    env, obs = start(potion="Ancient Potion", deck=["Flex"] * 5)
    obs = drink(env, obs)
    assert status(obs["player"], "Artifact") == 1
    obs = play(env, obs, "Flex")[0]
    assert status(obs["player"], "Artifact") == 0
    assert status(obs["player"], "Lose Strength") == 0
    assert status(env.step(50)[0]["player"], "Strength") == 2


def test_energy_potion_gains_two_energy():
    env, obs = start(potion="Energy Potion")
    assert drink(env, obs)["player"]["energy"] == 5


def test_swift_potion_draws_three_without_generating_cards():
    env, obs = start(potion="Swift Potion")
    assert len(obs["hand"]) == 5
    after = drink(env, obs)
    assert len(after["hand"]) == 8 and len(after["draw_pile"]) == 2


@pytest.mark.parametrize("hp", [60, 80])
def test_fruit_juice_increases_current_and_max_hp(hp):
    env, obs = start(potion="Fruit Juice", hp=hp)
    player = drink(env, obs)["player"]
    assert player["hp"] == hp + 5 and player["max_hp"] == 85


def test_explosive_potion_deals_ten_to_every_enemy():
    env, obs = start(potion="Explosive Potion", encounter="TWO_LOUSE")
    before = [m["hp"] for m in obs["enemies"][:2]]
    after = drink(env, obs)
    assert [m["hp"] for m in after["enemies"][:2]] == [max(0, hp - 10) for hp in before]


def test_regeneration_heals_at_end_of_turn_and_decrements():
    env, obs = start(potion="Regen Potion")
    obs = drink(env, obs)
    assert status(obs["player"], "Regen") == 5
    after = env.step(50)[0]
    assert after["player"]["hp"] == 65
    assert status(after["player"], "Regen") == 4


@pytest.mark.parametrize("potion,power,amount", [("HeartOfIron", "Metallicize", 6), ("EssenceOfSteel", "Plated Armor", 4)])
def test_end_turn_armor_potions_protect_against_actual_attack(potion, power, amount):
    env, obs = start(potion=potion, encounter="JAW_WORM")
    damage = obs["enemies"][0]["intent_damage"]
    obs = drink(env, obs)
    assert status(obs["player"], power) == amount
    after = env.step(50)[0]
    assert after["player"]["hp"] == 60 - max(0, damage - amount)
    if power == "Plated Armor":
        assert status(after["player"], power) == amount - int(damage > amount)


@pytest.mark.parametrize("potion,relics", [("LiquidBronze", []), (None, ["Bronze Scales"])])
def test_thorns_potion_and_relic_deal_real_retaliation(potion, relics):
    env, obs = start(potion=potion, relics=relics, encounter="JAW_WORM")
    if potion: obs = drink(env, obs)
    assert status(obs["player"], "Thorns") == 3
    before = obs["enemies"][0]["hp"]
    after = env.step(50)[0]
    assert after["enemies"][0]["hp"] == before - 3


@pytest.mark.parametrize("relic,field,expected", [("Anchor", "block", 10), ("Lantern", "energy", 4), ("Blood Vial", "hp", 62)])
def test_opening_relic_applies_once(relic, field, expected):
    env, obs = start(relics=[relic])
    assert obs["player"][field] == expected
    after = env.step(50)[0]
    assert after["player"][field] == {"block": 0, "energy": 3, "hp": 62}[field]


def test_bag_of_preparation_adds_only_initial_draw():
    env, obs = start(relics=["Bag of Preparation"], deck=["Defend_R"] * 15)
    assert len(obs["hand"]) == 7 and len(obs["draw_pile"]) == 8
    after = env.step(50)[0]
    assert len(after["hand"]) == 5


@pytest.mark.parametrize("relic,card,power,field,expected", [
    ("Vajra", "Strike_R", "Strength", "damage", 7),
    ("Oddly Smooth Stone", "Defend_R", "Dexterity", "block", 6),
])
def test_opening_attribute_relic_changes_actual_card_effect(relic, card, power, field, expected):
    env, obs = start(relics=[relic], deck=[card] * 5)
    assert status(obs["player"], power) == 1
    before_hp = obs["enemies"][0]["hp"]
    after = play(env, obs, card)[0]
    if field == "damage": assert before_hp - after["enemies"][0]["hp"] == expected
    else: assert after["player"]["block"] == expected


@pytest.mark.parametrize("relics,exit_hp", [([], 60), (["Burning Blood"], 66)])
def test_burning_blood_exit_healing_reward_and_no_repeat(relics, exit_hp):
    env, obs = start(relics=relics, potion="Energy Potion", deck=["Bludgeon+1", "Twin Strike+1", "Defend_R", "Defend_R", "Defend_R"])
    obs = drink(env, obs)
    obs, reward, done, truncated, _ = play(env, obs, "Bludgeon")
    assert not done and reward == 0
    obs, reward, done, truncated, _ = play(env, obs, "Twin Strike")
    assert done and not truncated
    assert obs["player"]["hp"] == exit_hp
    assert reward == pytest.approx(1 + .5 * exit_hp / 80)
    with pytest.raises(RuntimeError): env.step(50)
    assert env.observation()["player"]["hp"] == exit_hp


def test_fruit_juice_changes_exit_reward_denominator_with_burning_blood():
    env, obs = start(relics=["Burning Blood"], potion="Fruit Juice", deck=["Bludgeon+1"] * 10)
    obs = drink(env, obs)
    obs = play(env, obs, "Bludgeon")[0]
    obs = env.step(50)[0]
    obs, reward, done, truncated, _ = play(env, obs, "Bludgeon")
    assert done and not truncated
    assert obs["player"]["hp"] == 71 and obs["player"]["max_hp"] == 85
    assert reward == pytest.approx(1 + .5 * 71 / 85)
