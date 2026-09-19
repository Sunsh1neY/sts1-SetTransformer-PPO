"""Pinned A-v2 admission for the explicitly authorized bounded training smoke."""
import copy
import hashlib
import json
import uuid
from collections import defaultdict
from pathlib import Path

from sts.env.apath import canonical, load_pool
from sts.env.relics import RelicEnv
from sts.env.full_card_public import PublicBattleEnv
from sts.env.relic_state import validate_initial_relics, relic_features, DIMENSION, REGISTRY, REGISTRY_HASH
from sts.env.relic_card_state import card_features_v3, DIMENSION as CARD_DIM
from sts.env.entities import encode_observation, FEATURE_DIMS
from sts.battle_reward_v2 import BattleRewardV2, contract as reward_contract

POLICY = 'a-v2-natural-augmentation-half-component-uniform-v1'
PINNED_MANIFEST = 'c8806edb5cf6361de5673baecfb6c0650abdef81ad6165a0268a0653d2f1ea06'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ACorpus:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        if digest(self.directory/'manifest.json') != PINNED_MANIFEST:
            raise ValueError('Unapproved A-v2 manifest fingerprint')
        manifest = json.loads((self.directory/'manifest.json').read_bytes())
        for relative, expected in manifest['files'].items():
            if digest(self.directory/relative) != expected['sha256']:
                raise ValueError('A-v2 artifact fingerprint mismatch: '+relative)
        self.rows = {}
        partitions = defaultdict(set)
        self.groups = {k: defaultdict(list) for k in ('natural','augmentation')}
        for row in map(json.loads, (self.directory/'states.jsonl').read_bytes().splitlines()):
            key = row['state_hash']
            if hashlib.sha256(canonical({'schema':row['schema'],'state':row['state']})).hexdigest() != key:
                raise ValueError('Canonical state identity mismatch')
            if key in self.rows:
                raise ValueError('Duplicate state identity')
            self.rows[key] = row
            component, split = row['provenance']['component'], row['provenance']['partition']
            partitions[component].add(split)
            if split == 'audit-train':
                kind = 'augmentation' if 'augmentation' in row['evidence'] else 'natural'
                self.groups[kind][component].append(key)
        if any(len(v)!=1 for v in partitions.values()) or len(self.rows)!=1715:
            raise ValueError('Corpus split/count integrity failure')
        if any(not groups for groups in self.groups.values()):
            raise ValueError('Empty training stratum')
        for groups in self.groups.values():
            for values in groups.values():
                values.sort()

    def scene(self, key):
        row = self.rows[key]
        kind = 'augmentation' if 'augmentation' in row['evidence'] else 'natural'
        return copy.deepcopy(dict(source_admission_policy=POLICY, corpus_manifest_sha256=PINNED_MANIFEST,
            content_id=key, component_id=row['provenance']['component'], split=row['provenance']['partition'],
            content_group=kind, condition=kind, encounter=row['state']['encounter'],
            candidate=row['state'], candidate_sha256=digest_bytes(row['state'])))

    def sample(self, rng):
        kind = ('natural','augmentation')[int(rng.integers(2))]
        components = sorted(self.groups[kind])
        component = components[int(rng.integers(len(components)))]
        states = self.groups[kind][component]
        return self.scene(states[int(rng.integers(len(states)))])


def digest_bytes(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class ACorpusSmokeEnv(RelicEnv):
    """Train-purpose reset with exact frozen admission; no diagnostic bypass."""
    def __init__(self, corpus, max_actions=512, scope='smoke-only'):
        if scope not in ('smoke-only','experiment-protocol-v1'):
            raise ValueError('Unknown corpus admission scope')
        self.admission_scope = scope
        self.corpus = corpus
        super().__init__(max_actions=max_actions)

    def reset(self, registered, seed, *, purpose='train'):
        self._finished = True
        if purpose not in ('train','evaluation') or registered.get('content_id') not in self.corpus.rows:
            raise ValueError('Only registered smoke training states are admitted')
        expected = self.corpus.scene(registered['content_id'])
        allowed = ('audit-train',) if purpose=='train' else ('audit-dev','audit-holdout')
        if purpose=='evaluation' and self.admission_scope!='experiment-protocol-v1':
            raise ValueError('Smoke does not admit evaluation cases')
        if registered != expected or expected['split'] not in allowed:
            raise ValueError('Altered state or non-training split')
        scene = registered['candidate']
        validate_initial_relics(scene['relics'])
        self._selection.invalidate()
        self._snapshot = uuid.uuid4().hex
        envelope = dict(registered, content_admission_status='accepted', content_blockers=[],
                        scene_id=registered['content_id'], group_id=registered['component_id'],
                        research_split=registered['split'])
        obs = PublicBattleEnv.reset(self, envelope, seed, diagnostic=False, purpose=purpose)
        count = len(encode_observation(obs, relic_encoder=relic_features, card_encoder=card_features_v3,
                    feature_dims={**FEATURE_DIMS,'RELIC':DIMENSION,'CARD':CARD_DIM}).tokens)
        if count >= load_pool()['resources']['truncate_at_entities']:
            self._finished = True
            raise ValueError('Corpus state exceeds startup capacity')
        self._allocated = self._env.allocated_card_count()
        self._reward_v2 = BattleRewardV2(scene['player'],obs['potions'])
        self._context.update(source_admission_policy=POLICY, scene_kind='registered-a-v2',
            admission_scope=self.admission_scope, training_admitted=purpose=='train', formal_training_pool_admitted=False,
            corpus_manifest_sha256=PINNED_MANIFEST, reward_contract=reward_contract(),
            reward_version=reward_contract()['reward_version'], alpha_hp=1., victory_bonus=2., potion_use_cost=.05,
            observation_schema=obs['schema'], relic_state_schema=REGISTRY['schema'], relic_registry_hash=REGISTRY_HASH)
        return obs
