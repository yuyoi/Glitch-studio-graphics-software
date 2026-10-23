"""Smart pixelation: shrink a picture so it reads like hand-made pixel art instead of a blurry thumbnail.

Plain downscaling averages every block into mud and thin lines vanish. Here each output pixel looks at its block
of source pixels and
  - 'k-centroid': splits the block into its 2 main colours (2-means) and keeps the bigger one, so flat colours
    stay flat and crisp (the method Astropulse's K-Centroid / PixelOE use);
  - 'pixel art': k-centroid + outline keeping: if a block holds enough dark line pixels they win, so line art
    survives as clean 1-pixel outlines;
  - 'average': the plain blurry way, for comparison.
"""
import numpy as np
from PIL import Image

SUB = 4                                                   # source pixels per output pixel side (after a pre-resize)


def blocks(img, tw, th):
    big = np.asarray(Image.fromarray(img).resize((tw * SUB, th * SUB), Image.BOX)).astype(np.float32) / 255
    b = big.reshape(th, SUB, tw, SUB, -1).transpose(0, 2, 1, 3, 4).reshape(th, tw, SUB * SUB, -1)
    return b


def two_means(px, iters=4):
    """px (..., n, 3) -> (centre_a, centre_b, mask_a, count_a, count_b), vectorised over blocks."""
    lum = px @ np.array([0.299, 0.587, 0.114], np.float32)
    ia, ib = lum.argmin(-1), lum.argmax(-1)
    ca = np.take_along_axis(px, ia[..., None, None], -2)[..., 0, :]
    cb = np.take_along_axis(px, ib[..., None, None], -2)[..., 0, :]
    for _ in range(iters):
        da = ((px - ca[..., None, :]) ** 2).sum(-1)
        db = ((px - cb[..., None, :]) ** 2).sum(-1)
        ma = (da <= db)[..., None]
        na, nb = ma.sum(-2), (~ma).sum(-2)
        ca = np.where(na > 0, (px * ma).sum(-2) / np.maximum(na, 1), ca)
        cb = np.where(nb > 0, (px * ~ma).sum(-2) / np.maximum(nb, 1), cb)
    return ca, cb, ma[..., 0], na[..., 0], nb[..., 0]


def downscale(img, tw, th, mode='pixel art', outline=0.3):
    """img HxWx4 uint8 -> th x tw x 4 uint8."""
    if mode == 'average':
        return np.asarray(Image.fromarray(img).resize((tw, th), Image.BOX))
    b = blocks(img, tw, th)
    rgb, a = b[..., :3], b[..., 3]
    ca, cb, ma, na, nb = two_means(rgb)                   # ca = the darker cluster (seeded from the darkest pixel)
    out = np.where((na >= nb)[..., None], ca, cb)
    if mode == 'pixel art':
        lum_a = ca @ np.array([0.299, 0.587, 0.114], np.float32)
        lum_b = cb @ np.array([0.299, 0.587, 0.114], np.float32)
        line = (lum_a < 0.3) & (lum_b - lum_a > 0.35) & (na >= max(1, outline * SUB * SUB))
        out = np.where(line[..., None], ca, out)
    alpha = (a.mean(-1) > 0.5).astype(np.float32)          # hard pixel-art alpha
    res = np.concatenate([out, alpha[..., None]], -1)
    return (np.clip(res, 0, 1) * 255 + 0.5).astype(np.uint8)


def palette(img, n, dither=False):
    """Reduce to n colours (median cut), keeps alpha."""
    if n <= 0:
        return img
    im = Image.fromarray(np.ascontiguousarray(img[..., :3])).quantize(
        n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE)
    out = img.copy()
    out[..., :3] = np.asarray(im.convert('RGB'))
    return out
