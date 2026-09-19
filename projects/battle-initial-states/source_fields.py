"""Lossless numeric normalization for run-log source fields."""
from math import isfinite


def combat_floor(value):
    if type(value) is int and value > 0:
        return value
    if type(value) is float and isfinite(value) and value > 0 and value.is_integer():
        return int(value)
    raise ValueError('Combat floor must be a positive integer-valued JSON number')


def scene_key(source_group, floor, index):
    if type(index) is not int or index < 0:
        raise ValueError('Combat index must be a nonnegative integer')
    return f'{source_group}:floor-{combat_floor(floor)}:combat-{index}'
