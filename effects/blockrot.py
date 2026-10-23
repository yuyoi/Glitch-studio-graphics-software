"""Block rot: a broken digital TV / video stream. Real JPEG/MPEG maths: every 8x8 (or bigger) block's
DCT coefficients get crushed (blocky ringing, colour mush), then random macroblocks go wrong:
lost motion vectors, smears that drag down, flat blocks, swapped colour planes."""
import numpy as np

from gl import tvsignal as signal

NAME = 'Block Rot'
KIND = 'filter'
PARAMS = [
    P('crush', 'DCT CRUSH', 0.0, 200.0, 40.0, 1.0),
    P('chroma', 'COLOUR CRUSH x', 1.0, 6.0, 2.5, 0.1),
    P('block', 'MACROBLOCK px', choices=['16', '8', '32', '64']),
    P('chance', 'BROKEN BLOCKS', 0.0, 0.6, 0.08, 0.01),
    P('copy', 'WRONG-PLACE', 0.0, 1.0, 1.0, 0.05),
    P('smear', 'SMEAR DOWN', 0.0, 1.0, 1.0, 0.05),
    P('flat', 'FLAT BLOCKS', 0.0, 1.0, 0.5, 0.05),
    P('swap', 'COLOUR SWAP', 0.0, 1.0, 0.5, 0.05),
    P('trail', 'SMEAR LENGTH', 1, 20, 5),
]


def apply(img, p, rng):
    h, w = img.shape[:2]
    out = img.copy()
    if p['crush'] > 0:
        H, W = h - h % 8, w - w % 8
        rgb = out[:H, :W, :3].astype(np.float32) / 255
        out[:H, :W, :3] = (signal.dct_crush(rgb, 8, p['crush'], p['chroma']) * 255 + 0.5).astype(np.uint8)
    if p['chance'] > 0:
        signal.block_rot(out, rng, int(p['block']), p['chance'], (p['copy'], p['smear'], p['flat'], p['swap']), p['trail'])
    return out
