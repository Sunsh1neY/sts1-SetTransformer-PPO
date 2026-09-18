"""A路径项目实现验收：数学oracle、真实路由、上下文、梯度和边界。"""
import copy
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import torch

from sts.env.entities import Candidate, TYPES, encode_observation
from sts.models.apath import APathActorCritic, JointDistribution, TASKS, adapt, batch_samples, encode
from sts.train.ppo import ppo_loss
from sts.agents.apath import APathAgent
from test_unified_entities import observation
from test_ironclad_dynamics import start, play

torch.set_num_threads(1)


def golden():
    fixture = json.loads((Path(__file__).parents[1] / 'a-path/a-path-acceptance-cases.json').read_text(encoding='utf-8'))
    rows = fixture['joint_probability_case']['sources']
    s = torch.tensor([[r['p_source'] for r in rows]], dtype=torch.float64).log().requires_grad_()
    t = torch.tensor([[[.7, .3], [1., 1.], [.25, .75], [1., 1.]]], dtype=torch.float64).log().requires_grad_()
    mask = torch.tensor([[[True, True], [True, False], [True, True], [True, False]]])
    return fixture, s, t, mask, JointDistribution(s, t, mask.any(-1), mask)


def test_golden_probabilities_joint_logp_ratio_entropy_and_gradient():
    fixture, s, t, mask, d = golden()
    expected = fixture['joint_probability_case']
    torch.testing.assert_close(d.probs[mask], torch.tensor(expected['expected_joint_probs'], dtype=torch.float64))
    assert d.entropy().item() == pytest.approx(expected['expected_joint_entropy_nats'])
    oracle = -(d.probs[mask] * d.probs[mask].log()).sum()
    actual_grad = torch.autograd.grad(d.entropy().sum(), (s, t), retain_graph=True)
    expected_grad = torch.autograd.grad(oracle, (s, t))
    for actual, expected in zip(actual_grad, expected_grad):
        torch.testing.assert_close(actual, expected)
    old = d.log_prob(torch.tensor([0]), torch.tensor([0]))
    assert old.item() == pytest.approx(fixture['selected_action_ratio_case']['expected_old_joint_log_probability'])
    ratio = (torch.tensor(.45 * .6).log() - old).exp()
    assert ratio.item() == pytest.approx(fixture['selected_action_ratio_case']['expected_ratio'])
    assert d.target_logp[0, 1, 0] == 0
    assert not d.probs[~mask].any()


def test_shift_invariance_target_count_and_sequential_greedy_counterexample():
    _, s, t, mask, d = golden()
    shifted = JointDistribution(s, t + torch.tensor([[[20.], [-50.], [100.], [7.]]]), mask.any(-1), mask)
    torch.testing.assert_close(d.probs, shifted.probs)
    extra = mask.clone(); extra[0, 1, 1] = True
    more = JointDistribution(s, t, extra.any(-1), extra)
    torch.testing.assert_close(d.source_probs, more.source_probs)
    s = torch.tensor([[.6, .4]]).log()
    t = torch.tensor([[[.51, .49], [1., 1.]]]).log()
    mask = torch.tensor([[[True, True], [True, False]]])
    d = JointDistribution(s, t, mask.any(-1), mask)
    assert tuple(v.item() for v in d.sequential_greedy()) == (0, 0)
    assert tuple(v.item() for v in d.joint_map()) == (1, 0)


def test_single_joint_ppo_clip_detects_independent_clip_error():
    z = torch.zeros(1)
    loss, stats = ppo_loss(torch.tensor([1.15 * 1.15]).log(), z, torch.ones(1), z, z, z, z,
                           ent_coef=0, vf_coef=0, norm_adv=False)
    assert loss.item() == pytest.approx(-1.2)
    assert stats['clip_fraction'] == 1
    assert loss.item() != pytest.approx(-1.15 * 1.15)


def routed(sample, distribution, row=0):
    return {json.dumps(route, sort_keys=True): distribution.probs[row, u, j].item()
            for u, rs in enumerate(sample.routes) for j, route in enumerate(rs)}


