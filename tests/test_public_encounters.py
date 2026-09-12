"""扩展遭遇工程诊断，不能替代真实精英来源数据。"""
import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("encounter_diagnostics", ROOT / "scripts/diagnose-public-encounters.py")
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)


@pytest.mark.parametrize("encounter", D.PUBLIC_CONTRACT["encounters"])
@pytest.mark.parametrize("ascension", [0, 20])
def test_encounter_legal_trajectory_and_boundary(encounter, ascension):
    result = D.run_case(encounter, ascension, 710000, "random")
    assert result["terminated"] != result["truncated"]
    assert result["max_targetable"] <= 5


def test_five_targets_and_explicit_external_budget():
    scene, _ = D.diagnostic_scene("LOTS_OF_SLIMES", 20)
    env = D.PublicBattleEnv(max_actions=1)
    obs = env.reset(scene, 710001, diagnostic=True)
    assert sum(e["targetable"] for e in obs["enemies"]) == 5
    after, reward, terminated, truncated, _ = env.step(50)
    assert not terminated and truncated and reward == 0
    D.check_observation(after)
    with pytest.raises(RuntimeError):
        env.step(50)


def test_large_slime_splits_and_dead_slot_stays_unaddressable():
    result = D.run_case("LARGE_SLIME", 0, 710000, "random")
    assert result["max_targetable"] == 2
    assert any(e["present"] and not e["targetable"] and e["hp"] <= 0 for t in result["trace"] for e in t["enemies"])
    assert result["terminated"] and not result["truncated"]


@pytest.mark.parametrize("modifier", [True, "false", 0, None])
def test_unproved_burning_elite_modifier_is_rejected(modifier):
    scene, _ = D.diagnostic_scene("GREMLIN_NOB", 20)
    scene["burning_elite"] = modifier
    with pytest.raises((ValueError, RuntimeError, TypeError)):
        D.PublicBattleEnv().reset(scene, 710002, diagnostic=True)


def test_elite_missing_modifier_is_not_silently_defaulted():
    scene, _ = D.diagnostic_scene("THREE_SENTRIES", 20)
    del scene["burning_elite"]
    with pytest.raises((ValueError, RuntimeError, TypeError)):
        D.PublicBattleEnv().reset(scene, 710003, diagnostic=True)


def test_reset_replay_preserves_same_canonical_trace():
    a = D.run_case("LARGE_SLIME", 20, 710004, "rule")
    b = D.run_case("LARGE_SLIME", 20, 710004, "rule")
    assert a["trace"] == b["trace"] and a["final_observation"] == b["final_observation"]


@pytest.mark.parametrize("seed", [710000, 710001])
def test_red_slaver_entangle_is_used_once(seed):
    # 高HP只延长公开轨迹观测，不修改怪物规则、不进入真实场景池。
    scene, _ = D.diagnostic_scene("RED_SLAVER", 20)
    scene["player"]["hp"] = scene["player"]["max_hp"] = 30000
    env = D.PublicBattleEnv(max_actions=30)
    observation = env.reset(scene, seed, diagnostic=True)
    entangle_intents = 0
    while True:
        entangle_intents += observation["enemies"][0]["intent_kind"] == "DEBUFF"
        observation, _, terminated, truncated, _ = env.step(50)
        if terminated or truncated:
            break
    assert entangle_intents == 1


@pytest.mark.parametrize("ascension,ritual", [(0, 3), (20, 5)])
def test_cultist_ritual_strength_and_visible_damage_agree(ascension, ritual):
    scene, _ = D.diagnostic_scene("CULTIST", ascension)
    env = D.PublicBattleEnv()
    observation = env.reset(scene, 710000, diagnostic=True)
    assert observation["enemies"][0]["intent_kind"] == "BUFF"
    observation, *_ = env.step(50)
    enemy = observation["enemies"][0]
    assert enemy["statuses"]["Ritual"] == ritual
    assert enemy["statuses"].get("Strength", 0) == 0 and enemy["intent_damage"] == 6
    observation, *_ = env.step(50)
    enemy = observation["enemies"][0]
    assert enemy["statuses"]["Strength"] == ritual
    assert enemy["intent_damage"] == 6 + ritual
