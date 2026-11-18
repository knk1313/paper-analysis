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


class RenderLooseListTest(unittest.TestCase):
    """番号のあとに空白がない番号付きの行の扱い。"""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("render_html", SCRIPTS / "render_html.py")
        cls.render = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.render)

    def body(self, md: str) -> str:
        return self.render.convert("## 節\n\n" + md)[2]

    def test_consecutive_lines_become_list(self):
        html = self.body("1.単語を1つ読む\n2.表にあれば頻度を1増やす\n3．なければ頻度1で登録する\n")
        self.assertIn("<ol><li>単語を1つ読む</li><li>表にあれば頻度を1増やす</li><li>なければ頻度1で登録する</li></ol>", html)

    def test_list_after_paragraph_line(self):
        html = self.body("手順は次のとおりである。\n1.読む\n2.登録する\n")
        self.assertIn("<p>手順は次のとおりである。</p><ol><li>読む</li><li>登録する</li></ol>", html)

    def test_single_line_stays_paragraph(self):
        html = self.body("1.読むだけの手順である。\n")
        self.assertIn("<p>1.読むだけの手順である。</p>", html)

    def test_decimal_number_is_not_list(self):
        html = self.body("1.5倍に向上した。\n2.0倍の条件もある。\n")
        self.assertNotIn("<ol>", html)

    def test_code_block_is_untouched(self):
        html = self.body("```\n1.読む\n2.登録する\n```\n")
        self.assertIn("<pre><code>1.読む\n2.登録する</code></pre>", html)


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
