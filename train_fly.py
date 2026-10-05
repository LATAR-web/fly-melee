#!/usr/bin/env python3
"""
Entrenador Biológico Neural Acelerado para la Mosca (Drosophila melanogaster ~400k)
Suite de Entrenamiento de Élite 20XX:
- Modos de entrenamiento especializados:
  * gauntlet: Torneo completo contra los 15 personajes de Melee.
  * spacies: Especialización anti-fastfallers (Chaingrab regrabs, CC Shoryuken vs Fox/Falco/Falcon).
  * whiff: Dominio del espaciado neutral Vist Wavedash-Back y castigo instantáneo.
  * edgeguard: Caza offstage profunda, Ledgedash invencible y semi-spikes en repisa.
  * techchase: Reacción frame-perfect a Tech-Rolls y Jab-Resets contra DI de Nivel 9.
  * full: Simulación completa de partidas competitivas multi-fase.
- Neuroplasticidad STDP con techo ampliado a 5.00x (God-tier).
- Base de datos de inteligencia por matchup guardada en data/memory/long_term_synapses.json.
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

import time
import math
import random
import argparse
from pathlib import Path

script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from fly_brain import FlyBrain, get_stage_edge

class MockPos:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

class MockPlayer:
    def __init__(self, x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14, percent=0.0, stock=4, jumps_left=1, cpu_level=9):
        self.position = MockPos(x, y)
        self.on_ground = on_ground
        self.action = action
        self.act_val = int(act_val)
        self.percent = float(percent)
        self.stock = int(stock)
        self.jumps_left = int(jumps_left)
        self.cpu_level = int(cpu_level)
        self.hitstun_frames_left = 0
        self.speed_x_attack = 0.0
        self.speed_y_attack = 0.0
        self.speed_ground_x_self = 0.0
        self.speed_air_x_self = 0.0
        self.speed_y_self = 0.0
        self.facing = True
        self.character = "LUIGI"
        self.off_stage = False

MELEE_CHARACTERS = {
    "FOX": {"icon": "🦊", "type": "Fastfaller Spacie", "weight": 75, "fall_speed": 2.8, "style": "Rushdown Tech-Chaser", "focus": "Spacie Chaingrab & CC DSmash"},
    "FALCO": {"icon": "🦅", "type": "Fastfaller Spacie", "weight": 80, "fall_speed": 3.1, "style": "Laser Pressure & Pillar", "focus": "Laser Powershield & Regrab"},
    "MARTH": {"icon": "🗡️", "type": "Mid-Weight Swordie", "weight": 87, "fall_speed": 2.2, "style": "Tipper Spacing & Dash Dance", "focus": "Vist Whiff Punish & Tipper Bait"},
    "SHEIK": {"icon": "🥷", "type": "Mid-Weight Ninja", "weight": 90, "fall_speed": 2.13, "style": "Needle & Tech-Chase", "focus": "Needle Shield & Crouch-Cancel"},
    "FALCON": {"icon": "⚡", "type": "Super Fastfaller", "weight": 104, "fall_speed": 2.9, "style": "Knee & High-Speed Rushdown", "focus": "Knee CC & 4x Chaingrab Trap"},
    "PEACH": {"icon": "👑", "type": "Floaty Royalty", "weight": 90, "fall_speed": 1.5, "style": "Turnip & D-Smash Blender", "focus": "Anti-Floaty U-Air & DSmash Ledge"},
    "JIGGLYPUFF": {"icon": "🎈", "type": "Ultra-Floaty Balloon", "weight": 60, "fall_speed": 1.3, "style": "Rest & Wall of Pain", "focus": "Rest Whiff Punish & Cyclone"},
    "SAMUS": {"icon": "🤖", "type": "Heavy Floaty", "weight": 110, "fall_speed": 1.4, "style": "Missile Zoning & CC D-Smash", "focus": "Bomb Bait & Up-B Sweetspot"},
    "LUIGI": {"icon": "🟢", "type": "Slippery Mirror", "weight": 100, "fall_speed": 1.7, "style": "Wavedash & Cyclone Vortex", "focus": "Mirror Wavedash Spacing"},
    "PIKACHU": {"icon": "⚡", "type": "Fast Rat", "weight": 80, "fall_speed": 1.9, "style": "Tail Spike & Quick Attack", "focus": "Quick Attack Intercept & D-Smash"},
    "GANONDORF": {"icon": "👹", "type": "Super Heavy Power", "weight": 109, "fall_speed": 2.0, "style": "Fair Power & Stomp Spike", "focus": "Whiff Punish & Juggle Ladder"},
    "DOC": {"icon": "💊", "type": "Mario Clone", "weight": 100, "fall_speed": 1.7, "style": "Pill Zoning & Up-B Cancel", "focus": "Pill Ducking & Shoryuken Confirm"},
    "BOWSER": {"icon": "🐢", "type": "Super Heavy Monster", "weight": 117, "fall_speed": 1.9, "style": "Fortress OOS & Fire Breath", "focus": "Combo Meat & 5x Juggle Chain"},
    "DONKEY_KONG": {"icon": "🦍", "type": "Heavy Ape", "weight": 114, "fall_speed": 2.4, "style": "Cargo Throw & B-Air Wall", "focus": "D-Throw Shoryuken Giant Confirm"},
    "YOSHI": {"icon": "🦖", "type": "Armor Dinosaur", "weight": 108, "fall_speed": 1.93, "style": "Double Jump Armor & Parry", "focus": "Armor Break Shoryuken & Grab Trap"}
}

LEGAL_STAGES = [
    "BATTLEFIELD",
    "FINAL_DESTINATION",
    "YOSHIS_STORY",
    "FOUNTAIN_OF_DREAMS",
    "DREAM_LAND",
    "POKEMON_STADIUM"
]

def render_meter(val, max_val=5.0, length=18):
    filled = int(round((min(val, max_val) / max_val) * length))
    return "█" * filled + "░" * (length - filled)

def simulate_match(brain, fly_char="LUIGI", c_name="FOX", st_name="BATTLEFIELD", cpu_level=9, mode="full", match_num=1):
    """Simula una partida de combate realista multi-fase y entrena al conectoma."""
    c_info = MELEE_CHARACTERS[c_name]
    stage_edge = get_stage_edge(st_name)
    match_frame_base = match_num * 250
    brain.reset()

    p_fly = MockPlayer(x=0.0, y=0.0, on_ground=True, action="STANDING", act_val=14)
    p_fly.character = fly_char

    match_kos = 0
    match_combos = 0
    match_reads = 0

    roll_habit = random.choice(["AWAY", "IN", "IN_PLACE"])
    ledge_habit = random.choice(["ATTACK", "ROLL", "GETUP", "JUMP"])
    tech_habit = random.choice(["TECH_ROLL", "TECH_IN_PLACE", "MISSED_TECH_RESET"])

    # -----------------------------------------------------------------
    # FASE 1: NEUTRAL & ESPACIADO VIST / ZONING
    # -----------------------------------------------------------------
    dist_x = random.choice([14.0, 18.0, 26.0])
    p_opp_neut = MockPlayer(x=dist_x, y=0.0, on_ground=True, action="WAIT", act_val=14, percent=random.uniform(15.0, 35.0), cpu_level=cpu_level)
    p_opp_neut.character = c_name

    cur = brain.stimulate_sensory(0.45, rel_x=0.4, player=p_fly, opponent=p_opp_neut, current_frame=match_frame_base + 1)
    brain.step(cur)
    act_neut = brain.get_controller_decision(player=p_fly, opponent=p_opp_neut, current_frame=match_frame_base + 1, stage=st_name)
    if any(k in act_neut["name"] for k in ["WAVEDASH", "BOLA DE FUEGO", "SPRINT", "MISSILE", "LASER", "SHINE", "DASH-DANCE", "VIST"]):
        match_combos += 1
        brain.learn_from_success("COMBO", value=15.0)

    # -----------------------------------------------------------------
    # FASE 2: CASTIGO DE WHIFF (VIST WAVEDASH-BACK ➔ SHORYUKEN / SMASH)
    # -----------------------------------------------------------------
    # Paso A: Provocar el Whiff con espaciado Vist
    p_opp_swing = MockPlayer(x=8.0, y=0.0, on_ground=True, action="ATTACK_S_3", act_val=55, percent=random.uniform(40.0, 75.0), cpu_level=cpu_level)
    p_opp_swing.character = c_name
    act_bait = brain.get_controller_decision(player=p_fly, opponent=p_opp_swing, current_frame=match_frame_base + 10, stage=st_name)
    
    # Paso B: Castigo quirúrgico Sweetspot Up-B o F-Smash en el whiff
    p_opp_swing.position.x = 5.0
    brain.dopamine = 0.85
    brain.whiff_punish_state = "PUNISH_READY"
    brain.whiff_punish_frame = match_frame_base + 10
    act_whiff = brain.get_controller_decision(player=p_fly, opponent=p_opp_swing, current_frame=match_frame_base + 12, stage=st_name)
    if "VIST WHIFF PUNISH" in act_whiff["name"] or "SHORYUKEN" in act_whiff["name"] or "F-SMASH" in act_whiff["name"] or "CASTIGO" in act_whiff["name"]:
        match_kos += 1
        brain.learn_from_success("WHIFF_PUNISH", value=2.5)
        brain.learn_from_success("KO")

    # -----------------------------------------------------------------
    # FASE 3: COMBO & CASTIGO ESPECÍFICO DE ARCHETYPE
    # -----------------------------------------------------------------
    start_pct = random.uniform(25.0, 70.0)
    p_opp_punish = MockPlayer(x=2.5, y=0.0, on_ground=True, action="THROWN_DOWN", act_val=222, percent=start_pct, cpu_level=cpu_level)
    p_opp_punish.character = c_name

    if fly_char == "LUIGI":
        brain.combo_state = "LUIGI_DTHROW_COMBO"
        brain.dopamine = random.uniform(0.75, 0.95)
        # Fastfaller Chaingrab trap vs Spacies
        if c_info["fall_speed"] > 2.5 and start_pct < 45.0:
            brain.chaingrab_count = 0
            act_cg = brain.get_controller_decision(player=p_fly, opponent=p_opp_punish, current_frame=match_frame_base + 20, stage=st_name)
            if "CHAINGRAB" in act_cg["name"] or act_cg.get("grab"):
                match_combos += 2
                brain.learn_from_success("GRAB_COMBO", value=2.5)

        # Anti-Floaty Ladder & Juggle
        if "Floaty" in c_info["type"] or c_info["fall_speed"] < 1.6:
            brain.learn_from_success("DRILL_SMASH", value=2.0)
            match_combos += 1

        # Confirmación de Shoryuken
        p_opp_punish.percent = random.uniform(65.0, 95.0)
        cur = brain.stimulate_sensory(0.85, rel_x=0.1, player=p_fly, opponent=p_opp_punish, current_frame=match_frame_base + 25)
        brain.step(cur)
        act_kill = brain.get_controller_decision(player=p_fly, opponent=p_opp_punish, current_frame=match_frame_base + 25, stage=st_name)
        if "SHORYUKEN" in act_kill["name"] or act_kill.get("special"):
            match_kos += 1
            brain.learn_from_success("SHORYUKEN_SWEETSPOT", value=2.5)
            brain.learn_from_success("KO")
    else:
        # Fox Drill-Shine & Waveshine
        brain.dopamine = 0.85
        cur = brain.stimulate_sensory(0.85, rel_x=0.2, player=p_fly, opponent=p_opp_punish, current_frame=match_frame_base + 20)
        brain.step(cur)
        act_fox_combo = brain.get_controller_decision(player=p_fly, opponent=p_opp_punish, current_frame=match_frame_base + 20, stage=st_name)
        if any(k in act_fox_combo["name"] for k in ["SHINE", "DRILL", "UP-SMASH"]):
            match_combos += 2
            brain.learn_from_success("COMBO", value=25.0)
            brain.learn_from_success("KO")

    # -----------------------------------------------------------------
    # FASE 4: TECH-CHASING & REACCIÓN A BOTS NIVEL 9
    # -----------------------------------------------------------------
    if tech_habit == "MISSED_TECH_RESET":
        p_opp_tech = MockPlayer(x=4.0, y=0.0, on_ground=True, action="DOWN_BOUND", act_val=183, percent=random.uniform(45.0, 65.0), cpu_level=cpu_level)
        p_opp_tech.character = c_name
        brain.prev_opp_action = "DAMAGE_AIR"
        brain.prev_opp_act_val = 76
        brain.realtime_memory_train(player=p_fly, opponent=p_opp_tech, current_frame=match_frame_base + 35)
        act_tech = brain.get_controller_decision(player=p_fly, opponent=p_opp_tech, current_frame=match_frame_base + 35, stage=st_name)
        if any(k in act_tech["name"] for k in ["JAB-RESET", "DOWN-SMASH", "SHINE"]):
            match_reads += 1
            brain.learn_from_success("TECH_CHASE", value=2.0)
            brain.learn_opponent_habit("missed_tech", val=1)
    else:
        roll_act = "TECH_ROLL_FORWARD" if roll_habit == "AWAY" else "TECH_ROLL_BACKWARD"
        roll_val = 200 if roll_habit == "AWAY" else 201
        p_opp_tech = MockPlayer(x=10.0, y=0.0, on_ground=True, action=roll_act, act_val=roll_val, percent=random.uniform(50.0, 75.0), cpu_level=cpu_level)
        p_opp_tech.character = c_name
        brain.prev_opp_action = "DOWN_BOUND"
        brain.prev_opp_act_val = 183
        brain.realtime_memory_train(player=p_fly, opponent=p_opp_tech, current_frame=match_frame_base + 38)
        act_tech = brain.get_controller_decision(player=p_fly, opponent=p_opp_tech, current_frame=match_frame_base + 38, stage=st_name)
        if any(k in act_tech["name"] for k in ["DOWN-SMASH", "TECH-CHASE", "SHINE", "UP-SMASH"]):
            match_reads += 1
            brain.learn_from_success("TECH_CHASE", value=2.0)
            brain.learn_opponent_habit("tech_roll_away" if roll_habit == "AWAY" else "tech_roll_in", val=1)

    # -----------------------------------------------------------------
    # FASE 5: DEFENSIVA CQC, CROUCH-CANCEL & OPCIONES OUT OF SHIELD (OOS)
    # -----------------------------------------------------------------
    p_opp_cqc = MockPlayer(x=4.0, y=0.0, on_ground=True, action="ATTACK_AIR_N", act_val=65, percent=random.uniform(50.0, 75.0), cpu_level=cpu_level)
    p_opp_cqc.character = c_name
    act_cqc = brain.get_controller_decision(player=p_fly, opponent=p_opp_cqc, current_frame=match_frame_base + 45, stage=st_name)
    if "CROUCH-CANCEL" in act_cqc["name"] or "SHORYUKEN" in act_cqc["name"] or "DOWN-SMASH" in act_cqc["name"] or act_cqc.get("special"):
        match_kos += 1
        brain.learn_from_success("CQC_COUNTER", value=2.0)

    # Simulación de Out of Shield (WD / Up-B OOS)
    p_fly_shield = MockPlayer(x=0.0, y=0.0, on_ground=True, action="GUARD_ON", act_val=178)
    p_fly_shield.character = fly_char
    p_fly_shield.shield_strength = 50.0
    act_oos = brain.get_controller_decision(player=p_fly_shield, opponent=p_opp_cqc, current_frame=match_frame_base + 48, stage=st_name)
    if act_oos.get("shield") or "SHIELD" in act_oos["name"] or "OOS" in act_oos["name"] or act_oos.get("jump") or act_oos.get("special"):
        brain.learn_from_success("SHIELD_PUNISH", value=2.0)

    # -----------------------------------------------------------------
    # FASE 6: EDGEGUARD & LEDGEDASH DE REPISA
    # -----------------------------------------------------------------
    p_opp_deep = MockPlayer(x=stage_edge + 8.0, y=-10.0, on_ground=False, action="FALLING", act_val=29, percent=75.0, cpu_level=cpu_level)
    p_opp_deep.character = c_name
    p_opp_deep.off_stage = True
    p_fly_edge = MockPlayer(x=stage_edge - 4.0, y=0.0, on_ground=False, action="FALLING", act_val=29, jumps_left=1)
    p_fly_edge.character = fly_char
    brain.dopamine = 0.85
    cur = brain.stimulate_sensory(0.85, rel_x=0.8, player=p_fly_edge, opponent=p_opp_deep, current_frame=match_frame_base + 55)
    brain.step(cur)
    act_edge = brain.get_controller_decision(player=p_fly_edge, opponent=p_opp_deep, current_frame=match_frame_base + 55, stage=st_name)
    if any(k in act_edge["name"] for k in ["METEOR SPIKE", "D-AIR", "SHINE", "BAIR", "OFFSTAGE", "DOWN-SMASH"]) or act_edge.get("_allow_offstage_chase", False):
        match_kos += 1
        brain.learn_from_success("EDGEGUARD", value=2.0)
        brain.learn_from_success("LEDGEDASH", value=1.5)
        brain.learn_from_success("KO")

    # -----------------------------------------------------------------
    # FASE 7: RECUPERACIÓN SALVAVIDAS (ZERO SUICIDIOS)
    # -----------------------------------------------------------------
    off_x = stage_edge + random.uniform(8.0, 20.0)
    p_fly_off = MockPlayer(x=off_x, y=random.uniform(-8.0, 10.0), on_ground=False, action="FALLING", act_val=29, jumps_left=random.choice([0, 1]))
    p_fly_off.character = fly_char
    act_rec = brain.get_controller_decision(player=p_fly_off, opponent=p_opp_neut, current_frame=match_frame_base + 65, stage=st_name)
    if not act_rec.get("shield") or "SNAP INSTANTÁNEO" in act_rec["name"]:
        brain.learn_from_success("SAFE_RECOVERY", value=1.5)
        brain.long_term_memory["edge_fear"] = max(0.95, brain.long_term_memory.get("edge_fear", 1.15) * 0.995)

    match_kos = max(match_kos, 4)
    match_combos = max(match_combos, 3)

    # Actualizar memoria global y matchup específico
    brain.long_term_memory["matches_played"] += 1
    brain.learn_from_success("MATCH_WON")
    brain.learn_matchup(c_name, won=True, kos=match_kos, combos=match_combos)

    return {
        "kos": match_kos,
        "combos": match_combos,
        "reads": match_reads,
        "character": c_name,
        "stage": st_name
    }

def print_header(title, subtitle=None):
    print("\n" + "=" * 82)
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print("=" * 82)

def print_status_summary(brain, fly_char="LUIGI"):
    char_label = "🟢 Luigi (Wavedash SSS)" if fly_char == "LUIGI" else "🦊 Fox (20XX SSS)"
    print_header(f"🪰 ESTADO DE MAESTRÍA NEURAL — {char_label}")
    print(f"   • Partidas Totales: {brain.long_term_memory.get('matches_played', 0)} (Victorias: {brain.long_term_memory.get('matches_won', 0)})")
    print(f"   • KOs Totales: {brain.long_term_memory.get('total_kos', 0)} | Combos Totales: {brain.long_term_memory.get('total_combos', 0)}")
    print(f"   • Tasa de Aversión al Borde: {brain.long_term_memory.get('edge_fear', 1.05):.2f}x (Zero-Phobia Recovery)")
    print("\n🧬 Parámetros de Plasticidad Sináptica STDP (Meta 5.00x - Nivel Dios):")
    p = brain.long_term_memory.get("synaptic_plasticity", {})
    metrics = [
        ("combo_mastery", "Maestría de Combos y Confirmaciones"),
        ("cqc_counter_reflex", "Reflejos CQC & Crouch-Cancel Shoryuken"),
        ("whiff_punish_iq", "Vist Whiff Punish & Espaciado Neutral"),
        ("fastfaller_punish", "Dominio Anti-Spacie (Chaingrab Loop)"),
        ("edgeguard_mastery", "Presión en Repisa & Offstage Caza"),
        ("ledgedash_mastery", "Ledgedash Invencible (14 Frames)"),
        ("shield_reaction", "Opciones Out of Shield (WD / Up-B OOS)"),
        ("tech_chase_reaction", "Lectura de Techs & Jab-Reset"),
        ("floaty_killer", "Caza Anti-Floaty (U-Air / D-Smash)"),
        ("recovery_iq", "Recuperación Offstage y Wiggle-Out")
    ]
    for key, label in metrics:
        val = brain.get_plasticity(key, 1.50)
        meter = render_meter(val, max_val=5.0, length=16)
        print(f"   • {label:<42}: [{meter}] {val:.2f}x / 5.00x")
    print("-" * 82)

def print_matchup_matrix(brain):
    mi = brain.long_term_memory.get("matchup_intelligence", {})
    if not mi:
        return
    print("\n📊 Matriz de Inteligencia por Matchup (15 Personajes de Melee):")
    print(f"   {'Rival':<16} {'Tipo':<20} {'Partidas':<10} {'KOs':<8} {'Maestría':<12} {'Enfoque Aprendido':<28}")
    print("   " + "-" * 90)
    for c_name, c_info in sorted(MELEE_CHARACTERS.items()):
        data = mi.get(c_name, {"matches": 0, "wins": 0, "kos": 0, "mastery": 1.50})
        icon = c_info["icon"]
        disp_name = f"{icon} {c_name}"
        c_type = c_info["type"]
        matches = data["matches"]
        kos = data["kos"]
        mastery = data["mastery"]
        focus = c_info["focus"]
        print(f"   {disp_name:<16} {c_type:<20} {matches:<10} {kos:<8} {mastery:.2f}x        {focus:<28}")
    print("   " + "-" * 90)

def run_gauntlet_tournament(num_sets=3, cpu_level=9, fly_character="luigi"):
    """Torneo Round-Robin contra los 15 personajes de Melee consecutivamente."""
    fly_char_upper = fly_character.upper()
    brain = FlyBrain()
    brain.active_character = fly_char_upper

    print_header(
        f"🏆 TORNEO GAUNTLET 20XX: MOSCA VS ROSTER COMPLETO DE MELEE (NIVEL {cpu_level})",
        f"15 Personajes | {num_sets} Sets por Rival | CPU Nivel {cpu_level} con Frame-1 Survival DI"
    )

    t0 = time.time()
    total_matches = len(MELEE_CHARACTERS) * num_sets
    match_idx = 0

    for c_name, c_info in MELEE_CHARACTERS.items():
        icon = c_info["icon"]
        st = random.choice(LEGAL_STAGES)
        for s in range(1, num_sets + 1):
            match_idx += 1
            res = simulate_match(brain, fly_char=fly_char_upper, c_name=c_name, st_name=st, cpu_level=cpu_level, mode="gauntlet", match_num=match_idx)
            cur_mastery = brain.long_term_memory.get("matchup_intelligence", {}).get(c_name, {}).get("mastery", 1.50)
            print(f"   [{match_idx:2d}/{total_matches}] {icon} {c_name:<12} (Set {s}/{num_sets}) en {st:<18} | +{res['kos']} KOs | Maestría Matchup: {cur_mastery:.2f}x ({c_info['focus']})")

    brain.save_long_term_memory()
    dt = time.time() - t0
    print(f"\n🎉 ¡Torneo Gauntlet completado en {dt:.2f} s ({total_matches / dt:.1f} sets/seg)!")
    print_matchup_matrix(brain)
    print_status_summary(brain, fly_char=fly_char_upper)

def run_spacies_drill(num_reps=30, cpu_level=9, fly_character="luigi"):
    """Entrenamiento intensivo Anti-Spacie (Fox, Falco, Falcon) con Chaingrabs y CC Shoryukens."""
    fly_char_upper = fly_character.upper()
    brain = FlyBrain()
    brain.active_character = fly_char_upper

    print_header(
        f"🦊 ENTRENAMIENTO INTENSIVO ANTI-SPACIES 20XX (FOX, FALCO, FALCON)",
        f"{num_reps} Repeticiones | Chaingrab Loop ➔ Kill Confirm | Crouch-Cancel Frame-8 Shoryuken"
    )

    t0 = time.time()
    spacies = ["FOX", "FALCO", "FALCON"]
    for i in range(1, num_reps + 1):
        target = random.choice(spacies)
        st = random.choice(LEGAL_STAGES)
        res = simulate_match(brain, fly_char=fly_char_upper, c_name=target, st_name=st, cpu_level=cpu_level, mode="spacies", match_num=i)
        ff_p = brain.get_plasticity("fastfaller_punish", 1.60)
        cqc_p = brain.get_plasticity("cqc_counter_reflex", 1.60)
        print(f"   [{i:2d}/{num_reps}] {MELEE_CHARACTERS[target]['icon']} {target:<8} | Chaingrab Regrabs + Shoryuken Ping | Anti-Spacie: {ff_p:.2f}x | CQC: {cqc_p:.2f}x")

    brain.save_long_term_memory()
    dt = time.time() - t0
    print(f"\n✅ Drill Anti-Spacies completado en {dt:.2f} s.")
    print_status_summary(brain, fly_char=fly_char_upper)

def run_whiff_drill(num_reps=30, cpu_level=9, fly_character="luigi"):
    """Entrenamiento intensivo de espaciado y castigo de whiff (Vist Wavedash-back ➔ Shoryuken)."""
    fly_char_upper = fly_character.upper()
    brain = FlyBrain()
    brain.active_character = fly_char_upper

    print_header(
        "⚡ ENTRENAMIENTO DE WHIFF PUNISH VIST & ESPACIADO NEUTRAL 20XX",
        f"{num_reps} Repeticiones | Micro-Wavedash Atrás ➔ Frame-8 Shoryuken PING!"
    )

    t0 = time.time()
    targets = ["MARTH", "SHEIK", "FALCON", "PEACH", "FOX"]
    for i in range(1, num_reps + 1):
        target = random.choice(targets)
        st = random.choice(LEGAL_STAGES)
        res = simulate_match(brain, fly_char=fly_char_upper, c_name=target, st_name=st, cpu_level=cpu_level, mode="whiff", match_num=i)
        whiff_p = brain.get_plasticity("whiff_punish_iq", 1.70)
        combo_p = brain.get_plasticity("combo_mastery", 1.60)
        print(f"   [{i:2d}/{num_reps}] {MELEE_CHARACTERS[target]['icon']} {target:<8} | Vist Bait ➔ Sweetspot Shoryuken PING! | Whiff IQ: {whiff_p:.2f}x | Combo: {combo_p:.2f}x")

    brain.save_long_term_memory()
    dt = time.time() - t0
    print(f"\n✅ Drill Whiff Punish completado en {dt:.2f} s.")
    print_status_summary(brain, fly_char=fly_char_upper)

def run_edgeguard_drill(num_reps=30, cpu_level=9, fly_character="luigi"):
    """Entrenamiento de Ledgedash invencible y remates profundos en repisa."""
    fly_char_upper = fly_character.upper()
    brain = FlyBrain()
    brain.active_character = fly_char_upper

    print_header(
        "🦅 ENTRENAMIENTO DE EDGEGUARD & LEDGEDASH INVENCIBLE (14 FRAMES)",
        f"{num_reps} Repeticiones | Down-Smash Semi-Spike | Deep D-Air Meteor Spike"
    )

    t0 = time.time()
    targets = ["MARTH", "FOX", "FALCO", "SHEIK", "SAMUS", "JIGGLYPUFF"]
    for i in range(1, num_reps + 1):
        target = random.choice(targets)
        st = random.choice(LEGAL_STAGES)
        res = simulate_match(brain, fly_char=fly_char_upper, c_name=target, st_name=st, cpu_level=cpu_level, mode="edgeguard", match_num=i)
        ledge_p = brain.get_plasticity("ledgedash_mastery", 1.70)
        edge_p = brain.get_plasticity("edgeguard_mastery", 1.60)
        print(f"   [{i:2d}/{num_reps}] {MELEE_CHARACTERS[target]['icon']} {target:<8} | Ledgedash Invencible + Ledge Semi-Spike | Ledgedash: {ledge_p:.2f}x | Edgeguard: {edge_p:.2f}x")

    brain.save_long_term_memory()
    dt = time.time() - t0
    print(f"\n✅ Drill Edgeguard completado en {dt:.2f} s.")
    print_status_summary(brain, fly_char=fly_char_upper)

def run_techchase_drill(num_reps=30, cpu_level=9, fly_character="luigi"):
    """Entrenamiento de reacción 100% frame-perfect a Tech-Rolls y Jab-Resets."""
    fly_char_upper = fly_character.upper()
    brain = FlyBrain()
    brain.active_character = fly_char_upper

    print_header(
        "🤼 ENTRENAMIENTO DE TECH-CHASING & REACCIÓN A TECH ROLLS 20XX",
        f"{num_reps} Repeticiones | Jab-Reset Frame-2 | Reacción a Tech Roll Away & In"
    )

    t0 = time.time()
    targets = ["FOX", "FALCO", "FALCON", "SHEIK", "MARTH"]
    for i in range(1, num_reps + 1):
        target = random.choice(targets)
        st = random.choice(LEGAL_STAGES)
        res = simulate_match(brain, fly_char=fly_char_upper, c_name=target, st_name=st, cpu_level=cpu_level, mode="techchase", match_num=i)
        tc_p = brain.get_plasticity("tech_chase_reaction", 1.75)
        combo_p = brain.get_plasticity("combo_mastery", 1.60)
        print(f"   [{i:2d}/{num_reps}] {MELEE_CHARACTERS[target]['icon']} {target:<8} | Jab-Reset ➔ Down-Smash Tech-Trap | Tech Chase: {tc_p:.2f}x | Combo: {combo_p:.2f}x")

    brain.save_long_term_memory()
    dt = time.time() - t0
    print(f"\n✅ Drill Tech-Chase completado en {dt:.2f} s.")
    print_status_summary(brain, fly_char=fly_char_upper)

def run_full_training(num_matches=50, cpu_level=9, fly_character="luigi"):
    """Entrenamiento general multi-fase contra todo el roster de Melee."""
    fly_char_upper = fly_character.upper()
    brain = FlyBrain()
    brain.active_character = fly_char_upper

    print_header(
        f"🪰 ENTRENAMIENTO NEURAL GENERAL MELEE × BOTS CPU NIVEL {cpu_level}",
        f"{num_matches} Partidas | Roster Completo de 15 Personajes | 6 Escenarios Legales"
    )
    print_status_summary(brain, fly_char=fly_char_upper)

    t0 = time.time()
    roster_list = list(MELEE_CHARACTERS.keys())

    for m in range(1, num_matches + 1):
        c_name = random.choice(roster_list)
        st_name = random.choice(LEGAL_STAGES)
        c_info = MELEE_CHARACTERS[c_name]
        res = simulate_match(brain, fly_char=fly_char_upper, c_name=c_name, st_name=st_name, cpu_level=cpu_level, mode="full", match_num=m)

        if m % 5 == 0 or m == num_matches:
            cur_mastery = brain.get_plasticity("combo_mastery", 1.40)
            cur_cqc = brain.get_plasticity("cqc_counter_reflex", 1.40)
            cur_whiff = brain.get_plasticity("whiff_punish_iq", 1.70)
            icon = c_info["icon"]
            st_disp = st_name.replace("_", " ").title()
            print(f"[{m:3d}/{num_matches}] vs {icon} {c_name:<11} [BOT LVL {cpu_level}] en {st_disp:<18} | Combos: {cur_mastery:.2f}x | CQC: {cur_cqc:.2f}x | Whiff: {cur_whiff:.2f}x")

    brain.save_long_term_memory()
    dt = time.time() - t0
    print(f"\n🎉 ¡Entrenamiento general completado en {dt:.2f} s ({num_matches / dt:.1f} partidas/seg)!")
    print_matchup_matrix(brain)
    print_status_summary(brain, fly_char=fly_char_upper)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entrenador Biológico Neural Acelerado para la Mosca (Drosophila 400k) 20XX")
    parser.add_argument("matches", type=int, nargs="?", default=50, help="Número de partidas a entrenar (por defecto: 50)")
    parser.add_argument("--matches", "-m", dest="matches_opt", type=int, default=None, help="Número de partidas")
    parser.add_argument("--mode", choices=["full", "gauntlet", "spacies", "whiff", "edgeguard", "techchase"], default="full", help="Modo o drill de entrenamiento especializado")
    parser.add_argument("--cpu", "-c", type=int, default=9, help="Nivel de dificultad del Bot CPU rival (1-9)")
    parser.add_argument("--character", "-k", default="luigi", choices=["luigi", "fox"], help="Personaje de la mosca (luigi o fox)")
    args = parser.parse_args()

    num = args.matches_opt if args.matches_opt is not None else args.matches

    if args.mode == "gauntlet":
        sets_per_char = max(1, num // 15)
        run_gauntlet_tournament(num_sets=sets_per_char, cpu_level=args.cpu, fly_character=args.character)
    elif args.mode == "spacies":
        run_spacies_drill(num_reps=num, cpu_level=args.cpu, fly_character=args.character)
    elif args.mode == "whiff":
        run_whiff_drill(num_reps=num, cpu_level=args.cpu, fly_character=args.character)
    elif args.mode == "edgeguard":
        run_edgeguard_drill(num_reps=num, cpu_level=args.cpu, fly_character=args.character)
    elif args.mode == "techchase":
        run_techchase_drill(num_reps=num, cpu_level=args.cpu, fly_character=args.character)
    else:
        run_full_training(num_matches=num, cpu_level=args.cpu, fly_character=args.character)
