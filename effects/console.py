"""Console: renders the picture the way a games console would, then shows it on the screen that console
was played on. Step 1, the machine: its real resolution, its palette or colour depth, its dithering and one
signature quirk. Step 2, the screen: a composite / RF / RGB tube TV, the handheld's LCD, a PC monitor or an HDTV.

SYSTEM QUIRK per machine:
  NES          4-colour tile clash + sprite flicker bands      Game Boy / GBC / GBA   LCD ghosting
  Master Sys   soft composite smear                             Mega Drive   checker dither that the TV melts into rainbows
  SNES         mosaic mode                                      PlayStation  vertex wobble (polygon jitter) + PS1 dither
  N64          blurry 3-point filtering + distance fog          PS2          interlace comb
  Xbox 360     brown 'next-gen' grading + over-bloom            Dreamcast    VGA-sharp, 16-bit banding
  Atari 2600   double-wide pixels, colour bleed                 C64          multicolour double-wide pixels
  DOS CGA      palette swap (cyan/magenta <> green/red)         DOS VGA      256-colour adaptive palette
  Virtual Boy  red LED with the stereo ghost
"""
import numpy as np
from PIL import Image, ImageFilter

NAME = 'Console'
KIND = 'filter'
CATEGORY = 'Console'


def hexpal(s):
    return np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in s.split()], np.float32) / 255


NES = hexpal("""7C7C7C 0000FC 0000BC 4428BC 940084 A80020 A81000 881400 503000 007800 006800 005800 004058 000000
BCBCBC 0078F8 0058F8 6844FC D800CC E40058 F83800 E45C10 AC7C00 00B800 00A800 00A844 008888
F8F8F8 3CBCFC 6888FC 9878F8 F878F8 F85898 F87858 FCA044 F8B800 B8F818 58D854 58F898 00E8D8 787878
FCFCFC A4E4FC B8B8F8 D8B8F8 F8B8F8 F8A4C0 F0D0B0 FCE0A8 F8D878 D8F878 B8F8B8 B8F8D8 00FCFC F8D8F8""")
C64 = hexpal("000000 FFFFFF 68372B 70A4B2 6F3D86 588D43 352879 B8C76F 6F4F25 433900 9A6759 444444 6C6C6C 9AD284 6C5EB5 959595")
DMG = hexpal("0F380F 306230 8BAC0F 9BBC0F")
VB = hexpal("000000 550000 AA0000 FF0000")
CGA1 = hexpal("000000 55FFFF FF55FF FFFFFF")
CGA0 = hexpal("000000 55FF55 FF5555 FFFF55")


def atari_palette():
    out = [[0.0, 0.0, 0.0]]
    for hue in range(16):
        for lum in range(8):
            l = 0.08 + lum / 7 * 0.85
            if hue == 0:
                out.append([l, l, l]); continue
            a = (hue - 1) / 15 * 2 * np.pi + 0.6
            out.append(np.clip([l + 0.32 * np.cos(a), l + 0.32 * np.cos(a - 2.1), l + 0.32 * np.cos(a + 2.1)], 0, 1))
    return np.array(out, np.float32)


ATARI = atari_palette()

#            name: (native w, native h, colour, display, pixel width)
SYSTEMS = {
    'NES': (256, 240, 'nes', 'composite', 1),
    'Game Boy': (160, 144, 'dmg', 'lcd-dmg', 1),
    'Game Boy Color': (160, 144, 5, 'lcd-gbc', 1),
    'Game Boy Advance': (240, 160, 5, 'lcd-gba', 1),
    'Master System': (256, 192, 2, 'composite', 1),
    'Mega Drive / Genesis': (320, 224, 'md', 'composite', 1),
    'SNES': (256, 224, 5, 'composite', 1),
    'PlayStation': (320, 240, 'ps1', 'composite', 1),
    'N64': (320, 240, 5, 'composite', 1),
    'PS2': (640, 448, 8, 'composite', 1),
    'Xbox 360': (1280, 720, 8, 'hdtv', 1),
    'Dreamcast': (640, 480, 'rgb565', 'monitor', 1),
    'Atari 2600': (160, 192, 'atari', 'rf', 2),
    'Commodore 64': (320, 200, 'c64', 'composite', 1),
    'DOS CGA': (320, 200, 'cga', 'monitor', 1),
    'DOS VGA': (320, 200, 'vga', 'monitor', 1),
    'Virtual Boy': (384, 224, 'vb', 'vb', 1),
}
DISPLAYS = ['how it was shown', 'clean pixels', 'composite TV', 'RF TV', 'RGB TV', 'handheld LCD', 'monitor', 'HDTV']
PARAMS = [
    P('system', 'SYSTEM', choices=list(SYSTEMS)),
    P('display', 'SCREEN', choices=DISPLAYS),
    P('amount', 'AMOUNT', 0.0, 1.0, 1.0, 0.01),
    P('quirk', 'SYSTEM QUIRK', 0.0, 1.0, 0.5, 0.01),
    P('dither', 'DITHER', 0.0, 1.0, 0.6, 0.01),
    P('res', 'RESOLUTION x', 0.5, 2.0, 1.0, 0.05),
    P('scan', 'SCANLINES', 0.0, 1.0, 0.55, 0.01),
    P('curve', 'GLASS CURVE', 0.0, 0.3, 0.06, 0.01),
]
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16 - 0.5
PS1 = np.array([[-4, 0, -3, 1], [2, -2, 3, -1], [-3, 1, -4, 0], [3, -1, 2, -2]], np.float32) / 8


