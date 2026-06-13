#!/usr/bin/env bash
# install.sh — Instalador para msifan + msifan-gui
# Uso: sudo bash install.sh
# Plataformas probadas: Fedora 43 + Hyprland

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

ok()   { echo -e "${GREEN}✓${RESET} $*"; }
info() { echo -e "${CYAN}→${RESET} $*"; }
warn() { echo -e "${YELLOW}!${RESET} $*"; }
die()  { echo -e "${RED}✗ Error:${RESET} $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detectar usuario real (puede correr con sudo)
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

echo -e "${BOLD}msifan installer${RESET}"
echo "────────────────────────────────────"

# ── 1. Root check ────────────────────────────────────────────────────────────
[[ $EUID -eq 0 ]] || die "Ejecuta con sudo: sudo bash install.sh"

# ── 2. Detectar distro para dependencias ─────────────────────────────────────
detect_pkg_manager() {
    if command -v dnf &>/dev/null;    then echo "dnf";
    elif command -v pacman &>/dev/null; then echo "pacman";
    elif command -v apt &>/dev/null;   then echo "apt";
    else echo "unknown"; fi
}

PKG=$(detect_pkg_manager)

# ── 3. Dependencias Python/GTK4 ──────────────────────────────────────────────
info "Verificando dependencias de la GUI..."

check_python_dep() {
    python3 -c "import $1" 2>/dev/null
}

GUI_DEPS_OK=true

if ! check_python_dep "gi"; then
    GUI_DEPS_OK=false
    warn "python3-gobject no encontrado"
fi

if ! check_python_dep "cairo"; then
    GUI_DEPS_OK=false
    warn "python3-cairo no encontrado"
fi

if [[ "$GUI_DEPS_OK" == false ]]; then
    info "Instalando dependencias de la GUI..."
    case "$PKG" in
        dnf)    dnf install -y python3-gobject python3-cairo gtk4 libadwaita ;;
        pacman) pacman -S --noconfirm python-gobject python-cairo gtk4 libadwaita ;;
        apt)    apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 ;;
        *)      warn "Gestor de paquetes desconocido. Instala manualmente:
                  python3-gobject, python3-cairo, gtk4, libadwaita" ;;
    esac
fi

ok "Dependencias OK"

# ── 4. Verificar modulo msi-ec ────────────────────────────────────────────────
info "Verificando modulo msi-ec..."
if ! ls /sys/devices/platform/msi-ec &>/dev/null; then
    warn "El modulo msi-ec no esta cargado o no esta instalado."
    warn "Instala msi-ec: https://github.com/BeardOverflow/msi-ec"
    warn "Luego: sudo modprobe msi_ec debug=1"
    warn "Continuando instalacion de archivos de todas formas..."
else
    ok "msi-ec detectado"
fi

# ── 5. Instalar archivos ──────────────────────────────────────────────────────
info "Instalando archivos en /usr/local/bin..."

install -m 755 "$SCRIPT_DIR/msifan"          /usr/local/bin/msifan
install -m 755 "$SCRIPT_DIR/msifan-gui"      /usr/local/bin/msifan-gui

# La GUI es un paquete Python — se instala bajo /usr/local/lib/msifan-gui
# y el launcher la ejecuta con `python3 -m msifan_gui` (ver msifan-gui).
PKG_DST="/usr/local/lib/msifan-gui/msifan_gui"
rm -rf "$PKG_DST"
mkdir -p "$PKG_DST"
install -m 644 "$SCRIPT_DIR/msifan_gui"/*.py "$PKG_DST/"

ok "Binarios instalados"

# ── 6. Perfiles de curva ──────────────────────────────────────────────────────
CONF_DIR="$REAL_HOME/.config/msifan"
CONF_FILE="$CONF_DIR/profiles.conf"

if [[ ! -f "$CONF_FILE" ]]; then
    info "Instalando perfiles por defecto en $CONF_FILE..."
    mkdir -p "$CONF_DIR"
    install -m 644 "$SCRIPT_DIR/msifan-profiles.conf" "$CONF_FILE"
    chown -R "$REAL_USER:$REAL_USER" "$CONF_DIR"
    ok "Perfiles instalados"
else
    warn "Ya existe $CONF_FILE — no se sobreescribio"
fi

# ── 7. Entrada de escritorio (.desktop) ──────────────────────────────────────
info "Instalando entrada de escritorio..."

APPS_DIR="$REAL_HOME/.local/share/applications"
mkdir -p "$APPS_DIR"

# Generar .desktop con ruta absoluta
cat > "$APPS_DIR/msifan-gui.desktop" << 'EOF'
[Desktop Entry]
Name=MSI Fan Control
Comment=Fan controller for MSI laptops via EC
Exec=env GDK_BACKEND=wayland GSK_RENDERER=gl /usr/local/bin/msifan-gui
Icon=cpu
Terminal=false
Type=Application
Categories=System;HardwareSettings;
Keywords=fan;cooling;msi;temperature;ec;
EOF

chown "$REAL_USER:$REAL_USER" "$APPS_DIR/msifan-gui.desktop"

# Actualizar base de datos de aplicaciones
if command -v update-desktop-database &>/dev/null; then
    sudo -u "$REAL_USER" update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

ok ".desktop instalado en $APPS_DIR"

# ── 8. Regla sudoers (NOPASSWD para msifan) ──────────────────────────────────
SUDOERS_FILE="/etc/sudoers.d/msifan"

if [[ ! -f "$SUDOERS_FILE" ]]; then
    info "Creando regla sudoers para msifan sin contrasena..."
    echo "$REAL_USER ALL=(ALL) NOPASSWD: /usr/local/bin/msifan" > "$SUDOERS_FILE"
    chmod 440 "$SUDOERS_FILE"
    ok "Regla sudoers creada: $REAL_USER puede ejecutar msifan sin contrasena"
else
    warn "Ya existe $SUDOERS_FILE — no se modifico"
fi

# ── 9. Modprobe persistente ───────────────────────────────────────────────────
MODPROBE_CONF="/etc/modprobe.d/msi-ec.conf"
if [[ ! -f "$MODPROBE_CONF" ]]; then
    info "Configurando carga del modulo con debug=1..."
    echo "options msi_ec debug=1" > "$MODPROBE_CONF"
    ok "Creado $MODPROBE_CONF"
else
    warn "Ya existe $MODPROBE_CONF — no se modifico"
fi

# ── Resumen ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Instalacion completada.${RESET}"
echo "────────────────────────────────────"
echo -e "  CLI:        ${CYAN}sudo msifan status${RESET}"
echo -e "  GUI:        ${CYAN}msifan-gui${RESET}"
echo -e "  Launcher:   Busca 'MSI Fan Control' en tu lanzador de apps"
echo ""

if ! ls /sys/devices/platform/msi-ec &>/dev/null; then
    echo -e "${YELLOW}Recuerda instalar msi-ec y cargar el modulo antes de usar la herramienta.${RESET}"
fi
