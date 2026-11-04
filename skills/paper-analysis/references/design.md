# レポートのデザイン

`scripts/render_html.py` が使う `assets/template.html` は、knk1313/workspace-ui-template-dads（https://github.com/knk1313/workspace-ui-template-dads）のデザインに合わせている。もとは、デジタル庁デザインシステム（DADS）の公式のデザイントークン（`@digital-go-jp/design-tokens` 2.0.1）である。

## 合わせていること

| 項目 | 内容 | テンプレートの出典 |
| --- | --- | --- |
| 色 | 面、文字、線、キーカラー、リンク、意味色をセマンティックの名前（`--color-surface` など）で定義。値はDADSのプリミティブ | `src/tokens/theme.css`、`primitives.css` |
| ダークモード | OSの設定に従う。`<html data-theme="light|dark">` で固定もできる | `src/tokens/theme-dark.css` |
| 文字 | Noto Sans JP。本文16px・行の高さ1.7、見出し24px／20px／18px（太字・1.5〜1.6）。14px未満は使わない | `src/tokens/typography.css` |
| フォーカス | 黒い4pxの線に黄色い2pxの帯（ダークでは入れ替え） | `theme.css` の `focus-ring` |
| 表 | ヘッダーは濃い灰の面と強調色の下線、数値の列は右寄せ・等幅数字 | DADSのテーブル |
| カード | 地（canvas）の上に白い面、`border-on-canvas` の枠、角丸8px、影なし | `docs/tokens.md`（カードは影なし） |

## レポートに固有の部品

- 根拠の場所 `〔p.5 §3.2〕`：控えめな面と枠の小さなラベル（14px）。本文を読む邪魔をせず、探せば見つかる強さにしている
- 原文の引用：キーカラーの左の線と薄い面。`lang="en"` を付け、読み上げで英語として読まれるようにしている
- 論文外の補足：警告の色の枠。論文の中の事実と区別するため、見た目を変えている

## 変えるとき

- 色を変えるときは、`:root`、`@media (prefers-color-scheme: dark)`、`:root[data-theme="dark"]` の3か所を同じように直す
- 文字と背景の組み合わせは、文字で4.5:1以上、線や部品で3:1以上を保つ。もとのテンプレートの `src/tokens/contrast.test.ts` で確かめた組み合わせだけを使っている
- もとのテンプレートのトークンが変わったら、`src/tokens/` の値を写し直す
