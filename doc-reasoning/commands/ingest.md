---
description: Ingest a document (file or URL) into the document reasoning workspace
argument-hint: <path|url>
arguments:
  - name: source
    type: string
    description: Path to file or URL to ingest (docx, xlsx, pptx, pdf, md, html, Confluence URL)
    required: true
---

# /doc:ingest — Bring a document into the reasoning workspace

<input type="text" id="source" placeholder="e.g. ./template.docx or https://confluence.company.com/display/SPACE/Page" required>

!script <<'INNERSCRIPT'
#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

SOURCE = sys.argv[1] if len(sys.argv) > 1 else ""
if not SOURCE:
    print("ERROR: source required", file=sys.stderr)
    sys.exit(1)

PLUGIN_DIR = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", ""))
WS_DIR = Path(".claude/doc-reasoning")

# Find next session number
session_num = 1
while (WS_DIR / f"session-{session_num}").exists():
    session_num += 1
SESSION_DIR = WS_DIR / f"session-{session_num}"
(SESSION_DIR / "output").mkdir(parents=True, exist_ok=True)

print(f"Session {session_num}")
print()

if re.match(r"^https?://", SOURCE, re.IGNORECASE):
    is_confluence = "confluence" in SOURCE.lower()

    if is_confluence:
        print("Detected Confluence URL")

        confluence_plugin = None
        plugin_cache = Path.home() / ".claude/plugins/cache"
        if plugin_cache.exists():
            for d in plugin_cache.glob("*/confluence-search"):
                if d.is_dir():
                    confluence_plugin = d
                    break

        if not confluence_plugin:
            print("WARNING: confluence-search plugin not found. Install it first for Confluence support.")
            print("Proceeding with generic web fetch...")

        confluence_pat = os.environ.get("CONFLUENCE_PAT", "")
        confluence_url_env = os.environ.get("CONFLUENCE_URL", "")

        if not confluence_pat or not confluence_url_env:
            print("WARNING: CONFLUENCE_PAT or CONFLUENCE_URL not set.")
            print("Set them: export CONFLUENCE_PAT=<token> CONFLUENCE_URL=<base-url>")
            print("Proceeding with generic web fetch...")

        page_id_match = re.search(r"(?:pageId=|/pages/)(\d+)", SOURCE)
        page_id = page_id_match.group(1) if page_id_match else ""

        if confluence_plugin and confluence_pat and confluence_url_env and page_id:
            print("Fetching Confluence page...")
            confluence_script = confluence_plugin / "scripts/confluence-api.py"

            raw_json_path = SESSION_DIR / "confluence-raw.json"
            result = subprocess.run(
                [sys.executable, str(confluence_script),
                 "get-page", page_id, "body.storage,space,version"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                print(f"ERROR: Failed to fetch Confluence page {page_id}", file=sys.stderr)
                sys.exit(1)
            raw_json_path.write_text(result.stdout, encoding="utf-8")

            data = json.loads(raw_json_path.read_text(encoding="utf-8"))
            title = data.get("title", "untitled")
            html_content = data.get("body", {}).get("storage", {}).get("value", "")
            safe_title = title.replace("/", "-")

            confluence_html = SESSION_DIR / "confluence-content.html"
            confluence_html.write_text(html_content, encoding="utf-8")

            print(f"Page: {title} (ID: {page_id})")
            print()

            subprocess.run(
                [sys.executable, str(PLUGIN_DIR / "scripts/html-to-md.py"),
                 str(confluence_html), str(SESSION_DIR / f"{safe_title}.md")],
                check=True,
            )

            meta = {
                "source": SOURCE,
                "format": "confluence",
                "ingested_at": datetime.now().isoformat(),
                "page_id": page_id,
                "title": title,
                "markdown": f"{safe_title}.md",
            }
            (SESSION_DIR / f"{safe_title}.meta.json").write_text(
                json.dumps(meta, indent=2), encoding="utf-8"
            )

            raw_json_path.unlink(missing_ok=True)
            confluence_html.unlink(missing_ok=True)
            print(f"Ingested: {SESSION_DIR / (safe_title + '.md')}")

        else:
            print("WARNING: Could not extract page ID from URL. Use a URL with pageId= or /pages/<id>")
            sys.exit(1)

    else:
        print("Fetching web page...")
        tmp_html = SESSION_DIR / "page.html"
        req = urllib.request.Request(SOURCE, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req) as resp:
                tmp_html.write_bytes(resp.read())
        except Exception as e:
            print(f"ERROR: Failed to fetch {SOURCE}: {e}", file=sys.stderr)
            sys.exit(1)

        name = "web-page"
        subprocess.run(
            [sys.executable, str(PLUGIN_DIR / "scripts/html-to-md.py"),
             str(tmp_html), str(SESSION_DIR / f"{name}.md")],
            check=True,
        )
        tmp_html.unlink(missing_ok=True)

        meta = {
            "source": SOURCE,
            "format": "web",
            "ingested_at": datetime.now().isoformat(),
            "markdown": f"{name}.md",
        }
        (SESSION_DIR / f"{name}.meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        print(f"Ingested: {SESSION_DIR / (name + '.md')}")

else:
    source_path = Path(SOURCE)
    if not source_path.exists():
        print(f"ERROR: File not found: {SOURCE}", file=sys.stderr)
        sys.exit(1)

    abs_source = source_path.resolve()
    print(f"Ingesting: {abs_source.name}")

    result = subprocess.run(
        [sys.executable, str(PLUGIN_DIR / "scripts/doc-to-md.py"),
         str(abs_source), str(SESSION_DIR)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    print(result.stdout, end="")

    print()
    print("---")
    print(f"Document is now available in session {session_num}")
    print("Use the doc-reasoning skill to load and reason about it.")

print()
print(f"Session directory: {SESSION_DIR}")
INNERSCRIPT

<local-command>
  ingest "${source}"
</local-command>
