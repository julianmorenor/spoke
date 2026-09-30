# Spoke

> **Estado:** la versión de macOS (Swift) es la principal y está probada. La de
> Windows (`windows/`) es un port en Python cuya lógica se probó en macOS, pero
> las piezas propias de Windows (tecleo, atajo, HUD, bandeja, micrófono) aún no
> se han validado en un equipo real: se agradecen reportes.

Dictado por voz 100 % local para macOS, con Whisper (whisper.cpp + Metal).
Apretás **⌥ Space**, hablás, y el texto se va escribiendo **mientras hablás**
en la app que tenga el foco. Apretás ⌥ Space de nuevo para terminar.

## Cómo funciona

```
micrófono → 16 kHz mono → enunciados (voz entre pausas)
          → pasadas parciales cada 0.5 s → palabras estables → tecleo Unicode
          → pasada final en la pausa → completa lo que falte
```

- `AudioCapture` agrupa el audio en enunciados (VAD por energía, con piso de
  ruido adaptativo) y entrega el audio parcial del enunciado en curso.
- `DictationSession` escribe en vivo con *LocalAgreement-2*: una palabra se
  escribe cuando dos pasadas seguidas coinciden, así nunca hay que borrar. La
  pasada final del enunciado (ventana completa, máxima calidad) completa el resto.
- `Transcriber` envuelve whisper.cpp en una cola serial. Las parciales usan
  `audio_ctx = 768` (~0.5 s por pasada); ventanas más chicas producen basura.
- `TextInserter` escribe simulando teclas (no toca el portapapeles).
- `HUD` es la píldora flotante con la onda de voz; nunca roba el foco.

## Requisitos

```bash
brew install whisper-cpp ffmpeg
tools/instalar-modelo.sh   # descarga y verifica ggml-large-v3-turbo.bin (~1,6 GB)
```

> Guía completa (justificación del modelo, macOS y Windows):
> **[docs/INSTALACION.md](docs/INSTALACION.md)**

## Windows

Port en Python (mismo modelo, misma lógica de dictado) en [`windows/`](windows):

```powershell
powershell -ExecutionPolicy Bypass -File windows\install.ps1 -Autostart
```

Detalles, rendimiento y lista de validación en [docs/INSTALACION.md](docs/INSTALACION.md#3-windows).

## Compilar e instalar (macOS)

```bash
./build.sh --run     # compila, firma, instala en ~/Applications y abre
```

La firma usa el certificado local "Spoke Local Signing" (llavero de login)
para que macOS recuerde los permisos entre recompilaciones.

Permisos necesarios (la primera vez): **Micrófono** y **Accesibilidad**
(Configuración del Sistema → Privacidad y seguridad).

## Probar sin micrófono ni UI

```bash
swift build -c release
.build/release/Spoke --test audio.wav              # reproduce en tiempo real y muestra qué se escribe y cuándo
SPOKE_DEBUG=1 .build/release/Spoke --test audio.wav  # + hipótesis parciales y tiempos de Whisper
.build/release/Spoke --hud-snapshot hud.png        # render del HUD para revisar el diseño
```

## Transcribir archivos

Para audios o videos grabados (reuniones, notas de voz), con el mismo modelo:

```bash
tools/transcribir.sh reunion.m4a        # → reunion.txt, reunion.srt, reunion.vtt
tools/transcribir.sh interview.mp4 en   # otro idioma
```

## Ícono

`python3 tools/make_icon.py preview` compara diseños; `python3 tools/make_icon.py onda`
genera `Resources/AppIcon.icns` y el ícono de la barra de menú.

## Pendiente

- Puntuación: en modo en vivo faltan comas y puntos (las palabras se escriben
  antes de que Whisper decida la puntuación).

## Ajustes

Todo en `Sources/Spoke/Config.swift`: atajo, idioma, ruta del modelo,
duración de la pausa que corta un fragmento, etc.

## Licencia y créditos

[MIT](LICENSE). Usa [whisper.cpp](https://github.com/ggml-org/whisper.cpp) y el
modelo [Whisper](https://github.com/openai/whisper) de OpenAI (ambos MIT). El
modelo no se distribuye con este repositorio: se descarga con
`tools/instalar-modelo.*`.

## Privacidad

Todo el procesamiento es local: el audio no sale de tu equipo. Spoke escribe el
texto en la ventana que tenga el foco (incluidos campos de contraseña), así que
verifica dónde está el foco antes de dictar.
