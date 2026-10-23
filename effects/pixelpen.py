"""Plain hard square pixel pen / eraser, for cleanup."""
NAME = 'Pixel Pen'
KIND = 'brush'
PARAMS = [
    P('size', 'SIZE', 1, 256, 10),
    P('press', 'PRESSURE>SIZE', 0.0, 1.0, 0.7, 0.01),
    P('grid', 'SNAP TO GRID', choices=['off', 'on']),
]


def size(p, pr):
    return max(1, p['size'] * (1 - p['press'] + p['press'] * pr))


def spacing(p, pr):
    return max(1.0, size(p, pr) * 0.3)


def dab(ctx, x, y, pr, ang):
    s = size(ctx.p, pr)
    ctx.square(x, y, s, grid=round(s) if ctx.p['grid'] == 'on' else 0)


def outline(p):
    return 'rect', p['size'], p['size']
