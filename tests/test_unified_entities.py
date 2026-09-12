"""统一实体动态长度、置换、路由、关系、可见性和合法性。"""
import copy

import numpy as np
import pytest
import torch

from sts.env.entities import Candidate, CONTRACT, FEATURE_DIMS, collate, encode_observation
from sts.env.ironclad import IroncladEnv
from sts.models.entities import UnifiedEntityActorCritic
from test_ironclad_expansion import scene
from test_ironclad_dynamics import play

torch.set_num_threads(1)


def observation(n=8, encounter="EXORDIUM_THUGS"):
    candidate = scene(["True Grit+1", "Sentinel", *["Strike_R"] * (n - 2)])
    candidate.update(encounter=encounter, burning_elite=False)
    candidate["relics"] = ["Burning Blood", "Vajra"]
    candidate["potions"] = ["Weak Potion", "Block Potion"]
    env = IroncladEnv()
    return env, env.reset(candidate, 986001, diagnostic=True)


def test_actual_entities_all_types_and_dynamic_padding_exceeds_old_64():
    _, small = observation(5)
    _, large = observation(96)
    a, b = encode_observation(small), encode_observation(large)
    assert {t.entity_type for t in a.tokens} == set(CONTRACT["types"])
    assert sum(t.entity_type == "CARD" for t in b.tokens) == 96
    batch = collate([a, b])
    assert batch["entity_valid"].shape == (2, len(b.tokens))
    assert batch["entity_valid"].sum(1).tolist() == [len(a.tokens), len(b.tokens)]
    assert batch["entity_valid"].shape[1] != 512
    assert "routes" not in batch and "decision_id" not in batch
    assert batch["features"]["PLAYER_GLOBAL"].shape[-1] == FEATURE_DIMS["PLAYER_GLOBAL"]


def test_all_entity_permutation_and_candidate_permutation_preserve_routed_policy():
    _, obs = observation()
    sample = encode_observation(obs)
    model = UnifiedEntityActorCritic().eval()
    order = np.random.default_rng(2).permutation(len(sample.tokens))
    other = sample.permuted(order)
    with torch.no_grad():
        first, value = model.distribution(collate([sample]))
        second, other_value = model.distribution(collate([other]))
    torch.testing.assert_close(first.probs, second.probs, rtol=1e-5, atol=1e-6)
    torch.testing.assert_close(value, other_value, rtol=1e-5, atol=1e-6)
    action_order = list(reversed(range(len(other.candidates))))
    other.candidates = [other.candidates[i] for i in action_order]
    other.routes = [other.routes[i] for i in action_order]
    with torch.no_grad():
        third, _ = model.distribution(collate([other]))
    torch.testing.assert_close(first.probs[:, action_order], third.probs, rtol=1e-5, atol=1e-6)


def test_padding_and_unrelated_type_storage_do_not_affect_valid_outputs():
    _, small = observation(5)
    _, large = observation(80)
    a, b = encode_observation(small), encode_observation(large)
    model = UnifiedEntityActorCritic().eval()
    combined = collate([a, b])
    for kind, values in combined["features"].items():
        values[~combined["entity_valid"]] = 9999
    combined["edges"][0, len(a.tokens):] = 1234
    with torch.no_grad():
        one, value = model.distribution(collate([a]))
        many, values = model.distribution(combined)
    torch.testing.assert_close(one.probs[0], many.probs[0, :len(a.candidates)], rtol=1e-5, atol=1e-6)
    torch.testing.assert_close(value[0], values[0], rtol=1e-5, atol=1e-6)
    assert not many.probs[~combined["candidate_valid"]].any()


def test_enemy_information_participates_in_card_attention_not_late_fusion():
    _, obs = observation()
    sample = encode_observation(obs)
    altered = copy.deepcopy(obs)
    next(e for e in altered["enemies"] if e["present"])["hp"] -= 5
    second = encode_observation(altered)
    # 玩家原始token不展开其他实体；敌人变化通过共同注意力影响卡牌。
    p = next(i for i, t in enumerate(sample.tokens) if t.entity_type == "PLAYER_GLOBAL")
    np.testing.assert_array_equal(sample.tokens[p].features, second.tokens[p].features)
    model = UnifiedEntityActorCritic()
    x, _ = model.encode_entities(collate([sample]))
    y, _ = model.encode_entities(collate([second]))
    assert not torch.allclose(x[:, 0], y[:, 0])
    assert len(model.blocks) == 2 and all(block.heads == 4 for block in model.blocks)


