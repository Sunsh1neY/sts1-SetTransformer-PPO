"""直接效果十二类逐版本受控随机集成；不是训练或强度评估。"""
import argparse
import copy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from sts.env.public_battle import load_scene_manifest
from sts.env.entitycollection import UnifiedEntityCollectionEnv
from sts.env.entities import encode_observation

NAMES=['Clash','Hemokinesis','Bloodletting','Intimidate','Limit Break','Offering','Shockwave',
       'Feed','Reaper','Sword Boomerang','Second Wind','Sever Soul']


def run(output):
    if output.exists(): raise FileExistsError(output)
    _,scenes=load_scene_manifest();records=[]
    for i,name in enumerate(NAMES):
        for up in [0,1]:
            for repeat in [0,1]:
                candidate=copy.deepcopy(scenes[0]['candidate'])
                candidate.update(ascension=20,act=1,encounter=['JAW_WORM','EXORDIUM_THUGS'][repeat],burning_elite=False)
                candidate['player'].update(hp=75,max_hp=75)
                candidate['potions']=[None,None];candidate['relics']=[]
                candidate['deck']=[name+('+1' if up else '')]*2+['Strike_R']*4+['Defend_R']*3
                seed=983000+i*4+up*2+repeat
                env=UnifiedEntityCollectionEnv(max_actions=128)
                obs=env.reset(candidate,seed,diagnostic=True);rng=np.random.default_rng(seed)
                for step in range(128):
                    sample=encode_observation(obs)
                    legal=[j for j,c in enumerate(sample.candidates) if c.legal]
                    obs,reward,terminated,truncated,info=env.step(sample.routes[int(rng.choice(legal))])
                    if terminated or truncated:break
                else:raise RuntimeError('动作预算未结束')
                records.append(dict(name=name,upgrade=up,seed=seed,steps=step+1,reward=reward,
                                    terminated=terminated,truncated=truncated,reason=info['termination_reason']))
    report=dict(engineering_only=True,games=len(records),transitions=sum(x['steps'] for x in records),
                terminated=sum(x['terminated'] for x in records),truncated=sum(x['truncated'] for x in records),
                exceptions=0,records=records)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='records'}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
