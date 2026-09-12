"""统一实体采集超过64张后的完整输入、资源切段与选牌计数。"""
import pytest

from sts.env.entities import collate, encode_observation
from sts.env.entitycollection import UnifiedEntityCollectionEnv
from test_ironclad_expansion import scene


def test_unified_collection_accepts_96_initial_cards_without_old_model_cap():
    env = UnifiedEntityCollectionEnv()
    obs = env.reset(scene(["Strike_R"] * 96), 986101, diagnostic=True)
    sample = encode_observation(obs)
    assert sum(t.entity_type == "CARD" for t in sample.tokens) == 96
    assert collate([sample])["entity_valid"].sum() == len(sample.tokens)
    with pytest.raises(ValueError, match="96"):
        env.reset(scene(["Strike_R"] * 97), 986101, diagnostic=True)


def test_real_sentry_generation_reaches_new_resource_cut_with_complete_entities():
    env = UnifiedEntityCollectionEnv(max_actions=128)
    candidate = scene(["Defend_R"] * 96)
    candidate.update(encounter="THREE_SENTRIES", burning_elite=False, relics=[])
    candidate["player"].update(hp=32767, max_hp=32767)
    obs = env.reset(candidate, 986102, diagnostic=True)
    for _ in range(128):
        obs, reward, terminated, truncated, info = env.step(50)
        if terminated or truncated:
            break
    assert truncated and not terminated and reward == 0
    assert info["termination_reason"] == "external_card_capacity"
    assert 466 <= info["card_entities"] <= 480
    sample = encode_observation(obs)
    assert sum(t.entity_type == "CARD" for t in sample.tokens) == info["card_entities"]
    assert collate([sample])["entity_valid"].sum() == len(sample.tokens)


def test_real_selection_is_a_separate_decision_with_resolving_card_counted():
    env = UnifiedEntityCollectionEnv()
    obs = env.reset(scene(["True Grit+1", "Sentinel", *["Defend_R"] * 3]), 986103, diagnostic=True)
    slot = next(i for i, c in enumerate(obs["hand"]) if c["name"] == "True Grit")
    obs, _, _, _, info = env.step(slot * 5)
    assert info["card_plays"] == info["decision_steps"] == 1 and info["card_entities"] == 5
    sample = encode_observation(obs)
    assert all(c.kind == "SELECT_CARD" for c in sample.candidates)
    obs, _, _, _, info = env.step(sample.routes[0])
    assert info["card_plays"] == info["selections"] == 1 and info["decision_steps"] == 2


def test_backend_change_invalidates_capacity_proof_before_reset(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import sts.env.entitycollection as module
    changed = tmp_path / "different-backend.bin"
    changed.write_bytes(b"unproved-backend")
    monkeypatch.setattr(module, "_load_backend", lambda: SimpleNamespace(__file__=str(changed)))
    with pytest.raises(ValueError, match="后端"):
        UnifiedEntityCollectionEnv()
