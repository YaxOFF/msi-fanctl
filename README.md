# msifan - Controlador de Ventiladores MSI para Linux

Controlador personalizado de ventiladores para laptops MSI en Linux, basado en el modulo `msi-ec`. Permite gestionar modos de ventilador, perfiles de curvas personalizadas, cooler boost y monitoreo en tiempo real — tanto desde la **CLI** como desde una **interfaz grafica GTK4** nativa para Wayland/Hyprland.

---

## Hardware Soportado

| Campo | Valor |
|---|---|
| **Laptop** | MSI Vector GP76 12UGSO |
| **Placa Base** | MS-17K4 |
| **Firmware EC** | 17K4EMS1.112 |
| **BIOS** | E17K4IMS.509 |
| **Kernel probado** | 6.18.16-200.fc43.x86_64 |
| **Distro** | Fedora 43 + Hyprland |

> **Nota:** Este script fue disenado especificamente para el modelo GP76 12UGSO con firmware EC 17K4EMS1.112. Los registros del EC (direcciones de memoria para curvas de ventilador) pueden variar en otros modelos MSI. Consulta la lista de dispositivos soportados del proyecto [msi-ec](https://github.com/BeardOverflow/msi-ec) antes de usarlo en otro hardware.

---

## Como Funciona

### Arquitectura del Sistema

El control de ventiladores en laptops MSI se realiza a traves del **Embedded Controller (EC)**, un microcontrolador independiente en la placa base que gestiona funciones de bajo nivel como ventiladores, LEDs, bateria y sensores termicos.

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   msifan     │────>│  msi-ec (kernel)  │────>│  EC (chip)  │
│  (script)    │     │  /sys/devices/    │     │  MS-17K4    │
└─────────────┘     │  platform/msi-ec/ │     └─────────────┘
                    └──────────────────┘
                             │
                    ┌──────────────────┐
                    │  msi_wmi_platform │
                    │  (hwmon - RPM)    │
                    └──────────────────┘
```

El script `msifan` interactua con dos modulos del kernel:

- **msi-ec** (BeardOverflow/msi-ec): Expone controles del EC en `/sys/devices/platform/msi-ec/`. Permite cambiar modos de ventilador, shift modes, cooler boost, y en modo debug, leer/escribir registros individuales del EC.
- **msi_wmi_platform**: Expone las RPM reales de los ventiladores a traves de hwmon (`/sys/class/hwmon/`).

### Modos de Ventilador

El EC soporta tres modos de ventilador controlados por el registro `0xf4`:

- **auto** (`0x0d`): El EC gestiona los ventiladores automaticamente segun sus curvas internas.
- **silent** (`0x1d`): Curva conservadora que prioriza el silencio.
- **advanced** (`0x8d`): Permite definir curvas personalizadas de 7 puntos escritas directamente en los registros del EC.

### Shift Modes (Rendimiento)

Controlan el perfil de rendimiento del CPU/GPU:

- **eco**: Frecuencias y voltajes reducidos (ahorro de energia).
- **comfort**: Frecuencias dinamicas (equilibrado).
- **turbo**: Frecuencias y voltajes maximos (rendimiento completo).

### Registros del EC

#### Curva de Ventilador CPU

| Punto | Registro Temperatura | Registro Velocidad |
|-------|---------------------|--------------------|
| 1 | 0x6a | 0x72 |
| 2 | 0x6b | 0x73 |
| 3 | 0x6c | 0x74 |
| 4 | 0x6d | 0x75 |
| 5 | 0x6e | 0x76 |
| 6 | 0x6f | 0x77 |
| 7 | 0x70 | 0x78 |

- Velocidad actual CPU: `0x71`

#### Curva de Ventilador GPU

| Punto | Registro Temperatura | Registro Velocidad |
|-------|---------------------|--------------------|
| 1 | 0x82 | 0x8a |
| 2 | 0x83 | 0x8b |
| 3 | 0x84 | 0x8c |
| 4 | 0x85 | 0x8d |
| 5 | 0x86 | 0x8e |
| 6 | 0x87 | 0x8f |
| 7 | 0x88 | 0x90 |

- Velocidad actual GPU: `0x89`

#### Otros Registros Relevantes

| Registro | Funcion |
|----------|---------|
| 0xf4 | Fan mode (auto/silent/advanced) |
| 0xf2 | Shift mode (eco/comfort/turbo) |
| 0x98 bit 7 | Cooler Boost (on/off) |
| 0xa0-0xbb | Firmware version + fecha |

> **Advertencia:** Escribir valores incorrectos en registros desconocidos del EC puede danar el hardware o bloquear el dispositivo. Solo se deben modificar los registros documentados.

### Fuentes de Datos

| Dato | Fuente | Ruta |
|------|--------|------|
| Temperatura CPU | msi-ec | `/sys/devices/platform/msi-ec/cpu/realtime_temperature` |
| Temperatura GPU | msi-ec | `/sys/devices/platform/msi-ec/gpu/realtime_temperature` |
| Velocidad % CPU | EC registro 0x71 | via `debug/ec_get` |
| Velocidad % GPU | EC registro 0x89 | via `debug/ec_get` |
| RPM CPU | msi_wmi_platform | `/sys/class/hwmon/hwmonX/fan1_input` |
| RPM GPU | msi_wmi_platform | `/sys/class/hwmon/hwmonX/fan2_input` |
| Fan mode | msi-ec | `/sys/devices/platform/msi-ec/fan_mode` |
| Shift mode | msi-ec | `/sys/devices/platform/msi-ec/shift_mode` |
| Cooler Boost | msi-ec | `/sys/devices/platform/msi-ec/cooler_boost` |

> El numero de hwmon (`hwmonX`) puede cambiar entre reinicios. El script lo detecta dinamicamente buscando el que tenga nombre `msi_wmi_platform`.

---

## Dependencias

- **Fedora** (probado en Fedora 43, deberia funcionar en cualquier version reciente)
- Paquetes del sistema: `kernel-devel`, `kernel-headers`, `dkms`, `git`
- Modulo kernel: [BeardOverflow/msi-ec](https://github.com/BeardOverflow/msi-ec)
- Herramientas: `bash`, `watch`, `lm_sensors` (opcional, para `sensors`)

---

## Instalacion

### 1. Instalar dependencias

```bash
sudo dnf install -y kernel-devel kernel-headers dkms git lm_sensors
```

### 2. Instalar el modulo msi-ec

```bash
cd ~/Downloads
git clone https://github.com/BeardOverflow/msi-ec.git
cd msi-ec
sudo make dkms-install
```

### 3. Configurar carga automatica con debug

El modo debug es necesario para exponer los registros de curvas de ventilador:

```bash
echo "options msi_ec debug=1" | sudo tee /etc/modprobe.d/msi-ec.conf
```

El modulo ya se configuro para cargar automaticamente en `/etc/modules-load.d/msi-ec.conf` durante la instalacion DKMS.

### 4. Cargar el modulo (sin reiniciar)

```bash
sudo modprobe msi_ec debug=1
```

### 5. Verificar que funciona

```bash
ls /sys/devices/platform/msi-ec/debug/
# Debe mostrar: ec_dump  ec_get  ec_set  fw_version
```

### 6. Instalar msifan

```bash
sudo cp msifan /usr/local/bin/msifan
sudo chmod +x /usr/local/bin/msifan
```

Los perfiles se generan automaticamente en `~/.config/msifan/profiles.conf` la primera vez que se usa un comando de perfiles.

### 7. Verificar instalacion

```bash
sudo msifan status
```

---

## Uso

### Comandos Disponibles

```
msifan status                        Estado actual (temps, RPM, curvas)
msifan monitor                       Status en tiempo real (actualiza cada segundo)
msifan mode <auto|silent|advanced>   Cambiar modo de ventilador
msifan shift <eco|comfort|turbo>     Cambiar shift mode (rendimiento)
msifan boost <on|off|toggle>         Controlar Cooler Boost
msifan profile <nombre>              Aplicar un perfil de curva guardado
msifan profiles                      Listar perfiles disponibles
msifan save <nombre>                 Guardar curva actual como perfil nuevo
msifan set-curve <cpu|gpu> t1:v1 t2:v2 ... t7:v7
                                     Aplicar curva manual (7 puntos)
msifan help                          Mostrar ayuda
```

> Todos los comandos que modifican el sistema requieren `sudo`.

### Ejemplos

```bash
# Ver estado completo
sudo msifan status

# Monitoreo en tiempo real
sudo msifan monitor

# Aplicar perfil de juegos
sudo msifan profile gaming

# Aplicar perfil silencioso
sudo msifan profile silent

# Volver a valores de fabrica
sudo msifan profile default

# Ventiladores al maximo
sudo msifan profile max

# Activar/desactivar cooler boost
sudo msifan boost toggle

# Volver a modo automatico (el EC gestiona todo)
sudo msifan mode auto

# Cambiar a modo turbo (rendimiento maximo)
sudo msifan shift turbo

# Curva manual para CPU
sudo msifan set-curve cpu 45:20 50:40 58:55 65:65 72:80 80:90 90:100

# Guardar la curva actual con un nombre
sudo msifan save mi_perfil_custom
```

---

## Perfiles

Los perfiles se almacenan en `~/.config/msifan/profiles.conf`. Cada perfil define 7 puntos de curva para CPU y GPU en formato `temperatura:velocidad%`.

### Perfiles Incluidos

#### default
Curva de fabrica del EC. Equilibrio entre ruido y temperatura.
```
cpu = 50:0 56:40 62:49 70:58 75:67 80:76 100:85
gpu = 55:0 60:48 65:56 70:64 75:72 80:79 98:86
```

#### silent
Prioriza el silencio. Los ventiladores arrancan mas tarde y a menor velocidad.
```
cpu = 55:0 62:25 68:35 74:45 80:55 86:65 100:75
gpu = 60:0 66:25 72:35 76:45 80:55 86:65 100:75
```

#### gaming
Ventiladores agresivos. Arrancan antes y suben rapido para mantener temperaturas bajas bajo carga.
```
cpu = 45:30 50:45 58:55 65:65 72:80 80:90 90:100
gpu = 45:30 50:45 58:55 65:65 72:80 80:90 90:100
```

#### max
Todos los ventiladores al 100% sin importar la temperatura. Util para benchmarks o pruebas termicas.
```
cpu = 0:100 0:100 0:100 0:100 0:100 0:100 0:100
gpu = 0:100 0:100 0:100 0:100 0:100 0:100 0:100
```

### Crear Perfiles Personalizados

Hay dos formas:

**Opcion A:** Editar el archivo manualmente:

```bash
nano ~/.config/msifan/profiles.conf
```

Agregar un bloque nuevo:

```ini
[mi_perfil]
cpu = 50:10 55:30 60:45 68:55 75:70 82:85 95:100
gpu = 50:10 55:30 60:45 68:55 75:70 82:85 95:100
```

**Opcion B:** Ajustar la curva manualmente y guardarla:

```bash
sudo msifan set-curve cpu 50:10 55:30 60:45 68:55 75:70 82:85 95:100
sudo msifan set-curve gpu 50:10 55:30 60:45 68:55 75:70 82:85 95:100
sudo msifan save mi_perfil
```

### Reglas de los Perfiles

- Cada curva debe tener **exactamente 7 puntos**.
- Formato de cada punto: `temperatura:velocidad` (ambos valores de 0 a 100).
- Las temperaturas deben estar ordenadas de menor a mayor.
- Las velocidades son porcentajes (0% = apagado, 100% = maximo).

---

## Interfaz Grafica (msifan-gui)

La GUI es una aplicacion GTK4 nativa Wayland. Muestra temperatura, RPM y porcentaje de ventilador en gauges de arco en tiempo real, y permite cambiar modos, perfiles y cooler boost con un clic.

### Instalacion rapida (GUI)

```bash
# Instalador automatico (CLI + GUI + .desktop)
sudo bash install.sh
```

O manual:

```bash
sudo cp msifan /usr/local/bin/msifan
sudo chmod +x /usr/local/bin/msifan
sudo cp msifan-gui /usr/local/bin/msifan-gui
sudo chmod +x /usr/local/bin/msifan-gui
# La GUI es un paquete Python — copiar el directorio completo
sudo mkdir -p /usr/local/lib/msifan-gui
sudo cp -r msifan_gui /usr/local/lib/msifan-gui/
cp msifan-gui.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/
```

### Dependencias de la GUI

```bash
# Fedora
sudo dnf install python3-gobject python3-cairo gtk4 libadwaita

# Arch/Manjaro
sudo pacman -S python-gobject python-cairo gtk4 libadwaita

# Ubuntu/Debian
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
```

### Ejecutar

```bash
msifan-gui          # desde PATH (tras instalar)
./msifan-gui        # desde el directorio del repo
```

Los controles que modifican el EC (modo, perfil, boost) invocan `sudo msifan` internamente. Para evitar que pida contrasena cada vez:

```bash
echo "$USER ALL=(ALL) NOPASSWD: /usr/local/bin/msifan" | sudo tee /etc/sudoers.d/msifan
```

---

## Solucion: Pantalla Negra en Hyprland (GTK4)

Este problema afecta a aplicaciones GTK4 en Hyprland con GPU Intel y es causado por una incompatibilidad entre el renderer Vulkan de GTK4 y el compositor de Hyprland.

### Causa Raiz

GTK4 usa por defecto el renderer **Vulkan** (`GSK_RENDERER=vulkan`). En sistemas con Intel iGPU bajo Hyprland, el pipeline Vulkan de GTK entra en conflicto con el compositor, resultando en una superficie opaca negra en vez de renderizar el contenido.

### Solucion

Forzar el renderer **OpenGL** en vez de Vulkan:

```bash
GSK_RENDERER=gl GDK_BACKEND=wayland python3 -m msifan_gui
```

El launcher `msifan-gui` ya aplica estas variables automaticamente. No es necesario configurar nada manualmente.

### Por Que No Usar `sudo` Para la GUI

Ejecutar la GUI con `sudo python3 -m msifan_gui` tambien causa pantalla negra por una razon diferente: `sudo` elimina las variables de entorno de sesion (`WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, `DBUS_SESSION_BUS_ADDRESS`). Sin estas variables:

