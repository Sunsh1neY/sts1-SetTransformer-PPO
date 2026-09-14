"""独立入口的旧行为等价、信息完整性与未准入路径拒绝。"""
import copy
import json

import numpy as np
import pytest

from sts.env.ironclad import CONTRACT, IroncladEnv, normalize_ironclad, semantic_extensions
from sts.env.public_battle import CARD_BY_NAME, PublicBattleEnv, load_scene_manifest


def scene(cards=None):
    _, scenes = load_scene_manifest()
    value = copy.deepcopy(scenes[0]["candidate"])
    value.update(ascension=20, act=1, encounter="JAW_WORM", burning_elite=False)
    value["player"].update(hp=75, max_hp=75)
    value["potions"] = [None, None]
    if cards is not None:
        value["deck"] = cards
    return value


def legacy_view(obs):
    value = copy.deepcopy(obs)
    value["schema"] = "public-observation-v1"
    # 仅比较旧入口可表达的投影；新增公开信息另有实体和机制专项验收。
    assert not value.pop("stasis", []) and not value.pop("relations", [])
    value.pop("routing", None)
    for enemy in value["enemies"]:
        assert enemy.pop("phase", "NONE") == "NONE"
        enemy.pop("intent_history", None)
        enemy.pop("intent_history_valid", None)
    del value["decision"]
    assert not value.pop("resolving", [])
    del value["player"]["combust_hp_loss"]
    for pile in ("hand", "draw_pile", "discard_pile", "exhaust_pile"):
        for card in value[pile]:
            for key in ("combat_damage_bonus", "is_strike", "cost_kind", "effective_exhaust", "printed_cost", "effective_cost", "effective_cost_known", "cost_scope"):
                del card[key]
        if pile != "hand":
            value[pile].sort(key=lambda c: json.dumps(c, sort_keys=True))
    value["action_mask"] = value["action_mask"].tolist()
    return value


def plain(obs):
    value = copy.deepcopy(obs)
    for enemy in value["enemies"]:
        enemy["public_history"].pop("last_intent_kind", None)
        enemy["public_history"].pop("previous_intent_kind", None)
    for pile in ("draw_pile", "discard_pile", "exhaust_pile"):
        value[pile].sort(key=lambda c: json.dumps(c, sort_keys=True))
    value["action_mask"] = value["action_mask"].tolist()
    return value


VERSIONS = [(c["name"], up) for c in CARD_BY_NAME.values() if c["id"] <= 35
            for up in range(c["max_upgrade"] + 1)]


@pytest.mark.parametrize("name,upgrade", VERSIONS)
def test_inherited_versions_preserve_transition_and_full_final_observation(name, upgrade):
    cards = [name + ("+1" if upgrade else "")] * 5 + ["Strike_R", "Defend_R"]
    candidate = scene(cards)
    old, expanded = PublicBattleEnv(max_actions=12), IroncladEnv(max_actions=12)
    a = old.reset(candidate, 982001, diagnostic=True)
    b = expanded.reset(candidate, 982001, diagnostic=True)
    assert legacy_view(b) == plain(a)
    rng = np.random.default_rng(20)
    for _ in range(12):
        action = int(rng.choice(np.flatnonzero(a["action_mask"])))
        a, reward, terminal, truncated, _ = old.step(action)
        b, other_reward, other_terminal, other_truncated, info = expanded.step(action)
        left, right = legacy_view(b), plain(a)
        if terminal:
            # 集成版终局清理全部敌人，旧版保留尸体或失败时存活者；独立比较其余结果。
            assert not any(e["present"] for e in b["enemies"])
            left.pop("enemies"); right.pop("enemies")
        assert left == right
        assert (reward, terminal, truncated) == (other_reward, other_terminal, other_truncated)
        assert info["contract_id"] == CONTRACT["schema"]
        assert info["observation_schema"] == b["schema"]
        if terminal or truncated:
            if truncated:
                assert b["action_mask"].any()
            break


def test_named_extensions_preserve_instance_differences():
    env = IroncladEnv()
    obs = env.reset(scene(["Strike_R"] * 5), 982001, diagnostic=True)
    encoded = semantic_extensions(obs)
    assert encoded["cards"].shape == (5, 14)
    assert encoded["cards"][:, 1].all()
    # 合成观测用于输入可辨识性，不冒称Rampage/Combust实战行为已验收。
    changed = copy.deepcopy(obs)
    changed["hand"][0]["combat_damage_bonus"] = 8
    changed["player"]["combust_hp_loss"] = 2
    assert not np.array_equal(encoded["cards"], semantic_extensions(changed)["cards"])
    assert not np.array_equal(encoded["player"], semantic_extensions(changed)["player"])


def test_hidden_fields_and_incomplete_phase_are_rejected():
    env = IroncladEnv()
    env.reset(scene(), 982001, diagnostic=True)
    raw = json.loads(env._env.observation())
    broken = copy.deepcopy(raw)
    broken["decision"] = {"phase": "SELECT_CARD", "selection": None}
    with pytest.raises(ValueError, match="选择阶段"):
        normalize_ironclad(broken)
    raw["hand"][0]["uniqueId"] = 33
    with pytest.raises(ValueError, match="隐藏字段"):
        normalize_ironclad(raw)


@pytest.mark.parametrize("card", ["Zap", "Alchemize", "Discovery", "Apparition"])
def test_out_of_scope_cards_remain_rejected(card):
    with pytest.raises(ValueError):
        IroncladEnv().reset(scene([card] * 5), 982001, diagnostic=True)


def test_training_and_other_encounters_remain_rejected():
    env = IroncladEnv()
    with pytest.raises(ValueError, match="正式采集"):
        env.reset(scene(), 982001, diagnostic=True, purpose="train")
    candidate = scene()
    candidate["encounter"] = "TIME_EATER"
    with pytest.raises(ValueError, match="遭遇"):
        env.reset(candidate, 982001, diagnostic=True)
