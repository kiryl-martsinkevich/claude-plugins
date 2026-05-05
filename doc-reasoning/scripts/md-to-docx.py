#!/usr/bin/env python3
"""Convert markdown to target formats.

Usage: md-to-docx.py <input.md> <output-file>
Supported output formats: .docx .pdf .md .txt .html
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def log(logfile: Path, message: str) -> None:
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} {message}\n")


def die(logfile: Path, message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    log(logfile, f"FATAL: {message}")
    sys.exit(1)


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.md> <output-file>", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    outdir = output_path.parent
    ext = output_path.suffix.lstrip(".").lower()
    logfile = outdir / ".export.log"

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    outdir.mkdir(parents=True, exist_ok=True)
    log(logfile, f"Exporting {input_path} -> {output_path} ({ext})")

    if ext in ("docx", "pdf", "txt", "html", "htm"):
        if not shutil.which("pandoc"):
            die(logfile, "pandoc not found. Install: https://pandoc.org/installing.html")
        fmt_map = {"txt": "plain", "htm": "html"}
        target_fmt = fmt_map.get(ext, ext)
        result = subprocess.run(
            ["pandoc", "-f", "gfm", "-t", target_fmt,
             str(input_path), "-o", str(output_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            log(logfile, result.stderr)
            die(logfile, f"pandoc export failed: {result.stderr}")

    elif ext in ("md", "markdown"):
        shutil.copy(str(input_path), str(output_path))

    else:
        die(logfile, f"Unsupported output format: .{ext}. "
            "Supported: docx, pdf, md, txt, html")

    log(logfile, f"Done: {output_path} ({output_path.stat().st_size} bytes)")
    print(str(output_path))


if __name__ == "__main__":
    main()
