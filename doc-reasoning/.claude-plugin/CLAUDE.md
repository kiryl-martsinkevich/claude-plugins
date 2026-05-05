# Document Reasoning Plugin

Ingest documents in multiple formats (docx, xlsx, pptx, pdf, confluence, markdown), convert them to a unified markdown representation, reason across them with Claude, and export analysis outputs back to target formats.

## Architecture

Three layers:
1. **Ingest** — documents → markdown, stored in `.claude/doc-reasoning/`
2. **Context** — `doc-reasoning` skill loads documents for reasoning
3. **Output** — markdown → target format (docx, pdf, confluence, md)

## Commands

- `/doc:ingest <path|url>` — ingest a document into the working directory
- `/doc:export <path> [--format <fmt>]` — export analysis to target format

## Skills

- `doc-reasoning` — load, compare, analyze, and produce outputs from ingested documents

## Hooks

- `SessionStart` — detect and resume previous document reasoning sessions

## Dependencies

- `pandoc` — docx, pdf conversion
- `python3` with `openpyxl`, `python-pptx` — xlsx, pptx extraction
- `pdftotext` (poppler-utils) — pdf text extraction
- `confluence-search` plugin — Confluence page ingest/export (provides `confluence-api.py`)

## Confluence Integration

When the `confluence-search` plugin is installed (either as a sibling directory or in the plugin cache), `/doc:ingest` uses its `confluence-api.py` to:
- Fetch Confluence page body via the REST API
- List and download `.docx`/`.xlsx`/`.pptx`/`.pdf` attachments on the page

Use the `confluence-search` skill to discover pages and find page IDs, then hand them off to `/doc:ingest <url>` for full ingestion.
