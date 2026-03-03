# Azure DevOps REST API Endpoint Reference

Complete reference for ADO REST API endpoints used in PR and build operations.

## Authentication

All endpoints require:
```
Authorization: Basic {base64(":$ADO_PAT")}
Content-Type: application/json
```

## Base URL

```
https://dev.azure.com/{organization}/{project}/_apis
```

All endpoints below are relative to this base URL. Append `?api-version=7.1` to all requests.

---

## Pull Request Endpoints

### Create Pull Request

```
POST /git/repositories/{repositoryId}/pullrequests?api-version=7.1
```

**Request Body:**
```json
{
  "sourceRefName": "refs/heads/feature-branch",
  "targetRefName": "refs/heads/main",
  "title": "Add new feature",
  "description": "Detailed description of changes.\n\nSupports markdown.",
  "reviewers": [
    { "id": "reviewer-guid" }
  ],
  "workItemRefs": [
    { "id": "12345" }
  ],
  "isDraft": false,
  "labels": [
    { "name": "bug-fix" }
  ]
}
```

**Response (201 Created):**
```json
{
  "pullRequestId": 42,
  "codeReviewId": 42,
  "status": "active",
  "createdBy": { "displayName": "User", "id": "guid", "uniqueName": "user@org.com" },
  "creationDate": "2024-01-15T10:30:00Z",
  "title": "Add new feature",
  "description": "...",
  "sourceRefName": "refs/heads/feature-branch",
  "targetRefName": "refs/heads/main",
  "mergeStatus": "succeeded",
  "url": "https://dev.azure.com/org/project/_apis/git/repositories/repo/pullRequests/42",
  "repository": { "id": "repo-guid", "name": "repo-name" }
}
```

### Get Pull Request

```
GET /git/repositories/{repositoryId}/pullrequests/{pullRequestId}?api-version=7.1
```

**Response:** Same schema as create response, with additional fields:
```json
{
  "closedDate": "2024-01-16T15:00:00Z",
  "lastMergeSourceCommit": { "commitId": "abc123" },
  "lastMergeTargetCommit": { "commitId": "def456" },
  "lastMergeCommit": { "commitId": "ghi789" },
  "reviewers": [
    {
      "id": "reviewer-guid",
      "displayName": "Reviewer Name",
      "vote": 10,
      "isRequired": true,
      "hasDeclined": false
    }
  ],
  "completionOptions": {
    "mergeStrategy": "squash",
    "deleteSourceBranch": true,
    "transitionWorkItems": true,
    "mergeCommitMessage": "Merged PR 42: Add new feature"
  }
}
```

### Update Pull Request

```
PATCH /git/repositories/{repositoryId}/pullrequests/{pullRequestId}?api-version=7.1
```

**Request Body (any combination):**
```json
{
  "title": "Updated title",
  "description": "Updated description",
  "status": "completed",
  "targetRefName": "refs/heads/develop",
  "completionOptions": {
    "mergeStrategy": "squash",
    "deleteSourceBranch": true,
    "mergeCommitMessage": "Squash merge of PR"
  },
  "autoCompleteSetBy": { "id": "user-guid" }
}
```

**Status values:** `active`, `abandoned`, `completed`
**Merge strategies:** `noFastForward`, `squash`, `rebase`, `rebaseMerge`

### List Pull Requests

```
GET /git/repositories/{repositoryId}/pullrequests?api-version=7.1
```

**Query Parameters:**
| Parameter | Description | Example |
|-----------|-------------|---------|
| `searchCriteria.status` | Filter by status | `active`, `completed`, `abandoned`, `all` |
| `searchCriteria.creatorId` | Filter by creator GUID | `guid` |
| `searchCriteria.reviewerId` | Filter by reviewer GUID | `guid` |
| `searchCriteria.sourceRefName` | Filter by source branch | `refs/heads/feature` |
| `searchCriteria.targetRefName` | Filter by target branch | `refs/heads/main` |
| `$top` | Max results | `10` |
| `$skip` | Skip results | `0` |

**Response:**
```json
{
  "value": [ /* array of PR objects */ ],
  "count": 5
}
```

---

## PR Comment/Thread Endpoints

### Create Comment Thread

```
POST /git/repositories/{repositoryId}/pullrequests/{pullRequestId}/threads?api-version=7.1
```

