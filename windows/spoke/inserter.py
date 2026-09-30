"""Escribe texto en la app que tenga el foco simulando tecleo Unicode
(SendInput + KEYEVENTF_UNICODE). No toca el portapapeles."""
import sys
import time

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    ULONG_PTR = ctypes.c_size_t
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    INPUT_KEYBOARD = 1

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

    class _INPUTUNION(ctypes.Union):
        # Debe incluir MOUSEINPUT (la más grande) para que sizeof(INPUT) sea correcto.
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    _user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    _user32.SendInput.restype = wintypes.UINT
    _user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
    _user32.GetAsyncKeyState.restype = ctypes.c_short

    _MODIFIERS = (0x12, 0x11, 0x10, 0x5B, 0x5C)  # Alt, Ctrl, Shift, Win izq./der.


def _wait_modifiers_released(timeout: float = 1.0) -> None:
    """Si el usuario aún sostiene Alt/Ctrl/Win del atajo, el texto tecleado se
    interpretaría como combinaciones de teclas: se espera a que los suelte."""
    end = time.time() + timeout
    while time.time() < end and any(_user32.GetAsyncKeyState(vk) & 0x8000 for vk in _MODIFIERS):
        time.sleep(0.02)


def type_text(text: str) -> None:
    if sys.platform != "win32":
        raise RuntimeError("TextInserter sólo está implementado para Windows")
    _wait_modifiers_released()
    data = text.encode("utf-16-le")
    units = [int.from_bytes(data[i:i + 2], "little") for i in range(0, len(data), 2)]
    events = []
    for unit in units:
        for flags in (KEYEVENTF_UNICODE, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP):
            inp = INPUT(type=INPUT_KEYBOARD)
            inp.ki = KEYBDINPUT(wVk=0, wScan=unit, dwFlags=flags, time=0, dwExtraInfo=0)
            events.append(inp)
    # En trozos para no saturar la cola de entrada de la app destino.
    step = 64
    for i in range(0, len(events), step):
        chunk = events[i:i + step]
        arr = (INPUT * len(chunk))(*chunk)
        _user32.SendInput(len(chunk), arr, ctypes.sizeof(INPUT))