def test_every_legal_action_maps_to_real_source_and_target_entities():
    _, obs = observation()
    sample = encode_observation(obs)
    assert {r for c, r in zip(sample.candidates, sample.routes) if c.legal} == set(np.flatnonzero(obs["action_mask"]))
    for c in sample.candidates:
        if c.kind in {"PLAY_TARGET", "POTION_TARGET"}:
            assert sample.tokens[c.target].entity_type == "ENEMY"
        if c.kind.startswith("PLAY"):
            assert sample.tokens[c.source].entity_type == "CARD"
        if c.kind.startswith("POTION"):
            assert sample.tokens[c.source].entity_type == "POTION"
        if c.kind.endswith("SELF") or c.kind == "END_TURN":
            assert c.target == -1
    model = UnifiedEntityActorCritic()
    batch = collate([sample])
    distribution, _ = model.distribution(batch)
    assert not distribution.probs[~batch["legal"]].any()


def test_damage_preview_is_relation_and_not_fixed_enemy_slot_feature():
    _, obs = observation()
    changed = copy.deepcopy(obs)
    changed["hand"][0]["damage_by_target"][0] += 13
    a, b = encode_observation(obs), encode_observation(changed)
    np.testing.assert_array_equal(a.tokens[0].features, b.tokens[0].features)
    assert not np.array_equal(a.edges, b.edges)


@pytest.mark.parametrize("swap", ["hand", "enemy"])
def test_environment_slot_changes_only_remap_actions(swap):
    _, obs = observation()
    changed = copy.deepcopy(obs)
    mask = changed["action_mask"]
    if swap == "hand":
        changed["hand"][0], changed["hand"][1] = changed["hand"][1], changed["hand"][0]
        mask[:5], mask[5:10] = mask[5:10].copy(), mask[:5].copy()

        def remap(route):
            return route + 5 if route < 5 else route - 5 if route < 10 else route
    else:
        assert obs["enemies"][0]["present"] and obs["enemies"][1]["present"]
        changed["enemies"][0], changed["enemies"][1] = changed["enemies"][1], changed["enemies"][0]
        for zone in ("hand", "draw_pile", "discard_pile", "exhaust_pile", "resolving"):
            for card in changed[zone]:
                values = card["damage_by_target"]
                values[0], values[1] = values[1], values[0]
        affected = set()
        for i, card in enumerate(obs["hand"]):
            if card["target_kind"] == "ENEMY":
                affected.add(i * 5)
        for i, potion in enumerate(obs["potions"]):
            if potion["present"] and potion["target_kind"] == "ENEMY":
                affected.add(51 + i * 5)
        for base in affected:
            mask[base], mask[base + 1] = mask[base + 1], mask[base]

        def remap(route):
            return route + 1 if route in affected else route - 1 if route - 1 in affected else route
    a, b = encode_observation(obs), encode_observation(changed)
    model = UnifiedEntityActorCritic().eval()
    with torch.no_grad():
        da, va = model.distribution(collate([a]))
        db, vb = model.distribution(collate([b]))
    by_route = dict(zip(b.routes, db.probs[0].tolist()))
    np.testing.assert_allclose(da.probs[0].numpy(), [by_route[remap(r)] for r in a.routes], atol=1e-6, rtol=1e-5)
    torch.testing.assert_close(va, vb, atol=1e-6, rtol=1e-5)


def test_true_grit_candidates_reference_existing_entities_and_credentials_are_not_features():
    env, obs = observation(5, "LAGAVULIN")
    obs = play(env, obs, "True Grit")
    sample = encode_observation(obs)
    assert sum(t.entity_type == "CARD" for t in sample.tokens) == 5
    assert len(sample.candidates) == 4
    assert all(c.kind == "SELECT_CARD" for c in sample.candidates)
    changed = copy.deepcopy(obs)
    changed["decision"]["routing"]["decision_id"] = "different-envelope"
    other = encode_observation(changed)
    assert sample.routes != other.routes
    for x, y in zip(sample.tokens, other.tokens):
        np.testing.assert_array_equal(x.features, y.features)
    model = UnifiedEntityActorCritic()
    distribution, _ = model.distribution(collate([sample]))
    obs, _, _, _, _ = env.step(sample.routes[distribution.sample().item()])
    assert obs["decision"]["phase"] == "NORMAL"