def test_actual_codec_duplicates_and_act_evaluate_one_encoding():
    env, obs = observation()
    sample = encode(obs)
    assert sum(len(row) for row in sample.targets) == sum(obs['action_mask'])
    assert len(sample.sources) < sum(len(row) for row in sample.targets)
    assert len(sample.sources) == len(set(zip(sample.tasks, sample.sources)))
    for u, rs in enumerate(sample.routes):
        for j, route in enumerate(rs):
            assert sample.decompose(route) == (u, j)
            assert sample.route(u, j) == route
    model = APathActorCritic()
    batch = batch_samples([sample])
    with patch.object(model, 'encode_entities', wraps=model.encode_entities) as encoder, patch.object(env, 'step', wraps=env.step) as step:
        u, j, old_logp, value = model.act(batch, torch.Generator().manual_seed(3))
        assert encoder.call_count == 1 and step.call_count == 0
        route = sample.route(u.item(), j.item())
        env.step(route)
        assert step.call_count == 1
    logp, entropy, new_value = model.evaluate_actions(batch, u, j)
    torch.testing.assert_close(logp, old_logp)
    torch.testing.assert_close(value, new_value)
    assert logp.shape == entropy.shape == value.shape == (1,)
    with pytest.raises(ValueError):
        env.step(route)


def test_permutation_padding_batch_isolation_and_snapshot_immutability():
    _, obs = observation()
    raw = encode(obs).entities
    sample = adapt(raw)
    other = adapt(raw.permuted(np.random.default_rng(4).permutation(len(raw.tokens))))
    _, large = observation(80)
    model = APathActorCritic().eval()
    with torch.no_grad():
        d, value = model(batch_samples([sample]))
        d2, v2 = model(batch_samples([other]))
        batch = batch_samples([sample, encode(large)])
        for features in batch['features'].values():
            features[~batch['entity_valid']] = 1e30
        d3, v3 = model(batch)
    assert routed(sample, d) == pytest.approx(routed(other, d2), abs=1e-6)
    assert routed(sample, d) == pytest.approx(routed(sample, d3), abs=1e-6)
    torch.testing.assert_close(value, v2, atol=1e-6, rtol=1e-5)
    torch.testing.assert_close(value[0], v3[0], atol=1e-6, rtol=1e-5)
    original = sample.entities.tokens[0].features.copy()
    raw.tokens[0].features[:] = 0
    raw.routes[0]['snapshot'] = 'changed'
    np.testing.assert_array_equal(sample.entities.tokens[0].features, original)
    assert sample.entities.routes[0]['snapshot'] != 'changed'


@pytest.mark.parametrize('card,kind', [('Armaments','ARMAMENTS'), ('Dual Wield','DUAL_WIELD'),
                                      ('Burning Pact','EXHAUST_ONE'), ('Warcry','WARCRY')])
def test_real_selection_new_observation_no_target_and_mixed_batch(card, kind):
    env, obs = start([card, 'Sentinel', 'Strike_R', 'Rampage', 'Wound'])
    initial = encode(obs)
    selected = play(env, obs, card)
    sample = encode(selected)
    assert selected['decision']['phase'] == 'SELECT_CARD'
    assert sample.tasks and set(sample.tasks) == {TASKS.index(kind)}
    assert all(row == [-1] for row in sample.targets)
    assert any(c.target >= 0 for c in sample.entities.candidates)
    model = APathActorCritic()
    batch = batch_samples([initial, sample])
    with patch.object(model, 'encode_entities', wraps=model.encode_entities) as encoder:
        u, j, logp, _ = model.act(batch, torch.Generator().manual_seed(11))
        assert encoder.call_count == 1
    d, _ = model(batch)
    assert not d.target_logp[1].any()
    assert logp.shape == (2,)
    with patch.object(env, 'step', wraps=env.step) as step:
        after = env.step(sample.route(u[1].item(), j[1].item()))[0]
        assert step.call_count == 1 and after['decision']['phase'] == 'NORMAL'


def test_source_condition_and_all_parameter_groups_receive_gradients():
    torch.manual_seed(93)
    _, obs = observation()
    sample = encode(obs)
    model = APathActorCritic()
    batch = batch_samples([sample])
    d, value = model(batch)
    targets = [u for u, row in enumerate(sample.targets) if len(row) > 1]
    assert len(targets) >= 2
    assert not torch.allclose(d.target_probs[0, targets[0]], d.target_probs[0, targets[-1]])
    loss = -d.log_prob(torch.tensor([targets[0]]), torch.tensor([0])).mean() - .01*d.entropy().mean() + (value - 2).square().mean()
    loss.backward()
    for name in ('task_query.weight', 'source_key.weight', 'target_query.weight', 'target_key.weight',
                 'projections.CARD.weight', 'projections.ENEMY.weight', 'projections.PLAYER_GLOBAL.weight',
                 'blocks.0.qkv.weight', 'blocks.3.qkv.weight', 'pool_seed', 'pool.in_proj_weight',
                 'special.weight', 'value_head.2.weight'):
        grad = dict(model.named_parameters())[name].grad
        assert grad is not None and torch.isfinite(grad).all() and grad.abs().sum() > 0, name


