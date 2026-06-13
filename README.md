# ndlocr-lite-pdf

PDFをNDLOCR-LiteでOCRし、透明テキストレイヤー付きの検索可能PDFを作るCLIです。

NDLOCR-Lite本体は公式リポジトリの `v1.2.3` を依存として固定し、このプロジェクトはPDF向けの入力検証と出力制御だけを薄く提供します。

## Setup

```bash
mise install
mise exec -- uv sync
```

## Usage

```bash
mise exec -- uv run ndlocr-lite-pdf input.pdf
mise exec -- uv run ndlocr-lite-pdf input.pdf -o output.pdf
mise exec -- uv run ndlocr-lite-pdf input.pdf -o output.pdf --dpi 200
mise exec -- uv run ndlocr-lite-pdf input.pdf -o output.pdf --artifacts-dir ./ocr-artifacts --enable-tcy
```

`-o/--output` を省略した場合は、入力PDFと同じディレクトリに `<input_stem>_ocr.pdf` を作成します。既存ファイルは `--overwrite` を付けた場合だけ上書きします。

## Options

- `input`: OCRするPDF
- `-o, --output`: 出力PDF。省略時は `<stem>_ocr.pdf`
- `--dpi`: OCR用にPDFページを画像化するDPI。既定値は `150`
- `--device cpu|cuda`: NDLOCR-Liteへ渡す推論デバイス。既定値は `cpu`
- `--visible-text`: デバッグ用にPDFテキストレイヤーを青文字で表示
- `--viz`: NDLOCR-Liteの認識可視化画像を出力
- `--enable-tcy`: 縦中横補正を有効化
- `--artifacts-dir`: txt/json/xml/vizなどの中間成果物を保存するディレクトリ。未指定時は一時ディレクトリを使い、PDFだけ残します
- `--overwrite`: 既存の出力PDFを上書き

## Shell completion

Typerの補完機能を有効にできます。

```bash
mise exec -- uv run ndlocr-lite-pdf --install-completion zsh
mise exec -- uv run ndlocr-lite-pdf --show-completion zsh
```

## Development

```bash
mise exec -- uv run pytest
mise exec -- uv run ruff format --check .
mise exec -- uv run ruff check .
mise exec -- uv run ty check src tests scripts
```

重いOCR本体を含む実行確認は、任意の小さなPDFで次を実行してください。

```bash
mise exec -- uv run ndlocr-lite-pdf sample.pdf -o sample_ocr.pdf --artifacts-dir ./ocr-artifacts
```

実行可能バイナリはPyInstallerで生成します。

```bash
mise exec -- uv sync --group build
mise exec -- uv run --group build python scripts/build_binary.py
```

`v*` タグをpushするとGitHub ActionsがLinux/macOS/Windowsでバイナリを作成し、GitHub Releaseへアップロードします。
