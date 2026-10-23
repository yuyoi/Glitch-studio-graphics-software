"""Effect plug-ins: every .py file in glitch_lab/effects/ is a brush or a filter.

A file needs:
    NAME   = 'Dot Line'
    KIND   = 'brush' or 'filter'
    PARAMS = [P('size', 'SIZE', 1, 64, 4), P('mode', 'MODE', choices=['a', 'b']), ...]
Brush:  spacing(p, pressure) -> pixels between dabs;  dab(ctx, x, y, pressure, angle)
Filter: apply(img, p, rng) -> new HxWx4 uint8 image  (img is the layer, straight alpha)
p is a dict of the current values. Sliders and presets come for free.
"""
import glob, importlib.util, math, os, traceback

import numpy as np

from . import colour

PHI_STEPS = colour.PHI * np.arange(4096)


def P(key, label, lo=0, hi=1, default=None, step=None, choices=None):
    if choices:
        return dict(key=key, label=label, choices=list(choices), default=default or choices[0])
    is_int = isinstance(lo, int) and isinstance(hi, int) and (step is None or float(step).is_integer())
    return dict(key=key, label=label, lo=lo, hi=hi, default=lo if default is None else default,
                step=step or (1 if is_int else (hi - lo) / 100), int=is_int)


def load(folder):
    """Returns (effects list, errors list). A broken file never stops the app."""
    found, errors = [], []
    for f in sorted(glob.glob(os.path.join(folder, '*.py'))):
        name = os.path.splitext(os.path.basename(f))[0]
        if name.startswith('_'):
            continue
        try:
            spec = importlib.util.spec_from_file_location('glitch_fx_' + name, f)
            m = importlib.util.module_from_spec(spec)
            m.P = P
            spec.loader.exec_module(m)
            assert m.KIND in ('brush', 'filter'), 'KIND must be brush or filter'
            m.ID = name
            m.PARAMS = list(getattr(m, 'PARAMS', []))
            found.append(m)
        except Exception:
            errors.append('%s: %s' % (name, traceback.format_exc(limit=1).strip().splitlines()[-1]))
    return found, errors


def defaults(m):
    return {q['key']: q['default'] for q in m.PARAMS}


COLOUR_MODES = ['pick', 'palette', 'random', 'rgb', 'bust', 'golden', 'drift']
RGB3 = np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255]], np.uint8)


