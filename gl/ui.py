"""Glitch Lab window: retro purple bevels, pixel title, canvas with pen pressure, effect panels, layers."""
import json, math, os, random, time, traceback

import numpy as np
from PySide6.QtCore import Qt, QTimer, QRect, QRectF, QPointF, QEvent
from PySide6.QtGui import (QAction, QBrush, QColor, QFont, QImage, QKeySequence, QPainter, QPen, QPixmap,
                           QPointingDevice, QInputDevice, QShortcut, QIcon)
from PySide6.QtWidgets import (QApplication, QCheckBox, QColorDialog, QComboBox, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMainWindow, QTabWidget,
                               QMessageBox, QPushButton, QScrollArea, QSlider, QVBoxLayout, QWidget, QButtonGroup)

from . import effects
from .doc import Document

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = '0.2'

# ---------------------------------------------------------------- look
C = dict(bg='#160e20', panel='#24183a', hi='#a77ae0', lo='#07040c', face='#34234f', text='#e8d8ff',
         green='#7dffb0', pink='#ff4fd8', cyan='#4ff3ff', sel='#7b2fbe', well='#0d0816')
QSS = """
* {{ font-family: Consolas, 'Lucida Console', monospace; font-size: 12px; color: {text}; }}
QMainWindow, QWidget#root {{ background: {bg}; }}
QFrame#panel {{ background: {panel}; border: 2px solid; border-color: {hi} {lo} {lo} {hi}; }}
QLabel#sect {{ color: {green}; font-weight: bold; padding: 2px 0 1px 0; }}
QLabel#val {{ color: {cyan}; }}
QPushButton {{ background: {face}; border: 2px solid; border-color: {hi} {lo} {lo} {hi}; padding: 4px 8px; }}
QPushButton:hover {{ background: #45306a; }}
QPushButton:pressed, QPushButton:checked {{ background: #1b1030; border-color: {lo} {hi} {hi} {lo}; color: {green}; }}
QPushButton#erase:checked {{ color: {pink}; }}
QSlider::groove:horizontal {{ height: 6px; background: {lo}; border: 1px solid #5a3f86; }}
QSlider::sub-page:horizontal {{ background: {sel}; }}
QSlider::handle:horizontal {{ width: 10px; margin: -6px 0; background: #c9a6ff;
    border: 2px solid; border-color: #ffffff #4a2d70 #4a2d70 #ffffff; }}
QListWidget {{ background: {well}; border: 2px solid; border-color: {lo} {hi} {hi} {lo}; }}
QListWidget::item {{ padding: 3px; }}
QListWidget::item:selected {{ background: {sel}; color: #ffffff; }}
QComboBox {{ background: {well}; border: 2px solid; border-color: {lo} {hi} {hi} {lo}; padding: 3px; }}
QComboBox QAbstractItemView {{ background: {well}; selection-background-color: {sel}; }}
QCheckBox::indicator {{ width: 12px; height: 12px; background: {well}; border: 2px solid; border-color: {lo} {hi} {hi} {lo}; }}
QCheckBox::indicator:checked {{ background: {green}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: {lo}; width: 12px; }}
QScrollBar::handle:vertical {{ background: {face}; border: 2px solid; border-color: {hi} {lo} {lo} {hi}; }}
QLabel#status {{ background: {lo}; color: {green}; padding: 3px 6px; border-top: 2px solid {sel}; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: {face}; border: 2px solid; border-color: {hi} {lo} {lo} {hi}; padding: 3px 12px; }}
QTabBar::tab:selected {{ background: {sel}; color: #ffffff; }}
QPushButton#mask:checked {{ color: {pink}; }}
""".format(**C)


def sect(text):
    l = QLabel('▓▒░ ' + text)
    l.setObjectName('sect')
    return l


def panel():
    f = QFrame()
    f.setObjectName('panel')
    v = QVBoxLayout(f)
    v.setContentsMargins(8, 6, 8, 8)
    v.setSpacing(4)
    return f, v


class Title(QWidget):
    """Pixel-font GLITCH LAB with RGB split that glitches now and then."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(46)
        f = QFont('Consolas')
        f.setPixelSize(11)
        f.setBold(True)
        f.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
        self.small = QImage(84, 13, QImage.Format.Format_ARGB32)
        self.small.fill(Qt.transparent)
        p = QPainter(self.small)
        p.setFont(f)
        p.setPen(QColor('white'))
        p.drawText(self.small.rect(), Qt.AlignLeft | Qt.AlignVCenter, 'GLITCH LAB')
        p.end()
        self.tinted = {c: self.tint(c) for c in (C['pink'], C['cyan'], '#ffffff')}
        self.split, self.cut = 2, None
        self.mode = 'PAINT'
        t = QTimer(self)
        t.timeout.connect(self.tick)
        t.start(110)

    def tick(self):
        r = random.random()
        self.split = random.choice([3, 5, 8]) if r < 0.08 else 2
        self.cut = (random.randint(0, 38), random.randint(2, 8), random.randint(-14, 14)) if r < 0.05 else None
        self.update()

    def tint(self, color):
        im = self.small.copy()
        p = QPainter(im)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p.fillRect(im.rect(), QColor(color))
        p.end()
        return im

    def letters(self, p, x, y, tw, th):
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        for col, dx in ((C['pink'], -self.split), (C['cyan'], self.split), ('#ffffff', 0)):
            p.drawImage(QRectF(x + dx, y, tw, th), self.tinted[col])
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(C['lo']))
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        s = 3
        tw, th = self.small.width() * s, self.small.height() * s
        x, y = 12, (self.height() - th) // 2
        self.letters(p, x, y, tw, th)
        if self.cut:                                              # a torn band, slid sideways
            cy, ch, cx = self.cut
            p.setClipRect(QRect(0, y + cy, self.width(), ch))
            p.fillRect(self.rect(), QColor(C['lo']))
            self.letters(p, x + cx, y, tw, th)
            p.setClipping(False)
        p.setPen(QColor(0, 0, 0, 90))
        for yy in range(0, self.height(), 2):
            p.drawLine(0, yy, self.width(), yy)
        p.setPen(QColor(C['green']))
        p.setFont(QFont('Consolas', 9))
        p.drawText(x + tw + 16, y + th - 4, 'v%s // lo-fi glitch studio' % VERSION)
        p.setPen(QColor(C['pink'] if self.mode == 'ERASE' else C['green']))
        p.setFont(QFont('Consolas', 11, QFont.Weight.Bold))
        p.drawText(self.rect().adjusted(0, 0, -16, 0), Qt.AlignRight | Qt.AlignVCenter, '[ %s ]' % self.mode)


class Params(QWidget):
    """Auto-built sliders / choice boxes for one effect's PARAMS."""

    def __init__(self, on_change):
        super().__init__()
        self.on_change = on_change
        self.g = QGridLayout(self)
        self.g.setContentsMargins(0, 0, 0, 0)
        self.g.setVerticalSpacing(3)
        self.widgets = {}

    def build(self, mod, values):
        while self.g.count():
            w = self.g.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        for r in range(self.g.rowCount()):
            self.g.setRowStretch(r, 0)
        self.mod, self.values, self.widgets = mod, values, {}
        for row, q in enumerate(mod.PARAMS):
            k = q['key']
            lab = QLabel(q['label'])
            self.g.addWidget(lab, row * 2, 0)
            if 'choices' in q:
                w = QComboBox()
                w.addItems(q['choices'])
                w.setCurrentText(str(values[k]))
                w.currentTextChanged.connect(lambda t, k=k: self.changed(k, t))
                self.g.addWidget(w, row * 2 + 1, 0, 1, 2)
            else:
                val = QLabel()
                val.setObjectName('val')
                val.setAlignment(Qt.AlignRight)
                self.g.addWidget(val, row * 2, 1)
                w = QSlider(Qt.Horizontal)
                n = max(1, int(round((q['hi'] - q['lo']) / q['step'])))
                w.setRange(0, n)
                w.setValue(int(round((values[k] - q['lo']) / q['step'])))
                w.valueChanged.connect(lambda i, k=k, q=q, val=val: self.slid(k, q, i, val))
                self.g.addWidget(w, row * 2 + 1, 0, 1, 2)
                self.show_val(q, values[k], val)
                w.val = val
            self.widgets[k] = w
        self.g.setRowStretch(len(mod.PARAMS) * 2, 1)                 # keep rows packed at the top

    def show_val(self, q, v, lab):
        lab.setText(str(int(v)) if q['int'] else '%.2f' % v)

    def slid(self, k, q, i, lab):
        v = q['lo'] + i * q['step']
        v = int(round(v)) if q['int'] else round(v, 4)
        self.show_val(q, v, lab)
        self.changed(k, v)

    def changed(self, k, v):
        self.values[k] = v
        self.on_change()

    def set_values(self, values):
        """Moves the widgets to new values without firing on_change."""
        for q in self.mod.PARAMS:
            w, v = self.widgets.get(q['key']), values.get(q['key'])
            if w is None or v is None:
                continue
            w.blockSignals(True)
            if 'choices' in q:
                w.setCurrentText(str(v))
            else:
                w.setValue(int(round((v - q['lo']) / q['step'])))
                self.show_val(q, v, w.val)
            w.blockSignals(False)


