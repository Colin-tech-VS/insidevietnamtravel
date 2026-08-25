"""Assets statiques dérivés (CSS / JS minifiés)."""

from __future__ import annotations

from pathlib import Path

CORE_JS = (
    "js/loader.js",
    "js/cookies.js",
    "js/visitor_profile.js",
    "js/main.js",
    "js/search.js",
)


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


def ensure_minified_js(static_folder: str | Path) -> str | None:
    """Regroupe et minifie le JS critique en js/core.min.js. None = servir les fichiers séparés."""
    root = Path(static_folder)
    sources = [root / rel for rel in CORE_JS]
    if not all(p.is_file() for p in sources):
        return None
    dst = root / "js" / "core.min.js"
    newest = max(p.stat().st_mtime for p in sources)
    try:
        if dst.is_file() and dst.stat().st_mtime >= newest:
            return "js/core.min.js"
        chunks = []
        for path in sources:
            text = path.read_text(encoding="utf-8").strip()
            if text and not text.endswith(";"):
                text += ";"
            chunks.append(text)
        bundled = "\n".join(chunks)
        try:
            import rjsmin

            bundled = rjsmin.jsmin(bundled)
        except Exception:
            pass
        dst.write_text(bundled, encoding="utf-8")
        return "js/core.min.js"
    except Exception:
        return None
