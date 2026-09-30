"""Convierte audio parcial en texto escrito en vivo, sin borrar nunca.
Equivalente a DictationSession.swift (LocalAgreement-2, como whisper_streaming).

Cada pasada de Whisper sobre el enunciado en curso da una hipótesis. Las
palabras en las que coinciden dos hipótesis seguidas se dan por estables y se
escriben. La última palabra coincidente se retiene porque su puntuación aún
puede cambiar. Al terminar el enunciado, la pasada final completa lo que falte.

Todos los métodos deben llamarse desde un único hilo (el "hilo lógico");
`transcriber.transcribe` entrega los resultados por `post`, que los reenvía a ese hilo.
"""
import string

from . import config


def _normalize(word: str) -> str:
    w = word.lower()
    return w.strip(string.punctuation + "¡¿«»“”‘’…—–")


def _words(text: str) -> list[str]:
    return text.split()


def _trim_repetition(words: list[str]) -> list[str]:
    """Las parciales a veces repiten ("x x x", o la frase entera dos veces)."""
    n = [_normalize(w) for w in words]
    k = 3
    for i in range(len(n)):
        if i + 2 < len(n) and n[i] == n[i + 1] == n[i + 2]:
            return words[:i]
        if i > 0 and i + k <= len(n) and len(n) >= k and n[i:i + k] == n[0:k]:
            return words[:i]
    return words


class DictationSession:
    def __init__(self, transcriber, insert, post):
        """`insert(texto)` escribe en la app con foco; `post(fn)` ejecuta fn en el hilo lógico."""
        self._transcriber = transcriber
        self._insert = insert
        self._post = post
        self.text = ""                     # todo lo escrito en esta sesión
        self._current_id = 0
        self._committed: list[str] = []    # palabras ya escritas del enunciado en curso
        self._previous: list[str] = []     # hipótesis anterior
        self._context = ""                 # contexto para Whisper
        self._partial_in_flight = False
        self._pending_finals = 0

    @property
    def is_idle(self) -> bool:
        return self._pending_finals == 0

    @property
    def _prompt(self):
        return self._context[-200:] if self._context else None

    def partial(self, uid: int, samples) -> None:
        # Si Whisper sigue ocupado se saltea: la próxima pasada trae más audio.
        if self._partial_in_flight or uid != self._current_id:
            return
        self._partial_in_flight = True

        def done(hypothesis: str):
            self._post(lambda: self._on_partial(uid, samples, hypothesis))

        self._transcriber.transcribe(samples, self._prompt, True, done)

    def _on_partial(self, uid, samples, hypothesis):
        self._partial_in_flight = False
        if uid != self._current_id:
            return
        words = _trim_repetition(_words(hypothesis))
        if config.DEBUG:
            print(f"   parcial {len(samples) / config.SAMPLE_RATE:.1f}s: {hypothesis}")
        agreed = 0
        while (agreed < min(len(self._previous), len(words))
               and _normalize(self._previous[agreed]) == _normalize(words[agreed])):
            agreed += 1
        stable = agreed - 1
        if stable > len(self._committed) and self._matches(words):
            self._write(words[len(self._committed):stable])
            self._committed = words[:stable]
        self._previous = words

    def utterance(self, uid: int, samples, done) -> None:
        self._pending_finals += 1

        def finish(hypothesis: str):
            self._pending_finals -= 1
            words = _words(hypothesis)
            start = self._resume_index(words)
            if start < len(words):
                self._write(words[start:])
            self._current_id = uid + 1
            self._committed = []
            self._previous = []
            self._context = self.text
            done()

        if len(samples) == 0:
            self._post(lambda: finish(""))
        else:
            self._transcriber.transcribe(
                samples, self._prompt, False,
                lambda text: self._post(lambda: finish(text)))

    def _write(self, words: list[str]) -> None:
        if not words:
            return
        piece = " ".join(words)
        if self.text:
            piece = " " + piece
        self._insert(piece)
        self.text += piece

    def _resume_index(self, words: list[str]) -> int:
        """Dónde retomar en la hipótesis final. La pasada final puede diferir de
        las parciales (palabras agregadas, quitadas o unidas), así que se busca
        dónde terminan las últimas palabras ya escritas: gana la coincidencia
        más larga y, a igualdad, la más cercana a len(committed)."""
        if not self._committed:
            return 0
        tail = [_normalize(w) for w in self._committed[-4:]]
        final = [_normalize(w) for w in words]
        n = len(self._committed)
        best_len, best_idx = 0, n
        for k in range(1, len(final) + 1):
            length = 0
            while length < len(tail) and k - 1 - length >= 0 \
                    and final[k - 1 - length] == tail[len(tail) - 1 - length]:
                length += 1
            if length > best_len or (length == best_len and length > 0 and abs(k - n) < abs(best_idx - n)):
                best_len, best_idx = length, k
        return best_idx

    def _matches(self, words: list[str]) -> bool:
        """Lo ya escrito sigue siendo prefijo de la nueva hipótesis."""
        c = self._committed
        return len(c) <= len(words) and all(_normalize(a) == _normalize(b) for a, b in zip(c, words))
