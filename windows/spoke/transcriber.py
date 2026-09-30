"""Envuelve whisper.cpp (vía pywhispercpp) en una cola serial propia, así los
fragmentos se transcriben en orden. Equivalente a Transcriber.swift."""
import queue
import threading
import time

import numpy as np

from . import config

# Frases que Whisper "alucina" sobre silencio o ruido.
HALLUCINATIONS = {
    "gracias.", "gracias", "¡gracias!", "gracias por ver el video.", "gracias por ver.",
    "subtítulos realizados por la comunidad de amara.org",
    "subtítulos por la comunidad de amara.org",
    "¡suscríbete!", "suscríbete al canal.", "thank you.", "thanks for watching!",
    "...", ".",
}


class Transcriber:
    def __init__(self):
        self._model = None
        self._queue: "queue.Queue" = queue.Queue()
        self._thread = threading.Thread(target=self._worker, name="spoke-whisper", daemon=True)
        self._thread.start()

    def load(self, completion) -> None:
        """Carga el modelo en la cola serial. `completion(ok, error)`."""
        self._queue.put(lambda: self._load(completion))

    def _load(self, completion):
        try:
            from pywhispercpp.model import Model
            self._model = Model(
                config.MODEL_PATH,
                context_params={"use_gpu": config.USE_GPU, "flash_attn": True},
                print_progress=False, print_realtime=False,
                print_timestamps=False, print_special=False,
            )
            # Calentamiento: inicializa el backend antes del primer dictado.
            self._run(np.zeros(16_000, dtype=np.float32), None, False)
        except Exception as e:  # modelo ausente, DLL faltante, etc.
            completion(False, e)
            return
        completion(True, None)

    def transcribe(self, samples: np.ndarray, prompt, partial: bool, completion) -> None:
        """Transcribe en la cola serial; llama `completion(texto)` desde el hilo de Whisper."""
        def job():
            t0 = time.time()
            text = self._run(samples, prompt, partial)
            if config.DEBUG:
                print(f"   whisper {'parcial' if partial else 'final'} "
                      f"{len(samples) / config.SAMPLE_RATE:.1f}s de audio → {(time.time() - t0) * 1000:.0f} ms")
            completion(text)
        self._queue.put(job)

    def shutdown(self) -> None:
        done = threading.Event()
        self._queue.put(lambda: (setattr(self, "_model", None), done.set()))
        done.wait(timeout=5)

    def _worker(self):
        while True:
            self._queue.get()()

    def _run(self, samples: np.ndarray, prompt, partial: bool) -> str:
        if self._model is None:
            return ""
        seconds = len(samples) / config.SAMPLE_RATE
        # pywhispercpp conserva los parámetros entre llamadas: se fijan todos cada vez.
        params = dict(
            language=config.LANGUAGE, translate=False, n_threads=config.N_THREADS,
            no_context=True, no_timestamps=True, single_segment=False,
            suppress_blank=True, suppress_nst=True,
            initial_prompt=prompt or "",
            audio_ctx=0, temperature_inc=0.2, max_tokens=0,
        )
        if partial:
            # Ventana de ~15 s en vez de 30 s: pasadas ~2× más rápidas. Ventanas
            # más chicas producen basura. La pasada final usa la ventana completa.
            if seconds <= 14:
                params["audio_ctx"] = 768
            # Una hipótesis mala no importa: la próxima la corrige. Sin reintentos
            # por temperatura y con tope de tokens, una repetición no traba la cola.
            params["temperature_inc"] = 0.0
            params["max_tokens"] = int(seconds * 5 + 8)
        try:
            segments = self._model.transcribe(np.ascontiguousarray(samples, dtype=np.float32), **params)
        except Exception as e:
            if config.DEBUG:
                print("   whisper error:", e)
            return ""
        text = "".join(s.text for s in segments).strip()
        return "" if text.lower() in HALLUCINATIONS else text
