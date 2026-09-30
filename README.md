# Spoke

**English** · [Español](#-español)

100 % local voice dictation powered by Whisper. Press a hotkey, speak, and the
text is typed **as you speak** into whatever app has focus. Nothing leaves your
computer.

> **Status:** the macOS version (Swift) is the main one and is tested. The
> Windows version (`windows/`) is a Python port; its core logic was tested on
> macOS, but the Windows-specific parts (typing, hotkey, HUD, tray, microphone)
> have not been validated on a real Windows machine yet. Reports are welcome.

## How it works

```
microphone → 16 kHz mono → utterances (speech between pauses)
           → partial passes every 0.5 s → stable words → Unicode typing
           → final pass at the pause → fills in whatever is missing
```

- Energy-based voice detection with an adaptive noise floor splits audio into utterances.
- Live typing uses *LocalAgreement-2*: a word is typed once two consecutive
  passes agree on it, so text never has to be deleted. The final pass over the
  whole utterance completes the rest.
- Text is typed by simulating keystrokes (the clipboard is never touched).
- A floating pill shows your voice level and never steals focus.

**Model:** Whisper `large-v3-turbo` (ggml, ~1.6 GB) via
[whisper.cpp](https://github.com/ggml-org/whisper.cpp). Near `large-v3`
accuracy at ~8× the speed, which is what makes live dictation possible.
It is not bundled: the install scripts download it and verify its SHA-256.

## Install

**macOS (Apple Silicon)** — hotkey **⌥ Space**

```bash
git clone https://github.com/julianmorenor/spoke && cd spoke
brew install whisper-cpp ffmpeg
tools/instalar-modelo.sh     # downloads + verifies the model
./build.sh --run             # builds, installs to ~/Applications, opens
```

Grant **Microphone** and **Accessibility** permissions on first run.

**Windows** — hotkey **Alt + Space** (Python port, see status above)

```powershell
git clone https://github.com/julianmorenor/spoke
cd spoke
powershell -ExecutionPolicy Bypass -File windows\install.ps1 -Autostart
```

Full guide (model rationale, GPU/CPU notes, validation checklist, config
variables): [docs/INSTALACION.md](docs/INSTALACION.md) *(written in Spanish)*.

## Transcribe files

```bash
tools/transcribir.sh meeting.m4a        # → meeting.txt, .srt, .vtt (macOS)
windows\transcribir.bat meeting.mp4     # → meeting.txt, .srt (Windows)
```

## Privacy

All processing is local: audio never leaves your machine. Spoke types into the
focused window (including password fields), so check where focus is before
dictating.

## License & credits

[MIT](LICENSE). Uses [whisper.cpp](https://github.com/ggml-org/whisper.cpp) and
OpenAI's [Whisper](https://github.com/openai/whisper) model (both MIT).

---

## 🇪🇸 Español

> **Estado:** la versión de macOS (Swift) es la principal y está probada. La de
> Windows (`windows/`) es un port en Python cuya lógica se probó en macOS, pero
> las piezas propias de Windows (tecleo, atajo, HUD, bandeja, micrófono) aún no
> se han validado en un equipo real: se agradecen reportes.

Dictado por voz 100 % local para macOS, con Whisper (whisper.cpp + Metal).
Apretás **⌥ Space**, hablás, y el texto se va escribiendo **mientras hablás**
en la app que tenga el foco. Apretás ⌥ Space de nuevo para terminar.

### Cómo funciona

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

### Requisitos

```bash
brew install whisper-cpp ffmpeg
tools/instalar-modelo.sh   # descarga y verifica ggml-large-v3-turbo.bin (~1,6 GB)
```

> Guía completa (justificación del modelo, macOS y Windows):
> **[docs/INSTALACION.md](docs/INSTALACION.md)**

### Windows

Port en Python (mismo modelo, misma lógica de dictado) en [`windows/`](windows):

```powershell
powershell -ExecutionPolicy Bypass -File windows\install.ps1 -Autostart
```

Detalles, rendimiento y lista de validación en [docs/INSTALACION.md](docs/INSTALACION.md#3-windows).

### Compilar e instalar (macOS)

```bash
./build.sh --run     # compila, firma, instala en ~/Applications y abre
```

La firma usa el certificado local "Spoke Local Signing" (llavero de login)
para que macOS recuerde los permisos entre recompilaciones.

Permisos necesarios (la primera vez): **Micrófono** y **Accesibilidad**
(Configuración del Sistema → Privacidad y seguridad).

### Probar sin micrófono ni UI

```bash
swift build -c release
.build/release/Spoke --test audio.wav              # reproduce en tiempo real y muestra qué se escribe y cuándo
SPOKE_DEBUG=1 .build/release/Spoke --test audio.wav  # + hipótesis parciales y tiempos de Whisper
.build/release/Spoke --hud-snapshot hud.png        # render del HUD para revisar el diseño
```

### Transcribir archivos

Para audios o videos grabados (reuniones, notas de voz), con el mismo modelo:

```bash
tools/transcribir.sh reunion.m4a        # → reunion.txt, reunion.srt, reunion.vtt
tools/transcribir.sh interview.mp4 en   # otro idioma
```

### Ícono

`python3 tools/make_icon.py preview` compara diseños; `python3 tools/make_icon.py onda`
genera `Resources/AppIcon.icns` y el ícono de la barra de menú.

### Pendiente

- Puntuación: en modo en vivo faltan comas y puntos (las palabras se escriben
  antes de que Whisper decida la puntuación).

### Ajustes

Todo en `Sources/Spoke/Config.swift`: atajo, idioma, ruta del modelo,
duración de la pausa que corta un fragmento, etc.

### Licencia y créditos

[MIT](LICENSE). Usa [whisper.cpp](https://github.com/ggml-org/whisper.cpp) y el
modelo [Whisper](https://github.com/openai/whisper) de OpenAI (ambos MIT). El
modelo no se distribuye con este repositorio: se descarga con
`tools/instalar-modelo.*`.

### Privacidad

Todo el procesamiento es local: el audio no sale de tu equipo. Spoke escribe el
texto en la ventana que tenga el foco (incluidos campos de contraseña), así que
verifica dónde está el foco antes de dictar.
