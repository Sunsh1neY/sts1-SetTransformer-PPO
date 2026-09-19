"""Admission, exact sampler weights and terminal observation smoke prerequisites."""
import copy
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest

from sts.env.acorpus import ACorpus, ACorpusSmokeEnv, digest_bytes
from sts.env.full_card_public import PublicBattleEnv
from sts.models.apath import encode

CORPUS = Path(__file__).resolve().parents[1]/'projects/battle-initial-states/corpora/a-v2'


def test_exact_three_stage_sampling_and_distinct_component_counts():
    corpus = ACorpus(CORPUS)
    class Choices:
        def __init__(self, values): self.values=iter(values)
        def integers(self,n):
            value=next(self.values)
            assert 0 <= value < n
            return value
    for k,kind in enumerate(('natural','augmentation')):
        groups=corpus.groups[kind]
        assert len(groups)==(84 if k==0 else 56)
        total=0
        for i,component in enumerate(sorted(groups)):
            for j,key in enumerate(groups[component]):
                actual=corpus.sample(Choices([k,i,j]))
                assert actual['content_id']==key and actual['split']=='audit-train'
                assert actual['content_group']==kind
                total += .5/len(groups)/len(groups[component])
        assert total==pytest.approx(.5)


def test_strict_train_admission_no_diagnostic_bypass():
    corpus=ACorpus(CORPUS)
    env=ACorpusSmokeEnv(corpus)
    scene=corpus.sample(np.random.default_rng(123))
    with patch.object(PublicBattleEnv,'reset',autospec=True,side_effect=PublicBattleEnv.reset) as reset:
        env.reset(scene,100001)
        assert reset.call_args.kwargs['diagnostic'] is False
        assert reset.call_args.kwargs['purpose']=='train'
    assert env._context['admission_scope']=='smoke-only'
    changed=copy.deepcopy(scene)
    changed['candidate']['player']['hp']=1
    changed['candidate_sha256']=digest_bytes(changed['candidate'])
    with pytest.raises(ValueError): env.reset(changed,100001)
    with pytest.raises(ValueError): env.reset(scene,0)
    for split in ('audit-dev','audit-holdout'):
        key=next(k for k,r in corpus.rows.items() if r['provenance']['partition']==split)
        with pytest.raises(ValueError): env.reset(corpus.scene(key),100001)


def test_external_truncation_retains_final_observation_and_unsettled_reward():
    corpus=ACorpus(CORPUS)
    env=ACorpusSmokeEnv(corpus,max_actions=1)
    obs=env.reset(corpus.sample(np.random.default_rng(8)),100001)
    sample=encode(obs)
    route=next(r for routes in sample.routes for r in routes if r.get('action')==50)
    final,reward,term,trunc,info=env.step(route)
    assert trunc and not term and reward==0
    assert not info['reward_accounting']['complete']
    assert encode(final).entities.tokens
