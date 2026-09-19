"""Strict v2 canonical states for the current reset surface; no training admission."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re

VERSION = 'battle-initial-state-v2'
KEYS = frozenset(('character', 'ascension', 'act', 'floor', 'entry_timing',
                  'initialization_phase', 'player', 'deck', 'relics', 'potions',
                  'encounter', 'burning_elite'))
RECORD_KEYS = frozenset(('schema', 'state', 'state_hash', 'source_backbone',
                         'source_backbone_hash', 'provenance', 'evidence',
                         'training_admitted'))
BOTTLES = frozenset(('Bottled Flame', 'Bottled Lightning', 'Bottled Tornado'))
_ROOT = Path(__file__).resolve().parents[2]
_RELICS = {r['name']: r for r in json.loads(
    (_ROOT/'sts/env/relic-state-registry.json').read_text())['relics']}


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def integer(value, name, lo, hi):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f'{name} must be an integer in [{lo}, {hi}]')
    return value


def normalize(scene):
    if not isinstance(scene, dict) or set(scene) != KEYS:
        raise ValueError('State must contain exactly the v2 reset fields')
    state = copy.deepcopy(scene)
    if state['character'] != 'IRONCLAD':
        raise ValueError('Only Ironclad is in pilot scope')
    ascension = integer(state['ascension'], 'ascension', 0, 20)
    act = integer(state['act'], 'act', 1, 2)
    integer(state['floor'], 'floor', 1+(act-1)*17, act*17)
    if (state['entry_timing'], state['initialization_phase']) != (
            'pre_combat_initialization', 'before_destination_room_entry'):
        raise ValueError('Incorrect entry timing')
    player = state['player']
    if not isinstance(player, dict) or set(player) != {'hp', 'max_hp', 'gold'}:
        raise ValueError('HP, max HP and gold are required, without extra fields')
    integer(player['max_hp'], 'max_hp', 1, 32767)
    integer(player['hp'], 'hp', 1, player['max_hp'])
    integer(player['gold'], 'gold', 0, 32767)
    if not isinstance(state['encounter'], str) or not state['encounter']:
        raise ValueError('Encounter must be explicit')
    if type(state['burning_elite']) is not bool:
        raise ValueError('Burning-elite condition must be explicit')
    deck = state['deck']
    if not isinstance(deck, list) or not deck:
        raise ValueError('Complete nonempty master deck required')
    for card in deck:
        if not isinstance(card, str) or not re.fullmatch(r'[^+\s][^+]*(?:\+[1-9][0-9]*)?', card):
            raise ValueError('Card must be a name plus optional positive upgrade count; permanent state unsupported')
        if card.split('+')[0] in {'RitualDagger', 'Genetic Algorithm'}:
            raise ValueError('Required permanent card state is not representable by this reset adapter')
    relics = state['relics']
    if not isinstance(relics, list):
        raise ValueError('Complete acquisition-ordered relic list required')
    seen, bindings = set(), [[] for _ in deck]
    for relic in relics:
        if isinstance(relic, str):
            name = relic
            if name in BOTTLES:
                raise ValueError('Bottle requires exact binding')
        elif isinstance(relic, dict):
            name = relic.get('name')
            if name in BOTTLES and set(relic) == {'name', 'card_index'}:
                index = integer(relic['card_index'], 'card_index', 0, len(deck)-1)
                bindings[index].append(name)
            elif name not in BOTTLES and set(relic) == {'name', 'counter'}:
                integer(relic['counter'], 'counter', 0, 32767)
            else:
                raise ValueError('Unknown or missing relic state fields')
        else:
            raise ValueError('Invalid relic record')
        if not isinstance(name, str) or not name or name in seen:
            raise ValueError('Invalid or duplicate relic identity')
        if name not in _RELICS:
            raise ValueError('Relic identity outside the pinned runtime registry')
        rule = _RELICS[name]['counter']
        persistent = rule is not None and 'reset_on_battle_start' not in rule
        if persistent:
            if not isinstance(relic, dict) or set(relic) != {'name', 'counter'}:
                raise ValueError('Required persistent relic counter missing')
            integer(relic['counter'], name+' counter', rule['min'], rule['max'])
        elif name not in BOTTLES and not isinstance(relic, str):
            raise ValueError('Stateless/combat-reset relic must use its name only')
        seen.add(name)
    pots = state['potions']
    if not isinstance(pots, list) or len(pots) != (2 if ascension >= 11 else 3):
        raise ValueError('Potion slot capacity unsupported by current reset surface')
    if any(p is not None and (not isinstance(p, str) or not p) for p in pots):
        raise ValueError('Potion slots require explicit identity or null')
    order = sorted(range(len(deck)), key=lambda i: (deck[i], tuple(sorted(bindings[i]))))
    remap = {old: new for new, old in enumerate(order)}
    state['deck'] = [deck[i] for i in order]
    for relic in relics:
        if isinstance(relic, dict) and 'card_index' in relic:
            relic['card_index'] = remap[relic['card_index']]
    return state


def state_hash(state):
    return hashlib.sha256(canonical_bytes({'schema': VERSION, 'state': normalize(state)})).hexdigest()


def record(scene, provenance, evidence, source_backbone=None):
    state = normalize(scene)
    backbone = normalize(source_backbone if source_backbone is not None else scene)
    return {'schema': VERSION, 'state': state, 'state_hash': state_hash(state),
            'source_backbone': backbone,
            'source_backbone_hash': state_hash(backbone),
            'provenance': copy.deepcopy(provenance), 'evidence': copy.deepcopy(evidence),
            'training_admitted': False}


def validate_record(row):
    if set(row) != RECORD_KEYS:
        raise ValueError('Unexpected record fields')
    if row['schema'] != VERSION or row['training_admitted'] is not False:
        raise ValueError('Only diagnostic v2 records accepted')
    if (normalize(row['state']) != row['state'] or
            state_hash(row['state']) != row['state_hash'] or
            normalize(row['source_backbone']) != row['source_backbone'] or
            state_hash(row['source_backbone']) != row['source_backbone_hash']):
        raise ValueError('Noncanonical or tampered state')
    if not isinstance(row['provenance'], dict) or not isinstance(row['evidence'], dict):
        raise ValueError('Provenance and evidence must be explicit objects')
    return copy.deepcopy(row)


def write_records(path, rows):
    content = b''.join(canonical_bytes(validate_record(row))+b'\n' for row in rows)
    Path(path).write_bytes(content)


def read_records(path):
    return [validate_record(json.loads(line)) for line in Path(path).read_bytes().splitlines()]


def reset_payload(row):
    return validate_record(row)['state']
