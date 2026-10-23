"""Filter Brush: paints in whatever filter is selected in the FILTERS panel, with its current settings.
Pixel sort, VHS, Turing, Colour Rip... only where your pen goes. (The filter is rendered once when you start
painting, so slow filters take a moment on the first stroke.)"""
import numpy as np

NAME = 'Filter Brush'
KIND = 'brush'
CATEGORY = 'Tools'
NEEDS_FILTER = True
PARAMS = [
    P('size', 'SIZE', 4, 1000, 160),
    P('edge', 'EDGE', choices=['soft', 'hard', 'pixel blocks']),
    P('block', 'BLOCK px (pixel edge)', 2, 64, 12),
    P('strength', 'STRENGTH', 0.05, 1.0, 1.0, 0.01),
    P('press', 'PRESSURE>STRENGTH', 0.0, 1.0, 0.6, 0.01),
]


def spacing(p, pr):
    return max(2.0, p['size'] * 0.2)


def dab(ctx, x, y, pr, ang):
    p, src = ctx.p, ctx.source
    if src is None:
        return
    s = p['size']
    x0, y0 = max(0, int(x - s / 2)), max(0, int(y - s / 2))
    x1, y1 = min(ctx.w, int(x + s / 2) + 1), min(ctx.h, int(y + s / 2) + 1)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    if p['edge'] == 'pixel blocks':
        b = p['block']
        yy, xx = np.floor(yy / b) * b + b / 2, np.floor(xx / b) * b + b / 2
    r = np.sqrt((xx - x) ** 2 + (yy - y) ** 2) / (s / 2)
    if p['edge'] == 'soft':
        k = np.clip((1 - r) * 2.5, 0, 1)
    else:
        k = (r <= 1).astype(np.float32)
    k = (k * p['strength'] * (1 - p['press'] + p['press'] * pr))[..., None]
    a = ctx.arr[y0:y1, x0:x1].astype(np.float32)
    ctx.arr[y0:y1, x0:x1] = (a * (1 - k) + src[y0:y1, x0:x1].astype(np.float32) * k + 0.5).astype(np.uint8)
    ctx.mark(x0, y0, x1, y1)


def outline(p):
    return 'circle', p['size'], p['size']
