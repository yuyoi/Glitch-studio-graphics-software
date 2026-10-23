"""CRT scanlines: darkens or cuts every Nth row (or column)."""
import numpy as np

NAME = 'Scanlines'
KIND = 'filter'
PARAMS = [
    P('gap', 'EVERY N', 2, 32, 4),
    P('thick', 'THICKNESS', 1, 16, 1),
    P('strength', 'STRENGTH', 0.0, 1.0, 0.5, 0.01),
    P('mode', 'MODE', choices=['darken', 'cut alpha']),
    P('dir', 'DIRECTION', choices=['rows', 'columns']),
]


def apply(img, p, rng):
    out = img.copy()
    n = img.shape[0] if p['dir'] == 'rows' else img.shape[1]
    idx = np.arange(n) % p['gap'] < min(p['thick'], p['gap'] - 1)
    sel = (idx, slice(None)) if p['dir'] == 'rows' else (slice(None), idx)
    r = out[sel].astype(np.float32)
    if p['mode'] == 'darken':
        r[..., :3] *= 1 - p['strength']
    else:
        r[..., 3] *= 1 - p['strength']
    out[sel] = r.astype(np.uint8)
    return out
