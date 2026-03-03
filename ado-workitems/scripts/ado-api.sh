#!/usr/bin/env bash
set -euo pipefail

# Azure DevOps REST API helper
# Required env vars: ADO_PAT, ADO_ORG, ADO_PROJECT
# Optional: ADO_API_VERSION (default: 7.1)

ADO_API_VERSION="${ADO_API_VERSION:-7.1}"

check_env() {
  local missing=()
  [[ -z "${ADO_PAT:-}" ]] && missing+=("ADO_PAT")
  [[ -z "${ADO_ORG:-}" ]] && missing+=("ADO_ORG")
  [[ -z "${ADO_PROJECT:-}" ]] && missing+=("ADO_PROJECT")
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: Missing required environment variables: ${missing[*]}" >&2
    echo "Set them: export ADO_PAT=<token> ADO_ORG=<org> ADO_PROJECT=<project>" >&2
    exit 1
  fi
}

base_url() {
  echo "https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis"
}

auth_header() {
  echo "Basic $(printf ':%s' "${ADO_PAT}" | base64 -w0 2>/dev/null || printf ':%s' "${ADO_PAT}" | base64)"
}

ado_request() {
  local method="$1"
  local url="$2"
  local content_type="${3:-application/json}"
  local data="${4:-}"

  local -a args=(
    -s -S
    -X "$method"
    -H "Authorization: $(auth_header)"
    -H "Content-Type: ${content_type}"
  )

  if [[ -n "$data" ]]; then
    args+=(-d "$data")
  fi

  local tmpfile
  tmpfile=$(mktemp)
  trap "rm -f '$tmpfile' '${tmpfile}.err'" RETURN

  local exit_code=0
  curl -w "\n%{http_code}" "${args[@]}" "$url" 2>"${tmpfile}.err" >"$tmpfile" || exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    echo "ERROR: curl failed (exit $exit_code): $(cat "${tmpfile}.err")" >&2
    return 1
  fi

  local http_code response
  http_code=$(tail -1 "$tmpfile")
  response=$(sed '$d' "$tmpfile")

  if [[ "$http_code" -ge 400 ]] 2>/dev/null; then
    echo "ERROR: HTTP ${http_code}" >&2
    echo "$response" | jq . 2>/dev/null || echo "$response" >&2
    return 1
  fi

  echo "$response"
}

cmd_get() {
  local id="$1"
  local expand="${2:-all}"
  ado_request GET "$(base_url)/wit/workitems/${id}?\$expand=${expand}&api-version=${ADO_API_VERSION}"
}

cmd_create() {
  local type="$1"
  local body="$2"
  if [[ ! "$type" =~ ^[A-Za-z\ ]+$ ]]; then
    echo "ERROR: Invalid work item type: $type (only letters and spaces allowed)" >&2
    return 1
  fi
  local encoded_type="${type// /%20}"
  ado_request POST "$(base_url)/wit/workitems/\$${encoded_type}?api-version=${ADO_API_VERSION}" \
    "application/json-patch+json" "$body"
}

cmd_update() {
  local id="$1"
  local body="$2"
  ado_request PATCH "$(base_url)/wit/workitems/${id}?api-version=${ADO_API_VERSION}" \
    "application/json-patch+json" "$body"
}

cmd_query() {
  local wiql="$1"
  local body
  body=$(jq -n --arg q "$wiql" '{"query": $q}')
  ado_request POST "$(base_url)/wit/wiql?api-version=${ADO_API_VERSION}" \
    "application/json" "$body"
}

cmd_batch_get() {
  local ids="$1"
  local fields="${2:-System.Id,System.Title,System.State,System.WorkItemType,System.AssignedTo,System.AreaPath,System.IterationPath,Microsoft.VSTS.Scheduling.StoryPoints,Microsoft.VSTS.Common.Priority}"
  ado_request GET "$(base_url)/wit/workitems?ids=${ids}&fields=${fields}&api-version=${ADO_API_VERSION}"
}

cmd_attachments() {
  local id="$1"
  local result
  result=$(ado_request GET "$(base_url)/wit/workitems/${id}?\$expand=relations&api-version=${ADO_API_VERSION}")
  echo "$result" | jq '[.relations // [] | .[] | select(.rel == "AttachedFile") | {name: .attributes.name, url: .url, size: .attributes.resourceSize, comment: .attributes.comment}]'
}

cmd_download() {
  local url="$1"
  local output="$2"
  curl -s -S --fail-with-body \
    -H "Authorization: $(auth_header)" \
    -o "$output" \
    "$url"
  echo "$output"
}

cmd_add_parent() {
  local child_id="$1"
  local parent_id="$2"
  local body
  body=$(jq -n --arg url "https://dev.azure.com/${ADO_ORG}/${ADO_PROJECT}/_apis/wit/workitems/${parent_id}" '[{
    "op": "add",
    "path": "/relations/-",
    "value": {
      "rel": "System.LinkTypes.Hierarchy-Reverse",
      "url": $url
    }
  }]')
  ado_request PATCH "$(base_url)/wit/workitems/${child_id}?api-version=${ADO_API_VERSION}" \
    "application/json-patch+json" "$body"
}

cmd_children() {
  local id="$1"
  local result
  result=$(ado_request GET "$(base_url)/wit/workitems/${id}?\$expand=relations&api-version=${ADO_API_VERSION}")
  local child_ids
  child_ids=$(echo "$result" | jq -r '[.relations // [] | .[] | select(.rel == "System.LinkTypes.Hierarchy-Forward") | .url | split("/") | last] | join(",")')
  if [[ -n "$child_ids" ]]; then
    cmd_batch_get "$child_ids" | jq '.value // []'
  else
    echo "[]"
  fi
}

# Main dispatch
check_env

case "${1:-help}" in
  get)          cmd_get "$2" "${3:-all}" ;;
  create)       cmd_create "$2" "$3" ;;
  update)       cmd_update "$2" "$3" ;;
  query)        cmd_query "$2" ;;
  batch-get)    cmd_batch_get "$2" "${3:-}" ;;
  attachments)  cmd_attachments "$2" ;;
  download)     cmd_download "$2" "$3" ;;
  add-parent)   cmd_add_parent "$2" "$3" ;;
  children)     cmd_children "$2" ;;
  help|*)
    cat <<'USAGE'
Usage: ado-api.sh <command> [args]

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
USAGE
    ;;
esac