class Canvas(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.doc = None
        self.img = None
        self.s, self.ox, self.oy = 1.0, 0.0, 0.0
        self.stroke = None
        self.stroke_mask = False
        self.before = None
        self.pan = None
        self.space = False
        self.last_tablet = 0.0
        self.hover = None                                   # widget pos of the pen/mouse, for the brush outline
        self.pinch = None
        self.setMouseTracking(True)
        self.setTabletTracking(True)
        self.setAttribute(Qt.WA_AcceptTouchEvents)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.CrossCursor)
        self.setAcceptDrops(True)
        bg = QPixmap(4, 4)
        bg.fill(QColor('#120b1a'))
        p = QPainter(bg); p.fillRect(0, 0, 4, 1, QColor('#0b0611')); p.end()
        self.bg = QBrush(bg)
        ck = QPixmap(16, 16)
        ck.fill(QColor('#3a3346'))
        p = QPainter(ck); p.fillRect(0, 0, 8, 8, QColor('#2a2433')); p.fillRect(8, 8, 8, 8, QColor('#2a2433')); p.end()
        self.checker = QBrush(ck)

    # ---- view
    def set_doc(self, doc):
        self.doc = doc
        self.img = QImage(doc.comp.data, doc.w, doc.h, doc.w * 4, QImage.Format.Format_RGBA8888)
        self.mimg = QImage(doc.overlay.data, doc.w, doc.h, doc.w * 4, QImage.Format.Format_RGBA8888)
        self.fit()

    def fit(self):
        if not self.doc:
            return
        self.s = min(self.width() / self.doc.w, self.height() / self.doc.h) * 0.94
        self.center()

    def center(self):
        self.ox = (self.width() - self.doc.w * self.s) / 2
        self.oy = (self.height() - self.doc.h * self.s) / 2
        self.update()

    def to_doc(self, pos):
        return (pos.x() - self.ox) / self.s, (pos.y() - self.oy) / self.s

    def refresh(self, rect=None):
        if not self.doc:
            return
        r = self.doc.composite(rect)
        if rect is None:
            self.update()
        elif r:
            x0, y0, x1, y1 = r
            self.update(QRect(int(self.ox + x0 * self.s) - 2, int(self.oy + y0 * self.s) - 2,
                              int((x1 - x0) * self.s) + 5, int((y1 - y0) * self.s) + 5))

    def resizeEvent(self, ev):
        if self.doc and ev.oldSize().width() <= 0:
            self.fit()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.fillRect(ev.rect(), self.bg)
        if not self.doc:
            p.setPen(QColor(C['green']))
            p.setFont(QFont('Consolas', 14))
            p.drawText(self.rect(), Qt.AlignCenter,
                       'DROP A PNG / ORA HERE\nor  NEW  /  OPEN\n\n> waiting for signal_')
            return
        d, s = self.doc, self.s
        cr = QRectF(self.ox, self.oy, d.w * s, d.h * s)
        vis = QRectF(ev.rect()).intersected(cr)
        if vis.isEmpty():
            return
        sx0 = max(0, int(math.floor((vis.left() - self.ox) / s)))
        sy0 = max(0, int(math.floor((vis.top() - self.oy) / s)))
        sx1 = min(d.w, int(math.ceil((vis.right() - self.ox) / s)) + 1)
        sy1 = min(d.h, int(math.ceil((vis.bottom() - self.oy) / s)) + 1)
        tgt = QRectF(self.ox + sx0 * s, self.oy + sy0 * s, (sx1 - sx0) * s, (sy1 - sy0) * s)
        p.setClipRect(cr)
        p.fillRect(tgt, self.checker)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, s < 1)
        p.drawImage(tgt, self.img, QRectF(sx0, sy0, sx1 - sx0, sy1 - sy0))
        if d.has_mask and self.win.show_mask.isChecked():
            p.drawImage(tgt, self.mimg, QRectF(sx0, sy0, sx1 - sx0, sy1 - sy0))
        p.setClipping(False)
        p.setPen(QPen(QColor(C['sel']), 1))
        p.drawRect(cr.adjusted(-1, -1, 0, 0))
        r = self.outline_rect()
        if r is not None:
            kind, rect = r
            for col, w in ((QColor(0, 0, 0, 200), 3), (QColor(255, 255, 255, 230), 1)):
                p.setPen(QPen(col, w))
                p.setBrush(Qt.NoBrush)
                (p.drawEllipse if kind == 'circle' else p.drawRect)(rect)

    def outline_rect(self):
        b = self.win.brush
        if self.hover is None or not b or not hasattr(b, 'outline'):
            return None
        try:
            kind, w, h = b.outline(self.win.params[b.ID])
        except Exception:
            return None
        w, h = max(3.0, w * self.s), max(3.0, h * self.s)
        return kind, QRectF(self.hover.x() - w / 2, self.hover.y() - h / 2, w, h)

    def move_hover(self, pos):
        old = self.outline_rect()
        self.hover = pos
        new = self.outline_rect()
        for r in (old, new):
            if r:
                self.update(r[1].toAlignedRect().adjusted(-3, -3, 3, 3))

    def leaveEvent(self, ev):
        self.move_hover(None)

    def zoom_at(self, ns, pos=None):
        if not self.doc:
            return
        pos = pos or QPointF(self.width() / 2, self.height() / 2)
        ns = min(64.0, max(0.03, ns))
        x, y = self.to_doc(pos)
        self.s = ns
        self.ox, self.oy = pos.x() - x * ns, pos.y() - y * ns
        self.update()
        self.win.pos_status((x, y))

    def event(self, ev):
        t = ev.type()
        if t in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd, QEvent.Type.TouchCancel):
            self.touch_event(ev)
            return True
        return super().event(ev)

    def touch_event(self, ev):
        """One finger pans, two fingers pinch-zoom (fingers never paint)."""
        pts = [p.position() for p in ev.points()]
        if ev.type() in (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel) or not pts or not self.doc:
            self.pinch = None
            return
        cx = sum(p.x() for p in pts) / len(pts)
        cy = sum(p.y() for p in pts) / len(pts)
        dist = math.hypot(pts[0].x() - pts[-1].x(), pts[0].y() - pts[-1].y()) if len(pts) > 1 else 0
        if self.pinch is None or self.pinch[0] != len(pts):
            self.pinch = (len(pts), cx, cy, dist, self.s, self.to_doc(QPointF(cx, cy)))
            return
        n, _, _, d0, s0, (dx, dy) = self.pinch
        if n > 1 and d0 > 10:
            self.s = min(64.0, max(0.03, s0 * dist / d0))
        self.ox, self.oy = cx - dx * self.s, cy - dy * self.s       # the picture point under the fingers stays there
        self.update()

    # ---- strokes
    def begin(self, pos, pr, eraser):
        w = self.win
        if not self.doc or not w.brush:
            return
        w.commit_preview()
        if w.mask_pick:                                         # BY COLOUR: one click selects that colour
            w.mask_by_colour(self.to_doc(pos))
            return
        if w.mask_mode:                                         # any brush paints the mask instead of the layer
            self.doc.push_mask()
            ctx = effects.Ctx(self.doc.mask, (255, 255, 255), w.erase or eraser, w.params[w.brush.ID], w.rng)
            self.stroke_mask, self.before = True, None
            self.stroke = effects.Stroke(w.brush, ctx)
            self.feed(pos, pr)
            return
        L = self.doc.layer
        if not L.visible:
            w.say('active layer is hidden'); return
        if (w.erase or eraser or getattr(w.brush, 'NEEDS_PIXELS', False)) and not L.arr[..., 3].any():
            w.say('"%s" is empty: erasing / slipping needs a layer with picture on it' % L.name)
        src = None
        if getattr(w.brush, 'NEEDS_FILTER', False):
            src = w.filter_source(L)
            if src is None:
                return
        self.doc.push_pixels(L)
        self.stroke_mask, self.before = False, self.doc.undo[-1][2]
        ctx = effects.Ctx(L.arr, w.color, w.erase or eraser, w.params[w.brush.ID], w.rng,
                          w.cmode, w.palette, w.per_pixel.isChecked(), self.doc.comp)
        ctx.source = src
        self.stroke = effects.Stroke(w.brush, ctx)
        self.feed(pos, pr)

    def feed(self, pos, pr):
        x, y = self.to_doc(pos)
        try:
            self.stroke.to(x, y, pr)
        except Exception:
            self.win.say('brush error: ' + traceback.format_exc(limit=1).splitlines()[-1])
            self.stroke = None
            return
        self.flush()

    def flush(self):
        ctx = self.stroke.ctx
        if not ctx.dirty:
            return
        x0, y0, x1, y1 = (int(v) for v in ctx.dirty)
        if self.stroke_mask:
            self.doc.mask_changed(ctx.dirty)
        elif self.doc.has_mask and self.win.mask_brushes.isChecked() and self.before is not None:
            m = self.doc.mask[y0:y1, x0:x1, 3:4].astype(np.float32) / 255     # strokes only land inside the mask
            r = ctx.arr[y0:y1, x0:x1]
            r[:] = (self.before[y0:y1, x0:x1] * (1 - m) + r * m + 0.5).astype(np.uint8)
        self.refresh(ctx.dirty)
        ctx.dirty = None

    def finish(self):
        if not self.stroke:
            return
        try:
            self.stroke.end()
            self.flush()
        except Exception:
            self.win.say('brush error: ' + traceback.format_exc(limit=1).splitlines()[-1])
        if self.stroke_mask:
            self.doc.mask_changed()
        elif not getattr(self.win.brush, 'NEEDS_FILTER', False):
            self.win.fgen += 1                                  # layer changed: filter brush re-renders next time
        self.stroke = None
        self.before = None
        self.win.touched()

    # ---- input
    def tabletEvent(self, ev):
        self.last_tablet = time.time()
        t = ev.type()
        if t == QEvent.Type.TabletPress:
            self.setFocus()
            if ev.button() == Qt.LeftButton:
                self.begin(ev.position(), ev.pressure(), ev.pointerType() == QPointingDevice.PointerType.Eraser)
        elif t == QEvent.Type.TabletMove:
            if self.stroke:
                self.feed(ev.position(), ev.pressure())
            self.move_hover(ev.position())
            self.win.pos_status(self.to_doc(ev.position()))
        elif t == QEvent.Type.TabletRelease:
            self.finish()
        ev.accept()

    def from_pen(self, ev):
        return time.time() - self.last_tablet < 0.4

    def is_touch(self, ev):
        d = ev.device()
        return d is not None and d.type() == QInputDevice.DeviceType.TouchScreen

    def mousePressEvent(self, ev):
        self.setFocus()
        if self.from_pen(ev):
            return
        if ev.button() == Qt.MiddleButton or self.space or self.is_touch(ev):
            self.pan = (ev.position(), self.ox, self.oy)
            self.setCursor(Qt.ClosedHandCursor)
        elif ev.button() == Qt.LeftButton:
            self.begin(ev.position(), 1.0, False)

    def mouseMoveEvent(self, ev):
        if self.pan:
            p0, ox, oy = self.pan
            self.ox, self.oy = ox + ev.position().x() - p0.x(), oy + ev.position().y() - p0.y()
            self.update()
        elif self.stroke and not self.from_pen(ev):
            self.feed(ev.position(), 1.0)
        if not self.from_pen(ev):
            self.move_hover(ev.position())
        if self.doc:
            self.win.pos_status(self.to_doc(ev.position()))

    def mouseReleaseEvent(self, ev):
        if self.pan:
            self.pan = None
            self.setCursor(Qt.CrossCursor)
        elif not self.from_pen(ev):
            self.finish()

    def wheelEvent(self, ev):
        if not self.doc:
            return
        self.zoom_at(self.s * 1.25 ** (ev.angleDelta().y() / 120), ev.position())

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Space and not ev.isAutoRepeat():
            self.space = True
            self.setCursor(Qt.OpenHandCursor)
        else:
            super().keyPressEvent(ev)

    def keyReleaseEvent(self, ev):
        if ev.key() == Qt.Key_Space and not ev.isAutoRepeat():
            self.space = False
            self.setCursor(Qt.CrossCursor)
        else:
            super().keyReleaseEvent(ev)

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        urls = ev.mimeData().urls()
        if urls:
            self.win.open_path(urls[0].toLocalFile())


