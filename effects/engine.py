"""Game Engine: puts the picture INSIDE a little 3D world and renders it the way the console's hardware did,
with a real (tiny) software 3D rasteriser:

  PlayStation  affine texture mapping (textures warp and swim across big polygons), vertex snapping with jitter,
               no depth buffer (polygons sorted back to front), 15-bit colour with the PS1 dither, 320x240
  N64          perspective-correct but tiny blurry textures (4 KB texture memory), bilinear filtering,
               thick distance fog, the soft video filter, 320x240
  PS2          sharper bigger textures, depth buffer, haze, bloom, 640x448

SCENE: poster in a room, cut-out standing in a field (white paper becomes see-through), spinning cube,
floor (Mode 7 style), corridor (SPIN walks you down it: sweep SPIN 0 > 360 in GIF mode for an endless walk).
Then the frame goes through the Console filter's TV / screen simulation.
"""
import importlib.util, math, os

import numpy as np
from PIL import Image

from gl import colour, pixelart

NAME = 'Game Engine'
KIND = 'filter'
CATEGORY = 'Console'
ENGINES = {
    'PlayStation': dict(res=240, affine=True, zbuf=False, bilinear=False, tex=256, fog=(0.04, 0.03, 0.06), depth=31),
    'N64': dict(res=240, affine=False, zbuf=True, bilinear=True, tex=64, fog=(0.55, 0.6, 0.68), depth=31),
    'PS2': dict(res=448, affine=False, zbuf=True, bilinear=True, tex=512, fog=(0.32, 0.35, 0.42), depth=255),
}
PARAMS = [
    P('engine', 'ENGINE', choices=list(ENGINES)),
    P('scene', 'SCENE', choices=['poster room', 'cut-out in a field', 'spinning cube', 'floor (mode 7)', 'corridor']),
    P('spin', 'SPIN / WALK', 0, 360, 25),
    P('yaw', 'CAMERA TURN', -70, 70, 0),
    P('pitch', 'CAMERA HEIGHT', -40, 60, 8),
    P('dist', 'CAMERA DISTANCE', 0.3, 3.0, 1.0, 0.05),
    P('fov', 'FIELD OF VIEW', 30, 110, 65),
    P('fog', 'FOG', 0.0, 1.0, 0.45, 0.01),
    P('floor', 'FLOOR', choices=['default', 'checker', 'grass', 'stone', 'tiles', 'wood', 'sand', 'water', 'brick', 'your picture']),
    P('floorhue', 'FLOOR COLOUR (hue spin)', 0, 360, 0),
    P('floorbright', 'FLOOR BRIGHTNESS', 0.2, 2.0, 1.0, 0.05),
    P('walls', 'WALLS / CEILING', choices=['default', 'brick', 'stone', 'tiles', 'wood', 'checker', 'your picture']),
    P('wallhue', 'WALL COLOUR (hue spin)', 0, 360, 0),
    P('sky', 'SKY / FOG COLOUR', choices=['engine default', 'day', 'night', 'sunset', 'vapor', 'toxic', 'void', 'overcast', 'blood', 'underwater']),
    P('skyhue', 'SKY HUE SHIFT', 0, 360, 0),
    P('wobble', 'PS1 JITTER', 0.0, 1.0, 0.5, 0.01),
    P('texres', 'TEXTURE RES x', 0.25, 2.0, 1.0, 0.05),
    P('tess', 'POLYGON SPLIT', 1, 8, 2),
    P('light', 'LIGHTING', 0.0, 1.0, 0.6, 0.01),
    P('cutout', 'CUT-OUT (field scene)', choices=['white paper', 'transparent', 'none']),
    P('pixelate', 'TEXTURE SHRINK', choices=['pixel art (keeps lines)', 'k-centroid', 'blurry average']),
    P('screen', 'SCREEN', choices=['composite TV', 'RGB TV', 'RF TV', 'clean pixels']),
    P('scan', 'SCANLINES', 0.0, 1.0, 0.5, 0.01),
    P('curve', 'GLASS CURVE', 0.0, 0.3, 0.05, 0.01),
]
PS1_DITHER = np.array([[-4, 0, -3, 1], [2, -2, 3, -1], [-3, 1, -4, 0], [3, -1, 2, -2]], np.float32) / 8
_console = None


