#!/usr/bin/env python3
"""
msifan-gui — GTK4 interface para msi-fanctl
Fedora + Hyprland  |  Wayland native
Requiere: python3-gobject gtk4 libadwaita python3-cairo
"""

import os, sys

# GDK_BACKEND se setea en el launcher (msifan-gui).
# La GUI corre como usuario normal — D-Bus y Wayland auth funcionan sin root.
os.environ.setdefault("GTK_THEME",  "Adwaita:dark")
os.environ.setdefault("GTK4_THEME", "Adwaita:dark")

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk
import cairo
import subprocess, math, glob, re, threading, time


# ─────────────────────────────── sysfs helpers ───────────────────────────────

SYSFS = "/sys/devices/platform/msi-ec"
HWMON = "/sys/class/hwmon"
CONF  = os.path.expanduser("~/.config/msifan/profiles.conf")


def _r(path, default="0"):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return default


def _hwmon():
    for d in sorted(glob.glob(f"{HWMON}/hwmon*")):
        if "msi_wmi_platform" in _r(f"{d}/name", ""):
            return d
    return None


def cpu_temp():
    try:    return int(_r(f"{SYSFS}/cpu/realtime_temperature"))
    except: return 0

def gpu_temp():
    try:    return int(_r(f"{SYSFS}/gpu/realtime_temperature"))
    except: return 0

def fan_rpm(n):
    h = _hwmon()
    if not h: return 0
    try:    return int(_r(f"{h}/fan{n}_input"))
    except: return 0

def fan_mode():   return _r(f"{SYSFS}/fan_mode",    "auto")
def shift_mode(): return _r(f"{SYSFS}/shift_mode",  "comfort")
def boost_on():   return _r(f"{SYSFS}/cooler_boost", "off") == "on"
def ec_ok():      return os.path.isdir(SYSFS)

PROFILES_HEADER = """\
# ============================================================
# msifan - Perfiles de curvas de ventilador
# ============================================================
# Formato: cpu|gpu = temp1:vel1 temp2:vel2 ... (7 puntos exactos)
# Temperaturas en °C, velocidades en % (0-100)
# Los puntos deben estar ordenados de menor a mayor temperatura.
# Editado por msifan-gui.
# ============================================================
"""

# Curva por defecto usada al crear un perfil nuevo.
DEFAULT_CPU = [[50, 0], [56, 40], [62, 49], [70, 58], [75, 67], [80, 76], [100, 85]]
DEFAULT_GPU = [[55, 0], [60, 48], [65, 56], [70, 64], [75, 72], [80, 79], [98, 86]]


def read_profiles():
    """Lee profiles.conf → dict {nombre: {'cpu': str, 'gpu': str}} preservando orden."""
    profs = {}
    cur = None
    try:
        for line in open(CONF):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            m = re.match(r'^\[(.+)\]$', s)
            if m:
                cur = m.group(1)
                profs[cur] = {}
                continue
            if cur and "=" in s:
                k, v = s.split("=", 1)
                k = k.strip()
                if k in ("cpu", "gpu"):
                    profs[cur][k] = v.strip()
    except FileNotFoundError:
        pass
    return profs


def write_profiles(profs):
    """Reescribe profiles.conf desde dict {nombre: {'cpu','gpu'}}."""
    os.makedirs(os.path.dirname(CONF), exist_ok=True)
    out = [PROFILES_HEADER]
    for name, c in profs.items():
        out.append(f"[{name}]")
        out.append(f"cpu = {c.get('cpu', '')}")
        out.append(f"gpu = {c.get('gpu', '')}")
        out.append("")
    with open(CONF, "w") as f:
        f.write("\n".join(out))


def points_to_curve(points):
    """[[t,s],...] → 'T:S T:S ...' (7 puntos, temp ascendente)."""
    pts = sorted(([int(round(t)), int(round(s))] for t, s in points), key=lambda p: p[0])
    return " ".join(f"{t}:{s}" for t, s in pts)


