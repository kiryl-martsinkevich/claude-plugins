---
name: create-pr
description: Create a new Azure DevOps pull request from the current branch
allowed-tools:
  - Bash
  - Read
  - Grep
  - AskUserQuestion
argument-hint: "[target-branch] [title]"
---

Create an Azure DevOps pull request using the ADO REST API.

## Prerequisites

Verify `ADO_PAT` is set:
```bash
test -n "$ADO_PAT" || echo "ERROR: ADO_PAT environment variable is not set"
```

If not set, inform the user they need to export `ADO_PAT` with their Azure DevOps Personal Access Token.

## Steps

1. **Extract ADO context from git remote:**

```bash
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
eval $(python3 -c "
import re, sys
url = '$REMOTE_URL'
m = re.search(r'dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)', url)
if m:
    print(f'ADO_ORG={m.group(1)} ADO_PROJECT={m.group(2)} ADO_REPO={m.group(3)}')
    sys.exit()
m = re.search(r'v3/([^/]+)/([^/]+)/([^/]+)', url)
if m:
    print(f'ADO_ORG={m.group(1)} ADO_PROJECT={m.group(2)} ADO_REPO={m.group(3)}')
")
```

2. **Get the current branch name:**
```bash
SOURCE_BRANCH=$(git rev-parse --abbrev-ref HEAD)
```

3. **Determine the target branch:**
   - Use the target branch from arguments if provided
   - Otherwise default to `main` (or `master` if `main` doesn't exist)

4. **Determine the PR title:**
   - Use the title from arguments if provided
   - Otherwise generate from the branch name or recent commit messages

5. **Generate a PR description** from the git log between the source and target branches:
```bash
git log origin/{target}..HEAD --pretty=format:"- %s" --no-merges
```

6. **Push the current branch** to the remote if needed:
```bash
git push -u origin "$SOURCE_BRANCH"
```

7. **Create the PR via REST API:**
```bash
AUTH=$(python3 -c "import base64; print(base64.b64encode((':' + '$ADO_PAT').encode()).decode())")
BASE="https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis"

curl -s -X POST \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/json" \
  -d "{
    \"sourceRefName\": \"refs/heads/$SOURCE_BRANCH\",
    \"targetRefName\": \"refs/heads/$TARGET_BRANCH\",
    \"title\": \"$TITLE\",
    \"description\": \"$DESCRIPTION\"
  }" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests?api-version=7.1"
```

8. **Show the result** including the PR ID and web URL. The web URL follows the pattern:
   `https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{prId}`
