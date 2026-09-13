"""统一实体结构、动态路由及真实PPO恢复验收。"""
import copy
import numpy as np
import torch

from sts.env.unified import UnifiedEnv
from sts.env.real_deck import load_batch, sample_scene
from sts.models.unified import UnifiedActorCritic, encode, tensor_batch
from sts.train.unified import UnifiedTrainer

torch.set_num_threads(1)


def observation():
    env = UnifiedEnv()
    return env, env.reset(sample_scene(load_batch(), np.random.default_rng(4)), 981000)


def test_dynamic_entities_padding_and_each_type():
    _, obs = observation()
    expanded = copy.deepcopy(obs)
    expanded['draw_pile'] += [copy.deepcopy(obs['hand'][0]) for _ in range(90)]
    rows = [encode(obs), encode(expanded)]
    assert len(rows[1]['valid']) > 100
    model = UnifiedActorCritic().eval()
    small = model(tensor_batch(rows[:1]))
    padded = model(tensor_batch(rows))
    for a, b in zip(small, padded):
        torch.testing.assert_close(a[0], b[0], atol=3e-6, rtol=2e-5)
    batch = tensor_batch(rows)
    distribution, value = model.distribution(batch)
    (value.mean() + distribution.entropy().mean()).backward()
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())
    assert len(model.blocks) == 4
    assert set(rows[0]['kinds']) >= {0, 1, 3, 4}


def test_entity_permutation_with_route_remap():
    _, obs = observation()
    batch = tensor_batch([encode(obs)])
    model = UnifiedActorCritic().eval()
    a, av = model(batch)
    n = batch['valid'].shape[1]
    order = torch.arange(n-1, -1, -1)
    inverse = torch.argsort(order)
    other = {k: v.clone() for k, v in batch.items()}
    for key in ('features', 'kinds', 'ids', 'valid'):
        other[key] = other[key][:, order]
    other['sources'] = inverse[other['sources']]
    t = other['targets']
    other['targets'] = torch.where(t >= 0, inverse[t.clamp_min(0)], t)
    b, bv = model(other)
    torch.testing.assert_close(a, b, atol=3e-6, rtol=2e-5)
    torch.testing.assert_close(av, bv, atol=3e-6, rtol=2e-5)


def test_enemy_swap_routes_and_global_invariance():
    _, obs = observation()
    # 使用真实公开记录，构造两敌人的输入夹具；不把它当机制对拍。
    obs['enemies'][1] = copy.deepcopy(obs['enemies'][0])
    obs['enemies'][1]['hp'] = 3
    for region in ('hand', 'draw_pile', 'discard_pile', 'exhaust_pile'):
        for card in obs[region]:
            card['damage_by_target'][0:2] = [6, 9]
    other = copy.deepcopy(obs)
    other['enemies'][0], other['enemies'][1] = other['enemies'][1], other['enemies'][0]
    for region in ('hand', 'draw_pile', 'discard_pile', 'exhaust_pile'):
        for card in other[region]:
            card['damage_by_target'][0:2] = card['damage_by_target'][1::-1]
    model = UnifiedActorCritic().eval()
    a, av = model(tensor_batch([encode(obs)]))
    b, bv = model(tensor_batch([encode(other)]))
    torch.testing.assert_close(av, bv, atol=3e-6, rtol=2e-5)
    for slot, card in enumerate(obs['hand']):
        if card['target_kind'] == 'ENEMY':
            torch.testing.assert_close(a[:, slot*5], b[:, slot*5+1], atol=3e-6, rtol=2e-5)
    torch.testing.assert_close(a[:, 50], b[:, 50], atol=3e-6, rtol=2e-5)


def test_enemy_information_reaches_card_attention():
    _, obs = observation()
    changed = copy.deepcopy(obs)
    changed['enemies'][0]['hp'] += 25
    model = UnifiedActorCritic().eval()
    a = model.contextual(tensor_batch([encode(obs)]))
    b = model.contextual(tensor_batch([encode(changed)]))
    assert not torch.allclose(a[:, 0], b[:, 0])


