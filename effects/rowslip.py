"""Tape slip: slides thin horizontal bands of the picture under the brush sideways.
Pick one channel for an RGB tear. Uses what is already on the layer."""
import numpy as np

NAME = 'Row Slip'
KIND = 'brush'
NEEDS_PIXELS = True
PARAMS = [
    P('width', 'WIDTH', 8, 1200, 320),
    P('height', 'HEIGHT', 2, 600, 90),
    P('band', 'BAND MAX px', 1, 120, 10),
    P('shift', 'SHIFT MAX px', 1, 400, 70),
    P('chance', 'CHANCE', 0.05, 1.0, 0.6, 0.01),
    P('channel', 'CHANNEL', choices=['all', 'red', 'green', 'blue', 'alpha']),
    P('press', 'PRESSURE>SHIFT', 0.0, 1.0, 0.7, 0.01),
]
CH = {'all': slice(0, 4), 'red': slice(0, 1), 'green': slice(1, 2), 'blue': slice(2, 3), 'alpha': slice(3, 4)}


def spacing(p, pr):
    return max(2.0, p['height'] * 0.5)


def dab(ctx, x, y, pr, ang):
    p, rng, a = ctx.p, ctx.rng, ctx.arr
    x0, x1 = max(0, int(x - p['width'] / 2)), min(ctx.w, int(x + p['width'] / 2))
    y0, y1 = max(0, int(y - p['height'] / 2)), min(ctx.h, int(y + p['height'] / 2))
    if x1 - x0 < 2 or y1 <= y0:
        return
    amt = max(1, int(p['shift'] * (1 - p['press'] + p['press'] * pr)))
    ch = CH[p['channel']]
    yy = y0
    while yy < y1:
        bh = int(rng.integers(1, p['band'] + 1))
        if rng.random() < p['chance']:
            r = a[yy:min(y1, yy + bh), x0:x1, ch]
            r[:] = np.roll(r, int(rng.integers(-amt, amt + 1)), axis=1)
        yy += bh
    ctx.mark(x0, y0, x1, y1)


def outline(p):
    return 'rect', p['width'], p['height']
