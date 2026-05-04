#!/usr/bin/env python3
"""Convert Confluence storage-format HTML to markdown.

Usage: html-to-md.py <input.html> <output.md>
If input is "-", reads from stdin.
"""

import html as html_mod
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class ConfluenceToMarkdown(HTMLParser):
    """Parse Confluence storage format HTML and produce markdown."""

    def __init__(self):
        super().__init__()
        self.output = []
        self.stack = []  # Track nested elements
        self.list_depth = 0
        self.in_table = False
        self.table_rows = []
        self.current_row = []
        self.in_cell = False
        self.cell_tag = ""
        self.skip_content = False
        self.code_lang = ""
        self.in_pre = False
        self.pre_content = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self.stack.append(tag)

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self.output.append("\n" + "#" * level + " ")
        elif tag == "p":
            self.output.append("\n")
        elif tag == "br":
            self.output.append("\n")
        elif tag in ("strong", "b"):
            self.output.append("**")
        elif tag in ("em", "i"):
            self.output.append("*")
        elif tag == "code":
            if not self.in_pre:
                self.output.append("`")
        elif tag == "pre":
            self.in_pre = True
            self.pre_content = []
        elif tag == "ul":
            self.list_depth += 1
            self.output.append("\n")
        elif tag == "ol":
            self.list_depth += 1
            self.output.append("\n")
        elif tag == "li":
            indent = "  " * (self.list_depth - 1)
            self.output.append(indent + "- ")
        elif tag == "a":
            href = attrs_dict.get("href", "")
            self.output.append("[")
            self._last_href = href
        elif tag == "img":
            src = attrs_dict.get("src", "")
            alt = attrs_dict.get("alt", "image")
            self.output.append(f"![{alt}]({src})")
        elif tag == "hr":
            self.output.append("\n---\n")
        elif tag == "blockquote":
            self.output.append("\n> ")
        elif tag == "table":
            self.in_table = True
            self.table_rows = []
        elif tag == "tr":
            self.current_row = []
        elif tag in ("td", "th"):
            self.in_cell = True
            self.cell_tag = tag
            self._cell_content = []
        elif tag in ("ac:structured-macro", "ac:macro"):
            macro_name = attrs_dict.get("ac:name", "")
            self.skip_content = True
        elif tag == "ac:plain-text-body":
            self.skip_content = False
            self.output.append("\n```\n")
        elif tag == "ri:page":
            title = attrs_dict.get("ri:content-title", "")
            self.output.append(f"*{title}*")
        elif tag == "ac:link":
            self.output.append("\n> **Link:** ")
        elif tag == "ac:image":
            self.output.append("\n> **Image reference:** ")

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.output.append("\n")
        elif tag == "p":
            self.output.append("\n")
        elif tag in ("strong", "b"):
            self.output.append("**")
        elif tag in ("em", "i"):
            self.output.append("*")
        elif tag == "code":
            if not self.in_pre:
                self.output.append("`")
        elif tag == "pre":
            self.in_pre = False
            self.output.append("".join(self.pre_content))
            self.output.append("\n```\n")
        elif tag == "ul":
            self.list_depth = max(0, self.list_depth - 1)
        elif tag == "ol":
            self.list_depth = max(0, self.list_depth - 1)
        elif tag == "a":
            href = getattr(self, "_last_href", "")
            self.output.append(f"]({href})")
        elif tag == "blockquote":
            self.output.append("\n")
        elif tag == "table":
            self.in_table = False
            if self.table_rows:
                self.output.append(self._render_table())
        elif tag in ("td", "th"):
            self.in_cell = False
            self.current_row.append("".join(getattr(self, "_cell_content", [])))
        elif tag == "tr":
            if self.current_row:
                self.table_rows.append(self.current_row)
            self.current_row = []
        elif tag in ("ac:structured-macro", "ac:macro"):
            self.skip_content = False
        elif tag == "ac:plain-text-body":
            self.output.append("\n```\n")

    def handle_data(self, data):
        if self.skip_content:
            return
        if self.in_pre:
            self.pre_content.append(data)
        elif self.in_cell:
            self._cell_content.append(data.strip())
        else:
            self.output.append(data)

    def _render_table(self) -> str:
        if not self.table_rows:
            return ""
        lines = []
        max_cols = max(len(r) for r in self.table_rows)
        padded = [r + [""] * (max_cols - len(r)) for r in self.table_rows]
        # Header
        lines.append("\n| " + " | ".join(padded[0]) + " |")
        lines.append("|" + "|".join(" --- " for _ in padded[0]) + "|")
        for row in padded[1:]:
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        return "\n".join(lines)


def convert_html_to_md(html_content: str) -> str:
    """Convert Confluence HTML to markdown."""
    parser = ConfluenceToMarkdown()
    parser.feed(html_content)
    raw = "".join(parser.output)

    # Clean up: collapse multiple blank lines, fix spacing around headings
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = re.sub(r"\n(#+) ", r"\n\n\1 ", raw)
    raw = re.sub(r"(\*\*)\s+", r"\1", raw)
    raw = re.sub(r"\s+(\*\*)", r"\1", raw)
    raw = html_mod.unescape(raw)

    return raw.strip() + "\n"


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.html> [output.md]", file=sys.stderr)
        print("  If input is '-', reads from stdin", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if input_path == "-":
        content = sys.stdin.read()
    else:
        if not Path(input_path).exists():
            print(f"ERROR: File not found: {input_path}", file=sys.stderr)
            sys.exit(1)
        content = Path(input_path).read_text()

    md = convert_html_to_md(content)

    if output_path:
        Path(output_path).write_text(md)
        print(output_path)
    else:
        print(md)


if __name__ == "__main__":
    main()
