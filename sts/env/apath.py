"""版本化真实卡组配置入口；独立于旧comparison和机制诊断入口。"""
import copy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import uuid
import numpy as np

from sts.battle_reward_v2 import BattleRewardV2, contract as reward_contract

from sts.env.ironclad import IroncladEnv, CONTRACT_HASH, REGISTRY_HASH, CONTRACT as IRONCLAD_CONTRACT, REGISTRY
from sts.env.full_card_public import PublicBattleEnv
from sts.env.entities import encode_observation, CONTRACT as ENTITY_CONTRACT

PATH = Path(__file__).with_name('a-path-training-pool.json')
POLICY = 'a-path-source-group-uniform-v1'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


@lru_cache(maxsize=1)
def load_pool():
    data = json.loads(PATH.read_bytes())
    payload = {k:v for k,v in data.items() if k != 'payload_sha256'}
    if hashlib.sha256(canonical(payload)).hexdigest() != data.get('payload_sha256') or data['schema'] != POLICY:
        raise ValueError('A路径池版本或哈希不一致')
    if data['runtime_contract_hash'] != CONTRACT_HASH or data['registry_hash'] != REGISTRY_HASH:
        raise ValueError('池与扩展运行契约不一致')
    train = {r['component_id'] for r in data['contents'] if r['split']=='train_candidate'}
    dev = {r['component_id'] for r in data['contents'] if r['split']=='development'}
    if train & dev or len({r['content_id'] for r in data['contents']}) != len(data['contents']):
        raise ValueError('来源隔离或内容去重失败')
    return data


def scene(content_id, condition, encounter):
    pool = load_pool()
    row = next((r for r in pool['contents'] if r['content_id']==content_id), None)
    if row is None or condition not in pool['profiles'] or encounter not in pool['encounters']:
        raise ValueError('未登记初态')
    candidate = {**pool['common'], **pool['profiles'][condition], 'deck':row['cards'], 'encounter':encounter}
    return copy.deepcopy(dict(source_admission_policy=POLICY, pool_sha256=pool['payload_sha256'],
        content_id=content_id, component_id=row['component_id'], content_group=row['group'],
        split=row['split'], condition=condition, encounter=encounter,
        candidate=candidate, candidate_sha256=hashlib.sha256(canonical(candidate)).hexdigest()))


def sample_scene(rng, split='train_candidate'):
    pool = load_pool()
    rows = [r for r in pool['contents'] if r['split']==split]
    groups = sorted({r['component_id'] for r in rows})
    group = groups[int(rng.integers(len(groups)))]
    choices = sorted((r for r in rows if r['component_id']==group), key=lambda r:r['content_id'])
    row = choices[int(rng.integers(len(choices)))]
    profiles = sorted(pool['profiles'])
    return scene(row['content_id'], profiles[int(rng.integers(len(profiles)))],
                 pool['encounters'][int(rng.integers(len(pool['encounters'])))])


class APathEnv(IroncladEnv):
    """严格完整注册初态；只在完整决策后执行外部资源截断。"""

    def reset(self, registered, seed, *, purpose='train'):
        expected = scene(registered.get('content_id'), registered.get('condition'), registered.get('encounter'))
        if registered != expected or purpose not in {'train', 'development'}:
            raise ValueError('未注册或被修改的A路径初态/用途')
        if purpose=='train' and registered['split']!='train_candidate':
            raise ValueError('开发来源不能进入训练')
        if purpose=='development' and registered['split']!='development':
            raise ValueError('开发评估只接受开发来源')
        self._finished=True
        self._selection.invalidate()
        self._snapshot=uuid.uuid4().hex
        envelope = {**registered, 'content_admission_status':'accepted', 'content_blockers':[],
                    'scene_id':f"{registered['content_id']}:{registered['condition']}:{registered['encounter']}",
                    'group_id':registered['component_id'], 'research_split':registered['split']}
        # 通过新入口的注册核验后使用正式公开reset，绝不将train包装为diagnostic。
        obs = PublicBattleEnv.reset(self, envelope, seed, diagnostic=False, purpose=purpose)
        limits = load_pool()['resources']
        if len(encode_observation(obs).tokens) >= limits['truncate_at_entities']:
            self._finished=True
            raise ValueError('登记初态已越资源启动边界')
        self._allocated = self._env.allocated_card_count()
        self._context.update(source_admission_policy=POLICY, scene_kind='registered-real-deck-configured',
            contract_id=POLICY, environment_version=POLICY, task_spec_id=POLICY,
            contract_hash=CONTRACT_HASH, registry_hash=REGISTRY_HASH,
            observation_schema=IRONCLAD_CONTRACT['observation_schema'],
            action_schema_version=IRONCLAD_CONTRACT['action_schema'], registry_version=REGISTRY['schema'],
            pool_sha256=load_pool()['payload_sha256'], training_admitted=purpose=='train',
            content_group=registered['content_group'], content_id=registered['content_id'],
            group_id=registered['component_id'], condition=registered['condition'], encounter=registered['encounter'],
            termination_rule_version='a-path-complete-decision-resource-v1')
        self._reward_v2 = BattleRewardV2(registered['candidate']['player'], obs['potions'])
        self._context.update(reward_contract=reward_contract(),
            reward_version=reward_contract()['reward_version'], alpha_hp=1.0,
            victory_bonus=2.0, potion_use_cost=0.05)
        return obs

    def step(self, action):
        # Capture the public potion identity before the backend consumes it.
        selected = action.get('action') if isinstance(action, dict) and action.get('kind') == 'NORMAL' else action
        event = None
        if isinstance(selected, (int, np.integer)) and not isinstance(selected, bool) and 51 <= selected <= 65:
            slot = (int(selected)-51)//5
            before = self.observation()
            potion = before['potions'][slot]
            if not potion['present'] or not before['action_mask'][int(selected)]:
                raise ValueError('Cannot charge an absent or illegal potion action')
            event = dict(slot=slot, name=potion['name'], action=int(selected))
        obs,reward,term,trunc,info=super().step(action)
        try:
            allocated=self._env.allocated_card_count()
            # 真出口可能清理牌区；只对活动状态验证累计分配增长。
            limits=load_pool()['resources']
            if not term and not 0 <= allocated-self._allocated <= limits['max_generated_per_decision']:
                raise RuntimeError('完整动作卡牌分配增长超出原五遭遇容量契约')
            self._allocated=allocated
            count=len(encode_observation(obs).tokens)
            if count>ENTITY_CONTRACT['resources']['max_entities']:
                raise RuntimeError('完整观测超过实体硬边界；不能裁掉实体继续训练')
            if not term and count>=limits['truncate_at_entities']:
                trunc=True; self._finished=True
                info.update(termination_reason='external_entity_capacity', truncation_reason='external_entity_capacity')
            info.update(entity_count=count,allocated_card_count=allocated)
            backend_reward = reward
            reward, reward_info = self._reward_v2.transition(observation=obs,
                terminated=term, truncated=trunc, outcome=info['outcome'], potion_event=event)
            info.update(reward_info, backend_reward_v1=backend_reward)
            if term:
                info['termination_reason'] = info['task_outcome']
            return obs,reward,term,trunc,info
        except Exception:
            self._finished=True
            raise
