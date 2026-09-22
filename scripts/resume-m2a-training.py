"""Explicit update-boundary migration of the frozen M2a checkpoint; no legacy edits."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import sys, json, time, copy, random, hashlib, shutil
from pathlib import Path
from collections import Counter
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'third_party/sts_lightspeed/build'))
from sts.train.m2a import APathTrainer, fingerprint
from sts.train.apath import sample_digest, bind_route
from sts.models.apath import encode
from sts.models.architectures.m2a_source_context.model import M2aActorCritic
from sts.battle_reward_v2 import contract as reward_contract
from sts.train.corpus_evaluation import evaluate,summarize,strata
from torch.utils.tensorboard import SummaryWriter

class ResumedTrainer(APathTrainer):
    @classmethod
    def load(cls,path):
        state=torch.load(path,map_location='cpu',weights_only=False)
        if state.get('schema')!='m2a-ppo-checkpoint-v1' or state['fingerprint']!=fingerprint(state.get('config',{}).get('corpus_dir')):
            raise ValueError('Checkpoint schema or frozen fingerprint mismatch')
        if state.get('reward_contract') != reward_contract():
            raise ValueError('Checkpoint reward contract is incompatible')
        if state.get('phase') != 'idle' or state.get('pending_rollout') is not None or state.get('model_version') != M2aActorCritic.model_version:
            raise ValueError('Checkpoint is not a verified idle M2a boundary')
        if state['last_rollout'] and hashlib.sha256(state['last_rollout']).hexdigest()!=state['last_rollout_sha256']:
            raise ValueError('Saved rollout checksum mismatch')
        trainer=cls(**state['config']);trainer.model.load_state_dict(state['model']);trainer.optimizer.load_state_dict(state['optimizer'])
        trainer.iteration,trainer.env_steps=state['iteration'],state['env_steps']
        trainer.active=state['active'];trainer.used_seeds=state['used_seeds'];trainer.last_rollout=state['last_rollout']
        trainer.reset_counts=Counter(state.get('reset_counts',{}))
        trainer.observations=[]
        for env,active,expected in zip(trainer.envs,trainer.active,state['observations']):
            obs=env.reset(active['scene'],active['seed'],purpose='train')
            replay_return = 0.0
            replay_uses = 0
            for action in active['actions']:
                obs,reward,term,trunc,info=env.step(bind_route(action,obs))
                replay_return += reward
                replay_uses = info['reward_accounting']['potion_uses']
                if term or trunc:
                    raise ValueError('Active environment replay ended prematurely')
            if replay_return != active['return_observed'] or replay_uses != active['potion_uses']:
                raise ValueError('Replayed reward accounting disagrees with checkpoint')
            sample=encode(obs)
            if sample_digest(sample)!=expected:
                raise ValueError('Replayed observation or action candidates differ')
            trainer.observations.append(sample)
        for name in ('scene_rng','environment_rng','shuffle_rng'):
            getattr(trainer,name).bit_generator.state=state[name]
        trainer.action_rng.set_state(state['action_rng']);torch.set_rng_state(state['torch_rng'])
        if state['cuda_rng']:
            torch.cuda.set_rng_state_all(state['cuda_rng'])
        random.setstate(state['python_rng']);np.random.set_state(state['numpy_rng'])
        return trainer

def write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf8')

def main():
    parent=ROOT/'runs/m2a-source-context-v1'
    out=ROOT/'runs/m2a-source-context-continuation-v2'
    out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,out/'continuation-source.py')
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)
    started=time.monotonic()
    deadline=started+3600
    parent_hash=hashlib.sha256((parent/'final.pt').read_bytes()).hexdigest()
    fp=json.loads((parent/'fingerprint.json').read_bytes())
    if fingerprint(ROOT/'projects/battle-initial-states/corpora/a-v2') != fp:
        raise ValueError('Frozen launch fingerprint mismatch')
    write(out/'provenance.json',dict(parent_checkpoint_sha256=parent_hash,
        continuation_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        parent_run=parent.name,from_update=229,target_update=256,seconds_cap=3600,
        migration='Explicit idle-boundary restore despite legacy unsupported-resume flag; replay and fingerprints required',
        evaluation='Fixed dev at 256; holdout deferred to avoid automatic repeated test use'))
    writer=SummaryWriter(str(out/'tensorboard/m2a-continuation'),flush_secs=5)
    def status(phase,trainer=None,**kw):
        write(out/'status.json',dict(phase=phase,elapsed=time.monotonic()-started,
             iteration=trainer.iteration if trainer else 229,
             env_steps=trainer.env_steps if trainer else 234496,**kw))
    trainer=None
    try:
        status('restoring')
        trainer=ResumedTrainer.load(parent/'final.pt')
        if trainer.iteration!=229 or trainer.env_steps!=234496:raise ValueError('Unexpected continuation boundary')
        writer.add_text('configuration/continuation',(out/'provenance.json').read_text(),trainer.env_steps)
        status('training',trainer,active_environments_replayed=True)
        while trainer.iteration<256:
            metrics,episodes=trainer.iteration_step(deadline-900)
            with (out/'metrics.jsonl').open('a') as f:f.write(json.dumps(metrics)+'\n')
            with (out/'train-episodes.jsonl').open('a') as f:
                for row in episodes:f.write(json.dumps(row)+'\n')
            for key in ('policy_loss','value_loss','entropy','approx_kl','clip_fraction','learning_rate','grad_norm'):
                writer.add_scalar('train/ppo/'+key,metrics[key],trainer.env_steps)
            for kind,values in metrics['groups'].items():
                for key,value in values.items():
                    if value is not None:writer.add_scalar('train/groups/'+kind+'/'+key,value,trainer.env_steps)
            if trainer.iteration%8==0:trainer.save(out/'latest.pt')
            status('training',trainer)
            writer.flush()
            print(json.dumps(dict(update=trainer.iteration,steps=trainer.env_steps)),flush=True)
        trainer.save(out/'final.pt')
        status('dev',trainer)
        cases=json.loads((parent/'evaluation-cases.json').read_bytes())['audit-dev']
        def on_case(row,done,total):
            with (out/'dev-0256-episodes.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            if done%16==0:status('dev',trainer,evaluation_done=done,evaluation_total=total)
        results=evaluate(trainer.model,trainer.corpus,cases,deadline,on_case)
        summary=summarize(results)
        write(out/'dev-0256-summary.json',dict(overall=summary,strata=strata(results)))
        for key,value in summary.items():writer.add_scalar('dev/overall/'+key,value,trainer.env_steps)
        previous=json.loads((parent/'status.json').read_bytes())['best_dev']
        selected_update=256 if summary['reward']>previous['score'] else previous['update']
        shutil.copy2(out/'final.pt' if selected_update==256 else parent/'selected.pt',out/'selected.pt')
        if fingerprint(trainer.config['corpus_dir'])!=fp or hashlib.sha256((parent/'final.pt').read_bytes()).hexdigest()!=parent_hash:
            raise ValueError('Frozen parent changed')
        status('completed',trainer,selected_update=selected_update,dev=summary,holdout='not rerun')
    except Exception as exc:
        if trainer is not None:trainer.save(out/'interrupted.pt')
        status('failed',trainer,error=repr(exc))
        raise
    finally:
        writer.close()

if __name__=='__main__':main()
