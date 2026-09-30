"""Ícono en la bandeja del sistema (pystray)."""
from PIL import Image, ImageDraw

ORANGE = (255, 146, 84)
CORAL = (255, 84, 122)
STATES = {"idle": None, "listening": (220, 38, 38), "finishing": (245, 158, 11)}


def make_icon(state: str = "idle", size: int = 64) -> Image.Image:
    """Cuadrado redondeado con degradado y onda de voz (mismos colores que el ícono de macOS)."""
    solid = STATES.get(state)
    bg = Image.new("RGBA", (size, size))
    px = bg.load()
    for x in range(size):
        t = x / (size - 1)
        c = solid or tuple(int(ORANGE[i] + (CORAL[i] - ORANGE[i]) * t) for i in range(3))
        for y in range(size):
            px[x, y] = (*c, 255)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=size // 4, fill=255)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(bg, (0, 0), mask)
    d = ImageDraw.Draw(img)
    heights = [0.25, 0.5, 0.8, 0.5, 0.3, 0.6, 0.25]
    bar_w = size * 0.07
    pitch = size * 0.115
    x0 = size / 2 - pitch * (len(heights) - 1) / 2
    for i, h in enumerate(heights):
        x = x0 + i * pitch
        half = size * h / 2 * 0.75
        d.rounded_rectangle((x - bar_w, size / 2 - half, x + bar_w, size / 2 + half),
                            radius=bar_w, fill="white")
    return img


class Tray:
    def __init__(self, label_fn, status_fn, on_toggle, on_quit):
        import pystray
        self._pystray = pystray
        menu = pystray.Menu(
            pystray.MenuItem(label_fn, lambda icon, item: on_toggle(), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(status_fn, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir", lambda icon, item: on_quit()),
        )
        self._icon = pystray.Icon("Spoke", make_icon("idle"), "Spoke", menu)

    def start(self):
        self._icon.run_detached()

    def set_state(self, state: str):
        self._icon.icon = make_icon(state)
        self._icon.update_menu()

    def refresh(self):
        self._icon.update_menu()

    def notify(self, message: str):
        try:
            self._icon.notify(message, "Spoke")
        except Exception:
            pass

    def stop(self):
        self._icon.stop()
