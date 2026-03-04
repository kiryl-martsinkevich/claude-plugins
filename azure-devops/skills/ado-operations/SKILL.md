---
name: Azure DevOps Operations
description: This skill should be used when the user asks to "create a pull request in Azure DevOps", "check PR status in ADO", "review an ADO pull request", "approve or reject a PR", "check why a build failed", "re-run a pipeline", "check build logs", "list pull requests", "add PR comments", or mentions Azure DevOps, ADO REST API, pipelines, or repositories.
version: 0.1.0
---

# Azure DevOps Operations

Manage Azure DevOps pull requests and builds using the ADO REST API with Personal Access Token (PAT) authentication.

## Authentication

All ADO REST API calls require a Personal Access Token. Construct the authorization header using a cross-platform approach:

```bash
AUTH=$(python3 -c "import base64; print(base64.b64encode((':' + '$ADO_PAT').encode()).decode())")
curl -s -H "Authorization: Basic $AUTH" -H "Content-Type: application/json" "$URL"
```

**Required environment variable:** `ADO_PAT` — the Azure DevOps Personal Access Token.

Required PAT scopes:
- **Code (Read & Write)** — PR operations
- **Build (Read & Execute)** — build/pipeline operations

## API Base URL

```
https://dev.azure.com/{organization}/{project}/_apis
```

Determine organization and project from:
1. The git remote URL: `https://dev.azure.com/{org}/{project}/_git/{repo}` or `git@ssh.dev.azure.com:v3/{org}/{project}/{repo}`
2. User-provided values
3. Environment variables `ADO_ORG` and `ADO_PROJECT`

Append `?api-version=7.1` to all requests.

## Extracting ADO Context from Git Remotes

To auto-detect organization, project, and repository, attempt extraction from the git remote first, then fall back to asking the user. Use Python for cross-platform regex parsing:

```bash
REMOTE_URL=$(git remote get-url origin 2>/dev/null)

eval $(python3 -c "
import re, sys
url = '$REMOTE_URL'
# Parse HTTPS: https://dev.azure.com/{org}/{project}/_git/{repo}
m = re.search(r'dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)', url)
if m:
    print(f'ADO_ORG={m.group(1)} ADO_PROJECT={m.group(2)} ADO_REPO={m.group(3)}')
    sys.exit()
# Parse SSH: git@ssh.dev.azure.com:v3/{org}/{project}/{repo}
m = re.search(r'v3/([^/]+)/([^/]+)/([^/]+)', url)
if m:
    print(f'ADO_ORG={m.group(1)} ADO_PROJECT={m.group(2)} ADO_REPO={m.group(3)}')
")
```

## Core Operations

For complete request/response schemas, see `references/api-endpoints.md`.

### Pull Request Operations

- **Create PR**: `POST /git/repositories/{repo}/pullrequests` — body requires `sourceRefName`, `targetRefName`, `title`, `description`
- **Get PR**: `GET /git/repositories/{repo}/pullrequests/{prId}`
- **Update PR**: `PATCH /git/repositories/{repo}/pullrequests/{prId}` — update title, description, or set `status` to `completed`/`abandoned`
- **List PRs**: `GET /git/repositories/{repo}/pullrequests?searchCriteria.status=active`

### PR Review Operations

- **Add comment thread**: `POST /git/repositories/{repo}/pullrequests/{prId}/threads` — include `threadContext` with `filePath` and line range for inline comments
- **Vote on PR**: `PUT /git/repositories/{repo}/pullrequests/{prId}/reviewers/{reviewerId}` — vote values: `10`=Approved, `5`=Approved with suggestions, `0`=No vote, `-5`=Waiting for author, `-10`=Rejected
- **Get reviewer ID**: `GET https://dev.azure.com/{org}/_apis/connectionData` — use `authenticatedUser.id`
- **Get PR changes**: Fetch iterations then `GET /git/repositories/{repo}/pullrequests/{prId}/iterations/{id}/changes`

For detailed review workflow with inline comments, see `references/review-workflow.md`.

### Build & Pipeline Operations

- **Get build**: `GET /build/builds/{buildId}`
- **Get build timeline**: `GET /build/builds/{buildId}/timeline` — essential for diagnosing failures, filter records for `"result": "failed"`
- **Get build logs**: `GET /build/builds/{buildId}/logs/{logId}`
- **Queue a build**: `POST /build/builds` — body requires `definition.id` and `sourceBranch`
- **Find definition ID**: `GET /build/definitions?name={pipeline-name}` or check `definition.id` in any build response
- **List builds**: `GET /build/builds?definitions={definitionId}&$top=10`

## Build Failure Diagnosis Workflow

When checking why a build failed:

1. **Get the build details** to confirm status is `failed`
2. **Get the build timeline** — this is the most useful endpoint for diagnosis
3. **Filter timeline records** for `"result": "failed"` to identify which tasks failed
4. **Get the specific log** for the failed task using its `log.id`
5. **Analyze the log output** for error messages, stack traces, or test failures
6. **Determine if transient**: Network timeouts, package restore failures, agent availability issues, and flaky tests are typically transient
7. **If transient, re-run** by queuing a new build with the same definition and branch

### Identifying Transient Failures

Common transient failure patterns in build logs:
- `"The operation was canceled"` or timeout messages
- `"Unable to resolve"` package/dependency errors
- `"Connection refused"` or network errors
- `"No agent available"` or agent pool issues
- Flaky test failures (test passes on re-run)
- `"HTTP 503"` or `"Service Unavailable"` from external services

## Practical curl Patterns

Always check HTTP status codes. Use `python3` for base64 encoding (works on Linux, macOS, and Windows):

```bash
AUTH=$(python3 -c "import base64; print(base64.b64encode((':' + '$ADO_PAT').encode()).decode())")
BASE="https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis"

# GET request
curl -s -f \
  -H "Authorization: Basic $AUTH" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests?searchCriteria.status=active&api-version=7.1"

# POST request
curl -s -f \
  -X POST \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/json" \
  -d "$json_body" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests?api-version=7.1"
```

## Additional Resources

### Reference Files

For detailed API endpoint documentation and advanced patterns:
- **`references/api-endpoints.md`** — Complete ADO REST API endpoint reference with request/response schemas
- **`references/review-workflow.md`** — Detailed PR review workflow including fetching diffs, posting inline comments, and completing reviews
