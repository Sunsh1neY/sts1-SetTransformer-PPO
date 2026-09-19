"""A-path card visibility v3; legacy entity schemas remain immutable."""
from sts.env.entities import CARD_NUMERIC, CARD_BOOL, FEATURE_DIMS, card_features
from sts.env.full_card_public import _integer

DIMENSION = FEATURE_DIMS['CARD'] + 1
POSITION_INDEX = len(CARD_NUMERIC) + CARD_BOOL.index('known_top')


def card_features_v3(card, region):
    row = dict(card)
    if 'draw_position_known' in row or 'draw_position' in row:
        if 'known_top' in row:
            raise ValueError('Draw position replaces known_top in v3')
        known = row.pop('draw_position_known')
        position = row.pop('draw_position')
        if type(known) is not bool:
            raise TypeError('Draw visibility must be boolean')
        if known:
            position = _integer(position, 'draw_position')
            if region != 'draw_pile' or not 0 <= position < 65536:
                raise ValueError('Known position must identify a draw-pile card')
        elif position is not None:
            raise ValueError('Unknown draw position must be null')
    else:
        known = row.pop('known_top', False)
        if type(known) is not bool or known and region != 'draw_pile':
            raise ValueError('Invalid legacy known-top flag')
        position = 0 if known else None
    row['known_top'] = False
    features = card_features(row, region)
    features[POSITION_INDEX] = float(known)
    features.insert(POSITION_INDEX+1, position/512 if known else 0.0)
    return features
