"""Worn print dropout: the speckled screenprint look from the Hex girl accident.
Eats soft clumps + fine grain out of the layer's alpha; colours stay yours."""
import numpy as np
from PIL import Image, ImageFilter

NAME = 'Dropout'
KIND = 'filter'
PARAMS = [
    P('amount', 'AMOUNT', 0.0, 0.95, 0.4, 0.01),
    P('clump', 'CLUMP px', 0.0, 20.0, 5.0, 0.5),
    P('grain', 'GRAIN', 0.0, 1.0, 0.5, 0.01),
    P('edge', 'PROTECT LINES', 0.0, 1.0, 0.6, 0.01),
]


def apply(img, p, rng):
    h, w = img.shape[:2]
    soft = rng.random((h, w), np.float32)
    if p['clump'] > 0:
        im = Image.fromarray((soft * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(p['clump']))
        soft = np.asarray(im).astype(np.float32)
    soft = (soft - soft.min()) / max(1e-6, soft.max() - soft.min())
    field = (1 - p['grain']) * soft + p['grain'] * rng.random((h, w), np.float32)
    alpha = img[..., 3].astype(np.float32) / 255
    inside = alpha > 0.02
    cut = np.quantile(field[inside], p['amount']) if inside.any() else p['amount']
    keep = field >= cut
    if p['edge'] > 0:
        lum = img[..., :3].mean(axis=2) / 255
        keep |= (np.clip((0.35 - lum) / 0.35, 0, 1) * alpha) > (1 - p['edge'])
    out = img.copy()
    out[..., 3] = np.where(keep, img[..., 3], 0)
    return out
