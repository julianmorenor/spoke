"""Píldora flotante abajo al centro con la onda de la voz (tkinter). Nunca
toma el foco (WS_EX_NOACTIVATE), así el texto sigue yendo a la app en la que
estás escribiendo. Tk sólo se toca desde el hilo principal; los demás hilos
mandan comandos por una cola."""
import queue
import sys
from collections import deque

BAR_COUNT = 18
W, H = 150, 40
ORANGE = (255, 146, 84)
CORAL = (255, 84, 122)
TRANSPARENT = "#010203"


def _hex(c):
    return "#%02x%02x%02x" % tuple(int(v) for v in c)


class HUD:
    def __init__(self, root):
        import tkinter as tk
        self._tk = tk
        self._root = root
        self._cmds: "queue.Queue" = queue.Queue()
        self._levels = deque([0.0] * BAR_COUNT, maxlen=BAR_COUNT)
        self._phase = "listening"
        self._visible = False

        win = tk.Toplevel(root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=TRANSPARENT)
        if sys.platform == "win32":
            win.attributes("-transparentcolor", TRANSPARENT)
        self._win = win
        self._canvas = tk.Canvas(win, width=W, height=H, bg=TRANSPARENT, highlightthickness=0)
        self._canvas.pack()
        self._draw_background()
        self._bars = [self._canvas.create_line(0, 0, 0, 0, width=3, capstyle="round", fill="white")
                      for _ in range(BAR_COUNT)]
        self._render()
        root.after(30, self._poll)

    # -- API segura desde cualquier hilo ---------------------------------------
    def show(self): self._cmds.put(("show",))
    def hide(self): self._cmds.put(("hide",))
    def push_level(self, level: float): self._cmds.put(("level", level))
    def set_phase(self, phase: str): self._cmds.put(("phase", phase))

    # -- interno (hilo de Tk) --------------------------------------------------
    def _draw_background(self):
        """Cápsula con degradado horizontal naranja → coral, dibujada por columnas."""
        r = H / 2
        for x in range(W):
            t = x / (W - 1)
            color = _hex([ORANGE[i] + (CORAL[i] - ORANGE[i]) * t for i in range(3)])
            if x < r:
                dx = r - x - 0.5
            elif x > W - r:
                dx = x - (W - r) + 0.5
            else:
                dx = 0
            half = (r * r - dx * dx) ** 0.5 if dx < r else 0
            self._canvas.create_line(x, r - half, x, r + half + 1, fill=color)

    def _render(self):
        listening = self._phase == "listening"
        fill = "#ffffff" if listening else "#ffd9c9"
        pitch = 6
        x0 = (W - (BAR_COUNT - 1) * pitch) / 2
        for i, level in enumerate(self._levels):
            half = (4 + level * 22) / 2 if listening else 2
            x = x0 + i * pitch
            self._canvas.coords(self._bars[i], x, H / 2 - half, x, H / 2 + half)
            self._canvas.itemconfigure(self._bars[i], fill=fill)

    def _place(self):
        self._win.update_idletasks()
        sw, sh = self._root.winfo_screenwidth(), self._root.winfo_screenheight()
        # Barra de tareas ≈ 48 px: la píldora queda justo encima.
        self._win.geometry(f"{W}x{H}+{(sw - W) // 2}+{sh - H - 76}")

    def _set_noactivate(self):
        if sys.platform != "win32":
            return
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(self._win.winfo_id()) or self._win.winfo_id()
        GWL_EXSTYLE = -20
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        # NOACTIVATE | TOOLWINDOW (sin botón en la barra de tareas) | TRANSPARENT (clics pasan)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | 0x08000000 | 0x80 | 0x20)

    def _poll(self):
        dirty = False
        try:
            while True:
                cmd = self._cmds.get_nowait()
                if cmd[0] == "show":
                    self._phase = "listening"
                    self._levels.extend([0.0] * BAR_COUNT)
                    self._place()
                    self._win.deiconify()
                    self._set_noactivate()
                    self._win.attributes("-topmost", True)
                    self._visible = dirty = True
                elif cmd[0] == "hide":
                    self._win.withdraw()
                    self._visible = False
                elif cmd[0] == "level":
                    self._levels.append(cmd[1])
                    dirty = True
                elif cmd[0] == "phase":
                    self._phase = cmd[1]
                    dirty = True
        except queue.Empty:
            pass
        if dirty and self._visible:
            self._render()
        self._root.after(30, self._poll)
