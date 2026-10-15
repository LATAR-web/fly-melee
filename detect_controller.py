#!/usr/bin/env python3
"""
Detector y Configurador Automático de Mandos / Gamepads para Dolphin y Melee
Detecta cualquier mando genérico USB/Bluetooth, diagnostica problemas de conexión
y genera la configuración GCPadNew.ini para el Puerto 2 (Jugador Humano).
Compatible con Linux y Windows.
"""
import os
import sys
import platform
import time
import subprocess
import configparser
from pathlib import Path

# ==============================================================================
# Comprobación de Sistema Operativo (Linux o Windows - No incluye Mac)
# ==============================================================================
CURRENT_OS = platform.system()
if CURRENT_OS == "Linux":
    IS_LINUX = True
    IS_WINDOWS = False
elif CURRENT_OS == "Windows":
    IS_LINUX = False
    IS_WINDOWS = True
else:
    raise OSError(f"Sistema operativo no soportado: '{CURRENT_OS}'. Este script solo admite Linux o Windows.")

# ==============================================================================
# Inicialización y Entornos Virtuales
# ==============================================================================
if IS_LINUX:
    try:
        import evdev
    except ImportError:
        venv_candidates = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "bin", "python"),
            "/home/ltar/.venvs/pytorch/bin/python",
        ]
        for venv_python in venv_candidates:
            if os.path.exists(venv_python) and sys.executable != venv_python:
                script = os.path.abspath(__file__) if "__file__" in globals() else sys.argv[0]
                os.execv(venv_python, [venv_python] + sys.argv[1:])
elif IS_WINDOWS:
    venv_win = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_win) and sys.executable.lower() != venv_win.lower():
        script = os.path.abspath(__file__) if "__file__" in globals() else sys.argv[0]
        os.execv(venv_win, [venv_win] + sys.argv[1:])

# ==============================================================================
# Rutas de Configuración de Dolphin
# ==============================================================================
def get_dolphin_config_dir_windows():
    """Localiza el directorio de configuración de Dolphin / Slippi en Windows."""
    candidates = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "SlippiOnline" / "Config")
        candidates.append(Path(appdata) / "Slippi Launcher" / "netplay" / "Config")
        candidates.append(Path(appdata) / "Dolphin Emulator" / "Config")
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        candidates.append(Path(userprofile) / "Documents" / "Dolphin Emulator" / "Config")
        candidates.append(Path(userprofile) / "Documents" / "Slippi" / "Config")
    for p in candidates:
        if p.exists():
            return p
    if appdata:
        return Path(appdata) / "SlippiOnline" / "Config"
    return Path.home() / "AppData" / "Roaming" / "SlippiOnline" / "Config"

if IS_LINUX:
    _def_dir = Path("/home/ltar/.config/SlippiOnline/Config")
    DOLPHIN_CONFIG_DIR = _def_dir if _def_dir.exists() else (Path.home() / ".config/SlippiOnline/Config")
else:
    DOLPHIN_CONFIG_DIR = get_dolphin_config_dir_windows()

GCPAD_INI_PATH = DOLPHIN_CONFIG_DIR / "GCPadNew.ini"
DOLPHIN_INI_PATH = DOLPHIN_CONFIG_DIR / "Dolphin.ini"

# ==============================================================================
# LÓGICA EXISTENTE PARA LINUX (INTACTA)
# ==============================================================================
def get_evdev_devices():
    try:
        import evdev
        devices = []
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                devices.append(dev)
            except Exception:
                pass
        return devices
    except ImportError:
        return []

def is_gamepad_or_joystick(dev):
    if IS_WINDOWS:
        name = dev.get("name", "") if isinstance(dev, dict) else str(getattr(dev, "name", dev))
        name_lower = name.lower()
        exclusions = ["touchpad", "trackpoint", "keyboard", "mouse", "virtual device"]
        return not any(ex in name_lower for ex in exclusions)

    name_lower = dev.name.lower()
    
    # 1. Descartar explícitamente periféricos de la laptop, teclados, ratones y botones de sistema
    exclusions = [
        "touchpad", "trackpoint", "synaptics", "elan", "keyboard", "mouse", 
        "extra buttons", "power button", "lid switch", "sleep button", "switch", 
        "headphone", "mic", "hdmi", "video bus", "ydotoold", "virtual device",
        "consumer control", "system control"
    ]
    if any(ex in name_lower for ex in exclusions):
        return False
        
    caps = dev.capabilities()
    import evdev.ecodes as e
    
    # 2. Descartar pantallas táctiles y touchpads (tienen BTN_TOUCH o BTN_TOOL_FINGER)
    if e.EV_KEY in caps:
        keys = caps[e.EV_KEY]
        if e.BTN_TOUCH in keys or e.BTN_TOOL_FINGER in keys:
            return False
            
        # 3. Detectar botones típicos de mandos (Gamepads / Joysticks / Fightsticks)
        gamepad_keys = [
            e.BTN_A, e.BTN_B, e.BTN_X, e.BTN_Y,
            e.BTN_TL, e.BTN_TR, e.BTN_START, e.BTN_SELECT,
            e.BTN_JOYSTICK, e.BTN_TRIGGER, e.BTN_THUMB,
            0x120, 0x121, 0x122, 0x130, 0x131, 0x132
        ]
        if any(k in keys for k in gamepad_keys):
            return True
            
    # 4. Palabras clave explícitas en el nombre
    keywords = ["gamepad", "joystick", "controller", "pad", "xbox", "playstation", "dualshock", "dragonrise", "shanwan"]
    if any(k in name_lower for k in keywords):
        return True
        
    return False

