"""Sondes de santé et hôte canonique (apex, sans www)."""

import unittest

import config
from app import app


class HealthHostTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_api_health_ok(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("boot_time_utc", payload)

    def test_healthz_ok(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_apex_is_not_redirected_to_www(self):
        response = self.client.get(
            "/",
            headers={"Host": "insidevietnamtravel.fr"},
            follow_redirects=False,
        )
        location = response.headers.get("Location", "")
        self.assertNotIn("www.insidevietnamtravel.fr", location)

    def test_www_health_is_served_in_place(self):
        """Ne pas renvoyer www → apex : le registrar 301 l'apex vers http://www."""
        response = self.client.get(
            "/api/health",
            headers={"Host": "www.insidevietnamtravel.fr"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.headers.get("Location"))

    def test_admin_without_trailing_slash(self):
        response = self.client.get("/admin", follow_redirects=False)
        self.assertIn(response.status_code, (200, 302, 308))
        self.assertNotIn(
            "www.insidevietnamtravel.fr",
            response.headers.get("Location", ""),
        )

    def test_canonical_url_has_no_www(self):
        self.assertEqual(config.SITE_PUBLIC_DOMAIN, "insidevietnamtravel.fr")
        self.assertFalse(config.SITE_CANONICAL_URL.startswith("https://www."))
        self.assertEqual(
            config._without_www("https://www.insidevietnamtravel.fr/"),
            "https://insidevietnamtravel.fr",
        )
        self.assertEqual(
            config._without_www("https://insidevietnamtravel.fr"),
            "https://insidevietnamtravel.fr",
        )


if __name__ == "__main__":
    unittest.main()
