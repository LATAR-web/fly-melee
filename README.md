# 🪰 Fly-Melee: Una mosca real partiéndose la madre en Smash Bros Melee jaja

> *"¿Para qué curar enfermedades cuando puedes conectar 400,000 neuronas de una mosca de la fruta a un emulador de GameCube para que le haga Wavedash a la gente en el Melee?"*

Literalmente agarramos el mapa cerebral biológico completo de una mosca de la fruta (*Drosophila melanogaster*, sacado del proyecto FlyWire / Princeton) y se lo enchufamos a Super Smash Bros. Melee para ver qué pasaba. 

El resultado: la mosca aprendió a meter Shoryukens con Luigi a 60 FPS, spamear el Shine de Fox, hacer wavedash con tracción de mantequilla y hacerte burla en la cara. Cero seriedad, 100% diversión, risas y ciencia dudosa.

---

## 🎮 ¿Cómo le pego una paliza a la mosca?

Solo abre la terminal y dale:

```bash
./start_fly.sh
```

Te va a salir un menú chill:
1. **Ver el panel web en vivo**: Abre `http://localhost:8085` para ver el cerebro 3D del bicho iluminándose en tiempo real mientras pelea.
2. **Pelear tú contra la mosca**: Agarra tu teclado o conecta cualquier mando (USB o Bluetooth) y dale con todo (o déjate humillar por un insecto).
3. **Poner a la mosca contra un Bot Nivel 9**: Siéntate con unas palomitas a ver si el cerebro de la mosca se hace un combo contra un Fox de la máquina.
4. **Entrenamiento con esteroides**: La mosca se echa 50 partidas en 2 segundos contra bots para aprender tus mañas y memorizar combos.

---

## 🕹️ Controles pa' no morir en el intento (Tú en el Teclado)

Si no tienes mando de GameCube a mano, puedes jugar con tu teclado tranquilamente:

| ¿Qué quieres hacer? | Modo WASD (Gamer) | Modo Flechitas (Clásico) | Mando GameCube |
|---|---|---|---|
| **Moverte / Agacharte** | `W` `A` `S` `D` | `↑` `↓` `←` `→` | Stick Principal |
| **Pegar piña / Elegir muñeco** | `J` o `Espacio` | `X` o `Espacio` | Botón `A` |
| **Poder especial** | `K` | `Z` | Botón `B` |
| **Saltar** | `U` o `I` | `C` o `V` | Botón `X` / `Y` |
| **Agarrar del pescuezo** | `O` | `F` | Botón `Z` |
| **Escudo protector** | `L` | `Q` o `E` | Gatillo `L` / `R` |
| **Pausa / Empezar** | `Enter` | `Enter` | Botón `Start` |

*(Si conectas un mando de Xbox, PlayStation o GameCube por USB/Bluetooth, el script lo detecta y lo configura solo).*

---

## 🧠 ¿Cómo carajos juega una mosca? (Explicación para mortales)

1. **Ojos de mosca (Fotorreceptores)**: La red calcula a qué velocidad te le estás acercando. Si te le tiras encima a lo loco, se le activan los mismos reflejos de supervivencia que usa para esquivar un periodicazo.
2. **Dopamina al fallo (Modo Depredador)**:
   - Si te conecta un combo o te saca del escenario, se le sube la dopamina al 100% y se pone ultra agresiva a buscar el remate.
   - Si la matas, se le sube la octopamina (el equivalente a que una mosca entre en pánico) y juega a meter escudo y huir al centro.
3. **Memoria biológica**: Guarda en un archivo `.json` tus hábitos. Si siempre ruedas hacia la misma esquina o te levantas igual, la mosca te lee la mente y te mete un Smash cargado.

---

## 🌐 Panel Web Estilo Omarchy (`http://localhost:8085`)

El panel web tiene estética **Omarchy** (limpio, minimalista, tonos esmeralda relajantes, esquinas redondeadas y cero pantallas de hacker de película noventera):
- **Cerebro 3D interactivo**: Puedes girar y hacer zoom al conectoma para ver qué neuronas se encienden cuando salta o ataca.
- **Arena Melee en 2D**: Mira el combate animado en tiempo real sin necesidad de abrir Dolphin.
- **Mando GameCube en vivo**: Se mueven las palancas y los botones en la pantalla mostrando exactamente lo que el cerebro de la mosca manda por el cable.
- **Selector de Personaje**: Haz clic en la insignia superior para alternar en vivo entre el resbaloso **Luigi SSS** y el agresivo **Fox McCloud 20XX**.

---

## 🧪 Pruebas automáticas (por si dudas del código)

Si quieres verificar que todos los circuitos, combos y seguros anti-suicidios están bien:

```bash
/home/ltar/.venvs/pytorch/bin/python verify_fixes.py
```
*(62 de 62 pruebas pasando sin dramas).*

---

## 📜 Cosas nerds & Agradecimientos
Proyecto hecho 100% por diversión y amor al Smash Melee. Basado en los datos de conectoma de FlyWire Consortium / Princeton Neuroscience Institute. Si te gana la mosca en partida rápida, no nos hacemos responsables de tu crisis existencial jaja.
