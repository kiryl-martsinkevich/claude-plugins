# WIQL (Work Item Query Language) Reference

## Syntax

WIQL uses SQL-like syntax for querying Azure DevOps work items.

```sql
SELECT [field1], [field2], ...
FROM WorkItems
WHERE [conditions]
ORDER BY [field] [ASC|DESC]
```

**Note:** Field names must be enclosed in square brackets: `[System.Title]`.

## SELECT Clause

Specify which fields to return. The query endpoint returns only work item IDs regardless of SELECT fields — use batch-get to fetch field values.

```sql
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
```

## WHERE Clause

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equal | `[System.State] = 'Active'` |
| `<>` | Not equal | `[System.State] <> 'Closed'` |
| `>` | Greater than | `[Microsoft.VSTS.Common.Priority] > 2` |
| `<` | Less than | `[Microsoft.VSTS.Scheduling.StoryPoints] < 8` |
| `>=` | Greater or equal | `[System.CreatedDate] >= '2024-01-01'` |
| `<=` | Less or equal | `[System.ChangedDate] <= @today` |

### Logical Operators

```sql
WHERE [System.State] = 'Active'
  AND [System.AssignedTo] = @me
  OR  [System.State] = 'New'
```

Use parentheses for grouping:
```sql
WHERE ([System.State] = 'Active' OR [System.State] = 'New')
  AND [System.AssignedTo] = @me
```

### String Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `CONTAINS` | Substring match | `[System.Title] CONTAINS 'login'` |
| `NOT CONTAINS` | No substring match | `[System.Title] NOT CONTAINS 'test'` |
| `CONTAINS WORDS` | Word match | `[System.Title] CONTAINS WORDS 'login auth'` |
| `IN` | Value in list | `[System.State] IN ('Active', 'New')` |
| `NOT IN` | Value not in list | `[System.State] NOT IN ('Closed', 'Removed')` |
| `UNDER` | Tree path under | `[System.AreaPath] UNDER 'Project\\Team'` |
| `NOT UNDER` | Not under tree path | `[System.IterationPath] NOT UNDER 'Project\\Old'` |

### Special Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `EVER` | Field was ever value | `[System.AssignedTo] EVER 'user@example.com'` |
| `IN GROUP` | Member of group | `[System.AssignedTo] IN GROUP '[Project]\\Team'` |
| `NOT IN GROUP` | Not member of group | `[System.AssignedTo] NOT IN GROUP '[Project]\\PMs'` |
| `IS EMPTY` | Field has no value | `[System.AssignedTo] IS EMPTY` |
| `IS NOT EMPTY` | Field has value | `[System.Tags] IS NOT EMPTY` |

## Macros

| Macro | Description |
|-------|-------------|
| `@me` | Current authenticated user |
| `@today` | Current date (midnight) |
| `@today-N` | N days before today |
| `@today+N` | N days from today |
| `@project` | Current project name |
| `@currentIteration` | Current sprint iteration |
| `@currentIteration+N` | N iterations ahead |
| `@currentIteration-N` | N iterations behind |
| `@follows` | Work items followed by current user |
| `@myRecentActivity` | Recently viewed/modified by current user |
| `@recentMentions` | Recently mentioned current user |
| `@recentProjectActivity` | Recently changed in project |
| `@teamAreas` | Area paths assigned to default team |

## ORDER BY Clause

```sql
ORDER BY [System.CreatedDate] DESC
ORDER BY [Microsoft.VSTS.Common.Priority] ASC, [System.CreatedDate] DESC
```

Default sort is ascending (ASC).

## Linked Queries (WORKITEMLINKS)

Query parent-child or other relationships:

```sql
SELECT [System.Id]
FROM WorkItemLinks
WHERE ([Source].[System.WorkItemType] = 'Feature')
  AND ([Target].[System.WorkItemType] = 'User Story')
  AND ([System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward')
MODE (MustContain)
```

**Modes:**
- `MustContain` — Source must have matching links
- `MayContain` — Source may or may not have matching links
- `DoesNotContain` — Source must NOT have matching links

## Common Query Patterns

### My Active Work Items
```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
FROM WorkItems
WHERE [System.AssignedTo] = @me
  AND [System.State] <> 'Closed'
  AND [System.State] <> 'Removed'
ORDER BY [System.ChangedDate] DESC
```

### Current Sprint Backlog
```sql
SELECT [System.Id], [System.Title], [System.State], [Microsoft.VSTS.Scheduling.StoryPoints]
FROM WorkItems
WHERE [System.IterationPath] = @currentIteration
  AND [System.WorkItemType] IN ('User Story', 'Bug')
ORDER BY [Microsoft.VSTS.Common.StackRank] ASC
```

### Active Features with Story Count
```sql
SELECT [System.Id]
FROM WorkItemLinks
WHERE ([Source].[System.WorkItemType] = 'Feature')
  AND ([Source].[System.State] = 'Active')
  AND ([Target].[System.WorkItemType] = 'User Story')
  AND ([System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward')
MODE (MayContain)
```

### Recently Changed Items
```sql
SELECT [System.Id], [System.Title], [System.ChangedDate], [System.ChangedBy]
FROM WorkItems
WHERE [System.TeamProject] = @project
  AND [System.ChangedDate] >= @today-7
ORDER BY [System.ChangedDate] DESC
```

### Unassigned Stories in Area
```sql
SELECT [System.Id], [System.Title], [Microsoft.VSTS.Common.Priority]
FROM WorkItems
WHERE [System.WorkItemType] = 'User Story'
  AND [System.State] = 'New'
  AND [System.AssignedTo] IS EMPTY
  AND [System.AreaPath] UNDER 'Project\\TeamArea'
ORDER BY [Microsoft.VSTS.Common.Priority] ASC
```

### Bugs by Priority
```sql
SELECT [System.Id], [System.Title], [Microsoft.VSTS.Common.Priority], [Microsoft.VSTS.Common.Severity]
FROM WorkItems
WHERE [System.WorkItemType] = 'Bug'
  AND [System.State] IN ('New', 'Active')
ORDER BY [Microsoft.VSTS.Common.Priority] ASC, [Microsoft.VSTS.Common.Severity] ASC
```

### Items with Specific Tag
```sql
SELECT [System.Id], [System.Title], [System.Tags]
FROM WorkItems
WHERE [System.Tags] CONTAINS 'api'
  AND [System.State] <> 'Closed'
ORDER BY [System.CreatedDate] DESC
```

### Features Without Stories (Orphaned)
```sql
SELECT [System.Id]
FROM WorkItemLinks
WHERE ([Source].[System.WorkItemType] = 'Feature')
  AND ([Source].[System.State] = 'Active')
  AND ([Target].[System.WorkItemType] = 'User Story')
  AND ([System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward')
MODE (DoesNotContain)
```

### Items Modified by User
```sql
SELECT [System.Id], [System.Title], [System.ChangedDate]
FROM WorkItems
WHERE [System.ChangedBy] = 'user@example.com'
  AND [System.ChangedDate] >= @today-30
ORDER BY [System.ChangedDate] DESC
```

## Limits and Best Practices

- Maximum 20,000 work items returned per query (IDs only)
- Batch-get supports up to 200 IDs per request
- Use `$top` parameter to limit results: `POST /wit/wiql?$top=100`
- Index fields like `System.State`, `System.WorkItemType`, `System.AssignedTo` for best performance
- Avoid `CONTAINS` on large text fields when possible — prefer `CONTAINS WORDS`
- Use `@currentIteration` instead of hardcoding sprint paths
- Tree path queries (`UNDER`) are efficient for area/iteration filtering
