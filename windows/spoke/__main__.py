"""Punto de entrada.

  python -m spoke                 app de bandeja (Windows)
  python -m spoke --test a.wav    reproduce el audio en tiempo real y muestra qué se escribiría y cuándo
  python -m spoke --transcribe a.mp4 [es]   transcribe un archivo → a.txt y a.srt
  python -m spoke --devices       lista los micrófonos
  python -m spoke --check         verifica modelo, ffmpeg y dependencias
"""
import os
import shutil
import sys
import threading
import time
from pathlib import Path


def _redirect_output_if_windowless():
    """Con pythonw.exe no hay consola: los mensajes van a un archivo de log."""
    if sys.stdout is None or sys.stderr is None:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Spoke"
        base.mkdir(parents=True, exist_ok=True)
        log = open(base / "spoke.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log


def run_file_test(path: str) -> None:
    from . import config
    from .audio import AudioCapture
    from .dispatcher import Dispatcher
    from .session import DictationSession
    from .transcriber import Transcriber

    dispatcher, transcriber = Dispatcher(), Transcriber()
    t0 = [time.time()]
    done_event = threading.Event()
    state = {"fed": False}

    def t() -> str:
        return f"{time.time() - t0[0]:5.2f}s"

    session = DictationSession(transcriber, lambda piece: print(f"{t()} escribe: {piece!r}"), dispatcher.post)

    def finish_if_done():
        if state["fed"] and session.is_idle:
            print(f"{t()} texto final: {session.text}")
            done_event.set()

    def on_loaded(ok, error):
        if not ok:
            print("No se pudo cargar el modelo:", error)
            os._exit(1)
        capture = AudioCapture(
            on_partial=lambda uid, s: dispatcher.post(lambda: session.partial(uid, s)),
            on_utterance=lambda uid, s: dispatcher.post(lambda: (
                print(f"{t()} fin de enunciado {uid}"),
                session.utterance(uid, s, finish_if_done))),
        )
        t0[0] = time.time()
        print(" 0.00s empieza el audio")

        def audio_done():
            print(f"{t()} termina el audio")
            state["fed"] = True
            dispatcher.post(finish_if_done)

        capture.feed_file(path, audio_done)

    transcriber.load(on_loaded)
    done_event.wait()
    transcriber.shutdown()


def _srt_time(cs: int) -> str:
    ms = cs * 10
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def run_transcribe(path: str, language: str | None) -> None:
    """Transcribe un audio/video completo → <nombre>.txt y <nombre>.srt junto al original."""
    from . import config
    from .audio import decode_file
    from pywhispercpp.model import Model

    print("==> Cargando modelo…")
    model = Model(config.MODEL_PATH, context_params={"use_gpu": config.USE_GPU, "flash_attn": True},
                  print_progress=False)
    print("==> Transcribiendo…")
    segments = model.transcribe(decode_file(path), language=language or config.LANGUAGE,
                                n_threads=config.N_THREADS, print_progress=False)
    base = Path(path).with_suffix("")
    base.with_suffix(".txt").write_text("\n".join(s.text.strip() for s in segments) + "\n", encoding="utf-8")
    base.with_suffix(".srt").write_text("\n".join(
        f"{i}\n{_srt_time(s.t0)} --> {_srt_time(s.t1)}\n{s.text.strip()}\n"
        for i, s in enumerate(segments, 1)), encoding="utf-8")
    print(f"==> Listo: {base}.txt  {base}.srt")


def run_check() -> int:
    from . import config
    ok = True
    def line(good, msg):
        nonlocal ok
        ok &= good
        print(("OK   " if good else "FALTA"), msg)
    line(Path(config.MODEL_PATH).is_file(), f"modelo: {config.MODEL_PATH}")
    line(shutil.which("ffmpeg") is not None, "ffmpeg (sólo para --test y transcribir)")
    for mod in ("numpy", "sounddevice", "pywhispercpp", "pystray", "PIL"):
        try:
            __import__(mod)
            line(True, f"módulo {mod}")
        except Exception as e:
            line(False, f"módulo {mod}: {e}")
    try:
        from .hotkey import parse
        parse(config.HOTKEY)
        line(True, f"atajo: {config.HOTKEY}")
    except ValueError as e:
        line(False, str(e))
    return 0 if ok else 1


def main() -> None:
    args = sys.argv[1:]
    if args[:1] == ["--test"] and len(args) == 2:
        run_file_test(args[1])
    elif args[:1] == ["--transcribe"] and len(args) in (2, 3):
        run_transcribe(args[1], args[2] if len(args) == 3 else None)
    elif args[:1] == ["--devices"]:
        import sounddevice as sd
        print(sd.query_devices())
    elif args[:1] == ["--check"]:
        sys.exit(run_check())
    elif not args:
        if sys.platform != "win32":
            sys.exit("La app de bandeja sólo funciona en Windows (en macOS usa la app Swift). "
                     "Probá el motor con:  python -m spoke --test audio.wav")
        _redirect_output_if_windowless()
        from .app import main as app_main
        app_main()
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