- GTK4 no puede conectar al compositor Wayland
- El bus D-Bus de sesion no es accesible
- GTK muestra el error: `Unable to acquire session bus`

**Solucion:** La GUI corre como usuario normal. Los comandos que necesitan root (`msifan mode`, `msifan profile`, etc.) se ejecutan internamente con `sudo msifan`.

### Tabla de Variables de Entorno

| Variable | Valor | Proposito |
|---|---|---|
| `GDK_BACKEND` | `wayland` | Fuerza backend Wayland, evita caida a XWayland |
| `GSK_RENDERER` | `gl` | Renderer OpenGL, evita conflicto Vulkan+Hyprland |

---

## Integracion con Hyprland

### Atajos de Teclado

Agregar a `~/.config/hypr/hyprland.conf`:

```conf
# msifan - Control de ventiladores
bind = SUPER, F5, exec, sudo msifan boost toggle
bind = SUPER SHIFT, F1, exec, sudo msifan profile silent
bind = SUPER SHIFT, F2, exec, sudo msifan profile default
bind = SUPER SHIFT, F3, exec, sudo msifan profile gaming
bind = SUPER SHIFT, F4, exec, sudo msifan profile max
bind = SUPER SHIFT, F5, exec, sudo msifan mode auto
```

> Para que `sudo` funcione sin pedir contrasena en los atajos, agrega a `/etc/sudoers.d/msifan`:
>
> ```
> tu_usuario ALL=(ALL) NOPASSWD: /usr/local/bin/msifan
> ```
>
> Crealo con: `echo "tu_usuario ALL=(ALL) NOPASSWD: /usr/local/bin/msifan" | sudo tee /etc/sudoers.d/msifan`

