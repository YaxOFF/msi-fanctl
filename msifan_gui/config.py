"""Constantes de configuracion: rutas sysfs, perfiles por defecto, tema.

Sin dependencias del resto del paquete — es la capa mas baja.
Centraliza los "numeros magicos" para que ajustar el hardware/tema sea
un cambio de una sola linea aqui.
"""

import os

# ── rutas del sistema ─────────────────────────────────────────────────────────
SYSFS = "/sys/devices/platform/msi-ec"
HWMON = "/sys/class/hwmon"
CONF  = os.path.expanduser("~/.config/msifan/profiles.conf")

# ── perfiles ──────────────────────────────────────────────────────────────────
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

# Perfiles de respaldo si profiles.conf no existe / esta vacio.
FALLBACK_PROFILES = ["default", "silent", "gaming", "max"]

# ── tema (colores RGB 0-1 usados por los widgets de cairo) ─────────────────────
COLOR_ACCENT = (0.651, 0.529, 0.486)   # arena claro (CPU, curvas, gauges)
COLOR_GPU    = (0.455, 0.353, 0.318)   # arena oscuro (GPU)

# ── limites del hardware ──────────────────────────────────────────────────────
TEMP_MAX = 110   # tope de los gauges de temperatura (°C)
