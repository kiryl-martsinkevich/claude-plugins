#!/usr/bin/env python3
"""Confluence REST API helper — cross-platform (Linux, macOS, Windows).

Required env vars: CONFLUENCE_PAT, CONFLUENCE_URL
Optional: CONFLUENCE_USER (for Cloud basic auth — email:token)
"""

import base64
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


def check_env():
    missing = [v for v in ("CONFLUENCE_PAT", "CONFLUENCE_URL") if not os.environ.get(v)]
    if missing:
        print(f"ERROR: Missing required environment variables: {' '.join(missing)}", file=sys.stderr)
        print("Set them: export CONFLUENCE_PAT=<token> CONFLUENCE_URL=<base-url>", file=sys.stderr)
        print("  Server/DC: CONFLUENCE_URL=https://confluence.company.com", file=sys.stderr)
        print("  Cloud:     CONFLUENCE_URL=https://company.atlassian.net/wiki CONFLUENCE_USER=user@company.com", file=sys.stderr)
        sys.exit(1)


def get_base_url():
    return os.environ["CONFLUENCE_URL"].rstrip("/") + "/rest/api"


def auth_header():
    user = os.environ.get("CONFLUENCE_USER", "")
    pat = os.environ["CONFLUENCE_PAT"]
    if user:
        token = base64.b64encode(f"{user}:{pat}".encode()).decode()
        return f"Basic {token}"
    else:
        return f"Bearer {pat}"


