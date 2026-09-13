"""扩展Set输入的实例对应、掩码、梯度和同版权重恢复。"""
import copy

import numpy as np
import pytest
import torch

from sts.env.ironclad import IroncladEnv
from sts.models.comparison import ComparisonActorCritic, tensor_batch
from sts.models.ironclad import IroncladActorCritic, encode
from test_ironclad_expansion import scene

torch.set_num_threads(1)


def observation():
    return IroncladEnv().reset(scene(["Strike_R"] * 12), 982001, diagnostic=True)


def test_all_extension_fields_enter_numeric_input():
    obs = observation()
    a = encode(obs)
    for key, value in {"combat_damage_bonus": 8, "is_strike": False,
                       "effective_exhaust": True, "cost_kind": "X"}.items():
        changed = copy.deepcopy(obs)
        changed["hand"][0][key] = value
        assert not np.array_equal(a["cards"], encode(changed)["cards"])
    changed = copy.deepcopy(obs)
    changed["player"]["combust_hp_loss"] = 2
    assert not np.array_equal(a["global"], encode(changed)["global"])


def test_duplicate_dynamic_rows_stay_attached_and_set_ignores_nonhand_order():
    obs = observation()
    for i, card in enumerate(obs["draw_pile"]):
        card["combat_damage_bonus"] = i * 8
    a = encode(obs)
    assert a["valid"].sum() == 12
    assert sorted(a["cards"][5:12, -14]) == pytest.approx([i * 8 / 50 for i in range(7)])
    shuffled = copy.deepcopy(obs)
    shuffled["draw_pile"].reverse()
    b = encode(shuffled)
    model = IroncladActorCritic(a["global"].size).eval()
    with torch.no_grad():
        distribution, value = model.distribution(tensor_batch([a]))
        other_distribution, other_value = model.distribution(tensor_batch([b]))
    torch.testing.assert_close(distribution.probs, other_distribution.probs, atol=1e-6, rtol=1e-5)
    torch.testing.assert_close(value, other_value, atol=1e-6, rtol=1e-5)


def test_legal_distribution_gradients_and_same_version_weights(tmp_path):
    batch = tensor_batch([encode(observation())])
    model = IroncladActorCritic(batch["global"].shape[-1])
    distribution, value = model.distribution(batch)
    assert not distribution.probs[~batch["mask"]].any()
    action = distribution.sample()
    loss = -distribution.log_prob(action).mean() + value.square().mean()
    loss.backward()
    assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
    path = tmp_path / "weights.pt"
    torch.save(model.state_dict(), path)
    restored = IroncladActorCritic(batch["global"].shape[-1])
    restored.load_state_dict(torch.load(path, weights_only=True))
    for a, b in zip(model(batch), restored(batch)):
        torch.testing.assert_close(a, b, rtol=0, atol=0)
    old = ComparisonActorCritic("set", batch["global"].shape[-1] - 1)
    with pytest.raises(RuntimeError):
        model.load_state_dict(old.state_dict())


def test_capacity_and_unknown_fields_fail_without_truncating_input():
    obs = observation()
    obs["draw_pile"] *= 10
    with pytest.raises(ValueError, match="容量"):
        encode(obs)
    obs = observation()
    obs["hand"][0]["unregistered"] = 1
    with pytest.raises(ValueError, match="字段变化"):
        encode(obs)
