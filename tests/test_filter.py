import os
import sys
import csv
import tempfile
import unittest

import tests

sys.path.insert(0, os.path.join(tests.REPO_ROOT, "tools"))

import db
import tender_filter
import gate_terms

INCLUDE = ["pump", "pompa", "centrifugal", "mechanical seal", "spare parts"]
LABEL_COLUMNS = ("ref", "title", "jenis", "label", "note")


def judge_yes(title, profile):
    return True, "a pump supplier can do this"


def judge_no(title, profile):
    return False, ""


def judge_broken(title, profile):
    raise RuntimeError("model down")


class KeywordGateTest(unittest.TestCase):
    def test_bahasa_inclusion_matches(self):
        self.assertTrue(tender_filter.keyword_gate("Pengadaan Pompa Sentrifugal", INCLUDE)[0])

    def test_word_boundary_stops_partial_words(self):
        self.assertFalse(tender_filter.keyword_gate("Sealed unit", ["seal"])[0])

    def test_no_inclusion_is_hidden(self):
        self.assertFalse(tender_filter.keyword_gate("Pengadaan Jasa Catering", INCLUDE)[0])

    def test_empty_list_fails_open(self):
        passed, info = tender_filter.keyword_gate("anything at all", [])
        self.assertTrue(passed)
        self.assertTrue(info["filter_off"])

    def test_phrase_tolerates_extra_whitespace(self):
        self.assertTrue(tender_filter.keyword_gate("Supply of Mechanical   Seal kits", INCLUDE)[0])

    def test_reason_names_the_matched_terms(self):
        _passed, info = tender_filter.keyword_gate("Sea Water Lift Pump", INCLUDE)
        self.assertEqual(tender_filter.gate_reason(info), "matched: pump")


class FingerprintTest(unittest.TestCase):
    def test_stable_under_case_and_spacing(self):
        fp = tender_filter.content_fingerprint
        self.assertEqual(fp("Pengadaan Pompa", "Buyer", "R1", "2026-07-10"),
                         fp("  pengadaan   POMPA ", "buyer", "R1", "2026-07-10"))

    def test_changes_on_a_real_edit(self):
        fp = tender_filter.content_fingerprint
        self.assertNotEqual(fp("Pengadaan Pompa", "Buyer", "R1", "2026-07-10"),
                            fp("Pengadaan Pompa", "Buyer", "R1", "2026-07-18"))

    def test_fields_do_not_run_together(self):
        fp = tender_filter.content_fingerprint
        self.assertNotEqual(fp("ab", "c"), fp("a", "bc"))


LABELLED = [
    ("Pengadaan Pompa Sentrifugal", True),
    ("Supply of Mechanical Seal kits", True),
    ("Pengadaan Gas Engine Package", True),
    ("Jasa Perbaikan Pump di Lapangan", False),
    ("Pengadaan Jasa Catering", False),
]


class GateScoresTest(unittest.TestCase):
    def setUp(self):
        self.scores = tender_filter.gate_scores(LABELLED, INCLUDE)

    def test_each_title_lands_in_one_bucket(self):
        s = self.scores
        self.assertEqual(s["caught"], ["Pengadaan Pompa Sentrifugal", "Supply of Mechanical Seal kits"])
        self.assertEqual(s["missed"], ["Pengadaan Gas Engine Package"])
        self.assertEqual(s["let_through"], ["Jasa Perbaikan Pump di Lapangan"])
        self.assertEqual(s["held_back"], ["Pengadaan Jasa Catering"])

    def test_recall_and_precision(self):
        self.assertAlmostEqual(self.scores["recall"], 2 / 3)
        self.assertAlmostEqual(self.scores["precision"], 2 / 3)

    def test_by_term_names_the_keyword_that_let_a_service_through(self):
        self.assertEqual(self.scores["by_term"]["pump"], {"caught": 0, "let_through": 1})
        self.assertEqual(self.scores["by_term"]["pompa"], {"caught": 1, "let_through": 0})

    def test_nothing_passed_leaves_precision_undefined(self):
        s = tender_filter.gate_scores([("Pengadaan Jasa Catering", False)], INCLUDE)
        self.assertIsNone(s["precision"])
        self.assertIsNone(s["recall"])


