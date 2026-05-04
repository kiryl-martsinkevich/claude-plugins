#!/usr/bin/env bash
# doc-to-md.sh — Convert documents to markdown
# Usage: doc-to-md.sh <input-file> <output-dir>
# Supported: .docx .xlsx .pptx .pdf .md .txt .html
set -euo pipefail

INPUT="$1"
OUTDIR="$2"
BASENAME=$(basename "$INPUT")
NAME="${BASENAME%.*}"
EXT="${BASENAME##*.}"
EXT_LOWER=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')
OUTFILE="$OUTDIR/${NAME}.md"
LOGFILE="$OUTDIR/.convert.log"

log() { echo "$(date -Iseconds) $*" >> "$LOGFILE"; }
die() { echo "ERROR: $*" >&2; log "FATAL: $*"; exit 1; }

mkdir -p "$OUTDIR"
log "Converting $INPUT ($EXT_LOWER) → $OUTFILE"

case "$EXT_LOWER" in
  docx)
    command -v pandoc >/dev/null 2>&1 || die "pandoc not found. Install: sudo apt install pandoc"
    pandoc -f docx -t gfm --wrap=none "$INPUT" -o "$OUTFILE" 2>>"$LOGFILE" || die "pandoc conversion failed for $INPUT"
    ;;
  xlsx)
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/xlsx-to-md.py" "$INPUT" "$OUTFILE" 2>>"$LOGFILE" || die "xlsx conversion failed for $INPUT"
    ;;
  pptx)
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pptx-to-md.py" "$INPUT" "$OUTFILE" 2>>"$LOGFILE" || die "pptx conversion failed for $INPUT"
    ;;
  pdf)
    command -v pdftotext >/dev/null 2>&1 || die "pdftotext not found. Install: sudo apt install poppler-utils"
    TMP_TXT="$OUTDIR/${NAME}.txt"
    pdftotext -layout "$INPUT" "$TMP_TXT" 2>>"$LOGFILE" || die "pdftotext failed for $INPUT"
    # Clean up and add minimal markdown formatting
    cat "$TMP_TXT" > "$OUTFILE"
    rm -f "$TMP_TXT"
    ;;
  md|markdown)
    cp "$INPUT" "$OUTFILE"
    ;;
  txt)
    cp "$INPUT" "$OUTFILE"
    ;;
  html|htm)
    command -v pandoc >/dev/null 2>&1 || die "pandoc not found. Install: sudo apt install pandoc"
    pandoc -f html -t gfm --wrap=none "$INPUT" -o "$OUTFILE" 2>>"$LOGFILE" || die "pandoc conversion failed for $INPUT"
    ;;
  *)
    die "Unsupported format: .$EXT_LOWER. Supported: docx, xlsx, pptx, pdf, md, txt, html"
    ;;
esac

# Write metadata
META="$OUTDIR/${NAME}.meta.json"
SIZE=$(stat -c%s "$INPUT" 2>/dev/null || stat -f%z "$INPUT" 2>/dev/null || echo "0")
python3 -c "
import json, os
meta = {
    'source': os.path.basename('$INPUT'),
    'format': '$EXT_LOWER',
    'ingested_at': __import__('datetime').datetime.now().isoformat(),
    'original_size': $SIZE,
    'markdown': os.path.basename('$OUTFILE'),
}
with open('$META', 'w') as f:
    json.dump(meta, f, indent=2)
" 2>>"$LOGFILE"

log "Done: $OUTFILE ($(wc -c < "$OUTFILE") bytes)"
echo "$OUTFILE"