def curve_to_points(curve, fallback):
    """'T:S T:S ...' → [[t,s],...]. Usa fallback si no son 7 puntos validos."""
    pts = []
    for tok in (curve or "").split():
        if ":" in tok:
            t, s = tok.split(":", 1)
            try:
                pts.append([int(t), int(s)])
            except ValueError:
                pass
    if len(pts) != 7:
        return [p[:] for p in fallback]
    return pts


def list_profiles():
    return list(read_profiles().keys()) or ["default", "silent", "gaming", "max"]


def run_cmd(*args, on_done=None):
    """Ejecuta msifan con sudo en hilo separado — no bloquea la UI.

    on_done(ok: bool, err: str) se invoca en el hilo principal vía GLib.idle_add."""
    def _do():
        ok, err = False, ""
        try:
            r = subprocess.run(
                ["sudo", "msifan"] + list(args),
                capture_output=True, timeout=15, text=True,
            )
            ok = (r.returncode == 0)
            err = (r.stderr or "").strip()
        except Exception as e:
            err = str(e)
        if on_done is not None:
            GLib.idle_add(on_done, ok, err)
    threading.Thread(target=_do, daemon=True).start()


# ──────────────────────────────────── CSS ────────────────────────────────────

CSS = """
* {
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
    -gtk-icon-style: regular;
}

window.msifan {
    background-color: #141E26;
    color: #D9C4B8;
}

window.msifan .root-box {
    background-color: #141E26;
    color: #D9C4B8;
}

window.msifan headerbar,
window.msifan .titlebar {
    background-color: #0D0D0D;
    background-image: none;
    border-bottom: 1px solid rgba(115, 90, 81, 0.3);
    box-shadow: none;
    padding: 6px 12px;
}

window.msifan headerbar > windowhandle,
window.msifan headerbar > windowhandle > box {
    background-color: transparent;
}

window.msifan .card {
    background-color: #192330;
    border-radius: 18px;
    border: 1px solid rgba(115, 90, 81, 0.28);
}

window.msifan .card-inner { padding: 14px; }

window.msifan .lbl-section {
    color: #A6877C;
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 4px;
}

window.msifan .lbl-title {
    color: #A6877C;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 3px;
}

window.msifan .lbl-big {
    color: #D9C4B8;
    font-size: 34px;
    font-weight: 800;
}

window.msifan .lbl-unit {
    color: #735A51;
    font-size: 13px;
    font-weight: 600;
}

window.msifan .lbl-sub {
    color: #A6877C;
    font-size: 11px;
    letter-spacing: 1px;
}

window.msifan .app-title {
    color: #D9C4B8;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 4px;
}

window.msifan .app-sub {
    color: #735A51;
    font-size: 8px;
    letter-spacing: 2px;
}

window.msifan .status-ok  { color: #A6877C; font-size: 9px; font-weight: 700; letter-spacing: 2px; }
window.msifan .status-err { color: #735A51; font-size: 9px; font-weight: 700; letter-spacing: 2px; }

window.msifan button.mode-btn {
    background-color: rgba(115, 90, 81, 0.12);
    background-image: none;
    color: #D9C4B8;
    border-radius: 10px;
    border: 1px solid rgba(115, 90, 81, 0.25);
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 8px 4px;
    min-width: 62px;
    box-shadow: none;
}

window.msifan button.mode-btn:hover {
    background-color: rgba(166, 135, 124, 0.20);
    background-image: none;
    border-color: rgba(166, 135, 124, 0.5);
}

window.msifan button.mode-btn.active {
    background-color: #735A51;
    background-image: none;
    border-color: #A6877C;
    color: #D9C4B8;
}

window.msifan button.profile-btn {
    background-color: rgba(115, 90, 81, 0.10);
    background-image: none;
    color: #D9C4B8;
    border-radius: 12px;
    border: 1px solid rgba(115, 90, 81, 0.20);
    font-size: 11px;
    padding: 9px 12px;
    min-width: 80px;
    box-shadow: none;
}

window.msifan button.profile-btn:hover {
    background-color: rgba(166, 135, 124, 0.18);
    background-image: none;
    border-color: rgba(166, 135, 124, 0.4);
}

window.msifan button.profile-btn.active {
    background-color: rgba(115, 90, 81, 0.42);
    background-image: none;
    border-color: #A6877C;
    color: #D9C4B8;
    font-weight: 700;
}

window.msifan button.boost-btn {
    background-color: rgba(115, 90, 81, 0.10);
    background-image: none;
    color: #A6877C;
    border-radius: 12px;
    border: 1px solid rgba(115, 90, 81, 0.22);
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 3px;
    padding: 14px 0;
    box-shadow: none;
}

window.msifan button.boost-btn:hover {
    background-color: rgba(166, 135, 124, 0.18);
    background-image: none;
}

window.msifan button.boost-btn.active {
    background-color: rgba(166, 135, 124, 0.28);
    background-image: none;
    border-color: #A6877C;
    color: #D9C4B8;
}

window.msifan separator {
    background-color: rgba(115, 90, 81, 0.18);
    min-height: 1px;
    margin: 2px 0;
}

window.msifan flowboxchild {
    background-color: transparent;
    padding: 0;
}

/* ── Editor de curvas ── */
window.editor {
    background-color: #141E26;
    color: #D9C4B8;
}
window.editor .root-box { background-color: #141E26; color: #D9C4B8; }
window.editor headerbar,
window.editor .titlebar {
    background-color: #0D0D0D;
    background-image: none;
    border-bottom: 1px solid rgba(115, 90, 81, 0.3);
    box-shadow: none;
}
window.editor .card {
    background-color: #192330;
    border-radius: 14px;
    border: 1px solid rgba(115, 90, 81, 0.28);
}
window.editor .card-inner { padding: 12px; }
window.editor .lbl-section {
    color: #A6877C;
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 4px;
}
window.editor .hint { color: #735A51; font-size: 9px; letter-spacing: 1px; }
window.editor entry {
    background-color: #0D0D0D;
    background-image: none;
    color: #D9C4B8;
    border-radius: 8px;
    border: 1px solid rgba(115, 90, 81, 0.35);
    padding: 6px 10px;
    caret-color: #A6877C;
}
window.editor entry:focus { border-color: #A6877C; }
window.editor button.mode-btn {
    background-color: rgba(115, 90, 81, 0.12);
    background-image: none;
    color: #D9C4B8;
    border-radius: 10px;
    border: 1px solid rgba(115, 90, 81, 0.25);
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 8px 14px;
    box-shadow: none;
}
window.editor button.mode-btn:hover {
    background-color: rgba(166, 135, 124, 0.20);
    border-color: rgba(166, 135, 124, 0.5);
}
window.editor button.mode-btn.active {
    background-color: #735A51;
    border-color: #A6877C;
    color: #D9C4B8;
}
window.editor button.act-save {
    background-color: #735A51;
    background-image: none;
    color: #D9C4B8;
    border-radius: 10px;
    border: 1px solid #A6877C;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 10px 16px;
    box-shadow: none;
}
window.editor button.act-save:hover { background-color: #8a6c61; }
window.editor button.act-ghost {
    background-color: rgba(115, 90, 81, 0.10);
    background-image: none;
    color: #A6877C;
    border-radius: 10px;
    border: 1px solid rgba(115, 90, 81, 0.25);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 10px 16px;
    box-shadow: none;
}
window.editor button.act-ghost:hover { background-color: rgba(166, 135, 124, 0.18); }
window.editor button.act-danger { color: #C77; border-color: rgba(200, 119, 119, 0.4); }
window.editor button.act-danger:hover { background-color: rgba(200, 119, 119, 0.18); }

window.msifan button.new-btn {
    background-color: rgba(115, 90, 81, 0.10);
    background-image: none;
    color: #A6877C;
    border-radius: 10px;
    border: 1px solid rgba(115, 90, 81, 0.25);
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 6px 12px;
    box-shadow: none;
}
window.msifan button.new-btn:hover {
    background-color: rgba(166, 135, 124, 0.18);
    border-color: rgba(166, 135, 124, 0.45);
}
"""


