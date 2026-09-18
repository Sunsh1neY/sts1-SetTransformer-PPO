"""有硬预算的本地后台训练：三初始化上限、分层评估、自动保存和交付报告。"""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import argparse
import copy
import json
from pathlib import Path
import random
import sys
import time
import traceback
import zipfile
from collections import Counter
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from sts.battle_reward_v2 import contract as reward_contract
from sts.env.apath import APathEnv,load_pool,scene
from sts.models.apath import APathActorCritic,encode,batch_samples
from sts.train.apath import APathTrainer,check_deadline,fingerprint
from sts.agents.rule_agent import RuleAgent,CARD_NAMES,PUBLIC_SCHEMA,_name


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(path)


def cases():
    pool=load_pool();result=[]
    for row in sorted(pool['contents'],key=lambda r:r['content_id']):
        if row['split']!='development':continue
        for condition in sorted(pool['profiles']):
            for encounter in pool['encounters']:
                for repeat in range(2):
                    result.append(dict(scene=scene(row['content_id'],condition,encounter),
                        seed=95000000+len(result),case_id=f"{row['content_id']}:{condition}:{encounter}:{repeat}"))
    return result


@torch.no_grad()
def evaluate(model,policy,cases,device,deadline):
    results=[];rng=random.Random(946001);action_rng=torch.Generator(device=device).manual_seed(946002)
    if model is not None:model.eval()
    for offset in range(0,len(cases),8):
        active=[]
        for case in cases[offset:offset+8]:
            s=case['scene']
            record=dict(case_id=case['case_id'],group=s['content_group'],content_id=s['content_id'],
                source_group=s['component_id'],condition=s['condition'],encounter=s['encounter'],steps=0,
                potion_uses=0,reward_observed=0.,entropies=[],values=[],status='running')
            results.append(record)
            if policy=='rule' and any(_name(c.split('+')[0]) not in CARD_NAMES for c in s['candidate']['deck']):
                record.update(status='rule_gap',reason='卡组含旧规则未覆盖牌');continue
            env=APathEnv();obs=env.reset(s,case['seed'],purpose='development')
            active.append((env,obs,record))
        while active:
            check_deadline(deadline)
            samples=[encode(obs) for _,obs,_ in active]
            if policy=='a-path':
                dist,values=model(batch_samples(samples,device))
                u,j=dist.sample(action_rng);entropy=dist.entropy().cpu().tolist()
                routes=[s.route(a,b) for s,a,b in zip(samples,u.tolist(),j.tolist())]
                value_list=values.cpu().tolist()
            else:
                routes=[];entropy=[None]*len(active);value_list=[None]*len(active)
                for (_,obs,record),sample in zip(active,samples):
                    if policy=='random':
                        routes.append(rng.choice([r for rs in sample.routes for r in rs]))
                    else:
                        if obs['decision']['phase']!='NORMAL' or obs['relations']:
                            record.update(status='rule_gap',reason='新选择阶段或关系不在规则共同切片');routes.append(None);continue
                        try:
                            # 明确的共同语义视图适配，不声称旧规则覆盖新协议所有机制。
                            view=copy.deepcopy(obs);view['schema']=PUBLIC_SCHEMA
                            action=RuleAgent().decide(view).action
                            routes.append(next(r for rs in sample.routes for r in rs if r.get('action')==action))
                        except ValueError as error:
                            record.update(status='rule_gap',reason=str(error));routes.append(None)
            remaining=[]
            for i,((env,obs,record),route) in enumerate(zip(active,routes)):
                if route is None:continue
                if entropy[i] is not None:
                    record['entropies'].append(entropy[i]);record['values'].append(value_list[i])
                nxt,reward,term,trunc,info=env.step(route)
                record.update(potion_uses=info['reward_accounting']['potion_uses'],
                    reward_contract=info['reward_contract'],reward_accounting=info['reward_accounting'])
                record['steps']+=1;record['reward_observed']+=reward
                if term or trunc:
                    record.update(status='terminated' if term else 'truncated',
                        reward_complete=record['reward_observed'] if term else None,
                        victory=info['task_outcome']=='victory' if term else None,
                        exit_hp=nxt['player']['hp']/nxt['player']['max_hp'],reason=info['termination_reason'])
                else:remaining.append((env,nxt,record))
            active=remaining
    return results


