from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"


def main() -> None:
    DIST_DIR.mkdir(exist_ok=True)
    name = binary_name()
    workpath = ROOT / "build" / "pyinstaller"
    specpath = ROOT / "build" / "pyinstaller-spec"
    for path in (workpath, specpath):
        if path.exists():
            shutil.rmtree(path)

    subprocess.run(
        [
            "pyinstaller",
            "--name",
            name,
            "--onefile",
            "--clean",
            "--distpath",
            str(DIST_DIR),
            "--workpath",
            str(workpath),
            "--specpath",
            str(specpath),
            "--collect-all",
            "model",
            "--collect-all",
            "config",
            "--collect-all",
            "reading_order",
            "--collect-all",
            "pypdfium2",
            "--collect-all",
            "shellingham",
            "--hidden-import",
            "ocr",
            "--hidden-import",
            "deim",
            "--hidden-import",
            "parseq",
            "--hidden-import",
            "ndl_parser",
            "--hidden-import",
            "tablerecog",
            "--hidden-import",
            "tcy_wrapper",
            "--hidden-import",
            "shellingham.posix",
            "--hidden-import",
            "shellingham.nt",
            str(ROOT / "src" / "ndlocr_lite_pdf" / "__main__.py"),
        ],
        check=True,
        cwd=ROOT,
    )


def binary_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower().replace("amd64", "x86_64")
    suffix = ".exe" if system == "windows" else ""
    return f"ndlocr-lite-pdf-{system}-{machine}{suffix}"


if __name__ == "__main__":
    main()
