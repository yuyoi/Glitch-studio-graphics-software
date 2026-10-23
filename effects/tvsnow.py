"""TV snow: analog static from a tuner with no signal, smeared along the scan lines, with a rolling bright bar.

MODE
  over     static mixed over the picture
  behind   static only shows where the layer is see-through (the drawing floats on a dead channel)
  ghost    weak signal: the picture faint inside the snow
"""
import numpy as np

from gl import tvsignal as signal

NAME = 'TV Snow'
KIND = 'filter'
CATEGORY = 'TV & Signal'
PARAMS = [
    P('mode', 'MODE', choices=['over', 'behind', 'ghost']),
    P('amount', 'AMOUNT', 0.0, 1.0, 0.35, 0.01),
    P('grain', 'GRAIN px', 1, 12, 2),
    P('streak', 'SCAN STREAK', 0.0, 1.0, 0.4, 0.01),
    P('colour', 'COLOUR NOISE', 0.0, 1.0, 0.15, 0.01),
    P('bar', 'ROLLING BAR', 0.0, 1.0, 0.3, 0.01),
    P('barpos', 'BAR POSITION', 0.0, 1.0, 0.35, 0.01),
    P('key', 'SEE-THROUGH', choices=['white paper', 'transparent']),
]


def apply(img, p, rng):
    h, w = img.shape[:2]
    s = signal.snow(h, w, rng, p['grain'], p['streak'], p['colour'])
    if p['bar'] > 0:
        y = np.arange(h, dtype=np.float32) / h
        d = np.minimum(abs(y - p['barpos']), 1 - abs(y - p['barpos']))
        s = np.clip(s + p['bar'] * 0.5 * np.exp(-(d / 0.07) ** 2)[:, None, None], 0, 1)
    rgb = img[..., :3].astype(np.float32) / 255
    al = signal.see_through(img, p['key'])
    a = p['amount']
    out = img.copy()
    if p['mode'] == 'over':
        new = rgb * (1 - a) + s * a
    elif p['mode'] == 'behind':
        new = rgb * al + s * (1 - al)
        out[..., 3] = 255
    else:
        new = s * (1 - (1 - a) * 0.8) + rgb * al * (1 - a) * 0.8
        out[..., 3] = 255
    out[..., :3] = np.clip(new * 255 + 0.5, 0, 255).astype(np.uint8)
    return out
