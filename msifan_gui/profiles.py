"""IO de profiles.conf + conversion entre curva de texto y lista de puntos.

Formato del archivo:  [nombre]\\n cpu = T:S T:S ... \\n gpu = T:S T:S ...
Representacion interna: lista de 7 puntos [[temp, vel], ...].
"""

import re

from .config import CONF, PROFILES_HEADER, FALLBACK_PROFILES


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
    import os
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
    return list(read_profiles().keys()) or list(FALLBACK_PROFILES)
