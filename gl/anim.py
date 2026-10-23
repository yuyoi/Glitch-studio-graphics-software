"""GIF mode: the picture becomes a short loop. Each animation step is a filter (+ settings, + optional mask);
every frame re-rolls the random ones and sweeps chosen settings A -> B -> A, so the loop closes seamlessly."""
import math, os, shutil, subprocess

import numpy as np
from PIL import Image

from . import effects


def step_values(m, st, t):
    v = effects.defaults(m)
    v.update({k: x for k, x in st['params'].items() if k in v})
    q = {p['key']: p for p in m.PARAMS}
    for k, (a, b) in st.get('sweep', {}).items():
        if k in q and 'choices' not in q[k]:
            x = a + (b - a) * (1 - math.cos(2 * math.pi * t)) / 2           # there and back: the loop closes
            v[k] = int(round(x)) if q[k]['int'] else x
    return v


def fit_mask(mask, h, w):
    if mask is None:
        return None
    if mask.shape != (h, w):
        mask = np.asarray(Image.fromarray(mask).resize((w, h), Image.BILINEAR))
    return mask.astype(np.float32)[..., None] / 255


def render_frame(base, steps, fx, i, n, seed, px=None):
    out = base
    h, w = base.shape[:2]
    t = i / n
    for k, st in enumerate(steps):
        m = fx.get(st['effect'])
        if not m:
            continue
        rng = np.random.default_rng(seed + k * 7919 + (i * 104729 if st.get('reroll', True) else 0))
        vals = step_values(m, st, t)
        if px:
            vals = px(m, vals, out.shape)
        res = np.ascontiguousarray(m.apply(out, vals, rng), np.uint8)
        mk = fit_mask(st.get('mask'), h, w)
        if mk is not None:
            res = (out.astype(np.float32) * (1 - mk) + res.astype(np.float32) * mk + 0.5).astype(np.uint8)
        out = res
    return out


def scaled(img, s):
    if abs(s - 1) < 1e-3:
        return img
    h, w = img.shape[:2]
    return np.asarray(Image.fromarray(img).resize((max(2, int(w * s)), max(2, int(h * s))), Image.LANCZOS))


def describe(step, fx):
    m = fx.get(step['effect'])
    name = m.NAME if m else step['effect'] + ' (missing)'
    bits = []
    if step.get('reroll', True):
        bits.append('⟳ re-roll')
    for k, (a, b) in step.get('sweep', {}).items():
        bits.append('~%s %s→%s' % (k, round(a, 2), round(b, 2)))
    if step.get('mask') is not None:
        bits.append('masked')
    return '%s  %s' % (name, '  '.join(bits))


def export_mp4(frames_iter, path, fps, w, h, loops=1, progress=None):
    ff = shutil.which('ffmpeg')
    if not ff:
        raise RuntimeError('ffmpeg not found (winget install Gyan.FFmpeg)')
    w2, h2 = w - w % 2, h - h % 2
    cmd = [ff, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (w2, h2),
           '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17',
           '-preset', 'medium', '-movflags', '+faststart', path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    frames = []
    for k, fr in enumerate(frames_iter):
        rgb = composite_black(fr)[:h2, :w2]
        frames.append(rgb.tobytes())
        pr.stdin.write(frames[-1])
        if progress:
            progress(k)
    for _ in range(loops - 1):
        for b in frames:
            pr.stdin.write(b)
    pr.stdin.close()
    if pr.wait() != 0:
        raise RuntimeError('ffmpeg failed')


def export_gif(frames_iter, path, fps, progress=None):
    ims = []
    for k, fr in enumerate(frames_iter):
        ims.append(Image.fromarray(composite_black(fr)).quantize(256, method=Image.Quantize.MEDIANCUT,
                                                                 dither=Image.Dither.FLOYDSTEINBERG))
        if progress:
            progress(k)
    tmp = path + '.tmp.gif'
    ims[0].save(tmp, save_all=True, append_images=ims[1:], duration=int(round(1000 / fps)), loop=0, disposal=1)
    os.replace(tmp, path)


def composite_black(fr):
    a = fr[..., 3:4].astype(np.float32) / 255
    return np.ascontiguousarray((fr[..., :3].astype(np.float32) * a + 0.5).astype(np.uint8))
