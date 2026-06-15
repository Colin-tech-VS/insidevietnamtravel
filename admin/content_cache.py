"""Cache process-level du contenu public (invalidé à chaque écriture KV)."""

from __future__ import annotations

from typing import Any, Callable

_store: dict[str, Any] = {}
_hooks: list[Callable[[], None]] = []


def register_invalidate_hook(fn: Callable[[], None]) -> None:
    _hooks.append(fn)


def invalidate_all() -> None:
    _store.clear()
    for hook in _hooks:
        try:
            hook()
        except Exception:
            pass


def get_or_set(key: str, factory: Callable[[], Any]) -> Any:
    if key not in _store:
        _store[key] = factory()
    return _store[key]
