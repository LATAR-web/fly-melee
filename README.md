# 🪰 Fly-Melee: Conectoma Biológico de la Mosca × Super Smash Bros. Melee

> **Simulación biológica en tiempo real del conectoma cerebral completo de la mosca (*Drosophila melanogaster* - 395,144 neuronas LIF y ~73M sinapsis) controlando a Luigi y Fox en Super Smash Bros. Melee.**

---

## 🌟 Características Principales

- 🧠 **Conectoma Biológico Real (~400,000 Neuronas)**:
  Reconstrucción biológica a partir del conectoma *FlyWire / MaleCNS*, estructurada en 8 clusters anatómicos (Cerebelar, VNC Motor, Central Complex, Dopaminérgico PAM, Octopaminérgico PPL1, Giant Fiber, etc.) con ~73 millones de sinapsis recurrentes.
- ⚡ **Acelerador Sináptico CSC de Ultra Alta Velocidad**:
  Multiplicación dispersa en formato *Compressed Sparse Column* (CSC) que procesa fotogramas neuronales en menos de 3.5 ms, garantizando **60 FPS estables** sin latencia de emulación.
- 🟢 **Mapeo de Luigi 20XX (Wavedash Supremo & Shoryuken)**:
  - Deslizamiento infinito con tracción **0.005**.
  - *Sweetspot Up-B Shoryuken de Fuego* (Frame-8 Kill Confirm).
  - *Green Missile Torpedo* recargable y defensivo.
  - *Jab-Reset* Frame-2 y *D-Air Meteor Spike* en caza offstage.
  - *L-Cancel* universal en suelo y plataformas.
  - *ASDI Down* en hitstun con contraataque Crouch-Cancel.
- 🦊 **Soporte de Fox McCloud (20XX Tech-Chase)**:
  - Waveshine continuo y SHDL (*Short Hop Double Laser*).
  - Drill multihit y recuperación con Fire Fox.
- 🌐 **Panel Web 3D y Arena Interactiva en Tiempo Real** (`http://localhost:8085`):
  - Visualización 3D WebGL con Three.js del cerebro anatómico de la mosca iluminando los circuitos sinápticos activos.
  - Telemetría en vivo vía *Server-Sent Events* (SSE).
  - Dinámica neuroquímica (*Dopamina PAM* y *Octopamina PPL1*).
  - Mando virtual de GameCube animado con sticks analógicos y botones en tiempo real.
  - Arena 2D de combate en tiempo real con marcadores, daño y vidas.
- 🧬 **Entrenador Neural Acelerado vs Bots CPU Nivel 9**:
  - Simula decenas de partidas en segundos contra 15 personajes de Melee (Marth, Falco, Sheik, Falcon, Peach, etc.).
  - Neuroplasticidad STDP y memoria persistente a largo plazo guardada en `data/memory/long_term_synapses.json`.
- 🎮 **Soporte Plug-and-Play de Mandos en Linux**:
  - Detección y calibración automática de gamepads USB y Bluetooth genéricos para el Jugador 2 (Humano).
  - Soporte de teclado (WASD / Flechas) sin dependencias adicionales.

---

## 🚀 Inicio Rápido

### Menú Interactivo
El lanzador central te permite ejecutar cualquier componente con un solo comando:

```bash
./start_fly.sh
```

Opciones disponibles en el menú:
1. **Iniciar Panel Web 3D interactivo** (`http://localhost:8085`)
2. **Ejecutar Test de Simulación Neural en Terminal**
3. **Iniciar Dolphin: Mosca vs Humano (Tú en Puerto 2)**
4. **Iniciar Dolphin: Mosca vs Bot CPU Nivel 9 (P2 automático)**
5. **Abrir Slippi Launcher**
6. **Detectar y Configurar Mando / Gamepad (USB o Bluetooth)**
7. **Reparar Conexión de Mandos Bluetooth Genéricos en Linux**
8. **Entrenamiento Neural Acelerado vs Bots Nivel 9**

---

## 🖥️ Componentes del Proyecto

| Archivo | Descripción |
|---|---|
| [`fly_brain.py`](fly_brain.py) | Núcleo de simulación LIF, conectoma de 395k neuronas y decodificador biomecánico |
| [`fly_melee.py`](fly_melee.py) | Puente directo entre Dolphin/Slippi, la Mosca (P1) y el Humano/CPU (P2) |
| [`train_fly.py`](train_fly.py) | Entrenador acelerado de plasticidad y combate vs 15 personajes CPU Nivel 9 |
| [`dashboard_server.py`](dashboard_server.py) | Servidor HTTP / SSE para el visualizador 3D y telemetría en tiempo real |
| [`web/index.html`](web/index.html) | Panel 3D WebGL (Three.js), HUD de telemetría y arena virtual de combate |
| [`detect_controller.py`](detect_controller.py) | Detector y configurador automático de gamepads USB/Bluetooth para Dolphin |
| [`fix_bluetooth_gamepad.sh`](fix_bluetooth_gamepad.sh) | Script de ajuste BlueZ para mandos Android/inalámbricos genéricos |
| [`verify_fixes.py`](verify_fixes.py) | Suite de verificación con 58 pruebas automáticas de biomecánica 20XX |
| [`test_fly_brain.py`](test_fly_brain.py) | Benchmark y visualización de disparos neuronales en terminal |
| [`fast_download.py`](fast_download.py) | Descargador multihilo acelerado para la ISO de Melee |

---

## 🕹️ Controles para el Jugador Humano (Teclado)

| Acción | Esquema A (WASD) | Esquema B (Flechas) | Mando GameCube |
|---|---|---|---|
| **Moverse / Agacharse** | `W` `A` `S` `D` | `↑` `↓` `←` `→` | Stick Principal |
| **Ataque Normal / Ficha** | `J` o `Espacio` | `X` o `Espacio` | Botón `A` |
| **Ataque Especial** | `K` | `Z` | Botón `B` |
| **Salto** | `U` o `I` | `C` o `V` | Botón `X` / `Y` |
| **Agarre (Grab)** | `O` | `F` | Botón `Z` |
| **Escudo (Shield)** | `L` | `Q` o `E` | Gatillo `L` / `R` |
| **Start / Pausa** | `Enter` | `Enter` | Botón `Start` |

---

## 🧪 Pruebas y Verificación

Para ejecutar la suite de 58 pruebas biomecánicas y de seguridad:

```bash
python3 verify_fixes.py
```

Para ejecutar una sesión de entrenamiento neural de 50 partidas:

```bash
python3 train_fly.py 50 --character luigi --cpu 9
```

---

## 📜 Licencia

Desarrollado para investigación de neurociencia computacional aplicada a inteligencia artificial en videojuegos competitivos.
