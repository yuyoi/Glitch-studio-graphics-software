"""Square pixel dots laid along the stroke, in the direction you draw (the leg-stripe look).
In ERASE mode it punches the dots out of the layer instead."""
import math

NAME = 'Dot Line'
KIND = 'brush'
PARAMS = [
    P('size', 'DOT SIZE', 1, 64, 7),
    P('gap', 'GAP (x dot)', 1.0, 8.0, 2.2, 0.1),
    P('rows', 'ROWS', 1, 8, 1),
    P('rowgap', 'ROW GAP px', 1, 128, 14),
    P('jitter', 'JITTER', 0.0, 1.0, 0.0, 0.01),
    P('skip', 'DROPOUT', 0.0, 0.9, 0.0, 0.01),
    P('press', 'PRESSURE>SIZE', 0.0, 1.0, 0.35, 0.01),
    P('grid', 'SNAP TO GRID', choices=['off', 'on']),
]


def size(p, pr):
    return max(1, p['size'] * (1 - p['press'] + p['press'] * pr))


def spacing(p, pr):
    return size(p, pr) * p['gap']


def dab(ctx, x, y, pr, ang):
    p = ctx.p
    s = size(p, pr)
    nx, ny = -math.sin(ang), math.cos(ang)            # across the stroke
    for i in range(p['rows']):
        if p['skip'] and ctx.rng.random() < p['skip']:
            continue
        off = (i - (p['rows'] - 1) / 2) * p['rowgap']
        j = p['jitter'] * s
        jx, jy = (ctx.rng.uniform(-j, j), ctx.rng.uniform(-j, j)) if j else (0, 0)
        ctx.square(x + nx * off + jx, y + ny * off + jy, s, grid=round(s) if p['grid'] == 'on' else 0)


def outline(p):
    return 'rect', p['size'], (p['rows'] - 1) * p['rowgap'] + p['size']
