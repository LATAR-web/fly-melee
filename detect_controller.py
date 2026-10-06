#!/usr/bin/env python3
"""
Detector y Configurador Automático de Mandos / Gamepads para Dolphin y Melee
Detecta cualquier mando genérico USB/Bluetooth, diagnostica problemas de conexión
y genera la configuración GCPadNew.ini para el Puerto 2 (Jugador Humano).
"""
import os
import sys

try:
    import evdev
except ImportError:
    venv_python = "/home/ltar/.venvs/pytorch/bin/python"
    if os.path.exists(venv_python) and sys.executable != venv_python:
        script = os.path.abspath(__file__) if "__file__" in globals() else sys.argv[0]
        os.execv(venv_python, [venv_python, script] + sys.argv[1:])

import time
import subprocess
import configparser
from pathlib import Path

DOLPHIN_CONFIG_DIR = Path("/home/ltar/.config/SlippiOnline/Config")
GCPAD_INI_PATH = DOLPHIN_CONFIG_DIR / "GCPadNew.ini"
DOLPHIN_INI_PATH = DOLPHIN_CONFIG_DIR / "Dolphin.ini"

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
    """Escribe la configuración del mando en GCPadNew.ini para el Puerto 2."""
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
    
    # Mapeo estándar de botones para mandos genéricos USB (DInput y XInput)
    cfg.set(section, "Buttons/A", "`Button 0` | `Button 2` | `BtnSouth` | `BtnA` | `X` | `Space`")
    cfg.set(section, "Buttons/B", "`Button 1` | `Button 3` | `BtnEast` | `BtnB` | `Z`")
    cfg.set(section, "Buttons/X", "`Button 2` | `Button 0` | `BtnWest` | `BtnX` | `C`")
    cfg.set(section, "Buttons/Y", "`Button 3` | `Button 1` | `BtnNorth` | `BtnY` | `V`")
    cfg.set(section, "Buttons/Z", "`Button 4` | `Button 5` | `BtnTR` | `BtnR` | `F`")
    cfg.set(section, "Buttons/Start", "`Button 7` | `Button 9` | `BtnStart` | `Return`")
    
    # Sticks analógicos (Axis 0 = X, Axis 1 = Y)
    cfg.set(section, "Main Stick/Up", "`Axis 1-` | `Up` | `W`")
    cfg.set(section, "Main Stick/Down", "`Axis 1+` | `Down` | `S`")
    cfg.set(section, "Main Stick/Left", "`Axis 0-` | `Left` | `A`")
    cfg.set(section, "Main Stick/Right", "`Axis 0+` | `Right` | `D`")
    cfg.set(section, "Main Stick/Modifier", "`Shift_L` | `Shift_R`")
    cfg.set(section, "Main Stick/Calibration", "100.00 141.42 100.00 141.42 100.00 141.42 100.00 141.42")
    cfg.set(section, "Main Stick/Radius", "100")
    
    # C-Stick (Smash) para mando analógico derecho
    cfg.set(section, "C-Stick/Up", "`Axis 3-` | `Axis 4-` | `Axis 2-`")
    cfg.set(section, "C-Stick/Down", "`Axis 3+` | `Axis 4+` | `Axis 2+`")
    cfg.set(section, "C-Stick/Left", "`Axis 2-` | `Axis 3-` | `Axis 0-`")
    cfg.set(section, "C-Stick/Right", "`Axis 2+` | `Axis 3+` | `Axis 0+`")
    cfg.set(section, "C-Stick/Radius", "100")
    
    # Gatillos / Escudo (L y R)
    cfg.set(section, "Triggers/L", "`Button 4` | `Button 6` | `BtnTL` | `Axis 2+` | `Axis 5+` | `Q`")
    cfg.set(section, "Triggers/R", "`Button 5` | `Button 7` | `BtnTR` | `Axis 5+` | `Axis 4+` | `E`")
    cfg.set(section, "Triggers/Threshold", "50")
    
    # Cruceta / D-Pad
    cfg.set(section, "D-Pad/Up", "`Button 12` | `Axis 5-` | `Axis 7-` | `Hat0Y-` | `T`")
    cfg.set(section, "D-Pad/Down", "`Button 13` | `Axis 5+` | `Axis 7+` | `Hat0Y+` | `G`")
    cfg.set(section, "D-Pad/Left", "`Button 14` | `Axis 4-` | `Axis 6-` | `Hat0X-` | `F`")
    cfg.set(section, "D-Pad/Right", "`Button 15` | `Axis 4+` | `Axis 6+` | `Hat0X+` | `H`")
    
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
    """Muestra en pantalla los botones y ejes que el usuario va presionando."""
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

def main():
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

if __name__ == "__main__":
    main()