def check_kernel_usb_errors():
    """Revisa si hubo errores recientes de enumeración USB (-71, unable to enumerate)."""
    try:
        out = subprocess.check_output(
            ["journalctl", "-k", "-b", "-n", "30", "--no-pager"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore")
        
        errors = []
        if "error -71" in out or "device descriptor read" in out:
            errors.append("Error -71: Fallo al leer descriptor USB (problema de energía o puerto USB).")
        if "unable to enumerate" in out:
            errors.append("No se pudo enumerar el dispositivo USB.")
        if "Cannot enable. Maybe the USB cable is bad" in out:
            errors.append("El cable USB o puerto físico tiene falso contacto o no entrega energía suficiente.")
        return errors
    except Exception:
        return []

def configure_dolphin_for_gamepad(device_name, is_xinput=False):
    """Escribe la configuración del mando en GCPadNew.ini para el Puerto 2 (Linux o Windows)."""
    if IS_WINDOWS:
        if isinstance(device_name, dict):
            return configure_dolphin_for_gamepad_windows(device_name)
        dev_dict = {
            "name": str(device_name),
            "type": "xinput" if is_xinput else "dinput",
            "index": 0,
            "device_str": "XInput/0/Gamepad" if is_xinput else f"DInput/0/{device_name}"
        }
        return configure_dolphin_for_gamepad_windows(dev_dict)

    DOLPHIN_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    cfg = configparser.ConfigParser()
    if GCPAD_INI_PATH.exists():
        cfg.read(GCPAD_INI_PATH)
        
    section = "GCPad2"
    if not cfg.has_section(section):
        cfg.add_section(section)
        
    # Asignar dispositivo en formato evdev de Dolphin
    dev_str = f"evdev/0/{device_name}"
    cfg.set(section, "Device", dev_str)
    
    # Mapeo limpio y estándar de botones (sin colisiones ni cruces)
    cfg.set(section, "Buttons/A", "`Button 0` | `BtnSouth` | `BtnA` | `X` | `Space`")
    cfg.set(section, "Buttons/B", "`Button 1` | `BtnEast` | `BtnB` | `Z`")
    cfg.set(section, "Buttons/X", "`Button 2` | `BtnWest` | `BtnX` | `C`")
    cfg.set(section, "Buttons/Y", "`Button 3` | `BtnNorth` | `BtnY` | `V`")
    cfg.set(section, "Buttons/Z", "`Button 5` | `BtnTR` | `F`")
    cfg.set(section, "Buttons/Start", "`Button 7` | `Button 9` | `BtnStart` | `Return` | `Enter`")
    
    # Sticks analógicos: Main Stick es EXCLUSIVAMENTE Axis 0 (X) y Axis 1 (Y)
    cfg.set(section, "Main Stick/Up", "`Axis 1-` | `Up` | `W`")
    cfg.set(section, "Main Stick/Down", "`Axis 1+` | `Down` | `S`")
    cfg.set(section, "Main Stick/Left", "`Axis 0-` | `Left` | `A`")
    cfg.set(section, "Main Stick/Right", "`Axis 0+` | `Right` | `D`")
    cfg.set(section, "Main Stick/Modifier", "`Shift_L` | `Shift_R`")
    cfg.set(section, "Main Stick/Calibration", "100.00 141.42 100.00 141.42 100.00 141.42 100.00 141.42")
    cfg.set(section, "Main Stick/Radius", "100")
    
    # C-Stick (Smash) es EXCLUSIVAMENTE Stick Derecho: Axis 3 (X) y Axis 4 (Y)
    # NUNCA debe contener Axis 0 ni Axis 1 para no atacar al intentar avanzar
    cfg.set(section, "C-Stick/Up", "`Axis 4-` | `KP_8` | `Home`")
    cfg.set(section, "C-Stick/Down", "`Axis 4+` | `KP_2` | `End`")
    cfg.set(section, "C-Stick/Left", "`Axis 3-` | `KP_4` | `Delete`")
    cfg.set(section, "C-Stick/Right", "`Axis 3+` | `KP_6` | `Page_Down`")
    cfg.set(section, "C-Stick/Radius", "100")
    
    # Gatillos / Escudo (L y R)
    cfg.set(section, "Triggers/L", "`Button 4` | `BtnTL` | `BtnTL2` | `Axis 2+` | `Q`")
    cfg.set(section, "Triggers/R", "`BtnTR2` | `Axis 5+` | `E`")
    cfg.set(section, "Triggers/Threshold", "50")
    
    # Cruceta / D-Pad (Taunts)
    cfg.set(section, "D-Pad/Up", "`Hat0Y-` | `Button 12` | `KP_Up` | `1`")
    cfg.set(section, "D-Pad/Down", "`Hat0Y+` | `Button 13` | `KP_Down` | `2`")
    cfg.set(section, "D-Pad/Left", "`Hat0X-` | `Button 14` | `KP_Left` | `3`")
    cfg.set(section, "D-Pad/Right", "`Hat0X+` | `Button 15` | `KP_Right` | `4`")
    
    with open(GCPAD_INI_PATH, "w") as f:
        cfg.write(f)
        
    # Asegurar que Dolphin.ini tenga SIDevice1 = 6 (Mando habilitado)
    if DOLPHIN_INI_PATH.exists():
        d_cfg = configparser.ConfigParser()
        d_cfg.read(DOLPHIN_INI_PATH)
        if not d_cfg.has_section("Core"):
            d_cfg.add_section("Core")
        d_cfg.set("Core", "SIDevice1", "6")
        with open(DOLPHIN_INI_PATH, "w") as f:
            d_cfg.write(f)

def test_controller_inputs(dev):
    """Muestra en pantalla los botones y ejes que el usuario va presionando (Linux evdev)."""
    if IS_WINDOWS:
        return test_controller_inputs_windows(dev)

    import evdev
    print("\n" + "=" * 65)
    print(f"  🧪 MODO DE PRUEBA EN VIVO: {dev.name}")
    print("  Presiona cualquier botón o mueve los sticks de tu mando.")
    print("  (Presiona Ctrl+C en cualquier momento para salir)")
    print("=" * 65 + "\n")
    
    try:
        for event in dev.read_loop():
            if event.type == evdev.ecodes.EV_KEY and event.value in [0, 1]:
                state = "🟢 PRESIONADO" if event.value == 1 else "⚪ SOLTADO"
                btn_name = evdev.ecodes.KEY.get(event.code, evdev.ecodes.BTN.get(event.code, f"Code {event.code}"))
                print(f"  [Botón] {btn_name} ({event.code}): {state}")
            elif event.type == evdev.ecodes.EV_ABS and abs(event.value) > 2000:
                axis_name = evdev.ecodes.ABS.get(event.code, f"Axis {event.code}")
                print(f"  [Eje/Stick] {axis_name} ({event.code}): valor = {event.value}")
    except KeyboardInterrupt:
        print("\nPrueba terminada.")

def main_linux():
    print("=" * 70)
    print("  🎮 DETECTOR Y CONFIGURADOR DE MANDOS (GAMEPADS) EN LINUX")
    print("=" * 70)
    
    try:
        import evdev
    except ImportError:
        print("❌ Error: Se requiere el paquete 'evdev' para leer mandos en Linux.")
        print("   Instálalo con: pip install evdev")
        return

    devices = get_evdev_devices()
    gamepads = [d for d in devices if is_gamepad_or_joystick(d)]
    
    if gamepads:
        print(f"\n✅ ¡Se encontró {len(gamepads)} mando(s) reconocido(s) por el sistema!\n")
        for i, gp in enumerate(gamepads, 1):
            print(f"  [{i}] {gp.name}  -->  {gp.path}")
            
        selected_gp = gamepads[0]
        print(f"\n⚙️ Configurando automáticamente '{selected_gp.name}' en Dolphin (Puerto 2)...")
        configure_dolphin_for_gamepad(selected_gp.name)
        print("✅ ¡Configuración guardada en GCPadNew.ini con éxito!")
        print("🎮 Ahora el Puerto 2 responderá directamente a este mando.")
        
        test = input("\n¿Deseas probar los botones del mando ahora en pantalla? [s/N]: ").strip().lower()
        if test == 's':
            test_controller_inputs(selected_gp)
        return
        
    # Si no se detectó ningún mando, analizar el porqué:
    print("\n🔍 Analizando estado del bus USB y hardware...")
    errors = check_kernel_usb_errors()
    
    if errors:
        print("\n⚠️  EL KERNEL DE LINUX DETECTÓ UN PROBLEMA AL CONECTAR EL MANDO:")
        for err in errors:
            print(f"   ❌ {err}")
            
        print("\n" + "-" * 70)
        print("🛠️  CÓMO SOLUCIONARLO EN 3 PASOS:")
        print("-" * 70)
        print("1. 🔌 CAMBIA DE PUERTO USB DIRECTO:")
        print("   Si conectaste el mando a un HUB USB (ladrón de puertos), desconéctalo")
        print("   y conéctalo DIRECTAMENTE a un puerto USB de la laptop ThinkPad.")
        print("   (Prueba en el puerto USB del otro lado del portátil).")
        print()
        print("2. 🕹️ MODO XINPUT / DINPUT (BOTÓN HOME / MODE):")
        print("   La mayoría de mandos genéricos tienen un botón central (HOME, MODE")
        print("   o botón con logo). Mantén presionado ese botón durante 5 a 10 segundos")
        print("   para que cambie de modo (XInput <-> DirectInput).")
        print()
        print("3. 🪢 VERIFICA EL CABLE / CONECTOR:")
        print("   Empuja el conector USB firmemente hasta el fondo para asegurar")
        print("   que los 4 pines de datos hagan buen contacto.")
        print("-" * 70)
    else:
        print("\nℹ️  No hay mandos conectados actualmente o el sistema no ha recibido señal.")
        print("   Conecta tu mando genérico a un puerto USB directo del equipo.")
        
    print("\n⏳ Esperando a que conectes o cambies de puerto el mando...")
    print("   (Conéctalo ahora, esta ventana lo detectará automáticamente...)")
    
    last_dev_paths = set(d.path for d in devices)
    try:
        for _ in range(60): # Esperar hasta 60 segundos
            time.sleep(1)
            cur_devices = get_evdev_devices()
            cur_paths = set(d.path for d in cur_devices)
            new_paths = cur_paths - last_dev_paths
            
            for path in new_paths:
                try:
                    dev = evdev.InputDevice(path)
                    print(f"\n🎉 ¡NUEVO DISPOSITIVO DETECTADO!: {dev.name} ({dev.path})")
                    if is_gamepad_or_joystick(dev):
                        print("🎮 ¡Es un mando de juego válido!")
                        configure_dolphin_for_gamepad(dev.name)
                        print("✅ ¡Configurado automáticamente para Dolphin y Melee!")
                        test = input("\n¿Deseas probar los botones ahora? [s/N]: ").strip().lower()
                        if test == 's':
                            test_controller_inputs(dev)
                        return
                    else:
                        print("   (Dispositivo detectado, verificando compatibilidad...)")
                except Exception:
                    pass
            last_dev_paths = cur_paths
    except KeyboardInterrupt:
        print("\nCancelado.")
        
    print("\nSi sigues teniendo problemas, recuerda que también puedes jugar usando")
    print("tu teclado con las teclas W/A/S/D o Flechas de forma inmediata.")

# ==============================================================================
# NUEVAS FUNCIONES PARA WINDOWS (XInput / DirectInput / WinMM)
# ==============================================================================
def get_windows_gamepads():
    """
    Detecta mandos de juego en Windows mediante APIs nativas (XInput y WinMM)
    o pygame si está instalado. Devuelve una lista de diccionarios descriptivos.
    """
    gamepads = []
    seen_names = set()

    # 1. Detección mediante pygame si está disponible
    try:
        import pygame
        pygame.init()
        pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            try:
                joy = pygame.joystick.Joystick(i)
                joy.init()
                name = joy.get_name()
                is_xin = "xinput" in name.lower() or "xbox" in name.lower()
                dev_str = f"XInput/{i}/Gamepad" if is_xin else f"DInput/{i}/{name}"
                info = {
                    "name": name,
                    "type": "xinput" if is_xin else "dinput",
                    "index": i,
                    "device_str": dev_str,
                    "backend": "pygame"
                }
                gamepads.append(info)
                seen_names.add(name)
            except Exception:
                pass
        if gamepads:
            return gamepads
    except Exception:
        pass

    # 2. Detección nativa XInput mediante ctypes
    try:
        import ctypes
        xinput_dll = None
        for dll_name in ["xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"]:
            try:
                xinput_dll = ctypes.windll.LoadLibrary(dll_name)
                break
            except OSError:
                continue

        if xinput_dll and hasattr(xinput_dll, "XInputGetState"):
            class XINPUT_GAMEPAD(ctypes.Structure):
                _fields_ = [
                    ("wButtons", ctypes.c_ushort),
                    ("bLeftTrigger", ctypes.c_ubyte),
                    ("bRightTrigger", ctypes.c_ubyte),
                    ("sThumbLX", ctypes.c_short),
                    ("sThumbLY", ctypes.c_short),
                    ("sThumbRX", ctypes.c_short),
                    ("sThumbRY", ctypes.c_short),
                ]
            class XINPUT_STATE(ctypes.Structure):
                _fields_ = [
                    ("dwPacketNumber", ctypes.c_ulong),
                    ("Gamepad", XINPUT_GAMEPAD),
                ]

            for user_idx in range(4):
                state = XINPUT_STATE()
                res = xinput_dll.XInputGetState(user_idx, ctypes.byref(state))
                if res == 0:  # ERROR_SUCCESS
                    name = f"Mando XInput / Xbox (Ranura {user_idx + 1})"
                    gamepads.append({
                        "name": name,
                        "type": "xinput",
                        "index": user_idx,
                        "device_str": f"XInput/{user_idx}/Gamepad",
                        "backend": "xinput_native"
                    })
                    seen_names.add(name)
    except Exception:
        pass

    # 3. Detección nativa DirectInput / Joysticks USB mediante winmm.dll
    try:
        import ctypes
        winmm = ctypes.windll.winmm
        class JOYCAPSW(ctypes.Structure):
            _fields_ = [
                ("wMid", ctypes.c_ushort),
                ("wPid", ctypes.c_ushort),
                ("szPname", ctypes.c_wchar * 32),
                ("wXmin", ctypes.c_uint),
                ("wXmax", ctypes.c_uint),
                ("wYmin", ctypes.c_uint),
                ("wYmax", ctypes.c_uint),
                ("wZmin", ctypes.c_uint),
                ("wZmax", ctypes.c_uint),
                ("wNumButtons", ctypes.c_uint),
                ("wPeriodMin", ctypes.c_uint),
                ("wPeriodMax", ctypes.c_uint),
                ("wRmin", ctypes.c_uint),
                ("wRmax", ctypes.c_uint),
                ("wUmin", ctypes.c_uint),
                ("wUmax", ctypes.c_uint),
                ("wVmin", ctypes.c_uint),
                ("wVmax", ctypes.c_uint),
                ("wCaps", ctypes.c_uint),
                ("wMaxAxes", ctypes.c_uint),
                ("wNumAxes", ctypes.c_uint),
                ("wMaxButtons", ctypes.c_uint),
                ("szRegKey", ctypes.c_wchar * 32),
                ("szOEMVxD", ctypes.c_wchar * 260),
            ]
        class JOYINFOEX(ctypes.Structure):
            _fields_ = [
                ("dwSize", ctypes.c_uint),
                ("dwFlags", ctypes.c_uint),
                ("dwXpos", ctypes.c_uint),
                ("dwYpos", ctypes.c_uint),
                ("dwZpos", ctypes.c_uint),
                ("dwRpos", ctypes.c_uint),
                ("dwUpos", ctypes.c_uint),
                ("dwVpos", ctypes.c_uint),
                ("dwButtons", ctypes.c_uint),
                ("dwButtonNumber", ctypes.c_uint),
                ("dwPOV", ctypes.c_uint),
                ("dwReserved1", ctypes.c_uint),
                ("dwReserved2", ctypes.c_uint),
            ]

        num_devs = winmm.joyGetNumDevs()
        for i in range(min(num_devs, 16)):
            caps = JOYCAPSW()
            if winmm.joyGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps)) == 0:
                pji = JOYINFOEX()
                pji.dwSize = ctypes.sizeof(pji)
                pji.dwFlags = 0xFF
                if winmm.joyGetPosEx(i, ctypes.byref(pji)) == 0:
                    dev_name = caps.szPname.strip() or f"Joystick Genérico USB {i}"
                    if dev_name not in seen_names:
                        gamepads.append({
                            "name": dev_name,
                            "type": "dinput",
                            "index": i,
                            "device_str": f"DInput/{i}/{dev_name}",
                            "backend": "winmm_native"
                        })
                        seen_names.add(dev_name)
    except Exception:
        pass

    return gamepads

