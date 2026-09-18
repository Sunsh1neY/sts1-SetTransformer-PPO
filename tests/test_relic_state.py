"""Real backend transitions, public state, one-hot encoding and A-path checks."""
import json

import numpy as np
import pytest
import torch

from sts.env.relics import RelicEnv
from sts.env.relic_state import BY_NAME, DIMENSION, normalize_relics, relic_features
from sts.models.apath import APathActorCritic, adapt, batch_samples, encode
from sts.train.ppo import ppo_loss
from sts.train.apath import sample_digest, bind_route, plain_route

torch.set_num_threads(1)


def scene(relics=(), deck=None, encounter='JAW_WORM'):
    return dict(entry_timing='pre_combat_initialization',
        initialization_phase='before_destination_room_entry', act=1, floor=1,
        character='IRONCLAD', ascension=20, player=dict(hp=70, max_hp=80, gold=99),
        deck=deck or ['Strike_R'] * 10, relics=list(relics), potions=[None, None],
        encounter=encounter, burning_elite=False)


def start(relics=(), **kwargs):
    env = RelicEnv()
    return env, env.reset(scene(relics, **kwargs), 100123, diagnostic=True)


def counter(obs, name):
    return next(r for r in obs['relics'] if r['name'] == name)['state']['counter']['value']


def play(env, obs, name='Strike_R'):
    i = next(i for i, c in enumerate(obs['hand']) if c['name'] == name)
    return env.step(i * 5)


@pytest.mark.parametrize('name', list(BY_NAME)[:8])
def test_existing_eight_real_effects_and_one_hot(name):
    deck = ['Defend_R'] * 10 if name == 'Oddly Smooth Stone' else ['Strike_R'] * 10
    base, b = start(deck=deck)
    env, o = start([name], deck=deck)
    token = next(t for t in encode(o).entities.tokens if t.entity_type == 'RELIC')
    assert token.features.shape == (DIMENSION,)
    assert token.features[:-3].sum() == 1
    assert token.features[BY_NAME[name]['id'] - 1] == 1
    assert not token.features[-3:].any()
    if name == 'Lantern':
        assert o['player']['energy'] == b['player']['energy'] + 1
        assert env.step(50)[0]['player']['energy'] == base.step(50)[0]['player']['energy']
    elif name == 'Anchor':
        assert o['player']['block'] == b['player']['block'] + 10
        assert env.step(50)[0]['player']['block'] == 0
    elif name == 'Bag of Preparation':
        assert len(o['hand']) == len(b['hand']) + 2
        assert len(env.step(50)[0]['hand']) == 5
    elif name == 'Blood Vial':
        assert o['player']['hp'] == b['player']['hp'] + 2
    elif name == 'Vajra':
        assert play(env, o)[0]['enemies'][0]['hp'] == play(base, b)[0]['enemies'][0]['hp'] - 1
    elif name == 'Oddly Smooth Stone':
        assert play(env, o, 'Defend_R')[0]['player']['block'] == play(base, b, 'Defend_R')[0]['player']['block'] + 1
    elif name == 'Bronze Scales':
        assert o['enemies'][0]['intent_damage'] > 0
        assert env.step(50)[0]['enemies'][0]['hp'] == base.step(50)[0]['enemies'][0]['hp'] - 3
    else:
        env, o = start([name], deck=['Bludgeon'] * 10)
        base, b = start(deck=['Bludgeon'] * 10)
        for _ in range(10):
            a, z = play(env, o, 'Bludgeon'), play(base, b, 'Bludgeon')
            if a[2]:
                assert z[2] and a[4]['battle_won']
                assert a[0]['player']['hp'] == min(80, z[0]['player']['hp'] + 6)
                assert a[4]['reward_accounting']['hp_end'] == a[0]['player']['hp']
                break
            o, b = env.step(50)[0], base.step(50)[0]
        else:
            pytest.fail('Expected a real victory')


def test_pen_nib_boundary_nonattack_and_single_consumption():
    env, o = start([dict(name='Pen Nib', counter=8)])
    before = o['enemies'][0]['hp']
    o = play(env, o)[0]
    assert counter(o, 'Pen Nib') == 9
    assert before - o['enemies'][0]['hp'] == 6
    o = env.step(50)[0]
    assert counter(o, 'Pen Nib') == 9
    before = o['enemies'][0]['hp']
    o = play(env, o)[0]
    assert counter(o, 'Pen Nib') == 0
    assert before - o['enemies'][0]['hp'] == 12
    before = o['enemies'][0]['hp']
    o = play(env, o)[0]
    assert counter(o, 'Pen Nib') == 1 and before - o['enemies'][0]['hp'] == 6
    env, o = start([dict(name='Pen Nib', counter=9)], deck=['Defend_R'] * 10)
    assert counter(play(env, o, 'Defend_R')[0], 'Pen Nib') == 9


