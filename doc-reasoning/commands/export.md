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
set -euo pipefail

INPUT="${1:?path required}"
FORMAT="${2:-}"
PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT}"

# Resolve the input path
if [ -f "$INPUT" ]; then
  INPUT_PATH="$INPUT"
else
  # Try relative to workspace root
  INPUT_PATH=".claude/doc-reasoning/$INPUT" 2>/dev/null || true
  if [ ! -f "$INPUT_PATH" ]; then
    # Try to find the file in any session
    FOUND=$(find .claude/doc-reasoning -name "$(basename "$INPUT")" 2>/dev/null | head -1)
    if [ -n "$FOUND" ]; then
      INPUT_PATH="$FOUND"
    else
      echo "ERROR: File not found: $INPUT"
      echo "Looked in: $INPUT, .claude/doc-reasoning/$INPUT, and session directories"
      exit 1
    fi
  fi
fi

INPUT_NAME=$(basename "$INPUT_PATH" .md)

# Determine output directory (alongside input or in output/)
INPUT_DIR=$(dirname "$INPUT_PATH")
if echo "$INPUT_DIR" | grep -q '/output$'; then
  OUTDIR="$INPUT_DIR"
else
  # If input is a session doc, put output in the session's output/
  SESSION_DIR=$(echo "$INPUT_PATH" | grep -oP '\.claude/doc-reasoning/session-\d+' || echo "$INPUT_DIR")
  OUTDIR="$SESSION_DIR/output"
  mkdir -p "$OUTDIR"
fi

# Determine format
if [ -z "$FORMAT" ]; then
  echo "No format specified. Infer from context or specify: --format docx|pdf|html|confluence"
  echo "Defaulting to .docx"
  FORMAT="docx"
fi

OUTPUT="$OUTDIR/$INPUT_NAME.$FORMAT"

echo "Exporting: $INPUT_PATH"
echo "Format: $FORMAT"
echo "Output: $OUTPUT"
echo ""

case "$FORMAT" in
  confluence)
    # Check for confluence-search plugin
    CONFLUENCE_SEARCH_PLUGIN=""
    for d in "$HOME/.claude/plugins/cache/"*"/confluence-search"; do
      if [ -d "$d" ]; then CONFLUENCE_SEARCH_PLUGIN="$d"; break; fi
    done

    if [ -z "${CONFLUENCE_PAT:-}" ] || [ -z "${CONFLUENCE_URL:-}" ]; then
      echo "ERROR: CONFLUENCE_PAT and CONFLUENCE_URL must be set for Confluence export."
      exit 1
    fi

    echo "To push to Confluence, you need:"
    echo "  1. The page ID to update, OR"
    echo "  2. A space key and parent page to create a new page under"
    echo ""
    echo "First, convert markdown to Confluence storage format HTML:"

    HTML_OUTPUT="$OUTDIR/$INPUT_NAME.html"
    pandoc -f gfm -t html "$INPUT_PATH" -o "$HTML_OUTPUT" 2>/dev/null || {
      python3 -c "
import sys
from pathlib import Path
md = Path('$INPUT_PATH').read_text()
# Basic markdown to HTML
html = '<p>' + md.replace('\n\n', '</p>\n<p>').replace('\n', '<br/>\n') + '</p>'
Path('$HTML_OUTPUT').write_text(html)
"
    }

    echo "HTML generated: $HTML_OUTPUT"
    echo ""
    echo "To publish to Confluence, use the confluence-search plugin:"
    echo "  python3 <confluence-api.py> get-page <page-id>  # to see current content"
    echo "  Then use the Confluence REST API PUT /content/{id} to update"
    echo ""
    echo "Or use the doc-reasoning skill which will guide you through the process."
    ;;

  *)
    bash "$PLUGIN_DIR/scripts/md-to-docx.sh" "$INPUT_PATH" "$OUTPUT"
    echo ""
    echo "Exported: $OUTPUT"
    ;;
esac
INNERSCRIPT

<local-command>
  export "${path}" "${format}"
</local-command>
