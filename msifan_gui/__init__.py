"""
msifan-gui — GTK4 interface para msi-fanctl
Fedora + Hyprland  |  Wayland native
Requiere: python3-gobject gtk4 libadwaita python3-cairo

Estructura del paquete (capas, de abajo hacia arriba):

    config    — constantes: rutas sysfs, perfiles por defecto, colores del tema.
    backend   — lectura de sensores sysfs + ejecucion de `msifan` (sudo).
    profiles  — IO de profiles.conf + conversion curva <-> puntos.
    style     — hoja CSS de la aplicacion.
    widgets   — widgets reutilizables (ArcGauge, SensorCard, CurveEditor).
    editor    — ventana ProfileEditor (crear / editar / eliminar perfil).
    window    — MsiFanWindow (ventana principal).
    app       — MsiFanApp + punto de entrada main().

Para agregar una feature nueva:
  · widget reutilizable  -> widgets.py
  · ventana/dialogo nuevo -> archivo propio (ver editor.py como plantilla)
  · accion sobre el EC    -> wrapper en backend.py, boton en window.py
  · constante/color/ruta  -> config.py
"""

import os

# GDK_BACKEND se setea en el launcher (msifan-gui).
# La GUI corre como usuario normal — D-Bus y Wayland auth funcionan sin root.
os.environ.setdefault("GTK_THEME",  "Adwaita:dark")
os.environ.setdefault("GTK4_THEME", "Adwaita:dark")

# require_version DEBE ejecutarse antes de cualquier import de Gtk/Adw.
# Se hace una sola vez aqui, al importar el paquete, para que el resto de
# los modulos puedan hacer `from gi.repository import Gtk` sin repetirlo.
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
