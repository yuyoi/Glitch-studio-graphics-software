"""Databend: edits the picture's raw bytes like opening an image in a text editor. Inserting or deleting a
single byte knocks every pixel after it out of step, so the image skews and its colours rotate R>G>B:
the classic databending look. Also bit flips, echoed byte runs and the famous WordPad save."""
import numpy as np

NAME = 'Databend'
KIND = 'filter'
PARAMS = [
    P('mode', 'MODE', choices=['insert bytes', 'delete bytes', 'echo runs', 'bit flips', 'wordpad']),
    P('hits', 'HITS', 1, 200, 8),
    P('size', 'BYTES PER HIT', 1, 5000, 7),
    P('wordbyte', 'WORDPAD BYTE', 0, 255, 10),
    P('alpha', 'KEEP SHAPE (alpha)', choices=['yes', 'no']),
]


def apply(img, p, rng):
    h, w = img.shape[:2]
    data = np.ascontiguousarray(img[..., :3]).reshape(-1).copy()
    n = data.size
    m = p['mode']
    if m in ('insert bytes', 'delete bytes'):
        pos = np.sort(rng.integers(0, n, p['hits']))
        parts, last = [], 0
        for q in pos:
            parts.append(data[last:q])
            if m == 'insert bytes':
                parts.append(rng.integers(0, 256, p['size'], dtype=np.uint8))
                last = q
            else:
                last = min(n, q + p['size'])
        parts.append(data[last:])
        data = np.concatenate(parts)
    elif m == 'echo runs':
        for _ in range(p['hits']):
            ln = int(min(n // 4, p['size'] * 50))
            a = int(rng.integers(0, n - ln))
            b = int(rng.integers(0, n - ln))
            data[b:b + ln] = data[a:a + ln]
    elif m == 'bit flips':
        k = p['hits'] * p['size']
        idx = rng.integers(0, n, k)
        data[idx] ^= (1 << rng.integers(0, 8, k)).astype(np.uint8)
    else:                                                            # WordPad turns each LF into CR LF
        hit = np.flatnonzero(data == p['wordbyte'])
        if len(hit):
            data = np.insert(data, hit, np.uint8(13))
    if data.size < n:
        data = np.concatenate([data, data[:n - data.size]])
    out = img.copy()
    out[..., :3] = data[:n].reshape(h, w, 3)
    if p['alpha'] == 'no':
        out[..., 3] = 255
    return out
