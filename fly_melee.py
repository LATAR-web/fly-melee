#!/usr/bin/env python3
"""
Fly Melee Bridge - Mosca (P1 - Luigi/Fox) vs Jugador Humano (P2 - Tú)
- Puerto 1: Controlado por el conectoma biológico de la mosca (395,144 neuronas). Elige a LUIGI (Wavedash SSS & Shoryuken) o FOX.
- Puerto 2: JUGADOR HUMANO (Tú). Elige cualquier personaje y lucha directamente contra la mosca.
- Visualización dual en tiempo real: Dolphin 60 FPS en pantalla + WebGL 3D en http://localhost:8085.
"""
import sys
import os

try:
    import numpy as np
    import melee
except ImportError:
    venv_python = "/home/ltar/.venvs/pytorch/bin/python"
    if os.path.exists(venv_python) and sys.executable != venv_python:
        script = os.path.abspath(__file__) if "__file__" in globals() else sys.argv[0]
        os.execv(venv_python, [venv_python, script] + sys.argv[1:])
    raise

import time
import json
import math
import queue
import argparse
import threading
import subprocess
import configparser
import http.client
import urllib.request
from fly_brain import FlyBrain

DEFAULT_ISO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "games", "ssbm.iso")
DOLPHIN_HOME = os.path.expanduser("~/.config/SlippiOnline")
DASHBOARD_URL = "http://127.0.0.1:8085/api/push_state"

class TelemetryClient:
    """Cliente de telemetría HTTP persistente y asíncrono con 1 hilo y cola no-bloqueante (0 lag a 60 FPS)."""
    def __init__(self, host="127.0.0.1", port=8085):
        self.host = host
        self.port = port
        self.queue = queue.Queue(maxsize=1)
        self.running = True
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def send(self, data):
        """Descarta frames obsoletos inmediatamente si la cola está llena, protegiendo los 60 FPS de Dolphin."""
        try:
            self.queue.put_nowait(data)
        except queue.Full:
            pass

    def _run(self):
        conn = None
        while self.running:
            try:
                data = self.queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                body = json.dumps(data).encode("utf-8")
                headers = {
                    "Content-Type": "application/json",
                    "Content-Length": str(len(body)),
                    "Connection": "keep-alive"
                }
                if conn is None:
                    conn = http.client.HTTPConnection(self.host, self.port, timeout=0.15)
                conn.request("POST", "/api/push_state", body=body, headers=headers)
                resp = conn.getresponse()
                resp.read() # Reutilizar la misma conexión TCP Keep-Alive
            except Exception:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass
                conn = None
                time.sleep(0.04)

    def close(self):
        self.running = False

