"""Terminal net-HP and potion-cost reward for the A-path battle task."""

from copy import deepcopy
from math import isfinite
from numbers import Real


VERSION = "battle_reward_v2"


def contract():
    """Return an independent, serializable identity for the fixed v2 objective."""
    return dict(reward_version=VERSION, victory_bonus=2.0, alpha_hp=1.0,
                potion_use_cost=0.05, gamma=1.0, settlement="true_terminal_only",
                hp_start_timing="registered_pre_combat",
                hp_end_timing="after_supported_exit_effects")


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def terminal_components(*, victory, hp_start, max_hp_start, hp_end, potion_uses):
    """Recompute v2 only from verified complete-episode fields."""
    if type(victory) is not bool:
        raise ValueError("victory must be a boolean")
    start = _number(hp_start, "hp_start")
    maximum = _number(max_hp_start, "max_hp_start")
    end = _number(hp_end, "hp_end")
    if maximum <= 0 or not 0 < start <= maximum or end < 0:
        raise ValueError("invalid initial or final HP")
    if type(potion_uses) is not int or potion_uses < 0:
        raise ValueError("potion_uses must be a nonnegative integer")
    cfg = contract()
    return dict(victory=cfg['victory_bonus'] * victory,
                net_hp=cfg['alpha_hp'] * (end-start)/maximum,
                potion_cost=-cfg['potion_use_cost'] * potion_uses)


class BattleRewardV2:
    """Episode accounting; replaying accepted actions reconstructs this state."""

    def __init__(self, player, potions):
        self.hp_start = player['hp']
        self.max_hp_start = player['max_hp']
        terminal_components(victory=False, hp_start=self.hp_start,
                            max_hp_start=self.max_hp_start, hp_end=self.hp_start,
                            potion_uses=0)
        self.initial_potions = deepcopy(potions)
        self.events = []
        self.closed = False

    def transition(self, *, observation, terminated, truncated, outcome, potion_event=None):
        if self.closed:
            raise RuntimeError("reward episode already closed")
        if type(terminated) is not bool or type(truncated) is not bool or terminated and truncated:
            raise ValueError("invalid termination flags")
        if type(outcome) is not int or outcome not in (0, 1, 2) or terminated != (outcome != 0):
            raise ValueError("backend outcome and termination disagree")
        if potion_event is not None:
            self.events.append(deepcopy(potion_event))
        player = observation['player']
        components = terminal_components(victory=outcome == 1, hp_start=self.hp_start,
            max_hp_start=self.max_hp_start, hp_end=player['hp'], potion_uses=len(self.events)) if terminated else None
        reward = sum(components.values()) if components is not None else 0.0
        self.closed = terminated or truncated
        accounting = dict(hp_start=self.hp_start, max_hp_start=self.max_hp_start,
            hp_end=player['hp'], max_hp_end=player['max_hp'],
            net_hp_fraction=(player['hp']-self.hp_start)/self.max_hp_start,
            potion_uses=len(self.events), initial_potions=deepcopy(self.initial_potions),
            final_potions=deepcopy(observation['potions']), potion_events=deepcopy(self.events),
            reward_components=components, complete=terminated)
        return reward, dict(reward_contract=contract(), reward_version=VERSION,
            alpha_hp=1.0, victory_bonus=2.0, potion_use_cost=0.05,
            battle_won=terminated and outcome == 1,
            task_outcome='victory' if outcome == 1 else 'defeat' if outcome == 2 else 'external_truncation' if truncated else 'ongoing',
            reward_base=reward, reward_train=reward, reward_accounting=accounting)
