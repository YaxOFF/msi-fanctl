#!/usr/bin/env python3
"""
msifan-gui — GTK4 interface para msi-fanctl
Fedora + Hyprland  |  Wayland native
Requiere: python3-gobject gtk4 libadwaita python3-cairo
"""

import os, sys

# ── Wayland env fix ───────────────────────────────────────────────────────────
# sudo elimina WAYLAND_DISPLAY y XDG_RUNTIME_DIR del entorno.
# GTK4 cae a XWayland → pantalla negra en Hyprland.
# Reconstruimos las variables desde el usuario real antes de importar GTK.
_sudo_user = os.environ.get("SUDO_USER")
if _sudo_user and not os.environ.get("WAYLAND_DISPLAY"):
    import pwd, subprocess as _sp
    try:
        _real_uid = pwd.getpwnam(_sudo_user).pw_uid
        os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{_real_uid}")
        _env_out = _sp.run(
            ["sudo", "-u", _sudo_user, "--", "env"],
            capture_output=True, text=True, timeout=3,
        ).stdout
        for _line in _env_out.splitlines():
            if _line.startswith("WAYLAND_DISPLAY="):
                os.environ.setdefault("WAYLAND_DISPLAY", _line.split("=", 1)[1])
            elif _line.startswith("XDG_RUNTIME_DIR="):
                os.environ.setdefault("XDG_RUNTIME_DIR", _line.split("=", 1)[1])
    except Exception:
        pass

os.environ["GDK_BACKEND"]        = "wayland"   # nunca caer a X11
os.environ.setdefault("GTK_THEME",          "Adwaita:dark")
os.environ.setdefault("GTK4_THEME",         "Adwaita:dark")
os.environ.setdefault("GSETTINGS_BACKEND",  "memory")      # sin dconf daemon

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk
import cairo
import subprocess, math, glob, re, threading


# ─────────────────────────────── sysfs helpers ───────────────────────────────

SYSFS = "/sys/devices/platform/msi-ec"
HWMON = "/sys/class/hwmon"
CONF  = os.path.expanduser("~/.config/msifan/profiles.conf")

if _sudo_user:
    import pwd as _pwd
    _real_home = _pwd.getpwnam(_sudo_user).pw_dir
    CONF = os.path.join(
        os.environ.get("XDG_CONFIG_HOME", f"{_real_home}/.config"),
        "msifan/profiles.conf",
    )


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

def list_profiles():
    names = []
    try:
        for line in open(CONF):
            m = re.match(r'^\[(.+)\]', line.strip())
            if m:
                names.append(m.group(1))
    except Exception:
        pass
    return names or ["default", "silent", "gaming", "max"]


def run_cmd(*args):
    """Ejecuta msifan con sudo en hilo separado — no bloquea la UI."""
    def _do():
        try:
            subprocess.run(
                ["sudo", "msifan"] + list(args),
                capture_output=True, timeout=8,
            )
        except Exception:
            pass
    threading.Thread(target=_do, daemon=True).start()


# ──────────────────────────────────── CSS ────────────────────────────────────

CSS = """
* {
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
    -gtk-icon-style: regular;
}

window.msifan,
window.msifan > *,
window.msifan > * > *,
window.msifan .main-bg,
window.msifan box,
window.msifan scrolledwindow,
window.msifan viewport {
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


# ──────────────────────────────── Main Window ────────────────────────────────

class MsiFanWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="msifan")
        self.add_css_class("msifan")
        self.set_default_size(700, 560)
        self.set_resizable(False)
        self._active_profile = None
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

        prof_inner.append(self._section("PROFILES"))
        pbox = Gtk.FlowBox()
        pbox.set_max_children_per_line(8)
        pbox.set_min_children_per_line(2)
        pbox.set_selection_mode(Gtk.SelectionMode.NONE)
        pbox.set_column_spacing(6)
        pbox.set_row_spacing(6)
        prof_inner.append(pbox)

        self.profile_btns = {}
        for name in list_profiles():
            b = Gtk.Button(label=name)
            b.add_css_class("profile-btn")
            b.connect("clicked", self._on_profile, name)
            self.profile_btns[name] = b
            pbox.append(b)

    def _section(self, txt):
        l = Gtk.Label(label=txt)
        l.add_css_class("lbl-section")
        l.set_halign(Gtk.Align.START)
        return l

    def _on_fan_mode(self, _b, m): run_cmd("mode", m);         GLib.timeout_add(500, self._refresh)
    def _on_shift(self, _b, m):    run_cmd("shift", m);        GLib.timeout_add(500, self._refresh)
    def _on_boost(self, _b):       run_cmd("boost", "toggle"); GLib.timeout_add(500, self._refresh)

    def _on_profile(self, _b, name):
        self._active_profile = name
        run_cmd("profile", name)
        GLib.timeout_add(500, self._refresh)

    def _refresh(self):
        ok = ec_ok()
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

        fm = fan_mode()
        sm = shift_mode()
        bo = boost_on()

        for k, b in self.fan_btns.items():   _tog(b, k in fm)
        for k, b in self.shift_btns.items(): _tog(b, k in sm)

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