def test_public_context_changes_source_representation_and_value_without_changing_card_features():
    _, obs = observation()
    a = encode(obs); b = copy.deepcopy(a)
    b.context[0] += 1
    model = APathActorCritic()
    x, g = model.encode_entities(batch_samples([a]))
    y, h = model.encode_entities(batch_samples([b]))
    index = next(i for i, token in enumerate(a.entities.tokens) if token.entity_type == 'CARD')
    assert not torch.allclose(x[:, index], y[:, index])
    assert not torch.allclose(g, h)
    np.testing.assert_array_equal(a.entities.tokens[index].features, b.entities.tokens[index].features)


def test_terminal_empty_candidate_value_and_finite_backward():
    _, obs = observation()
    raw = encode(obs).entities; raw.candidates = []; raw.routes = []
    sample = adapt(raw)
    batch = batch_samples([sample]); model = APathActorCritic()
    value = model.value_only(batch)
    assert torch.isfinite(value).all()
    d, _ = model(batch)
    assert not d.probs.any() and not d.entropy().any()
    with pytest.raises(ValueError, match='Value-only'):
        d.sample(torch.Generator())
    (value.sum() + d.entropy().sum()).backward()
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())


def test_extreme_logits_masks_and_invalid_routes_fail_explicitly():
    s = torch.tensor([[1e20, -1e20, 0.]], requires_grad=True)
    t = torch.tensor([[[1e20, -1e20], [-1e20, 1e20], [float('nan'), 0.]]], requires_grad=True)
    mask = torch.tensor([[[True, True], [True, False], [False, False]]])
    d = JointDistribution(s, t, mask.any(-1), mask)
    d.entropy().sum().backward()
    assert torch.isfinite(s.grad).all() and torch.isfinite(t.grad).all()
    with pytest.raises(ValueError, match='合法条件'):
        JointDistribution(s, t, torch.ones_like(s, dtype=torch.bool), mask)
    _, obs = observation()
    raw = encode(obs).entities
    raw.routes.pop()
    with pytest.raises(ValueError, match='等长'):
        adapt(raw)


def test_relation_validation_and_empty_entity_mask():
    _, obs = observation()
    batch = batch_samples([encode(obs)]); model = APathActorCritic()
    batch['held_card_index'][0, 0] = 0
    with pytest.raises(ValueError, match='关系'):
        model.value_only(batch)
    batch['held_card_index'].fill_(-1); batch['entity_valid'].fill_(False)
    with pytest.raises(ValueError, match='玩家实体'):
        model.value_only(batch)


@pytest.mark.parametrize('kind', ['EXHUME', 'HEADBUTT'])
def test_real_exhaust_and_discard_selection_routes(kind):
    if kind == 'EXHUME':
        env, obs = start(['Exhume', 'Intimidate', 'Seeing Red', 'Strike_R', 'Strike_R'])
        for name in ('Intimidate', 'Seeing Red', 'Exhume'):
            obs = play(env, obs, name)
        zone = 'exhaust_pile'
    else:
        env, obs = start(['Headbutt', 'Strike_R', 'Defend_R', 'Pommel Strike', 'Seeing Red'])
        for name in ('Seeing Red', 'Defend_R', 'Strike_R', 'Headbutt'):
            obs = play(env, obs, name)
        zone = 'discard_pile'
    assert obs['decision']['selection']['candidate_zone'] == zone
    agent = APathAgent(APathActorCritic(), 45)
    decision = agent.act([obs])
    assert set(decision.samples[0].tasks) == {TASKS.index(kind)}
    assert all(row == [-1] for row in decision.samples[0].targets)
    after, _, _, _, _ = env.step(decision.routes[0])
    assert after['decision']['phase'] == 'NORMAL'


