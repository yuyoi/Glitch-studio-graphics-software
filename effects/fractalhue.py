"""Fractal 1/f colour: noise with the same statistics as clouds, coastlines and the Pollock drip paintings
people rate most beautiful (fractal dimension ~1.3-1.5, i.e. spectral BETA around 2.4-3).
Made by shaping white noise in the Fourier domain, then (optionally) warping it through itself.

MODE
  hue bust     spins each pixel's hue by the noise: your colours, broken up in fractal clouds
  palette      maps the noise through a cosine palette and blends it over your colours
  posterize    noise-shifted colour bands (contour-map / thermal camera look)
"""
import numpy as np

from gl import colour

NAME = 'Fractal Colour'
KIND = 'filter'
PARAMS = [
    P('mode', 'MODE', choices=['hue bust', 'palette', 'posterize']),
    P('beta', '1/f BETA (smooth)', 1.0, 4.0, 2.6, 0.05),
    P('scale', 'ZOOM', 0.2, 8.0, 1.0, 0.1),
    P('warp', 'DOMAIN WARP', 0.0, 1.0, 0.3, 0.01),
    P('amount', 'AMOUNT', 0.0, 1.0, 0.7, 0.01),
    P('palette', 'PALETTE', choices=list(colour.PALETTES)),
    P('bands', 'BANDS', 2, 24, 7),
]


def apply(img, p, rng):
    h, w = img.shape[:2]
    n = colour.pink2d(h, w, p['beta'], rng, 1 / p['scale'])
    if p['warp'] > 0:                                      # domain warp: look the noise up through more noise
        wx = colour.pink2d(h, w, p['beta'], rng, 1 / p['scale']) - 0.5
        wy = colour.pink2d(h, w, p['beta'], rng, 1 / p['scale']) - 0.5
        d = p['warp'] * 0.25 * min(h, w)
        yy, xx = np.mgrid[0:h, 0:w]
        n = n[np.clip((yy + wy * d).astype(int), 0, h - 1), np.clip((xx + wx * d).astype(int), 0, w - 1)]
    rgb = img[..., :3].astype(np.float32) / 255
    a = p['amount']
    if p['mode'] == 'hue bust':
        out = colour.rotate_hue(rgb, (n - 0.5) * 2 * np.pi * a * 1.5)
    elif p['mode'] == 'palette':
        lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
        pal = colour.cosine(n + lum * 0.5, p['palette'])
        out = rgb * (1 - a) + (pal * (0.35 + 0.65 * lum[..., None])) * a
    else:
        lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
        t = np.floor((lum + (n - 0.5) * a) * p['bands']) / p['bands']
        out = colour.cosine(t, p['palette'])
    res = img.copy()
    res[..., :3] = np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)
    return res
