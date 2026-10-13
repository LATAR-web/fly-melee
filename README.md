# 🪰 Fly-Melee: Simulación Biofísica del Conectoma de la Mosca (400k) × Super Smash Bros. Melee

[![Tests Status](https://img.shields.io/badge/Tests-103%2F103%20Passing%20(Militar)-brightgreen.svg)](#-verificación-experimental--tests-103103)
[![Platform](https://img.shields.io/badge/Plataforma-Linux%20%7C%20Windows-blue.svg)](#-instalación-de-dependencias)
[![Simulation Rate](https://img.shields.io/badge/Biofísica-60Hz%20Nativos%20(0.97ms)-blue.svg)](#-ciencia-friki-total-la-neurobiología-computacional-del-proyecto)
[![Neurons](https://img.shields.io/badge/Neuronas%20LIF-395%2C144%20(Princeton%2FFlyWire)-orange.svg)](#-ciencia-friki-total-la-neurobiología-computacional-del-proyecto)
[![Synapses](https://img.shields.io/badge/Sinapsis%20Activas-72.9M%20(CSC%20Sparse)-purple.svg)](#-ciencia-friki-total-la-neurobiología-computacional-del-proyecto)
[![Disrespect Level](https://img.shields.io/badge/Disrespect-Teabagging%20%2B%20Shoryuken-red.svg)](#-el-luigi-insectoide-terror-biológico-en-battlefield)

> ### 🎭 La Paradoja Existencial de Fly-Melee:
> **La Ciencia:** Científicos de Princeton y el consorcio FlyWire invirtieron más de una década cortando cerebros de insectos con microscopía electrónica de barrido (FIB-SEM) para mapear 395,144 neuronas individuales y ~73 millones de sinapsis químicas. Nosotros tomamos ese mapa y resolvimos sistemas de ecuaciones diferenciales estocásticas *Leaky Integrate-and-Fire* (LIF) en tiempo real a 60Hz nativos.
>
> **La Realidad:** Todo ese pináculo de la neurobiología computacional existe con un único propósito en el universo: **que una mosca de la fruta (*Drosophila melanogaster*) de 0.5 miligramos te agarre con Luigi en Battlefield, te meta un *Down-Throw ➔ Wavedash Shoryuken ("PING!")*, te haga un meteoro con la burla y te spamee *teabagging* frame-perfect en la cara.**
>
> *O sea weon, piensa en esto por diez segundos: ES UNA MOSCA. No tiene pulgares. No tiene corteza cerebral. Su cerebro mide menos de un milímetro cúbico. Come fruta fermentada en la basura. Y te acaba de hacer un cuatro-stocks sin despeinarse.*

---

## 🤓 Ciencia Friki Total: La Neurobiología Computacional del Proyecto

¿Por qué no usamos simplemente una IA moderna con *Deep Reinforcement Learning (PPO)* como OpenAI Five o AlphaStar?  
**Porque las redes neuronales artificiales convencionales son cajas negras aburridas.**  
Aquí no hay capas densas arbitrarias con *backpropagation*. **Fly-Melee es una simulación biofísica determinista de un organismo vivo real:**

```
                  ┌────────────────────────────────────────────────────────┐
                  │          ENTORNO SLIPPI (60 FPS / GAMEPLAY MELEE)       │
                  └───────────┬────────────────────────────────┬───────────┘
                              │ Percepción visual              │ Emisión motora
                              ▼ (Looming & Optical Flow)       ▲ (VNC Spikes)
     ┌─────────────────────────────────────────────────────────┴─────────────────────┐
     │           CEREBRO BIOLÓGICO DE LA MOSCA (395,144 NEURONAS LIF)                │
     │                                                                               │
     │  [Lobula Plate (LPTC)] ──> [Giant Fiber DNp01] ──> [Central Complex (CX)]     │
     │     Detección de              Evasión Saccádica        Navegación espacial    │
     │     Amenaza / Looming         y Reacción CQC            y Control de Escenario │
     │            │                         │                         │              │
     │            ▼                         ▼                         ▼              │
     │  ┌─────────────────────────────────────────────────────────────────────────┐  │
     │  │ MODULACIÓN NEUROENDOCRINA:                                              │  │
     │  │ • Dopamina (PAM): Refuerzo de victoria y adicción al combo.              │  │
     │  │ • Octopamina (PPL1): Alarma y aceleración de reflejos offstage.         │  │
     │  │ • Serotonina (5-HT): Spacing paciente en neutral.                       │  │
     │  │ • Acetilcolina (ACh): Potencia muscular (mashing de botón B a 30Hz).     │  │
     │  └─────────────────────────────────────────────────────────────────────────┘  │
     └───────────────────────────────────────────────────────────────────────────────┘
```

### 🔬 1. Ecuaciones Diferenciales LIF (Leaky Integrate-and-Fire)
Cada una de las neuronas se modela mediante integración numérica de voltaje de membrana:

$$\tau_m \frac{dV_i(t)}{dt} = -(V_i(t) - V_{\text{rest}}) + R_m \sum_{j} W_{ij} S_j(t) + I_{\text{ext}}(t)$$

Cuando $V_i(t) \ge V_{\text{threshold}}$, la neurona emite un potencial de acción (*espiga*), resetea su potencial a $V_{\text{reset}}$ y entra en periodo refractario absoluto.

### ⚡ 2. Álgebra Lineal Dispersa Extrema (CSC SpMV)
Un tensor sináptico denso de $395{,}144 \times 395{,}144$ elementos en coma flotante requeriría **más de 624 Gigabytes de memoria RAM**.  
Para resolver la simulación en tiempo real, empaquetamos el conectoma en formato **Compressed Sparse Column (CSC)**. Una multiplicación matriz-vector dispersa (SpMV) sobre **72.9 millones de conexiones** toma apenas **0.97 milisegundos**, lo que deja más de 15 ms libres en cada frame de la Nintendo GameCube.

### 👁️ 3. Transducción de Looming y Circuito Giant Fiber (`DNp01`)
En la naturaleza, si intentas aplastar una mosca con la mano, el circuito de neuronas tangenciales de la placa lobular calcula la tasa de expansión angular $\eta(t) = \theta(t) \cdot \dot{\theta}(t)$. Si el objeto se expande rápidamente hacia la retina, se dispara el axón gigante **Giant Fiber (`DNp01`)**, que activa el salto de escape en menos de 5 milisegundos.  
En Melee, este mismo circuito detecta la aproximación de tu personaje: si entras a quemarropa con un ataque, la mosca no "piensa": **su reflejo biológico ejecuta un Crouch-Cancel Down-Smash instantáneo o un Wavedash-back defensivo.**

---

## 🟢 El Luigi Insectoide: Terror Biológico en Battlefield

¿Por qué Luigi? Porque Luigi tiene una fricción terrestre de **0.005** (básicamente se desliza sobre hielo con mantequilla) y su Up-B Sweetspot tiene una ventana de 1 frame de impacto que suena como una campana de iglesia apocalíptica (*"PING!"*). 

La mosca ha canalizado sus 73 millones de sinapsis en la siguiente batería de humillaciones:

1. **Down-Throw ➔ Wavedash ➔ Sweetspot Shoryuken ("PING!")**:  
   Te agarra en el suelo, calcula la parábola de tu DI con tensores sinápticos, se desliza pegada a ti con Wavedash y te conecta el puño de fuego en la mandíbula. K.O. vertical a partir de 55%.
2. **Jab-Reset ➔ Shoryuken Indefendible**:  
   Fallas un tech en el piso, el insecto te despierta con un Jab Frame-2 que te pone de pie indefenso y te borra de la existencia antes de que puedas tocar el escudo.
3. **Chaingrab Loop a Fastfallers**:  
   Contra Fox, Falco y Captain Falcon, ejecuta una cadena infinita de agarres con Wavedash terrestre hasta dejarte en porcentaje de ejecución.
4. **Down-Taunt Meteor Spike (Frame-45)**:  
   El golpe más insultante del juego. Luigi clava el tacón en la orilla con hitbox activa de 2 frames a 45° hacia abajo; te manda en trayectoria meteórica al fondo del abismo sin posibilidad de recuperarte.
5. **Teabagging Táctico de Alta Frecuencia**:  
   En el momento en que tu personaje es noqueado o cae al abismo sin doble salto, el exceso de dopamina en su red motora desencadena oscilaciones rítmicas en el stick analógico: **teabagging automático de grado militar.**
6. **Rising Cyclone Anti-Ceiling (Cero Suicidios)**:  
   Mashing neuromuscular del botón B a 30Hz que genera sustentación vertical infinita, rescatando a Luigi de debajo de cualquier escenario.
7. **Anti-Pinch Crowd Control (Despeje 360° en FFA)**:  
   Si múltiples enemigos intentan atrapar a Luigi en un ataque simultáneo en pinza ("sándwich"), su reflejo periférico ejecuta de inmediato un *Rising Cyclone 360°* o un *Down-Smash Semi-Spike* bilateral para castigar ambos lados y despejar el área.
8. **Target Selection IQ (Inteligencia FFA Multi-Bot)**:  
   En partidas multijugador Free-For-All, evalúa heurísticamente a todos los contrincantes activos, fijando el objetivo más vulnerable o peligroso, ignorando rivales invulnerables en halo de respawn y eliminando cualquier taunt o distracción prematura.

---

## 🦊 Fox McCloud (Modo Spacie 20XX)

Si cambias a Fox en el panel:
- **Reflector Shine Frame-1 & Waveshine**: Presión de escudo sin huecos de vulnerabilidad.
- **Anti-Pinch Fox Shine 360° Frame-1**: Disparo instantáneo del reflector para neutralizar emboscadas multi-bot coordinadas.
- **Drill-Shine Shield Pressure**: D-Air multihit directo a Shine instantáneo al aterrizar.
- **Running Jump-Cancel Up-Smash**: Castigo en carrera con timing submilisegundo.
- **Powershield Frame-1**: Refleja proyectiles con reflejos de insecto gracias al cluster Giant Fiber.

---

## 🚀 Inicio Rápido: Cómo Jugar en Dolphin & Panel 3D

Para encender el emulador Dolphin, conectar la mosca en el Puerto 1 y abrir el Panel Web 3D en tu navegador:

#### En Linux:
```bash
# ⚡ Modo Recomendado: Ultra-Fluido 60 FPS (0 lag / 470 FPS / 49k neuronas)
./start_fly.sh 5

# O menú interactivo con todas las opciones:
./start_fly.sh
```

#### En Windows (PowerShell):
```powershell
# Habilitar ejecución de scripts locales en PowerShell (solo una vez):
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# ⚡ Modo Recomendado: Ultra-Fluido 60 FPS (0 lag / 470 FPS / 49k neuronas)
.\start_fly.ps1 5

# O menú interactivo con todas las opciones:
.\start_fly.ps1
```
*(Alternativa sin cambiar la directiva: `powershell -ExecutionPolicy Bypass -File .\start_fly.ps1`).*

### ⚡ Tabla Comparativa de Modos de Simulación
| Modo | Neuronas LIF | Sinapsis Activas | Tiempo por Frame | FPS Equivalentes | Dolphin FPS | Diagnóstico |
|---|---|---|---|---|---|---|
| **⚡ Ultra-Fluido (Opción 5)** | **49,393** (1 Cluster) | **~9.05M CSC** | **2.12 ms** | **472 FPS** | **60.0 FPS (0% lag)** | *Modo torneo. La mosca te humilla con suavidad total.* |
| **🧠 Conectoma Completo (Opción 1)** | 395,144 (8 Clusters) | ~73.0M CSC | 6.26 ms | 160 FPS | 58–60 FPS | *Cerebro biológico completo a nivel de investigación.* |

*(Para abrir únicamente el panel web 3D sin Dolphin: `./start_fly.sh --web` en Linux o `.\start_fly.ps1 -Web` en Windows en `http://localhost:8085`).*

#### 🛠️ Scripts y Herramientas Adicionales:
- **Menú Integral Dolphin**: `./start_dolphin.sh` (Linux) o `.\start_dolphin.ps1` (Windows) para modos vs CPU 9, entrenamiento acelerado (`train_fly.py`), test de simulación y descarga rápida de ISOs.
- **Descarga y Verificación de ISO**: `python fast_download.py` verifica la presencia de la ISO oficial de Melee en `data/games/ssbm.iso` y la descarga con 16 hilos si no está presente.
- **Diagnóstico de Mandos**: `./fix_bluetooth_gamepad.sh` (Linux) o `.\fix_bluetooth_gamepad.ps1` (Windows) para diagnosticar mandos USB y Bluetooth.

---

## 📦 Instalación de Dependencias

> [!NOTE]
> **Compatibilidad de Plataforma:** Fly-Melee es compatible de forma nativa con **Linux** y **Windows**.  
> *(macOS no está soportado debido a restricciones de sockets de baja latencia, emulación determinista a 60 FPS y control IPC por pipes).*

### 1. Paquetes del Sistema Operativo

#### Linux
```bash
# Ubuntu / Debian / Pop!_OS
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git build-essential

# Arch Linux / Manjaro
sudo pacman -S python python-pip git base-devel

# Fedora
sudo dnf install -y python3 python3-pip git gcc
```

#### Windows
- Instala **Python 3.10+** desde [python.org](https://www.python.org/) asegurándote de marcar la casilla *"Add Python to PATH"*.
- Instala [Git para Windows](https://git-scm.com/).
- *(Opcional)* [Slippi Desktop App](https://slippi.gg/): Si no lo tienes instalado, Fly-Melee **descargará y configurará automáticamente Slippi Dolphin (Ishiiruka v3.6.4, ~11.6 MB) y su archivo Settings en `%APPDATA%\Slippi Launcher\netplay\`** en el primer inicio.

---

### 2. Clonar y Configurar Entorno Virtual

#### En Linux:
```bash
git clone https://github.com/LATAR-web/fly-melee.git
cd fly-melee

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

#### En Windows (PowerShell o CMD):
```powershell
git clone https://github.com/LATAR-web/fly-melee.git
cd fly-melee

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

> [!TIP]
> **Compatibilidad de dependencias:** `requirements.txt` utiliza marcadores de entorno estándar PEP 508 (`sys_platform == 'linux'` para `evdev`), por lo que en Windows se omiten los encabezados del kernel de Linux y se instalan automáticamente `psutil`, `pygame` y `pywin32` para la gestión de procesos y mandos (XInput/DirectInput).

---

### 3. Obtención de la ISO de Super Smash Bros. Melee (Automática o Manual)

Fly-Melee requiere la imagen de disco de Nintendo GameCube de **Super Smash Bros. Melee** (Versión 1.02 USA / NTSC) ubicada en `data/games/ssbm.iso`.

- **⚡ Descarga Automática (Recomendada)**: Al ejecutar `./start_fly.sh` o `.\start_fly.ps1`, el lanzador comprueba automáticamente si la ISO existe. Si no está en el equipo o está incompleta, ejecutará automáticamente [`fast_download.py`](fast_download.py), descargándola con 16 hilos concurrentes (~1.35 GB) y ubicándola en `data/games/ssbm.iso`. En ejecuciones posteriores, detecta el archivo válido en menos de 0.02s y continúa de inmediato al combate.
- **📥 Descarga Manual Anticipada**: Puedes ejecutar el descargador directamente en cualquier momento:
  ```bash
  # En Linux:
  python3 fast_download.py

  # En Windows:
  python fast_download.py
  ```
- **📁 Si ya tienes tu propia ISO**: Crea la carpeta `data/games` y copia tu copia de Melee renombrada a `ssbm.iso`:
  ```bash
  mkdir -p data/games
  cp /ruta/donde/tengas/tu_juego.iso data/games/ssbm.iso
  ```
  *(O pásala como parámetro directo al ejecutar: `./start_fly.sh --iso /ruta/a/tu_juego.iso`).*

---

## 🎮 Controles para Humanos (Teclado)

Si tienes el coraje de enfrentarte a un insecto de 0.5 miligramos usando tu teclado:

| Acción | Modo WASD (Gamer) | Modo Flechas (Clásico) | Mando GameCube |
|---|---|---|---|
| **Moverse / Agacharse** | `W` `A` `S` `D` | `↑` `↓` `←` `→` | Stick Principal |
| **Ataque Normal (A)** | `J` o `Espacio` | `X` o `Espacio` | Botón `A` |
| **Ataque Especial (B)** | `K` | `Z` | Botón `B` |
| **Salto (Jump)** | `U` o `I` | `C` o `V` | Botón `X` / `Y` |
| **Agarre (Grab)** | `O` | `F` | Botón `Z` |
| **Escudo (Shield)** | `L` | `Q` o `E` | Gatillo `L` / `R` |
| **Pausa / Start** | `Enter` | `Enter` | Botón `Start` |

*(Si conectas un mando de GameCube con adaptador Mayflash, mando de Xbox, Switch Pro o PlayStation, ejecuta `python detect_controller.py` para calibrarlo automáticamente tanto en Linux como en Windows).*

---

## 🧪 Verificación Experimental & Tests (103/103)

La suite de validación biofísica y biomecánica consta de **103 pruebas unitarias automatizadas**:

```bash
# En Linux:
python3 verify_fixes.py

# En Windows:
python verify_fixes.py
```

```text
======================================================================
🎉 ¡TODAS LAS PRUEBAS COMPLETADAS CON ÉXITO! (103/103 SUPERADAS)
======================================================================
```

Cubren:
- Integración temporal LIF $< 10\text{ ms}$ y conservación de memoria sináptica.
- Compatibilidad multiplataforma nativa (Linux y Windows con detección automática).
- Cero suicidios por tracción 0.005 en los bordes y barrera fail-safe de Green Missile.
- Confirmación milimétrica de D-Throw ➔ Shoryuken y Jab-Reset ➔ Up-B.
- Protocolo edge-triggered del mando a 30Hz sin desbordamiento de buffers.
- Homeostasis neuroendocrina con endorfinas, analgesia y Flow State 20XX sin depresión tras perder stocks.
- Target Selection IQ en partidas multijugador Free-For-All (FFA multi-bot) y discriminación de halos invulnerables.
- Anti-Pinch Crowd Control 360° para neutralizar emboscadas simultáneas de múltiples bots.
- Pista mínima para Wavedash (45 unidades) y descenso vertical protegido de plataforma halo post-respawn.

---

## 📚 Documentación Técnica & Whitepapers
- 📄 **[README_TECNICO.md](README_TECNICO.md)**: El Whitepaper definitivo con demostraciones matemáticas, dinámica de clusters y microarquitectura.
- 📖 **[DICCIONARIO_TECNICO.md](DICCIONARIO_TECNICO.md)**: Glosario de la A a la Z que une la neurobiología de Princeton con el Melee competitivo 20XX.

---

## ❓ Preguntas Frecuentes (FAQ Existencial)

**P: ¿Por qué la mosca me hace teabagging si es un insecto?**  
*R: Cuando el oponente es noqueado o cae al abismo, la liberación masiva de dopamina PAM genera descargas bifásicas rítmicas en las neuronas motoras descendentes. Es un subproducto biofísico de la excitación post-victoria... que convenientemente se traduce en el mando como agacharse 15 veces por segundo.*

**P: ¿Tiene la mosca consciencia de lo que está haciendo?**  
*R: No. Para la mosca, la barra de porcentaje de tu Fox es un gradiente de concentración de sacarosa y tu aproximación es un predador que debe ser castigado con un Shoryuken.*

**P: ¿Puedo ganarle a la mosca?**  
*R: Sí, si juegas con espaciado impecable y evitas ser agarrado en el centro del escenario. Si te aproximas a lo loco, la biofísica hará su trabajo.*

**P: ¿Necesito conseguir o configurar la ISO de Melee manualmente?**  
*R: No es necesario. Tanto `./start_fly.sh` (Linux) como `.\start_fly.ps1` (Windows) verifican de forma automática la presencia de `data/games/ssbm.iso`. Si no existe, lanzan el descargador multihilo `fast_download.py` que la descarga en 16 conexiones concurrentes y la deja lista. Si ya tienes tu propia ISO v1.02 NTSC, solo colócala en `data/games/ssbm.iso`.*

---

## 👥 Desarrolladores y Créditos

### 🛠️ Equipo de Desarrollo
- **Desarrollador Principal:** [LATAR](https://github.com/LATAR-web)
- **Desarrollador Secundario:** [Absorbedfish](https://github.com/Absorbedfish)

### 📜 Reconocimientos
- **FlyWire Consortium & Princeton Neuroscience Institute**: Por la titánica reconstrucción del conectoma de *Drosophila melanogaster*.
- **Project Slippi & libmelee**: Por el puente de red determinista a 60 FPS sobre emulación Dolphin.
- **Al Reino Animal**: Por demostrarnos que un insecto de 0.5 miligramos puede jugar Melee mejor que nosotros.

