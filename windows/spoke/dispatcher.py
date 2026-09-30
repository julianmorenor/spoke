"""Hilo lógico único: equivale a la cola main de la versión de macOS. La
sesión de dictado y el estado de la app sólo se tocan desde aquí."""
import queue
import threading
import traceback


class Dispatcher:
    def __init__(self):
        self._queue: "queue.Queue" = queue.Queue()
        self._thread = threading.Thread(target=self._loop, name="spoke-logic", daemon=True)
        self._thread.start()

    def post(self, fn) -> None:
        self._queue.put(fn)

    def _loop(self):
        while True:
            fn = self._queue.get()
            if fn is None:
                return
            try:
                fn()
            except Exception:
                traceback.print_exc()

    def stop(self):
        self._queue.put(None)
