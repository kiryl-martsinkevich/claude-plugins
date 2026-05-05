---
description: Export analysis output to a target format
argument-hint: <path> [--format docx|pdf|html|confluence]
arguments:
  - name: path
    type: string
    description: Path to the markdown file to export (in .claude/doc-reasoning/session-N/output/)
    required: true
  - name: format
    type: string
    description: Target format (docx, pdf, md, html, confluence)
    required: false
---

# /doc:export — Export analysis to target format

<input type="text" id="path" placeholder="e.g. output/gap-analysis.md">
<input type="text" id="format" placeholder="Target format: docx, pdf, html, confluence (default: inferred from filename)">

!script <<'INNERSCRIPT'
#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

INPUT = sys.argv[1] if len(sys.argv) > 1 else ""
FORMAT = sys.argv[2] if len(sys.argv) > 2 else ""

if not INPUT:
    print("ERROR: path required", file=sys.stderr)
    sys.exit(1)

PLUGIN_DIR = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", ""))

# Resolve the input path
input_path = Path(INPUT)
if not input_path.exists():
    candidate = Path(".claude/doc-reasoning") / INPUT
    if candidate.exists():
        input_path = candidate
    else:
        base = Path(".claude/doc-reasoning")
        found = list(base.glob(f"*/{Path(INPUT).name}")) if base.exists() else []
        if found:
            input_path = found[0]
        else:
            print(f"ERROR: File not found: {INPUT}", file=sys.stderr)
            print(f"Looked in: {INPUT}, .claude/doc-reasoning/{INPUT}, and session directories",
                  file=sys.stderr)
            sys.exit(1)

input_name = input_path.stem
input_dir = input_path.parent

# Determine output directory
if input_dir.name == "output":
    outdir = input_dir
else:
    session_match = re.search(r"(\.claude/doc-reasoning/session-\d+)",
                              str(input_path).replace("\\", "/"))
    if session_match:
        outdir = Path(session_match.group(1)) / "output"
    else:
        outdir = input_dir
outdir.mkdir(parents=True, exist_ok=True)

# Determine format
if not FORMAT:
    print("No format specified. Infer from context or specify: --format docx|pdf|html|confluence")
    print("Defaulting to .docx")
    FORMAT = "docx"

output_path = outdir / f"{input_name}.{FORMAT}"

print(f"Exporting: {input_path}")
print(f"Format: {FORMAT}")
print(f"Output: {output_path}")
print()

if FORMAT == "confluence":
    confluence_pat = os.environ.get("CONFLUENCE_PAT", "")
    confluence_url_env = os.environ.get("CONFLUENCE_URL", "")

    if not confluence_pat or not confluence_url_env:
        print("ERROR: CONFLUENCE_PAT and CONFLUENCE_URL must be set for Confluence export.",
              file=sys.stderr)
        sys.exit(1)

    print("To push to Confluence, you need:")
    print("  1. The page ID to update, OR")
    print("  2. A space key and parent page to create a new page under")
    print()
    print("First, convert markdown to Confluence storage format HTML:")

    html_output = outdir / f"{input_name}.html"

    if shutil.which("pandoc"):
        result = subprocess.run(
            ["pandoc", "-f", "gfm", "-t", "html",
             str(input_path), "-o", str(html_output)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            md = input_path.read_text(encoding="utf-8")
            html = "<p>" + md.replace("\n\n", "</p>\n<p>").replace("\n", "<br/>\n") + "</p>"
            html_output.write_text(html, encoding="utf-8")
    else:
        md = input_path.read_text(encoding="utf-8")
        html = "<p>" + md.replace("\n\n", "</p>\n<p>").replace("\n", "<br/>\n") + "</p>"
        html_output.write_text(html, encoding="utf-8")

    print(f"HTML generated: {html_output}")
    print()
    print("To publish to Confluence, use the confluence-search plugin:")
    print("  python3 <confluence-api.py> get-page <page-id>  # to see current content")
    print("  Then use the Confluence REST API PUT /content/{id} to update")
    print()
    print("Or use the doc-reasoning skill which will guide you through the process.")

else:
    result = subprocess.run(
        [sys.executable, str(PLUGIN_DIR / "scripts/md-to-docx.py"),
         str(input_path), str(output_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    print(result.stdout, end="")
    print()
    print(f"Exported: {output_path}")
INNERSCRIPT

<local-command>
  export "${path}" "${format}"
</local-command>