def check_windows_usb_errors():
    """Revisa si Windows reporta periféricos USB / HID en estado de error o degradado."""
    errors = []
    try:
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "Get-PnpDevice -Class 'USB','HIDClass' | Where-Object { $_.Status -ne 'OK' } | Select-Object -ExpandProperty FriendlyName"
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=5).decode("utf-8", errors="ignore").strip()
        if out:
            for line in out.splitlines():
                line = line.strip()
                if line:
                    errors.append(f"Dispositivo con advertencia de controlador o conexión: {line}")
    except Exception:
        pass
    return errors

def configure_dolphin_for_gamepad_windows(gamepad_info):
    """Escribe la configuración del mando en GCPadNew.ini para el Puerto 2 en Windows."""
    DOLPHIN_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = configparser.ConfigParser()
    if GCPAD_INI_PATH.exists():
        cfg.read(GCPAD_INI_PATH)

    section = "GCPad2"
    if not cfg.has_section(section):
        cfg.add_section(section)

    is_xinput = (gamepad_info.get("type") == "xinput")
    dev_str = gamepad_info.get("device_str", "XInput/0/Gamepad" if is_xinput else "DInput/0/Gamepad")
    cfg.set(section, "Device", dev_str)

    if is_xinput:
        cfg.set(section, "Buttons/A", "`Button A` | `Button 0` | `X` | `Space`")
        cfg.set(section, "Buttons/B", "`Button B` | `Button 1` | `Z`")
        cfg.set(section, "Buttons/X", "`Button X` | `Button 2` | `C`")
        cfg.set(section, "Buttons/Y", "`Button Y` | `Button 3` | `V`")
        cfg.set(section, "Buttons/Z", "`Shoulder R` | `Button 5` | `F`")
        cfg.set(section, "Buttons/Start", "`Start` | `Button 7` | `Return`")
        cfg.set(section, "Main Stick/Up", "`Left Y+` | `Up` | `W`")
        cfg.set(section, "Main Stick/Down", "`Left Y-` | `Down` | `S`")
        cfg.set(section, "Main Stick/Left", "`Left X-` | `Left` | `A`")
        cfg.set(section, "Main Stick/Right", "`Left X+` | `Right` | `D`")
        cfg.set(section, "Main Stick/Modifier", "`Shift`")
        cfg.set(section, "Main Stick/Calibration", "100.00 141.42 100.00 141.42 100.00 141.42 100.00 141.42")
        cfg.set(section, "Main Stick/Radius", "100")
        cfg.set(section, "C-Stick/Up", "`Right Y+`")
        cfg.set(section, "C-Stick/Down", "`Right Y-`")
        cfg.set(section, "C-Stick/Left", "`Right X-`")
        cfg.set(section, "C-Stick/Right", "`Right X+`")
        cfg.set(section, "C-Stick/Radius", "100")
        cfg.set(section, "Triggers/L", "`Trigger L` | `Button 4` | `Q`")
        cfg.set(section, "Triggers/R", "`Trigger R` | `Button 5` | `E`")
        cfg.set(section, "Triggers/Threshold", "50")
        cfg.set(section, "D-Pad/Up", "`Pad N` | `Up`")
        cfg.set(section, "D-Pad/Down", "`Pad S` | `Down`")
        cfg.set(section, "D-Pad/Left", "`Pad W` | `Left`")
        cfg.set(section, "D-Pad/Right", "`Pad E` | `Right`")
    else:
        cfg.set(section, "Buttons/A", "`Button 0` | `X` | `Space`")
        cfg.set(section, "Buttons/B", "`Button 1` | `Z`")
        cfg.set(section, "Buttons/X", "`Button 2` | `C`")
        cfg.set(section, "Buttons/Y", "`Button 3` | `V`")
        cfg.set(section, "Buttons/Z", "`Button 5` | `F`")
        cfg.set(section, "Buttons/Start", "`Button 7` | `Button 9` | `Return`")
        cfg.set(section, "Main Stick/Up", "`Axis 1-` | `Up` | `W`")
        cfg.set(section, "Main Stick/Down", "`Axis 1+` | `Down` | `S`")
        cfg.set(section, "Main Stick/Left", "`Axis 0-` | `Left` | `A`")
        cfg.set(section, "Main Stick/Right", "`Axis 0+` | `Right` | `D`")
        cfg.set(section, "Main Stick/Modifier", "`Shift`")
        cfg.set(section, "Main Stick/Calibration", "100.00 141.42 100.00 141.42 100.00 141.42 100.00 141.42")
        cfg.set(section, "Main Stick/Radius", "100")
        cfg.set(section, "C-Stick/Up", "`Axis 4-` | `KP_8`")
        cfg.set(section, "C-Stick/Down", "`Axis 4+` | `KP_2`")
        cfg.set(section, "C-Stick/Left", "`Axis 3-` | `KP_4`")
        cfg.set(section, "C-Stick/Right", "`Axis 3+` | `KP_6`")
        cfg.set(section, "C-Stick/Radius", "100")
        cfg.set(section, "Triggers/L", "`Button 4` | `Axis 2+` | `Q`")
        cfg.set(section, "Triggers/R", "`Button 6` | `Axis 5+` | `E`")
        cfg.set(section, "Triggers/Threshold", "50")
        cfg.set(section, "D-Pad/Up", "`Hat0Y-` | `Up`")
        cfg.set(section, "D-Pad/Down", "`Hat0Y+` | `Down`")
        cfg.set(section, "D-Pad/Left", "`Hat0X-` | `Left`")
        cfg.set(section, "D-Pad/Right", "`Hat0X+` | `Right`")

    with open(GCPAD_INI_PATH, "w") as f:
        cfg.write(f)

    if DOLPHIN_INI_PATH.exists():
        d_cfg = configparser.ConfigParser()
        d_cfg.read(DOLPHIN_INI_PATH)
        if not d_cfg.has_section("Core"):
            d_cfg.add_section("Core")
        d_cfg.set("Core", "SIDevice1", "6")
        with open(DOLPHIN_INI_PATH, "w") as f:
            d_cfg.write(f)

