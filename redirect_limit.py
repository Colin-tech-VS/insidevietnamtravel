"""Middleware WSGI : coupe les chaînes de redirections 301/302 trop longues.

Sur `/` et `/api/health`, une boucle (plus de MAX_REDIRECTS réponses 301/302)
renvoie 500 au lieu de laisser le client suivre indéfiniment.
"""

from __future__ import annotations

from urllib.parse import urlparse

MAX_REDIRECTS = 5
PROTECTED_PATHS = frozenset({"/", "/api/health"})
ERROR_MESSAGE = "Too many redirects, please contact support"
REDIRECT_STATUSES = frozenset({"301", "302"})


class RedirectLimitMiddleware:
    """Suit les Location en interne et s'arrête après ``max_redirects`` sauts."""

    def __init__(
        self,
        app,
        max_redirects: int = MAX_REDIRECTS,
        paths: frozenset[str] | set[str] | None = None,
    ):
        self.app = app
        self.max_redirects = max_redirects
        self.paths = frozenset(paths) if paths is not None else PROTECTED_PATHS

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO") or "/"
        if path not in self.paths:
            return self.app(environ, start_response)

        first_status, first_headers, first_body = self._invoke(environ)
        code = _status_code(first_status)
        if code not in REDIRECT_STATUSES:
            return _commit(start_response, first_status, first_headers, first_body)

        hops = 0
        status, headers, body = first_status, first_headers, first_body
        current_environ = environ
        while code in REDIRECT_STATUSES:
            hops += 1
            if hops > self.max_redirects:
                return _error(start_response)
            location = _header_value(headers, "Location")
            if not location:
                break
            current_environ = _follow_environ(current_environ, location)
            status, headers, body = self._invoke(current_environ)
            code = _status_code(status)

        return _commit(start_response, first_status, first_headers, first_body)

    def _invoke(self, environ):
        captured: list = []
        chunks: list[bytes] = []

        def start_response(status, headers, exc_info=None):
            captured[:] = [status, headers]
            return chunks.append

        result = self.app(environ, start_response)
        try:
            for piece in result:
                if isinstance(piece, bytes):
                    chunks.append(piece)
                else:
                    chunks.append(piece.encode("utf-8"))
        finally:
            close = getattr(result, "close", None)
            if close is not None:
                close()
        status, headers = captured
        return status, list(headers), [b"".join(chunks)]


def _status_code(status: str) -> str:
    return (status or "")[:3]


def _header_value(headers, name: str) -> str:
    needle = name.lower()
    for key, value in headers:
        if key.lower() == needle:
            return value
    return ""


def _follow_environ(environ: dict, location: str) -> dict:
    """Prépare un nouvel environ WSGI pour le Location (même process)."""
    new_env = dict(environ)
    parsed = urlparse(location)
    if parsed.scheme:
        new_env["wsgi.url_scheme"] = parsed.scheme
        new_env["HTTP_X_FORWARDED_PROTO"] = parsed.scheme
    if parsed.netloc:
        new_env["HTTP_HOST"] = parsed.netloc
        new_env["HTTP_X_FORWARDED_HOST"] = parsed.netloc
        host, _, port = parsed.netloc.partition(":")
        new_env["SERVER_NAME"] = host
        if port:
            new_env["SERVER_PORT"] = port
        elif parsed.scheme == "https":
            new_env["SERVER_PORT"] = "443"
        elif parsed.scheme == "http":
            new_env["SERVER_PORT"] = "80"
    new_env["PATH_INFO"] = parsed.path or "/"
    new_env["QUERY_STRING"] = parsed.query
    new_env["REQUEST_METHOD"] = "GET"
    new_env["CONTENT_LENGTH"] = "0"
    new_env.pop("wsgi.input", None)
    return new_env


def _error(start_response):
    payload = ERROR_MESSAGE.encode("utf-8")
    start_response(
        "500 Internal Server Error",
        [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(payload))),
        ],
    )
    return [payload]


def _commit(start_response, status, headers, body):
    start_response(status, headers)
    return body
