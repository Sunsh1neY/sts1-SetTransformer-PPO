"""全75战士牌基础/升级版与三个新敌人的短程集成；人工策略，不是训练。"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sts.env.ironclad import IroncladEnv,REGISTRY,CONTRACT_HASH,CONTRACT
from sts.env.entities import encode_observation


def run(output,act2=False):
    if output.exists():raise FileExistsError(output)
    cards=[c['name'] for c in REGISTRY['cards'] if c['name'] not in {'Wound','Dazed','Burn','Slimed','AscendersBane'}]
    assert len(cards)==75
    records=[]
    encounters=[x for x in CONTRACT['scope']['encounters'] if x not in {'JAW_WORM','EXORDIUM_THUGS','GREMLIN_NOB','LAGAVULIN','THREE_SENTRIES','MAW','TRANSIENT'}] if act2 else ['MAW','TRANSIENT','SNECKO']
    for encounter in encounters:
        for name in cards:
            for upgrade in [0,1]:
                seed=870000+len(records);rng=np.random.default_rng(seed)
                scene=dict(entry_timing='pre_combat_initialization',initialization_phase='before_destination_room_entry',
                  act=3 if encounter in {'MAW','TRANSIENT'} else 2,floor=46 if encounter in {'MAW','TRANSIENT'} else 34 if encounter in {'AUTOMATON','COLLECTOR','CHAMP'} else 29,
                  character='IRONCLAD',ascension=20,player=dict(hp=80,max_hp=80,gold=0),
                  deck=[name+('+1' if upgrade else '')]*2+['Strike_R']*3+['Defend_R']*3+['Bash','Seeing Red'],
                  relics=[],potions=[None,None],encounter=encounter,burning_elite=False)
                record=dict(encounter=encounter,card=name,upgrade=upgrade,seed=seed,steps=0,selections=0)
                try:
                    env=IroncladEnv(32);obs=env.reset(scene,seed,diagnostic=True)
                    for _ in range(32):
                        sample=encode_observation(obs)
                        indices=[i for i,c in enumerate(sample.candidates) if c.legal]
                        if obs['decision']['phase']=='SELECT_CARD':record['selections']+=1
                        index=int(rng.choice(indices));obs,reward,term,trunc,info=env.step(sample.routes[index]);record['steps']+=1
                        if term or trunc:
                            encode_observation(obs)
                            record.update(terminated=term,truncated=trunc,reward=reward);break
                    else:raise RuntimeError('预算内未停止')
                except Exception as error:
                    record['error']=type(error).__name__+': '+str(error)
                records.append(record)
    summary=dict(episodes=len(records),transitions=sum(r['steps'] for r in records),selections=sum(r['selections'] for r in records),
      terminated=sum(r.get('terminated',False) for r in records),truncated=sum(r.get('truncated',False) for r in records),errors=sum('error' in r for r in records))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(dict(schema='enemy-full-card-diagnostic-v1',contract_hash=CONTRACT_HASH,summary=summary,records=records),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary));print('sha256='+hashlib.sha256(output.read_bytes()).hexdigest())
    if summary['errors']:raise SystemExit(1)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument("--act2",action="store_true")
    args=parser.parse_args();run(args.output,args.act2)
