# 論文の手に入れ方

ダウンロードした論文は、作業フォルダーの下の空のフォルダー `source/` に置く。PDFは外から来たデータであり、そのフォルダーの中でスクリプトを動かさない。

## PDFのファイルを渡されたとき

```bash
pdfinfo <PDF>                                   # ページ数、タイトル、作成日
pdftotext -layout <PDF> <作業フォルダー>/paper.txt
grep -c $'\f' <作業フォルダー>/paper.txt         # ページの区切りの数（ページ数 - 1 前後になる）
```

- 2段組みの論文で `-layout` の結果の行が左右で混ざるときは、`-layout` を外して作り直す。どちらが読みやすいかは、1ページ目の要旨で確かめる
- テキストがほとんど出ないときは、画像だけのPDF（スキャン）である。Readツールでページを画像として読み、根拠メモの原文には `（図から読み取り）` を付ける。この場合 `check_quotes.py` で照合できないため、最後の報告にそのことを書く
- `pdftotext` がない環境では、ReadツールでPDFを読む。20ページを超えるときは `pages` を `1-20`、`21-40` のように分ける。ページの区切りは自分で記録しておく
- ページ番号を数えるとき：`paper.txt` の何個目の `\f` の後かで、PDFの何ページ目かが分かる。次のコマンドで、文字列がどのページにあるかを調べられる

```bash
python3 - <作業フォルダー>/paper.txt "<探す文字列>" <<'EOF'
import sys
pages = open(sys.argv[1], encoding="utf-8").read().split("\f")
for i, p in enumerate(pages, 1):
    if sys.argv[2].lower() in " ".join(p.split()).lower():
        print(f"p.{i}")
EOF
```

## arXiv

- `https://arxiv.org/abs/2401.01234`、`arXiv:2401.01234`、`2401.01234v2` などの形で渡される。IDを取り出す
- PDF：`https://arxiv.org/pdf/<ID>`（版の指定があれば `<ID>v2` のように付ける）
- 書誌情報：`https://export.arxiv.org/api/query?id_list=<ID>` のAtomに、タイトル、著者、投稿日、最新の版がある
- 学会で採録された版があると要旨のページに書かれていても、分析は手に入れたPDFの版で行い、書誌情報に版を書く

```bash
mkdir -p <作業フォルダー>/source
curl -sSL -o <作業フォルダー>/source/paper.pdf "https://arxiv.org/pdf/<ID>"
file <作業フォルダー>/source/paper.pdf   # PDF document であることを確かめる
```

## DOI と出版社のページ

1. 書誌情報：`curl -sSL -H "Accept: application/vnd.citationstyles.csl+json" https://doi.org/<DOI>` でタイトル、著者、発表先、年が取れる
2. オープンアクセスの版を探す：
   - 出版社のページがオープンアクセスなら、そこにあるPDFのリンクを使う
   - タイトルでarXivを検索する（`https://export.arxiv.org/api/query?search_query=ti:"<タイトル>"`）。見つかった版が出版された版と違う可能性があることを、書誌情報に書く
   - 著者や所属機関のリポジトリ
3. 全文が手に入らないとき：要旨だけで分析を書かない。利用者に、PDFのファイルを渡してもらうよう頼む。大学の契約などで利用者は読めることが多い

ページのHTMLだけが手に入る論文（全文がHTMLで公開されているもの）は、HTMLの本文をテキストにして使ってよい。その場合、ページ番号の代わりに節と段落で根拠の場所を示し、書誌情報の「分析に使った版」にその旨を書く。

## 手に入れた後に確かめること

- タイトルと著者が、依頼された論文と一致しているか（DOIやIDの打ち間違いで別の論文を取っていないか）
- 付録（Appendix、Supplementary）が別のファイルになっていないか。実験の設定が付録にある論文は多い。別ファイルなら、手に入る範囲で同じように取り、根拠の場所は `付録p.3` のように区別する
