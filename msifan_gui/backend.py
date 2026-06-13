"""Acceso al hardware: lectura de sensores sysfs + ejecucion de `msifan`.

Toda interaccion con el EC pasa por aqui. La UI nunca toca sysfs ni
subprocess directamente — asi cambiar el backend (p.ej. D-Bus) no obliga
a tocar las ventanas.
"""

import os
import glob
import subprocess
import threading

from gi.repository import GLib

from .config import SYSFS, HWMON


def _r(path, default="0"):
    """Lee un archivo sysfs y devuelve su contenido sin espacios."""
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return default


def _hwmon():
    """Ruta del hwmon de msi_wmi_platform (donde viven los fanN_input)."""
    for d in sorted(glob.glob(f"{HWMON}/hwmon*")):
        if "msi_wmi_platform" in _r(f"{d}/name", ""):
            return d
    return None


# ── sensores ──────────────────────────────────────────────────────────────────
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


# ── estado del EC ──────────────────────────────────────────────────────────────
def fan_mode():   return _r(f"{SYSFS}/fan_mode",    "auto")
def shift_mode(): return _r(f"{SYSFS}/shift_mode",  "comfort")
def boost_on():   return _r(f"{SYSFS}/cooler_boost", "off") == "on"
def ec_ok():      return os.path.isdir(SYSFS)


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
