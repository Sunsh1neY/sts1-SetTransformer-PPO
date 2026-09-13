"""第一幕独立诊断；保留截断与异常，不作为PPO或真实分布证据。"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import hashlib
import json
import numpy as np
from sts.env.enemy_potion import EnemyPotionBattleEnv, PUBLIC_CONTRACT


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='reference/enemy-potion-diagnostic.json')
    args=parser.parse_args()
    results=[]
    for asc in (0,20):
        for encounter in PUBLIC_CONTRACT['encounters'][:20]:
            for variant in range(3):
                seed=840000+len(results)
                potion=['Blood Potion','Fire Potion','FairyPotion'][variant]
                scene=dict(entry_timing='pre_combat_initialization',initialization_phase='before_destination_room_entry',
                    act=1,floor=17 if encounter in ('HEXAGHOST','SLIME_BOSS','THE_GUARDIAN') else 8,
                    character='IRONCLAD',ascension=asc,player=dict(hp=80,max_hp=80,gold=0),
                    deck=['Strike_R']*4+['Defend_R']*4+['Bash','Bludgeon','Power Through','Cleave'],
                    relics=[],potions=[potion]+[None]*(1 if asc>=11 else 2),encounter=encounter,burning_elite=False)
                row=dict(seed=seed,ascension=asc,encounter=encounter,potion=potion,actions=[],status='incomplete',max_entities=0,max_entity_growth=0)
                try:
                    env=EnemyPotionBattleEnv(128);obs=env.reset(scene,seed,diagnostic=True)
                    rng=np.random.default_rng(seed)
                    for _ in range(128):
                        count=lambda o:sum(len(o[k]) for k in ('hand','draw_pile','discard_pile','exhaust_pile'))
                        before=count(obs)
                        action=int(rng.choice(np.flatnonzero(obs['action_mask'])))
                        row['actions'].append(action)
                        obs,reward,term,trunc,info=env.step(action)
                        row['max_entities']=max(row['max_entities'],count(obs))
                        row['max_entity_growth']=max(row['max_entity_growth'],count(obs)-before)
                        if term or trunc:
                            row.update(status='truncated' if trunc else 'victory' if reward else 'defeat',reward=reward if term else None,final_hp=obs['player']['hp'])
                            break
                except Exception as exc:
                    row.update(status='error',error=repr(exc))
                results.append(row)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    summary={s:sum(r['status']==s for r in results) for s in ['victory','defeat','truncated','error','incomplete']}
    report=dict(schema='enemy-potion-diagnostic-v1',synthetic_scenes=True,training=False,summary=summary,
        contract_sha256=hashlib.sha256(Path('sts/env/enemy-potion-contract.json').read_bytes()).hexdigest(),results=results)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary)); print(out.resolve())
    return 1 if summary['error'] or summary['incomplete'] else 0


if __name__=='__main__':raise SystemExit(main())
