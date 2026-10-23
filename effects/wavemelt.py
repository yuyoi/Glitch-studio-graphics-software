"""Wave / Melt: bends the picture. Sine waves with 1/f wobble, a melting drip that pulls columns down,
a swirl around a point, or ripples like a stone in water."""
import numpy as np

NAME = 'Wave Melt'
KIND = 'filter'
PARAMS = [
    P('mode', 'MODE', choices=['wave', 'melt drip', 'swirl', 'ripple']),
    P('amount', 'AMOUNT px', 0, 400, 30),
    P('length', 'WAVELENGTH px', 4, 1000, 120),
    P('rough', '1/f ROUGHNESS', 0.0, 1.0, 0.3, 0.01),
    P('dir', 'DIRECTION', choices=['horizontal', 'vertical']),
    P('cx', 'CENTRE X', 0.0, 1.0, 0.5, 0.01),
    P('cy', 'CENTRE Y', 0.0, 1.0, 0.5, 0.01),
]


def walk(n, rng):
    w = np.cumsum(rng.standard_normal(n))
    w -= np.linspace(w[0], w[-1], n)
    return w / max(1e-6, np.abs(w).max())


def apply(img, p, rng):
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    A, L = p['amount'], p['length']
    m = p['mode']
    if m == 'wave':
        if p['dir'] == 'horizontal':
            off = A * np.sin(2 * np.pi * yy / L) + A * p['rough'] * walk(h, rng)[:, None]
            sx, sy = xx - off, yy
        else:
            off = A * np.sin(2 * np.pi * xx / L) + A * p['rough'] * walk(w, rng)[None, :]
            sx, sy = xx, yy - off
        sx, sy = sx % w, sy % h
    elif m == 'melt drip':
        drip = np.abs(walk(w, rng) * (1 - p['rough']) + rng.standard_normal(w) * p['rough'] * 0.3)
        drip = np.convolve(drip, np.ones(max(1, int(L / 20))) / max(1, int(L / 20)), 'same')
        sx, sy = xx, np.clip(yy - A * drip[None, :] * (yy / h) ** 0.7, 0, h - 1)
    else:
        cx, cy = p['cx'] * w, p['cy'] * h
        dx, dy = xx - cx, yy - cy
        r = np.sqrt(dx * dx + dy * dy)
        if m == 'swirl':
            t = np.radians(A) * np.exp(-r / L)
            c, s = np.cos(t), np.sin(t)
            sx, sy = cx + dx * c - dy * s, cy + dx * s + dy * c
        else:
            k = A * 0.2 * np.sin(2 * np.pi * r / L) / np.maximum(r, 1)
            sx, sy = xx + dx * k, yy + dy * k
        sx, sy = np.clip(sx, 0, w - 1), np.clip(sy, 0, h - 1)
    return img[sy.astype(int), sx.astype(int)]
