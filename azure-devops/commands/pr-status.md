---
name: pr-status
description: Check the status of an Azure DevOps pull request
allowed-tools:
  - Bash
  - Read
argument-hint: "[pr-id]"
---

Check the status of an Azure DevOps pull request using the ADO REST API.

## Prerequisites

Verify `ADO_PAT` is set. If not, inform the user.

## Steps

1. **Extract ADO context from git remote** (org, project, repo).

2. **Determine the PR ID:**
   - Use the PR ID from arguments if provided
   - Otherwise, list active PRs for the current branch:
     ```bash
     SOURCE_BRANCH=$(git rev-parse --abbrev-ref HEAD)
     ```
     Search for PRs with `searchCriteria.sourceRefName=refs/heads/$SOURCE_BRANCH`

3. **Fetch PR details:**
```bash
AUTH=$(echo -n ":$ADO_PAT" | base64)
BASE="https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis"

curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID?api-version=7.1"
```

4. **Display a summary** including:
   - PR title and ID
   - Status (active/completed/abandoned)
   - Source and target branches
   - Merge status (succeeded/conflicts/etc.)
   - Reviewers and their votes (10=Approved, 5=Approved with suggestions, 0=No vote, -5=Waiting for author, -10=Rejected)
   - Created date and author
   - Link to PR in browser

5. **Check for linked builds:**
```bash
# Get the latest build for the source branch
curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/build/builds?branchName=refs/heads/$SOURCE_BRANCH&\$top=1&queryOrder=startTimeDescending&api-version=7.1"
```

Show the build status if a linked build exists.
