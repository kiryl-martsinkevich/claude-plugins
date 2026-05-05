#!/usr/bin/env python3
"""Convert documents to markdown.

Usage: doc-to-md.py <input-file> <output-dir>
Supported: .docx .xlsx .pptx .pdf .md .txt .html
"""

import json
import os
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
        print(f"Usage: {sys.argv[0]} <input-file> <output-dir>", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    outdir = Path(sys.argv[2])

    name = input_path.stem
    ext = input_path.suffix.lstrip(".").lower()
    outfile = outdir / f"{name}.md"
    logfile = outdir / ".convert.log"

    outdir.mkdir(parents=True, exist_ok=True)
    log(logfile, f"Converting {input_path} ({ext}) -> {outfile}")

    # Locate sibling scripts next to this file
    scripts_dir = Path(__file__).parent

    if ext == "docx":
        if not shutil.which("pandoc"):
            die(logfile, "pandoc not found. Install: https://pandoc.org/installing.html")
        result = subprocess.run(
            ["pandoc", "-f", "docx", "-t", "gfm", "--wrap=none",
             str(input_path), "-o", str(outfile)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            log(logfile, result.stderr)
            die(logfile, f"pandoc conversion failed for {input_path}")

    elif ext == "xlsx":
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "xlsx-to-md.py"),
             str(input_path), str(outfile)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            log(logfile, result.stderr)
            die(logfile, f"xlsx conversion failed for {input_path}")

    elif ext == "pptx":
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "pptx-to-md.py"),
             str(input_path), str(outfile)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            log(logfile, result.stderr)
            die(logfile, f"pptx conversion failed for {input_path}")

    elif ext == "pdf":
        if not shutil.which("pdftotext"):
            die(logfile, "pdftotext not found. Install poppler-utils: "
                "https://poppler.freedesktop.org/")
        tmp_txt = outdir / f"{name}.txt"
        result = subprocess.run(
            ["pdftotext", "-layout", str(input_path), str(tmp_txt)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            log(logfile, result.stderr)
            die(logfile, f"pdftotext failed for {input_path}")
        shutil.move(str(tmp_txt), str(outfile))

    elif ext in ("md", "markdown", "txt"):
        shutil.copy(str(input_path), str(outfile))

    elif ext in ("html", "htm"):
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "html-to-md.py"),
             str(input_path), str(outfile)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            log(logfile, result.stderr)
            die(logfile, f"html conversion failed for {input_path}")

    else:
        die(logfile, f"Unsupported format: .{ext}. "
            "Supported: docx, xlsx, pptx, pdf, md, txt, html")

    meta_file = outdir / f"{name}.meta.json"
    meta = {
        "source": input_path.name,
        "format": ext,
        "ingested_at": datetime.now().isoformat(),
        "original_size": input_path.stat().st_size,
        "markdown": outfile.name,
    }
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    log(logfile, f"Done: {outfile} ({outfile.stat().st_size} bytes)")
    print(str(outfile))


if __name__ == "__main__":
    main()
