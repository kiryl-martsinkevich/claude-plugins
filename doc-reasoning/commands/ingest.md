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
set -euo pipefail

SOURCE="${1:?source required}"
PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT}"
WS_DIR=".claude/doc-reasoning"

# Find next session number
SESSION_NUM=1
while [ -d "$WS_DIR/session-$SESSION_NUM" ]; do
  SESSION_NUM=$((SESSION_NUM + 1))
done
SESSION_DIR="$WS_DIR/session-$SESSION_NUM"
mkdir -p "$SESSION_DIR/output"

echo "Session $SESSION_NUM"
echo ""

# --- Case 1: URL (Confluence or web) ---
if echo "$SOURCE" | grep -qE '^https?://'; then
  # Check if this is a Confluence URL
  if echo "$SOURCE" | grep -qi confluence; then
    echo "Detected Confluence URL"

    # Check for confluence-search plugin
    CONFLUENCE_SEARCH_PLUGIN=""
    for d in "$HOME/.claude/plugins/cache/"*"/confluence-search"; do
      if [ -d "$d" ]; then CONFLUENCE_SEARCH_PLUGIN="$d"; break; fi
    done
    if [ -z "$CONFLUENCE_SEARCH_PLUGIN" ]; then
      echo "WARNING: confluence-search plugin not found. Install it first for Confluence support."
      echo "Proceeding with generic web fetch..."
    fi

    if [ -z "${CONFLUENCE_PAT:-}" ] || [ -z "${CONFLUENCE_URL:-}" ]; then
      echo "WARNING: CONFLUENCE_PAT or CONFLUENCE_URL not set."
      echo "Set them: export CONFLUENCE_PAT=<token> CONFLUENCE_URL=<base-url>"
      echo "Proceeding with generic web fetch..."
    fi

    # Extract page ID from URL if possible
    PAGE_ID=$(echo "$SOURCE" | grep -oP '(?:pageId=|/pages/)\K\d+' || echo "")

    if [ -n "$CONFLUENCE_SEARCH_PLUGIN" ] && [ -n "${CONFLUENCE_PAT:-}" ] && [ -n "${CONFLUENCE_URL:-}" ]; then
      echo "Fetching Confluence page..."
      CONFLUENCE_SCRIPT="$CONFLUENCE_SEARCH_PLUGIN/scripts/confluence-api.py"

      if [ -n "$PAGE_ID" ]; then
        # Get page content as HTML storage format
        python3 "$CONFLUENCE_SCRIPT" get-page "$PAGE_ID" "body.storage,space,version" > "$SESSION_DIR/confluence-raw.json" 2>/dev/null || {
          echo "ERROR: Failed to fetch Confluence page $PAGE_ID"
          exit 1
        }

        # Extract title and HTML content
        TITLE=$(python3 -c "
import json, sys
with open('$SESSION_DIR/confluence-raw.json') as f:
    data = json.load(f)
print(data.get('title', 'untitled'))
" 2>/dev/null || echo "untitled")

        python3 -c "
import json
with open('$SESSION_DIR/confluence-raw.json') as f:
    data = json.load(f)
html = data.get('body', {}).get('storage', {}).get('value', '')
print(html)
" > "$SESSION_DIR/confluence-content.html" 2>/dev/null

        echo "Page: $TITLE (ID: $PAGE_ID)"
        echo ""

        # Convert HTML to markdown
        python3 "$PLUGIN_DIR/scripts/html-to-md.py" \
          "$SESSION_DIR/confluence-content.html" \
          "$SESSION_DIR/${TITLE//\//-}.md"

        # Write metadata
        python3 -c "
import json
meta = {
    'source': '$SOURCE',
    'format': 'confluence',
    'ingested_at': __import__('datetime').datetime.now().isoformat(),
    'page_id': '$PAGE_ID',
    'title': '$TITLE',
    'markdown': '${TITLE//\//-}.md',
}
with open('$SESSION_DIR/${TITLE//\//-}.meta.json', 'w') as f:
    json.dump(meta, f, indent=2)
" 2>/dev/null

        rm -f "$SESSION_DIR/confluence-raw.json" "$SESSION_DIR/confluence-content.html"
        echo "Ingested: $SESSION_DIR/${TITLE//\//-}.md"

      else
        echo "WARNING: Could not extract page ID from URL. Use a URL with pageId= or /pages/<id>"
        exit 1
      fi
    fi

  else
    # Generic web URL — fetch and convert
    echo "Fetching web page..."
    TMP_HTML="$SESSION_DIR/page.html"
    python3 -c "
import urllib.request, sys
req = urllib.request.Request('$SOURCE', headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        sys.stdout.buffer.write(resp.read())
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" > "$TMP_HTML" 2>/dev/null || {
      echo "ERROR: Failed to fetch $SOURCE"
      exit 1
    }

    NAME="web-page"
    python3 "$PLUGIN_DIR/scripts/html-to-md.py" "$TMP_HTML" "$SESSION_DIR/${NAME}.md"
    rm -f "$TMP_HTML"

    python3 -c "
import json
meta = {
    'source': '$SOURCE',
    'format': 'web',
    'ingested_at': __import__('datetime').datetime.now().isoformat(),
    'markdown': '${NAME}.md',
}
with open('$SESSION_DIR/${NAME}.meta.json', 'w') as f:
    json.dump(meta, f, indent=2)
"
    echo "Ingested: $SESSION_DIR/${NAME}.md"
  fi

else
  # --- Case 2: Local file ---
  if [ ! -f "$SOURCE" ]; then
    echo "ERROR: File not found: $SOURCE"
    exit 1
  fi

  ABS_SOURCE=$(realpath "$SOURCE" 2>/dev/null || readlink -f "$SOURCE" 2>/dev/null || echo "$SOURCE")
  echo "Ingesting: $(basename "$ABS_SOURCE")"

  bash "$PLUGIN_DIR/scripts/doc-to-md.sh" "$ABS_SOURCE" "$SESSION_DIR"

  echo ""
  echo "---"
  echo "Document is now available in session $SESSION_NUM"
  echo "Use the doc-reasoning skill to load and reason about it."
fi

echo ""
echo "Session directory: $SESSION_DIR"
INNERSCRIPT

<local-command>
  ingest "${source}"
</local-command>
