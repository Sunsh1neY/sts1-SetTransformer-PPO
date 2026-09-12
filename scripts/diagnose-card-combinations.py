"""具名组合在五个当前遭遇中的工程采集，不用于策略排名。"""
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from sts.env.public_battle import load_scene_manifest
from sts.env.entitycollection import UnifiedEntityCollectionEnv
from sts.env.entities import encode_observation

DECKS=[
 ['Corruption','Dark Embrace','Feel No Pain','Second Wind','Fiend Fire','Sentinel','Power Through'],
 ['Evolve','Fire Breathing','Power Through','Wild Strike','Reckless Charge','Offering','Burning Pact'],
 ['Double Tap','Havoc','Headbutt','Warcry','True Grit','Armaments','Infernal Blade'],
 ['Rampage','Dual Wield','Double Tap','Headbutt','Pommel Strike','Battle Trance','Exhume'],
 ['Rupture','Brutality','Combust','Bloodletting','Hemokinesis','Blood for Blood','Offering'],
 ['Barricade','Entrench','Juggernaut','Metallicize','Rage','Iron Wave','Body Slam'],
 ['Whirlwind','Seeing Red','Berserk','Bloodletting','Double Tap','Disarm','Shockwave'],
 ['Anger','Perfected Strike','Twin Strike','Pommel Strike','Wild Strike','Dual Wield','Feed'],
 ['Fiend Fire','Exhume','Dark Embrace','Feel No Pain','Sentinel','Second Wind','Sever Soul'],
 ['Armaments','Searing Blow','Warcry','Headbutt','Infernal Blade','Havoc','Reaper']]
ENCOUNTERS=['JAW_WORM','EXORDIUM_THUGS','GREMLIN_NOB','LAGAVULIN','THREE_SENTRIES']


def run(output):
    if output.exists():raise FileExistsError(output)
    _,scenes=load_scene_manifest();records=[]
    for deck_index,deck in enumerate(DECKS):
        for encounter_index,encounter in enumerate(ENCOUNTERS):
            candidate=copy.deepcopy(scenes[0]['candidate'])
            candidate.update(ascension=20,act=1,encounter=encounter,burning_elite=False)
            candidate['player'].update(hp=75,max_hp=75);candidate['relics']=[];candidate['potions']=[None,None]
            candidate['deck']=[name+('+1' if encounter_index%2 else '') for name in deck]+['Strike_R']*2+['Defend_R']*2
            seed=988000+deck_index*5+encounter_index;rng=np.random.default_rng(seed)
            record=dict(deck=deck_index,encounter=encounter,seed=seed)
            try:
                env=UnifiedEntityCollectionEnv(max_actions=128);obs=env.reset(candidate,seed,diagnostic=True);selections=0
                for step in range(128):
                    sample=encode_observation(obs);legal=[i for i,c in enumerate(sample.candidates) if c.legal]
                    plays=[i for i in legal if sample.candidates[i].kind!='END_TURN']
                    i=int(rng.choice(plays or legal));selections+=sample.candidates[i].kind=='SELECT_CARD'
                    obs,reward,terminated,truncated,info=env.step(sample.routes[i])
                    if terminated or truncated:break
                record.update(steps=step+1,reward=reward,terminated=terminated,truncated=truncated,selections=selections)
            except Exception as error:record['error']=repr(error)
            records.append(record)
    report=dict(games=len(records),transitions=sum(x.get('steps',0) for x in records),
                terminated=sum(x.get('terminated',False) for x in records),truncated=sum(x.get('truncated',False) for x in records),
                selections=sum(x.get('selections',0) for x in records),exceptions=sum('error' in x for x in records),records=records)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='records'}))
    for record in records:
        if 'error' in record:print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
