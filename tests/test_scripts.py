"""skills/paper-analysis/scripts/ の動作を確かめるテスト。

論文は架空のもの（tests/fixtures/）を使う。実在の論文の本文やレポートはリポジトリに入れない。
実行：python3 -m unittest discover -s tests
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "paper-analysis" / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True)


class CheckQuotesTest(unittest.TestCase):
    def test_all_quotes_match(self):
        r = run("check_quotes.py", str(FIXTURES / "report.md"), str(FIXTURES / "paper.txt"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("不一致 0件", r.stdout)
        # 図から読み取った引用は照合しない
        self.assertIn("図から読み取り 1件", r.stdout)

    def test_missing_quote_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.md"
            bad.write_text('> 原文："This sentence is not in the paper."\n', encoding="utf-8")
            r = run("check_quotes.py", str(bad), str(FIXTURES / "paper.txt"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("L1:", r.stdout)

    def test_bad_arguments(self):
        r = run("check_quotes.py", "only-one-arg")
        self.assertEqual(r.returncode, 2)


class RenderHtmlTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        out = Path(self.tmp.name) / "report.html"
        r = run("render_html.py", str(FIXTURES / "report.md"), str(out))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.html = out.read_text(encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_placeholders_left(self):
        self.assertNotIn("{{", self.html)

    def test_title_and_toc(self):
        self.assertIn("<title>Sample Paper on Deliberation Summaries</title>", self.html)
        self.assertIn('<a href="#s1">書誌情報</a>', self.html)

    def test_parts_are_rendered(self):
        self.assertIn('<span class="cite">〔p.2 §3〕</span>', self.html)
        self.assertIn('<span class="quote-label">原文</span>', self.html)
        self.assertIn('class="note"', self.html)
        self.assertIn('<td class="num">0.91</td>', self.html)
        # 入れ子の箇条書き
        self.assertRegex(self.html, r"<li>[^<]*<span class=\"cite\">[^<]*</span><ul><li>")

    def test_dark_mode(self):
        self.assertIn("prefers-color-scheme: dark", self.html)
        self.assertIn(':root[data-theme="dark"]', self.html)


class ProofFilterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("proof", SCRIPTS / "proof.py")
        cls.proof = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.proof)

    def test_numbers_from_paper_are_not_fixed(self):
        self.assertTrue(self.proof.known_false_positive({"rule_id": "NOT-012", "excerpt": "1350"}))

    def test_variable_names_are_not_typos(self):
        self.assertTrue(self.proof.known_false_positive({"rule_id": "NOT-036", "excerpt": "kの値は記載がない"}))

    def test_real_violation_is_kept(self):
        self.assertFalse(self.proof.known_false_positive({"rule_id": "FW-008", "excerpt": "べき"}))

    def test_quote_and_citation_are_protected(self):
        self.assertTrue(self.proof.protected('> 原文："It works."', 3, "It"))
        self.assertTrue(self.proof.protected("結果である〔p.2 §3〕。", None, "p.2 §3"))
        self.assertFalse(self.proof.protected("結果であるべき。", 6, "べき"))


if __name__ == "__main__":
    unittest.main()
