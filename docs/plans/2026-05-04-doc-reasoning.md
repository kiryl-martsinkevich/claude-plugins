# Document Reasoning Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a plugin that ingests documents in multiple formats (docx, xlsx, pptx, pdf, confluence, markdown), converts them to markdown for unified reasoning, and exports analysis outputs back to target formats.

**Architecture:** Three layers — ingest (documents → markdown), context (skill loads docs for reasoning), output (markdown → target format). Working directory at `.claude/doc-reasoning/` with session-based organization.

**Tech Stack:** Bash scripts for conversion dispatch, Python 3 (stdlib + openpyxl, python-pptx), pandoc for docx/pdf conversion, existing confluence-search plugin for Confluence integration.

---

### Task 1: Plugin Scaffold and Manifest

**Files:**
- Create: `doc-reasoning/.claude-plugin/plugin.json`
- Create: `doc-reasoning/.claude-plugin/CLAUDE.md`

**Step 1: Create directory structure**

```bash
mkdir -p doc-reasoning/.claude-plugin
mkdir -p doc-reasoning/commands
mkdir -p doc-reasoning/scripts
mkdir -p doc-reasoning/skills/doc-reasoning/references
mkdir -p doc-reasoning/hooks
```

**Step 2: Write plugin.json**

```json
{
  "name": "doc-reasoning",
  "version": "0.1.0",
  "description": "Ingest documents in multiple formats, reason across them, and export analysis outputs",
  "author": { "name": "kiryl" },
  "keywords": ["documents", "analysis", "conversion", "docx", "pdf", "confluence", "template"]
}
```

**Step 3: Write CLAUDE.md**

Brief plugin overview and architecture summary.

**Step 4: Commit**

---

### Task 2: Document-to-Markdown Conversion Script

**Files:**
- Create: `doc-reasoning/scripts/doc-to-md.sh`

**Step 1: Write the dispatcher script**

Handles routing based on file extension:
- `.docx` → `pandoc -f docx -t gfm`
- `.xlsx` → Python openpyxl to extract sheets as markdown tables
- `.pptx` → Python python-pptx to extract slides as markdown
- `.pdf` → `pdftotext -layout` then markdown clean
- `.md` → copy as-is
- `.txt` → copy as-is

**Step 2: Test with sample files**

**Step 3: Commit**

---

### Task 3: Markdown-to-Target Export Script

**Files:**
- Create: `doc-reasoning/scripts/md-to-docx.sh`
- Create: `doc-reasoning/scripts/html-to-md.py`

**Step 1: Write md-to-docx.sh**

Handles routing based on target format:
- `.docx` → `pandoc -f gfm -t docx`
- `.pdf` → `pandoc -f gfm -t pdf`
- `.md` → copy as-is
- Confluence → convert markdown to Confluence storage format HTML, then PUT/POST via REST API

**Step 2: Write html-to-md.py**

Converts Confluence HTML storage format to markdown using Python stdlib (html.parser).

**Step 3: Test round-trip**

**Step 4: Commit**

---

### Task 4: Ingest Command

**Files:**
- Create: `doc-reasoning/commands/ingest.md`

**Step 1: Write the slash command**

`/doc:ingest <path|url>` — Detects format, runs appropriate converter, stores in `.claude/doc-reasoning/session-N/`, reports result.

**Step 2: Commit**

---

### Task 5: Export Command

**Files:**
- Create: `doc-reasoning/commands/export.md`

**Step 1: Write the slash command**

`/doc:export <path> [--format <fmt>] [--target confluence]` — Converts markdown to target format, handles Confluence page update/create.

**Step 2: Commit**

---

### Task 6: Document Reasoning Skill

**Files:**
- Create: `doc-reasoning/skills/doc-reasoning/SKILL.md`
- Create: `doc-reasoning/skills/doc-reasoning/references/conversion-tools.md`
- Create: `doc-reasoning/skills/doc-reasoning/references/reasoning-patterns.md`
- Create: `doc-reasoning/skills/doc-reasoning/references/confluence-format.md`

**Step 1: Write SKILL.md**

Main skill with discovery, loading, reasoning, and output guidance.

**Step 2: Write reference files**

Tool installation guides, analysis patterns, Confluence format mapping.

**Step 3: Commit**

---

### Task 7: SessionStart Hook

**Files:**
- Create: `doc-reasoning/hooks/session-start.md`

**Step 1: Write the hook**

Checks if `.claude/doc-reasoning/` exists, if so reports available sessions and offers to resume.

**Step 2: Commit**

---

### Task 8: Validation and Final Review

**Files:**
- Validate: `doc-reasoning/` all files

**Step 1: Validate plugin structure**

**Step 2: Review all files for correctness**

**Step 3: Final commit**
