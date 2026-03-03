# PR Review Workflow

Detailed guide for performing comprehensive pull request reviews in Azure DevOps using the REST API.

## Complete Review Workflow

### Step 1: Fetch PR Details

Get the pull request metadata to understand what is being changed:

```bash
AUTH=$(echo -n ":$ADO_PAT" | base64)
BASE="https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis"

pr=$(curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID?api-version=7.1")

echo "$pr" | jq '{
  title: .title,
  description: .description,
  sourceBranch: .sourceRefName,
  targetBranch: .targetRefName,
  status: .status,
  mergeStatus: .mergeStatus,
  createdBy: .createdBy.displayName,
  reviewers: [.reviewers[] | {name: .displayName, vote: .vote}]
}'
```

### Step 2: Get Changed Files

Fetch the iterations (pushes) and then the changes in the latest iteration:

```bash
# Get iterations
iterations=$(curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID/iterations?api-version=7.1")

# Get the latest iteration ID
latest_iteration=$(echo "$iterations" | jq '.value | length')

# Get changes in latest iteration
changes=$(curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID/iterations/$latest_iteration/changes?api-version=7.1")

# List changed files
echo "$changes" | jq '.changeEntries[] | {path: .item.path, changeType: .changeType}'
```

### Step 3: Review File Contents

For each changed file, fetch the file content at both the source and target versions to understand the diff:

```bash
# Get the source commit (PR branch)
source_commit=$(echo "$pr" | jq -r '.lastMergeSourceCommit.commitId')

# Get the target commit (base branch)
target_commit=$(echo "$pr" | jq -r '.lastMergeTargetCommit.commitId')

# Get file at source (new version)
curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/git/repositories/$ADO_REPO/items?path=/src/file.cs&versionDescriptor.version=$source_commit&versionDescriptor.versionType=commit&api-version=7.1"

# Get the commit diff
curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/git/repositories/$ADO_REPO/diffs/commits?baseVersion=$target_commit&targetVersion=$source_commit&api-version=7.1" \
  | jq '.changes[] | {path: .item.path, changeType: .changeType}'
```

### Step 4: Post Review Comments

#### General Comment

For overall observations about the PR:

```bash
curl -s -X POST \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "comments": [{
      "parentCommentId": 0,
      "content": "Overall the changes look good. A few suggestions below.",
      "commentType": 1
    }],
    "status": 1
  }' \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID/threads?api-version=7.1"
```

#### Inline/File-Level Comments

For specific code feedback:

```bash
curl -s -X POST \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "comments": [{
      "parentCommentId": 0,
      "content": "Consider using `using` statement here to ensure proper disposal.",
      "commentType": 1
    }],
    "threadContext": {
      "filePath": "/src/Services/DataService.cs",
      "rightFileStart": { "line": 25, "offset": 1 },
      "rightFileEnd": { "line": 25, "offset": 100 }
    },
    "status": 1
  }' \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID/threads?api-version=7.1"
```

### Step 5: Submit Vote

After reviewing all changes and posting comments:

```bash
# Get current user ID
user_info=$(curl -s \
  -H "Authorization: Basic $AUTH" \
  "https://dev.azure.com/${ADO_ORG}/_apis/connectionData?api-version=7.1")
reviewer_id=$(echo "$user_info" | jq -r '.authenticatedUser.id')

# Vote: 10=approve, 5=approve with suggestions, -5=waiting for author, -10=reject
curl -s -X PUT \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/json" \
  -d '{"vote": 10}' \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID/reviewers/$reviewer_id?api-version=7.1"
```

## Review with Code Reading

For a thorough review that reads the actual code changes:

1. **Get the list of changed files** from the iteration changes endpoint
2. **For each changed file**, use the Read tool to read the local file (if the branch is checked out) or fetch via the Items API
3. **Analyze the changes** considering:
   - Correctness: Does the code do what the PR description says?
   - Security: Any SQL injection, XSS, credential exposure?
   - Performance: N+1 queries, unnecessary loops, missing indexes?
   - Error handling: Are errors properly caught and handled?
   - Code style: Consistent with the rest of the codebase?
   - Tests: Are there adequate tests for the changes?
4. **Post inline comments** on specific lines with issues
5. **Post a summary comment** with overall assessment
6. **Submit vote** based on findings

## Handling Existing Threads

Check existing comment threads before posting to avoid duplicate feedback:

```bash
threads=$(curl -s \
  -H "Authorization: Basic $AUTH" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID/threads?api-version=7.1")

# Show active threads
echo "$threads" | jq '.value[] | select(.status == 1) | {
  id: .id,
  status: .status,
  file: .threadContext.filePath,
  line: .threadContext.rightFileStart.line,
  comment: .comments[0].content
}'
```

## Completing a PR After Review

If the review is approved and the PR should be completed:

```bash
# Set auto-complete (will merge when all policies pass)
user_info=$(curl -s \
  -H "Authorization: Basic $AUTH" \
  "https://dev.azure.com/${ADO_ORG}/_apis/connectionData?api-version=7.1")
user_id=$(echo "$user_info" | jq -r '.authenticatedUser.id')

curl -s -X PATCH \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/json" \
  -d "{
    \"autoCompleteSetBy\": { \"id\": \"$user_id\" },
    \"completionOptions\": {
      \"mergeStrategy\": \"squash\",
      \"deleteSourceBranch\": true,
      \"mergeCommitMessage\": \"Merged PR $PR_ID\"
    }
  }" \
  "$BASE/git/repositories/$ADO_REPO/pullrequests/$PR_ID?api-version=7.1"
```

## Review Checklist

When reviewing a PR, check for:

- [ ] PR title and description are clear
- [ ] Changes match the PR description
- [ ] No unrelated changes included
- [ ] Code follows project conventions
- [ ] Error handling is appropriate
- [ ] Security concerns addressed
- [ ] Tests cover the changes
- [ ] No hardcoded secrets or credentials
- [ ] Documentation updated if needed
- [ ] Build passes (check linked build status)