@pytest.mark.parametrize('name', ['Nunchaku', 'Ink Bottle'])
def test_play_counter_boundary_and_no_repeat(name):
    env, o = start([dict(name=name, counter=9)])
    o = play(env, o)[0]
    assert counter(o, name) == 0
    assert o['player']['energy'] == (3 if name == 'Nunchaku' else 2)
    assert len(o['hand']) == (5 if name == 'Ink Bottle' else 4)
    o = play(env, o)[0]
    assert counter(o, name) == 1
    assert o['player']['energy'] == (2 if name == 'Nunchaku' else 1)
    env, o = start([dict(name=name, counter=9)], deck=['Defend_R'] * 10)
    assert counter(play(env, o, 'Defend_R')[0], name) == (9 if name == 'Nunchaku' else 0)


@pytest.mark.parametrize('name,period', [('Happy Flower', 3), ('Incense Burner', 6)])
def test_turn_counters_entry_and_later_trigger(name, period):
    env, o = start([dict(name=name, counter=period - 1)])
    assert counter(o, name) == 0
    if name == 'Happy Flower':
        assert o['player']['energy'] == 4
    else:
        assert o['player']['statuses']['Intangible'] == 1
        hp = o['player']['hp']
    o = env.step(50)[0]
    assert counter(o, name) == 1
    assert o['player']['energy'] == 3
    if name == 'Incense Burner':
        assert hp - o['player']['hp'] == 1
        assert not o['player']['statuses'].get('Intangible', 0)
    env, o = start([dict(name=name, counter=period - 2)])
    assert counter(o, name) == period - 1
    assert o['player']['energy'] == 3
    assert not o['player']['statuses'].get('Intangible', 0)
    o = env.step(50)[0]
    assert counter(o, name) == 0
    assert (o['player']['energy'] == 4 if name == 'Happy Flower' else o['player']['statuses']['Intangible'] == 1)


def test_sundial_real_shuffle_and_nonshuffle():
    env, o = start([dict(name='Sundial', counter=2)])
    o = env.step(50)[0]
    assert counter(o, 'Sundial') == 2 and o['player']['energy'] == 3
    o = env.step(50)[0]
    assert counter(o, 'Sundial') == 0 and o['player']['energy'] == 5
    o = env.step(50)[0]
    assert counter(o, 'Sundial') == 0 and o['player']['energy'] == 3


@pytest.mark.parametrize('bad', [None, -1, 10, True, 1.5])
def test_invalid_counter_is_rejected_before_backend(bad):
    with pytest.raises((ValueError, TypeError)):
        start([dict(name='Pen Nib', counter=bad)])


def test_missing_duplicate_special_and_unknown_fields_rejected():
    for relics in [['Pen Nib'], ['Anchor', 'Anchor'], ['Potion Belt'],
                   [dict(name='Pen Nib', counter=0, hidden=1)]]:
        with pytest.raises((TypeError, ValueError)):
            start(relics)
    row = normalize_relics([dict(name='Pen Nib', counter=0)])[0]
    assert relic_features(row)[-3:] == [1, 1, 0]
    row['state']['counter']['known'] = False
    with pytest.raises(ValueError):
        relic_features(row)


def test_legacy_backend_rejects_new_relics_and_external_truncation_keeps_state():
    from sts.env.ironclad import IroncladEnv
    with pytest.raises((ValueError, TypeError, RuntimeError)):
        IroncladEnv().reset(scene(['Pen Nib']), 100123, diagnostic=True)
    env = RelicEnv(max_actions=1)
    env.reset(scene([dict(name='Pen Nib', counter=8)]), 100123, diagnostic=True)
    o, reward, term, trunc, info = env.step(0)
    assert not term and trunc and reward == 0
    assert counter(o, 'Pen Nib') == 9
    assert 'battle_exit' not in info
    assert not info['training_admitted']
    assert info['relic_state_before'][0]['state']['counter']['value'] == 8
    assert info['relic_state_after'][0]['state']['counter']['value'] == 9
    with pytest.raises(RuntimeError):
        env.step(50)