def confluence_request(method, url, data=None):
    headers = {
        "Authorization": auth_header(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = None
    if data is not None:
        body = data.encode("utf-8") if isinstance(data, str) else data

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            response_body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        response_body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {e.code}", file=sys.stderr)
        try:
            print(json.dumps(json.loads(response_body), indent=2), file=sys.stderr)
        except (json.JSONDecodeError, ValueError):
            print(response_body, file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Request failed: {e.reason}", file=sys.stderr)
        sys.exit(1)

    return response_body


def cmd_search(args):
    cql = args[0]
    limit = args[1] if len(args) > 1 else "25"
    start = args[2] if len(args) > 2 else "0"
    encoded_cql = urllib.parse.quote(cql)
    result = confluence_request(
        "GET",
        f"{get_base_url()}/content/search?cql={encoded_cql}&limit={limit}&start={start}"
        "&expand=space,version,body.view,metadata.labels",
    )
    print(result)


def cmd_search_compact(args):
    cql = args[0]
    limit = args[1] if len(args) > 1 else "25"
    result = json.loads(cmd_search_raw(cql, limit, "0"))
    compact = [
        {
            "id": r.get("id"),
            "type": r.get("type"),
            "title": r.get("title"),
            "space": (r.get("space", {}) or {}).get("key", "N/A"),
            "url": (r.get("_links", {}).get("base", "") + r.get("_links", {}).get("webui", "")),
            "lastUpdated": (r.get("version", {}) or {}).get("when", "N/A"),
            "lastAuthor": ((r.get("version", {}) or {}).get("by", {}) or {}).get("displayName", "N/A"),
        }
        for r in result.get("results", [])
    ]
    print(json.dumps(compact, indent=2))


def cmd_search_raw(cql, limit, start):
    encoded_cql = urllib.parse.quote(cql)
    return confluence_request(
        "GET",
        f"{get_base_url()}/content/search?cql={encoded_cql}&limit={limit}&start={start}"
        "&expand=space,version,body.view,metadata.labels",
    )


def cmd_get_page(args):
    page_id = args[0]
    expand = args[1] if len(args) > 1 else "body.storage,version,space,metadata.labels,children.attachment"
    result = confluence_request("GET", f"{get_base_url()}/content/{page_id}?expand={expand}")
    print(result)


def cmd_get_page_text(args):
    page_id = args[0]
    result = confluence_request("GET", f"{get_base_url()}/content/{page_id}?expand=body.storage,space")
    data = json.loads(result)
    html_content = data.get("body", {}).get("storage", {}).get("value", "")
    # Strip HTML tags and convert to plain text
    text = re.sub(r"<br\s*/?>", "\n", html_content)
    text = re.sub(r"</?(p|div|h[1-6]|li|tr)[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            print(stripped)


def cmd_attachments(args):
    page_id = args[0]
    limit = args[1] if len(args) > 1 else "50"
    result = confluence_request(
        "GET",
        f"{get_base_url()}/content/{page_id}/child/attachment?limit={limit}&expand=version,metadata.mediaType",
    )
    data = json.loads(result)
    attachments = [
        {
            "id": r.get("id"),
            "title": r.get("title"),
            "mediaType": (
                (r.get("metadata", {}) or {}).get("mediaType")
                or (r.get("extensions", {}) or {}).get("mediaType")
                or "unknown"
            ),
            "size": (r.get("extensions", {}) or {}).get("fileSize", 0),
            "downloadUrl": (r.get("_links", {}).get("base", "") + r.get("_links", {}).get("download", "")),
            "lastUpdated": (r.get("version", {}) or {}).get("when", "N/A"),
        }
        for r in data.get("results", [])
    ]
    print(json.dumps(attachments, indent=2))


def cmd_download(args):
    url = args[0]
    output = args[1]
    # Handle relative URLs
    if url.startswith("/"):
        url = os.environ["CONFLUENCE_URL"].rstrip("/") + url
    headers = {"Authorization": auth_header()}
    req = urllib.request.Request(url, headers=headers)
    # Follow redirects
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
    try:
        with opener.open(req) as resp:
            with open(output, "wb") as f:
                f.write(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Download failed: {e.reason}", file=sys.stderr)
        sys.exit(1)
    print(output)


def cmd_search_attachments(args):
    query = args[0]
    space = args[1] if len(args) > 1 and args[1] else ""
    limit = args[2] if len(args) > 2 else "25"
    if space:
        cql = f'type = attachment AND space.key = "{space}" AND text ~ "{query}"'
    else:
        cql = f'type = attachment AND text ~ "{query}"'
    # Reuse search-compact logic
    result = json.loads(cmd_search_raw(cql, limit, "0"))
    compact = [
        {
            "id": r.get("id"),
            "type": r.get("type"),
            "title": r.get("title"),
            "space": (r.get("space", {}) or {}).get("key", "N/A"),
            "url": (r.get("_links", {}).get("base", "") + r.get("_links", {}).get("webui", "")),
            "lastUpdated": (r.get("version", {}) or {}).get("when", "N/A"),
            "lastAuthor": ((r.get("version", {}) or {}).get("by", {}) or {}).get("displayName", "N/A"),
        }
        for r in result.get("results", [])
    ]
    print(json.dumps(compact, indent=2))


def cmd_search_space(args):
    query = args[0]
    space = args[1]
    limit = args[2] if len(args) > 2 else "25"
    cql = f'type = page AND space.key = "{space}" AND (text ~ "{query}" OR title ~ "{query}")'
    result = json.loads(cmd_search_raw(cql, limit, "0"))
    compact = [
        {
            "id": r.get("id"),
            "type": r.get("type"),
            "title": r.get("title"),
            "space": (r.get("space", {}) or {}).get("key", "N/A"),
            "url": (r.get("_links", {}).get("base", "") + r.get("_links", {}).get("webui", "")),
            "lastUpdated": (r.get("version", {}) or {}).get("when", "N/A"),
            "lastAuthor": ((r.get("version", {}) or {}).get("by", {}) or {}).get("displayName", "N/A"),
        }
        for r in result.get("results", [])
    ]
    print(json.dumps(compact, indent=2))


def cmd_spaces(args):
    limit = args[0] if args else "100"
    result = confluence_request("GET", f"{get_base_url()}/space?limit={limit}&expand=description.plain")
    data = json.loads(result)
    spaces = [
        {
            "key": s.get("key"),
            "name": s.get("name"),
            "type": s.get("type"),
            "description": (s.get("description", {}) or {}).get("plain", {}).get("value", ""),
        }
        for s in data.get("results", [])
    ]
    print(json.dumps(spaces, indent=2))


def cmd_space_info(args):
    space_key = args[0]
    result = confluence_request("GET", f"{get_base_url()}/space/{space_key}?expand=description.plain,homepage")
    print(result)


USAGE = """\
Usage: confluence-api.py <command> [args]

Commands:
  search <cql> [limit] [start]         Search with raw CQL query
  search-compact <cql> [limit]         Search with compact JSON output
  get-page <id> [expand]               Get page content by ID
  get-page-text <id>                   Get page body as plain text
  attachments <page-id> [limit]        List attachments on a page
  download <url> <output>              Download attachment to file
  search-attachments <query> [space] [limit]  Search within attachments
  search-space <query> <space> [limit] Search pages in a specific space
  spaces [limit]                       List available spaces
  space-info <space-key>               Get space details

Required: CONFLUENCE_PAT, CONFLUENCE_URL
Optional: CONFLUENCE_USER (for Cloud basic auth)

Examples:
  CONFLUENCE_URL=https://confluence.company.com
  CONFLUENCE_URL=https://company.atlassian.net/wiki CONFLUENCE_USER=user@co.com
"""

COMMANDS = {
    "search": (cmd_search, 1),
    "search-compact": (cmd_search_compact, 1),
    "get-page": (cmd_get_page, 1),
    "get-page-text": (cmd_get_page_text, 1),
    "attachments": (cmd_attachments, 1),
    "download": (cmd_download, 2),
    "search-attachments": (cmd_search_attachments, 1),
    "search-space": (cmd_search_space, 2),
    "spaces": (cmd_spaces, 0),
    "space-info": (cmd_space_info, 1),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "--help", "-h"):
        print(USAGE)
        sys.exit(0)

    check_env()

    command = sys.argv[1]
    cmd_args = sys.argv[2:]

    if command not in COMMANDS:
        print(f"ERROR: Unknown command: {command}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        sys.exit(1)

    func, min_args = COMMANDS[command]
    if len(cmd_args) < min_args:
        print(f"ERROR: '{command}' requires at least {min_args} argument(s)", file=sys.stderr)
        sys.exit(1)

    func(cmd_args)


if __name__ == "__main__":
    main()
