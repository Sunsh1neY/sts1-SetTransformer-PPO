"""Versioned public relic state and one-hot encoding for A-path."""
import hashlib
import json
from pathlib import Path

from sts.env.full_card_public import _integer

PATH = Path(__file__).with_name('relic-state-registry.json')
REGISTRY = json.loads(PATH.read_bytes())
REGISTRY_HASH = hashlib.sha256(PATH.read_bytes()).hexdigest()
BY_NAME = {row['name']: row for row in REGISTRY['relics']}
DIMENSION = REGISTRY['feature_dimension']
BOTTLES = ('Bottled Flame', 'Bottled Lightning', 'Bottled Tornado')
PLAYED_TYPES = ('attack_played', 'skill_played', 'power_played')


def normalize_relics(rows):
    """Reject missing required counters; only stateless relics accept null."""
    if not isinstance(rows, list):
        raise TypeError('Relics must be a complete list')
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != ({'name', 'counter', 'played_types'} if row.get('name') == 'Orange Pellets' else {'name', 'counter'}):
            raise ValueError('Backend relic fields do not match the registered state schema')
        name = row['name']
        if name not in BY_NAME or name in seen:
            raise ValueError('Unknown or duplicate relic')
        seen.add(name)
        definition = BY_NAME[name]
        rule = definition['counter']
        value = row['counter']
        if rule is None:
            if value is not None:
                raise ValueError('Stateless relic cannot carry a counter')
        else:
            value = _integer(value, 'relic counter')
            if not rule['min'] <= value <= rule['max']:
                raise ValueError('Relic counter outside its semantic range')
        result.append(dict(name=name, relic_id=definition['id'], state={
            'counter': dict(applicable=rule is not None, known=rule is not None, value=value)}))
        if name == 'Orange Pellets':
            bits = row['played_types']
            if not isinstance(bits, dict) or set(bits) != set(PLAYED_TYPES) or any(type(v) is not bool for v in bits.values()):
                raise ValueError('Orange Pellets requires three explicit boolean progress fields')
            result[-1]['state']['played_types'] = dict(bits)
    return result


def relic_features(row):
    """Identity columns are fixed by registry order, never by instance order."""
    if not isinstance(row, dict):
        raise TypeError('Relic must be an object')
    # Explicit compatibility conversion for the original eight stateless relics.
    if set(row) == {'name', 'relic_id', 'counter'}:
        definition = BY_NAME.get(row['name'])
        if definition is None or definition['id'] > 8 or definition['counter'] is not None:
            raise ValueError('Legacy relic observation cannot introduce counter relics')
        if type(row['relic_id']) is not int or row['relic_id'] != definition['id']:
            raise ValueError('Relic identity mismatch')
        row = normalize_relics([{'name': row['name'], 'counter': row['counter']}])[0]
    if set(row) != {'name', 'relic_id', 'state'} or row['name'] not in BY_NAME:
        raise ValueError('Invalid public relic schema')
    definition = BY_NAME[row['name']]
    if type(row['relic_id']) is not int or row['relic_id'] != definition['id']:
        raise ValueError('Relic identity mismatch')
    state = row['state']
    if not isinstance(state, dict) or set(state) != ({'counter', 'played_types'} if row['name'] == 'Orange Pellets' else {'counter'}):
        raise ValueError('Unregistered relic state field')
    field = state['counter']
    if not isinstance(field, dict) or set(field) != {'applicable', 'known', 'value'}:
        raise ValueError('Incomplete relic counter')
    raw = dict(name=row['name'], counter=field['value'])
    if row['name'] == 'Orange Pellets': raw['played_types'] = state['played_types']
    expected = normalize_relics([raw])[0]
    if any(type(field[k]) is not bool for k in ('applicable', 'known')) or row != expected:
        raise ValueError('Counter applicability/visibility mismatch')
    rule = definition['counter']
    return [float(name == row['name']) for name in REGISTRY['identity_columns']] + [
        float(state['played_types'][k]) if row['name'] == 'Orange Pellets' else 0.0 for k in PLAYED_TYPES] + [
        float(field['applicable']), float(field['known']),
        field['value'] / rule['scale'] if rule else 0.0]


def validate_initial_relics(rows):
    """Validate the pre-initialization state without supplying guessed counters."""
    if not isinstance(rows, list):
        raise TypeError('Initial relics must be a list')
    raw = []
    for row in rows:
        if isinstance(row, str):
            if row in BOTTLES: raise ValueError('Bottled relic requires an exact master-deck card_index')
            raw.append(dict(name=row, counter=None, **({'played_types': dict.fromkeys(PLAYED_TYPES, False)} if row == 'Orange Pellets' else {})))
        elif isinstance(row, dict) and row.get('name') in BOTTLES and set(row) == {'name', 'card_index'}:
            if _integer(row['card_index'], 'card_index') < 0: raise ValueError('Negative bottled card index')
            raw.append(dict(name=row['name'],counter=None))
        elif isinstance(row, dict) and set(row) == {'name', 'counter'}:
            if row['name'] not in BY_NAME or BY_NAME[row['name']]['counter'] is None:
                raise ValueError('Stateless relics use name strings')
            raw.append(row)
        else:
            raise ValueError('Invalid initial relic record')
    normalized = normalize_relics(raw)
    owned = {row['name'] for row in normalized}
    if {'Burning Blood', 'Black Blood'} <= owned:
        raise ValueError('Black Blood replaces Burning Blood')
