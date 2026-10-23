"""Colour maths shared by brushes and filters.

- golden-ratio hue steps: each new hue lands in the biggest gap left so far (most evenly spread colours)
- Voss-McCartney pink (1/f) noise: drifts like nature does, between boring smooth and harsh random
- cosine palettes (Inigo Quilez): a + b*cos(2pi(c*t + d)) gives smooth looping gradients
- hue rotation around the grey axis (Rodrigues): turns colours without changing their brightness much
- spectral 1/f^beta noise: white noise shaped in the Fourier domain; beta near 2-3 matches the
  fractal statistics of clouds, coastlines and the Pollock/Taylor "most liked" fractal dimension 1.3-1.5
"""
import numpy as np

PHI = 0.6180339887498949
GOLDEN_ANGLE = np.pi * (3 - np.sqrt(5))          # 137.5 degrees, sunflower seeds

PALETTES = {                                      # name: (a, b, c, d)
    'rainbow': ((.5, .5, .5), (.5, .5, .5), (1, 1, 1), (0, .33, .67)),
    'vapor': ((.5, .5, .5), (.5, .5, .5), (1, 1, .5), (.8, .9, .3)),
    'acid': ((.5, .5, .5), (.5, .5, .5), (2, 1, 0), (.5, .2, .25)),
    'sunset': ((.5, .5, .5), (.5, .5, .5), (1, 1, 1), (0, .1, .2)),
    'ice': ((.8, .5, .4), (.2, .4, .2), (2, 1, 1), (0, .25, .25)),
    'hexgirl': ((.45, .45, .7), (.35, .3, .3), (1, 1, 1), (.55, .62, .72)),
    'toxic': ((.5, .5, .5), (.5, .5, .5), (1, .7, .4), (0, .15, .2)),
}


def cosine(t, name='rainbow'):
    a, b, c, d = (np.array(v, np.float32) for v in PALETTES[name])
    t = np.asarray(t, np.float32)[..., None]
    return np.clip(a + b * np.cos(2 * np.pi * (c * t + d)), 0, 1)


def hsv(h, s=0.85, v=1.0):
    """Vectorised HSV -> RGB floats 0..1."""
    h = np.asarray(h, np.float32) % 1
    s = np.broadcast_to(np.asarray(s, np.float32), h.shape)
    v = np.broadcast_to(np.asarray(v, np.float32), h.shape)
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1)


def rotate_hue(rgb, angle):
    """rgb floats 0..1 (...,3), angle radians (scalar or per pixel)."""
    k = np.float32(1 / np.sqrt(3))
    c, s = np.cos(angle), np.sin(angle)
    c, s = np.asarray(c, np.float32)[..., None], np.asarray(s, np.float32)[..., None]
    v = rgb.astype(np.float32) - 0.5
    kv = v.sum(-1, keepdims=True) * k
    cross = np.stack([v[..., 2] - v[..., 1], v[..., 0] - v[..., 2], v[..., 1] - v[..., 0]], -1) * k   # k x v
    out = v * c + cross * s + k * kv * (1 - c)
    return np.clip(out + 0.5, 0, 1)


def pink2d(h, w, beta=2.0, rng=None, scale=1.0):
    """2-D noise with a 1/f^beta power spectrum, normalised to 0..1."""
    rng = rng or np.random.default_rng()
    white = rng.standard_normal((h, w)).astype(np.float32)
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy) * scale
    f[0, 0] = 1
    spec = np.fft.rfft2(white) / f ** (beta / 2)
    spec[0, 0] = 0
    n = np.fft.irfft2(spec, s=(h, w)).astype(np.float32)
    lo, hi = np.percentile(n, (1, 99))
    return np.clip((n - lo) / max(1e-6, hi - lo), 0, 1)


class Voss:
    """Voss-McCartney 1/f sequence: call next() for a value in 0..1 that drifts like pink noise."""

    def __init__(self, rng, rows=8):
        self.rng, self.rows = rng, rows
        self.v = rng.random(rows)
        self.n = 0

    def next(self):
        self.n += 1
        z = (self.n & -self.n).bit_length() - 1          # trailing zeros: which row to refresh
        if z < self.rows:
            self.v[z] = self.rng.random()
        return float(self.v.mean())
