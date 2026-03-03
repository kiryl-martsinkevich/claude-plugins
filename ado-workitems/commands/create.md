---
name: create
description: Create an Azure DevOps work item (Story, Bug, Task, Feature, or Epic)
allowed-tools:
  - Bash
  - AskUserQuestion
argument-hint: "[type] [title] — e.g. 'User Story Implement login page'"
---

# Create ADO Work Item

Create a new work item in Azure DevOps with the specified type and fields.

## Steps

1. **Determine work item type and title** from arguments:
   - If type is provided (e.g., "User Story", "Bug", "Task", "Feature", "Epic"), use it
   - If only a title is provided, ask the user which type to create
   - If no arguments, ask for both type and title

2. **Gather fields** — ask the user what details to include. Offer these standard fields:
   - **Title** (required) — already provided or ask
   - **Description** — free text, will be wrapped in `<p>` tags
   - **Acceptance Criteria** — for User Stories
   - **Repro Steps** — for Bugs
   - **Story Points** — numeric estimate for Stories
   - **Priority** — 1 (Critical), 2 (High), 3 (Medium), 4 (Low)
   - **Assigned To** — email address
   - **Area Path** — team area
   - **Iteration Path** — sprint
   - **Tags** — semicolon-separated
   - **Parent** — parent work item ID (to link under a Feature/Epic)

   Do not ask for every field — only prompt for what seems relevant based on the type and context. Always ask for description at minimum.

3. **Build the JSON Patch document:**
   ```json
   [
     {"op":"add","path":"/fields/System.Title","value":"<title>"},
     {"op":"add","path":"/fields/System.Description","value":"<p>description</p>"}
   ]
   ```

   Wrap Description, Acceptance Criteria, and Repro Steps in HTML tags.

4. **Create the work item:**
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.sh" create "<Type>" '<json-patch>'
   ```

5. **If a parent ID was specified**, add the parent link:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.sh" add-parent <new-id> <parent-id>
   ```

6. **Show the result** — display the created work item's ID, URL, and key fields. The URL format is:
   ```
   https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}/_workitems/edit/{id}
   ```

## Notes

- For User Stories, suggest the "As a [role], I want [goal], so that [benefit]" format for the title
- HTML fields (Description, Acceptance Criteria, Repro Steps) should use `<p>`, `<ul>`, `<li>` tags
- Properly escape JSON strings — use jq for building the JSON patch to handle special characters
- If creation fails, show the error message and suggest fixes
