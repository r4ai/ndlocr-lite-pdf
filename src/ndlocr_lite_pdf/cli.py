from __future__ import annotations

import argparse
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


class UsageError(Exception):
    """Error caused by invalid CLI input."""


@dataclass(frozen=True)
class CliOptions:
    input_pdf: Path
    output_pdf: Path
    dpi: float
    device: str
    visible_text: bool
    viz: bool
    enable_tcy: bool
    artifacts_dir: Path | None
    overwrite: bool


OcrRunner = Callable[[list[str]], None]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ndlocr-lite-pdf",
        description="Convert a PDF into a searchable PDF with NDLOCR-Lite.",
    )
    parser.add_argument("input", help="Path to the source PDF")
    parser.add_argument("-o", "--output", help="Path to the output searchable PDF")
    parser.add_argument(
        "--dpi",
        type=float,
        default=150.0,
        help="DPI used to render PDF pages for OCR. Default: 150",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default="cpu",
        help="Inference device passed to NDLOCR-Lite. Default: cpu",
    )
    parser.add_argument(
        "--visible-text",
        action="store_true",
        help="Draw the PDF text layer visibly in blue for debugging",
    )
    parser.add_argument(
        "--viz",
        action="store_true",
        help="Save NDLOCR-Lite visualization artifacts",
    )
    parser.add_argument(
        "--enable-tcy",
        action="store_true",
        help="Enable tate-chuu-yoko correction in NDLOCR-Lite",
    )
    parser.add_argument(
        "--artifacts-dir",
        help="Directory for NDLOCR-Lite txt/json/xml/viz artifacts",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output PDF if it already exists",
    )
    return parser


def parse_options(argv: Sequence[str] | None = None) -> CliOptions:
    args = build_parser().parse_args(argv)
    input_pdf = Path(args.input).expanduser()
    output_pdf = (
        Path(args.output).expanduser()
        if args.output
        else input_pdf.with_name(f"{input_pdf.stem}_ocr.pdf")
    )
    artifacts_dir = Path(args.artifacts_dir).expanduser() if args.artifacts_dir else None

    options = CliOptions(
        input_pdf=input_pdf,
        output_pdf=output_pdf,
        dpi=args.dpi,
        device=args.device,
        visible_text=args.visible_text,
        viz=args.viz,
        enable_tcy=args.enable_tcy,
        artifacts_dir=artifacts_dir,
        overwrite=args.overwrite,
    )
    validate_options(options)
    return options


def validate_options(options: CliOptions) -> None:
    if not options.input_pdf.exists():
        raise UsageError(f"input PDF does not exist: {options.input_pdf}")
    if not options.input_pdf.is_file():
        raise UsageError(f"input path is not a file: {options.input_pdf}")
    if options.input_pdf.suffix.lower() != ".pdf":
        raise UsageError(f"input must be a PDF file: {options.input_pdf}")
    if options.output_pdf.suffix.lower() != ".pdf":
        raise UsageError(f"output must be a PDF file: {options.output_pdf}")
    if options.dpi <= 0:
        raise UsageError("--dpi must be greater than 0")
    if options.output_pdf.exists() and not options.overwrite:
        raise UsageError(
            f"output PDF already exists: {options.output_pdf} "
            "(use --overwrite to replace it)"
        )
    if _same_path(options.input_pdf, options.output_pdf):
        raise UsageError("output PDF must be different from the input PDF")


def build_ndlocr_args(
    options: CliOptions,
    artifacts_dir: Path,
) -> list[str]:
    args = [
        "--sourcepdf",
        str(options.input_pdf),
        "--output",
        str(artifacts_dir),
        "--pdf-output",
        str(options.output_pdf),
        "--pdf-render-dpi",
        str(options.dpi),
        "--device",
        options.device,
    ]
    if options.visible_text:
        args.append("--pdf-visible-text")
    if options.viz:
        args.extend(["--viz", "True"])
    if options.enable_tcy:
        args.append("--enable-tcy")
    return args


def run_ndlocr_lite(ndlocr_args: list[str]) -> None:
    import ocr

    old_argv = sys.argv[:]
    try:
        sys.argv = ["ndlocr-lite", *ndlocr_args]
        ocr.main()
    finally:
        sys.argv = old_argv


def run(options: CliOptions, runner: OcrRunner = run_ndlocr_lite) -> None:
    options.output_pdf.parent.mkdir(parents=True, exist_ok=True)

    if options.artifacts_dir is not None:
        options.artifacts_dir.mkdir(parents=True, exist_ok=True)
        runner(build_ndlocr_args(options, options.artifacts_dir))
        return

    with tempfile.TemporaryDirectory(prefix="ndlocr-lite-pdf-") as tmpdir:
        runner(build_ndlocr_args(options, Path(tmpdir)))


def main(argv: Sequence[str] | None = None) -> int:
    try:
        options = parse_options(argv)
        run(options)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()


if __name__ == "__main__":
    raise SystemExit(main())
