"""Ventana ProfileEditor — crear / editar / eliminar un perfil de curvas.

Plantilla para ventanas/dialogos nuevos: subclase de Gtk.Window, construye
la UI en _build(), notifica al padre con un callback `on_saved`.
"""

import re

from gi.repository import Gtk, Adw

from .config import DEFAULT_CPU, DEFAULT_GPU, COLOR_ACCENT
from .profiles import read_profiles, write_profiles, points_to_curve, curve_to_points
from .widgets import CurveEditor


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
        self.curve = CurveEditor(color=COLOR_ACCENT)
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
