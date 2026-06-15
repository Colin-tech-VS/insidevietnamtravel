"""Assets statiques dérivés (CSS minifié)."""

from __future__ import annotations

from pathlib import Path


def ensure_minified_css(static_folder: str | Path) -> str:
    """Génère css/style.min.css si style.css est plus récent. Retourne le chemin relatif à servir."""
    root = Path(static_folder)
    src = root / "css" / "style.css"
    dst = root / "css" / "style.min.css"
    rel = "css/style.css"
    if not src.is_file():
        return rel
    try:
        if dst.is_file() and dst.stat().st_mtime >= src.stat().st_mtime:
            return "css/style.min.css"
        import rcssmin

        dst.write_text(
            rcssmin.cssmin(src.read_text(encoding="utf-8")),
            encoding="utf-8",
        )
        return "css/style.min.css"
    except Exception:
        return rel