def test_exact_next_update_after_restore(tmp_path):
    trainer = UnifiedTrainer('set', iterations=3, num_envs=2, num_steps=4)
    trainer.iteration_step()
    path = tmp_path / 'checkpoint.pt'
    trainer.save(path)
    restored = UnifiedTrainer.load(path)
    trainer.iteration_step()
    restored.iteration_step()
    assert trainer.env_steps == restored.env_steps == 16
    for key, value in trainer.model.state_dict().items():
        torch.testing.assert_close(value, restored.model.state_dict()[key], rtol=0, atol=0)


def test_legal_distribution_and_distinct_checkpoint():
    _, obs = observation()
    batch = tensor_batch([encode(obs)])
    distribution, value = UnifiedActorCritic().distribution(batch)
    assert torch.all(distribution.probs[~batch['mask']] == 0)
    assert torch.isfinite(value).all()
    torch.testing.assert_close(distribution.probs.sum(-1), torch.ones(1))


def test_hand_and_potion_swap_route_probabilities():
    _, obs = observation()
    other = copy.deepcopy(obs)
    other['hand'][0], other['hand'][1] = other['hand'][1], other['hand'][0]
    order = np.arange(66)
    order[:10] = np.r_[np.arange(5, 10), np.arange(5)]
    other['action_mask'] = np.asarray(obs['action_mask'])[order]
    model = UnifiedActorCritic().eval()
    a, av = model.distribution(tensor_batch([encode(obs)]))
    b, bv = model.distribution(tensor_batch([encode(other)]))
    torch.testing.assert_close(a.probs[:, order], b.probs, atol=3e-6, rtol=2e-5)
    torch.testing.assert_close(av, bv, atol=3e-6, rtol=2e-5)


def test_five_types_reach_attention_and_gradients():
    batch = load_batch()
    from sts.env.real_deck import configured_scene
    row = next(r for r in batch['decks'] if r['split'] == 'train')
    scene = configured_scene(batch, row['deck_id'], 'wounded-equipped', 'JAW_WORM')
    obs = UnifiedEnv().reset(scene, 982000)
    encoded = encode(obs)
    assert set(encoded['kinds']) == {0, 1, 2, 3, 4}
    model = UnifiedActorCritic()
    logits, value = model(tensor_batch([encoded]))
    (logits.square().mean() + value.square().mean()).backward()
    for projection in model.projections:
        assert projection[0].weight.grad.abs().sum() > 0
    other = copy.deepcopy(obs)
    other['potions'][0], other['potions'][1] = other['potions'][1], other['potions'][0]
    order = np.arange(66)
    order[51:61] = np.r_[np.arange(56, 61), np.arange(51, 56)]
    other['action_mask'] = np.asarray(obs['action_mask'])[order]
    model.eval()
    a, av = model.distribution(tensor_batch([encode(obs)]))
    b, bv = model.distribution(tensor_batch([encode(other)]))
    torch.testing.assert_close(a.probs[:, order], b.probs, atol=3e-6, rtol=2e-5)
    torch.testing.assert_close(av, bv, atol=3e-6, rtol=2e-5)


def test_public_time_truncation_retains_full_observation():
    env = UnifiedEnv()
    # 真实后端仅缩短外部步数预算，直接验证新包装的截断路径。
    from sts.env.public_battle import PublicBattleEnv
    env.env = PublicBattleEnv(max_actions=1)
    obs = env.reset(sample_scene(load_batch(), np.random.default_rng(4)), 981000)
    final, reward, done, truncated, info = env.step(50)
    assert truncated and not done
    inputs = tensor_batch([encode(final)])
    assert inputs['valid'].sum() == sum(len(final[k]) for k in ('hand', 'draw_pile', 'discard_pile', 'exhaust_pile')) + sum(e['present'] for e in final['enemies']) + sum(p['present'] for p in final['potions']) + len(final['relics']) + 1
    assert np.array_equal(inputs['mask'][0].numpy(), final['action_mask'])
    from sts.train.ppo import compute_gae
    with torch.no_grad():
        nextvalue = UnifiedActorCritic()(inputs)[1].reshape(1, 1)
    advantages, returns = compute_gae(torch.tensor([[reward]]), torch.zeros(1, 1), nextvalue,
        torch.zeros(1, 1, dtype=torch.bool), truncated=torch.ones(1, 1, dtype=torch.bool),
        episode_ends=torch.ones(1, 1, dtype=torch.bool), gamma=1, gae_lambda=.95)
    torch.testing.assert_close(returns, torch.tensor([[reward]]) + nextvalue)
