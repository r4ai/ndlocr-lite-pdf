from __future__ import annotations

import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from typer.completion import get_completion_script, install

SUPPORTED_SHELLS = {"bash", "zsh", "fish", "powershell", "pwsh"}
DEFAULT_PROG_NAME = "ndlocr-lite-pdf"

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Convert a PDF into a searchable PDF with NDLOCR-Lite.",
    name=DEFAULT_PROG_NAME,
    no_args_is_help=True,
)


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


def parse_options(
    input_pdf: Path,
    output_pdf: Path | None,
    dpi: float,
    device: str,
    visible_text: bool,
    viz: bool,
    enable_tcy: bool,
    artifacts_dir: Path | None,
    overwrite: bool,
) -> CliOptions:
    resolved_output_pdf = (
        output_pdf.expanduser()
        if output_pdf
        else input_pdf.expanduser().with_name(f"{input_pdf.stem}_ocr.pdf")
    )
    options = CliOptions(
        input_pdf=input_pdf.expanduser(),
        output_pdf=resolved_output_pdf,
        dpi=dpi,
        device=device,
        visible_text=visible_text,
        viz=viz,
        enable_tcy=enable_tcy,
        artifacts_dir=artifacts_dir.expanduser() if artifacts_dir else None,
        overwrite=overwrite,
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


def complete_shells() -> list[str]:
    return sorted(SUPPORTED_SHELLS)


def show_completion_callback(ctx: typer.Context, value: str | None) -> str | None:
    if not value or ctx.resilient_parsing:
        return value
    shell = normalize_shell(value)
    prog_name = ctx.find_root().info_name or DEFAULT_PROG_NAME
    typer.echo(
        get_completion_script(
            prog_name=prog_name,
            complete_var=completion_var(prog_name),
            shell=shell,
        )
    )
    raise typer.Exit()


def install_completion_callback(ctx: typer.Context, value: str | None) -> str | None:
    if not value or ctx.resilient_parsing:
        return value
    shell = normalize_shell(value)
    prog_name = ctx.find_root().info_name or DEFAULT_PROG_NAME
    installed_shell, path = install(
        shell=shell,
        prog_name=prog_name,
        complete_var=completion_var(prog_name),
    )
    typer.secho(f"{installed_shell} completion installed in {path}", fg="green")
    typer.echo("Completion will take effect once you restart the terminal")
    raise typer.Exit()


def normalize_shell(shell: str) -> str:
    normalized = shell.lower()
    if normalized not in SUPPORTED_SHELLS:
        supported = ", ".join(complete_shells())
        raise typer.BadParameter(f"shell must be one of: {supported}")
    return normalized


def completion_var(prog_name: str) -> str:
    return f"_{prog_name.replace('-', '_').upper()}_COMPLETE"


@app.command()
def cli(
    input_pdf: Annotated[
        Path,
        typer.Argument(
            exists=False,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=False,
            help="Path to the source PDF.",
        ),
    ],
    output_pdf: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Path to the output searchable PDF.",
        ),
    ] = None,
    dpi: Annotated[
        float,
        typer.Option(
            "--dpi",
            min=0.0,
            help="DPI used to render PDF pages for OCR.",
        ),
    ] = 150.0,
    device: Annotated[
        str,
        typer.Option(
            "--device",
            case_sensitive=False,
            help="Inference device passed to NDLOCR-Lite.",
        ),
    ] = "cpu",
    visible_text: Annotated[
        bool,
        typer.Option(
            "--visible-text",
            help="Draw the PDF text layer visibly in blue for debugging.",
        ),
    ] = False,
    viz: Annotated[
        bool,
        typer.Option("--viz", help="Save NDLOCR-Lite visualization artifacts."),
    ] = False,
    enable_tcy: Annotated[
        bool,
        typer.Option(
            "--enable-tcy",
            help="Enable tate-chuu-yoko correction in NDLOCR-Lite.",
        ),
    ] = False,
    artifacts_dir: Annotated[
        Path | None,
        typer.Option(
            "--artifacts-dir",
            file_okay=False,
            dir_okay=True,
            resolve_path=False,
            help="Directory for NDLOCR-Lite txt/json/xml/viz artifacts.",
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite the output PDF if it exists."),
    ] = False,
    show_completion: Annotated[
        str | None,
        typer.Option(
            "--show-completion",
            callback=show_completion_callback,
            autocompletion=complete_shells,
            is_eager=True,
            help="Show completion script for a shell.",
            metavar="SHELL",
        ),
    ] = None,
    install_completion: Annotated[
        str | None,
        typer.Option(
            "--install-completion",
            callback=install_completion_callback,
            autocompletion=complete_shells,
            is_eager=True,
            help="Install completion for a shell.",
            metavar="SHELL",
        ),
    ] = None,
) -> None:
    del show_completion, install_completion
    """Convert a PDF into a searchable PDF with NDLOCR-Lite."""
    if device not in {"cpu", "cuda"}:
        raise typer.BadParameter("device must be 'cpu' or 'cuda'")

    try:
        options = parse_options(
            input_pdf=input_pdf,
            output_pdf=output_pdf,
            dpi=dpi,
            device=device,
            visible_text=visible_text,
            viz=viz,
            enable_tcy=enable_tcy,
            artifacts_dir=artifacts_dir,
            overwrite=overwrite,
        )
        run(options)
    except UsageError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc


def main(argv: Sequence[str] | None = None) -> int:
    old_argv = sys.argv[:]
    try:
        if argv is not None:
            sys.argv = ["ndlocr-lite-pdf", *argv]
        app()
        return 0
    finally:
        sys.argv = old_argv


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()


if __name__ == "__main__":
    main()