def test_controller_inputs_windows(gamepad_info):
    """Muestra en pantalla los botones y ejes que el usuario va presionando en Windows."""
    name = gamepad_info.get("name", "Mando Windows")
    backend = gamepad_info.get("backend", "nativo")
    print("\n" + "=" * 65)
    print(f"  🧪 MODO DE PRUEBA EN VIVO (WINDOWS): {name} ({backend})")
    print("  Presiona cualquier botón o mueve los sticks de tu mando.")
    print("  (Presiona Ctrl+C en cualquier momento para salir)")
    print("=" * 65 + "\n")

    # 1. Si pygame está disponible
    if backend == "pygame":
        try:
            import pygame
            idx = gamepad_info.get("index", 0)
            joy = pygame.joystick.Joystick(idx)
            joy.init()
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.JOYBUTTONDOWN:
                        print(f"  [Botón] Botón {event.button}: 🟢 PRESIONADO")
                    elif event.type == pygame.JOYBUTTONUP:
                        print(f"  [Botón] Botón {event.button}: ⚪ SOLTADO")
                    elif event.type == pygame.JOYAXISMOTION and abs(event.value) > 0.2:
                        print(f"  [Eje/Stick] Eje {event.axis}: valor = {event.value:.2f}")
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\nPrueba terminada.")
            return
        except Exception:
            pass

    # 2. XInput nativo
    if gamepad_info.get("type") == "xinput":
        try:
            import ctypes
            xinput_dll = None
            for dll_name in ["xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"]:
                try:
                    xinput_dll = ctypes.windll.LoadLibrary(dll_name)
                    break
                except OSError:
                    continue

            class XINPUT_GAMEPAD(ctypes.Structure):
                _fields_ = [
                    ("wButtons", ctypes.c_ushort),
                    ("bLeftTrigger", ctypes.c_ubyte),
                    ("bRightTrigger", ctypes.c_ubyte),
                    ("sThumbLX", ctypes.c_short),
                    ("sThumbLY", ctypes.c_short),
                    ("sThumbRX", ctypes.c_short),
                    ("sThumbRY", ctypes.c_short),
                ]
            class XINPUT_STATE(ctypes.Structure):
                _fields_ = [
                    ("dwPacketNumber", ctypes.c_ulong),
                    ("Gamepad", XINPUT_GAMEPAD),
                ]

            user_idx = gamepad_info.get("index", 0)
            last_buttons = 0
            while True:
                state = XINPUT_STATE()
                if xinput_dll.XInputGetState(user_idx, ctypes.byref(state)) == 0:
                    btns = state.Gamepad.wButtons
                    diff = btns ^ last_buttons
                    if diff != 0:
                        for bit in range(16):
                            mask = 1 << bit
                            if diff & mask:
                                state_str = "🟢 PRESIONADO" if (btns & mask) else "⚪ SOLTADO"
                                print(f"  [Botón XInput] Bit {bit} (0x{mask:04X}): {state_str}")
                        last_buttons = btns
                    lx = state.Gamepad.sThumbLX
                    ly = state.Gamepad.sThumbLY
                    if abs(lx) > 8000 or abs(ly) > 8000:
                        print(f"  [Stick Principal] X={lx}, Y={ly}")
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\nPrueba terminada.")
            return
        except Exception:
            pass

    # 3. DirectInput nativo vía WinMM
    try:
        import ctypes
        winmm = ctypes.windll.winmm
        class JOYINFOEX(ctypes.Structure):
            _fields_ = [
                ("dwSize", ctypes.c_uint),
                ("dwFlags", ctypes.c_uint),
                ("dwXpos", ctypes.c_uint),
                ("dwYpos", ctypes.c_uint),
                ("dwZpos", ctypes.c_uint),
                ("dwRpos", ctypes.c_uint),
                ("dwUpos", ctypes.c_uint),
                ("dwVpos", ctypes.c_uint),
                ("dwButtons", ctypes.c_uint),
                ("dwButtonNumber", ctypes.c_uint),
                ("dwPOV", ctypes.c_uint),
                ("dwReserved1", ctypes.c_uint),
                ("dwReserved2", ctypes.c_uint),
            ]
        uJoyID = gamepad_info.get("index", 0)
        last_btns = 0
        while True:
            pji = JOYINFOEX()
            pji.dwSize = ctypes.sizeof(pji)
            pji.dwFlags = 0xFF
            if winmm.joyGetPosEx(uJoyID, ctypes.byref(pji)) == 0:
                diff = pji.dwButtons ^ last_btns
                if diff != 0:
                    for b in range(32):
                        mask = 1 << b
                        if diff & mask:
                            s = "🟢 PRESIONADO" if (pji.dwButtons & mask) else "⚪ SOLTADO"
                            print(f"  [Botón DInput] Botón {b + 1}: {s}")
                    last_btns = pji.dwButtons
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nPrueba terminada.")

