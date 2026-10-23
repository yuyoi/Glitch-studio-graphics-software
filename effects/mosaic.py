"""Mosaic brush: pixelates what's under the brush into big blocks (on one fixed grid, so blocks line up
between strokes). Censor-bar / low-res-cam look."""
import numpy as np

NAME = 'Mosaic'
KIND = 'brush'
CATEGORY = 'Pixel'
NEEDS_PIXELS = True
PARAMS = [
    P('size', 'SIZE', 8, 1000, 180),
    P('block', 'BLOCK px', 2, 128, 16),
    P('shape', 'SHAPE', choices=['circle', 'square']),
    P('colour', 'BLOCK COLOUR', choices=['average', 'corner pixel', 'brightest']),
]


def spacing(p, pr):
    return max(2.0, p['size'] * 0.25)


def dab(ctx, x, y, pr, ang):
    p = ctx.p
    b, s = p['block'], p['size']
    x0, y0 = max(0, int(x - s / 2) // b * b), max(0, int(y - s / 2) // b * b)
    x1, y1 = min(ctx.w, int(x + s / 2) // b * b + b), min(ctx.h, int(y + s / 2) // b * b + b)
    x1, y1 = x0 + (x1 - x0) // b * b, y0 + (y1 - y0) // b * b
    if x1 <= x0 or y1 <= y0:
        return
    r = ctx.arr[y0:y1, x0:x1]
    by, bx = (y1 - y0) // b, (x1 - x0) // b
    blocks = r.reshape(by, b, bx, b, 4).astype(np.float32)
    if p['colour'] == 'average':
        col = blocks.mean((1, 3))
    elif p['colour'] == 'corner pixel':
        col = blocks[:, 0, :, 0]
    else:
        lum = blocks[..., :3].sum(-1)
        i = lum.reshape(by, b, bx, b).transpose(0, 2, 1, 3).reshape(by, bx, -1).argmax(-1)
        col = blocks.transpose(0, 2, 1, 3, 4).reshape(by, bx, -1, 4)[np.arange(by)[:, None], np.arange(bx)[None], i]
    cy = y0 + (np.arange(by) + 0.5) * b
    cx = x0 + (np.arange(bx) + 0.5) * b
    if p['shape'] == 'circle':
        inside = ((cx[None] - x) ** 2 + (cy[:, None] - y) ** 2) <= (s / 2) ** 2
    else:
        inside = np.ones((by, bx), bool)
    new = np.where(inside[:, None, :, None, None], col[:, None, :, None, :], blocks)
    r[:] = (new + 0.5).astype(np.uint8).reshape(r.shape)
    ctx.mark(x0, y0, x1, y1)


def outline(p):
    return ('circle' if p['shape'] == 'circle' else 'rect'), p['size'], p['size']
