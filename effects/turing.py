"""Turing patterns: Gray-Scott reaction-diffusion, the maths Alan Turing proposed for leopard spots,
zebra stripes and coral. Seeded from YOUR drawing (dark lines start the reaction), so the pattern
grows out of the picture.

MODE
  cut         eats the layer where the pattern is (organic lace holes)
  palette     pattern through a cosine palette over your colours
  hue bust    your colours spun by the pattern
  ink         pattern printed as dark ink over the picture
"""
import numpy as np
from PIL import Image

from gl import colour

NAME = 'Turing'
KIND = 'filter'
CATEGORY = 'Maths'
SLOW = True                                   # no live preview: press APPLY
STYLES = {'coral': (0.0545, 0.062), 'spots': (0.035, 0.065), 'mitosis': (0.0367, 0.0649),
          'worms': (0.078, 0.061), 'maze': (0.029, 0.057), 'bubbles': (0.098, 0.0555)}
PARAMS = [
    P('style', 'STYLE', choices=list(STYLES)),
    P('mode', 'MODE', choices=['cut', 'palette', 'hue bust', 'ink']),
    P('cell', 'CELL SIZE px', 2, 16, 6),
    P('steps', 'GROWTH STEPS', 200, 6000, 1500, 100),
    P('seed', 'SEED FROM', choices=['lines', 'random']),
    P('amount', 'AMOUNT', 0.0, 1.0, 0.8, 0.01),
    P('palette', 'PALETTE', choices=list(colour.PALETTES)),
]


def lap(z):
    return (np.roll(z, 1, 0) + np.roll(z, -1, 0) + np.roll(z, 1, 1) + np.roll(z, -1, 1) - 4 * z)


def grow(h, w, img, p, rng):
    F, K = STYLES[p['style']]
    U = np.ones((h, w), np.float32)
    V = np.zeros((h, w), np.float32)
    if p['seed'] == 'lines':
        small = np.asarray(Image.fromarray(img).resize((w, h), Image.BILINEAR)).astype(np.float32) / 255
        lum = small[..., :3].mean(2)
        m = (lum < 0.35) & (small[..., 3] > 0.5)
        if m.mean() < 0.002:
            m = rng.random((h, w)) < 0.02
    else:
        m = rng.random((h, w)) < 0.03
    V[m] = 0.5
    U[m] = 0.5
    V += rng.random((h, w)).astype(np.float32) * 0.02
    for _ in range(int(p['steps'])):
        uvv = U * V * V
        U += 0.16 * lap(U) - uvv + F * (1 - U)
        V += 0.08 * lap(V) + uvv - (F + K) * V
    v = V - V.min()
    return v / max(1e-6, v.max())


def apply(img, p, rng):
    H, W = img.shape[:2]
    c = p['cell']
    h, w = max(8, H // c), max(8, W // c)
    v = grow(h, w, img, p, rng)
    v = np.asarray(Image.fromarray((v * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255
    a = p['amount']
    out = img.copy()
    rgb = img[..., :3].astype(np.float32) / 255
    if p['mode'] == 'cut':
        out[..., 3] = np.where(v > 1 - a * 0.7 - 0.15, 0, img[..., 3])
        return out
    if p['mode'] == 'palette':
        new = rgb * (1 - a * v[..., None]) + colour.cosine(v, p['palette']) * a * v[..., None]
    elif p['mode'] == 'hue bust':
        new = colour.rotate_hue(rgb, v * 2 * np.pi * a)
    else:
        new = rgb * (1 - (v > 0.5)[..., None] * a)
    out[..., :3] = np.clip(new * 255 + 0.5, 0, 255).astype(np.uint8)
    return out
