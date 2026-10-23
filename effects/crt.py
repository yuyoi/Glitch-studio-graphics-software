"""CRT: the picture on an old tube TV. Barrel-curved glass, RGB phosphor mask (aperture grille / shadow mask /
slot mask), scanlines, bloom glow around bright parts, edge colour fringing and a vignette."""
import numpy as np
from PIL import Image, ImageFilter

NAME = 'CRT'
KIND = 'filter'
PARAMS = [
    P('curve', 'GLASS CURVE', 0.0, 0.4, 0.12, 0.01),
    P('mask', 'PHOSPHOR MASK', choices=['aperture grille', 'shadow mask', 'slot mask', 'none']),
    P('dot', 'PHOSPHOR px', 1, 8, 2),
    P('maskamt', 'MASK STRENGTH', 0.0, 1.0, 0.5, 0.01),
    P('lines', 'SCANLINES', 0.0, 1.0, 0.35, 0.01),
    P('bloom', 'BLOOM', 0.0, 1.5, 0.45, 0.01),
    P('radius', 'BLOOM RADIUS', 1, 60, 12),
    P('fringe', 'EDGE FRINGE px', 0, 20, 3),
    P('vignette', 'VIGNETTE', 0.0, 1.0, 0.35, 0.01),
]


def apply(img, p, rng):
    h, w = img.shape[:2]
    src = img[..., :3].astype(np.float32) / 255
    a = img[..., 3:4].astype(np.float32) / 255
    src = src * a + (1 - a) * 0.02                                    # see-through parts show a dark tube
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / (w / 2) - 1, yy / (h / 2) - 1
    r2 = u * u + v * v
    out = np.zeros_like(src)
    for c, f in ((0, 1 + p['fringe'] / w), (1, 1.0), (2, 1 - p['fringe'] / w)):
        k = (1 + p['curve'] * r2) * f
        sx, sy = (u * k + 1) * w / 2, (v * k + 1) * h / 2
        ok = (sx >= 0) & (sx < w) & (sy >= 0) & (sy < h)
        out[..., c] = np.where(ok, src[np.clip(sy, 0, h - 1).astype(int), np.clip(sx, 0, w - 1).astype(int), c], 0)
    if p['bloom'] > 0:
        bright = np.clip((out - 0.55) * 2.2, 0, 1)
        im = Image.fromarray((bright * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(p['radius']))
        out = out + np.asarray(im).astype(np.float32) / 255 * p['bloom']
    d = p['dot']
    if p['mask'] != 'none' and p['maskamt'] > 0:
        col = (xx // d).astype(int)
        row = (yy // d).astype(int)
        if p['mask'] == 'shadow mask':
            col = col + (row % 2) * 1                               # triads offset every other row
        ch = col % 3
        m = np.full((h, w, 3), 1 - p['maskamt'], np.float32)
        for c in range(3):
            m[..., c][ch == c] = 1
        if p['mask'] == 'slot mask':
            gap = ((row % 4) == 3) & (((col // 3) % 2) == (row // 4) % 2)
            m[gap] *= 1 - p['maskamt'] * 0.6
        out = out * m * (1 + p['maskamt'] * 0.6)
    if p['lines'] > 0:
        out *= np.where((yy.astype(int) // max(1, d)) % 2 == 1, 1 - p['lines'], 1)[..., None]
    out *= np.clip(1 - p['vignette'] * r2 * 0.6, 0, 1)[..., None]
    res = img.copy()
    res[..., :3] = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
    res[..., 3] = 255
    return res