def setup_human_and_bot_controllers(home_path, cpu_mode=False):
    """Configura Dolphin para que el Puerto 1 sea la Mosca y el Puerto 2 sea el Jugador Humano o Bot CPU."""
    config_dir = os.path.join(home_path, "Config")
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(os.path.join(home_path, "Pipes"), exist_ok=True)

    # 1. Configurar Dolphin.ini: SIDevice0 = 6 (Bot), SIDevice1 = 0 si CPU o 6 si Humano, Fullscreen = False
    dolphin_ini_path = os.path.join(config_dir, "Dolphin.ini")
    d_cfg = configparser.ConfigParser()
    d_cfg.read(dolphin_ini_path)
    if not d_cfg.has_section("Core"):
        d_cfg.add_section("Core")
    d_cfg.set("Core", "SIDevice0", "6")  # Port 1: Bot estándar (Pipe)
    d_cfg.set("Core", "SIDevice1", "0" if cpu_mode else "6")  # Port 2: CPU (sin mando externo) o Humano
    d_cfg.set("Core", "SIDevice2", "0")
    d_cfg.set("Core", "SIDevice3", "0")

    if not d_cfg.has_section("Display"):
        d_cfg.add_section("Display")
    d_cfg.set("Display", "Fullscreen", "False")
    d_cfg.set("Display", "RenderToMain", "False")
    d_cfg.set("Display", "RenderWindowWidth", "960")
    d_cfg.set("Display", "RenderWindowHeight", "720")

    if not d_cfg.has_section("Input"):
        d_cfg.add_section("Input")
    d_cfg.set("Input", "BackgroundInput", "True")

    with open(dolphin_ini_path, "w") as f:
        d_cfg.write(f)

    # 2. Configurar GCPadNew.ini
    g_ini_path = os.path.join(config_dir, "GCPadNew.ini")
    g_cfg = configparser.ConfigParser()
    g_cfg.read(g_ini_path)

    # Puerto 1: Pipe para la mosca (slippibot1)
    if not g_cfg.has_section("GCPad1"):
        g_cfg.add_section("GCPad1")
    g_cfg.set("GCPad1", "Device", "Pipe/0/slippibot1")
    g_cfg.set("GCPad1", "Buttons/A", "Button A")
    g_cfg.set("GCPad1", "Buttons/B", "Button B")
    g_cfg.set("GCPad1", "Buttons/X", "Button X")
    g_cfg.set("GCPad1", "Buttons/Y", "Button Y")
    g_cfg.set("GCPad1", "Buttons/Z", "Button Z")
    g_cfg.set("GCPad1", "Buttons/L", "Button L")
    g_cfg.set("GCPad1", "Buttons/R", "Button R")
    g_cfg.set("GCPad1", "Buttons/Start", "Button START")
    g_cfg.set("GCPad1", "Main Stick/Up", "Axis MAIN Y +")
    g_cfg.set("GCPad1", "Main Stick/Down", "Axis MAIN Y -")
    g_cfg.set("GCPad1", "Main Stick/Left", "Axis MAIN X -")
    g_cfg.set("GCPad1", "Main Stick/Right", "Axis MAIN X +")
    g_cfg.set("GCPad1", "C-Stick/Up", "Axis C Y +")
    g_cfg.set("GCPad1", "C-Stick/Down", "Axis C Y -")
    g_cfg.set("GCPad1", "C-Stick/Left", "Axis C X -")
    g_cfg.set("GCPad1", "C-Stick/Right", "Axis C X +")
    g_cfg.set("GCPad1", "Triggers/L", "Button L")
    g_cfg.set("GCPad1", "Triggers/R", "Button R")
    g_cfg.set("GCPad1", "Triggers/Threshold", "90")
    g_cfg.set("GCPad1", "Main Stick/Radius", "100")
    g_cfg.set("GCPad1", "C-Stick/Radius", "100")

    # Puerto 2: Jugador Humano (Auto-detectar Gamepad USB si está conectado, o Teclado)
    gamepad_device_name = None
    try:
        import evdev
        from detect_controller import is_gamepad_or_joystick
        for p in evdev.list_devices():
            try:
                d = evdev.InputDevice(p)
                if is_gamepad_or_joystick(d):
                    gamepad_device_name = d.name
                    break
            except Exception:
                pass
    except Exception:
        pass

    if gamepad_device_name:
        print(f"🎮 ¡Mando USB detectado automáticamente para P2: '{gamepad_device_name}'!")
        from detect_controller import configure_dolphin_for_gamepad
        configure_dolphin_for_gamepad(gamepad_device_name)
    else:
        # Fallback a Teclado (sin colisiones ni drift: WASD/Flechas, Z/K, X/Space/J, C/U, V/I, Q/L, Return)
        if not g_cfg.has_section("GCPad2"):
            g_cfg.add_section("GCPad2")
        g_cfg.set("GCPad2", "Device", "XInput2/0/Virtual core pointer")
        g_cfg.set("GCPad2", "Buttons/A", "`J` | `X` | `space` | `Space`")
        g_cfg.set("GCPad2", "Buttons/B", "`K` | `Z`")
        g_cfg.set("GCPad2", "Buttons/X", "`U` | `C`")
        g_cfg.set("GCPad2", "Buttons/Y", "`I` | `V`")
        g_cfg.set("GCPad2", "Buttons/Z", "`O` | `F`")
        g_cfg.set("GCPad2", "Buttons/Start", "`Return` | `Enter`")
        g_cfg.set("GCPad2", "Main Stick/Up", "`Up` | `W`")
        g_cfg.set("GCPad2", "Main Stick/Down", "`Down` | `S`")
        g_cfg.set("GCPad2", "Main Stick/Left", "`Left` | `A`")
        g_cfg.set("GCPad2", "Main Stick/Right", "`Right` | `D`")
        g_cfg.set("GCPad2", "Main Stick/Modifier", "`Shift_L` | `Shift_R`")
        g_cfg.set("GCPad2", "Main Stick/Calibration", "100.00 141.42 100.00 141.42 100.00 141.42 100.00 141.42")
        g_cfg.set("GCPad2", "Main Stick/Radius", "100")
        g_cfg.set("GCPad2", "C-Stick/Up", "`KP_8` | `Home`")
        g_cfg.set("GCPad2", "C-Stick/Down", "`KP_2` | `End`")
        g_cfg.set("GCPad2", "C-Stick/Left", "`KP_4` | `Delete`")
        g_cfg.set("GCPad2", "C-Stick/Right", "`KP_6` | `Page_Down`")
        g_cfg.set("GCPad2", "C-Stick/Radius", "100")
        g_cfg.set("GCPad2", "Triggers/L", "`L` | `Q`")
        g_cfg.set("GCPad2", "Triggers/R", "`P` | `E`")
        g_cfg.set("GCPad2", "Triggers/Threshold", "50")
        g_cfg.set("GCPad2", "D-Pad/Up", "`KP_Up` | `1`")
        g_cfg.set("GCPad2", "D-Pad/Down", "`KP_Down` | `2`")
        g_cfg.set("GCPad2", "D-Pad/Left", "`KP_Left` | `3`")
        g_cfg.set("GCPad2", "D-Pad/Right", "`KP_Right` | `4`")

        with open(g_ini_path, "w") as f:
            g_cfg.write(f)

def is_dolphin_running():
    try:
        out = subprocess.check_output(["pgrep", "-f", "Slippi_Online|dolphin-emu"]).decode()
        return bool(out.strip())
    except Exception:
        return False

