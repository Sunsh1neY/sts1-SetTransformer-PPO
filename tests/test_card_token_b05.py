"""B05暂停结算上下文：公开、最小、进入候选动作评分。"""

import copy

import torch

from sts.env.entities import collate, encode_observation
from sts.env.ironclad import IroncladEnv
from sts.models.entities import UnifiedEntityActorCritic
from test_ironclad_dynamics import play
from test_ironclad_expansion import scene
from test_ironclad_selection_cards import choose


def _scene(cards):
    value = scene(cards)
    value.update(encounter="LAGAVULIN", burning_elite=False)
    value["relics"] = []
    value["potions"] = [None, None]
    return value


def test_b05_manual_replay_and_autoplay_context_are_public_and_minimal():
    """三条真实路径只暴露来源、耗尽结果和重复选择汇总，不暴露队列明细。"""
    env = IroncladEnv()
    obs = env.reset(_scene(["Headbutt", "Strike_R", "Defend_R", "Pommel Strike", "Seeing Red"]), 982401, diagnostic=True)
    for card in ("Seeing Red", "Defend_R", "Strike_R", "Headbutt"):
        obs = play(env, obs, card)
    manual = encode_observation(obs)
    assert obs["decision"]["resolution_context"] == {
        "source_mode": "MANUAL", "source_will_exhaust": False, "pending_replay_count": 0}
    assert all(candidate.context == (1.0, 0.0, 0.0, 0.0, 0.0) for candidate in manual.candidates)

    env = IroncladEnv()
    obs = env.reset(_scene(["Double Tap", "Headbutt", "Strike_R", "Defend_R", "Defend_R"]), 982402, diagnostic=True)
    for card in ("Defend_R", "Double Tap", "Headbutt"):
        obs = play(env, obs, card)
    replay = encode_observation(obs)
    assert obs["decision"]["resolution_context"] == {
        "source_mode": "MANUAL", "source_will_exhaust": False, "pending_replay_count": 1}
    assert all(candidate.context == (1.0, 0.0, 0.0, 0.0, 0.25) for candidate in replay.candidates)
    obs = choose(env, obs, "Defend_R")
    assert obs["decision"]["resolution_context"] == {
        "source_mode": "REPLAY", "source_will_exhaust": False, "pending_replay_count": 0}

    env = IroncladEnv()
    obs = env.reset(_scene(["Havoc", "Warcry", "Headbutt", "True Grit+1", "Strike_R", "Defend_R"]), 982500, diagnostic=True)
    obs = play(env, obs, "Defend_R")
    obs = play(env, obs, "Warcry")
    obs = choose(env, obs, "Headbutt")
    obs = play(env, obs, "Havoc")
    autoplay = encode_observation(obs)
    assert obs["decision"]["resolution_context"] == {
        "source_mode": "AUTOPLAY", "source_will_exhaust": True, "pending_replay_count": 0}
    assert all(candidate.context == (0.0, 1.0, 0.0, 1.0, 0.0) for candidate in autoplay.candidates)

    for decision in (obs["decision"],):
        assert set(decision["resolution_context"]) == {"source_mode", "source_will_exhaust", "pending_replay_count"}


def test_b05_candidate_context_reaches_action_scorer():
    """候选上下文不是日志字段；改变它会改变实际候选logit。"""
    env = IroncladEnv()
    obs = env.reset(_scene(["Headbutt", "Strike_R", "Defend_R", "Pommel Strike", "Seeing Red"]), 982401, diagnostic=True)
    for card in ("Seeing Red", "Defend_R", "Strike_R", "Headbutt"):
        obs = play(env, obs, card)
    sample = encode_observation(obs)
    altered = copy.deepcopy(sample)
    altered.candidates = [type(candidate)(candidate.kind, candidate.source, candidate.target, candidate.legal,
                                          (0.0, 0.0, 1.0, 1.0, 1.0)) for candidate in altered.candidates]
    model = UnifiedEntityActorCritic().eval()
    with torch.no_grad():
        model.action_head[0].weight[:, -5:] = 0.25
        first, _ = model(collate([sample]))
        second, _ = model(collate([altered]))
    legal = collate([sample])["legal"]
    assert not torch.equal(first[legal], second[legal])
