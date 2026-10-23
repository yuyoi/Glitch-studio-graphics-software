"""Hue Shift brush: spins the colours under the brush around the colour wheel (brightness stays).
Keeps spinning as you scrub, so going over a spot again pushes it further."""
import numpy as np

from gl import colour

NAME = 'Hue Shift'
KIND = 'brush'
CATEGORY = 'Colour'
NEEDS_PIXELS = True
PARAMS = [
    P('size', 'SIZE', 4, 1000, 140),
    P('angle', 'SPIN degrees', -180, 180, 40),
    P('mode', 'MODE', choices=['fixed', 'random per dab', 'pressure']),
    P('sat', 'SATURATION BOOST', 0.0, 2.0, 0.3, 0.05),
    P('soft', 'SOFT EDGE', 0.0, 1.0, 0.5, 0.01),
]


def spacing(p, pr):
    return max(2.0, p['size'] * 0.3)


def dab(ctx, x, y, pr, ang):
    p, rng = ctx.p, ctx.rng
    s = p['size']
    x0, y0 = max(0, int(x - s / 2)), max(0, int(y - s / 2))
    x1, y1 = min(ctx.w, int(x + s / 2) + 1), min(ctx.h, int(y + s / 2) + 1)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    r = np.sqrt((xx - x) ** 2 + (yy - y) ** 2) / (s / 2)
    soft = max(0.01, p['soft'])
    k = np.clip((1 - r) / soft, 0, 1)[..., None] if p['soft'] > 0 else (r <= 1)[..., None].astype(np.float32)
    deg = p['angle']
    if p['mode'] == 'random per dab':
        deg = rng.uniform(-abs(deg) - 1, abs(deg) + 1)
    elif p['mode'] == 'pressure':
        deg = deg * pr
    reg = ctx.arr[y0:y1, x0:x1]
    rgb = reg[..., :3].astype(np.float32) / 255
    out = colour.rotate_hue(rgb, np.radians(deg))
    if p['sat']:
        lum = out.mean(-1, keepdims=True)
        out = np.clip(lum + (out - lum) * (1 + p['sat'] * 0.3), 0, 1)
    reg[..., :3] = ((rgb * (1 - k) + out * k) * 255 + 0.5).astype(np.uint8)
    ctx.mark(x0, y0, x1, y1)


def outline(p):
    return 'circle', p['size'], p['size']
