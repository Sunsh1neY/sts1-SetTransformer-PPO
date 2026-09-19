"""Bounded CUDA collector/update/recovery smoke; never launches formal training."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import time
import traceback

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
PROJECT=Path(__file__).resolve().parent
ROOT=PROJECT.parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    sys.path[:0]=[str(ROOT),str(args.backend_root/'build')]
    import torch
    from sts.env.acorpus import ACorpus, POLICY
    from sts.train.apath import APathTrainer, fingerprint, sample_digest
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available(): raise RuntimeError('Approved CUDA device unavailable')
    started=time.monotonic();deadline=started+900
    corpus_dir=PROJECT/'corpora/a-v2'
    report={'status':'running','scope':'smoke-only','formal_training_started':False,
            'budget_seconds':900,'sampling_policy':POLICY,'corpus_dir':str(corpus_dir),
            'device':torch.cuda.get_device_name(0),'torch_version':torch.__version__,
            'fingerprint':fingerprint(corpus_dir),
            'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'metrics':[], 'episodes':[], 'physical_collector_transitions':0}
    def save():
        report['elapsed_seconds']=time.monotonic()-started
        (args.output/'smoke-report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    def equal(a,b):
        if isinstance(a,torch.Tensor): assert torch.equal(a.cpu(),b.cpu())
        elif isinstance(a,dict):
            assert a.keys()==b.keys()
            for k in a: equal(a[k],b[k])
        elif isinstance(a,(list,tuple)):
            assert len(a)==len(b)
            for x,y in zip(a,b):equal(x,y)
        else: assert a==b
    def step(trainer,label):
        print('Starting '+label,flush=True)
        result,episodes=trainer.iteration_step(deadline)
        report['physical_collector_transitions']+=1024
        report['metrics'].append(dict(branch=label,**result))
        report['episodes'].extend(dict(branch=label,**e) for e in episodes)
        save()
        print(json.dumps({'branch':label,'env_steps':trainer.env_steps,'seconds':time.monotonic()-started}),flush=True)
    try:
        corpus=ACorpus(corpus_dir)
        # Cases are fixed but not evaluated: holdout results remain unopened.
        cases={split:[{'state_hash':k,'environment_seed':seed,'policy_seed':700000+seed}
                      for k,r in sorted(corpus.rows.items()) if r['provenance']['partition']==split
                      for seed in ([0] if split=='audit-dev' else [1,2])]
               for split in ('audit-dev','audit-holdout')}
        (args.output/'evaluation-cases.json').write_text(json.dumps(cases,indent=2)+'\n')
        report['evaluation_manifest_sha256']=hashlib.sha256((args.output/'evaluation-cases.json').read_bytes()).hexdigest()
        trainer=APathTrainer(group=100,device='cuda',corpus_dir=corpus_dir)
        report['config']=trainer.config
        report['model_version']=trainer.model.model_version
        before={k:v.detach().cpu().clone() for k,v in trainer.model.state_dict().items()}
        save()
        for i in range(2):step(trainer,f'warmup-{i+1}')
        assert any(not torch.equal(before[k],v.cpu()) for k,v in trainer.model.state_dict().items())
        trainer.save(args.output/'after-two-updates.pt')
        assert trainer.iteration==2 and trainer.env_steps==2048
        report['parameter_update_verified']=True
        step(trainer,'reference-continuation')
        restored=APathTrainer.load(args.output/'after-two-updates.pt')
        assert restored.env_steps==2048 and restored.iteration==2
        step(restored,'restored-continuation')
        equal(trainer.model.state_dict(),restored.model.state_dict())
        equal(trainer.optimizer.state_dict(),restored.optimizer.state_dict())
        equal(trainer.action_rng.get_state(),restored.action_rng.get_state())
        for rng in ('scene_rng','environment_rng','shuffle_rng'):
            equal(getattr(trainer,rng).bit_generator.state,getattr(restored,rng).bit_generator.state)
        assert trainer.reset_counts==restored.reset_counts
        assert [sample_digest(s) for s in trainer.observations]==[sample_digest(s) for s in restored.observations]
        a,b=pickle.loads(trainer.last_rollout),pickle.loads(restored.last_rollout)
        for key in ('source','target','old_logp','old_value','rewards','returns','advantage','terminated','truncated','next_values'):
            equal(a[key],b[key])
        assert [sample_digest(s) for s in a['samples']]==[sample_digest(s) for s in b['samples']]
        assert not a['next_values'][a['terminated']].any()
        restored.save(args.output/'restored-final.pt')
        report.update(status='passed', exact_recovery_verified=True,
            logical_transitions=3072,physical_collector_transitions=4096,
            optimizer_steps_per_branch=192,reset_counts=dict(restored.reset_counts),
            final_model_sha256=hashlib.sha256(b''.join(v.detach().cpu().contiguous().numpy().tobytes() for v in restored.model.state_dict().values())).hexdigest())
        try: restored.iteration_step(deadline)
        except ValueError as exc: report['smoke_limit_guard']=str(exc)
        else: raise AssertionError('Smoke limit not enforced')
        assert fingerprint(corpus_dir)==report['fingerprint']
    except Exception as exc:
        report.update(status='failed',error=repr(exc),traceback=traceback.format_exc())
        raise
    finally:save()
    print(json.dumps({k:report[k] for k in ('status','elapsed_seconds','physical_collector_transitions','exact_recovery_verified')}),flush=True)


if __name__=='__main__':main()