### Widget para Waybar

Agregar un modulo custom en `~/.config/waybar/config`:

```json
"custom/msifan": {
    "exec": "bash -c 'CPU_T=$(cat /sys/devices/platform/msi-ec/cpu/realtime_temperature); GPU_T=$(cat /sys/devices/platform/msi-ec/gpu/realtime_temperature); MODE=$(cat /sys/devices/platform/msi-ec/fan_mode); echo \"{\\\"text\\\": \\\"CPU:${CPU_T}° GPU:${GPU_T}°\\\", \\\"tooltip\\\": \\\"Fan: ${MODE}\\\"}\"'",
    "return-type": "json",
    "interval": 3,
    "on-click": "sudo msifan boost toggle",
    "on-click-right": "sudo msifan mode auto"
}
```

Agregar a la barra en la seccion `modules-right` (o donde prefieras):

```json
"modules-right": ["custom/msifan", ...]
```

Estilo en `~/.config/waybar/style.css`:

```css
#custom-msifan {
    padding: 0 10px;
    color: #a6e3a1;
}
```

---

## Diagnostico

### El modulo no carga

```bash
sudo dmesg | grep msi
```

Si dice "Your firmware version is not supported", tu version de EC no esta en la lista del driver. Abre un issue en el repositorio msi-ec.

