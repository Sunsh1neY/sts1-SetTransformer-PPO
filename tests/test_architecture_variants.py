"""Architecture isolation, exact M0 initialization and model API regression."""
import copy
import pytest
import torch
from sts.models.apath import APathActorCritic, TASKS, batch_samples, encode
from sts.models.architectures import build_model
from test_unified_entities import observation

torch.set_num_threads(1)


def models_and_batch():
    torch.manual_seed(19)
    baseline = build_model("m0_baseline")
    torch.manual_seed(19)
    variant = build_model("m2a_source_context")
    _, obs = observation()
    return baseline, variant, batch_samples([encode(obs)])


def test_m0_alias_and_initial_pairing():
    baseline, variant, batch = models_and_batch()
    assert type(baseline) is APathActorCritic
    for key, value in baseline.state_dict().items():
        torch.testing.assert_close(value, variant.state_dict()[key], rtol=0, atol=0)
    d0, v0 = baseline(batch)
    d1, v1 = variant(batch)
    torch.testing.assert_close(d0.probs, d1.probs, rtol=0, atol=0)
    torch.testing.assert_close(v0, v1, rtol=0, atol=0)
    assert baseline.model_version != variant.model_version
    with pytest.raises(RuntimeError):
        variant.load_state_dict(baseline.state_dict())
    with pytest.raises(ValueError):
        build_model("unknown")


def test_raw_head_gradient_isolation_and_context_dependency():
    _, model, batch = models_and_batch()
    # Activate the residual for structural sensitivity/gradient testing.
    torch.nn.init.normal_(model.source_query_delta[-1].weight, std=.02)
    h, _ = model.encode_entities(batch)
    source, target = model.readout_logits(h, batch)
    end = batch["task"] == TASKS.index("END_TURN")
    live = batch["source_mask"] & ~end
    assert live.any() and end.any()
    source[live].sum().backward()
    assert model.pool_seed.grad is None or not model.pool_seed.grad.any()
    assert model.pool.in_proj_weight.grad is None or not model.pool.in_proj_weight.grad.any()
    assert model.source_context_pool.attention.in_proj_weight.grad.abs().sum() > 0
    assert model.actor_blocks[0].parameters().__next__().grad is not None
    original_source, original_target = source.detach(), target.detach()
    with torch.no_grad():
        model.source_context_pool.final.bias.add_(torch.randn(64))
        changed_source, changed_target = model.readout_logits(h.detach(), batch)
    torch.testing.assert_close(original_source[end], changed_source[end], rtol=0, atol=0)
    torch.testing.assert_close(original_target, changed_target, rtol=0, atol=0)
    assert not torch.equal(original_source[live], changed_source[live])


def test_masked_pool_and_checkpoint_roundtrip(tmp_path):
    _, model, batch = models_and_batch()
    entities = torch.randn(1, 4, 64)
    valid = torch.tensor([[True, True, False, False]])
    expected = model.source_context_pool(entities, valid)
    entities[:, 2:] = 1e6
    torch.testing.assert_close(expected, model.source_context_pool(entities, valid))
    path = tmp_path / "m2a.pt"
    torch.save({"model_version": model.model_version, "state_dict": model.state_dict()}, path)
    restored = build_model("m2a_source_context")
    checkpoint = torch.load(path, weights_only=True)
    assert checkpoint["model_version"] == restored.model_version
    restored.load_state_dict(checkpoint["state_dict"], strict=True)
    torch.testing.assert_close(model(batch)[0].probs, restored(batch)[0].probs)
    u, j, old, value = model.act(batch, torch.Generator().manual_seed(11))
    logp, entropy, evaluated_value = model.evaluate_actions(batch, u, j)
    torch.testing.assert_close(old, logp)
    torch.testing.assert_close(value, evaluated_value)
    loss = -(logp + .01 * entropy).mean() + evaluated_value.square().mean()
    loss.backward()
    assert model.source_query_delta[-1].weight.grad.abs().sum() > 0
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())
    torch.testing.assert_close(model.value_only(batch), evaluated_value)
