#!/usr/bin/env python3
"""レポートの `原文："..."` が、論文の本文に一字一句あるかを確かめる。

使い方:
    python3 check_quotes.py <report.md または evidence.md> <paper.txt>

- PDF からテキストにしたときの揺れ（改行、行末のハイフン、合字、引用符の形、空白）は吸収して比べる
- `（図から読み取り）` を含む行は照合しない
- 見つからない引用を行番号つきで出す

終了コード: 0 = すべて一致、1 = 見つからない引用がある、2 = 引数の誤り
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

QUOTE = re.compile(r"原文[：:]\s*[\"“](.+?)[\"”](?=\s*(?:$|〔|（|\())")

TRANSLATE = str.maketrans({
    "“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "′": "'",
    "–": "-", "—": "-", "−": "-", "‐": "-", "‑": "-",
    "­": None,
})


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)  # 合字（ﬁ）や全角英数をそろえる
    s = s.translate(TRANSLATE)
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)  # 行末のハイフンでの分割
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def squash(s: str) -> str:
    """空白を全部消した形。2段組みなどで空白の位置がずれる場合の予備の比較に使う。"""
    return re.sub(r"[\s\-]", "", s)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    report, paper = Path(sys.argv[1]), Path(sys.argv[2])
    if not report.is_file() or not paper.is_file():
        print("ファイルが見つからない", file=sys.stderr)
        return 2

    body = normalize(paper.read_text(encoding="utf-8", errors="replace"))
    body_sq = squash(body)

    total, missing, skipped = 0, [], 0
    for no, line in enumerate(report.read_text(encoding="utf-8").splitlines(), 1):
        for m in QUOTE.finditer(line):
            if "図から読み取り" in line:
                skipped += 1
                continue
            total += 1
            q = normalize(m.group(1)).rstrip(".…").strip()
            q = q.replace("...", "\x00")
            # 「...」で省略した引用は、前後の断片がそれぞれ本文にあればよい
            parts = [p.strip() for p in q.split("\x00") if p.strip()]
            ok = all(p in body or squash(p) in body_sq for p in parts)
            if not ok:
                missing.append((no, m.group(1)))

    print(f"引用 {total}件のうち一致 {total - len(missing)}件、不一致 {len(missing)}件（図から読み取り {skipped}件は対象外）")
    for no, q in missing:
        short = q if len(q) <= 120 else q[:117] + "..."
        print(f"  L{no}: \"{short}\"")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