def main_windows():
    print("=" * 70)
    print("  🎮 DETECTOR Y CONFIGURADOR DE MANDOS (GAMEPADS) EN WINDOWS")
    print("=" * 70)

    gamepads = get_windows_gamepads()

    if gamepads:
        print(f"\n✅ ¡Se encontró {len(gamepads)} mando(s) reconocido(s) por Windows!\n")
        for i, gp in enumerate(gamepads, 1):
            print(f"  [{i}] {gp['name']}  -->  {gp['device_str']} ({gp['type'].upper()})")

        selected_gp = gamepads[0]
        print(f"\n⚙️ Configurando automáticamente '{selected_gp['name']}' en Dolphin (Puerto 2)...")
        configure_dolphin_for_gamepad_windows(selected_gp)
        print("✅ ¡Configuración guardada en GCPadNew.ini con éxito!")
        print("🎮 Ahora el Puerto 2 responderá directamente a este mando en Dolphin.")

        test = input("\n¿Deseas probar los botones del mando ahora en pantalla? [s/N]: ").strip().lower()
        if test == 's':
            test_controller_inputs_windows(selected_gp)
        return

    # Si no se detectó ningún mando en Windows:
    print("\n🔍 Analizando estado de dispositivos USB e HID en Windows...")
    errors = check_windows_usb_errors()

    if errors:
        print("\n⚠️  WINDOWS REPORTA ADVERTENCIAS EN LOS DISPOSITIVOS CONECTADOS:")
        for err in errors:
            print(f"   ❌ {err}")

        print("\n" + "-" * 70)
        print("🛠️  CÓMO SOLUCIONARLO EN WINDOWS:")
        print("-" * 70)
        print("1. 🔌 CAMBIA DE PUERTO USB DIRECTO:")
        print("   Conecta el mando directamente al puerto USB de la placa base/laptop.")
        print("2. 🕹️ MODO XINPUT / DINPUT (BOTÓN HOME / MODE):")
        print("   Mantén presionado el botón central (HOME/MODE) durante 5 a 10 segundos")
        print("   para que cambie entre modo DirectInput y XInput.")
        print("3. ⚙️ ADMINISTRADOR DE DISPOSITIVOS:")
        print("   Revisa 'Dispositivos de juego compatibles con HID' o 'Controladores de bus serie universal'.")
        print("-" * 70)
    else:
        print("\nℹ️  No hay mandos conectados actualmente o el sistema no ha recibido señal.")
        print("   Conecta tu mando USB o sincronízalo por Bluetooth.")

    print("\n⏳ Esperando a que conectes el mando...")
    print("   (Conéctalo ahora, esta ventana lo detectará automáticamente...)")

    try:
        for _ in range(60):
            time.sleep(1)
            cur_gamepads = get_windows_gamepads()
            if cur_gamepads:
                gp = cur_gamepads[0]
                print(f"\n🎉 ¡NUEVO MANDO DETECTADO!: {gp['name']} ({gp['device_str']})")
                configure_dolphin_for_gamepad_windows(gp)
                print("✅ ¡Configurado automáticamente para Dolphin y Melee!")
                test = input("\n¿Deseas probar los botones ahora? [s/N]: ").strip().lower()
                if test == 's':
                    test_controller_inputs_windows(gp)
                return
    except KeyboardInterrupt:
        print("\nCancelado.")

    print("\nRecuerda que también puedes jugar usando tu teclado con las teclas W/A/S/D")
    print("o Flechas de forma inmediata.")

def main():
    if IS_WINDOWS:
        main_windows()
    else:
        main_linux()

if __name__ == "__main__":
    main()
