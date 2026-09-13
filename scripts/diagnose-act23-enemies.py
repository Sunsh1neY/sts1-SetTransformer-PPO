"""第二/三幕13遭遇多seed诊断；空药水，合成卡组，不训练。"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hashlib,json
import numpy as np
from sts.env.enemy_potion import EnemyPotionBattleEnv,PUBLIC_CONTRACT
from sts.env.enemy_potion_entities import EnemyPotionEntityView


def main():
    rows=[]
    for name in PUBLIC_CONTRACT['encounters']:
        act=PUBLIC_CONTRACT['encounter_acts'][name]
        if act==1:continue
        for asc in (0,20):
            for seed in range(860000,860006):
                for policy in ('random','attack_first'):
                    scene=dict(entry_timing='pre_combat_initialization',initialization_phase='before_destination_room_entry',
                        act=act,floor=act*17-5,character='IRONCLAD',ascension=asc,player=dict(hp=80,max_hp=80,gold=0),
                        deck=['Strike_R']*4+['Defend_R']*4+['Bash','Bludgeon','Power Through','Cleave'],relics=[],
                        potions=[None]*(2 if asc>=11 else 3),encounter=name,burning_elite=False)
                    row=dict(encounter=name,ascension=asc,seed=seed,policy=policy,actions=[],status='incomplete',max_entities=0)
                    try:
                        env=EnemyPotionBattleEnv(128);obs=env.reset(scene,seed,diagnostic=True)
                        view=EnemyPotionEntityView();view.reset();rng=np.random.default_rng(seed)
                        for _ in range(128):
                            view.update(obs)
                            legal=np.flatnonzero(obs['action_mask'])
                            attacks=[int(a) for a in legal if a<50 and obs['hand'][a//5]['card_type']=='ATTACK']
                            action=attacks[0] if policy=='attack_first' and attacks else int(rng.choice(legal))
                            row['actions'].append(action)
                            obs,reward,term,trunc,info=env.step(action)
                            view.update(obs)
                            row['max_entities']=max(row['max_entities'],sum(len(obs[k]) for k in ['hand','draw_pile','discard_pile','exhaust_pile']))
                            if term or trunc:
                                row.update(status='truncated' if trunc else 'victory' if reward else 'defeat',reward=None if trunc else reward)
                                break
                    except Exception as exc:row.update(status='error',error=repr(exc))
                    rows.append(row)
    summary={s:sum(r['status']==s for r in rows) for s in ['victory','defeat','truncated','error','incomplete']}
    root=Path(__file__).resolve().parents[1]
    report=dict(schema='act23-enemy-diagnostic-v1',synthetic=True,summary=summary,transitions=sum(len(r['actions']) for r in rows),
                contract_sha256=hashlib.sha256((root/'sts/env/enemy-potion-contract.json').read_bytes()).hexdigest(),results=rows)
    (root/'reference/act23-enemy-diagnostic.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(episodes=len(rows),summary=summary,transitions=report['transitions'])))
    return 1 if summary['error'] or summary['incomplete'] else 0


if __name__=='__main__':raise SystemExit(main())
