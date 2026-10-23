"""RGB split: slides the red and blue channels apart (VHS / bad cable)."""
import numpy as np

NAME = 'RGB Shift'
KIND = 'filter'
CATEGORY = 'Colour'
PARAMS = [
    P('rx', 'RED X', -64, 64, 6),
    P('ry', 'RED Y', -64, 64, 0),
    P('bx', 'BLUE X', -64, 64, -6),
    P('by', 'BLUE Y', -64, 64, 0),
    P('alpha', 'FRINGE OUTSIDE', choices=['yes', 'no']),
]


def apply(img, p, rng):
    out = img.copy()
    out[..., 0] = np.roll(img[..., 0], (p['ry'], p['rx']), (0, 1))
    out[..., 2] = np.roll(img[..., 2], (p['by'], p['bx']), (0, 1))
    if p['alpha'] == 'yes':                               # fringes show outside the shape too
        ra = np.roll(img[..., 3], (p['ry'], p['rx']), (0, 1))
        ba = np.roll(img[..., 3], (p['by'], p['bx']), (0, 1))
        out[..., 3] = np.maximum(img[..., 3], np.maximum(ra, ba))
    return out