def test_multi_relic_interaction_and_no_relic_padding():
    env, o = start(['Vajra', dict(name='Pen Nib', counter=9), dict(name='Nunchaku', counter=9), dict(name='Ink Bottle', counter=9)])
    before = o['enemies'][0]['hp']
    o = play(env, o)[0]
    assert before - o['enemies'][0]['hp'] == 14
    assert o['player']['energy'] == 3 and len(o['hand']) == 5
    assert all(counter(o, n) == 0 for n in ('Pen Nib', 'Nunchaku', 'Ink Bottle'))
    _, empty = start()
    sample, other = encode(o), encode(empty)
    batch = batch_samples([sample, other])
    assert not any(t.entity_type == 'RELIC' for t in other.entities.tokens)
    assert batch['features']['RELIC'].shape[-1] == DIMENSION
    assert not batch['features']['RELIC'][1].any()


def test_actor_critic_gradients_permutation_and_real_ppo_step():
    _, o = start([dict(name='Pen Nib', counter=8), dict(name='Nunchaku', counter=9)])
    sample = encode(o)
    model = APathActorCritic().eval()
    batch = batch_samples([sample])
    batch['features']['RELIC'].requires_grad_()
    dist, value = model(batch)
    actor_grad = torch.autograd.grad(dist.log_prob(torch.tensor([0]), torch.tensor([0])).sum(), batch['features']['RELIC'], retain_graph=True)[0]
    critic_grad = torch.autograd.grad(value.sum(), batch['features']['RELIC'])[0]
    assert actor_grad[..., -1].abs().sum() > 0
    assert critic_grad[..., -1].abs().sum() > 0
    permuted = adapt(sample.entities.permuted(np.random.default_rng(18).permutation(len(sample.entities.tokens))))
    with torch.no_grad():
        a, v = model(batch_samples([sample]))
        b, w = model(batch_samples([permuted]))
    torch.testing.assert_close(a.probs, b.probs)
    torch.testing.assert_close(v, w)
    old = a.log_prob(torch.tensor([0]), torch.tensor([0]))
    logp, entropy, values = model.evaluate_actions(batch_samples([sample]), torch.tensor([0]), torch.tensor([0]))
    torch.testing.assert_close(logp, old)
    before = model.projections['RELIC'].weight.detach().clone()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    # A controlled PPO ratio with a nonzero advantage and a value target.
    loss, _ = ppo_loss(logp, old, torch.ones_like(logp), values, v, torch.ones_like(values), entropy, norm_adv=False)
    optimizer.zero_grad(); loss.backward(); optimizer.step()
    assert not torch.equal(before, model.projections['RELIC'].weight)


@pytest.mark.parametrize('name', [n for n, r in BY_NAME.items() if r['counter'] is not None])
def test_serialized_action_replay_and_exit_counter_carry(name):
    definition = BY_NAME[name]['counter']
    initial = scene([dict(name=name, counter=definition['max'])], deck=['Bludgeon'] * 10)
    env = RelicEnv(); o = env.reset(initial, 100123, diagnostic=True)
    actions = []
    for _ in range(8):
        sample = encode(o)
        route = next(r for rs in sample.routes for r in rs if r.get('action', 50) < 50) if o['player']['energy'] >= 3 else next(r for rs in sample.routes for r in rs if r.get('action') == 50)
        actions.append(plain_route(route))
        o, reward, term, trunc, info = env.step(route)
        saved = json.loads(json.dumps(dict(scene=initial, seed=100123, actions=actions)))
        restored = RelicEnv(); replay = restored.reset(saved['scene'], saved['seed'], diagnostic=True)
        for action in saved['actions']:
            replay, rr, rt, rx, ri = restored.step(bind_route(action, replay))
        assert sample_digest(encode(o)) == sample_digest(encode(replay))
        assert (reward, term, trunc) == (rr, rt, rx)
        assert info['reward_accounting'] == ri['reward_accounting']
        if term:
            assert info['battle_won'] and not trunc
            exported = info['battle_exit']['relics']
            assert exported[0]['counter'] == counter(o, name)
            next_scene = scene(exported)
            next_obs = restored.reset(next_scene, 100124, diagnostic=True)
            expected = (exported[0]['counter'] + 1) % (definition['max'] + 1) if name in ('Happy Flower', 'Incense Burner') else exported[0]['counter']
            assert counter(next_obs, name) == expected
            break
    else:
        pytest.fail('Expected victory and an actual backend exit export')
