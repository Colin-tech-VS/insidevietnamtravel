"""Titres dynamiques seo_feed + injection dans le HTML rendu."""

from __future__ import annotations

import unittest

from app import app
from seo_feed import (
    DESC_MAX,
    MAIN_PAGE_SEO,
    TITLE_MAX,
    check_url,
    destination_seo,
    enrich_title_with_place,
    itinerary_seo,
    page_seo,
    place_keyword,
)


class SeoFeedMetaTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_main_page_packs_respect_limits_and_stay_unique(self):
        titles = []
        for key in ("home", "voyages", "guides"):
            for lang in ("fr", "en"):
                title, desc = page_seo(key, lang)
                self.assertEqual(title, MAIN_PAGE_SEO[key][lang]["title"])
                self.assertLessEqual(len(title), TITLE_MAX, title)
                self.assertLessEqual(len(desc), DESC_MAX, desc)
                titles.append(title.lower())
        self.assertEqual(len(titles), len(set(titles)))
        self.assertIn("voyage vietnam", page_seo("home", "fr")[0].lower())
        self.assertIn("hanoï-ho chi minh", page_seo("home", "fr")[0].lower())
        self.assertIn("circuits vietnam", page_seo("voyages", "fr")[0].lower())
        self.assertIn("guides vietnam", page_seo("guides", "fr")[0].lower())

    def test_dalat_title_uses_voyage_keyword(self):
        for place in ("Dalat", "Đà Lạt", "Da Lat", "Đà Lạt / Lâm Đồng"):
            title, desc = destination_seo(place, "fr")
            self.assertIn("Voyage Dalat", title, place)
            self.assertLessEqual(len(title), TITLE_MAX, title)
            self.assertLessEqual(len(desc), DESC_MAX, desc)
            self.assertIn("découvrez", desc.lower())
        self.assertEqual(place_keyword("Dalat", "fr", kind="circuit"), "Circuit Dalat")
        en_title, _ = destination_seo("Dalat", "en")
        self.assertIn("Dalat trip", en_title)

    def test_enrich_title_prefixes_place_keyword(self):
        title = enrich_title_with_place("Guide des collines et du climat", "Đà Lạt", "fr")
        self.assertTrue(title.startswith("Voyage Dalat"))
        self.assertLessEqual(len(title), TITLE_MAX)

    def test_itinerary_titles_are_circuit_scoped(self):
        title, desc = itinerary_seo(10, "fr")
        self.assertIn("Circuit Vietnam 10 jours", title)
        self.assertLessEqual(len(title), TITLE_MAX)
        self.assertLessEqual(len(desc), DESC_MAX)

    def test_check_url_injects_tags_on_main_pages(self):
        home = check_url("/", client=self.client)
        self.assertTrue(home["ok"], home)
        self.assertEqual(home["title"], page_seo("home", "fr")[0])
        self.assertEqual(home["description"], page_seo("home", "fr")[1])
        self.assertLessEqual(home["title_len"], TITLE_MAX)
        self.assertLessEqual(home["description_len"], DESC_MAX)

        voyages = check_url("/voyages", client=self.client)
        self.assertTrue(voyages["ok"], voyages)
        self.assertEqual(voyages["title"], page_seo("voyages", "fr")[0])
        self.assertEqual(voyages["description"], page_seo("voyages", "fr")[1])

        guides = check_url("/guides", client=self.client)
        self.assertTrue(guides["ok"], guides)
        self.assertEqual(guides["title"], page_seo("guides", "fr")[0])
        self.assertEqual(guides["description"], page_seo("guides", "fr")[1])

    def test_check_url_destination_hanoi(self):
        page = check_url("/hanoi", client=self.client)
        self.assertTrue(page["ok"], page)
        self.assertIn("Voyage Hanoï", page["title"])
        self.assertLessEqual(page["title_len"], TITLE_MAX)
        self.assertLessEqual(page["description_len"], DESC_MAX)

    def test_viewport_meta_is_kept(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('name="viewport"', html)
        self.assertIn('name="description"', html)
        self.assertIn("<title>", html)


if __name__ == "__main__":
    unittest.main()
