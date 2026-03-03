# Confluence REST API Reference

## Authentication

### Server / Data Center
```
Authorization: Bearer <PAT>
```
PAT created at: `{base-url}/plugins/personalaccesstokens/usertokens.action`

### Cloud
```
Authorization: Basic base64(<email>:<api-token>)
```
API token created at: https://id.atlassian.com/manage-profile/security/api-tokens

## Base URLs

| Deployment | Base URL | API Root |
|------------|----------|----------|
| Server/DC | `https://confluence.company.com` | `{base}/rest/api` |
| Cloud | `https://company.atlassian.net/wiki` | `{base}/rest/api` |

## Endpoints

### Content Search

```
GET /rest/api/content/search?cql=<CQL>&limit=25&start=0&expand=<fields>
```

**Parameters:**
- `cql` — Confluence Query Language expression (URL-encoded)
- `limit` — Max results per page (default 25, max 100)
- `start` — Pagination offset
- `expand` — Comma-separated fields: `body.storage`, `body.view`, `space`, `version`, `metadata.labels`, `children.attachment`

**Response:**
```json
{
  "results": [
    {
      "id": "12345",
      "type": "page",
      "title": "Page Title",
      "space": {"key": "ENTARCH", "name": "Enterprise Architecture"},
      "version": {"number": 5, "when": "2024-01-15T10:30:00.000Z", "by": {"displayName": "Author"}},
      "body": {"storage": {"value": "<p>HTML content</p>"}},
      "_links": {"base": "https://confluence.company.com", "webui": "/display/ENTARCH/Page+Title"}
    }
  ],
  "start": 0,
  "limit": 25,
  "size": 10,
  "_links": {"next": "/rest/api/content/search?cql=...&start=25&limit=25"}
}
```

### Get Content

```
GET /rest/api/content/{id}?expand=body.storage,version,space,metadata.labels,children.attachment
```

### Get Attachments

```
GET /rest/api/content/{id}/child/attachment?limit=50&expand=version,metadata.mediaType
```

**Response:**
```json
{
  "results": [
    {
      "id": "att67890",
      "title": "architecture-overview.pdf",
      "metadata": {"mediaType": "application/pdf"},
      "extensions": {"fileSize": 245760, "mediaType": "application/pdf"},
      "version": {"when": "2024-01-10T08:00:00.000Z"},
      "_links": {
        "base": "https://confluence.company.com",
        "download": "/download/attachments/12345/architecture-overview.pdf?api=v2"
      }
    }
  ]
}
```

### Download Attachment

```
GET {base-url}/download/attachments/{pageId}/{filename}?api=v2
```

Or use the full download URL from the attachment's `_links.download` field.

### List Spaces

```
GET /rest/api/space?limit=100&expand=description.plain
```

### Get Space

```
GET /rest/api/space/{spaceKey}?expand=description.plain,homepage
```

## CQL (Confluence Query Language)

### Field Reference

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `type` | keyword | Content type | `type = page`, `type = attachment`, `type = blogpost` |
| `space` | keyword | Space name | `space = "Enterprise Architecture"` |
| `space.key` | keyword | Space key | `space.key = "ENTARCH"` |
| `title` | text | Page/attachment title | `title ~ "architecture"` |
| `text` | text | Full content text | `text ~ "microservices"` |
| `label` | keyword | Content labels | `label = "architecture"` |
| `contributor` | keyword | Content contributor | `contributor = "user@company.com"` |
| `creator` | keyword | Content creator | `creator = "user@company.com"` |
| `created` | date | Creation date | `created >= "2024-01-01"` |
| `lastModified` | date | Last modification | `lastModified >= now("-30d")` |
| `ancestor` | keyword | Page ancestor ID | `ancestor = 12345` |
| `parent` | keyword | Direct parent ID | `parent = 12345` |
| `id` | keyword | Content ID | `id = 12345` |
| `mention` | keyword | Mentioned user | `mention = "user@company.com"` |

### Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Exact match | `space.key = "ENTARCH"` |
| `!=` | Not equal | `space.key != "ARCHIVE"` |
| `~` | Contains (text search) | `text ~ "microservices"` |
| `!~` | Does not contain | `title !~ "draft"` |
| `>`, `>=`, `<`, `<=` | Comparison | `created >= "2024-01-01"` |
| `IN` | In list | `space.key IN ("ENTARCH", "TECHSTD")` |
| `NOT IN` | Not in list | `type NOT IN ("comment", "blogpost")` |
| `AND` | Logical AND | `type = page AND space.key = "ENTARCH"` |
| `OR` | Logical OR | `label = "architecture" OR label = "design"` |
| `NOT` | Logical NOT | `NOT label = "draft"` |

### Date Functions

| Function | Description | Example |
|----------|-------------|---------|
| `now()` | Current time | `lastModified >= now()` |
| `now("-7d")` | 7 days ago | `lastModified >= now("-7d")` |
| `now("-1M")` | 1 month ago | `created >= now("-1M")` |
| `now("-1y")` | 1 year ago | `lastModified >= now("-1y")` |
| `startOfDay()` | Start of today | `created >= startOfDay()` |
| `startOfWeek()` | Start of week | `lastModified >= startOfWeek()` |
| `startOfMonth()` | Start of month | `created >= startOfMonth()` |
| `startOfYear()` | Start of year | `lastModified >= startOfYear()` |
| `endOfDay()` | End of today | `created <= endOfDay()` |

### ORDER BY

```
ORDER BY title ASC
ORDER BY lastModified DESC
ORDER BY created DESC
ORDER BY relevance DESC     (default for text searches)
```

### Common CQL Patterns

**Pages containing text in a space:**
```
type = page AND space.key = "ENTARCH" AND text ~ "microservices" ORDER BY lastModified DESC
```

**Attachments with specific content:**
```
type = attachment AND text ~ "data model" AND space.key = "ENTARCH"
```

**Pages with specific label:**
```
type = page AND label = "architecture" ORDER BY lastModified DESC
```

**Recently modified pages:**
```
type = page AND lastModified >= now("-7d") ORDER BY lastModified DESC
```

**Pages in multiple spaces:**
```
type = page AND space.key IN ("ENTARCH", "TECHSTD") AND text ~ "microservices"
```

**Title search (faster than full text):**
```
type = page AND title ~ "Architecture Decision Record"
```

**Attachments by file type (by name pattern):**
```
type = attachment AND title ~ "*.pdf" AND space.key = "ENTARCH"
```

**Pages under a specific parent:**
```
type = page AND ancestor = 12345 AND text ~ "deployment"
```

**Pages by contributor:**
```
type = page AND contributor = "architect@company.com" AND lastModified >= now("-30d")
```

## Pagination

Results are paginated. Check the response for:
- `size` — Number of results in this page
- `start` — Current offset
- `limit` — Max per page
- `_links.next` — URL for next page (absent when no more results)

To fetch all results:
```bash
start=0
while true; do
  result=$(confluence_request GET "...&start=${start}&limit=100")
  # process results
  next=$(echo "$result" | jq -r '._links.next // empty')
  [[ -z "$next" ]] && break
  start=$((start + 100))
done
```

## Content Types

| Type | Description |
|------|-------------|
| `page` | Wiki page |
| `blogpost` | Blog post |
| `attachment` | File attachment |
| `comment` | Page comment |

## Media Types for Attachments

| Extension | Media Type |
|-----------|-----------|
| `.pdf` | `application/pdf` |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| `.pptx` | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |
| `.doc` | `application/msword` |
| `.xls` | `application/vnd.ms-excel` |
| `.png` | `image/png` |
| `.jpg` | `image/jpeg` |

## Rate Limits

- Confluence Cloud: Rate limits apply per user (typically ~100 requests/minute)
- Server/DC: Configurable by admin, typically higher limits
- Use pagination with reasonable `limit` values (25-100)
- Add small delays between bulk operations

## Error Codes

| HTTP Code | Meaning |
|-----------|---------|
| 400 | Invalid CQL syntax or bad request |
| 401 | Authentication failed (expired/invalid PAT) |
| 403 | Forbidden (insufficient permissions on space/page) |
| 404 | Content or space not found |
| 429 | Rate limited (Cloud) |
