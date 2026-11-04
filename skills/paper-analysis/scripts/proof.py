#!/usr/bin/env python3
"""docs-rules の機械の採点（score.mjs）を、トークンを節約する形で実行する。

使い方:
    python3 proof.py <report.md> [--max N] [--save <採点結果.json>] [--score <score.mjs のパス>]

- score.mjs の場所は、--score、環境変数 DOCS_RULES_SCORE、既定の置き場所の順に探す
- 採点結果の JSON は全部を --save に保存し、標準出力には違反を最大 N 件（既定30件）だけ短く出す
- 原文の引用（`原文：` を含む行）と根拠の場所（〔…〕）への指摘は、校正で直してはいけない箇所なので外す

終了コード: 0 = 違反なし、1 = 違反あり、3 = 採点できない（docs-rules がない、node がないなど）
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SEARCH_PATTERNS = [
    "~/.claude/plugins/marketplaces/*/skills/docs-rules/evaluators/score.mjs",
    "~/.claude/plugins/cache/*/docs-rules/*/skills/docs-rules/evaluators/score.mjs",
    "~/.claude/skills/docs-rules/evaluators/score.mjs",
    "~/.claude/skills/**/docs-rules/evaluators/score.mjs",
    "./.claude/skills/docs-rules/evaluators/score.mjs",
    # claude.ai などのアプリにzipでアップロードしたスキルの置き場所
    "/mnt/skills/*/docs-rules/evaluators/score.mjs",
    "/mnt/skills/**/docs-rules/evaluators/score.mjs",
]

CITATION = re.compile(r"〔[^〕]*〕")


def find_score(explicit: str | None) -> Path | None:
    for cand in (explicit, os.environ.get("DOCS_RULES_SCORE")):
        if cand and Path(cand).expanduser().is_file():
            return Path(cand).expanduser()
    found: list[Path] = []
    for pat in SEARCH_PATTERNS:
        found += [Path(p) for p in glob.glob(os.path.expanduser(pat), recursive=True)]
    if not found:
        return None
    # いちばん新しく更新されたものを使う
    return max(found, key=lambda p: p.stat().st_mtime)


VARIABLE = re.compile(r"(?<![A-Za-z])[A-Za-zα-ωΑ-Ω](?![A-Za-z])")


def known_false_positive(v: dict) -> bool:
    """論文分析の原稿で必ず出る、直す必要のない指摘。"""
    excerpt = v.get("excerpt") or ""
    if v.get("rule_id") == "NOT-012":  # 桁区切りを求める指摘。論文の数値は原文のとおりに書くため直さない
        return True
    if v.get("rule_id") == "NOT-036" and VARIABLE.search(excerpt):  # 変数名（k、τ など）を誤字とみなす指摘
        return True
    if "Blank line inside blockquote" in (v.get("fix") or ""):  # 引用を続けて置いたとき
        return True
    return False


def protected(line_text: str, column: int | None, excerpt: str) -> bool:
    if "原文：" in line_text or line_text.lstrip().startswith(">"):
        return True
    for m in CITATION.finditer(line_text):
        if column is not None and m.start() < column <= m.end() + 1:
            return True
        if excerpt and excerpt in m.group(0):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--max", type=int, default=30)
    ap.add_argument("--save")
    ap.add_argument("--score")
    args = ap.parse_args()

    score = find_score(args.score)
    if score is None:
        print("SKIP: docs-rules の score.mjs が見つからない。校正を飛ばす。", file=sys.stderr)
        return 3
    if shutil.which("node") is None:
        print("SKIP: node がない。校正を飛ばす。", file=sys.stderr)
        return 3

    proc = subprocess.run(["node", str(score), args.report], capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        print(f"SKIP: score.mjs が終了コード {proc.returncode} で終わった。\n{proc.stderr[-500:]}", file=sys.stderr)
        return 3
    result = json.loads(proc.stdout)
    if args.save:
        Path(args.save).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = Path(args.report).read_text(encoding="utf-8").splitlines()
    kept, dropped = [], 0
    for v in result.get("violations", []):
        ln = v.get("line")
        text = lines[ln - 1] if ln and 0 < ln <= len(lines) else ""
        if known_false_positive(v) or protected(text, v.get("column"), v.get("excerpt") or ""):
            dropped += 1
            continue
        kept.append(v)

    print(f"score.mjs: {score}")
    print(f"違反 {len(kept)}件（引用・根拠の場所・論文の数値・変数名への指摘 {dropped}件は除外）")
    for v in kept[: args.max]:
        print(f"L{v.get('line')} {v.get('rule_id')} 「{v.get('excerpt')}」 → {v.get('fix')}")
    if len(kept) > args.max:
        print(f"…ほか{len(kept) - args.max}件は上限のため渡さない")
    return 1 if kept else 0


if __name__ == "__main__":
    sys.exit(main())