Si dice "Key was rejected by service", tienes Secure Boot activado y el modulo no esta firmado. Opciones: desactivar Secure Boot en BIOS, o registrar la clave MOK generada por DKMS.

### No aparece la carpeta debug

```bash
sudo modprobe -r msi_ec
sudo modprobe msi_ec debug=1
```

Verifica que el parametro quede persistente:

```bash
cat /etc/modprobe.d/msi-ec.conf
# Debe decir: options msi_ec debug=1
```

### Las RPM no se muestran

```bash
sensors | grep fan
```

Si no hay salida, instala lm_sensors y detecta sensores:

```bash
sudo dnf install lm_sensors
sudo sensors-detect --auto
sensors
```

### Resetear el EC a valores de fabrica

Si algo sale mal con las curvas:

```bash
sudo msifan mode auto
```

Esto hace que el EC vuelva a gestionar los ventiladores con sus curvas internas. Si el problema es mas grave, usa el boton de reset del EC en la parte inferior de la laptop (necesitas un clip).

### Obtener el dump del EC

Util para diagnosticar problemas o reportar bugs:

```bash
sudo cat /sys/devices/platform/msi-ec/debug/ec_dump
```

---

## Estructura de Archivos

### Instalado en el sistema

```
/usr/local/bin/msifan                    Script principal (CLI)
/usr/local/bin/msifan-gui                Launcher de la GUI
/usr/local/lib/msifan-gui/msifan_gui/    Paquete Python de la GUI
~/.config/msifan/profiles.conf           Perfiles de curvas
/etc/modprobe.d/msi-ec.conf              Opciones del modulo (debug=1)
/etc/modules-load.d/msi-ec.conf          Carga automatica del modulo
/sys/devices/platform/msi-ec/            Interfaz sysfs del driver
/sys/devices/platform/msi-ec/debug/      Interfaz debug (ec_dump, ec_get, ec_set)
/sys/class/hwmon/hwmonX/                 RPM reales (msi_wmi_platform)
```

