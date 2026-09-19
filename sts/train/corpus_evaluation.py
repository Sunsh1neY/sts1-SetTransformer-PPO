"""Fixed-case, component-macro evaluation for experiment protocol v1."""
from collections import defaultdict
import numpy as np
import torch

from sts.env.acorpus import ACorpusSmokeEnv
from sts.models.apath import encode, batch_samples
from sts.train.apath import check_deadline


def summarize(rows):
    """Average seeds within states, states within components, then components."""
    if not rows:
        return {}
    result={'cases':len(rows),'truncation_rate':sum(r['truncated'] for r in rows)/len(rows)}
    if any(not r['terminated'] for r in rows):
        return result
    components=defaultdict(lambda:defaultdict(list))
    for r in rows:
        components[r['component']][r['state_hash']].append(r)
    for metric in ('reward','win','exit_hp_ratio','potion_uses'):
        result[metric]=float(np.mean([np.mean([np.mean([r[metric] for r in values])
                         for values in states.values()]) for states in components.values()]))
    result['components']=len(components)
    return result


def hp_band(state):
    ratio=state['player']['hp']/state['player']['max_hp']
    return 'le25' if ratio<=.25 else '25to50' if ratio<=.5 else '50to75' if ratio<=.75 else 'gt75'


def strata(rows):
    buckets=defaultdict(list)
    for row in rows:
        for key in ('kind','act','hp_band','encounter','family'):
            buckets[f'{key}/{row[key]}'].append(row)
    return {k:summarize(v) for k,v in buckets.items()}


def evaluate(model,corpus,cases,deadline,on_case):
    env=ACorpusSmokeEnv(corpus,scope='experiment-protocol-v1')
    device=next(model.parameters()).device
    model.eval()
    rows=[]
    for case in cases:
        check_deadline(deadline)
        key=case['state_hash'];source=corpus.rows[key];scene=corpus.scene(key)
        obs=env.reset(scene,case['environment_seed'],purpose='evaluation')
        rng=torch.Generator(device=device).manual_seed(case['policy_seed'])
        total=0.
        for steps in range(1,513):
            check_deadline(deadline)
            sample=encode(obs)
            with torch.no_grad():
                dist,value=model(batch_samples([sample],device))
                if not torch.isfinite(value).all() or not torch.isfinite(dist.entropy()).all():
                    raise FloatingPointError('Nonfinite evaluation policy/value')
                u,j=dist.sample(rng)
            obs,reward,term,trunc,info=env.step(sample.route(u.item(),j.item()))
            total+=reward
            if term or trunc:break
        else:raise RuntimeError('Episode did not close at action limit')
        row=dict(case,component=source['provenance']['component'],kind=scene['content_group'],
            act=source['state']['act'],hp_band=hp_band(source['state']),encounter=scene['encounter'],
            family=source['evidence'].get('augmentation',{}).get('category','natural'),
            terminated=term,truncated=trunc,steps=steps,reward=total if term else None,
            win=int(info['task_outcome']=='victory') if term else None,
            exit_hp_ratio=obs['player']['hp']/source['state']['player']['max_hp'],
            potion_uses=info['reward_accounting']['potion_uses'])
        rows.append(row);on_case(row,len(rows),len(cases))
    return rows


def paired_comparison(initial,selected):
    a={(r['state_hash'],r['environment_seed']):r for r in initial}
    b={(r['state_hash'],r['environment_seed']):r for r in selected}
    if a.keys()!=b.keys():raise ValueError('Paired evaluation cases differ')
    result={'initial':summarize(initial),'selected':summarize(selected)}
    if any(r['truncated'] for r in initial+selected):
        result['status']='incomplete-terminal-evaluation'
        return result
    result['strata_initial']=strata(initial);result['strata_selected']=strata(selected)
    groups=defaultdict(lambda:defaultdict(list))
    for key,r in a.items():groups[r['component']][r['state_hash']].append(b[key]['reward']-r['reward'])
    differences=np.array([np.mean([np.mean(v) for v in states.values()]) for states in groups.values()])
    rng=np.random.default_rng(190919)
    samples=rng.choice(differences,size=(10000,len(differences)),replace=True).mean(1)
    result.update(status='complete',paired_reward_difference=float(differences.mean()),
                  reward_difference_ci95=np.quantile(samples,[.025,.975]).tolist(),components=len(differences))
    return result
