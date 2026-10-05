# 🪰 Fly-Melee: Conectoma de la Mosca (400k) × Super Smash Bros. Melee

Simulación biológica en tiempo real del cerebro completo de la mosca de la fruta (*Drosophila melanogaster*, ~400,000 neuronas y 130 millones de sinapsis del proyecto **FlyWire / Princeton**) conectado directamente a **Super Smash Bros. Melee**.

El conectoma biológico decodifica la percepción visual del combate, procesa la dinámica de neurotransmisores (**Dopamina** y **Octopamina**), ejecuta biomecánica avanzada a nivel competitivo 20XX (Wavedashing, Sweetspot Shoryukens, L-canceling, Tech-chasing) y aprende mediante neuroplasticidad persistente.

---

## 🚀 Inicio Rápido: Jugar en Dolphin & Panel Web en Vivo

Para arrancar el juego en Dolphin y visualizar la telemetría biológica en 3D:

```bash
./start_fly.sh
```

Esto ejecuta automáticamente:
1. **Emulador Dolphin**: Inicia *Super Smash Bros. Melee* con la mosca conectada en el Puerto 1 y tus controles listos en el Puerto 2.
2. **Panel Web 3D**: Abre automáticamente tu navegador en **`http://localhost:8085`** sincronizado a 60 FPS con el combate.

*(Si solo deseas abrir el panel web sin el emulador Dolphin, puedes ejecutar `./start_fly.sh --web`).*

### ¿Qué incluye el Panel Web?
- **🧠 Conectoma 3D Interactivo (Three.js WebGL)**: Explora las 400,000 neuronas anatómicas, rota con el ratón o touchpad, haz zoom e inspecciona los circuitos neuronales iluminándose en vivo según cada decisión motora (Salto `DNp01`, Ataque, Reflector, Escudo).
- **⚔️ Arena Melee en Tiempo Real**: Simulación visual del combate sobre escenarios oficiales (*Battlefield, Final Destination, Dream Land, Yoshi's Story, Fountain of Dreams, Pokémon Stadium*) con barras de porcentaje, stocks y proyectiles.
- **🎮 Mando GameCube en Vivo**: Muestra en tiempo real los movimientos exactos del stick analógico principal, el C-Stick y los botones accionados por el sistema nervioso de la mosca.
- **🧪 Neuroquímica y Plasticidad**: Monitores en tiempo real de Dopamina PAM (modo depredador/ataque), Octopamina PPL1 (supervivencia/alarma), racha de combos y memoria acumulada.
- **🔄 Selector de Personaje en Caliente**: Cambia en vivo entre **🟢 Luigi (Wavedash SSS)** y **🦊 Fox McCloud (20XX Spacie)** con un solo clic en la insignia superior.

---

## 📦 Instalación de Dependencias (Paso a Paso)

Sigue estos pasos en Linux para instalar y configurar todo el entorno desde cero:

### 1. Requisitos Previos del Sistema
Asegúrate de contar con Python 3.10 o superior y las utilidades básicas del sistema:

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
Se recomienda utilizar un entorno virtual aislado:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Instalar Dependencias de Python
Instala todas las librerías necesarias especificadas en `requirements.txt`:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Dependencias incluidas en `requirements.txt`:
| Librería | Propósito |
|---|---|
| `numpy` (>=1.24) | Computación vectorial y álgebra lineal de potenciales de membrana LIF |
| `scipy` (>=1.10) | Matrices dispersas para almacenar las conexiones sinápticas (130M+) |
| `melee` (libmelee) | Protocolo Slippi y puente de comunicación con el emulador Dolphin |
| `pyenet-vladfi` | Protocolo de red ENet para telemetría Melee a 60 FPS |
| `py-ubjson` | Decodificación de eventos de combate y replays de Slippi |
| `evdev` | Detección y calibración de mandos (USB / Bluetooth) en Linux |

---

## 🎮 Controles para Jugador Humano (Teclado)

Si conectas un emulador o juegas directamente contra la mosca, puedes usar el teclado sin mandos adicionales:

| Acción | Modo WASD (Gamer) | Modo Flechas (Clásico) | Mando GameCube |
|---|---|---|---|
| **Movimiento / Agacharse** | `W` `A` `S` `D` | `↑` `↓` `←` `→` | Stick Principal |
| **Ataque Normal / Selección** | `J` o `Espacio` | `X` o `Espacio` | Botón `A` |
| **Ataque Especial** | `K` | `Z` | Botón `B` |
| **Salto** | `U` o `I` | `C` o `V` | Botón `X` / `Y` |
| **Agarre (Grab)** | `O` | `F` | Botón `Z` |
| **Escudo (Shield)** | `L` | `Q` o `E` | Gatillo `L` / `R` |
| **Start / Pausa** | `Enter` | `Enter` | Botón `Start` |

*(Si conectas un mando de GameCube, Xbox o PlayStation por USB/Bluetooth, el sistema lo detecta y lo configura automáticamente).*

---

## 🧬 Biomecánica y Conectoma 20XX

El modelo biológico no utiliza árboles de decisión simples ni trampas de emulación; las acciones emergen de la dinámica neural:

1. **Fotorreceptores Visuales**: Detectan distancia relativa, velocidad de aproximación y posición de repisas para activar reflejos de esquiva o contragolpe.
2. **Sistema Neuroquímico**:
   - **Dopamina (PAM)**: Se eleva al encadenar golpes y castigos, induciendo tech-chases agresivos y confirms letales.
   - **Octopamina (PPL1)**: Señal de peligro biológico ante daño crítico, activando reseteo neutral y retorno seguro al centro del escenario.
3. **Cerebelo y Memoria Persistente**:
   - Registra patrones en `data/memory/long_term_synapses.json`.
   - Aprende tendencias de rodamiento del rival, castiga opciones repetitivas y optimiza trayectorias de recuperación.
4. **Técnicas Avanzadas Implementadas**:
   - **Luigi**: Wavedash frame-perfect, Sweetspot Up-B Shoryuken Kill Confirm, Chaingrab en fastfallers, Vist whiff punisher, Ledgedash invencible y Down-Taunt Meteor Spike en repisa.
   - **Fox**: Waveshine continuo, Drill-Shine shield pressure, SHDL (*Short Hop Double Laser*) y recuperación calculada con Fox Illusion / Fire Fox.

---

## 🧪 Pruebas y Verificación del Sistema

El proyecto cuenta con una suite integral de **71 pruebas automáticas** que validan la biomecánica, la recuperación anti-suicidios y el subsistema web:

```bash
python3 verify_fixes.py
```
*(Resultado esperado: **71/71 tests superados con éxito**).*

---

## 🚀 Utilidades Avanzadas (Dolphin / Entrenamiento)

Para usuarios avanzados que deseen jugar partidas directas en Dolphin o ejecutar sesiones de entrenamiento acelerado:

```bash
# Lanzador avanzado de Dolphin, mandos y bots
./start_dolphin.sh

# Entrenar 50 partidas aceleradas contra CPU Nivel 9
python3 train_fly.py 50 --character luigi --cpu 9

# Probar la simulación neural en la terminal
python3 test_fly_brain.py
```

---

## 📜 Créditos y Referencias
- **FlyWire Consortium & Princeton Neuroscience Institute**: Mapa del conectoma completo de la *Drosophila melanogaster*.
- **Project Slippi & libmelee**: Puente de emulación y telemetría de Super Smash Bros. Melee a 60 FPS.
