"""Balises SEO des pages principales (titres, descriptions, H1, slugs)."""

from __future__ import annotations

import re
import unittest
from html import unescape

from app import app
from config import SITE_DESCRIPTION, SITE_DESCRIPTION_I18N
from data.pillars import PILLARS
from locales.ui import UI


def _plain(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    return _plain(match.group(1)) if match else ""


def _meta_description(html: str) -> str:
    match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']',
        html,
        re.I,
    )
    return unescape(match.group(1)).strip() if match else ""


def _h1(html: str) -> str:
    match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
    return _plain(match.group(1)) if match else ""


def _h2s(html: str) -> list[str]:
    return [_plain(chunk) for chunk in re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.I | re.S)]


CTA_HINTS = (
    "maintenant",
    "préparez",
    "preparez",
    "commencez",
    "lisez",
    "consultez",
    "explore",
    "plan your trip",
    "comparez",
    "composez",
    "partez",
    "suivez",
    "start now",
    "start planning",
    "browse",
    "follow the checklist",
    "build your trip",
    "get ready",
)


class SeoMainPagesTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _get(self, path: str) -> str:
        response = self.client.get(path, follow_redirects=False)
        self.assertEqual(response.status_code, 200, path)
        return response.get_data(as_text=True)

    def test_ui_meta_descriptions_max_160(self):
        keys = (
            "meta.home.desc",
            "meta.prepare.desc",
            "meta.blog.desc",
            "meta.destinations.desc",
            "seo_hub.meta_description",
        )
        for key in keys:
            for lang, text in UI[key].items():
                self.assertLessEqual(
                    len(text),
                    160,
                    f"{key}[{lang}] has {len(text)} chars: {text}",
                )
                lowered = text.lower()
                self.assertTrue(
                    any(hint in lowered for hint in CTA_HINTS),
                    f"{key}[{lang}] missing CTA: {text}",
                )

        for lang, text in SITE_DESCRIPTION_I18N.items():
            self.assertLessEqual(len(text), 160, f"SITE_DESCRIPTION[{lang}]={len(text)}")
        self.assertLessEqual(len(SITE_DESCRIPTION), 160)

    def test_ui_titles_include_target_keywords(self):
        fr_home = UI["meta.home.title"]["fr"].lower()
        self.assertIn("voyage au vietnam", fr_home)
        self.assertIn("itinéraires", fr_home)

        fr_prepare = UI["meta.prepare.title"]["fr"].lower()
        self.assertIn("voyage au vietnam", fr_prepare)
        self.assertIn("guide itinéraire", fr_prepare)

        fr_blog = UI["meta.blog.title"]["fr"].lower()
        self.assertIn("voyage vietnam", fr_blog)
        self.assertIn("actualités", fr_blog)

        self.assertIn("voyage", UI["home.hero.title"]["fr"].lower())
        self.assertIn("vietnam", UI["home.hero.title_em"]["fr"].lower())
        self.assertIn("guide itinéraire", UI["home.itin.title"]["fr"].lower())
        self.assertIn("guide itinéraire", UI["home.pillars.title"]["fr"].lower())

    def test_pillar_guide_itinerary_tags(self):
        itin = PILLARS["itineraires"]
        self.assertIn("Guide itinéraire", itin["title"]["fr"])
        self.assertIn("Guide itinéraire Vietnam", itin["meta_title"]["fr"])
        self.assertLessEqual(len(itin["meta_description"]["fr"]), 160)
        self.assertLessEqual(len(itin["meta_description"]["en"]), 160)

        prep = PILLARS["preparer-son-voyage"]
        self.assertIn("voyage au Vietnam", prep["title"]["fr"])
        self.assertIn("Guide voyage Vietnam", prep["meta_title"]["fr"])
        self.assertLessEqual(len(prep["meta_description"]["fr"]), 160)
        self.assertLessEqual(len(prep["meta_description"]["en"]), 160)

    def test_homepage_title_h1_h2(self):
        html = self._get("/")
        title = _title(html)
        desc = _meta_description(html)
        h1 = _h1(html)
        h2s = _h2s(html)

        self.assertEqual(title, UI["meta.home.title"]["fr"])
        self.assertEqual(desc, UI["meta.home.desc"]["fr"])
        self.assertLessEqual(len(desc), 160)
        self.assertIn("Guide ultime pour un voyage", h1)
        self.assertIn("au Vietnam", h1)
        joined = " ".join(h2s).lower()
        self.assertIn("guide itinéraire", joined)
        self.assertIn("voyage au vietnam", joined)

    def test_voyage_page_and_alias(self):
        html = self._get("/preparer-mon-voyage")
        self.assertEqual(_title(html), UI["meta.prepare.title"]["fr"])
        self.assertEqual(_meta_description(html), UI["meta.prepare.desc"]["fr"])
        self.assertIn("Voyage au Vietnam", _h1(html))
        self.assertIn("itinéraire", _h1(html).lower())

        alias = self.client.get("/voyage", follow_redirects=False)
        self.assertEqual(alias.status_code, 301)
        self.assertTrue(alias.headers["Location"].endswith("/preparer-mon-voyage"))

        en_alias = self.client.get("/en/voyage", follow_redirects=False)
        self.assertEqual(en_alias.status_code, 301)
        self.assertTrue(en_alias.headers["Location"].endswith("/en/plan-my-trip"))

    def test_actualites_page_and_alias(self):
        html = self._get("/blog")
        self.assertEqual(_title(html), UI["meta.blog.title"]["fr"])
        self.assertEqual(_meta_description(html), UI["meta.blog.desc"]["fr"])
        self.assertIn("Actualités voyage Vietnam", _h1(html))

        alias = self.client.get("/actualites", follow_redirects=False)
        self.assertEqual(alias.status_code, 301)
        self.assertTrue(alias.headers["Location"].endswith("/blog"))

    def test_guide_page_and_alias(self):
        html = self._get("/guide/preparer-son-voyage")
        self.assertIn("Guide voyage Vietnam", _title(html))
        self.assertIn("voyage au Vietnam", _h1(html))
        self.assertLessEqual(len(_meta_description(html)), 160)

        itin = self._get("/guide/itineraires-vietnam")
        self.assertIn("Guide itinéraire Vietnam", _title(itin))
        self.assertIn("Guide itinéraire", _h1(itin))

        alias = self.client.get("/guide", follow_redirects=False)
        self.assertEqual(alias.status_code, 301)
        self.assertTrue(alias.headers["Location"].endswith("/guide/preparer-son-voyage"))

        still_ok = self.client.get("/guide/itineraires-vietnam", follow_redirects=False)
        self.assertEqual(still_ok.status_code, 200)

    def test_destinations_index_and_short_slugs(self):
        html = self._get("/destinations-vietnam")
        self.assertEqual(_title(html), UI["meta.destinations.title"]["fr"])
        self.assertIn("voyage au Vietnam", _h1(html))

        for slug in ("hanoi", "hoi-an", "halong", "hue"):
            response = self.client.get(f"/{slug}", follow_redirects=False)
            self.assertEqual(response.status_code, 200, slug)
            self.assertIsNone(re.fullmatch(r"page\d+", slug))

    def test_generic_page_ids_are_not_used_as_slugs(self):
        from admin.store import get_destinations_dict

        for slug in get_destinations_dict("fr"):
            self.assertFalse(re.fullmatch(r"page\d+", slug), slug)
            self.assertLessEqual(len(slug), 40, slug)
            self.assertNotIn("_", slug)


if __name__ == "__main__":
    unittest.main()
