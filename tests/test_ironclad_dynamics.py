"""真实战斗中的实例成长、战斗费用与Power语义；不注入隐藏状态。"""
import pytest
import torch

from sts.env.ironclad import IroncladEnv
from sts.env.public_battle import PublicBattleEnv
from sts.models.comparison import tensor_batch
from sts.models.ironclad import IroncladActorCritic, encode
from test_ironclad_expansion import scene


def start(cards, potions=None):
    candidate = scene(cards)
    candidate.update(encounter="LAGAVULIN", burning_elite=False)
    candidate["relics"] = []
    candidate["potions"] = potions or [None, None]
    env = IroncladEnv()
    return env, env.reset(candidate, 982101, diagnostic=True)


def play(env, obs, name, target=0):
    slot = next(i for i, c in enumerate(obs["hand"]) if c["name"] == name)
    action = slot * 5 + target
    assert obs["action_mask"][action], (name, obs["player"], obs["hand"])
    return env.step(action)[0]


def rows(obs, name):
    return [c for zone in ("hand", "draw_pile", "discard_pile", "exhaust_pile")
            for c in obs[zone] if c["name"] == name]


@pytest.mark.parametrize("upgrade", [False, True])
def test_rampage_only_played_instance_grows_and_repeated_play_keeps_growth(upgrade):
    name = "Rampage+1" if upgrade else "Rampage"
    env, obs = start([name, name, "Defend_R", "Defend_R", "Defend_R"])
    growth = 8 if upgrade else 5
    obs = play(env, obs, "Rampage")
    assert sorted(c["combat_damage_bonus"] for c in rows(obs, "Rampage")) == [0, growth]
    assert sorted(c["damage"] for c in rows(obs, "Rampage")) == [8, 8 + growth]
    obs = env.step(50)[0]
    grown = next(i for i, c in enumerate(obs["hand"]) if c["name"] == "Rampage" and c["combat_damage_bonus"] == growth)
    obs = env.step(grown * 5)[0]
    assert sorted(c["combat_damage_bonus"] for c in rows(obs, "Rampage")) == [0, 2 * growth]


@pytest.mark.parametrize("upgrade", [False, True])
def test_blood_for_blood_loses_one_cost_per_hp_loss_event_not_per_hp(upgrade):
    name = "Blood for Blood+1" if upgrade else "Blood for Blood"
    env, obs = start([name, name, "Burn", "Defend_R", "Defend_R"])
    printed = 3 if upgrade else 4
    assert all(c["printed_cost"] == c["base_cost"] == printed for c in rows(obs, "Blood for Blood"))
    hp = obs["player"]["hp"]
    obs = env.step(50)[0]
    assert obs["player"]["hp"] == hp - 2
    assert all(c["base_cost"] == printed - 1 and c["printed_cost"] == printed for c in rows(obs, "Blood for Blood"))
    assert all(c["damage"] == (22 if upgrade else 18) for c in rows(obs, "Blood for Blood"))


@pytest.mark.parametrize("upgrade", [False, True])
def test_barricade_boolean_export_and_block_persists_at_turn_start(upgrade):
    env, obs = start(["Barricade+1" if upgrade else "Barricade", *["Defend_R"] * 4], ["Energy Potion", None])
    obs = env.step(51)[0]
    obs = play(env, obs, "Barricade")
    assert obs["player"]["statuses"]["Barricade"] == 1
    obs = play(env, obs, "Defend_R")
    obs = play(env, obs, "Defend_R")
    assert obs["player"]["block"] == 10
    obs = env.step(50)[0]
    assert obs["player"]["block"] == 10
    assert not rows(obs, "Barricade")


@pytest.mark.parametrize("upgrade", [False, True])
def test_corruption_skills_are_free_exhaust_and_distinguish_printed_cost(upgrade):
    env, obs = start(["Corruption+1" if upgrade else "Corruption", *["Defend_R"] * 4])
    obs = play(env, obs, "Corruption")
    energy = obs["player"]["energy"]
    assert energy == (1 if upgrade else 0)
    assert obs["player"]["statuses"]["Corruption"] == 1
    for card in obs["hand"]:
        assert card["effective_cost"] == 0 and card["effective_cost_known"]
        assert card["cost_scope"] == "POWER" and card["effective_exhaust"]
        # base_cost在旧接口实际表示战斗修改费；印刷费必须单独保留。
        assert card["base_cost"] == 0 and card["printed_cost"] == 1
    obs = play(env, obs, "Defend_R")
    assert obs["player"]["energy"] == energy
    assert len(obs["exhaust_pile"]) == 1 and obs["player"]["block"] == 5
    exhausted = obs["exhaust_pile"][0]
    assert not exhausted["effective_cost_known"] and exhausted["cost_scope"] == "UNKNOWN"
    obs = env.step(50)[0]
    assert all(c["effective_cost"] == 0 and c["effective_exhaust"] for c in obs["hand"])


