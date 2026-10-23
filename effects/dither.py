"""Lo-fi colour: chunky pixels, few colour levels, ordered (Bayer) dither like old consoles."""
import numpy as np

NAME = 'Dither'
KIND = 'filter'
CATEGORY = 'Pixel'
PARAMS = [
    P('pixel', 'PIXEL SIZE', 1, 32, 2),
    P('levels', 'LEVELS', 2, 16, 4),
    P('dither', 'DITHER', 0.0, 1.0, 0.7, 0.01),
    P('matrix', 'MATRIX', choices=['bayer 4', 'bayer 8', 'noise']),
    P('mono', 'COLOUR', choices=['colour', 'mono']),
]


def bayer(n):
    m = np.array([[0, 2], [3, 1]])
    while m.shape[0] < n:
        m = np.block([[4 * m, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
    return (m + 0.5) / m.size - 0.5


def apply(img, p, rng):
    h, w = img.shape[:2]
    s = p['pixel']
    small = img[::s, ::s].astype(np.float32) / 255
    sh, sw = small.shape[:2]
    if p['matrix'] == 'noise':
        t = rng.random((sh, sw), np.float32) - 0.5
    else:
        b = bayer(4 if p['matrix'] == 'bayer 4' else 8)
        t = np.tile(b, (sh // b.shape[0] + 1, sw // b.shape[1] + 1))[:sh, :sw]
    rgb = small[..., :3]
    if p['mono'] == 'mono':
        rgb = np.repeat((rgb @ np.array([0.299, 0.587, 0.114], np.float32))[..., None], 3, 2)
    L = p['levels'] - 1
    small[..., :3] = np.clip(np.floor(rgb * L + 0.5 + t[..., None] * p['dither']) / L, 0, 1)
    out = (small * 255 + 0.5).astype(np.uint8)
    return np.ascontiguousarray(np.repeat(np.repeat(out, s, 0), s, 1)[:h, :w])
