"""Kaleidoscope: folds the picture into N mirrored wedges around a centre point. Symmetry is one of the
most reliable things the eye reads as beautiful; 6 and 8 wedges feel like snowflakes and mandalas."""
import numpy as np

NAME = 'Kaleidoscope'
KIND = 'filter'
CATEGORY = 'Maths'
PARAMS = [
    P('n', 'WEDGES', 2, 24, 6),
    P('mode', 'MODE', choices=['mirror', 'rotate']),
    P('turn', 'TURN degrees', 0, 360, 0),
    P('zoom', 'ZOOM', 0.2, 4.0, 1.0, 0.05),
    P('cx', 'CENTRE X', 0.0, 1.0, 0.5, 0.01),
    P('cy', 'CENTRE Y', 0.0, 1.0, 0.5, 0.01),
    P('edge', 'OUTSIDE', choices=['mirror', 'wrap', 'clamp']),
]


def apply(img, p, rng):
    h, w = img.shape[:2]
    cx, cy = p['cx'] * w, p['cy'] * h
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    r = np.sqrt(dx * dx + dy * dy) / p['zoom']
    t = np.arctan2(dy, dx) - np.radians(p['turn'])
    wedge = 2 * np.pi / p['n']
    t = np.mod(t, wedge)
    if p['mode'] == 'mirror':
        t = np.where(t > wedge / 2, wedge - t, t)
    t += np.radians(p['turn'])
    sx, sy = cx + r * np.cos(t), cy + r * np.sin(t)
    if p['edge'] == 'wrap':
        sx, sy = sx % w, sy % h
    elif p['edge'] == 'mirror':
        sx = np.abs((sx + w) % (2 * w) - w)
        sy = np.abs((sy + h) % (2 * h) - h)
    sx, sy = np.clip(sx, 0, w - 1), np.clip(sy, 0, h - 1)
    return img[sy.astype(int), sx.astype(int)]
