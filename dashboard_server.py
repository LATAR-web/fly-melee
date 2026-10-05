#!/usr/bin/env python3
"""
Servidor web interactivo y telemetría en tiempo real para el Conectoma de la Mosca.
Muestra la visualización 3D WebGL (400k neuronas) y la Arena Melee en tiempo real.
"""
import sys
import os

try:
    import numpy as np
except ImportError:
    for venv_python in [
        os.path.join(os.path.dirname(__file__), ".venv", "bin", "python"),
        "/home/ltar/.venvs/pytorch/bin/python",
    ]:
        if os.path.exists(venv_python) and sys.executable != venv_python:
            os.execv(venv_python, [venv_python] + sys.argv)
    raise

import json
import time
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Asegurar import de fly_brain
sys.path.insert(0, str(Path(__file__).parent))
from fly_brain import FlyBrain

PORT = 8085
BASE_DIR = Path(__file__).parent

# Estado global de la simulación
class SimState:
    def __init__(self):
        # Modo ligero demo: ahorra >1 GB de RAM en el servidor web mientras mantiene visualización completa
        self.brain = FlyBrain(lightweight=True)
        self.distance = 35.0
        self.threat = 0.35
        self.running = True
        self.manual_override = False
        self.action_name = "🏃 DASH DANCE / SPACING"
        self.last_action = {}
        self.p1 = {
            "name": "Luigi (Mosca)",
            "x": -20.0,
            "y": 0.0,
            "percent": 12,
            "stock": 4,
            "facing": 1,
            "is_shining": False,
            "is_laser": False
        }
        self.p2 = {
            "name": "Marth (Rival)",
            "x": 20.0,
            "y": 0.0,
            "percent": 34,
            "stock": 4,
            "facing": -1
        }
        self.lock = threading.Lock()
        self.is_live = False
        self.last_live_time = 0.0
        self.dopamine = 0.5
        self.octopamine = 0.2
        self.stage_name = "Battlefield"
        self.stage_edge = 68.4
        self.active_char = "LUIGI"

class MockPos:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

class MockPlayer:
    def __init__(self, x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14, percent=0.0, stock=4, jumps_left=1):
        self.position = MockPos(x, y)
        self.on_ground = on_ground
        self.action = action
        self.act_val = int(act_val)
        self.percent = float(percent)
        self.stock = int(stock)
        self.jumps_left = jumps_left
        self.hitstun_frames_left = 0
        self.speed_x_attack = 0.0
        self.speed_y_attack = 0.0
        self.speed_ground_x_self = 0.0
        self.speed_air_x_self = 0.0
        self.speed_y_self = 0.0
        self.facing = True

state = SimState()

