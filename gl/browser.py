"""Preset browser: search, category filter, favourites, and a thumbnail of every preset rendered once on the
test picture (cached in glitch_lab/thumbs, rendered in the background)."""
import hashlib, json, math, os, queue, threading

import numpy as np
from PIL import Image
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QIcon, QImage, QPixmap, QColor
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QVBoxLayout, QListView)

from . import effects

TW, TH = 192, 116


def preset_key(pr):
    return pr.get('effect', '') + '|' + pr.get('name', '')


def render_thumb(pr, fx, src):
    """Small preview of one preset on the test picture."""
    if pr.get('effect') == '__stack__':
        out = src
        for k, st in enumerate(pr['stack']):
            m = fx.get(st['effect'])
            if m:
                v = effects.defaults(m); v.update({a: b for a, b in st.get('params', {}).items() if a in v})
                out = np.ascontiguousarray(m.apply(out, v, np.random.default_rng(k + 1)), np.uint8)
    else:
        m = fx[pr['effect']]
        v = effects.defaults(m); v.update({a: b for a, b in pr.get('params', {}).items() if a in v})
        if m.KIND == 'filter':
            out = m.apply(src.copy(), v, np.random.default_rng(1))
        else:
            out = src.copy()
            ctx = effects.Ctx(out, tuple(pr.get('color', (16, 8, 24))), pr.get('erase', False), v, np.random.default_rng(1),
                              pr.get('cmode', 'pick'), [(255, 79, 216), (79, 243, 255), (125, 255, 176), (123, 47, 190),
                                                        (255, 255, 255)], pr.get('per_pixel', False), src)
            if getattr(m, 'NEEDS_FILTER', False):
                ctx.source = 255 - src                     # stand-in filter so the stroke shows
                ctx.source[..., 3] = 255
            st = effects.Stroke(m, ctx)
            h, w = src.shape[:2]
            for i in range(140):
                st.to(w * 0.06 + i * w * 0.0063, h * 0.5 + h * 0.22 * math.sin(i / 20), 0.4 + 0.6 * min(1, i / 50))
            st.end()
    im = Image.new('RGBA', (out.shape[1], out.shape[0]), (60, 60, 70, 255))
    im.alpha_composite(Image.fromarray(np.ascontiguousarray(out, np.uint8), 'RGBA'))
    return im.convert('RGB').resize((TW, TH), Image.LANCZOS)


