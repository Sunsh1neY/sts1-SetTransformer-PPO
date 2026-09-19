"""Branch isolation and current checkpoint round-trip for the 2+2+2 model."""
import copy
import torch
import pytest

from sts.models.apath import APathActorCritic, batch_samples, encode
from test_unified_entities import observation


def active(module):
    return any(p.grad is not None and p.grad.abs().sum() > 0 for p in module.parameters())


def test_actor_and_critic_gradients_share_only_trunk():
    torch.manual_seed(10)
    model = APathActorCritic()
    _, obs = observation()
    batch = batch_samples([encode(obs)])
    dist, value = model(batch)
    (-dist.entropy().sum()).backward()
    assert active(model.shared_blocks) and active(model.actor_blocks)
    assert not active(model.critic_blocks) and not active(model.critic_pool)
    assert not active(model.value_head)
    model.zero_grad(set_to_none=True)
    _, value = model(batch)
    value.sum().backward()
    assert active(model.shared_blocks) and active(model.critic_blocks)
    assert active(model.critic_pool) and active(model.value_head)
    assert not active(model.actor_blocks) and not active(model.pool)
    assert not active(model.source_key)


def test_private_branch_perturbation_does_not_change_other_output():
    torch.manual_seed(11)
    model = APathActorCritic().eval()
    _, obs = observation()
    batch = batch_samples([encode(obs)])
    with torch.no_grad():
        before, value = model(batch)
        model.actor_blocks[0].ff[0].weight.add_(torch.randn_like(model.actor_blocks[0].ff[0].weight)*.2)
        after, new_value = model(batch)
        torch.testing.assert_close(value,new_value,rtol=0,atol=0)
        assert not torch.allclose(before.probs,after.probs)
        model.critic_blocks[0].ff[0].weight.add_(torch.randn_like(model.critic_blocks[0].ff[0].weight)*.2)
        last, last_value = model(batch)
        torch.testing.assert_close(after.probs,last.probs,rtol=0,atol=0)
        assert not torch.allclose(new_value,last_value)
        torch.testing.assert_close(model.value_only(batch),last_value)


def test_topology_and_state_dict_roundtrip_reject_old_keys():
    model = APathActorCritic()
    assert [len(model.shared_blocks),len(model.actor_blocks),len(model.critic_blocks)] == [2,2,2]
    sets = [{id(p) for p in blocks.parameters()} for blocks in (model.shared_blocks,model.actor_blocks,model.critic_blocks)]
    assert not sets[0]&sets[1] and not sets[0]&sets[2] and not sets[1]&sets[2]
    restored = APathActorCritic()
    restored.load_state_dict(model.state_dict(),strict=True)
    for key,value in model.state_dict().items():
        torch.testing.assert_close(value,restored.state_dict()[key],rtol=0,atol=0)
    old = copy.deepcopy(model.state_dict())
    old['blocks.0.qkv.weight'] = old.pop('shared_blocks.0.qkv.weight')
    with pytest.raises(RuntimeError):
        restored.load_state_dict(old,strict=True)