# ───────────────────────────────── Arc Gauge ─────────────────────────────────

class ArcGauge(Gtk.DrawingArea):
    SIZE = 100

    def __init__(self, max_val=100, color=(0.651, 0.529, 0.486)):
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
    def __init__(self, title, unit, max_val, color=(0.651, 0.529, 0.486)):
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

    def __init__(self, color=(0.651, 0.529, 0.486)):
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


class ProfileEditor(Gtk.Window):
    """Dialogo para crear / editar un perfil de curvas (CPU + GPU)."""

    def __init__(self, parent, name=None, on_saved=None):
        super().__init__(title="Editor de perfil")
        self.add_css_class("editor")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(520, 520)
        self._parent = parent
        self._on_saved = on_saved
        self._editing = name

        profs = read_profiles()
        if name and name in profs:
            cpu = curve_to_points(profs[name].get("cpu"), DEFAULT_CPU)
            gpu = curve_to_points(profs[name].get("gpu"), DEFAULT_GPU)
        else:
            cpu = [list(p) for p in DEFAULT_CPU]
            gpu = [list(p) for p in DEFAULT_GPU]
        self._cpu = cpu
        self._gpu = gpu
        self._target = "cpu"

        self._build(name or "")

    def _build(self, name):
        hb = Adw.HeaderBar()
        hb.set_decoration_layout("close:")
        title = Gtk.Label(label="EDITOR DE CURVA")
        title.add_css_class("app-title")
        hb.set_title_widget(title)
        self.set_titlebar(hb)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.add_css_class("root-box")
        for m in ("set_margin_top", "set_margin_bottom", "set_margin_start", "set_margin_end"):
            getattr(root, m)(14)
        self.set_child(root)

        # nombre
        name_card = self._card()
        ni = name_card.get_first_child()
        ni.append(self._section("NOMBRE DEL PERFIL"))
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("mi-perfil")
        self.entry.set_text(name)
        if self._editing:
            self.entry.set_sensitive(False)  # no renombrar al editar
        ni.append(self.entry)
        root.append(name_card)

        # selector CPU / GPU
        sel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.btn_cpu = Gtk.Button(label="CPU")
        self.btn_gpu = Gtk.Button(label="GPU")
        self.btn_cpu.add_css_class("mode-btn")
        self.btn_gpu.add_css_class("mode-btn")
        self.btn_cpu.add_css_class("active")
        self.btn_cpu.connect("clicked", lambda _b: self._switch("cpu"))
        self.btn_gpu.connect("clicked", lambda _b: self._switch("gpu"))
        sel.append(self.btn_cpu)
        sel.append(self.btn_gpu)
        root.append(sel)

        # editor
        ed_card = self._card()
        ec = ed_card.get_first_child()
        hint = Gtk.Label(label="ARRASTRA LOS PUNTOS · X = °C · Y = VELOCIDAD %")
        hint.add_css_class("hint")
        hint.set_halign(Gtk.Align.START)
        ec.append(hint)
        self.curve = CurveEditor(color=(0.651, 0.529, 0.486))
        self.curve.set_hexpand(True)
        self.curve.set_vexpand(True)
        self.curve.set_points(self._cpu)
        ec.append(self.curve)
        ed_card.set_vexpand(True)
        root.append(ed_card)

        # acciones
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        if self._editing:
            dele = Gtk.Button(label="ELIMINAR")
            dele.add_css_class("act-ghost")
            dele.add_css_class("act-danger")
            dele.connect("clicked", self._on_delete)
            actions.append(dele)
        spacer = Gtk.Box(); spacer.set_hexpand(True)
        actions.append(spacer)
        cancel = Gtk.Button(label="CANCELAR")
        cancel.add_css_class("act-ghost")
        cancel.connect("clicked", lambda _b: self.close())
        actions.append(cancel)
        save = Gtk.Button(label="GUARDAR")
        save.add_css_class("act-ghost")
        save.connect("clicked", lambda _b: self._save(apply=False))
        actions.append(save)
        sapply = Gtk.Button(label="GUARDAR Y APLICAR")
        sapply.add_css_class("act-save")
        sapply.connect("clicked", lambda _b: self._save(apply=True))
        actions.append(sapply)
        root.append(actions)

        self.status = Gtk.Label(label="")
        self.status.add_css_class("hint")
        self.status.set_halign(Gtk.Align.START)
        root.append(self.status)

    def _card(self):
        c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        c.add_css_class("card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.add_css_class("card-inner")
        c.append(inner)
        return c

    def _section(self, txt):
        l = Gtk.Label(label=txt)
        l.add_css_class("lbl-section")
        l.set_halign(Gtk.Align.START)
        return l

    def _switch(self, target):
        # guardar puntos actuales antes de cambiar
        if self._target == "cpu":
            self._cpu = self.curve.get_points()
        else:
            self._gpu = self.curve.get_points()
        self._target = target
        if target == "cpu":
            self.btn_cpu.add_css_class("active")
            self.btn_gpu.remove_css_class("active")
            self.curve.set_points(self._cpu)
        else:
            self.btn_gpu.add_css_class("active")
            self.btn_cpu.remove_css_class("active")
            self.curve.set_points(self._gpu)

    def _collect(self):
        if self._target == "cpu":
            self._cpu = self.curve.get_points()
        else:
            self._gpu = self.curve.get_points()

    def _save(self, apply=False):
        self._collect()
        name = self.entry.get_text().strip()
        if not re.fullmatch(r"[A-Za-z0-9_\-]+", name or ""):
            self.status.set_text("Nombre invalido. Usa letras, numeros, - y _ .")
            return
        profs = read_profiles()
        profs[name] = {
            "cpu": points_to_curve(self._cpu),
            "gpu": points_to_curve(self._gpu),
        }
        try:
            write_profiles(profs)
        except Exception as e:
            self.status.set_text(f"Error al guardar: {e}")
            return
        if self._on_saved:
            self._on_saved(name, apply)
        self.close()

    def _on_delete(self, _b):
        name = self._editing
        profs = read_profiles()
        profs.pop(name, None)
        try:
            write_profiles(profs)
        except Exception as e:
            self.status.set_text(f"Error al eliminar: {e}")
            return
        if self._on_saved:
            self._on_saved(None, False)
        self.close()


# ──────────────────────────────── Main Window ────────────────────────────────

class MsiFanWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="msifan")
        self.add_css_class("msifan")
        self.set_default_size(700, 560)
        self._active_profile = None
        self._err_until = 0.0
        self._build_ui()
        GLib.timeout_add(1000, self._refresh)
        self._refresh()

    def _build_ui(self):
        hb = Adw.HeaderBar()
        hb.set_show_end_title_buttons(True)
        hb.set_decoration_layout("close:minimize")

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_box.set_valign(Gtk.Align.CENTER)
        t1 = Gtk.Label(label="MSI FAN CONTROL")
        t1.add_css_class("app-title")
        t2 = Gtk.Label(label="GP76 · EC CONTROLLER")
        t2.add_css_class("app-sub")
        title_box.append(t1)
        title_box.append(t2)
        hb.set_title_widget(title_box)

        self.lbl_status = Gtk.Label(label="● EC OK")
        self.lbl_status.add_css_class("status-ok")
        self.lbl_status.set_margin_end(8)
        hb.pack_end(self.lbl_status)

        self.set_titlebar(hb)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.add_css_class("root-box")
        root.set_margin_top(14)
        root.set_margin_bottom(14)
        root.set_margin_start(14)
        root.set_margin_end(14)
        self.set_child(root)

        # ── Row 1: sensors + controls ─────────────────────────────────────────
        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        root.append(row1)

        self.cpu_card = SensorCard("CPU", "°C", 110, color=(0.651, 0.529, 0.486))
        self.cpu_card.set_hexpand(True)
        row1.append(self.cpu_card)

        self.gpu_card = SensorCard("GPU", "°C", 110, color=(0.455, 0.353, 0.318))
        self.gpu_card.set_hexpand(True)
        row1.append(self.gpu_card)

        ctrl_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ctrl_card.add_css_class("card")
        ctrl_card.set_hexpand(True)
        ctrl = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        ctrl.add_css_class("card-inner")
        ctrl_card.append(ctrl)
        row1.append(ctrl_card)

        ctrl.append(self._section("FAN MODE"))
        fan_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        ctrl.append(fan_row)
        self.fan_btns = {}
        for m in ["auto", "silent", "advanced"]:
            b = Gtk.Button(label=m.upper())
            b.add_css_class("mode-btn")
            b.connect("clicked", self._on_fan_mode, m)
            fan_row.append(b)
            self.fan_btns[m] = b

        ctrl.append(Gtk.Separator())
        ctrl.append(self._section("SHIFT MODE"))
        shift_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        ctrl.append(shift_row)
        self.shift_btns = {}
        for m in ["eco", "comfort", "turbo"]:
            b = Gtk.Button(label=m.upper())
            b.add_css_class("mode-btn")
            b.connect("clicked", self._on_shift, m)
            shift_row.append(b)
            self.shift_btns[m] = b

        ctrl.append(Gtk.Separator())
        ctrl.append(self._section("COOLER BOOST"))
        self.boost_btn = Gtk.Button(label="BOOST  OFF")
        self.boost_btn.add_css_class("boost-btn")
        self.boost_btn.set_hexpand(True)
        self.boost_btn.connect("clicked", self._on_boost)
        ctrl.append(self.boost_btn)

        # ── Row 2: profiles ───────────────────────────────────────────────────
        prof_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        prof_card.add_css_class("card")
        prof_card.set_hexpand(True)
        prof_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        prof_inner.add_css_class("card-inner")
        prof_card.append(prof_inner)
        root.append(prof_card)

        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        head.append(self._section("PROFILES"))
        spacer = Gtk.Box(); spacer.set_hexpand(True)
        head.append(spacer)
        edit_b = Gtk.Button(label="✎ EDIT")
        edit_b.add_css_class("new-btn")
        edit_b.connect("clicked", self._on_edit_profile)
        head.append(edit_b)
        new_b = Gtk.Button(label="+ NEW")
        new_b.add_css_class("new-btn")
        new_b.connect("clicked", lambda _b: self._open_editor(None))
        head.append(new_b)
        prof_inner.append(head)

        self.pbox = Gtk.FlowBox()
        self.pbox.set_max_children_per_line(8)
        self.pbox.set_min_children_per_line(2)
        self.pbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.pbox.set_column_spacing(6)
        self.pbox.set_row_spacing(6)
        prof_inner.append(self.pbox)

        self.profile_btns = {}
        self._reload_profiles()

    def _reload_profiles(self):
        child = self.pbox.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.pbox.remove(child)
            child = nxt
        self.profile_btns = {}
        for name in list_profiles():
            b = Gtk.Button(label=name)
            b.add_css_class("profile-btn")
            b.connect("clicked", self._on_profile, name)
            self.profile_btns[name] = b
            self.pbox.append(b)

    def _open_editor(self, name):
        ed = ProfileEditor(self, name=name, on_saved=self._on_profile_saved)
        ed.present()

    def _on_edit_profile(self, _b):
        target = self._active_profile or (list_profiles()[0] if list_profiles() else None)
        if target:
            self._open_editor(target)

    def _on_profile_saved(self, name, apply):
        self._reload_profiles()
        self._refresh()
        if name and apply:
            self._on_profile(None, name)

    def _section(self, txt):
        l = Gtk.Label(label=txt)
        l.add_css_class("lbl-section")
        l.set_halign(Gtk.Align.START)
        return l

    def _on_fan_mode(self, _b, m):
        for k, b in self.fan_btns.items():   _tog(b, k == m)   # optimista
        self._apply_verified("mode", m, self.fan_btns, fan_mode, 0)

    def _on_shift(self, _b, m):
        for k, b in self.shift_btns.items(): _tog(b, k == m)   # optimista
        self._apply_verified("shift", m, self.shift_btns, shift_mode, 0)

    def _apply_verified(self, cmd, value, btns, getter, tries):
        """Aplica cmd y verifica contra sysfs; reintenta hasta 3 veces si no persiste."""
        def done(ok, err):
            cur = getter().strip()
            if cur == value:
                self._refresh()
            elif tries < 2:
                self._apply_verified(cmd, value, btns, getter, tries + 1)
            else:
                self._flash_error(err or f"No se pudo aplicar {cmd} {value}")
                self._refresh()
            return False
        run_cmd(cmd, value, on_done=done)

    def _on_boost(self, _b):
        run_cmd("boost", "toggle", on_done=lambda ok, err: (
            self._flash_error(err) if not ok else None, self._refresh(), False)[-1])

    def _on_profile(self, _b, name):
        self._active_profile = name
        for k, b in self.profile_btns.items(): _tog(b, k == name)
        def done(ok, err):
            if not ok:
                self._flash_error(err or f"No se pudo aplicar perfil {name}")
            self._refresh()
            return False
        run_cmd("profile", name, on_done=done)

    def _flash_error(self, msg):
        if not msg:
            return
        self._err_until = time.monotonic() + 4.0
        self.lbl_status.set_text("● " + msg.splitlines()[0][:48])
        self.lbl_status.remove_css_class("status-ok")
        self.lbl_status.add_css_class("status-err")

    def _refresh(self):
        ok = ec_ok()
        if time.monotonic() >= self._err_until:   # no pisar error reciente
            if ok:
                self.lbl_status.set_text("● EC OK")
                self.lbl_status.remove_css_class("status-err")
                self.lbl_status.add_css_class("status-ok")
            else:
                self.lbl_status.set_text("● EC OFFLINE")
                self.lbl_status.remove_css_class("status-ok")
                self.lbl_status.add_css_class("status-err")

        self.cpu_card.update(cpu_temp(), fan_rpm(1))
        self.gpu_card.update(gpu_temp(), fan_rpm(2))

        fm = fan_mode().strip()
        sm = shift_mode().strip()
        bo = boost_on()

        for k, b in self.fan_btns.items():   _tog(b, k == fm)
        for k, b in self.shift_btns.items(): _tog(b, k == sm)

        if bo:
            self.boost_btn.set_label("BOOST  ON")
            self.boost_btn.add_css_class("active")
        else:
            self.boost_btn.set_label("BOOST  OFF")
            self.boost_btn.remove_css_class("active")

        for k, b in self.profile_btns.items():
            _tog(b, k == self._active_profile)

        return True


def _tog(w, state):
    if state: w.add_css_class("active")
    else:     w.remove_css_class("active")


# ────────────────────────────────── App ──────────────────────────────────────
# Gtk.Application puro — sin Adw.Application para evitar que libadwaita
# sobreescriba el CSS con su propio stylesheet de mayor prioridad.

class MsiFanApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.github.yaxoff.msifan")

    def do_activate(self):
        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings:
            gtk_settings.set_property("gtk-application-prefer-dark-theme", True)
            gtk_settings.set_property("gtk-theme-name", "Adwaita-dark")

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER,
        )
        win = MsiFanWindow(self)
        win.present()


if __name__ == "__main__":
    app = MsiFanApp()
    sys.exit(app.run(sys.argv))