**General comment:**
```json
{
  "comments": [
    {
      "parentCommentId": 0,
      "content": "General comment on the PR.\n\nSupports **markdown**.",
      "commentType": 1
    }
  ],
  "status": 1
}
```

**File-level comment:**
```json
{
  "comments": [
    {
      "parentCommentId": 0,
      "content": "This line has a potential null reference issue.",
      "commentType": 1
    }
  ],
  "threadContext": {
    "filePath": "/src/Services/UserService.cs",
    "rightFileStart": { "line": 42, "offset": 1 },
    "rightFileEnd": { "line": 42, "offset": 80 }
  },
  "status": 1
}
```

**Comment types:** `0` = Unknown, `1` = Text, `2` = CodeChange, `3` = System

**Thread status values:**
| Value | Status | Description |
|-------|--------|-------------|
| 0 | Unknown | Not set |
| 1 | Active | Open for discussion |
| 2 | Fixed | Issue resolved |
| 3 | WontFix | Acknowledged, not fixing |
| 4 | Closed | Discussion closed |
| 5 | ByDesign | Intentional behavior |
| 6 | Pending | Awaiting response |

### List Comment Threads

```
GET /git/repositories/{repositoryId}/pullrequests/{pullRequestId}/threads?api-version=7.1
```

### Reply to a Thread

```
POST /git/repositories/{repositoryId}/pullrequests/{pullRequestId}/threads/{threadId}/comments?api-version=7.1
```

**Request Body:**
```json
{
  "parentCommentId": 1,
  "content": "Reply to the comment."
}
```

### Update Thread Status

```
PATCH /git/repositories/{repositoryId}/pullrequests/{pullRequestId}/threads/{threadId}?api-version=7.1
```

**Request Body:**
```json
{
  "status": 2
}
```

---

## PR Review/Vote Endpoints

### Set Vote (Approve/Reject)

```
PUT /git/repositories/{repositoryId}/pullrequests/{pullRequestId}/reviewers/{reviewerId}?api-version=7.1
```

**Request Body:**
```json
{
  "vote": 10
}
```

**Vote values:**
| Value | Meaning |
|-------|---------|
| 10 | Approved |
| 5 | Approved with suggestions |
| 0 | No vote / Reset vote |
| -5 | Waiting for author |
| -10 | Rejected |

### Get Current User ID

```
GET https://dev.azure.com/{organization}/_apis/connectionData?api-version=7.1
```

**Response (extract authenticatedUser.id):**
```json
{
  "authenticatedUser": {
    "id": "user-guid",
    "descriptor": "...",
    "providerDisplayName": "User Name"
  }
}
```

### Add Reviewer

```
PUT /git/repositories/{repositoryId}/pullrequests/{pullRequestId}/reviewers/{reviewerId}?api-version=7.1
```

**Request Body:**
```json
{
  "id": "reviewer-guid",
  "isRequired": true,
  "vote": 0
}
```

---

## PR Iteration/Diff Endpoints

### List Iterations

```
GET /git/repositories/{repositoryId}/pullrequests/{pullRequestId}/iterations?api-version=7.1
```

Each iteration represents a push to the source branch.

### Get Iteration Changes

```
GET /git/repositories/{repositoryId}/pullrequests/{pullRequestId}/iterations/{iterationId}/changes?api-version=7.1
```

**Response:**
```json
{
  "changeEntries": [
    {
      "changeTrackingId": 1,
      "changeId": 1,
      "item": { "path": "/src/file.cs" },
      "changeType": "edit"
    }
  ]
}
```

**Change types:** `add`, `edit`, `delete`, `rename`

### Get File Diff

To get the actual diff content, use the Git Items API:
```
GET /git/repositories/{repositoryId}/items?path={filePath}&versionDescriptor.version={commitId}&api-version=7.1
```

Or compare between commits:
```
GET /git/repositories/{repositoryId}/diffs/commits?baseVersion={baseCommitId}&targetVersion={targetCommitId}&api-version=7.1
```

---

## Build Endpoints

### Get Build

```
GET /build/builds/{buildId}?api-version=7.1
```

