"""Aplicación de bandeja (equivalente a AppDelegate.swift)."""
import os
import sys
import threading

from . import config
from .audio import AudioCapture
from .dispatcher import Dispatcher
from .hotkey import HotKey
from .hud import HUD
from .inserter import type_text
from .session import DictationSession
from .transcriber import Transcriber
from .tray import Tray

HOTKEY_LABEL = config.HOTKEY.replace("+", " + ").title()


def _single_instance():
    """Evita abrir dos Spoke a la vez (mutex con nombre)."""
    import ctypes
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\SpokeDictation")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return None
    return handle


class App:
    def __init__(self):
        import tkinter as tk
        self._root = tk.Tk()
        self._root.withdraw()
        self.hud = HUD(self._root)
        self.dispatcher = Dispatcher()
        self.transcriber = Transcriber()
        self.capture = AudioCapture(
            on_partial=lambda uid, s: self.dispatcher.post(lambda: self.session and self.session.partial(uid, s)),
            on_utterance=lambda uid, s: self.dispatcher.post(self._utterance(uid, s)),
            on_level=self.hud.push_level,
        )
        self.session = None
        self.model_ready = False
        self.listening = False
        self.finishing = False
        self.status = "Cargando modelo…"
        self.tray = Tray(self._toggle_label, lambda item: self.status, self._request_toggle, self.quit)
        self.hotkey = None

    def _utterance(self, uid, samples):
        def run():
            if self.session:
                self.session.utterance(uid, samples, self._finish_if_done)
        return run

    # -- ciclo de vida ---------------------------------------------------------
    def run(self):
        self.tray.start()
        self.transcriber.load(self._on_model_loaded)
        try:
            self.hotkey = HotKey(config.HOTKEY, self._request_toggle, on_error=self._hotkey_failed)
        except ValueError as e:
            self._set_status(str(e))
        self._root.mainloop()

    def quit(self):
        self.tray.stop()
        if self.hotkey:
            self.hotkey.stop()
        self.transcriber.shutdown()
        self._root.after(0, self._root.quit)

    # -- estado ----------------------------------------------------------------
    def _on_model_loaded(self, ok, error):
        self.model_ready = ok
        if ok:
            self._set_status(f"Listo · {HOTKEY_LABEL}")
        else:
            print("No se pudo cargar el modelo:", error)
            self._set_status(f"No se encontró/cargó el modelo en {config.MODEL_PATH}")
            self.tray.notify(f"No se pudo cargar el modelo: {error}")

    def _hotkey_failed(self, error):
        self._set_status(f"El atajo {HOTKEY_LABEL} está ocupado: cambiá SPOKE_HOTKEY")
        self.tray.notify(f"No se pudo registrar el atajo {HOTKEY_LABEL}: {error}")

    def _set_status(self, text):
        self.status = text
        self.tray.refresh()

    def _toggle_label(self, item):
        return f"{'Detener' if self.listening else 'Dictar'} ({HOTKEY_LABEL})"

    def _update_icon(self):
        self.tray.set_state("listening" if self.listening else "finishing" if self.finishing else "idle")

    # -- sesión de dictado (hilo lógico) -----------------------------------------
    def _request_toggle(self):
        self.dispatcher.post(self._toggle)

    def _toggle(self):
        self._stop() if self.listening else self._start()

    def _start(self):
        if not self.model_ready or self.finishing:
            print("\a", end="")
            return
        try:
            self.capture.start()
        except Exception as e:
            self._set_status(f"Error de micrófono: {e}")
            self.tray.notify(str(e))
            return
        self.listening = True
        self.session = DictationSession(self.transcriber, type_text, self.dispatcher.post)
        self.hud.show()
        self._update_icon()

    def _stop(self):
        self.listening = False
        self.finishing = True
        self.hud.set_phase("finishing")
        self.capture.stop(lambda: self.dispatcher.post(self._finish_if_done))
        self._update_icon()

    def _finish_if_done(self):
        if not self.finishing or not (self.session is None or self.session.is_idle):
            return
        self.finishing = False
        self.hud.hide()
        self._update_icon()


def main():
    if _single_instance() is None:
        return
    App().run()