def select_character_fly(gamestate, controller, cpu_mode=False, target_char_name="LUIGI"):
    """
    Controlador autónomo e infalible de Menú CSS para la Mosca (Luigi o Fox en Puerto 1):
    1. Si el Puerto 1 está en 'N/A' (desconectado) o 'CP' (CPU):
       Navega directo al botón del banner P1 (-31.5, -2.2) y pulsa 'A' para activar el slot a 'HMN'.
    2. Si la ficha está en la mano (coin_down == False):
       Navega de forma diagonal directa hacia el personaje objetivo y pulsa 'A'.
    3. Si la ficha cayó por error en otro personaje:
       Pulsa 'B' con cadencia lenta para levantar la ficha.
    4. Si cpu_mode está activo:
       Asegura que el Puerto 2 esté configurado como Bot CPU.
    5. Si el personaje ya está seleccionado y la ficha colocada:
       Mueve el cursor hacia arriba a zona de descanso neutral (-15.0, 25.0) para no estorbar.
    6. Cuando ambos jugadores están listos (ready_to_start == True):
       Pulsa START para arrancar la partida inmediatamente.
    """
    p1 = gamestate.players.get(1)
    if not p1:
        controller.release_all()
        return

    cur_x = p1.cursor.x
    cur_y = p1.cursor.y

    is_fox = ("FOX" in str(target_char_name).upper())
    target_character = melee.Character.FOX if is_fox else melee.Character.LUIGI
    target_x, target_y = (-22.0, 11.5) if is_fox else (-15.0, 18.5)

    def move_towards(tx, ty, wiggleroom=1.4):
        dx = tx - cur_x
        dy = ty - cur_y
        dist = math.hypot(dx, dy)
        if dist > wiggleroom:
            mag = max(abs(dx), abs(dy), 1e-4)
            sx = max(0.0, min(1.0, 0.5 + 0.5 * (dx / mag)))
            sy = max(0.0, min(1.0, 0.5 + 0.5 * (dy / mag)))
            controller.tilt_analog(melee.Button.BUTTON_MAIN, sx, sy)
            controller.release_button(melee.Button.BUTTON_A)
            controller.release_button(melee.Button.BUTTON_B)
            return False
        else:
            controller.tilt_analog(melee.Button.BUTTON_MAIN, 0.5, 0.5)
            return True

    # 1. Recuperar ranura si está en "N/A" (desconectada) o "CP"
    if p1.controller_status != melee.ControllerStatus.CONTROLLER_HUMAN:
        target_slot_x = -31.5
        target_slot_y = -2.2
        if move_towards(target_slot_x, target_slot_y, wiggleroom=1.5):
            if gamestate.frame % 3 == 0:
                controller.press_button(melee.Button.BUTTON_A)
            else:
                controller.release_button(melee.Button.BUTTON_A)
            controller.release_button(melee.Button.BUTTON_B)
        return

    # 2. Puerto activo: verificar si el personaje objetivo está seleccionado con ficha puesta
    char_chosen = (p1.character == target_character and p1.coin_down)

    if not char_chosen:
        # Si la ficha está en otro personaje, levantarla con B
        if p1.coin_down and p1.character != target_character:
            if gamestate.frame % 4 == 0:
                controller.press_button(melee.Button.BUTTON_B)
            else:
                controller.release_button(melee.Button.BUTTON_B)
            controller.release_button(melee.Button.BUTTON_A)
            return

        # Ficha en mano: NUNCA pulsar B. Moverse al objetivo y soltar con A
        controller.release_button(melee.Button.BUTTON_B)
        if move_towards(target_x, target_y, wiggleroom=1.4):
            if gamestate.frame % 3 == 0:
                controller.press_button(melee.Button.BUTTON_A)
            else:
                controller.release_button(melee.Button.BUTTON_A)
        return

    # 3. Si estamos en modo CPU, activar el Puerto 2 como CPU si aún no lo está
    if cpu_mode:
        p2 = gamestate.players.get(2)
        if p2 and p2.controller_status != melee.ControllerStatus.CONTROLLER_CPU:
            target_p2_slot_x = -16.5
            target_p2_slot_y = -2.2
            if move_towards(target_p2_slot_x, target_p2_slot_y, wiggleroom=1.5):
                if gamestate.frame % 3 == 0:
                    controller.press_button(melee.Button.BUTTON_A)
                else:
                    controller.release_button(melee.Button.BUTTON_A)
            return

    # 4. Personaje ya elegido: aparcar cursor en zona de descanso arriba
    rest_x = -15.0
    rest_y = 25.0
    move_towards(rest_x, rest_y, wiggleroom=2.0)

    # 5. Arrancar partida cuando ambos jugadores están listos
    is_ready = getattr(gamestate, "ready_to_start", False)
    if is_ready:
        if gamestate.frame % 4 == 0:
            controller.press_button(melee.Button.BUTTON_START)
        else:
            controller.release_button(melee.Button.BUTTON_START)
    else:
        controller.release_button(melee.Button.BUTTON_START)

def select_stage_battlefield(gamestate, controller):
    """
    Selecciona Battlefield (1.0, -9.0) de forma directa en el SSS.
    """
    p1 = gamestate.players.get(1)
    if not p1:
        controller.release_all()
        return

    cur_x = p1.cursor.x
    cur_y = p1.cursor.y
    target_x = 1.0
    target_y = -9.0
    dx = target_x - cur_x
    dy = target_y - cur_y
    dist = math.hypot(dx, dy)
    if dist > 1.5:
        mag = max(abs(dx), abs(dy), 1e-4)
        controller.tilt_analog(melee.Button.BUTTON_MAIN, 0.5 + 0.5 * (dx / mag), 0.5 + 0.5 * (dy / mag))
        controller.release_button(melee.Button.BUTTON_A)
    else:
        controller.tilt_analog(melee.Button.BUTTON_MAIN, 0.5, 0.5)
        if gamestate.frame % 3 == 0:
            controller.press_button(melee.Button.BUTTON_A)
        else:
            controller.release_button(melee.Button.BUTTON_A)

