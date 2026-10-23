"""Quasicrystal: N plane waves at evenly turned angles added together. 5 waves give Penrose-like
order that never repeats (the maths of Shechtman's Nobel-prize quasicrystals); the eye locks onto it
as moire flowers.

MODE
  palette     the interference pattern through a cosine palette, blended over your picture
  hue bust    your colours spun by the wave height
  cut         eats the layer where the waves dip (lace / halftone holes)
  rgb split   each channel sampled at a wave-shifted spot (glitchy chromatic moire)
"""
import numpy as np

from gl import colour

NAME = 'Quasicrystal'
KIND = 'filter'
PARAMS = [
    P('mode', 'MODE', choices=['palette', 'hue bust', 'cut', 'rgb split']),
    P('waves', 'WAVES (symmetry)', 3, 13, 7),
    P('freq', 'WAVE SIZE px', 4, 400, 40),
    P('phase', 'PHASE', 0.0, 1.0, 0.0, 0.01),
    P('amount', 'AMOUNT', 0.0, 1.0, 0.6, 0.01),
    P('thresh', 'CUT LEVEL', 0.0, 1.0, 0.45, 0.01),
    P('palette', 'PALETTE', choices=list(colour.PALETTES)),
]


def field(h, w, n, size, phase, rng):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    k = 2 * np.pi / size
    rot = rng.uniform(0, np.pi)
    f = np.zeros((h, w), np.float32)
    for i in range(n):
        t = rot + np.pi * i / n
        f += np.cos(k * (xx * np.cos(t) + yy * np.sin(t)) + 2 * np.pi * phase * (i + 1))
    return (f / n + 1) / 2                                           # 0..1


def apply(img, p, rng):
    h, w = img.shape[:2]
    f = field(h, w, p['waves'], p['freq'], p['phase'], rng)
    rgb = img[..., :3].astype(np.float32) / 255
    a = p['amount']
    out = img.copy()
    if p['mode'] == 'cut':
        keep = f > p['thresh']
        out[..., 3] = np.where(keep, img[..., 3], 0)
        return out
    if p['mode'] == 'palette':
        lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
        new = rgb * (1 - a) + colour.cosine(f + lum * 0.3, p['palette']) * (0.3 + 0.7 * lum[..., None]) * a
    elif p['mode'] == 'hue bust':
        new = colour.rotate_hue(rgb, (f - 0.5) * 2 * np.pi * a * 2)
    else:
        d = ((f - 0.5) * a * p['freq']).astype(int)
        yy, xx = np.mgrid[0:h, 0:w]
        new = rgb.copy()
        new[..., 0] = rgb[yy, np.clip(xx + d, 0, w - 1), 0]
        new[..., 2] = rgb[yy, np.clip(xx - d, 0, w - 1), 2]
    out[..., :3] = np.clip(new * 255 + 0.5, 0, 255).astype(np.uint8)
    return out
