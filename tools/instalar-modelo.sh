#!/usr/bin/env bash
# Descarga el modelo de Whisper que usa Spoke y verifica su integridad.
#   tools/instalar-modelo.sh
set -euo pipefail

DIR="$HOME/.local/share/whisper"
MODELO="$DIR/ggml-large-v3-turbo.bin"
URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin"
SHA256="1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69"

mkdir -p "$DIR"
if [[ ! -f "$MODELO" ]]; then
  echo "==> Descargando modelo (~1,6 GB)..."
  curl -L --fail -C - -o "$MODELO" "$URL"
fi

echo "==> Verificando SHA-256..."
ACTUAL="$(shasum -a 256 "$MODELO" | cut -d' ' -f1)"
if [[ "$ACTUAL" != "$SHA256" ]]; then
  echo "❌ El checksum no coincide (descarga corrupta). Borrá $MODELO y reintentá."
  exit 1
fi
echo "✅ Modelo listo en $MODELO"
