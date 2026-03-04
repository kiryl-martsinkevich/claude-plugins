---
name: Confluence Search
description: This skill should be used when the user asks to "search Confluence", "find documentation", "look up in Confluence", "search wiki", "find architecture docs", "find standards", "technology standards", "check Confluence for", mentions Confluence spaces like ENTARCH/TECHSTD, or needs to retrieve content from Confluence pages or attachments (docx/xlsx/pdf). Provides Confluence REST API integration for documentation search.
---

# Confluence Documentation Search

Search and retrieve documentation from Confluence pages and their attachments (docx/xlsx/pdf) via REST API. Supports searching across configured spaces with predefined purpose mappings. Works on Linux, macOS, and Windows — requires only Python 3 (no external dependencies).

## Prerequisites

Two environment variables must be set:

| Variable | Description |
|----------|-------------|
| `CONFLUENCE_PAT` | Personal Access Token |
| `CONFLUENCE_URL` | Base URL (e.g., `https://confluence.company.com` or `https://company.atlassian.net/wiki`) |
| `CONFLUENCE_USER` | *(Optional, Cloud only)* Email for basic auth |

**Server/Data Center**: Uses `Bearer` token auth. Set `CONFLUENCE_PAT` to your PAT.
**Cloud**: Uses basic auth. Set `CONFLUENCE_USER` to your email and `CONFLUENCE_PAT` to your API token.

Verify with:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/confluence-api.py spaces
```

## Helper Script

All operations use `${CLAUDE_PLUGIN_ROOT}/scripts/confluence-api.py` (cross-platform Python). Uses only Python standard library modules — no `curl`, `jq`, or `base64` CLI required.

| Command | Usage | Description |
|---------|-------|-------------|
| `search` | `search <cql> [limit] [start]` | Raw CQL search |
| `search-compact` | `search-compact <cql> [limit]` | Compact result format |
| `search-space` | `search-space <query> <space> [limit]` | Search pages in a space |
| `search-attachments` | `search-attachments <query> [space] [limit]` | Search within attachments |
| `get-page` | `get-page <id> [expand]` | Get full page content |
| `get-page-text` | `get-page-text <id>` | Get page as plain text |
| `attachments` | `attachments <page-id> [limit]` | List page attachments |
| `download` | `download <url> <output>` | Download attachment file |
| `spaces` | `spaces [limit]` | List available spaces |
| `space-info` | `space-info <key>` | Get space details |

## Space Configuration

Consult `references/spaces.md` for the configured space-to-purpose mapping. When searching for domain-specific documentation, target the appropriate space to improve relevance.

**Default mapping** (customize in `references/spaces.md`):

| Space Key | Purpose | Search When |
|-----------|---------|-------------|
| `ENTARCH` | Enterprise Architecture | Architecture decisions, system design, diagrams |
| `TECHSTD` | Technology Standards | Coding standards, tech stack, approved tools |
| `SECPOL` | Security Policies | Security requirements, compliance, access control |
| `DEVOPS` | DevOps & Infrastructure | CI/CD, deployment, infrastructure, monitoring |
| `APIREF` | API Documentation | API specs, integration guides, contracts |
| `ONBOARD` | Onboarding & Guides | How-to guides, onboarding, runbooks |

To search across ALL spaces, omit the space filter from the CQL query.

## Search Workflows

### Search Pages by Topic

```bash
SCRIPT="${CLAUDE_PLUGIN_ROOT}/scripts/confluence-api.py"

# Search in a specific space
python3 "$SCRIPT" search-space "microservices architecture" "ENTARCH"

# Search across all spaces
python3 "$SCRIPT" search-compact 'type = page AND (text ~ "microservices" OR title ~ "microservices") ORDER BY lastModified DESC'
```

### Search Attachments

Confluence indexes content of common file types. Search within attachments:

```bash
# Search attachments in a specific space
python3 "$SCRIPT" search-attachments "data model" "ENTARCH"

# Search all attachments
python3 "$SCRIPT" search-attachments "API specification"
```

### Read Page Content

After finding a relevant page, fetch its content:

```bash
# Get full HTML content
python3 "$SCRIPT" get-page 12345

# Get as plain text (stripped HTML)
python3 "$SCRIPT" get-page-text 12345
```

### Download and Read Attachments

For deeper analysis of docx/xlsx/pdf attachments:

```bash
# List attachments on a page
python3 "$SCRIPT" attachments 12345

# Download a specific attachment
python3 "$SCRIPT" download "<download-url>" "confluence-doc.pdf"
```

Then use the Read tool for the downloaded file:
- **PDF**: Read directly (Claude supports PDF natively)
- **DOCX**: Convert with `pandoc -f docx -t plain file.docx` or use python-docx
- **XLSX**: Use `python3 -c "import openpyxl; ..."` or `ssconvert` to extract data

### Combined Search Strategy

For thorough documentation lookup:

1. **Identify target space** from the space mapping based on the topic
2. **Search pages first**: `search-space "<query>" "<space>"`
3. **Search attachments**: `search-attachments "<query>" "<space>"`
4. **Read top results**: Fetch page text for the most relevant hits
5. **Check attachments** on relevant pages: `attachments <page-id>`, download and read if needed
6. **Broaden search** if results are insufficient — search across all spaces or use alternate terms

Present results with: Title, Space, URL, Last Updated, and a brief excerpt.

## CQL Quick Reference

Confluence Query Language (CQL) is used for all searches.

| Pattern | CQL |
|---------|-----|
| Pages with text | `type = page AND text ~ "search term"` |
| Pages by title | `type = page AND title ~ "search term"` |
| In specific space | `space.key = "ENTARCH" AND text ~ "term"` |
| Attachments | `type = attachment AND text ~ "term"` |
| By label | `label = "architecture"` |
| Recent changes | `lastModified >= now("-7d")` |
| By contributor | `contributor = "user@company.com"` |
| Combined | `type = page AND space.key = "ENTARCH" AND text ~ "term" ORDER BY lastModified DESC` |

**Operators**: `=`, `!=`, `~` (contains), `!~` (not contains), `IN`, `NOT IN`, `>=`, `<=`
**Wildcards**: `*` in text searches
**Ordering**: `ORDER BY title ASC`, `ORDER BY lastModified DESC`, `ORDER BY created DESC`

For complete CQL reference, consult `references/api-reference.md`.

## Additional Resources

### Reference Files

- **`references/spaces.md`** — Configurable space-to-purpose mapping template (edit to match your organization)
- **`references/api-reference.md`** — Complete Confluence REST API reference, CQL syntax, field types, pagination

### Helper Script

- **`${CLAUDE_PLUGIN_ROOT}/scripts/confluence-api.py`** — Cross-platform Python helper wrapping all Confluence REST API operations (works on Linux, macOS, and Windows)
