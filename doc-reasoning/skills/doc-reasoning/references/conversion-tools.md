# Conversion Tools

Tools required for document format conversion and their installation.

## Required Tools

| Tool | Formats | Install |
|------|---------|---------|
| **pandoc** | docx, html, pdf (output) | `sudo apt install pandoc` (Linux) / `brew install pandoc` (macOS) / `choco install pandoc` (Windows) |
| **poppler-utils** | pdf (input) | `sudo apt install poppler-utils` (Linux) / `brew install poppler` (macOS) |
| **Python 3** | xlsx, pptx, html | Already available on most systems |

## Python Packages

| Package | Format | Install |
|---------|--------|---------|
| `openpyxl` | xlsx input | `pip install openpyxl` |
| `python-pptx` | pptx input | `pip install python-pptx` |

## Format-Specific Caveats

### DOCX
- **What converts well:** Headings, paragraphs, lists, tables, bold/italic formatting
- **What is lost:** Images, comments, tracked changes, embedded objects, complex page layouts
- **Tables:** Converted as GFM markdown tables. Merged cells may not render correctly
- **Recommendation:** Use pandoc for best results. Plain `python-docx` extraction is a fallback

### XLSX
- **What converts well:** Cell values, sheet names, table structure
- **What is lost:** Formulas (only computed values extracted), charts, pivot tables, conditional formatting, images
- **Large sheets:** Limited to first 2000 rows per sheet to avoid context overflow
- **Multiple sheets:** Each sheet becomes a separate markdown section with its name as heading

### PPTX
- **What converts well:** Slide titles, bullet points, text boxes, speaker notes
- **What is lost:** Images, animations, slide layouts, embedded video/audio, SmartArt
- **Tables in slides:** Text extracted, but complex table formatting is flattened
- **Speaker notes:** Preserved as blockquotes under each slide

### PDF
- **What converts well:** Plain text content with layout preservation
- **What is lost:** Images, forms, annotations, columns (may be intermixed), headers/footers (may appear mid-text)
- **Scanned PDFs:** Not supported — requires OCR which is not integrated
- **Recommendation:** Use pdftotext with `-layout` flag for best structure retention

### Confluence
- **Requires:** `confluence-search` plugin — provides `scripts/confluence-api.py` (pure Python, no external deps)
- **API script:** `confluence-api.py` handles `get-page`, `get-page-text`, `attachments`, `download`, `search-space`, etc.
- **Bidirectional conversion:** HTML storage format → markdown (ingest) and markdown → HTML (export)
- **What converts well:** Headings, paragraphs, lists, tables, bold/italic, links
- **What is lost:** Confluence macros (Jira issues, page trees, task lists), embedded attachments, page properties, comments
- **Macros:** Recognized and noted in output but content not extracted
- **Page hierarchy:** Only the page content is captured, not its position in the page tree
- **Images:** Converted to markdown image references. Actual image content must be downloaded separately
- **Attachments:** `.docx`, `.xlsx`, `.pptx`, `.pdf` attachments are automatically downloaded and converted on ingest

### HTML / Web Pages
- **What converts well:** Semantic HTML (headings, paragraphs, lists, tables, links)
- **What is lost:** JavaScript-rendered content, CSS layout, navigation, ads
- **Recommendation:** For JS-heavy pages, use a browser-based approach as fallback

## Checking Tool Availability

```python
import importlib.util, shutil
checks = {
    "pandoc": lambda: shutil.which("pandoc") is not None,
    "pdftotext": lambda: shutil.which("pdftotext") is not None,
    "openpyxl": lambda: importlib.util.find_spec("openpyxl") is not None,
    "python-pptx": lambda: importlib.util.find_spec("pptx") is not None,
}
for name, check in checks.items():
    print(f"{name}: {'OK' if check() else 'MISSING'}")
```
