"""逐牌等信息、动作路由、容量截断与PPO恢复的行为验证。"""
import copy

import numpy as np
import pytest
import torch

from sts.env.comparison import ComparisonEnv, card_count, load_contract
from sts.env.real_deck import load_batch, sample_scene
from sts.models.comparison import ComparisonActorCritic, SLOTS, encode, tensor_batch
from sts.train.comparison import ComparisonTrainer

torch.set_num_threads(1)


def observation():
    env = ComparisonEnv()
    obs = env.reset(sample_scene(load_batch(), np.random.default_rng(4)), 981000)
    return env, obs


def test_individual_duplicates_and_all_public_changes_encode():
    _, obs = observation()
    a = encode(obs)
    assert a["valid"].sum() == card_count(obs)
    changed = copy.deepcopy(obs)
    changed["hand"][0]["free_to_play_once"] = not changed["hand"][0]["free_to_play_once"]
    assert not np.array_equal(a["cards"], encode(changed)["cards"])
    changed = copy.deepcopy(obs)
    changed["player"]["statuses"]["Strength"] = 12
    assert not np.array_equal(a["global"], encode(changed)["global"])
    changed = copy.deepcopy(obs)
    changed["enemies"][0]["public_history"]["completed_enemy_turns"] = 2
    assert not np.array_equal(a["global"], encode(changed)["global"])
    changed = copy.deepcopy(obs)
    changed["draw_pile"] += [copy.deepcopy(obs["hand"][0])] * 3
    assert encode(changed)["valid"].sum() == a["valid"].sum() + 3
    changed["player"]["secret"] = 1
    with pytest.raises(ValueError, match="字段变化"):
        encode(changed)


def test_set_nonhand_invariance_and_hand_action_equivariance():
    _, obs = observation()
    x = tensor_batch([encode(obs)])
    model = ComparisonActorCritic("set", x["global"].shape[-1]).eval()
    a, av = model(x)
    y = {k: v.clone() for k, v in x.items()}
    order = torch.arange(SLOTS)
    order[10:] = order[10:].flip(0)
    for k in ("ids", "cards", "valid"):
        y[k] = y[k][:, order]
    b, bv = model(y)
    torch.testing.assert_close(a, b, atol=2e-6, rtol=1e-5)
    torch.testing.assert_close(av, bv, atol=2e-6, rtol=1e-5)
    order = torch.arange(SLOTS)
    order[0], order[1] = 1, 0
    y = {k: (v[:, order] if k in {"ids", "cards", "valid"} else v) for k, v in x.items()}
    c, cv = model(y)
    torch.testing.assert_close(a[:, :5], c[:, 5:10], atol=2e-6, rtol=1e-5)
    torch.testing.assert_close(av, cv, atol=2e-6, rtol=1e-5)


@pytest.mark.parametrize("kind", ["mlp", "set"])
def test_padding_and_mask_no_effect(kind):
    _, obs = observation()
    x = tensor_batch([encode(obs)])
    model = ComparisonActorCritic(kind, x["global"].shape[-1]).eval()
    a, av = model(x)
    y = {k: v.clone() for k, v in x.items()}
    y["cards"][~y["valid"]] = 100
    y["ids"][~y["valid"]] = 2
    b, bv = model(y)
    torch.testing.assert_close(a, b)
    torch.testing.assert_close(av, bv)
    dist, _ = model.distribution(x)
    assert not dist.probs[~x["mask"]].any()


@pytest.mark.parametrize("done", [False, True])
def test_capacity_full_final_observation_and_natural_priority(done):
    env, obs = observation()
    row = copy.deepcopy(obs["draw_pile"][0])
    obs["hand"] = []
    obs["draw_pile"] = [row] * 64
    obs["discard_pile"] = []
    obs["exhaust_pile"] = []
    class Backend:
        def step(self, action):
            return obs, 1.0 if done else 0, done, False, {"termination_reason": "victory" if done else "ongoing"}
    env.env = Backend()
    env.count = 56
    final, reward, terminated, truncated, info = env.step(50)
    assert card_count(final) == 64
    assert terminated == done and truncated != done
    assert info["termination_reason"] == ("victory" if done else "external_card_capacity")
    assert encode(final)["valid"].sum() == 64
    if not done:
        assert final["action_mask"].any() and reward == 0
    with pytest.raises(RuntimeError):
        env.step(50)


def test_frozen_generation_eight_has_final_state_headroom():
    c = load_contract()
    assert c["initial_cards"] == 14 and c["generated_per_action"] == 8
    assert c["truncate_at"] - 1 + c["generated_per_action"] == c["card_entities"]


@pytest.mark.parametrize("kind", ["mlp", "set"])
def test_ppo_update_and_checkpoint_exact_resume(kind, tmp_path):
    trainer = ComparisonTrainer(kind, iterations=3, num_envs=2, num_steps=8)
    initial = {k: v.clone() for k, v in trainer.model.state_dict().items()}
    trainer.iteration_step()
    assert any(not torch.equal(initial[k], v) for k, v in trainer.model.state_dict().items())
    path = tmp_path / "resume.pt"
    trainer.save(path)
    restored = ComparisonTrainer.load(path)
    for a, b in zip(trainer.observations, restored.observations):
        for k in a:
            np.testing.assert_array_equal(a[k], b[k])
    a, ae = trainer.iteration_step()
    b, be = restored.iteration_step()
    assert ae == be
    assert a["steps"] == b["steps"]
    for k, v in trainer.model.state_dict().items():
        torch.testing.assert_close(v, restored.model.state_dict()[k], rtol=0, atol=0)
