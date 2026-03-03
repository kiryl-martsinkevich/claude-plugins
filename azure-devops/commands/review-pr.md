---
name: review-pr
description: Review an Azure DevOps pull request — fetch changes, analyze code, post comments, and vote
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - AskUserQuestion
argument-hint: "<pr-id> [approve|reject|suggestions]"
---

Perform a code review on an Azure DevOps pull request using the ADO REST API.

## Prerequisites

Verify `ADO_PAT` is set. If not, inform the user.

## Steps

1. **Extract ADO context from git remote** (org, project, repo).

2. **Get the PR ID** from arguments. This is required — ask the user if not provided.

3. **Fetch PR details** to understand context:
```bash
AUTH=$(echo -n ":$ADO_PAT" | base64)
BASE="https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis"

curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID?api-version=7.1"
```

4. **Get the list of changed files** via iterations:
```bash
# Get iterations
iterations=$(curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID/iterations?api-version=7.1")

latest=$(echo "$iterations" | jq '.value | length')

# Get changes
curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID/iterations/$latest/changes?api-version=7.1"
```

5. **Fetch and read the changed files.** For each changed file:
   - If the source branch is checked out locally, read the local file using the Read tool
   - Otherwise, fetch the file content via the Items API:
     ```
     GET /git/repositories/{repo}/items?path={filePath}&versionDescriptor.version={sourceCommitId}&versionDescriptor.versionType=commit&api-version=7.1
     ```

6. **Analyze the changes** checking for:
   - Correctness — does the code match the PR description?
   - Security — SQL injection, XSS, credential exposure, command injection
   - Performance — N+1 queries, unnecessary allocations, missing indexes
   - Error handling — proper exception handling, edge cases
   - Code style — consistency with existing codebase conventions
   - Tests — adequate coverage for the changes

7. **Check existing comment threads** to avoid duplicate feedback:
```bash
curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID/threads?api-version=7.1"
```

8. **Post review comments** as needed:
   - Use **file-level comments** with `threadContext` for specific code issues
   - Use **general comments** for overall observations
   - Set thread status to `1` (Active) for issues, `6` (Pending) for questions

9. **Post a summary comment** with the overall assessment.

10. **Submit vote** if a vote preference was provided in arguments, or ask the user:
    - `approve` → vote `10`
    - `suggestions` → vote `5` (approved with suggestions)
    - `reject` → vote `-10`
    - `waiting` → vote `-5` (waiting for author)

```bash
# Get reviewer ID
user_info=$(curl -s \
  -H "Authorization: Basic $AUTH" \
  "https://dev.azure.com/${ADO_ORG}/_apis/connectionData?api-version=7.1")
reviewer_id=$(echo "$user_info" | jq -r '.authenticatedUser.id')

# Submit vote
curl -s -X PUT \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"vote\": $VOTE}" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID/reviewers/$reviewer_id?api-version=7.1"
```

11. **Show a summary** of the review: number of comments posted, vote submitted, and link to PR.
