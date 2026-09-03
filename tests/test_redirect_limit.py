"""Middleware de limitation des redirections 301/302 (max 5)."""

from __future__ import annotations

import unittest

from werkzeug.test import Client

from app import app
from redirect_limit import (
    ERROR_MESSAGE,
    MAX_REDIRECTS,
    RedirectLimitMiddleware,
)


def _redirect_app(mapping: dict[str, str], code: str = "302 Found"):
    def application(environ, start_response):
        path = environ.get("PATH_INFO") or "/"
        target = mapping.get(path)
        if target is not None:
            start_response(code, [("Location", target)])
            return [b""]
        start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"ok"]

    return application


class RedirectLimitMiddlewareTests(unittest.TestCase):
    def _client(self, inner):
        return Client(RedirectLimitMiddleware(inner))

    def test_root_loop_returns_500_after_max_redirects(self):
        client = self._client(_redirect_app({"/": "/"}))
        response = client.get("/")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_data(as_text=True), ERROR_MESSAGE)

    def test_health_loop_returns_500(self):
        client = self._client(
            _redirect_app({"/api/health": "/api/health"}, code="301 Moved Permanently")
        )
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_data(as_text=True), ERROR_MESSAGE)

    def test_chain_longer_than_five_returns_500(self):
        mapping = {
            "/": "/1",
            "/1": "/2",
            "/2": "/3",
            "/3": "/4",
            "/4": "/5",
            "/5": "/6",
        }
        client = self._client(_redirect_app(mapping))
        response = client.get("/")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_data(as_text=True), ERROR_MESSAGE)

    def test_five_redirects_then_ok_keeps_original_302(self):
        mapping = {
            "/": "/1",
            "/1": "/2",
            "/2": "/3",
            "/3": "/4",
            "/4": "/done",
        }
        client = self._client(_redirect_app(mapping))
        response = client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/1")

    def test_unprotected_path_is_not_limited(self):
        client = self._client(_redirect_app({"/blog": "/blog"}))
        response = client.get("/blog")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/blog")

    def test_max_redirects_constant(self):
        self.assertEqual(MAX_REDIRECTS, 5)


class AppRedirectLimitTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_middleware_wraps_wsgi_app(self):
        current = app.wsgi_app
        found = False
        while current is not None and not found:
            if isinstance(current, RedirectLimitMiddleware):
                found = True
                break
            current = getattr(current, "app", None)
        self.assertTrue(found, "RedirectLimitMiddleware doit envelopper l'app Flask")

    def test_homepage_is_200(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 200)

    def test_api_health_is_200(self):
        response = self.client.get("/api/health", follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_www_homepage_is_served_in_place(self):
        """Pas de 301 www → apex : ça boucle avec le Redirect / LWS."""
        response = self.client.get(
            "/",
            headers={"Host": "www.insidevietnamtravel.fr"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        location = response.headers.get("Location", "")
        self.assertNotIn("insidevietnamtravel.fr", location)


if __name__ == "__main__":
    unittest.main()
