"""Widgets reutilizables (sin estado de aplicacion).

ArcGauge    — gauge circular para un valor 0..max.
SensorCard  — tarjeta CPU/GPU (gauge + numero + RPM).
CurveEditor — editor de curva de 7 puntos arrastrables.
_tog        — helper: alterna la clase CSS 'active' de un widget.

Para agregar un widget reutilizable nuevo, ponlo aqui.
"""

import math

from gi.repository import Gtk
import cairo

from .config import DEFAULT_CPU, COLOR_ACCENT


def _tog(w, state):
    """Alterna la clase CSS 'active' segun `state`."""
    if state: w.add_css_class("active")
    else:     w.remove_css_class("active")


# ───────────────────────────────── Arc Gauge ─────────────────────────────────

class ArcGauge(Gtk.DrawingArea):
    SIZE = 100

    def __init__(self, max_val=100, color=COLOR_ACCENT):
        super().__init__()
        self._val   = 0
        self._max   = max_val
        self._color = color
        self.set_size_request(self.SIZE, self.SIZE)
        self.set_draw_func(self._draw, None)

    def update(self, v):
        self._val = int(v)
        self.queue_draw()

    def _draw(self, _area, cr, w, h, _data):
        cx, cy = w / 2, h / 2
        r      = min(w, h) / 2 - 10
        start  = math.radians(150)
        sweep  = math.radians(240)
        frac   = min(self._val / max(self._max, 1), 1.0)

        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        cr.set_line_width(7)
        cr.set_source_rgba(0.05, 0.08, 0.12, 1.0)
        cr.arc(cx, cy, r, start, start + sweep)
        cr.stroke()

        if frac > 0.005:
            rc, gc, bc = self._color
            cr.set_line_width(7)
            cr.set_source_rgba(rc, gc, bc, 1.0)
            cr.arc(cx, cy, r, start, start + frac * sweep)
            cr.stroke()

            ea = start + frac * sweep
            ex = cx + r * math.cos(ea)
            ey = cy + r * math.sin(ea)
            cr.set_source_rgba(rc, gc, bc, 0.9)
            cr.arc(ex, ey, 4, 0, 2 * math.pi)
            cr.fill()

        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL,
                            cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(18)
        txt = str(self._val)
        ext = cr.text_extents(txt)
        cr.set_source_rgba(0.851, 0.769, 0.722, 1.0)
        cr.move_to(cx - ext.width / 2, cy + ext.height / 2)
        cr.show_text(txt)


# ─────────────────────────────── Sensor Card ─────────────────────────────────

class SensorCard(Gtk.Box):
    def __init__(self, title, unit, max_val, color=COLOR_ACCENT):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("card")

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        inner.add_css_class("card-inner")
        self.append(inner)

        t = Gtk.Label(label=title.upper())
        t.add_css_class("lbl-title")
        t.set_halign(Gtk.Align.START)
        inner.append(t)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_valign(Gtk.Align.CENTER)
        inner.append(row)

        self.gauge = ArcGauge(max_val=max_val, color=color)
        row.append(self.gauge)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        right.set_valign(Gtk.Align.CENTER)
        row.append(right)

        num_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        num_row.set_valign(Gtk.Align.BASELINE)
        right.append(num_row)

        self.lbl_val = Gtk.Label(label="0")
        self.lbl_val.add_css_class("lbl-big")
        num_row.append(self.lbl_val)

        u = Gtk.Label(label=unit)
        u.add_css_class("lbl-unit")
        u.set_valign(Gtk.Align.END)
        u.set_margin_bottom(5)
        num_row.append(u)

        self.lbl_sub = Gtk.Label(label="— 0 RPM")
        self.lbl_sub.add_css_class("lbl-sub")
        self.lbl_sub.set_halign(Gtk.Align.START)
        right.append(self.lbl_sub)

    def update(self, temp, rpm):
        self.gauge.update(temp)
        self.lbl_val.set_text(str(temp))
        self.lbl_sub.set_text(f"{rpm:,} RPM")


# ─────────────────────────────── Curve Editor ────────────────────────────────

