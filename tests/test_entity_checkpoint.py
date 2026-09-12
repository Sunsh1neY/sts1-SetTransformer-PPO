"""统一实体模型/Adam/Torch RNG更新边界精确恢复及不兼容拒绝。"""
import pytest
import torch

from sts.env.entities import collate, encode_observation
from sts.models.entities import UnifiedEntityActorCritic
from sts.train.entitycheckpoint import load_entity_checkpoint, save_entity_checkpoint
from test_unified_entities import observation


def update(model, optimizer, batch):
    optimizer.zero_grad(set_to_none=True)
    distribution, value = model.distribution(batch)
    action = distribution.sample()
    loss = -distribution.log_prob(action).mean() + value.square().mean() - 0.01 * distribution.entropy().mean()
    loss.backward()
    assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
    optimizer.step()
    return action.detach().clone(), loss.detach().clone()


def test_same_version_restores_optimizer_rng_and_next_update_exactly(tmp_path):
    _, obs = observation()
    batch = collate([encode_observation(obs)])
    torch.manual_seed(986020)
    model = UnifiedEntityActorCritic()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.00025)
    update(model, optimizer, batch)
    path = tmp_path / "update-1.pt"
    save_entity_checkpoint(path, model, optimizer, update_index=1)
    expected_action, expected_loss = update(model, optimizer, batch)
    expected = {k: v.clone() for k, v in model.state_dict().items()}
    restored, restored_optimizer, metadata = load_entity_checkpoint(path)
    actual_action, actual_loss = update(restored, restored_optimizer, batch)
    assert metadata["update_index"] == 1 and metadata["rng_restored"]
    torch.testing.assert_close(expected_action, actual_action, rtol=0, atol=0)
    torch.testing.assert_close(expected_loss, actual_loss, rtol=0, atol=0)
    for key, value in restored.state_dict().items():
        torch.testing.assert_close(expected[key], value, rtol=0, atol=0)
    for before, after in zip(optimizer.state.values(), restored_optimizer.state.values()):
        for key in before:
            torch.testing.assert_close(before[key], after[key], rtol=0, atol=0)


def test_old_checkpoints_and_changed_contracts_are_rejected(tmp_path):
    old = tmp_path / "old.pt"
    torch.save({"format_version": 2, "kind": "set"}, old)
    with pytest.raises(ValueError, match="旧MLP"):
        load_entity_checkpoint(old)
    path = tmp_path / "new.pt"
    save_entity_checkpoint(path, UnifiedEntityActorCritic())
    data = torch.load(path, weights_only=True)
    data["fingerprint"]["entity_contract_sha256"] = "different-input-layout"
    changed = tmp_path / "changed.pt"
    torch.save(data, changed)
    with pytest.raises(ValueError, match="契约"):
        load_entity_checkpoint(changed)


def test_checkpoint_does_not_claim_active_environment_restore(tmp_path):
    with pytest.raises(ValueError, match="无活动环境"):
        save_entity_checkpoint(tmp_path / "invalid.pt", UnifiedEntityActorCritic(), boundary="active_episode")


def test_checkpoint_rejects_implicit_half_precision_conversion(tmp_path):
    with pytest.raises(ValueError, match="FP32"):
        save_entity_checkpoint(tmp_path / "half.pt", UnifiedEntityActorCritic().half())


def test_changed_numerical_runtime_is_not_exact_restore(tmp_path):
    path = tmp_path / "runtime.pt"
    save_entity_checkpoint(path, UnifiedEntityActorCritic())
    data = torch.load(path, weights_only=True)
    data["fingerprint"]["numerical_runtime"]["threads"] += 1
    changed = tmp_path / "changed-runtime.pt"
    torch.save(data, changed)
    with pytest.raises(ValueError, match="契约"):
        load_entity_checkpoint(changed)
