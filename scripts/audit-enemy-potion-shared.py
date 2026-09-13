"""只读审计共享统一实体接口，输出主集成增量需求，不修改共享工作区。"""
from pathlib import Path
import argparse
import hashlib
import json


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--shared-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('docs/enemy-potion-shared-handoff.json'))
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    shared_path=args.shared_root/'sts/models/unified-entity-contract.json'
    shared_bytes=shared_path.read_bytes()
    shared=json.loads(shared_bytes)
    local=json.loads((root/'sts/env/enemy-potion-contract.json').read_text(encoding='utf-8'))
    names={p['name'] for p in shared['potions']}
    additions=[p for p in local['potions'] if p['name'] not in names]
    conflicts=[p for p in local['potions'] if p['name'] in names and
               next(q['id'] for q in shared['potions'] if q['name']==p['name'])!=p['id']]
    source=args.shared_root/'sts/env/entities.py'
    report=dict(schema='enemy-potion-shared-handoff-v1',audit_kind='static-read-only',
        shared_contract_schema=shared['schema'],shared_contract_sha256=hashlib.sha256(shared_bytes).hexdigest(),
        shared_encoder_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        append_potions=additions,potion_id_conflicts=conflicts,
        boss_name_gaps=[n for n in ['SLIME_BOSS','THE_GUARDIAN','HEXAGHOST'] if n not in shared['enemy_names']],
        boss_status_gaps=[n for n in ['Mode Shift','Sharp Hide'] if n not in shared['enemy_statuses']],
        required_potion_feature_extension=dict(activation=['active','passive_on_lethal_damage'],potency_unit=['effect_amount','percent_max_hp']),
        selection_kinds_seen=shared['selection_kinds'],
        integration_requirements=[
            '以共享EntitySample/Candidate/routes为统一输出，本分支视图是机制交接材料，不另建编码器',
            '新增5药水词表及activation/potency_unit后同步共享feature_dimensions和checkpoint契约',
            '共享编码器保留present的不可选敌人；本分支视图省略非targetable实体，需统一公开生命周期规则',
            '本分支旧卡牌字段不能补零伪装ironclad-observation-v4；在全卡后端入口合入敌人药水增量后再编码',
            'EXHAUST_ONE单选不代表Elixir/Gamblers多选与确认已实现；继续拒绝这些药水',
            'resolve后选择来源若药水已经消耗，必须提供公开resolving来源，不输出内部队列',
            '按同一真实观测验证实体/候选置换、合法mask、目标路由和全部特征进入共享模型'],
        tensor_integration_verified=False,training_admitted=False)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['append_potions','potion_id_conflicts','boss_name_gaps','boss_status_gaps']},ensure_ascii=False))


if __name__=='__main__':main()
