"""VHS / bad cable: wobbly scan lines (1/f jitter), colour bleeding sideways (the tape stores colour at a
fraction of the brightness resolution), tracking bands, head-switching tear at the bottom, interlace comb, faded colour."""
import numpy as np

from gl import tvsignal as signal

NAME = 'VHS / Cable'
KIND = 'filter'
PARAMS = [
    P('jitter', 'LINE WOBBLE px', 0, 60, 6),
    P('rough', 'WOBBLE ROUGHNESS', 0.0, 1.0, 0.3, 0.01),
    P('bleed', 'COLOUR BLEED px', 0, 60, 10),
    P('cshift', 'COLOUR SHIFT px', -40, 40, 6),
    P('bands', 'TRACKING BANDS', 0, 12, 2),
    P('bandh', 'BAND HEIGHT px', 2, 120, 16),
    P('head', 'HEAD SWITCH TEAR', 0.0, 0.1, 0.02, 0.005),
    P('comb', 'INTERLACE COMB px', 0, 12, 0),
    P('fade', 'TAPE FADE', 0.0, 1.0, 0.25, 0.01),
]
YIQ = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]], np.float32)


def pink1d(n, rng):
    """Row wobble: a random walk (smooth) mixed with white noise (rough) is close enough to 1/f."""
    walk = np.cumsum(rng.standard_normal(n))
    walk -= np.linspace(walk[0], walk[-1], n)
    return walk / max(1e-6, np.abs(walk).max())


def apply(img, p, rng):
    h, w = img.shape[:2]
    out = img.copy()
    off = pink1d(h, rng) * p['jitter'] * (1 - p['rough']) + rng.standard_normal(h) * p['jitter'] * p['rough'] * 0.3
    if p['comb']:
        off[1::2] += p['comb']
    bands = []
    for _ in range(p['bands']):
        y = int(rng.integers(0, h))
        bh = int(rng.integers(max(2, p['bandh'] // 2), p['bandh'] + 1))
        off[y:y + bh] += rng.uniform(-1, 1) * max(20, p['jitter'] * 4) + rng.standard_normal(min(bh, h - y)) * 6
        bands.append((y, bh))
    ht = int(h * p['head'])
    if ht:
        off[h - ht:] += np.linspace(0, w * 0.15, ht) * rng.choice([-1, 1])
    xs = (np.arange(w)[None, :] - off.astype(int)[:, None]) % w
    out = np.take_along_axis(out, xs[..., None].repeat(4, 2), 1)

    rgb = out[..., :3].astype(np.float32) / 255
    yiq = rgb @ YIQ.T
    if p['bleed'] or p['cshift']:
        c = signal.hblur(yiq[..., 1:], 1 + p['bleed'])
        yiq[..., 1:] = np.roll(c, p['cshift'], 1)
    yiq[..., 1:] *= 1 - p['fade'] * 0.6
    rgb = yiq @ np.linalg.inv(YIQ).T
    if p['fade']:
        rgb = rgb * (1 - p['fade'] * 0.15) + np.array([0.06, 0.03, -0.02], np.float32) * p['fade'] + 0.04 * p['fade']
    for y, bh in bands:                                   # tracking noise inside the bands
        y1 = min(h, y + bh)
        s = signal.snow(y1 - y, w, rng, 1, 0.8, 0.1)
        rgb[y:y1] = rgb[y:y1] * 0.45 + s * 0.55 + 0.08
    if ht:
        s = signal.snow(ht, w, rng, 1, 0.9, 0.2)
        rgb[h - ht:] = rgb[h - ht:] * 0.5 + s * 0.5
    out[..., :3] = np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8)
    return out
