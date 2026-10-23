"""Pixel Art: smart pixelation. Each big pixel keeps its block's dominant colour (k-centroid) and dark line work
wins its block, so the drawing turns into crisp hand-made-looking sprite art instead of a blurry mosaic.
Optional palette reduction and a 1-pixel dark outline around shapes, like sprites have."""
import numpy as np

from gl import pixelart

NAME = 'Pixel Art'
KIND = 'filter'
CATEGORY = 'Pixel'
PARAMS = [
    P('pixel', 'PIXEL SIZE', 2, 48, 8),
    P('mode', 'METHOD', choices=['pixel art', 'k-centroid', 'average']),
    P('outline', 'LINE KEEPING (lower = more lines)', 0.05, 0.8, 0.3, 0.01),
    P('colours', 'PALETTE COLOURS (0=all)', 0, 64, 0),
    P('dither', 'PALETTE DITHER', choices=['no', 'yes']),
    P('sprite', 'SPRITE OUTLINE', choices=['no', 'dark', 'black']),
]


def apply(img, p, rng):
    h, w = img.shape[:2]
    s = p['pixel']
    tw, th = max(2, w // s), max(2, h // s)
    small = pixelart.downscale(img, tw, th, p['mode'], p['outline'])
    small = pixelart.palette(small, p['colours'], p['dither'] == 'yes')
    if p['sprite'] != 'no':                                # pixels on the edge of a shape get the outline colour
        a = small[..., 3] > 0
        edge = a & ~(np.roll(a, 1, 0) & np.roll(a, -1, 0) & np.roll(a, 1, 1) & np.roll(a, -1, 1))
        col = small[..., :3].astype(np.float32)
        col[edge] = col[edge] * 0.35 if p['sprite'] == 'dark' else 12
        small[..., :3] = col.astype(np.uint8)
    ys = np.minimum(np.arange(h) * th // h, th - 1)
    xs = np.minimum(np.arange(w) * tw // w, tw - 1)
    return np.ascontiguousarray(small[ys][:, xs])
