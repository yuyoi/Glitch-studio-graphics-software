"""Pixel Stretch brush: grabs the line of pixels where you put the pen down and drags it along your stroke,
the classic stretched-pixel glitch. Move sideways for horizontal streaks, up/down for vertical ones."""
import numpy as np

NAME = 'Stretch Brush'
KIND = 'brush'
NEEDS_PIXELS = True
PARAMS = [
    P('size', 'GRAB LENGTH px', 4, 1200, 200),
    P('dir', 'DIRECTION', choices=['auto', 'horizontal', 'vertical']),
    P('follow', 'FOLLOW PEN', choices=['no (straight streaks)', 'yes (wavy)']),
    P('regrab', 'RE-GRAB CHANCE', 0.0, 0.2, 0.0, 0.005),
    P('jitter', 'JITTER px', 0, 40, 0),
]


def spacing(p, pr):
    return 1.0


def grab(ctx, x, y, horiz):
    s = ctx.p['size']
    if horiz:                                        # moving sideways: grab a vertical line of pixels
        y0 = int(np.clip(y - s / 2, 0, ctx.h - 1))
        y1 = int(np.clip(y + s / 2, y0 + 1, ctx.h))
        xi = int(np.clip(x, 0, ctx.w - 1))
        ctx.state.update(strip=ctx.arr[y0:y1, xi].copy(), a0=y0, a1=y1, horiz=True, gy=y)
    else:
        x0 = int(np.clip(x - s / 2, 0, ctx.w - 1))
        x1 = int(np.clip(x + s / 2, x0 + 1, ctx.w))
        yi = int(np.clip(y, 0, ctx.h - 1))
        ctx.state.update(strip=ctx.arr[yi, x0:x1].copy(), a0=x0, a1=x1, horiz=False, gx=x)


def dab(ctx, x, y, pr, ang):
    p, st, rng = ctx.p, ctx.state, ctx.rng
    if 'strip' not in st or (p['regrab'] and rng.random() < p['regrab']):
        d = p['dir']
        horiz = abs(np.cos(ang)) >= abs(np.sin(ang)) if d == 'auto' else d == 'horizontal'
        if 'strip' in st:
            horiz = st['horiz']
        grab(ctx, x, y, horiz)
    j = int(rng.integers(-p['jitter'], p['jitter'] + 1)) if p['jitter'] else 0
    strip = st['strip']
    follow = p['follow'].startswith('yes')
    if st['horiz']:
        xi = int(x)
        if not 0 <= xi < ctx.w:
            return
        a0 = st['a0'] + (int(y - st['gy']) if follow else 0) + j
        lo, hi = max(0, a0), min(ctx.h, a0 + len(strip))
        if hi > lo:
            ctx.arr[lo:hi, xi] = strip[lo - a0:hi - a0]
            ctx.mark(xi, lo, xi + 1, hi)
    else:
        yi = int(y)
        if not 0 <= yi < ctx.h:
            return
        a0 = st['a0'] + (int(x - st['gx']) if follow else 0) + j
        lo, hi = max(0, a0), min(ctx.w, a0 + len(strip))
        if hi > lo:
            ctx.arr[yi, lo:hi] = strip[lo - a0:hi - a0]
            ctx.mark(lo, yi, hi, yi + 1)


def outline(p):
    return 'rect', 4, p['size']
