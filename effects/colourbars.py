"""Colour bars: the SMPTE test card (75% bars, castellations, PLUGE row) or EBU bars, as a backdrop,
an overlay, or torn into the picture as glitch slices."""
import numpy as np

from gl import tvsignal as signal

NAME = 'Colour Bars'
KIND = 'filter'
PARAMS = [
    P('style', 'STYLE', choices=['smpte', 'ebu', 'rgb ramp']),
    P('mode', 'MODE', choices=['behind', 'slices', 'over', 'replace']),
    P('amount', 'AMOUNT', 0.0, 1.0, 0.5, 0.01),
    P('slices', 'SLICES', 1, 80, 14),
    P('sliceh', 'SLICE HEIGHT px', 1, 300, 40),
    P('shift', 'SLICE SHIFT px', 0, 1000, 120),
    P('key', 'SEE-THROUGH', choices=['white paper', 'transparent']),
]
B75 = [(191, 191, 191), (191, 191, 0), (0, 191, 191), (0, 191, 0), (191, 0, 191), (191, 0, 0), (0, 0, 191)]


def bars(h, w, style):
    out = np.zeros((h, w, 3), np.uint8)
    x = np.arange(w)
    if style == 'rgb ramp':
        t = x / max(1, w - 1)
        for k, (y0, y1) in enumerate(((0, .25), (.25, .5), (.5, .75), (.75, 1))):
            row = np.zeros((w, 3))
            if k < 3:
                row[:, k] = t * 255
            else:
                row[:] = (t * 255)[:, None]
            out[int(y0 * h):int(y1 * h)] = row.astype(np.uint8)
        return out
    if style == 'ebu':
        cols = [(255, 255, 255)] + [tuple(int(c / 191 * 255 * 0.75 + 0.5) for c in b) for b in B75[1:]] + [(0, 0, 0)]
        idx = np.minimum(x * 8 // w, 7)
        out[:] = np.array(cols, np.uint8)[idx][None]
        return out
    idx = np.minimum(x * 7 // w, 6)
    out[:int(h * .67)] = np.array(B75, np.uint8)[idx][None]
    cast = [(0, 0, 191), (19, 19, 19), (191, 0, 191), (19, 19, 19), (0, 191, 191), (19, 19, 19), (191, 191, 191)]
    out[int(h * .67):int(h * .75)] = np.array(cast, np.uint8)[idx][None]
    bottom = np.zeros((w, 3), np.uint8)
    seg = [(0, 5 / 28, (0, 33, 76)), (5 / 28, 10 / 28, (255, 255, 255)), (10 / 28, 15 / 28, (50, 0, 106)),
           (15 / 28, 20 / 28, (19, 19, 19)), (20 / 28, 21.5 / 28, (9, 9, 9)), (21.5 / 28, 23 / 28, (19, 19, 19)),
           (23 / 28, 24.5 / 28, (29, 29, 29)), (24.5 / 28, 1, (19, 19, 19))]
    for a, b, c in seg:
        bottom[int(a * w):int(b * w)] = c
    out[int(h * .75):] = bottom[None]
    return out


def apply(img, p, rng):
    h, w = img.shape[:2]
    b = bars(h, w, p['style']).astype(np.float32) / 255
    rgb = img[..., :3].astype(np.float32) / 255
    al = signal.see_through(img, p['key'])
    a = p['amount']
    out = img.copy()
    if p['mode'] == 'behind':
        new = rgb * al + b * (1 - al)
        out[..., 3] = 255
    elif p['mode'] == 'over':
        new = rgb * (1 - a) + b * a
    elif p['mode'] == 'replace':
        new = b
        out[..., 3] = 255
    else:
        new = rgb.copy()
        for _ in range(p['slices']):
            sh = int(rng.integers(max(1, p['sliceh'] // 3), p['sliceh'] + 1))
            y = int(rng.integers(0, max(1, h - sh)))
            band = np.roll(b[y:y + sh], int(rng.integers(-p['shift'], p['shift'] + 1)), 1)
            m = 0.5 + 0.5 * a
            new[y:y + sh] = new[y:y + sh] * (1 - m) + band * m
            out[y:y + sh, :, 3] = np.maximum(out[y:y + sh, :, 3], int(255 * m))
    out[..., :3] = np.clip(new * 255 + 0.5, 0, 255).astype(np.uint8)
    return out
