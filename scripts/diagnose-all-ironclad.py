"""75类150版本的受控随机/规则采集；不用于正式训练成绩。"""
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from sts.env.public_battle import load_scene_manifest
from sts.env.entitycollection import UnifiedEntityCollectionEnv
from sts.env.entities import encode_observation


def run(output):
    if output.exists():raise FileExistsError(output)
    _,scenes=load_scene_manifest()
    versions=json.loads((ROOT/'sts/env/ironclad-expansion-coverage.json').read_text(encoding='utf-8'))['versions']
    records=[]
    for index,row in enumerate(versions):
        for policy in ['random','rule']:
            candidate=copy.deepcopy(scenes[0]['candidate'])
            candidate.update(ascension=20,act=1,encounter='JAW_WORM' if policy=='random' else 'EXORDIUM_THUGS',burning_elite=False)
            candidate['player'].update(hp=75,max_hp=75);candidate['relics']=[];candidate['potions']=[None,None]
            name=row['name']+('+1' if row['upgrade_count'] else '')
            candidate['deck']=[name]*2+['Strike_R']*4+['Defend_R']*3
            seed=987000+index*2+(policy=='rule');rng=np.random.default_rng(seed)
            record=dict(name=row['name'],upgrade=row['upgrade_count'],policy=policy,seed=seed)
            try:
                env=UnifiedEntityCollectionEnv(max_actions=128);obs=env.reset(candidate,seed,diagnostic=True)
                selections=0
                for step in range(128):
                    sample=encode_observation(obs);legal=[i for i,c in enumerate(sample.candidates) if c.legal]
                    if policy=='random':i=int(rng.choice(legal))
                    else:
                        # 可复核简规则：优先具名被测牌，再攻击，再其他牌，最后结束回合。
                        def score(i):
                            route=sample.routes[i]
                            if isinstance(route,dict):return 1
                            if route==50:return -1
                            card=obs['hand'][route//5]
                            return 100*(card['name']==row['name'])+card['damage']+card['block']*.2
                        i=max(legal,key=score)
                    selections+=sample.candidates[i].kind=='SELECT_CARD'
                    obs,reward,terminated,truncated,info=env.step(sample.routes[i])
                    if terminated or truncated:break
                record.update(steps=step+1,selections=selections,reward=reward,terminated=terminated,truncated=truncated)
            except Exception as error:record['error']=repr(error)
            records.append(record)
    report=dict(engineering_only=True,games=len(records),transitions=sum(x.get('steps',0) for x in records),
                terminated=sum(x.get('terminated',False) for x in records),truncated=sum(x.get('truncated',False) for x in records),
                selections=sum(x.get('selections',0) for x in records),exceptions=sum('error' in x for x in records),records=records)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='records'}))
    for record in records:
        if 'error' in record:print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
