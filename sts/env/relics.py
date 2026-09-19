"""Explicit relic mechanism diagnostics; no new training-pool admission."""
from sts.env.relic_card_state import card_features_v3, DIMENSION as CARD_V3_DIM
import copy
from types import SimpleNamespace

from sts.battle_reward_v2 import BattleRewardV2, contract as reward_contract
from sts.env.apath import APathEnv, load_pool
from sts.env.entities import encode_observation, FEATURE_DIMS
from sts.env.full_card_public import PublicBattleEnv
from sts.env.ironclad import IroncladEnv, CONTRACT_HASH, REGISTRY_HASH
from sts.env.lightspeed import _load_backend
from sts.env.relic_state import (REGISTRY, REGISTRY_HASH as RELIC_HASH,
                                DIMENSION, relic_features, normalize_relics, validate_initial_relics)
from sts.env.selection import SelectionRouter


class RelicEnv(APathEnv):
    """Reuse A-path reward/steps with strict, development-only relic reset."""

    def __init__(self, max_actions=512):
        module = _load_backend()
        if (getattr(module, 'RELIC_STATE_REGISTRY_SHA256', None) != RELIC_HASH
                or getattr(module, 'IRONCLAD_CONTRACT_SHA256', None) != CONTRACT_HASH
                or getattr(module, 'IRONCLAD_REGISTRY_SHA256', None) != REGISTRY_HASH):
            raise RuntimeError('Rebuild the relic backend: contract fingerprint mismatch')
        self._selection = SelectionRouter()
        PublicBattleEnv.__init__(self, max_actions,
            backend=SimpleNamespace(PublicBattleEnv=module.RelicStateBattleEnv))

    def _normalize_observation(self, raw):
        value = copy.deepcopy(raw)
        relics = normalize_relics(value['relics'])
        # Other entities retain the existing strict normalization and routing.
        value['relics'] = []
        obs = IroncladEnv._normalize_observation(self, value)
        obs['relics'] = relics
        obs['routing']['bound_card_refs'] = {}
        for region in ('hand','draw_pile','discard_pile','exhaust_pile','resolving','stasis'):
            for index, card in enumerate(obs[region]):
                name = card.pop('bottled_by', None)
                if name is None: continue
                if name not in {r['name'] for r in relics}: raise ValueError('Binding refers to an unowned relic')
                ref = f'bound:{region}:{index}'
                obs['routing']['bound_card_refs'][ref] = dict(region=region, index=index)
                obs['relations'].append(dict(kind='bottled_card', relic_name=name, card_ref=ref))
        return obs

    def reset(self, scene, seed, *, diagnostic=False, purpose='development'):
        self._finished = True
        validate_initial_relics(scene.get('relics'))
        if scene.get('act') not in (1, 2):
            raise ValueError('Relic diagnostics are limited to Act 1/2')
        obs = IroncladEnv.reset(self, scene, seed, diagnostic=diagnostic, purpose=purpose)
        if len(encode_observation(obs, relic_encoder=relic_features, card_encoder=card_features_v3,
                feature_dims={**FEATURE_DIMS, 'RELIC': DIMENSION, 'CARD': CARD_V3_DIM}).tokens) >= load_pool()['resources']['truncate_at_entities']:
            self._finished = True
            raise ValueError('Initial relic scene exceeds the entity startup limit')
        self._allocated = self._env.allocated_card_count()
        self._reward_v2 = BattleRewardV2(scene['player'], obs['potions'])
        self._context.update(reward_contract=reward_contract(),
            reward_version=reward_contract()['reward_version'], alpha_hp=1.0,
            victory_bonus=2.0, potion_use_cost=0.05,
            relic_state_schema=REGISTRY['schema'], relic_registry_hash=RELIC_HASH,
            training_admitted=False)
        return obs

    def step(self, action):
        before = self.observation()['relics']
        obs, reward, terminated, truncated, info = super().step(action)
        info.update(relic_state_before=before, relic_state_after=copy.deepcopy(obs['relics']))
        return obs, reward, terminated, truncated, info
