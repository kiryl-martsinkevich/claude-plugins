---
name: Document Reasoning
description: This skill should be used when the user wants to reason across documents — compare templates against actual pages, find gaps, synthesize information from multiple sources, check compliance, extract data, or produce analysis outputs. Triggers on: "compare these documents", "find gaps", "check against the template", "analyze the docs", "what's different between", "synthesize these", "extract from", or when the user has ingested documents and wants to work with them.
---

# Document Reasoning

Load and reason across documents in the working directory. Compare, analyze, find gaps, synthesize information, and produce outputs from ingested documents in multiple formats.

## Phase 1: Discovery

First, scan the working directory to see what's available:

```bash
find .claude/doc-reasoning -name "*.md" -not -path "*/output/*" 2>/dev/null | sort
```

If nothing is found, tell the user:
> No documents ingested yet. Use `/doc:ingest <path|url>` to bring documents into the workspace.

If sessions exist, present them as a table:

```
## Available Sessions

| Session | Documents | Formats | Ingested |
|---------|-----------|---------|----------|
| session-1 | template.md, page.md | docx, confluence | 2026-05-04 14:30 |
```

Also list any existing outputs:
```bash
find .claude/doc-reasoning -path "*/output/*.md" 2>/dev/null | sort
```

The user can say:
- "load session 1" — load all docs from a session
- "load template.md" — load a specific document
- "load template.md and page.md" — load multiple specific docs
- "compare template.md with page.md" — load two docs and run gap analysis

## Phase 2: Loading Documents

Load the requested documents using the Read tool. For each document, read the `.meta.json` file first to show context:

```bash
cat .claude/doc-reasoning/session-N/docname.meta.json
```

Then read the markdown content. If a document is very large (over ~2000 lines), load it in sections and summarize what's available. Offer to load specific sections on demand.

**Context management:**
- Track total lines loaded across documents
- If approaching context limits, warn the user: "These documents together are ~N lines. I'll load the key sections first. Tell me which parts to focus on."
- For large documents, start with headings only to give an overview:
  ```bash
  grep '^##' .claude/doc-reasoning/session-N/docname.md
  ```

## Phase 3: Reasoning

Once documents are loaded, reason according to the user's request. Common patterns are documented in `references/reasoning-patterns.md`. The most common:

### Gap Analysis (template vs. actual)
1. Identify the template document and the target document
2. Parse section headings from the template as expected structure
3. Check which sections exist, are partially present, or are entirely missing in the target
4. For each gap, note what the template expects vs. what the target contains
5. Produce a structured gap report

### Cross-Document Synthesis
1. Identify a topic/question that spans multiple documents
2. Extract relevant information from each document
3. Note conflicts, corroborations, and unique contributions
4. Produce a synthesis that combines findings

## Phase 4: Output

When analysis is complete, write findings to the session's output directory:

```bash
mkdir -p .claude/doc-reasoning/session-N/output
```

Write the analysis as a markdown file, then tell the user:
> Analysis written to `.claude/doc-reasoning/session-N/output/<name>.md`.
> To export: `/doc:export session-N/output/<name>.md --format docx`

For Confluence updates specifically:
> To push changes to Confluence, I'll need the target page ID. Use `/doc:export output/analysis.md --format confluence` and I'll guide you through publishing.

## Reference Files

- **`references/conversion-tools.md`** — Required tools, installation per OS, format limitations
- **`references/reasoning-patterns.md`** — Detailed analysis patterns with examples
- **`references/confluence-format.md`** — Confluence storage format mapping, limitations when converting