class Ctx:
    """What a brush paints with. ctx.square() is the basic hard pixel stamp.

    Colour modes (every brush gets them for free):
      pick     the colour you chose
      palette  random pick from your palette swatches
      random   random RGB
      rgb      pure red / green / blue
      bust     takes the picture's own colours under the stamp and busts them (hue spin, channel swap, invert)
      golden   hue steps by the golden ratio: every new colour lands in the biggest gap (evenly spread rainbow)
      drift    hue wanders with 1/f pink noise (Voss-McCartney), the drift found in nature and music
    per_pixel: the mode picks a colour for every pixel instead of every stamp.
    """

    def __init__(self, arr, color, erase, params, rng, mode='pick', palette=None, per_pixel=False, sample=None):
        self.arr, self.color, self.erase, self.p, self.rng = arr, color, erase, params, rng
        self.h, self.w = arr.shape[:2]
        self.dirty = None
        self.mode, self.per_pixel = mode, per_pixel
        self.palette = np.array(palette or [color], np.uint8).reshape(-1, 3)
        self.sample = sample if sample is not None else arr          # what 'bust' reads (the visible picture)
        self.hue = float(rng.random())
        self.voss = colour.Voss(rng)
        self.drift_base = float(rng.random())

    def paint_colour(self, y0, y1, x0, x1):
        """uint8 colour for a stamp: shape (3,) or (h, w, 3)."""
        m, rng = self.mode, self.rng
        shape = (y1 - y0, x1 - x0) if self.per_pixel else ()
        if m == 'random':
            return rng.integers(0, 256, shape + (3,), dtype=np.uint8)
        if m == 'rgb':
            return RGB3[rng.integers(0, 3, shape)]
        if m == 'palette':
            return self.palette[rng.integers(0, len(self.palette), shape)]
        if m == 'golden':
            n = int(np.prod(shape)) if shape else 1
            h = (self.hue + PHI_STEPS[:n] if n <= len(PHI_STEPS) else self.hue + colour.PHI * np.arange(n)) % 1
            self.hue = float((self.hue + colour.PHI * n) % 1)
            return (colour.hsv(h.reshape(shape) if shape else h[0], 0.85, 1.0) * 255 + 0.5).astype(np.uint8)
        if m == 'drift':
            h = self.drift_base + self.voss.next() * 0.9
            if shape:
                h = h + rng.normal(0, 0.03, shape)
            return (colour.hsv(h, 0.8, 1.0) * 255 + 0.5).astype(np.uint8)
        if m == 'bust':
            r = max(6, 4 * (y1 - y0))                          # pull the colour from a torn-off spot nearby
            dy, dx = rng.integers(-r, r + 1, 2)
            ys = np.clip(np.arange(y0, y1) + dy, 0, self.h - 1)
            xs = np.clip(np.arange(x0, x1) + dx, 0, self.w - 1)
            src = self.sample[np.ix_(ys, xs)][..., :3].astype(np.float32) / 255
            lum = src.mean(-1, keepdims=True)
            src = np.clip(lum + (src - lum) * 2.2, 0, 1)      # saturation kick
            ang = rng.uniform(-np.pi, np.pi, shape if shape else ())
            out = colour.rotate_hue(src, ang)
            perm = rng.permutation(3)
            out = out[..., perm]
            if rng.random() < 0.25:
                out = 1 - out
            return (out * 255 + 0.5).astype(np.uint8)
        return np.array(self.color, np.uint8)

    def mark(self, x0, y0, x1, y1):
        d = self.dirty
        self.dirty = (x0, y0, x1, y1) if d is None else (min(d[0], x0), min(d[1], y0), max(d[2], x1), max(d[3], y1))

    def square(self, cx, cy, size, alpha=1.0, grid=0):
        s = max(1, int(round(size)))
        if grid:
            g = max(1, int(round(grid)))
            x0, y0 = int(math.floor(cx / g)) * g, int(math.floor(cy / g)) * g
        else:
            x0, y0 = int(math.floor(cx - s / 2 + 0.5)), int(math.floor(cy - s / 2 + 0.5))
        x1, y1 = min(self.w, x0 + s), min(self.h, y0 + s)
        x0, y0 = max(0, x0), max(0, y0)
        if x1 <= x0 or y1 <= y0:
            return
        r = self.arr[y0:y1, x0:x1]
        if alpha >= 1:
            if self.erase:
                r[..., 3] = 0
            else:
                r[..., :3] = self.paint_colour(y0, y1, x0, x1)
                r[..., 3] = 255
        else:
            oa = r[..., 3:4].astype(np.float32) / 255
            if self.erase:
                r[..., 3] = (oa[..., 0] * (1 - alpha) * 255 + 0.5).astype(np.uint8)
            else:
                na = alpha + oa * (1 - alpha)
                c = self.paint_colour(y0, y1, x0, x1).astype(np.float32)
                rgb = (c * alpha + r[..., :3].astype(np.float32) * oa * (1 - alpha)) / np.maximum(na, 1e-6)
                r[..., :3] = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
                r[..., 3] = (na[..., 0] * 255 + 0.5).astype(np.uint8)
        self.mark(x0, y0, x1, y1)


class Stroke:
    """Walks the pen path and calls the brush's dab() every spacing() pixels, in the drawing direction."""

    def __init__(self, mod, ctx):
        self.m, self.ctx = mod, ctx
        self.last = None
        self.need = 0.0
        self.started = False

    def to(self, x, y, pr):
        if self.last is None:
            self.last = (x, y, pr)
            return
        lx, ly, lp = self.last
        dx, dy = x - lx, y - ly
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return
        ang = math.atan2(dy, dx)
        if not self.started:                         # first dab waits for a direction
            self.m.dab(self.ctx, lx, ly, lp, ang)
            self.started = True
            self.need = max(0.5, self.m.spacing(self.ctx.p, lp))
        t = 0.0
        while dist - t >= self.need:
            t += self.need
            f = t / dist
            p = lp + (pr - lp) * f
            self.m.dab(self.ctx, lx + dx * f, ly + dy * f, p, ang)
            self.need = max(0.5, self.m.spacing(self.ctx.p, p))
        self.need -= dist - t
        self.last = (x, y, pr)

    def end(self):
        if not self.started and self.last is not None:   # a tap: one dab
            lx, ly, lp = self.last
            self.m.dab(self.ctx, lx, ly, lp, 0.0)