@pytest.mark.parametrize("entity,key", [("enemies", "seed"), ("potions", "private_counter"), ("hand", "slot")])
def test_hidden_or_unregistered_fields_are_rejected(entity, key):
    _, obs = observation()
    obs[entity][0][key] = 123
    with pytest.raises(ValueError):
        encode_observation(obs)


def test_resource_guards_reject_instead_of_slicing_and_bad_refs_fail():
    _, obs = observation(80)
    sample = encode_observation(obs)
    with pytest.raises(ValueError, match="资源"):
        collate([sample], resources={**CONTRACT["resources"], "max_entities": 64})
    with pytest.raises(ValueError, match="资源"):
        collate([sample], resources={**CONTRACT["resources"], "max_attention_elements": 1})
    sample.candidates[0] = Candidate("PLAY_TARGET", len(sample.tokens), -1, True)
    with pytest.raises(ValueError, match="引用"):
        collate([sample])


def test_terminal_value_without_fake_action_and_configurable_depth():
    _, obs = observation()
    obs["action_mask"][:] = False
    batch = collate([encode_observation(obs)])
    model = UnifiedEntityActorCritic({"layers": 3, "width": 48, "heads": 6, "ff_width": 96, "dropout": 0.0})
    assert len(model.blocks) == 3
    scores, value = model(batch)
    assert torch.isfinite(value).all() and torch.isneginf(scores).all()
    with pytest.raises(ValueError, match="终局"):
        model.distribution(batch)


def test_backward_reaches_each_entity_projection_and_is_finite():
    _, obs = observation()
    batch = collate([encode_observation(obs)])
    model = UnifiedEntityActorCritic()
    distribution, value = model.distribution(batch)
    loss = -distribution.log_prob(distribution.sample()).mean() + value.square().mean()
    loss.backward()
    for projection in model.projections.values():
        assert projection.weight.grad is not None and projection.weight.grad.abs().sum() > 0
    assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)


def test_offer_cards_and_resolving_potion_have_distinct_lifecycle_and_origin():
    _, obs = observation()
    # 纯接口夹具，不执行或宣称新药水机制已实现。
    obs["offers"] = [copy.deepcopy(obs["hand"][0]), copy.deepcopy(obs["hand"][1])]
    obs["resolving_potions"] = [copy.deepcopy(obs["potions"][0])]
    obs["potions"][0] = {"name": "", "present": False, "potency": 0, "target_kind": "NO_TARGET", "potion_id": 0}
    obs["action_mask"][:] = False
    obs["decision"] = {"phase": "SELECT_CARD", "selection": {"phase": "SELECT_CARD", "selection_kind": "DISCOVERY",
                        "candidate_zone": "offer", "min_choices": 1, "max_choices": 1,
                        "candidates": copy.deepcopy(obs["offers"]), "candidate_mask": [True, False]},
                       "routing": {"decision_id": "interface-fixture", "source_ref": {"region": "resolving_potion", "index": 0}}}
    sample = encode_observation(obs)
    assert len(sample.candidates) == 2
    assert all(sample.tokens[c.source].entity_type == "CARD" and sample.tokens[c.target].entity_type == "POTION"
               for c in sample.candidates)
    assert sample.tokens[sample.candidates[0].target].features[-2:].tolist() == [0, 1]
    distribution, _ = UnifiedEntityActorCritic().distribution(collate([sample]))
    assert distribution.probs[0].tolist() == [1, 0]
    assert "source_ref" not in sample.routes[0]


def test_shared_candidates_reject_wrong_entity_types_and_boolean_indices():
    _, obs = observation()
    sample = encode_observation(obs)
    enemy = next(i for i, t in enumerate(sample.tokens) if t.entity_type == "ENEMY")
    for invalid in (Candidate("PLAY_TARGET", enemy, enemy, True), Candidate("PLAY_SELF", True, -1, True),
                    Candidate("PLAY_SELF", 0, enemy, True)):
        changed = copy.deepcopy(sample)
        changed.candidates[0] = invalid
        with pytest.raises(ValueError):
            collate([changed])