class Win(QMainWindow):
    def __init__(self, path=None):
        super().__init__()
        self.setWindowTitle('GLITCH LAB')
        ico = os.path.join(HERE, 'glitch_lab.ico')
        if os.path.exists(ico):
            self.setWindowIcon(QIcon(ico))
        self.resize(1500, 950)
        self.fx, errs = effects.load(os.path.join(HERE, 'effects'))
        self.brushes = [m for m in self.fx if m.KIND == 'brush']
        self.filters = [m for m in self.fx if m.KIND == 'filter']
        order = ['dotline', 'speckle', 'staticbrush', 'blockbrush', 'filterbrush', 'stretch', 'mosaic', 'hueshift',
                 'rowslip', 'pixelpen']           # nice order, new ones go after
        self.brushes.sort(key=lambda m: order.index(m.ID) if m.ID in order else 99)
        self.params = {m.ID: effects.defaults(m) for m in self.fx}
        self.brush = self.brushes[0] if self.brushes else None
        self.filter = self.filters[0] if self.filters else None
        self.color = (16, 8, 24)
        self.erase = False
        self.cmode = 'pick'
        self.palette = [(255, 79, 216), (79, 243, 255), (125, 255, 176), (123, 47, 190), (255, 255, 255)]
        self.seed = 1
        self.rng = np.random.default_rng()
        self.live = None                                                # (layer, untouched copy) while previewing
        self.mask_mode = False                                          # M: brushes paint the selection mask
        self.mask_pick = False                                          # next click selects by colour
        self.stack = []                                                 # glitch stack: [{effect, params}, ...]
        self.fgen = 0                                                   # bumps when the layer changes (filter brush cache)
        self.fcache = None
        self.dirty = False
        self.doc = None

        root = QWidget(); root.setObjectName('root')
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.title = Title()
        v.addWidget(self.title)
        v.addWidget(self.build_toolbar())
        mid = QHBoxLayout()
        mid.setContentsMargins(6, 6, 6, 6)
        mid.setSpacing(6)
        self.canvas = Canvas(self)
        mid.addWidget(self.build_left())
        mid.addWidget(self.canvas, 1)
        mid.addWidget(self.build_right())
        v.addLayout(mid, 1)
        self.status = QLabel()
        self.status.setObjectName('status')
        v.addWidget(self.status)
        self.msg = 'READY'
        self.posmsg = ''
        self.blink = True
        bt = QTimer(self); bt.timeout.connect(self.blink_tick); bt.start(500)

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.run_preview)
        self.layer_timer = QTimer(self)
        self.layer_timer.setSingleShot(True)
        self.layer_timer.timeout.connect(lambda: self.canvas.refresh())
        at = QTimer(self); at.timeout.connect(self.autosave); at.start(180000)

        for keys, fn in (('Ctrl+Z', self.undo), ('Ctrl+Y', self.redo), ('Ctrl+Shift+Z', self.redo),
                         ('Ctrl+S', self.save), ('Ctrl+Shift+S', self.save_as), ('Ctrl+O', self.open_dialog),
                         ('Ctrl+N', self.new_dialog), ('Ctrl+E', self.export), ('E', self.toggle_erase),
                         ('[', lambda: self.size_step(1 / 1.2)), (']', lambda: self.size_step(1.2)),
                         ('F', self.canvas.fit), ('1', self.zoom100), ('Ctrl+Return', self.apply_filter),
                         ('+', lambda: self.zoom_step(1.5)), ('=', lambda: self.zoom_step(1.5)),
                         ('-', lambda: self.zoom_step(1 / 1.5)), ('M', self.toggle_mask_mode)):
            QShortcut(QKeySequence(keys), self, fn)

        self.load_presets()
        self.pick_brush(self.brush)
        self.pick_filter(self.filter)
        if errs:
            self.say('effect load errors: ' + ' | '.join(errs))
        if path:
            self.open_path(path)
        else:
            self.say('READY: drop a PNG/ORA or press NEW. E = erase, [ ] = size, space-drag = pan')

    # ---------------------------------------------------------------- building
    def btn(self, text, fn, tip=None, check=False):
        b = QPushButton(text)
        b.setCheckable(check)
        if fn:
            b.clicked.connect(fn)
        if tip:
            b.setToolTip(tip)
        b.setFocusPolicy(Qt.NoFocus)
        return b

    def build_toolbar(self):
        f = QFrame(); f.setObjectName('panel')
        h = QHBoxLayout(f)
        h.setContentsMargins(6, 4, 6, 4)
        for text, fn, tip in (('NEW', self.new_dialog, 'Ctrl+N'), ('OPEN', self.open_dialog, 'Ctrl+O  PNG / JPG / ORA'),
                              ('SAVE ORA', self.save, 'Ctrl+S  layered, opens in Krita'),
                              ('SAVE AS', self.save_as, 'Ctrl+Shift+S'), ('EXPORT PNG', self.export, 'Ctrl+E  flattened copy'),
                              (None, None, None),
                              ('◀ UNDO', self.undo, 'Ctrl+Z'), ('REDO ▶', self.redo, 'Ctrl+Y'),
                              (None, None, None),
                              ('ZOOM -', lambda: self.zoom_step(1 / 1.5), '-  (or mouse wheel / pinch)'),
                              ('ZOOM +', lambda: self.zoom_step(1.5), '+  (or mouse wheel / pinch)'),
                              ('FIT', self.canvas_fit, 'F'), ('1:1', self.zoom100, '1'),
                              ('RELOAD FX', self.reload_fx, 'reload the effects folder (new effect files)')):
            if text is None:
                h.addSpacing(16)
            else:
                h.addWidget(self.btn(text, fn, tip))
        h.addStretch(1)
        return f

    def canvas_fit(self):
        self.canvas.fit()

    def build_left(self):
        f, v = panel()
        f.setFixedWidth(270)
        v.addWidget(sect('PRESETS'))
        self.preset_box = QComboBox()
        self.preset_box.activated.connect(self.pick_preset)
        v.addWidget(self.preset_box)
        v.addWidget(self.btn('SAVE CURRENT AS PRESET', self.save_preset))
        v.addSpacing(6)
        v.addWidget(sect('BRUSHES'))
        self.brush_group = QButtonGroup(self)
        self.brush_btns = {}
        grid = QGridLayout()
        grid.setSpacing(3)
        for i, m in enumerate(self.brushes):
            b = self.btn(m.NAME.upper(), None, (m.__doc__ or '').strip(), check=True)
            b.clicked.connect(lambda _=False, m=m: self.pick_brush(m))
            self.brush_group.addButton(b)
            self.brush_btns[m.ID] = b
            grid.addWidget(b, i // 2, i % 2)
        v.addLayout(grid)
        row = QHBoxLayout()
        self.color_btn = self.btn('', self.pick_color, 'paint colour')
        self.color_btn.setFixedWidth(60)
        self.erase_btn = self.btn('PAINT', self.toggle_erase, 'E: paint / erase (pen eraser end always erases)', check=True)
        self.erase_btn.setObjectName('erase')
        row.addWidget(self.color_btn)
        row.addWidget(self.erase_btn, 1)
        v.addLayout(row)
        self.show_color()
        row = QHBoxLayout()
        row.addWidget(QLabel('COLOUR'))
        self.cmode_box = QComboBox()
        for m, tip in (('pick', 'the colour in the swatch'), ('palette', 'random pick from the 5 swatches below'),
                       ('random', 'random RGB'), ('rgb', 'pure red / green / blue'),
                       ('bust', "the picture's own colours, busted (hue spin, channel swap, invert)"),
                       ('golden', 'golden-ratio hue steps: evenly spread rainbow'),
                       ('drift', 'hue wanders with 1/f pink noise, like nature')):
            self.cmode_box.addItem(m.upper(), m)
            self.cmode_box.setItemData(self.cmode_box.count() - 1, tip, Qt.ToolTipRole)
        self.cmode_box.currentIndexChanged.connect(lambda i: self.set_cmode(self.cmode_box.itemData(i)))
        row.addWidget(self.cmode_box, 1)
        v.addLayout(row)
        row = QHBoxLayout()
        row.setSpacing(3)
        self.swatches = []
        for i in range(len(self.palette)):
            b = self.btn('', lambda _=False, i=i: self.edit_swatch(i), 'palette colour %d (click to change)' % (i + 1))
            b.setFixedHeight(20)
            self.swatches.append(b)
            row.addWidget(b)
        v.addLayout(row)
        self.per_pixel = QCheckBox('EVERY PIXEL ITS OWN COLOUR')
        self.per_pixel.setFocusPolicy(Qt.NoFocus)
        v.addWidget(self.per_pixel)
        self.show_swatches()
        v.addSpacing(6)
        v.addWidget(sect('BRUSH SETTINGS'))
        self.brush_params = Params(self.brush_changed)
        v.addWidget(self.scroll(self.brush_params), 1)
        return f

    def scroll(self, w):
        s = QScrollArea()
        s.setWidgetResizable(True)
        s.setWidget(w)
        w.setStyleSheet('background: transparent;')
        return s

    def build_right(self):
        f, outer = panel()
        f.setFixedWidth(290)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)
        ftab = QWidget()
        v = QVBoxLayout(ftab)
        v.setContentsMargins(0, 4, 0, 0)
        v.setSpacing(4)
        self.tabs.addTab(ftab, 'FILTERS')
        self.filter_list = QListWidget()
        for m in self.filters:
            it = QListWidgetItem(m.NAME.upper())
            it.setToolTip((m.__doc__ or '').strip())
            self.filter_list.addItem(it)
        self.filter_list.setFixedHeight(min(230, 24 * max(1, len(self.filters)) + 8))
        self.filter_list.currentRowChanged.connect(lambda i: 0 <= i < len(self.filters) and self.pick_filter(self.filters[i]))
        v.addWidget(self.filter_list)
        self.filter_params = Params(self.filter_changed)
        v.addWidget(self.scroll(self.filter_params), 1)
        row = QHBoxLayout()
        self.live_box = QCheckBox('LIVE')
        self.live_box.setChecked(True)
        self.live_box.setToolTip('preview while you move the sliders (Ctrl+Z drops it)')
        row.addWidget(self.live_box)
        row.addWidget(self.btn('RESEED', self.reseed, 'new random pattern'))
        row.addWidget(self.btn('+STACK', self.stack_add, 'add this filter with these settings to the glitch stack'))
        row.addWidget(self.btn('APPLY', self.apply_filter, 'Ctrl+Enter'), 1)
        v.addLayout(row)

        stab = QWidget()
        sv = QVBoxLayout(stab)
        sv.setContentsMargins(0, 4, 0, 0)
        sv.setSpacing(4)
        self.tabs.addTab(stab, 'GLITCH STACK')
        sv.addWidget(QLabel('runs top to bottom = one undo.\n+STACK (FILTERS tab) adds steps.'))
        self.stack_list = QListWidget()
        sv.addWidget(self.stack_list, 1)
        row = QHBoxLayout()
        for text, fn, tip in (('\u25b2', lambda: self.stack_move(-1), 'move up'), ('\u25bc', lambda: self.stack_move(1), 'move down'),
                              ('DEL', self.stack_del, 'remove step'), ('CLEAR', self.stack_clear, 'empty the stack'),
                              ('EDIT', self.stack_edit, 'load this step into the FILTERS tab')):
            row.addWidget(self.btn(text, fn, tip))
        sv.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(self.btn('SAVE STACK', self.save_stack, 'save as a preset'))
        row.addWidget(self.btn('RUN STACK', self.run_stack, 'apply every step to the active layer'), 1)
        sv.addLayout(row)

        v = outer
        v.addWidget(sect('MASK  (effects stay inside)'))
        row = QHBoxLayout()
        self.mask_btn = self.btn('PAINT MASK', self.toggle_mask_mode, 'M: brushes paint the mask (erase removes)', check=True)
        self.mask_btn.setObjectName('mask')
        row.addWidget(self.mask_btn, 1)
        row.addWidget(self.btn('BY COLOUR', self.mask_pick_arm, 'then click a colour on the canvas: adds all similar colours'))
        v.addLayout(row)
        row = QHBoxLayout()
        for text, fn, tip in (('ALL', self.mask_all, 'select everything'), ('INVERT', self.mask_invert, 'swap inside / outside'),
                              ('CLEAR', self.mask_clear, 'no mask: everything is affected')):
            row.addWidget(self.btn(text, fn, tip))
        v.addLayout(row)
        row = QHBoxLayout()
        self.show_mask = QCheckBox('SHOW')
        self.show_mask.setChecked(True)
        self.show_mask.toggled.connect(lambda _: self.canvas.update())
        self.mask_brushes = QCheckBox('LIMITS BRUSHES')
        self.mask_brushes.setChecked(True)
        self.mask_tol = QSlider(Qt.Horizontal)
        self.mask_tol.setRange(1, 60)
        self.mask_tol.setValue(12)
        self.mask_tol.setToolTip('BY COLOUR tolerance')
        for wdg in (self.show_mask, self.mask_brushes):
            wdg.setFocusPolicy(Qt.NoFocus)
            row.addWidget(wdg)
        row.addWidget(QLabel('TOL'))
        row.addWidget(self.mask_tol, 1)
        v.addLayout(row)
        v.addSpacing(4)
        v.addWidget(sect('LAYERS'))
        self.layer_list = QListWidget()
        self.layer_list.setFixedHeight(120)
        self.layer_list.currentRowChanged.connect(self.pick_layer)
        self.layer_list.itemChanged.connect(self.layer_edited)
        v.addWidget(self.layer_list)
        row = QHBoxLayout()
        for text, fn, tip in (('+', self.layer_add, 'new layer'), ('DUP', self.layer_dup, 'duplicate'),
                              ('DEL', self.layer_del, 'delete'), ('▲', lambda: self.layer_move(1), 'up'),
                              ('▼', lambda: self.layer_move(-1), 'down')):
            row.addWidget(self.btn(text, fn, tip))
        v.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel('OPACITY'))
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.valueChanged.connect(self.opacity_changed)
        row.addWidget(self.opacity, 1)
        v.addLayout(row)
        return f

    # ---------------------------------------------------------------- status
    def say(self, text):
        self.msg = text
        self.paint_status()

    def pos_status(self, xy):
        if self.doc:
            self.posmsg = 'x%d y%d  %d%%' % (xy[0], xy[1], self.canvas.s * 100)
            self.paint_status()

    def blink_tick(self):
        self.blink = not self.blink
        self.paint_status()

    def paint_status(self):
        info = ''
        if self.doc:
            info = '%dx%d | %s | %s | %s' % (self.doc.w, self.doc.h, self.doc.layer.name,
                                             self.brush.NAME if self.brush else '-', 'ERASE' if self.erase else 'PAINT')
        self.status.setText('> %s%s     %s   %s' % (self.msg, '_' if self.blink else ' ', info, self.posmsg))

    # ---------------------------------------------------------------- effects
    def pick_brush(self, m):
        if not m:
            return
        self.brush = m
        self.brush_btns[m.ID].setChecked(True)
        self.brush_params.build(m, self.params[m.ID])
        self.paint_status()

    def brush_changed(self):
        self.canvas.update()                                   # outline follows the size sliders

    def pick_filter(self, m):
        if not m:
            return
        self.commit_preview()
        self.filter = m
        i = self.filters.index(m)
        if self.filter_list.currentRow() != i:
            self.filter_list.blockSignals(True)
            self.filter_list.setCurrentRow(i)
            self.filter_list.blockSignals(False)
        self.filter_params.build(m, self.params[m.ID])

    def filter_changed(self):
        if getattr(self.filter, 'SLOW', False):
            self.say('%s is slow: press APPLY to run it' % self.filter.NAME)
        elif self.live_box.isChecked() and self.doc:
            self.preview_timer.start(180)

    def run_filter(self, src):
        return self.filter.apply(src, dict(self.params[self.filter.ID]), np.random.default_rng(self.seed))

    def run_preview(self):
        if not self.doc or not self.filter:
            return
        L = self.doc.layer
        if self.live is None or self.live[0] is not L:
            self.commit_preview()
            self.doc.push_pixels(L)
            self.live = (L, L.arr.copy())
        self.say('rendering %s...' % self.filter.NAME)
        QApplication.processEvents()
        t = time.time()
        try:
            out = self.run_filter(self.live[1])
        except Exception:
            self.say('filter error: ' + traceback.format_exc(limit=1).splitlines()[-1])
            return
        L.arr = self.doc.masked(self.live[1], np.ascontiguousarray(out, np.uint8))
        self.fgen += 1
        self.canvas.refresh()
        self.touched()
        self.say('%s preview (%.1fs)%s  APPLY keeps it, Ctrl+Z drops it' %
                 (self.filter.NAME, time.time() - t, ' inside mask' if self.doc.has_mask else ''))

    def commit_preview(self):
        self.live = None

    def apply_filter(self):
        if not self.doc or not self.filter:
            return
        if self.live is not None:
            self.live = None
            self.say('%s applied' % self.filter.NAME)
            return
        L = self.doc.layer
        self.doc.push_pixels(L)
        try:
            L.arr = self.doc.masked(L.arr, np.ascontiguousarray(self.run_filter(L.arr), np.uint8))
            self.fgen += 1
        except Exception:
            self.doc.do_undo(); self.doc.redo.clear()
            self.say('filter error: ' + traceback.format_exc(limit=1).splitlines()[-1])
            return
        self.canvas.refresh()
        self.touched()
        self.say('%s applied' % self.filter.NAME)

    def filter_source(self, L):
        """The active layer run through the current filter, cached for the Filter Brush."""
        if not self.filter:
            return None
        key = (self.filter.ID, json.dumps(self.params[self.filter.ID], sort_keys=True), self.seed, id(L), self.fgen)
        if self.fcache and self.fcache[0] == key:
            return self.fcache[1]
        self.say('rendering %s for the filter brush...' % self.filter.NAME)
        QApplication.processEvents()
        try:
            src = np.ascontiguousarray(self.run_filter(L.arr), np.uint8)
        except Exception:
            self.say('filter error: ' + traceback.format_exc(limit=1).splitlines()[-1])
            return None
        self.fcache = (key, src)
        self.say('filter brush paints: %s (change it on the FILTERS tab)' % self.filter.NAME)
        return src

    # ---------------------------------------------------------------- mask
    def toggle_mask_mode(self):
        self.mask_mode = not self.mask_mode
        self.mask_pick = False
        self.mask_btn.setChecked(self.mask_mode)
        self.show_mode()
        self.say('MASK MODE: brushes paint the mask, erase removes it. M to go back' if self.mask_mode
                 else 'painting the layer again')

    def show_mode(self):
        self.title.mode = ('MASK ' if self.mask_mode else '') + ('ERASE' if self.erase else 'PAINT')
        self.paint_status()

    def mask_edit(self, fn, what):
        if not self.doc:
            return
        self.commit_preview()
        self.doc.push_mask()
        fn(self.doc.mask[..., 3])
        self.doc.mask_changed()
        self.canvas.update()
        self.touched()
        self.say(what)

    def mask_all(self):
        self.mask_edit(lambda m: m.fill(255), 'mask: everything')

    def mask_clear(self):
        self.mask_edit(lambda m: m.fill(0), 'mask cleared: filters and brushes hit everything')

    def mask_invert(self):
        self.mask_edit(lambda m: np.subtract(255, m, out=m), 'mask inverted')

    def mask_pick_arm(self):
        self.mask_pick = True
        self.say('BY COLOUR: click a colour on the canvas (adds every similar colour to the mask)')

    def mask_by_colour(self, xy):
        self.mask_pick = False
        d = self.doc
        x, y = int(np.clip(xy[0], 0, d.w - 1)), int(np.clip(xy[1], 0, d.h - 1))
        c = d.comp[y, x, :3].astype(np.int16)
        dist = np.abs(d.comp[..., :3].astype(np.int16) - c).sum(-1)
        hit = (dist <= self.mask_tol.value() / 100 * 765) & (d.comp[..., 3] > 0)
        self.mask_edit(lambda m: np.maximum(m, hit.astype(np.uint8) * 255, out=m),
                       'mask: added %d pixels like rgb%s' % (int(hit.sum()), tuple(int(v) for v in c)))

    # ---------------------------------------------------------------- glitch stack
    def stack_add(self):
        if not self.filter:
            return
        self.stack.append(dict(effect=self.filter.ID, params=dict(self.params[self.filter.ID])))
        self.sync_stack()
        self.say('stack: added %s (%d steps)' % (self.filter.NAME, len(self.stack)))

    def sync_stack(self):
        names = {m.ID: m.NAME for m in self.fx}
        self.stack_list.clear()
        for i, st in enumerate(self.stack):
            self.stack_list.addItem('%d. %s' % (i + 1, names.get(st['effect'], st['effect'] + ' (missing)')))

    def stack_move(self, d):
        i = self.stack_list.currentRow()
        j = i + d
        if 0 <= i < len(self.stack) and 0 <= j < len(self.stack):
            self.stack[i], self.stack[j] = self.stack[j], self.stack[i]
            self.sync_stack()
            self.stack_list.setCurrentRow(j)

    def stack_del(self):
        i = self.stack_list.currentRow()
        if 0 <= i < len(self.stack):
            del self.stack[i]
            self.sync_stack()

    def stack_clear(self):
        self.stack = []
        self.sync_stack()

    def stack_edit(self):
        i = self.stack_list.currentRow()
        if not 0 <= i < len(self.stack):
            return
        st = self.stack[i]
        m = next((m for m in self.filters if m.ID == st['effect']), None)
        if m:
            self.params[m.ID].update(st['params'])
            self.pick_filter(m)
            self.filter_params.set_values(self.params[m.ID])
            self.tabs.setCurrentIndex(0)
            self.say('editing step %d: change it, then +STACK adds the new version (DEL the old one)' % (i + 1))

    def run_stack(self):
        if not self.doc or not self.stack:
            self.say('the stack is empty: pick a filter, set it up, press +STACK')
            return
        self.commit_preview()
        fx = {m.ID: m for m in self.filters}
        L = self.doc.layer
        base = L.arr
        self.doc.push_pixels(L)
        out = base
        t = time.time()
        for i, st in enumerate(self.stack):
            m = fx.get(st['effect'])
            if not m:
                continue
            vals = effects.defaults(m)
            vals.update({k: v for k, v in st['params'].items() if k in vals})
            self.say('stack %d/%d: %s...' % (i + 1, len(self.stack), m.NAME))
            QApplication.processEvents()
            try:
                out = np.ascontiguousarray(m.apply(out, vals, np.random.default_rng(self.seed + i)), np.uint8)
            except Exception:
                self.say('stack step %d (%s) failed: %s' % (i + 1, m.NAME, traceback.format_exc(limit=1).splitlines()[-1]))
                L.arr = base
                self.doc.undo.pop()
                return
        L.arr = self.doc.masked(base, out)
        self.fgen += 1
        self.canvas.refresh()
        self.touched()
        self.say('stack done: %d steps in %.1fs%s' % (len(self.stack), time.time() - t,
                                                      ' inside mask' if self.doc.has_mask else ''))

    def save_stack(self):
        if not self.stack:
            return
        name, ok = QInputDialog.getText(self, 'save stack', 'stack name')
        if ok and name.strip():
            pr = dict(name=name.strip(), effect='__stack__', stack=[dict(s) for s in self.stack])
            self.presets = [p for p in self.presets if not (p['name'] == pr['name'] and p['effect'] == '__stack__')] + [pr]
            self.write_presets()
            self.say('stack saved: ' + pr['name'])

    def reseed(self):
        self.seed += 1
        if self.live is not None:
            self.run_preview()
        else:
            self.say('seed %d' % self.seed)

    def reload_fx(self):
        self.commit_preview()
        fx, errs = effects.load(os.path.join(HERE, 'effects'))
        known = {m.ID for m in self.fx}
        new = [m.NAME for m in fx if m.ID not in known]
        self.say('found %d effects%s%s' % (len(fx), ('; new: ' + ', '.join(new)) if new else '',
                                           ('; errors: ' + ' | '.join(errs)) if errs else '') +
                 ('  (restart Glitch Lab to see new buttons)' if new else ''))
        for m in fx:                                         # code changes to existing effects apply right away
            for i, old in enumerate(self.fx):
                if old.ID == m.ID:
                    self.fx[i] = m
            for lst in (self.brushes, self.filters):
                for i, old in enumerate(lst):
                    if old.ID == m.ID:
                        lst[i] = m
            for q in m.PARAMS:
                self.params.setdefault(m.ID, {}).setdefault(q['key'], q['default'])
        self.brush = next((m for m in self.brushes if m.ID == self.brush.ID), self.brush)
        self.filter = next((m for m in self.filters if m.ID == self.filter.ID), self.filter)
        self.brush_params.build(self.brush, self.params[self.brush.ID])
        self.filter_params.build(self.filter, self.params[self.filter.ID])

    def toggle_erase(self):
        self.erase = not self.erase
        self.erase_btn.setChecked(self.erase)
        self.erase_btn.setText('ERASE' if self.erase else 'PAINT')
        self.show_mode()

    def pick_color(self):
        c = QColorDialog.getColor(QColor(*self.color), self, 'paint colour')
        if c.isValid():
            self.color = (c.red(), c.green(), c.blue())
            self.show_color()

    def show_color(self):
        self.color_btn.setStyleSheet('background: rgb(%d,%d,%d);' % self.color)

    def show_swatches(self):
        for b, c in zip(self.swatches, self.palette):
            b.setStyleSheet('background: rgb(%d,%d,%d); padding: 0;' % tuple(c))

    def edit_swatch(self, i):
        c = QColorDialog.getColor(QColor(*self.palette[i]), self, 'palette colour %d' % (i + 1))
        if c.isValid():
            self.palette[i] = (c.red(), c.green(), c.blue())
            self.show_swatches()
            if self.cmode != 'palette':
                self.cmode_box.setCurrentIndex(self.cmode_box.findData('palette'))

    def set_cmode(self, m):
        self.cmode = m
        if self.cmode_box.currentData() != m:
            self.cmode_box.setCurrentIndex(self.cmode_box.findData(m))
        self.say('colour mode: %s' % m)

    def size_step(self, f):
        if not self.brush:
            return
        for q in self.brush.PARAMS:
            if q['key'] in ('size', 'area', 'width') and 'choices' not in q:
                v = self.params[self.brush.ID][q['key']]
                nv = v * f
                if q['int']:
                    nv = int(round(nv))
                    if nv == v:
                        nv = v + (1 if f > 1 else -1)
                nv = min(q['hi'], max(q['lo'], nv))
                self.params[self.brush.ID][q['key']] = nv
                self.brush_params.set_values(self.params[self.brush.ID])
                self.say('%s %s' % (q['label'], nv))
                return

    # ---------------------------------------------------------------- presets
    def preset_path(self):
        return os.path.join(HERE, 'presets.json')

    def load_presets(self):
        try:
            with open(self.preset_path(), encoding='utf-8') as fh:
                self.presets = json.load(fh)
        except Exception:
            self.presets = []
        ids = {m.ID: m for m in self.fx}
        self.preset_box.clear()
        self.preset_box.addItem('-- pick a preset --')
        for kind in ('brush', 'filter'):
            for pr in self.presets:
                m = ids.get(pr.get('effect'))
                if m and m.KIND == kind:
                    self.preset_box.addItem('%s  %s  (%s)' % ('✎' if kind == 'brush' else '✦', pr['name'], m.NAME),
                                            pr)
        for pr in self.presets:
            if pr.get('effect') == '__stack__' and all(s['effect'] in ids for s in pr.get('stack', [])):
                self.preset_box.addItem('☰  %s  (stack: %s)' % (pr['name'], ' > '.join(ids[s['effect']].NAME for s in pr['stack'])), pr)

    def pick_preset(self, i):
        pr = self.preset_box.itemData(i)
        if not pr:
            return
        if pr.get('effect') == '__stack__':
            self.stack = [dict(effect=s['effect'], params=dict(s.get('params', {}))) for s in pr['stack']]
            self.sync_stack()
            self.tabs.setCurrentIndex(1)
            self.say('stack loaded: %s (%d steps), press RUN STACK' % (pr['name'], len(self.stack)))
            return
        m = next((m for m in self.fx if m.ID == pr['effect']), None)
        if not m:
            return
        vals = effects.defaults(m)
        vals.update({k: v for k, v in pr.get('params', {}).items() if k in vals})
        self.params[m.ID].clear()
        self.params[m.ID].update(vals)
        if m.KIND == 'brush':
            self.pick_brush(m)
            if 'erase' in pr and bool(pr['erase']) != self.erase:
                self.toggle_erase()
            if pr.get('color'):
                self.color = tuple(pr['color'])
                self.show_color()
            self.set_cmode(pr.get('cmode', 'pick'))
            self.per_pixel.setChecked(bool(pr.get('per_pixel', False)))
        else:
            self.pick_filter(m)
            self.filter_params.set_values(vals)
        self.say('preset: %s' % pr['name'])

    def save_preset(self):
        kinds = []
        if self.brush:
            kinds.append('brush: ' + self.brush.NAME)
        if self.filter:
            kinds.append('filter: ' + self.filter.NAME)
        which, ok = QInputDialog.getItem(self, 'save preset', 'save the settings of', kinds, 0, False)
        if not ok:
            return
        name, ok = QInputDialog.getText(self, 'save preset', 'preset name')
        if not ok or not name.strip():
            return
        m = self.brush if which.startswith('brush') else self.filter
        pr = dict(name=name.strip(), effect=m.ID, params=dict(self.params[m.ID]))
        if m.KIND == 'brush':
            pr['erase'] = self.erase
            pr['color'] = list(self.color)
            pr['cmode'] = self.cmode
            pr['per_pixel'] = self.per_pixel.isChecked()
        self.presets = [p for p in self.presets if not (p['name'] == pr['name'] and p['effect'] == m.ID)] + [pr]
        self.write_presets()
        self.say('preset saved: ' + pr['name'])

    def write_presets(self):
        tmp = self.preset_path() + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write('[\n' + ',\n'.join(' ' + json.dumps(p) for p in self.presets) + '\n]\n')
        os.replace(tmp, self.preset_path())
        self.load_presets()

    # ---------------------------------------------------------------- layers
    def sync_layers(self):
        if not self.doc:
            return
        ll = self.layer_list
        ll.blockSignals(True)
        ll.clear()
        for L in reversed(self.doc.layers):
            it = QListWidgetItem(L.name)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
            it.setCheckState(Qt.Checked if L.visible else Qt.Unchecked)
            ll.addItem(it)
        ll.setCurrentRow(len(self.doc.layers) - 1 - self.doc.active)
        ll.blockSignals(False)
        self.opacity.blockSignals(True)
        self.opacity.setValue(int(self.doc.layer.opacity * 100))
        self.opacity.blockSignals(False)
        self.paint_status()

    def row_layer(self, row):
        return len(self.doc.layers) - 1 - row

    def pick_layer(self, row):
        if not self.doc or row < 0:
            return
        self.commit_preview()
        self.doc.active = self.row_layer(row)
        self.opacity.blockSignals(True)
        self.opacity.setValue(int(self.doc.layer.opacity * 100))
        self.opacity.blockSignals(False)
        self.paint_status()

    def layer_edited(self, it):
        row = self.layer_list.row(it)
        L = self.doc.layers[self.row_layer(row)]
        vis = it.checkState() == Qt.Checked
        L.name = it.text()
        if vis != L.visible:
            L.visible = vis
            self.canvas.refresh()
        self.touched()

    def layer_add(self):
        if not self.doc:
            return
        self.commit_preview()
        self.doc.push_stack()
        self.doc.layers.insert(self.doc.active + 1, self.doc.blank('Glitch %d' % len(self.doc.layers)))
        self.doc.active += 1
        self.sync_layers(); self.touched()

    def layer_dup(self):
        if not self.doc:
            return
        self.commit_preview()
        self.doc.push_stack()
        L = self.doc.layer
        from .doc import Layer
        self.doc.layers.insert(self.doc.active + 1, Layer(L.name + ' copy', L.arr.copy(), L.visible, L.opacity))
        self.doc.active += 1
        self.sync_layers(); self.canvas.refresh(); self.touched()

    def layer_del(self):
        if not self.doc or len(self.doc.layers) < 2:
            return
        self.commit_preview()
        self.doc.push_stack()
        del self.doc.layers[self.doc.active]
        self.doc.active = max(0, self.doc.active - 1)
        self.sync_layers(); self.canvas.refresh(); self.touched()

    def layer_move(self, d):
        if not self.doc:
            return
        i, j = self.doc.active, self.doc.active + d
        if not 0 <= j < len(self.doc.layers):
            return
        self.commit_preview()
        self.doc.push_stack()
        ls = self.doc.layers
        ls[i], ls[j] = ls[j], ls[i]
        self.doc.active = j
        self.sync_layers(); self.canvas.refresh(); self.touched()

    def opacity_changed(self, v):
        if self.doc:
            self.doc.layer.opacity = v / 100
            self.layer_timer.start(60)
            self.touched()

    # ---------------------------------------------------------------- undo
    def undo(self):
        if self.canvas.stroke or not self.doc:
            return
        self.live = None
        if self.doc.do_undo():
            self.after_history('undo')

    def redo(self):
        if self.canvas.stroke or not self.doc:
            return
        self.live = None
        if self.doc.do_redo():
            self.after_history('redo')

    def after_history(self, what):
        self.fgen += 1
        self.sync_layers()
        self.canvas.refresh()
        self.touched()
        self.say(what)

    def touched(self):
        self.dirty = True
        name = os.path.basename(self.doc.path or self.doc.source or 'untitled') if self.doc else ''
        self.setWindowTitle('GLITCH LAB - %s *' % name)

    # ---------------------------------------------------------------- files
    def set_doc(self, doc):
        self.doc = doc
        self.live = None
        self.fgen += 1
        self.mask_mode = False
        self.canvas.set_doc(doc)
        self.sync_layers()
        self.dirty = False
        self.setWindowTitle('GLITCH LAB - %s' % os.path.basename(doc.source or 'untitled'))

    def ok_to_drop(self):
        if not self.dirty or not self.doc:
            return True
        r = QMessageBox.question(self, 'GLITCH LAB', 'Save this picture first (layered .ora)?',
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return self.save()
        return r == QMessageBox.Discard

    def new_dialog(self):
        if not self.ok_to_drop():
            return
        t, ok = QInputDialog.getText(self, 'new picture', 'size  W x H', text='2048 x 2048')
        if not ok:
            return
        try:
            w, h = [int(s) for s in t.lower().replace(' ', '').split('x')]
            assert 8 <= w <= 12000 and 8 <= h <= 12000
        except Exception:
            self.say('size must look like 2048 x 2048'); return
        self.set_doc(Document.new(w, h))
        self.say('new %dx%d' % (w, h))

    def open_dialog(self):
        if not self.ok_to_drop():
            return
        p, _ = QFileDialog.getOpenFileName(self, 'open', self.last_dir(), 'Pictures (*.png *.jpg *.jpeg *.ora *.webp *.bmp)')
        if p:
            self.open_path(p, ask=False)

    def open_path(self, p, ask=True):
        if ask and not self.ok_to_drop():
            return
        try:
            self.set_doc(Document.open(p))
        except Exception:
            self.say('could not open: ' + traceback.format_exc(limit=1).splitlines()[-1]); return
        self.say('opened %s  (%d layers) - the original file is never overwritten' % (os.path.basename(p), len(self.doc.layers)))

    def last_dir(self):
        if self.doc and (self.doc.path or self.doc.source):
            return os.path.dirname(self.doc.path or self.doc.source)
        return os.path.join(os.path.expanduser('~'), 'Desktop')

    def suggest(self, ext):
        base = self.doc.path or self.doc.source
        if base:
            stem = os.path.splitext(base)[0]
            if self.doc.path and ext == '.ora':
                return self.doc.path
            return stem + ('' if stem.endswith('_glitch') else '_glitch') + ext
        return os.path.join(self.last_dir(), 'glitch' + ext)

    def save(self):
        if not self.doc:
            return False
        if self.doc.path:
            return self.write_ora(self.doc.path)
        return self.save_as()

    def save_as(self):
        if not self.doc:
            return False
        p, _ = QFileDialog.getSaveFileName(self, 'save layered', self.suggest('.ora'), 'OpenRaster (*.ora)')
        if not p:
            return False
        if not p.lower().endswith('.ora'):
            p += '.ora'
        return self.write_ora(p)

    def write_ora(self, p):
        self.commit_preview()
        try:
            self.doc.save_ora(p)
        except Exception as e:
            self.say('NOT saved: %s' % e); return False
        self.dirty = False
        self.setWindowTitle('GLITCH LAB - %s' % os.path.basename(p))
        self.say('saved %s (layers kept, opens in Krita)' % p)
        return True

    def export(self):
        if not self.doc:
            return
        p, _ = QFileDialog.getSaveFileName(self, 'export flat PNG', self.suggest('.png'), 'PNG (*.png)')
        if not p:
            return
        try:
            self.doc.export_png(p)
            self.say('exported %s' % p)
        except Exception as e:
            self.say('NOT exported: %s' % e)

    def autosave(self):
        if not self.doc or not self.dirty or self.canvas.stroke:
            return
        d = os.path.join(HERE, 'autosave')
        os.makedirs(d, exist_ok=True)
        keep_path, keep_source = self.doc.path, self.doc.source
        try:
            self.doc.source = None
            self.doc.save_ora(os.path.join(d, 'autosave.ora'))
            self.say('autosaved to glitch_lab\\autosave\\autosave.ora')
        except Exception as e:
            self.say('autosave failed: %s' % e)
        finally:
            self.doc.path, self.doc.source = keep_path, keep_source

    def zoom_step(self, f):
        c = self.canvas
        c.zoom_at(c.s * f, c.hover)
        self.say('zoom %d%%' % (c.s * 100))

    def zoom100(self):
        if self.doc:
            self.canvas.s = 1.0
            self.canvas.center()

    def closeEvent(self, ev):
        if self.ok_to_drop():
            ev.accept()
        else:
            ev.ignore()


def main(argv):
    app = QApplication(argv)
    app.setStyleSheet(QSS)
    w = Win(argv[1] if len(argv) > 1 else None)
    w.show()
    return app.exec()
