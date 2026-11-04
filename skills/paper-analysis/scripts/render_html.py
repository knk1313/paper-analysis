#!/usr/bin/env python3
"""レポートの原稿（Markdown）を、DADS のトークンに沿った1ファイルの HTML にする。

使い方:
    python3 render_html.py <report.md> <出力.html>

外部のライブラリーは使わない。原稿で使う記法だけに対応する。
- `# ` タイトル（1個）。直後の段落は副題になる
- `## ` 節（目次に載る）、`### ` `#### ` 小見出し
- 段落、箇条書き（`- ` と `1. `、2段まで）、表（`| a | b |`）、コードブロック、`---`
- 引用：`> 原文："..."` は原文の引用として、`> 論文外の補足：...` は注意の枠として表示する
- 行内：`**太字**`、`` `コード` ``、`[文字](URL)`、裸の URL、根拠の場所 `〔...〕`
"""
from __future__ import annotations

import html
import re
import sys
from datetime import date
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"

NUM_CELL = re.compile(r"^[\s(（]*[-+−±]?[\d.,]+\s*(%|％|pt|ms|s|x|×|倍|件|人|M|B|K|k)?[\s)）]*$")


def inline(text: str) -> str:
    codes: list[str] = []

    def keep_code(m: re.Match) -> str:
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep_code, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    links: list[str] = []

    def keep_link(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        links.append(f'<a href="{html.escape(url, quote=True)}">{label}</a>')
        return f"\x01{len(links) - 1}\x01"

    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", keep_link, text)
    text = re.sub(
        r"(?<![\"'=])(https?://[^\s<>）」』、。]+)",
        lambda m: f'<a href="{html.escape(m.group(1), quote=True)}">{m.group(1)}</a>',
        text,
    )
    text = re.sub(r"\x01(\d+)\x01", lambda m: links[int(m.group(1))], text)
    text = re.sub(r"〔([^〕]+)〕", r'<span class="cite">〔\1〕</span>', text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{html.escape(codes[int(m.group(1))], quote=False)}</code>", text)
    return text


def render_table(rows: list[str]) -> str:
    def cells(row: str) -> list[str]:
        row = row.strip()
        if row.startswith("|"):
            row = row[1:]
        if row.endswith("|"):
            row = row[:-1]
        return [c.strip() for c in re.split(r"(?<!\\)\|", row)]

    head = cells(rows[0])
    body_rows = [cells(r) for r in rows[2:]] if len(rows) > 1 and re.match(r"^\s*\|?\s*:?-{3,}", rows[1]) else [cells(r) for r in rows[1:]]
    out = ['<div class="table-wrap"><table>', "<thead><tr>"]
    out += [f'<th scope="col">{inline(c)}</th>' for c in head]
    out.append("</tr></thead><tbody>")
    for r in body_rows:
        out.append("<tr>")
        for i, c in enumerate(r):
            cls = ' class="num"' if NUM_CELL.match(c) else ""
            tag = "th" if i == 0 else "td"
            scope = ' scope="row"' if i == 0 else ""
            out.append(f"<{tag}{scope}{cls}>{inline(c)}</{tag}>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def render_quote(lines: list[str]) -> str:
    text = " ".join(l.strip() for l in lines).strip()
    m = re.match(r"^原文[：:]\s*(.*)$", text)
    if m:
        return (
            '<blockquote><span class="quote-label">原文</span>'
            f'<p class="quote-text" lang="en">{inline(m.group(1))}</p></blockquote>'
        )
    m = re.match(r"^論文外の補足[：:]\s*(.*)$", text)
    if m:
        return f'<div class="note" role="note"><span class="note-label">論文外の補足</span><p>{inline(m.group(1))}</p></div>'
    paras = "".join(f"<p>{inline(l)}</p>" for l in lines if l.strip())
    return f"<blockquote>{paras}</blockquote>"


LIST_ITEM = re.compile(r"^(\s*)([-*]|\d+[.)])\s+(.*)$")


def render_list(lines: list[str]) -> str:
    """2段までの入れ子に対応した箇条書き。"""
    out: list[str] = []
    stack: list[tuple[int, str]] = []  # (字下げ, タグ)
    for line in lines:
        m = LIST_ITEM.match(line)
        if not m:
            # 前の項目の続きの行
            if out:
                out[-1] = out[-1].removesuffix("</li>") + " " + inline(line.strip()) + "</li>"
            continue
        indent, marker, content = len(m.group(1).replace("\t", "    ")), m.group(2), m.group(3)
        tag = "ol" if marker[0].isdigit() else "ul"
        if not stack or indent > stack[-1][0]:
            if stack and out and out[-1].endswith("</li>"):
                out[-1] = out[-1].removesuffix("</li>")
            out.append(f"<{tag}>")
            stack.append((indent, tag))
        else:
            while stack and indent < stack[-1][0]:
                _, t = stack.pop()
                out.append(f"</{t}></li>")
        out.append(f"<li>{inline(content)}</li>")
    while stack:
        _, t = stack.pop()
        out.append(f"</{t}>" + ("</li>" if stack else ""))
    return "".join(out)


def convert(md: str) -> tuple[str, str, str, list[tuple[str, str]]]:
    lines = md.splitlines()
    title, subtitle = "論文分析レポート", ""
    sections: list[tuple[str, str, list[str]]] = []  # (id, 見出し, 本文の HTML の断片)
    preamble: list[str] = []
    cur: list[str] = preamble
    i, n = 0, len(lines)
    expect_subtitle = False

    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith("<!--"):
            while i < n and "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        if s.startswith("```"):
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            cur.append(f"<pre><code>{html.escape(chr(10).join(buf), quote=False)}</code></pre>")
            expect_subtitle = False
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            if level == 1:
                title = text
                expect_subtitle = True
            elif level == 2:
                sid = f"s{len(sections) + 1}"
                sections.append((sid, text, []))
                cur = sections[-1][2]
                expect_subtitle = False
            else:
                cur.append(f"<h{level}>{inline(text)}</h{level}>")
                expect_subtitle = False
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,})$", s):
            cur.append("<hr>")
            i += 1
            continue
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            cur.append(render_quote(buf))
            expect_subtitle = False
            continue
        if s.startswith("|"):
            buf = []
            while i < n and lines[i].strip().startswith("|"):
                buf.append(lines[i])
                i += 1
            cur.append(render_table(buf))
            expect_subtitle = False
            continue
        if LIST_ITEM.match(line):
            buf = []
            while i < n and lines[i].strip() and (LIST_ITEM.match(lines[i]) or lines[i].startswith((" ", "\t"))):
                buf.append(lines[i])
                i += 1
            cur.append(render_list(buf))
            expect_subtitle = False
            continue
        # 段落
        buf = []
        while i < n and lines[i].strip() and not re.match(r"^\s*(#{1,4}\s|>|\||```|[-*]\s|\d+[.)]\s)", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        para = " ".join(buf) if not all(re.search(r"[　-鿿]$", b) for b in buf[:-1]) else "".join(buf)
        if expect_subtitle and not sections:
            subtitle = para
            expect_subtitle = False
        else:
            cur.append(f"<p>{inline(para)}</p>")
    body_parts = []
    if preamble:
        body_parts.append("<section>" + "".join(preamble) + "</section>")
    for sid, head, frags in sections:
        body_parts.append(
            f'<section aria-labelledby="{sid}"><h2 id="{sid}">{inline(head)}</h2>' + "".join(frags) + "</section>"
        )
    toc = [(sid, head) for sid, head, _ in sections]
    return title, subtitle, "\n".join(body_parts), toc


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    title, subtitle, body, toc = convert(src.read_text(encoding="utf-8"))
    toc_html = "<ol>" + "".join(f'<li><a href="#{sid}">{inline(h)}</a></li>' for sid, h in toc) + "</ol>"
    plain_title = re.sub(r"<[^>]+>", "", inline(title))
    page = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("<title>{{TITLE}}</title>", f"<title>{plain_title}</title>")
        .replace("{{TITLE}}", inline(title))
        .replace("{{SUBTITLE}}", f'<p class="subtitle">{inline(subtitle)}</p>' if subtitle else "")
        .replace("{{TOC}}", toc_html)
        .replace("{{BODY}}", body)
        .replace("{{GENERATED}}", f"作成日：{date.today().isoformat()}")
    )
    dst.write_text(page, encoding="utf-8")
    print(f"書き出し：{dst}（節 {len(toc)}個）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
