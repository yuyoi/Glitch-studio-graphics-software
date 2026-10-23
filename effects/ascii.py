"""ASCII / ANSI art: the picture rebuilt from text characters, picked by how much ink each glyph has.
Green or amber terminal, real colours, or the 16-colour ANSI palette of old BBS art."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

NAME = 'ASCII'
KIND = 'filter'
CATEGORY = 'Print'
PARAMS = [
    P('cell', 'CHAR HEIGHT px', 6, 48, 14),
    P('chars', 'CHARACTERS', choices=['ascii', 'blocks', 'binary', 'symbols']),
    P('colour', 'COLOUR', choices=['green terminal', 'original', 'ansi 16', 'amber terminal', 'white']),
    P('bg', 'BACKGROUND', choices=['black', 'transparent', 'dim picture']),
    P('contrast', 'CONTRAST', 0.5, 3.0, 1.3, 0.05),
    P('invert', 'INVERT', choices=['no', 'yes']),
]
SETS = {'ascii': " .'`^,:;Il!i><~+_-?][}{1)(|tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
        'blocks': ' ░▒▓█', 'binary': ' 01', 'symbols': ' .:-=+*#%@'}
ANSI = np.array([[0, 0, 0], [170, 0, 0], [0, 170, 0], [170, 85, 0], [0, 0, 170], [170, 0, 170], [0, 170, 170],
                 [170, 170, 170], [85, 85, 85], [255, 85, 85], [85, 255, 85], [255, 255, 85], [85, 85, 255],
                 [255, 85, 255], [85, 255, 255], [255, 255, 255]], np.float32) / 255
_cache = {}


def glyphs(chars, ch):
    key = (chars, ch)
    if key in _cache:
        return _cache[key]
    cw = max(3, int(round(ch * 0.6)))
    try:
        font = ImageFont.truetype('consola.ttf', ch)
    except Exception:
        font = ImageFont.load_default()
    g = []
    for c in SETS[chars]:
        im = Image.new('L', (cw, ch), 0)
        ImageDraw.Draw(im).text((cw / 2, ch / 2), c, fill=255, font=font, anchor='mm')
        g.append(np.asarray(im).astype(np.float32) / 255)
    g = np.array(g)
    order = np.argsort(g.mean((1, 2)))                                  # sort by ink: light to heavy
    _cache[key] = (g[order], cw)
    return _cache[key]


def apply(img, p, rng):
    h, w = img.shape[:2]
    ch = p['cell']
    g, cw = glyphs(p['chars'], ch)
    rows, cols = h // ch, w // cw
    if rows < 1 or cols < 1:
        return img.copy()
    rgba = img[:rows * ch, :cols * cw].astype(np.float32) / 255
    cells = rgba.reshape(rows, ch, cols, cw, 4).mean((1, 3))
    a = cells[..., 3:4]
    rgb = cells[..., :3] * a + (1 - a) * (0 if p['bg'] == 'black' else 1) * (p['bg'] != 'transparent')
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    lum = np.clip((lum - 0.5) * p['contrast'] + 0.5, 0, 1)
    if p['invert'] == 'yes':
        lum = 1 - lum
    if p['bg'] != 'black':
        lum = 1 - lum                                                   # dark ink on light: darker = more ink
    idx = np.clip((lum * (len(g) - 1) + 0.5).astype(int), 0, len(g) - 1)
    ink = g[idx].transpose(0, 2, 1, 3).reshape(rows * ch, cols * cw)
    if p['colour'] == 'original':
        col = cells[..., :3] * 1.15
    elif p['colour'] == 'ansi 16':
        col = ANSI[((cells[..., None, :3] - ANSI[None, None]) ** 2).sum(-1).argmin(-1)]
    else:
        col = np.broadcast_to(np.array({'green terminal': (0.3, 1, 0.45), 'amber terminal': (1, 0.7, 0.15),
                                        'white': (0.95, 0.95, 0.95)}[p['colour']], np.float32), (rows, cols, 3))
    colf = np.repeat(np.repeat(col, ch, 0), cw, 1)
    out = np.zeros((h, w, 4), np.float32)
    if p['bg'] == 'black':
        out[..., 3] = 1
        out[:rows * ch, :cols * cw, :3] = colf * ink[..., None]
    elif p['bg'] == 'dim picture':
        out[..., :3] = img[..., :3].astype(np.float32) / 255 * 0.25
        out[..., 3] = 1
        out[:rows * ch, :cols * cw, :3] = out[:rows * ch, :cols * cw, :3] * (1 - ink[..., None]) + colf * ink[..., None]
    else:
        out[:rows * ch, :cols * cw, :3] = colf
        out[:rows * ch, :cols * cw, 3] = ink
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
