"""True Grit+真实暂停、选定实例、公开结算中区域及续跑。"""
import pytest

from sts.env.ironclad import IroncladEnv, REGIONS
from test_ironclad_dynamics import play, start
from test_ironclad_expansion import scene


def selected_action(obs, name):
    index = next(i for i, c in enumerate(obs["decision"]["selection"]["candidates"]) if c["name"] == name)
    return {"kind": "SELECT_CARD", **obs["decision"]["routing"], "candidate_index": index}


def test_true_grit_pauses_with_complete_entities_then_exhausts_selected_sentinel():
    env, obs = start(["True Grit+1", "Sentinel", "Defend_R", "Strike_R", "Rampage"])
    obs = play(env, obs, "True Grit")
    assert obs["decision"]["phase"] == "SELECT_CARD" and not obs["action_mask"].any()
    assert obs["player"]["block"] == 9
    assert sum(len(obs[z]) for z in REGIONS) == 5
    assert obs["resolving"][0]["name"] == "True Grit"
    assert env.observation()["decision"]["routing"] == obs["decision"]["routing"]
    action = selected_action(obs, "Sentinel")
    energy = obs["player"]["energy"]
    obs, reward, terminated, truncated, info = env.step(action)
    assert obs["decision"]["phase"] == "NORMAL" and not obs["resolving"]
    assert obs["player"]["energy"] == energy + 2
    assert [c["name"] for c in obs["exhaust_pile"]] == ["Sentinel"]
    assert [c["name"] for c in obs["discard_pile"]] == ["True Grit"]
    assert info["action_count"] == 2 and reward == 0 and not terminated and not truncated
    with pytest.raises(RuntimeError):
        env.step(action)


@pytest.mark.parametrize("remaining", [[], ["Sentinel"]])
def test_zero_or_one_candidate_is_automatic_without_extra_decision(remaining):
    env, obs = start(["True Grit+1", *remaining])
    obs = play(env, obs, "True Grit")
    assert obs["decision"]["phase"] == "NORMAL" and not obs["resolving"]
    assert len(obs["exhaust_pile"]) == len(remaining)


def test_action_budget_at_selection_keeps_complete_final_decision():
    env = IroncladEnv(max_actions=1)
    obs = env.reset(scene(["True Grit+1", *["Defend_R"] * 4]), 985000, diagnostic=True)
    slot = next(i for i, c in enumerate(obs["hand"]) if c["name"] == "True Grit")
    obs, reward, terminal, truncated, _ = env.step(slot * 5)
    assert truncated and not terminal and reward == 0
    assert obs["decision"]["selection"]["candidate_mask"] == [True] * 4
    assert sum(len(obs[z]) for z in REGIONS) == 5
    with pytest.raises(RuntimeError):
        env.step(selected_action(obs, "Defend_R"))


def test_selected_sentinel_and_source_true_grit_both_trigger_exhaust_under_corruption():
    env, obs = start(["Corruption", "True Grit+1", "Sentinel", "Feel No Pain", "Defend_R"], ["Energy Potion", None])
    obs = env.step(51)[0]
    obs = play(env, obs, "Feel No Pain")
    obs = play(env, obs, "Corruption")
    obs = play(env, obs, "True Grit")
    assert obs["resolving"][0]["effective_exhaust"]
    obs = env.step(selected_action(obs, "Sentinel"))[0]
    assert sorted(c["name"] for c in obs["exhaust_pile"]) == ["Sentinel", "True Grit"]
    assert obs["player"]["block"] == 15


def test_previous_selection_reference_is_rejected_after_reset():
    env, obs = start(["True Grit+1", *["Defend_R"] * 4])
    obs = play(env, obs, "True Grit")
    old_action = selected_action(obs, "Defend_R")
    obs = env.reset(scene(["True Grit+1", *["Defend_R"] * 4]), 985010, diagnostic=True)
    obs = play(env, obs, "True Grit")
    with pytest.raises(ValueError, match="引用"):
        env.step(old_action)
