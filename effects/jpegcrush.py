"""JPEG crush: re-saves as a terrible JPEG over and over (blocks, ringing, colour smear). Alpha kept."""
import io

import numpy as np
from PIL import Image

NAME = 'JPEG Crush'
KIND = 'filter'
PARAMS = [
    P('quality', 'QUALITY', 1, 40, 6),
    P('passes', 'PASSES', 1, 20, 3),
    P('scale', 'DOWNSCALE', 0.1, 1.0, 0.6, 0.05),
]


def apply(img, p, rng):
    h, w = img.shape[:2]
    im = Image.fromarray(np.ascontiguousarray(img[..., :3]))
    im = im.resize((max(8, int(w * p['scale'])), max(8, int(h * p['scale']))), Image.BILINEAR)
    for i in range(p['passes']):
        b = io.BytesIO()
        im.save(b, 'JPEG', quality=max(1, p['quality'] - (i % 2)), subsampling=2)
        im = Image.open(io.BytesIO(b.getvalue())).convert('RGB')
    out = img.copy()
    out[..., :3] = np.asarray(im.resize((w, h), Image.NEAREST))
    return out
