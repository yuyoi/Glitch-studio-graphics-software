"""Sharpen: unsharp mask. Takes a blurred copy, finds what blur removed (the edges) and adds more of it back.
THRESHOLD leaves flat areas and fine noise alone so only real edges get crisper. 'luma only' sharpens brightness
without colour fringes. Stack it after VHS / CRT / JPEG / N64 when they got too soft."""
import numpy as np
from PIL import Image, ImageFilter

NAME = 'Sharpen'
KIND = 'filter'
CATEGORY = 'Tools'
PARAMS = [
    P('amount', 'AMOUNT', 0.0, 3.0, 1.0, 0.05),
    P('radius', 'RADIUS px', 0.3, 8.0, 1.2, 0.1),
    P('threshold', 'THRESHOLD', 0, 40, 3),
    P('mode', 'MODE', choices=['luma only', 'all colours']),
]


def apply(img, p, rng):
    rgb = img[..., :3].astype(np.float32)
    blur = np.asarray(Image.fromarray(np.ascontiguousarray(img[..., :3])).filter(
        ImageFilter.GaussianBlur(p['radius']))).astype(np.float32)
    detail = rgb - blur
    if p['mode'] == 'luma only':                       # same boost on R, G and B = no colour halos
        detail = (detail @ np.array([0.299, 0.587, 0.114], np.float32))[..., None].repeat(3, -1)
    mag = np.abs(detail).max(-1, keepdims=True)
    keep = np.clip((mag - p['threshold']) / max(1.0, p['threshold']), 0, 1) if p['threshold'] > 0 else 1.0
    out = img.copy()
    out[..., :3] = np.clip(rgb + detail * p['amount'] * keep, 0, 255).astype(np.uint8)
    return out
