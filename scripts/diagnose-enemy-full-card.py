"""全75战士牌基础/升级版的分幕遭遇诊断；随机合法策略，不是训练。"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sts.env.ironclad import IroncladEnv,REGISTRY,CONTRACT_HASH,CONTRACT
from sts.env.entities import encode_observation


def run(output,act2=False,act1=False,act12=False):
    if output.exists():raise FileExistsError(output)
    cards=[c['name'] for c in REGISTRY['cards'] if c['name'] not in {'Wound','Dazed','Burn','Slimed','AscendersBane'}]
    assert len(cards)==75
    records=[]
    encounter_acts=CONTRACT['scope']['encounter_acts']
    acts={1,2} if act12 else {1} if act1 else {2} if act2 else set()
    encounters=[x for x in CONTRACT['scope']['encounters'] if encounter_acts[x] in acts] if acts else ['MAW','TRANSIENT','SNECKO']
    bosses={'SLIME_BOSS','THE_GUARDIAN','HEXAGHOST','AUTOMATON','COLLECTOR','CHAMP'}
    for encounter in encounters:
        for name in cards:
            for upgrade in [0,1]:
                seed=870000+len(records);rng=np.random.default_rng(seed)
                scene=dict(entry_timing='pre_combat_initialization',initialization_phase='before_destination_room_entry',
                  act=encounter_acts[encounter],floor=17*encounter_acts[encounter] if encounter in bosses else 8+17*(encounter_acts[encounter]-1),
                  character='IRONCLAD',ascension=20,player=dict(hp=80,max_hp=80,gold=0),
                  deck=[name+('+1' if upgrade else '')]*2+['Strike_R']*3+['Defend_R']*3+['Bash','Seeing Red'],
                  relics=[],potions=[None,None],encounter=encounter,burning_elite=False)
                record=dict(encounter=encounter,act=encounter_acts[encounter],card=name,upgrade=upgrade,seed=seed,steps=0,selections=0,tested_card_plays=0)
                try:
                    env=IroncladEnv(32);obs=env.reset(scene,seed,diagnostic=True)
                    for _ in range(32):
                        sample=encode_observation(obs)
                        indices=[i for i,c in enumerate(sample.candidates) if c.legal]
                        if obs['decision']['phase']=='SELECT_CARD':record['selections']+=1
                        index=int(rng.choice(indices));route=sample.routes[index]
                        if route.get('kind')=='NORMAL' and route['action']<50:
                            card=obs['hand'][route['action']//5]
                            if card['name']==name and card['upgrade_count']==upgrade:record['tested_card_plays']+=1
                        obs,reward,term,trunc,info=env.step(route);record['steps']+=1
                        if term or trunc:
                            encode_observation(obs)
                            assert not (term and trunc)
                            assert ('battle_exit' in info)==term
                            if term:assert not any(e['present'] for e in obs['enemies'])
                            record.update(terminated=term,truncated=trunc,reward=reward);break
                    else:raise RuntimeError('预算内未停止')
                except Exception as error:
                    record['error']=type(error).__name__+': '+str(error)
                records.append(record)
        print(json.dumps(dict(encounter=encounter,completed=len(records),errors=sum('error' in r for r in records))),flush=True)
    summary=dict(episodes=len(records),transitions=sum(r['steps'] for r in records),selections=sum(r['selections'] for r in records),
      terminated=sum(r.get('terminated',False) for r in records),truncated=sum(r.get('truncated',False) for r in records),errors=sum('error' in r for r in records),
      tested_card_played_episodes=sum(r['tested_card_plays']>0 for r in records))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(dict(schema='enemy-full-card-diagnostic-v1',contract_hash=CONTRACT_HASH,summary=summary,records=records),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary));print('sha256='+hashlib.sha256(output.read_bytes()).hexdigest())
    if summary['errors']:raise SystemExit(1)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    group=parser.add_mutually_exclusive_group()
    group.add_argument("--act2",action="store_true")
    group.add_argument("--act1",action="store_true")
    group.add_argument("--act12",action="store_true")
    args=parser.parse_args();run(args.output,args.act2,args.act1,args.act12)
