---
name: ADO Work Items
description: This skill should be used when the user asks to "create a work item", "update a work item", "search work items", "query ADO", "split a feature into stories", "fetch BRD", "Azure DevOps boards", "user stories", "backlog items", mentions work item IDs like "#12345", or discusses Agile planning with Azure DevOps. Provides ADO REST API integration for work item management.
---

# Azure DevOps Work Item Management

Manage Azure DevOps work items through the REST API using a cross-platform Python helper script. Supports the Agile process template hierarchy: Epic > Feature > User Story > Task/Bug. Works on Linux, macOS, and Windows — requires only Python 3 (no external dependencies).

## Prerequisites

Three environment variables must be set:

| Variable | Description |
|----------|-------------|
| `ADO_PAT` | Personal Access Token with Work Items read/write scope |
| `ADO_ORG` | Azure DevOps organization name |
| `ADO_PROJECT` | Project name |

Verify configuration by running:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.py help
```

## Helper Script

All API operations use `${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.py` (cross-platform Python). The script handles authentication, URL construction, error handling, and JSON formatting. It uses only Python standard library modules — no `curl`, `jq`, or `base64` required.

### Available Commands

| Command | Usage | Description |
|---------|-------|-------------|
| `get` | `get <id> [expand]` | Fetch work item by ID |
| `create` | `create <type> <json-patch>` | Create work item |
| `update` | `update <id> <json-patch>` | Update work item fields |
| `query` | `query <wiql>` | Execute WIQL query |
| `batch-get` | `batch-get <ids> [fields]` | Fetch multiple work items |
| `attachments` | `attachments <id>` | List file attachments |
| `download` | `download <url> <output>` | Download attachment file |
| `add-parent` | `add-parent <child> <parent>` | Set parent-child link |
| `children` | `children <id>` | Get child work items |

### Usage Pattern

```bash
SCRIPT="${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.py"

# Get a work item
python3 "$SCRIPT" get 12345

# Create a User Story
python3 "$SCRIPT" create "User Story" '[
  {"op":"add","path":"/fields/System.Title","value":"As a user, I want to..."},
  {"op":"add","path":"/fields/System.Description","value":"<p>Description here</p>"}
]'

# Search with WIQL
python3 "$SCRIPT" query "SELECT [System.Id],[System.Title] FROM WorkItems WHERE [System.WorkItemType]='User Story' AND [System.State]='Active' ORDER BY [System.CreatedDate] DESC"
```

## Work Item Operations

### Creating Work Items

Construct a JSON Patch document with field operations:

```bash
python3 "$SCRIPT" create "User Story" '[
  {"op":"add","path":"/fields/System.Title","value":"Story title"},
  {"op":"add","path":"/fields/System.Description","value":"<p>Description</p>"},
  {"op":"add","path":"/fields/Microsoft.VSTS.Common.AcceptanceCriteria","value":"<p>Criteria</p>"},
  {"op":"add","path":"/fields/Microsoft.VSTS.Scheduling.StoryPoints","value":5},
  {"op":"add","path":"/fields/Microsoft.VSTS.Common.Priority","value":2},
  {"op":"add","path":"/fields/System.AssignedTo","value":"user@example.com"},
  {"op":"add","path":"/fields/System.AreaPath","value":"Project\\Team"},
  {"op":"add","path":"/fields/System.IterationPath","value":"Project\\Sprint 1"},
  {"op":"add","path":"/fields/System.Tags","value":"tag1; tag2"}
]'
```

### Updating Work Items

Use the same JSON Patch format with `update`:

```bash
python3 "$SCRIPT" update 12345 '[
  {"op":"replace","path":"/fields/System.State","value":"Active"},
  {"op":"replace","path":"/fields/Microsoft.VSTS.Scheduling.StoryPoints","value":8}
]'
```

### Searching Work Items

Translate natural language queries into WIQL. Execute the query, then batch-fetch details for returned IDs:

```bash
# Step 1: Query returns IDs
RESULT=$(python3 "$SCRIPT" query "SELECT [System.Id] FROM WorkItems WHERE [System.AssignedTo]=@me AND [System.State]<>'Closed' ORDER BY [System.ChangedDate] DESC")

# Step 2: Extract IDs and fetch details (skip batch-get if no results)
IDS=$(echo "$RESULT" | python3 -c "import sys,json; data=json.load(sys.stdin); print(','.join(str(w['id']) for w in data.get('workItems',[])))")
[ -n "$IDS" ] && python3 "$SCRIPT" batch-get "$IDS"
```

Display results in a markdown table for readability.

### Linking Work Items

To set a parent-child relationship (e.g., Story under Feature):

```bash
python3 "$SCRIPT" add-parent <story-id> <feature-id>
```

## Feature Splitting Workflow

To split a Feature into User Stories:

1. **Fetch the feature**: `python3 "$SCRIPT" get <feature-id>` — extract title, description, acceptance criteria
2. **Check for BRD attachments**: `python3 "$SCRIPT" attachments <feature-id>` — look for .docx/.pdf files
3. **If BRD exists**: Download and read it (see BRD Extraction below)
4. **Analyze the feature**: Based on description and BRD content, decompose into logical user stories
5. **Propose stories**: Present a numbered table with Title, Description, Acceptance Criteria, Story Points estimate
6. **Get approval**: Ask the user to confirm, modify, or reject proposed stories
7. **Create approved stories**: Create each story via API with parent link to the feature

Each proposed story should follow the "As a [role], I want [goal], so that [benefit]" format and include specific acceptance criteria.

## BRD Extraction Workflow

To extract BRD content from work item attachments:

1. **List attachments**: `python3 "$SCRIPT" attachments <work-item-id>`
2. **Identify BRD files**: Filter for `.docx` and `.pdf` extensions
3. **Download to temp**: `python3 "$SCRIPT" download <attachment-url> brd-<id>.<ext>` (use the system temp directory or current directory)
4. **Read content**: Use the Read tool to open the downloaded file — Claude natively supports PDF reading; for `.docx`, convert first with `pandoc` if available, or use `python3 -c "import docx; ..."` with python-docx
5. **Summarize**: Present key sections — scope, requirements, acceptance criteria, assumptions, constraints

For `.docx` extraction when pandoc is not available:

```bash
python3 -c "
from docx import Document
doc = Document('brd-file.docx')
for p in doc.paragraphs:
    if p.text.strip():
        print(p.text)
"
```

## Common WIQL Patterns

| Query | WIQL |
|-------|------|
| My active items | `WHERE [System.AssignedTo]=@me AND [System.State]<>'Closed'` |
| Sprint backlog | `WHERE [System.IterationPath]=@currentIteration AND [System.WorkItemType]='User Story'` |
| Features without stories | `WHERE [System.WorkItemType]='Feature' AND [System.State]='Active'` (then check children) |
| Recently updated | `WHERE [System.ChangedDate]>=@today-7 ORDER BY [System.ChangedDate] DESC` |

For full WIQL syntax, consult `references/wiql.md`.

## Additional Resources

### Reference Files

- **`references/rest-api.md`** — Complete field name mappings, work item types, relation types, API endpoints
- **`references/wiql.md`** — Full WIQL syntax reference with operators, macros, and advanced query examples

### Helper Script

- **`${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.py`** — Cross-platform Python helper wrapping all ADO REST API operations with auth and error handling (works on Linux, macOS, and Windows)
