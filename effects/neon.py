"""Neon Edges: finds the edges (Sobel gradient) and colours each one by the direction it runs, so curves
sweep through a cosine palette, then adds a glow. Neon sign, Tron grid, blacklight poster."""
import numpy as np
from PIL import Image, ImageFilter

from gl import colour

NAME = 'Neon Edges'
KIND = 'filter'
PARAMS = [
    P('mode', 'MODE', choices=['neon on black', 'over picture', 'edges only']),
    P('thresh', 'EDGE THRESHOLD', 0.0, 1.0, 0.15, 0.01),
    P('thick', 'LINE THICKNESS', 0, 6, 1),
    P('glow', 'GLOW', 0.0, 3.0, 1.2, 0.05),
    P('radius', 'GLOW RADIUS', 1, 40, 8),
    P('palette', 'PALETTE', choices=list(colour.PALETTES)),
    P('spin', 'COLOUR BY', choices=['edge direction', 'position', 'one colour']),
]


def blur(a, r):
    out = np.empty_like(a)
    for c in range(a.shape[2]):
        im = Image.fromarray((np.clip(a[..., c], 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
        out[..., c] = np.asarray(im).astype(np.float32) / 255
    return out


def apply(img, p, rng):
    h, w = img.shape[:2]
    a = img[..., 3:4].astype(np.float32) / 255
    lum = ((img[..., :3].astype(np.float32) / 255) * a + (1 - a)) @ np.array([0.299, 0.587, 0.114], np.float32)
    pad = np.pad(lum, 1, mode='edge')
    gx = (pad[:-2, 2:] + 2 * pad[1:-1, 2:] + pad[2:, 2:]) - (pad[:-2, :-2] + 2 * pad[1:-1, :-2] + pad[2:, :-2])
    gy = (pad[2:, :-2] + 2 * pad[2:, 1:-1] + pad[2:, 2:]) - (pad[:-2, :-2] + 2 * pad[:-2, 1:-1] + pad[:-2, 2:])
    mag = np.sqrt(gx * gx + gy * gy) / 4
    edge = (mag > p['thresh']).astype(np.float32)
    if p['thick'] > 0:
        im = Image.fromarray((edge * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(p['thick'] * 2 + 1))
        edge = np.asarray(im).astype(np.float32) / 255
    if p['spin'] == 'edge direction':
        t = (np.arctan2(gy, gx) / np.pi + 1) / 2 * 2
    elif p['spin'] == 'position':
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        t = (xx + yy) / (w + h) * 1.5
    else:
        t = np.full((h, w), 0.6, np.float32)
    col = colour.cosine(t, p['palette']) * edge[..., None]
    glow = blur(col, p['radius']) * p['glow'] if p['glow'] > 0 else 0
    neon = np.clip(col + glow, 0, 1)
    out = img.copy()
    if p['mode'] == 'neon on black':
        out[..., :3] = (neon * 255 + 0.5).astype(np.uint8)
        out[..., 3] = 255
    elif p['mode'] == 'over picture':
        base = img[..., :3].astype(np.float32) / 255
        out[..., :3] = (np.clip(base * 0.55 + neon, 0, 1) * 255 + 0.5).astype(np.uint8)
    else:
        out[..., :3] = (np.clip(neon / np.maximum(neon.max(-1, keepdims=True), 1e-3), 0, 1) * 255).astype(np.uint8)
        out[..., 3] = (np.clip(neon.max(-1), 0, 1) * 255).astype(np.uint8)
    return out
