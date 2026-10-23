"""Glitch Lab - texture: the worn, speckled "screenprint dropout" look from the Hex girl recovery accident.

It eats holes into a layer: big soft clumps (where whole patches go thin) mixed with fine grain (the speckle),
so colour fills look printed and worn while the picture still reads.

    python glitch_tex.py layer.png                       -> layer_glitch.png next to it
    python glitch_tex.py layer.png --amount 0.45 --clump 6 --grain 0.6 --seed 3
    python glitch_tex.py layer.png --mask                -> also layer_glitch_mask.png (white = keep)

  --amount  how much is eaten away, 0..1                      (default 0.35)
  --clump   size of the soft patches in pixels                (default 4)
  --grain   0 = only soft patches, 1 = only fine speckle      (default 0.5)
  --edge    0..1: protect strong lines (lineart) from holes   (default 0)
  --seed    a number; same seed = same texture                (default 1)

Works best on a single colour layer exported from Krita (transparent background). It only changes alpha,
so colours stay exactly yours.
"""
import argparse, os, sys

import numpy as np
from PIL import Image, ImageFilter


def blur(a, r):
    if r <= 0:
        return a
    im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255


def texture(img, amount=0.35, clump=4.0, grain=0.5, edge=0.0, seed=1):
    rgba = np.asarray(img.convert('RGBA')).astype(np.float32)
    h, w = rgba.shape[:2]
    rng = np.random.default_rng(seed)
    soft = blur(rng.random((h, w), np.float32), clump)                # clumpy patches
    soft = (soft - soft.min()) / max(1e-6, soft.max() - soft.min())
    fine = rng.random((h, w), np.float32)                             # single-pixel speckle
    field = (1 - grain) * soft + grain * fine
    alpha = rgba[..., 3] / 255
    inside = alpha > 0.02
    if inside.any():
        cut = np.quantile(field[inside], amount)                      # eat exactly `amount` of the painted area
    else:
        cut = amount
    keep = (field >= cut).astype(np.float32)
    if edge > 0:                                                      # protect dark, strong strokes (lines)
        lum = rgba[..., :3].mean(axis=2) / 255
        line = np.clip((0.35 - lum) / 0.35, 0, 1) * alpha
        keep = np.maximum(keep, (line > (1 - edge)).astype(np.float32))
    out = rgba.copy()
    out[..., 3] = rgba[..., 3] * keep
    return Image.fromarray(out.astype(np.uint8), 'RGBA'), Image.fromarray((keep * 255).astype(np.uint8), 'L')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('image')
    ap.add_argument('--amount', type=float, default=0.35)
    ap.add_argument('--clump', type=float, default=4.0)
    ap.add_argument('--grain', type=float, default=0.5)
    ap.add_argument('--edge', type=float, default=0.0)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--mask', action='store_true', help='also save the keep-mask (for a Krita transparency mask)')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    img = Image.open(a.image)
    out, mask = texture(img, a.amount, a.clump, a.grain, a.edge, a.seed)
    base = os.path.splitext(a.out or a.image)[0]
    dst = a.out or base + '_glitch.png'
    if os.path.abspath(dst) == os.path.abspath(a.image):
        sys.exit('refusing to overwrite the input; pick another --out')
    out.save(dst)
    print('saved', dst)
    if a.mask:
        mask.save(base + '_glitch_mask.png'); print('saved', base + '_glitch_mask.png')


if __name__ == '__main__':
    main()
