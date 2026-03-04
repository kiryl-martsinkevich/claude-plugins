---
name: search
description: Search Azure DevOps work items using natural language or WIQL query
allowed-tools:
  - Bash
  - Read
argument-hint: "<query, e.g. 'my active stories' or WIQL>"
---

# Search ADO Work Items

Translate the user's query into a WIQL query and execute it against Azure DevOps.

## Steps

1. **Parse the user's intent** from the provided arguments. If the query is already WIQL, use it directly. Otherwise, translate natural language into WIQL using patterns from the ado-workitems skill.

2. **Common translations:**
   - "my items" / "assigned to me" → `[System.AssignedTo] = @me`
   - "active stories" → `[System.WorkItemType] = 'User Story' AND [System.State] = 'Active'`
   - "sprint backlog" → `[System.IterationPath] = @currentIteration`
   - "bugs" → `[System.WorkItemType] = 'Bug'`
   - "recently changed" → `[System.ChangedDate] >= @today-7`
   - A number like "12345" → direct work item lookup via `get`

3. **Execute the WIQL query:**
   ```bash
   RESULT=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.py" query "<WIQL>")
   ```

4. **Extract work item IDs** from the query result:
   ```bash
   IDS=$(echo "$RESULT" | python3 -c "import sys,json; data=json.load(sys.stdin); print(','.join(str(w['id']) for w in data.get('workItems',[])))")
   ```

5. **Check for empty results** — if `$IDS` is empty, inform the user no matching work items were found and suggest broadening the query. Do not call `batch-get` with an empty string.

6. **Fetch work item details** if IDs were returned:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ado-api.py" batch-get "$IDS"
   ```

7. **Display results** in a markdown table with columns: ID, Type, Title, State, Assigned To, Story Points (or other relevant fields).

## Notes

- Always include `ORDER BY` in WIQL for predictable results
- Limit to top 50 results by default unless the user asks for more
- For direct ID lookups, use `get` instead of `query`
- The Python script outputs formatted JSON — pipe through `python3 -m json.tool` or `jq` for additional filtering
