"""规则策略的公开信息边界、评分行为和输入拒绝测试。"""

from copy import deepcopy
import numpy as np
import pytest

from sts.agents.rule_agent import RuleAgent, score_public_actions, validate_public_observation


def card(name="Strike", damage=6, block=0, cost=1, magic=0, hits=1, target="ENEMY"):
    return dict(name=name, card_id=1, upgrade_count=0, cost=cost, cost_known=True,
                target_kind=target, damage=damage, block=block, magic=magic, hits=hits,
                damage_by_target=[damage] * 5)


def observation(cards=None):
    enemies = [dict(present=i == 0, targetable=i == 0, name="Cultist" if i == 0 else "",
                    hp=20 if i == 0 else 0, max_hp=20 if i == 0 else 0, block=0,
                    intent_kind="ATTACK", intent_damage=6 if i == 0 else 0,
                    intent_hits=1 if i == 0 else 0, statuses={}) for i in range(5)]
    hand = cards if cards is not None else [card()]
    mask = np.zeros(66, dtype=np.bool_)
    mask[50] = True
    for i, value in enumerate(hand):
        if value["cost"] >= 0:
            mask[i * 5] = True
    return dict(schema="public-observation-v1", hand=hand, enemies=enemies,
                player=dict(hp=50, max_hp=80, block=0, energy=3, energy_per_turn=3,
                            turn=1, ascension=20, statuses={}),
                potions=[dict(present=False, name="", potency=0, target_kind="NO_TARGET") for _ in range(3)],
                relics=[dict(name="Burning Blood", counter=0)], action_mask=mask,
                draw_pile=[], discard_pile=[], exhaust_pile=[])


def test_纯字典决策不修改输入且概率符合mask():
    obs = observation()
    before = deepcopy(obs)
    decision = RuleAgent().decide(obs)
    assert decision.action == 0
    assert decision.probabilities.sum() == 1
    assert not decision.probabilities[~obs["action_mask"]].any()
    assert np.array_equal(obs.pop("action_mask"), before.pop("action_mask"))
    assert obs == before


def test_只剩结束回合():
    obs = observation([])
    assert RuleAgent().decide(obs).action == 50


def test_确定击杀优先于普通伤害():
    obs = observation([card()])
    obs["enemies"][1] = deepcopy(obs["enemies"][0])
    obs["enemies"][1]["hp"] = 5
    obs["action_mask"][1] = True
    assert RuleAgent().decide(obs).action == 1
    obs["enemies"][1]["block"] = 20
    assert RuleAgent().decide(obs).action == 0


def test_满盾不盲打防御与有伤害时格挡有效():
    obs = observation([card("Defend", damage=0, block=5, target="NO_TARGET")])
    obs["player"]["block"] = 6
    assert RuleAgent().decide(obs).action == 50
    obs["player"]["block"] = 0
    assert RuleAgent().decide(obs).action == 0


def test_伤害预览不重复应用力量易伤():
    obs = observation()
    baseline = score_public_actions(obs)[0]
    obs["player"]["statuses"] = {"Strength": 100, "Weak": 2}
    obs["enemies"][0]["statuses"] = {"Vulnerable": 2}
    assert score_public_actions(obs)[0] == baseline


def test_多敌多段意图累计且不重复乘玩家易伤():
    obs = observation([card("Defend", damage=0, block=20, target="NO_TARGET")])
    obs["enemies"][0]["intent_damage"] = 3
    obs["enemies"][0]["intent_hits"] = 2
    obs["enemies"][1] = deepcopy(obs["enemies"][0])
    obs["player"]["statuses"] = {"Vulnerable": 2}
    assert score_public_actions(obs)[0] == pytest.approx(12 * 1.1 - 0.25)


def test_dropkick条件与禁抽牌():
    obs = observation([card("Dropkick", damage=5)])
    base = score_public_actions(obs)[0]
    obs["enemies"][0]["statuses"] = {"Vulnerable": 1}
    assert score_public_actions(obs)[0] == base + 7
    obs["player"]["statuses"] = {"No Draw": 1}
    assert score_public_actions(obs)[0] == base + 4


def test_随机消耗不窥探结果与牌堆顺序无关():
    obs = observation([card("True Grit", damage=0, block=7, target="NO_TARGET")])
    obs["draw_pile"] = [card(), card("Defend", damage=0, block=5)]
    first = score_public_actions(obs)
    obs["draw_pile"].reverse()
    assert np.array_equal(first, score_public_actions(obs))


def test_手牌置换使唯一最优动作槽位对应迁移():
    obs = observation([card(), card("Bludgeon", damage=32, cost=3)])
    assert RuleAgent().decide(obs).action == 5
    obs["hand"].reverse()
    assert RuleAgent().decide(obs).action == 0


def test_不可打状态牌负费用哨兵合法但不能开放动作():
    obs = observation([card("Wound", damage=0, cost=-2, target="NO_TARGET")])
    assert RuleAgent().decide(obs).action == 50
    obs["action_mask"][0] = True
    with pytest.raises(ValueError, match="负费用"):
        RuleAgent().decide(obs)


@pytest.mark.parametrize("mutation", [
    lambda x: x.update(schema="future-schema"),
    lambda x: x["hand"][0].update(name="UnknownCard"),
    lambda x: x["hand"][0].update(cost_known=False),
    lambda x: x["hand"][0].update(damage_by_target=[1]),
    lambda x: x["hand"][0].update(name="True Grit", upgrade_count=1),
    lambda x: x["player"].pop("statuses"),
    lambda x: x["relics"][0].update(name="UnknownRelic"),
    lambda x: x["action_mask"].fill(False),
    lambda x: x["action_mask"].__setitem__(49, True),
])
def test_未知协议残缺必要字段整输入拒绝(mutation):
    obs = observation()
    mutation(obs)
    with pytest.raises((ValueError, KeyError)):
        RuleAgent().decide(obs)


def test_药水空槽与目标合法性():
    obs = observation([])
    obs["action_mask"][51] = True
    with pytest.raises(ValueError, match="空药水"):
        RuleAgent().decide(obs)
    obs["potions"][0] = dict(present=True, name="Block Potion", potency=12, target_kind="NO_TARGET")
    assert RuleAgent().decide(obs).action == 51
    obs["player"]["block"] = 20
    assert RuleAgent().decide(obs).action == 50


def test_全部十五类药水有显式评分分支():
    from sts.agents.rule_agent import POTION_NAMES
    for name in POTION_NAMES:
        obs = observation([])
        obs["potions"][0] = dict(present=True, name=name, potency=3,
                                   target_kind="ENEMY" if name in ("fearpotion", "weakpotion") else "NO_TARGET")
        obs["action_mask"][51] = True
        assert np.isfinite(score_public_actions(obs)[51])


def test_无法访问env_info或隐藏字段():
    class VisibleOnly(dict):
        def __getitem__(self, key):
            assert key not in ("env", "info", "seed", "rng", "source_run_group", "moveHistory")
            return super().__getitem__(key)
    obs = VisibleOnly(observation())
    assert RuleAgent().decide(obs).action == 0


def test_中央八遗物无适用计数允许null():
    from sts.agents.rule_agent import _CONTRACT, RELIC_NAMES
    assert len(RELIC_NAMES) == 8
    obs = observation()
    obs["relics"] = [dict(name=row["name"], counter=None) for row in _CONTRACT["relics"]]
    assert RuleAgent().decide(obs).action == 0