def summarize(results):
    output={}
    for group in ('simple','transition','combo'):
        rows=[r for r in results if r['group']==group]
        complete=[r for r in rows if r['status']=='terminated']
        values=[];errors=[];entropies=[]
        for row in complete:
            values.extend(row['values']);errors.extend(v-row['reward_complete'] for v in row['values']);entropies.extend(row['entropies'])
        output[group]=dict(cases=len(rows),status_counts=dict(Counter(r['status'] for r in rows)),
            win_rate_natural=float(np.mean([r['victory'] for r in complete])) if complete else None,
            return_natural=float(np.mean([r['reward_complete'] for r in complete])) if complete else None,
            exit_hp_natural=float(np.mean([r['exit_hp'] for r in complete])) if complete else None,
            net_hp_natural=float(np.mean([r['reward_accounting']['net_hp_fraction'] for r in complete])) if complete else None,
            potion_uses_natural=float(np.mean([r['potion_uses'] for r in complete])) if complete else None,
            truncation_rate=sum(r['status']=='truncated' for r in rows)/len(rows) if rows else None,
            entropy=float(np.mean(entropies)) if entropies else None,value_mean=float(np.mean(values)) if values else None,
            value_mse=float(np.mean(np.square(errors))) if errors else None,value_bias=float(np.mean(errors)) if errors else None)
    return output


