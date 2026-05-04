#!/usr/bin/env bash
# md-to-docx.sh — Convert markdown to target formats
# Usage: md-to-docx.sh <input.md> <output-file>
# Supported output formats: .docx .pdf .md .txt .html (confluence)
set -euo pipefail

INPUT="$1"
OUTPUT="$2"
OUTDIR=$(dirname "$OUTPUT")
EXT="${OUTPUT##*.}"
EXT_LOWER=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')
LOGFILE="$OUTDIR/.export.log"

log() { echo "$(date -Iseconds) $*" >> "$LOGFILE"; }
die() { echo "ERROR: $*" >&2; log "FATAL: $*"; exit 1; }

[ -f "$INPUT" ] || die "Input file not found: $INPUT"
mkdir -p "$OUTDIR"
log "Exporting $INPUT → $OUTPUT ($EXT_LOWER)"

case "$EXT_LOWER" in
  docx)
    command -v pandoc >/dev/null 2>&1 || die "pandoc not found. Install: sudo apt install pandoc"
    pandoc -f gfm -t docx "$INPUT" -o "$OUTPUT" 2>>"$LOGFILE" || die "pandoc export failed"
    ;;
  pdf)
    command -v pandoc >/dev/null 2>&1 || die "pandoc not found. Install: sudo apt install pandoc"
    pandoc -f gfm -t pdf "$INPUT" -o "$OUTPUT" 2>>"$LOGFILE" || die "pandoc export failed"
    ;;
  md|markdown)
    cp "$INPUT" "$OUTPUT"
    ;;
  txt)
    command -v pandoc >/dev/null 2>&1 || die "pandoc not found. Install: sudo apt install pandoc"
    pandoc -f gfm -t plain "$INPUT" -o "$OUTPUT" 2>>"$LOGFILE" || die "pandoc export failed"
    ;;
  html|htm)
    command -v pandoc >/dev/null 2>&1 || die "pandoc not found. Install: sudo apt install pandoc"
    pandoc -f gfm -t html "$INPUT" -o "$OUTPUT" 2>>"$LOGFILE" || die "pandoc export failed"
    ;;
  *)
    die "Unsupported output format: .$EXT_LOWER. Supported: docx, pdf, md, txt, html"
    ;;
esac

log "Done: $OUTPUT ($(wc -c < "$OUTPUT") bytes)"
echo "$OUTPUT"
