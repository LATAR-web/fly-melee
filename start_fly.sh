#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/home/ltar/.venvs/pytorch/bin/python"
DEFAULT_ISO="$DIR/data/games/ssbm.iso"

echo "================================================================="
echo "  🪰 CEREBRO DE LA MOSCA (Drosophila 400k) × SUPER SMASH BROS MELEE"
echo "================================================================="
echo "Selecciona una opción:"
echo "  1) Iniciar Panel Web 3D interactivo (http://localhost:8085)"
echo "  2) Ejecutar Test de Simulación Neural en Terminal"
echo "  3) Iniciar Dolphin: Mosca vs Humano (Tú en P2)"
echo "  4) Iniciar Dolphin: Mosca vs Bot CPU Nivel 9 (P2 automático)"
echo "  5) Abrir Slippi Launcher (Dolphin)"
echo "  6) Detectar y Configurar Mando / Gamepad (USB o Bluetooth)"
echo "  7) Arreglar Mando Bluetooth Genérico (Permitir 'Gamepad Android')"
echo "  8) Entrenamiento Neural vs Bots CPU Nivel 9 (50 / 100 partidas)"
echo "  9) Salir"
echo "================================================================="
read -p "Opción [1-9]: " OPT

case $OPT in
  1)
    echo "Iniciando servidor del visualizador 3D..."
    if ! pgrep -f "dashboard_server.py" > /dev/null; then
      nohup "$PYTHON" "$DIR/dashboard_server.py" >/dev/null 2>&1 &
      sleep 2
    fi
    echo "Abriendo navegador en http://localhost:8085 ..."
    nohup xdg-open "http://localhost:8085" >/dev/null 2>&1 &
    ;;
  2)
    echo "Ejecutando simulación biológica en tiempo real..."
    "$PYTHON" "$DIR/test_fly_brain.py"
    ;;
  3)
    echo "Iniciando conexión con Dolphin contra Jugador Humano..."
    if ! pgrep -f "dashboard_server.py" > /dev/null; then
      echo "Iniciando visualizador 3D en segundo plano..."
      nohup "$PYTHON" "$DIR/dashboard_server.py" >/dev/null 2>&1 &
      sleep 1
    fi
    nohup xdg-open "http://localhost:8085" >/dev/null 2>&1 &

    echo "Selecciona personaje de la Mosca:"
    echo "  1) 🟢 Luigi (Wavedash SSS & Shoryuken Kill Confirms) [Recomendado]"
    echo "  2) 🦊 Fox McCloud (20XX Shine & Spacie)"
    read -p "Personaje [1-2] (1): " CHAR_OPT
    FLY_CHAR="luigi"
    if [ "$CHAR_OPT" == "2" ]; then
      FLY_CHAR="fox"
    fi

    if [ -f "$DEFAULT_ISO" ]; then
      echo "📁 Usando ISO oficial verificada: $DEFAULT_ISO"
      ISO_PATH="$DEFAULT_ISO"
    else
      read -p "Ruta a la ISO de Melee (deja en blanco si ya está corriendo en Dolphin): " ISO_PATH
    fi

    if [ -n "$ISO_PATH" ]; then
      "$PYTHON" "$DIR/fly_melee.py" --iso "$ISO_PATH" --character "$FLY_CHAR"
    else
      "$PYTHON" "$DIR/fly_melee.py" --character "$FLY_CHAR"
    fi
    ;;
  4)
    echo "Iniciando conexión con Dolphin contra Bot CPU Nivel 9..."
    if ! pgrep -f "dashboard_server.py" > /dev/null; then
      echo "Iniciando visualizador 3D en segundo plano..."
      nohup "$PYTHON" "$DIR/dashboard_server.py" >/dev/null 2>&1 &
      sleep 1
    fi
    nohup xdg-open "http://localhost:8085" >/dev/null 2>&1 &

    echo "Selecciona personaje de la Mosca:"
    echo "  1) 🟢 Luigi (Wavedash SSS & Shoryuken Kill Confirms) [Recomendado]"
    echo "  2) 🦊 Fox McCloud (20XX Shine & Spacie)"
    read -p "Personaje [1-2] (1): " CHAR_OPT
    FLY_CHAR="luigi"
    if [ "$CHAR_OPT" == "2" ]; then
      FLY_CHAR="fox"
    fi

    if [ -f "$DEFAULT_ISO" ]; then
      echo "📁 Usando ISO oficial verificada: $DEFAULT_ISO"
      ISO_PATH="$DEFAULT_ISO"
    else
      read -p "Ruta a la ISO de Melee: " ISO_PATH
    fi

    if [ -n "$ISO_PATH" ]; then
      "$PYTHON" "$DIR/fly_melee.py" --iso "$ISO_PATH" --cpu 9 --character "$FLY_CHAR"
    else
      "$PYTHON" "$DIR/fly_melee.py" --cpu 9 --character "$FLY_CHAR"
    fi
    ;;
  5)
    if [ -f "$DIR/bin/slippi-launcher.AppImage" ]; then
      "$DIR/bin/slippi-launcher.AppImage" &
    else
      echo "Slippi Launcher aún no encontrado en bin/."
    fi
    ;;
  6)
    echo "Iniciando detector y configurador de mandos..."
    "$PYTHON" "$DIR/detect_controller.py"
    ;;
  7)
    echo "Ejecutando reparador de conexión Bluetooth para mandos genéricos..."
    "$DIR/fix_bluetooth_gamepad.sh"
    ;;
  8)
    echo "================================================================="
    echo "  🧬 ENTRENAMIENTO BIOLÓGICO ACELERADO VS BOTS CPU NIVEL 9"
    echo "================================================================="
    echo "Selecciona el personaje de la Mosca a entrenar:"
    echo "  1) 🟢 Luigi (Wavedash SSS & Shoryuken) [Recomendado]"
    echo "  2) 🦊 Fox (20XX SSS)"
    read -p "Personaje [1-2] (1): " CHAR_OPT
    FLY_CHAR="luigi"
    if [ "$CHAR_OPT" == "2" ]; then
      FLY_CHAR="fox"
    fi

    echo "Selecciona la cantidad de partidas:"
    echo "  1) 50 Partidas (Rápido, ~1.5 seg)"
    echo "  2) 100 Partidas (Profundo con adaptación multi-personaje, ~3 seg)"
    echo "  3) Cantidad personalizada"
    read -p "Opción [1-3] (por defecto 50): " MATCH_OPT
    case $MATCH_OPT in
      2) NUM_MATCHES=100 ;;
      3) read -p "Introduce el número de partidas: " NUM_MATCHES ;;
      *) NUM_MATCHES=50 ;;
    esac
    echo "Ejecutando: python3 train_fly.py $NUM_MATCHES --cpu 9 --character $FLY_CHAR"
    "$PYTHON" "$DIR/train_fly.py" "$NUM_MATCHES" --cpu 9 --character "$FLY_CHAR"
    ;;
  9)
    exit 0
    ;;
  *)
    echo "Opción no válida."
    ;;
esac
