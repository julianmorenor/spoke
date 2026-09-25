#!/usr/bin/env python3
"""Genera el ícono pixel-art de Spoke.

    python3 tools/make_icon.py preview   # compara las opciones → build/icon-options.png
    python3 tools/make_icon.py <opcion>  # genera Resources/AppIcon.icns + ícono de barra de menú
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw

GRID = 16

# '#' = voz (color de acento), '+' = acento claro. Cada opción es 16×16.
OPTIONS = {
    # Onda de voz: barras de distintas alturas, como una voz hablando.
    "onda": [
        "................",
        ".......##.......",
        ".......##.......",
        ".......##.##....",
        "....##.##.##....",
        "....##.##.##.##.",
        ".##.##.##.##.##.",
        ".##.##.##.##.##.",
        ".##.##.##.##.##.",
        ".##.##.##.##.##.",
        "....##.##.##.##.",
        "....##.##.##....",
        ".......##.##....",
        ".......##.......",
        ".......##.......",
        "................",
    ],
    # Globo de diálogo con la onda de voz calada adentro.
    "globo": [
        "................",
        "..############..",
        ".##############.",
        ".##############.",
        ".#######.######.",
        ".#####.#.#.####.",
        ".###.#.#.#.#.##.",
        ".###.#.#.#.#.##.",
        ".#####.#.#.####.",
        ".#######.######.",
        ".##############.",
        "..############..",
        "...###..........",
        "...##...........",
        "...#............",
        "................",
    ],
    # Perfil hablando: la voz sale de la boca en ondas.
    "perfil": [
        "................",
        "..#####.........",
        ".#######........",
        "#########.......",
        "#########.....+.",
        "##########.....+",
        "###########.+..+",
        "#########....+.+",
        "##########.+.+.+",
        "#########..+.+.+",
        "##########.+.+.+",
        "########.....+.+",
        "#######.....+..+",
        ".####..........+",
        ".####.........+.",
        ".####...........",
    ],
}

BG_TOP = (30, 27, 46)
BG_BOTTOM = (18, 16, 28)
ACCENT_TOP = (255, 146, 84)     # naranja
ACCENT_BOTTOM = (255, 84, 122)  # coral/rosa
ACCENT_LIGHT = (255, 214, 170)


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def render_app_icon(name, size=1024):
    """Ícono de app estilo macOS: cuerpo redondeado 824/1024 con la grilla adentro."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    s = size / 1024
    body = (round(100 * s), round(100 * s), round(924 * s), round(924 * s))

    # Fondo con degradé vertical, recortado a rectángulo redondeado.
    bg = Image.new("RGBA", (size, size))
    d = ImageDraw.Draw(bg)
    for y in range(size):
        d.line([(0, y), (size, y)], fill=lerp(BG_TOP, BG_BOTTOM, y / size))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(body, radius=round(185 * s), fill=255)
    img.paste(bg, (0, 0), mask)

    # Píxeles: la grilla de 16 ocupa 640/1024, centrada.
    cell = 40 * s
    origin = 192 * s
    d = ImageDraw.Draw(img)
    rows = OPTIONS[name]
    for y, row in enumerate(rows):
        color = lerp(ACCENT_TOP, ACCENT_BOTTOM, y / (GRID - 1))
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            fill = ACCENT_LIGHT if ch == "+" else color
            x0, y0 = origin + x * cell, origin + y * cell
            d.rectangle([round(x0), round(y0), round(x0 + cell) - 1, round(y0 + cell) - 1], fill=fill)
    return img


def render_template(name, size):
    """Ícono de barra de menú: negro sobre transparente (macOS lo tiñe solo)."""
    scale = size // GRID
    img = Image.new("RGBA", (GRID * scale, GRID * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y, row in enumerate(OPTIONS[name]):
        for x, ch in enumerate(row):
            if ch != ".":
                d.rectangle([x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1], fill=(0, 0, 0, 255))
    return img


def preview():
    names = list(OPTIONS)
    tile, small = 320, 64
    sheet = Image.new("RGBA", (tile * len(names), tile + small + 40), (236, 236, 240, 255))
    for i, name in enumerate(names):
        big = render_app_icon(name).resize((tile, tile), Image.LANCZOS)
        sheet.alpha_composite(big, (i * tile, 0))
        mini = render_app_icon(name).resize((small, small), Image.LANCZOS)
        sheet.alpha_composite(mini, (i * tile + tile // 2 - small // 2, tile + 10))
        ImageDraw.Draw(sheet).text((i * tile + 12, tile + small + 18), name, fill=(40, 40, 40))
    os.makedirs("build", exist_ok=True)
    sheet.save("build/icon-options.png")
    print("build/icon-options.png")


def build(name):
    iconset = "build/AppIcon.iconset"
    os.makedirs(iconset, exist_ok=True)
    master = render_app_icon(name)
    for base in (16, 32, 128, 256, 512):
        for mult in (1, 2):
            px = base * mult
            suffix = "" if mult == 1 else "@2x"
            master.resize((px, px), Image.LANCZOS).save(f"{iconset}/icon_{base}x{base}{suffix}.png")
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", "Resources/AppIcon.icns"], check=True)
    # Barra de menú: 16 pt → 16 px @1x y 32 px @2x, píxeles exactos.
    render_template(name, 16).save("Resources/MenuBarIcon.png")
    render_template(name, 32).save("Resources/MenuBarIcon@2x.png")
    print("Resources/AppIcon.icns, Resources/MenuBarIcon{,@2x}.png")


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    arg = sys.argv[1] if len(sys.argv) > 1 else "preview"
    preview() if arg == "preview" else build(arg)
