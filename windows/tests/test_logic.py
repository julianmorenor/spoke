"""Pruebas de la lógica portable (segmentador + sesión LocalAgreement-2) con
un transcriptor falso. Corren en cualquier SO:  python -m pytest windows/tests"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spoke import config
from spoke.segmenter import Segmenter
from spoke.session import DictationSession


def tone(seconds, amp=0.2):
    n = int(seconds * config.SAMPLE_RATE)
    return (amp * np.sin(np.arange(n) * 2 * np.pi * 220 / config.SAMPLE_RATE)).astype(np.float32)


def silence(seconds):
    return np.zeros(int(seconds * config.SAMPLE_RATE), dtype=np.float32)


def test_segmenter_emite_parciales_y_un_enunciado():
    partials, utterances = [], []
    seg = Segmenter(lambda i, s: partials.append(i), lambda i, s: utterances.append((i, len(s))))
    seg.feed(silence(0.5))
    seg.feed(tone(2.0))
    seg.feed(silence(1.0))
    assert partials and set(partials) == {0}
    assert len(utterances) == 1 and utterances[0][0] == 0


def test_segmenter_dos_enunciados_separados_por_pausa():
    utterances = []
    seg = Segmenter(None, lambda i, s: utterances.append(i))
    for _ in range(2):
        seg.feed(silence(0.5)); seg.feed(tone(1.0)); seg.feed(silence(1.0))
    assert utterances == [0, 1]


def test_segmenter_descarta_ruido_corto_pero_cierra_enunciado():
    got = []
    seg = Segmenter(None, lambda i, s: got.append(len(s)))
    seg.feed(silence(0.5)); seg.feed(tone(0.1)); seg.feed(silence(1.0))
    assert got == [0]


class FakeTranscriber:
    """Devuelve hipótesis guionadas en orden (parciales y luego la final)."""
    def __init__(self, hypotheses):
        self.h = list(hypotheses)

    def transcribe(self, samples, prompt, partial, completion):
        completion(self.h.pop(0))


def run_session(hypotheses, n_partials):
    written = []
    t = FakeTranscriber(hypotheses)
    s = DictationSession(t, written.append, lambda fn: fn())
    for _ in range(n_partials):
        s.partial(0, np.zeros(16000, dtype=np.float32))
    s.utterance(0, np.zeros(16000, dtype=np.float32), lambda: None)
    return s, written


def test_escribe_solo_palabras_estables_y_completa_al_final():
    s, written = run_session(
        ["hola cómo", "hola cómo estás hoy", "hola cómo estás hoy amigo", "Hola, cómo estás hoy, amigo."],
        n_partials=3)
    assert written[0].strip() == "hola"          # estable tras 2 pasadas, reteniendo la última
    assert s.text.replace(",", "").replace(".", "").lower().split() == "hola cómo estás hoy amigo".split()


def test_no_reescribe_ni_borra_entre_enunciados():
    written = []
    t = FakeTranscriber(["Buenas tardes.", "Gracias por venir."])
    s = DictationSession(t, written.append, lambda fn: fn())
    s.utterance(0, np.ones(16000, dtype=np.float32), lambda: None)
    s.utterance(1, np.ones(16000, dtype=np.float32), lambda: None)
    assert s.text == "Buenas tardes. Gracias por venir."
    assert s.is_idle
