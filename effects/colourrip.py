"""Colour Rip: the Hex girl accident on purpose. The picture is split into colour plates (k-means
clustering finds the main colours), then every plate is printed on its own like a screenprint /
risograph: slightly off register, torn where it meets other colours, with speckled grain.
Holes follow your shapes, so it reads as deliberate.

COLOURS  original = each plate keeps your real pixels;  flat = one ink per plate (riso look)
PAPER    white = holes show paper;  transparent = holes are see-through (put anything behind)
"""
import numpy as np
from PIL import Image, ImageFilter

NAME = 'Colour Rip'
KIND = 'filter'
CATEGORY = 'Print'
PARAMS = [
    P('plates', 'PLATES (colours)', 2, 12, 6),
    P('shift', 'MISREGISTER px', 0, 40, 4),
    P('tear', 'EDGE TEAR', 0.0, 1.0, 0.55, 0.01),
    P('width', 'TEAR WIDTH px', 1, 30, 6),
    P('clump', 'TEAR CLUMPS', 0.0, 1.0, 0.4, 0.01),
    P('grain', 'INK GRAIN', 0.0, 0.8, 0.12, 0.01),
    P('colours', 'COLOURS', choices=['original', 'flat']),
    P('paper', 'PAPER', choices=['white', 'transparent']),
    P('lines', 'PROTECT LINES', choices=['yes', 'no']),
]


def blur(m, r):
    im = Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255


def kmeans(px, k, rng, iters=10):
    lum = px @ np.array([0.299, 0.587, 0.114], np.float32)
    order = np.argsort(lum)
    c = px[order[np.linspace(0, len(px) - 1, k).astype(int)]].copy()      # start spread from dark to light
    for _ in range(iters):
        lab = ((px[:, None, :] - c[None]) ** 2).sum(-1).argmin(1)
        for j in range(k):
            sel = px[lab == j]
            if len(sel):
                c[j] = sel.mean(0)
    return c


def apply(img, p, rng):
    h, w = img.shape[:2]
    rgb = img[..., :3].astype(np.float32) / 255
    alpha = img[..., 3] > 8
    flat = rgb.reshape(-1, 3)
    pick = np.flatnonzero(alpha.ravel())
    if len(pick) == 0:
        return img.copy()
    sample = flat[rng.choice(pick, min(len(pick), 30000), replace=False)]
    k = p['plates']
    cent = kmeans(sample, k, rng)
    lab = np.empty(h * w, np.int16)
    for s in range(0, h * w, 400000):                                      # chunks keep memory small
        lab[s:s + 400000] = ((flat[s:s + 400000, None, :] - cent[None]) ** 2).sum(-1).argmin(1)
    lab = lab.reshape(h, w)
    lum = cent @ np.array([0.299, 0.587, 0.114], np.float32)
    order = np.argsort(-lum)                                               # print light inks first, dark last

    if p['paper'] == 'white':
        canvas = np.ones((h, w, 3), np.float32)
        cov = np.ones((h, w), bool)
    else:
        canvas = np.zeros((h, w, 3), np.float32)
        cov = np.zeros((h, w), bool)
    fine = rng.random((h, w), np.float32)
    clumpy = blur(rng.random((h, w), np.float32), 3)
    clumpy = (clumpy - clumpy.min()) / max(1e-6, clumpy.max() - clumpy.min())
    noise = fine * (1 - p['clump']) + clumpy * p['clump']
    for j in order:
        m = (lab == j) & alpha
        if not m.any():
            continue
        is_line = p['lines'] == 'yes' and lum[j] < 0.22
        keep = m.copy()
        if not is_line:
            inner = blur(m.astype(np.float32), p['width'])                 # < 1 near the plate's edges
            edge = np.clip((1 - inner) * 2.2, 0, 1)
            keep &= ~(noise < edge * p['tear'])
            if p['grain'] > 0:
                keep &= rng.random((h, w), np.float32) > p['grain']
        ink = np.broadcast_to(cent[j], rgb.shape) if p['colours'] == 'flat' else rgb
        if p['shift'] and not is_line:
            dy, dx = rng.integers(-p['shift'], p['shift'] + 1, 2)
            keep = np.roll(keep, (dy, dx), (0, 1))
            ink = np.roll(ink, (dy, dx), (0, 1))
        canvas[keep] = ink[keep]
        cov |= keep
    out = img.copy()
    out[..., :3] = (np.clip(canvas, 0, 1) * 255 + 0.5).astype(np.uint8)
    out[..., 3] = np.where(cov, 255, 0).astype(np.uint8)
    return out
