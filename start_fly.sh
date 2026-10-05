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
  echo "   Crea un entorno e instala dependencias con:"
  echo "     python3 -m venv .venv"
  echo "     source .venv/bin/activate"
  echo "     pip install -r requirements.txt"
  exit 1
fi

PORT=8085
URL="http://localhost:$PORT"

echo "================================================================="
echo "  🪰 CEREBRO DE LA MOSCA (Drosophila 400k) × SUPER SMASH BROS MELEE"
echo "  🌐 Panel Web 3D & Arena en Tiempo Real"
echo "================================================================="

# Iniciar servidor web si no está corriendo
if ! pgrep -f "dashboard_server.py" > /dev/null 2>&1; then
  echo "🚀 Iniciando servidor web (dashboard_server.py)..."
  nohup "$PYTHON" "$DIR/dashboard_server.py" >/dev/null 2>&1 &
  sleep 2
fi

echo "🌐 Abriendo navegador en $URL ..."
if command -v xdg-open > /dev/null 2>&1; then
  nohup xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open > /dev/null 2>&1; then
  nohup open "$URL" >/dev/null 2>&1 &
fi

echo "================================================================="
echo "  ✅ Panel web en línea: $URL"
echo "  ℹ️  Para detener el servidor: pkill -f dashboard_server.py"
echo "================================================================="
