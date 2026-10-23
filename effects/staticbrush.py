"""Static brush: paints TV snow where you draw (scan-line streaked, optional colour noise).
ERASE mode: the static eats random holes into the layer instead."""
import numpy as np

from gl import tvsignal as signal

NAME = 'Static'
KIND = 'brush'
PARAMS = [
    P('size', 'SIZE', 4, 800, 120),
    P('shape', 'SHAPE', choices=['circle', 'square', 'scan band']),
    P('grain', 'GRAIN px', 1, 16, 2),
    P('streak', 'SCAN STREAK', 0.0, 1.0, 0.5, 0.01),
    P('colour', 'COLOUR NOISE', 0.0, 1.0, 0.1, 0.01),
    P('amount', 'STRENGTH', 0.05, 1.0, 0.6, 0.01),
    P('press', 'PRESSURE>STRENGTH', 0.0, 1.0, 0.7, 0.01),
]


def spacing(p, pr):
    return max(2.0, p['size'] * 0.35)


def dims(p):
    s = p['size']
    return (s * 3, max(2, s // 6)) if p['shape'] == 'scan band' else (s, s)


def dab(ctx, x, y, pr, ang):
    p, rng = ctx.p, ctx.rng
    bw, bh = dims(p)
    g = max(1, int(p['grain']))
    x0, y0 = int(x - bw / 2) // g * g, int(y - bh / 2) // g * g     # grain cells stay on one grid between dabs
    x1, y1 = min(ctx.w, x0 + int(bw)), min(ctx.h, y0 + int(bh))
    x0, y0 = max(0, x0), max(0, y0)
    if x1 <= x0 or y1 <= y0:
        return
    hh, ww = y1 - y0, x1 - x0
    m = np.ones((hh, ww), np.float32)
    if p['shape'] == 'circle':
        yy, xx = np.mgrid[y0:y1, x0:x1]
        m = (((xx + 0.5 - x) / (bw / 2)) ** 2 + ((yy + 0.5 - y) / (bh / 2)) ** 2 <= 1).astype(np.float32)
    a = p['amount'] * (1 - p['press'] + p['press'] * pr)
    s = signal.snow(hh, ww, rng, g, p['streak'], p['colour'])
    r = ctx.arr[y0:y1, x0:x1]
    if ctx.erase:
        hole = (s[..., 0] < a * 0.9) & (m > 0)
        r[..., 3] = np.where(hole, 0, r[..., 3])
    else:
        k = (m * a)[..., None]
        rgb = r[..., :3].astype(np.float32) / 255
        r[..., :3] = np.clip((rgb * (1 - k) + s * k) * 255 + 0.5, 0, 255).astype(np.uint8)
        r[..., 3] = np.maximum(r[..., 3], (m * 255).astype(np.uint8) * (a > 0))
    ctx.mark(x0, y0, x1, y1)


def outline(p):
    bw, bh = dims(p)
    return ('circle' if p['shape'] == 'circle' else 'rect'), bw, bh