class CurveEditor(Gtk.DrawingArea):
    """Editor de curva de 7 puntos arrastrables. Eje X = °C (0-100), Y = % (0-100)."""

    PAD_L, PAD_R, PAD_T, PAD_B = 38, 12, 14, 26
    HIT = 16  # radio de captura del punto en px

    def __init__(self, color=COLOR_ACCENT):
        super().__init__()
        self._color = color
        self._points = [list(p) for p in DEFAULT_CPU]
        self._drag_idx = None
        self.set_size_request(440, 280)
        self.set_draw_func(self._draw, None)

        drag = Gtk.GestureDrag()
        drag.connect("drag-begin",  self._on_begin)
        drag.connect("drag-update", self._on_update)
        drag.connect("drag-end",    self._on_end)
        self.add_controller(drag)

    # ── datos ──
    def set_points(self, points):
        self._points = [[int(t), int(s)] for t, s in points]
        self.queue_draw()

    def get_points(self):
        return [p[:] for p in self._points]

    # ── mapeo data <-> pixel ──
    def _plot(self):
        w, h = self.get_width(), self.get_height()
        x0, y0 = self.PAD_L, self.PAD_T
        pw = max(w - self.PAD_L - self.PAD_R, 1)
        ph = max(h - self.PAD_T - self.PAD_B, 1)
        return x0, y0, pw, ph

    def _to_px(self, t, s):
        x0, y0, pw, ph = self._plot()
        return x0 + t / 100.0 * pw, y0 + (1 - s / 100.0) * ph

    def _to_data(self, px, py):
        x0, y0, pw, ph = self._plot()
        t = (px - x0) / pw * 100.0
        s = (1 - (py - y0) / ph) * 100.0
        return t, s

    # ── arrastre ──
    def _on_begin(self, _g, sx, sy):
        self._start = (sx, sy)
        self._drag_idx = None
        best = self.HIT ** 2
        for i, (t, s) in enumerate(self._points):
            px, py = self._to_px(t, s)
            d2 = (px - sx) ** 2 + (py - sy) ** 2
            if d2 <= best:
                best = d2
                self._drag_idx = i

    def _on_update(self, _g, ox, oy):
        if self._drag_idx is None:
            return
        i = self._drag_idx
        sx, sy = self._start
        t, s = self._to_data(sx + ox, sy + oy)
        # temp acotada entre vecinos (mantiene orden ascendente)
        lo = self._points[i - 1][0] if i > 0 else 0
        hi = self._points[i + 1][0] if i < 6 else 100
        t = max(lo, min(hi, t))
        s = max(0, min(100, s))
        self._points[i] = [int(round(t)), int(round(s))]
        self.queue_draw()

    def _on_end(self, _g, _ox, _oy):
        self._drag_idx = None

    # ── dibujo ──
    def _draw(self, _area, cr, w, h, _d):
        x0, y0, pw, ph = self._plot()
        rc, gc, bc = self._color

        # grilla
        cr.set_line_width(1)
        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(8)
        for v in range(0, 101, 20):
            # vertical (temp)
            gx = x0 + v / 100.0 * pw
            cr.set_source_rgba(0.45, 0.35, 0.32, 0.18)
            cr.move_to(gx, y0); cr.line_to(gx, y0 + ph); cr.stroke()
            cr.set_source_rgba(0.45, 0.35, 0.32, 0.9)
            cr.move_to(gx - 6, y0 + ph + 14); cr.show_text(f"{v}")
            # horizontal (vel)
            gy = y0 + (1 - v / 100.0) * ph
            cr.set_source_rgba(0.45, 0.35, 0.32, 0.18)
            cr.move_to(x0, gy); cr.line_to(x0 + pw, gy); cr.stroke()
            cr.set_source_rgba(0.45, 0.35, 0.32, 0.9)
            cr.move_to(4, gy + 3); cr.show_text(f"{v:>3}")

        # area + linea de la curva
        pts_px = [self._to_px(t, s) for t, s in self._points]

        cr.move_to(pts_px[0][0], y0 + ph)
        for px, py in pts_px:
            cr.line_to(px, py)
        cr.line_to(pts_px[-1][0], y0 + ph)
        cr.close_path()
        cr.set_source_rgba(rc, gc, bc, 0.12)
        cr.fill()

        cr.set_line_width(2)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_source_rgba(rc, gc, bc, 0.95)
        cr.move_to(*pts_px[0])
        for px, py in pts_px[1:]:
            cr.line_to(px, py)
        cr.stroke()

        # puntos + etiqueta del que se arrastra
        for i, (px, py) in enumerate(pts_px):
            active = (i == self._drag_idx)
            cr.set_source_rgba(0.05, 0.08, 0.12, 1.0)
            cr.arc(px, py, 6 if active else 5, 0, 2 * math.pi); cr.fill()
            cr.set_source_rgba(rc, gc, bc, 1.0)
            cr.arc(px, py, 4 if active else 3, 0, 2 * math.pi); cr.fill()
            if active:
                t, s = self._points[i]
                cr.set_source_rgba(0.851, 0.769, 0.722, 1.0)
                cr.set_font_size(9)
                cr.move_to(px + 8, py - 6)
                cr.show_text(f"{t}°C  {s}%")
