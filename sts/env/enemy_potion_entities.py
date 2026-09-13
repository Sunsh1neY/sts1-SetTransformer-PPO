"""敌人/药水的变长实体交接视图；不实现模型、卡牌候选或批次编码。"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from sts.env.enemy_potion import _reject_hidden_fields


class EnemyPotionEntityView:
    """引用仅作路由；features才可进入共享实体编码器。"""

    def __init__(self) -> None:
        self._epoch = 0
        self._revision = 0
        self._identities: dict[tuple[str, int], tuple[str, int]] = {}
        self._generations: dict[tuple[str, int], int] = {}
        self._routes: dict[tuple[str, str | None], int] = {}

    def reset(self) -> None:
        """每次环境reset后调用；跨战斗旧引用必失效。"""
        self._epoch += 1
        self._identities.clear()
        self._generations.clear()
        self._routes.clear()
        self._revision += 1

    def _reference(self, kind: str, slot: int, name: str) -> str:
        key = (kind, slot)
        previous = self._identities.get(key)
        if previous is None or previous[0] != name:
            self._generations[key] = self._generations.get(key, 0) + 1
        generation = self._generations[key]
        self._identities[key] = (name, generation)
        return f'{kind}:{self._epoch}:{slot}:{generation}'

    def update(self, observation: dict[str, Any]) -> dict[str, Any]:
        """当前无召唤/复活批次：死亡敌人/空药水不输出有效实体。"""
        if observation.get('schema') != 'enemy-potion-observation-v3':
            raise ValueError('实体视图schema不匹配')
        _reject_hidden_fields(observation)
        self._revision += 1
        self._routes.clear()
        enemies, potions, targets, slots = [], [], {}, {}
        active = set()
        for slot, enemy in enumerate(observation['enemies']):
            if not enemy['present'] or not enemy['targetable']:
                continue
            key = ('enemy', slot)
            active.add(key)
            reference = self._reference(*key, enemy['name'])
            targets[slot] = reference
            features = {k: deepcopy(enemy[k]) for k in (
                'name', 'hp', 'max_hp', 'block', 'intent_kind', 'intent_damage',
                'intent_hits', 'statuses', 'public_history', 'intent_history', 'intent_history_valid')}
            enemies.append(dict(entity_type='enemy', reference=reference, features=features))
        for slot, potion in enumerate(observation['potions']):
            if not potion['present']:
                continue
            key = ('potion', slot)
            active.add(key)
            reference = self._reference(*key, potion['name'])
            slots[slot] = reference
            features = {k: deepcopy(potion[k]) for k in ('name', 'potency', 'target_kind')}
            features['activation'] = 'passive_on_lethal_damage' if potion['name'] == 'FairyPotion' else 'active'
            features['potency_unit'] = 'percent_max_hp' if potion['name'] in ('Blood Potion', 'FairyPotion') else 'effect_amount'
            potions.append(dict(entity_type='potion', reference=reference, features=features))
        self._identities = {k: v for k, v in self._identities.items() if k in active}
        legal = []
        for slot, source in slots.items():
            potion = observation['potions'][slot]
            for target in range(5):
                action = 51 + slot * 5 + target
                if not observation['action_mask'][action]:
                    continue
                target_ref = targets.get(target) if potion['target_kind'] == 'ENEMY' else None
                if potion['target_kind'] == 'ENEMY' and target_ref is None:
                    raise ValueError('合法药水动作引用了无效敌人')
                self._routes[(source, target_ref)] = action
                legal.append(dict(source_reference=source, target_reference=target_ref, action=action))
        return dict(schema='enemy-potion-entities-v2', revision=self._revision,
                    enemy_entities=enemies, potion_entities=potions,
                    routing=dict(enemy_target_references=targets, potion_slot_references=slots,
                                 legal_potion_actions=legal),
                    integration=dict(card_candidates='owned-by-full-card-task',
                                     batching='dynamic-padding-owned-by-shared-encoder',
                                     training_admitted=False))

    def resolve_potion(self, source_reference: str, target_reference: str | None, *, revision: int) -> int:
        """提交动作前校验快照版本与合法引用，不依赖token集合排序。"""
        if revision != self._revision:
            raise ValueError('过期观测引用，必须重新读取合法动作')
        try:
            return self._routes[(source_reference, target_reference)]
        except KeyError as exc:
            raise ValueError('药水或目标引用已失效/动作不合法') from exc
