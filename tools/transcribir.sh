#!/usr/bin/env bash
# Transcribe un archivo de audio o video con el mismo modelo que usa Spoke.
#
#   tools/transcribir.sh reunion.m4a [idioma]      # idioma por defecto: es
#
# Genera, junto al archivo original: <nombre>.txt, <nombre>.srt y <nombre>.vtt
set -euo pipefail

MODELO="$HOME/.local/share/whisper/ggml-large-v3-turbo.bin"
ENTRADA="${1:-}"
IDIOMA="${2:-es}"

if [[ -z "$ENTRADA" ]]; then
  echo "Uso: $0 <audio-o-video> [idioma]"
  exit 1
fi
[[ -f "$ENTRADA" ]] || { echo "No encuentro el archivo: $ENTRADA"; exit 1; }
[[ -f "$MODELO" ]] || { echo "Falta el modelo: $MODELO (ver README)"; exit 1; }

BASE="${ENTRADA%.*}"
WAV="$(mktemp -t spoke).wav"
trap 'rm -f "$WAV"' EXIT

echo "==> Convirtiendo a WAV 16 kHz mono..."
ffmpeg -y -i "$ENTRADA" -ar 16000 -ac 1 -c:a pcm_s16le "$WAV" -hide_banner -loglevel error

echo "==> Transcribiendo (large-v3-turbo, idioma $IDIOMA)..."
whisper-cli -m "$MODELO" -f "$WAV" -l "$IDIOMA" -pp \
  --output-txt --output-srt --output-vtt --output-file "$BASE"

echo "==> Listo: ${BASE}.txt  ${BASE}.srt  ${BASE}.vtt"
