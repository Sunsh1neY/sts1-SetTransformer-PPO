"""Fixed evaluation aggregation, admission and TensorBoard event checks."""
import copy
from pathlib import Path
import pytest
import torch
from torch.utils.tensorboard import SummaryWriter
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
from sts.env.acorpus import ACorpus, ACorpusSmokeEnv
from sts.train.corpus_evaluation import summarize,paired_comparison


def row(component,state,reward,seed=0):
    return dict(component=component,state_hash=state,reward=reward,environment_seed=seed,
                terminated=True,truncated=False,win=int(reward>0),exit_hp_ratio=.5,potion_uses=0,
                kind='natural',act=1,hp_band='gt75',encounter='CULTIST',family='natural')


def test_component_macro_is_not_flat_episode_average():
    rows=[row('a','x',0),row('a','x',2,1),row('a','y',3),row('b','z',10)]
    assert summarize(rows)['reward']==6
    changed=copy.deepcopy(rows);changed[0]['truncated']=True;changed[0]['terminated']=False
    assert 'reward' not in summarize(changed)
    comparison=paired_comparison(rows,[dict(r,reward=r['reward']+1) for r in rows])
    assert comparison['paired_reward_difference']==1
    assert comparison['reward_difference_ci95']==[1,1]


def test_formal_env_admits_only_correct_split_and_seed():
    directory=Path(__file__).resolve().parents[1]/'projects/battle-initial-states/corpora/a-v2'
    corpus=ACorpus(directory)
    env=ACorpusSmokeEnv(corpus,scope='experiment-protocol-v1')
    dev=corpus.scene(next(k for k,r in corpus.rows.items() if r['provenance']['partition']=='audit-dev'))
    obs=env.reset(dev,0,purpose='evaluation')
    assert obs and env._context['training_admitted'] is False
    with pytest.raises(ValueError):env.reset(dev,100001,purpose='train')
    train=corpus.scene(next(k for k,r in corpus.rows.items() if r['provenance']['partition']=='audit-train'))
    with pytest.raises(ValueError):env.reset(train,0,purpose='evaluation')
    with pytest.raises(ValueError):env.reset(dev,100001,purpose='evaluation')


def test_single_writer_contains_train_and_dev_namespaces(tmp_path):
    with SummaryWriter(str(tmp_path/'one-run')) as writer:
        writer.add_scalar('train/ppo/policy_loss',.1,1024)
        writer.add_scalar('dev/overall/reward',.2,0)
    events=EventAccumulator(str(tmp_path/'one-run')).Reload()
    assert set(events.Tags()['scalars'])=={'train/ppo/policy_loss','dev/overall/reward'}
