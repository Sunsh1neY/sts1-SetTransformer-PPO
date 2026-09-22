"""Approved one-initialization A-v2 PPO with one train/dev TensorBoard run."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import threading
import zipfile
from datetime import datetime, timezone

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def write(path,value):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    temp.replace(path)


def append(path,value):
    with path.open('a',encoding='utf-8') as f:f.write(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--architecture',choices=('m3a','c_w128','c_d4'),required=True)
    parser.add_argument('--seconds',type=int,default=43200)
    args=parser.parse_args()
    sys.path.insert(0,str(args.backend_root/'build'))
    import torch
    from torch.utils.tensorboard import SummaryWriter
    from sts.env.acorpus import ACorpus, POLICY
    from sts.train.critic_ablation import CriticTrainer as APathTrainer,fingerprint,check_deadline
    from sts.train.corpus_evaluation import evaluate,summarize,strata,paired_comparison
    from sts.models.architectures.critic_variants import MODELS
    APathActorCritic=MODELS[args.architecture]
    from sts.battle_reward_v2 import contract
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    if (out/'status.json').exists():raise ValueError('Refusing to overwrite an existing run')
    torch.set_num_threads(1);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
    if args.seconds != 43200:raise ValueError('Approved cap is 43200 seconds')
    started=time.monotonic();deadline=started+args.seconds;train_deadline=deadline-3600
    corpus_path=ROOT/'projects/battle-initial-states/corpora/a-v2'
    corpus=ACorpus(corpus_path)
    writer=SummaryWriter(str(out/'tensorboard'/(args.architecture+'-v1')),flush_secs=5)
    config=dict(protocol='experiment-protocol-v1',group=0,device='cuda',num_envs=8,num_steps=128,
                total_transitions=262144,seconds=args.seconds,closure_reserve_seconds=3600,
                corpus_scope='experiment-protocol-v1',sampling=POLICY,model=APathActorCritic.model_version,
                lr=2.5e-4,lr_schedule='linear',gamma=1.,gae_lambda=.95,minibatch=64,epochs=4,
                clip=.2,value_clip=True,entropy_coef=.01,value_coef=.5,max_grad_norm=.5,
                adam_eps=1e-5,adam_betas=[.9,.999],weight_decay=0,precision='fp32',tf32=False,
                reward=contract(),eval_updates=[0,64,128,192,256],selection='max_dev_component_macro_reward_earliest_tie')
    config.update(architecture=args.architecture, parameter_count=sum(p.numel() for p in APathActorCritic().parameters()), baseline_run='m2a-source-context-continuation-v2', holdout_scope='deferred; dev-only selection', initialization='same-seed fresh M0 modules; zero-output source-query residual')
    write(out/'config.json',config)
    cases=json.loads((ROOT/'projects/battle-initial-states/experiments/smoke-v1/evaluation-cases.json').read_bytes())
    reserved=set(json.loads((ROOT/'eval_seeds.json').read_text(encoding='utf-8'))['seeds'])
    cases={'audit-dev':cases['audit-dev']}
    for split,n in (('audit-dev',288),):
        assert len(cases[split])==n
        assert all(corpus.rows[c['state_hash']]['provenance']['partition']==split and c['environment_seed'] in reserved for c in cases[split])
    write(out/'evaluation-cases.json',cases)
    fp=fingerprint(corpus_path)
    write(out/'fingerprint.json',fp)
    with zipfile.ZipFile(out/'source-snapshot.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in fp:
            if path=='backend':continue
            original=corpus_path/path[7:] if path.startswith('corpus/') else ROOT/path
            archive.write(original,path)
        for file in ('config.json','evaluation-cases.json'):archive.write(out/file,file)
        archive.write(ROOT/'projects/battle-initial-states/experiment-protocol-v1.md','experiment-protocol-v1.md')
    writer.add_text('configuration/protocol',(ROOT/'projects/battle-initial-states/experiment-protocol-v1.md').read_text(encoding='utf-8'),0)
    writer.add_text('configuration/effective',json.dumps(config,indent=2),0)
    writer.add_text('configuration/critic_ablation',(ROOT/'docs/critic-ablation-protocol-v1.md').read_text(encoding='utf-8'),0)
    status=dict(status='starting',pid=os.getpid(),started_at=datetime.now(timezone.utc).isoformat(),
                env_steps=0,iteration=0,budget_seconds=args.seconds,formal_training_started=True,
                device=torch.cuda.get_device_name(0),fingerprint=fp,best_dev=None)
    trainer=None;best_score=-math.inf;best_update=None;best_path=None
    from sts.train.resource_telemetry import memory_sample
    stop_telemetry=threading.Event()
    def sample_resources():
        while not stop_telemetry.is_set():
            sample=memory_sample()
            sample.update(wall_time=time.time(),elapsed_seconds=time.monotonic()-started)
            append(out/'resource-telemetry.jsonl',sample)
            stop_telemetry.wait(5)
    telemetry_thread=threading.Thread(target=sample_resources,daemon=True)
    telemetry_thread.start()
    def refresh(phase,**extra):
        if trainer is not None:
            status.update(env_steps=trainer.env_steps,iteration=trainer.iteration)
        status.update(status=phase,elapsed_seconds=time.monotonic()-started,**extra)
        write(out/'status.json',status)
        step=trainer.env_steps if trainer is not None else 0
        writer.add_scalar('system/elapsed_seconds',status['elapsed_seconds'],step)
        for key,value in memory_sample().items():writer.add_scalar('system/memory/'+key,value,step)
        writer.add_scalar('system/phase',{'starting':0,'dev':1,'training':2,'holdout':3,'completed':4,'failed':-1,'time_limit':-2,'incomplete_evaluation':-3}.get(phase,5),step)
        writer.flush()
    def log_summary(prefix,summary,step):
        for k,v in summary.items():
            if isinstance(v,(int,float)) and math.isfinite(v):writer.add_scalar(prefix+'/'+k,v,step)
    def eval_checkpoint(model,split,label,step):
        nonlocal best_score,best_update,best_path
        phase='dev' if split=='audit-dev' else 'holdout'
        refresh(phase,evaluation_label=label,evaluation_done=0,evaluation_total=len(cases[split]))
        path=out/(label+'-episodes.jsonl')
        def on_case(row,done,total):
            append(path,row)
            if done%16==0 or done==total:
                refresh(phase,evaluation_label=label,evaluation_done=done,evaluation_total=total)
                writer.add_scalar('system/evaluation_progress',done/total,step)
        rows=evaluate(model,corpus,cases[split],deadline-30,on_case)
        summary=summarize(rows);breakdown=strata(rows)
        write(out/(label+'-summary.json'),dict(overall=summary,strata=breakdown))
        prefix='dev' if phase=='dev' else label.replace('-','/')
        log_summary(prefix+'/overall',summary,step)
        for key,value in breakdown.items():log_summary(prefix+'/strata/'+key,value,step)
        writer.flush()
        if phase=='dev':
            if 'reward' not in summary:raise ValueError('Incomplete dev terminal evaluation; selection blocked')
            update=step//1024
            if summary['reward']>best_score:
                best_score=summary['reward'];best_update=update
                best_path=out/('initial.pt' if update==0 else f'update-{update:04d}.pt')
                shutil.copy2(best_path,out/'selected.pt')
                status['best_dev']=dict(update=update,score=best_score)
            writer.add_scalar('dev/selection/best_reward',best_score,step)
            writer.add_scalar('dev/selection/best_update',best_update,step)
        return rows
    try:
        trainer=APathTrainer(architecture=args.architecture,corpus_dir=corpus_path,corpus_scope='experiment-protocol-v1',device='cuda')
        trainer.save(out/'initial.pt')
        shutil.copy2(out/'initial.pt',out/'latest.pt')
        initial=APathActorCritic().cuda();initial.load_state_dict(copy.deepcopy(trainer.model.state_dict()))
        eval_checkpoint(initial,'audit-dev','dev-0000',0)
        refresh('training')
        last_duration=0.
        while trainer.env_steps<262144 and time.monotonic()+max(60,last_duration*2)<train_deadline:
            before=time.monotonic()
            metrics,episodes=trainer.iteration_step(train_deadline)
            last_duration=time.monotonic()-before
            step=trainer.env_steps
            append(out/'metrics.jsonl',metrics)
            for e in episodes:append(out/'train-episodes.jsonl',e)
            for key in ('policy_loss','value_loss','entropy','approx_kl','clip_fraction','learning_rate','grad_norm'):
                writer.add_scalar('train/ppo/'+key,metrics[key],step)
            for group,values in metrics['groups'].items():log_summary('train/groups/'+group,values,step)
            for group,values in metrics['group_updates'].items():log_summary('train/groups/'+group+'/ppo',values,step)
            def log_episodes(prefix,items):
                writer.add_scalar(prefix+'/completed',len(items),step)
                if not items:return
                writer.add_scalar(prefix+'/truncation_rate',sum(e['truncated'] for e in items)/len(items),step)
                terminal=[e for e in items if e['terminated']]
                if terminal:
                    for key,fn in {'reward':lambda e:e['return_complete'],'win_rate':lambda e:e['outcome']=='victory',
                                   'exit_hp_ratio':lambda e:e['hp']/e['max_hp'],'potion_uses':lambda e:e['potion_uses']}.items():
                        writer.add_scalar(prefix+'/'+key,sum(fn(e) for e in terminal)/len(terminal),step)
            log_episodes('train/episodes',episodes)
            resets=sum(trainer.reset_counts.values())
            for kind in ('natural','augmentation'):
                writer.add_scalar('train/sampling/'+kind+'_resets',trainer.reset_counts[kind],step)
                writer.add_scalar('train/sampling/'+kind+'_reset_fraction',trainer.reset_counts[kind]/resets,step)
                writer.add_scalar('train/sampling/'+kind+'_transition_fraction',metrics['groups'].get(kind,{}).get('transitions',0)/1024,step)
                log_episodes('train/groups/'+kind+'/episodes',[e for e in episodes if e['group']==kind])
            log_summary('system',dict(env_steps=step,iteration=trainer.iteration,collect_seconds=metrics['collect_seconds'],
                        update_seconds=metrics['update_seconds'],transitions_per_second=1024/last_duration,
                        peak_cuda_memory_mb=torch.cuda.max_memory_allocated()/1024**2),step)
            if trainer.iteration==1 or trainer.iteration%8==0:trainer.save(out/'latest.pt')
            if trainer.iteration%64==0:
                trainer.save(out/f'update-{trainer.iteration:04d}.pt')
                eval_checkpoint(trainer.model,'audit-dev',f'dev-{trainer.iteration:04d}',step)
            refresh('training',env_steps=step,iteration=trainer.iteration,last_metrics=metrics)
            print(json.dumps({'iteration':trainer.iteration,'env_steps':step,'elapsed':time.monotonic()-started}),flush=True)
        trainer.save(out/'final.pt')
        if fingerprint(corpus_path)!=fp:raise ValueError('Run fingerprint changed')
        complete=trainer.env_steps==262144
        refresh('completed' if complete else 'time_limit',env_steps=trainer.env_steps,
                iteration=trainer.iteration,step_budget_completed=complete,
                holdout_status='deferred',selected_update=best_update)
    except TimeoutError as exc:
        if trainer is not None:trainer.save(out/'time-limit-snapshot.pt')
        refresh('time_limit',error=str(exc),env_steps=trainer.env_steps if trainer else 0)
    except Exception as exc:
        if trainer is not None:
            try:trainer.save(out/'failure-snapshot.pt')
            except Exception:pass
        refresh('failed',error=repr(exc),traceback=traceback.format_exc(),env_steps=trainer.env_steps if trainer else 0)
        raise
    finally:
        stop_telemetry.set()
        telemetry_thread.join(timeout=6)
        writer.close()
        write(out/'run-report.json',status)


if __name__=='__main__':main()
