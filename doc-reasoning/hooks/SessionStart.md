---
type: hook
event: SessionStart
description: Detect and resume previous document reasoning sessions
---

# Document Reasoning Session — Resume Check

!script <<'INNERSCRIPT'
if [ -d ".claude/doc-reasoning" ]; then
  SESSION_COUNT=$(find .claude/doc-reasoning -maxdepth 1 -type d -name "session-*" 2>/dev/null | wc -l)
  OUTPUT_COUNT=$(find .claude/doc-reasoning -path "*/output/*.md" 2>/dev/null | wc -l)

  if [ "$SESSION_COUNT" -gt 0 ]; then
    echo "---"
    echo "Previous document reasoning sessions found:"
    echo ""
    for session_dir in .claude/doc-reasoning/session-*; do
      if [ -d "$session_dir" ]; then
        session_name=$(basename "$session_dir")
        docs=$(find "$session_dir" -maxdepth 1 -name "*.md" -not -name ".*" 2>/dev/null | wc -l)
        outputs=$(find "$session_dir/output" -name "*.md" 2>/dev/null | wc -l)
        echo "  **$session_name:** $docs document(s), $outputs output(s)"
      fi
    done
    echo ""
    echo "Use the **doc-reasoning** skill to resume working with these documents."
    echo "Or start fresh with \`/doc:ingest <path>\`"
  fi

  if [ "$OUTPUT_COUNT" -gt 0 ]; then
    echo ""
    echo "Pending outputs (not yet exported):"
    find .claude/doc-reasoning -path "*/output/*.md" -exec echo "  - {}" \; 2>/dev/null
  fi
fi
INNERSCRIPT
