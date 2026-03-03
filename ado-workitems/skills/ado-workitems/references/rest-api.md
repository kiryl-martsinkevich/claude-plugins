# Azure DevOps REST API Reference

## Authentication

All requests use Basic auth with a Personal Access Token (PAT):

```
Authorization: Basic base64(:<PAT>)
```

PAT must have **Work Items (Read & Write)** scope.

## Base URL

```
https://dev.azure.com/{organization}/{project}/_apis
```

## API Version

Append `api-version=7.1` to all requests.

## Endpoints

### Work Items

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/wit/workitems/{id}?$expand={expand}` | Get single work item |
| GET | `/wit/workitems?ids={id1,id2}&fields={fields}` | Get multiple work items |
| POST | `/wit/workitems/${type}` | Create work item |
| PATCH | `/wit/workitems/{id}` | Update work item |
| DELETE | `/wit/workitems/{id}` | Delete work item |
| POST | `/wit/wiql` | Execute WIQL query |

**Expand options**: `all`, `relations`, `fields`, `links`, `none`

### Attachments

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/wit/attachments?fileName={name}` | Upload attachment |
| GET | `/wit/attachments/{id}` | Download attachment |

## JSON Patch Document

Create and update operations use JSON Patch format (`Content-Type: application/json-patch+json`):

```json
[
  {
    "op": "add",
    "path": "/fields/System.Title",
    "value": "Work item title"
  }
]
```

**Operations:**
- `add` — Set a field value (use for create)
- `replace` — Replace existing value (use for update)
- `remove` — Remove a field value
- `test` — Test a value before applying changes

## Work Item Types (Agile Process)

| Type | Parent | Description |
|------|--------|-------------|
| Epic | — | Large business initiative |
| Feature | Epic | Deliverable functionality |
| User Story | Feature | User-facing requirement |
| Task | User Story | Implementation work |
| Bug | User Story | Defect to fix |

## Field Reference

### System Fields

| Display Name | API Field Path | Type |
|-------------|----------------|------|
| Title | `System.Title` | string |
| Description | `System.Description` | html |
| State | `System.State` | string |
| Reason | `System.Reason` | string |
| Assigned To | `System.AssignedTo` | identity |
| Area Path | `System.AreaPath` | treePath |
| Iteration Path | `System.IterationPath` | treePath |
| Work Item Type | `System.WorkItemType` | string |
| Tags | `System.Tags` | string (semicolon-separated) |
| Created By | `System.CreatedBy` | identity |
| Created Date | `System.CreatedDate` | dateTime |
| Changed By | `System.ChangedBy` | identity |
| Changed Date | `System.ChangedDate` | dateTime |
| Board Column | `System.BoardColumn` | string |
| Board Lane | `System.BoardLane` | string |
| Comment Count | `System.CommentCount` | integer |

### Agile-Specific Fields

| Display Name | API Field Path | Type | Applies To |
|-------------|----------------|------|------------|
| Story Points | `Microsoft.VSTS.Scheduling.StoryPoints` | double | User Story |
| Priority | `Microsoft.VSTS.Common.Priority` | integer (1-4) | All |
| Severity | `Microsoft.VSTS.Common.Severity` | string | Bug |
| Value Area | `Microsoft.VSTS.Common.ValueArea` | string | Feature, Story |
| Risk | `Microsoft.VSTS.Common.Risk` | string | Feature |
| Acceptance Criteria | `Microsoft.VSTS.Common.AcceptanceCriteria` | html | User Story |
| Repro Steps | `Microsoft.VSTS.TCM.ReproSteps` | html | Bug |
| Remaining Work | `Microsoft.VSTS.Scheduling.RemainingWork` | double | Task |
| Original Estimate | `Microsoft.VSTS.Scheduling.OriginalEstimate` | double | Task |
| Completed Work | `Microsoft.VSTS.Scheduling.CompletedWork` | double | Task |
| Activity | `Microsoft.VSTS.Common.Activity` | string | Task |
| Stack Rank | `Microsoft.VSTS.Common.StackRank` | double | All |
| Target Date | `Microsoft.VSTS.Scheduling.TargetDate` | dateTime | Feature, Epic |
| Start Date | `Microsoft.VSTS.Scheduling.StartDate` | dateTime | Feature, Epic |