def test_agent_rng_roundtrip_and_historical_reevaluation_after_environment_advance():
    env, obs = observation()
    agent = APathAgent(APathActorCritic(), 73)
    state = agent.rng_state()
    first = agent.act([obs])
    agent.restore_rng(state)
    second = agent.act([obs])
    assert first.routes == second.routes
    torch.testing.assert_close(first.logp, second.logp, rtol=0, atol=0)
    env.step(first.routes[0])
    logp, entropy, value = agent.evaluate_actions(first.samples, first.source, first.target)
    torch.testing.assert_close(logp, first.logp, rtol=0, atol=0)
    torch.testing.assert_close(value, first.value, rtol=0, atol=0)
    assert torch.isfinite(entropy).all()


def test_real_stasis_fusion_and_opaque_reference_renaming():
    from test_enemy_act2_final import held_state
    _, obs = held_state()
    sample = encode(obs); model = APathActorCritic()
    batch = batch_samples([sample])
    assert (batch['held_card_index'] >= 0).sum() == 2
    d, value = model(batch)
    no_relation = {**batch, 'held_card_index': torch.full_like(batch['held_card_index'], -1)}
    empty, empty_value = model(no_relation)
    torch.testing.assert_close(d.probs, empty.probs)
    torch.testing.assert_close(value, empty_value)
    torch.nn.init.normal_(model.holds_fusion.weight, std=.1)
    d, value = model(batch)
    renamed = copy.deepcopy(obs)
    mapping = {r: f'opaque-{i}' for i, r in enumerate(obs['routing']['enemy_refs'] + obs['routing']['stasis_refs']) if r is not None}
    for key in ('enemy_refs', 'stasis_refs'):
        renamed['routing'][key] = [mapping.get(r) for r in renamed['routing'][key]]
    for relation in renamed['relations']:
        relation['enemy_ref'] = mapping[relation['enemy_ref']]
        relation['card_ref'] = mapping[relation['card_ref']]
    renamed['routing']['snapshot'] = 'new-snapshot'
    changed, changed_value = model(batch_samples([encode(renamed)]))
    torch.testing.assert_close(d.probs, changed.probs, rtol=0, atol=0)
    torch.testing.assert_close(value, changed_value, rtol=0, atol=0)
    (d.entropy().mean() + value.square().mean()).backward()
    assert model.holds_fusion.weight.grad.abs().sum() > 0


@pytest.mark.parametrize('swap', ['hand', 'potions', 'enemies'])
def test_slot_permutation_changes_only_routing(swap):
    _, obs = observation()
    changed = copy.deepcopy(obs)
    changed[swap][0], changed[swap][1] = changed[swap][1], changed[swap][0]
    permutation = list(range(66))
    if swap in ('hand', 'potions'):
        base = 0 if swap == 'hand' else 51
        for i in range(5):
            permutation[base + i], permutation[base + 5 + i] = base + 5 + i, base + i
    else:
        changed['routing']['enemy_refs'][0], changed['routing']['enemy_refs'][1] = changed['routing']['enemy_refs'][1], changed['routing']['enemy_refs'][0]
        for zone in ('hand', 'draw_pile', 'discard_pile', 'exhaust_pile', 'resolving'):
            for card in changed[zone]:
                card['damage_by_target'][0], card['damage_by_target'][1] = card['damage_by_target'][1], card['damage_by_target'][0]
        bases = [5*i for i, c in enumerate(obs['hand']) if c['target_kind'] == 'ENEMY']
        bases += [51+5*i for i, p in enumerate(obs['potions']) if p['present'] and p['target_kind'] == 'ENEMY']
        for base in bases:
            permutation[base], permutation[base+1] = base+1, base
    changed['action_mask'] = obs['action_mask'][permutation].copy()
    a, b = encode(obs), encode(changed); model = APathActorCritic()
    da, va = model(batch_samples([a])); db, vb = model(batch_samples([b]))
    by_route = {r['action']: db.probs[0,u,j].item() for u,rs in enumerate(b.routes) for j,r in enumerate(rs)}
    for u, rs in enumerate(a.routes):
        for j, r in enumerate(rs):
            assert da.probs[0,u,j].item() == pytest.approx(by_route[permutation[r['action']]], abs=1e-6)
    torch.testing.assert_close(va, vb, atol=1e-6, rtol=1e-5)
