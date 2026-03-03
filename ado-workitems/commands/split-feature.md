---
name: split-feature
description: Analyze an ADO Feature and split it into User Stories
allowed-tools:
  - Bash
  - Read
  - AskUserQuestion
argument-hint: "<feature-id>"
---

# Split Feature into User Stories

Analyze a Feature work item and decompose it into well-defined User Stories.

## Steps

1. **Validate input** — a feature ID must be provided. If missing, ask the user.

2. **Fetch the feature:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.sh" get <feature-id>
   ```
   Extract: Title, Description, Acceptance Criteria, State, Area Path, Iteration Path.

3. **Check for existing children:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.sh" children <feature-id>
   ```
   If stories already exist, show them and ask if the user wants to add more or start fresh.

4. **Check for BRD attachments:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.sh" attachments <feature-id>
   ```
   If .docx or .pdf attachments exist, offer to download and read them for additional context:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.sh" download <url> /tmp/brd-<feature-id>.<ext>
   ```
   Then use the Read tool to extract content from the downloaded file.

5. **Analyze and decompose** the feature into User Stories based on:
   - Feature description and acceptance criteria
   - BRD content (if extracted)
   - Each story should be independently deliverable
   - Follow the Agile hierarchy: Feature → User Stories

6. **Propose stories** in a numbered markdown table:

   | # | Title | Description | Acceptance Criteria | Story Points |
   |---|-------|-------------|-------------------|--------------|
   | 1 | As a user, I want to... | ... | ... | 3 |
   | 2 | As a user, I want to... | ... | ... | 5 |

   Include 3-8 stories typically. Each story should:
   - Follow "As a [role], I want [goal], so that [benefit]" format
   - Have specific, testable acceptance criteria
   - Be independently estimable (1-13 story points)
   - Cover a single slice of functionality

7. **Ask for approval** — present the proposed stories and ask:
   - Approve all and create
   - Modify specific stories (edit title, description, points)
   - Remove some stories
   - Add additional stories
   - Cancel

8. **Create approved stories** — for each approved story:
   ```bash
   # Create the story
   RESULT=$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.sh" create "User Story" '<json-patch>')

   # Extract new ID and link to parent feature
   NEW_ID=$(echo "$RESULT" | jq -r '.id')
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.sh" add-parent "$NEW_ID" <feature-id>
   ```

   Set the same Area Path and Iteration Path as the parent feature unless specified otherwise.

9. **Show summary** — list all created stories with IDs and URLs.

## Notes

- For large features or BRDs, propose stories in logical groups (e.g., by user role, by workflow step)
- Suggest story point estimates using Fibonacci scale: 1, 2, 3, 5, 8, 13
- Preserve the feature's Area Path and Iteration Path in child stories
- Use jq to build JSON patch documents to handle special characters in descriptions
