"""MsiFanWindow — ventana principal.

Orquesta: sensores (SensorCard), controles del EC (fan/shift/boost),
y la lista de perfiles. Cada accion llama a backend.run_cmd y refresca
el estado leyendo sysfs.

Para agregar un control nuevo:
  1. wrapper de lectura/escritura en backend.py
  2. boton + handler aqui (ver _on_fan_mode como patron)
  3. reflejar su estado en _refresh()
"""

import time

from gi.repository import Gtk, Adw, GLib

from .config import TEMP_MAX, COLOR_ACCENT, COLOR_GPU
from .backend import (
    cpu_temp, gpu_temp, fan_rpm,
    fan_mode, shift_mode, boost_on, ec_ok, run_cmd,
)
from .profiles import list_profiles
from .widgets import SensorCard, _tog
from .editor import ProfileEditor


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

        self.cpu_card = SensorCard("CPU", "°C", TEMP_MAX, color=COLOR_ACCENT)
        self.cpu_card.set_hexpand(True)
        row1.append(self.cpu_card)

        self.gpu_card = SensorCard("GPU", "°C", TEMP_MAX, color=COLOR_GPU)
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