class LooseTermsTest(unittest.TestCase):
    def test_a_term_that_lets_through_more_than_it_catches_is_loose(self):
        by_term = tender_filter.gate_scores(LABELLED, INCLUDE)["by_term"]
        self.assertEqual(tender_filter.loose_terms(by_term), ["pump"])

    def test_a_tie_is_not_loose_and_the_worst_comes_first(self):
        by_term = {"seal": {"caught": 1, "let_through": 1}, "coupling": {"caught": 0, "let_through": 1},
                   "panel": {"caught": 1, "let_through": 3}}
        self.assertEqual(tender_filter.loose_terms(by_term), ["panel", "coupling"])


class GateTermsToolTest(unittest.TestCase):
    def setUp(self):
        self.labels = os.path.join(tempfile.mkdtemp(dir=db.DB_DIR), "labels.csv")
        rows = [("Pengadaan Pompa Sentrifugal", "1"), ("Jasa Perbaikan Pump di Lapangan", "0"),
                ("Pengadaan Gas Engine Package", "1"), ("Stock material", "?"), ("Pengadaan Jasa Catering", "")]
        with open(self.labels, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=LABEL_COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows({"ref": str(i), "title": t, "jenis": "", "label": label, "note": ""}
                        for i, (t, label) in enumerate(rows))

    def test_only_rows_labelled_0_or_1_are_scored(self):
        self.assertEqual(gate_terms.load_labelled(self.labels),
                         [("Pengadaan Pompa Sentrifugal", True), ("Jasa Perbaikan Pump di Lapangan", False),
                          ("Pengadaan Gas Engine Package", True)])

    def test_report_names_the_loose_term_and_the_missed_title(self):
        out = gate_terms.report(gate_terms.load_labelled(self.labels), INCLUDE)
        self.assertIn("lets through more than it catches: pump", out)
        self.assertIn("3 of 5 terms matched no labelled title", out)
        self.assertIn("  Pengadaan Gas Engine Package", out)


class TokensTest(unittest.TestCase):
    def test_stopwords_digits_and_short_words_drop(self):
        self.assertEqual(tender_filter.tokens("Pengadaan Pompa 125 HP untuk CPP"), ["pompa", "cpp"])


class RelevanceSeamTest(unittest.TestCase):
    def test_keyword_match_never_asks_the_model(self):
        self.assertTrue(tender_filter.relevance_check("Pengadaan Pompa", INCLUDE, mode="ollama", judge=judge_no)[0])

    def test_model_yes_promotes_and_is_tagged(self):
        passed, why = tender_filter.relevance_check("Pengadaan Gas Engine Package", INCLUDE,
                                                    mode="ollama", judge=judge_yes)
        self.assertTrue(passed)
        self.assertTrue(why.startswith("AI:"))

    def test_model_no_leaves_it_in_the_feed(self):
        self.assertFalse(tender_filter.relevance_check("Pengadaan Gas Engine Package", INCLUDE,
                                                       mode="ollama", judge=judge_no)[0])

    def test_broken_model_changes_nothing(self):
        self.assertFalse(tender_filter.relevance_check("Pengadaan Gas Engine Package", INCLUDE,
                                                       mode="ollama", judge=judge_broken)[0])

    def test_mode_off_ignores_the_judge(self):
        self.assertFalse(tender_filter.relevance_check("Pengadaan Gas Engine Package", INCLUDE,
                                                       mode="off", judge=judge_yes)[0])


EXAMPLE_YES = [
    "Pengadaan Pompa Air Laut",
    "Supply of Gas Compressor Spare Parts",
    "Pengadaan Suku Cadang Turbin dan Turbine Bearing",
]

EXAMPLE_NO = [
    "Jasa Penyediaan Catering",
    "Kendaraan Bermotor Operasional",
    "PENGADAAN PIPA SEAMLESS 3, 4 dan 6 In di PEP ZONA 4",
]


class ExampleListTest(unittest.TestCase):
    def test_the_example_list_is_short(self):
        self.assertLessEqual(len(db.DEFAULT_INCLUDE_TERMS), 12)

    def test_titles_naming_its_goods_pass(self):
        for title in EXAMPLE_YES:
            with self.subTest(title=title):
                self.assertTrue(tender_filter.keyword_gate(title, db.DEFAULT_INCLUDE_TERMS)[0])

    def test_services_and_materials_stay_out(self):
        for title in EXAMPLE_NO:
            with self.subTest(title=title):
                self.assertFalse(tender_filter.keyword_gate(title, db.DEFAULT_INCLUDE_TERMS)[0])


class SavedDayTest(unittest.TestCase):
    def test_dates_run_from_the_day_the_pages_were_saved(self):
        self.assertEqual(db.PAGES_SAVED_ON, tests.FIXTURES_SAVED_ON)


if __name__ == "__main__":
    unittest.main()
