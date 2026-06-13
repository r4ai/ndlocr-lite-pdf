from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ndlocr_lite_pdf.cli import (
    CliOptions,
    UsageError,
    app,
    build_ndlocr_args,
    complete_shells,
    main,
    parse_options,
    run,
    validate_options,
)

runner = CliRunner()


def write_pdf(path: Path) -> None:
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [] /Count 0 >> endobj\n"
        b"trailer << /Root 1 0 R >>\n%%EOF\n"
    )


def base_options(input_pdf: Path, output_pdf: Path) -> CliOptions:
    return CliOptions(
        input_pdf=input_pdf,
        output_pdf=output_pdf,
        dpi=150.0,
        device="cpu",
        visible_text=False,
        viz=False,
        enable_tcy=False,
        artifacts_dir=None,
        overwrite=False,
    )


def test_missing_input_errors(tmp_path: Path) -> None:
    options = base_options(tmp_path / "missing.pdf", tmp_path / "out.pdf")

    with pytest.raises(UsageError, match="does not exist"):
        validate_options(options)


def test_non_pdf_input_errors(tmp_path: Path) -> None:
    input_file = tmp_path / "input.txt"
    input_file.write_text("not a pdf", encoding="utf-8")
    options = base_options(input_file, tmp_path / "out.pdf")

    with pytest.raises(UsageError, match="PDF"):
        validate_options(options)


def test_existing_output_requires_overwrite(tmp_path: Path) -> None:
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "out.pdf"
    write_pdf(input_pdf)
    write_pdf(output_pdf)
    options = base_options(input_pdf, output_pdf)

    with pytest.raises(UsageError, match="already exists"):
        validate_options(options)


def test_default_output_path(tmp_path: Path) -> None:
    input_pdf = tmp_path / "sample.pdf"
    write_pdf(input_pdf)

    options = parse_options(
        input_pdf=input_pdf,
        output_pdf=None,
        dpi=150.0,
        device="cpu",
        visible_text=False,
        viz=False,
        enable_tcy=False,
        artifacts_dir=None,
        overwrite=False,
    )

    assert options.output_pdf == tmp_path / "sample_ocr.pdf"


def test_build_ndlocr_args_contains_pdf_arguments(tmp_path: Path) -> None:
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "out.pdf"
    artifacts_dir = tmp_path / "artifacts"
    write_pdf(input_pdf)
    options = base_options(input_pdf, output_pdf)

    args = build_ndlocr_args(options, artifacts_dir)

    assert args[args.index("--sourcepdf") + 1] == str(input_pdf)
    assert args[args.index("--pdf-output") + 1] == str(output_pdf)
    assert args[args.index("--output") + 1] == str(artifacts_dir)
    assert args[args.index("--pdf-render-dpi") + 1] == "150.0"


def test_run_uses_temp_artifacts_dir_by_default(tmp_path: Path) -> None:
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "out.pdf"
    write_pdf(input_pdf)
    seen_args: list[str] = []

    def fake_runner(args: list[str]) -> None:
        seen_args.extend(args)

    run(base_options(input_pdf, output_pdf), runner=fake_runner)

    artifacts_dir = Path(seen_args[seen_args.index("--output") + 1])
    assert artifacts_dir.name.startswith("ndlocr-lite-pdf-")
    assert not artifacts_dir.exists()


def test_typer_help_includes_completion_options() -> None:
    result = runner.invoke(app, ["--help"], env={"COLUMNS": "120"})

    assert result.exit_code == 0
    assert "COMMAND" not in result.output
    assert "--install-completion" in result.output
    assert "--show-completion" in result.output
    assert "SHELL" in result.output


def test_show_completion_accepts_explicit_shell() -> None:
    result = runner.invoke(app, ["--show-completion", "zsh"])

    assert result.exit_code == 0
    assert "complete_zsh" in result.output
    assert "compdef" in result.output


def test_shell_completion_candidates() -> None:
    assert complete_shells() == ["bash", "fish", "powershell", "pwsh", "zsh"]


def test_typer_reports_usage_error(tmp_path: Path) -> None:
    with (
        pytest.raises(SystemExit) as exc_info,
        patch("sys.argv", ["ndlocr-lite-pdf", str(tmp_path / "missing.pdf")]),
    ):
        main()

    assert exc_info.value.code == 2
