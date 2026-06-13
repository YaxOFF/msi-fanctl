"""MsiFanApp + punto de entrada main().

Gtk.Application puro — sin Adw.Application para evitar que libadwaita
sobreescriba el CSS con su propio stylesheet de mayor prioridad.
"""

import sys

from gi.repository import Gtk, Gdk

from .style import CSS
from .window import MsiFanWindow


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


def main():
    app = MsiFanApp()
    return app.run(sys.argv)
