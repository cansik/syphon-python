"""Build or serve the API documentation using pdoc's public command-line interface."""

import argparse
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=Path("docs"), help="HTML output directory (default: docs)")
    parser.add_argument(
        "--serve", action="store_true", help="Launch the local documentation server instead of writing HTML"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    command = [
        sys.executable,
        "-m",
        "pdoc",
        "syphon",
        "--footer-text",
        f"syphon-python v{version('syphon-python')}",
        "--logo-link",
        "https://github.com/cansik/syphon-python",
        "--template-directory",
        str(root / "doc/theme"),
    ]
    if not args.serve:
        command.extend(["--output-directory", str(args.output.resolve())])
    try:
        return subprocess.call(command, cwd=root)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
