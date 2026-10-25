"""Document: layers, compositing, undo, and ORA/PNG files (ORA opens in Krita with layers intact)."""
import io, os, zipfile
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

UNDO_LIMIT = 30
UNDO_BYTES = 1500 * 1024 * 1024        # big pictures: keep fewer undo steps instead of eating all the RAM


class Layer:
    def __init__(self, name, arr, visible=True, opacity=1.0):
        self.name = name
        self.arr = arr                      # HxWx4 uint8, straight (not premultiplied) alpha
        self.visible = visible
        self.opacity = opacity


class Document:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.layers = []                    # bottom .. top
        self.active = 0
        self.source = None                  # file it was opened from: never overwritten
        self.path = None                    # last ORA saved by Glitch Lab (Ctrl+S re-saves here)
        self.undo, self.redo = [], []
        self.comp = np.zeros((h, w, 4), np.uint8)
        self.mask = np.zeros((h, w, 4), np.uint8)       # selection: alpha channel only (brushes paint it like a layer)
        self.overlay = np.zeros((h, w, 4), np.uint8)    # pink tint shown over the canvas where the mask is
        self.overlay[..., 0], self.overlay[..., 1], self.overlay[..., 2] = 255, 40, 200
        self.has_mask = False

    # ---------- layers ----------
    @property
    def layer(self):
        return self.layers[self.active]

    def blank(self, name='Layer'):
        return Layer(name, np.zeros((self.h, self.w, 4), np.uint8))

    # ---------- compositing ----------
    def composite(self, rect=None):
        x0, y0, x1, y1 = rect or (0, 0, self.w, self.h)
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1, y1 = min(self.w, int(x1)), min(self.h, int(y1))
        if x1 <= x0 or y1 <= y0:
            return None
        vis = [L for L in self.layers if L.visible and L.opacity > 0]
        if len(vis) <= 1 and (not vis or vis[0].opacity >= 1):  # one plain layer (the usual case): just copy it
            if vis:
                self.comp[y0:y1, x0:x1] = vis[0].arr[y0:y1, x0:x1]
            else:
                self.comp[y0:y1, x0:x1] = 0
            return x0, y0, x1, y1
        rgb = np.zeros((y1 - y0, x1 - x0, 3), np.float32)        # premultiplied accumulator
        a = np.zeros((y1 - y0, x1 - x0, 1), np.float32)
        for L in self.layers:
            if not L.visible or L.opacity <= 0:
                continue
            s = L.arr[y0:y1, x0:x1].astype(np.float32) / 255
            sa = s[..., 3:4] * L.opacity
            rgb = s[..., :3] * sa + rgb * (1 - sa)
            a = sa + a * (1 - sa)
        out = np.where(a > 0, rgb / np.maximum(a, 1e-6), 0)
        self.comp[y0:y1, x0:x1, :3] = np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)
        self.comp[y0:y1, x0:x1, 3] = np.clip(a[..., 0] * 255 + 0.5, 0, 255).astype(np.uint8)
        return x0, y0, x1, y1

    # ---------- undo ----------
    def push(self, entry):
        self.undo.append(entry)
        del self.undo[:-UNDO_LIMIT]
        size = lambda e: e[2].nbytes if e[0] == 'pixels' else (e[1].nbytes if e[0] == 'mask' else 0)
        while len(self.undo) > 3 and sum(size(e) for e in self.undo) > UNDO_BYTES:
            del self.undo[0]                                      # oldest steps go first
        self.redo.clear()

    def push_pixels(self, layer):
        self.push(('pixels', layer, layer.arr.copy()))

    def push_mask(self):
        self.push(('mask', self.mask[..., 3].copy()))

    def mask_changed(self, rect=None):
        x0, y0, x1, y1 = rect or (0, 0, self.w, self.h)
        x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(self.w, int(x1)), min(self.h, int(y1))
        self.overlay[y0:y1, x0:x1, 3] = self.mask[y0:y1, x0:x1, 3] // 2
        if rect is None:
            self.has_mask = bool(self.mask[..., 3].any())
        elif not self.has_mask:
            self.has_mask = bool(self.mask[y0:y1, x0:x1, 3].any())

    def masked_with(self, mask, before, after):
        """masked() with a mask captured earlier (safe to run in a background thread)."""
        if mask is None:
            return after
        m = mask[..., None].astype(np.float32) / 255
        return (before.astype(np.float32) * (1 - m) + after.astype(np.float32) * m + 0.5).astype(np.uint8)

    def masked(self, before, after):
        """Blend a filter result into the layer only where the mask is (whole layer if there is no mask)."""
        if not self.has_mask:
            return after
        m = self.mask[..., 3:4].astype(np.float32) / 255
        return (before.astype(np.float32) * (1 - m) + after.astype(np.float32) * m + 0.5).astype(np.uint8)

    def push_stack(self):
        self.push(('stack', list(self.layers), self.active))

    def _swap(self, entry):
        if entry[0] == 'mask':
            cur = self.mask[..., 3].copy()
            self.mask[..., 3] = entry[1]
            self.mask_changed()
            return ('mask', cur)
        if entry[0] == 'pixels':
            _, L, old = entry
            cur, L.arr = L.arr, old
            if L in self.layers:
                self.active = self.layers.index(L)
            return ('pixels', L, cur)
        _, layers, active = entry
        cur = ('stack', self.layers, self.active)
        self.layers, self.active = list(layers), active
        return cur

    def do_undo(self):
        if not self.undo:
            return False
        self.redo.append(self._swap(self.undo.pop()))
        return True

    def do_redo(self):
        if not self.redo:
            return False
        self.undo.append(self._swap(self.redo.pop()))
        return True

    # ---------- files ----------
    @classmethod
    def new(cls, w, h, paper=(255, 255, 255)):
        d = cls(w, h)
        bg = d.blank('Paper')
        bg.arr[..., :3] = paper
        bg.arr[..., 3] = 255
        d.layers = [bg, d.blank('Glitch')]
        d.active = 1
        d.composite()
        return d

    @classmethod
    def open(cls, path):
        if path.lower().endswith('.ora'):
            d = cls._open_ora(path)
        else:
            im = np.asarray(Image.open(path).convert('RGBA')).copy()
            d = cls(im.shape[1], im.shape[0])
            d.layers = [Layer(os.path.splitext(os.path.basename(path))[0], im)]   # picture selected: erase/slip work on it
            d.active = 0
        d.source = os.path.abspath(path)
        d.composite()
        return d

    @classmethod
    def _open_ora(cls, path):
        z = zipfile.ZipFile(path)
        root = ET.fromstring(z.read('stack.xml'))
        d = cls(int(root.get('w')), int(root.get('h')))
        found = []

        def walk(stack, ox, oy):                              # stack.xml lists top first; groups get flattened
            for el in stack:
                x, y = ox + int(float(el.get('x', 0))), oy + int(float(el.get('y', 0)))
                if el.tag == 'stack':
                    walk(el, x, y)
                elif el.tag == 'layer' and el.get('src'):
                    try:
                        im = np.asarray(Image.open(io.BytesIO(z.read(el.get('src')))).convert('RGBA'))
                    except Exception:
                        continue
                    arr = np.zeros((d.h, d.w, 4), np.uint8)
                    sx0, sy0 = max(0, -x), max(0, -y)
                    dx0, dy0 = max(0, x), max(0, y)
                    cw = min(im.shape[1] - sx0, d.w - dx0)
                    ch = min(im.shape[0] - sy0, d.h - dy0)
                    if cw > 0 and ch > 0:
                        arr[dy0:dy0 + ch, dx0:dx0 + cw] = im[sy0:sy0 + ch, sx0:sx0 + cw]
                    found.append(Layer(el.get('name', 'Layer'), arr,
                                       el.get('visibility', 'visible') != 'hidden',
                                       float(el.get('opacity', 1))))
        walk(root.find('stack'), 0, 0)
        d.layers = found[::-1] or [d.blank()]
        d.active = len(d.layers) - 1
        return d

    def save_ora(self, path):
        path = os.path.abspath(path)
        if self.source and os.path.normcase(path) == os.path.normcase(self.source):
            raise ValueError('that is the file you opened; save under a new name')
        self.composite()
        stack = ET.Element('image', w=str(self.w), h=str(self.h), version='0.0.3')
        st = ET.SubElement(stack, 'stack')
        tmp = path + '.tmp'
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr(zipfile.ZipInfo('mimetype'), 'image/openraster', zipfile.ZIP_STORED)
            for i, L in reversed(list(enumerate(self.layers))):
                src = 'data/layer%03d.png' % i
                ET.SubElement(st, 'layer', name=L.name, src=src, x='0', y='0',
                              opacity='%.3f' % L.opacity, visibility='visible' if L.visible else 'hidden')
                z.writestr(src, png_bytes(L.arr))
            z.writestr('stack.xml', ET.tostring(stack, encoding='utf-8', xml_declaration=True))
            z.writestr('mergedimage.png', png_bytes(self.comp))
            th = Image.fromarray(self.comp, 'RGBA')
            th.thumbnail((256, 256))
            b = io.BytesIO(); th.save(b, 'PNG')
            z.writestr('Thumbnails/thumbnail.png', b.getvalue())
        os.replace(tmp, path)
        self.path = path

    def export_png(self, path):
        path = os.path.abspath(path)
        if self.source and os.path.normcase(path) == os.path.normcase(self.source):
            raise ValueError('that is the file you opened; export under a new name')
        self.composite()
        Image.fromarray(self.comp, 'RGBA').save(path)


def png_bytes(arr):
    b = io.BytesIO()
    Image.fromarray(arr, 'RGBA').save(b, 'PNG', compress_level=3)
    return b.getvalue()
