"""Pixel Stretch: picks a start pixel in each column (or row) and smears it to the edge, like a frozen
scan line. Start where it gets bright, where it gets dark, or at random."""
import numpy as np

NAME = 'Pixel Stretch'
KIND = 'filter'
CATEGORY = 'Distort'
PARAMS = [
    P('dir', 'DIRECTION', choices=['down', 'up', 'right', 'left']),
    P('start', 'START AT', choices=['bright', 'dark', 'random']),
    P('thresh', 'THRESHOLD', 0.0, 1.0, 0.7, 0.01),
    P('chance', 'COLUMNS HIT', 0.0, 1.0, 0.5, 0.01),
    P('length', 'MAX LENGTH px (0=edge)', 0, 3000, 0),
    P('band', 'COLUMN GROUPS px', 1, 64, 1),
]


def apply(img, p, rng):
    d = p['dir']
    a = {'down': img, 'up': img[::-1], 'right': img.transpose(1, 0, 2), 'left': img.transpose(1, 0, 2)[::-1]}[d]
    h, w = a.shape[:2]
    lum = (a[..., :3].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)) / 255
    if p['start'] == 'bright':
        hit = (lum > p['thresh']) & (a[..., 3] > 0)
    elif p['start'] == 'dark':
        hit = (lum < 1 - p['thresh']) & (a[..., 3] > 0)
    else:
        hit = rng.random((h, w)) < 0.002 + (1 - p['thresh']) * 0.01
    start = np.where(hit.any(0), hit.argmax(0), h)
    band = p['band']
    groups = (np.arange(w) // band)
    on = rng.random(groups.max() + 1) < p['chance']
    start = np.where(on[groups], start, h)
    if band > 1:                                                     # columns in a group share one start
        g = np.minimum.reduceat(start, np.arange(0, w, band))
        start = np.where(on[groups], g[groups], h)
    y = np.arange(h)[:, None]
    stop = h if p['length'] == 0 else start + p['length']
    sy = np.where((y >= start[None]) & (y < stop if np.ndim(stop) == 0 else y < stop[None]), start[None], y)
    out = a[np.clip(sy, 0, h - 1), np.arange(w)[None]]
    return np.ascontiguousarray({'down': out, 'up': out[::-1], 'right': out.transpose(1, 0, 2),
                                 'left': out[::-1].transpose(1, 0, 2)}[d])
