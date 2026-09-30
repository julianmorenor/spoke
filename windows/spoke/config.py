"""Ajustes de Spoke (equivalente a Config.swift). Se pueden sobreescribir con
variables de entorno SPOKE_MODEL, SPOKE_LANGUAGE y SPOKE_HOTKEY."""
import os
from pathlib import Path

MODEL_PATH = os.environ.get(
    "SPOKE_MODEL",
    str(Path.home() / ".local" / "share" / "whisper" / "ggml-large-v3-turbo.bin"),
)
LANGUAGE = os.environ.get("SPOKE_LANGUAGE", "es")

# Atajo global. Formato: modificadores separados por "+" y una tecla.
# Modificadores: alt, ctrl, shift, win. Teclas: space, a-z, 0-9, f1-f12.
HOTKEY = os.environ.get("SPOKE_HOTKEY", "alt+space")

# Segmentación (detección de voz por energía)
SAMPLE_RATE = 16_000
FRAME_MS = 30.0
PARTIAL_INTERVAL_MS = 500.0   # cada cuánto se retranscribe mientras hablás
SILENCE_TO_CUT_MS = 500.0     # pausa que cierra un enunciado
MIN_SPEECH_MS = 250.0         # enunciados más cortos se descartan
MAX_SEGMENT_MS = 15_000.0     # corte forzado si no hay pausas
PRE_ROLL_MS = 240.0           # audio previo al inicio de voz

# Whisper
USE_GPU = os.environ.get("SPOKE_GPU", "1") != "0"
N_THREADS = int(os.environ.get("SPOKE_THREADS", max(1, min(8, (os.cpu_count() or 4) - 2))))
DEBUG = os.environ.get("SPOKE_DEBUG") is not None
