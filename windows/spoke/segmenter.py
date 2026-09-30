"""Segmentador de voz (equivalente a la lógica de AudioCapture.swift).

Agrupa audio 16 kHz mono float32 en "enunciados" (voz entre pausas). Mientras
hay voz entrega parciales por `on_partial(id, samples)` cada PARTIAL_INTERVAL_MS
y al detectar la pausa el enunciado completo por `on_utterance(id, samples)`.
No depende del micrófono, así que se prueba con archivos.
"""
from collections import deque

import numpy as np

from . import config


class Segmenter:
    def __init__(self, on_partial=None, on_utterance=None, on_level=None):
        self.on_partial = on_partial
        self.on_utterance = on_utterance
        self.on_level = on_level
        self.frame_len = int(config.SAMPLE_RATE * config.FRAME_MS / 1000)
        self.reset()

    def reset(self):
        self._pending = np.zeros(0, dtype=np.float32)
        self._pre_roll = np.zeros(0, dtype=np.float32)
        self._segment: list[np.ndarray] = []
        self._segment_len = 0
        self._in_speech = False
        self._speech_frames = 0
        self._silence_frames = 0
        self._since_partial = 0
        self._utterance_id = 0
        self._recent_rms: deque[float] = deque(maxlen=100)

    def feed(self, samples: np.ndarray) -> None:
        self._pending = np.concatenate([self._pending, samples.astype(np.float32, copy=False)])
        n = self.frame_len
        while len(self._pending) >= n:
            frame, self._pending = self._pending[:n], self._pending[n:]
            self._process(frame)

    def flush(self) -> None:
        """Cierra el enunciado en curso (al detener la captura)."""
        if self._in_speech:
            self._end_utterance()
        self.reset()

    def _threshold(self, rms: float) -> float:
        # Ruido de fondo = el frame más bajo de los últimos ~3 s.
        self._recent_rms.append(rms)
        return max(min(self._recent_rms) * 3, 0.006)

    def _process(self, frame: np.ndarray) -> None:
        rms = float(np.sqrt(np.mean(frame * frame)))
        is_speech = rms > self._threshold(rms)
        if self.on_level:
            self.on_level(min(1.0, rms * 12))

        if self._in_speech:
            self._segment.append(frame)
            self._segment_len += len(frame)
            self._since_partial += len(frame)
            if is_speech:
                self._speech_frames += 1
                self._silence_frames = 0
            else:
                self._silence_frames += 1

            silence_ms = self._silence_frames * config.FRAME_MS
            segment_ms = self._segment_len / config.SAMPLE_RATE * 1000
            if silence_ms >= config.SILENCE_TO_CUT_MS or segment_ms >= config.MAX_SEGMENT_MS:
                self._end_utterance()
            elif (self._since_partial / config.SAMPLE_RATE * 1000 >= config.PARTIAL_INTERVAL_MS
                  and self._speech_frames * config.FRAME_MS >= config.MIN_SPEECH_MS):
                self._since_partial = 0
                if self.on_partial:
                    self.on_partial(self._utterance_id, self._padded())
        else:
            self._pre_roll = np.concatenate([self._pre_roll, frame])
            max_pre = int(config.SAMPLE_RATE * config.PRE_ROLL_MS / 1000)
            if len(self._pre_roll) > max_pre:
                self._pre_roll = self._pre_roll[-max_pre:]
            if is_speech:
                self._in_speech = True
                self._segment = [self._pre_roll]
                self._segment_len = len(self._pre_roll)
                self._pre_roll = np.zeros(0, dtype=np.float32)
                self._speech_frames = 1
                self._silence_frames = 0
                self._since_partial = 0

    def _end_utterance(self) -> None:
        speech_ms = self._speech_frames * config.FRAME_MS
        # Aunque sea muy corto se entrega vacío: la sesión necesita cerrar el enunciado.
        samples = self._padded() if speech_ms >= config.MIN_SPEECH_MS else np.zeros(0, dtype=np.float32)
        uid = self._utterance_id
        self._utterance_id += 1
        self._segment = []
        self._segment_len = 0
        self._in_speech = False
        self._speech_frames = 0
        self._silence_frames = 0
        self._since_partial = 0
        if self.on_utterance:
            self.on_utterance(uid, samples)

    def _padded(self) -> np.ndarray:
        """Whisper rinde mejor con al menos ~1 s de audio: rellena con silencio."""
        audio = np.concatenate(self._segment) if self._segment else np.zeros(0, dtype=np.float32)
        min_len = int(config.SAMPLE_RATE)
        if len(audio) >= min_len:
            return audio
        return np.concatenate([audio, np.zeros(min_len - len(audio), dtype=np.float32)])
