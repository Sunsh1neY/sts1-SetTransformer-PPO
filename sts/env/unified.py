"""统一实体开发环境：完整变长观测，沿用公共后端512动作外部切段。"""
from sts.env.comparison import card_count, load_contract as comparison_contract
from sts.env.public_battle import PublicBattleEnv


def load_contract():
    old = comparison_contract()
    return {'schema': 'unified-battle-v1', 'encoding': 'unified-entity-v1',
            'model': 'unified-sab4-64-h4-preln-v1', 'max_actions': 512,
            'termination_rule_version': 'battle-natural-with-external-action-budget-v1',
            'content_batch_sha256': old['batch_sha256'], 'initial_cards': old['initial_cards'],
            'public_contract_sha256': old['public_contract_sha256'], 'model_card_capacity': None}


class UnifiedEnv:
    def __init__(self):
        self.env = PublicBattleEnv(max_actions=512)

    def reset(self, scene, seed, purpose='development'):
        if len(scene['candidate']['deck']) > load_contract()['initial_cards']:
            raise ValueError('本轮初始卡组超出已冻结真实批次')
        return self.env.reset(scene, seed, purpose=purpose)

    def step(self, action):
        obs, reward, done, truncated, info = self.env.step(action)
        info.update(environment_version='unified-battle-v1', task_spec_id='unified-battle-v1',
                    card_entities=card_count(obs))
        return obs, reward, done, truncated, info
