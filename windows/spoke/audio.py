"""Captura del micrófono (sounddevice / WASAPI) y modo prueba con archivos.
Equivalente a la parte de E/S de AudioCapture.swift; la segmentación vive en
segmenter.py."""
import queue
import subprocess
import threading
import time

import numpy as np

from . import config
from .segmenter import Segmenter


def decode_file(path: str) -> np.ndarray:
    """Decodifica cualquier audio/video a float32 16 kHz mono con ffmpeg."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1",
         "-ar", str(config.SAMPLE_RATE), "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32)


def _resample(x: np.ndarray, src_rate: int) -> np.ndarray:
    """Remuestreo simple a 16 kHz (promedio móvil + interpolación lineal)."""
    if src_rate == config.SAMPLE_RATE or len(x) == 0:
        return x
    k = max(1, int(round(src_rate / config.SAMPLE_RATE)))
    if k > 1:
        x = np.convolve(x, np.ones(k, dtype=np.float32) / k, mode="same")
    n_out = int(len(x) * config.SAMPLE_RATE / src_rate)
    idx = np.linspace(0, len(x) - 1, n_out)
    return np.interp(idx, np.arange(len(x)), x).astype(np.float32)


class AudioCapture:
    def __init__(self, on_partial=None, on_utterance=None, on_level=None):
        self._segmenter = Segmenter(on_partial, on_utterance, on_level)
        self._stream = None
        self._queue: "queue.Queue" = queue.Queue()
        self._src_rate = config.SAMPLE_RATE

    # -- micrófono ---------------------------------------------------------
    def start(self) -> None:
        import sounddevice as sd
        self._segmenter.reset()
        q: "queue.Queue" = queue.Queue()
        self._queue = q
        threading.Thread(target=self._worker, args=(q,), daemon=True).start()

        def callback(indata, frames, t, status):
            q.put(indata[:, 0].copy())

        attempts = []
        try:
            attempts.append(dict(
                rate=config.SAMPLE_RATE, extra=sd.WasapiSettings(auto_convert=True)))
        except Exception:
            pass  # sin WASAPI (no es Windows)
        attempts.append(dict(rate=config.SAMPLE_RATE, extra=None))
        attempts.append(dict(rate=int(sd.query_devices(kind="input")["default_samplerate"]), extra=None))

        last_error = None
        for opt in attempts:
            try:
                stream = sd.InputStream(channels=1, dtype="float32", callback=callback,
                                        samplerate=opt["rate"], blocksize=int(opt["rate"] * 0.03),
                                        extra_settings=opt["extra"])
                stream.start()
            except Exception as e:
                last_error = e
                continue
            self._src_rate = opt["rate"]
            self._stream = stream
            return
        q.put(None)
        raise RuntimeError(f"No se pudo abrir el micrófono: {last_error}")

    def stop(self, completion) -> None:
        """Detiene la captura, entrega el enunciado en curso y llama a
        `completion()` (desde el hilo de audio) después de ese `on_utterance`."""
        stream, self._stream = self._stream, None
        if stream is not None:
            stream.stop()
            stream.close()
        self._queue.put(completion)

    def _worker(self, q: "queue.Queue") -> None:
        while True:
            item = q.get()
            if item is None:
                return
            if callable(item):          # señal de parada
                self._segmenter.flush()
                item()
                return
            self._segmenter.feed(_resample(item, self._src_rate))

    # -- modo prueba ---------------------------------------------------------
    def feed_file(self, path: str, completion) -> None:
        """Reproduce un archivo en tiempo real a través del mismo segmentador."""
        samples = decode_file(path)
        self._segmenter.reset()

        def run():
            chunk = config.SAMPLE_RATE // 10  # 100 ms
            t0 = time.time()
            for i, start in enumerate(range(0, len(samples), chunk)):
                delay = t0 + i * 0.1 - time.time()
                if delay > 0:
                    time.sleep(delay)
                self._segmenter.feed(samples[start:start + chunk])
            self._segmenter.flush()
            completion()

        threading.Thread(target=run, daemon=True).start()
