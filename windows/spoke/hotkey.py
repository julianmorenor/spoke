"""Atajo global con RegisterHotKey (Win32). No requiere permisos especiales."""
import sys
import threading

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
    WM_HOTKEY, WM_QUIT = 0x0312, 0x0012

_MODS = {"alt": 0x1, "ctrl": 0x2, "control": 0x2, "shift": 0x4, "win": 0x8}
_KEYS = {"space": 0x20, "enter": 0x0D, "tab": 0x09, "esc": 0x1B}
_KEYS.update({chr(c): c for c in range(ord("a"), ord("z") + 1)})
_KEYS.update({str(d): 0x30 + d for d in range(10)})
_KEYS.update({f"f{n}": 0x6F + n for n in range(1, 13)})


def parse(spec: str) -> tuple[int, int]:
    """'alt+space' → (modificadores, código de tecla virtual)."""
    parts = [p.strip().lower() for p in spec.split("+") if p.strip()]
    if not parts or parts[-1] not in _KEYS:
        raise ValueError(f"Atajo inválido: {spec!r}")
    mods = 0
    for p in parts[:-1]:
        if p not in _MODS:
            raise ValueError(f"Modificador desconocido: {p!r}")
        mods |= _MODS[p]
    return mods, _KEYS[parts[-1]]


class HotKey:
    def __init__(self, spec: str, action, on_error=None):
        self._mods, self._vk = parse(spec)
        self._action = action
        self._on_error = on_error
        self._thread_id = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="spoke-hotkey", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2)

    def _loop(self):
        self._thread_id = _kernel32.GetCurrentThreadId()
        ok = _user32.RegisterHotKey(None, 1, self._mods | MOD_NOREPEAT, self._vk)
        self._ready.set()
        if not ok:
            if self._on_error:
                self._on_error(ctypes.WinError(ctypes.get_last_error()))
            return
        msg = wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                self._action()
        _user32.UnregisterHotKey(None, 1)

    def stop(self):
        if self._thread_id:
            _user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
