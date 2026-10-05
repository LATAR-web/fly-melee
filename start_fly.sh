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

# Si se pasa --web como argumento, solo abrir el panel web
if [ "$1" == "--web" ]; then
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

# Si se pasan otros argumentos directamente (ej: --cpu 9, --character fox)
if [ $# -gt 0 ]; then
  if ! pgrep -f "dashboard_server.py" > /dev/null 2>&1; then
    nohup "$PYTHON" "$DIR/dashboard_server.py" >/dev/null 2>&1 &
    sleep 1
  fi
  if command -v xdg-open > /dev/null 2>&1; then
    nohup xdg-open "$URL" >/dev/null 2>&1 &
  fi
  exec "$PYTHON" "$DIR/fly_melee.py" --iso "$DEFAULT_ISO" "$@"
fi

echo "================================================================="
echo "  🪰 CEREBRO DE LA MOSCA (Drosophila 400k) × SUPER SMASH BROS MELEE"
echo "================================================================="
echo "¿Cómo quieres jugar?"
echo "  1) 🎮 Jugar tú contra la Mosca (P1: Luigi, P2: Tú con Teclado/Mando) [ENTER]"
echo "  2) 🤖 Ver a la Mosca humillar a un Bot CPU Nivel 9 en Dolphin"
echo "  3) 🦊 Jugar tú contra la Mosca Fox McCloud (20XX Shine)"
echo "  4) 🌐 Solo abrir el Panel Web 3D interactivo (Sin emulador)"
echo "================================================================="

# Esperar 5 segundos; si no responde o da ENTER, arrancar opción 1 por defecto
CHOICE="1"
read -t 5 -p "Opción [1-4] (Inicia juego 1 automáticamente en 5s): " USER_INPUT || true
if [ -n "$USER_INPUT" ]; then
  CHOICE="$USER_INPUT"
fi
echo ""

case "$CHOICE" in
  2)
    echo "🤖 Modo Espectador: Mosca Luigi vs Bot CPU Nivel 9..."
    FLY_CHAR="luigi"
    EXTRA_ARGS="--cpu 9"
    ;;
  3)
    echo "🦊 Modo Desafío 20XX: Jugador Humano vs Mosca Fox..."
    FLY_CHAR="fox"
    EXTRA_ARGS=""
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
  *)
    echo "🎮 Modo Combate: Jugador Humano vs Mosca Luigi..."
    FLY_CHAR="luigi"
    EXTRA_ARGS=""
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
if [ -f "$DEFAULT_ISO" ]; then
  exec "$PYTHON" "$DIR/fly_melee.py" --iso "$DEFAULT_ISO" --character "$FLY_CHAR" $EXTRA_ARGS
else
  exec "$PYTHON" "$DIR/fly_melee.py" --character "$FLY_CHAR" $EXTRA_ARGS
fi
