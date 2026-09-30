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

La versión de Windows está en [`windows/`](../windows): es un port en **Python**
de la app de macOS. Usa **el mismo modelo** (`ggml-large-v3-turbo.bin`, vía
`pywhispercpp`, que envuelve whisper.cpp) y **la misma lógica** de dictado en
vivo (segmentador por energía + LocalAgreement-2). Cambian sólo las piezas del SO:

| Pieza en macOS (Swift) | Windows (Python) |
|---|---|
| `AudioCapture` (AVFoundation) | `sounddevice` (WASAPI) + `segmenter.py` |
| Atajo global (Carbon) | `RegisterHotKey` (`hotkey.py`) |
| `TextInserter` (CGEvent) | `SendInput` con `KEYEVENTF_UNICODE` (`inserter.py`) |
| HUD (AppKit/SwiftUI) | Ventana `tkinter` sin foco, `WS_EX_NOACTIVATE` (`hud.py`) |
| Ícono de barra de menú | Ícono de bandeja con `pystray` (`tray.py`) |

> **Estado de la validación.** La lógica portable (segmentador, sesión y
> transcripción con el modelo real) se probó end-to-end en macOS con
> `python -m spoke --test` y hay pruebas automáticas (`windows/tests`). Las
> piezas exclusivas de Windows (SendInput, RegisterHotKey, HUD, bandeja,
> WASAPI, instalador) **no se han ejecutado todavía en Windows**: la primera
> vez que se instale en el otro equipo hay que validarlas (ver §3.4).

### 3.1 Instalación (un comando)

En PowerShell, dentro del repo clonado (requiere Git y `winget`, incluido en
Windows 10/11 actuales):

```powershell
winget install Git.Git
git clone <URL-de-este-repo> spoke
cd spoke
powershell -ExecutionPolicy Bypass -File windows\install.ps1 -Autostart
```

El script: busca Python 3.10-3.13 (lo instala con winget si falta), crea
`windows\.venv`, instala las dependencias, instala `ffmpeg` (sólo para
transcribir archivos), descarga y verifica el modelo en
`%USERPROFILE%\.local\share\whisper\`, crea el acceso "Spoke" en el Menú
Inicio (y con `-Autostart`, en el inicio de sesión) y corre `--check`.
Si `-SkipModel`, no descarga el modelo.

Uso: abrí **Spoke** desde el Menú Inicio (o `windows\spoke.bat`). Aparece un
ícono en la bandeja. Apretá **Alt + Espacio**, hablá, y el texto se escribe en
la app con foco; apretá de nuevo para terminar. Si hay problemas:
`windows\spoke-debug.bat` (consola con mensajes) y el log en
`%LOCALAPPDATA%\Spoke\spoke.log`.

### 3.2 Configuración

Variables de entorno (opcionales; o editar `windows/spoke/config.py`):

| Variable | Por defecto | Para qué |
|---|---|---|
| `SPOKE_MODEL` | `~\.local\share\whisper\ggml-large-v3-turbo.bin` | Ruta del modelo |
| `SPOKE_LANGUAGE` | `es` | Idioma |
| `SPOKE_HOTKEY` | `alt+space` | Atajo (`ctrl+alt+d`, `win+shift+s`…) |
| `SPOKE_GPU` | `1` | `0` fuerza CPU |
| `SPOKE_THREADS` | núcleos − 2 (máx. 8) | Hilos de Whisper |
| `SPOKE_DEBUG` | — | Muestra hipótesis parciales y tiempos |

`Alt + Espacio` es también el menú de sistema de las ventanas; si Windows lo
rechaza, la app avisa en la bandeja: usá otro, p. ej. `ctrl+alt+space`.

### 3.3 Rendimiento: GPU o CPU

- La rueda de `pywhispercpp` para Windows que instala pip es **sólo CPU**. Con
  `large-v3-turbo` en CPU las pasadas parciales pueden tardar más de 0,5 s y el
  texto en vivo se atrasa (sigue siendo correcto; la pasada final completa
  todo). Mejora usando un modelo más chico: bajá `ggml-small.bin` de
  <https://huggingface.co/ggerganov/whisper.cpp> y define
  `SPOKE_MODEL` apuntando a él.
- Para **GPU NVIDIA**, compilar `pywhispercpp` con CUDA (necesita Visual Studio
  Build Tools con C++, CMake y CUDA Toolkit):
  ```powershell
  $env:GGML_CUDA = "1"
  windows\.venv\Scripts\pip install --no-binary pywhispercpp --force-reinstall pywhispercpp
  ```
  (Vulkan para AMD/Intel: `GGML_VULKAN=1` con el Vulkan SDK.) Las variables
  exactas pueden variar según la versión de pywhispercpp; revisar su README.
- Si `pip` no encuentra rueda para tu versión de Python y intenta compilar,
  instalá las Build Tools de C++ (`winget install Microsoft.VisualStudio.2022.BuildTools`)
  o usá Python 3.12.

### 3.4 Lista de validación en el equipo Windows

1. `windows\.venv\Scripts\python -m spoke --check` → todo `OK`.
2. `python -m spoke --devices` → aparece tu micrófono.
3. `python -m spoke --test audio.wav` → escribe texto por consola (prueba el motor).
4. Abrir Spoke → ícono en bandeja con "Listo · Alt + Space".
5. Abrir el Bloc de notas, **Alt + Espacio**, hablar → el HUD aparece abajo sin
   robar el foco y el texto se escribe. Probar también acentos y `ñ`.
6. Probar en una app "elevada" (ejecutada como administrador): Windows
   bloquea `SendInput` hacia ellas salvo que Spoke también corra elevado.

### 3.5 Transcribir archivos

```powershell
windows\transcribir.bat reunion.mp4        # -> reunion.txt y reunion.srt
windows\transcribir.bat entrevista.m4a en
```

(Alternativa sin Python: `whisper-cli.exe` de los binarios oficiales de
whisper.cpp con `-m <modelo> -f <wav 16 kHz> -l es --output-txt --output-srt`.)

### 3.6 Limitaciones conocidas

- No se puede teclear en ventanas con privilegios más altos que Spoke (UAC).
- En apps que interceptan `SendInput` Unicode (algunos juegos/escritorios
  remotos) el tecleo puede no llegar.
- Sin ícono `.ico` propio: el de bandeja se genera en código con los mismos
  colores del de macOS.

---

## 4. Solución de problemas

| Síntoma | Causa probable |
|---|---|
| `Falta el modelo` | No se corrió `instalar-modelo`; o la ruta no coincide con `Config.swift` / el script |
| Checksum no coincide | Descarga cortada; borrar el `.bin` y reintentar (el script reanuda con `-C -`) |
| Transcripción lenta | Sin aceleración por GPU; probar un binario CUDA/Vulkan o un modelo más chico |
| Mac: el atajo no escribe | Falta el permiso de **Accesibilidad** |
| Mac: los permisos se pierden al recompilar | Falta el certificado "Spoke Local Signing" (ver `build.sh`) |
