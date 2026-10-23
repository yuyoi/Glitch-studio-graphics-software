"""Broken-signal maths shared by the noise filters and brushes.

snow()      analog TV static: random luminance, smeared along the scan direction like a real tuner
dct()       the 8x8 discrete cosine transform JPEG and MPEG use; crushing its coefficients = real codec artefacts
block_rot() macroblock errors from a broken digital stream: lost motion vectors, smears, flat blocks, swapped chroma
"""
import numpy as np


def hblur(a, n):
    """Box blur along x (axis 1), length n, keeps shape. Works on 2-D or 3-D float arrays."""
    n = int(n)
    if n <= 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[1] = (n // 2, n - n // 2)
    c = np.cumsum(np.pad(a, pad, mode='edge'), axis=1, dtype=np.float32)
    return (c[:, n:] - c[:, :-n]) / n


def snow(h, w, rng, grain=1, streak=0.3, colour=0.0):
    """0..1 float (h, w, 3) static."""
    g = max(1, int(grain))
    sh, sw = h // g + 1, w // g + 1
    n = rng.random((sh, sw), np.float32)
    if streak > 0:                                         # tuner noise is correlated along each scan line
        n = n * (1 - streak) + hblur(n, 2 + streak * 40) * streak
        n = (n - n.mean()) / max(1e-6, n.std()) * 0.22 + 0.5
    rgb = np.repeat(n[..., None], 3, 2)
    if colour > 0:
        rgb = rgb + (rng.random((sh, sw, 3), np.float32) - 0.5) * colour
    rgb = np.repeat(np.repeat(rgb, g, 0), g, 1)[:h, :w]
    return np.clip(rgb, 0, 1)


def dct_matrix(n):
    k = np.arange(n)
    m = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n)) * np.sqrt(2 / n)
    m[0] /= np.sqrt(2)
    return m.astype(np.float32)


def dct_crush(rgb, n=8, q=40.0, chroma=2.0):
    """Quantise each nxn block's DCT coefficients, harder for high frequencies and for colour (like JPEG).
    rgb float 0..1 with h, w multiples of n."""
    h, w = rgb.shape[:2]
    D = dct_matrix(n)
    # YCbCr so colour can be crushed harder than brightness
    M = np.array([[0.299, 0.587, 0.114], [-0.1687, -0.3313, 0.5], [0.5, -0.4187, -0.0813]], np.float32)
    ycc = rgb @ M.T
    u = np.arange(n)
    Q = (1 + q * 0.12 + (u[:, None] + u[None, :]) * q / n) * 3 / 255.0      # DC crushed too: colour banding
    out = np.empty_like(ycc)
    for c in range(3):
        b = ycc[..., c].reshape(h // n, n, w // n, n).transpose(0, 2, 1, 3)
        co = np.einsum('ij,abjk,lk->abil', D, b, D)
        qq = Q * (chroma if c else 1.0)
        co = np.round(co / qq) * qq
        b = np.einsum('ji,abjk,kl->abil', D, co, D)
        out[..., c] = b.transpose(0, 2, 1, 3).reshape(h, w)
    return np.clip(out @ np.linalg.inv(M).T, 0, 1)


def block_rot(img, rng, n=16, chance=0.15, mix=(1, 1, 1, 1), trail=4):
    """In-place macroblock corruption on an HxWx4 uint8 array (any size; edge blocks are skipped).
    mix = weights for (copy from elsewhere, smear down, flat colour, chroma swap)."""
    h, w = img.shape[:2]
    by, bx = h // n, w // n
    if by < 1 or bx < 1:
        return img
    weights = np.array(mix, np.float64)
    if weights.sum() <= 0:
        return img
    weights /= weights.sum()
    hits = np.argwhere(rng.random((by, bx)) < chance)
    rng.shuffle(hits)
    src = img.copy()
    for j, i in hits:
        y, x = j * n, i * n
        kind = rng.choice(4, p=weights)
        blk = img[y:y + n, x:x + n]
        if kind == 0:                                      # lost motion vector: block from a nearby wrong place
            sy = int(np.clip(y + rng.integers(-4, 5) * n + rng.integers(-n, n), 0, h - n))
            sx = int(np.clip(x + rng.integers(-6, 7) * n + rng.integers(-n, n), 0, w - n))
            blk[:] = src[sy:sy + n, sx:sx + n]
        elif kind == 1:                                    # smear: the block's top row drags down for a few blocks
            y1 = min(h, y + n * int(rng.integers(1, trail + 1)))
            img[y:y1, x:x + n] = src[y:y + 1, x:x + n]
        elif kind == 2:                                    # flat: only the DC coefficient survived
            blk[..., :3] = src[y:y + n, x:x + n, :3].reshape(-1, 3).mean(0).astype(np.uint8)
        else:                                              # chroma planes swapped / shifted
            blk[..., :3] = src[y:y + n, x:x + n, :3][..., rng.permutation(3)]
    return img


def see_through(img, key):
    """0..1 (h, w, 1) how much of the layer counts as solid: its alpha, or also treat white paper as see-through."""
    al = img[..., 3:4].astype(np.float32) / 255
    if key == 'white paper':
        mn = img[..., :3].min(-1, keepdims=True).astype(np.float32) / 255
        al = al * np.clip((0.97 - mn) / 0.12, 0, 1)
    return al
