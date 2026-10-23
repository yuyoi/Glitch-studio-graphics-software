"""Datamosh bands: random slices of the whole layer jump sideways."""
import numpy as np

NAME = 'Slice Shift'
KIND = 'filter'
CATEGORY = 'Distort'
PARAMS = [
    P('count', 'SLICES', 1, 200, 18),
    P('hmin', 'SLICE MIN px', 1, 200, 2),
    P('hmax', 'SLICE MAX px', 1, 400, 30),
    P('shift', 'SHIFT MAX px', 1, 800, 60),
    P('channel', 'CHANNEL', choices=['all', 'red', 'green', 'blue']),
    P('dir', 'DIRECTION', choices=['horizontal', 'vertical']),
]
CH = {'all': slice(0, 4), 'red': slice(0, 1), 'green': slice(1, 2), 'blue': slice(2, 3)}


def apply(img, p, rng):
    out = img.copy() if p['dir'] == 'horizontal' else img.transpose(1, 0, 2).copy()
    h = out.shape[0]
    lo, hi = sorted((p['hmin'], p['hmax']))
    ch = CH[p['channel']]
    for _ in range(p['count']):
        bh = int(rng.integers(lo, hi + 1))
        y = int(rng.integers(0, max(1, h - bh)))
        r = out[y:y + bh, :, ch]
        r[:] = np.roll(r, int(rng.integers(-p['shift'], p['shift'] + 1)), axis=1)
    return np.ascontiguousarray(out if p['dir'] == 'horizontal' else out.transpose(1, 0, 2))