### States (Agile Process)

| Work Item Type | States |
|---------------|--------|
| Epic | New, Active, Resolved, Closed |
| Feature | New, Active, Resolved, Closed |
| User Story | New, Active, Resolved, Closed, Removed |
| Task | New, Active, Closed, Removed |
| Bug | New, Active, Resolved, Closed |

### Priority Values

| Value | Meaning |
|-------|---------|
| 1 | Critical |
| 2 | High |
| 3 | Medium |
| 4 | Low |

## Relation Types

### Hierarchy (Parent/Child)

```json
{
  "rel": "System.LinkTypes.Hierarchy-Reverse",
  "url": "https://dev.azure.com/{org}/{project}/_apis/wit/workitems/{parentId}"
}
```

- `System.LinkTypes.Hierarchy-Reverse` — This item is a **child of** the target
- `System.LinkTypes.Hierarchy-Forward` — This item is a **parent of** the target

### Other Link Types

| Relation | Forward | Reverse |
|----------|---------|---------|
| Related | `System.LinkTypes.Related` | `System.LinkTypes.Related` |
| Predecessor/Successor | `System.LinkTypes.Dependency-Forward` | `System.LinkTypes.Dependency-Reverse` |
| Duplicate | `System.LinkTypes.Duplicate-Forward` | `System.LinkTypes.Duplicate-Reverse` |
| Tested By | `Microsoft.VSTS.Common.TestedBy-Forward` | `Microsoft.VSTS.Common.TestedBy-Reverse` |

### Attachment Relation

Attachments appear in the `relations` array with:
```json
{
  "rel": "AttachedFile",
  "url": "https://dev.azure.com/{org}/_apis/wit/attachments/{guid}",
  "attributes": {
    "name": "filename.pdf",
    "resourceSize": 12345,
    "comment": "optional comment"
  }
}
```

## Adding Relations

To add a relation when creating or updating:

```json
[
  {
    "op": "add",
    "path": "/relations/-",
    "value": {
      "rel": "System.LinkTypes.Hierarchy-Reverse",
      "url": "https://dev.azure.com/{org}/{project}/_apis/wit/workitems/{targetId}",
      "attributes": {
        "comment": "Optional comment"
      }
    }
  }
]
```

## Comments

### Add Comment

```
POST /wit/workitems/{id}/comments?api-version=7.1-preview.4
Content-Type: application/json

{"text": "<p>Comment text</p>"}
```

### Get Comments

```
GET /wit/workitems/{id}/comments?api-version=7.1-preview.4
```

## Error Codes

| HTTP Code | Meaning |
|-----------|---------|
| 400 | Invalid request (bad field name, wrong type, missing required field) |
| 401 | Authentication failed (expired or invalid PAT) |
| 403 | Forbidden (PAT lacks required scope) |
| 404 | Work item or project not found |
| 409 | Conflict (concurrent update) |
| 429 | Rate limited |

## Pagination

WIQL queries return a maximum of 200 work items by default. Use `$top` parameter:

```
POST /wit/wiql?$top=500&api-version=7.1
```

Maximum `$top` value is 20,000 for IDs-only queries.

For batch-get, request up to 200 IDs at a time. Split larger sets into multiple requests.

## HTML Fields

Description, Acceptance Criteria, and Repro Steps are HTML fields. Wrap values in HTML tags:

```json
{"op":"add","path":"/fields/System.Description","value":"<p>Plain text paragraph</p><ul><li>List item</li></ul>"}
```