def console():
    global _console
    if _console is None:
        spec = importlib.util.spec_from_file_location('glitch_fx_console_for_engine',
                                                      os.path.join(os.path.dirname(os.path.abspath(__file__)), 'console.py'))
        m = importlib.util.module_from_spec(spec)
        m.P = P
        spec.loader.exec_module(m)
        _console = m
    return _console


# ------------------------------------------------------------------ textures
def proc_texture(kind, rng, n=64):
    yy, xx = np.mgrid[0:n, 0:n]
    noise = rng.random((n, n)).astype(np.float32)
    t = np.ones((n, n, 4), np.float32)
    if kind == 'checker':
        c = ((xx // 16 + yy // 16) % 2).astype(np.float32)[..., None]
        t[..., :3] = (0.62, 0.57, 0.5) * c + (0.36, 0.32, 0.3) * (1 - c)
        t[..., :3] *= (0.9 + noise * 0.2)[..., None]
    elif kind == 'brick':
        row = yy // 8
        off = (row % 2) * 8
        mortar = ((yy % 8) == 0) | (((xx + off) % 16) == 0)
        t[..., :3] = np.where(mortar[..., None], (0.55, 0.52, 0.48), (0.5, 0.22, 0.16))
        t[..., :3] *= (0.8 + noise * 0.35)[..., None]
    elif kind == 'grass':
        t[..., :3] = np.stack([0.2 + noise * 0.15, 0.45 + noise * 0.3, 0.12 + noise * 0.1], -1)
    elif kind == 'stone':
        cell = ((xx // 21 + (yy // 21) * 3) % 5).astype(np.float32) / 5
        crack = ((xx % 21) == 0) | ((yy % 21) == 0)
        g = 0.42 + cell[..., None] * 0.12 + noise[..., None] * 0.12
        t[..., :3] = np.where(crack[..., None], 0.2, g)
    elif kind == 'tiles':
        grout = ((xx % 16) < 1) | ((yy % 16) < 1)
        t[..., :3] = np.where(grout[..., None], (0.45, 0.45, 0.43), (0.86, 0.86, 0.84))
        t[..., :3] *= (0.95 + noise * 0.08)[..., None]
    elif kind == 'wood':
        plank = (yy // 11) % 6
        grain = np.sin(xx * 0.35 + plank * 2.1 + noise * 1.5) * 0.05
        seam = (yy % 11) == 0
        base = 0.42 + plank[..., None] * 0.025 + grain[..., None]
        t[..., :3] = np.where(seam[..., None], (0.18, 0.1, 0.05), base * np.array([1.0, 0.68, 0.42]))
    elif kind == 'sand':
        t[..., :3] = np.stack([0.78 + noise * 0.1, 0.68 + noise * 0.1, 0.45 + noise * 0.08], -1)
    elif kind == 'water':
        wave = np.sin(xx * 0.4 + np.sin(yy * 0.3) * 2) * 0.5 + 0.5
        t[..., :3] = np.stack([0.08 + wave * 0.08, 0.3 + wave * 0.15 + noise * 0.05, 0.55 + wave * 0.2], -1)
    else:                                               # dark ceiling
        t[..., :3] = (0.16 + noise[..., None] * 0.08)
    return np.clip(t, 0, 1)


def picture_texture(img, limit, cutout, how):
    h, w = img.shape[:2]
    s = min(1.0, limit / max(h, w))
    tw, th = max(4, int(w * s)), max(4, int(h * s))
    mode = {'pixel art (keeps lines)': 'pixel art', 'k-centroid': 'k-centroid', 'blurry average': 'average'}[how]
    t = (pixelart.downscale(img, tw, th, mode) if s < 1 else img).astype(np.float32) / 255
    if cutout == 'white paper':
        t[..., 3] *= (t[..., :3].min(-1) < 0.9).astype(np.float32)
    elif cutout == 'none':
        t[..., 3] = 1
    return t


def sample(tex, u, v, wrap, bilinear):
    th, tw = tex.shape[:2]
    if wrap:
        u, v = u % 1.0, v % 1.0
    else:
        u, v = np.clip(u, 0, 0.9999), np.clip(v, 0, 0.9999)
    x, y = u * tw - 0.5, v * th - 0.5
    if not bilinear:
        xi = np.clip(np.floor(x + 0.5).astype(int) % tw if wrap else np.floor(x + 0.5).astype(int), 0, tw - 1)
        yi = np.clip(np.floor(y + 0.5).astype(int) % th if wrap else np.floor(y + 0.5).astype(int), 0, th - 1)
        return tex[yi, xi]
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    if wrap:
        x0, y0, x1, y1 = x0 % tw, y0 % th, (x0 + 1) % tw, (y0 + 1) % th
    else:
        x0, y0 = np.clip(x0, 0, tw - 1), np.clip(y0, 0, th - 1)
        x1, y1 = np.clip(x0 + 1, 0, tw - 1), np.clip(y0 + 1, 0, th - 1)
    return (tex[y0, x0] * (1 - fx) * (1 - fy) + tex[y0, x1] * fx * (1 - fy) +
            tex[y1, x0] * (1 - fx) * fy + tex[y1, x1] * fx * fy)


# ------------------------------------------------------------------ scenes (quads: 4 corners, 4 uvs, texture, wrap)
def rot_y(p, a):
    c, s = math.cos(a), math.sin(a)
    return np.array([p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c])


def rot_x(p, a):
    c, s = math.cos(a), math.sin(a)
    return np.array([p[0], p[1] * c - p[2] * s, p[1] * s + p[2] * c])


def quad(corners, uvs, tex, wrap=False, sub=1):
    return ([np.array(c, np.float64) for c in corners], [np.array(u, np.float64) for u in uvs], tex, wrap, sub)


UV = [(0, 1), (1, 1), (1, 0), (0, 0)]             # bottom-left, bottom-right, top-right, top-left


def build(p, A):
    sc = p['scene']
    spin = math.radians(p['spin'])
    Q = []
    sky = True
    if sc == 'poster room':
        hw, d, hgt = max(3.5, A * 1.6 + 1.2), 9.0, 4.2
        Q.append(quad([(-hw, 0, 0), (hw, 0, 0), (hw, 0, d), (-hw, 0, d)], [(0, 0), (hw / 1.2, 0), (hw / 1.2, d / 1.2), (0, d / 1.2)], 'floor', True, 4))
        Q.append(quad([(-hw, hgt, d), (hw, hgt, d), (hw, hgt, 0), (-hw, hgt, 0)], [(0, 0), (4, 0), (4, 4), (0, 4)], 'ceiling', True))
        Q.append(quad([(-hw, 0, d), (hw, 0, d), (hw, hgt, d), (-hw, hgt, d)], [(0, hgt / 2), (2 * hw / 2, hgt / 2), (2 * hw / 2, 0), (0, 0)], 'wall', True))
        Q.append(quad([(-hw, 0, 0), (-hw, 0, d), (-hw, hgt, d), (-hw, hgt, 0)], [(0, hgt / 2), (d / 2, hgt / 2), (d / 2, 0), (0, 0)], 'wall', True))
        Q.append(quad([(hw, 0, d), (hw, 0, 0), (hw, hgt, 0), (hw, hgt, d)], [(0, hgt / 2), (d / 2, hgt / 2), (d / 2, 0), (0, 0)], 'wall', True))
        ph, pw = 2.9, 2.9 * A
        if pw > 2 * hw - 0.6:
            pw, ph = 2 * hw - 0.6, (2 * hw - 0.6) / A
        y0 = 0.7
        Q.append(quad([(-pw / 2, y0, d - 0.02), (pw / 2, y0, d - 0.02), (pw / 2, y0 + ph, d - 0.02), (-pw / 2, y0 + ph, d - 0.02)], UV, 'pic'))
        target, base_d, eye_h = np.array([0, y0 + ph / 2, d]), 4.6, 1.8
        sky = False
    elif sc == 'cut-out in a field':
        Q.append(quad([(-24, 0, -24), (24, 0, -24), (24, 0, 24), (-24, 0, 24)], [(0, 0), (12, 0), (12, 12), (0, 12)], 'floor', True, 18))
        ph, pw = 3.0, 3.0 * A
        corners = [(-pw / 2, 0, 0), (pw / 2, 0, 0), (pw / 2, ph, 0), (-pw / 2, ph, 0)]
        Q.append(quad([rot_y(c, spin) for c in corners], UV, 'pic'))
        target, base_d, eye_h = np.array([0, ph * 0.5, 0]), 7.5, 1.4
    elif sc == 'spinning cube':
        s = 1.3
        faces = [[(-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s)], [(s, -s, s), (-s, -s, s), (-s, s, s), (s, s, s)],
                 [(s, -s, -s), (s, -s, s), (s, s, s), (s, s, -s)], [(-s, -s, s), (-s, -s, -s), (-s, s, -s), (-s, s, s)],
                 [(-s, s, -s), (s, s, -s), (s, s, s), (-s, s, s)], [(-s, -s, s), (s, -s, s), (s, -s, -s), (-s, -s, -s)]]
        for f in faces:
            Q.append(quad([rot_x(rot_y(c, spin), math.radians(20)) + np.array([0, 2.0, 0]) for c in f], UV, 'pic'))
        Q.append(quad([(-30, 0, -30), (30, 0, -30), (30, 0, 30), (-30, 0, 30)], [(0, 0), (15, 0), (15, 15), (0, 15)], 'floor', True, 10))
        target, base_d, eye_h = np.array([0, 2.0, 0]), 6.0, 2.4
    elif sc == 'floor (mode 7)':
        hw, hd = 6.0 * A, 6.0
        corners = [(-hw, 0, -hd), (hw, 0, -hd), (hw, 0, hd), (-hw, 0, hd)]
        Q.append(quad([rot_y(c, spin) for c in corners], [(0, 1), (1, 1), (1, 0), (0, 0)], 'pic'))
        target, base_d, eye_h = np.array([0, 0, 1.5]), 8.0, 3.2
    else:                                               # corridor: walking forward is SPIN
        L, w, hgt = 40.0, 2.2, 3.2
        Q.append(quad([(-w, 0, 0), (w, 0, 0), (w, 0, L), (-w, 0, L)], [(0, 0), (2, 0), (2, L / 2.2), (0, L / 2.2)], 'floor', True, 8))
        Q.append(quad([(-w, hgt, L), (w, hgt, L), (w, hgt, 0), (-w, hgt, 0)], [(0, 0), (2, 0), (2, L / 2), (0, L / 2)], 'ceiling', True, 8))
        rep = L / (hgt * A)
        Q.append(quad([(-w, 0, 0), (-w, 0, L), (-w, hgt, L), (-w, hgt, 0)], [(0, 1), (rep, 1), (rep, 0), (0, 0)], 'pic', True, 8))
        Q.append(quad([(w, 0, L), (w, 0, 0), (w, hgt, 0), (w, hgt, L)], [(0, 1), (rep, 1), (rep, 0), (0, 0)], 'pic', True, 8))
        walk = (p['spin'] / 360.0) * hgt * A * 2
        target, base_d, eye_h = np.array([0, 1.5, 10.0 + walk]), 9.5, 1.5
        sky = False
    return Q, target, base_d, eye_h, sky


SKIES = {'day': ((0.25, 0.5, 0.95), (0.75, 0.85, 0.95)), 'night': ((0.01, 0.01, 0.05), (0.08, 0.08, 0.2)),
         'sunset': ((0.2, 0.1, 0.35), (1.0, 0.5, 0.25)), 'vapor': ((0.35, 0.1, 0.55), (1.0, 0.45, 0.75)),
         'toxic': ((0.02, 0.12, 0.04), (0.45, 0.9, 0.2)), 'void': ((0, 0, 0), (0.02, 0.02, 0.02)),
         'overcast': ((0.55, 0.57, 0.6), (0.78, 0.79, 0.8)), 'blood': ((0.12, 0, 0), (0.6, 0.05, 0.03)),
         'underwater': ((0.0, 0.08, 0.2), (0.05, 0.45, 0.55))}
ENGINE_TOP = {'PlayStation': (0.05, 0.05, 0.16), 'N64': (0.35, 0.55, 0.95), 'PS2': (0.25, 0.35, 0.55)}


def sky_colours(p, E):
    """(top of sky, horizon = fog colour). The fog fades into the horizon so the world melts into the sky."""
    if p['sky'] == 'engine default':
        top, hor = ENGINE_TOP[p['engine']], E['fog']
    else:
        top, hor = SKIES[p['sky']]
    top, hor = np.array(top, np.float32), np.array(hor, np.float32)
    if p['skyhue']:
        top = colour.rotate_hue(top[None], np.radians(p['skyhue']))[0]
        hor = colour.rotate_hue(hor[None], np.radians(p['skyhue']))[0]
    return top, hor


# ------------------------------------------------------------------ rasteriser
def clip_near(tri, near):
    """tri: list of (view_pos(3), uv(2), shade). Sutherland-Hodgman against z = near."""
    out = []
    n = len(tri)
    for i in range(n):
        a, b = tri[i], tri[(i + 1) % n]
        ain, bin_ = a[0][2] >= near, b[0][2] >= near
        if ain:
            out.append(a)
        if ain != bin_:
            t = (near - a[0][2]) / (b[0][2] - a[0][2])
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t))
    return [(out[0], out[i], out[i + 1]) for i in range(1, len(out) - 1)] if len(out) >= 3 else []


def render(img, p, rng):
    E = ENGINES[p['engine']]
    H, W = img.shape[:2]
    A = W / H
    fh = max(32, min(E['res'], H))
    fw = int(round(fh * A))
    if fw > fh * 2.2:
        fw = int(fh * 2.2)
    textures = {'pic': picture_texture(img, E['tex'] * p['texres'],
                                       p['cutout'] if p['scene'] == 'cut-out in a field' else 'none', p['pixelate'])}
    default_floor = {'cut-out in a field': 'grass'}.get(p['scene'], 'checker')
    fl = default_floor if p['floor'] == 'default' else p['floor']
    wl = 'brick' if p['walls'] == 'default' else p['walls']
    for k, kind in (('floor', fl), ('wall', wl), ('ceiling', 'ceiling' if p['walls'] == 'default' else wl)):
        if kind == 'your picture':
            textures[k] = picture_texture(img, E['tex'] * p['texres'], 'none', p['pixelate'])
        else:
            textures[k] = proc_texture(kind, np.random.default_rng(7))
        hue = p['floorhue'] if k == 'floor' else p['wallhue']
        if hue:
            textures[k][..., :3] = colour.rotate_hue(textures[k][..., :3], np.radians(hue))
        if k == 'floor':
            textures[k][..., :3] = np.clip(textures[k][..., :3] * p['floorbright'], 0, 1)
        if k == 'ceiling' and p['walls'] != 'default':
            textures[k][..., :3] *= 0.7
    for k in ('floor', 'wall', 'ceiling'):
        if E['tex'] <= 64:                              # N64 textures are tiny AND blurry
            textures[k] = np.asarray(Image.fromarray((textures[k] * 255).astype(np.uint8)).resize((32, 32), Image.BOX)
                                     .resize((64, 64), Image.BILINEAR)).astype(np.float32) / 255
    Q, target, base_d, eye_h, sky = build(p, A)
    yaw, pitch = math.radians(p['yaw']), math.radians(p['pitch'])
    d = base_d * p['dist']
    eye = target + np.array([math.sin(yaw) * d * math.cos(pitch), eye_h - target[1] + math.sin(pitch) * d * 0.6,
                             -math.cos(yaw) * d * math.cos(pitch)])
    if p['scene'] == 'corridor':
        eye = np.array([math.sin(yaw) * 1.2, eye_h + math.sin(pitch) * 1.0, target[2] - d])
    fwd = target - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross(np.array([0, 1.0, 0]), fwd)
    right /= max(1e-9, np.linalg.norm(right))
    up = np.cross(fwd, right)
    f = (fh / 2) / math.tan(math.radians(p['fov']) / 2)
    light = np.array([0.4, 1.0, -0.6]); light /= np.linalg.norm(light)
    near, far = 0.08, 30.0 if p['scene'] != 'corridor' else 34.0

    top, fogc = sky_colours(p, E)
    color = np.zeros((fh, fw, 3), np.float32)
    if sky:
        g = np.linspace(0, 1, fh, dtype=np.float32)[:, None, None]
        color[:] = top * (1 - g) + fogc * g
    else:
        color[:] = fogc * 0.3
    zb = np.full((fh, fw), np.inf, np.float32)
    tess = int(p['tess'])
    tris = []
    for corners, uvs, tex, wrap, sub in Q:
        nrm = np.cross(corners[1] - corners[0], corners[3] - corners[0])
        nrm /= max(1e-9, np.linalg.norm(nrm))
        shade = (1 - p['light']) + p['light'] * (0.55 + 0.45 * abs(float(nrm @ light)))
        n = tess * sub                                  # big floors get split finer, like real games did
        for i in range(n):
            for j in range(n):
                def P3(a, b):
                    s0, t0 = a / n, b / n
                    pos = (corners[0] * (1 - s0) * (1 - t0) + corners[1] * s0 * (1 - t0) +
                           corners[2] * s0 * t0 + corners[3] * (1 - s0) * t0)
                    uv = uvs[0] * (1 - s0) * (1 - t0) + uvs[1] * s0 * (1 - t0) + uvs[2] * s0 * t0 + uvs[3] * (1 - s0) * t0
                    v = pos - eye
                    return (np.array([v @ right, v @ up, v @ fwd]), uv, shade, pos)
                a, b, c, dd = P3(i, j), P3(i + 1, j), P3(i + 1, j + 1), P3(i, j + 1)
                for t in ((a, b, c), (a, c, dd)):
                    for ct in clip_near([(v[0], v[1], v[2]) for v in t], near):
                        tris.append((ct, tex, wrap, [v[3] for v in t]))
    if not E['zbuf']:                                   # PS1: no depth buffer, painter's sort
        tris.sort(key=lambda t: -sum(v[0][2] for v in t[0]) / 3)
    for (verts, tex, wrap, world) in tris:
        sx, sy, zs, us, vs, sh = [], [], [], [], [], []
        for k, (vp, uv, s) in enumerate(verts):
            x = fw / 2 + vp[0] / vp[2] * f
            y = fh / 2 - vp[1] / vp[2] * f
            if p['engine'] == 'PlayStation':           # integer vertex snapping + jitter
                wp = world[min(k, 2)]
                j = math.sin(wp[0] * 12.99 + wp[1] * 78.23 + wp[2] * 37.72 + rng.random() * 0.0) * 43758.5453
                x = round(x + ((j % 1) - 0.5) * 3 * p['wobble'])
                y = round(y + (((j * 7.13) % 1) - 0.5) * 3 * p['wobble'])
            sx.append(x); sy.append(y); zs.append(vp[2]); us.append(uv[0]); vs.append(uv[1]); sh.append(s)
        x0, x1 = max(0, int(math.floor(min(sx)))), min(fw, int(math.ceil(max(sx))) + 1)
        y0, y1 = max(0, int(math.floor(min(sy)))), min(fh, int(math.ceil(max(sy))) + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        area = (sx[1] - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (sy[1] - sy[0])
        if abs(area) < 1e-6:
            continue
        py, px = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
        w0 = ((sx[1] - px) * (sy[2] - py) - (sx[2] - px) * (sy[1] - py)) / area
        w1 = ((sx[2] - px) * (sy[0] - py) - (sx[0] - px) * (sy[2] - py)) / area
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
        if not inside.any():
            continue
        if E['affine']:                                 # PS1: uv straight across the screen = the warp
            u = w0 * us[0] + w1 * us[1] + w2 * us[2]
            v = w0 * vs[0] + w1 * vs[1] + w2 * vs[2]
            z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
        else:
            iz = w0 / zs[0] + w1 / zs[1] + w2 / zs[2]
            u = (w0 * us[0] / zs[0] + w1 * us[1] / zs[1] + w2 * us[2] / zs[2]) / iz
            v = (w0 * vs[0] / zs[0] + w1 * vs[1] / zs[1] + w2 * vs[2] / zs[2]) / iz
            z = 1 / iz
        if E['zbuf']:
            inside &= z < zb[y0:y1, x0:x1]
        texel = sample(textures[tex], u, v, wrap, E['bilinear'])
        inside &= texel[..., 3] > 0.5
        if not inside.any():
            continue
        s = (w0 * sh[0] + w1 * sh[1] + w2 * sh[2])[..., None]
        rgb = texel[..., :3] * s
        fogk = np.clip((z - 2.0) / (far * (1.05 - p['fog'] * 0.8) - 2.0), 0, 1)[..., None] * p['fog']
        rgb = rgb * (1 - fogk) + fogc * fogk
        reg = color[y0:y1, x0:x1]
        reg[inside] = rgb[inside]
        if E['zbuf']:
            zr = zb[y0:y1, x0:x1]
            zr[inside] = z[inside]
    return color, fw, fh


def apply(img, p, rng):
    H, W = img.shape[:2]
    E = ENGINES[p['engine']]
    color, fw, fh = render(img, p, rng)
    L = E['depth']
    if p['engine'] == 'PlayStation':
        dth = np.tile(PS1_DITHER, (fh // 4 + 1, fw // 4 + 1))[:fh, :fw, None]
        color = np.clip(np.floor(color * L + 0.5 + dth), 0, L) / L
    elif p['engine'] == 'N64':
        color = np.clip(np.floor(color * L + 0.5), 0, L) / L
        color = np.asarray(Image.fromarray((color * 255).astype(np.uint8)).resize((fw * 2, fh * 2), Image.BILINEAR)
                           .resize((fw, fh), Image.BOX)).astype(np.float32) / 255           # the soft VI filter
    else:
        bright = np.clip(color - 0.6, 0, 1)
        glow = np.asarray(Image.fromarray((bright * 255).astype(np.uint8)).resize((fw // 8, fh // 8), Image.BOX)
                          .resize((fw, fh), Image.BILINEAR)).astype(np.float32) / 255
        color = np.clip(color + glow * 0.8, 0, 1)
    ys = np.minimum(np.arange(H) * fh // H, fh - 1)
    xs = np.minimum(np.arange(W) * fw // W, fw - 1)
    up = color[ys][:, xs]
    disp = {'composite TV': 'composite', 'RGB TV': 'rgb', 'RF TV': 'rf', 'clean pixels': None}[p['screen']]
    if disp:
        up = console().screen(up, disp, fw, fh, dict(scan=p['scan'], curve=p['curve']), rng, 0.3, 8)
    out = np.empty_like(img)
    out[..., :3] = (np.clip(up, 0, 1) * 255 + 0.5).astype(np.uint8)
    out[..., 3] = 255
    return out
