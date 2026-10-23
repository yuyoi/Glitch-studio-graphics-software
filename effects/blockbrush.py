"""Block Rot brush: paint broken digital video where you draw. DCT-crushes the blocks under the brush
(real JPEG maths, on the same 8px grid everywhere) and corrupts macroblocks: wrong-place copies,
drag-down smears, flat blocks, swapped colour."""
import numpy as np

from gl import tvsignal as signal

NAME = 'Block Brush'
KIND = 'brush'
NEEDS_PIXELS = True
PARAMS = [
    P('size', 'SIZE', 16, 800, 160),
    P('block', 'MACROBLOCK px', choices=['16', '8', '32', '64']),
    P('crush', 'DCT CRUSH', 0.0, 200.0, 50.0, 1.0),
    P('chance', 'BROKEN BLOCKS', 0.0, 1.0, 0.25, 0.01),
    P('smear', 'SMEAR vs COPY', 0.0, 1.0, 0.5, 0.01),
    P('trail', 'SMEAR LENGTH', 1, 20, 4),
    P('press', 'PRESSURE>CHANCE', 0.0, 1.0, 0.6, 0.01),
]


def spacing(p, pr):
    return max(8.0, p['size'] * 0.5)


def dab(ctx, x, y, pr, ang):
    p, rng = ctx.p, ctx.rng
    n = int(p['block'])
    s = p['size']
    x0, y0 = int(x - s / 2) // n * n, int(y - s / 2) // n * n         # snap to the block grid
    x1, y1 = min(ctx.w, x0 + int(s) // n * n + n), min(ctx.h, y0 + int(s) // n * n + n)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = x0 + (x1 - x0) // 8 * 8, y0 + (y1 - y0) // 8 * 8
    if x1 - x0 < 8 or y1 - y0 < 8:
        return
    r = ctx.arr[y0:y1, x0:x1]
    if p['crush'] > 0:
        rgb = r[..., :3].astype(np.float32) / 255
        r[..., :3] = (signal.dct_crush(rgb, 8, p['crush'], 2.5) * 255 + 0.5).astype(np.uint8)
    ch = p['chance'] * (1 - p['press'] + p['press'] * pr)
    sm = p['smear']
    signal.block_rot(r, rng, n, ch, (1 - sm, sm, 0.3, 0.3), p['trail'])
    ctx.mark(x0, y0, x1, y1)


def outline(p):
    return 'rect', p['size'], p['size']
