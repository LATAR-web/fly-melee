#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detectar entorno virtual de Python
if [ -f "$DIR/.venv/bin/python" ]; then
  PYTHON="$DIR/.venv/bin/python"
elif [ -f "/home/ltar/.venvs/pytorch/bin/python" ]; then
  PYTHON="/home/ltar/.venvs/pytorch/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "❌ Error: No se encontró Python 3 instalado."
  echo "   Instálalo y crea un entorno virtual con:"
  echo "     python3 -m venv .venv && source .venv/bin/activate"
  echo "     pip install -r requirements.txt"
  exit 1
fi

DEFAULT_ISO="$DIR/data/games/ssbm.iso"
PORT=8085
URL="http://localhost:$PORT"

# Manejar argumentos directos
if [ "$1" == "--web" ] || [ "$1" == "4" ]; then
  echo "🌐 Iniciando solo panel web en $URL ..."
  if ! pgrep -f "dashboard_server.py" > /dev/null 2>&1; then
    nohup "$PYTHON" "$DIR/dashboard_server.py" >/dev/null 2>&1 &
    sleep 2
  fi
  if command -v xdg-open > /dev/null 2>&1; then
    nohup xdg-open "$URL" >/dev/null 2>&1 &
  elif command -v open > /dev/null 2>&1; then
    nohup open "$URL" >/dev/null 2>&1 &
  fi
  echo "✅ Panel web activo en: $URL"
  exit 0
fi

CHOICE=""
if [ "$1" == "1" ]; then
  CHOICE="1"
elif [ "$1" == "2" ]; then
  CHOICE="2"
elif [ "$1" == "3" ]; then
  CHOICE="3"
elif [ "$1" == "5" ] || [ "$1" == "--lightweight" ] || [ "$1" == "-l" ]; then
  CHOICE="5"
elif [ $# -gt 0 ]; then
  if ! pgrep -f "dashboard_server.py" > /dev/null 2>&1; then
    nohup "$PYTHON" "$DIR/dashboard_server.py" >/dev/null 2>&1 &
    sleep 1
  fi
  if command -v xdg-open > /dev/null 2>&1; then
    nohup xdg-open "$URL" >/dev/null 2>&1 &
  fi
  "$PYTHON" "$DIR/fly_melee.py" --iso "$DEFAULT_ISO" "$@" || true
  exit 0
fi

if [ -z "$CHOICE" ]; then
  echo "================================================================="
  echo "  🪰 CEREBRO DE LA MOSCA (Drosophila) × SUPER SMASH BROS MELEE"
  echo "================================================================="
  echo "¿Cómo quieres jugar?"
  echo "  1) 🎮 Jugar tú contra la Mosca (P1: Luigi, P2: Tú con Teclado/Mando) [ENTER]"
  echo "  2) 🤖 Ver a la Mosca humillar a un Bot CPU Nivel 9 en Dolphin"
  echo "  3) 🦊 Jugar tú contra la Mosca Fox McCloud (20XX Shine)"
  echo "  4) 🌐 Solo abrir el Panel Web 3D interactivo (Sin emulador)"
  echo "  5) ⚡ Modo Ultra-Fluido 60 FPS (49k neuronas / 0 lag / 2ms por frame)"
  echo "================================================================="

  # Esperar 5 segundos; si no responde o da ENTER, arrancar opción 1 por defecto
  CHOICE="1"
  read -t 5 -p "Opción [1-5] (Inicia juego 1 automáticamente en 5s): " USER_INPUT || true
  if [ -n "$USER_INPUT" ]; then
    CHOICE="$USER_INPUT"
  fi
  echo ""
fi

EXTRA_ARGS=""
if [[ "$*" == *"--lightweight"* ]] || [[ "$*" == *"-l"* ]]; then
  EXTRA_ARGS="--lightweight"
fi

case "$CHOICE" in
  2)
    echo "🤖 Modo Espectador: Mosca Luigi vs Bot CPU Nivel 9..."
    FLY_CHAR="luigi"
    EXTRA_ARGS="$EXTRA_ARGS --cpu 9"
    ;;
  3)
    echo "🦊 Modo Desafío 20XX: Jugador Humano vs Mosca Fox..."
    FLY_CHAR="fox"
    ;;
  4)
    echo "🌐 Abriendo solo visualizador web en $URL ..."
    if ! pgrep -f "dashboard_server.py" > /dev/null 2>&1; then
      nohup "$PYTHON" "$DIR/dashboard_server.py" >/dev/null 2>&1 &
      sleep 2
    fi
    if command -v xdg-open > /dev/null 2>&1; then
      nohup xdg-open "$URL" >/dev/null 2>&1 &
    fi
    echo "✅ Panel web activo en: $URL"
    exit 0
    ;;
  5)
    echo "⚡ Modo Ultra-Fluido 60 FPS: Mosca Luigi (49k neuronas, 0 lag)..."
    FLY_CHAR="luigi"
    EXTRA_ARGS="$EXTRA_ARGS --lightweight"
    ;;
  *)
    echo "🎮 Modo Combate: Jugador Humano vs Mosca Luigi..."
    FLY_CHAR="luigi"
    ;;
esac

# 1. Iniciar servidor de telemetría web en segundo plano
if ! pgrep -f "dashboard_server.py" > /dev/null 2>&1; then
  echo "🌐 Iniciando servidor web de telemetría (http://localhost:8085)..."
  nohup "$PYTHON" "$DIR/dashboard_server.py" >/dev/null 2>&1 &
  sleep 1
fi

# 2. Abrir navegador
echo "🌐 Abriendo visualizador web en el navegador..."
if command -v xdg-open > /dev/null 2>&1; then
  nohup xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open > /dev/null 2>&1; then
  nohup open "$URL" >/dev/null 2>&1 &
fi

# 3. Lanzar emulador Dolphin con el juego Melee y la Mosca
echo "🚀 Abriendo emulador Dolphin con Super Smash Bros. Melee..."
while true; do
  if [ -f "$DEFAULT_ISO" ]; then
    "$PYTHON" "$DIR/fly_melee.py" --iso "$DEFAULT_ISO" --character "$FLY_CHAR" $EXTRA_ARGS || true
  else
    "$PYTHON" "$DIR/fly_melee.py" --character "$FLY_CHAR" $EXTRA_ARGS || true
  fi
  echo ""
  echo "================================================================="
  echo "🎮 Sesión de juego finalizada."
  echo "Presiona ENTER para reiniciar la Mosca o escribe 'q' + ENTER para salir:"
  echo "================================================================="
  read -r RESTART_INPUT || break
  if [ "$RESTART_INPUT" == "q" ] || [ "$RESTART_INPUT" == "Q" ]; then
    break
  fi
done
