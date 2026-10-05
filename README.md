# 🪰 Fly-Melee: Conectoma de la Mosca (400k) × Super Smash Bros. Melee

[![Tests Status](https://img.shields.io/badge/Tests-81%2F81%20Passing-brightgreen.svg)](#-pruebas-y-verificación-del-sistema-8181)
[![Simulation Rate](https://img.shields.io/badge/Simulation-60Hz%20Nativos%20(0.97ms)-blue.svg)](#-arquitectura-técnica-y-modulación-por-clusters)
[![Neurons](https://img.shields.io/badge/LIF%20Neurons-395%2C144-orange.svg)](#-arquitectura-técnica-y-modulación-por-clusters)
[![Synapses](https://img.shields.io/badge/Active%20Synapses-72.9M%20(CSC)-purple.svg)](#-arquitectura-técnica-y-modulación-por-clusters)

Simulación biofísica en tiempo real del cerebro completo de la mosca de la fruta (*Drosophila melanogaster*, **395,144 neuronas Leaky Integrate-and-Fire** y **~73 millones de sinapsis** del proyecto **FlyWire / Princeton**) conectado de manera síncrona a **Super Smash Bros. Melee** a **60Hz nativos**.

El conectoma biológico decodifica la percepción visual del combate, procesa la dinámica de neurotransmisores (**Dopamina PAM** y **Octopamina PPL1**), modula decisiones motoras mediante descargas de espigas en clusters anatómicos y ejecuta biomecánica avanzada a nivel competitivo 20XX con una barrera fail-safe de **cero suicidios**.

> 📖 **Documentación Técnica & Glosario de Conceptos:**  
> - **[README_TECNICO.md](file:///home/ltar/projects/fly-melee/README_TECNICO.md)**: Whitepaper de arquitectura profunda (Ecuaciones LIF, tensores dispersos CSC, dinámica de los 8 clusters, justificación de librerías y transducción de looming).  
> - **[DICCIONARIO_TECNICO.md](file:///home/ltar/projects/fly-melee/DICCIONARIO_TECNICO.md)**: Enciclopedia / Blog de conceptos de la A a la Z (Términos de neurobiología, matemáticas, hardware y jerga competitiva 20XX de Super Smash Bros. Melee).

---

## 🚀 Inicio Rápido: Jugar en Dolphin & Panel Web 3D en Vivo

Para arrancar el juego en Dolphin y visualizar la telemetría biológica en 3D:

```bash
./start_fly.sh
```

Esto ejecuta automáticamente:
1. **Emulador Dolphin**: Inicia *Super Smash Bros. Melee* con la mosca conectada en el Puerto 1 y tus controles listos en el Puerto 2.
2. **Panel Web 3D en Vivo**: Abre automáticamente tu navegador en **`http://localhost:8085`** sincronizado a 60 FPS con el combate.

*(Si solo deseas abrir el panel web sin Dolphin, puedes ejecutar `./start_fly.sh --web`).*

### ¿Qué incluye el Panel Web?
- **🧠 Conectoma 3D Interactivo (Three.js WebGL)**: Explora las 395,144 neuronas anatómicas en tiempo real, rota la cámara 3D, haz zoom e inspecciona las descargas sinápticas iluminándose en vivo según cada decisión motora (Salto `DNp01`, Ataque, Reflector Shine, Escudo).
- **⚔️ Arena Melee en Tiempo Real**: Simulación visual del combate sobre escenarios oficiales (*Battlefield, Final Destination, Dream Land, Yoshi's Story, Fountain of Dreams, Pokémon Stadium*) con barras de porcentaje, stocks y proyectiles.
- **🎮 Mando GameCube en Vivo**: Muestra en tiempo real los movimientos exactos del stick analógico principal, el C-Stick y los botones accionados por el sistema nervioso de la mosca.
- **🧪 Neuroquímica y Plasticidad**: Monitores en tiempo real de Dopamina PAM (modo depredador/ataque), Octopamina PPL1 (supervivencia/alarma), racha de combos y memoria acumulada.
- **🔄 Selector de Personaje en Caliente**: Cambia en vivo entre **🟢 Luigi (Wavedash SSS)** y **🦊 Fox McCloud (20XX Spacie)** con un solo clic en la insignia superior.

---

## 📦 Instalación de Dependencias (Paso a Paso)

### 1. Requisitos Previos del Sistema (Linux)
Asegúrate de contar con Python 3.10 o superior y las utilidades de compilación:

**En Ubuntu / Debian / Pop!_OS:**
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git build-essential
```

**En Arch Linux / Manjaro:**
```bash
sudo pacman -S python python-pip git base-devel
```

**En Fedora:**
```bash
sudo dnf install -y python3 python3-pip git gcc
```

### 2. Clonar el Repositorio
```bash
git clone https://github.com/LATAR-web/fly-melee.git
cd fly-melee
```

### 3. Crear y Activar el Entorno Virtual
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Instalar Dependencias de Python
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Dependencias incluidas en `requirements.txt`:
| Librería | Versión | Propósito |
|---|---|---|
| `numpy` | `>=1.24` | Vectorización de potenciales de membrana LIF y álgebra matricial |
| `scipy` | `>=1.10` | Matrices dispersas CSC para las 72.9M de conexiones sinápticas |
| `melee` (libmelee) | `>=0.38` | Protocolo Slippi y puente de comunicación con el emulador Dolphin |
| `pyenet-vladfi` | `>=1.3` | Protocolo de red ENet para telemetría Melee a 60 FPS |
| `py-ubjson` | `>=0.16` | Decodificación de eventos de combate y replays de Slippi |
| `evdev` | `>=1.6` | Detección y calibración de mandos (USB / Bluetooth) en Linux |

---

## 🎮 Controles para Jugador Humano (Teclado)

Si juegas contra la mosca desde el teclado sin mandos adicionales:

| Acción | Modo WASD (Gamer) | Modo Flechas (Clásico) | Mando GameCube |
|---|---|---|---|
| **Movimiento / Agacharse** | `W` `A` `S` `D` | `↑` `↓` `←` `→` | Stick Principal |
| **Ataque Normal / Selección** | `J` o `Espacio` | `X` o `Espacio` | Botón `A` |
| **Ataque Especial** | `K` | `Z` | Botón `B` |
| **Salto** | `U` o `I` | `C` o `V` | Botón `X` / `Y` |
| **Agarre (Grab)** | `O` | `F` | Botón `Z` |
| **Escudo (Shield)** | `L` | `Q` o `E` | Gatillo `L` / `R` |
| **Start / Pausa** | `Enter` | `Enter` | Botón `Start` |

*(Si conectas un mando de GameCube, Xbox, Switch Pro o PlayStation por USB/Bluetooth, el sistema lo detecta y lo autocalibra).*

---

## 🧬 Arquitectura Técnica y Modulación por Clusters

El sistema nervioso no utiliza árboles de decisión fijos ni heurísticas estáticas. Las decisiones motoras son impulsadas por la propagación biofísica en **8 clusters anatómicos**:

- **Simulación a 60Hz Nativos**: Gracias al formato de matrices dispersas CSC (*Compressed Sparse Column*), un paso completo de integración LIF sobre 395,144 neuronas toma **0.97 ms** (1032 FPS), consumiendo menos del 6% del presupuesto de 16.6 ms de cada frame.
- **Cluster 5 (Giant Fiber `DNp01` / Evasión Saccádica)**:
  - Ante amenazas inminentes en CQC, el circuito Giant Fiber se sobreexcita y desencadena una **evasión saccádica inmediata** (Wavedash-back fuera de rango o salto salvavidas).
- **Cluster 6 (VNC de Precisión 20XX)**:
  - Gobierna el timing submilisegundo de **Powershield Frame-1**, **Shield Drop** instantáneo en plataformas, **Reflector Shine Frame-1 OoS** (Fox) y **N-Air Frame-3 OoS** (Luigi).
  - Ejecuta el **Ledge-Stall Invulnerable** para regrabar la repisa y reiniciar los 30 frames de intangibilidad total.
- **Cluster 7 (Red Cerebelar de Combos & Tech-Chase)**:
  - Al detectar al rival en tumble o derribo en suelo, enruta el castigo: **Running JC Up-Smash** en Fox, y **Wavedash Down-Tilt Launcher** o **Chaingrab Loop** en Luigi.
- **Barrera de Seguridad Fail-Safe Anti-Suicidios**:
  - Filtro estricto que previene correr fuera del escenario (runway barrier) y neutraliza el stick analógico en bolas de fuego (`stick_x = 0.5`) para **garantizar 0 suicidios con Green Missile**.

---

## 🥋 Arsenal Técnico 20XX de los Personajes

### 🟢 Luigi (Fricción 0.005 & Tournament-Tier)
1. **Wavedash Deslizante Infinito**: Aprovecha la tracción mínima de Luigi (0.005) para cruzar el escenario con 14 frames de intangibilidad.
2. **Short-Hop B-Air Wall**: Salto corto con patada trasera dropkick de alto impacto (12% daño, knockback horizontal mortal).
3. **Wavedash Down-Tilt Launcher**: Entrada a ras de suelo con Down-Tilt frame-5 que proyecta verticalmente al rival hacia combos aéreos.
4. **Sweetspot Up-B Shoryuken Kill Confirm**: Remate a quemarropa (frame-8) con sonido "PING!" que noquea a porcentajes medios/altos.
5. **Chaingrab / Regrab Loop en Fastfallers**: Cadena de agarres terrestres contra Fox, Falco y Falcon.
6. **Ledge-Stall & Ledgedash Invencible**: Regrab defensivo en repisa y subida deslizante con intangibilidad.
7. **Down-Taunt Meteor Spike**: Remate despectivo frame-45 en repisa contra rivales colgando indefensos.

### 🦊 Fox McCloud (20XX Spacie)
1. **Frame-1 Reflector Shine & Waveshine**: Presión de escudo y combos continuos en suelo.
2. **Drill-Shine Shield Pressure**: D-Air drill multihit cancelado instantáneamente en Shine al tocar el suelo.
3. **Running JC Up-Smash**: Confirmación letal corriendo mediante Jump-Cancel instantáneo hacia Up-Smash.
4. **Powershield Frame-1 & Shine OoS**: Reflejo perfecto de proyectiles rivales y respuesta inmediata fuera del escudo.
5. **Short-Hop Double Laser (SHDL)**: Zonificación a distancia con dos láseres por cada salto corto.
6. **Recuperación Inteligente Fox Illusion / Fire Fox**: Ángulos calculados hacia el centro del escenario para evitar edgehogs.

---

## 🧪 Pruebas y Verificación del Sistema (81/81)

El proyecto cuenta con una suite integral de **81 pruebas automáticas** que validan la biomecánica, la recuperación anti-suicidios, la simulación a 60Hz y la modulación de clusters:

```bash
/home/ltar/.venvs/pytorch/bin/python verify_fixes.py
```

### Resumen de Pruebas:
- **Tests 1–10**: Rendimiento LIF ($< 10\text{ ms}$), prevención de suicidio en borde y Fire Fox seguro.
- **Tests 11–30**: Cadena Bread & Butter, Tech-chase con Down-Smash, Wavedash OoS y SHDL.
- **Tests 31–50**: L-Cancel automático, Wiggle-out de tumble y geometría de escenarios.
- **Tests 51–65**: Tracción de Luigi, Shoryuken Kill Confirm, Rising Cyclone y Jab-Reset confirm.
- **Tests 66–76**: Ledge roll invencible, Shield Drop, Platform Edge-Cancel y Mash-Out a 60 inputs/s.
- **Test 77**: Luigi Short-Hop B-Air Wall (`AERIAL_BAIR` buffered).
- **Test 78**: Luigi Ledge-Stall Invincible Regrab (renovación de 30 frames de intangibilidad).
- **Test 79**: Luigi Wavedash Down-Tilt Launcher (pop-up vertical).
- **Test 80**: Modulación biológica por descarga de espigas en Clusters 5, 6 y 7.
- **Test 81**: Simulación biológica continua a 60Hz nativos sin throttle.

```text
======================================================================
🎉 ¡TODAS LAS PRUEBAS COMPLETADAS CON ÉXITO! (81/81 SUPERADAS)
======================================================================
```

---

## 🚀 Utilidades Avanzadas (Dolphin / Entrenamiento)

```bash
# Lanzador avanzado de Dolphin, mandos y bots
./start_dolphin.sh

# Entrenar partidas aceleradas contra CPU Nivel 9
python3 train_fly.py 50 --character luigi --cpu 9

# Probar la simulación neural en la terminal
python3 test_fly_brain.py
```

---

## 📜 Créditos y Referencias
- **FlyWire Consortium & Princeton Neuroscience Institute**: Reconstrucción y mapa sináptico del conectoma completo de *Drosophila melanogaster*.
- **Project Slippi & libmelee**: Puente de emulación y protocolo de red de *Super Smash Bros. Melee* a 60 FPS.