**Response:**
```json
{
  "id": 123,
  "buildNumber": "20240115.1",
  "status": "completed",
  "result": "failed",
  "definition": { "id": 5, "name": "CI Pipeline" },
  "sourceBranch": "refs/heads/feature-branch",
  "sourceVersion": "abc123",
  "requestedBy": { "displayName": "User" },
  "startTime": "2024-01-15T10:00:00Z",
  "finishTime": "2024-01-15T10:15:00Z",
  "url": "...",
  "_links": { "web": { "href": "https://dev.azure.com/org/project/_build/results?buildId=123" } }
}
```

**Build status values:** `none`, `inProgress`, `completed`, `cancelling`, `postponed`, `notStarted`
**Build result values:** `none`, `succeeded`, `partiallySucceeded`, `failed`, `canceled`

### Get Build Timeline

```
GET /build/builds/{buildId}/timeline?api-version=7.1
```

**Response (records array — each record is a task/step):**
```json
{
  "records": [
    {
      "id": "record-guid",
      "parentId": "parent-guid",
      "type": "Task",
      "name": "Run tests",
      "state": "completed",
      "result": "failed",
      "startTime": "2024-01-15T10:05:00Z",
      "finishTime": "2024-01-15T10:10:00Z",
      "log": { "id": 7, "type": "Container", "url": "..." },
      "issues": [
        {
          "type": "error",
          "message": "Process completed with exit code 1.",
          "category": "General"
        }
      ],
      "errorCount": 2,
      "warningCount": 5
    }
  ]
}
```

**Record types:** `Stage`, `Phase`, `Job`, `Task`
**Record states:** `pending`, `inProgress`, `completed`
**Record results:** `succeeded`, `succeededWithIssues`, `failed`, `canceled`, `skipped`, `abandoned`

### Get Build Logs

List all logs:
```
GET /build/builds/{buildId}/logs?api-version=7.1
```

Get specific log content:
```
GET /build/builds/{buildId}/logs/{logId}?api-version=7.1
```

Returns plain text log output.

### Queue a Build (Re-run Pipeline)

```
POST /build/builds?api-version=7.1
```

**Request Body:**
```json
{
  "definition": { "id": 5 },
  "sourceBranch": "refs/heads/feature-branch",
  "sourceVersion": "abc123",
  "reason": "manual",
  "parameters": "{\"system.debug\":\"true\"}"
}
```

**Minimal re-run (same settings):**
```json
{
  "definition": { "id": 5 },
  "sourceBranch": "refs/heads/feature-branch"
}
```

### List Build Definitions

```
GET /build/definitions?api-version=7.1
```

**Query Parameters:**
| Parameter | Description |
|-----------|-------------|
| `name` | Filter by name (exact match) |
| `$top` | Max results |
| `path` | Filter by folder path |
| `queryOrder` | `definitionNameAscending` or `definitionNameDescending` |

### List Builds

```
GET /build/builds?api-version=7.1
```

**Query Parameters:**
| Parameter | Description |
|-----------|-------------|
| `definitions` | Comma-separated definition IDs |
| `branchName` | Filter by branch (`refs/heads/main`) |
| `statusFilter` | `inProgress`, `completed`, `cancelling`, etc. |
| `resultFilter` | `succeeded`, `failed`, `canceled` |
| `$top` | Max results |
| `requestedFor` | Filter by user email |
| `buildNumber` | Filter by build number |
| `queryOrder` | `startTimeAscending` or `startTimeDescending` |

---

## Work Item Linking

### Link Work Items to PR

Include in PR create/update:
```json
{
  "workItemRefs": [
    { "id": "12345" },
    { "id": "67890" }
  ]
}
```

### Get PR Work Items

```
GET /git/repositories/{repositoryId}/pullrequests/{pullRequestId}/workitems?api-version=7.1
```

---

## Error Responses

Standard error format:
```json
{
  "$id": "1",
  "innerException": null,
  "message": "TF401019: The pull request is not found or has been deleted.",
  "typeName": "Microsoft.TeamFoundation.Git.Server.GitPullRequestNotFoundException",
  "typeKey": "GitPullRequestNotFoundException",
  "errorCode": 0,
  "eventId": 3000
}
```

Common HTTP status codes:
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (check body) |
| 401 | Unauthorized (check PAT) |
| 403 | Forbidden (check PAT scopes) |
| 404 | Resource not found |
| 409 | Conflict (e.g., merge conflicts) |