def report(output,state):
    write(output/'run-report.json',state)
    lines=['# A路径受限训练与评估运行记录','',f"状态：{state['status']}；实际耗时{state.get('elapsed_seconds',0):.1f}秒。",'',
        'source-group均匀初态，PPO全局shuffle，无内容配额；未单独执行32k smoke。',
        '报告是固定历史开发库的新配置战斗证据，不是未见run泛化或与旧MLP的架构消融。','',
        '| 初始化 | 真实训练transition | 结束原因 |','|---|---:|---|']
    for g in state.get('initializations',[]):
        lines.append(f"| {g['group']} | {g.get('env_steps',0)} | {g.get('status','运行中')} |")
    lines+=['','逐组回报、胜率、退出HP、药水、截断、entropy和Value见各初始化evaluation-summary.json；所有逐场记录保留。',
            'checkpoint保存活动环境重放与RNG；故障中途快照只作诊断，latest.pt为最近完整更新边界。',
            '尚无模型改进时不冒称学习成功；simple退化不能被混合平均回报上涨抵消。']
    if state.get('error'):lines+=['','故障：'+state['error']]
    (output/'run-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=14400);parser.add_argument('--initializations',type=int,default=3)
    args=parser.parse_args()
    if not 1<=args.seconds<=14400 or not 1<=args.initializations<=3:raise ValueError('超过用户上限')
    output=args.output;output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():raise RuntimeError('已批准本地CUDA入口不可用')
    device='cuda';started=time.monotonic();deadline=started+args.seconds
    state=dict(status='starting',pid=os.getpid(),started_at=datetime.now(timezone.utc).isoformat(),
        reward_contract=reward_contract(),budget_seconds=args.seconds,max_transitions_per_initialization=262144,initializations=[],fingerprint=fingerprint(),
        device=torch.cuda.get_device_name(0),torch_version=torch.__version__)
    write(output/'status.json',state)
    all_cases=cases();write(output/'evaluation-cases.json',all_cases)
    with zipfile.ZipFile(output/'source-snapshot.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in state['fingerprint']:
            if path!='backend':archive.write(ROOT/path,path)
    trainer=None
    try:
        for group in range(args.initializations):
            # 留出最终对照、检查点与报告时间；不足一个完整更新窗口不再启动新初始化。
            if time.monotonic()+600>=deadline:break
            directory=output/f'init-{group}';directory.mkdir()
            trainer=APathTrainer(group=group,device=device)
            initial=APathActorCritic().to(device);initial.load_state_dict(copy.deepcopy(trainer.model.state_dict()))
            trainer.save(directory/'initial.pt')
            run=dict(group=group,status='training',env_steps=0);state['initializations'].append(run)
            remaining_groups=args.initializations-group
            stage_end=min(deadline-600,time.monotonic()+(deadline-time.monotonic()-600)/remaining_groups)
            metrics_path=directory/'metrics.jsonl';episodes_path=directory/'episodes.jsonl'
            last_duration=0.
            while trainer.env_steps<262144 and time.monotonic()+max(30,last_duration*2)<stage_end-150:
                iteration_start=time.monotonic()
                metrics,episodes=trainer.iteration_step(deadline-120)
                last_duration=time.monotonic()-iteration_start
                metrics['peak_gpu_memory_bytes']=torch.cuda.max_memory_allocated()
                with metrics_path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(metrics,ensure_ascii=False,allow_nan=False)+'\n')
                with episodes_path.open('a',encoding='utf-8') as stream:
                    for episode in episodes:stream.write(json.dumps(episode,ensure_ascii=False,allow_nan=False)+'\n')
                run['env_steps']=trainer.env_steps
                state.update(status='training',active_initialization=group,iteration=trainer.iteration,
                    active_env_steps=trainer.env_steps,elapsed_seconds=time.monotonic()-started,last_metrics=metrics)
                if trainer.iteration==1 or trainer.iteration%8==0:trainer.save(directory/'latest.pt')
                write(output/'status.json',state)
                print(json.dumps({'group':group,'steps':trainer.env_steps,'seconds':round(state['elapsed_seconds'],1)},ensure_ascii=False),flush=True)
            trainer.save(directory/'final.pt')
            run['status']='step_limit' if trainer.env_steps==262144 else 'allocated_time_limit'
            state['status']='evaluating';write(output/'status.json',state)
            before=evaluate(initial,'a-path',all_cases,device,deadline-90)
            write(directory/'initial-evaluation.json',before)
            after=evaluate(trainer.model,'a-path',all_cases,device,deadline-60)
            write(directory/'final-evaluation.json',after)
            summary={'initial':summarize(before),'final':summarize(after),'scope':'全部初始化、两阶段随机策略、历史开发配置；分组单独判定'}
            write(directory/'evaluation-summary.json',summary);run['evaluation']=summary
            del initial
            state['elapsed_seconds']=time.monotonic()-started;report(output,state)
        if time.monotonic()+180<deadline:
            random_results=evaluate(None,'random',all_cases,device,deadline-60)
            write(output/'random-evaluation.json',random_results)
            state['random_summary']=summarize(random_results)
        if time.monotonic()+90<deadline:
            rule_results=evaluate(None,'rule',all_cases,device,deadline-30)
            write(output/'rule-common-slice-evaluation.json',rule_results)
            state['rule_summary']=summarize(rule_results)
        state['status']='completed_within_limits'
    except TimeoutError as error:
        state.update(status='time_limit',error=str(error))
        if trainer is not None:
            state['initializations'][-1].update(env_steps=trainer.env_steps,phase=trainer.phase)
            trainer.save(output/'time-limit-snapshot.pt')
    except Exception as error:
        state.update(status='failed',error=repr(error),traceback=traceback.format_exc())
        if trainer is not None:
            state['initializations'][-1].update(env_steps=trainer.env_steps,phase=trainer.phase)
            try:trainer.save(output/'failure-snapshot.pt')
            except Exception:state['checkpoint_error']=traceback.format_exc()
    finally:
        state['elapsed_seconds']=time.monotonic()-started
        state['total_real_training_transitions']=sum(r.get('env_steps',0) for r in state['initializations'])
        report(output,state);write(output/'status.json',state)
    if state['status']=='failed':raise RuntimeError(state['error'])


if __name__=='__main__':main()
