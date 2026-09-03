"""Boucles de redirection : /fr/ ↔ /, www ↔ apex, /checkout vers soi-même."""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

from app import app
from i18n_utils import strip_legacy_fr_prefix


def _location_path(location: str) -> str:
    parsed = urlparse(location)
    return parsed.path if parsed.scheme or parsed.netloc else location.split("?", 1)[0]


class StripLegacyFrPrefixTests(unittest.TestCase):
    def test_root_and_en_unchanged(self):
        self.assertEqual(strip_legacy_fr_prefix("/"), "/")
        self.assertEqual(strip_legacy_fr_prefix("/en/"), "/en/")
        self.assertEqual(strip_legacy_fr_prefix("/en/blog"), "/en/blog")
        self.assertEqual(strip_legacy_fr_prefix("/hanoi"), "/hanoi")
        self.assertEqual(strip_legacy_fr_prefix("/france"), "/france")

    def test_fr_prefix_stripped(self):
        self.assertEqual(strip_legacy_fr_prefix("/fr"), "/")
        self.assertEqual(strip_legacy_fr_prefix("/fr/"), "/")
        self.assertEqual(strip_legacy_fr_prefix("/fr/hanoi"), "/hanoi")
        self.assertEqual(strip_legacy_fr_prefix("/fr/blog/visa"), "/blog/visa")


class RedirectLoopTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _follow_until_settled(self, path: str, headers=None, limit: int = 5):
        seen = []
        current = path
        response = None
        for _ in range(limit):
            response = self.client.get(
                current, headers=headers or {}, follow_redirects=False
            )
            seen.append((current, response.status_code, response.headers.get("Location")))
            if response.status_code not in (301, 302, 307, 308):
                return response, seen
            location = response.headers.get("Location") or ""
            next_path = _location_path(location)
            if next_path == current:
                self.fail(f"redirection vers soi-même: {seen}")
            current = next_path or "/"
        self.fail(f"chaîne trop longue (boucle probable): {seen}")

    def test_homepage_is_not_redirected_to_fr_prefix(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        location = response.headers.get("Location", "")
        self.assertNotRegex(location, r"/fr(/|$)")

    def test_fr_root_redirects_once_to_slash(self):
        response = self.client.get("/fr", follow_redirects=False)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(_location_path(response.headers.get("Location", "")), "/")

        response = self.client.get("/fr/", follow_redirects=False)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(_location_path(response.headers.get("Location", "")), "/")

    def test_fr_prefix_path_redirects_without_loop(self):
        response, seen = self._follow_until_settled("/fr/")
        self.assertEqual(response.status_code, 200, seen)
        self.assertEqual(len(seen), 2, seen)

        response = self.client.get("/fr/hanoi", follow_redirects=False)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(_location_path(response.headers["Location"]), "/hanoi")

    def test_en_homepage_is_not_redirected_to_fr_or_root(self):
        response = self.client.get("/en/", follow_redirects=False)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.headers.get("Location"))

    def test_www_fr_prefix_strips_without_bouncing_to_apex(self):
        """www reste www : un 301 vers l'apex boucle avec LWS apex → www."""
        response = self.client.get(
            "/fr/hanoi?utm_source=gsc",
            headers={"Host": "www.insidevietnamtravel.fr"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        location = response.headers.get("Location", "")
        self.assertEqual(_location_path(location), "/hanoi")
        self.assertIn("utm_source=gsc", location)
        self.assertNotIn("insidevietnamtravel.fr", location)

        response, seen = self._follow_until_settled(
            "/", headers={"Host": "www.insidevietnamtravel.fr"}
        )
        self.assertEqual(response.status_code, 200, seen)
        self.assertEqual(len(seen), 1, seen)

    def test_www_checkout_does_not_redirect_to_apex(self):
        response = self.client.get(
            "/checkout",
            headers={"Host": "www.insidevietnamtravel.fr"},
            follow_redirects=False,
        )
        location = response.headers.get("Location", "")
        self.assertNotEqual(location, "https://insidevietnamtravel.fr/checkout")
        self.assertNotEqual(location, "http://insidevietnamtravel.fr/checkout")
        self.assertNotIn("://insidevietnamtravel.fr/checkout", location)

    def test_apex_checkout_does_not_redirect_to_itself(self):
        response = self.client.get(
            "/checkout",
            headers={"Host": "insidevietnamtravel.fr"},
            follow_redirects=False,
        )
        location = response.headers.get("Location", "")
        self.assertNotEqual(location, "https://insidevietnamtravel.fr/checkout")
        self.assertNotEqual(location, "http://insidevietnamtravel.fr/checkout")
        if response.status_code in (301, 302, 307, 308):
            self.assertNotEqual(_location_path(location), "/checkout")
        else:
            self.assertEqual(response.status_code, 200)

    def test_nginx_strips_fr_prefix_and_never_adds_it(self):
        text = Path(__file__).resolve().parents[1].joinpath("nginx.conf").read_text()
        self.assertIn("location = /fr", text)
        self.assertIn("location = /fr/", text)
        self.assertIn("rewrite ^/fr/(.*)$ https://insidevietnamtravel.fr/$1 permanent;", text)
        self.assertNotIn("return 301 https://insidevietnamtravel.fr/fr", text)
        self.assertNotIn("return 301 /fr/", text)
        active = "\n".join(
            line for line in text.splitlines() if line.strip() and not line.strip().startswith("#")
        )
        self.assertNotIn("http://www.insidevietnamtravel.fr", active)
        self.assertNotIn("RedirectMatch 301 ^/admin", active)

    def test_nginx_apex_has_no_catch_all_slash_redirect(self):
        """Le bloc apex ne doit pas 301 le chemin / (Redirect / → boucle www)."""
        text = Path(__file__).resolve().parents[1].joinpath("nginx.conf").read_text()
        active_lines = [
            line.split("#", 1)[0] for line in text.splitlines()
        ]
        active = "\n".join(active_lines)
        blocks = re.split(r"\bserver\s*\{", active)
        apex_blocks = [
            block for block in blocks if "server_name insidevietnamtravel.fr" in block
        ]
        self.assertEqual(len(apex_blocks), 1, apex_blocks)
        apex = apex_blocks[0]
        self.assertNotRegex(apex, r"location\s+=\s+/\s*\{")
        self.assertNotRegex(apex, r"location\s+/\s*\{")
        self.assertIn("location = /fr", apex)
        www_blocks = [
            block for block in blocks if "server_name www.insidevietnamtravel.fr" in block
        ]
        self.assertEqual(len(www_blocks), 1, www_blocks)
        self.assertNotIn(
            "return 301 https://insidevietnamtravel.fr$request_uri;",
            www_blocks[0],
        )
        self.assertNotIn("insidevietnamtravel.fr$request_uri", www_blocks[0])


if __name__ == "__main__":
    unittest.main()
