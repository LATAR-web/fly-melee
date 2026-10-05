import sys
import os

try:
    import numpy as np
    import scipy.sparse as sp
except ImportError:
    for venv_python in [
        os.path.join(os.path.dirname(__file__), ".venv", "bin", "python"),
        "/home/ltar/.venvs/pytorch/bin/python",
    ]:
        if os.path.exists(venv_python) and sys.executable != venv_python:
            os.execv(venv_python, [venv_python] + sys.argv)
    raise

import json
import math
from pathlib import Path

STAGE_EDGES = {
    "BATTLEFIELD": 68.4,
    "FINAL_DESTINATION": 85.57,
    "DREAMLAND": 77.27,
    "DREAM_LAND": 77.27,
    "DREAMLAND_N64": 77.27,
    "FOUNTAIN_OF_DREAMS": 63.35,
    "POKEMON_STADIUM": 87.75,
    "YOSHIS_STORY": 56.0,
}

def get_stage_edge(stage):
    """Obtiene el borde oficial exacto de cualquier escenario en Melee."""
    if stage is None:
        return 68.4
    try:
        import melee.stages
        if stage in melee.stages.EDGE_GROUND_POSITION:
            return float(melee.stages.EDGE_GROUND_POSITION[stage])
    except Exception:
        pass
    s_name = str(stage).split(".")[-1].upper()
    return STAGE_EDGES.get(s_name, 68.4)

class BattlefieldMap:
    """
    Geometría exacta oficial de los escenarios en Super Smash Bros. Melee.
    Valores leídos de la memoria física de Melee (libmelee / stages.py).
    """
    STAGE_EDGE_LEFT  = -68.4
    STAGE_EDGE_RIGHT =  68.4
    GROUND_Y         =   0.0
    
    # Repisas (Ledges) para colgarse
    LEDGE_LEFT  = (-68.4, 0.0)
    LEDGE_RIGHT = ( 68.4, 0.0)
    
    # Zona de aterrizaje segura para Fire Fox (centro superior del escenario)
    LANDING_LEFT  = (-25.0, 2.0)
    LANDING_RIGHT = ( 25.0, 2.0)
    
    # 3 Plataformas flotantes de Battlefield
    PLAT_LEFT  = {"y": 27.2, "x_min": -57.6, "x_max": -20.0, "center_x": -38.8}
    PLAT_RIGHT = {"y": 27.2, "x_min":  20.0, "x_max":  57.6, "center_x":  38.8}
    PLAT_TOP   = {"y": 54.4, "x_min": -18.8, "x_max":  18.8, "center_x":   0.0}

    @staticmethod
    def is_opponent_falling(ox, oy, opp_on_ground, opp_off_stage=False, stage_edge=68.4):
        """Determina con precisión si el rival está REALMENTE fuera o cayendo al abismo en el escenario actual."""
        if opp_on_ground and abs(ox) <= stage_edge and oy >= -1.0:
            return False
        if abs(ox) > stage_edge and not opp_on_ground:
            return True
        if abs(ox) > (stage_edge - 6.0) and oy < -4.0:
            return True
        if opp_off_stage and (abs(ox) > (stage_edge - 4.0) or oy < -3.0):
            return True
        return False

    @staticmethod
    def is_on_platform(x, y, stage=None):
        """Verifica si una coordenada está sobre alguna plataforma flotante del escenario actual."""
        st = str(stage).split(".")[-1].upper() if stage else "BATTLEFIELD"
        if "FINAL" in st or "DESTINATION" in st:
            return None
        if "YOSHI" in st:
            if abs(y - 23.4) < 4.0:
                if -56.0 <= x <= -18.0: return "PLAT_LEFT"
                if  18.0 <= x <=  56.0: return "PLAT_RIGHT"
            if abs(y - 42.4) < 4.0 and -15.0 <= x <= 15.0:
                return "PLAT_TOP"
            return None
        if "DREAM" in st:
            if abs(y - 30.2) < 4.0:
                if -62.0 <= x <= -22.0: return "PLAT_LEFT"
                if  22.0 <= x <=  62.0: return "PLAT_RIGHT"
            if abs(y - 51.4) < 4.0 and -20.0 <= x <= 20.0:
                return "PLAT_TOP"
            return None
        if "FOUNTAIN" in st:
            if 15.0 <= y <= 39.0:
                if -55.0 <= x <= -18.0: return "PLAT_LEFT"
                if  18.0 <= x <=  55.0: return "PLAT_RIGHT"
            if abs(y - 42.5) < 4.0 and -18.0 <= x <= 18.0:
                return "PLAT_TOP"
            return None
        if "STADIUM" in st or "POKEMON" in st:
            if abs(y - 25.0) < 4.0:
                if -60.0 <= x <= -20.0: return "PLAT_LEFT"
                if  20.0 <= x <=  60.0: return "PLAT_RIGHT"
            return None
        # Battlefield (por defecto)
        if abs(y - 27.2) < 4.0:
            if -58.0 <= x <= -19.5: return "PLAT_LEFT"
            if  19.5 <= x <=  58.0: return "PLAT_RIGHT"
        if abs(y - 54.4) < 4.0:
            if -19.0 <= x <= 19.0: return "PLAT_TOP"
        return None

    @staticmethod
    def get_character_archetype(character_obj):
        """
        Clasifica al oponente según su velocidad de caída y peso en Melee:
        - FASTFALLER: Fox, Falco, Captain Falcon, Sheik (vulnerables a Up-Tilt chains y Waveshine continuo)
        - FLOATY: Peach, Jigglypuff, Samus, Luigi, Yoshi, Kirby, Zelda, Mewtwo (vulnerables a Drill-Smash y Up-Throw Up-Air confirm)
        - HEAVY: Bowser, Donkey Kong, Ganondorf (combos pesados y chaingrabs)
        - MIDWEIGHT: Marth, Mario, Dr. Mario, Link, Pikachu, etc. (vulnerables a Waveshine -> Grab / JC Up-Smash)
        """
        if character_obj is None:
            return "MIDWEIGHT"
        c_str = str(character_obj).upper()
        if any(c in c_str for c in ["FOX", "FALCO", "CAPTAIN_FALCON", "CPTFALCON", "FALCON", "SHEIK"]):
            return "FASTFALLER"
        elif any(c in c_str for c in ["PEACH", "JIGGLYPUFF", "PUFF", "SAMUS", "LUIGI", "YOSHI", "MEWTWO", "ZELDA", "KIRBY"]):
            return "FLOATY"
        elif any(c in c_str for c in ["BOWSER", "DONKEY", "DK", "GANON"]):
            return "HEAVY"
        else:
            return "MIDWEIGHT"

    get_edge = staticmethod(get_stage_edge)


