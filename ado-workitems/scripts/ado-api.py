#!/usr/bin/env python3
"""Azure DevOps REST API helper — cross-platform (Linux, macOS, Windows).

Required env vars: ADO_PAT, ADO_ORG, ADO_PROJECT
Optional: ADO_API_VERSION (default: 7.1)
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


ADO_API_VERSION = os.environ.get("ADO_API_VERSION", "7.1")


def check_env():
    missing = [v for v in ("ADO_PAT", "ADO_ORG", "ADO_PROJECT") if not os.environ.get(v)]
    if missing:
        print(f"ERROR: Missing required environment variables: {' '.join(missing)}", file=sys.stderr)
        print("Set them: export ADO_PAT=<token> ADO_ORG=<org> ADO_PROJECT=<project>", file=sys.stderr)
        sys.exit(1)


def base_url():
    org = os.environ["ADO_ORG"]
    project = os.environ["ADO_PROJECT"]
    return f"https://dev.azure.com/{org}/{project}/_apis"


def auth_header():
    pat = os.environ["ADO_PAT"]
    token = base64.b64encode(f":{pat}".encode()).decode()
    return f"Basic {token}"


def ado_request(method, url, content_type="application/json", data=None):
    headers = {
        "Authorization": auth_header(),
        "Content-Type": content_type,
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


def cmd_get(args):
    work_item_id = args[0]
    expand = args[1] if len(args) > 1 else "all"
    result = ado_request("GET", f"{base_url()}/wit/workitems/{work_item_id}?$expand={expand}&api-version={ADO_API_VERSION}")
    print(result)


def cmd_create(args):
    wi_type = args[0]
    body = args[1]
    import re
    if not re.match(r"^[A-Za-z ]+$", wi_type):
        print(f"ERROR: Invalid work item type: {wi_type} (only letters and spaces allowed)", file=sys.stderr)
        sys.exit(1)
    encoded_type = urllib.parse.quote(wi_type)
    result = ado_request(
        "POST",
        f"{base_url()}/wit/workitems/${encoded_type}?api-version={ADO_API_VERSION}",
        "application/json-patch+json",
        body,
    )
    print(result)


def cmd_update(args):
    work_item_id = args[0]
    body = args[1]
    result = ado_request(
        "PATCH",
        f"{base_url()}/wit/workitems/{work_item_id}?api-version={ADO_API_VERSION}",
        "application/json-patch+json",
        body,
    )
    print(result)


def cmd_query(args):
    wiql = args[0]
    body = json.dumps({"query": wiql})
    result = ado_request("POST", f"{base_url()}/wit/wiql?api-version={ADO_API_VERSION}", "application/json", body)
    print(result)


def cmd_batch_get(args):
    ids = args[0]
    fields = args[1] if len(args) > 1 and args[1] else (
        "System.Id,System.Title,System.State,System.WorkItemType,"
        "System.AssignedTo,System.AreaPath,System.IterationPath,"
        "Microsoft.VSTS.Scheduling.StoryPoints,Microsoft.VSTS.Common.Priority"
    )
    result = ado_request("GET", f"{base_url()}/wit/workitems?ids={ids}&fields={fields}&api-version={ADO_API_VERSION}")
    print(result)


def cmd_attachments(args):
    work_item_id = args[0]
    result = ado_request("GET", f"{base_url()}/wit/workitems/{work_item_id}?$expand=relations&api-version={ADO_API_VERSION}")
    data = json.loads(result)
    relations = data.get("relations") or []
    attachments = [
        {
            "name": r.get("attributes", {}).get("name"),
            "url": r.get("url"),
            "size": r.get("attributes", {}).get("resourceSize"),
            "comment": r.get("attributes", {}).get("comment"),
        }
        for r in relations
        if r.get("rel") == "AttachedFile"
    ]
    print(json.dumps(attachments, indent=2))


def cmd_download(args):
    url = args[0]
    output = args[1]
    headers = {"Authorization": auth_header()}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            with open(output, "wb") as f:
                f.write(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Download failed: {e.reason}", file=sys.stderr)
        sys.exit(1)
    print(output)


def cmd_add_parent(args):
    child_id = args[0]
    parent_id = args[1]
    org = os.environ["ADO_ORG"]
    project = os.environ["ADO_PROJECT"]
    body = json.dumps([
        {
            "op": "add",
            "path": "/relations/-",
            "value": {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"https://dev.azure.com/{org}/{project}/_apis/wit/workitems/{parent_id}",
            },
        }
    ])
    result = ado_request(
        "PATCH",
        f"{base_url()}/wit/workitems/{child_id}?api-version={ADO_API_VERSION}",
        "application/json-patch+json",
        body,
    )
    print(result)


def cmd_children(args):
    work_item_id = args[0]
    result = ado_request("GET", f"{base_url()}/wit/workitems/{work_item_id}?$expand=relations&api-version={ADO_API_VERSION}")
    data = json.loads(result)
    relations = data.get("relations") or []
    child_ids = []
    for r in relations:
        if r.get("rel") == "System.LinkTypes.Hierarchy-Forward":
            url = r.get("url", "")
            child_ids.append(url.rstrip("/").split("/")[-1])
    if child_ids:
        ids_str = ",".join(child_ids)
        batch_result = ado_request("GET", f"{base_url()}/wit/workitems?ids={ids_str}&api-version={ADO_API_VERSION}")
        batch_data = json.loads(batch_result)
        print(json.dumps(batch_data.get("value", []), indent=2))
    else:
        print("[]")


USAGE = """\
Usage: ado-api.py <command> [args]

Commands:
  get <id> [expand]           Get work item (expand: all|relations|fields|links|none)
  create <type> <json-body>   Create work item (JSON patch document)
  update <id> <json-body>     Update work item (JSON patch document)
  query <wiql>                Execute WIQL query
  batch-get <ids> [fields]    Get multiple work items (comma-separated IDs)
  attachments <id>            List file attachments on a work item
  download <url> <output>     Download attachment to file
  add-parent <child> <parent> Link child to parent work item
  children <id>               Get child work items

Required: ADO_PAT, ADO_ORG, ADO_PROJECT
Optional: ADO_API_VERSION (default: 7.1)
"""

COMMANDS = {
    "get": (cmd_get, 1),
    "create": (cmd_create, 2),
    "update": (cmd_update, 2),
    "query": (cmd_query, 1),
    "batch-get": (cmd_batch_get, 1),
    "attachments": (cmd_attachments, 1),
    "download": (cmd_download, 2),
    "add-parent": (cmd_add_parent, 2),
    "children": (cmd_children, 1),
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
