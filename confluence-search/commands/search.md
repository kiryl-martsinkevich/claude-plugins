---
name: search
description: Search Confluence pages and attachments for documentation
allowed-tools:
  - Bash
  - Read
argument-hint: "<query> — e.g. 'microservices architecture in ENTARCH' or raw CQL"
---

# Search Confluence

Search for documentation across Confluence pages and attachments.

## Steps

1. **Parse the query** from the provided arguments:
   - If the query mentions a specific space key (e.g., "in ENTARCH", "TECHSTD"), target that space
   - If the query looks like raw CQL (contains `type =`, `space.key`, `AND`, `OR`), use it directly
   - Otherwise, consult the confluence-search skill's space configuration (`references/spaces.md`) to determine the best target space based on the topic
   - If no clear space match, search across all spaces

2. **Construct the CQL query:**

   For targeted space search:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/confluence-api.py" search-space "<query>" "<SPACE_KEY>"
   ```

   For cross-space search:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/confluence-api.py" search-compact 'type = page AND (text ~ "<query>" OR title ~ "<query>") ORDER BY lastModified DESC'
   ```

3. **Also search attachments** if the query suggests looking for documents (mentions "BRD", "spec", "document", "standard", "policy", "diagram", or file types like pdf/docx/xlsx):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/confluence-api.py" search-attachments "<query>" "<SPACE_KEY>"
   ```

4. **Display results** in a markdown table:

   | # | Title | Space | Last Updated | URL |
   |---|-------|-------|-------------|-----|

5. **If the user wants to read a specific result**, fetch the page content:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/confluence-api.py" get-page-text <page-id>
   ```

6. **For attachment results**, offer to download and read:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/confluence-api.py" download "<url>" "confluence-<id>.<ext>"
   ```
   Then use the Read tool for PDF files, or pandoc/python for docx/xlsx.

7. **If no results found**, suggest:
   - Broader search terms
   - Searching in different spaces
   - Checking with different keywords or labels

## Notes

- Default to searching pages AND attachments for comprehensive results
- For text searches, use `~` (contains) not `=` (exact match)
- Always add `ORDER BY lastModified DESC` for relevance
- Limit initial results to 25; offer to fetch more if needed
- Present URLs as clickable links when showing results