### Paquete de la GUI (`msifan_gui/`)

La GUI esta organizada en capas: cada modulo tiene una sola responsabilidad,
asi agregar features no obliga a tocar un archivo gigante.

```
msifan_gui/
├── __init__.py     Setup de gi/Gtk + mapa del paquete
├── __main__.py     Entry point: python3 -m msifan_gui
├── config.py       Constantes: rutas sysfs, perfiles default, colores del tema
├── backend.py      Lectura de sensores sysfs + ejecucion de `msifan` (sudo)
├── profiles.py     IO de profiles.conf + conversion curva <-> puntos
├── style.py        Hoja CSS de la aplicacion
├── widgets.py      Widgets reutilizables (ArcGauge, SensorCard, CurveEditor)
├── editor.py       Ventana ProfileEditor (crear/editar/eliminar perfil)
├── window.py       MsiFanWindow (ventana principal)
└── app.py          MsiFanApp + main()
```

**Donde agregar una feature:**

| Feature                    | Archivo                                      |
|----------------------------|----------------------------------------------|
| Widget reutilizable nuevo  | `widgets.py`                                 |
| Ventana / dialogo nuevo    | archivo propio (usar `editor.py` de plantilla) |
| Accion sobre el EC         | wrapper en `backend.py` + boton en `window.py` |
| Constante / color / ruta   | `config.py`                                  |
| Estilo / CSS               | `style.py`                                   |

Dependencias entre capas (siempre hacia abajo, sin ciclos):
`app → window → {widgets, editor, backend, profiles} → config`

---

## Creditos y Referencias

- **msi-ec**: [github.com/BeardOverflow/msi-ec](https://github.com/BeardOverflow/msi-ec) - Modulo kernel que hace posible todo esto.
- **MControlCenter**: [github.com/dmitry-s93/MControlCenter](https://github.com/dmitry-s93/MControlCenter) - GUI alternativa para control de MSI en Linux.
- **MSI_Fan_Control**: [github.com/atharvalele/MSI_Fan_Control](https://github.com/atharvalele/MSI_Fan_Control) - Referencia para el mapeo de registros EC.

---

## Licencia

Este script es software libre. Usalo, modificalo y distribuyelo como quieras. Sin garantia. Si le escribes valores raros al EC y algo se rompe, es bajo tu responsabilidad.