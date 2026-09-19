"""Scope projection stays separate from source reconstruction and admission."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path


PROJECT = Path(__file__).resolve().parent


def load_reconstructor():
    spec = importlib.util.spec_from_file_location('reconstruct_pilot', PROJECT / 'reconstruct-pilot.py')
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def candidate():
    return {
        'character': 'IRONCLAD', 'ascension': 20, 'act': 1, 'floor': 4,
        'entry_timing': 'pre_combat_initialization',
        'initialization_phase': 'before_destination_room_entry',
        'player': {'hp': 65, 'max_hp': 80, 'gold': 99},
        'deck': ['Strike_R', 'Bash'], 'relics': ['Burning Blood'],
        'potions': ['PowerPotion', 'Weak Potion'],
        'encounter': 'JAW_WORM', 'burning_elite': False,
        'field_evidence': {'potions': 'source'},
    }


def test_projection_preserves_source_and_does_not_replace_or_expand_registry():
    module = load_reconstructor()
    source = candidate()
    before = copy.deepcopy(source)

    projected = module.project_supported_potions(source, {'Weak Potion'})

    assert source == before
    assert projected['source_backbone']['potions'] == ['PowerPotion', 'Weak Potion']
    assert projected['potions'] == [None, 'Weak Potion']
    assert projected['potion_projection'] == {
        'policy': 'supported-potions-only-v1',
        'projected': True,
        'source_potions': ['PowerPotion', 'Weak Potion'],
        'training_potions': [None, 'Weak Potion'],
        'removed_potions': ['PowerPotion'],
        'removed_potion_counts': {'PowerPotion': 1},
        'supported_potion_whitelist': ['Weak Potion'],
        'empty_slots_preserved': 1,
        'source_inventory_preserved': True,
        'replacement_used': False,
        'backend_registry_expanded': False,
    }


def test_projection_does_not_change_non_potion_semantics():
    module = load_reconstructor()
    source = candidate()
    projected = module.project_supported_potions(source, {'Weak Potion'})

    for key in ('character', 'ascension', 'act', 'floor', 'entry_timing',
                'initialization_phase', 'player', 'deck', 'relics',
                'encounter', 'burning_elite'):
        assert projected[key] == source[key]
