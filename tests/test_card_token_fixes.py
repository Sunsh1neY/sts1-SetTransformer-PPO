"""全卡合并前 B01、B02、B03、B04 的定向反例与修复回归。"""

import copy

import numpy as np
import pytest

from sts.env.entities import card_features, encode_observation
from sts.env.ironclad import IroncladEnv
from test_ironclad_dynamics import play, rows, start
from test_ironclad_expansion import scene
from test_ironclad_selection_cards import choose


def _scene(cards):
    value = scene(cards)
    value.update(encounter="LAGAVULIN", burning_elite=False)
    value["relics"] = []
    value["potions"] = [None, None]
    return value


def _infernal_scene():
    return _scene(["Infernal Blade", "Exhume", "Defend_R", "Defend_R", "Defend_R"])


def _pummel_after_infernal(env, obs):
    obs = play(env, obs, "Infernal Blade")
    assert any(card["name"] == "Pummel" for card in obs["hand"])
    return play(env, obs, "Pummel")


def test_b01_same_turn_exhume_keeps_temporary_zero_cost_and_payment():
    """同回合取回仍保留Infernal Blade的一次本回合免费效果。"""
    env = IroncladEnv()
    obs = env.reset(_infernal_scene(), 982155, diagnostic=True)
    obs = _pummel_after_infernal(env, obs)
    obs = play(env, obs, "Exhume")
    obs = choose(env, obs, "Pummel")

    pummel = next(card for card in obs["hand"] if card["name"] == "Pummel")
    assert pummel["base_cost"] == 1
    assert pummel["effective_cost"] == 0
    before_energy = obs["player"]["energy"]
    obs = play(env, obs, "Pummel")
    assert obs["player"]["energy"] == before_energy


def test_b01_cross_turn_exhume_restores_cost_and_mask_payment():
    """跨回合取回恢复原实例费用，合法mask和实际能量支付一致。"""
    env = IroncladEnv()
    obs = env.reset(_infernal_scene(), 982155, diagnostic=True)
    obs = _pummel_after_infernal(env, obs)
    obs, _, terminated, truncated, _ = env.step(50)
    assert not terminated and not truncated
    obs = play(env, obs, "Exhume")
    obs = choose(env, obs, "Pummel")

    pummel = next(card for card in obs["hand"] if card["name"] == "Pummel")
    assert pummel["base_cost"] == 1
    assert pummel["effective_cost"] == 1
    slot = next(i for i, card in enumerate(obs["hand"]) if card["name"] == "Pummel")
    assert obs["action_mask"][slot * 5]
    before_energy = obs["player"]["energy"]
    obs = play(env, obs, "Pummel")
    assert obs["player"]["energy"] == before_energy - 1


@pytest.mark.parametrize("top", ["Wound", "Dazed", "Burn", "AscendersBane", "Clash"])
def test_b02_havoc_unusable_top_card_is_not_lost(top):
    """Havoc从抽牌堆取出的不可执行牌仍须落入明确区域。"""
    env = IroncladEnv()
    obs = env.reset(_scene(["Havoc", "Warcry", top, "Defend_R", "Defend_R"]), 982321, diagnostic=True)
    obs = play(env, obs, "Warcry")
    obs = choose(env, obs, top)
    obs = play(env, obs, "Havoc")

    locations = {
        zone: sum(card["name"] == top for card in obs[zone])
        for zone in ("hand", "draw_pile", "discard_pile", "exhaust_pile")
    }
    assert sum(locations.values()) == 1, locations
    assert locations["exhaust_pile"] == 1, locations


def test_b02_havoc_exhaust_trigger_runs_for_unusable_wound():
    """不可用Wound的耗尽仍触发已公开的Feel No Pain。"""
    env = IroncladEnv()
    obs = env.reset(_scene(["Havoc", "Warcry", "Wound", "Feel No Pain", "Defend_R"]), 982321, diagnostic=True)
    obs = play(env, obs, "Feel No Pain")
    obs = play(env, obs, "Warcry")
    obs = choose(env, obs, "Wound")
    before_block = obs["player"]["block"]
    obs = play(env, obs, "Havoc")
    assert obs["player"]["block"] == before_block + 3
    assert sum(card["name"] == "Wound" for card in obs["exhaust_pile"]) == 1


def test_b03_searing_blow_plus_100_is_not_upgraded_by_armaments_plus():
    """+100可构造但Armaments+不应再次进入后端升级异常。"""
    env, obs = start(["Searing Blow+100", "Armaments+1", "Wound", "Dazed", "Burn"])
    obs = play(env, obs, "Armaments")
    assert obs["decision"]["phase"] == "NORMAL"
    assert rows(obs, "Searing Blow")[0]["upgrade_count"] == 100


def test_b04_ascenders_bane_is_unplayable_in_every_card_region():
    """不可主动打出类别在四个牌区都用0占位并由类别表达。"""
    env = IroncladEnv()
    obs = env.reset(_scene(["AscendersBane", "Defend_R", "Strike_R", "Defend_R", "Strike_R"]), 982321, diagnostic=True)
    bane = next(card for card in obs["hand"] if card["name"] == "AscendersBane")
    assert bane["cost_kind"] == "UNPLAYABLE"

    synthetic = copy.deepcopy(obs)
    row = copy.deepcopy(bane)
    synthetic["hand"] = []
    synthetic["draw_pile"] = [copy.deepcopy(row)]
    synthetic["discard_pile"] = [copy.deepcopy(row)]
    synthetic["exhaust_pile"] = [copy.deepcopy(row)]
    synthetic["action_mask"] = np.zeros(66, dtype=np.bool_)
    sample = encode_observation(synthetic)
    card_tokens = [token.features for token in sample.tokens if token.entity_type == "CARD"]
    assert len(card_tokens) == 3
    for features in card_tokens:
        assert features[8] == 0.0
        np.testing.assert_array_equal(features[106:109], [0.0, 0.0, 1.0])
    assert all(not legal for legal in (candidate.legal for candidate in sample.candidates))
