#!/usr/bin/env python3
"""
Test interactivo del cerebro de la mosca (MaleCNS ~400k)
Simula un escenario de combate de Super Smash Bros. Melee y visualiza la actividad neural.
"""
import sys
import os

try:
    import numpy as np
except ImportError:
    venv_python = "/home/ltar/.venvs/pytorch/bin/python"
    if os.path.exists(venv_python) and sys.executable != venv_python:
        os.execv(venv_python, [venv_python] + sys.argv)
    raise

import time
from fly_brain import FlyBrain

def main():
    print("=" * 70)
    print("  🧪 SIMULADOR BIOLÓGICO: CONECTOMA DE LA MOSCA EN COMBATE")
    print("=" * 70)
    
    brain = FlyBrain()
    print("\nIniciando simulación de 120 fotogramas (2 segundos a 60 FPS)...")
    print("-" * 70)
    print(f"{'Frame':^7} | {'Dist':^6} | {'Amenaza':^8} | {'Spikes Totales':^15} | {'Acción de Melee':^22}")
    print("-" * 70)
    
    # Simular un rival (Fox) que se aproxima rápidamente desde la derecha
    # Distancia va de 60 a 5 unidades
    for frame in range(120):
        t = frame / 120.0
        # El rival se acerca y luego retrocede
        if t < 0.6:
            dist = 60.0 - (t / 0.6) * 55.0  # Se acerca de 60 a 5
            rel_x = 0.8 * (dist / 60.0)
        else:
            dist = 5.0 + ((t - 0.6) / 0.4) * 45.0  # Rebota / retrocede
            rel_x = -0.5
            
        threat = max(0.0, min(1.0, (60.0 - dist) / 60.0))
        
        # 1. Inyectar estímulo visual en fotorreceptores
        current = brain.stimulate_sensory(threat_level=threat, rel_x=rel_x, rel_y=0.0)
        
        # 2. Paso temporal LIF en el conectoma
        brain.step(current)
        
        # 3. Leer decisión de las neuronas motoras
        action = brain.get_controller_decision()
        stats = action["stats"]
        
        # Formatear acción legible
        actions_str = []
        if action["jump"]:
            actions_str.append("🦘 SALTO (DNp01)")
        if action["attack"]:
            actions_str.append("⚔️ ATAQUE (A)")
        if action["special"]:
            actions_str.append("✨ ESPECIAL (B)")
        if action["shield"]:
            actions_str.append("🛡️ ESCUDO (L)")
            
        if not actions_str:
            direction = "➡️ Der" if action["stick_x"] > 0.55 else ("⬅️ Izq" if action["stick_x"] < 0.45 else "⏸️ Quieto")
            actions_str.append(f"Mover: {direction}")
            
        action_display = " + ".join(actions_str)
        
        # Barra gráfica de disparos de neuronas
        bar_len = min(20, stats['total_spikes'] // 15)
        bar = "█" * bar_len
        
        print(f"{frame:^7d} | {dist:^6.1f} | {threat*100:^7.1f}% | {stats['total_spikes']:4d} {bar:<10} | {action_display}")
        time.sleep(0.02)
        
    print("-" * 70)
    print("✅ Prueba de simulación completada exitosamente.")

if __name__ == "__main__":
    main()
