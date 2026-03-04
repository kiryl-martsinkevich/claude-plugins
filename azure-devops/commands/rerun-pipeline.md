---
name: rerun-pipeline
description: Re-run an Azure DevOps pipeline/build, optionally for a specific build that failed
allowed-tools:
  - Bash
  - Read
  - AskUserQuestion
argument-hint: "[build-id|pipeline-name]"
---

Re-run an Azure DevOps pipeline using the ADO REST API. Useful for resolving transient build failures.

## Prerequisites

Verify `ADO_PAT` is set. If not, inform the user.

## Steps

1. **Extract ADO context from git remote** (org, project, repo).

2. **Determine what to re-run:**
   - If a **build ID** is provided, fetch that build to get the definition ID and source branch:
     ```bash
     AUTH=$(python3 -c "import base64; print(base64.b64encode((':' + '$ADO_PAT').encode()).decode())")
     BASE="https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis"

     build=$(curl -s \
       -H "Authorization: Basic $AUTH" \
       "$BASE/build/builds/$BUILD_ID?api-version=7.1")

     DEFINITION_ID=$(echo "$build" | jq -r '.definition.id')
     SOURCE_BRANCH=$(echo "$build" | jq -r '.sourceBranch')
     PIPELINE_NAME=$(echo "$build" | jq -r '.definition.name')
     ```

   - If a **pipeline name** is provided, look up the definition:
     ```bash
     defs=$(curl -s \
       -H "Authorization: Basic $AUTH" \
       "$BASE/build/definitions?name=$PIPELINE_NAME&api-version=7.1")

     DEFINITION_ID=$(echo "$defs" | jq -r '.value[0].id')
     ```
     Use the current git branch as the source branch.

   - If **neither** is provided, find the most recent build for the current branch:
     ```bash
     SOURCE_BRANCH=$(git rev-parse --abbrev-ref HEAD)
     builds=$(curl -s \
       -H "Authorization: Basic $AUTH" \
       "$BASE/build/builds?branchName=refs/heads/$SOURCE_BRANCH&\$top=1&queryOrder=startTimeDescending&api-version=7.1")

     DEFINITION_ID=$(echo "$builds" | jq -r '.value[0].definition.id')
     PIPELINE_NAME=$(echo "$builds" | jq -r '.value[0].definition.name')
     ```

3. **Confirm with the user** before queuing:
   Show the pipeline name, definition ID, and source branch. Ask for confirmation to proceed.

4. **Queue the new build:**
```bash
result=$(curl -s -X POST \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/json" \
  -d "{
    \"definition\": { \"id\": $DEFINITION_ID },
    \"sourceBranch\": \"$SOURCE_BRANCH\"
  }" \
  "$BASE/build/builds?api-version=7.1")
```

5. **Show the result:**
   - New build ID
   - Build number
   - Status (should be `notStarted` or `inProgress`)
   - Link to build: `https://dev.azure.com/{org}/{project}/_build/results?buildId={newBuildId}`
   - Inform the user they can check the status later with `/azure-devops:check-build {newBuildId}`
