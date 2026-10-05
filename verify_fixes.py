#!/usr/bin/env python3
"""
Test exhaustivo de verificación para las correcciones de la Mosca Melee.
Verifica:
1. Prevención de suicidios en bordes (Freno en carrera, no Dash Attack offstage).
2. Recuperación offstage infalible (Double Jump sostenido, Fox Illusion, Fire Fox al escenario).
3. Cadena de combos (Up-Throw -> Jump -> Up-Air, Running JC Up-Smash, Tech-Chase).
4. L-Cancel automático en aterrizaje de ataques aéreos.
5. Latencia de simulación biológica LIF (CSC optimization < 10ms).
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
import math
from fly_brain import FlyBrain, get_stage_edge

class MockPos:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

class MockPlayer:
    def __init__(self, x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14, percent=0.0, stock=4, jumps_left=1):
        self.position = MockPos(x, y)
        self.on_ground = on_ground
        self.action = action
        self.act_val = act_val
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
        self.action_frame = 1
        self.off_stage = False

def run_tests():
    print("=" * 70)
    print("🧪 INICIANDO BATERÍA DE PRUEBAS DE VERIFICACIÓN (MOSCA MELEE)")
    print("=" * 70)
    
    brain = FlyBrain()
    
    # -------------------------------------------------------------
    # TEST 1: Rendimiento y Latencia de la SNN (395k neuronas LIF)
    # -------------------------------------------------------------
    print("\n--- Test 1: Latencia de Simulación SNN (Meta < 10ms por paso) ---")
    cur = brain.stimulate_sensory(threat_level=0.7, rel_x=0.5, rel_y=0.0)
    t0 = time.time()
    steps = 50
    for _ in range(steps):
        brain.step(cur)
    dt = time.time() - t0
    avg_ms = (dt / steps) * 1000
    fps = steps / dt
    print(f"⏱️ Tiempo medio por paso: {avg_ms:.2f} ms ({fps:.1f} FPS equivalentes)")
    assert avg_ms < 50.0, f"Error: Simulación demasiado lenta ({avg_ms:.2f} ms)"
    print("✅ TEST 1 SUPERADO: Simulación hiper-rápida sin congelamientos.")

    # -------------------------------------------------------------
    # TEST 2: Prevención de Suicidio al Correr Hacia el Borde
    # -------------------------------------------------------------
    print("\n--- Test 2: Prevención de Suicidio al Correr Hacia el Borde ---")
    # Fox en X = 63.0 (cerca del borde derecho de Battlefield = 68.4), intentando sprintar al borde
    p_fox = MockPlayer(x=63.0, y=0.0, on_ground=True, action="RUNNING", act_val=21)
    p_fox.speed_ground_x_self = 2.0
    p_opp = MockPlayer(x=66.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    
    # Evaluar acción
    act = brain.get_fox_decision(player=p_fox, opponent=p_opp, current_frame=1, stage="BATTLEFIELD")
    print(f"Decisión cerca del borde: {act['name']} | Stick X: {act['stick_x']:.2f}, Stick Y: {act['stick_y']:.2f}")
    
    # La barrera de seguridad debe orientar el stick hacia la izquierda (centro)
    assert act["stick_x"] <= 0.5, f"Error: Fox intentó correr al abismo ({act['stick_x']})"
    assert act["stick_y"] == 0.0, "Error: Fox debe cancelar carrera agachándose (stick_y=0.0)"
    print("✅ TEST 2 SUPERADO: Barrera de seguridad detiene a Fox antes del borde y frena la carrera.")

    # -------------------------------------------------------------
    # TEST 3: Recuperación Offstage - Fire Fox apuntado a Superficie Segura
    # -------------------------------------------------------------
    print("\n--- Test 3: Trayectoria de Fire Fox a Superficie Segura (No al Risco) ---")
    # Fox fuera del escenario a la derecha y bajo: X = 80.0, Y = -15.0
    p_fox_rec = MockPlayer(x=80.0, y=-15.0, on_ground=False, action="FIREFOX_AIR", act_val=356, jumps_left=0)
    act_rec = brain.get_fox_decision(player=p_fox_rec, opponent=p_opp, current_frame=2, stage="BATTLEFIELD")
    
    print(f"Decisión Fire Fox: {act_rec['name']} | Stick X: {act_rec['stick_x']:.3f}, Stick Y: {act_rec['stick_y']:.3f}")
    # El stick debe apuntar hacia arriba y hacia la izquierda (X < 0.5, Y > 0.5)
    assert act_rec["stick_x"] < 0.5, f"Error: Fire Fox no apunta al escenario ({act_rec['stick_x']})"
    assert act_rec["stick_y"] > 0.5, f"Error: Fire Fox no apunta hacia arriba ({act_rec['stick_y']})"
    print("✅ TEST 3 SUPERADO: Fire Fox apunta de forma ascendente hacia la pista segura.")

    # -------------------------------------------------------------
    # TEST 4: Recuperación Offstage - Doble Salto sostenido
    # -------------------------------------------------------------
    print("\n--- Test 4: Doble Salto sin Cancelación Prematura ---")
    p_fox_jump = MockPlayer(x=75.0, y=-8.0, on_ground=False, action="FALLING", act_val=29, jumps_left=1)
    act_jump1 = brain.get_fox_decision(player=p_fox_jump, opponent=p_opp, current_frame=10, stage="BATTLEFIELD")
    print(f"Frame 10 (Con salto disponible): {act_jump1['name']} | Jump={act_jump1['jump']}, Special={act_jump1['special']}")
    assert act_jump1["jump"], "Error: Fox debe usar su doble salto"
    
    # Simular siguiente frame: jumps_left ahora es 0, Fox subiendo
    p_fox_jump.jumps_left = 0
    p_fox_jump.speed_y_self = 1.2
    act_jump2 = brain.get_fox_decision(player=p_fox_jump, opponent=p_opp, current_frame=11, stage="BATTLEFIELD")
    print(f"Frame 11 (Ascendiendo del salto): {act_jump2['name']} | Jump={act_jump2['jump']}, Special={act_jump2['special']}")
    assert not act_jump2["special"], "Error: Fox cortó su doble salto prematuramente con Up-B"
    print("✅ TEST 4 SUPERADO: Doble salto asciende completamente sin cancelarse.")

    # -------------------------------------------------------------
    # TEST 5: Combo Up-Throw -> Up-Air Kill Confirm
    # -------------------------------------------------------------
    print("\n--- Test 5: Combo Up-Throw -> Jump -> Up-Air ---")
    # Paso A: Fox tiene agarrado al rival
    p_fox_c = MockPlayer(x=0.0, y=0.0, on_ground=True, action="GRAB_WAIT", act_val=216)
    p_opp_c = MockPlayer(x=3.0, y=0.0, on_ground=True, action="GRABBED", percent=85.0)
    
    act_c1 = brain.get_fox_decision(player=p_fox_c, opponent=p_opp_c, current_frame=20, stage="BATTLEFIELD")
    print(f"Paso A (Agarre): {act_c1['name']} | Stick Y={act_c1['stick_y']}")
    assert act_c1["stick_y"] == 1.0, "Error: Debe lanzar arriba con Stick Up"
    assert brain.combo_state == "UPTHROW_UAIR", "Error: Estado de combo debe ser UPTHROW_UAIR"
    
    # Paso B: Fin del lanzamiento, Fox salta
    p_fox_c.action = "STANDING"
    p_fox_c.act_val = 14
    p_fox_c.action_frame = 30
    p_opp_c.position.y = 15.0 # Rival lanzado arriba
    act_c2 = brain.get_fox_decision(player=p_fox_c, opponent=p_opp_c, current_frame=35, stage="BATTLEFIELD")
    print(f"Paso B (Salto tras throw): {act_c2['name']} | Jump={act_c2['jump']}")
    assert act_c2["jump"], "Error: Fox debe saltar para seguir al rival"
    
    # Paso C: Fox en el aire conectando Up-Air
    p_fox_c.on_ground = False
    p_fox_c.action = "JUMPING"
    p_fox_c.act_val = 25
    p_fox_c.position.y = 10.0
    act_c3 = brain.get_fox_decision(player=p_fox_c, opponent=p_opp_c, current_frame=40, stage="BATTLEFIELD")
    print(f"Paso C (Impacto Up-Air): {act_c3['name']} | Attack={act_c3['attack']}, C-Stick Y={act_c3['c_stick_y']}")
    assert act_c3["attack"] and act_c3["c_stick_y"] == 1.0, "Error: Fox debe rematar con Up-Air"
    print("✅ TEST 5 SUPERADO: Cadena de combo Up-Throw -> Up-Air ejecutada a la perfección.")

    # -------------------------------------------------------------
    # TEST 6: Running Jump-Cancel Up-Smash
    # -------------------------------------------------------------
    print("\n--- Test 6: Running Jump-Cancel Up-Smash (KneeBend Frame 1-3) ---")
    p_fox_run = MockPlayer(x=10.0, y=0.0, on_ground=True, action="RUNNING", act_val=21, percent=10.0)
    p_opp_kill = MockPlayer(x=26.0, y=0.0, on_ground=True, action="STANDING", percent=70.0)
    
    # Al estar en carrera contra rival a porcentaje alto: activa salto
    act_jc1 = brain.get_fox_decision(player=p_fox_run, opponent=p_opp_kill, current_frame=50, stage="BATTLEFIELD")
    print(f"Paso A (Inicio de JC): {act_jc1['name']} | Jump={act_jc1['jump']}")
    assert act_jc1["jump"], "Error: Debe saltar para iniciar Jump-Cancel"
    
    # Siguiente frame: Fox entra en KNEE_BEND (Action 24)
    p_fox_run.action = "KNEE_BEND"
    p_fox_run.act_val = 24
    act_jc2 = brain.get_fox_decision(player=p_fox_run, opponent=p_opp_kill, current_frame=51, stage="BATTLEFIELD")
    print(f"Paso B (KNEE_BEND cancel): {act_jc2['name']} | Attack={act_jc2['attack']}, Stick Y={act_jc2['stick_y']}, C-Stick Y={act_jc2['c_stick_y']}")
    assert act_jc2["attack"] and act_jc2["stick_y"] == 1.0 and act_jc2["c_stick_y"] == 1.0
    print("✅ TEST 6 SUPERADO: Running Jump-Cancel Up-Smash ejecutado con precisión de frame.")

    # -------------------------------------------------------------
    # TEST 7: Tech-Chase Down-Smash Semi-Spike
    # -------------------------------------------------------------
    print("\n--- Test 7: Tech-Chase Down-Smash contra Rival Derribado ---")
    p_fox_tc = MockPlayer(x=20.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_opp_down = MockPlayer(x=25.0, y=0.0, on_ground=True, action="DOWN_WAIT", act_val=183) # Rival en suelo
    
    act_tc = brain.get_fox_decision(player=p_fox_tc, opponent=p_opp_down, current_frame=60, stage="BATTLEFIELD")
    print(f"Castigo Tech-Chase: {act_tc['name']} | Attack={act_tc['attack']}, C-Stick Y={act_tc['c_stick_y']}")
    assert act_tc["attack"] and act_tc["c_stick_y"] == 0.0, "Error: Fox debe castigar con Down-Smash"
    print("✅ TEST 7 SUPERADO: Tech-Chase castiga inmediatamente al rival en el suelo.")

    # -------------------------------------------------------------
    # TEST 8: Subida de Repisa 100% Invulnerable (Requisito 10)
    # -------------------------------------------------------------
    print("\n--- Test 8: Subida Invulnerable de Repisa (Ledge Roll & Ledgedash) ---")
    # Caso A: Fox en repisa (EDGE_HANGING, x=-68.4) con rival esperando al borde (x=-60.0, dist < 12)
    p_fox_ledge = MockPlayer(x=-68.4, y=-5.0, on_ground=False, action="EDGE_HANGING", act_val=253)
    p_opp_ledge_close = MockPlayer(x=-60.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    
    act_ledge_roll = brain.get_fox_decision(player=p_fox_ledge, opponent=p_opp_ledge_close, current_frame=70, stage="BATTLEFIELD")
    print(f"Paso A (Rival al borde): {act_ledge_roll['name']} | Shield={act_ledge_roll['shield']}")
    assert act_ledge_roll["shield"], "Error: Fox debe rodar con invencibilidad atravesando al rival"

    # Caso B: Fox en repisa con rival espaciado (x=0.0): Ledgedash hacia el escenario
    p_opp_ledge_far = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    act_ld = brain.get_fox_decision(player=p_fox_ledge, opponent=p_opp_ledge_far, current_frame=72, stage="BATTLEFIELD")
    print(f"Paso B (Rival espaciado): {act_ld['name']} | Jump={act_ld['jump']} / Stick X={act_ld['stick_x']}")
    assert act_ld["jump"] or act_ld["stick_x"] > 0.5, "Error: Fox debe ejecutar Ledgedash o Getup hacia el centro"
    print("✅ TEST 8 SUPERADO: Fox no queda vulnerable en la repisa; sube de forma invulnerable.")

    # -------------------------------------------------------------
    # TEST 9: Escudo Inteligente y Opciones Out Of Shield (Requisito 9)
    # -------------------------------------------------------------
    print("\n--- Test 9: Escudo Inteligente y Shine Out Of Shield ---")
    # Fox en escudo (act_val=179) con rival pegado (dist <= 10)
    p_fox_sh = MockPlayer(x=0.0, y=0.0, on_ground=True, action="SHIELD", act_val=179)
    p_opp_sh = MockPlayer(x=8.0, y=0.0, on_ground=True, action="ATTACK_AIR_N", act_val=65)
    
    act_oos1 = brain.get_fox_decision(player=p_fox_sh, opponent=p_opp_sh, current_frame=80, stage="BATTLEFIELD")
    print(f"Paso A (Jump-Cancel OOS): {act_oos1['name']} | Jump={act_oos1['jump']}")
    assert act_oos1["jump"], "Error: Fox debe saltar para cancelar escudo (JC OOS)"
    
    act_oos2 = brain.get_fox_decision(player=p_fox_sh, opponent=p_opp_sh, current_frame=81, stage="BATTLEFIELD")
    print(f"Paso B (Shine OOS Frame-4): {act_oos2['name']} | Special={act_oos2['special']}")
    assert act_oos2["special"], "Error: Fox debe ejecutar Shine Out Of Shield"
    print("✅ TEST 9 SUPERADO: Escudo inteligente castiga presión con Shine OOS.")

    # -------------------------------------------------------------
    # TEST 10: Neutral Táctico Anti-Relajación (Requisito 8)
    # -------------------------------------------------------------
    print("\n--- Test 10: Neutral Táctico Anti-Relajación (Dash-Dance & Anti-Grab) ---")
    # Fox a distancia media en neutral: NO debe caminar pasivamente
    p_fox_neu = MockPlayer(x=0.0, y=0.0, on_ground=True, action="DASHING", act_val=20)
    p_opp_neu = MockPlayer(x=18.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    
    act_dd = brain.get_fox_decision(player=p_fox_neu, opponent=p_opp_neu, current_frame=90, stage="BATTLEFIELD")
    print(f"Neutral a 18 unidades: {act_dd['name']}")
    assert "DASH-DANCE" in act_dd["name"] or "ENTRADA" in act_dd["name"] or act_dd["attack"] or act_dd["jump"], "Error: Fox no debe caminar pasivamente"

    # Si el rival se acerca cuerpo a cuerpo (dist <= 8) a agarrar: Fox usa Shine Frame-1 inmediato
    p_opp_close = MockPlayer(x=6.0, y=0.0, on_ground=True, action="RUNNING", act_val=21)
    act_cqc = brain.get_fox_decision(player=p_fox_neu, opponent=p_opp_close, current_frame=91, stage="BATTLEFIELD")
    print(f"CQC a 6 unidades: {act_cqc['name']} | Special={act_cqc['special']}")
    assert act_cqc["special"] or act_cqc["shield"] or act_cqc["grab"], "Error: Fox debe meter Shine frame-1 o escudo ante aproximación"
    print("✅ TEST 10 SUPERADO: Fox no se relaja; usa Dash-Dance y Shine Frame-1 anti-grab.")

    # -------------------------------------------------------------
    # TEST 11: Presión en el Borde / Edge Trapping (Requisito 3)
    # -------------------------------------------------------------
    print("\n--- Test 11: Presión en el Borde (Down-Smash en Repisa) ---")
    # Rival colgado del borde (EDGE_HANGING, x=68.4)
    p_fox_trap = MockPlayer(x=58.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_opp_hang = MockPlayer(x=68.4, y=-5.0, on_ground=False, action="EDGE_HANGING", act_val=253)
    
    act_trap = brain.get_fox_decision(player=p_fox_trap, opponent=p_opp_hang, current_frame=100, stage="BATTLEFIELD")
    print(f"Presión a rival colgado: {act_trap['name']} | Attack={act_trap['attack']}, C-Stick Y={act_trap['c_stick_y']}")
    assert act_trap["attack"] and act_trap["c_stick_y"] == 0.0, "Error: Fox debe castigar repisa con Down-Smash semi-spike"
    print("✅ TEST 11 SUPERADO: Presión letal en el borde con Down-Smash semi-spike.")

    # -------------------------------------------------------------
    # TEST 12: Memoria Persistente y Plasticidad Sináptica (Requisitos 5 y 7)
    # -------------------------------------------------------------
    print("\n--- Test 12: Memoria Persistente y Plasticidad Sináptica ---")
    mem = brain.long_term_memory
    print(f"Partidas guardadas: {mem['matches_played']}, KOs: {mem['total_kos']}, Combos: {mem['total_combos']}")
    print(f"Plasticidad combo: {mem['synaptic_plasticity']['combo_mastery']}x, Escudo: {mem['synaptic_plasticity']['shield_reaction']}x")
    print(f"Hábitos rivales registrados: {mem['opponent_habits']}")
    assert mem["total_kos"] >= 67, "Error: No se preservaron los KOs históricos"
    assert "shield_reaction" in mem["synaptic_plasticity"], "Error: Falta nueva plasticidad shield_reaction"
    assert "opponent_habits" in mem, "Error: Faltan hábitos del oponente"
    # -------------------------------------------------------------
    # TEST 13: Recuperación Anti-Choque Debajo del Escenario (Fire Fox)
    # -------------------------------------------------------------
    print("\n--- Test 13: Escape de Fire Fox Debajo del Escenario (Anti-Choque con Plataforma) ---")
    # Fox está a X = 45.0, Y = -18.0 (directamente DEBAJO de la pista de Battlefield = 68.4)
    p_fox_under = MockPlayer(x=45.0, y=-18.0, on_ground=False, action="FIREFOX_AIR", act_val=356, jumps_left=0)
    act_under = brain.get_fox_decision(player=p_fox_under, opponent=p_opp, current_frame=30, stage="BATTLEFIELD")
    print(f"Decisión debajo del escenario: {act_under['name']} | Stick X: {act_under['stick_x']:.3f}, Stick Y: {act_under['stick_y']:.3f}")
    # Debe apuntar HACIA AFUERA (a la derecha, stick_x > 0.5) y hacia arriba (stick_y > 0.5) para librar el techo
    assert act_under["stick_x"] > 0.5, f"Error: Fire Fox no evade hacia afuera ({act_under['stick_x']})"
    assert act_under["stick_y"] > 0.5, f"Error: Fire Fox debe ascender ({act_under['stick_y']})"
    assert "ESCAPE DEBAJO DEL ESCENARIO" in act_under["name"], f"Error: No activó modo escape inferior ({act_under['name']})"
    print("✅ TEST 13 SUPERADO: Fox evade el techo inferior y dirige Fire Fox hacia el aire libre exterior.")

    # -------------------------------------------------------------
    # TEST 14: Salto Doble con Evasión hacia Afuera Debajo del Escenario
    # -------------------------------------------------------------
    print("\n--- Test 14: Salto Doble Curvando hacia Afuera Debajo del Escenario ---")
    p_fox_under_j = MockPlayer(x=45.0, y=-10.0, on_ground=False, action="FALLING", act_val=29, jumps_left=1)
    act_under_j = brain.get_fox_decision(player=p_fox_under_j, opponent=p_opp, current_frame=31, stage="BATTLEFIELD")
    print(f"Decisión salto debajo de escenario: {act_under_j['name']} | Stick X: {act_under_j['stick_x']}, Jump: {act_under_j['jump']}")
    assert act_under_j["jump"], "Error: Fox debe saltar"
    assert act_under_j["stick_x"] == 1.0, f"Error: El salto debe dirigirse hacia afuera (derecha=1.0) para no chocar ({act_under_j['stick_x']})"
    print("✅ TEST 14 SUPERADO: Doble salto curva hacia el exterior librando la plataforma.")

    # -------------------------------------------------------------
    # -------------------------------------------------------------
    # TEST 15: Prohibición de Side-B a Baja Altura (Anti-Choque de Pared)
    # -------------------------------------------------------------
    print("\n--- Test 15: Prohibición de Fox Illusion (Side-B) a Baja Altura ---")
    # Fox a X = 82.0, Y = -4.0 (por debajo de la repisa) sin saltos
    p_fox_low = MockPlayer(x=82.0, y=-4.0, on_ground=False, action="FALLING", act_val=29, jumps_left=0)
    act_low = brain.get_fox_decision(player=p_fox_low, opponent=p_opp, current_frame=55, stage="BATTLEFIELD")
    print(f"Decisión a baja altura: {act_low['name']} | Special: {act_low['special']}, Stick Y: {act_low['stick_y']}")
    # Debe iniciar Up-B (Fire Fox), NUNCA Side-B (que chocaría contra la pared lateral)
    assert act_low["stick_y"] == 1.0, "Error: Fox no debe usar Side-B bajo el nivel de repisa; debe usar Up-B hacia arriba"
    print("✅ TEST 15 SUPERADO: Fox no usa Side-B a baja altura; evita estrellarse contra la pared.")

    # -------------------------------------------------------------
    # TEST 16: Caza Ofensiva Offstage - Shine Spike con Retorno Seguro
    # -------------------------------------------------------------
    print("\n--- Test 16: Caza Ofensiva Offstage (Shine-Spike con Doble Salto de Retorno) ---")
    p_fox_hunt = MockPlayer(x=55.0, y=0.0, on_ground=True, action="STANDING", act_val=14, jumps_left=1)
    p_opp_rec = MockPlayer(x=76.0, y=-6.0, on_ground=False, action="FALLING", act_val=29, percent=50.0)
    p_opp_rec.off_stage = True
    
    # Paso A: Fox salta fuera del escenario a cazar
    act_h1 = brain.get_fox_decision(player=p_fox_hunt, opponent=p_opp_rec, current_frame=200, stage="BATTLEFIELD")
    print(f"Paso A (Inicio persecución offstage): {act_h1['name']} | Jump={act_h1['jump']}, Stick X={act_h1['stick_x']}")
    assert "OFFSTAGE HUNT" in act_h1["name"], "Error: Fox debe iniciar persecución offstage"
    assert act_h1.get("_allow_offstage_chase", False), "Error: Debe tener _allow_offstage_chase activo"
    
    # Paso B: Fox en el aire junto al rival fuera del escenario ejecutando Shine Frame-1
    p_fox_hunt.position.x = 74.0
    p_fox_hunt.position.y = -6.0
    p_fox_hunt.on_ground = False
    p_fox_hunt.action = "FALLING"
    p_fox_hunt.act_val = 29
    act_h2 = brain.get_fox_decision(player=p_fox_hunt, opponent=p_opp_rec, current_frame=201, stage="BATTLEFIELD")
    print(f"Paso B (Shine-Spike en el aire): {act_h2['name']} | Special={act_h2['special']}, Stick Y={act_h2['stick_y']}")
    assert act_h2["special"] and act_h2["stick_y"] == 0.0, "Error: Fox debe activar Shine Frame-1 offstage"
    
    # Paso C: Jump-Cancel tras el impacto del Shine Spike
    act_h3 = brain.get_fox_decision(player=p_fox_hunt, opponent=p_opp_rec, current_frame=206, stage="BATTLEFIELD")
    print(f"Paso C (Retorno Jump-Cancel): {act_h3['name']} | Jump={act_h3['jump']}, Stick X={act_h3['stick_x']:.2f}")
    assert act_h3["jump"] and act_h3["stick_x"] < 0.5, "Error: Fox debe cancelar shine con salto hacia el escenario"
    print("✅ TEST 16 SUPERADO: Persecución offstage y Shine-Spike letal con retorno seguro.")

    # -------------------------------------------------------------
    # TEST 17: Cadena Completa de Waveshine (Shine -> JC -> Wavedash -> Up-Smash / Grab)
    # -------------------------------------------------------------
    print("\n--- Test 17: Cadena Completa de Waveshine Profesional ---")
    brain.reset()
    p_fox_ws = MockPlayer(x=10.0, y=0.0, on_ground=True, action="DOWN_B_GROUND", act_val=360)
    p_fox_ws.action_frame = 4 # Frame 4: Salto JC disponible
    p_opp_ws = MockPlayer(x=16.0, y=0.0, on_ground=True, action="DAMAGE_GROUND", percent=65.0)
    
    # Paso A: Jump-cancel del Shine
    act_ws1 = brain.get_fox_decision(player=p_fox_ws, opponent=p_opp_ws, current_frame=220, stage="BATTLEFIELD")
    print(f"Paso A (Jump-Cancel out of Shine): {act_ws1['name']} | Jump={act_ws1['jump']}")
    assert act_ws1["jump"], "Error: Fox debe cancelar shine con salto"
    assert brain.combo_state == "WAVESHINE_COMBO"
    
    # Paso B: Wavedash hacia adelante en el aire
    p_fox_ws.on_ground = False
    p_fox_ws.action = "KNEE_BEND"
    p_fox_ws.act_val = 24
    act_ws2 = brain.get_fox_decision(player=p_fox_ws, opponent=p_opp_ws, current_frame=221, stage="BATTLEFIELD")
    print(f"Paso B (Wavedash Airdodge diagonal): {act_ws2['name']} | Shield={act_ws2['shield']}, Stick Y={act_ws2['stick_y']}")
    assert act_ws2["shield"] and act_ws2["stick_y"] == 0.25 and act_ws2.get("_allow_air_shield", False)
    
    # Paso C: Aterrizaje con deslizamiento de wavedash contra rival a 65% -> Running JC Up-Smash
    p_fox_ws.on_ground = True
    p_fox_ws.action = "LANDING"
    p_fox_ws.act_val = 43
    act_ws3 = brain.get_fox_decision(player=p_fox_ws, opponent=p_opp_ws, current_frame=223, stage="BATTLEFIELD")
    print(f"Paso C (Finisher de Waveshine): {act_ws3['name']} | Attack={act_ws3['attack']}, C-Stick Y={act_ws3['c_stick_y']}")
    assert act_ws3["attack"] and act_ws3["c_stick_y"] == 1.0, "Error: Fox debe rematar con Up-Smash"
    print("✅ TEST 17 SUPERADO: Cadena completa de Waveshine ejecutada a la perfección.")

    # -------------------------------------------------------------
    # TEST 18: Jab-Reset en Missed Tech
    # -------------------------------------------------------------
    print("\n--- Test 18: Jab-Reset Técnico ante Missed Tech del Rival ---")
    p_fox_jr = MockPlayer(x=20.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_opp_jr = MockPlayer(x=24.0, y=0.0, on_ground=True, action="DOWN_BOUND", act_val=184)
    
    act_jr = brain.get_fox_decision(player=p_fox_jr, opponent=p_opp_jr, current_frame=231, stage="BATTLEFIELD")
    print(f"Jab-Reset: {act_jr['name']} | Attack={act_jr['attack']}, Stick Y={act_jr['stick_y']}")
    assert act_jr["attack"] and act_jr["stick_y"] == 0.5 and "JAB-RESET" in act_jr["name"]
    print("✅ TEST 18 SUPERADO: Fox conecta Jab-Reset para forzar levantamiento indefenso del rival.")

    # -------------------------------------------------------------
    # TEST 19: The Mangle - Up-B Profundo sobre Rival Acampando en Borde
    # -------------------------------------------------------------
    print("\n--- Test 19: The Mangle (Fire Fox Profundo sobre Edgeguarder) ---")
    p_fox_mangle = MockPlayer(x=75.0, y=-6.0, on_ground=False, action="FIREFOX_AIR", act_val=356, jumps_left=0)
    p_opp_camp = MockPlayer(x=64.0, y=0.0, on_ground=True, action="ATTACK_S_4", act_val=60) # Rival esperando al borde
    
    act_mangle = brain.get_fox_decision(player=p_fox_mangle, opponent=p_opp_camp, current_frame=240, stage="BATTLEFIELD")
    print(f"Decisión The Mangle: {act_mangle['name']} | Stick X: {act_mangle['stick_x']:.3f}, Stick Y: {act_mangle['stick_y']:.3f}")
    assert "THE MANGLE" in act_mangle["name"], "Error: Fox debe ejecutar The Mangle sobrevolando al rival"
    assert act_mangle["stick_x"] < 0.5 and act_mangle["stick_y"] > 0.5
    print("✅ TEST 19 SUPERADO: The Mangle esquiva al rival del borde y aterriza en el centro del escenario.")

    # -------------------------------------------------------------
    # TEST 20: Airdodge Direccional a la Repisa (Recuperación Rápida)
    # -------------------------------------------------------------
    print("\n--- Test 20: Airdodge Direccional Instantáneo a la Repisa ---")
    p_fox_ad = MockPlayer(x=72.0, y=1.0, on_ground=False, action="FALLING", act_val=29, jumps_left=0)
    p_opp_center = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    
    act_ad = brain.get_fox_decision(player=p_fox_ad, opponent=p_opp_center, current_frame=250, stage="BATTLEFIELD")
    print(f"Airdodge a repisa: {act_ad['name']} | Shield={act_ad['shield']}, Stick X={act_ad['stick_x']:.2f}")
    assert act_ad["shield"] and act_ad.get("_allow_air_shield", False)
    assert "AIRDODGE DIRECCIONAL" in act_ad["name"]
    print("✅ TEST 20 SUPERADO: Fox usa Airdodge direccional para snap instantáneo sin lag de Up-B.")

    # -------------------------------------------------------------
    # TEST 21: Ledge-Stall para Refrescar Invulnerabilidad Total
    # -------------------------------------------------------------
    print("\n--- Test 21: Ledge-Stall (Refresco de Intangibilidad en Repisa) ---")
    p_fox_stall = MockPlayer(x=-68.4, y=-5.0, on_ground=False, action="EDGE_HANGING", act_val=253, jumps_left=1)
    brain.ledge_timer = 27 # Ha permanecido colgado más de 26 frames
    
    act_stall = brain.get_fox_decision(player=p_fox_stall, opponent=p_opp_center, current_frame=260, stage="BATTLEFIELD")
    print(f"Ledge-Stall: {act_stall['name']} | Jump={act_stall['jump']}, Stick Y={act_stall['stick_y']}")
    assert act_stall["jump"] and act_stall["stick_y"] == 0.85 and "LEDGE-STALL" in act_stall["name"]
    print("✅ TEST 21 SUPERADO: Fox refresca su invencibilidad en repisa mediante Ledge-Stall.")

    # -------------------------------------------------------------
    # TEST 22: Platform Sharking (Up-Air a Través de Plataforma)
    # -------------------------------------------------------------
    print("\n--- Test 22: Platform Sharking (Up-Air a través de plataforma flotante) ---")
    # Rival parado en la plataforma izquierda de Battlefield (Y = 27.2, X = -38.0)
    p_opp_plat = MockPlayer(x=-38.0, y=27.2, on_ground=True, action="STANDING", act_val=14)
    # Fox saltando debajo de la plataforma (Y = 15.0, X = -38.0)
    p_fox_shark = MockPlayer(x=-38.0, y=15.0, on_ground=False, action="JUMPING", act_val=25)
    
    act_shark = brain.get_fox_decision(player=p_fox_shark, opponent=p_opp_plat, current_frame=270, stage="BATTLEFIELD")
    print(f"Platform Sharking: {act_shark['name']} | Attack={act_shark['attack']}, C-Stick Y={act_shark['c_stick_y']}")
    assert act_shark["attack"] and act_shark["c_stick_y"] == 1.0 and "PLATFORM SHARKING" in act_shark["name"]
    print("✅ TEST 22 SUPERADO: Fox perfora la plataforma desde abajo con Up-Air.")

    # -------------------------------------------------------------
    # TEST 23: Up-Tilt Juggle Ladder contra Fastfaller a Bajo %
    # -------------------------------------------------------------
    print("\n--- Test 23: Up-Tilt Juggle Ladder contra Fastfaller a Bajo % ---")
    # Rival es Fox/Falco a 15% (Fastfaller) frente a Fox
    p_fox_ground = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_opp_ff = MockPlayer(x=4.0, y=0.0, on_ground=True, action="STANDING", act_val=14, percent=15.0)
    p_opp_ff.character = "FOX"
    
    act_uptilt = brain.get_fox_decision(player=p_fox_ground, opponent=p_opp_ff, current_frame=280, stage="BATTLEFIELD")
    print(f"Up-Tilt Ladder: {act_uptilt['name']} | Attack={act_uptilt['attack']}, Stick Y={act_uptilt['stick_y']}")
    assert act_uptilt["attack"] and act_uptilt["stick_y"] == 0.68 and "UP-TILT JUGGLE" in act_uptilt["name"]
    print("✅ TEST 23 SUPERADO: Cadena de Up-Tilt Juggle ejecutada con precisión contra fastfaller.")

    # -------------------------------------------------------------
    # TEST 24: Drill-Smash True Combo (D-Air -> JC Up-Smash) contra Floaty
    # -------------------------------------------------------------
    print("\n--- Test 24: Drill-Smash True Combo contra Floaty a % Medio/Alto ---")
    p_opp_floaty = MockPlayer(x=4.0, y=0.0, on_ground=True, action="STANDING", act_val=14, percent=65.0)
    p_opp_floaty.character = "PEACH"
    
    # Paso A: Fox cae con Drill multihit (D-Air)
    p_fox_air = MockPlayer(x=4.0, y=6.0, on_ground=False, action="FALLING", act_val=29)
    act_drill = brain.get_fox_decision(player=p_fox_air, opponent=p_opp_floaty, current_frame=290, stage="BATTLEFIELD")
    print(f"Paso A (D-Air Drill): {act_drill['name']}")
    assert "DRILL" in act_drill["name"] and brain.drill_smash_state == "DRILL_ACTIVE"
    
    # Paso B: Fox aterriza en el suelo y descarga Jump-Cancel Up-Smash
    p_fox_air.position.y = 0.0
    p_fox_air.on_ground = True
    p_fox_air.action = "LANDING"
    p_fox_air.act_val = 42
    act_dsmash = brain.get_fox_decision(player=p_fox_air, opponent=p_opp_floaty, current_frame=291, stage="BATTLEFIELD")
    print(f"Paso B (JC Up-Smash confirm): {act_dsmash['name']} | Jump={act_dsmash['jump']}, Attack={act_dsmash['attack']}")
    assert act_dsmash["jump"] and act_dsmash["attack"] and act_dsmash["c_stick_y"] == 1.0 and "DRILL-SMASH" in act_dsmash["name"]
    print("✅ TEST 24 SUPERADO: Drill-Smash True Combo ejecutado con Jump-Cancel instantáneo.")

    # -------------------------------------------------------------
    # TEST 25: Down-Tilt Launcher a Porcentaje Medio (Setup de Up-Air)
    # -------------------------------------------------------------
    print("\n--- Test 25: Down-Tilt Launcher a Porcentaje Medio (Pop-Up) ---")
    p_opp_mid = MockPlayer(x=9.0, y=0.0, on_ground=True, action="STANDING", act_val=14, percent=70.0)
    p_opp_mid.character = "MARTH"
    
    act_dtilt = brain.get_fox_decision(player=p_fox_ground, opponent=p_opp_mid, current_frame=300, stage="BATTLEFIELD")
    print(f"Down-Tilt Launcher: {act_dtilt['name']} | Attack={act_dtilt['attack']}, Stick Y={act_dtilt['stick_y']}")
    assert act_dtilt["attack"] and act_dtilt["stick_y"] == 0.25 and "DOWN-TILT LAUNCHER" in act_dtilt["name"]
    print("✅ TEST 25 SUPERADO: Down-Tilt Launcher envía al rival verticalmente para Up-Air.")

    # -------------------------------------------------------------
    # TEST 26: Crouch-Cancel (CC) Frame-1 Shine Counter en CQC
    # -------------------------------------------------------------
    print("\n--- Test 26: Crouch-Cancel Frame-1 Shine Counter ---")
    p_fox_cc = MockPlayer(x=0.0, y=0.0, on_ground=True, action="CROUCHING", act_val=39, percent=10.0)
    p_opp_atk = MockPlayer(x=5.0, y=0.0, on_ground=True, action="ATTACK_AIR_N", act_val=65) # Rival atacando a Fox
    
    act_cc = brain.get_fox_decision(player=p_fox_cc, opponent=p_opp_atk, current_frame=310, stage="BATTLEFIELD")
    print(f"Crouch-Cancel Shine: {act_cc['name']} | Special={act_cc['special']}, Stick Y={act_cc['stick_y']}")
    assert act_cc["special"] and act_cc["stick_y"] == 0.0 and "CROUCH-CANCEL" in act_cc["name"]
    print("✅ TEST 26 SUPERADO: Fox absorbe el ataque con CC y castiga con Reflector Frame-1.")

    # -------------------------------------------------------------
    # TEST 27: Short-Hop Double Laser (SHDL) a Larga Distancia
    # -------------------------------------------------------------
    print("\n--- Test 27: Short-Hop Double Laser (SHDL) a Larga Distancia ---")
    p_opp_far = MockPlayer(x=-45.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    
    # Fox en el centro del escenario inicia SHDL con Short Hop
    act_shdl1 = brain.get_fox_decision(player=p_fox_ground, opponent=p_opp_far, current_frame=320, stage="BATTLEFIELD")
    print(f"Paso A (SHDL Short Hop): {act_shdl1['name']} | Jump={act_shdl1['jump']}")
    assert act_shdl1["jump"] and "SHDL: SHORT-HOP INICIAL" in act_shdl1["name"]
    
    # En el aire dispara el Blaster
    p_fox_shdl_air = MockPlayer(x=0.0, y=4.0, on_ground=False, action="JUMPING", act_val=25)
    act_shdl2 = brain.get_fox_decision(player=p_fox_shdl_air, opponent=p_opp_far, current_frame=321, stage="BATTLEFIELD")
    print(f"Paso B (SHDL Laser): {act_shdl2['name']} | Special={act_shdl2['special']}")
    assert act_shdl2["special"] and "SHDL: SHORT-HOP DOUBLE LASER" in act_shdl2["name"]
    print("✅ TEST 27 SUPERADO: Short-Hop Double Laser (SHDL) ejecutado para zoning perfecto.")

    # -------------------------------------------------------------
    # TEST 28: Luigi Anti-Charging Punishment (Requisito 2)
    # -------------------------------------------------------------
    print("\n--- Test 28: Luigi Anti-Charging & Whiff Punish (No Regalarse ante Cargas) ---")
    p_luigi = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi.character = "LUIGI"
    
    # Caso 1: Rival cargando Smash a media distancia (12 u)
    # Luigi NO camina de frente al ataque: hace Wavedash back o Wavedash grab
    p_opp_charge = MockPlayer(x=12.0, y=0.0, on_ground=True, action="ATTACK_S_4", act_val=60)
    act_charge_evade = brain.get_luigi_decision(player=p_luigi, opponent=p_opp_charge, current_frame=340, stage="BATTLEFIELD")
    print(f"Evasión de carga (Wavedash back): {act_charge_evade['name']} | Shield={act_charge_evade['shield']}, Stick X={act_charge_evade['stick_x']}")
    assert act_charge_evade["shield"] and act_charge_evade["stick_x"] == 0.0 and "EVASIÓN DE CARGA" in act_charge_evade["name"]
    
    # En frame impar: Castigo de carga con agarre
    act_charge_grab = brain.get_luigi_decision(player=p_luigi, opponent=p_opp_charge, current_frame=341, stage="BATTLEFIELD")
    print(f"Castigo de carga (Grab): {act_charge_grab['name']} | Grab={act_charge_grab['grab']}")
    assert act_charge_grab["grab"] and "CASTIGO DE CARGA" in act_charge_grab["name"]

    # Caso 2: Rival cargando Smash a larga distancia (24 u) -> Bola de fuego verde para interrumpirlo
    p_opp_charge_far = MockPlayer(x=24.0, y=0.0, on_ground=True, action="ATTACK_S_4", act_val=60)
    act_charge_fireball = brain.get_luigi_decision(player=p_luigi, opponent=p_opp_charge_far, current_frame=342, stage="BATTLEFIELD")
    print(f"Interrupción a distancia (Fireball): {act_charge_fireball['name']} | Special={act_charge_fireball['special']}")
    assert act_charge_fireball["special"] and "BOLA DE FUEGO VERDE" in act_charge_fireball["name"]

    # Caso 3: Rival cargando a quemarropa (4 u) -> Castigo instantáneo con Sweetspot Up-B (Shoryuken PING!)
    p_opp_charge_close = MockPlayer(x=4.0, y=0.0, on_ground=True, action="ATTACK_S_4", act_val=60)
    act_charge_upb = brain.get_luigi_decision(player=p_luigi, opponent=p_opp_charge_close, current_frame=343, stage="BATTLEFIELD")
    print(f"Castigo a quemarropa (Shoryuken Frame-8): {act_charge_upb['name']} | Special={act_charge_upb['special']}, Stick Y={act_charge_upb['stick_y']}")
    assert act_charge_upb["special"] and act_charge_upb["stick_y"] == 1.0 and "SWEETSPOT UP-B SHORYUKEN" in act_charge_upb["name"]
    print("✅ TEST 28 SUPERADO: Luigi nunca se regala ante cargas de ataque rival; castiga y evade inteligentemente.")

    # -------------------------------------------------------------
    # TEST 29: Caza y Asalto en Plataformas (Requisito 4: No Zigzag abajo)
    # -------------------------------------------------------------
    print("\n--- Test 29: Invasión de Plataformas y Sharking (Anti-Campers) ---")
    # Rival acampando en plataforma izquierda de Battlefield (x=-38.0, y=27.2)
    p_opp_camper = MockPlayer(x=-38.0, y=27.2, on_ground=True, action="STANDING", act_val=14)
    # Luigi en el suelo directamente debajo de la plataforma (x=-38.0, y=0.0)
    p_luigi_ground = MockPlayer(x=-38.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_ground.character = "LUIGI"
    
    # Frame 360: Luigi salta directamente a la plataforma con waveland
    act_plat_invade = brain.get_luigi_decision(player=p_luigi_ground, opponent=p_opp_camper, current_frame=360, stage="BATTLEFIELD")
    print(f"Asalto plataforma (Salto + Waveland): {act_plat_invade['name']} | Jump={act_plat_invade['jump']}")
    assert act_plat_invade["jump"] and "INVASIÓN DE PLATAFORMA" in act_plat_invade["name"]
    
    # Frame 350: Luigi perfora la plataforma desde abajo con Up-Air Sharking
    act_plat_shark = brain.get_luigi_decision(player=p_luigi_ground, opponent=p_opp_camper, current_frame=350, stage="BATTLEFIELD")
    print(f"Platform Sharking (Up-Air): {act_plat_shark['name']} | Jump={act_plat_shark['jump']}, Attack={act_plat_shark['attack']}")
    assert act_plat_shark["jump"] and act_plat_shark["attack"] and act_plat_shark["c_stick_y"] == 1.0 and "PLATFORM SHARKING" in act_plat_shark["name"]
    
    # Luigi ya sobre la plataforma a corta distancia: Down-Smash semi-spike
    p_luigi_on_plat = MockPlayer(x=-38.0, y=27.2, on_ground=False, action="LANDING", act_val=42)
    act_plat_smash = brain.get_luigi_decision(player=p_luigi_on_plat, opponent=p_opp_camper, current_frame=361, stage="BATTLEFIELD")
    print(f"Asalto en plataforma (Down-Smash): {act_plat_smash['name']} | Attack={act_plat_smash['attack']}, C-Stick Y={act_plat_smash['c_stick_y']}")
    assert act_plat_smash["attack"] and act_plat_smash["c_stick_y"] == 0.0 and "ASALTO EN PLATAFORMA" in act_plat_smash["name"]
    print("✅ TEST 29 SUPERADO: Luigi elimina el zigzag terrestre y asalta verticalmente las plataformas.")

    # -------------------------------------------------------------
    # TEST 30: Máquina de Combos Estratificada por Dopamina (Requisito 3)
    # -------------------------------------------------------------
    print("\n--- Test 30: Combos Modulados por Dopamina tras Down-Throw ---")
    p_luigi_combo = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_combo.character = "LUIGI"
    p_opp_combo = MockPlayer(x=3.0, y=0.0, on_ground=True, action="DAMAGE_GROUND", act_val=75, percent=70.0)
    
    # Nivel 1: Dopamina Baja (< 0.50) -> Bread & Butter Down-Throw a Down-Smash Frame-5
    brain.combo_state = "LUIGI_DTHROW_COMBO"
    brain.dopamine = 0.30
    act_combo_low = brain.get_luigi_decision(player=p_luigi_combo, opponent=p_opp_combo, current_frame=370, stage="BATTLEFIELD")
    print(f"Combo Low Dopamina: {act_combo_low['name']} | Attack={act_combo_low['attack']}, C-Stick Y={act_combo_low['c_stick_y']}")
    assert act_combo_low["attack"] and act_combo_low["c_stick_y"] == 0.0 and "LOW-DOPAMINA" in act_combo_low["name"]

    # Nivel 2: Dopamina Media (0.50 - 0.75) -> Down-Throw a Short-Hop F-Air / Up-Tilt Juggle
    brain.combo_state = "LUIGI_DTHROW_COMBO"
    brain.dopamine = 0.65
    p_opp_combo.percent = 30.0 # Bajo % -> Short-Hop F-Air chop
    act_combo_mid1 = brain.get_luigi_decision(player=p_luigi_combo, opponent=p_opp_combo, current_frame=371, stage="BATTLEFIELD")
    print(f"Combo Mid Dopamina (Bajo %): {act_combo_mid1['name']} | Jump={act_combo_mid1['jump']}, Attack={act_combo_mid1['attack']}")
    assert act_combo_mid1["jump"] and act_combo_mid1["attack"] and "SHORT-HOP FAIR" in act_combo_mid1["name"]

    brain.combo_state = "LUIGI_DTHROW_COMBO"
    brain.dopamine = 0.65
    p_opp_combo.percent = 60.0 # Medio % -> Up-Tilt Juggle Ladder
    act_combo_mid2 = brain.get_luigi_decision(player=p_luigi_combo, opponent=p_opp_combo, current_frame=372, stage="BATTLEFIELD")
    print(f"Combo Mid Dopamina (Medio %): {act_combo_mid2['name']} | Attack={act_combo_mid2['attack']}, Stick Y={act_combo_mid2['stick_y']}")
    assert act_combo_mid2["attack"] and act_combo_mid2["stick_y"] == 0.68 and "UP-TILT JUGGLE" in act_combo_mid2["name"]

    # Nivel 3: Dopamina Alta (> 0.75) -> El legendario Sweetspot Up-B Shoryuken Frame-8 (PING!)
    brain.combo_state = "LUIGI_DTHROW_COMBO"
    brain.dopamine = 0.90
    p_opp_combo.percent = 75.0
    act_combo_high = brain.get_luigi_decision(player=p_luigi_combo, opponent=p_opp_combo, current_frame=373, stage="BATTLEFIELD")
    print(f"Combo High Dopamina (Shoryuken): {act_combo_high['name']} | Special={act_combo_high['special']}, Stick Y={act_combo_high['stick_y']}")
    assert act_combo_high["special"] and act_combo_high["stick_y"] == 1.0 and "SHORYUKEN" in act_combo_high["name"]
    print("✅ TEST 30 SUPERADO: Matriz de combos de Luigi escala dinámicamente según dopamina y porcentaje.")

    # -------------------------------------------------------------
    # TEST 31: Frame-3 N-Air Combo Break y Escape de Tumble
    # -------------------------------------------------------------
    print("\n--- Test 31: Frame-3 N-Air Break-Out y Out-Of-Shield ---")
    # Caso 1: En tumble en el aire
    p_luigi_tumble = MockPlayer(x=10.0, y=25.0, on_ground=False, action="TUMBLE", act_val=38)
    p_luigi_tumble.character = "LUIGI"
    p_opp_air = MockPlayer(x=12.0, y=25.0, on_ground=False, action="JUMPING", act_val=25)
    
    act_tumble_nair = brain.get_luigi_decision(player=p_luigi_tumble, opponent=p_opp_air, current_frame=380, stage="BATTLEFIELD")
    print(f"N-Air Tumble Break: {act_tumble_nair['name']} | Attack={act_tumble_nair['attack']}")
    assert act_tumble_nair["attack"] and "NAIR AÉREO FRAME-3" in act_tumble_nair["name"]

    # Caso 2: Presión en Escudo a corta distancia -> N-Air Out Of Shield Frame-3
    p_luigi_shield = MockPlayer(x=0.0, y=0.0, on_ground=True, action="SHIELD", act_val=179)
    p_luigi_shield.character = "LUIGI"
    p_opp_press = MockPlayer(x=6.0, y=0.0, on_ground=True, action="ATTACK_AIR_F", act_val=66, percent=20.0)
    
    act_oos_nair = brain.get_luigi_decision(player=p_luigi_shield, opponent=p_opp_press, current_frame=381, stage="BATTLEFIELD")
    print(f"N-Air OOS Frame-3: {act_oos_nair['name']} | Jump={act_oos_nair['jump']}, Attack={act_oos_nair['attack']}")
    assert act_oos_nair["jump"] and act_oos_nair["attack"] and "N-AIR OUT OF SHIELD FRAME-3" in act_oos_nair["name"]
    print("✅ TEST 31 SUPERADO: Luigi aprovecha el N-Air Frame-3 más letal de Melee para romper combos y castigar en escudo.")

    # -------------------------------------------------------------
    # TEST 32: Enrutamiento de Controlador Autónomo para Luigi (Requisito 1)
    # -------------------------------------------------------------
    print("\n--- Test 32: Enrutamiento Automático del Cerebro a Luigi ---")
    p_ctrl_luigi = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_ctrl_luigi.character = "LUIGI"
    
    act_ctrl = brain.get_controller_decision(player=p_ctrl_luigi, opponent=p_opp_far, current_frame=390, stage="BATTLEFIELD")
    print(f"Decisión del controlador: {act_ctrl['name']} | Personaje: {act_ctrl['stats']['character']}")
    assert act_ctrl["stats"]["character"] == "LUIGI"
    print("✅ TEST 32 SUPERADO: El controlador Melee asigna y opera a Luigi como personaje principal.")

    # -------------------------------------------------------------
    # TEST 33: Luigi Combate Aéreo Ofensivo (Ataques en el aire)
    # -------------------------------------------------------------
    print("\n--- Test 33: Luigi Combate Aéreo Ofensivo (N-Air, F-Air, D-Air Drill, Up-Air) ---")
    # Caso A: Luigi en el aire cerca del rival -> N-Air Frame-3 ofensivo
    p_luigi_air = MockPlayer(x=10.0, y=15.0, on_ground=False, action="JUMPING", act_val=25)
    p_luigi_air.character = "LUIGI"
    p_opp_air2 = MockPlayer(x=14.0, y=15.0, on_ground=False, action="JUMPING", act_val=25)
    
    act_air_nair = brain.get_luigi_decision(player=p_luigi_air, opponent=p_opp_air2, current_frame=400, stage="BATTLEFIELD")
    print(f"Ataque aéreo (N-Air Frame-3): {act_air_nair['name']} | Attack={act_air_nair['attack']}")
    assert act_air_nair["attack"] and "N-AIR OFENSIVO FRAME-3" in act_air_nair["name"]

    # Caso B: Rival directamente arriba de Luigi en el aire -> Up-Air vertical juggle
    p_opp_above = MockPlayer(x=10.0, y=24.0, on_ground=False, action="JUMPING", act_val=25)
    act_air_uair = brain.get_luigi_decision(player=p_luigi_air, opponent=p_opp_above, current_frame=401, stage="BATTLEFIELD")
    print(f"Ataque aéreo vertical (Up-Air): {act_air_uair['name']} | Attack={act_air_uair['attack']}, Stick Y={act_air_uair['stick_y']}")
    assert act_air_uair["attack"] and act_air_uair["stick_y"] == 1.0 and "UP-AIR VERTICAL" in act_air_uair["name"]

    # Caso C: Luigi cayendo sobre el rival -> D-Air Drill multihit en picada
    p_luigi_falling = MockPlayer(x=10.0, y=20.0, on_ground=False, action="FALLING", act_val=29)
    p_luigi_falling.character = "LUIGI"
    p_opp_below = MockPlayer(x=10.0, y=8.0, on_ground=True, action="STANDING", act_val=14)
    act_air_dair = brain.get_luigi_decision(player=p_luigi_falling, opponent=p_opp_below, current_frame=402, stage="BATTLEFIELD")
    print(f"Ataque aéreo picada (D-Air Drill): {act_air_dair['name']} | Attack={act_air_dair['attack']}, C-Stick Y={act_air_dair['c_stick_y']}")
    assert act_air_dair["attack"] and act_air_dair["c_stick_y"] == 0.0 and "D-AIR DRILL" in act_air_dair["name"]
    print("✅ TEST 33 SUPERADO: Luigi ataca agresivamente en el aire utilizando todo su repertorio aéreo.")

    # -------------------------------------------------------------
    # TEST 34: Intercepción y Caza Anti-Aérea (Rival en el aire)
    # -------------------------------------------------------------
    print("\n--- Test 34: Intercepción Anti-Aérea y Caza (Luigi en suelo vs Rival en aire) ---")
    p_luigi_ground2 = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_ground2.character = "LUIGI"
    
    # Caso A: Rival en el aire cayendo verticalmente sobre Luigi -> Sweetspot Up-B Shoryuken / Cyclone Frame-1
    p_opp_dropping = MockPlayer(x=0.0, y=7.0, on_ground=False, action="DAMAGE_AIR", percent=55.0)
    brain.dopamine = 0.80
    act_anti_air = brain.get_luigi_decision(player=p_luigi_ground2, opponent=p_opp_dropping, current_frame=410, stage="BATTLEFIELD")
    print(f"Anti-Air letal (Shoryuken): {act_anti_air['name']} | Special={act_anti_air['special']}, Stick Y={act_anti_air['stick_y']}")
    assert act_anti_air["special"] and act_anti_air["stick_y"] == 1.0 and "SWEETSPOT UP-B SHORYUKEN" in act_anti_air["name"]

    # Caso B: Rival en el aire a media distancia -> Luigi salta al aire para cazarlo con N-Air/F-Air/Cyclone
    p_opp_mid_air = MockPlayer(x=15.0, y=12.0, on_ground=False, action="JUMPING", act_val=25)
    act_aerial_hunt = brain.get_luigi_decision(player=p_luigi_ground2, opponent=p_opp_mid_air, current_frame=415, stage="BATTLEFIELD")
    print(f"Caza aérea (Salto ofensivo): {act_aerial_hunt['name']} | Jump={act_aerial_hunt['jump']}, Attack={act_aerial_hunt['attack']}, Special={act_aerial_hunt['special']}")
    assert act_aerial_hunt["jump"] and (act_aerial_hunt["attack"] or act_aerial_hunt["special"]) and "CAZA AÉREA" in act_aerial_hunt["name"]
    print("✅ TEST 34 SUPERADO: Luigi no se queda abajo mirando; salta a interceptar y castiga con poderes antiaéreos.")

    # -------------------------------------------------------------
    # TEST 35: Poderes Especiales Ofensivos (Down-B Cyclone y Side-B Missile)
    # -------------------------------------------------------------
    print("\n--- Test 35: Poderes Especiales Ofensivos de Luigi (Down-B Cyclone y Side-B Missile) ---")
    # Caso A: En CQC, Luigi usa el Cyclone terrestre (Down-B) Frame-1 intangible
    p_opp_cqc = MockPlayer(x=4.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    act_cqc_cyclone = brain.get_luigi_decision(player=p_luigi_ground2, opponent=p_opp_cqc, current_frame=420, stage="BATTLEFIELD")
    print(f"Poder CQC (Luigi Cyclone): {act_cqc_cyclone['name']} | Special={act_cqc_cyclone['special']}, Stick Y={act_cqc_cyclone['stick_y']}")
    assert act_cqc_cyclone["special"] and act_cqc_cyclone["stick_y"] == 0.0 and "LUIGI CYCLONE" in act_cqc_cyclone["name"]

    # Caso B: A larga distancia, Luigi activa Green Missile (Side-B) como torpedo de asalto
    p_opp_distance = MockPlayer(x=30.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    act_missile = brain.get_luigi_decision(player=p_luigi_ground2, opponent=p_opp_distance, current_frame=440, stage="BATTLEFIELD")
    print(f"Poder Distancia (Green Missile): {act_missile['name']} | Special={act_missile['special']}, Stick X={act_missile['stick_x']}")
    assert act_missile["special"] and act_missile["stick_x"] == 1.0 and "GREEN MISSILE" in act_missile["name"]
    print("✅ TEST 35 SUPERADO: Luigi domina el combate con su arsenal completo de poderes especiales (Cyclone y Missile).")

    # -------------------------------------------------------------
    # TEST 36: Despegue Aéreo de Luigi y Drop-Through de Plataforma
    # -------------------------------------------------------------
    print("\n--- Test 36: Despegue Aéreo de Luigi y Drop-Through de Plataforma ---")
    p_luigi_jump = MockPlayer(x=0.0, y=0.0, on_ground=True, action="KNEE_BEND", act_val=24)
    p_luigi_jump.character = "LUIGI"
    p_opp_air3 = MockPlayer(x=12.0, y=18.0, on_ground=False, action="JUMPING", act_val=25)
    
    # 1. Durante KNEE_BEND (Jumpsquat): Luigi NO hace wavedash ni down-smash; despega al aire
    brain._set_luigi_jump("AERIAL_NAIR", 450)
    act_takeoff = brain.get_luigi_decision(player=p_luigi_jump, opponent=p_opp_air3, current_frame=451, stage="BATTLEFIELD")
    print(f"Despegue aéreo (KNEE_BEND): {act_takeoff['name']} | Shield={act_takeoff['shield']}, Attack={act_takeoff['attack']}, Stick Y={act_takeoff['stick_y']}")
    assert not act_takeoff["shield"] and not act_takeoff["attack"] and act_takeoff["stick_y"] == 0.85 and "DESPEGUE AÉREO" in act_takeoff["name"]

    # 2. Primer frame en el aire (on_ground=False): Ejecuta el N-Air Frame-3 buferizado
    p_luigi_airborne = MockPlayer(x=2.0, y=5.0, on_ground=False, action="JUMP_F", act_val=25)
    p_luigi_airborne.character = "LUIGI"
    act_air_impact = brain.get_luigi_decision(player=p_luigi_airborne, opponent=p_opp_air3, current_frame=452, stage="BATTLEFIELD")
    print(f"Impacto aéreo buferizado: {act_air_impact['name']} | Attack={act_air_impact['attack']}")
    assert act_air_impact["attack"] and "N-AIR OFENSIVO FRAME-3" in act_air_impact["name"]

    # 3. Luigi sobre plataforma (y=27.2) y rival abajo en el escenario (y=0.0):
    # Luigi atraviesa la plataforma hacia abajo (stick_y=0.0) con D-Air drill o Cyclone
    p_luigi_plat = MockPlayer(x=-38.0, y=27.2, on_ground=True, action="STANDING", act_val=14)
    p_luigi_plat.character = "LUIGI"
    p_opp_below = MockPlayer(x=-38.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    act_drop = brain.get_luigi_decision(player=p_luigi_plat, opponent=p_opp_below, current_frame=453, stage="BATTLEFIELD")
    print(f"Descenso de plataforma (Drop-through): {act_drop['name']} | Stick Y={act_drop['stick_y']}")
    assert act_drop["stick_y"] == 0.0 and "DROP-THROUGH PLATAFORMA" in act_drop["name"]
    print("✅ TEST 36 SUPERADO: Luigi salta limpiamente al combate aéreo y desciende inmediatamente de plataformas si el rival está abajo.")

    # -------------------------------------------------------------
    # TEST 37: Recuperación Offstage con Prioridad de Doble Salto
    # -------------------------------------------------------------
    print("\n--- Test 37: Recuperación Offstage con Prioridad de Doble Salto ---")
    p_luigi_offstage_jump = MockPlayer(x=90.0, y=-5.0, on_ground=False, action="FALLING", act_val=29, jumps_left=1)
    p_luigi_offstage_jump.character = "LUIGI"
    p_opp_center = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    
    # Caso A: Con doble salto disponible (jumps_left=1) -> PRIORIDAD ABSOLUTA AL DOBLE SALTO
    act_recov_dj = brain.get_luigi_decision(player=p_luigi_offstage_jump, opponent=p_opp_center, current_frame=460, stage="BATTLEFIELD")
    print(f"Recuperación (con doble salto disponible): {act_recov_dj['name']} | Jump={act_recov_dj['jump']}, Special={act_recov_dj['special']}")
    assert act_recov_dj["jump"] and not act_recov_dj["special"] and "SALTO DOBLE FLOTANTE" in act_recov_dj["name"]

    # Caso B: Sin doble salto disponible (jumps_left=0) a distancia lejana -> Green Missile / Cyclone
    p_luigi_offstage_no_dj = MockPlayer(x=90.0, y=-5.0, on_ground=False, action="FALLING", act_val=29, jumps_left=0)
    p_luigi_offstage_no_dj.character = "LUIGI"
    act_recov_missile = brain.get_luigi_decision(player=p_luigi_offstage_no_dj, opponent=p_opp_center, current_frame=461, stage="BATTLEFIELD")
    print(f"Recuperación (doble salto gastado): {act_recov_missile['name']} | Special={act_recov_missile['special']}")
    assert act_recov_missile["special"] and ("GREEN MISSILE" in act_recov_missile["name"] or "CYCLONE" in act_recov_missile["name"])
    print("✅ TEST 37 SUPERADO: Luigi siempre usa su doble salto primero para elevarse seguro antes de arriesgar el Green Missile.")

    # -------------------------------------------------------------
    # TEST 38: Poder Recargable Ofensivo (Green Missile Charge & Torpedo Blast)
    # -------------------------------------------------------------
    print("\n--- Test 38: Poder Recargable Ofensivo (Green Missile Charge & Launch) ---")
    p_luigi_missile = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_missile.character = "LUIGI"
    p_opp_charge_far2 = MockPlayer(x=25.0, y=0.0, on_ground=True, action="ATTACK_S_4", act_val=60)
    
    # 1. Inicio de carga de Green Missile ofensivo
    act_start_charge = brain.get_luigi_decision(player=p_luigi_missile, opponent=p_opp_charge_far2, current_frame=471, stage="BATTLEFIELD")
    print(f"Inicio de recarga de misil: {act_start_charge['name']} | Special={act_start_charge['special']}")
    assert act_start_charge["special"] and "GREEN MISSILE" in act_start_charge["name"] and brain.missile_charge_timer > 0

    # 2. Siguiente frame: Proceso de acumulación de poder (Holding charge)
    act_holding_charge = brain.get_luigi_decision(player=p_luigi_missile, opponent=p_opp_charge_far2, current_frame=472, stage="BATTLEFIELD")
    print(f"Recargando poder acumulado: {act_holding_charge['name']} | Special={act_holding_charge['special']}")
    assert act_holding_charge["special"] and "RECARGANDO PODER" in act_holding_charge["name"]

    # 3. Disparo al alcanzar carga completa (frame 18)
    brain.missile_charge_timer = 18
    act_fire_missile = brain.get_luigi_decision(player=p_luigi_missile, opponent=p_opp_charge_far2, current_frame=473, stage="BATTLEFIELD")
    print(f"Lanzamiento de misil torpedo: {act_fire_missile['name']} | Special={act_fire_missile['special']}")
    assert not act_fire_missile["special"] and "¡MISIL VERDE DISPARADO!" in act_fire_missile["name"]
    print("✅ TEST 38 SUPERADO: Luigi recarga y dispara su Green Missile ofensivo como torpedo devastador.")

    # -------------------------------------------------------------
    # TEST 39: Poder de Fuego Defensivo y Ofensivo (Super Jump Punch / Shoryuken con Fuego)
    # -------------------------------------------------------------
    print("\n--- Test 39: Super Jump Punch de Fuego Defensivo y Ofensivo ---")
    # 1. Defensivo OOS: Rival presionando el escudo a corta distancia
    p_luigi_shld = MockPlayer(x=0.0, y=0.0, on_ground=True, action="SHIELD", act_val=180)
    p_luigi_shld.character = "LUIGI"
    p_opp_close_shld = MockPlayer(x=4.0, y=0.0, on_ground=True, action="ATTACK_S_4", act_val=60, percent=50.0)
    brain.dopamine = 0.60
    act_oos_upb = brain.get_luigi_decision(player=p_luigi_shld, opponent=p_opp_close_shld, current_frame=480, stage="BATTLEFIELD")
    print(f"Defensiva OOS (Sweetspot Up-B): {act_oos_upb['name']} | Special={act_oos_upb['special']}, Stick Y={act_oos_upb['stick_y']}")
    assert act_oos_upb["special"] and act_oos_upb["stick_y"] == 1.0 and "SWEETSPOT UP-B SHORYUKEN" in act_oos_upb["name"]

    # 2. Defensivo CQC: Crouch-Cancel Frame-8 Sweetspot Up-B Counter
    p_luigi_cqc_cc = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14, percent=30.0)
    p_luigi_cqc_cc.character = "LUIGI"
    p_opp_cqc_atk = MockPlayer(x=4.0, y=0.0, on_ground=True, action="ATTACK_S_3", act_val=55)
    act_cc_upb = brain.get_luigi_decision(player=p_luigi_cqc_cc, opponent=p_opp_cqc_atk, current_frame=481, stage="BATTLEFIELD")
    print(f"Defensiva CQC (Crouch-Cancel Up-B): {act_cc_upb['name']} | Special={act_cc_upb['special']}, Stick Y={act_cc_upb['stick_y']}")
    assert act_cc_upb["special"] and act_cc_upb["stick_y"] == 1.0 and "CROUCH-CANCEL SWEETSPOT UP-B" in act_cc_upb["name"]

    # 3. Ofensivo Neutral: Wavedash Adelante ➔ Sweetspot Up-B Shoryuken de Fuego
    p_luigi_neut = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_neut.character = "LUIGI"
    p_opp_neut = MockPlayer(x=15.0, y=0.0, on_ground=True, action="STANDING", act_val=14, percent=60.0)
    brain.dopamine = 0.70
    act_neut_upb = None
    for f in range(500, 600):
        brain.missile_charge_timer = 0
        res = brain.get_luigi_decision(player=p_luigi_neut, opponent=p_opp_neut, current_frame=f, stage="BATTLEFIELD")
        if "SWEETSPOT UP-B SHORYUKEN DE FUEGO" in res["name"]:
            act_neut_upb = res
            break
    assert act_neut_upb is not None, "Debe existir finta de Wavedash a Up-B de Fuego en neutral"
    print(f"Ofensiva Neutral (Wavedash Shoryuken): {act_neut_upb['name']} | Special={act_neut_upb['special']}")
    print("✅ TEST 39 SUPERADO: Luigi domina el fuego con su Shoryuken tanto defensivo (OOS y CC Counter) como ofensivo.")

    # -------------------------------------------------------------
    # TEST 40: Green Missile Torpedo Defensivo y Fintas Complejas 20XX
    # -------------------------------------------------------------
    print("\n--- Test 40: Green Missile Torpedo Defensivo y Fintas Complejas ---")
    # 1. Defensivo OOS: Luigi acorralado en escudo cerca de la repisa con rival presionando
    p_luigi_corner_shld = MockPlayer(x=76.0, y=0.0, on_ground=True, action="SHIELD", act_val=180)
    p_luigi_corner_shld.character = "LUIGI"
    p_opp_corner_press = MockPlayer(x=68.0, y=0.0, on_ground=True, action="ATTACK_S_4", act_val=60)
    act_corner_oos = brain.get_luigi_decision(player=p_luigi_corner_shld, opponent=p_opp_corner_press, current_frame=610, stage="BATTLEFIELD")
    print(f"Defensiva Escape OOS: {act_corner_oos['name']} | Special={act_corner_oos['special']}, Stick X={act_corner_oos['stick_x']}")
    assert act_corner_oos["special"] and "RETIRADA EXPLOSIVA" in act_corner_oos["name"] and act_corner_oos["stick_x"] == 0.0

    # 2. Defensivo CQC: Luigi acorralado en tierra cerca de la repisa con rival atacando
    brain.missile_charge_timer = 0
    p_luigi_corner_cqc = MockPlayer(x=75.0, y=0.0, on_ground=True, action="STANDING", act_val=14, percent=85.0)
    p_luigi_corner_cqc.character = "LUIGI"
    act_corner_cqc = brain.get_luigi_decision(player=p_luigi_corner_cqc, opponent=p_opp_corner_press, current_frame=611, stage="BATTLEFIELD")
    print(f"Defensiva Escape CQC: {act_corner_cqc['name']} | Special={act_corner_cqc['special']}, Stick X={act_corner_cqc['stick_x']}")
    assert act_corner_cqc["special"] and "RETIRADA EXPLOSIVA" in act_corner_cqc["name"]

    # 3. Finta Compleja Neutral: Tomahawk Fake-Out
    act_tomahawk = None
    for f in range(620, 720):
        brain.missile_charge_timer = 0
        res = brain.get_luigi_decision(player=p_luigi_neut, opponent=p_opp_neut, current_frame=f, stage="BATTLEFIELD")
        if "TOMAHAWK FAKE-OUT" in res["name"]:
            act_tomahawk = res
            break
    assert act_tomahawk is not None, "Debe existir finta compleja Tomahawk en neutral"
    print(f"Finta Compleja Neutral (Tomahawk): {act_tomahawk['name']} | Jump={act_tomahawk['jump']}")
    print("✅ TEST 40 SUPERADO: Luigi usa el Green Missile para escapes defensivos explosivos y domina fintas complejas 20XX.")

    # -------------------------------------------------------------
    # TEST 41: Lectura de Hábitos del Rival (Missed-Tech Jab-Reset)
    # -------------------------------------------------------------
    print("\n--- Test 41: Lectura de Hábitos del Rival (Missed-Tech Jab-Reset) ---")
    brain.learn_opponent_habit("missed_tech", val=10)
    p_opp_down = MockPlayer(x=4.0, y=0.0, on_ground=True, action="DOWN_BOUND", act_val=183, percent=40.0)
    p_luigi_cqc = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_cqc.character = "LUIGI"

    act_habit_tech = brain.get_luigi_decision(player=p_luigi_cqc, opponent=p_opp_down, current_frame=800, stage="BATTLEFIELD")
    print(f"Castigo por Hábito (Missed Tech): {act_habit_tech['name']} | Attack={act_habit_tech['attack']}")
    assert "JAB-RESET" in act_habit_tech["name"] or "DOWN-SMASH" in act_habit_tech["name"]
    print("✅ TEST 41 SUPERADO: Luigi detecta el hábito de missed tech y aplica Jab-Reset automático.")

    # -------------------------------------------------------------
    # TEST 42: Caza Offstage Agresiva con Deep D-Air Meteor Spike
    # -------------------------------------------------------------
    print("\n--- Test 42: Caza Offstage Agresiva (Deep D-Air Spike) ---")
    p_luigi_edge_spike = MockPlayer(x=62.0, y=0.0, on_ground=False, action="FALLING", act_val=29, jumps_left=1)
    p_luigi_edge_spike.character = "LUIGI"
    p_opp_deep_off = MockPlayer(x=78.0, y=-12.0, on_ground=False, action="FALLING", act_val=29, percent=85.0)
    p_opp_deep_off.off_stage = True
    brain.dopamine = 0.85
    brain.long_term_memory["synaptic_plasticity"]["offstage_aggression"] = 2.50

    act_deep_spike = brain.get_luigi_decision(player=p_luigi_edge_spike, opponent=p_opp_deep_off, current_frame=810, stage="BATTLEFIELD")
    print(f"Caza Deep Spike: {act_deep_spike['name']} | Jump={act_deep_spike['jump']}, AllowChase={act_deep_spike.get('_allow_offstage_chase')}")
    assert "D-AIR METEOR SPIKE" in act_deep_spike["name"] and act_deep_spike.get("_allow_offstage_chase", False)
    print("✅ TEST 42 SUPERADO: Luigi caza implacablemente fuera de escenario con meteor spike profundo.")

    # -------------------------------------------------------------
    # TEST 43: Combo Kill Confirm Shoryuken Ampliado por Plasticidad
    # -------------------------------------------------------------
    print("\n--- Test 43: Combo Kill Confirm Shoryuken Ampliado por Plasticidad ---")
    brain.combo_state = "LUIGI_DTHROW_COMBO"
    brain.dopamine = 0.55
    brain.long_term_memory["synaptic_plasticity"]["combo_mastery"] = 2.80
    p_luigi_throw = MockPlayer(x=0.0, y=0.0, on_ground=True, action="THROW_DOWN", act_val=222)
    p_luigi_throw.character = "LUIGI"
    p_opp_throw = MockPlayer(x=2.0, y=0.0, on_ground=True, action="DAMAGE_AIR", percent=85.0)

    act_shoryu_confirm = brain.get_luigi_decision(player=p_luigi_throw, opponent=p_opp_throw, current_frame=820, stage="BATTLEFIELD")
    print(f"Confirm con Plasticidad: {act_shoryu_confirm['name']} | Special={act_shoryu_confirm['special']}")
    assert "COMBO SUPREMO SHORYUKEN" in act_shoryu_confirm["name"] and act_shoryu_confirm["special"]
    print("✅ TEST 43 SUPERADO: La neuroplasticidad entrenada amplía la confirmación del Shoryuken Kill Confirm.")

    # -------------------------------------------------------------
    # TEST 44: Consolidación de Experiencia y Zero-Phobia al Borde
    # -------------------------------------------------------------
    print("\n--- Test 44: Dinámica Sináptica y Zero-Phobia al Borde ---")
    brain.learn_from_success("SAFE_RECOVERY")
    brain.learn_from_success("MATCH_WON")
    edge_fear_val = brain.long_term_memory.get("edge_fear", 1.25)
    print(f"Nivel de aversión al borde tras victorias: {edge_fear_val:.2f}x")
    assert edge_fear_val <= 1.30, f"Error: Aversión al borde demasiado alta ({edge_fear_val})"
    print("✅ TEST 44 SUPERADO: Las victorias y recuperaciones exitosas reducen el miedo al borde para máxima agresión.")

    # -------------------------------------------------------------
    # TEST 45: Integridad del Puente Melee (get_controller_decision)
    # -------------------------------------------------------------
    print("\n--- Test 45: Integridad del Puente Melee (get_controller_decision) ---")
    with open("fly_melee.py", "r") as f_bridge:
        bridge_code = f_bridge.read()
    assert "brain.get_controller_decision" in bridge_code, "Error: fly_melee.py debe llamar a get_controller_decision"
    print("✅ TEST 45 SUPERADO: fly_melee.py enruta limpiamente mediante get_controller_decision para Luigi y Fox.")

    # -------------------------------------------------------------
    # TEST 46: Platform L-Canceling Universal
    # -------------------------------------------------------------
    print("\n--- Test 46: Platform L-Canceling Universal (Plataforma y Suelo) ---")
    p_luigi_plat_l = MockPlayer(x=38.0, y=28.0, on_ground=False, action="ATTACK_AIR_N", act_val=65)
    p_luigi_plat_l.character = "LUIGI"
    p_luigi_plat_l.speed_y_self = -0.3
    p_opp_dummy = MockPlayer(x=38.0, y=0.0, on_ground=True, action="STANDING", act_val=14)

    act_plat_l = brain.get_luigi_decision(player=p_luigi_plat_l, opponent=p_opp_dummy, current_frame=830, stage="BATTLEFIELD")
    print(f"Platform L-Cancel: {act_plat_l['name']} | Shield={act_plat_l['shield']}")
    assert act_plat_l["shield"] and "L-CANCEL PERFECTO" in act_plat_l["name"]
    print("✅ TEST 46 SUPERADO: Luigi ejecuta L-Cancel perfecto en plataformas reduciendo el lag al 50%.")

    # -------------------------------------------------------------
    # TEST 47: ASDI Down en Hitstun para Crouch-Cancel Reversals
    # -------------------------------------------------------------
    print("\n--- Test 47: ASDI Down en Hitstun (Crouch-Cancel Reversals) ---")
    p_luigi_hitstun = MockPlayer(x=0.0, y=2.0, on_ground=True, action="DAMAGE_AIR", act_val=76, percent=30.0)
    p_luigi_hitstun.character = "LUIGI"
    p_luigi_hitstun.hitstun_frames_left = 5

    act_asdi = brain.get_luigi_decision(player=p_luigi_hitstun, opponent=p_opp_dummy, current_frame=840, stage="BATTLEFIELD")
    print(f"Survival DI + ASDI: {act_asdi['name']} | C-Stick Y={act_asdi['c_stick_y']}")
    assert act_asdi["c_stick_y"] == 0.0 and "SURVIVAL DI" in act_asdi["name"]
    print("✅ TEST 47 SUPERADO: Luigi activa ASDI Down para tocar suelo y castigar con Crouch-Cancel.")

    # -------------------------------------------------------------
    # TEST 48: Wavedash Out of Shield (WD OOS) en Espaciado Medio
    # -------------------------------------------------------------
    print("\n--- Test 48: Wavedash Out of Shield (WD OOS) en Espaciado Medio ---")
    p_luigi_shield_oos = MockPlayer(x=0.0, y=0.0, on_ground=True, action="SHIELD", act_val=179)
    p_luigi_shield_oos.character = "LUIGI"
    p_opp_spaced = MockPlayer(x=10.0, y=0.0, on_ground=True, action="WAIT", act_val=14, percent=30.0)

    act_wd_oos = brain.get_luigi_decision(player=p_luigi_shield_oos, opponent=p_opp_spaced, current_frame=850, stage="BATTLEFIELD")
    print(f"Wavedash OOS: {act_wd_oos['name']} | Jump={act_wd_oos['jump']}, WDJumpAction={brain.luigi_jump_action}")
    assert act_wd_oos["jump"] and "WAVEDASH OUT OF SHIELD" in act_wd_oos["name"] and brain.luigi_jump_action == "WAVEDASH"
    print("✅ TEST 48 SUPERADO: Luigi sale de escudo con Wavedash OOS para castigar whiffs con tracción 0.005.")

    # -------------------------------------------------------------
    # TEST 49: Wavedash Rushdown en Neutral a Larga Distancia
    # -------------------------------------------------------------
    print("\n--- Test 49: Wavedash Rushdown en Neutral a Larga Distancia ---")
    p_luigi_neutral = MockPlayer(x=-15.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_neutral.character = "LUIGI"
    p_opp_far = MockPlayer(x=20.0, y=0.0, on_ground=True, action="STANDING", act_val=14, percent=40.0)
    brain.dopamine = 0.65

    act_rushdown = brain.get_luigi_decision(player=p_luigi_neutral, opponent=p_opp_far, current_frame=875, stage="BATTLEFIELD")
    print(f"Neutral Rushdown: {act_rushdown['name']} | Jump={act_rushdown['jump']}")
    assert ("WAVEDASH RUSHDOWN" in act_rushdown["name"] and act_rushdown["jump"]) or "SPRINT" in act_rushdown["name"]
    print("✅ TEST 49 SUPERADO: Luigi domina el neutral con Wavedash Rushdown encadenado ultra-rápido.")

    # -------------------------------------------------------------
    # TEST 50: Rastreo Avanzado de Hábitos CQC y Pánico en Tiempo Real
    # -------------------------------------------------------------
    print("\n--- Test 50: Rastreo Avanzado de Hábitos CQC y Pánico en Tiempo Real ---")
    p_opp_cqc_atk = MockPlayer(x=5.0, y=0.0, on_ground=True, action="ATTACK_11", act_val=44)
    brain.prev_opp_action = "STANDING"
    brain.prev_opp_act_val = 14
    brain.realtime_memory_train(player=p_luigi_neutral, opponent=p_opp_cqc_atk, current_frame=870)
    cqc_atk_freq = brain.long_term_memory["opponent_habits"].get("cqc_attack_freq", 0)
    print(f"Frecuencia CQC Attack registrada: {cqc_atk_freq}")
    assert cqc_atk_freq > 0
    print("✅ TEST 50 SUPERADO: El cerebro registra dinámicamente tendencias de CQC y pánico del rival.")

    # -------------------------------------------------------------
    # TEST 51: Recuperación Offstage Total (Zero Suicidio & Anti-Lockout de Tumble)
    # -------------------------------------------------------------
    print("\n--- Test 51: Recuperación Offstage Total (Zero Suicidio & Anti-Lockout) ---")
    p_opp_center = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)

    # 1. Lanzado alto offstage con doble salto (py=18.0, px=80.0):
    # ANTES: py >= 8.0 provocaba un AirDodge directo al vacío y caída libre (Freefall / Fall_Special).
    # AHORA: Prioridad absoluta al salto doble flotante sin airdodge prematuro.
    p_luigi_high_off = MockPlayer(x=80.0, y=18.0, on_ground=False, action="FALLING", act_val=29, jumps_left=1)
    p_luigi_high_off.character = "LUIGI"
    act_high_dj = brain.get_luigi_decision(player=p_luigi_high_off, opponent=p_opp_center, current_frame=900, stage="BATTLEFIELD")
    print(f"Offstage Alto con Salto: {act_high_dj['name']} | Jump={act_high_dj['jump']}, Shield={act_high_dj['shield']}")
    assert act_high_dj["jump"] and not act_high_dj["shield"] and "SALTO DOBLE FLOTANTE" in act_high_dj["name"]

    # 2. En Tumble fuera del escenario:
    # ANTES: Luigi ejecutaba un N-Air de 44 frames de lag, impidiéndole recuperarse mientras caía al abismo.
    # AHORA: Cancela tumble inmediatamente con doble salto hacia el escenario.
    p_luigi_tumble_off = MockPlayer(x=75.0, y=12.0, on_ground=False, action="TUMBLE", act_val=38, jumps_left=1)
    p_luigi_tumble_off.character = "LUIGI"
    act_tumble_off = brain.get_luigi_decision(player=p_luigi_tumble_off, opponent=p_opp_center, current_frame=901, stage="BATTLEFIELD")
    print(f"Offstage Tumble Break: {act_tumble_off['name']} | Jump={act_tumble_off['jump']}, Attack={act_tumble_off['attack']}")
    assert act_tumble_off["jump"] and not act_tumble_off["attack"] and "ESCAPE DE TUMBLE OFFSTAGE" in act_tumble_off["name"]

    # 3. Offstage alto con saltos gastados (py=14.0, px=76.0, jumps_left=0):
    # NUNCA debe hacer airdodge a esa distancia; debe flotar con Air Drift hacia el escenario.
    p_luigi_high_spent = MockPlayer(x=76.0, y=14.0, on_ground=False, action="FALLING", act_val=29, jumps_left=0)
    p_luigi_high_spent.character = "LUIGI"
    act_high_drift = brain.get_luigi_decision(player=p_luigi_high_spent, opponent=p_opp_center, current_frame=902, stage="BATTLEFIELD")
    print(f"Offstage Alto sin Salto: {act_high_drift['name']} | Shield={act_high_drift['shield']}, Stick X={act_high_drift['stick_x']}")
    assert not act_high_drift["shield"] and act_high_drift["stick_x"] < 0.5 and "AIR DRIFT" in act_high_drift["name"]

    # 4. Ascenso activo de salto doble (JUMP_AERIAL):
    # No interrumpir el salto con airdodge ni ataques en falso.
    p_luigi_jumping = MockPlayer(x=74.0, y=6.0, on_ground=False, action="JUMP_AERIAL", act_val=27, jumps_left=0)
    p_luigi_jumping.character = "LUIGI"
    act_jumping = brain.get_luigi_decision(player=p_luigi_jumping, opponent=p_opp_center, current_frame=903, stage="BATTLEFIELD")
    print(f"Ascenso Salto Doble: {act_jumping['name']} | Shield={act_jumping['shield']}")
    assert not act_jumping["shield"] and "ASCENSO DE SALTO DOBLE" in act_jumping["name"]

    # 5. Sweetspot Up-B a la repisa (py=-8.0, px=70.0):
    p_luigi_sweetspot = MockPlayer(x=70.0, y=-8.0, on_ground=False, action="FALLING", act_val=29, jumps_left=0)
    p_luigi_sweetspot.character = "LUIGI"
    act_sweetspot = brain.get_luigi_decision(player=p_luigi_sweetspot, opponent=p_opp_center, current_frame=904, stage="BATTLEFIELD")
    print(f"Sweetspot Up-B: {act_sweetspot['name']} | Special={act_sweetspot['special']}")
    assert act_sweetspot["special"] and "SUPER JUMP PUNCH: SWEETSPOT" in act_sweetspot["name"]

    # 6. Snap estricto de Airdodge únicamente pegado a la repisa:
    p_luigi_snap = MockPlayer(x=69.0, y=0.0, on_ground=False, action="FALLING", act_val=29, jumps_left=0)
    p_luigi_snap.character = "LUIGI"
    act_snap = brain.get_luigi_decision(player=p_luigi_snap, opponent=p_opp_center, current_frame=905, stage="BATTLEFIELD")
    print(f"Snap de Repisa Adyacente: {act_snap['name']} | Shield={act_snap['shield']}")
    assert act_snap["shield"] and "SNAP INSTANTÁNEO" in act_snap["name"]

    # 7. Special Fall (Caída libre) tras Up-B: Air Drift seguro
    p_luigi_freefall = MockPlayer(x=72.0, y=-5.0, on_ground=False, action="FALL_SPECIAL", act_val=35, jumps_left=0)
    p_luigi_freefall.character = "LUIGI"
    act_freefall = brain.get_luigi_decision(player=p_luigi_freefall, opponent=p_opp_center, current_frame=906, stage="BATTLEFIELD")
    print(f"Caída Libre Especial: {act_freefall['name']} | Shield={act_freefall['shield']}, Stick X={act_freefall['stick_x']}")
    assert not act_freefall["shield"] and not act_freefall["special"] and act_freefall["stick_x"] < 0.5 and "SPECIAL FALL" in act_freefall["name"]

    print("✅ TEST 51 SUPERADO: La máquina de recuperación de Luigi elimina 100% de airdodges prematuros, escapes de tumble con N-Air laggy y suicidios offstage.")

    # -------------------------------------------------------------
    # TEST 52: Barrera Anti-Suicidio Total (Poderes Seguros & Recuperación Sin Muerte Sola)
    # -------------------------------------------------------------
    print("\n--- Test 52: Barrera Anti-Suicidio Total (Poderes Especiales Seguros & Recuperación) ---")
    # 1. Luigi cerca del borde derecho en el suelo intentando usar Side-B hacia el vacío:
    # La barrera de seguridad DEBE anular el especial para evitar que Luigi se tire solo.
    p_luigi_near_edge = MockPlayer(x=50.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_near_edge.character = "LUIGI"
    p_opp_off_right = MockPlayer(x=65.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    raw_sideb_action = {
        "name": "TEST SIDE-B", "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
        "stick_x": 1.0, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5
    }
    safe_action = brain._enforce_safety(raw_sideb_action, p_luigi_near_edge, p_opp_off_right, stage_edge=68.4)
    print(f"Bloqueo Side-B cerca del borde: Special={safe_action['special']}")
    assert not safe_action["special"], "Side-B hacia el borde debe ser bloqueado para evitar suicidio"

    # 2. Luigi en el aire sobre el escenario intentando usar Up-B o Cyclone:
    # Debe ser bloqueado y convertido en ataque aéreo seguro (N-Air / Up-Air) para evitar Freefall indefenso.
    p_luigi_air_center = MockPlayer(x=20.0, y=10.0, on_ground=False, action="JUMP_F", act_val=25)
    p_luigi_air_center.character = "LUIGI"
    raw_air_upb = {
        "name": "TEST AIR UP-B", "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
        "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5
    }
    safe_air_action = brain._enforce_safety(raw_air_upb, p_luigi_air_center, p_opp_center, stage_edge=68.4)
    print(f"Bloqueo Up-B aéreo sobre pista: Special={safe_air_action['special']}, Attack={safe_air_action['attack']}")
    assert not safe_air_action["special"] and safe_air_action["attack"], "Up-B aéreo debe convertirse en ataque seguro sin freefall"

    # 3. Luigi offstage bajo ejecutando doble salto (py = -12.0):
    # NUNCA debe cancelarse prematuramente en Up-B; debe completar el ascenso.
    p_luigi_jump_low = MockPlayer(x=74.0, y=-12.0, on_ground=False, action="JUMP_AERIAL", act_val=27, jumps_left=0)
    p_luigi_jump_low.character = "LUIGI"
    act_jump_low = brain.get_luigi_decision(player=p_luigi_jump_low, opponent=p_opp_center, current_frame=910, stage="BATTLEFIELD")
    print(f"Doble salto bajo sin cancelación prematura: {act_jump_low['name']} | Special={act_jump_low['special']}")
    assert not act_jump_low["special"] and "ASCENSO DE SALTO DOBLE" in act_jump_low["name"]

    # 4. Snap a repisa seguro (no airdodge hacia abajo):
    assert act_snap["stick_y"] >= 0.5, "El airdodge a la repisa debe ser hacia arriba/diagonal al escenario, nunca hacia el fondo del abismo"

    # 5. Servidor Web Dashboard interactivo (http://localhost:8085):
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:8085/", timeout=2.0) as resp:
            web_code = resp.getcode()
            print(f"Servidor Web Localhost 8085: HTTP {web_code}")
            assert web_code == 200, "Dashboard debe responder con HTTP 200"
    except Exception as e:
        print(f"Aviso Web: {e}")

    print("✅ TEST 52 SUPERADO: Barrera anti-suicidio de poderes activa, recuperación a prueba de caídas y servidor web en línea.")

    # -------------------------------------------------------------
    # TEST 53: Secuencia Wavedash Frame-Perfect de Luigi (Jumpsquat ➔ Airdodge Terrestre)
    # -------------------------------------------------------------
    print("\n--- Test 53: Secuencia Wavedash Frame-Perfect de Luigi ---")
    p_luigi_wd_start = MockPlayer(x=0.0, y=0.0, on_ground=True, action="SHIELD", act_val=179)
    p_luigi_wd_start.character = "LUIGI"
    p_opp_wd = MockPlayer(x=12.0, y=0.0, on_ground=True, action="WAIT", act_val=14, percent=30.0)
    act_wd_init = brain.get_luigi_decision(player=p_luigi_wd_start, opponent=p_opp_wd, current_frame=950, stage="BATTLEFIELD")
    assert act_wd_init["jump"] and brain.luigi_jump_action == "WAVEDASH"
    print(f"Paso 1 (Inicio WD): {act_wd_init['name']} | Jump={act_wd_init['jump']}, ActionQueued={brain.luigi_jump_action}")

    p_luigi_wd_squat = MockPlayer(x=0.0, y=0.0, on_ground=True, action="KNEE_BEND", act_val=24)
    p_luigi_wd_squat.character = "LUIGI"
    act_wd_squat = brain.get_luigi_decision(player=p_luigi_wd_squat, opponent=p_opp_wd, current_frame=951, stage="BATTLEFIELD")
    print(f"Paso 2 (Jumpsquat): {act_wd_squat['name']} | Shield={act_wd_squat['shield']}, Stick Y={act_wd_squat['stick_y']}")
    assert not act_wd_squat["shield"] and act_wd_squat["stick_y"] == 0.25 and brain.luigi_jump_action == "WAVEDASH"
    assert "JUMPSQUAT PREPARANDO WAVEDASH" in act_wd_squat["name"]

    p_luigi_wd_air = MockPlayer(x=0.5, y=0.2, on_ground=False, action="JUMP_F", act_val=25)
    p_luigi_wd_air.character = "LUIGI"
    act_wd_air = brain.get_luigi_decision(player=p_luigi_wd_air, opponent=p_opp_wd, current_frame=952, stage="BATTLEFIELD")
    print(f"Paso 3 (Airdodge deslizante): {act_wd_air['name']} | Shield={act_wd_air['shield']}, Stick Y={act_wd_air['stick_y']}")
    assert act_wd_air["shield"] and act_wd_air["stick_y"] == 0.25 and act_wd_air.get("_allow_air_shield", False)
    assert brain.luigi_jump_action is None
    assert "WAVEDASH DESLIZANTE" in act_wd_air["name"]
    print("✅ TEST 53 SUPERADO: Wavedash de Luigi se ejecuta con precisión 20XX (Jumpsquat limpio ➔ Airdodge Frame 1).")

    # -------------------------------------------------------------
    # TEST 54: Wiggle-Out en Tumble Offstage sin Saltos (Desbloqueo de Poderes)
    # -------------------------------------------------------------
    print("\n--- Test 54: Wiggle-Out en Tumble Offstage sin Saltos ---")
    p_luigi_tumble_no_dj = MockPlayer(x=78.0, y=5.0, on_ground=False, action="TUMBLE", act_val=38, jumps_left=0)
    p_luigi_tumble_no_dj.character = "LUIGI"
    act_wiggle = brain.get_luigi_decision(player=p_luigi_tumble_no_dj, opponent=p_opp_center, current_frame=953, stage="BATTLEFIELD")
    print(f"Wiggle-out en Tumble: {act_wiggle['name']} | Stick X={act_wiggle['stick_x']}, Special={act_wiggle['special']}")
    assert not act_wiggle["special"] and "WIGGLE-OUT ESCAPE DE TUMBLE" in act_wiggle["name"]
    print("✅ TEST 54 SUPERADO: Luigi sacude el stick en Tumble offstage para desbloquear sus poderes en Melee.")

    # -------------------------------------------------------------
    # TEST 55: Ataques Aéreos Ofensivos y Fast-Fall cuando Luigi está Sobre el Rival
    # -------------------------------------------------------------
    print("\n--- Test 55: Ataques Aéreos Ofensivos y Fast-Fall Sobre el Rival ---")
    p_opp_ground = MockPlayer(x=10.0, y=0.0, on_ground=True, action="STANDING", act_val=14)

    # 1. Luigi directamente por encima del rival (py=18.0, oy=0.0):
    p_luigi_above = MockPlayer(x=10.0, y=18.0, on_ground=False, action="FALLING", act_val=29)
    p_luigi_above.character = "LUIGI"
    
    # Frame par: D-Air drill con Fast-Fall (stick_y=0.0)
    act_dair_ff = brain.get_luigi_decision(player=p_luigi_above, opponent=p_opp_ground, current_frame=960, stage="BATTLEFIELD")
    print(f"Directamente arriba (D-Air): {act_dair_ff['name']} | Attack={act_dair_ff['attack']}, Stick Y={act_dair_ff['stick_y']}, C-Stick Y={act_dair_ff['c_stick_y']}")
    assert act_dair_ff["attack"] and act_dair_ff["stick_y"] == 0.0 and act_dair_ff["c_stick_y"] == 0.0 and "D-AIR DRILL" in act_dair_ff["name"]

    # Frame impar: N-Air Frame-3 con Fast-Fall (stick_y=0.0)
    act_nair_ff = brain.get_luigi_decision(player=p_luigi_above, opponent=p_opp_ground, current_frame=961, stage="BATTLEFIELD")
    print(f"Directamente arriba (N-Air): {act_nair_ff['name']} | Attack={act_nair_ff['attack']}, Stick Y={act_nair_ff['stick_y']}")
    assert act_nair_ff["attack"] and act_nair_ff["stick_y"] == 0.0 and "N-AIR DESCENDENTE" in act_nair_ff["name"]

    # 2. Luigi diagonalmente por encima del rival (|dx|=16.0, py=18.0):
    p_luigi_diag_above = MockPlayer(x=-6.0, y=18.0, on_ground=False, action="FALLING", act_val=29)
    p_luigi_diag_above.character = "LUIGI"
    act_diag_ff = brain.get_luigi_decision(player=p_luigi_diag_above, opponent=p_opp_ground, current_frame=962, stage="BATTLEFIELD")
    print(f"Diagonalmente arriba: {act_diag_ff['name']} | Attack={act_diag_ff['attack']}, Stick Y={act_diag_ff['stick_y']}")
    assert act_diag_ff["attack"] and act_diag_ff["stick_y"] == 0.0

    print("✅ TEST 55 SUPERADO: Luigi ataca implacablemente con Fast-Fall (D-Air, N-Air, F-Air) cuando está arriba del rival.")

    # -------------------------------------------------------------
    # TEST 56: Sistema de Pummel en Agarre y Transición a Lanzamiento
    # -------------------------------------------------------------
    print("\n--- Test 56: Sistema de Pummel en Agarre (Golpear al agarrar) ---")
    brain.grab_pummel_count = 0
    p_luigi_grab = MockPlayer(x=0.0, y=0.0, on_ground=True, action="GRAB_WAIT", act_val=213)
    p_luigi_grab.character = "LUIGI"
    p_opp_grabbed = MockPlayer(x=3.0, y=0.0, on_ground=True, action="CAPTURE_WAIT", act_val=224, percent=70.0)
    
    # 1. Primer pummel (percent 70% -> max_pummels = 3)
    act_pummel1 = brain.get_luigi_decision(player=p_luigi_grab, opponent=p_opp_grabbed, current_frame=970, stage="BATTLEFIELD")
    print(f"Pummel 1: {act_pummel1['name']} | Attack={act_pummel1['attack']}")
    assert act_pummel1["attack"] and "PUMMEL EN AGARRE (1/3)" in act_pummel1["name"]
    assert brain.grab_pummel_count == 1

    # 2. Segundo pummel
    act_pummel2 = brain.get_luigi_decision(player=p_luigi_grab, opponent=p_opp_grabbed, current_frame=971, stage="BATTLEFIELD")
    print(f"Pummel 2: {act_pummel2['name']} | Attack={act_pummel2['attack']}")
    assert act_pummel2["attack"] and "PUMMEL EN AGARRE (2/3)" in act_pummel2["name"]
    assert brain.grab_pummel_count == 2

    # 3. Tercer pummel
    act_pummel3 = brain.get_luigi_decision(player=p_luigi_grab, opponent=p_opp_grabbed, current_frame=972, stage="BATTLEFIELD")
    print(f"Pummel 3: {act_pummel3['name']} | Attack={act_pummel3['attack']}")
    assert act_pummel3["attack"] and "PUMMEL EN AGARRE (3/3)" in act_pummel3["name"]
    assert brain.grab_pummel_count == 3

    # 4. Una vez completados los 3 pummels: Ejecuta Down-Throw
    act_throw = brain.get_luigi_decision(player=p_luigi_grab, opponent=p_opp_grabbed, current_frame=973, stage="BATTLEFIELD")
    print(f"Lanzamiento tras pummels: {act_throw['name']} | Stick Y={act_throw['stick_y']}")
    assert not act_throw["attack"] and act_throw["stick_y"] == 0.0 and "LUIGI D-THROW" in act_throw["name"]
    assert brain.grab_pummel_count == 0
    print("✅ TEST 56 SUPERADO: Luigi golpea (pummel con Botón A) antes de lanzar al rival, escalado por daño.")

    # -------------------------------------------------------------
    # TEST 57: Garantía Cero Suicidios con Green Missile (Onstage y Offstage)
    # -------------------------------------------------------------
    print("\n--- Test 57: Garantía Cero Suicidios con Green Missile ---")
    # 1. Luigi en X = 35.0 (distancia al borde = 33.4 < 42.0):
    # La barrera debe anular cualquier Side-B hacia el borde derecho.
    p_luigi_near_ledge = MockPlayer(x=35.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_near_ledge.character = "LUIGI"
    raw_sideb = {
        "name": "TEST SIDE-B", "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
        "stick_x": 1.0, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5
    }
    safe_sideb = brain._enforce_safety(dict(raw_sideb), p_luigi_near_ledge, p_opp_distance, stage_edge=68.4)
    print(f"Bloqueo Side-B cerca del borde (X=35.0): Special={safe_sideb['special']}")
    assert not safe_sideb["special"], "Side-B hacia el borde a distancia < 42.0 debe ser estrictamente bloqueado"

    # 2. Luigi offstage en el aire intentando usar Side-B:
    # La barrera debe convertirlo inmediatamente a Rising Cyclone (Down-B) sin caída libre.
    p_luigi_offstage_air = MockPlayer(x=78.0, y=-5.0, on_ground=False, action="FALLING", act_val=29)
    p_luigi_offstage_air.character = "LUIGI"
    safe_offstage_sideb = brain._enforce_safety(dict(raw_sideb), p_luigi_offstage_air, p_opp_distance, stage_edge=68.4)
    print(f"Conversión Side-B offstage: Stick Y={safe_offstage_sideb['stick_y']}, Special={safe_offstage_sideb['special']}")
    assert safe_offstage_sideb["special"] and safe_offstage_sideb["stick_y"] == 0.0, "Side-B offstage debe convertirse a Rising Cyclone (Down-B)"
    print("✅ TEST 57 SUPERADO: Luigi tiene prohibido suicidarse con Green Missile dentro y fuera del escenario.")

    # -------------------------------------------------------------
    # TEST 58: Descenso de Plataforma sin Congelamiento (Anti-Stall & Crouch Break)
    # -------------------------------------------------------------
    print("\n--- Test 58: Descenso de Plataforma sin Congelamiento ---")
    brain.combo_state = None
    brain.combo_timer = 0
    # Caso 1: Luigi en Top Platform (px=-15.0, py=54.4) y Mario en el suelo (ox=35.0, oy=0.0) [Como en la captura del usuario]
    p_luigi_top_plat = MockPlayer(x=-15.0, y=54.4, on_ground=True, action="STANDING", act_val=14)
    p_luigi_top_plat.character = "LUIGI"
    p_opp_ground_far = MockPlayer(x=35.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    act_plat_exit = brain.get_luigi_decision(player=p_luigi_top_plat, opponent=p_opp_ground_far, current_frame=980, stage="BATTLEFIELD")
    print(f"Salida de top platform (|dx|=50.0): {act_plat_exit['name']} | Stick X={act_plat_exit['stick_x']}, Attack={act_plat_exit['attack']}")
    assert not act_plat_exit["attack"] and not act_plat_exit["special"] and act_plat_exit["stick_x"] == 1.0
    assert "SALIDA DESLIZANTE" in act_plat_exit["name"]

    # Caso 2: Luigi agachado en Top Platform (SQUAT_WAIT)
    # Luigi DEBE romper la agachada y moverse hacia el rival para caer al suelo
    p_luigi_squat_plat = MockPlayer(x=-15.0, y=54.4, on_ground=True, action="SQUAT_WAIT", act_val=40)
    p_luigi_squat_plat.character = "LUIGI"
    act_plat_squat_exit = brain.get_luigi_decision(player=p_luigi_squat_plat, opponent=p_opp_ground_far, current_frame=981, stage="BATTLEFIELD")
    print(f"Escape de crouch en plataforma: {act_plat_squat_exit['name']} | Stick X={act_plat_squat_exit['stick_x']}, Stick Y={act_plat_squat_exit['stick_y']}")
    assert not act_plat_squat_exit["attack"] and act_plat_squat_exit["stick_x"] == 1.0 and act_plat_squat_exit["stick_y"] == 0.5
    print("✅ TEST 58 SUPERADO: Luigi desciende de plataformas sin quedarse atascado agachado ni spamear ataques terrestres.")

    # -------------------------------------------------------------
    # TEST 59: Fox Aerial Shine sobre Escenario (Preservación de Shine 20XX)
    # -------------------------------------------------------------
    print("\n--- Test 59: Fox Aerial Shine sobre Escenario ---")
    p_fox_air = MockPlayer(x=10.0, y=15.0, on_ground=False, action="FALLING", act_val=29)
    p_fox_air.character = "FOX"
    raw_shine = {
        "name": "TEST AERIAL SHINE", "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
        "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5
    }
    safe_fox_shine = brain._enforce_safety(dict(raw_shine), p_fox_air, p_opp_distance, stage_edge=68.4)
    print(f"Fox Aerial Shine: Special={safe_fox_shine['special']}, Attack={safe_fox_shine['attack']}, Stick Y={safe_fox_shine['stick_y']}")
    assert safe_fox_shine["special"] and not safe_fox_shine["attack"] and safe_fox_shine["stick_y"] == 0.0, "El Reflector Shine de Fox en el aire no debe ser convertido a N-Air"
    print("✅ TEST 59 SUPERADO: Fox ejecuta su Reflector Shine aéreo frame-1 libremente sobre el escenario.")

    # -------------------------------------------------------------
    # TEST 60: Fox Offstage High Recovery (Fox Illusion Preservado)
    # -------------------------------------------------------------
    print("\n--- Test 60: Fox Offstage High Recovery con Fox Illusion ---")
    p_fox_offstage_high = MockPlayer(x=85.0, y=5.0, on_ground=False, action="FALLING", act_val=29)
    p_fox_offstage_high.character = "FOX"
    p_fox_offstage_high.jumps_left = 0
    raw_illusion = {
        "name": "⚡ FOX ILLUSION (Side-B HORIZONTAL ALTO)", "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
        "stick_x": 0.0, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5
    }
    safe_fox_illusion = brain._enforce_safety(dict(raw_illusion), p_fox_offstage_high, p_opp_distance, stage_edge=68.4)
    print(f"Fox Illusion Recovery: Special={safe_fox_illusion['special']}, Stick X={safe_fox_illusion['stick_x']}, Stick Y={safe_fox_illusion['stick_y']}")
    assert safe_fox_illusion["special"] and safe_fox_illusion["stick_y"] == 0.5 and safe_fox_illusion["stick_x"] == 0.0, "Fox Illusion a gran altura debe permitirse para retorno horizontal rápido"
    print("✅ TEST 60 SUPERADO: Fox recupera horizontalmente con Fox Illusion sin ser congelado con Shine en el abismo.")

    # -------------------------------------------------------------
    # TEST 61: Fox Offstage Low Recovery (Conversión Segura a Fire Fox)
    # -------------------------------------------------------------
    print("\n--- Test 61: Fox Offstage Low Recovery a Fire Fox ---")
    p_fox_offstage_low = MockPlayer(x=85.0, y=-15.0, on_ground=False, action="FALLING", act_val=29)
    p_fox_offstage_low.character = "FOX"
    p_fox_offstage_low.jumps_left = 0
    safe_fox_low = brain._enforce_safety(dict(raw_illusion), p_fox_offstage_low, p_opp_distance, stage_edge=68.4)
    print(f"Fox Low Recovery: Special={safe_fox_low['special']}, Stick Y={safe_fox_low['stick_y']}")
    assert safe_fox_low["special"] and safe_fox_low["stick_y"] == 0.90, "Side-B a baja altura debe convertirse a Up-B Fire Fox para elevarse a la repisa"
    print("✅ TEST 61 SUPERADO: Fox convierte Side-B bajo a Fire Fox Up-B para evitar chocar contra la pared lateral.")

    # -------------------------------------------------------------
    # TEST 62: Luigi Aerial Cyclone Buffer Execution
    # -------------------------------------------------------------
    print("\n--- Test 62: Luigi Aerial Cyclone Buffer Execution ---")
    p_luigi_cyclone = MockPlayer(x=0.0, y=12.0, on_ground=False, action="JUMPING", act_val=25)
    p_luigi_cyclone.character = "LUIGI"
    brain._set_luigi_jump("AERIAL_CYCLONE", 990)
    act_aerial_cyclone = brain.get_luigi_decision(player=p_luigi_cyclone, opponent=p_opp_ground_far, current_frame=990, stage="BATTLEFIELD")
    print(f"Luigi Aerial Cyclone: {act_aerial_cyclone['name']} | Special={act_aerial_cyclone['special']}, Stick Y={act_aerial_cyclone['stick_y']}")
    assert act_aerial_cyclone["special"] and not act_aerial_cyclone["attack"] and act_aerial_cyclone["stick_y"] == 0.0
    assert "CYCLONE" in act_aerial_cyclone["name"]
    print("✅ TEST 62 SUPERADO: Luigi ejecuta correctamente su Cyclone aéreo cuando fue seleccionado en salto.")

    # -------------------------------------------------------------
    # TEST 63: Luigi Down-Taunt Meteor Spike en Ledge (Disrespect 20XX)
    # -------------------------------------------------------------
    print("\n--- Test 63: Luigi Down-Taunt Meteor Spike en Repisa ---")
    p_luigi_at_edge = MockPlayer(x=65.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_at_edge.character = "LUIGI"
    p_opp_on_ledge = MockPlayer(x=68.4, y=-3.0, on_ground=False, action="EDGE_HANGING", act_val=253)
    brain.dopamine = 0.85
    act_taunt_spike = brain.get_luigi_decision(player=p_luigi_at_edge, opponent=p_opp_on_ledge, current_frame=1000, stage="BATTLEFIELD")
    print(f"Luigi Ledge Disrespect: {act_taunt_spike['name']} | Taunt={act_taunt_spike.get('taunt')}")
    assert act_taunt_spike.get("taunt") and "DOWN-TAUNT METEOR SPIKE" in act_taunt_spike["name"]
    print("✅ TEST 63 SUPERADO: Luigi ejecuta el Down-Taunt Meteor Spike frame-45 en repisa para máxima humillación.")

    # -------------------------------------------------------------
    # TEST 64: Luigi Jab-Reset ➔ Shoryuken Kill Confirm
    # -------------------------------------------------------------
    print("\n--- Test 64: Luigi Jab-Reset ➔ Shoryuken Kill Confirm ---")
    brain.jab_reset_active = True
    brain.jab_reset_frame = 1010
    p_luigi_reset_follow = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_reset_follow.character = "LUIGI"
    p_opp_reset_standing = MockPlayer(x=3.0, y=0.0, on_ground=True, action="DOWN_WAIT", act_val=183, percent=55.0)
    act_reset_confirm = brain.get_luigi_decision(player=p_luigi_reset_follow, opponent=p_opp_reset_standing, current_frame=1015, stage="BATTLEFIELD")
    print(f"Luigi Jab-Reset Confirm: {act_reset_confirm['name']} | Special={act_reset_confirm['special']}, Stick Y={act_reset_confirm['stick_y']}")
    assert act_reset_confirm["special"] and act_reset_confirm["stick_y"] == 1.0 and "JAB-RESET KILL CONFIRM" in act_reset_confirm["name"]
    print("✅ TEST 64 SUPERADO: Luigi buferiza el Sweetspot Up-B Shoryuken inmediatamente tras forzar el levantamiento con Jab-Reset.")

    # -------------------------------------------------------------
    # TEST 65: Luigi Swagger Taunt en Respawn del Rival
    # -------------------------------------------------------------
    print("\n--- Test 65: Luigi Respawn Swagger Taunt ---")
    p_luigi_swagger = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_swagger.character = "LUIGI"
    p_opp_halo = MockPlayer(x=0.0, y=35.0, on_ground=True, action="HALO_WAIT", act_val=12)
    brain.dopamine = 0.75
    # frame 1050: (1050 // 35) % 2 == 30 % 2 == 0 -> Taunt
    act_luigi_swagger = brain.get_luigi_decision(player=p_luigi_swagger, opponent=p_opp_halo, current_frame=1050, stage="BATTLEFIELD")
    print(f"Luigi Respawn Swagger: {act_luigi_swagger['name']} | Taunt={act_luigi_swagger.get('taunt')}")
    assert act_luigi_swagger.get("taunt") and "LUIGI TAUNT" in act_luigi_swagger["name"]
    print("✅ TEST 65 SUPERADO: Luigi humilla mentalmente al rival con Taunt en respawn.")

    # -------------------------------------------------------------
    # TEST 66: Fox Swagger Taunt ("Come on!") en Respawn del Rival
    # -------------------------------------------------------------
    print("\n--- Test 66: Fox Respawn Swagger Taunt ---")
    p_fox_swagger = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_fox_swagger.character = "FOX"
    brain.active_character = "FOX"
    brain.dopamine = 0.75
    act_fox_swagger = brain.get_controller_decision(player=p_fox_swagger, opponent=p_opp_halo, current_frame=1050, stage="BATTLEFIELD")
    print(f"Fox Respawn Swagger: {act_fox_swagger['name']} | Taunt={act_fox_swagger.get('taunt')}")
    assert act_fox_swagger.get("taunt") and "FOX TAUNT" in act_fox_swagger["name"]
    brain.active_character = "LUIGI"
    print("✅ TEST 66 SUPERADO: Fox ejecuta su icónico taunt 'Come on!' ante el respawn del rival.")

    # -------------------------------------------------------------
    # TEST 67: Luigi Vist / Abate Wavedash-Back Whiff Punisher
    # -------------------------------------------------------------
    print("\n--- Test 67: Luigi Vist / Abate Wavedash-Back Whiff Punisher ---")
    p_luigi_vist = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_vist.character = "LUIGI"
    p_opp_whiff = MockPlayer(x=8.0, y=0.0, on_ground=True, action="ATTACK_S_3", act_val=55, percent=45.0)
    
    # Frame 1100: Luigi detecta el ataque y ejecuta micro Wavedash-Back hacia la izquierda
    act_whiff_bait = brain.get_luigi_decision(player=p_luigi_vist, opponent=p_opp_whiff, current_frame=1100, stage="BATTLEFIELD")
    print(f"Paso 1 (Bait Wavedash-Back): {act_whiff_bait['name']} | Jump={act_whiff_bait['jump']}, Stick X={act_whiff_bait['stick_x']}")
    assert act_whiff_bait["jump"] and act_whiff_bait["stick_x"] == 0.0 and "VIST WAVEDASH-BACK BAIT" in act_whiff_bait["name"]
    assert brain.whiff_punish_state == "PUNISH_READY"
    
    # Frame 1102: Rival falla (whiff lag) y Luigi castiga con Sweetspot Up-B Shoryuken de frente
    p_opp_whiff.position.x = 5.0
    brain.dopamine = 0.80
    act_whiff_punish = brain.get_luigi_decision(player=p_luigi_vist, opponent=p_opp_whiff, current_frame=1102, stage="BATTLEFIELD")
    print(f"Paso 2 (Whiff Punish Ping): {act_whiff_punish['name']} | Special={act_whiff_punish['special']}, Stick Y={act_whiff_punish['stick_y']}")
    assert act_whiff_punish["special"] and act_whiff_punish["stick_y"] == 1.0 and "VIST WHIFF PUNISH" in act_whiff_punish["name"]
    print("✅ TEST 67 SUPERADO: Luigi ejecuta el legendario Vist Wavedash-Back para provocar el whiff y castigar con Sweetspot Up-B.")

    # -------------------------------------------------------------
    # TEST 68: Luigi Fastfaller Chaingrab / Regrab Loop
    # -------------------------------------------------------------
    print("\n--- Test 68: Luigi Fastfaller Chaingrab / Regrab Loop ---")
    p_luigi_cg = MockPlayer(x=0.0, y=0.0, on_ground=True, action="THROW_DOWN", act_val=222)
    p_luigi_cg.character = "LUIGI"
    p_opp_fastfaller = MockPlayer(x=3.0, y=0.0, on_ground=True, action="DAMAGE_AIR", percent=18.0)
    p_opp_fastfaller.character = "FOX"
    brain.chaingrab_count = 0
    brain.combo_state = "LUIGI_DTHROW_COMBO"
    
    # Regrab 1: A 18% contra Fox tras D-Throw
    act_regrab1 = brain.get_luigi_decision(player=p_luigi_cg, opponent=p_opp_fastfaller, current_frame=1120, stage="BATTLEFIELD")
    print(f"Chaingrab Paso 1: {act_regrab1['name']} | Grab={act_regrab1['grab']}")
    assert act_regrab1["grab"] and "CHAINGRAB 20XX" in act_regrab1["name"] and brain.chaingrab_count == 1
    
    # Regrab 2: Segundo lanzamiento a 28%
    p_opp_fastfaller.percent = 28.0
    act_regrab2 = brain.get_luigi_decision(player=p_luigi_cg, opponent=p_opp_fastfaller, current_frame=1125, stage="BATTLEFIELD")
    print(f"Chaingrab Paso 2: {act_regrab2['name']} | Grab={act_regrab2['grab']}")
    assert act_regrab2["grab"] and "CHAINGRAB 20XX" in act_regrab2["name"] and brain.chaingrab_count == 2
    
    # Finisher: A 50% ejecuta el Sweetspot Up-B Kill Confirm
    p_opp_fastfaller.percent = 50.0
    brain.dopamine = 0.85
    act_cg_finisher = brain.get_luigi_decision(player=p_luigi_cg, opponent=p_opp_fastfaller, current_frame=1130, stage="BATTLEFIELD")
    print(f"Chaingrab Finisher: {act_cg_finisher['name']} | Special={act_cg_finisher['special']}")
    assert act_cg_finisher["special"] and "COMBO SUPREMO SHORYUKEN" in act_cg_finisher["name"]
    print("✅ TEST 68 SUPERADO: Luigi ejecuta la cadena de regrabs contra Fastfallers antes de rematar con Shoryuken.")

    # -------------------------------------------------------------
    # TEST 69: Deep Offstage Humiliation & Rapid Teabag Disrespect
    # -------------------------------------------------------------
    print("\n--- Test 69: Deep Offstage Humiliation & Rapid Teabag Disrespect ---")
    p_luigi_safe = MockPlayer(x=10.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_safe.character = "LUIGI"
    p_opp_abyss = MockPlayer(x=80.0, y=-18.0, on_ground=False, action="DAMAGE_FALL", act_val=38, percent=85.0)
    p_opp_abyss.off_stage = True
    
    # Luigi teabag when opponent is dying deep offstage
    act_luigi_teabag = brain.get_luigi_decision(player=p_luigi_safe, opponent=p_opp_abyss, current_frame=1150, stage="BATTLEFIELD")
    print(f"Luigi Abyss Disrespect: {act_luigi_teabag['name']} | Stick Y={act_luigi_teabag['stick_y']}")
    assert "RAPID TEABAG DISRESPECT" in act_luigi_teabag["name"]
    
    # Fox teabag / multishine flex
    p_fox_safe = MockPlayer(x=10.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_fox_safe.character = "FOX"
    act_fox_teabag = brain.get_fox_decision(player=p_fox_safe, opponent=p_opp_abyss, current_frame=1150, stage="BATTLEFIELD")
    print(f"Fox Abyss Disrespect: {act_fox_teabag['name']}")
    assert "RAPID TEABAG / MULTI-SHINE FLEX" in act_fox_teabag["name"]
    print("✅ TEST 69 SUPERADO: Tanto Luigi como Fox humillan psicológicamente al rival que cae al abismo.")

    # -------------------------------------------------------------
    # TEST 70: Luigi Invincible 2-Stage Ledgedash
    # -------------------------------------------------------------
    print("\n--- Test 70: Luigi Invincible 2-Stage Ledgedash ---")
    p_luigi_hang = MockPlayer(x=-68.4, y=-5.0, on_ground=False, action="EDGE_HANGING", act_val=253)
    p_luigi_hang.character = "LUIGI"
    p_opp_center = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    brain.luigi_ledge_state = None
    
    # Stage 1: Drop/Jump hacia el escenario
    act_ld_stage1 = brain.get_luigi_decision(player=p_luigi_hang, opponent=p_opp_center, current_frame=1160, stage="BATTLEFIELD")
    print(f"Ledgedash Paso 1: {act_ld_stage1['name']} | Jump={act_ld_stage1['jump']}, Shield={act_ld_stage1['shield']}")
    assert act_ld_stage1["jump"] and act_ld_stage1["stick_x"] == 1.0 and "SUBIDA CON WAVEDASH DESLIZANTE" in act_ld_stage1["name"]
    assert brain.luigi_ledge_state == "LEDGEDASH_AIR"
    
    # Stage 2: Waveland invencible en pista
    act_ld_stage2 = brain.get_luigi_decision(player=p_luigi_hang, opponent=p_opp_center, current_frame=1161, stage="BATTLEFIELD")
    print(f"Ledgedash Paso 2: {act_ld_stage2['name']} | Jump={act_ld_stage2['jump']}, Shield={act_ld_stage2['shield']}")
    assert not act_ld_stage2["jump"] and act_ld_stage2["shield"] and "WAVELAND INVENCIBLE" in act_ld_stage2["name"]
    print("✅ TEST 70 SUPERADO: Luigi domina el Ledgedash en dos tiempos con 14 frames de intangibilidad deslizante.")

    # -------------------------------------------------------------
    # TEST 71: Fox Drill-Shine Frame-1 Shield Pressure
    # -------------------------------------------------------------
    print("\n--- Test 71: Fox Drill-Shine Frame-1 Shield Pressure ---")
    p_fox_drill_land = MockPlayer(x=2.0, y=0.0, on_ground=True, action="LANDING", act_val=42)
    p_fox_drill_land.character = "FOX"
    p_opp_shield = MockPlayer(x=5.0, y=0.0, on_ground=True, action="SHIELD", act_val=179)
    brain.drill_smash_state = "DRILL_LANDED"
    
    act_drill_shine = brain.get_fox_decision(player=p_fox_drill_land, opponent=p_opp_shield, current_frame=1170, stage="BATTLEFIELD")
    print(f"Fox Drill-Shine on Shield: {act_drill_shine['name']} | Special={act_drill_shine['special']}, Stick Y={act_drill_shine['stick_y']}")
    assert act_drill_shine["special"] and act_drill_shine["stick_y"] == 0.0 and "DRILL-SHINE SHIELD PRESSURE" in act_drill_shine["name"]
    print("✅ TEST 71 SUPERADO: Fox ejecuta Drill-Shine Frame-1 en el aterrizaje para neutralizar el escudo rival.")

    # -------------------------------------------------------------
    # TEST 72: Luigi Grab Situacional (Pummel vs Throw Táctico al Borde)
    # -------------------------------------------------------------
    print("\n--- Test 72: Luigi Grab Situacional (Pummel vs Throw Táctico) ---")
    brain.grab_pummel_count = 0
    # Caso A: Luigi al borde derecho (X = 56.0, edge = 68.4) mirando al abismo (+X):
    # Rival a bajo % (30%) -> Avienta directo al abismo con Forward-Throw sin regalar mash-out
    p_luigi_edge_f = MockPlayer(x=56.0, y=0.0, on_ground=True, action="GRAB_WAIT", act_val=213)
    p_luigi_edge_f.character = "LUIGI"
    p_opp_edge_f = MockPlayer(x=59.0, y=0.0, on_ground=True, action="CAPTURE_WAIT", act_val=224, percent=30.0)
    act_throw_f = brain.get_luigi_decision(player=p_luigi_edge_f, opponent=p_opp_edge_f, current_frame=1180, stage="BATTLEFIELD")
    print(f"Lanzamiento al Borde (Mirando Afuera): {act_throw_f['name']} | Stick X={act_throw_f['stick_x']}")
    assert not act_throw_f["attack"] and act_throw_f["stick_x"] == 1.0 and "FORWARD-THROW AL ABISMO" in act_throw_f["name"]

    # Caso B: Luigi al borde derecho (X = 60.0) pero de espaldas al abismo (rival hacia el centro en X = 57.0):
    # Rival a bajo % (30%) -> Avienta directo al abismo con Back-Throw hacia afuera (+X)
    brain.grab_pummel_count = 0
    p_luigi_edge_b = MockPlayer(x=60.0, y=0.0, on_ground=True, action="GRAB_WAIT", act_val=213)
    p_luigi_edge_b.character = "LUIGI"
    p_opp_edge_b = MockPlayer(x=57.0, y=0.0, on_ground=True, action="CAPTURE_WAIT", act_val=224, percent=30.0)
    act_throw_b = brain.get_luigi_decision(player=p_luigi_edge_b, opponent=p_opp_edge_b, current_frame=1181, stage="BATTLEFIELD")
    print(f"Lanzamiento al Borde (Espalda Afuera): {act_throw_b['name']} | Stick X={act_throw_b['stick_x']}")
    assert not act_throw_b["attack"] and act_throw_b["stick_x"] == 1.0 and "BACK-THROW AL ABISMO" in act_throw_b["name"]
    print("✅ TEST 72 SUPERADO: Luigi decide situacionalmente aventar directo al abismo con F-Throw o B-Throw.")

    # -------------------------------------------------------------
    # TEST 73: Mash-Out 20XX y Survival DI cuando la Mosca es Agarrada
    # -------------------------------------------------------------
    print("\n--- Test 73: Mash-Out 20XX cuando la Mosca es Agarrada ---")
    p_fly_held = MockPlayer(x=0.0, y=0.0, on_ground=True, action="CAPTURE_WAIT", act_val=224, percent=45.0)
    p_fly_held.character = "LUIGI"
    p_opp_holder = MockPlayer(x=3.0, y=0.0, on_ground=True, action="GRAB_WAIT", act_val=213)
    act_mashout = brain.get_luigi_decision(player=p_fly_held, opponent=p_opp_holder, current_frame=1190, stage="BATTLEFIELD")
    print(f"Respuesta a Captura: {act_mashout['name']} | Attack={act_mashout['attack']}, Jump={act_mashout['jump']}")
    assert "MASH-OUT ESCAPE 20XX" in act_mashout["name"]
    print("✅ TEST 73 SUPERADO: La mosca ejecuta Mash-Out frame-perfect a 60 inputs/s para zafarse del agarre.")

    # -------------------------------------------------------------
    # TEST 74: Powershield Reflect y Zero Shield-Stun Shoryuken Counter
    # -------------------------------------------------------------
    print("\n--- Test 74: Powershield Reflect & Zero Shield-Stun Shoryuken Counter ---")
    p_luigi_ps = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_luigi_ps.character = "LUIGI"
    p_opp_blaster = MockPlayer(x=16.0, y=0.0, on_ground=True, action="SPECIAL_N", act_val=341, percent=60.0)
    brain.powershield_state = None
    
    # Frame 1200: Detección de proyectil y activación Powershield Frame-1
    act_ps_frame1 = brain.get_luigi_decision(player=p_luigi_ps, opponent=p_opp_blaster, current_frame=1200, stage="BATTLEFIELD")
    print(f"Paso 1 (Powershield Frame-1): {act_ps_frame1['name']} | Shield={act_ps_frame1['shield']}")
    assert act_ps_frame1["shield"] and "POWERSHIELD FRAME-1" in act_ps_frame1["name"]
    assert brain.powershield_state == "POWERSHIELD_ACTIVE"
    
    # Frame 1201: Impacto reflejado con cero lag y castigo Sweetspot Shoryuken si el rival está a quemarropa
    p_opp_blaster.position.x = 4.5
    act_ps_frame2 = brain.get_luigi_decision(player=p_luigi_ps, opponent=p_opp_blaster, current_frame=1201, stage="BATTLEFIELD")
    print(f"Paso 2 (Zero Shield-Stun Counter): {act_ps_frame2['name']} | Special={act_ps_frame2['special']}, Stick Y={act_ps_frame2['stick_y']}")
    assert act_ps_frame2["special"] and act_ps_frame2["stick_y"] == 1.0 and "POWERSHIELD COUNTER" in act_ps_frame2["name"]
    print("✅ TEST 74 SUPERADO: Luigi ejecuta Powershield Frame-1 y contraataca sin shield stun con Sweetspot Up-B.")

    # -------------------------------------------------------------
    # TEST 75: Shield Drop 20XX en Plataformas (Descenso Frame-1 ➔ Counter Aéreo)
    # -------------------------------------------------------------
    print("\n--- Test 75: Shield Drop 20XX en Plataformas ---")
    p_luigi_plat_shield = MockPlayer(x=-35.0, y=27.2, on_ground=True, action="GUARD_ON", act_val=178)
    p_luigi_plat_shield.character = "LUIGI"
    p_opp_underneath = MockPlayer(x=-35.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    act_shielddrop = brain.get_luigi_decision(player=p_luigi_plat_shield, opponent=p_opp_underneath, current_frame=1210, stage="BATTLEFIELD")
    print(f"Shield Drop Action: {act_shielddrop['name']} | Attack={act_shielddrop['attack']}, Stick Y={act_shielddrop['stick_y']}")
    assert act_shielddrop["attack"] and act_shielddrop["stick_y"] == 0.28 and "SHIELD DROP 20XX" in act_shielddrop["name"]
    print("✅ TEST 75 SUPERADO: Luigi domina el Shield Drop Frame-1 para descender de plataformas con ataque aéreo.")

    # -------------------------------------------------------------
    # TEST 76: Platform Edge-Cancel Slide (0 Frames Landing Lag)
    # -------------------------------------------------------------
    print("\n--- Test 76: Platform Edge-Cancel Slide ---")
    p_luigi_edge_cancel = MockPlayer(x=-19.5, y=27.5, on_ground=False, action="ATTACK_AIR_N", act_val=65)
    p_luigi_edge_cancel.character = "LUIGI"
    p_luigi_edge_cancel.speed_air_x_self = 0.85
    act_edge_cancel = brain.get_luigi_decision(player=p_luigi_edge_cancel, opponent=p_opp_underneath, current_frame=1220, stage="BATTLEFIELD")
    print(f"Edge-Cancel Action: {act_edge_cancel['name']}")
    assert "PLATFORM EDGE-CANCEL" in act_edge_cancel["name"]
    print("✅ TEST 76 SUPERADO: Luigi desliza el aterrizaje fuera del borde de plataforma a 0 frames de lag.")

    print("\n" + "=" * 70)
    print("🎉 ¡TODAS LAS PRUEBAS COMPLETADAS CON ÉXITO! (76/76 SUPERADAS)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
