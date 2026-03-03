---
name: check-build
description: Check why an Azure DevOps build/pipeline failed and show the error details
allowed-tools:
  - Bash
  - Read
argument-hint: "<build-id>"
---

Diagnose why an Azure DevOps build failed using the ADO REST API.

## Prerequisites

Verify `ADO_PAT` is set. If not, inform the user.

## Steps

1. **Extract ADO context from git remote** (org, project, repo).

2. **Determine the build ID:**
   - Use the build ID from arguments if provided
   - If not provided, find the most recent failed build for the current branch:
     ```bash
     SOURCE_BRANCH=$(git rev-parse --abbrev-ref HEAD)
     AUTH=$(echo -n ":$ADO_PAT" | base64)
     BASE="https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis"

     curl -s \
       -H "Authorization: Basic $AUTH" \
       "$BASE/build/builds?branchName=refs/heads/$SOURCE_BRANCH&resultFilter=failed&\$top=1&queryOrder=startTimeDescending&api-version=7.1"
     ```

3. **Get build details** to confirm status:
```bash
build=$(curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/build/builds/$BUILD_ID?api-version=7.1")
```

Show: build number, status, result, pipeline name, branch, start/finish times.

4. **Get the build timeline** to identify failed tasks:
```bash
timeline=$(curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/build/builds/$BUILD_ID/timeline?api-version=7.1")

# Extract failed records
echo "$timeline" | jq '[.records[] | select(.result == "failed") | {
  name: .name,
  type: .type,
  result: .result,
  logId: .log.id,
  issues: [.issues[]? | {type: .type, message: .message}],
  errorCount: .errorCount
}]'
```

5. **For each failed task, fetch its log:**
```bash
# Get the log content for the failed task
curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/build/builds/$BUILD_ID/logs/$LOG_ID?api-version=7.1"
```

6. **Analyze the log output** to determine the root cause. Look for:
   - Error messages and stack traces
   - Test failure summaries
   - Compilation errors
   - Missing dependency errors
   - Timeout messages

7. **Classify the failure:**
   - **Transient** — network errors, timeouts, agent issues, flaky tests, package restore failures
   - **Code issue** — compilation errors, test failures due to code bugs, linting errors
   - **Configuration** — missing variables, wrong settings, infrastructure issues

8. **Present the diagnosis** with:
   - Which task(s) failed
   - Root cause summary
   - Relevant error messages from the logs
   - Whether the failure appears transient or requires code changes
   - If transient, suggest using `/azure-devops:rerun-pipeline` to re-run
   - Link to the build in browser: `https://dev.azure.com/{org}/{project}/_build/results?buildId={buildId}`
