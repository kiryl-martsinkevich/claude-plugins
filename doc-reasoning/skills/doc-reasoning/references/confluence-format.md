# Confluence Format Mapping

How Confluence storage format maps to markdown and back, and known limitations.

## Confluence HTML → Markdown (Ingest)

| Confluence Element | Markdown Output |
|-------------------|-----------------|
| `<h1>` - `<h6>` | `#` - `######` |
| `<p>` | Paragraph break |
| `<strong>`, `<b>` | `**bold**` |
| `<em>`, `<i>` | `*italic*` |
| `<ul>` / `<ol>` / `<li>` | Bullet/numbered lists |
| `<table>` / `<tr>` / `<td>` / `<th>` | GFM table |
| `<a href="...">` | `[text](url)` |
| `<img>` | `![alt](src)` |
| `<br>` | Newline |
| `<hr>` | `---` |
| `<blockquote>` | `> quote` |
| `<code>` | `` `code` `` |
| `<pre>` | ` ``` code block ``` ` |
| `<ri:page>` | `*page title*` |
| `<ac:structured-macro>` | Skipped (noted) |
| `<ac:link>` | `> **Link:** ` |
| `<ac:image>` | `> **Image reference:** ` |

## Known Limitations

### Ingest (Confluence → Markdown)

- **Macros are skipped:** Task lists, Jira issue macros, page trees, table of contents, children display — none of these are converted. Their presence is noted.
- **Images are references only:** The markdown includes `![alt](url)` but the actual image file is not downloaded.
- **Page metadata (version, author, labels) is in the .meta.json file**, not in the markdown.
- **Code blocks inside macros:** The `ac:plain-text-body` inside code macros is extracted, but language metadata may be lost.
- **Nested pages:** Not fetched. Only the specific page requested is ingested.
- **Comments:** Not fetched by default. Use the expand parameter to include them if needed.

### Export (Markdown → Confluence)

- **Markdown → Confluence HTML requires conversion.** Use pandoc (`pandoc -f gfm -t html`) first, then wrap in Confluence storage format.
- **Confluence storage format envelope:**
  ```xml
  <ac:structured-macro ac:name="...">
    <ac:plain-text-body><![CDATA[...]]></ac:plain-text-body>
  </ac:structured-macro>
  ```
- **Tables:** Confluence supports tables but complex markdown tables (merged cells, nested tables) will not map cleanly.
- **Task lists:** Markdown `- [ ]` and `- [x]` are converted to HTML but Confluence uses its own task list macro. Post-ingest manual adjustment may be needed.
- **Code blocks:** Use Confluence code block macro for syntax highlighting.
- **Images:** Must be uploaded as attachments first, then referenced by attachment ID.
- **Page updates:** Use `PUT /rest/api/content/{id}` with the full page object including version number (increment by 1).

## API Reference (from confluence-search plugin)

The `confluence-api.py` script in the confluence-search plugin handles:
- `get-page <id>` — fetch page content
- `get-page-text <id>` — fetch as plain text

For page updates and creation, additional API calls are needed:
- `PUT /rest/api/content/{id}` — update existing page
- `POST /rest/api/content` — create new page

### Update Page Example

```json
{
  "id": "12345",
  "type": "page",
  "title": "Page Title",
  "space": {"key": "SPACEKEY"},
  "body": {
    "storage": {
      "value": "<p>New content in Confluence storage format</p>",
      "representation": "storage"
    }
  },
  "version": {
    "number": 2,
    "message": "Updated via doc-reasoning"
  }
}
```

The current version number must be fetched first (from `get-page`), then incremented by 1 in the PUT request. Confluence rejects updates with incorrect version numbers.
