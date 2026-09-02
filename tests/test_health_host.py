"""Sondes de santé et hôte canonique (apex, sans www)."""

import os
import unittest
from pathlib import Path

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

    def test_public_ip_default(self):
        self.assertEqual(config.PUBLIC_IP, "185.135.132.50")
        self.assertNotIn("localhost", config._resolve_site_url())

    def test_pdf_flow_uses_canonical_host(self):
        self.assertIsNone(os.environ.get("PDF_USE_SCALINGO_HOST"))
        self.assertEqual(
            config.pdf_flow_base_url(),
            "https://insidevietnamtravel.fr",
        )

    def test_checkout_http_from_public_ip_goes_to_canonical_https(self):
        response = self.client.get(
            "/checkout",
            headers={"Host": "185.135.132.50"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.headers.get("Location"),
            "https://insidevietnamtravel.fr/checkout",
        )

    def test_checkout_http_from_www_goes_to_canonical_https(self):
        response = self.client.get(
            "/checkout",
            headers={"Host": "www.insidevietnamtravel.fr"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.headers.get("Location"),
            "https://insidevietnamtravel.fr/checkout",
        )

    def test_nginx_checkout_redirects_to_canonical_https(self):
        text = Path(__file__).resolve().parents[1].joinpath("nginx.conf").read_text()
        self.assertNotIn("localhost", text)
        self.assertNotIn("SCALINGO_HOSTNAME", text)
        self.assertNotIn("10.100.4.", text)
        self.assertIn("185.135.132.50", text)
        self.assertIn("location = /checkout", text)
        self.assertIn("return 301 https://insidevietnamtravel.fr/checkout;", text)

    def test_env_example_has_public_ip_and_no_scalingo_pdf_host(self):
        text = Path(__file__).resolve().parents[1].joinpath(".env.example").read_text()
        self.assertIn("PUBLIC_IP=185.135.132.50", text)
        self.assertNotIn("PDF_USE_SCALINGO_HOST", text)


if __name__ == "__main__":
    unittest.main()
