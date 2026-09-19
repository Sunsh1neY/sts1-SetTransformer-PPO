"""Regression tests for source-derived potion capacity transitions."""
from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("public_prefix_expansion", ROOT / "scripts/expand-public-prefixes.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_potion_belt_acquisition_updates_capacity_before_final_inventory_check():
    state = {
        "ascension": 20,
        "deck": Counter(),
        "relics": [],
        "potions": Counter(["Weak Potion", "Fruit Juice"]),
        "capacity": 2,
    }
    run = {
        "path_per_floor": ["M"],
        "event_choices": [],
        "items_purged_floors": [],
        "item_purchase_floors": [],
        "card_choices": [],
        "campfire_choices": [],
        "relics_obtained": [{"floor": 1, "key": "Potion Belt"}],
        "potions_obtained": [{"floor": 1, "key": "Swift Potion"}],
        "potions_obtained_alchemize": [[]],
        "potions_obtained_entropic_brew": [[]],
        "potion_use_per_floor": [[]],
        "potion_discard_per_floor": [[]],
    }

    MODULE.AUDIT.advance_floor(run, state, 1)

    assert state["capacity"] == 3
    assert state["potions"] == Counter(["Weak Potion", "Fruit Juice", "Swift Potion"])
