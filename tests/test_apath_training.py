"""正式来源准入、真实PPO更新及活动环境的CPU/CUDA恢复预检。"""
import copy
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import pickle

import numpy as np
import pytest
import torch

from sts.env.apath import APathEnv,load_pool,scene,sample_scene,canonical
from sts.models.apath import batch_samples,encode
from sts.train.apath import APathTrainer,sample_digest

torch.set_num_threads(1)


def test_strict_formal_scene_no_diagnostic_bypass_and_split_guard():
    selected=sample_scene(np.random.default_rng(11))
    env=APathEnv()
    obs=env.reset(selected,100001)
    assert env._context['training_admitted'] is True
    assert env._context['scene_kind']=='registered-real-deck-configured'
    assert env._context['observation_schema']==obs['schema']
    assert obs['decision']['phase']=='NORMAL'
    changed=copy.deepcopy(selected);changed['candidate']['deck'].append('Strike_R')
    import hashlib
    changed['candidate_sha256']=hashlib.sha256(canonical(changed['candidate'])).hexdigest()
    with pytest.raises(ValueError,match='未注册'):
        env.reset(changed,100001)
    dev=next(r for r in load_pool()['contents'] if r['split']=='development')
    registered=scene(dev['content_id'],'full-basic','JAW_WORM')
    with pytest.raises(ValueError,match='开发来源'):
        env.reset(registered,100001,purpose='train')
    with pytest.raises(ValueError,match='seed'):
        env.reset(selected,5)


def test_external_truncation_retains_full_final_observation_and_value():
    selected=sample_scene(np.random.default_rng(2))
    env=APathEnv(max_actions=1);obs=env.reset(selected,777001)
    sample=encode(obs)
    route=next(r for rs in sample.routes for r in rs if r.get('action')==50)
    final,reward,term,trunc,info=env.step(route)
    assert trunc and not term and reward==0
    assert len(encode(final).entities.tokens)>0
    assert 'battle_exit' not in info


@pytest.mark.parametrize('device',['cpu','cuda'])
def test_real_update_rng_replay_next_update_and_immutable_targets(tmp_path,device):
    if device=='cuda' and not torch.cuda.is_available():pytest.skip('CPU解释器无CUDA')
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    trainer=APathTrainer(num_envs=2,num_steps=4,total_transitions=64,device=device)
    initial={k:v.detach().cpu().clone() for k,v in trainer.model.state_dict().items()}
    result,_=trainer.iteration_step()
    assert result['env_steps']==8
    assert any(not torch.equal(initial[k],v.cpu()) for k,v in trainer.model.state_dict().items())
    old=pickle.loads(trainer.last_rollout)
    with torch.no_grad():
        logp,entropy,values=trainer.model.evaluate_actions(batch_samples(old['samples'],device),old['source'].to(device),old['target'].to(device))
    assert torch.isfinite(logp).all() and torch.isfinite(entropy).all()
    checkpoint=tmp_path/'state.pt';trainer.save(checkpoint)
    restored=APathTrainer.load(checkpoint)
    assert [sample_digest(s) for s in restored.observations]==[sample_digest(s) for s in trainer.observations]
    assert restored.last_rollout==trainer.last_rollout
    for s in restored.observations:
        assert s.routes
    first,_=trainer.iteration_step();second,_=restored.iteration_step()
    assert first['env_steps']==second['env_steps']==16
    for name,value in trainer.model.state_dict().items():
        torch.testing.assert_close(value,restored.model.state_dict()[name],rtol=0,atol=0)
    a,b=pickle.loads(trainer.last_rollout),pickle.loads(restored.last_rollout)
    for key in ('source','target','old_logp','old_value','rewards','returns','advantage'):
        torch.testing.assert_close(a[key],b[key],rtol=0,atol=0)
    saved=torch.load(checkpoint,weights_only=False)
    saved['schema']='old-checkpoint';torch.save(saved,checkpoint)
    with pytest.raises(ValueError,match='版本'):
        APathTrainer.load(checkpoint)


def test_selection_phase_checkpoint_rebinds_live_credentials(tmp_path):
    trainer=APathTrainer(num_envs=2,num_steps=4,total_transitions=64)
    content=next(r for r in load_pool()['contents'] if r['split']=='train_candidate' and
                 any(c.split('+')[0]=='Burning Pact' for c in r['cards']))
    registered=scene(content['content_id'],'full-basic','LAGAVULIN')
    for seed in range(884000,884100):
        obs=trainer.envs[0].reset(registered,seed)
        slot=next((i for i,c in enumerate(obs['hand']) if c['name']=='Burning Pact'),None)
        if slot is not None and obs['action_mask'][slot*5]:break
    else:pytest.fail('没有找到真实Burning Pact初手')
    sample=encode(obs)
    route=next(r for rs in sample.routes for r in rs if r.get('action')==slot*5)
    obs,reward,term,trunc,_=trainer.envs[0].step(route)
    assert not term and not trunc and obs['decision']['phase']=='SELECT_CARD'
    trainer.observations[0]=encode(obs)
    from sts.train.apath import plain_route
    trainer.active[0]=dict(scene=registered,seed=seed,actions=[plain_route(route)],
                           return_observed=reward,potion_uses=0,steps=1)
    path=tmp_path/'selection.pt';trainer.save(path);restored=APathTrainer.load(path)
    assert sample_digest(restored.observations[0])==sample_digest(trainer.observations[0])
    assert restored.observations[0].routes != trainer.observations[0].routes
    restored.envs[0].step(restored.observations[0].routes[0][0])