@pytest.mark.parametrize("upgrade", [False, True])
def test_combust_stacks_damage_and_hp_loss_independently(upgrade):
    name = "Combust+1" if upgrade else "Combust"
    env, obs = start([name, name, "Defend_R", "Defend_R", "Defend_R"])
    obs = play(env, obs, "Combust")
    obs = play(env, obs, "Combust")
    damage = 14 if upgrade else 10
    assert obs["player"]["statuses"]["Combust"] == damage
    assert obs["player"]["combust_hp_loss"] == 2
    hp, enemy_hp, block = obs["player"]["hp"], obs["enemies"][0]["hp"], obs["enemies"][0]["block"]
    obs = env.step(50)[0]
    assert obs["player"]["hp"] == hp - 2
    assert obs["enemies"][0]["hp"] == enemy_hp - max(0, damage - block)


@pytest.mark.parametrize("card", ["Rampage", "Blood for Blood", "Barricade", "Corruption", "Combust"])
@pytest.mark.parametrize("upgrade", [False, True])
def test_probe_versions_encode_into_set_and_do_not_open_legacy_entry(card, upgrade):
    name = card + ("+1" if upgrade else "")
    env, obs = start([name, *["Defend_R"] * 4])
    batch = tensor_batch([encode(obs)])
    model = IroncladActorCritic(batch["global"].shape[-1])
    distribution, value = model.distribution(batch)
    assert torch.isfinite(distribution.probs).all() and torch.isfinite(value).all()
    assert not distribution.probs[~batch["mask"]].any()
    with pytest.raises(ValueError):
        PublicBattleEnv().reset(scene([name] * 5), 982101, diagnostic=True)


def test_nonhand_cost_does_not_become_known_from_numeric_placeholder():
    _, obs = start(["Blood for Blood"] * 12)
    assert obs["draw_pile"]
    assert all(c["cost_scope"] == "UNKNOWN" and not c["effective_cost_known"] for c in obs["draw_pile"])
    assert all(c["base_cost"] == 4 for c in obs["draw_pile"])


@pytest.mark.parametrize("upgrade", [False, True])
def test_rampage_strength_changes_preview_without_overwriting_instance_bonus(upgrade):
    env, obs = start(["Rampage+1" if upgrade else "Rampage", *["Defend_R"] * 4], ["Strength Potion", None])
    obs = env.step(51)[0]
    card = rows(obs, "Rampage")[0]
    assert card["damage_by_target"][0] == 10 and card["combat_damage_bonus"] == 0
    obs = play(env, obs, "Rampage")
    card = rows(obs, "Rampage")[0]
    assert card["damage_by_target"][0] == 10 + (8 if upgrade else 5)
    assert card["combat_damage_bonus"] == (8 if upgrade else 5)


@pytest.mark.parametrize("upgrade", [False, True])
def test_blood_for_blood_multiple_hp_loss_events_clamp_cost_at_zero(upgrade):
    env, obs = start(["Blood for Blood+1" if upgrade else "Blood for Blood", "Burn", "Burn", "Burn", "Defend_R"])
    obs = env.step(50)[0]
    obs = env.step(50)[0]
    assert rows(obs, "Blood for Blood")[0]["base_cost"] == 0
    slot = next(i for i, c in enumerate(obs["hand"]) if c["name"] == "Blood for Blood")
    assert obs["action_mask"][slot * 5]


@pytest.mark.parametrize("upgrade", [False, True])
def test_barricade_preserves_end_turn_metallicize_block(upgrade):
    env, obs = start(["Barricade+1" if upgrade else "Barricade", "Metallicize", *["Defend_R"] * 3], ["Energy Potion", None])
    obs = env.step(51)[0]
    obs = play(env, obs, "Barricade")
    obs = play(env, obs, "Metallicize")
    obs = play(env, obs, "Defend_R")
    obs = env.step(50)[0]
    assert obs["player"]["block"] == 8


@pytest.mark.parametrize("upgrade", [False, True])
def test_corruption_exhaust_triggers_sentinel_and_feel_no_pain(upgrade):
    env, obs = start(["Corruption+1" if upgrade else "Corruption", "Feel No Pain", "Sentinel", "Defend_R", "Defend_R"], ["Energy Potion", None])
    obs = env.step(51)[0]
    obs = play(env, obs, "Feel No Pain")
    obs = play(env, obs, "Corruption")
    energy = obs["player"]["energy"]
    obs = play(env, obs, "Sentinel")
    assert obs["player"]["energy"] == energy + 2
    assert obs["player"]["block"] == 8
    assert any(c["name"] == "Sentinel" for c in obs["exhaust_pile"])


@pytest.mark.parametrize("upgrade", [False, True])
def test_combust_single_stacked_loss_event_reduces_blood_cost_once(upgrade):
    name = "Combust+1" if upgrade else "Combust"
    env, obs = start([name, name, "Blood for Blood", "Defend_R", "Defend_R"])
    obs = play(env, obs, "Combust")
    obs = play(env, obs, "Combust")
    obs = env.step(50)[0]
    assert obs["player"]["combust_hp_loss"] == 2
    assert rows(obs, "Blood for Blood")[0]["base_cost"] == 3


def test_backend_registry_fingerprint_mismatch_rejects_before_reset(monkeypatch):
    from sts.env.lightspeed import _load_backend
    module = _load_backend()
    monkeypatch.setattr(module, "IRONCLAD_REGISTRY_SHA256", "stale-build")
    with pytest.raises(RuntimeError, match="指纹"):
        IroncladEnv()
