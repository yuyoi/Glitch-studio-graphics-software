"""Pixel sort: pixels inside the brightness window get sorted along each row (or column)."""
import numpy as np

NAME = 'Pixel Sort'
KIND = 'filter'
CATEGORY = 'Data'
PARAMS = [
    P('dir', 'DIRECTION', choices=['horizontal', 'vertical']),
    P('lo', 'LOW', 0.0, 1.0, 0.25, 0.01),
    P('hi', 'HIGH', 0.0, 1.0, 0.85, 0.01),
    P('maxlen', 'MAX RUN px', 0, 2000, 0),
    P('order', 'ORDER', choices=['dark to light', 'light to dark']),
]


def apply(img, p, rng):
    a = img if p['dir'] == 'horizontal' else img.transpose(1, 0, 2)
    h, w = a.shape[:2]
    flat = np.ascontiguousarray(a).reshape(-1, 4)
    lum = (flat[:, 0] * 0.299 + flat[:, 1] * 0.587 + flat[:, 2] * 0.114) / 255
    lo, hi = sorted((p['lo'], p['hi']))
    m = (lum >= lo) & (lum <= hi) & (flat[:, 3] > 0)
    start = np.ones(m.size, bool)
    start[1:] = ~(m[1:] & m[:-1])
    start[::w] = True
    if p['maxlen'] > 0:                                   # cut long runs into pieces
        seg = np.cumsum(start)
        first = np.flatnonzero(start)
        pos = np.arange(m.size) - first[seg - 1]
        start |= (pos > 0) & (pos % p['maxlen'] == 0)
    seg = np.cumsum(start)
    key = -lum if p['order'] == 'light to dark' else lum
    order = np.lexsort((np.where(m, key, 0), seg))
    out = flat[order].reshape(h, w, 4)
    return np.ascontiguousarray(out if p['dir'] == 'horizontal' else out.transpose(1, 0, 2))
