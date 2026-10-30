import io
import os
import shutil
import tempfile
import unittest
import contextlib
from unittest import mock

import tests

import no_leak

LIVE_ADDRESS = "https://civd." + "skkmigas.go.id/index.jwebs"


class NoLeakTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="no_leak_")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        patcher = mock.patch.object(no_leak, "REPO_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, path, text):
        full = os.path.join(self.root, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path

    def run_main(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return no_leak.main()

    def test_a_csv_with_a_label_column_is_refused(self):
        f = self.write("evaluation/answers.csv", "ref,title,Label\na,Pengadaan Pompa,1\n")
        self.assertEqual(no_leak.check_answers([f]), [f])

    def test_labels_csv_is_refused_by_its_name_alone(self):
        f = self.write("evaluation/labels.csv", "ref,title\n")
        self.assertEqual(no_leak.check_answers([f]), [f])

    def test_a_csv_without_a_label_column_passes(self):
        f = self.write("evaluation/totals.csv", "system,recall,precision\nkeywords,0.5,0.12\n")
        self.assertEqual(no_leak.check_answers([f]), [])

    def test_the_live_site_in_the_code_is_refused(self):
        f = self.write("src/scraper.py", "BASE = " + repr(LIVE_ADDRESS) + "\n")
        self.assertEqual(no_leak.check_live_site([f]), [f + ":1"])

    def test_the_live_site_in_the_readme_passes(self):
        f = self.write("README.md", "The listings come from " + LIVE_ADDRESS + ".\n")
        self.assertEqual(no_leak.check_live_site([f]), [])

    def test_an_em_dash_is_refused(self):
        f = self.write("README.md", "one\ntwo " + chr(0x2014) + " three\n")
        self.assertEqual(no_leak.check_em_dash([f]), [f + ":2"])

    def test_a_python_comment_is_refused(self):
        f = self.write("src/app.py", "x = 1\ny = 2  " + chr(35) + " two\n")
        self.assertEqual(no_leak.check_comments([f]), [f + ":2  comment"])

    def test_a_docstring_is_refused(self):
        f = self.write("tools/x.py", "def f():\n    " + '"""' + "Says hello." + '"""' + "\n    return 1\n")
        self.assertEqual(no_leak.check_comments([f]), [f + ":1  docstring"])

    def test_a_template_comment_is_refused(self):
        f = self.write("src/templates/base.html", "<p>hi</p>\n<" + "!-- note -->\n")
        self.assertEqual(no_leak.check_comments([f]), [f + ":2  markup comment"])

    def test_a_comment_in_requirements_is_refused(self):
        f = self.write("requirements.txt", chr(35) + " web\nFlask>=3.0\n")
        self.assertEqual(no_leak.check_comments([f]), [f + "  comment"])

    def test_a_database_and_an_env_file_are_refused(self):
        files = ["data/tender.db", ".env", "src/app.py", ".env.example"]
        self.assertEqual(no_leak.check_private_files(files), ["data/tender.db", ".env"])

    def test_a_local_path_is_refused(self):
        f = self.write("docs/notes.md", "saved in C:" + chr(92) + "Users" + chr(92) + "someone\n")
        self.assertEqual(no_leak.check_local_paths([f]), [f + ":1"])

    def test_a_clean_folder_passes_every_check(self):
        self.write("README.md", "# Tender\n")
        self.write("src/app.py", "x = 1\n")
        self.assertEqual(self.run_main(), 0)

    def test_one_planted_defect_fails_the_run(self):
        self.write("README.md", "# Tender\n")
        self.write("evaluation/labels.csv", "ref,title,label\n")
        self.assertEqual(self.run_main(), 1)


if __name__ == "__main__":
    unittest.main()