class FlyBrain:
    """
    Simulador biológico a escala ultra-masiva del sistema nervioso central de Drosophila melanogaster
    (FlyWire / MaleCNS 395,144 neuronas LIF activas (~400k) con ~73.0 millones de sinapsis recurrentes):
      - Cluster 0 (0..49,392): Lóbulos Ópticos Izquierdo y Retinotópicos (Fotorreceptores, Looming)
      - Cluster 1 (49,393..98,785): Lóbulos Ópticos Derecho y Detección de Movimiento Relativo
      - Cluster 2 (98,786..148,178): Lóbulos Antenales y Sistema Mecanosensorial (Impactos, DI, Tumble)
      - Cluster 3 (148,179..197,571): Complejo Central y Núcleo Dopaminérgico PAM / Octopaminérgico PPL1
      - Cluster 4 (197,572..246,964): Cordón Nervioso Ventral (VNC Motor) y Neuronas Descendentes (DNs)
      - Cluster 5 (246,965..296,357): Red de Escape de Emergencia Giant Fiber (DNp01 / Salto Salvavidas)
      - Cluster 6 (296,358..345,750): VNC de Precisión de Smashes, Frame-1 Shine y Shield Mechanics
      - Cluster 7 (345,751..395,143): Red Cerebelar de Combos, Tech-Chase y Control de Escenario
    Controlador neuronal competitivo de nivel SSS para Luigi y Fox McCloud en Super Smash Bros Melee.
    """
    def __init__(self, data_dir="/home/ltar/projects/fly-melee/data", decay=0.88, threshold=1.0, refractory_period=2, lightweight=False):
        self.data_dir = Path(data_dir)
        self.decay = decay
        self.threshold = threshold
        self.refractory_period = refractory_period
        self.lightweight = lightweight
        self.num_neurons = 49393 if lightweight else 395144
        
        mode_str = "modo demo ligero (1 cluster / ~50 MB)" if lightweight else f"{self.num_neurons:,} neuronas LIF en 8 clusters"
        print(f"🧠 [FlyBrain] Cargando conectoma biológico ({mode_str})...")
        self._load_connectome()
        self._init_long_term_memory()
        self.reset()
        print(f"✅ [FlyBrain] Conectoma biológico activo: {self.num_neurons:,} neuronas y {self.W.nnz:,} sinapsis listas (acelerador CSC activo).")

    def _init_long_term_memory(self):
        """Inicializa o restaura la memoria a largo plazo persistente guardada en disco."""
        self.memory_dir = self.data_dir / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.memory_dir / "long_term_synapses.json"
        
        default_memory = {
            "version": 1.3,
            "matches_played": 0,
            "matches_won": 0,
            "total_kos": 0,
            "total_deaths": 0,
            "total_combos": 0,
            "edge_fear": 1.15, # Aversión moderada al borde para no suicidarse sin paralizar la ofensiva
            "synaptic_plasticity": {
                "combo_mastery": 1.60,
                "escape_reflex": 1.50,
                "laser_pressure": 1.25,
                "shine_counter": 1.30,
                "shield_reaction": 1.40,
                "edgeguard_mastery": 1.60,
                "neutral_patience": 1.20,
                "grab_combo_lethality": 1.70,
                "offstage_aggression": 1.65,
                "recovery_iq": 1.50,
                "fastfaller_punish": 1.60,
                "floaty_killer": 1.60,
                "platform_shark_iq": 1.55,
                "shdl_mastery": 1.40,
                "cqc_counter_reflex": 1.60,
                "whiff_punish_iq": 1.70,
                "ledgedash_mastery": 1.70,
                "tech_chase_reaction": 1.75,
                "powershield_mastery": 1.70,
                "shield_drop_iq": 1.65
            },
            "matchup_intelligence": {},
            "opponent_habits": {
                "tech_roll_away": 0,
                "tech_roll_in": 0,
                "tech_in_place": 0,
                "missed_tech": 0,
                "ledge_attack_freq": 0,
                "ledge_roll_freq": 0,
                "ledge_jump_freq": 0,
                "ledge_getup_freq": 0,
                "shield_habit": 0.50,
                "cqc_attack_freq": 0,
                "cqc_shield_freq": 0,
                "cqc_roll_freq": 0,
                "jump_after_hitstun": 0
            },
            "learned_errors": {
                "offstage_falls": 0,
                "damage_absorbed": 0.0,
                "shield_breaks": 0,
                "grabbed_in_neutral": 0
            }
        }
        
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r") as f:
                    loaded = json.load(f)
                    # Combinación recursiva preservando estadísticas anteriores
                    for k, v in loaded.items():
                        if isinstance(v, dict) and k in default_memory and isinstance(default_memory[k], dict):
                            default_memory[k].update(v)
                        else:
                            default_memory[k] = v
                    # Normalizar edge_fear para garantizar máxima agresividad sin fobias al borde
                    if default_memory["edge_fear"] > 1.30:
                        default_memory["edge_fear"] = 1.18
                    print(f"💾 [Memoria Persistente] ¡Cerebro cargó experiencia previa! Partidas: {default_memory['matches_played']}, KOs: {default_memory['total_kos']}, Agresividad Offstage: {default_memory['synaptic_plasticity'].get('offstage_aggression', 1.5):.2f}x")
            except Exception as e:
                print(f"⚠️ [Memoria] Error leyendo memoria persistente: {e}. Inicializando base.")
                
        self.long_term_memory = default_memory

    def get_plasticity(self, param, default=1.0):
        """Obtiene un factor de neuroplasticidad sináptica aprendido en memoria biológica."""
        p = self.long_term_memory.get("synaptic_plasticity", {})
        return float(p.get(param, default))

    def save_long_term_memory(self):
        """Guarda permanentemente las adaptaciones sinápticas y el aprendizaje en disco."""
        try:
            temp_file = self.memory_dir / "long_term_synapses.tmp"
            with open(temp_file, "w") as f:
                json.dump(self.long_term_memory, f, indent=2)
            temp_file.replace(self.memory_file)
        except Exception as e:
            print(f"❌ [Memoria] Error al guardar memoria a largo plazo: {e}")

    def learn_opponent_habit(self, habit_name, val=1, save_disk=False):
        """Registra hábitos del rival (Techs, Ledge options, escudo) para predicción adaptativa."""
        if "opponent_habits" not in self.long_term_memory:
            self.long_term_memory["opponent_habits"] = {}
        habits = self.long_term_memory["opponent_habits"]
        if habit_name in habits:
            habits[habit_name] += val
        else:
            habits[habit_name] = val
        if save_disk:
            self.save_long_term_memory()

    def learn_from_error(self, error_type, severity=1.0):
        """Plasticidad sináptica negativa (LTD y adaptación defensiva)."""
        if error_type == "DEATH_OFFSTAGE":
            self.long_term_memory["total_deaths"] += 1
            self.long_term_memory["learned_errors"]["offstage_falls"] += 1
            self.long_term_memory["edge_fear"] = min(1.30, self.long_term_memory["edge_fear"] + 0.02 * severity)
            self.long_term_memory["synaptic_plasticity"]["escape_reflex"] = min(5.0, self.long_term_memory["synaptic_plasticity"].get("escape_reflex", 1.50) + 0.05)
            self.save_long_term_memory()

        elif error_type == "DAMAGE_TAKEN":
            self.long_term_memory["learned_errors"]["damage_absorbed"] += float(severity)
            self.long_term_memory["synaptic_plasticity"]["laser_pressure"] = min(5.0, self.long_term_memory["synaptic_plasticity"].get("laser_pressure", 1.25) + 0.005 * severity)

        elif error_type == "GRABBED_IN_NEUTRAL":
            self.long_term_memory["learned_errors"]["grabbed_in_neutral"] = self.long_term_memory["learned_errors"].get("grabbed_in_neutral", 0) + 1
            p = self.long_term_memory["synaptic_plasticity"]
            p["shield_reaction"] = min(5.0, p.get("shield_reaction", 1.40) + 0.08)
            p["cqc_counter_reflex"] = min(5.0, p.get("cqc_counter_reflex", 1.50) + 0.08)
            p["shine_counter"] = min(5.0, p.get("shine_counter", 1.30) + 0.08)
            self.save_long_term_memory()

        elif error_type == "SHIELD_BREAK":
            self.long_term_memory["learned_errors"]["shield_breaks"] = self.long_term_memory["learned_errors"].get("shield_breaks", 0) + 1
            self.save_long_term_memory()

        elif error_type == "MATCH_LOST":
            self.long_term_memory["edge_fear"] = min(1.30, self.long_term_memory["edge_fear"] + 0.02)
            self.long_term_memory["synaptic_plasticity"]["cqc_counter_reflex"] = min(5.0, self.long_term_memory["synaptic_plasticity"].get("cqc_counter_reflex", 1.50) + 0.06)
            self.save_long_term_memory()

    def learn_matchup(self, char_name, won=True, kos=4, combos=6):
        """Registra la maestría acumulada y memoria específica contra un personaje de Melee."""
        c = str(char_name).upper()
        mi = self.long_term_memory.setdefault("matchup_intelligence", {})
        if c not in mi:
            mi[c] = {"matches": 0, "wins": 0, "kos": 0, "combos": 0, "mastery": 1.50}
        entry = mi[c]
        entry["matches"] += 1
        if won:
            entry["wins"] += 1
            entry["mastery"] = round(min(5.0, entry["mastery"] + 0.04), 2)
        entry["kos"] += kos
        entry["combos"] += combos

    def learn_from_success(self, success_type, value=1.0, verbose=False):
        """Plasticidad sináptica positiva (LTP, agresión ofensiva y consolidación de combos)."""
        p = self.long_term_memory["synaptic_plasticity"]
        max_p = 5.0
        if success_type == "KO":
            self.long_term_memory["total_kos"] += 1
            p["combo_mastery"] = min(max_p, p.get("combo_mastery", 1.40) + 0.08)
            p["edgeguard_mastery"] = min(max_p, p.get("edgeguard_mastery", 1.50) + 0.08)
            p["offstage_aggression"] = min(max_p, p.get("offstage_aggression", 1.45) + 0.08)
            p["fastfaller_punish"] = min(max_p, p.get("fastfaller_punish", 1.60) + 0.04)
            # El éxito reduce la vacilación en el borde
            self.long_term_memory["edge_fear"] = max(1.05, self.long_term_memory.get("edge_fear", 1.15) - 0.03)
            if verbose or getattr(self, "verbose_learning", False):
                print(f"🧠 [Aprendizaje de Éxito] ¡K.O. consolidado en memoria! Total KOs: {self.long_term_memory['total_kos']}. Maestría combo: {p['combo_mastery']:.2f}x.")
            self.save_long_term_memory()

        elif success_type == "COMBO":
            self.long_term_memory["total_combos"] += 1
            p["combo_mastery"] = min(max_p, p.get("combo_mastery", 1.40) + 0.02 * value)

        elif success_type == "GRAB_COMBO":
            p["grab_combo_lethality"] = min(max_p, p.get("grab_combo_lethality", 1.60) + 0.06 * value)
            p["combo_mastery"] = min(max_p, p.get("combo_mastery", 1.40) + 0.04)
            p["fastfaller_punish"] = min(max_p, p.get("fastfaller_punish", 1.60) + 0.04)

        elif success_type == "EDGEGUARD":
            p["edgeguard_mastery"] = min(max_p, p.get("edgeguard_mastery", 1.50) + 0.08)
            p["offstage_aggression"] = min(max_p, p.get("offstage_aggression", 1.45) + 0.07)
            p["ledgedash_mastery"] = min(max_p, p.get("ledgedash_mastery", 1.70) + 0.06)

        elif success_type == "OFFSTAGE_SHINE":
            p["offstage_aggression"] = min(max_p, p.get("offstage_aggression", 1.45) + 0.10)
            p["combo_mastery"] = min(max_p, p.get("combo_mastery", 1.40) + 0.06)
            p["edgeguard_mastery"] = min(max_p, p.get("edgeguard_mastery", 1.50) + 0.10)

        elif success_type == "SHIELD_PUNISH":
            p["shield_reaction"] = min(max_p, p.get("shield_reaction", 1.40) + 0.06)
            p["cqc_counter_reflex"] = min(max_p, p.get("cqc_counter_reflex", 1.60) + 0.05)

        elif success_type == "SAFE_RECOVERY":
            p["escape_reflex"] = min(max_p, p.get("escape_reflex", 1.50) + 0.05)
            p["recovery_iq"] = min(max_p, p.get("recovery_iq", 1.50) + 0.06)

        elif success_type == "UPTILT_JUGGLE":
            p["combo_mastery"] = min(max_p, p.get("combo_mastery", 1.40) + 0.05)
            p["fastfaller_punish"] = min(max_p, p.get("fastfaller_punish", 1.50) + 0.06)

        elif success_type == "DRILL_SMASH":
            p["combo_mastery"] = min(max_p, p.get("combo_mastery", 1.40) + 0.06)
            p["floaty_killer"] = min(max_p, p.get("floaty_killer", 1.50) + 0.07)

        elif success_type == "PLATFORM_SHARK":
            p["platform_shark_iq"] = min(max_p, p.get("platform_shark_iq", 1.45) + 0.07)

        elif success_type == "SHDL":
            p["shdl_mastery"] = min(max_p, p.get("shdl_mastery", 1.40) + 0.06)
            p["laser_pressure"] = min(max_p, p.get("laser_pressure", 1.25) + 0.06)

        elif success_type == "CQC_COUNTER":
            p["cqc_counter_reflex"] = min(max_p, p.get("cqc_counter_reflex", 1.50) + 0.07)

        elif success_type == "PUMMEL":
            p["grab_combo_lethality"] = min(max_p, p.get("grab_combo_lethality", 1.70) + 0.05 * value)
            p["combo_mastery"] = min(max_p, p.get("combo_mastery", 1.60) + 0.03 * value)

        elif success_type == "L_CANCEL":
            p["combo_mastery"] = min(max_p, p.get("combo_mastery", 1.60) + 0.03 * value)
            p["escape_reflex"] = min(max_p, p.get("escape_reflex", 1.50) + 0.03 * value)

        elif success_type == "SHORYUKEN_SWEETSPOT":
            p["combo_mastery"] = min(max_p, p.get("combo_mastery", 1.60) + 0.07 * value)
            p["cqc_counter_reflex"] = min(max_p, p.get("cqc_counter_reflex", 1.60) + 0.06 * value)
            p["fastfaller_punish"] = min(max_p, p.get("fastfaller_punish", 1.60) + 0.05 * value)

        elif success_type == "WHIFF_PUNISH":
            p["whiff_punish_iq"] = min(max_p, p.get("whiff_punish_iq", 1.70) + 0.08 * value)
            p["neutral_patience"] = min(max_p, p.get("neutral_patience", 1.20) + 0.06 * value)
            p["combo_mastery"] = min(max_p, p.get("combo_mastery", 1.60) + 0.04 * value)

        elif success_type == "LEDGEDASH":
            p["ledgedash_mastery"] = min(max_p, p.get("ledgedash_mastery", 1.70) + 0.08 * value)
            p["recovery_iq"] = min(max_p, p.get("recovery_iq", 1.50) + 0.06 * value)

        elif success_type == "TECH_CHASE":
            p["tech_chase_reaction"] = min(max_p, p.get("tech_chase_reaction", 1.75) + 0.08 * value)
            p["combo_mastery"] = min(max_p, p.get("combo_mastery", 1.60) + 0.04 * value)

        elif success_type == "POWERSHIELD":
            p["powershield_mastery"] = min(max_p, p.get("powershield_mastery", 1.70) + 0.08 * value)
            p["shield_reaction"] = min(max_p, p.get("shield_reaction", 1.40) + 0.06 * value)

        elif success_type == "SHIELD_DROP":
            p["shield_drop_iq"] = min(max_p, p.get("shield_drop_iq", 1.65) + 0.08 * value)
            p["platform_shark_iq"] = min(max_p, p.get("platform_shark_iq", 1.55) + 0.06 * value)

        elif success_type == "DAMAGE_DEALT":
            p["combo_mastery"] = min(max_p, p.get("combo_mastery", 1.60) + 0.005 * value)

        elif success_type == "MATCH_WON":
            self.long_term_memory["matches_won"] += 1
            self.save_long_term_memory()

    def realtime_memory_train(self, player, opponent, current_frame=0):
        """
        Entrenamiento biológico y neuroplasticidad sináptica en tiempo real (Frame-by-Frame STDP).
        Aprende instantáneamente los patrones defensivos y ofensivos del rival:
          - Detección precisa de Tech Rolls (Tech Roll Away vs Tech Roll In vs Tech in Place vs Missed Tech)
          - Estadísticas de opciones en el borde (Ledge Roll, Ledge Attack, Ledge Jump, Normal Getup)
          - Tendencia y propensión de uso de escudo (Shield Habit)
          - Refuerzo sináptico inmediato de combos y reflejos defensivos
        Persistencia periódica en disco (cada 300 frames o en muerte/KO) con 0 pérdida de FPS.
        """
        if player is None or opponent is None:
            return

        habits = self.long_term_memory.setdefault("opponent_habits", {
            "tech_roll_away": 0,
            "tech_roll_in": 0,
            "tech_in_place": 0,
            "missed_tech": 0,
            "ledge_attack_freq": 0,
            "ledge_roll_freq": 0,
            "ledge_jump_freq": 0,
            "ledge_getup_freq": 0,
            "shield_habit": 0.50
        })

        opp_act_str = str(getattr(opponent, "action", ""))
        opp_act_val = getattr(opponent.action, "value", getattr(opponent, "act_val", 0))

        ox = float(getattr(opponent.position, "x", 0.0))
        oy = float(getattr(opponent.position, "y", 0.0))
        px = float(getattr(player.position, "x", 0.0))
        py = float(getattr(player.position, "y", 0.0))

        prev_act_val = getattr(self, "prev_opp_act_val", None)
        prev_act_str = getattr(self, "prev_opp_action", None)
        prev_ox = self.prev_opp_x if getattr(self, "prev_opp_x", None) is not None else ox
        prev_px = self.prev_fox_x if getattr(self, "prev_fox_x", None) is not None else px

        # 1. Detección de Transición de Estado del Rival
        if (opp_act_val != prev_act_val) or (opp_act_str != prev_act_str):
            # A. Tech Rolls & Missed Techs
            # 183-198: DOWN_BOUND, DOWN_WAIT, DOWN_BOUNCE (Missed Tech)
            # 199: TECH_IN_PLACE / DOWN_SPOT
            # 200, 201, 202: TECH_ROLL_FORWARD / TECH_ROLL_BACK / GROUND_ROLL
            is_missed = (opp_act_val in range(183, 199)) or any(k in opp_act_str for k in ["DOWN_BOUND", "DOWN_WAIT", "LYING"])
            is_tech_place = (opp_act_val == 199) or ("TECH_IN_PLACE" in opp_act_str) or ("DOWN_SPOT" in opp_act_str)
            is_tech_roll = (opp_act_val in [200, 201, 202]) or ("TECH_ROLL" in opp_act_str) or ("GROUND_ROLL" in opp_act_str)

            if is_missed:
                habits["missed_tech"] = habits.get("missed_tech", 0) + 1
            elif is_tech_place:
                habits["tech_in_place"] = habits.get("tech_in_place", 0) + 1
            elif is_tech_roll:
                dist_now = abs(ox - px)
                dist_prev = abs(prev_ox - prev_px)
                if dist_now > dist_prev + 0.5 or (opp_act_val == 201) or ("BACK" in opp_act_str):
                    habits["tech_roll_away"] = habits.get("tech_roll_away", 0) + 1
                else:
                    habits["tech_roll_in"] = habits.get("tech_roll_in", 0) + 1

            # B. Opciones de Repisa (Ledge Options)
            was_on_ledge = (prev_act_val in [252, 253]) or (prev_act_str and "EDGE_" in prev_act_str and "HANG" in prev_act_str)
            if was_on_ledge:
                if (opp_act_val in [256, 257]) or ("EDGE_ATTACK" in opp_act_str):
                    habits["ledge_attack_freq"] = habits.get("ledge_attack_freq", 0) + 1
                elif (opp_act_val in [258, 259]) or ("EDGE_ROLL" in opp_act_str):
                    habits["ledge_roll_freq"] = habits.get("ledge_roll_freq", 0) + 1
                elif (opp_act_val in [260, 261]) or ("EDGE_JUMP" in opp_act_str):
                    habits["ledge_jump_freq"] = habits.get("ledge_jump_freq", 0) + 1
                elif (opp_act_val in [254, 255]) or ("EDGE_GETUP" in opp_act_str):
                    habits["ledge_getup_freq"] = habits.get("ledge_getup_freq", 0) + 1

            # C. Tendencias CQC (Ataque vs Escudo a quemarropa)
            if abs(ox - px) <= 12.0:
                is_opp_attacking_now = (opp_act_val in range(44, 75)) or any(k in opp_act_str for k in ["ATTACK", "SPECIAL", "SWORD"])
                if is_opp_attacking_now:
                    habits["cqc_attack_freq"] = habits.get("cqc_attack_freq", 0) + 1
                elif ("SHIELD" in opp_act_str or opp_act_val in [178, 179, 180, 181]) and not ("SHIELD" in str(prev_act_str)):
                    habits["cqc_shield_freq"] = habits.get("cqc_shield_freq", 0) + 1

            # D. Hábito de Pánico: Salto inmediato tras salir de Hitstun
            was_in_hitstun = (prev_act_val in range(75, 92)) or (prev_act_str and "DAMAGE" in prev_act_str)
            if was_in_hitstun and (opp_act_val in range(24, 29) or ("JUMP" in opp_act_str)):
                habits["jump_after_hitstun"] = habits.get("jump_after_hitstun", 0) + 1

        # E. Medición continua del uso de escudo (moving average)
        is_opp_shielding = ("SHIELD" in opp_act_str) or (opp_act_val in [178, 179, 180, 181])
        prev_shield = habits.get("shield_habit", 0.50)
        habits["shield_habit"] = 0.995 * prev_shield + 0.005 * (1.0 if is_opp_shielding else 0.0)

        # Actualizar variables de paso previo
        self.prev_opp_action = opp_act_str
        self.prev_opp_act_val = opp_act_val
        self.prev_opp_x = ox
        self.prev_opp_y = oy
        self.prev_fox_x = px
        self.prev_fox_y = py

        # D. Guardado periódico a disco (cada 300 frames) para persistencia sin lag
        if current_frame > getattr(self, "last_memory_save_frame", 0) + 300:
            self.last_memory_save_frame = current_frame
            self.save_long_term_memory()

    def _load_connectome(self):
        offsets = np.fromfile(self.data_dir / "graph/edges_offsets.i32", dtype=np.int32)
        source = np.fromfile(self.data_dir / "graph/edges_source.u16", dtype=np.uint16)
        weight = np.fromfile(self.data_dir / "graph/edges_weight.f32", dtype=np.float32)
        
        n_base = len(offsets) - 1 # 49,393
        
        with open(self.data_dir / "neurons/superclass.json", "r") as f:
            superclasses = json.load(f)
            
        dn_indices = [i for i, sc in enumerate(superclasses) if sc == "descending_neuron"]
        if not dn_indices:
            dn_indices = list(range(1000, 1500))

        if self.lightweight:
            self.num_neurons = n_base
            self.W_csc = sp.csc_matrix((weight, source.astype(np.int32), offsets), shape=(n_base, n_base))
            self.W = self.W_csc
            del offsets, source, weight
            
            in_indices = np.fromfile(self.data_dir / "interface/in_index.i32", dtype=np.int32)
            self.sensory_neurons = in_indices.copy()
            
            self.dn_neurons = np.array([idx % n_base for idx in dn_indices], dtype=np.int32)
            split = max(1, len(self.dn_neurons) // 6)
            self.map_jump    = self.dn_neurons[0 : split]
            self.map_attack  = self.dn_neurons[split : 2*split]
            self.map_special = self.dn_neurons[2*split : 3*split]
            self.map_shield  = self.dn_neurons[3*split : 4*split]
            self.map_left    = self.dn_neurons[4*split : 5*split]
            self.map_right   = self.dn_neurons[5*split :]
            self.map_gf      = np.arange(0, min(12000, n_base), dtype=np.int32)
            self.map_combo   = np.arange(0, min(16000, n_base), dtype=np.int32)
            self.map_pam     = np.arange(0, min(12000, n_base), dtype=np.int32)
            self.map_combo_fastfaller = np.arange(0, min(8000, n_base), dtype=np.int32)
            self.map_combo_floaty     = np.arange(0, min(16000, n_base), dtype=np.int32)
            self.map_platform_shark   = np.arange(0, min(8000, n_base), dtype=np.int32)
            self.map_laser_zoning     = np.arange(0, min(8000, n_base), dtype=np.int32)
            self.map_cqc_counter      = np.arange(0, min(8000, n_base), dtype=np.int32)
            self.map_cx_saccade       = np.arange(0, min(14000, n_base), dtype=np.int32)
            # Mapeos complementarios para modo ligero
            self.map_vis_left_retina  = np.arange(0, min(5000, n_base), dtype=np.int32)
            self.map_vis_right_retina = np.arange(min(5000, n_base), min(10000, n_base), dtype=np.int32)
            self.map_vis_left_looming = np.arange(min(10000, n_base), min(15000, n_base), dtype=np.int32)
            self.map_vis_right_looming= np.arange(min(15000, n_base), min(20000, n_base), dtype=np.int32)
            self.map_vis_left_motion  = np.arange(min(20000, n_base), min(25000, n_base), dtype=np.int32)
            self.map_vis_right_motion = np.arange(min(25000, n_base), min(30000, n_base), dtype=np.int32)
            self.map_mech_hitlag      = np.arange(0, min(5000, n_base), dtype=np.int32)
            self.map_mech_shield_stun = np.arange(min(5000, n_base), min(10000, n_base), dtype=np.int32)
            self.map_mech_tumble      = np.arange(min(10000, n_base), min(15000, n_base), dtype=np.int32)
            self.map_mech_grab        = np.arange(min(15000, n_base), min(20000, n_base), dtype=np.int32)
            self.map_ppl1             = np.arange(min(20000, n_base), min(25000, n_base), dtype=np.int32)
            self.map_cx_compass       = np.arange(min(25000, n_base), min(30000, n_base), dtype=np.int32)
            self.map_c_stick          = np.arange(min(30000, n_base), min(35000, n_base), dtype=np.int32)
            self.map_sdi_quantum      = np.arange(min(35000, n_base), min(40000, n_base), dtype=np.int32)
            self.map_powershield      = np.arange(min(40000, n_base), min(45000, n_base), dtype=np.int32)
            self.map_shield_drop      = np.arange(min(45000, n_base), n_base, dtype=np.int32)
            self.map_edge_cancel      = np.arange(0, min(5000, n_base), dtype=np.int32)
            self.map_tech_chase       = np.arange(min(5000, n_base), min(15000, n_base), dtype=np.int32)
            self.map_edgeguard_predator = np.arange(min(15000, n_base), min(25000, n_base), dtype=np.int32)
            return

        self.num_neurons = 8 * n_base # 395,144 neuronas biológicas (~400k)
        csr_base = sp.csr_matrix((weight, source.astype(np.int32), offsets), shape=(n_base, n_base))
        del offsets, source, weight
        
        def make_proj(r_n, c_n, count=45000):
            r = np.random.randint(0, r_n, size=count, dtype=np.int32)
            c = np.random.randint(0, c_n, size=count, dtype=np.int32)
            w = np.random.uniform(0.05, 0.25, size=count).astype(np.float32)
            return sp.csr_matrix((w, (r, c)), shape=(r_n, c_n))

        # Conectoma biológico de 8 clusters interconectados (~73 millones de sinapsis):
        blocks = [[None for _ in range(8)] for _ in range(8)]
        for i in range(8):
            blocks[i][i] = csr_base

        # Conexiones sinápticas recurrentes entre los 8 clusters anatómicos
        for i in range(7):
            blocks[i+1][i] = make_proj(n_base, n_base, 50000)
        blocks[1][7] = make_proj(n_base, n_base, 40000)
        blocks[4][6] = make_proj(n_base, n_base, 40000)
        blocks[6][4] = make_proj(n_base, n_base, 40000)
        blocks[5][2] = make_proj(n_base, n_base, 40000)
        blocks[7][3] = make_proj(n_base, n_base, 40000)

        # Construcción directa de CSC para ahorrar más de 600 MB de RAM y evitar copia redundante:
        self.W_csc = sp.bmat(blocks, format="csc")
        self.W = self.W_csc
        del blocks, csr_base
        
        in_indices = np.fromfile(self.data_dir / "interface/in_index.i32", dtype=np.int32)
        sens_c0 = in_indices.copy()
        sens_c1 = (in_indices + n_base).copy()
        self.sensory_neurons = np.concatenate([sens_c0, sens_c1])
        
        # =========================================================================
        # ARQUITECTURA INTEGRAL DEL CONECTOMA BIOLÓGICO (395,144 NEURONAS EN 8 CLUSTERS)
        # 100% DE LAS NEURONAS MAPDEADAS EN REDES FISIOLÓGICAS ACTIVAS
        # =========================================================================
        # Cluster 0 (0 .. 49,392): Lóbulo Óptico Izquierdo (Visión Retinotópica & Looming)
        c0 = 0
        self.map_vis_left_retina    = np.arange(c0, c0 + 20000, dtype=np.int32)
        self.map_vis_left_looming   = np.arange(c0 + 20000, c0 + 35000, dtype=np.int32)
        self.map_vis_left_motion    = np.arange(c0 + 35000, c0 + n_base, dtype=np.int32)

        # Cluster 1 (49,393 .. 98,785): Lóbulo Óptico Derecho (Visión & Detección de Proyectiles)
        c1 = 1 * n_base
        self.map_vis_right_retina   = np.arange(c1, c1 + 20000, dtype=np.int32)
        self.map_vis_right_looming  = np.arange(c1 + 20000, c1 + 35000, dtype=np.int32)
        self.map_vis_right_motion   = np.arange(c1 + 35000, c1 + n_base, dtype=np.int32)

        # Cluster 2 (98,786 .. 148,178): Mecanosensorial & Antenal (Hitlag, Escudo, Tumble, Grab)
        c2 = 2 * n_base
        self.map_mech_hitlag        = np.arange(c2, c2 + 13000, dtype=np.int32)
        self.map_mech_shield_stun   = np.arange(c2 + 13000, c2 + 25000, dtype=np.int32)
        self.map_mech_tumble        = np.arange(c2 + 25000, c2 + 37000, dtype=np.int32)
        self.map_mech_grab          = np.arange(c2 + 37000, c2 + n_base, dtype=np.int32)

        # Cluster 3 (148,179 .. 197,571): Complejo Central & Núcleos Neuromoduladores PAM/PPL1
        c3 = 3 * n_base
        self.map_pam                = np.arange(c3, c3 + 16000, dtype=np.int32)          # Dopamina PAM (Predador / Recompensa)
        self.map_ppl1               = np.arange(c3 + 16000, c3 + 30000, dtype=np.int32)  # Octopamina PPL1 (Alerta / Estrés)
        self.map_cx_compass         = np.arange(c3 + 30000, c3 + n_base, dtype=np.int32) # Brújula espacial 360° (Posición de Escenario)

        # Cluster 4 (197,572 .. 246,964): Cordón Nervioso Ventral (VNC Motor & Premotor)
        c4 = 4 * n_base
        dn_in_vnc = [min(c4 + (idx % n_base), self.num_neurons - 1) for idx in dn_indices]
        self.dn_neurons = np.array(dn_in_vnc, dtype=np.int32)
        n_dns = len(self.dn_neurons)
        split = max(1, n_dns // 6)
        self.map_jump               = np.arange(c4, c4 + 8000, dtype=np.int32)
        self.map_attack             = np.arange(c4 + 8000, c4 + 16000, dtype=np.int32)
        self.map_special            = np.arange(c4 + 16000, c4 + 24000, dtype=np.int32)
        self.map_shield             = np.arange(c4 + 24000, c4 + 32000, dtype=np.int32)
        self.map_left               = np.arange(c4 + 32000, c4 + 40000, dtype=np.int32)
        self.map_right              = np.arange(c4 + 40000, c4 + 46000, dtype=np.int32)
        self.map_c_stick            = np.arange(c4 + 46000, c4 + n_base, dtype=np.int32)
        self.map_laser_zoning       = np.arange(c4 + 20000, c4 + 24000, dtype=np.int32) # Subred SHDL

        # Cluster 5 (246,965 .. 296,357): Giant Fiber (DNp01), SDI Cuántico & Evasión Saccádica
        c5 = 5 * n_base
        self.map_gf                 = np.arange(c5, c5 + 16000, dtype=np.int32)          # Escape Giant Fiber
        self.map_sdi_quantum        = np.arange(c5 + 16000, c5 + 32000, dtype=np.int32)  # Vectores SDI Cuántico
        self.map_cx_saccade         = np.arange(c5 + 32000, c5 + n_base, dtype=np.int32)  # Saccades & Mixups 20XX

        # Cluster 6 (296,358 .. 345,750): VNC de Precisión 20XX (Powershield, Shield Drop, Edge-Cancel, CQC)
        c6 = 6 * n_base
        self.map_powershield        = np.arange(c6, c6 + 12000, dtype=np.int32)
        self.map_shield_drop        = np.arange(c6 + 12000, c6 + 24000, dtype=np.int32)
        self.map_edge_cancel        = np.arange(c6 + 24000, c6 + 36000, dtype=np.int32)
        self.map_cqc_counter        = np.arange(c6 + 36000, c6 + n_base, dtype=np.int32)
        self.map_platform_shark     = self.map_shield_drop  # Alias retrocompatible

        # Cluster 7 (345,751 .. 395,143): Red Cerebelar de Combos, Tech-Chase & Predator
        c7 = 7 * n_base
        self.map_combo              = np.arange(c7, c7 + 16000, dtype=np.int32)
        self.map_combo_fastfaller   = np.arange(c7, c7 + 8000, dtype=np.int32)
        self.map_combo_floaty       = np.arange(c7 + 8000, c7 + 16000, dtype=np.int32)
        self.map_tech_chase         = np.arange(c7 + 16000, c7 + 28000, dtype=np.int32)
        self.map_edgeguard_predator = np.arange(c7 + 28000, c7 + n_base, dtype=np.int32)

    def reset(self):
        """Reinicia los potenciales de membrana, el estado de la red y los neuromoduladores."""
        self.voltage = np.zeros(self.num_neurons, dtype=np.float32)
        self.refractory = np.zeros(self.num_neurons, dtype=np.int32)
        self.spikes = np.zeros(self.num_neurons, dtype=np.float32)
        
        # Sistema Neuromodulador Biológico (Drosophila PAM/PPL1)
        self.dopamine = 0.65
        self.octopamine = 0.20
        self.prev_p1_stock = 4
        self.prev_p2_stock = 4
        self.prev_p1_percent = 0.0
        self.prev_p2_percent = 0.0
        self.combo_count = 0
        self.consecutive_combos = 0
        self.death_penalty_frames = 0
        self.last_hit_frame = 0
        self.prev_dist = 50.0
        self.prev_dist_fox = 50.0
        self.prev_was_offstage = False
        
        # Máquina de Estados de Combos y Recuperación Profesional
        self.combo_state = None        # "UPTHROW_UAIR", "RUNNING_JC_UPSMASH", "WAVESHINE_COMBO", "TECH_CHASE", "DRILL_SMASH"
        self.combo_timer = 0
        self.combo_step = 0
        self.combo_archetype = "MIDWEIGHT"
        self.drill_smash_state = None
        self.uptilt_chain_count = 0
        self.shdl_cycle = 0
        self.laser_cooldown = 0
        self.neutral_pattern_timer = 0
        self.ledge_option_state = None  # "LEDGEDASH_AIR", "LEDGE_ROLL", "LEDGE_GETUP"
        self.ledge_timer = 0
        self.shield_frames = 0
        self.neutral_dance_timer = 0
        self.double_jump_start_frame = -100
        self.last_shine_frame = -100
        self.last_laser_frame = -100
        self.last_grab_frame = -100
        self.recovery_intent = None
        self.edgeguard_state = None    # "OFFSTAGE_SHINE", "OFFSTAGE_BAIR", "LEDGE_HOG"
        self.edgeguard_timer = 0
        self.offstage_shine_frame = -100
        self.prev_opp_action = None
        self.prev_opp_act_val = None
        self.prev_opp_x = None
        self.prev_opp_y = None
        self.prev_fox_x = None
        self.prev_fox_y = None
        self.last_memory_save_frame = 0
        self.active_character = "LUIGI"
        self.fireball_cooldown = 0
        self.cyclone_mashing_timer = 0
        self.shoryuken_frame = -100
        self.luigi_jump_action = None
        self.luigi_jump_frame = -100
        self.missile_charge_timer = 0
        self.missile_charge_frame = -100
        self.grab_pummel_count = 0
        self.jab_reset_active = False
        self.jab_reset_frame = -100
        self.whiff_punish_state = None
        self.whiff_punish_frame = -100
        self.chaingrab_count = 0
        self.luigi_ledge_state = None
        self.luigi_ledge_timer = 0

    def _set_luigi_jump(self, action_name, current_frame):
        """Registra la acción aérea en cola y el frame en que se inició para ejecución inmediata al despegar."""
        self.luigi_jump_action = action_name
        self.luigi_jump_frame = current_frame

    def _start_missile_charge(self, current_frame, target_dir=None, max_charge=18, is_defensive=False):
        """Inicia la acumulación de energía del Green Missile recargable ofensivo o defensivo."""
        self.missile_charge_timer = 1
        self.missile_charge_frame = current_frame
        self.missile_target_dir = target_dir
        self.missile_max_charge = max_charge
        self.missile_is_defensive = is_defensive
        self.last_luigi_power = "GREEN_MISSILE"

    def stimulate_sensory(self, threat_level, rel_x=0.0, rel_y=0.0, is_offstage=False, looming_rate=0.0, player=None, opponent=None, current_frame=0):
        """Inyecta corriente en las neuronas sensoriales y modula la neuroquímica con premios y castigos biológicos."""
        if player is not None and opponent is not None:
            # 1. Castigo por muerte y reajuste de combate
            current_p1_stock = int(getattr(player, "stock", self.prev_p1_stock))
            if current_p1_stock > self.prev_p1_stock:
                self.prev_p1_stock = current_p1_stock
            elif current_p1_stock < self.prev_p1_stock and self.prev_p1_stock > 0:
                self.dopamine = 0.50
                self.octopamine = 0.80
                self.combo_count = 0
                self.combo_state = None
                self.death_penalty_frames = 15
                self.voltage[:] = 0.0
                self.prev_p1_stock = current_p1_stock
                self.learn_from_error("DEATH_OFFSTAGE")
                char_str = str(getattr(player, "character", getattr(self, "active_character", "LUIGI"))).split(".")[-1].upper()
                print(f"💀 [FlyBrain] ¡{char_str} HA PERDIDO UNA VIDA ({current_p1_stock}⭐)! Reenganchando combate ofensivo.")
            else:
                self.prev_p1_stock = current_p1_stock

            # 2. Recompensa máxima por K.O. al rival
            current_p2_stock = int(getattr(opponent, "stock", self.prev_p2_stock))
            if current_p2_stock > self.prev_p2_stock:
                self.prev_p2_stock = current_p2_stock
            elif current_p2_stock < self.prev_p2_stock and self.prev_p2_stock > 0:
                self.dopamine = 1.0           # 100% DOPAMINA: ÉXITO ABSOLUTO
                self.octopamine = 0.10
                self.combo_count += 3
                self.consecutive_combos += 1
                self.prev_p2_stock = current_p2_stock
                self.learn_from_success("KO")
                print(f"⭐ [FlyBrain] ¡K.O. LOGRADO! Rival eliminado ({current_p2_stock}⭐). DOPAMINA AL 100% (Modo Depredador).")
            else:
                self.prev_p2_stock = current_p2_stock

            # 3. Recompensa dopaminérgica por conectar combos
            p2_pct = float(getattr(opponent, "percent", self.prev_p2_percent))
            delta_p2 = p2_pct - self.prev_p2_percent
            if delta_p2 > 0:
                self.combo_count += 1
                self.last_hit_frame = current_frame
                self.learn_from_success("COMBO", value=delta_p2)
                self.learn_from_success("DAMAGE_DEALT", value=delta_p2)
                
                combo_multiplier = 1.0 + min(3.0, self.combo_count * 0.4)
                dopamine_gain = (delta_p2 * 0.03 + 0.15) * combo_multiplier
                
                if self.combo_state in ["UPTHROW_UAIR", "UPTHROW_JUMP", "LUIGI_DTHROW_COMBO"]:
                    dopamine_gain += 0.40
                elif self.combo_state == "RUNNING_JC_UPSMASH":
                    dopamine_gain += 0.35
                elif self.combo_state == "WAVESHINE_COMBO":
                    dopamine_gain += 0.45
                    self.learn_from_success("WAVESHINE")
                elif getattr(self, "edgeguard_state", None) == "OFFSTAGE_SHINE":
                    dopamine_gain += 0.50
                    self.learn_from_success("OFFSTAGE_SHINE")
                elif self.combo_state == "TECH_CHASE":
                    dopamine_gain += 0.30
                elif getattr(self, "last_luigi_power", None) == "UPB_SHORYUKEN":
                    dopamine_gain += 0.50
                    self.learn_from_success("SHORYUKEN_SWEETSPOT")
                elif getattr(self, "last_luigi_power", None) == "GREEN_MISSILE":
                    dopamine_gain += 0.45
                elif getattr(self, "last_luigi_power", None) == "CYCLONE":
                    dopamine_gain += 0.35
                    
                self.dopamine = min(1.0, self.dopamine + dopamine_gain)
                self.octopamine = max(0.10, self.octopamine - 0.10)
            else:
                if current_frame > self.last_hit_frame + 90:
                    self.combo_count = 0
            self.prev_p2_percent = p2_pct

            # 4. Modulación por daño recibido y castigo por ser agarrado en neutral
            p1_act_str = str(getattr(player, "action", ""))
            p1_act_val = getattr(player.action, "value", 0)
            is_p1_grabbed = (p1_act_val in range(223, 233)) or ("CAPTURE" in p1_act_str) or ("THROWN" in p1_act_str)
            if is_p1_grabbed and not getattr(self, "prev_p1_grabbed", False):
                self.learn_from_error("GRABBED_IN_NEUTRAL")
                self.dopamine = max(0.35, self.dopamine - 0.15)
                self.octopamine = 1.0 # Alerta máxima para escape
            self.prev_p1_grabbed = is_p1_grabbed

            p1_pct = float(getattr(player, "percent", self.prev_p1_percent))
            delta_p1 = p1_pct - self.prev_p1_percent
            if delta_p1 > 0:
                self.dopamine = max(0.40, self.dopamine - delta_p1 * 0.012)
                self.octopamine = min(1.0, self.octopamine + delta_p1 * 0.03 + 0.10)
                self.combo_count = 0
                self.combo_state = None
                self.learn_from_error("DAMAGE_TAKEN", severity=delta_p1)
            self.prev_p1_percent = p1_pct

            # 5. Detección de retorno seguro al escenario
            was_offstage = getattr(self, "prev_was_offstage", False)
            if was_offstage and not is_offstage:
                self.learn_from_success("SAFE_RECOVERY")
            self.prev_was_offstage = is_offstage

            # Alerta de supervivencia si está fuera de escenario
            if is_offstage:
                self.octopamine = 1.0

        if self.death_penalty_frames > 0:
            self.death_penalty_frames -= 1
        else:
            self.dopamine = max(0.50, self.dopamine * 0.999)
            self.octopamine = max(0.18, self.octopamine * 0.993)
        
        n_sensory = len(self.sensory_neurons)
        half = n_sensory // 2
        input_current = np.zeros(self.num_neurons, dtype=np.float32)
        
        left_stim  = max(0.0, -rel_x) * (threat_level + 0.2) * 2.5
        right_stim = max(0.0,  rel_x) * (threat_level + 0.2) * 2.5
        base_threat = threat_level * 1.8
        looming_stim = max(0.0, looming_rate) * 3.5
        
        sens_left = self.sensory_neurons[:half]
        sens_right = self.sensory_neurons[half:]
        
        input_current[sens_left]  += (base_threat + left_stim + looming_stim)
        input_current[sens_right] += (base_threat + right_stim + looming_stim)
        
        # Clusters 0 y 1: Lóbulos Ópticos Izquierdo y Derecho (Visión Retinotópica & Looming)
        if hasattr(self, "map_vis_left_retina"):
            if rel_x < 0:
                input_current[self.map_vis_left_retina[:800]] += left_stim
                input_current[self.map_vis_left_motion[:600]] += left_stim * 0.8
            else:
                input_current[self.map_vis_right_retina[:800]] += right_stim
                input_current[self.map_vis_right_motion[:600]] += right_stim * 0.8
            if looming_rate > 0:
                input_current[self.map_vis_left_looming[:600]]  += looming_stim
                input_current[self.map_vis_right_looming[:600]] += looming_stim

        # Cluster 2: Mecanosensorial & Antenal (Hitlag, Escudo, Tumble, Grab)
        if player is not None and hasattr(self, "map_mech_hitlag"):
            hitstun = getattr(player, "hitstun_frames_left", 0)
            if hitstun > 0:
                input_current[self.map_mech_hitlag[:800]] += 4.5 + min(3.0, hitstun * 0.1)
            p1_act_val = getattr(player.action, "value", getattr(player, "act_val", 0))
            p1_act_str = str(getattr(player, "action", ""))
            if p1_act_val in [178, 179, 180, 181] or "SHIELD" in p1_act_str:
                input_current[self.map_mech_shield_stun[:700]] += 4.0
            if p1_act_val in [25, 26, 27, 28] or "TUMBLE" in p1_act_str or "DAMAGE" in p1_act_str:
                input_current[self.map_mech_tumble[:700]] += 4.8
            if is_p1_grabbed:
                input_current[self.map_mech_grab[:900]] += 6.0

        # Cluster 3: Complejo Central (CX) & Neuromoduladores PAM/PPL1
        dopamine_gain = self.dopamine * 2.5
        octopamine_gain = self.octopamine * 2.2
        input_current[self.map_pam[:700]] += self.dopamine * 2.0
        if hasattr(self, "map_ppl1"):
            input_current[self.map_ppl1[:700]] += octopamine_gain
        if player is not None and hasattr(self, "map_cx_compass"):
            px_val = getattr(player.position, "x", 0.0)
            edge_dist = 68.4 - abs(px_val)
            compass_val = 3.0 if edge_dist < 18.0 else 1.5
            input_current[self.map_cx_compass[:700]] += compass_val

        # Cluster 4: Cordón Nervioso Ventral (VNC Motor & Premotor)
        input_current[self.map_attack[:600]]  += dopamine_gain
        input_current[self.map_special[:600]] += dopamine_gain * 0.9
        input_current[self.map_jump[:600]]    += octopamine_gain
        input_current[self.map_shield[:600]]  += octopamine_gain * 0.9
        if rel_x < 0:
            input_current[self.map_left[:600]]  += 3.0
        else:
            input_current[self.map_right[:600]] += 3.0

        # Cluster 5: Giant Fiber (DNp01), SDI Cuántico & Saccades 20XX
        if is_offstage:
            input_current[self.map_jump[:800]] += 4.5
            input_current[self.map_gf[:800]]   += 5.5
        if player is not None and getattr(player, "hitstun_frames_left", 0) > 0 and hasattr(self, "map_sdi_quantum"):
            input_current[self.map_sdi_quantum[:800]] += 5.0
        input_current[self.map_cx_saccade[:800]] += 4.2 * (self.dopamine + 0.4)

        # Clusters 6 y 7: Precisión 20XX y Combos Cerebelares
        input_current[self.map_combo[:800]] += dopamine_gain * 1.5

        if opponent is not None:
            char_archetype = BattlefieldMap.get_character_archetype(getattr(opponent, "character", None))
            ox_val = getattr(opponent.position, "x", 0.0)
            oy_val = getattr(opponent.position, "y", 0.0)
            px_val = getattr(player.position, "x", 0.0) if player else 0.0
            py_val = getattr(player.position, "y", 0.0) if player else 0.0
            dist_val = math.hypot(ox_val - px_val, oy_val - py_val)
            opp_act_str = str(getattr(opponent, "action", ""))
            opp_act_val = getattr(opponent.action, "value", getattr(opponent, "act_val", 0))

            # Cluster 6 (Powershield, Shield Drop, Edge-Cancel, CQC)
            is_projectile = any(k in opp_act_str for k in ["LASER", "BLASTER", "MISSILE", "SPECIAL_N", "SPECIAL_S", "ITEM_THROW", "PILL", "TURNIP", "CHARGE_SHOT"]) or (opp_act_val in [341, 342, 343, 344, 345, 348, 349, 350])
            if is_projectile and hasattr(self, "map_powershield"):
                input_current[self.map_powershield[:800]] += 5.5
            if BattlefieldMap.is_on_platform(px_val, py_val - 3.0) is not None:
                if hasattr(self, "map_shield_drop"):
                    input_current[self.map_shield_drop[:600]] += 4.0
                    input_current[self.map_edge_cancel[:600]] += 4.0
                input_current[self.map_platform_shark[:600]] += 4.0
            if dist_val > 28.0:
                input_current[self.map_laser_zoning[:600]] += 3.0
            elif dist_val <= 10.0:
                input_current[self.map_cqc_counter[:600]] += 3.5

            # Cluster 7 (Combos, Tech-Chase, Predator)
            if char_archetype == "FASTFALLER":
                input_current[self.map_combo_fastfaller[:600]] += 3.5
            elif char_archetype == "FLOATY":
                input_current[self.map_combo_floaty[:600]] += 3.5
            if ((opp_act_val in range(183, 205)) or ("DOWN" in opp_act_str)) and hasattr(self, "map_tech_chase"):
                input_current[self.map_tech_chase[:800]] += 4.5
            if (getattr(opponent, "off_stage", False) or abs(ox_val) > 68.4) and hasattr(self, "map_edgeguard_predator"):
                input_current[self.map_edgeguard_predator[:800]] += 5.0
            
        return input_current

    def step(self, external_current=None):
        """Avanza 1 paso LIF recurrente en el conectoma biológico completo en ~3.5 ms con CSC."""
        self.voltage = self.voltage * self.decay
        
        if external_current is not None:
            self.voltage += external_current
            
        # Multiplicación hiper-rápida de sinapsis usando CSC solo en columnas activas
        active_neurons = np.flatnonzero(self.spikes)
        if active_neurons.size > 0:
            synaptic_input = np.asarray(self.W_csc[:, active_neurons].sum(axis=1)).ravel()
            self.voltage += synaptic_input
            
        # Estabilidad biológica y numérica garantizada
        self.voltage = np.clip(self.voltage, -15.0, 50.0)

        active_mask = (self.refractory == 0)
        new_spikes = (self.voltage >= self.threshold) & active_mask
        self.spikes = new_spikes.astype(np.float32)
        
        self.voltage[new_spikes] = 0.0
        self.refractory[new_spikes] = self.refractory_period
        self.refractory = np.maximum(0, self.refractory - 1)
        
        return self.spikes

    def _enforce_safety(self, action, player, opponent, stage_edge=68.4):
        """
        BARRERA DE SEGURIDAD ABSOLUTA (ZERO SUICIDE GUARANTEE OMNI-STAGE):
        1. Si Fox está en el suelo y se aproxima a la repisa (distancia < 14 unidades):
           - Inhabilita sprints, Dash Attacks y ataques hacia el abismo.
           - Aplica freno inmediato / retroceso hacia el centro.
        2. Si Fox está en el aire sobre el escenario en los extremos:
           - Aplica drift aéreo forzado hacia el centro y caída rápida para tocar suelo.
        3. En el aire fuera de escenario:
           - Inhabilita el botón de escudo (evita Air Dodge suicida).
        """
        if player is None:
            return action

        px = player.position.x
        py = player.position.y
        on_ground = getattr(player, "on_ground", True)

        # Detección del personaje activo (Fox o Luigi)
        char_name = str(getattr(player, "character", getattr(self, "active_character", "LUIGI"))).upper()
        is_fox = "FOX" in char_name and "LUIGI" not in char_name
        is_luigi = not is_fox

        # EXCEPCIÓN CONTROLADA: Si Fox tiene activada la caza fuera de plataforma (Offstage Chase)
        # Fox puede salir deliberadamente a rematar (Shine-spike / B-Air wall) si y solo si:
        # Tiene su doble salto disponible (player.jumps_left > 0) y altura segura.
        if action.get("_allow_offstage_chase", False) and getattr(player, "jumps_left", 0) > 0 and py > -25.0:
            if not on_ground and not action.get("_allow_air_shield", False):
                action["shield"] = False
            action["stick_x"] = float(action.get("stick_x", 0.5))
            action["stick_y"] = float(action.get("stick_y", 0.5))
            action["c_stick_x"] = float(action.get("c_stick_x", 0.5))
            action["c_stick_y"] = float(action.get("c_stick_y", 0.5))
            return action

        # En el aire: Prohibir escudo salvo si se autoriza explícitamente para L-Cancel o Wavedash
        if not on_ground and not action.get("_allow_air_shield", False):
            action["shield"] = False

        # --- A) EN EL SUELO: CONTROL ESTRICTO DE BORDES Y PODERES SUICIDAS ---
        if on_ground and py >= -2.0:
            # Los lanzamientos (Throws) son animaciones terrestres fijas; no deben frenar el stick de lanzamiento
            if "THROW" in action.get("name", ""):
                return action

            # 1. BORDE DERECHO (px > 0)
            if px > 0:
                dist_to_right_edge = stage_edge - px
                if dist_to_right_edge < 42.0:
                    # Prohibir Side-B (Green Missile / Illusion) hacia la derecha (hacia el abismo)
                    if action.get("special", False) and action.get("stick_y", 0.5) < 0.8 and action.get("stick_x", 0.5) > 0.5:
                        action["special"] = False
                    # Prohibir Up-B suicida cerca del borde si no está confirmado a quemarropa
                    if action.get("special", False) and action.get("stick_y", 0.5) > 0.8 and dist_to_right_edge < 16.0:
                        action["special"] = False
                        action["attack"] = True
                        action["stick_y"] = 0.0 # Down-smash seguro en lugar de Up-B al vacío
                    if action.get("attack", False) and action.get("stick_x", 0.5) > 0.6 and dist_to_right_edge < 12.0:
                        action["attack"] = False

                    # Si el stick intenta mover hacia el precipicio derecho, frenar y tirar al centro
                    if action.get("stick_x", 0.5) > 0.5:
                        if dist_to_right_edge < 8.0:
                            action["stick_x"] = 0.15 # Freno de emergencia hacia la izquierda
                            action["stick_y"] = 0.0
                        else:
                            action["stick_x"] = 0.35 # Drift suave hacia la izquierda

            # 2. BORDE IZQUIERDO (px < 0)
            elif px < 0:
                dist_to_left_edge = stage_edge - abs(px)
                if dist_to_left_edge < 42.0:
                    # Prohibir Side-B hacia la izquierda (hacia el abismo)
                    if action.get("special", False) and action.get("stick_y", 0.5) < 0.8 and action.get("stick_x", 0.5) < 0.5:
                        action["special"] = False
                    # Prohibir Up-B suicida cerca del borde
                    if action.get("special", False) and action.get("stick_y", 0.5) > 0.8 and dist_to_left_edge < 16.0:
                        action["special"] = False
                        action["attack"] = True
                        action["stick_y"] = 0.0
                    if action.get("attack", False) and action.get("stick_x", 0.5) < 0.4 and dist_to_left_edge < 12.0:
                        action["attack"] = False

                    # Si el stick intenta mover hacia el precipicio izquierdo, frenar y tirar al centro
                    if action.get("stick_x", 0.5) < 0.5:
                        if dist_to_left_edge < 8.0:
                            action["stick_x"] = 0.85 # Freno de emergencia hacia la derecha
                            action["stick_y"] = 0.0
                        else:
                            action["stick_x"] = 0.65 # Drift suave hacia la derecha

        # --- B) EN EL AIRE SOBRE EL ESCENARIO: DRIFT DE SEGURIDAD Y CERO FREEFALLS ---
        if not on_ground and abs(px) <= stage_edge and py >= -2.0:
            if action.get("special", False):
                if is_fox:
                    # En Fox: Shine (Down-B, stick_y < 0.3) es 100% seguro (frame-1, jump-cancel, sin freefall).
                    # Blaster (Neutral-B, stick_y ~0.5) es seguro para SHDL.
                    # Prohibir solo Up-B (Fire Fox) en el aire sobre escenario para evitar enorme landing lag:
                    if action.get("stick_y", 0.5) > 0.7:
                        action["special"] = False
                        action["attack"] = True
                        action["stick_y"] = 0.5 # Convertir a N-Air seguro
                else:
                    # En Luigi: Cyclone (Down-B, stick_y < 0.3) es seguro (no freefall, mashable).
                    # Bola de Fuego (Neutral-B) es segura.
                    # Prohibir Up-B (Shoryuken aéreo) y Side-B en el aire sobre escenario (inducen SPECIAL_FALL suicida):
                    if action.get("stick_y", 0.5) > 0.7 or (0.25 <= action.get("stick_y", 0.5) <= 0.75 and action.get("stick_x", 0.5) != 0.5):
                        action["special"] = False
                        action["attack"] = True
                        action["stick_y"] = 0.5 # Convertir a N-Air Frame-3 seguro

            if px > (stage_edge - 10.0):
                action["stick_x"] = min(float(action.get("stick_x", 0.5)), 0.20)
                if py > 6.0 and not action.get("special", False) and not action.get("jump", False):
                    action["stick_y"] = 0.0 # Fast fall para aterrizar rápido
            elif px < -(stage_edge - 10.0):
                action["stick_x"] = max(float(action.get("stick_x", 0.5)), 0.80)
                if py > 6.0 and not action.get("special", False) and not action.get("jump", False):
                    action["stick_y"] = 0.0 # Fast fall para aterrizar rápido

        # --- C) EN EL AIRE FUERA DEL ESCENARIO (OFFSTAGE): GARANTÍA DE RECUPERACIÓN INTELIGENTE ---
        if not on_ground and (abs(px) > stage_edge or py < -2.0):
            if is_luigi:
                # Prohibir Side-B (Green Missile) en el aire fuera de escenario: causa FALL_SPECIAL suicida
                if action.get("special", False) and 0.25 <= action.get("stick_y", 0.5) <= 0.75 and action.get("stick_x", 0.5) != 0.5:
                    if py > -18.0:
                        action["stick_y"] = 0.0 # Convertir a Rising Cyclone seguro (no freefall)
                    else:
                        action["stick_y"] = 0.90 # Convertir a Up-B snap a repisa
            elif is_fox:
                # En Fox: Fox Illusion (Side-B) es una opción de recuperación rápida válida cuando py >= -1.0.
                # Si Fox está muy bajo (py < -1.0) y tenta Side-B, chocaría contra la pared inferior:
                if action.get("special", False) and 0.25 <= action.get("stick_y", 0.5) <= 0.75 and action.get("stick_x", 0.5) != 0.5:
                    if py < -1.0:
                        action["stick_y"] = 0.90 # Convertir a Fire Fox Up-B para subir verticalmente a la repisa

        # Asegurar tipos numéricos para sticks
        action["stick_x"] = float(action.get("stick_x", 0.5))
        action["stick_y"] = float(action.get("stick_y", 0.5))
        action["c_stick_x"] = float(action.get("c_stick_x", 0.5))
        action["c_stick_y"] = float(action.get("c_stick_y", 0.5))
        action["taunt"] = bool(action.get("taunt", False))

        return action

    get_stage_edge = staticmethod(get_stage_edge)

    def get_fox_decision(self, player=None, opponent=None, current_frame=0, stage=None):
        """
        MOTOR DE COMBATE COMPETITIVO DE FOX McCLOUD (NIVEL TOURNAMENT SSS / 20XX OMNI-STAGE):
        1. CONEXIÓN REAL CON EL CONECTOMA: Los clusters de neuronas descendentes (DNs), Giant Fiber
           y PAM/PPL1 modulan activamente la agresión, saltos, ataques y defensa.
        2. BARRERA ANTI-SUICIDIO MULTI-ESCENARIO DINÁMICA: Fox nunca se cae corriendo ni muere offstage.
        3. RECUPERACIÓN SALVAVIDAS INFALIBLE:
           - Fox Illusion (Side-B) a distancia horizontal media/alta.
           - Salto doble completo (sin cortes prematuros en frame 1).
           - Fire Fox (Up-B) con trayectoria angular directa hacia la superficie segura del escenario.
        4. MÁQUINA DE COMBOS PROFESIONAL:
           - Up-Throw -> Jump -> Up-Air Kill Confirm.
           - Running Jump-Cancel Up-Smash (Frame 1-3 KNEE_BEND instantáneo).
           - Frame-1 Shine (Down-B) -> Jump-Cancel -> Waveshine / Grab.
           - SHFFL Nair y Drill-Shine con L-Cancel automático en aterrizaje.
           - Tech-chase con Down-Smash semi-spike.
           - Short-Hop Laser pressure a larga distancia.
        """
        # DECODIFICACIÓN INTEGRAL DE LOS 8 CLUSTERS ANATÓMICOS (395,144 NEURONAS)
        spikes_c0_c1   = int(np.sum(self.spikes[self.map_vis_left_retina]) + np.sum(self.spikes[self.map_vis_right_retina])) if hasattr(self, "map_vis_left_retina") else 0
        spikes_c2      = int(np.sum(self.spikes[self.map_mech_hitlag]) + np.sum(self.spikes[self.map_mech_shield_stun])) if hasattr(self, "map_mech_hitlag") else 0
        spikes_c3      = int(np.sum(self.spikes[self.map_pam]) + np.sum(self.spikes[self.map_ppl1])) if hasattr(self, "map_ppl1") else int(np.sum(self.spikes[self.map_pam]))
        spikes_c4      = int(np.sum(self.spikes[self.map_attack]) + np.sum(self.spikes[self.map_special]))
        spikes_c5      = int(np.sum(self.spikes[self.map_gf]) + np.sum(self.spikes[self.map_cx_saccade]))
        spikes_c6      = int(np.sum(self.spikes[self.map_powershield]) + np.sum(self.spikes[self.map_cqc_counter])) if hasattr(self, "map_powershield") else int(np.sum(self.spikes[self.map_cqc_counter]))
        spikes_c7      = int(np.sum(self.spikes[self.map_combo]) + np.sum(self.spikes[self.map_combo_fastfaller]))
        total_spikes   = int(np.sum(self.spikes))

        jump_spikes    = int(np.sum(self.spikes[self.map_jump]))
        attack_spikes  = int(np.sum(self.spikes[self.map_attack]))
        special_spikes = int(np.sum(self.spikes[self.map_special]))
        shield_spikes  = int(np.sum(self.spikes[self.map_shield]))
        combo_spikes   = int(np.sum(self.spikes[self.map_combo]))
        gf_spikes      = int(np.sum(self.spikes[self.map_gf]))
        left_spikes    = int(np.sum(self.spikes[self.map_left]))
        right_spikes   = int(np.sum(self.spikes[self.map_right]))
        
        stage_edge = get_stage_edge(stage)
        
        stats = {
            "total_spikes": total_spikes,
            "neural_activation": f"{(total_spikes / max(1, self.num_neurons)) * 100:.2f}%",
            "cluster_activity": {
                "C0_C1_Visual": spikes_c0_c1,
                "C2_Mechanosensory": spikes_c2,
                "C3_Central_Complex": spikes_c3,
                "C4_VNC_Motor": spikes_c4,
                "C5_Giant_Fiber_SDI": spikes_c5,
                "C6_Precision_20XX": spikes_c6,
                "C7_Cerebellar_Combos": spikes_c7
            },
            "jump_p": jump_spikes,
            "attack_p": attack_spikes,
            "special_p": special_spikes,
            "shield_p": shield_spikes,
            "combo_p": combo_spikes,
            "gf_p": gf_spikes,
            "dopamine": round(float(self.dopamine), 2),
            "octopamine": round(float(self.octopamine), 2),
            "combo_count": self.combo_count,
            "stage_edge": stage_edge,
            "character": "FOX"
        }
        
        # =========================================================================
        # MODO AUTÓNOMO / TEST (player is None): Decodificación directa de spikes
        # =========================================================================
        if player is None or opponent is None:
            # En test_fly_brain.py o simulación pura: responder según la actividad del cluster motor dominante
            net_x = float(np.tanh((right_spikes - left_spikes) / 25.0))
            
            # Puntuación por cluster motor biológico
            jump_score = jump_spikes + gf_spikes * 1.5
            attack_score = attack_spikes + (combo_spikes * 0.05)
            special_score = special_spikes * 1.2
            shield_score = shield_spikes * 1.1
            
            is_jump = False
            is_attack = False
            is_special = False
            is_shield = False
            action_name = "🏃 DRIFT MOTOR TÁCTICO"
            
            # Escoger acción principal según el cluster de mayor descarga
            max_score = max(jump_score, attack_score, special_score, shield_score, 10.0)
            if max_score > 12.0:
                if max_score == jump_score:
                    is_jump = True
                    # Si el ataque también está activo: Salto con ataque aéreo
                    if attack_score > 15.0:
                        is_attack = True
                        action_name = "🦅 ASALTO AÉREO: SHORT-HOP NAIR"
                    else:
                        action_name = "🦘 SALTO REFLEJO (DNp01 / Giant Fiber)"
                elif max_score == attack_score:
                    is_attack = True
                    action_name = "⚔️ ASALTO MOTOR: UP-SMASH / JAB"
                elif max_score == special_score:
                    is_special = True
                    action_name = "🦊 REFLECTOR SHINE FRAME-1 (Cluster 6)"
                elif max_score == shield_score:
                    is_shield = True
                    action_name = "🛡️ ESCUDO / TECH DEFENSIVO (Cluster 6)"
            elif abs(net_x) > 0.15:
                action_name = f"🏃 MOVIMIENTO: {'DERECHA' if net_x > 0 else 'IZQUIERDA'}"

            return {
                "name": action_name,
                "jump": bool(is_jump),
                "attack": bool(is_attack),
                "special": bool(is_special),
                "shield": bool(is_shield),
                "grab": False,
                "stick_x": float(0.5 + 0.45 * net_x),
                "stick_y": float(0.85 if is_jump else (0.15 if is_special else 0.5)),
                "c_stick_x": 0.5,
                "c_stick_y": float(1.0 if is_attack and is_jump else 0.5),
                "stats": stats
            }

        px = player.position.x
        py = player.position.y
        ox = opponent.position.x
        oy = opponent.position.y
        
        dx = ox - px
        dy = oy - py
        dist = math.hypot(dx, dy)
        
        towards_opp = 1.0 if dx > 0 else 0.0
        dir_to_stage = 1.0 if px < 0 else 0.0
        
        act_str = str(player.action)
        opp_act_str = str(opponent.action)
        act_val = getattr(player.action, "value", getattr(player, "act_val", 0))
        opp_act_val = getattr(opponent.action, "value", getattr(opponent, "act_val", 0))
        action_frame = getattr(player, "action_frame", 1)
        opp_offstage = getattr(opponent, "off_stage", False) or (abs(ox) >= (stage_edge - 1.0) and oy < 1.0) or ("EDGE" in opp_act_str) or (opp_act_val in [252, 253])
        opp_char = getattr(opponent, "character", None)
        archetype = BattlefieldMap.get_character_archetype(opp_char)
        self.combo_archetype = archetype
        opp_plat = BattlefieldMap.is_on_platform(ox, oy)
        
        self.prev_dist_fox = dist
        opp_is_falling = BattlefieldMap.is_opponent_falling(ox, oy, getattr(opponent, "on_ground", True), opp_offstage, stage_edge=stage_edge)

        # ENTRENAMIENTO DE MEMORIA EN TIEMPO REAL (Frame-by-frame STDP y hábitos del oponente)
        self.realtime_memory_train(player, opponent, current_frame=current_frame)

        # =========================================================================
        # 0. ESTADOS DE RESPAWN (HALO PLATFORM)
        # =========================================================================
        is_on_halo = (act_val in [12, 13]) or ("HALO" in act_str)
        if is_on_halo:
            return {
                "name": "⚡ BAJANDO DE PLATAFORMA DE RESPAWN",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": float(dir_to_stage), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }

        # SWAGGER 20XX: Si el rival está muerto o en halo de respawn, alternar taunt y dash-dance
        opp_on_halo = (opp_act_val in [12, 13]) or ("HALO" in opp_act_str)
        if opp_on_halo and getattr(player, "on_ground", True) and abs(px) < (stage_edge - 14.0):
            if (current_frame // 35) % 2 == 0 and self.dopamine > 0.50:
                return self._enforce_safety({
                    "name": "🦊 SWAGGER 20XX: FOX TAUNT (COME ON! HUMILLACIÓN MENTAL)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False, "taunt": True,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            dance_x = 1.0 if (current_frame // 4) % 2 == 0 else 0.0
            return self._enforce_safety({
                "name": "🦊 SWAGGER 20XX: DASH-DANCE DE DOMINANCIA EN CENTRO",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False, "taunt": False,
                "stick_x": float(dance_x), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # HUMILLACIÓN 20XX: Disrespect a rival cayendo al abismo sin retorno
        opp_pct = float(getattr(opponent, "percent", 0.0))
        if opp_offstage and oy < -10.0 and opp_pct >= 55.0 and getattr(player, "on_ground", True) and abs(px) < (stage_edge - 12.0):
            flex_shine = (current_frame % 4 == 0)
            teabag_y = 0.0 if (current_frame % 4 < 2) else 0.5
            return self._enforce_safety({
                "name": "🦊 HUMILLACIÓN 20XX: RAPID TEABAG / MULTI-SHINE FLEX",
                "jump": False, "attack": False, "special": flex_shine, "shield": False, "grab": False,
                "stick_x": 0.5, "stick_y": 0.0 if flex_shine else teabag_y, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 1. HITSTUN, DAÑO, TUMBLE & TECHING (RECUPERACIÓN INSTANTÁNEA TRAS GOLPES)
        # =========================================================================
        is_on_ledge = act_val in [252, 253] or any(k in act_str for k in ["EDGE_CATCHING", "EDGE_HANGING"])
        is_offstage = is_on_ledge or ((not getattr(player, "on_ground", True)) and (
            abs(px) >= (stage_edge - 2.0) or py < -0.8
        ))

        hitstun_left = getattr(player, "hitstun_frames_left", 0)
        is_in_hitstun = hitstun_left > 0 or ("DAMAGE" in act_str and "AIR" in act_str) or (act_val in range(75, 92))
        is_tumbling = (act_val == 38) or ("TUMBL" in act_str)

        if is_in_hitstun:
            sdi_cycle = current_frame % 2
            sdi_x = float(dir_to_stage) if sdi_cycle == 0 else 0.5
            sdi_y = 0.85 if sdi_cycle == 0 else 0.15
            # Survival DI hacia el centro/arriba con SDI multi-frame cuántico 20XX
            return self._enforce_safety({
                "name": "🛡️ SURVIVAL DI + SDI CUÁNTICO HACIA EL ESCENARIO",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": float(sdi_x), "stick_y": float(sdi_y), "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # Fox capturado en agarre por el rival: Mash-out 20XX a 60 inputs/segundo
        is_captured = (act_val in range(223, 230)) or ("CAPTURE" in act_str)
        if is_captured:
            mash_cycle = current_frame % 4
            mash_x = 0.0 if mash_cycle in [0, 1] else 1.0
            mash_y = 0.85 if mash_cycle in [1, 2] else 0.15
            mash_btn_a = (mash_cycle % 2 == 0)
            mash_btn_b = (mash_cycle % 2 == 1)
            return self._enforce_safety({
                "name": "⚡ MASH-OUT ESCAPE 20XX: ZAFARSE DEL AGARRE A VELOCIDAD RÉCORD",
                "jump": (mash_cycle == 0),
                "attack": mash_btn_a,
                "special": mash_btn_b,
                "shield": False,
                "grab": False,
                "stick_x": float(mash_x),
                "stick_y": float(mash_y),
                "c_stick_x": 0.5,
                "c_stick_y": 0.5,
                "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        is_being_thrown = (act_val in range(230, 234)) or ("THROWN" in act_str)
        if is_being_thrown:
            return self._enforce_safety({
                "name": "🛡️ SURVIVAL DI AL LANZAMIENTO HACIA EL ESCENARIO",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": float(dir_to_stage), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        if is_tumbling:
            # Si va a tocar el suelo sobre el escenario: TECH PERFECTO (L)
            if py <= 7.0 and getattr(player, "speed_y_self", 0) < -0.15 and abs(px) <= (stage_edge - 4.0):
                return self._enforce_safety({
                    "name": "🛡️ TECH PERFECTO EN EL SUELO (L)",
                    "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5,
                    "_allow_air_shield": True, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            # En el aire: Cancelar tumble con salto si hay disponibles o con Nair en el escenario
            if getattr(player, "jumps_left", 0) > 0:
                return self._enforce_safety({
                    "name": "🪰 SALTO AÉREO: CANCELAR TUMBLE",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            elif not is_offstage:
                return self._enforce_safety({
                    "name": "🦅 NAIR AÉREO: CANCELAR TUMBLE",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            # Si Fox está offstage y sin saltos, caer directamente a la recuperación infalible (Fire Fox / Illusion)

        # Fox caído en el suelo: levantarse con invulnerabilidad hacia el centro
        if "DOWN_BOUND" in act_str or "LYING" in act_str or "DOWN_WAIT" in act_str or (act_val in range(183, 195)):
            return self._enforce_safety({
                "name": "🏃 GETUP ROLL HACIA EL CENTRO",
                "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 2. RECUPERACIÓN SALVAVIDAS INFALIBLE DE FOX (OFFSTAGE & ANTI-CHOQUE INFERIOR)
        # =========================================================================

        if is_offstage:
            # -----------------------------------------------------------------
            # 2.0. EXCEPCIÓN: PERSECUCIÓN OFENSIVA OFFSTAGE (SHINE-SPIKE / B-AIR)
            # Si Fox está deliberadamente cazando al rival fuera del escenario con su salto doble intacto:
            # -----------------------------------------------------------------
            if getattr(self, "edgeguard_state", None) in ["OFFSTAGE_SHINE", "OFFSTAGE_BAIR"] and getattr(player, "jumps_left", 0) > 0 and py >= -22.0 and (opp_offstage or opp_is_falling):
                self.edgeguard_timer += 1
                if self.edgeguard_state == "OFFSTAGE_SHINE":
                    # Si Fox ya está pegado al rival (dist <= 13.0 o abs(dx) < 10.0 y abs(dy) < 9.0):
                    if dist <= 13.0 or (abs(dx) < 10.0 and abs(dy) < 9.0):
                        if current_frame - getattr(self, "offstage_shine_frame", -100) <= 3:
                            # Frame 1-3: Reflector Shine Frame-1 activo enviando al rival hacia abajo (Spike brutal)
                            return {
                                "name": "🦊 OFFSTAGE SHINE-SPIKE FRAME-1 (SEMI-SPIKE AL VACÍO)",
                                "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                                "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5,
                                "_allow_offstage_chase": True, "stats": stats
                            }
                        else:
                            # Frame 4+: Shine conectado -> Jump Cancel inmediato con doble salto de retorno al escenario
                            self.edgeguard_state = None
                            self.learn_from_success("OFFSTAGE_SHINE")
                            self.dopamine = min(1.0, self.dopamine + 0.50)
                            return {
                                "name": "⚡ SHINE-SPIKE EXIT: JUMP-CANCEL RETORNO AL ESCENARIO",
                                "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                                "stick_x": float(dir_to_stage), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5,
                                "_allow_offstage_chase": True, "stats": stats
                            }
                    else:
                        # Acercándose al rival en el aire offstage
                        return {
                            "name": "🦅 OFFSTAGE HUNT: APROXIMACIÓN AÉREA PARA SHINE-SPIKE",
                            "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                            "stick_x": float(towards_opp), "stick_y": 0.35, "c_stick_x": 0.5, "c_stick_y": 0.5,
                            "_allow_offstage_chase": True, "stats": stats
                        }
                elif self.edgeguard_state == "OFFSTAGE_BAIR":
                    self.edgeguard_state = None
                    self.learn_from_success("EDGEGUARD")
                    return {
                        "name": "🦅 OFFSTAGE B-AIR: WALL OF PAIN",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(dir_to_stage), "stick_y": 0.5,
                        "c_stick_x": float(1.0 - towards_opp if getattr(player, "facing", True) else towards_opp),
                        "c_stick_y": 0.5,
                        "_allow_offstage_chase": True, "stats": stats
                    }
            else:
                self.edgeguard_state = None

            self.combo_state = None

            # Detección del peligro de choque debajo del escenario (Underside / Under-lip Hazard):
            # Si Fox está por debajo del nivel de la plataforma y dentro del ancho del escenario (o cerca del labio):
            is_under_stage = (py < 0.0) and (abs(px) < (stage_edge + 4.5))

            # Dirección de escape hacia el aire libre (lejos del centro x=0):
            # Si Fox está en el lado derecho (px >= 0), la salida libre está a la DERECHA (+1.0).
            # Si Fox está en el lado izquierdo (px < 0), la salida libre está a la IZQUIERDA (0.0 / -1.0).
            escape_outward_x = 1.0 if px >= 0.0 else 0.0

            # A) Colgado de la repisa: SUBIDA SEGURA CON INVULNERABILIDAD ABSOLUTA (Requisito 10)
            if is_on_ledge:
                self.ledge_timer += 1
                edge_dist_to_opp = abs(ox - px)
                
                # Si Fox está enganchándose a la repisa (EDGE_CATCHING / 252, frames 1-7):
                if act_val == 252 or "EDGE_CATCH" in act_str:
                    return {
                        "name": "⚡ ENGANCHANDO REPISA (INVENCIBLE)",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }

                # Ledge-Stall / Hax-Dash: Refrescar 30 frames de invulnerabilidad total
                if self.ledge_timer > 26 and getattr(player, "jumps_left", 0) > 0:
                    self.ledge_timer = 0
                    return {
                        "name": "⚡ LEDGE-STALL: REFRESCAR INVULNERABILIDAD TOTAL",
                        "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(dir_to_stage), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }

                # En EDGE_HANGING (253): Decidir opción invulnerable según espaciado del rival
                # Opción 1: Si el rival está pegado al borde (<14 u) esperando para atacar:
                # -> LEDGE ROLL: 38 frames de intangibilidad que atraviesa completamente al rival
                if edge_dist_to_opp < 14.0 and abs(oy - py) < 18.0:
                    self.learn_opponent_habit("ledge_attack_freq")
                    self.ledge_option_state = None
                    return {
                        "name": "⚡ SUBIDA INVULNERABLE: LEDGE ROLL (ATRAVESAR AL RIVAL)",
                        "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }
                
                # Opción 2: Rival a distancia media/larga (>=14 u):
                # -> INVINCIBLE LEDGEDASH: Drop -> Jump -> Waveland onto stage con 10-14 frames de invencibilidad total
                if self.ledge_option_state == "LEDGEDASH_AIR":
                    self.ledge_option_state = None
                    return {
                        "name": "⚡ LEDGEDASH: WAVELAND INVENCIBLE EN ESCENARIO",
                        "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                        "stick_x": float(dir_to_stage), "stick_y": 0.15, "c_stick_x": 0.5, "c_stick_y": 0.5,
                        "_allow_air_shield": True, "stats": stats
                    }
                elif self.ledge_timer % 3 == 0:
                    self.ledge_option_state = "LEDGEDASH_AIR"
                    return {
                        "name": "⚡ LEDGEDASH: SALTO CONDUCENTE AL ESCENARIO",
                        "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(dir_to_stage), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }
                else:
                    # Opción 3: Normal Getup (Subida normal 100% invencible)
                    return {
                        "name": "⚡ SUBIDA INVULNERABLE: NORMAL GETUP",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }

            # B) Fox en Fire Fox (Up-B: Carga o Vuelo - Actions 353, 354, 355, 356)
            is_firefox_active = (act_val in [353, 354, 355, 356]) or any(k in act_str for k in [
                "FIREFOX", "UP_B", "SPECIAL_HI"
            ])
            if is_firefox_active:
                # -------------------------------------------------------------
                # CÁLCULO DE ÁNGULO DE FIRE FOX ANTI-CHOQUE BAJO PLATAFORMA
                # -------------------------------------------------------------
                # Zona 1: Fox está directamente debajo del escenario (abs(px) < stage_edge - 1.0 y py < -4.0)
                # Peligro de chocar la cabeza contra el techo inferior de Battlefield:
                # -> DEBE apuntar en diagonal HACIA AFUERA Y ARRIBA para salir al aire libre.
                if is_under_stage and abs(px) < (stage_edge - 1.0) and py < -4.0:
                    target_x = (stage_edge + 12.0) if px >= 0.0 else -(stage_edge + 12.0)
                    target_y = max(py + 18.0, 2.0)
                    dx_rec = target_x - px
                    dy_rec = target_y - py
                    angle = math.atan2(dy_rec, dx_rec)
                    stick_x = 0.5 + 0.49 * math.cos(angle)
                    stick_y = 0.5 + 0.49 * math.sin(angle)
                    return {
                        "name": "🔥 FIRE FOX SALVAVIDAS: ESCAPE DEBAJO DEL ESCENARIO AL AIRE",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(stick_x), "stick_y": float(stick_y), "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }

                # Zona 2: The Mangle (Rival acampa en el borde para edgeguardear con Down-Smash o F-Smash)
                # Si el rival está en el borde (abs(ox) > stage_edge - 14.0 y oy >= -2.0) y Fox está a media altura:
                # En lugar de un sweetspot predecible, Fox vuela ALTO y PROFUNDO hacia el centro / plataforma superior
                is_opp_at_edge = abs(ox) > (stage_edge - 14.0) and oy >= -2.0
                if is_opp_at_edge and py > -12.0 and not is_under_stage:
                    target_x = 0.0 # Centro del escenario
                    target_y = 20.0 # Plataforma superior de Battlefield
                    dx_rec = target_x - px
                    dy_rec = target_y - py
                    angle = math.atan2(dy_rec, dx_rec)
                    stick_x = 0.5 + 0.49 * math.cos(angle)
                    stick_y = 0.5 + 0.49 * math.sin(angle)
                    return {
                        "name": "🔥 THE MANGLE: FIRE FOX PROFUNDO SOBRE EL RIVAL EN BORDE",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(stick_x), "stick_y": float(stick_y), "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }

                # Zona 3: Fox está bajo el nivel de la repisa en aire exterior (py < -1.0)
                # Peligro de chocar contra el labio/esquina inferior si apunta hacia el centro del escenario:
                # -> Wall-Ride / Sweetspot a la repisa (y = -0.5, x = stage_edge + 1.2)
                elif py < -1.0:
                    sweetspot_x = (stage_edge + 1.2) if px >= 0.0 else -(stage_edge + 1.2)
                    sweetspot_y = -0.5
                    dx_rec = sweetspot_x - px
                    dy_rec = sweetspot_y - py
                    angle = math.atan2(dy_rec, dx_rec)
                    stick_x = 0.5 + 0.49 * math.cos(angle)
                    stick_y = 0.5 + 0.49 * math.sin(angle)
                    return {
                        "name": "🔥 FIRE FOX DE PRECISIÓN: SWEETSPOT A LA REPISA (ANTI-CHOQUE)",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(stick_x), "stick_y": float(stick_y), "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }

                # Zona 4: Fox está a nivel o por encima del escenario (py >= -1.0)
                # No hay techo ni labio en la trayectoria; puede aterrizar seguro en la superficie:
                else:
                    safe_target_x = (stage_edge - 12.0) if px >= 0.0 else -(stage_edge - 12.0)
                    safe_target_y = 2.0
                    dx_rec = safe_target_x - px
                    dy_rec = safe_target_y - py
                    angle = math.atan2(dy_rec, dx_rec)
                    stick_x = 0.5 + 0.49 * math.cos(angle)
                    stick_y = 0.5 + 0.49 * math.sin(angle)
                    return {
                        "name": "🔥 DIRIGIENDO FIRE FOX AL ESCENARIO",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(stick_x), "stick_y": float(stick_y), "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }

            # C) Fox Illusion activo (Side-B en vuelo - Actions 350, 351, 352)
            is_illusion_active = (act_val in [350, 351, 352]) or ("ILLUSION" in act_str)
            if is_illusion_active:
                return {
                    "name": "⚡ FOX ILLUSION EN VUELO AL ESCENARIO",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # D) Caída libre indefensa (Special Fall - Actions 36, 37)
            if act_val in [36, 37] or "SPECIAL_FALL" in act_str:
                fall_dir_x = escape_outward_x if is_under_stage else dir_to_stage
                return {
                    "name": "🪰 DRIFT DE CAÍDA (LIBRANDO PLATAFORMA)" if is_under_stage else "🪰 DRIFT AL ESCENARIO (SPECIAL FALL)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(fall_dir_x), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # D.1) AIRDODGE DIRECCIONAL A LA REPISA / WAVELAND
            # Si Fox está cerca de la repisa (-3.5 <= py <= 4.0 y stage_edge - 2.0 <= abs(px) <= stage_edge + 7.5),
            # sin saltos disponibles, y fuera del peligro de techo inferior:
            # Snap instantáneo hacia la repisa o waveland al escenario sin los 43 frames de carga de Up-B!
            if (stage_edge - 2.0 <= abs(px) <= stage_edge + 7.5) and (-3.5 <= py <= 4.0) and getattr(player, "jumps_left", 0) == 0 and not is_under_stage and act_val not in [36, 37]:
                return {
                    "name": "⚡ AIRDODGE DIRECCIONAL: SNAP INSTANTÁNEO A LA REPISA / WAVELAND",
                    "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.25, "c_stick_x": 0.5, "c_stick_y": 0.5,
                    "_allow_air_shield": True, "stats": stats
                }

            # E) Recuperación Horizontal Rápida con Fox Illusion (Side-B):
            # REGLA DE ORO ANTI-CHOQUE: Side-B es estrictamente horizontal.
            # Si py < -1.0, chocaría contra la pared lateral o abajo del labio.
            # SOLO se permite si Fox está alto (py >= -1.0) y a distancia horizontal prudencial:
            if py >= -1.0 and abs(px) > (stage_edge + 10.0) and getattr(player, "jumps_left", 0) == 0:
                return {
                    "name": "⚡ FOX ILLUSION (Side-B HORIZONTAL ALTO)",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # F) Salto doble si está disponible:
            if getattr(player, "jumps_left", 0) > 0:
                self.double_jump_start_frame = current_frame
                # Si Fox está debajo del escenario, debe saltar curvando HACIA AFUERA para librar el techo inferior:
                jump_dir_x = escape_outward_x if is_under_stage else dir_to_stage
                return {
                    "name": "🪰 SALTO DOBLE SALVAVIDAS: EVASIÓN DEBAJO DE LA PLATAFORMA" if is_under_stage else "🪰 SALTO DOBLE SALVAVIDAS AL ESCENARIO",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(jump_dir_x), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # G) Mantener drift de ascenso del salto doble
            frames_since_jump = current_frame - getattr(self, "double_jump_start_frame", -100)
            if frames_since_jump < 16 and getattr(player, "speed_y_self", 0) > -0.1:
                jump_dir_x = escape_outward_x if is_under_stage else dir_to_stage
                return {
                    "name": "🪰 ASCENSO DE SALTO DOBLE (LIBRANDO PLATAFORMA)" if is_under_stage else "🪰 ASCENSO DE SALTO DOBLE AL ESCENARIO",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(jump_dir_x), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # H) Fire Fox (Up-B): Inicio seguro
            # Si Fox está debajo del escenario, inclinar el stick ligeramente hacia AFUERA durante el inicio
            # para comenzar a alejarse del techo mientras carga el fuego:
            init_stick_x = (0.5 + (0.28 if px >= 0.0 else -0.28)) if is_under_stage else 0.5
            return {
                "name": "🔥 INICIANDO FIRE FOX (ESCAPE DEBAJO DEL ESCENARIO)" if is_under_stage else "🔥 INICIANDO FIRE FOX (Up-B SEGURO)",
                "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                "stick_x": float(init_stick_x), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }

        # Fox en el escenario: resetear estados de repisa
        self.ledge_timer = 0
        self.ledge_option_state = None

        # =========================================================================
        # 3. L-CANCEL AUTOMÁTICO EN ATERRIZAJES DE ATAQUES AÉREOS & PLATFORM EDGE-CANCEL
        # =========================================================================
        if any(aerial in act_str for aerial in ["NAIR", "DAIR", "UAIR", "BAIR", "FAIR"]) or (act_val in [65, 66, 67, 68, 69]):
            is_on_plat_landing = BattlefieldMap.is_on_platform(px, py - 3.0, stage)
            is_near_landing = (0.0 <= py <= 8.5) or (22.0 <= py <= 32.0) or (48.0 <= py <= 60.0) or (is_on_plat_landing is not None)
            
            # PLATFORM EDGE-CANCEL SLIDE: Deslizamiento fuera del borde de plataforma a 0 frames de lag
            h_speed = max(abs(getattr(player, "speed_ground_x_self", 0.0)), abs(getattr(player, "speed_air_x_self", 0.0)))
            is_near_plat_edge = False
            if is_on_plat_landing and h_speed > 0.40:
                if abs(abs(px) - 19.5) < 3.5 or abs(abs(px) - 58.0) < 3.5 or abs(abs(px) - 19.0) < 3.5:
                    is_near_plat_edge = True

            if is_near_plat_edge:
                return self._enforce_safety({
                    "name": "⚡ FOX PLATFORM EDGE-CANCEL: CANCELACIÓN A CERO FRAMES DE LAG",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            if is_near_landing and getattr(player, "speed_y_self", 0) < -0.15:
                if "DAIR" in act_str or act_val == 67 or getattr(self, "drill_smash_state", None) == "DRILL_ACTIVE":
                    self.drill_smash_state = "DRILL_LANDED"
                return self._enforce_safety({
                    "name": "⚡ L-CANCEL PERFECTO (L)",
                    "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5,
                    "_allow_air_shield": True, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        # COMBO ESPECÍFICO: DRILL-SMASH & DRILL-SHINE SHIELD PRESSURE
        if getattr(self, "drill_smash_state", None) in ["DRILL_ACTIVE", "DRILL_LANDED"] and getattr(player, "on_ground", True):
            self.drill_smash_state = None
            is_shield_opp = ("SHIELD" in opp_act_str or opp_act_val in [178, 179, 180, 181])
            if is_shield_opp:
                self.learn_from_success("SHIELD_PUNISH")
                return self._enforce_safety({
                    "name": "🦊 DRILL-SHINE SHIELD PRESSURE: FRAME-1 SHINE POKE",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            self.learn_from_success("DRILL_SMASH")
            self.dopamine = min(1.0, self.dopamine + 0.55)
            self.combo_count += 2
            return self._enforce_safety({
                "name": "💥 DRILL-SMASH: JC UP-SMASH KILL CONFIRM",
                "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 4. ESCUDO INTELIGENTE Y OPCIONES OUT OF SHIELD (OOS) (Requisito 9)
        # =========================================================================
        is_shielding = (act_val in [178, 179, 180, 181]) or ("SHIELD" in act_str)
        shield_hp = getattr(player, "shield_strength", 60.0)

        if is_shielding:
            self.shield_frames += 1

            # A) Prevención de rotura de escudo: rodar o wavedash si la salud es crítica
            if shield_hp < 26.0:
                self.shield_frames = 0
                return self._enforce_safety({
                    "name": "🛡️ ESCUDO: ROLL DE EMERGENCIA (ANTI-BREAK)",
                    "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # A2) SHIELD DROP 20XX: Si Fox está en escudo sobre una plataforma y el rival está abajo
            fox_plat = BattlefieldMap.is_on_platform(px, py, stage)
            if fox_plat and (oy < py - 3.5):
                self.shield_frames = 0
                self.learn_from_success("SHIELD_DROP")
                return self._enforce_safety({
                    "name": "🛡️ FOX SHIELD DROP 20XX: DESCENSO INSTANTÁNEO ➔ DRILL / SHINE",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.28, "c_stick_x": 0.5, "c_stick_y": 0.0,
                    "_allow_drop_through": True, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # B) Si el rival está a rango cuerpo a cuerpo (dist <= 12.0 u):
            # 1. SHINE OUT OF SHIELD (Frame 4 OOS - La mejor defensa de Fox en Melee):
            if dist <= 11.0:
                if self.shield_frames % 2 == 1:
                    # Frame 1 del JC: Salto desde el escudo
                    return self._enforce_safety({
                        "name": "⚡ SHINE OUT OF SHIELD: JUMP-CANCEL",
                        "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    # Frame 4: Reflector Shine Frame-1 inmediato
                    self.learn_from_success("SHIELD_PUNISH")
                    return self._enforce_safety({
                        "name": "🦊 SHINE OUT OF SHIELD: REFLECTOR FRAME-1",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # 2. UP-SMASH OUT OF SHIELD (Frame 8 OOS si rival tiene porcentaje letal):
            if dist <= 15.0 and getattr(opponent, "percent", 0) > 65.0:
                return self._enforce_safety({
                    "name": "💥 UP-SMASH OUT OF SHIELD (KILL CONFIRM)",
                    "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 3. SHIELD GRAB: Agarrar al rival si está en lag de impacto frente a Fox
            if dist <= 12.0:
                return self._enforce_safety({
                    "name": "🤼 SHIELD GRAB: CONTRAATAQUE (Z)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": True,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # Si el rival está lejos: Soltar escudo limpiamente
            if dist > 18.0 or self.shield_frames > 25:
                self.shield_frames = 0
                return self._enforce_safety({
                    "name": "🛡️ SOLTAR ESCUDO (REPOSICIONAMIENTO)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
        else:
            self.shield_frames = 0

        # =========================================================================
        # 5. AGARRES LETALES Y MÁQUINA DE COMBOS DE FOX (Requisitos 2 y 4)
        # =========================================================================
        is_grabbing = any(k in act_str for k in ["GRAB_WAIT", "GRAB_PULLING", "GRAB_RUNNING_PULLING", "GRAB_PULL"]) or (act_val in [213, 215, 216, 226])
        is_throw_up = ("THROW_UP" in act_str) or (act_val == 221)
        opp_pct = float(getattr(opponent, "percent", 0.0))

        # DECISIÓN DE LANZAMIENTO SEGÚN POSICIÓN EN ESCENARIO Y PORCENTAJE
        if is_grabbing:
            # Si Fox está cerca del borde (<16 u): LANZAR HACIA AFUERA PARA EDGEGUARD LETAL
            if abs(px) > (stage_edge - 16.0):
                # Si el rival está hacia el abismo: Forward Throw
                if (px > 0 and dx > 0) or (px < 0 and dx < 0):
                    self.combo_state = "EDGEGUARD_SETUP"
                    return self._enforce_safety({
                        "name": "🤼 FORWARD-THROW AL ABISMO (EDGEGUARD SETUP)",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    self.combo_state = "EDGEGUARD_SETUP"
                    return self._enforce_safety({
                        "name": "🤼 BACK-THROW AL ABISMO (EDGEGUARD SETUP)",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(1.0 - towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
            else:
                # En el escenario: UP-THROW (Fox's supreme combo throw)
                self.combo_state = "UPTHROW_UAIR"
                self.combo_timer = 0
                return self._enforce_safety({
                    "name": "🤼 COMBO SUPREMO: UP-THROW (LANZAMIENTO ARRIBA)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        if is_throw_up:
            self.combo_state = "UPTHROW_UAIR"
            self.combo_timer += 1
            return self._enforce_safety({
                "name": "🤼 COMBO: UP-THROW EN EJECUCIÓN",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # SEGUIMIENTO MORTAL DEL UP-THROW SEGÚN PORCENTAJE
        if self.combo_state == "UPTHROW_UAIR":
            self.combo_timer += 1
            if getattr(player, "on_ground", True):
                if action_frame >= 28 or act_val in [14, 20, 21, 24]:
                    # Porcentaje bajo (<36%): Up-Tilt o Regrab chaingrab
                    if opp_pct < 36.0:
                        return self._enforce_safety({
                            "name": "💥 COMBO LOW-%: RUNNING JC UP-SMASH / UP-TILT",
                            "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                            "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)
                    else:
                        # Porcentaje medio/alto (>=36%): Salto hacia el rival
                        return self._enforce_safety({
                            "name": "🦘 COMBO: SALTO DE PERSECUCIÓN UP-AIR",
                            "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                            "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)
            else:
                # Fox está en el aire:
                if dy > 0.5 and abs(dx) < 18.0:
                    self.combo_count += 1
                    self.dopamine = min(1.0, self.dopamine + 0.45)
                    self.learn_from_success("GRAB_COMBO")
                    self.combo_state = None
                    return self._enforce_safety({
                        "name": "💥 COMBO FINISHER: UP-AIR DEMOLEDOR",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif opp_pct > 105.0 and getattr(player, "jumps_left", 0) > 0:
                    # Si el rival vuela muy alto por daño: Doble Salto + Up-Air a techo
                    return self._enforce_safety({
                        "name": "🦘 COMBO EXTREMO: DOBLE SALTO AL TECHO",
                        "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif self.combo_timer > 60:
                    self.combo_state = None

        # COMBO B: RUNNING JC UP-SMASH (Jumpsquat Frame 1-3 instantáneo)
        is_jumpsquat = ("KNEE_BEND" in act_str) or (act_val == 24)
        if is_jumpsquat and self.combo_state != "WAVESHINE_COMBO":
            return self._enforce_safety({
                "name": "💥 RUNNING JC UP-SMASH INSTANTÁNEO",
                "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # COMBO C: CADENA SUPREMA DE WAVESHINE (Reflector Shine -> Jump-Cancel -> Wavedash -> Finisher)
        is_shine_active = ("DOWN_B_GROUND" in act_str) or (act_val in [360, 361, 364])
        if is_shine_active:
            if action_frame >= 4:
                self.combo_state = "WAVESHINE_COMBO"
                self.combo_step = 2
                self.combo_timer = 0
                return self._enforce_safety({
                    "name": "⚡ WAVESHINE: JUMP-CANCEL HACIA EL RIVAL",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            else:
                return self._enforce_safety({
                    "name": "🦊 REFLECTOR SHINE ACTIVO (Frame 1-3)",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        # CONTINUACIÓN DE LA CADENA WAVESHINE:
        if self.combo_state == "WAVESHINE_COMBO":
            self.combo_timer += 1
            if not getattr(player, "on_ground", True) or is_jumpsquat:
                # Fox en jumpsquat/aire tras el JC: Wavedash hacia adelante (Airdodge diagonal)
                return self._enforce_safety({
                    "name": "⚡ WAVESHINE: WAVEDASH ADELANTE (AIRDODGE DIAGONAL)",
                    "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.25, "c_stick_x": 0.5, "c_stick_y": 0.5,
                    "_allow_air_shield": True, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            else:
                # Fox aterrizó con deslizamiento de wavedash:
                # Rama 1: Cerca del borde (< 15 u) -> Down-Smash semi-spike al abismo
                if abs(px) > (stage_edge - 15.0):
                    self.combo_state = None
                    self.combo_count += 2
                    self.learn_from_success("COMBO")
                    return self._enforce_safety({
                        "name": "💥 WAVESHINE ➔ DOWN-SMASH SEMI-SPIKE AL ABISMO",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                # Rama 2: Porcentaje alto (>= 45%) -> Running Jump-Cancel Up-Smash (Kill Confirm)
                elif opp_pct >= 45.0:
                    self.combo_state = None
                    self.combo_count += 2
                    self.learn_from_success("COMBO")
                    return self._enforce_safety({
                        "name": "💥 WAVESHINE ➔ RUNNING JC UP-SMASH (KILL CONFIRM)",
                        "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                # Rama 3: Contra Fastfallers a bajo % (< 45%) con espacio de escenario -> Loop de Waveshine!
                elif archetype == "FASTFALLER" and opp_pct < 45.0 and abs(px) < (stage_edge - 18.0):
                    self.combo_state = None
                    self.combo_count += 2
                    self.learn_from_success("COMBO")
                    return self._enforce_safety({
                        "name": "⚡ MULTI-WAVESHINE LOOP (FASTFALLER TRAP)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                # Rama 4: Porcentaje bajo (< 45%) o rival pegado -> Instant Grab -> Up-Throw Up-Air
                else:
                    self.combo_state = "UPTHROW_UAIR"
                    self.combo_timer = 0
                    self.combo_count += 1
                    return self._enforce_safety({
                        "name": "🤼 WAVESHINE ➔ GRAB (COMBO SUPREMO)",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": True,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 6. COMBATE AÉREO SOBRE EL ESCENARIO & PLATAFORMAS (Requisito 2, 4)
        # =========================================================================
        if not getattr(player, "on_ground", True):
            # PLATFORM WAVELAND TECH-CHASE: Si Fox está a la altura de una plataforma aérea
            # y se desplaza hacia ella para perseguir al rival
            if (19.0 <= py <= 31.0 or 46.0 <= py <= 58.0) and getattr(player, "speed_y_self", 0) <= 0.3 and (opp_plat is not None or "DOWN" in opp_act_str):
                return self._enforce_safety({
                    "name": "⚡ PLATFORM WAVELAND: TECH-CHASE EN PLATAFORMA",
                    "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.25, "c_stick_x": 0.5, "c_stick_y": 0.5,
                    "_allow_air_shield": True, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # A) Si el rival está arriba de Fox: Up-Air (C-Up) o Platform Sharking
            if dy > 1.2 and abs(dx) < 15.0:
                if opp_plat is not None:
                    self.learn_from_success("PLATFORM_SHARK")
                    self.dopamine = min(1.0, self.dopamine + 0.40)
                    return self._enforce_safety({
                        "name": "🦈 PLATFORM SHARKING: UP-AIR A TRAVÉS DE LA PLATAFORMA",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                return self._enforce_safety({
                    "name": "🦅 INTERCEPCIÓN AÉREA: UP-AIR (C-UP)",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # B) Cayendo sobre el rival: Down-Air (Drill multihit)
            if dy < -0.8 and abs(dx) < 14.0:
                if archetype == "FLOATY" or opp_pct >= 50.0:
                    self.drill_smash_state = "DRILL_ACTIVE"
                return self._enforce_safety({
                    "name": "🌪️ DRILL AÉREO EN PICADA (DAIR)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # C) Combate aéreo cercano: Nair
            if dist < 22.0:
                return self._enforce_safety({
                    "name": "🦅 SHFFL NAIR OFENSIVO",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # D) SHDL aéreo a larga distancia (Zoning con Blaster en el aire)
            if dist > 24.0 and abs(px) < (stage_edge - 16.0):
                self.learn_from_success("SHDL")
                return self._enforce_safety({
                    "name": "🔫 SHDL: SHORT-HOP DOUBLE LASER (ZONING PROFESIONAL)",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # E) Acercamiento aéreo
            return self._enforce_safety({
                "name": "🦅 DRIFT AÉREO DE APROXIMACIÓN",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 7. TECH-CHASE & CASTIGO A RIVAL DERRIBADO (JAB-RESET Y DOWN-SMASH)
        # =========================================================================
        is_opp_knockdown = (opp_act_val in range(183, 203)) or any(k in opp_act_str for k in [
            "DOWN", "LYING", "TECH", "GROUND_ROLL"
        ])
        if is_opp_knockdown:
            habits = self.long_term_memory.get("opponent_habits", {})
            self.combo_count += 1
            self.dopamine = min(1.0, self.dopamine + 0.35)

            # A quemarropa (dist <= 6.0): Jab-Reset en frames impares, Down-Smash en pares
            if dist <= 6.0 and current_frame % 2 == 1:
                return self._enforce_safety({
                    "name": "🥊 JAB-RESET FRAME-2 (FORZAR LEVANTAMIENTO)",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # Rango medio de derribo (dist <= 15.0):
            if dist <= 15.0:
                # Si el rival está rodando activamente o tiene hábito fuerte de roll-away:
                is_rolling = (opp_act_val in [200, 201, 202]) or ("ROLL" in opp_act_str)
                if is_rolling and habits.get("tech_roll_away", 0) > habits.get("tech_roll_in", 0) + 3 and dist > 8.0:
                    return self._enforce_safety({
                        "name": "🏃 TECH-CHASE: SPRINT PREDICTIVO A FIN DE ROLL",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

                return self._enforce_safety({
                    "name": "💥 TECH-CHASE: DOWN-SMASH SEMI-SPIKE",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            else:
                return self._enforce_safety({
                    "name": "🏃 TECH-CHASE: SPRINT AL RIVAL EN EL SUELO",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 8. PRESIÓN LETAL EN EL BORDE & EDGEGUARDING (Requisito 3)
        # =========================================================================
        is_opp_on_ledge = ("EDGE_" in opp_act_str) or (opp_act_val in [252, 253])
        if opp_is_falling or opp_offstage or is_opp_on_ledge:
            edge_guard_x = (stage_edge - 10.0) if ox > 0 else -(stage_edge - 10.0)
            
            # Si el rival está colgado del borde (EDGE_HANGING):
            if is_opp_on_ledge:
                # El Down-Smash de Fox conecta debajo de la repisa y semi-spikes al abismo
                return self._enforce_safety({
                    "name": "💥 PRESIÓN EN BORDE: DOWN-SMASH SEMI-SPIKE DE REPISA",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # NUEVO: CAZA OFFSTAGE (SHINE-SPIKE & B-AIR WALL OF PAIN)
            # Si Fox tiene su salto doble disponible y está cerca del borde, salta fuera a rematar
            has_double_jump = getattr(player, "jumps_left", 0) > 0
            is_near_ledge = abs(px) > (stage_edge - 22.0)
            if has_double_jump and is_near_ledge and py >= -2.0:
                # Caso 1: Rango letal de Shine-Spike (dist <= 26.0 y oy entre -25.0 y 12.0)
                if dist <= 26.0 and abs(ox) > (stage_edge - 6.0) and -25.0 <= oy <= 12.0:
                    self.edgeguard_state = "OFFSTAGE_SHINE"
                    self.edgeguard_timer = 0
                    self.offstage_shine_frame = current_frame
                    return self._enforce_safety({
                        "name": "🦅 OFFSTAGE HUNT: SALTO HACIA EL RIVAL PARA SHINE-SPIKE",
                        "jump": bool(abs(px) > (stage_edge - 6.0) or not getattr(player, "on_ground", True)),
                        "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.65, "c_stick_x": 0.5, "c_stick_y": 0.5,
                        "_allow_offstage_chase": True, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

                # Caso 2: Rango de B-Air Wall of Pain (26.0 < dist <= 36.0 y oy >= -12.0)
                elif 26.0 < dist <= 36.0 and oy >= -12.0:
                    self.edgeguard_state = "OFFSTAGE_BAIR"
                    self.edgeguard_timer = 0
                    return self._enforce_safety({
                        "name": "🦅 OFFSTAGE B-AIR: WALL OF PAIN",
                        "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5,
                        "c_stick_x": float(1.0 - towards_opp if getattr(player, "facing", True) else towards_opp),
                        "c_stick_y": 0.5,
                        "_allow_offstage_chase": True, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # Si el rival está en el abismo recuperándose y Fox permanece en el escenario:
            if abs(px - edge_guard_x) < 8.0:
                if dist <= 16.0:
                    # Si el rival sube pegado al borde bajo el labio: F-Tilt down poke para interceptar
                    if -10.0 <= oy < 0.0 and abs(ox) > (stage_edge - 6.0):
                        return self._enforce_safety({
                            "name": "🥊 EDGEGUARD: F-TILT ANGLED DOWN (LEDGE POKE)",
                            "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                            "stick_x": float(towards_opp), "stick_y": 0.32, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)
                    # Rival cerca del borde: Down-Smash o Up-Smash
                    if current_frame % 2 == 0:
                        return self._enforce_safety({
                            "name": "💥 EDGEGUARD: DOWN-SMASH SEMI-SPIKE",
                            "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                            "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)
                    else:
                        return self._enforce_safety({
                            "name": "💥 EDGEGUARD: UP-SMASH KILL CONFIRM",
                            "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                            "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)
                else:
                    # Rival lejos fuera de escenario: Presión implacable de Láser
                    return self._enforce_safety({
                        "name": "🔫 EDGEGUARD: PRESIÓN DE LÁSER (FREE DAMAGE)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
            else:
                sx = 0.85 if edge_guard_x > px else 0.15
                return self._enforce_safety({
                    "name": "🏃 POSICIONAMIENTO EN BORDE PARA TRAP",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(sx), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 9. POWERSHIELD REFLECT & ZERO SHIELD-STUN COUNTER (FRAME-1 REFLEJO DE PROYECTIL)
        # =========================================================================
        is_projectile = any(k in opp_act_str for k in ["LASER", "BLASTER", "MISSILE", "SPECIAL_N", "SPECIAL_S", "ITEM_THROW", "PILL", "TURNIP", "CHARGE_SHOT"]) or (opp_act_val in [341, 342, 343, 344, 345, 348, 349, 350])
        is_ps_ready = (getattr(self, "powershield_state", None) == "POWERSHIELD_ACTIVE") and (current_frame - getattr(self, "powershield_frame", -100) <= 2)
        if is_ps_ready and getattr(player, "on_ground", True):
            self.powershield_state = None
            self.learn_from_success("POWERSHIELD")
            if dist <= 8.0:
                return self._enforce_safety({
                    "name": "💥 FOX POWERSHIELD COUNTER: RUNNING JC UP-SMASH",
                    "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            else:
                return self._enforce_safety({
                    "name": "⚡ FOX POWERSHIELD REFLECT: WAVEDASH ADELANTE",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        if is_projectile and getattr(player, "on_ground", True):
            self.powershield_state = "POWERSHIELD_ACTIVE"
            self.powershield_frame = current_frame
            return self._enforce_safety({
                "name": "🛡️ POWERSHIELD FRAME-1: REFLEJO DE PROYECTIL (CERO SHIELD-STUN)",
                "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                "stick_x": 0.5, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 10. COMBATE CUERPO A CUERPO CQC (dist <= 11.0 unidades) (Requisito 8: NUNCA RELAJARSE)
        # =========================================================================
        is_opp_attacking = ("ATTACK" in opp_act_str or "SWORD" in opp_act_str or "SPECIAL" in opp_act_str or opp_act_val in range(44, 75))
        is_opp_shielding = ("SHIELD" in opp_act_str or opp_act_val in [178, 179, 180, 181])
        if dist <= 11.0:
            # 1. Si el rival está en escudo: PRESIÓN DE MULTISHINE Y AGARRES
            if is_opp_shielding:
                # 20XX MULTISHINE SHIELD PRESSURE: Alternancia letal entre Shine Frame-1 y Grab
                if dist <= 7.0 and (current_frame % 3 == 0):
                    return self._enforce_safety({
                        "name": "🦊 PRESIÓN DE ESCUDO: MULTISHINE FRAME-1",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                return self._enforce_safety({
                    "name": "🤼 ROMPE-ESCUDO: GRAB INMEDIATO (Z)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": True,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 2. UP-TILT JUGGLE LADDER CONTRA FASTFALLERS A BAJO %
            if archetype == "FASTFALLER" and opp_pct < 40.0 and not is_opp_attacking:
                self.uptilt_chain_count += 1
                self.learn_from_success("UPTILT_JUGGLE")
                self.dopamine = min(1.0, self.dopamine + 0.30)
                return self._enforce_safety({
                    "name": "🥊 UP-TILT JUGGLE LADDER (FASTFALLER COMBO)",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.68, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 3. Si el rival está atacando o corriendo a agarrar a Fox:
            # INTERRUPCIÓN CON REFLECTOR SHINE FRAME-1 (¡El Shine sale en Frame 1 e interrumpe cualquier agarre!)
            if is_opp_attacking or dist <= 8.5:
                if current_frame - getattr(self, "last_shine_frame", -100) > 12:
                    self.last_shine_frame = current_frame
                    # CROUCH-CANCEL (CC) SHINE FRAME-1 COUNTER SI FOX ESTÁ A BAJO % Y RIVAL ATACANDO
                    if is_opp_attacking and getattr(player, "percent", 0.0) < 45.0:
                        self.learn_from_success("CQC_COUNTER")
                        return self._enforce_safety({
                            "name": "🦊 CQC: CROUCH-CANCEL FRAME-1 SHINE COUNTER",
                            "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                            "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)
                    return self._enforce_safety({
                        "name": "🦊 CQC: REFLECTOR SHINE FRAME-1 (ANTI-GRAB)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    # Escudo reactivo inmediato
                    return self._enforce_safety({
                        "name": "🛡️ CQC: ESCUDO REACTIVO (BLOQUEO)",
                        "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # 4. DOWN-TILT LAUNCHER A MID-% (POP-UP DIRECTO PARA UP-AIR)
            if 55.0 <= opp_pct <= 95.0 and dist <= 10.0:
                return self._enforce_safety({
                    "name": "💥 CQC: DOWN-TILT LAUNCHER (POP-UP PARA UP-AIR)",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.25, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 5. Si el rival tiene alto porcentaje (>65%): Kill confirm Up-Smash directo
            if opp_pct > 65.0:
                return self._enforce_safety({
                    "name": "💥 CQC: UP-SMASH KILL CONFIRM (C-UP)",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 6. Agarre ofensivo si combo clusters activos
            if combo_spikes > 10:
                return self._enforce_safety({
                    "name": "🤼 CQC: GRAB OFENSIVO (Z)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": True,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 7. Jab rápido Frame-2 (A)
            return self._enforce_safety({
                "name": "🥊 CQC: JAB RÁPIDO FRAME-2 (A)",
                "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 11. NEUTRAL TÁCTICO: DASH-DANCE Y ENTRADAS SEGURAS (11.0 < dist <= 24.0 u)
        # (Requisito 8: NUNCA CAMINAR EN LÍNEA RECTA DE FRENTE AL JUGADOR)
        # =========================================================================
        elif dist <= 24.0:
            if getattr(self, "laser_cooldown", 0) > 0:
                self.laser_cooldown -= 1

            # 1. PLATFORM SHARKING: Fox en suelo bajo plataforma con rival arriba
            if opp_plat is not None and abs(dx) <= 14.0 and dy >= 16.0:
                return self._enforce_safety({
                    "name": "🦈 PLATFORM SHARKING: SALTO DEBAJO DE PLATAFORMA",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 2. WHIFF PUNISH: Si el rival está atacando al aire o en lag: CASTIGO INMEDIATO CON RUNNING JC UP-SMASH
            if is_opp_attacking:
                return self._enforce_safety({
                    "name": "💥 WHIFF PUNISH: RUNNING JC UP-SMASH",
                    "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 3. KILL CONFIRM SETUP: Rival en porcentaje letal a rango de carrera
            if (opp_pct > 55.0 and dist <= 18.0) or (act_val == 21 and opp_pct > 35.0 and dist <= 17.0):
                return self._enforce_safety({
                    "name": "💥 RUNNING JC UP-SMASH",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 4. MATRIZ DE MOVIMIENTO IMPREDECIBLE 20XX (CENTRAL COMPLEX + DOPAMINA)
            # Entropía neural biológica derivada del conectoma LIF de la mosca:
            cx_spikes = int(self.spikes[self.map_cx_saccade].sum()) if hasattr(self, "map_cx_saccade") else 0
            entropy = (current_frame * 17 + cx_spikes * 7 + int(self.dopamine * 100)) % 100

            # Mixup A: WAVEDASH BACK BAIT (Provoca que rivales y bots fallen ataques para castigarlos)
            if entropy < 25 and dist <= 19.0 and abs(px) < (stage_edge - 12.0):
                return self._enforce_safety({
                    "name": "🏃 DASH-DANCE ➔ WAVEDASH BACK BAIT (WHIFF TRAP)",
                    "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                    "stick_x": float(1.0 - towards_opp), "stick_y": 0.25,
                    "_allow_air_shield": True, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # Mixup B: TOMAHAWK EMPTY HOP (Engaño de salto vacío para humillar escudos)
            if 25 <= entropy < 45 and dist <= 18.0:
                return self._enforce_safety({
                    "name": "🦅 ENTRADA AÉREA: TOMAHAWK EMPTY HOP",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # Mixup C: SHFFL NAIR CROSS-UP (Atraviesa y cae detrás del rival)
            if 45 <= entropy < 65:
                return self._enforce_safety({
                    "name": "🦅 ENTRADA SEGURA: SHFFL NAIR CROSS-UP",
                    "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # Mixup D: RUNNING JC GRAB
            if 65 <= entropy < 82:
                return self._enforce_safety({
                    "name": "🤼 ENTRADA OFENSIVA: RUNNING JC GRAB",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": True,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # Mixup E: DASH-DANCE ERRÁTICO 20XX (Velocidad adaptativa según dopamina)
            step_len = 3 if self.dopamine > 0.70 else (4 if self.dopamine > 0.50 else 6)
            is_forward_step = ((current_frame // step_len) % 2 == 0)
            dance_stick_x = towards_opp if is_forward_step else (1.0 - towards_opp)
            
            return self._enforce_safety({
                "name": f"🏃 DASH-DANCE ERRÁTICO 20XX ({'PRESION' if is_forward_step else 'AMAGO'})",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": float(dance_stick_x), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 11. DISTANCIA LARGA (dist > 24.0 u): PRESIÓN DE BLASTER, SHDL O SPRINT 20XX
        # =========================================================================
        else:
            if getattr(self, "laser_cooldown", 0) > 0:
                self.laser_cooldown -= 1

            # SHDL: Short-Hop Double Laser profesional a larga distancia (con cadencia y drift)
            if dist > 28.0 and abs(px) < (stage_edge - 16.0) and getattr(self, "laser_cooldown", 0) <= 0:
                self.learn_from_success("SHDL")
                self.laser_cooldown = 18 # Cooldown para permitir sprint veloz y no quedar atrapado en salto
                if getattr(player, "on_ground", True):
                    return self._enforce_safety({
                        "name": "🔫 SHDL: SHORT-HOP INICIAL (DOUBLE LASER)",
                        "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    return self._enforce_safety({
                        "name": "🔫 SHDL: SHORT-HOP DOUBLE LASER (ZONING PROFESIONAL)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # SPRINT AGRESIVO 20XX / CIERRE EXPLOSIVO DE DISTANCIA:
            # En lugar de caminar pasivamente, Fox utiliza su máxima aceleración de carrera
            return self._enforce_safety({
                "name": "🏃 20XX SPRINT AGRESIVO (CIERRE DE DISTANCIA)",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

    def get_luigi_decision(self, player=None, opponent=None, current_frame=0, stage="BATTLEFIELD"):
        """
        CEREBRO COMPETITIVO NIVEL SSS PARA LUIGI (Super Smash Bros Melee).
        Domina el metajuego con la tracción más resbaladiza (0.005), wavedashes legendarios,
        Frame-3 N-Air, Frame-5 Down-Smash, Frame-8 Sweetspot Up-B (Shoryuken PING!),
        caza implacable en plataformas y castigo de whiff anti-cargas.
        """
        stage_edge = BattlefieldMap.get_edge(stage)
        
        # DECODIFICACIÓN INTEGRAL DE LOS 8 CLUSTERS ANATÓMICOS (395,144 NEURONAS)
        spikes_c0_c1   = int(np.sum(self.spikes[self.map_vis_left_retina]) + np.sum(self.spikes[self.map_vis_right_retina])) if hasattr(self, "map_vis_left_retina") else 0
        spikes_c2      = int(np.sum(self.spikes[self.map_mech_hitlag]) + np.sum(self.spikes[self.map_mech_shield_stun])) if hasattr(self, "map_mech_hitlag") else 0
        spikes_c3      = int(np.sum(self.spikes[self.map_pam]) + np.sum(self.spikes[self.map_ppl1])) if hasattr(self, "map_ppl1") else int(np.sum(self.spikes[self.map_pam]))
        spikes_c4      = int(np.sum(self.spikes[self.map_attack]) + np.sum(self.spikes[self.map_special]))
        spikes_c5      = int(np.sum(self.spikes[self.map_gf]) + np.sum(self.spikes[self.map_cx_saccade]))
        spikes_c6      = int(np.sum(self.spikes[self.map_powershield]) + np.sum(self.spikes[self.map_cqc_counter])) if hasattr(self, "map_powershield") else int(np.sum(self.spikes[self.map_cqc_counter]))
        spikes_c7      = int(np.sum(self.spikes[self.map_combo]) + np.sum(self.spikes[self.map_combo_fastfaller]))
        total_spikes   = int(np.sum(self.spikes))

        stats = {
            "dopamine": float(self.dopamine),
            "octopamine": float(self.octopamine),
            "total_spikes": total_spikes,
            "neural_activation": f"{(total_spikes / max(1, self.num_neurons)) * 100:.2f}%",
            "cluster_activity": {
                "C0_C1_Visual": spikes_c0_c1,
                "C2_Mechanosensory": spikes_c2,
                "C3_Central_Complex": spikes_c3,
                "C4_VNC_Motor": spikes_c4,
                "C5_Giant_Fiber_SDI": spikes_c5,
                "C6_Precision_20XX": spikes_c6,
                "C7_Cerebellar_Combos": spikes_c7
            },
            "jump_p": int(np.sum(self.spikes[self.map_jump])),
            "attack_p": int(np.sum(self.spikes[self.map_attack])),
            "special_p": int(np.sum(self.spikes[self.map_special])),
            "shield_p": int(np.sum(self.spikes[self.map_shield])),
            "combo_p": int(np.sum(self.spikes[self.map_combo])),
            "gf_p": int(np.sum(self.spikes[self.map_gf])),
            "character": "LUIGI"
        }

        # MODO AUTÓNOMO / TEST (player is None): Decodificación directa de spikes adaptada a Luigi
        if player is None or opponent is None:
            jump_spikes    = int(np.sum(self.spikes[self.map_jump]))
            attack_spikes  = int(np.sum(self.spikes[self.map_attack]))
            special_spikes = int(np.sum(self.spikes[self.map_special]))
            shield_spikes  = int(np.sum(self.spikes[self.map_shield]))
            combo_spikes   = int(np.sum(self.spikes[self.map_combo]))
            gf_spikes      = int(np.sum(self.spikes[self.map_gf]))
            left_spikes    = int(np.sum(self.spikes[self.map_left]))
            right_spikes   = int(np.sum(self.spikes[self.map_right]))

            net_x = float(np.tanh((right_spikes - left_spikes) / 25.0))
            jump_score = jump_spikes + gf_spikes * 1.5
            attack_score = attack_spikes + (combo_spikes * 0.05)
            special_score = special_spikes * 1.2
            shield_score = shield_spikes * 1.1

            is_jump = False
            is_attack = False
            is_special = False
            is_shield = False
            action_name = "🟢 DRIFT WAVEDASH LUIGI (0.005 TRACTION)"

            max_score = max(jump_score, attack_score, special_score, shield_score, 10.0)
            if max_score > 12.0:
                if max_score == jump_score:
                    is_jump = True
                    if attack_score > 15.0:
                        is_attack = True
                        action_name = "🟢 NAIR AÉREO FRAME-3"
                    else:
                        action_name = "🦘 SALTO FLOTANTE (DNp01 / Giant Fiber)"
                elif max_score == attack_score:
                    is_attack = True
                    action_name = "💥 DOWN-SMASH FRAME-5 / JAB"
                elif max_score == special_score:
                    is_special = True
                    action_name = "🔥 BOLA DE FUEGO VERDE / SHORYUKEN"
                elif max_score == shield_score:
                    is_shield = True
                    action_name = "🛡️ ESCUDO / WAVEDASH SLIDE"

            stick_x = 0.5 + 0.48 * net_x
            return {
                "name": action_name,
                "jump": is_jump,
                "attack": is_attack,
                "special": is_special,
                "shield": is_shield,
                "grab": False,
                "stick_x": float(stick_x),
                "stick_y": 0.5,
                "c_stick_x": 0.5,
                "c_stick_y": 0.5,
                "stats": stats
            }

        px = float(player.position.x)
        py = float(player.position.y)
        ox = float(opponent.position.x)
        oy = float(opponent.position.y)
        
        dx = ox - px
        dy = oy - py
        dist = math.hypot(dx, dy)
        
        towards_opp = 1.0 if dx > 0 else 0.0
        dir_to_stage = 1.0 if px < 0 else 0.0
        
        act_str = str(player.action)
        opp_act_str = str(opponent.action)
        act_val = getattr(player.action, "value", getattr(player, "act_val", 0))
        opp_act_val = getattr(opponent.action, "value", getattr(opponent, "act_val", 0))
        opp_offstage = getattr(opponent, "off_stage", False) or (abs(ox) >= (stage_edge - 1.0) and oy < 1.0) or ("EDGE" in opp_act_str) or (opp_act_val in [252, 253])
        opp_char = getattr(opponent, "character", None)
        archetype = BattlefieldMap.get_character_archetype(opp_char)
        self.combo_archetype = archetype
        opp_plat = BattlefieldMap.is_on_platform(ox, oy)
        luigi_plat = BattlefieldMap.is_on_platform(px, py)
        luigi_on_plat = (luigi_plat is not None) or (getattr(player, "on_ground", True) and py >= 18.0)
        opp_on_plat = (opp_plat is not None) or (getattr(opponent, "on_ground", True) and oy >= 18.0)
        
        self.prev_dist_fox = dist
        opp_is_falling = BattlefieldMap.is_opponent_falling(ox, oy, getattr(opponent, "on_ground", True), opp_offstage, stage_edge=stage_edge)

        # Si pasaron más de 6 frames desde que se inició un salto, expirar la acción aérea en cola
        if current_frame - getattr(self, "luigi_jump_frame", current_frame) > 6:
            self.luigi_jump_action = None
        # Si pasaron más de 25 frames desde que se inició la carga de misil, resetear carga
        if current_frame - getattr(self, "missile_charge_frame", current_frame) > 25:
            self.missile_charge_timer = 0

        # ENTRENAMIENTO DE MEMORIA EN TIEMPO REAL (Frame-by-frame STDP)
        self.realtime_memory_train(player, opponent, current_frame=current_frame)
        habits = self.long_term_memory.get("opponent_habits", {})

        # =========================================================================
        # 0. ESTADOS DE RESPAWN (HALO PLATFORM) & SWAGGER LUIGI 20XX
        # =========================================================================
        is_on_halo = (act_val in [12, 13]) or ("HALO" in act_str)
        if is_on_halo:
            return {
                "name": "⚡ BAJANDO DE PLATAFORMA DE RESPAWN",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": float(dir_to_stage), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }

        opp_on_halo = (opp_act_val in [12, 13]) or ("HALO" in opp_act_str)
        if opp_on_halo and getattr(player, "on_ground", True) and abs(px) < (stage_edge - 14.0):
            # SWAGGER LUIGI 20XX: Alternar Disrespect Taunt y Wavedash Dance
            if (current_frame // 35) % 2 == 0 and self.dopamine > 0.50:
                return self._enforce_safety({
                    "name": "👟 DISRESPECT EN RESPAWN: LUIGI TAUNT (HUMILLACIÓN MENTAL)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False, "taunt": True,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            dance_x = 1.0 if (current_frame // 4) % 2 == 0 else 0.0
            return self._enforce_safety({
                "name": "🟢 SWAGGER LUIGI 20XX: WAVEDASH DE DOMINANCIA EN CENTRO",
                "jump": False, "attack": False, "special": False, "shield": (current_frame % 4 == 0), "grab": False, "taunt": False,
                "stick_x": float(dance_x), "stick_y": 0.25 if (current_frame % 4 == 0) else 0.5,
                "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # HUMILLACIÓN 20XX: Disrespect a rival cayendo al abismo sin retorno
        opp_pct = float(getattr(opponent, "percent", 0.0))
        if opp_offstage and oy < -10.0 and opp_pct >= 55.0 and getattr(player, "on_ground", True) and abs(px) < (stage_edge - 12.0):
            teabag_y = 0.0 if (current_frame % 4 < 2) else 0.5
            teabag_taunt = (current_frame % 20 == 0) and self.dopamine > 0.60
            return self._enforce_safety({
                "name": "👟 HUMILLACIÓN 20XX: RAPID TEABAG DISRESPECT (SPAM ABAJO)",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False, "taunt": teabag_taunt,
                "stick_x": 0.5, "stick_y": teabag_y, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # Detección de repisa y offstage para todo el árbol de decisiones
        is_on_ledge = act_val in [252, 253] or any(k in act_str for k in ["EDGE_CATCHING", "EDGE_HANGING"])
        is_offstage = is_on_ledge or ((not getattr(player, "on_ground", True)) and (
            abs(px) >= (stage_edge - 2.0) or py < -0.8
        ))

        # =========================================================================
        # 1. HITSTUN, DAÑO, TUMBLE & FRAME-3 N-AIR BREAK-OUT
        # =========================================================================
        hitstun_left = getattr(player, "hitstun_frames_left", 0)
        is_in_hitstun = hitstun_left > 0 or ("DAMAGE" in act_str and "AIR" in act_str) or (act_val in range(75, 92))
        is_tumbling = (act_val == 38) or ("TUMBL" in act_str)

        if is_in_hitstun:
            asdi_y = 0.0 if (py <= 8.5 and getattr(player, "percent", 0.0) < 80.0) else 0.5
            sdi_cycle = current_frame % 2
            sdi_x = float(dir_to_stage) if sdi_cycle == 0 else 0.5
            sdi_y = 0.85 if sdi_cycle == 0 else 0.15
            return self._enforce_safety({
                "name": "🛡️ SURVIVAL DI + SDI CUÁNTICO 20XX HACIA EL ESCENARIO",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": float(sdi_x), "stick_y": float(sdi_y), "c_stick_x": 0.5, "c_stick_y": float(asdi_y), "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # Luigi capturado en agarre por el rival: Mash-out 20XX a 60 inputs/segundo
        is_captured = (act_val in range(223, 230)) or ("CAPTURE" in act_str)
        if is_captured:
            mash_cycle = current_frame % 4
            mash_x = 0.0 if mash_cycle in [0, 1] else 1.0
            mash_y = 0.85 if mash_cycle in [1, 2] else 0.15
            mash_btn_a = (mash_cycle % 2 == 0)
            mash_btn_b = (mash_cycle % 2 == 1)
            return self._enforce_safety({
                "name": "⚡ MASH-OUT ESCAPE 20XX: ZAFARSE DEL AGARRE A VELOCIDAD RÉCORD",
                "jump": (mash_cycle == 0),
                "attack": mash_btn_a,
                "special": mash_btn_b,
                "shield": False,
                "grab": False,
                "stick_x": float(mash_x),
                "stick_y": float(mash_y),
                "c_stick_x": 0.5,
                "c_stick_y": 0.5,
                "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        is_being_thrown = (act_val in range(230, 234)) or ("THROWN" in act_str)
        if is_being_thrown:
            return self._enforce_safety({
                "name": "🛡️ SURVIVAL DI AL LANZAMIENTO HACIA EL ESCENARIO",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": float(dir_to_stage), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        if is_tumbling:
            if is_offstage:
                if getattr(player, "jumps_left", 0) > 0:
                    return {
                        "name": "🪰 SALTO DOBLE SALVAVIDAS: ESCAPE DE TUMBLE OFFSTAGE",
                        "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(dir_to_stage), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }
                else:
                    # En Melee, los movimientos especiales (botón B) están BLOQUEADOS durante TUMBLE.
                    # Presionar Up-B o Cyclone en TUMBLE es ignorado y causa que el personaje caiga al abismo.
                    # Wiggle-out: alternar el stick horizontalmente cancela TUMBLE a FALL en 1 frame,
                    # desbloqueando inmediatamente los poderes de recuperación (Up-B / Cyclone) en el siguiente frame.
                    wiggle_x = float(dir_to_stage) if (current_frame % 2 == 0) else (1.0 - float(dir_to_stage))
                    return {
                        "name": "⚡ WIGGLE-OUT ESCAPE DE TUMBLE OFFSTAGE (DESBLOQUEO DE PODERES)",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(wiggle_x), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }
            else:
                is_landing_surface = (py <= 7.0) or (24.0 <= py <= 32.0) or (50.0 <= py <= 60.0) or (BattlefieldMap.is_on_platform(px, py - 3.0) is not None)
                if is_landing_surface and getattr(player, "speed_y_self", 0) < -0.15 and abs(px) <= (stage_edge - 4.0):
                    return self._enforce_safety({
                        "name": "🛡️ TECH PERFECTO EN EL SUELO (L)",
                        "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                        "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5,
                        "_allow_air_shield": True, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                return self._enforce_safety({
                    "name": "🟢 NAIR AÉREO FRAME-3: CANCELAR TUMBLE / ESCAPE DE COMBO",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        if "DOWN_BOUND" in act_str or "LYING" in act_str or "DOWN_WAIT" in act_str or (act_val in range(183, 195)):
            return self._enforce_safety({
                "name": "🏃 GETUP ROLL HACIA EL CENTRO",
                "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 2. RECUPERACIÓN OFFSTAGE DE LUIGI (RISING CYCLONE & ANTI-CHOQUE INFERIOR)
        # =========================================================================
        if is_offstage:
            is_under_stage = (abs(px) < (stage_edge - 1.5)) and (py < -4.0)
            
            # Subida de repisa invulnerable
            if is_on_ledge:
                dist_to_opp = math.hypot(ox - px, oy - py)
                if dist_to_opp <= 14.0 or (ox * px > 0 and abs(ox) > (stage_edge - 15.0)):
                    self.luigi_ledge_state = None
                    return {
                        "name": "⚡ SUBIDA INVULNERABLE: LEDGE ROLL (ATRAVESAR AL RIVAL)",
                        "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                        "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }
                if getattr(self, "luigi_ledge_state", None) == "LEDGEDASH_AIR":
                    self.luigi_ledge_state = None
                    return {
                        "name": "⚡ LEDGEDASH LUIGI: WAVELAND INVENCIBLE EN ESCENARIO (0.005 TRACTION)",
                        "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                        "stick_x": float(dir_to_stage), "stick_y": 0.25, "c_stick_x": 0.5, "c_stick_y": 0.5,
                        "_allow_air_shield": True, "stats": stats
                    }
                else:
                    self.luigi_ledge_state = "LEDGEDASH_AIR"
                    return {
                        "name": "⚡ LEDGEDASH LUIGI: SUBIDA CON WAVEDASH DESLIZANTE",
                        "jump": True, "attack": False, "special": False, "shield": True, "grab": False,
                        "stick_x": float(dir_to_stage), "stick_y": 0.25, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }

            # Si Luigi está DEBAJO de la plataforma: CURVAR HACIA AFUERA
            if is_under_stage:
                outward_dir = 1.0 if px >= 0.0 else 0.0
                if getattr(player, "jumps_left", 0) > 0:
                    return {
                        "name": "🟢 SALTO DOBLE SALVAVIDAS: EVASIÓN DEBAJO DE LA PLATAFORMA",
                        "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(outward_dir), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }
                return {
                    "name": "🌪️ ESCAPE DEBAJO DEL ESCENARIO: CYCLONE / MISSILE EXTERIOR",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": float(outward_dir), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # A) Special Fall (FALL_SPECIAL - Acciones 35, 36, 37):
            # Luigi ya usó Up-B o Airdodge y está en caída libre especial. Solo puede hacer Air Drift.
            is_special_fall = (act_val in [35, 36, 37]) or any(k in act_str for k in ["FALL_SPECIAL", "SPECIAL_FALL"])
            if is_special_fall:
                return {
                    "name": "🪰 AIR DRIFT HACIA EL ESCENARIO (SPECIAL FALL)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # B) Acciones especiales y saltos en ejecución activa
            # B.1) Up-B Super Jump Punch activo (362, 363 o SPECIAL_HI)
            if (act_val in [362, 363]) or any(k in act_str for k in ["SPECIAL_HI", "SUPER_JUMP_PUNCH"]):
                return {
                    "name": "🟢 SUPER JUMP PUNCH ACTIVO: APUNTANDO A LA REPISA",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # B.2) Luigi Cyclone activo en el aire (364, 365 o CYCLONE)
            if (act_val in [364, 365]) or any(k in act_str for k in ["SPECIAL_LW", "CYCLONE"]):
                mash_b = (current_frame % 2 == 0)
                drift_x = 0.65 if dir_to_stage > 0.5 else 0.35
                return {
                    "name": "🌪️ RISING LUIGI CYCLONE: MASHING B ACTIVO",
                    "jump": False, "attack": False, "special": bool(mash_b), "shield": False, "grab": False,
                    "stick_x": float(drift_x), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # B.3) Green Missile en vuelo (347-350 o MISSILE)
            if (act_val in range(347, 351)) or any(k in act_str for k in ["SPECIAL_S", "MISSILE"]):
                return {
                    "name": "🚀 GREEN MISSILE EN VUELO: DIRECCIÓN AL ESCENARIO",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # B.4) Salto doble aéreo en progreso (Acciones 27, 28 o JUMP_AERIAL)
            # ¡CRUCIAL! NUNCA interrumpir prematuramente el ascenso del doble salto con Up-B.
            # Se debe permitir que Luigi aproveche toda la enorme flotabilidad vertical de su salto.
            if (act_val in [27, 28]) or ("JUMP_AERIAL" in act_str):
                return {
                    "name": "🪰 ASCENSO DE SALTO DOBLE FLOTANTE AL ESCENARIO",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # C) PRIORIDAD 1: SALTO DOBLE FLOTANTE DISPONIBLE
            # En Melee, el salto flotante de Luigi es enorme y seguro. Usar SIEMPRE primero para ascender.
            if getattr(player, "jumps_left", 0) > 0:
                return {
                    "name": "🪰 SALTO DOBLE FLOTANTE HACIA EL ESCENARIO (PRIORIDAD SALVAVIDAS)",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # D) DOBLE SALTO YA GASTADO (jumps_left == 0):
            # D.1) Snap de Airdodge direccional a la repisa:
            # ÚNICAMENTE permitido si está inmediatamente adyacente a la repisa para evitar Freefall suicida:
            if (stage_edge - 2.0 <= abs(px) <= stage_edge + 6.0) and (-3.0 <= py <= 3.0):
                return {
                    "name": "⚡ AIRDODGE DIRECCIONAL: SNAP INSTANTÁNEO A LA REPISA",
                    "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.70, "c_stick_x": 0.5, "c_stick_y": 0.5,
                    "_allow_air_shield": True, "stats": stats
                }

            # D.2) Rango de sweetspot de repisa: SUPER JUMP PUNCH (UP-B)
            if (-28.0 <= py <= 4.0) and abs(px) <= (stage_edge + 16.0):
                return {
                    "name": "🟢 SUPER JUMP PUNCH: SWEETSPOT A LA REPISA (UP-B)",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.90, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # D.3) Distancia horizontal lejana: RISING CYCLONE (DOWN-B) CON MASHING Y AIR DRIFT
            # En Melee, el Cyclone no induce FALL_SPECIAL (freefall) y puede mashearse para ganar altura y retorno seguro
            if abs(px) > (stage_edge + 14.0) and py > -22.0:
                return {
                    "name": "🌪️ RISING LUIGI CYCLONE: MASHING DOWN-B DE RETORNO",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False, "taunt": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }

            # D.4) Fallback seguro: Air Drift hacia el escenario (NUNCA airdodge suicida)
            return {
                "name": "🪰 AIR DRIFT HACIA EL ESCENARIO (RECOVERY DRIFT)",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }

        # =========================================================================
        # 3. L-CANCEL & PLATFORM EDGE-CANCEL SLIDE A CERO FRAMES DE LAG
        # =========================================================================
        if any(aerial in act_str for aerial in ["NAIR", "DAIR", "UAIR", "BAIR", "FAIR"]) or (act_val in [65, 66, 67, 68, 69]):
            is_on_plat_landing = BattlefieldMap.is_on_platform(px, py - 3.0, stage)
            is_near_landing = (0.0 <= py <= 8.5) or (22.0 <= py <= 32.0) or (48.0 <= py <= 60.0) or (is_on_plat_landing is not None)
            
            # PLATFORM EDGE-CANCEL SLIDE: Si aterriza en el borde exacto de una plataforma con inercia:
            h_speed = max(abs(getattr(player, "speed_ground_x_self", 0.0)), abs(getattr(player, "speed_air_x_self", 0.0)))
            is_near_plat_edge = False
            if is_on_plat_landing and h_speed > 0.40:
                if abs(abs(px) - 19.5) < 3.5 or abs(abs(px) - 58.0) < 3.5 or abs(abs(px) - 19.0) < 3.5:
                    is_near_plat_edge = True

            if is_near_plat_edge:
                return self._enforce_safety({
                    "name": "⚡ PLATFORM EDGE-CANCEL: CANCELACIÓN A CERO FRAMES DE LAG",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            if is_near_landing and getattr(player, "speed_y_self", 0) < -0.15:
                return self._enforce_safety({
                    "name": "⚡ L-CANCEL PERFECTO (L)",
                    "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5,
                    "_allow_air_shield": True, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 4. ESCUDO INTELIGENTE Y OPCIONES OUT OF SHIELD (OOS)
        # =========================================================================
        is_shielding = (act_val in [178, 179, 180, 181]) or ("SHIELD" in act_str)
        shield_hp = getattr(player, "shield_strength", 60.0)

        if is_shielding:
            self.shield_frames += 1
            if shield_hp < 26.0:
                self.shield_frames = 0
                return self._enforce_safety({
                    "name": "🛡️ ESCUDO: ROLL DE EMERGENCIA (ANTI-BREAK)",
                    "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # A2) SHIELD DROP 20XX: Si Luigi está en escudo sobre una plataforma y el rival está abajo
            luigi_plat = BattlefieldMap.is_on_platform(px, py, stage)
            if luigi_plat and (oy < py - 3.5):
                self.shield_frames = 0
                self.learn_from_success("SHIELD_DROP")
                return self._enforce_safety({
                    "name": "🛡️ SHIELD DROP 20XX: DESCENSO INSTANTÁNEO ➔ COUNTER AÉREO",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.28, "c_stick_x": 0.5, "c_stick_y": 0.0,
                    "_allow_drop_through": True, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            if dist <= 16.0:
                opp_pct = float(getattr(opponent, "percent", 0.0))
                # 1. SWEETSPOT UP-B SHORYUKEN DE FUEGO OUT OF SHIELD: Si el rival está a quemarropa y % alto o buena dopamina
                if dist <= 5.0 and (opp_pct >= 35.0 or self.dopamine > 0.55):
                    self.shield_frames = 0
                    self.last_luigi_power = "UPB_SHORYUKEN"
                    return self._enforce_safety({
                        "name": "💥 SWEETSPOT UP-B SHORYUKEN OUT OF SHIELD (FRAME-8 KILL CONFIRM)",
                        "jump": True, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

                # 2. RETIRADA EXPLOSIVA: GREEN MISSILE TORPEDO OOS DEFENSIVO
                # Si Luigi está acorralado cerca de la repisa y en escudo bajo presión, lanza un torpedo de escape hacia el centro
                is_cornered_in_shield = (abs(px) > (stage_edge - 18.0)) and (px * (ox - px) < 0)
                if is_cornered_in_shield and dist <= 16.0:
                    self.shield_frames = 0
                    self._start_missile_charge(current_frame, target_dir=dir_to_stage, max_charge=8, is_defensive=True)
                    return self._enforce_safety({
                        "name": "🚀 RETIRADA EXPLOSIVA: GREEN MISSILE TORPEDO OOS (ESCAPE DEFENSIVO)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

                # 3. FRAME-3 N-AIR OUT OF SHIELD (Combo breaker insuperable de Luigi)
                is_opp_attacking_shield = ("ATTACK" in opp_act_str or "SPECIAL" in opp_act_str or opp_act_val in range(44, 75))
                if dist <= 7.0 or is_opp_attacking_shield:
                    return self._enforce_safety({
                        "name": "🟢 N-AIR OUT OF SHIELD FRAME-3 (COMBO BREAKER)",
                        "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

                # 4. WAVEDASH OUT OF SHIELD (WD OOS): DESLIZAMIENTO DE CASTIGO / ESPACIADO (7.0 < dist <= 16.0)
                self.shield_frames = 0
                self.luigi_jump_action = "WAVEDASH"
                self.luigi_jump_frame = current_frame
                wd_dir = towards_opp if self.dopamine > 0.45 else (1.0 - towards_opp)
                self.luigi_wd_dir = wd_dir
                return self._enforce_safety({
                    "name": "⚡ WAVEDASH OUT OF SHIELD (WD OOS): DESLIZAMIENTO DE CASTIGO",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(wd_dir), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            if dist > 18.0 or self.shield_frames > 25:
                self.shield_frames = 0
                return self._enforce_safety({
                    "name": "🛡️ SOLTAR ESCUDO (REPOSICIONAMIENTO)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
        else:
            self.shield_frames = 0

        # =========================================================================
        # 5. AGARRES Y MÁQUINA DE COMBOS ESTRATIFICADA POR DOPAMINA (Requisito 3)
        # =========================================================================
        is_grabbing = any(k in act_str for k in ["GRAB_WAIT", "GRAB_PULLING", "GRAB_RUNNING_PULLING", "GRAB_PULL", "GRAB_PUMMEL"]) or (act_val in [213, 214, 215, 216, 226])
        is_throw_down = ("THROW_DOWN" in act_str) or (act_val == 222)
        opp_pct = float(getattr(opponent, "percent", 0.0))

        if is_grabbing:
            is_near_edge = abs(px) > (stage_edge - 16.0)
            edge_dir = 1.0 if px > 0 else 0.0
            is_facing_edge = (px > 0 and towards_opp > 0.5) or (px < 0 and towards_opp < 0.5)

            # DECISIÓN SITUACIONAL 20XX: ¿GOLPEA (PUMMEL) O AVIENTA (THROW)?
            # 1. Al borde del escenario (Edge Zone):
            #    - Si el rival tiene bajo/medio daño (<60%): AVIENTA DE INMEDIATO al abismo (0 pummels)
            #      para evitar zafadas de mash-out sobre la plataforma.
            #    - Si tiene daño alto (>=60%): 1 pummel rápido de ventaja y avienta fuera.
            # 2. Al centro del escenario:
            #    - Si tiene muy poco daño (<20%): Avienta de inmediato a Down-Throw combo sin regalar mash-out.
            #    - A daño medio (20% <= % < 55%): Golpea 2 pummels antes de aventar.
            #    - A daño medio-alto (55% <= % < 95%): Golpea 3 pummels (cumple Test 56 con 70%).
            #    - A daño crítico (>= 95%): Golpea hasta 4 pummels para exprimir 12% extra.
            if is_near_edge:
                max_pummels = 0 if opp_pct < 60.0 else 1
            elif opp_pct < 20.0:
                max_pummels = 0
            elif opp_pct < 55.0:
                max_pummels = 2
            elif opp_pct < 95.0:
                max_pummels = 3
            else:
                max_pummels = 4

            curr_pummels = getattr(self, "grab_pummel_count", 0)

            # A) FASE GOLPEAR (PUMMEL CON BOTÓN A):
            if curr_pummels < max_pummels:
                if act_val in [213, 215, 216, 226] or "WAIT" in act_str or "PULL" in act_str:
                    self.grab_pummel_count = curr_pummels + 1
                    self.dopamine = min(1.0, self.dopamine + 0.10)
                    self.learn_from_success("PUMMEL")
                    return self._enforce_safety({
                        "name": f"🥊 PUMMEL EN AGARRE ({self.grab_pummel_count}/{max_pummels}) [BOTÓN A]",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif act_val == 214 or "PUMMEL" in act_str:
                    # En animación activa de pummel: esperar a que termine el impacto
                    return self._enforce_safety({
                        "name": f"🥊 ANIMACIÓN PUMMEL EN CURSO ({curr_pummels}/{max_pummels})",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # B) FASE AVENTAR (LANZAMIENTO SITUACIONAL):
            self.grab_pummel_count = 0
            if is_near_edge:
                # Lanzar directamente fuera del escenario hacia el abismo:
                if is_facing_edge:
                    return self._enforce_safety({
                        "name": "🤼 FORWARD-THROW AL ABISMO (EDGEGUARD SETUP)",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    return self._enforce_safety({
                        "name": "🤼 BACK-THROW AL ABISMO (EDGEGUARD SETUP)",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(1.0 - towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
            else:
                self.combo_state = "LUIGI_DTHROW_COMBO"
                self.combo_timer = 0
                return self._enforce_safety({
                    "name": "🤼 LUIGI D-THROW: INICIADOR SUPREMO DE COMBOS",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
        else:
            self.grab_pummel_count = 0

        # MÁQUINA DE COMBOS MODULADA POR DOPAMINA TRAS DOWN-THROW:
        if self.combo_state == "LUIGI_DTHROW_COMBO" or is_throw_down:
            self.combo_timer += 1
            if getattr(player, "on_ground", True):
                # CHAINGRAB 20XX CONTRA FASTFALLERS (FOX, FALCO, FALCON) A BAJO % (<45%)
                ff_punish = self.get_plasticity("fastfaller_punish", 1.60)
                if archetype == "FASTFALLER" and opp_pct < 45.0 and dist <= 14.0 and getattr(self, "chaingrab_count", 0) < 3:
                    self.chaingrab_count = getattr(self, "chaingrab_count", 0) + 1
                    self.combo_count += 1
                    self.dopamine = min(1.0, self.dopamine + 0.25)
                    self.learn_from_success("GRAB_COMBO")
                    return self._enforce_safety({
                        "name": f"🤼 CHAINGRAB 20XX: WAVEDASH ADELANTE ➔ REGRAB (FASTFALLER TRAP {self.chaingrab_count}/3)",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": True,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

                combo_mastery = self.get_plasticity("combo_mastery", 1.40)
                # TIER 3: DOPAMINA ALTA (>0.75) O ALTA MAESTRÍA APRENDIDA -> THE LEGENDARY SHORYUKEN (SWEETSPOT UP-B)
                can_shoryuken = (self.dopamine > 0.75 and (45.0 <= opp_pct <= 115.0) and dist <= 6.5) or \
                                (combo_mastery >= 2.0 and self.dopamine >= 0.50 and (65.0 <= opp_pct <= 135.0) and dist <= 6.5)
                if can_shoryuken:
                    self.combo_state = None
                    self.combo_count += 3
                    self.dopamine = 1.0
                    self.last_luigi_power = "UPB_SHORYUKEN"
                    self.learn_from_success("KO")
                    return self._enforce_safety({
                        "name": "💥 COMBO SUPREMO SHORYUKEN: D-THROW ➔ SWEETSPOT UP-B KILL CONFIRM (PING!)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

                # TIER 2: DOPAMINA MEDIA (0.50 - 0.75) -> D-THROW TO SHORT-HOP FAIR / UAIR
                elif self.dopamine >= 0.50:
                    if opp_pct < 45.0:
                        self.luigi_jump_action = "AERIAL_FAIR"
                        return self._enforce_safety({
                            "name": "🦅 COMBO MID-DOPAMINA: D-THROW ➔ SHORT-HOP FAIR (CHOP)",
                            "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                            "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": float(towards_opp), "c_stick_y": 0.5, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)
                    else:
                        return self._enforce_safety({
                            "name": "🥊 COMBO MID-DOPAMINA: D-THROW ➔ UP-TILT JUGGLE LADDER",
                            "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                            "stick_x": float(towards_opp), "stick_y": 0.68, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)

                # TIER 1: DOPAMINA BAJA (<0.50) -> BREAD & BUTTER D-THROW TO DOWN-SMASH
                else:
                    return self._enforce_safety({
                        "name": "💥 COMBO LOW-DOPAMINA: D-THROW ➔ DOWN-SMASH FRAME-5",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            if self.combo_timer > 45:
                self.combo_state = None

        # JUMPSQUAT DE LUIGI (4 frames en KNEE_BEND / Action 24):
        is_jumpsquat = ("KNEE_BEND" in act_str) or (act_val == 24)
        if is_jumpsquat:
            jump_intent = getattr(self, "luigi_jump_action", None)
            if jump_intent in ["WAVEDASH", "WAVEDASH_BACK"]:
                wd_dir = getattr(self, "luigi_wd_dir", towards_opp)
                # Durante KNEE_BEND en el suelo: Luigi prepara el ángulo diagonal con el stick
                # SIN presionar escudo aún (presionar escudo en el suelo NO genera airdodge).
                # Se preserva luigi_jump_action para ejecutar el airdodge en el primer frame en el aire (frame 5).
                return self._enforce_safety({
                    "name": "⚡ JUMPSQUAT PREPARANDO WAVEDASH (4 FRAMES)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(wd_dir), "stick_y": 0.25, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            else:
                # DESPEGUE AÉREO: Luigi salta limpiamente hacia el aire para ejecutar su ataque aéreo
                # No activa escudo ni down-smash: permite un despegue limpio al combate aéreo
                jump_intent_name = jump_intent or "AERIAL_HUNT"
                return self._enforce_safety({
                    "name": f"🦘 DESPEGUE AÉREO: ELEVACIÓN AL COMBATE ({jump_intent_name})",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 5.5. COMBATE AÉREO OFENSIVO DE LUIGI (Luigi en el aire sobre el escenario)
        # =========================================================================
        if not getattr(player, "on_ground", True) and not is_offstage:
            # Si Luigi está aterrizando (LANDING): limpiar cualquier acción de despegue previa
            if "LAND" in act_str or act_val in [42, 43]:
                self.luigi_jump_action = None

            # 1. ASALTO EN PLATAFORMA: Si está a rango cuerpo a cuerpo del rival en plataforma (dist <= 6.5)
            if opp_plat is not None and dist <= 6.5:
                self.luigi_jump_action = None
                return self._enforce_safety({
                    "name": "💥 ASALTO EN PLATAFORMA: DOWN-SMASH SEMI-SPIKE",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 0. BUFFERED AERIAL ATTACK / WAVEDASH EXECUTION (Si venía de un despegue aéreo o jumpsquat)
            jump_act = getattr(self, "luigi_jump_action", None)
            if jump_act:
                self.luigi_jump_action = None
                if jump_act in ["WAVEDASH", "WAVEDASH_BACK"]:
                    wd_dir = getattr(self, "luigi_wd_dir", towards_opp)
                    return self._enforce_safety({
                        "name": "⚡ WAVEDASH DESLIZANTE: AIRDODGE DIAGONAL (0.005 TRACTION)",
                        "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                        "stick_x": float(wd_dir), "stick_y": 0.25, "_allow_air_shield": True, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif jump_act == "AERIAL_NAIR":
                    return self._enforce_safety({
                        "name": "🟢 N-AIR OFENSIVO FRAME-3: IMPACTO EN EL AIRE",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif jump_act == "AERIAL_FAIR":
                    return self._enforce_safety({
                        "name": "🦅 F-AIR CHOP: IMPACTO EN EL AIRE",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": float(towards_opp), "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif jump_act == "AERIAL_UAIR":
                    return self._enforce_safety({
                        "name": "🦈 UP-AIR PLATFORM SHARKING: IMPACTO EN EL AIRE",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif jump_act == "AERIAL_DAIR":
                    return self._enforce_safety({
                        "name": "🌪️ D-AIR DRILL MULTIHIT: PICADA EN EL AIRE",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif jump_act == "AERIAL_CYCLONE":
                    return self._enforce_safety({
                        "name": "🌪️ AERIAL LUIGI CYCLONE: VORTEX MULTIHIT",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif jump_act == "AERIAL_UPB":
                    return self._enforce_safety({
                        "name": "🦅 UP-AIR VERTICAL JUGGLE: VOLTERETA EN EL AIRE",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif jump_act == "PLATFORM_INVASION":
                    return self._enforce_safety({
                        "name": "🟢 N-AIR OFENSIVO FRAME-3: INVASIÓN DE PLATAFORMA",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # PLATFORM WAVELAND: Si está a la altura de una plataforma, aterrizar deslizándose
            if (19.0 <= py <= 31.0 or 46.0 <= py <= 58.0) and getattr(player, "speed_y_self", 0) <= 0.3 and opp_plat is not None:
                return self._enforce_safety({
                    "name": "⚡ PLATFORM WAVELAND: DESLIZAMIENTO EN PLATAFORMA",
                    "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.25, "c_stick_x": 0.5, "c_stick_y": 0.5,
                    "_allow_air_shield": True, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 1.5. CAZA OFFSTAGE AGRESIVA (DEEP METEOR SPIKE DESDE EL AIRE)
            offstage_aggro = self.get_plasticity("offstage_aggression", 1.50)
            has_double_jump = getattr(player, "jumps_left", 0) > 0
            is_near_ledge = abs(px) > (stage_edge - 22.0)
            if (opp_offstage or opp_is_falling or abs(ox) > (stage_edge - 6.0)) and has_double_jump and is_near_ledge and py >= -6.0 and (self.dopamine > 0.65 or offstage_aggro >= 1.40):
                max_chase = 24.0 * min(1.5, max(1.0, offstage_aggro / 1.45))
                if dist <= max_chase:
                    return self._enforce_safety({
                        "name": "🌪️ OFFSTAGE HUNT: D-AIR METEOR SPIKE (DEPOT)",
                        "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.0,
                        "_allow_offstage_chase": True, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # 2. RIVAL EN EL AIRE DIRECTAMENTE ARRIBA (dy > 1.2, |dx| <= 12.0)
            if dy > 1.2 and abs(dx) <= 12.0:
                return self._enforce_safety({
                    "name": "🦅 UP-AIR VERTICAL JUGGLE (VOLTERETA EN EL AIRE)",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 3. CAYENDO O ATACANDO DESDE ARRIBA DEL RIVAL (dy < -0.5 / py > oy)
            if dy < -0.5:
                # A) Directamente o muy cerca por encima (|dx| <= 12.0)
                if abs(dx) <= 12.0:
                    # Alternancia táctica letal: D-Air Drill multihit y N-Air Frame-3 ambos con FAST-FALL (stick_y: 0.0)
                    if (current_frame % 2 == 0) or (self.dopamine > 0.60 and dist <= 9.0):
                        return self._enforce_safety({
                            "name": "🌪️ D-AIR DRILL MULTIHIT: PICADA EN HELICÓPTERO",
                            "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                            "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)
                    else:
                        return self._enforce_safety({
                            "name": "🟢 N-AIR DESCENDENTE FRAME-3: PICADA AGRESIVA FAST-FALL",
                            "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                            "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)

                # B) En picada diagonal hacia el rival (12.0 < |dx| <= 22.0)
                elif abs(dx) <= 22.0:
                    is_facing_opp = (dx > 0 and getattr(player, "facing", True)) or (dx < 0 and not getattr(player, "facing", True))
                    if not is_facing_opp and current_frame % 3 != 0:
                        bair_dir = 0.0 if getattr(player, "facing", True) else 1.0
                        return self._enforce_safety({
                            "name": "🦅 B-AIR DE PRECISIÓN DESCENDENTE: PATADA TRASERA AL RIVAL ABAJO",
                            "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                            "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": float(bair_dir), "c_stick_y": 0.5, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)
                    elif current_frame % 2 == 0:
                        return self._enforce_safety({
                            "name": "🦅 F-AIR CHOP DESCENDENTE: GOLPE DE KARATE AL RIVAL ABAJO",
                            "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                            "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": float(towards_opp), "c_stick_y": 0.5, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)
                    else:
                        return self._enforce_safety({
                            "name": "🌪️ D-AIR DRILL MULTIHIT: PICADA EN HELICÓPTERO",
                            "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                            "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                        }, player, opponent, stage_edge=stage_edge)

                # C) A mayor distancia horizontal (|dx| > 22.0) pero por encima: picada agresiva de avance
                else:
                    return self._enforce_safety({
                        "name": "🦅 ASALTO AÉREO EN PICADA: F-AIR / N-AIR AVANZANDO DESDE ARRIBA",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.15, "c_stick_x": float(towards_opp), "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # 4. COMBATE AÉREO A LA MISMA ALTURA O CERCANO (dist <= 16.0 u)
            if dist <= 16.0:
                is_facing_opp = (dx > 0 and getattr(player, "facing", True)) or (dx < 0 and not getattr(player, "facing", True))
                if not is_facing_opp and current_frame % 3 != 0:
                    bair_dir = 0.0 if getattr(player, "facing", True) else 1.0
                    return self._enforce_safety({
                        "name": "🦅 B-AIR DE PRECISIÓN: PATADA TRASERA DE MULA",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": float(bair_dir), "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

                if current_frame % 2 == 0 or self.dopamine > 0.70:
                    return self._enforce_safety({
                        "name": "🟢 N-AIR OFENSIVO FRAME-3: PATADA DIVINA EN EL AIRE",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    return self._enforce_safety({
                        "name": "🦅 F-AIR CHOP: GOLPE DE KARATE AÉREO",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": float(towards_opp), "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # 5. APROXIMACIÓN AÉREA HACIA EL RIVAL (dist > 16.0 u)
            return self._enforce_safety({
                "name": "🦅 DRIFT AÉREO DE APROXIMACIÓN HACIA EL RIVAL",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 5.6. DESCENSO Y DROP-THROUGH DE PLATAFORMA (LUIGI EN PLATAFORMA Y RIVAL ABAJO)
        # =========================================================================
        if luigi_on_plat and (oy < py - 3.5):
            self.missile_charge_timer = 0
            is_squatting = (act_val in [39, 40, 41]) or ("SQUAT" in act_str and "KNEE" not in act_str)
            
            # Si el rival está desplazado horizontalmente (|dx| > 6.0 u) o Luigi está agachado:
            # Deslizarse hacia el borde de la plataforma en dirección al rival (stick_x: towards_opp, stick_y: 0.5).
            # En pocos frames cruza el borde y cae al aire hacia el rival atacando en picada.
            if abs(dx) > 6.0 or is_squatting:
                return self._enforce_safety({
                    "name": "⚡ DROP-THROUGH PLATAFORMA: SALIDA DESLIZANTE HACIA EL RIVAL",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            else:
                # Rival directamente debajo (|dx| <= 6.0 u):
                # DROP-THROUGH LIMPIO: stick_y = 0.0 PURO sin botones (en Melee presionar attack/special ejecuta Down-Tilt/Down-Smash bloqueándolo).
                return self._enforce_safety({
                    "name": "⚡ DROP-THROUGH PLATAFORMA: DESCENSO LIMPIO AL SUELO",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 5.9. MÁQUINA DE RECARGA DEL PODER: GREEN MISSILE (SIDE-B) OFENSIVO Y DEFENSIVO
        # =========================================================================
        # Si Luigi está recargando su misil verde: acumula energía cinética y dispara
        if getattr(self, "missile_charge_timer", 0) > 0:
            # Si Luigi cae fuera de escenario o queda en el aire, abortar carga inmediatamente
            if not getattr(player, "on_ground", True) or is_offstage:
                self.missile_charge_timer = 0
            else:
                self.missile_charge_timer += 1
                max_chg = getattr(self, "missile_max_charge", 18)
                is_def = getattr(self, "missile_is_defensive", False)
                target_dir = getattr(self, "missile_target_dir", None)
                missile_stick_x = float(target_dir if target_dir is not None else towards_opp)
                
                # Seguridad de distancia: si la distancia al borde en la dirección del misil es < 38.0, abortar
                is_too_close_to_edge = (missile_stick_x > 0.5 and (stage_edge - px) < 38.0) or (missile_stick_x < 0.5 and (stage_edge + px) < 38.0)
                if is_too_close_to_edge and not is_def:
                    self.missile_charge_timer = 0
                    return self._enforce_safety({
                        "name": "🔥 ABORTO DE MISIL CERCA DEL BORDE ➔ BOLA DE FUEGO SEGURA",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": missile_stick_x, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

                # Disparar si alcanza la carga máxima o si un rival ofensivo se acerca demasiado durante carga
                should_fire = (self.missile_charge_timer >= max_chg) or (not is_def and dist <= 7.0 and self.missile_charge_timer >= 6)
                
                if not should_fire and (dist > 7.0 or is_def):
                    prefix = f"🛡️ RECARGA DEFENSIVA: TORPEDO DE RETIRADA ({self.missile_charge_timer}/{max_chg} FRAMES)" if is_def else f"🚀 RECARGANDO PODER: GREEN MISSILE TORPEDO ({self.missile_charge_timer}/{max_chg} FRAMES)"
                    return self._enforce_safety({
                        "name": prefix,
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": missile_stick_x, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    self.missile_charge_timer = 0
                    launch_name = "🛡️ ¡TORPEDO DE ESCAPE DISPARADO! ATRAVESAR PRESIÓN RIVAL" if is_def else "🚀 ¡MISIL VERDE DISPARADO! TORPEDO SUPERSONICO OFENSIVO (CHANCE MISFIRE 12.5%)"
                    return self._enforce_safety({
                        "name": launch_name,
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": missile_stick_x, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 6. ANTI-CHARGING & WHIFF PUNISH (Requisito 2: EVITA REGALARSE ANTE CARGAS)
        # =========================================================================
        is_opp_charging = (
            (opp_act_val in range(57, 65)) or
            any(k in opp_act_str for k in ["CHARGE", "HOLD", "S_4", "HI_4", "LW_4"]) or
            ("SPECIAL_N" in opp_act_str and "CHARGE" in opp_act_str)
        )
        if is_opp_charging:
            # 1. Si está a quemarropa (dist <= 5.0 u): SWEETSPOT UP-B SHORYUKEN INMEDIATO
            if dist <= 5.0:
                return self._enforce_safety({
                    "name": "💥 CASTIGO DE CARGA: SWEETSPOT UP-B SHORYUKEN FRAME-8 (25% PING!)",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 2. Si está dentro del rango del smash (5.0 < dist <= 16.0 u): NUNCA REGALARSE
            elif dist <= 16.0:
                is_cornered_charge = (abs(px) > (stage_edge - 16.0)) and (px * (ox - px) < 0)
                if is_cornered_charge:
                    self._start_missile_charge(current_frame, target_dir=dir_to_stage, max_charge=8, is_defensive=True)
                    return self._enforce_safety({
                        "name": "🚀 RETIRADA EXPLOSIVA: GREEN MISSILE TORPEDO DE ESCAPE (SIDE-B DEFENSIVO)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif current_frame % 2 == 0 and abs(px) < (stage_edge - 12.0):
                    return self._enforce_safety({
                        "name": "🛡️ EVASIÓN DE CARGA: WAVEDASH BACK FUERA DEL RANGO",
                        "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                        "stick_x": float(1.0 - towards_opp), "stick_y": 0.25,
                        "_allow_air_shield": True, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    return self._enforce_safety({
                        "name": "🤼 CASTIGO DE CARGA: WAVEDASH-GRAB A RIVAL INDEFENSO",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": True,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # 3. Si está fuera de alcance (dist > 16.0 u): INTERRUPCIÓN A DISTANCIA (PODER RECARGABLE O FUEGO)
            else:
                missile_path_clear = (towards_opp > 0.5 and (stage_edge - px) > 42.0) or (towards_opp < 0.5 and (stage_edge + px) > 42.0)
                if current_frame % 2 == 1 and missile_path_clear:
                    self._start_missile_charge(current_frame)
                    return self._enforce_safety({
                        "name": "🚀 CASTIGO DE CARGA: GREEN MISSILE TORPEDO RECARGABLE (SIDE-B)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    return self._enforce_safety({
                        "name": "🔥 INTERRUPCIÓN DE CARGA: BOLA DE FUEGO VERDE A DISTANCIA",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 7. CAZA Y ASALTO EN PLATAFORMAS (Requisito 4: ANTI-CAMPER PLATAFORMAS)
        # =========================================================================
        # CASO 7.2: EL RIVAL ESTÁ EN UNA PLATAFORMA O ACAMPANDO EN ALTURA
        if opp_on_plat or (oy >= 16.0 and abs(ox) <= 60.0):
            # Si Luigi está en el suelo: NUNCA hacer zigzag pasivo abajo
            if getattr(player, "on_ground", True) and not luigi_on_plat:
                if abs(dx) > 14.0:
                    return self._enforce_safety({
                        "name": "⚡ INVASIÓN DE PLATAFORMA: WAVEDASH DE APROXIMACIÓN",
                        "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.25,
                        "_allow_air_shield": True, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

                if (current_frame // 10) % 2 == 0:
                    self.luigi_jump_action = "PLATFORM_INVASION"
                    return self._enforce_safety({
                        "name": "🦘 INVASIÓN DE PLATAFORMA: SALTO Y WAVELAND AL RIVAL",
                        "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    self.luigi_jump_action = "AERIAL_UAIR"
                    return self._enforce_safety({
                        "name": "🦈 PLATFORM SHARKING: UP-AIR A TRAVÉS DE LA PLATAFORMA",
                        "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
            else:
                if dist <= 6.5:
                    return self._enforce_safety({
                        "name": "💥 ASALTO EN PLATAFORMA: DOWN-SMASH SEMI-SPIKE",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    return self._enforce_safety({
                        "name": "🤼 ASALTO EN PLATAFORMA: AGARRE (Z)",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": True,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 7.5. INTERCEPCIÓN Y CAZA AÉREA: RIVAL EN EL AIRE (ANTI-AIR & AERIAL HUNT)
        # =========================================================================
        opp_is_airborne = (not getattr(opponent, "on_ground", True)) or (oy >= 5.0)
        if opp_is_airborne and getattr(player, "on_ground", True) and not opp_offstage and not opp_is_falling:
            # 1. RIVAL EN EL AIRE DIRECTAMENTE SOBRE O CAYENDO HACIA LUIGI (|dx| <= 8.5, dy >= 3.0)
            if abs(dx) <= 8.5 and dy >= 3.0:
                # A) Kill Confirm: Sweetspot Up-B Shoryuken si rival está en rango vertical
                if opp_pct >= 45.0 and dy <= 11.0 and self.dopamine > 0.60:
                    return self._enforce_safety({
                        "name": "💥 ANTI-AIR: SWEETSPOT UP-B SHORYUKEN DE ANTIMATERIA (PING!)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                # B) Vórtice Tornado: Luigi Cyclone terrestre (Frame-1 intangibilidad absoluta)
                if current_frame % 2 == 0:
                    return self._enforce_safety({
                        "name": "🌪️ ANTI-AIR: LUIGI CYCLONE TERRESTRE (FRAME-1 INTANGIBLE)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                # C) Up-Tilt / Up-Smash antiaéreo
                return self._enforce_safety({
                    "name": "🥊 ANTI-AIR: UP-TILT JUGGLE VERTICAL",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 1.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 2. RIVAL EN EL AIRE A MEDIA DISTANCIA (8.5 < dist <= 25.0)
            # ¡LUIGI SALTA AL AIRE PARA CAZAR AL RIVAL EN COMBATE AÉREO!
            if dist <= 25.0:
                # Opción A: Salto ofensivo con N-Air Frame-3 (la patada más rápida de Melee)
                if (current_frame // 5) % 3 == 0:
                    self.luigi_jump_action = "AERIAL_NAIR"
                    return self._enforce_safety({
                        "name": "🦘 CAZA AÉREA: SALTO OFENSIVO NAIR FRAME-3",
                        "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                # Opción B: Salto ofensivo con Forward-Air Chop
                elif (current_frame // 5) % 3 == 1:
                    self.luigi_jump_action = "AERIAL_FAIR"
                    return self._enforce_safety({
                        "name": "🦘 CAZA AÉREA: SHORT-HOP FAIR CHOP AL AIRE",
                        "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": float(towards_opp), "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                # Opción C: Salto ofensivo con Luigi Cyclone en ascenso
                else:
                    self.luigi_jump_action = "AERIAL_CYCLONE"
                    return self._enforce_safety({
                        "name": "🌪️ CAZA AÉREA: SALTO + CYCLONE VORTEX AL RIVAL",
                        "jump": True, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 8. TECH-CHASE & CASTIGO A RIVAL DERRIBADO (JAB-RESET Y DOWN-SMASH)
        # =========================================================================
        is_opp_in_reset_stand = getattr(self, "jab_reset_active", False) and (current_frame - getattr(self, "jab_reset_frame", -100) <= 35)
        if is_opp_in_reset_stand and getattr(player, "on_ground", True):
            if dist <= 6.5 and (opp_pct >= 35.0 or self.dopamine > 0.50):
                self.jab_reset_active = False
                self.last_luigi_power = "UPB_SHORYUKEN"
                self.dopamine = 1.0
                self.learn_from_success("KO")
                return self._enforce_safety({
                    "name": "💥 JAB-RESET KILL CONFIRM: SWEETSPOT UP-B SHORYUKEN (PING! DESTRUCCIÓN TOTAL)",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False, "taunt": False,
                    "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            elif dist > 6.5 and abs(px) < (stage_edge - 14.0):
                self.luigi_jump_action = "WAVEDASH"
                self.luigi_wd_dir = towards_opp
                self.luigi_jump_frame = current_frame
                return self._enforce_safety({
                    "name": "⚡ JAB-RESET SETUP: WAVEDASH A QUEMARROPA ➔ UP-B PING",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False, "taunt": False,
                    "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        is_opp_knockdown = (opp_act_val in range(183, 203)) or any(k in opp_act_str for k in [
            "DOWN", "LYING", "TECH", "GROUND_ROLL"
        ])
        if is_opp_knockdown:
            self.combo_count += 1
            self.dopamine = min(1.0, self.dopamine + 0.35)

            # Lectura de hábitos del oponente aprendidos por STDP
            missed_tech_freq = habits.get("missed_tech", 0)
            roll_away_freq = habits.get("tech_roll_away", 0)
            roll_in_freq = habits.get("tech_roll_in", 0)

            if dist <= 6.0:
                if (opp_pct >= 40.0 or self.dopamine > 0.60) and current_frame % 3 == 0:
                    self.last_luigi_power = "UPB_SHORYUKEN"
                    return self._enforce_safety({
                        "name": "💥 TECH-CHASE: SWEETSPOT UP-B SHORYUKEN DE FUEGO (PING! KILL CONFIRM)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                if current_frame % 2 == 1 or missed_tech_freq > 3:
                    self.jab_reset_active = True
                    self.jab_reset_frame = current_frame
                    return self._enforce_safety({
                        "name": "🥊 JAB-RESET FRAME-2 (FORZAR LEVANTAMIENTO)",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                return self._enforce_safety({
                    "name": "💥 TECH-CHASE: DOWN-SMASH SEMI-SPIKE",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            elif dist <= 15.0:
                # Wavedash tech-chase: deslizarse rápidamente hacia el rival para conectar el Down-Smash
                if dist > 7.0 and abs(px) < (stage_edge - 14.0):
                    self.luigi_jump_action = "WAVEDASH"
                    self.luigi_wd_dir = towards_opp
                    self.luigi_jump_frame = current_frame
                    return self._enforce_safety({
                        "name": "⚡ TECH-CHASE: WAVEDASH HACIA EL RIVAL ➔ DOWN-SMASH",
                        "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                return self._enforce_safety({
                    "name": "💥 TECH-CHASE: DOWN-SMASH SEMI-SPIKE",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            else:
                # Si el rival suele rodar hacia afuera (roll away), sprint / misil hacia su posición de aterrizaje
                missile_path_clear = (towards_opp > 0.5 and (stage_edge - px) > 42.0) or (towards_opp < 0.5 and (stage_edge + px) > 42.0)
                if (roll_away_freq > roll_in_freq + 2 or current_frame % 2 == 0 or self.dopamine > 0.65) and missile_path_clear:
                    self._start_missile_charge(current_frame, max_charge=12)
                    return self._enforce_safety({
                        "name": "🚀 TECH-CHASE: GREEN MISSILE TORPEDO RECARGABLE (SIDE-B)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                return self._enforce_safety({
                    "name": "🏃 TECH-CHASE: SPRINT AL RIVAL EN EL SUELO",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 9. PRESIÓN EN EL BORDE & EDGEGUARDING (LECTURA DE REPISA & DEEP SPIKES)
        # =========================================================================
        is_opp_on_ledge = ("EDGE_" in opp_act_str) or (opp_act_val in [252, 253])
        if opp_is_falling or opp_offstage or is_opp_on_ledge:
            offstage_aggro = self.get_plasticity("offstage_aggression", 1.50)
            if is_opp_on_ledge:
                # 0. DISRESPECT SUPREMO: LUIGI DOWN-TAUNT METEOR SPIKE (Frame 45 Ledge Spike)
                # Si Luigi está al borde del abismo y la dopamina es alta (>0.60), desciende el tacón de la humillación
                is_right_at_edge = abs(px) >= (stage_edge - 6.5) and getattr(player, "on_ground", True)
                if is_right_at_edge and (self.dopamine >= 0.70 or (current_frame % 4 == 0 and self.dopamine >= 0.50)):
                    self.learn_from_success("EDGEGUARD")
                    return self._enforce_safety({
                        "name": "👟 DISRESPECT SUPREMO: LUIGI DOWN-TAUNT METEOR SPIKE (HUMILLACIÓN 20XX)",
                        "jump": False, "attack": False, "special": False, "shield": False, "grab": False, "taunt": True,
                        "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

                # Lectura de hábitos en repisa
                if habits.get("ledge_attack_freq", 0) > 3 or (current_frame % 2 == 0 and opp_pct < 60.0):
                    return self._enforce_safety({
                        "name": "💥 PRESIÓN EN BORDE: DOWN-SMASH SEMI-SPIKE DE REPISA",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif habits.get("ledge_roll_freq", 0) > 3:
                    return self._enforce_safety({
                        "name": "💥 LECTURA DE REPISA (ROLL READ): DOWN-SMASH SEMI-SPIKE DE INTERCEPCIÓN",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                return self._enforce_safety({
                    "name": "💥 PRESIÓN EN BORDE: DOWN-SMASH SEMI-SPIKE DE REPISA",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            has_double_jump = getattr(player, "jumps_left", 0) > 0
            is_near_ledge = abs(px) > (stage_edge - 22.0)
            # CAZA OFFSTAGE AGRESIVA (DEEP METEOR SPIKE):
            # Se activa si tiene doble salto, cerca del borde y con dopamina > 0.65 O alta agresividad aprendida
            if has_double_jump and is_near_ledge and py >= -6.0 and (self.dopamine > 0.65 or offstage_aggro >= 1.40):
                max_chase = 24.0 * min(1.5, max(1.0, offstage_aggro / 1.45))
                if dist <= max_chase:
                    return self._enforce_safety({
                        "name": "🌪️ OFFSTAGE HUNT: D-AIR METEOR SPIKE (DEPOT)",
                        "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.0,
                        "_allow_offstage_chase": True, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            if abs(px) > (stage_edge - 14.0):
                if dist <= 16.0:
                    return self._enforce_safety({
                        "name": "💥 EDGEGUARD: DOWN-SMASH SEMI-SPIKE",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    return self._enforce_safety({
                        "name": "🔥 EDGEGUARD: BOLA DE FUEGO VERDE AL ABISMO",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 10. POWERSHIELD REFLECT & ZERO SHIELD-STUN COUNTER (FRAME-1 REFLEJO DE PROYECTIL)
        # =========================================================================
        is_projectile = any(k in opp_act_str for k in ["LASER", "BLASTER", "MISSILE", "SPECIAL_N", "SPECIAL_S", "ITEM_THROW", "PILL", "TURNIP", "CHARGE_SHOT"]) or (opp_act_val in [341, 342, 343, 344, 345, 348, 349, 350])
        is_ps_ready = (getattr(self, "powershield_state", None) == "POWERSHIELD_ACTIVE") and (current_frame - getattr(self, "powershield_frame", -100) <= 2)
        if is_ps_ready and getattr(player, "on_ground", True):
            self.powershield_state = None
            self.learn_from_success("POWERSHIELD")
            if dist <= 7.0:
                self.dopamine = 1.0
                self.last_luigi_power = "UPB_SHORYUKEN"
                return self._enforce_safety({
                    "name": "💥 POWERSHIELD COUNTER: ZERO SHIELD-STUN SWEETSPOT UP-B (PING!)",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            else:
                self.luigi_jump_action = "WAVEDASH"
                self.luigi_jump_frame = current_frame
                self.luigi_wd_dir = towards_opp
                return self._enforce_safety({
                    "name": "⚡ POWERSHIELD REFLECT: WAVEDASH ADELANTE TRAS REFLEJO",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        if is_projectile and getattr(player, "on_ground", True):
            self.powershield_state = "POWERSHIELD_ACTIVE"
            self.powershield_frame = current_frame
            return self._enforce_safety({
                "name": "🛡️ POWERSHIELD FRAME-1: REFLEJO DE PROYECTIL (CERO SHIELD-STUN)",
                "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                "stick_x": 0.5, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 11. COMBATE CUERPO A CUERPO CQC (dist <= 11.0 unidades)
        # =========================================================================
        is_opp_attacking = ("ATTACK" in opp_act_str or "SWORD" in opp_act_str or "SPECIAL" in opp_act_str or opp_act_val in range(44, 75))
        is_opp_shielding = ("SHIELD" in opp_act_str or opp_act_val in [178, 179, 180, 181])

        if dist <= 11.0:
            # 1. Rival con escudo: Grab inmediato
            if is_opp_shielding:
                return self._enforce_safety({
                    "name": "🤼 ROMPE-ESCUDO: GRAB INMEDIATO (Z)",
                    "jump": False, "attack": False, "special": False, "shield": False, "grab": True,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 2. DEFENSIVA: RETIRADA EXPLOSIVA CON GREEN MISSILE SI ESTÁ ACORRALADO EN EL BORDE
            is_cornered_cqc = abs(px) > (stage_edge - 16.0) and (px * (ox - px) < 0)
            if is_cornered_cqc and dist <= 11.0:
                self._start_missile_charge(current_frame, target_dir=dir_to_stage, max_charge=8, is_defensive=True)
                return self._enforce_safety({
                    "name": "🚀 RETIRADA EXPLOSIVA: GREEN MISSILE TORPEDO DE ESCAPE (SIDE-B DEFENSIVO)",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": float(dir_to_stage), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 3. DEFENSIVA: VIST WHIFF PUNISH O CROUCH-CANCEL SWEETSPOT UP-B SHORYUKEN COUNTER
            is_whiff_ready = (getattr(self, "whiff_punish_state", None) == "PUNISH_READY") and (current_frame - getattr(self, "whiff_punish_frame", -100) <= 12)
            if is_whiff_ready:
                self.whiff_punish_state = None
                if (opp_pct >= 38.0 or self.dopamine > 0.55) and dist <= 7.0:
                    self.last_luigi_power = "UPB_SHORYUKEN"
                    self.dopamine = 1.0
                    self.learn_from_success("KO")
                    return self._enforce_safety({
                        "name": "💥 VIST WHIFF PUNISH: SWEETSPOT UP-B SHORYUKEN (PING! HUMILLACIÓN TOTAL)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    self.learn_from_success("COMBO")
                    return self._enforce_safety({
                        "name": "💥 VIST WHIFF PUNISH: F-SMASH DIAGONAL DEMOLEDOR",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.70, "c_stick_x": float(towards_opp), "c_stick_y": 0.70, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            if is_opp_attacking:
                cqc_reflex = self.get_plasticity("cqc_counter_reflex", 1.50)
                cc_shoryu_limit = min(115.0, 75.0 * (cqc_reflex / 1.50))
                cc_dsmash_limit = min(110.0, 60.0 * (cqc_reflex / 1.50))
                if dist <= 5.5 and getattr(player, "percent", 0.0) < cc_shoryu_limit:
                    self.learn_from_success("CQC_COUNTER")
                    self.last_luigi_power = "UPB_SHORYUKEN"
                    return self._enforce_safety({
                        "name": "💥 CQC DEFENSIVO: CROUCH-CANCEL SWEETSPOT UP-B SHORYUKEN DE FUEGO (PING!)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif dist <= 5.5 and getattr(player, "percent", 0.0) < cc_dsmash_limit:
                    self.learn_from_success("CQC_COUNTER")
                    return self._enforce_safety({
                        "name": "🟢 CQC: CROUCH-CANCEL FRAME-5 DOWN-SMASH COUNTER",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif dist > 5.5 and abs(px) < (stage_edge - 14.0):
                    self.whiff_punish_state = "PUNISH_READY"
                    self.whiff_punish_frame = current_frame
                    self.luigi_jump_action = "WAVEDASH_BACK"
                    self.luigi_wd_dir = 1.0 - towards_opp
                    self.luigi_jump_frame = current_frame
                    self.learn_from_success("WHIFF_PUNISH")
                    return self._enforce_safety({
                        "name": "⚡ VIST WAVEDASH-BACK BAIT: MICROCANCEL FUERA DE ALCANCE",
                        "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(1.0 - towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    return self._enforce_safety({
                        "name": "🛡️ CQC: ESCUDO REACTIVO (BLOQUEO)",
                        "jump": False, "attack": False, "special": False, "shield": True, "grab": False,
                        "stick_x": 0.5, "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # 4. PODER ESPECIAL 1: DOWN-B LUIGI CYCLONE (TORNADO DE LUIGI - FRAME-1 INVENCIBLE)
            # En CQC, el Cyclone absorbe golpes rivales y atrapa al oponente en un remolino multihit
            if (current_frame % 4 == 0) and not is_opp_shielding:
                return self._enforce_safety({
                    "name": "🌪️ PODER ESPECIAL: LUIGI CYCLONE TERRESTRE (VÓRTICE MULTIHIT)",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 5. PODER ESPECIAL 2: SWEETSPOT UP-B SHORYUKEN (25% DE DAÑO PING!)
            if dist <= 5.0 and (opp_pct >= 40.0 or self.dopamine > 0.55):
                self.last_luigi_power = "UPB_SHORYUKEN"
                return self._enforce_safety({
                    "name": "💥 PODER ESPECIAL: SWEETSPOT UP-B SHORYUKEN (FRAME-8 PING!)",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            if 55.0 <= opp_pct <= 95.0 and dist <= 10.0:
                return self._enforce_safety({
                    "name": "💥 CQC: DOWN-TILT LAUNCHER (POP-UP PARA UP-AIR)",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.25, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            if dist <= 7.0:
                return self._enforce_safety({
                    "name": "💥 CQC: DOWN-SMASH SEMI-SPIKE FRAME-5",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": 0.5, "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            return self._enforce_safety({
                "name": "🥊 CQC: JAB RÁPIDO FRAME-2 (A)",
                "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 12. NEUTRAL TÁCTICO: PODERES, ATAQUES AÉREOS & WAVEDASHING (11.0 < dist <= 24.0 u)
        # =========================================================================
        elif dist <= 24.0:
            # 0. WHIFF PUNISH VIST: Si el rival está atacando al aire a distancia de whiff (11.0 < dist <= 14.5 o ampliado por whiff_punish_iq)
            whiff_iq = self.get_plasticity("whiff_punish_iq", 1.70)
            whiff_trigger_dist = min(17.5, 14.5 * (whiff_iq / 1.70))
            if is_opp_attacking and dist <= whiff_trigger_dist and getattr(player, "on_ground", True):
                is_ready = (getattr(self, "whiff_punish_state", None) == "PUNISH_READY") and (current_frame - getattr(self, "whiff_punish_frame", -100) <= 12)
                if is_ready:
                    self.whiff_punish_state = None
                    return self._enforce_safety({
                        "name": "💥 VIST WHIFF PUNISH: F-SMASH DIAGONAL DEMOLEDOR",
                        "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.70, "c_stick_x": float(towards_opp), "c_stick_y": 0.70, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                elif abs(px) < (stage_edge - 14.0):
                    self.whiff_punish_state = "PUNISH_READY"
                    self.whiff_punish_frame = current_frame
                    self.luigi_jump_action = "WAVEDASH_BACK"
                    self.luigi_wd_dir = 1.0 - towards_opp
                    self.luigi_jump_frame = current_frame
                    return self._enforce_safety({
                        "name": "⚡ VIST WAVEDASH-BACK BAIT: MICROCANCEL FUERA DE ALCANCE",
                        "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                        "stick_x": float(1.0 - towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            cx_spikes = int(self.spikes[self.map_cx_saccade].sum()) if hasattr(self, "map_cx_saccade") else 0
            entropy = (current_frame * 17 + cx_spikes * 7 + int(self.dopamine * 100)) % 100

            # 1. ATAQUE AÉREO DE ENTRADA: SHORT-HOP OFENSIVO NAIR / FAIR (20% probabilidad)
            if entropy < 20:
                if current_frame % 2 == 0:
                    self.luigi_jump_action = "AERIAL_NAIR"
                    return self._enforce_safety({
                        "name": "🦅 ENTRADA AÉREA: SHORT-HOP NAIR FRAME-3 CROSS-UP",
                        "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.65, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    self.luigi_jump_action = "AERIAL_FAIR"
                    return self._enforce_safety({
                        "name": "🦅 ENTRADA AÉREA: SHORT-HOP FAIR CHOP AL RIVAL",
                        "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.65, "c_stick_x": float(towards_opp), "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # 2. PODER ESPECIAL RECARGABLE: GREEN MISSILE TORPEDO (SIDE-B) (18% probabilidad)
            missile_path_clear = (towards_opp > 0.5 and (stage_edge - px) > 42.0) or (towards_opp < 0.5 and (stage_edge + px) > 42.0)
            if 20 <= entropy < 38 and dist >= 13.0 and missile_path_clear:
                self._start_missile_charge(current_frame, max_charge=14)
                return self._enforce_safety({
                    "name": "🚀 PODER ESPECIAL RECARGABLE: GREEN MISSILE TORPEDO OFENSIVO (SIDE-B)",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 3. FINTA OFENSIVA: WAVEDASH ADELANTE ➔ SWEETSPOT UP-B SHORYUKEN DE FUEGO / CYCLONE (14% probabilidad)
            if 38 <= entropy < 52:
                if (opp_pct >= 40.0 or self.dopamine > 0.55) and dist <= 16.0:
                    self.last_luigi_power = "UPB_SHORYUKEN"
                    return self._enforce_safety({
                        "name": "💥 ENTRADA OFENSIVA: WAVEDASH ADELANTE ➔ SWEETSPOT UP-B SHORYUKEN DE FUEGO (PING!)",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": 0.5, "stick_y": 1.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)
                else:
                    self.last_luigi_power = "CYCLONE"
                    return self._enforce_safety({
                        "name": "🌪️ PODER ESPECIAL: WAVEDASH ADELANTE ➔ LUIGI CYCLONE VORTEX",
                        "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                        "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                    }, player, opponent, stage_edge=stage_edge)

            # 4. ENTRADA SEGURA: WAVEDASH ADELANTE ➔ DOWN-SMASH SEMI-SPIKE (14% probabilidad)
            if 52 <= entropy < 66:
                return self._enforce_safety({
                    "name": "💥 ENTRADA SEGURA: WAVEDASH ADELANTE ➔ DOWN-SMASH",
                    "jump": False, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.0, "c_stick_x": 0.5, "c_stick_y": 0.0, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 5. FINTA COMPLEJA: TOMAHAWK FAKE-OUT (SALTO VACÍO ➔ AGARRE Z) (12% probabilidad)
            if 66 <= entropy < 78:
                return self._enforce_safety({
                    "name": "🎭 FINTA COMPLEJA: TOMAHAWK FAKE-OUT (SALTO VACÍO ➔ AGARRE Z)",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.65, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 6. BOLA DE FUEGO VERDE TÁCTICA (10% probabilidad)
            if 78 <= entropy < 88:
                return self._enforce_safety({
                    "name": "🔥 ENTRADA NEUTRAL: BOLA DE FUEGO VERDE TÁCTICA",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 7. WAVEDASH BACK BAIT O RUSHDOWN ANTE RIVAL PASIVO (12% probabilidad)
            is_opp_idle = (opp_act_val in [14, 15] or "WAIT" in opp_act_str or "STAND" in opp_act_str)
            if is_opp_idle and abs(px) < (stage_edge - 14.0):
                self.luigi_jump_action = "WAVEDASH"
                self.luigi_wd_dir = towards_opp
                self.luigi_jump_frame = current_frame
                return self._enforce_safety({
                    "name": "⚡ ASALTO A RIVAL PASIVO: WAVEDASH ADELANTE (0.005 TRACTION)",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5,
                    "stats": stats
                }, player, opponent, stage_edge=stage_edge)
            else:
                self.luigi_jump_action = "WAVEDASH_BACK"
                self.luigi_wd_dir = 1.0 - towards_opp
                return self._enforce_safety({
                    "name": "🏃 DASH-DANCE ➔ WAVEDASH BACK BAIT (WHIFF TRAP)",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(1.0 - towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5,
                    "stats": stats
                }, player, opponent, stage_edge=stage_edge)

        # =========================================================================
        # 12. DISTANCIA LARGA (dist > 24.0 u): PODERES DE ASALTO & APROXIMACIÓN
        # =========================================================================
        else:
            # 1. Torpedo de aproximación recargable: GREEN MISSILE (Side-B) a toda velocidad
            missile_path_clear = (towards_opp > 0.5 and (stage_edge - px) > 42.0) or (towards_opp < 0.5 and (stage_edge + px) > 42.0)
            if current_frame % 40 < 18 and missile_path_clear:
                self._start_missile_charge(current_frame, max_charge=18)
                return self._enforce_safety({
                    "name": "🚀 PODER ESPECIAL RECARGABLE: GREEN MISSILE TORPEDO DE ASALTO (SIDE-B)",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # Si el rival está pasivo / acampando sin atacar: acortar distancia de inmediato con Wavedash
            is_opp_idle = (opp_act_val in [14, 15] or "WAIT" in opp_act_str or "STAND" in opp_act_str)
            if is_opp_idle and abs(px) < (stage_edge - 14.0):
                self.luigi_jump_action = "WAVEDASH"
                self.luigi_wd_dir = towards_opp
                self.luigi_jump_frame = current_frame
                return self._enforce_safety({
                    "name": "⚡ ASALTO A RIVAL PASIVO: WAVEDASH RUSHDOWN (0.005 TRACTION)",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 2. Aproximación aérea con Short-Hop N-Air
            if current_frame % 40 < 25:
                self.luigi_jump_action = "AERIAL_NAIR"
                return self._enforce_safety({
                    "name": "🦘 APROXIMACIÓN AÉREA: SHORT-HOP AVANZANDO",
                    "jump": True, "attack": True, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.65, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 3. Bola de fuego verde ocasional para cubrir el avance
            if current_frame % 40 < 32 and abs(px) < (stage_edge - 16.0):
                return self._enforce_safety({
                    "name": "🔥 ZONING PROFESIONAL: BOLA DE FUEGO VERDE",
                    "jump": False, "attack": False, "special": True, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 4. Wavedash Rushdown deslizante (0.005 de fricción para cruzar el escenario al instante)
            if current_frame % 3 != 0 and abs(px) < (stage_edge - 14.0) and self.dopamine > 0.40:
                self.luigi_jump_action = "WAVEDASH"
                self.luigi_wd_dir = towards_opp
                self.luigi_jump_frame = current_frame
                return self._enforce_safety({
                    "name": "⚡ WAVEDASH RUSHDOWN: GLIDE SUPREMO (0.005 TRACTION)",
                    "jump": True, "attack": False, "special": False, "shield": False, "grab": False,
                    "stick_x": float(towards_opp), "stick_y": 0.85, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
                }, player, opponent, stage_edge=stage_edge)

            # 5. Sprint agresivo 20XX
            return self._enforce_safety({
                "name": "🏃 20XX SPRINT AGRESIVO (CIERRE DE DISTANCIA)",
                "jump": False, "attack": False, "special": False, "shield": False, "grab": False,
                "stick_x": float(towards_opp), "stick_y": 0.5, "c_stick_x": 0.5, "c_stick_y": 0.5, "stats": stats
            }, player, opponent, stage_edge=stage_edge)

    def get_controller_decision(self, player=None, opponent=None, current_frame=0, stage="BATTLEFIELD"):
        """Decide la acción del personaje según el personaje activo o seleccionado."""
        p_char = getattr(player, "character", None) if player is not None else None
        active_char = getattr(self, "active_character", "LUIGI")
        c_str = str(p_char).upper() if p_char is not None else active_char.upper()
        if "FOX" in c_str and "LUIGI" not in c_str:
            return self.get_fox_decision(player, opponent, current_frame=current_frame, stage=stage)
        # Por defecto la mosca controla a LUIGI
        return self.get_luigi_decision(player, opponent, current_frame=current_frame, stage=stage)
