"""候选完整卡组的真实环境准入预检；随机及未训练Pointer，不执行PPO。"""
import copy
import hashlib
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from sts.env.ironclad import IroncladEnv
from sts.env.entities import encode_observation
from sts.env.lightspeed import _load_backend
from sts.models.apath import APathActorCritic, adapt, batch_samples


def run():
    torch.set_num_threads(1)
    torch.manual_seed(190914)
    model = APathActorCritic().eval()
    action_rng = torch.Generator().manual_seed(190915)
    random_rng = random.Random(190916)
    groups = json.loads((ROOT/'docs/a-path-deck-grouping-proposal.json').read_bytes())
    audit = json.loads((ROOT/'docs/a-path-source-sampling-audit.json').read_bytes())
    batch = json.loads((ROOT/'sts/env/real-deck-batch.json').read_bytes())
    train = {d['content_id']:d for d in groups['contents'] if d['split']=='train_candidate'}
    dev = [d for d in groups['contents'] if d['split']=='development']
    train_components = {d['component_id'] for d in train.values()}
    train_runs = {s['run'] for d in train.values() for s in d['sources']}
    dev_components = {d['component_id'] for d in dev}
    dev_runs = {s['run'] for d in dev for s in d['sources']}
    separation = {'train_component_count':len(train_components), 'development_component_count':len(dev_components),
                  'component_overlap':sorted(train_components & dev_components),
                  'run_overlap':sorted(train_runs & dev_runs),
                  'deck_content_overlap':sorted(set(train) & {d['content_id'] for d in dev}),
                  'heldout_source_set': '不存在新未见保留集；当前评估沿用历史开发来源',
                  'eval_seeds_sha256':hashlib.sha256((ROOT/'eval_seeds.json').read_bytes()).hexdigest()}
    assert not any(separation[k] for k in ('component_overlap','run_overlap','deck_content_overlap'))
    assert separation['eval_seeds_sha256'] == groups['source_sha256']['eval_seeds.json']
    sizes = Counter()
    for group_id in train_components:
        sizes[sum(d['component_id']==group_id for d in train.values())] += 1
    config_rows = audit['initial_configurations']
    results, started = [], time.monotonic()
    for policy in ('uniform_complete_action', 'untrained_a_path'):
        for base in range(0, len(config_rows), 8):
            active = []
            for index, config in enumerate(config_rows[base:base+8], start=base):
                row = train[config['content_id']]
                candidate = {**batch['common'], **batch['profiles'][config['condition']],
                             'deck':row['cards'], 'encounter':config['encounter']}
                canonical = json.dumps(candidate,sort_keys=True,ensure_ascii=False,separators=(',', ':')).encode()
                assert hashlib.sha256(canonical).hexdigest()==config['initial_config_sha256']
                seed = 91000000 + index
                record = dict(policy=policy, initial_config_sha256=config['initial_config_sha256'],
                    content_id=config['content_id'], component_id=config['component_id'], group=row['group'],
                    condition=config['condition'], encounter=config['encounter'], environment_seed=seed,
                    steps=0, return_observed=0., max_entities=0, max_legal_actions=0, max_allocated_cards=0,
                    phases={}, potion_uses=0, status='running')
                results.append(record)
                try:
                    env = IroncladEnv(max_actions=512)
                    obs = env.reset(copy.deepcopy(candidate), seed, diagnostic=True, purpose='development')
                    active.append((env,obs,record))
                except Exception as error:
                    record.update(status='error_reset',error=repr(error))
            while active:
                if time.monotonic()-started>600:
                    raise TimeoutError('工程运行预检达到10分钟上限，未开展训练')
                ready=[]
                for env,obs,record in active:
                    try:
                        sample=adapt(encode_observation(obs))
                        record['max_entities']=max(record['max_entities'],len(sample.entities.tokens))
                        record['max_legal_actions']=max(record['max_legal_actions'],sum(map(len,sample.routes)))
                        phase=obs['decision']['phase']
                        record['phases'][phase]=record['phases'].get(phase,0)+1
                        ready.append((env,obs,record,sample))
                    except Exception as error:
                        record.update(status='error_encode',error=repr(error))
                if not ready:
                    break
                if policy=='untrained_a_path':
                    with torch.no_grad():
                        u,j,logp,value=model.act(batch_samples([r[3] for r in ready]),action_rng)
                        assert torch.isfinite(logp).all() and torch.isfinite(value).all()
                    routes=[r[3].route(a,b) for r,a,b in zip(ready,u.tolist(),j.tolist())]
                else:
                    routes=[random_rng.choice([x for rs in r[3].routes for x in rs]) for r in ready]
                active=[]
                for (env,obs,record,sample),route in zip(ready,routes):
                    try:
                        assert sample.route(*sample.decompose(route))==route
                        nxt,reward,term,trunc,info=env.step(route)
                        record['steps']+=1;record['return_observed']+=reward
                        if route.get('kind')=='NORMAL' and route['action']>=51:
                            record['potion_uses']+=1
                        encoded=encode_observation(nxt)
                        record['max_entities']=max(record['max_entities'],len(encoded.tokens))
                        record['max_allocated_cards']=max(record['max_allocated_cards'],env._env.allocated_card_count())
                        if term or trunc:
                            assert not (term and trunc)
                            record.update(status='terminated' if term else 'truncated',
                                outcome=info['task_outcome'], exit_hp=nxt['player']['hp'],
                                battle_exit_present='battle_exit' in info, final_observation_complete=True)
                            if term:
                                assert 'battle_exit' in info
                                assert not any(e['present'] for e in nxt['enemies'])
                            else:
                                with torch.no_grad():
                                    assert torch.isfinite(model.value_only(batch_samples([adapt(encoded)]))).all()
                        else:
                            active.append((env,nxt,record))
                    except Exception as error:
                        record.update(status='error_step',error=repr(error))
            if base % 80 == 0:
                print(json.dumps({'policy':policy,'finished':min(base+8,len(config_rows)),
                                  'seconds':round(time.monotonic()-started,2)},ensure_ascii=False),flush=True)
    summary=[]
    for policy in ('uniform_complete_action','untrained_a_path'):
        selected=[r for r in results if r['policy']==policy]
        summary.append(dict(policy=policy,episodes=len(selected),status_counts=dict(Counter(r['status'] for r in selected)),
            total_transitions=sum(r['steps'] for r in selected),
            max_entities=max(r['max_entities'] for r in selected),
            max_legal_actions=max(r['max_legal_actions'] for r in selected),
            max_allocated_cards=max(r['max_allocated_cards'] for r in selected),
            selection_transitions=sum(r['phases'].get('SELECT_CARD',0) for r in selected)))
    report=dict(schema='a-path-candidate-runtime-check-v1', formal_training=False, ppo_updates=0,
                diagnostic_entry=True, elapsed_seconds=time.monotonic()-started,
                separation=separation, source_group_deck_counts=dict(sorted(sizes.items())),
                source_audit_sha256=hashlib.sha256((ROOT/'docs/a-path-source-sampling-audit.json').read_bytes()).hexdigest(),
                backend_sha256=hashlib.sha256(Path(_load_backend().__file__).read_bytes()).hexdigest(),
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),summary=summary,episodes=results)
    output=ROOT/'runs/environment-integration/a-path-candidate-runtime.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='episodes'},ensure_ascii=False,indent=2),flush=True)
    if any(r['status'] not in ('terminated','truncated') for r in results):
        raise RuntimeError('存在reset/运行失败，不能批准候选池')


if __name__=='__main__':
    run()
