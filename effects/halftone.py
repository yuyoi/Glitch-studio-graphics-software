"""Halftone: print-shop dots. CMYK screens at the classic angles (C 15, M 75, Y 0, K 45 degrees) for the
comic / newspaper moire, one-ink mono, or dots in each spot's own colour."""
import numpy as np

NAME = 'Halftone'
KIND = 'filter'
CATEGORY = 'Print'
PARAMS = [
    P('mode', 'MODE', choices=['cmyk', 'mono', 'colour dots']),
    P('cell', 'DOT GRID px', 3, 60, 10),
    P('angle', 'ANGLE (mono)', 0, 90, 45),
    P('shape', 'DOT SHAPE', choices=['circle', 'square', 'line']),
    P('gain', 'DOT GAIN', 0.5, 2.0, 1.0, 0.05),
    P('paper', 'PAPER', choices=['white', 'cream', 'transparent']),
]
PAPER = {'white': (1, 1, 1), 'cream': (0.96, 0.93, 0.84), 'transparent': (1, 1, 1)}


def screen(t, h, w, cell, deg, shape, gain):
    """t = ink amount 0..1 (h, w). Returns ink coverage 0/1 for one rotated dot screen."""
    th = np.radians(deg)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx * np.cos(th) + yy * np.sin(th)
    v = -xx * np.sin(th) + yy * np.cos(th)
    cu, cv = (np.floor(u / cell) + 0.5) * cell, (np.floor(v / cell) + 0.5) * cell
    sx = np.clip(cu * np.cos(th) - cv * np.sin(th), 0, w - 1).astype(int)       # cell centre back in the picture
    sy = np.clip(cu * np.sin(th) + cv * np.cos(th), 0, h - 1).astype(int)
    amt = np.clip(t[sy, sx] * gain, 0, 1)
    du, dv = (u - cu) / cell, (v - cv) / cell
    if shape == 'circle':
        return np.sqrt(du * du + dv * dv) < 0.71 * np.sqrt(amt)
    if shape == 'square':
        return np.maximum(abs(du), abs(dv)) < 0.5 * np.sqrt(amt)
    return abs(dv) < 0.5 * amt


def apply(img, p, rng):
    h, w = img.shape[:2]
    rgb = img[..., :3].astype(np.float32) / 255
    al = img[..., 3].astype(np.float32) / 255
    rgb = rgb * al[..., None] + (1 - al[..., None])
    paper = np.array(PAPER[p['paper']], np.float32)
    out = np.ones((h, w, 3), np.float32) * paper
    c, sh, g = p['cell'], p['shape'], p['gain']
    if p['mode'] == 'cmyk':
        k = 1 - rgb.max(-1)
        cmy = (1 - rgb - k[..., None]) / np.maximum(1 - k[..., None], 1e-4)
        for t, deg, ink in ((cmy[..., 0], 15, (0, 0.68, 0.94)), (cmy[..., 1], 75, (0.93, 0.0, 0.55)),
                            (cmy[..., 2], 0, (1.0, 0.94, 0.0)), (k, 45, (0.08, 0.08, 0.1))):
            dots = screen(t, h, w, c, deg, sh, g)
            out = np.where(dots[..., None], out * np.array(ink, np.float32), out)
    elif p['mode'] == 'mono':
        lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
        dots = screen(1 - lum, h, w, c, p['angle'], sh, g)
        out = np.where(dots[..., None], np.float32(0.07), out)
    else:
        lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
        dots = screen(1 - lum * 0.85, h, w, c, p['angle'], sh, g)
        out = np.where(dots[..., None], rgb, out)
    res = img.copy()
    res[..., :3] = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
    if p['paper'] == 'transparent':
        ink = np.abs(out - paper).sum(-1) > 0.02
        res[..., 3] = np.where(ink, 255, 0)
    else:
        res[..., 3] = 255
    return res
