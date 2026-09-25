# Spoke

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
brew install whisper-cpp
mkdir -p ~/.local/share/whisper
curl -L -o ~/.local/share/whisper/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

## Compilar e instalar

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

## Ícono

`python3 tools/make_icon.py preview` compara diseños; `python3 tools/make_icon.py onda`
genera `Resources/AppIcon.icns` y el ícono de la barra de menú.

## Pendiente

- Puntuación: en modo en vivo faltan comas y puntos (las palabras se escriben
  antes de que Whisper decida la puntuación).

## Ajustes

Todo en `Sources/Spoke/Config.swift`: atajo, idioma, ruta del modelo,
duración de la pausa que corta un fragmento, etc.