def simulation_worker():
    """Bucle de simulación demostrativa. Se pausa automáticamente si Dolphin está en vivo."""
    frame = 0
    while True:
        with state.lock:
            # Si estamos recibiendo telemetría real de Dolphin (en los últimos 3 segundos), pausar la demo
            is_live = state.is_live and (time.time() - state.last_live_time < 3.0)
            if not is_live:
                state.is_live = False

        if is_live:
            time.sleep(0.05)
            continue

        if state.running:
            with state.lock:
                if not state.manual_override:
                    cycle = (frame % 200) / 200.0
                    if cycle < 0.4:
                        # Fase de aproximación: Marth corre hacia Fox
                        state.distance = 55.0 - (cycle / 0.4) * 42.0
                    elif cycle < 0.6:
                        # Fase de CQC (cuerpo a cuerpo): 8 a 15 u
                        state.distance = 10.0 + ((cycle - 0.4) / 0.2) * 5.0
                    else:
                        # Fase de alejamiento / laser spacing
                        state.distance = 15.0 + ((cycle - 0.6) / 0.4) * 40.0
                        
                    state.threat = max(0.0, min(1.0, (65.0 - state.distance) / 65.0))
                    rel_x = 0.8 if state.threat > 0.4 else -0.3
                    
                    # Simular coordenadas relativas en arena
                    p1_x = -state.distance / 2.0
                    p2_x = state.distance / 2.0
                    state.p1["x"] = p1_x
                    state.p2["x"] = p2_x
                    state.p1["facing"] = 1 if p2_x > p1_x else -1
                    state.p2["facing"] = 1 if p1_x > p2_x else -1
                    
                    p1_y = state.p1.get("y", 0.0)
                    p1_vy = state.p1.get("vy", 0.0)
                    is_p1_ground = (p1_y <= 0.01)

                    char_to_use = getattr(state, "active_char", "LUIGI").upper()
                    mock_p1 = MockPlayer(
                        x=p1_x, y=p1_y, on_ground=is_p1_ground,
                        action="JUMPING" if not is_p1_ground else ("RUNNING" if abs(p1_x) > 5 else "STANDING"),
                        percent=state.p1.get("percent", 0), stock=state.p1.get("stock", 4)
                    )
                    mock_p1.character = char_to_use
                    state.brain.active_character = char_to_use
                    state.p1["name"] = f"{char_to_use.capitalize()} (Mosca)"
                    mock_p1.speed_y_self = p1_vy
                    mock_p2 = MockPlayer(
                        x=p2_x, y=state.p2.get("y", 0.0), on_ground=True,
                        action="RUNNING" if state.distance > 20 else "SHIELD",
                        percent=state.p2.get("percent", 0), stock=state.p2.get("stock", 4)
                    )

                    # Inyectar corriente y avanzar paso LIF en el conectoma
                    current = state.brain.stimulate_sensory(
                        threat_level=state.threat,
                        rel_x=rel_x,
                        rel_y=0.0,
                        player=mock_p1,
                        opponent=mock_p2,
                        current_frame=frame
                    )
                    state.brain.step(current)
                    
                    # Decodificar decisión técnica de Luigi
                    act = state.brain.get_controller_decision(player=mock_p1, opponent=mock_p2, current_frame=frame)
                    state.last_action = act
                    state.action_name = act.get("name", "EN GUARDIA")
                    state.dopamine = float(state.brain.dopamine)
                    state.octopamine = float(state.brain.octopamine)
                    state.p1["is_shining"] = "UP-B" in state.action_name or "SHORYUKEN" in state.action_name or "SHINE" in state.action_name
                    state.p1["is_laser"] = "FUEGO" in state.action_name or "FIREBALL" in state.action_name or "LÁSER" in state.action_name
                    
                    # Dinámica de salto y gravedad para la mosca en el visualizador 3D
                    if act.get("jump") and is_p1_ground:
                        p1_vy = 3.2
                        is_p1_ground = False
                    if not is_p1_ground:
                        p1_y += p1_vy
                        p1_vy -= 0.35 # Gravedad
                        if p1_y <= 0.0:
                            p1_y = 0.0
                            p1_vy = 0.0
                            is_p1_ground = True
                    state.p1["y"] = p1_y
                    state.p1["vy"] = p1_vy
                    
                    # Si la mosca conecta ataque especial o proyectil, subir daño al rival
                    if state.p1["is_shining"] and state.distance < 18:
                        state.p2["percent"] = min(250, state.p2["percent"] + 1)
                    elif state.p1["is_laser"] and frame % 4 == 0:
                        state.p2["percent"] = min(250, state.p2["percent"] + 2)
                        
            frame += 1
        time.sleep(0.033) # ~30 FPS

class FlyDashboardHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        try:
            super().log_message(format, *args)
        except OSError:
            pass

    def do_HEAD(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ["/", "/index.html"]:
            html_content = (BASE_DIR / "web/index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_content)))
            self.end_headers()
        elif path == "/three.min.js":
            three_file = BASE_DIR / "web/three.min.js"
            if three_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript")
                self.send_header("Content-Length", str(three_file.stat().st_size))
                self.end_headers()
            else:
                self.send_error(404, "three.min.js not found")
        elif path in ["/soma_norm.f32", "/soma_norm_139k.f32", "/soma_norm_197k.f32", "/soma_norm_400k.f32"]:
            fname = path.strip("/")
            soma_file = BASE_DIR / f"data/neurons/{fname}"
            if soma_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(soma_file.stat().st_size))
                self.end_headers()
            else:
                self.send_error(404, "Soma file not found")
        else:
            self.send_response(200)
            self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/" or path == "/index.html":
            html_content = (BASE_DIR / "web/index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_content)))
            self.end_headers()
            self.wfile.write(html_content)
            return

        elif path == "/three.min.js":
            three_file = BASE_DIR / "web/three.min.js"
            if three_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript")
                self.send_header("Content-Length", str(three_file.stat().st_size))
                self.end_headers()
                self.wfile.write(three_file.read_bytes())
                return
            else:
                self.send_error(404, "three.min.js not found")
                return
            
        elif path in ["/soma_norm.f32", "/soma_norm_139k.f32", "/soma_norm_197k.f32", "/soma_norm_400k.f32"]:
            fname = path.strip("/")
            soma_file = BASE_DIR / f"data/neurons/{fname}"
            if soma_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(soma_file.stat().st_size))
                self.end_headers()
                self.wfile.write(soma_file.read_bytes())
                return
            else:
                self.send_error(404, "Soma file not found")
                return
                
        elif path == "/api/events":
            # Server-Sent Events (SSE) para enviar telemetría en vivo
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            try:
                while True:
                    with state.lock:
                        is_live = state.is_live and (time.time() - state.last_live_time < 3.0)
                        payload = {
                            "is_live": is_live,
                            "distance": state.distance,
                            "threat": state.threat,
                            "action": state.last_action,
                            "action_name": state.action_name,
                            "stats": state.last_action.get("stats", {"total_spikes": 0}),
                            "dopamine": state.dopamine,
                            "octopamine": state.octopamine,
                            "combo_count": getattr(state.brain, "combo_count", 0),
                            "num_neurons": getattr(state.brain, "num_neurons", 395144),
                            "stage_name": state.stage_name,
                            "stage_edge": state.stage_edge,
                            "memory": {
                                "matches_played": state.brain.long_term_memory.get("matches_played", 0),
                                "matches_won": state.brain.long_term_memory.get("matches_won", 0),
                                "total_kos": state.brain.long_term_memory.get("total_kos", 0),
                                "edge_fear": round(float(state.brain.long_term_memory.get("edge_fear", 1.35)), 2),
                                "combo_mastery": round(float(state.brain.long_term_memory.get("synaptic_plasticity", {}).get("combo_mastery", 1.2)), 2)
                            },
                            "p1": state.p1,
                            "p2": state.p2
                        }
                    
                    data_str = f"data: {json.dumps(payload)}\n\n"
                    self.wfile.write(data_str.encode("utf-8"))
                    self.wfile.flush()
                    time.sleep(0.033) # 30 updates por segundo
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                return
                
        elif path == "/api/set_distance":
            qs = parse_qs(parsed.query)
            if "val" in qs:
                try:
                    val = float(qs["val"][0])
                    with state.lock:
                        state.distance = val
                        state.manual_override = True
                except ValueError:
                    pass
            resp_body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp_body)
            return

        elif path == "/api/set_character":
            qs = parse_qs(parsed.query)
            if "char" in qs:
                c = qs["char"][0].strip().upper()
                if c in ["FOX", "LUIGI"]:
                    with state.lock:
                        state.active_char = c
                        state.brain.active_character = c
                        state.p1["name"] = f"{c.capitalize()} (Mosca)"
            resp_body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp_body)
            return
            
        elif path == "/api/state":
            with state.lock:
                is_live = state.is_live and (time.time() - state.last_live_time < 3.0)
                payload = {
                    "is_live": is_live,
                    "distance": state.distance,
                    "threat": state.threat,
                    "action": state.last_action,
                    "action_name": state.action_name,
                    "stats": state.last_action.get("stats", {"total_spikes": 0}),
                    "dopamine": state.dopamine,
                    "octopamine": state.octopamine,
                    "combo_count": getattr(state.brain, "combo_count", 0),
                    "num_neurons": getattr(state.brain, "num_neurons", 395144),
                    "stage_name": state.stage_name,
                    "stage_edge": state.stage_edge,
                    "memory": {
                        "matches_played": state.brain.long_term_memory.get("matches_played", 0),
                        "matches_won": state.brain.long_term_memory.get("matches_won", 0),
                        "total_kos": state.brain.long_term_memory.get("total_kos", 0),
                        "edge_fear": round(float(state.brain.long_term_memory.get("edge_fear", 1.35)), 2),
                        "combo_mastery": round(float(state.brain.long_term_memory.get("synaptic_plasticity", {}).get("combo_mastery", 1.2)), 2)
                    },
                    "p1": state.p1,
                    "p2": state.p2
                }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return
            
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/push_state":
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                raw_data = self.rfile.read(length)
                try:
                    payload = json.loads(raw_data.decode("utf-8"))
                    with state.lock:
                        state.distance = float(payload.get("distance", state.distance))
                        state.threat = float(payload.get("threat", state.threat))
                        state.last_action = payload.get("action", state.last_action)
                        state.action_name = payload.get("action_name", state.action_name)
                        state.dopamine = float(payload.get("dopamine", state.dopamine))
                        state.octopamine = float(payload.get("octopamine", state.octopamine))
                        state.stage_name = str(payload.get("stage_name", state.stage_name))
                        state.stage_edge = float(payload.get("stage_edge", state.stage_edge))
                        if "combo_count" in payload:
                            state.brain.combo_count = int(payload["combo_count"])
                        if "memory" in payload:
                            state.brain.long_term_memory.update(payload["memory"])
                        if "p1" in payload:
                            state.p1.update(payload["p1"])
                        if "p2" in payload:
                            state.p2.update(payload["p2"])
                        state.is_live = True
                        state.last_live_time = time.time()
                        state.manual_override = True
                except Exception:
                    pass
            resp_body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_body)))
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp_body)
            return
        else:
            self.send_error(404, "Not Found")

def main():
    # Iniciar bucle de simulación
    sim_thread = threading.Thread(target=simulation_worker, daemon=True)
    sim_thread.start()
    
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(("0.0.0.0", PORT), FlyDashboardHandler)
    print("=" * 65)
    print(f"  🌐 PANEL 3D Y ARENA MELEE DE LA MOSCA EN VIVO")
    print(f"  URL: http://localhost:{PORT}")
    print("=" * 65)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")

if __name__ == "__main__":
    main()
