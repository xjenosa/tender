import unittest
from unittest import mock

import tests
import scraper

FIRST_TITLE = "Pengadaan Material Pressure Controller PWD"
PUMP_TITLE = "Pengadaan Sea Water Lift Pump 125 HP for CBU PHE OSES"
PUMP_FIRST_ATTACHMENT = "8d7afe75-54df-42e8-93db-8a36cbc0796c"
LISTINGS_PER_PAGE = 6
FIXTURE_TOTAL = 43


class NormDateTest(unittest.TestCase):
    def test_formats_portals_print(self):
        self.assertEqual(scraper.norm_date("2026-12-31"), "2026-12-31")
        self.assertEqual(scraper.norm_date("31/12/2026"), "2026-12-31")
        self.assertEqual(scraper.norm_date("5 Agustus 2026 14:00 WIB"), "2026-08-05")
        self.assertEqual(scraper.norm_date("16 Okt 2026,"), "2026-10-16")
        self.assertEqual(scraper.norm_date("31 December 2026"), "2026-12-31")

    def test_impossible_or_blank_is_none(self):
        self.assertIsNone(scraper.norm_date("31/02/2026"))
        self.assertIsNone(scraper.norm_date("TBA"))
        self.assertIsNone(scraper.norm_date(""))


class CivdParseTest(unittest.TestCase):
    def setUp(self):
        self.page = scraper.parse_civd_listing(tests.read_fixture(tests.CIVD_PAGE_1))

    def test_reads_every_card_on_the_page(self):
        self.assertEqual(len(self.page["candidates"]), LISTINGS_PER_PAGE)

    def test_reads_the_total_the_site_reported(self):
        self.assertEqual(self.page["total"], FIXTURE_TOTAL)

    def test_first_card_fields(self):
        first = self.page["candidates"][0]
        self.assertEqual(first["title"], FIRST_TITLE)
        self.assertEqual(first["customer_name"], "PT PERTAMINA HULU ROKAN")
        self.assertEqual(first["deadline"], "2026-10-16")
        self.assertEqual(first["procurement_type"], "Barang")
        self.assertEqual(first["tender_ref"], "570a6511-93b6-4fcc-b406-c543ea6fb0c6")
        self.assertIn("Golongan Usaha: Kecil", first["description"])

    def test_the_first_attachment_identifies_a_listing(self):
        page_two = scraper.parse_civd_listing(tests.read_fixture(tests.CIVD_PAGE_2))
        pump = next(c for c in page_two["candidates"] if c["title"] == PUMP_TITLE)
        self.assertEqual(pump["tender_ref"], PUMP_FIRST_ATTACHMENT)

    def test_services_are_marked_jasa(self):
        kinds = {c["procurement_type"] for c in self.page["candidates"]}
        self.assertEqual(kinds, {"Barang", "Jasa"})


class CivdFetchTest(unittest.TestCase):
    def test_both_saved_pages_are_read(self):
        res = scraper.CivdAdapter.fetch()
        self.assertEqual(res["status"], "ok")
        self.assertEqual(len(res["candidates"]), 2 * LISTINGS_PER_PAGE)
        self.assertEqual(res["total"], FIXTURE_TOTAL)
        self.assertIn(PUMP_TITLE, [c["title"] for c in res["candidates"]])

    def test_pages_are_read_in_the_order_given(self):
        seen = []
        res = scraper.CivdAdapter.fetch(pages=("b", "a"),
                                        read=lambda name: seen.append(name) or tests.read_fixture(tests.CIVD_PAGE_1))
        self.assertEqual(seen, ["b", "a"])
        self.assertEqual(len(res["candidates"]), 2 * LISTINGS_PER_PAGE)

    def test_nothing_reaches_the_network(self):
        self.assertFalse(hasattr(scraper, "urllib"))


class FetchAllTest(unittest.TestCase):
    def test_statuses_without_a_network(self):
        with mock.patch.object(scraper.CivdAdapter, "fetch",
                               return_value={"status": "ok", "candidates": [], "detail": ""}):
            res = scraper.fetch_all([{"key": "civd"}, {"key": "nowhere"}, {"key": "manual"}])
        self.assertFalse(res["busy"])
        self.assertEqual(res["sources"]["civd"]["status"], "ok")
        self.assertEqual(res["sources"]["nowhere"]["status"], "no_adapter")
        self.assertNotIn("manual", res["sources"])

    def test_a_failing_source_reports_error(self):
        with mock.patch.object(scraper.CivdAdapter, "fetch", side_effect=OSError("offline")):
            res = scraper.fetch_all([{"key": "civd"}])
        self.assertEqual(res["sources"]["civd"]["status"], "error")


if __name__ == "__main__":
    unittest.main()
