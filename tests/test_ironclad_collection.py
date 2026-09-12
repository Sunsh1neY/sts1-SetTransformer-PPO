"""完整最终状态、自举边界与累计分配计数的真实环境测试。"""
import pytest
import torch

from sts.env.ironclad_collection import IroncladCollectionEnv, load_capacity
from sts.models.comparison import tensor_batch
from sts.models.ironclad import IroncladActorCritic, encode
from sts.train.ppo import compute_gae
from test_ironclad_expansion import scene


def test_generated_cards_fit_complete_final_observation_at_capacity_cut():
    env = IroncladCollectionEnv()
    initial = env.reset(scene(["Power Through"] * 49), 982201, diagnostic=True)
    final, reward, terminated, truncated, info = env.step(0)
    assert not terminated and truncated and reward == 0
    assert info["card_entities"] == info["allocated_card_entities"] == 51
    assert info["generated_card_entities"] == 2
    assert info["truncation_reasons"] == ["external_card_capacity"]
    assert info["decision_steps"] == info["card_plays"] == 1
    assert final["action_mask"].any()
    assert encode(final)["valid"].sum() == 51
    assert "allocated_card_entities" not in final
    assert len(final["hand"]) == len(initial["hand"]) + 1
    with pytest.raises(RuntimeError, match="reset"):
        env.step(50)


def test_capacity_final_value_bootstraps_without_crossing_reset():
    env = IroncladCollectionEnv()
    initial = env.reset(scene(["Power Through"] * 49), 982201, diagnostic=True)
    final, _, _, _, _ = env.step(0)
    batch = tensor_batch([encode(initial), encode(final)])
    model = IroncladActorCritic(batch["global"].shape[-1])
    with torch.no_grad():
        _, values = model(batch)
    rewards = torch.tensor([[0.0], [100.0]])
    previous = torch.stack([values[0], torch.tensor(0.0)])[:, None]
    next_values = torch.stack([values[1], torch.tensor(0.0)])[:, None]
    advantages, returns = compute_gae(rewards, previous, next_values,
                                      torch.tensor([[False], [True]]),
                                      truncated=torch.tensor([[True], [False]]))
    torch.testing.assert_close(advantages[0, 0], values[1] - values[0])
    torch.testing.assert_close(returns[0, 0], values[1])


def test_action_and_entity_budget_reasons_are_both_recorded():
    env = IroncladCollectionEnv(max_actions=1)
    env.reset(scene(["Power Through"] * 49), 982201, diagnostic=True)
    _, reward, terminated, truncated, info = env.step(0)
    assert reward == 0 and not terminated and truncated
    assert set(info["truncation_reasons"]) == {"external_action_budget", "external_card_capacity"}


def test_power_leaves_regions_but_does_not_recycle_allocated_ids():
    env = IroncladCollectionEnv()
    obs = env.reset(scene(["Barricade", *["Defend_R"] * 4]), 982201, diagnostic=True)
    slot = next(i for i, c in enumerate(obs["hand"]) if c["name"] == "Barricade")
    _, _, _, _, info = env.step(slot * 5)
    assert info["card_entities"] == 4 and info["allocated_card_entities"] == 5
    assert info["generated_card_entities"] == 0


def test_failed_reset_invalidates_previous_collection():
    env = IroncladCollectionEnv()
    env.reset(scene(["Defend_R"] * 5), 982201, diagnostic=True)
    with pytest.raises(ValueError, match="49"):
        env.reset(scene(["Defend_R"] * 50), 982201, diagnostic=True)
    with pytest.raises(RuntimeError, match="reset"):
        env.step(50)


def test_capacity_proof_cannot_silently_follow_new_card_registry(monkeypatch):
    import sts.env.ironclad_collection as module
    monkeypatch.setattr(module, "REGISTRY_HASH", "unproved-content")
    with pytest.raises(ValueError, match="重新证明"):
        load_capacity()