def run_fly_vs_human(dolphin_path=None, iso_path=None, cpu_level=None, fly_character="luigi", lightweight=False):
    char_title = fly_character.upper()
    char_desc = "LUIGI (Wavedash SSS & Shoryuken)" if char_title == "LUIGI" else "FOX McCLOUD (20XX Shine & Spacie)"
    opponent_label = f"BOT CPU NIVEL {cpu_level}" if cpu_level else "JUGADOR HUMANO (TÚ)"
    net_desc = "49k neuronas (Ultra-rápido 0 lag)" if lightweight else "MaleCNS 400k (Conectoma completo)"
    print("=" * 72)
    print(f"  🪰 CEREBRO DE LA MOSCA ({net_desc}) VS {opponent_label}")
    print(f"  🎮 Puerto 1: {char_desc}")
    if cpu_level:
        print(f"  🤖 Puerto 2: BOT MELEE CPU Nivel {cpu_level} (Configurado automáticamente)")
    else:
        print("  🕹️ Puerto 2: TÚ (Elige cualquier personaje con tu teclado/mando)")
    print("=" * 72)

    # Inicializar cliente de telemetría asíncrono persistente (0 lag, 0 sobrecarga)
    telemetry_client = TelemetryClient()
    
    # 0. Resolver ISO
    if not iso_path:
        if os.path.exists(DEFAULT_ISO):
            iso_path = DEFAULT_ISO
            print(f"📁 Usando ISO verificada: {iso_path}")
        else:
            print(f"⚠️ Aviso: No se encontró la ISO en {DEFAULT_ISO}.")
            
    # 1. Inicializar cerebro biológico
    brain = FlyBrain(lightweight=lightweight)
    brain.active_character = fly_character.upper()
    
    # 2. Inicializar consola de Dolphin usando DOLPHIN_HOME
    print("\n⏳ Inicializando consola Dolphin...")
    if not dolphin_path:
        local_apprun = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dolphin", "AppRun")
        if os.path.exists(local_apprun):
            dolphin_path = local_apprun

    console = melee.Console(
        path=dolphin_path,
        fullscreen=False,
        tmp_home_directory=False,
        dolphin_home_path=DOLPHIN_HOME
    )
    
    # Solo conectamos el controlador 1 para la mosca. El puerto 2 lo maneja el usuario o CPU.
    controller_fly = melee.Controller(console=console, port=1, type=melee.ControllerType.STANDARD)
    
    # 3. Configurar mandos en Dolphin (P1: Mosca Pipe, P2: Humano Teclado o Bot CPU)
    if cpu_level:
        print(f"⚙️ Configurando puertos en Dolphin (P1: Mosca Luigi, P2: Bot CPU Nivel {cpu_level})...")
        setup_human_and_bot_controllers(DOLPHIN_HOME, cpu_mode=True)
    else:
        print("⚙️ Configurando puertos en Dolphin (P1: Mosca Luigi, P2: Jugador Humano)...")
        setup_human_and_bot_controllers(DOLPHIN_HOME, cpu_mode=False)
    
    # 4. Lanzar Dolphin
    if not is_dolphin_running() and iso_path:
        print(f"🚀 Iniciando emulador Dolphin con {iso_path}...")
        console.run(iso_path=iso_path)
    else:
        print("🔗 Conectando a instancia de Dolphin en ejecución...")
        
    print("⏳ Esperando conexión a Dolphin...")
    connected = False
    for attempt in range(1, 25):
        if console.connect():
            connected = True
            break
        time.sleep(1)
        
    if not connected:
        print("❌ Error: No se pudo conectar a Dolphin.")
        sys.exit(1)
        
    print("🎮 Conectando controlador de GameCube P1 (Mosca - Luigi)...")
    if not controller_fly.connect():
        print("❌ Error al conectar controlador P1.")
        sys.exit(1)
        
    print("\n" + "=" * 72)
    print("  ✅ ¡CONEXIÓN ESTABLECIDA CON ÉXITO!")
    print("  ⌨️  CONTROLES PARA TI (PUERTO 2 - TECLADO):")
    print("      --- Esquema A (WASD + Mano Derecha) ---")
    print("      • Moverte / Cursor:  W / A / S / D")
    print("      • Elegir Ficha / Ataque A:  J  o  ESPACIO")
    print("      • Ataque Especial B:        K")
    print("      • Saltar (X / Y):           U  o  I")
    print("      • Agarrar (Grab Z):         O")
    print("      • Escudo (L / R):           L")
    print("      • Empezar / Pausa (Start):  ENTER")
    print("      ---------------------------------------")
    print("      --- Esquema B (Flechas + Mano Izquierda) ---")
    print("      • Moverte / Cursor:  FLECHAS (↑ ↓ ← →)")
    print("      • Elegir Ficha / Ataque A:  X  o  ESPACIO")
    print("      • Ataque Especial B:        Z")
    print("      • Saltar (X / Y):           C  o  V")
    print("      • Agarrar (Grab Z):         F")
    print("      • Escudo (L / R):           Q  o  E")
    print("      • Empezar / Pausa (Start):  ENTER")
    print("  🌐 Panel 3D y combate en vivo: http://localhost:8085")
    print("=" * 72 + "\n")
    print(f"🪰 La mosca está eligiendo a {char_title} en el menú y colocando su ficha.")
    print("👉 ¡Toma tu teclado, mueve tu ficha y elige a tu personaje con J, X o Espacio!\n")
    
    step_count = 0
    active_controller_buttons = {
        melee.Button.BUTTON_A: False,
        melee.Button.BUTTON_B: False,
        melee.Button.BUTTON_X: False,
        melee.Button.BUTTON_Y: False,
        melee.Button.BUTTON_Z: False,
        melee.Button.BUTTON_L: False,
        melee.Button.BUTTON_R: False,
        melee.Button.BUTTON_START: False,
        melee.Button.BUTTON_D_UP: False,
    }
    menu_helper_fly = melee.MenuHelper()
    was_in_game = False
    match_number = 1
    postgame_frames = 0
    
    try:
        while True:
            try:
                gamestate = console.step()
            except (melee.slippstream.EnetDisconnected, EOFError, ConnectionResetError, BrokenPipeError) as conn_err:
                if console._process is not None and console._process.poll() is not None:
                    print(f"\n🚪 Dolphin se ha cerrado (código de salida: {console._process.returncode}). Sesión finalizada limpiamente.")
                    break
                print(f"\n⚠️ [Slippi Bridge] Desconexión detectada ({type(conn_err).__name__}). Reenganchando Dolphin...")
                reconnected = False
                for attempt in range(1, 15):
                    if console._process is not None and console._process.poll() is not None:
                        break
                    time.sleep(0.5)
                    try:
                        console._slippstream.shutdown()
                    except Exception:
                        pass
                    try:
                        if console.connect():
                            print(f"✅ ¡Reconexión exitosa a Dolphin (intento {attempt})! Reanudando...")
                            reconnected = True
                            break
                    except Exception:
                        pass
                if reconnected:
                    continue
                else:
                    print("❌ No se pudo reconectar a Dolphin tras múltiples intentos.")
                    break

            if gamestate is None:
                continue
                
            is_in_game = gamestate.menu_state in [melee.Menu.IN_GAME, melee.Menu.SUDDEN_DEATH]

            # -------------------------------------------------------------
            # DETECCIÓN DE FIN DE PARTIDA & APRENDIZAJE PERSISTENTE
            # -------------------------------------------------------------
            if was_in_game and not is_in_game:
                print(f"\n🏁 [Fin de Partida #{match_number}] Guardando experiencia en memoria biológica a largo plazo...")
                p1_stk = getattr(brain, "prev_p1_stock", 0)
                p2_stk = getattr(brain, "prev_p2_stock", 0)
                p1_obj = gamestate.players.get(1)
                char_p1 = str(p1_obj.character).split(".")[-1].capitalize() if p1_obj and getattr(p1_obj, "character", None) else "Luigi"
                if p1_stk > p2_stk:
                    print(f"🏆 ¡VICTORIA DE LA MOSCA! {char_p1} ({p1_stk}⭐) superó a su rival ({p2_stk}⭐).")
                    brain.learn_from_success("MATCH_WON")
                else:
                    print(f"💀 DERROTA. {char_p1} ({p1_stk}⭐) cayó ante su rival ({p2_stk}⭐). Adaptando sinapsis defensivas.")
                    brain.learn_from_error("MATCH_LOST")

                brain.long_term_memory["matches_played"] += 1
                brain.save_long_term_memory()

                # Reiniciar para la siguiente partida sin bugs
                brain.reset()
                step_count = 0
                controller_fly.release_all()
                for b in active_controller_buttons:
                    active_controller_buttons[b] = False
                postgame_frames = 0
                match_number += 1
                menu_helper_fly = melee.MenuHelper() # Nuevo helper limpio para la revancha
                print(f"🔄 ¡Preparando revancha inmediata para Partida #{match_number}!\n")

            was_in_game = is_in_game

            # -------------------------------------------------------------
            # MÁQUINA DE ESTADOS DE MENÚS (REENGANCHE AUTOMÁTICO DE PARTIDAS)
            # -------------------------------------------------------------
            # 1. Pantalla de Selección de Personajes (CSS - Auto-recupera Slot N/A y elige a Luigi / activa CPU)
            if gamestate.menu_state in [melee.Menu.CHARACTER_SELECT, melee.Menu.SLIPPI_ONLINE_CSS]:
                select_character_fly(gamestate, controller_fly, cpu_mode=(cpu_level is not None), target_char_name=fly_character)

            # 2. Pantalla de Selección de Escenario (SSS - Selección directa de Battlefield)
            elif gamestate.menu_state == melee.Menu.STAGE_SELECT:
                select_stage_battlefield(gamestate, controller_fly)

            # 3. Pantalla de Victoria / Tabla de Resultados (Post-Game Scores)
            elif gamestate.menu_state == melee.Menu.POSTGAME_SCORES:
                postgame_frames += 1
                if postgame_frames % 8 == 0:
                    controller_fly.press_button(melee.Button.BUTTON_START)
                elif postgame_frames % 8 == 4:
                    controller_fly.press_button(melee.Button.BUTTON_A)
                else:
                    controller_fly.release_all()

            # 4. Menú Desconocido / Transición / Diálogo del Sistema (Liberar mandos para evitar confirmar salidas involuntarias)
            elif gamestate.menu_state == melee.Menu.UNKNOWN_MENU:
                controller_fly.release_all()
                controller_fly.tilt_analog(melee.Button.BUTTON_MAIN, 0.5, 0.5)
                controller_fly.tilt_analog(melee.Button.BUTTON_C, 0.5, 0.5)

            # 4. Menú Principal o Press Start
            elif gamestate.menu_state in [melee.Menu.MAIN_MENU, melee.Menu.PRESS_START]:
                menu_helper_fly.choose_versus_mode(gamestate=gamestate, controller=controller_fly)

            # -------------------------------------------------------------
            # ESTADO EN COMBATE (MOSCA VS HUMANO)
            # -------------------------------------------------------------
            elif is_in_game:
                # 0. Guardia de Inicio de Partida: Durante el conteo inicial (READY... GO!) o entrada de personajes:
                game_frame = getattr(gamestate, "frame", 0)
                if game_frame < 0:
                    controller_fly.release_all()
                    p1_obj = gamestate.players.get(1)
                    if p1_obj and getattr(p1_obj, "stock", None) is not None:
                        brain.prev_p1_stock = int(p1_obj.stock)
                    for p_num in [2, 3, 4]:
                        cand = gamestate.players.get(p_num)
                        if cand and getattr(cand, "stock", None) is not None:
                            brain.prev_p2_stock = int(cand.stock)
                            break
                    brain.dopamine = 0.85 # Motivación inicial de combate: Adicción a ganar (85%)
                    brain.endorphin = 0.50
                    brain.octopamine = 0.20
                    step_count = 0
                    continue

                fly_player = gamestate.players.get(1)
                human_player = None
                for p_num in [2, 3, 4]:
                    cand = gamestate.players.get(p_num)
                    if cand and getattr(cand, "character", None) is not None:
                        human_player = cand
                        break
                
                if fly_player and human_player:
                    # Guardia de animación de entrada (Fox bajando del Arwing):
                    act_str_check = str(getattr(fly_player, "action", ""))
                    act_val_p1 = getattr(fly_player.action, "value", 0)
                    if "ENTRY" in act_str_check or act_val_p1 in [322, 323, 324]:
                        controller_fly.release_all()
                        controller_fly.tilt_analog(melee.Button.BUTTON_MAIN, 0.5, 0.5)
                        controller_fly.tilt_analog(melee.Button.BUTTON_C, 0.5, 0.5)
                        continue

                    # Guardia de muerte: Si la mosca está en animación de muerte (0..10), liberar controles y limpiar buffers
                    is_p1_dead = (act_val_p1 in range(0, 11)) or ("DEAD_" in act_str_check and "FALL" not in act_str_check and "LEAP" not in act_str_check)
                    if is_p1_dead:
                        controller_fly.release_all()
                        controller_fly.tilt_analog(melee.Button.BUTTON_MAIN, 0.5, 0.5)
                        controller_fly.tilt_analog(melee.Button.BUTTON_C, 0.5, 0.5)
                        brain.stimulate_sensory(
                            threat_level=0.0,
                            rel_x=0.0,
                            rel_y=0.0,
                            is_offstage=True,
                            looming_rate=0.0,
                            player=fly_player,
                            opponent=human_player,
                            current_frame=step_count
                        )
                        step_count += 1
                        continue
                    # 1. Extraer posición y velocidad de aproximación óptica (Looming)
                    dx = human_player.position.x - fly_player.position.x
                    dy = human_player.position.y - fly_player.position.y
                    distance = (dx**2 + dy**2)**0.5
                    
                    last_distance = getattr(brain, "prev_dist", distance)
                    looming_rate = max(0.0, (last_distance - distance) * 1.5)
                    brain.prev_dist = distance
                    
                    current_stage = getattr(gamestate, "stage", None)
                    stage_edge_val = brain.get_stage_edge(current_stage)
                    stage_name_str = str(current_stage).split(".")[-1].replace("_", " ").title() if current_stage else "Battlefield"
                    
                    threat = max(0.0, min(1.0, (75.0 - distance) / 75.0))
                    rel_x = max(-1.0, min(1.0, dx / 45.0))
                    rel_y = max(-1.0, min(1.0, dy / 45.0))
                    act_val_p1 = getattr(fly_player.action, "value", 0)
                    is_on_ledge_p1 = act_val_p1 in [252, 253]
                    is_offstage = is_on_ledge_p1 or ((not fly_player.on_ground) and (
                        getattr(fly_player, "off_stage", False) or abs(fly_player.position.x) > (stage_edge_val - 2.0) or fly_player.position.y < -2.0
                    ))
                    
                    # 2. Estimular neuronas sensoriales visuales y neuromodulación (Dopamina/Octopamina)
                    current = brain.stimulate_sensory(
                        threat_level=threat,
                        rel_x=rel_x,
                        rel_y=rel_y,
                        is_offstage=is_offstage,
                        looming_rate=looming_rate,
                        player=fly_player,
                        opponent=human_player,
                        current_frame=step_count
                    )
                    
                    # 3. Avanzar simulación biológica LIF a 60Hz nativos en tiempo real (CSC sub-milisecond)
                    brain.step(current)
                    
                    # 4. Decodificar decisión técnica inteligente (Luigi o Fox según personaje en P1)
                    action = brain.get_controller_decision(player=fly_player, opponent=human_player, current_frame=step_count, stage=current_stage)
                    
                    # 5. Aplicar acciones en el mando de la mosca (P1) mediante transiciones limpias (Edge-Triggered)
                    # Se eliminó controller_fly.release_all() por frame para NO saturar el buffer FIFO de Dolphin
                    # ni cancelar cargas continuas (Green Missile) o pulsos de botón (Cyclone mashing / Jump).
                    desired_buttons = {b: False for b in active_controller_buttons}

                    # Jump: pulso limpio de flanco de subida (1 frame ON, 1 frame OFF)
                    if action.get("jump"):
                        if active_controller_buttons[melee.Button.BUTTON_Y]:
                            desired_buttons[melee.Button.BUTTON_Y] = False
                        else:
                            desired_buttons[melee.Button.BUTTON_Y] = True
                    else:
                        desired_buttons[melee.Button.BUTTON_Y] = False

                    # Special (Button B):
                    # - MASHING (ej. Rising Cyclone): alternar press y release en cada frame (30Hz nativos limpios)
                    # - Carga o poder sostenido (ej. Green Missile charge, Fire Fox, etc.): mantener presionado
                    if action.get("special"):
                        if "MASHING" in action.get("name", ""):
                            desired_buttons[melee.Button.BUTTON_B] = not active_controller_buttons[melee.Button.BUTTON_B]
                        else:
                            desired_buttons[melee.Button.BUTTON_B] = True
                    else:
                        desired_buttons[melee.Button.BUTTON_B] = False

                    # Attack (Button A): pulso limpio (1 frame ON, 1 frame OFF) para encadenar jabs/pummels sin bloqueo de smash charge
                    if action.get("attack"):
                        if active_controller_buttons[melee.Button.BUTTON_A]:
                            desired_buttons[melee.Button.BUTTON_A] = False
                        else:
                            desired_buttons[melee.Button.BUTTON_A] = True
                    else:
                        desired_buttons[melee.Button.BUTTON_A] = False

                    # Shield (Button L):
                    if action.get("shield"):
                        desired_buttons[melee.Button.BUTTON_L] = True

                    # Grab (Button Z): pulso limpio para no quedar atascado en Light Shield
                    if action.get("grab"):
                        if active_controller_buttons[melee.Button.BUTTON_Z]:
                            desired_buttons[melee.Button.BUTTON_Z] = False
                        else:
                            desired_buttons[melee.Button.BUTTON_Z] = True
                    else:
                        desired_buttons[melee.Button.BUTTON_Z] = False

                    # Taunt (Button D_UP):
                    if action.get("taunt"):
                        desired_buttons[melee.Button.BUTTON_D_UP] = True

                    # Enviar únicamente cambios de estado (Rising edge -> press, Falling edge -> release)
                    for btn, desired in desired_buttons.items():
                        if desired and not active_controller_buttons[btn]:
                            controller_fly.press_button(btn)
                            active_controller_buttons[btn] = True
                        elif not desired and active_controller_buttons[btn]:
                            controller_fly.release_button(btn)
                            active_controller_buttons[btn] = False
                        
                    # Reset C-stick a neutral (0.5, 0.5) si el personaje ya está ejecutando la animación de un ataque previo para que Melee registre el siguiente C-stick flick
                    c_x = float(action.get("c_stick_x", 0.5))
                    c_y = float(action.get("c_stick_y", 0.5))
                    fly_act_val = getattr(getattr(fly_player, "action", None), "value", None)
                    if fly_act_val is None:
                        fly_act_val = fly_player.action if isinstance(getattr(fly_player, "action", None), int) else None
                    if fly_act_val is not None and 44 <= fly_act_val <= 75:
                        c_x = 0.5
                        c_y = 0.5

                    controller_fly.tilt_analog(melee.Button.BUTTON_MAIN, float(action.get("stick_x", 0.5)), float(action.get("stick_y", 0.5)))
                    controller_fly.tilt_analog(melee.Button.BUTTON_C, c_x, c_y)
                    
                    step_count += 1
                    
                    # 6. Telemetría hacia el dashboard web con memoria biológica a largo plazo y escenario dinámico
                    if step_count % 2 == 0:
                        human_char_name = str(human_player.character).split(".")[-1].capitalize()
                        p1_char_name = str(fly_player.character).split(".")[-1].capitalize() if getattr(fly_player, "character", None) else "Luigi"
                        is_shining_or_power = "SPECIAL_DOWN" in str(fly_player.action) or any(k in action["name"] for k in ["SHINE", "SHORYUKEN", "CYCLONE", "DOWN-SMASH"])
                        is_projectile = "SPECIAL_N" in str(fly_player.action) or any(k in action["name"] for k in ["BLASTER", "FUEGO", "FIREBALL", "MISSILE"])
                        telemetry_data = {
                            "stage_name": stage_name_str,
                            "stage_edge": float(stage_edge_val),
                            "distance": float(distance),
                            "threat": float(threat),
                            "action_name": action.get("name", "EN GUARDIA"),
                            "dopamine": action.get("stats", {}).get("dopamine", getattr(brain, "dopamine", 0.85)),
                            "endorphin": action.get("stats", {}).get("endorphin", getattr(brain, "endorphin", 0.5)),
                            "flow_state": action.get("stats", {}).get("flow_state", False),
                            "octopamine": action.get("stats", {}).get("octopamine", getattr(brain, "octopamine", 0.2)),
                            "combo_count": getattr(brain, "combo_count", 0),
                            "last_power": getattr(brain, "last_luigi_power", None),
                            "num_neurons": getattr(brain, "num_neurons", 395144),
                            "memory": {
                                "matches_played": brain.long_term_memory.get("matches_played", 0),
                                "matches_won": brain.long_term_memory.get("matches_won", 0),
                                "total_kos": brain.long_term_memory.get("total_kos", 0),
                                "total_deaths": brain.long_term_memory.get("total_deaths", 0),
                                "win_addiction": round(float(brain.long_term_memory.get("synaptic_plasticity", {}).get("win_addiction", 5.0)), 2),
                                "loss_aversion_fury": round(float(brain.long_term_memory.get("synaptic_plasticity", {}).get("loss_aversion_fury", 5.0)), 2),
                                "edge_fear": round(float(brain.long_term_memory.get("edge_fear", 1.0)), 2),
                                "combo_mastery": round(float(brain.long_term_memory.get("synaptic_plasticity", {}).get("combo_mastery", 1.6)), 2),
                                "offstage_aggression": round(float(brain.long_term_memory.get("synaptic_plasticity", {}).get("offstage_aggression", 1.65)), 2),
                                "endorphin_resilience": round(float(brain.long_term_memory.get("synaptic_plasticity", {}).get("endorphin_resilience", 1.5)), 2),
                                "pain_tolerance": round(float(brain.long_term_memory.get("synaptic_plasticity", {}).get("pain_tolerance", 1.4)), 2),
                                "flow_mastery": round(float(brain.long_term_memory.get("synaptic_plasticity", {}).get("flow_mastery", 1.5)), 2)
                            },
                            "p1": {
                                "name": f"{p1_char_name} (Mosca)",
                                "x": float(fly_player.position.x),
                                "y": float(fly_player.position.y),
                                "percent": int(fly_player.percent),
                                "stock": int(fly_player.stock),
                                "action": str(fly_player.action).split(".")[-1],
                                "facing": 1 if fly_player.facing else -1,
                                "is_shining": is_shining_or_power,
                                "is_laser": is_projectile
                            },
                            "p2": {
                                "name": f"{human_char_name} (Tú)",
                                "x": float(human_player.position.x),
                                "y": float(human_player.position.y),
                                "percent": int(human_player.percent),
                                "stock": int(human_player.stock),
                                "action": str(human_player.action).split(".")[-1],
                                "facing": 1 if human_player.facing else -1
                            },
                            "action": action
                        }
                        telemetry_client.send(telemetry_data)
                    
                    # Mostrar en terminal cada segundo
                    if step_count % 60 == 0:
                        try:
                            human_char_name = str(human_player.character).split(".")[-1].capitalize()
                            p1_char_disp = str(fly_player.character).split(".")[-1].capitalize() if getattr(fly_player, "character", None) else char_title.capitalize()
                            p1_pct = int(fly_player.percent)
                            p2_pct = int(human_player.percent)
                            p1_stk = int(fly_player.stock)
                            p2_stk = int(human_player.stock)
                            dopa_val = action.get("stats", {}).get("dopamine", getattr(brain, "dopamine", 0.85))
                            dopa_icon = "🔥 ADICCIÓN" if dopa_val >= 0.80 else "⚡ FURIA"
                            endo_val = action.get("stats", {}).get("endorphin", getattr(brain, "endorphin", 0.5))
                            flow_active = action.get("stats", {}).get("flow_state", False)
                            flow_str = " ✨ FLOW 20XX" if flow_active else ""
                            combo_str = f"| 💥 COMBO x{brain.combo_count}" if brain.combo_count > 1 else ""
                            stage_display = f" en {stage_name_str}" if stage_name_str else ""
                            opp_label = f"CPU L{cpu_level}" if cpu_level else "Tú"
                            octo_val = action.get("stats", {}).get("octopamine", getattr(brain, "octopamine", 0.2))
                            print(f"[{step_count//60:3d}s] {action.get('name', 'COMBATE')} | "
                                  f"{p1_char_disp}(Mosca 400k): {p1_pct:3d}% ({p1_stk}⭐) vs "
                                  f"{opp_label}({human_char_name}): {p2_pct:3d}% ({p2_stk}⭐){stage_display} | "
                                  f"🧠 Dopa:{int(dopa_val*100)}% {dopa_icon} Endo:{int(endo_val*100)}% 🛡️{flow_str} {combo_str} | Octo:{int(octo_val*100)}%")
                        except Exception:
                            pass
                              
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo partida.")
    finally:
        telemetry_client.close()
        try:
            if 'console' in locals() and console is not None:
                console.stop()
        except Exception:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fly Brain vs Human Player / CPU Bot Melee Bridge")
    parser.add_argument("--dolphin", type=str, default=None, help="Ruta al binario de Dolphin-emu")
    parser.add_argument("--iso", type=str, default=None, help="Ruta a Super Smash Bros Melee NTSC ISO")
    parser.add_argument("--cpu", type=int, default=None, help="Nivel de CPU rival en Puerto 2 (ej: 9 para Bot Nivel 9)")
    parser.add_argument("--character", "-c", type=str, default="luigi", choices=["luigi", "fox"], help="Personaje de la mosca (luigi o fox)")
    parser.add_argument("--lightweight", "-l", action="store_true", help="Modo neuronal ultraligero (49k neuronas / 0 lag / 60 FPS garantizados)")
    args = parser.parse_args()
    
    run_fly_vs_human(dolphin_path=args.dolphin, iso_path=args.iso, cpu_level=args.cpu, fly_character=args.character, lightweight=args.lightweight)
