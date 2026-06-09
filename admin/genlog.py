"""Logs de diagnostic du pipeline de génération IA (visibles dans les logs Scalingo).

But : repérer EXACTEMENT l'étape qui bloque. Chaque ligne est horodatée et préfixée
`[AIGEN]` pour filtrer facilement (`scalingo logs | grep AIGEN`). On écrit sur stderr
avec flush immédiat pour que rien ne reste bufferisé même si le process se fige ensuite.
"""

from __future__ import annotations

import sys
import time


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    try:
        print(f"[AIGEN {ts}] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass


class step:
    """Context manager qui logue le début, la fin et la DURÉE d'une étape.

    Usage :
        with step("rédaction"):
            ...
    Loggue aussi l'exception (type + message) si l'étape échoue, avant de la relayer.
    """

    def __init__(self, label: str):
        self.label = label
        self.t0 = 0.0

    def __enter__(self):
        self.t0 = time.time()
        log(f"START {self.label}")
        return self

    def __exit__(self, exc_type, exc, tb):
        dt = time.time() - self.t0
        if exc_type is None:
            log(f"DONE  {self.label} en {dt:.1f}s")
        else:
            log(f"FAIL  {self.label} apres {dt:.1f}s -- {exc_type.__name__}: {str(exc)[:200]}")
        return False
