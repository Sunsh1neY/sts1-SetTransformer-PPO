"""Reward semantics and real A-path potion/termination/replay regression tests."""
import random

import pytest
import torch

from sts.battle_reward_v2 import BattleRewardV2, contract, terminal_components
from sts.env.apath import APathEnv, load_pool, scene
from sts.models.apath import encode
from sts.train.apath import APathTrainer, plain_route


def total(win, start, end, uses=0, maximum=75):
    return sum(terminal_components(victory=win, hp_start=start, max_hp_start=maximum,
                                  hp_end=end, potion_uses=uses).values())


def test_objective_tradeoffs_and_hp_growth():
    assert total(True, 45, 30) == pytest.approx(total(True, 75, 60))
    assert total(True, 45, 40, 1) > total(True, 45, 30)
    assert total(False, 45, 0, 1) == pytest.approx(-.65)
    assert total(True, 45, 55) > 2
    assert total(True, 75, 79) == pytest.approx(2 + 4/75)
    assert total(False, 45, 50) > 0  # Reward sign does not encode outcome.


def observation(hp=40):
    return dict(player=dict(hp=hp,max_hp=75),potions=[])


def test_partial_episode_no_payment_and_terminal_paid_once():
    tracker=BattleRewardV2(dict(hp=45,max_hp=75),[])
    reward,info=tracker.transition(observation=observation(),terminated=False,truncated=False,
        outcome=0,potion_event=dict(name='Block Potion',slot=0,action=51))
    assert reward == 0 and info['reward_accounting']['potion_uses'] == 1
    reward,info=tracker.transition(observation=observation(),terminated=True,truncated=False,outcome=1)
    assert reward == pytest.approx(total(True,45,40,1))
    with pytest.raises(RuntimeError):
        tracker.transition(observation=observation(),terminated=True,truncated=False,outcome=1)
    partial=BattleRewardV2(dict(hp=45,max_hp=75),[])
    reward,info=partial.transition(observation=observation(),terminated=False,truncated=True,outcome=0)
    assert reward == 0 and not info['reward_accounting']['complete']
    assert info['reward_accounting']['reward_components'] is None


def registered():
    row=next(r for r in load_pool()['contents'] if r['split']=='train_candidate')
    return scene(row['content_id'],'wounded-equipped','JAW_WORM')


def route(obs, action):
    return dict(kind='NORMAL',snapshot=obs['routing']['snapshot'],action=action)


def test_real_potion_truncation_and_reset():
    env=APathEnv(max_actions=1)
    obs=env.reset(registered(),100123)
    obs,reward,term,trunc,info=env.step(route(obs,51))
    assert trunc and not term and reward == 0
    assert info['reward_version']=='battle_reward_v2'
    assert info['reward_accounting']['potion_uses']==1
    assert info['reward_accounting']['potion_events'][0]['name']=='Block Potion'
    assert not obs['potions'][0]['present']
    env.reset(registered(),100123)
    assert env._reward_v2.events == []


def test_invalid_potion_not_charged():
    env=APathEnv()
    obs=env.reset(registered(),100123)
    obs,*_=env.step(route(obs,51))
    with pytest.raises(ValueError):
        env.step(route(obs,51))
    assert len(env._reward_v2.events)==1


def test_real_complete_episodes_recompute_and_both_outcomes():
    outcomes=set()
    for seed in range(100101,100121):
        env=APathEnv(); obs=env.reset(registered(),seed)
        rng=random.Random(seed)
        rewards=[]
        while True:
            sample=encode(obs)
            actions=[r for choices in sample.routes for r in choices]
            obs,reward,term,trunc,info=env.step(rng.choice(actions))
            rewards.append(reward)
            if term or trunc:
                break
        if not term:
            continue
        accounting=info['reward_accounting']
        expected=total(info['battle_won'],accounting['hp_start'],accounting['hp_end'],accounting['potion_uses'])
        assert sum(rewards)==pytest.approx(expected)
        assert all(r==0 for r in rewards[:-1])
        assert info['task_outcome']==('victory' if info['battle_won'] else 'defeat')
        assert info['reward_contract']==contract()
        outcomes.add(info['task_outcome'])
    assert outcomes=={'victory','defeat'}


def test_checkpoint_replays_potion_and_rejects_reward_drift(tmp_path):
    trainer=APathTrainer(num_envs=1,num_steps=2,total_transitions=4)
    active=trainer.active[0]
    active.update(scene=registered(),seed=100123,actions=[],return_observed=0.,potion_uses=0,steps=0)
    obs=trainer.envs[0].reset(active['scene'],active['seed'])
    action=route(obs,51)
    obs,reward,_,_,info=trainer.envs[0].step(action)
    active.update(actions=[plain_route(action)],return_observed=reward,potion_uses=1,steps=1)
    trainer.observations=[encode(obs)]
    path=tmp_path/'state.pt';trainer.save(path)
    restored=APathTrainer.load(path)
    assert restored.envs[0]._reward_v2.events==trainer.envs[0]._reward_v2.events
    left=trainer.envs[0].step(route(obs,50))
    right=restored.envs[0].step(route(restored.envs[0].observation(),50))
    assert left[1:4]==right[1:4]
    assert left[4]['reward_accounting']==right[4]['reward_accounting']
    data=torch.load(path,weights_only=False)
    data['reward_contract']['potion_use_cost']=.1
    torch.save(data,path)
    with pytest.raises(ValueError,match='reward contract'):
        APathTrainer.load(path)


def test_evaluation_records_v2_accounting():
    import importlib.util
    from pathlib import Path
    import time
    spec=importlib.util.spec_from_file_location('apath_runner',Path(__file__).parents[1]/'scripts/run-a-path-ppo.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    row=next(r for r in load_pool()['contents'] if r['split']=='development')
    selected=scene(row['content_id'],'wounded-equipped','JAW_WORM')
    records=runner.evaluate(None,'random',[dict(scene=selected,seed=100123,case_id='v2-test')],
                            'cpu',time.monotonic()+30)
    record=records[0]
    assert record['reward_contract']==contract()
    assert record['potion_uses']==record['reward_accounting']['potion_uses']
    if record['status']=='terminated':
        assert record['reward_complete']==pytest.approx(sum(record['reward_accounting']['reward_components'].values()))
    summary=runner.summarize(records)[row['group']]
    assert 'net_hp_natural' in summary
