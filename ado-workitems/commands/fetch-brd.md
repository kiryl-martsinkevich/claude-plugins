---
name: fetch-brd
description: Extract BRD content from Azure DevOps work item attachments (docx/pdf)
allowed-tools:
  - Bash
  - Read
argument-hint: "<work-item-id>"
---

# Fetch BRD from Work Item Attachments

Download and extract Business Requirements Document (BRD) content from docx/pdf attachments on an Azure DevOps work item.

## Steps

1. **Validate input** — a work item ID must be provided.

2. **List attachments:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.sh" attachments <work-item-id>
   ```

3. **Identify BRD files** — filter for files with `.docx`, `.pdf`, `.doc` extensions. Also look for filenames containing "BRD", "requirement", "spec", or "PRD". If multiple candidates exist, show the list and let the user choose. If only one match, proceed automatically.

4. **Download the attachment:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.sh" download "<attachment-url>" "/tmp/ado-brd-<work-item-id>.<ext>"
   ```

5. **Extract content** based on file type:

   **For PDF files:**
   Use the Read tool directly — Claude natively supports PDF reading:
   ```
   Read /tmp/ado-brd-<id>.pdf
   ```

   **For DOCX files:**
   First try pandoc (if available):
   ```bash
   pandoc -f docx -t plain "/tmp/ado-brd-<id>.docx" 2>/dev/null
   ```

   If pandoc is not available, use python-docx:
   ```bash
   python3 -c "
   from docx import Document
   doc = Document('/tmp/ado-brd-<id>.docx')
   for p in doc.paragraphs:
       if p.text.strip():
           prefix = ''
           if p.style and p.style.name and 'Heading' in p.style.name:
               level = p.style.name.replace('Heading ', '')
               prefix = '#' * int(level) + ' ' if level.isdigit() else '## '
           print(prefix + p.text)
   for table in doc.tables:
       for row in table.rows:
           print(' | '.join(cell.text for cell in row.cells))
   "
   ```

   If neither is available, suggest the user install one:
   ```
   pip install python-docx   # or: apt install pandoc
   ```

6. **Present the BRD content** — show a structured summary with key sections:
   - **Scope** — what the document covers
   - **Requirements** — functional and non-functional requirements
   - **Acceptance Criteria** — how to validate
   - **Assumptions & Constraints** — limitations noted
   - **Dependencies** — external dependencies mentioned

   Quote relevant sections directly from the document.

7. **Clean up** — note the temp file location in case the user needs it again.

## Notes

- Large PDFs: use the `pages` parameter with Read tool to read specific page ranges
- If the document is very large, provide a summary first and offer to dive into specific sections
- Preserve formatting from the original document as much as possible
- If no BRD-like attachments are found, check the work item description itself — the BRD content may be inline
