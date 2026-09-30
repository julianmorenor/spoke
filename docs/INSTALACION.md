# Guía de instalación

Cómo dejar Spoke (o al menos su motor de transcripción) funcionando en un
equipo nuevo, con **el mismo modelo** que usamos hoy.

## 1. El modelo: qué es y por qué este

| | |
|---|---|
| Modelo | **Whisper large-v3-turbo** (OpenAI), convertido a formato `ggml` |
| Archivo | `ggml-large-v3-turbo.bin` (~1,6 GB) |
| Origen | <https://huggingface.co/ggerganov/whisper.cpp> |
| SHA-256 | `1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69` |
| Motor | [whisper.cpp](https://github.com/ggml-org/whisper.cpp) (versión con la que se desarrolló: 1.9.2) |
| Idioma | Multilingüe; Spoke lo usa en español (`es`) |

**Justificación de la elección**

- **large-v3-turbo** es casi tan preciso como `large-v3` (el mejor de Whisper)
  pero ~8× más rápido: su decodificador se redujo de 32 a 4 capas. Esa
  velocidad es lo que permite el dictado "en vivo" (pasadas parciales cada
  0,5 s) sin que el texto se atrase.
- Es **multilingüe** y maneja bien el español, a diferencia de los modelos
  `.en`.
- Corre **100 % local**: el audio nunca sale del equipo.
- Alternativas si el otro equipo es modesto (sin GPU o con poca RAM):
  `ggml-medium.bin` (~1,5 GB, más lento) o `ggml-small.bin` (~470 MB, menos
  preciso). Se cambian con la ruta del modelo y no requieren tocar nada más.
  Con menos calidad, el dictado en vivo pierde palabras.

**Requisitos de hardware aproximados**: ~3 GB de RAM libre para el modelo.
Lo ideal es GPU (Metal en Mac, CUDA/Vulkan en Windows); solo con CPU funciona
pero el modo en vivo puede ir lento (sirve igual para transcribir archivos).

> El modelo **no está en el repositorio** (pesa demasiado); se descarga con los
> scripts de abajo y se verifica con el SHA-256.

---

## 2. macOS (Apple Silicon)

```bash
git clone <URL-de-este-repo> spoke && cd spoke

brew install whisper-cpp ffmpeg
tools/instalar-modelo.sh        # descarga y verifica el modelo en ~/.local/share/whisper/

./build.sh --run                # compila, firma, instala en ~/Applications y abre
```

- Requiere Xcode / Command Line Tools (`xcode-select --install`) y Swift 5.10+.
- Permisos la primera vez: **Micrófono** y **Accesibilidad**
  (Configuración del Sistema → Privacidad y seguridad).
- `Package.swift` y `Config.swift` asumen Homebrew en `/opt/homebrew`
  (Apple Silicon). En un Mac Intel hay que cambiar esas rutas a `/usr/local`.
- Verificar el motor sin la app: `tools/transcribir.sh algun-audio.m4a`.

---

## 3. Windows

> **Estado:** la app de dictado (`Sources/Spoke`) está escrita en Swift contra
> APIs de macOS (AppKit, Carbon, AVFoundation), así que **no compila en
> Windows**. Lo que sí se puede usar en Windows hoy es el **mismo modelo y
> motor** (transcripción de archivos). Portar el dictado en vivo
> (atajo global + captura de micrófono + tecleo) es trabajo aparte; ver §3.4.
> Las especificaciones del equipo se definirán al estar en él.

### 3.1 Requisitos previos

Con `winget` (PowerShell):

```powershell
winget install Git.Git
winget install Gyan.FFmpeg
```

Reiniciá la terminal para que `git` y `ffmpeg` queden en el `PATH`.

### 3.2 Descargar el modelo

```powershell
git clone <URL-de-este-repo> spoke
cd spoke
powershell -ExecutionPolicy Bypass -File tools\instalar-modelo.ps1
```

Queda en `%USERPROFILE%\.local\share\whisper\ggml-large-v3-turbo.bin` y se
verifica con SHA-256.

### 3.3 Obtener `whisper-cli.exe`

Elegí **una** opción según el hardware:

**a) Binarios oficiales (lo más simple).** En
<https://github.com/ggml-org/whisper.cpp/releases> descargá el zip de Windows:

- `whisper-bin-x64.zip` → solo CPU.
- `whisper-cublas-*-bin-x64.zip` → GPU NVIDIA (CUDA). Es la mejor opción si hay
  tarjeta NVIDIA.

Descomprimilo (p. ej. en `C:\whisper`) y agregá esa carpeta al `PATH`. Los
nombres de los zips cambian entre versiones: si no aparecen, usá la opción b.

**b) Compilar desde el código fuente** (permite elegir backend):

```powershell
winget install Kitware.CMake
winget install Microsoft.VisualStudio.2022.BuildTools   # con "Desarrollo para el escritorio con C++"
git clone https://github.com/ggml-org/whisper.cpp
cd whisper.cpp
cmake -B build                       # CPU
# cmake -B build -DGGML_CUDA=1       # NVIDIA (requiere CUDA Toolkit)
# cmake -B build -DGGML_VULKAN=1     # AMD / Intel (requiere Vulkan SDK)
cmake --build build -j --config Release
# el ejecutable queda en build\bin\Release\whisper-cli.exe
```

### 3.4 Probar la transcripción

```powershell
$m = "$env:USERPROFILE\.local\share\whisper\ggml-large-v3-turbo.bin"
ffmpeg -y -i reunion.m4a -ar 16000 -ac 1 -c:a pcm_s16le reunion.wav
whisper-cli -m $m -f reunion.wav -l es -pp --output-txt --output-srt --output-vtt --output-file reunion
```

Es lo mismo que hace `tools/transcribir.sh` en Mac. (`tools/transcribir.sh`
también corre en Windows dentro de **Git Bash** o **WSL**, pero usa la ruta del
modelo de Unix; en Git Bash funciona porque `$HOME` apunta al perfil.)

### 3.5 Dictado en vivo en Windows (pendiente)

Para tener lo mismo que la app de Mac habría que portar cuatro piezas; el
modelo y la lógica de `DictationSession` (LocalAgreement-2) se reutilizan:

| Pieza en Mac | Equivalente en Windows |
|---|---|
| `AudioCapture` (AVFoundation) | WASAPI / `sounddevice` / NAudio |
| Atajo global (Carbon) | `RegisterHotKey` (Win32) |
| `TextInserter` (CGEvent) | `SendInput` con `KEYEVENTF_UNICODE` |
| HUD (AppKit) | Ventana WPF/WinUI sin foco (`WS_EX_NOACTIVATE`) |

Decidir el stack (Python + `whisper.cpp`/`pywhispercpp`, C#, Rust…) cuando
estemos en ese equipo, según sus especificaciones.

---

## 4. Solución de problemas

| Síntoma | Causa probable |
|---|---|
| `Falta el modelo` | No se corrió `instalar-modelo`; o la ruta no coincide con `Config.swift` / el script |
| Checksum no coincide | Descarga cortada; borrar el `.bin` y reintentar (el script reanuda con `-C -`) |
| Transcripción lenta | Sin aceleración por GPU; probar un binario CUDA/Vulkan o un modelo más chico |
| Mac: el atajo no escribe | Falta el permiso de **Accesibilidad** |
| Mac: los permisos se pierden al recompilar | Falta el certificado "Spoke Local Signing" (ver `build.sh`) |
