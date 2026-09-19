"""Bounded diagnostics on canonical candidates; never updates model parameters."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from initial_state import canonical_bytes, read_records, reset_payload

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parent


def families(row):
    state = row['state']
    return ({'encounter:'+state['encounter']} |
            {'augmentation:'+row.get('evidence',{}).get('augmentation',{}).get('category','baseline')} |
            {'entry-counter:'+r['name']+':'+str(r['counter']) for r in state['relics'] if isinstance(r,dict) and 'counter' in r} |
            {'relic:'+(r if isinstance(r,str) else r['name']) for r in state['relics']} |
            {'potion:'+p for p in state['potions'] if p} |
            {'card:'+c for c in state['deck']})


def select_cases(rows, limit):
    remaining = sorted(rows,key=lambda r:r['state_hash']); selected=[]; seen=set()
    while remaining and len(selected)<limit:
        best = max(remaining,key=lambda r:len(families(r)-seen))
        selected.append(best); seen |= families(best); remaining.remove(best)
    return selected, seen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend-root',type=Path,required=True)
    parser.add_argument('--states',type=Path,default=PROJECT/'pilot-states.jsonl')
    parser.add_argument('--output-dir',type=Path,default=PROJECT)
    args=parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    manifest_path=args.output_dir/'runtime-manifest.json'
    report_path=args.output_dir/'runtime-report.json'
    if args.output_dir != PROJECT and (manifest_path.exists() or report_path.exists()):
        raise ValueError('Refusing to overwrite versioned runtime evidence')
    inventory=json.loads((PROJECT/'source-inventory.json').read_text())
    expected=inventory['backend']['sha256']
    sys.path[:0]=[str(ROOT),str(args.backend_root/'build')]
    import torch
    import slaythespire
    from sts.env.relics import RelicEnv
    from sts.models.apath import APathActorCritic, encode, batch_samples
    from sts.train.apath import sample_digest
    actual=hashlib.sha256(Path(slaythespire.__file__).read_bytes()).hexdigest()
    if actual != expected: raise ValueError('Backend binary differs from frozen inventory')
    for relative, wanted in inventory['implementation_hashes'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=wanted:
            raise ValueError('Implementation changed since inventory: '+relative)
    torch.set_num_threads(1);torch.manual_seed(190919)
    model=APathActorCritic().eval()
    rows=read_records(args.states)
    selected, covered=select_cases(rows,32)
    manifest={'model':'untrained APathActorCritic','model_seed':190919,'optimizer_updates':0,
              'max_actions':128,'development_seeds':[100123,100124],
              'full_episode_selection':'greedy coverage of card/encounter/relic/potion/augmentation/counter labels, max 32 states; not independent source sampling',
              'selected_hashes':[r['state_hash'] for r in selected],
              'covered_labels':sorted(covered),
              'uncovered_labels':sorted(set().union(*(families(r) for r in rows))-covered)}
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')

    def action(obs,generator):
        sample=encode(obs)
        if not sample.sources: raise ValueError('Nonterminal state has no legal action')
        batch=batch_samples([sample])
        with torch.no_grad():
            dist,value=model(batch)
            if not torch.isfinite(value).all() or not torch.isfinite(dist.entropy()).all():
                raise ValueError('Nonfinite model value or entropy')
            if not torch.allclose(dist.probs.sum((1,2)),torch.ones(1),atol=1e-5):
                raise ValueError('Joint probabilities do not sum to one')
            u,j=dist.sample(generator)
        route=sample.route(u.item(),j.item())
        if sample.decompose(route)!=(u.item(),j.item()): raise ValueError('Routing mismatch')
        return route,sample_digest(sample)

    def episode(row,seed,one_step=False):
        env=RelicEnv(max_actions=128)
        obs=env.reset(reset_payload(row),seed,diagnostic=True,purpose='development')
        initial=sample_digest(encode(obs)); trace=[]; uses=0
        rng=torch.Generator().manual_seed(seed)
        for step in range(128):
            route,before=action(obs,rng)
            if route.get('kind')=='NORMAL' and 51<=route['action']<=65: uses+=1
            obs,reward,term,trunc,info=env.step(route)
            assert info['training_admitted'] is False
            assert info['reward_version']=='battle_reward_v2'
            assert not (term and trunc)
            trace.append([before,reward,term,trunc,sample_digest(encode(obs))])
            if term:
                p=row['state']['player']
                expected_reward=2*int(info['battle_won'])+(obs['player']['hp']-p['hp'])/p['max_hp']-0.05*uses
                if abs(expected_reward-reward)>1e-10: raise ValueError('Independent v2 reward recomputation failed')
                if not info['reward_accounting']['complete']: raise ValueError('Terminal accounting incomplete')
            elif reward!=0: raise ValueError('Nonterminal reward must be zero')
            if uses!=info['reward_accounting']['potion_uses']: raise ValueError('Potion use count mismatch')
            if term or trunc:
                with torch.no_grad():
                    value=model.value_only(batch_samples([encode(obs)]))
                if not torch.isfinite(value).all(): raise ValueError('Nonfinite final-observation value')
                if trunc and info['reward_accounting']['complete']: raise ValueError('Truncation labeled complete')
                try: env.step(route)
                except RuntimeError: pass
                else: raise ValueError('Closed episode accepted another step')
            if term or trunc or one_step:
                return {'state_hash':row['state_hash'],'seed':seed,'steps':step+1,
                        'status':'terminated' if term else 'truncated' if trunc else 'one-step-checked',
                        'outcome':info['task_outcome'],'reward':reward,'potion_uses':uses,
                        'initial_digest':initial,'trace_digest':hashlib.sha256(canonical_bytes(trace)).hexdigest(),
                        'reward_accounting':info['reward_accounting']}
        raise ValueError('No termination/truncation at declared action bound')

    checks=[];episodes=[];failures=[]
    for i,row in enumerate(rows):
        try: checks.append(episode(row,100123,one_step=True))
        except Exception as exc: failures.append({'phase':'reset-forward-step','state_hash':row['state_hash'],'error':repr(exc)})
        if (i+1)%25==0: print(f'Initial-state diagnostics: {i+1}/{len(rows)}',flush=True)
    for i,row in enumerate(selected):
        for seed in (100123,100124):
            try: episodes.append(episode(row,seed))
            except Exception as exc: failures.append({'phase':'episode','state_hash':row['state_hash'],'seed':seed,'error':repr(exc)})
        if (i+1)%4==0: print(f'Complete-episode cases: {i+1}/{len(selected)}',flush=True)
    replay=[]
    for row in selected[:2]:
        try:
            again=episode(row,100123)
            original=next(e for e in episodes if e['state_hash']==row['state_hash'] and e['seed']==100123)
            if again!=original: raise ValueError('Same-state same-seed replay differs')
            replay.append({'state_hash':row['state_hash'],'equal':True})
        except Exception as exc: failures.append({'phase':'replay','state_hash':row['state_hash'],'error':repr(exc)})
    report={'schema':'initial-state-runtime-diagnostic-v1','backend_sha256':actual,
            'initial_state_checks':checks,'episodes':episodes,'replay':replay,'failures':failures,
            'counts':{'states_checked':len(checks),'episodes':len(episodes),
                      'episode_status':dict(Counter(e['status'] for e in episodes)),
                      'outcomes':dict(Counter(e['outcome'] for e in episodes)),
                      'failures':len(failures)},'training_admitted':False,'optimizer_updates':0,
            'scope':'Engineering diagnostics of supplied canonical states; not historical equivalence, training or generalization',
            'hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [
                Path(__file__),PROJECT/'initial_state.py',args.states,manifest_path]}}
    report_path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report['counts'],indent=2),flush=True)
    if failures: raise SystemExit(1)


if __name__=='__main__':main()
