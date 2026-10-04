#!/bin/bash
# Script para habilitar mandos genéricos Bluetooth (Gamepad Android / Ipega / Terios / clones)
# Soluciona el error: "Rejected connection from !bonded device" en BlueZ

echo "=================================================================="
echo "  🔧 REPARADOR DE MANDOS BLUETOOTH GENÉRICOS EN LINUX"
echo "=================================================================="

if [ "$EUID" -ne 0 ]; then
  echo "Solicitando permisos de administrador para ajustar /etc/bluetooth/input.conf..."
  sudo "$0" "$@"
  exit $?
fi

INPUT_CONF="/etc/bluetooth/input.conf"

if [ -f "$INPUT_CONF" ]; then
  echo "⚙️ Configurando ClassicBondedOnly=false en $INPUT_CONF ..."
  sed -i 's/#ClassicBondedOnly=true/ClassicBondedOnly=false/g' "$INPUT_CONF"
  sed -i 's/ClassicBondedOnly=true/ClassicBondedOnly=false/g' "$INPUT_CONF"
  
  if ! grep -q "ClassicBondedOnly=false" "$INPUT_CONF"; then
    echo -e "\n[General]\nClassicBondedOnly=false" >> "$INPUT_CONF"
  fi
  
  echo "🔄 Reiniciando servicio Bluetooth..."
  systemctl restart bluetooth
  sleep 2
  echo "✅ ¡Configuración aplicada con éxito!"
else
  echo "❌ No se encontró $INPUT_CONF"
fi

echo "=================================================================="
echo "👉 Ahora presiona cualquier botón de tu mando para reconectarlo,"
echo "   o ejecútalo en 'start_fly.sh' (Opción 6) para probar los botones."
echo "=================================================================="
