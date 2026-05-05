---
type: hook
event: SessionStart
description: Detect and resume previous document reasoning sessions
---

# Document Reasoning Session — Resume Check

!script <<'INNERSCRIPT'
#!/usr/bin/env python3
from pathlib import Path

ws_dir = Path(".claude/doc-reasoning")
if not ws_dir.exists():
    raise SystemExit(0)

sessions = sorted(ws_dir.glob("session-*"))
output_files = sorted(ws_dir.glob("*/output/*.md"))

if sessions:
    print("---")
    print("Previous document reasoning sessions found:")
    print()
    for session_dir in sessions:
        docs = len(list(session_dir.glob("*.md")))
        outputs_dir = session_dir / "output"
        outputs = len(list(outputs_dir.glob("*.md"))) if outputs_dir.exists() else 0
        print(f"  **{session_dir.name}:** {docs} document(s), {outputs} output(s)")
    print()
    print("Use the **doc-reasoning** skill to resume working with these documents.")
    print("Or start fresh with `/doc:ingest <path>`")

if output_files:
    print()
    print("Pending outputs (not yet exported):")
    for f in output_files:
        print(f"  - {f}")
INNERSCRIPT