def tile(m, h, w):
    return np.tile(m, (h // m.shape[0] + 1, w // m.shape[1] + 1))[:h, :w]


def blur(rgb, r):
    if r <= 0.05:
        return rgb
    im = Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im).astype(np.float32) / 255


def hblur(a, n):
    n = int(round(n))
    if n <= 1:
        return a
    pad = np.pad(a, [(0, 0), (n // 2, n - n // 2)] + [(0, 0)] * (a.ndim - 2), mode='edge')
    c = np.cumsum(pad, axis=1, dtype=np.float32)
    return (c[:, n:] - c[:, :-n]) / n


def nearest(rgb, pal, offset=None):
    flat = rgb.reshape(-1, 3)
    if offset is not None:
        flat = flat + offset.reshape(-1, 1)
    idx = np.empty(len(flat), np.int32)
    for s in range(0, len(flat), 60000):
        idx[s:s + 60000] = ((flat[s:s + 60000, None, :] - pal[None]) ** 2).sum(-1).argmin(1)
    return idx.reshape(rgb.shape[:2])


def nes_clash(idx, pal, rng, q):
    """NES attribute limit: each 16x16 area may only use 3 colours + the shared background colour."""
    h, w = idx.shape
    bg = np.bincount(idx.ravel(), minlength=len(pal)).argmax()
    out = idx.copy()
    for y in range(0, h, 16):
        for x in range(0, w, 16):
            t = idx[y:y + 16, x:x + 16]
            cnt = np.bincount(t.ravel(), minlength=len(pal))
            cnt[bg] = 0
            keep = np.append(np.argsort(cnt)[::-1][:3], bg)
            d = ((pal[t][..., None, :] - pal[keep][None, None]) ** 2).sum(-1)
            out[y:y + 16, x:x + 16] = keep[d.argmin(-1)]
    return out


def machine(small, kind, p, rng):
    h, w = small.shape[:2]
    d, q = p['dither'], p['quirk']
    bay = tile(BAYER4, h, w)
    if kind == 'nes':
        idx = nearest(small, NES, bay * d * 0.25)
        if q > 0.15:
            idx = nes_clash(idx, NES, rng, q)
        out = NES[idx]
        for y in range(0, h, 8):                          # sprite flicker: some 8-line bands drop out
            if rng.random() < q * 0.12:
                out[y:y + 8] *= 0.45
        return out
    if kind == 'dmg':
        lum = small @ np.array([0.299, 0.587, 0.114], np.float32)
        lv = np.clip(np.floor(lum * 3 + 0.5 + bay * d * 0.9), 0, 3).astype(int)
        return DMG[lv]
    if kind == 'vb':
        lum = small @ np.array([0.299, 0.587, 0.114], np.float32)
        return VB[np.clip(np.floor(lum * 3 + 0.5 + bay * d * 0.9), 0, 3).astype(int)]
    if kind == 'cga':
        return (CGA0 if q > 0.5 else CGA1)[nearest(small, CGA0 if q > 0.5 else CGA1, bay * d * 0.5)]
    if kind == 'c64':
        return C64[nearest(small, C64, bay * d * 0.3)]
    if kind == 'atari':
        return ATARI[nearest(small, ATARI, bay * d * 0.12)]
    if kind == 'vga':
        im = Image.fromarray((np.clip(small, 0, 1) * 255).astype(np.uint8))
        im = im.quantize(256, method=Image.Quantize.MEDIANCUT,
                         dither=Image.Dither.FLOYDSTEINBERG if d > 0.3 else Image.Dither.NONE)
        return np.asarray(im.convert('RGB')).astype(np.float32) / 255
    if kind == 'md':                                       # 9-bit colour, checkerboard dither (TVs blur it into new colours)
        L = 7
        chk = ((np.indices((h, w)).sum(0) % 2) - 0.5) * (0.5 + q)
        return np.clip(np.floor(small * L + 0.5 + chk[..., None] * d), 0, L) / L
    if kind == 'ps1':
        L = 31
        return np.clip(np.floor(small * L + 0.5 + tile(PS1, h, w)[..., None] * d * 2), 0, L) / L
    if kind == 'rgb565':
        out = small.copy()
        for c, L in ((0, 31), (1, 63), (2, 31)):
            out[..., c] = np.clip(np.floor(small[..., c] * L + 0.5 + bay * d * 0.8), 0, L) / L
        return out
    L = 2 ** int(kind) - 1                                # plain bit depth per channel
    if L >= 255:
        return small
    return np.clip(np.floor(small * L + 0.5 + bay[..., None] * d * 0.8), 0, L) / L


def pre_quirk(small, name, q, rng):
    h, w = small.shape[:2]
    if name == 'PlayStation' and q > 0:                    # vertex snapping wobble: a jittered polygon grid
        g = 16
        gy, gx = h // g + 2, w // g + 2
        jx = rng.uniform(-1, 1, (gy, gx)) * q * 3
        jy = rng.uniform(-1, 1, (gy, gx)) * q * 3
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        fy, fx = yy / g, xx / g
        y0, x0 = fy.astype(int), fx.astype(int)
        ty, tx = fy - y0, fx - x0

        def lerp(j):
            return (j[y0, x0] * (1 - tx) * (1 - ty) + j[y0, x0 + 1] * tx * (1 - ty) +
                    j[y0 + 1, x0] * (1 - tx) * ty + j[y0 + 1, x0 + 1] * tx * ty)
        sx = np.clip(np.round(xx + lerp(jx)), 0, w - 1).astype(int)
        sy = np.clip(np.round(yy + lerp(jy)), 0, h - 1).astype(int)
        return small[sy, sx]
    if name == 'N64':
        out = blur(small, 0.9)
        fog = np.linspace(1, 0, h, dtype=np.float32)[:, None, None] ** 1.5 * q * 0.7
        return out * (1 - fog) + np.array([0.62, 0.66, 0.72], np.float32) * fog
    if name == 'Xbox 360':
        lum = small @ np.array([0.299, 0.587, 0.114], np.float32)
        brown = lum[..., None] * np.array([1.08, 0.98, 0.78], np.float32)
        out = small * (1 - q * 0.6) + brown * q * 0.6
        return np.clip((out - 0.5) * (1 + q * 0.35) + 0.5, 0, 1)
    if name == 'SNES' and q > 0.15:
        b = 1 + int(q * 7)
        m = small[::b, ::b]
        return np.repeat(np.repeat(m, b, 0), b, 1)[:h, :w]
    if name == 'Master System':
        return hblur(small, 1 + q * 2)
    if name == 'Atari 2600':
        return hblur(small, 1 + q * 3)
    return small


def curve(img, k):
    if k <= 0:
        return img
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / (w / 2) - 1, yy / (h / 2) - 1
    f = 1 + k * (u * u + v * v)
    sx, sy = (u * f + 1) * w / 2, (v * f + 1) * h / 2
    ok = (sx >= 0) & (sx < w) & (sy >= 0) & (sy < h)
    out = img[np.clip(sy, 0, h - 1).astype(int), np.clip(sx, 0, w - 1).astype(int)]
    out[~ok] = 0
    return out * np.clip(1 - 0.25 * (u * u + v * v) * k * 4, 0, 1)[..., None]


def scanlines(up, yy_frac, s, lum):
    beam = np.exp(-((yy_frac - 0.5) / (0.28 + 0.3 * lum)) ** 2)            # bright lines bloom fatter, like a real beam
    return up * ((1 - s) + s * beam[..., None] * 1.3)


YIQ = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]], np.float32)


def screen(up, disp, nw, nh, p, rng, q, kind):
    H, W = up.shape[:2]
    px = W / nw
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    fy = (yy * nh / H) % 1
    fx = (xx * nw / W) % 1
    lum = up @ np.array([0.299, 0.587, 0.114], np.float32)
    s = p['scan']
    if disp in ('composite', 'rf'):
        yiq = up @ YIQ.T
        luma = hblur(yiq[..., 0:1], px * 0.7)[..., 0]
        hi = yiq[..., 0] - luma
        chroma = hblur(yiq[..., 1:], px * (2.6 if kind == 'md' else 1.8))
        phase = np.sin((xx / px) * np.pi + (yy * nh / H).astype(int) * np.pi / 2)     # dot crawl / NTSC rainbow
        chroma[..., 0] += hi * phase * 0.35
        chroma[..., 1] += hi * np.cos((xx / px) * np.pi) * 0.25
        out = np.concatenate([luma[..., None], chroma], -1) @ np.linalg.inv(YIQ).T
        if disp == 'rf':
            out = out * 0.88 + np.roll(out, int(px * 0.8), 1) * 0.12          # RF ghost
            out += (rng.random((H, W)).astype(np.float32)[..., None] - 0.5) * 0.08
            jit = (rng.standard_normal(nh) * 0.6 * px).astype(int)[(yy[:, 0] * nh / H).astype(int)]
            out = np.take_along_axis(out, ((np.arange(W)[None] - jit[:, None]) % W)[..., None].repeat(3, 2), 1)
        out = scanlines(np.clip(out, 0, 1), fy, s, lum)
        mask = np.ones((H, W, 3), np.float32) * 0.82
        ch = (xx.astype(int) % 3)
        for c in range(3):
            mask[..., c][ch == c] = 1.08
        out = out * mask
        out = out + blur(np.clip(out - 0.6, 0, 1), 3) * 0.6
        return curve(out, p['curve'])
    if disp == 'rgb':
        return curve(scanlines(up, fy, s, lum), p['curve'])
    if disp == 'monitor':
        return curve(scanlines(up, fy, s * 0.45, lum) * 1.05, p['curve'] * 0.5)
    if disp == 'hdtv':
        out = up
        if kind == 8 and q > 0:
            out = out + blur(np.clip(out - 0.55, 0, 1), 6) * q * 1.4
        return out
    if disp.startswith('lcd') or disp == 'vb':
        g = 0.14
        grid = ((fx < g) | (fy < g)).astype(np.float32)[..., None]
        if disp == 'lcd-dmg':
            out = up * (1 - grid * 0.18) + DMG[3] * grid * 0.18
            ghost = np.roll(np.roll(out, max(1, int(px * 0.5)), 0), max(1, int(px * 0.5)), 1)
            out = out * (1 - q * 0.25) + np.minimum(out, ghost) * q * 0.25
            return blur(out, px * 0.15)
        if disp == 'lcd-gba':
            out = np.clip(up, 0, 1) ** 1.6 * 0.92                             # the dark, unlit original GBA screen
            lum2 = out.mean(-1, keepdims=True)
            out = lum2 + (out - lum2) * 0.8
            return out * (1 - grid * 0.35)
        if disp == 'vb':
            out = up * (1 - (fx < 0.18).astype(np.float32)[..., None] * 0.55)
            if q > 0:
                out = np.maximum(out, np.roll(out, int(px * 2 * q), 1) * 0.35)   # stereo ghost
            return out
        out = np.clip(up, 0, 1) ** 1.2
        lum2 = out.mean(-1, keepdims=True)
        out = lum2 + (out - lum2) * 0.78
        ghost = np.roll(out, max(1, int(px * 0.5)), 0)
        out = out * (1 - q * 0.2) + ghost * q * 0.2
        return out * (1 - grid * 0.25)
    return up


def apply(img, p, rng):
    H, W = img.shape[:2]
    nw0, nh0, kind, disp_auto, hpix = SYSTEMS[p['system']]
    q = p['quirk']
    a = img[..., 3:4].astype(np.float32) / 255
    rgb = img[..., :3].astype(np.float32) / 255 * a                       # see-through = black screen
    nh = max(16, min(H, int(round(nh0 * p['res']))))            # never more lines than the picture has
    nw = max(16, int(round(min(nw0 * p['res'] * 1.4, nh * W / H))))
    if p['system'] == 'Commodore 64' and q > 0.5:
        hpix = 2
    nwp = max(8, nw // hpix)
    small = np.asarray(Image.fromarray((rgb * 255).astype(np.uint8)).resize((nwp, nh), Image.BOX)).astype(np.float32) / 255
    small = pre_quirk(small, p['system'], q, rng)
    small = machine(small, kind, p, rng)
    if hpix > 1:
        small = np.repeat(small, hpix, 1)
    ys = np.minimum(np.arange(H) * nh // H, nh - 1)
    xs = np.minimum(np.arange(W) * small.shape[1] // W, small.shape[1] - 1)
    up = small[ys][:, xs]
    if p['system'] == 'PS2' and q > 0:                                      # interlace comb on odd fields
        odd = (ys % 2 == 1)
        up[odd] = np.roll(up[odd], int(q * 3 * W / nw), 1)
    d = p['display']
    disp = {'how it was shown': disp_auto, 'clean pixels': 'pixels', 'composite TV': 'composite', 'RF TV': 'rf',
            'RGB TV': 'rgb', 'monitor': 'monitor', 'HDTV': 'hdtv',
            'handheld LCD': disp_auto if disp_auto.startswith('lcd') else 'lcd-gbc'}[d]
    out = screen(up, disp, small.shape[1], nh, p, rng, q, kind) if disp != 'pixels' else up
    out = np.clip(out, 0, 1)
    am = p['amount']
    out = out * am + img[..., :3].astype(np.float32) / 255 * (1 - am)
    res = np.empty_like(img)
    res[..., :3] = (out * 255 + 0.5).astype(np.uint8)
    res[..., 3] = 255
    return res
