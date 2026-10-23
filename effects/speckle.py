"""Square specks scattered fresh on every dab: no dragging, no smearing.
ERASE mode eats pixel holes (bit rot).

SCATTER:
  random     plain random points
  blue noise Mitchell's best-candidate: random but never clumped, the even "grain" the eye reads as calm
             (same idea as the retina's cone layout and print dithering)
  sunflower  golden-angle spiral (137.5 deg, Vogel's phyllotaxis model): seeds of a sunflower
  clumps     gaussian clump to the centre
"""
import math

import numpy as np

NAME = 'Speckle'
KIND = 'brush'
PARAMS = [
    P('area', 'AREA radius', 2, 600, 90),
    P('density', 'SPECKS / DAB', 1, 600, 45),
    P('dmin', 'SPECK MIN', 1, 32, 2),
    P('dmax', 'SPECK MAX', 1, 64, 6),
    P('spacing', 'SPACING (x area)', 0.1, 3.0, 0.5, 0.05),
    P('scatter', 'SCATTER', choices=['random', 'blue noise', 'sunflower', 'clumps']),
    P('press', 'PRESSURE>DENSITY', 0.0, 1.0, 0.5, 0.01),
    P('grid', 'SNAP TO GRID', choices=['off', 'on']),
]
GOLDEN = math.pi * (3 - math.sqrt(5))


def spacing(p, pr):
    return p['area'] * p['spacing']


def points(p, rng, n, r, ang):
    s = p['scatter']
    if s == 'sunflower':
        i = np.arange(n) + 0.5
        t = i * GOLDEN + ang
        d = r * np.sqrt(i / n)
        return np.stack([d * np.cos(t), d * np.sin(t)], 1)
    if s == 'clumps':
        return rng.normal(0, r / 3, (n, 2))
    a = rng.uniform(0, 2 * math.pi, (n * (8 if s == 'blue noise' else 1),))
    d = r * np.sqrt(rng.random(a.shape))
    cand = np.stack([d * np.cos(a), d * np.sin(a)], 1)
    if s != 'blue noise' or n < 2:
        return cand[:n]
    cand = cand.reshape(n, 8, 2)
    pts = [cand[0, 0]]
    for k in range(1, n):                                  # keep the candidate farthest from all kept points
        c = cand[k]
        dist = ((c[:, None, :] - np.array(pts)[None]) ** 2).sum(-1).min(1)
        pts.append(c[int(dist.argmax())])
    return np.array(pts)


def dab(ctx, x, y, pr, ang):
    p, rng = ctx.p, ctx.rng
    n = int(round(p['density'] * (1 - p['press'] + p['press'] * pr)))
    if n < 1:
        return
    lo, hi = sorted((p['dmin'], p['dmax']))
    rot = ang if p['scatter'] == 'sunflower' else 0
    for dx, dy in points(p, rng, n, p['area'], rot):
        s = int(rng.integers(lo, hi + 1))
        ctx.square(x + dx, y + dy, s, grid=s if p['grid'] == 'on' else 0)


def outline(p):
    return 'circle', p['area'] * 2, p['area'] * 2