class PresetBrowser(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle('GLITCH LAB - presets')
        self.resize(900, 680)
        self.dir = os.path.join(win.here, 'thumbs')
        os.makedirs(self.dir, exist_ok=True)
        self.fav_path = os.path.join(win.here, 'favourites.json')
        try:
            self.favs = set(json.load(open(self.fav_path, encoding='utf-8')))
        except Exception:
            self.favs = set()
        v = QVBoxLayout(self)
        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('search: vhs, melt, ps1, print...')
        self.search.textChanged.connect(self.populate)
        self.cat = QComboBox()
        self.cat.currentIndexChanged.connect(self.populate)
        row.addWidget(self.search, 1)
        row.addWidget(self.cat)
        v.addLayout(row)
        self.list = QListWidget()
        self.list.setViewMode(QListView.IconMode)
        self.list.setIconSize(QSize(TW, TH))
        self.list.setGridSize(QSize(TW + 16, TH + 40))
        self.list.setResizeMode(QListView.Adjust)
        self.list.setMovement(QListView.Static)
        self.list.setWordWrap(True)
        self.list.itemClicked.connect(self.use)
        v.addWidget(self.list, 1)
        row = QHBoxLayout()
        self.hint = QLabel('click = use it  |  ★ = favourite  |  thumbnails render once, then they are instant')
        row.addWidget(self.hint, 1)
        for text, fn in (('★ FAVOURITE', self.toggle_fav), ('CLOSE', self.close)):
            b = QPushButton(text); b.clicked.connect(fn); b.setFocusPolicy(Qt.NoFocus); row.addWidget(b)
        v.addLayout(row)
        self.blank = QPixmap(TW, TH); self.blank.fill(QColor('#24183a'))
        self.ready = queue.Queue()
        self.timer = QTimer(self); self.timer.timeout.connect(self.collect); self.timer.start(120)
        self.worker = None
        self.refresh_categories()
        self.populate()

    # ---- data
    def fx(self):
        return {m.ID: m for m in self.win.fx}

    def category(self, pr):
        if pr.get('effect') == '__stack__':
            return 'Stacks'
        m = self.fx().get(pr.get('effect'))
        return getattr(m, 'CATEGORY', 'Other') if m else 'Other'

    def usable(self, pr):
        fx = self.fx()
        if pr.get('effect') == '__stack__':
            return all(s['effect'] in fx for s in pr.get('stack', []))
        return pr.get('effect') in fx

    def thumb_path(self, pr):
        fx = self.fx()
        ids = [s['effect'] for s in pr['stack']] if pr.get('effect') == '__stack__' else [pr['effect']]
        stamp = ''.join('%s%d' % (i, int(os.path.getmtime(fx[i].__file__))) for i in ids if i in fx)
        h = hashlib.sha1((json.dumps(pr, sort_keys=True) + stamp).encode()).hexdigest()[:16]
        return os.path.join(self.dir, h + '.png')

    def refresh_categories(self):
        cats = sorted({self.category(p) for p in self.win.presets if self.usable(p)} - {'Stacks'})
        self.cat.blockSignals(True)
        cur = self.cat.currentText()
        self.cat.clear()
        self.cat.addItems(['All', '★ Favourites', 'Mine', 'Brushes', 'Filters', 'Stacks'] + cats)
        if cur:
            self.cat.setCurrentText(cur)
        self.cat.blockSignals(False)

    def match(self, pr):
        c = self.cat.currentText()
        fx = self.fx()
        kind = 'stack' if pr.get('effect') == '__stack__' else fx[pr['effect']].KIND
        if c == '★ Favourites' and preset_key(pr) not in self.favs:
            return False
        if c == 'Mine' and not pr.get('mine'):
            return False
        if c == 'Brushes' and kind != 'brush' or c == 'Filters' and kind != 'filter' or c == 'Stacks' and kind != 'stack':
            return False
        if c not in ('All', '★ Favourites', 'Mine', 'Brushes', 'Filters', 'Stacks') and self.category(pr) != c:
            return False
        s = self.search.text().strip().lower()
        if s:
            name = fx[pr['effect']].NAME if kind != 'stack' else ' '.join(fx[x['effect']].NAME for x in pr['stack'])
            hay = (pr['name'] + ' ' + name + ' ' + self.category(pr) + ' ' + json.dumps(pr.get('params', {}))).lower()
            return all(w in hay for w in s.split())
        return True

    # ---- view
    def populate(self):
        self.list.clear()
        fx = self.fx()
        todo = []
        rows = [p for p in self.win.presets if self.usable(p) and self.match(p)]
        rows.sort(key=lambda p: (preset_key(p) not in self.favs, self.category(p), p['name'].lower()))
        for pr in rows:
            kind = 'stack' if pr.get('effect') == '__stack__' else fx[pr['effect']].KIND
            sym = {'brush': '✎', 'filter': '✦', 'stack': '☰'}[kind]
            star = '★ ' if preset_key(pr) in self.favs else ''
            it = QListWidgetItem('%s%s %s' % (star, sym, pr['name']))
            it.setData(Qt.UserRole, pr)
            it.setToolTip('%s  (%s)' % (pr['name'], self.category(pr)))
            tp = self.thumb_path(pr)
            if os.path.exists(tp):
                it.setIcon(QIcon(tp))
            else:
                it.setIcon(QIcon(self.blank))
                todo.append((pr, tp))
            self.list.addItem(it)
        self.hint.setText('%d presets  |  click = use it  |  ★ = favourite' % len(rows) +
                          ('  |  rendering %d thumbnails...' % len(todo) if todo else ''))
        if todo and (self.worker is None or not self.worker.is_alive()):
            self.worker = threading.Thread(target=self.render_all, args=(todo,), daemon=True)
            self.worker.start()

    def render_all(self, todo):
        fx = self.fx()
        src = np.asarray(Image.open(os.path.join(self.win.here, 'assets', 'test_picture.png')).convert('RGBA')
                         .resize((480, 288), Image.LANCZOS)).copy()
        for pr, tp in todo:
            try:
                render_thumb(pr, fx, src).save(tp)
                self.ready.put((preset_key(pr), tp))
            except Exception:
                pass

    def collect(self):
        got = {}
        while not self.ready.empty():
            k, tp = self.ready.get()
            got[k] = tp
        if not got:
            return
        for i in range(self.list.count()):
            it = self.list.item(i)
            tp = got.get(preset_key(it.data(Qt.UserRole)))
            if tp:
                it.setIcon(QIcon(tp))

    def use(self, it):
        self.win.apply_preset(it.data(Qt.UserRole))

    def toggle_fav(self):
        it = self.list.currentItem()
        if not it:
            return
        k = preset_key(it.data(Qt.UserRole))
        self.favs.symmetric_difference_update({k})
        tmp = self.fav_path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(sorted(self.favs), fh)
        os.replace(tmp, self.fav_path)
        self.populate()

    def showEvent(self, ev):
        self.refresh_categories()
        self.populate()
        super().showEvent(ev)
