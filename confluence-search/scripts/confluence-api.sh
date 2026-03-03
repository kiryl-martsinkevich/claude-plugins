#!/usr/bin/env bash
set -euo pipefail

# Confluence REST API helper
# Required env vars: CONFLUENCE_PAT, CONFLUENCE_URL
# Optional: CONFLUENCE_USER (for Cloud basic auth — email:token)

check_env() {
  local missing=()
  [[ -z "${CONFLUENCE_PAT:-}" ]] && missing+=("CONFLUENCE_PAT")
  [[ -z "${CONFLUENCE_URL:-}" ]] && missing+=("CONFLUENCE_URL")
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: Missing required environment variables: ${missing[*]}" >&2
    echo "Set them: export CONFLUENCE_PAT=<token> CONFLUENCE_URL=<base-url>" >&2
    echo "  Server/DC: CONFLUENCE_URL=https://confluence.company.com" >&2
    echo "  Cloud:     CONFLUENCE_URL=https://company.atlassian.net/wiki CONFLUENCE_USER=user@company.com" >&2
    exit 1
  fi
}

# Normalize base URL (strip trailing slash)
base_url() {
  echo "${CONFLUENCE_URL%/}/rest/api"
}

auth_header() {
  if [[ -n "${CONFLUENCE_USER:-}" ]]; then
    # Cloud: Basic auth with email:api-token
    echo "Basic $(printf '%s:%s' "${CONFLUENCE_USER}" "${CONFLUENCE_PAT}" | base64 -w0 2>/dev/null || printf '%s:%s' "${CONFLUENCE_USER}" "${CONFLUENCE_PAT}" | base64)"
  else
    # Server/DC: Bearer token
    echo "Bearer ${CONFLUENCE_PAT}"
  fi
}

confluence_request() {
  local method="$1"
  local url="$2"
  local data="${3:-}"

  local -a args=(
    -s -S
    -X "$method"
    -H "Authorization: $(auth_header)"
    -H "Content-Type: application/json"
    -H "Accept: application/json"
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

# URL-encode a string
urlencode() {
  python3 -c "import sys,urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip()))" <<< "$1"
}

# Search using CQL
cmd_search() {
  local cql="$1"
  local limit="${2:-25}"
  local start="${3:-0}"
  local encoded_cql
  encoded_cql=$(urlencode "$cql")
  confluence_request GET "$(base_url)/content/search?cql=${encoded_cql}&limit=${limit}&start=${start}&expand=space,version,body.view,metadata.labels"
}

# Search and return compact results (id, title, space, url)
cmd_search_compact() {
  local cql="$1"
  local limit="${2:-25}"
  local result
  result=$(cmd_search "$cql" "$limit")
  echo "$result" | jq '[.results[] | {
    id: .id,
    type: .type,
    title: .title,
    space: (.space.key // "N/A"),
    url: (._links.base + ._links.webui),
    lastUpdated: (.version.when // "N/A"),
    lastAuthor: (.version.by.displayName // "N/A")
  }]'
}

# Get page content by ID
cmd_get_page() {
  local id="$1"
  local expand="${2:-body.storage,version,space,metadata.labels,children.attachment}"
  confluence_request GET "$(base_url)/content/${id}?expand=${expand}"
}

# Get page body as plain text (strip HTML)
cmd_get_page_text() {
  local id="$1"
  local result
  result=$(cmd_get_page "$id" "body.storage,space")
  echo "$result" | jq -r '.body.storage.value' | python3 -c "
import sys, html, re
text = sys.stdin.read()
text = re.sub(r'<br\s*/?>', '\n', text)
text = re.sub(r'</?(p|div|h[1-6]|li|tr)[^>]*>', '\n', text)
text = re.sub(r'<[^>]+>', '', text)
text = html.unescape(text)
for line in text.split('\n'):
    stripped = line.strip()
    if stripped:
        print(stripped)
"
}

# List attachments on a page
cmd_attachments() {
  local page_id="$1"
  local limit="${2:-50}"
  local result
  result=$(confluence_request GET "$(base_url)/content/${page_id}/child/attachment?limit=${limit}&expand=version,metadata.mediaType")
  echo "$result" | jq '[.results[] | {
    id: .id,
    title: .title,
    mediaType: (.metadata.mediaType // .extensions.mediaType // "unknown"),
    size: (.extensions.fileSize // 0),
    downloadUrl: (._links.base + ._links.download),
    lastUpdated: (.version.when // "N/A")
  }]'
}

# Download an attachment
cmd_download() {
  local url="$1"
  local output="$2"

  # Handle relative URLs
  if [[ "$url" == /* ]]; then
    url="${CONFLUENCE_URL%/}${url}"
  fi

  curl -s -S -L \
    -H "Authorization: $(auth_header)" \
    -o "$output" \
    "$url"
  echo "$output"
}

# Search specifically for attachments matching criteria
cmd_search_attachments() {
  local query="$1"
  local space="${2:-}"
  local limit="${3:-25}"
  local cql="type = attachment AND text ~ \"${query}\""
  if [[ -n "$space" ]]; then
    cql="type = attachment AND space.key = \"${space}\" AND text ~ \"${query}\""
  fi
  cmd_search_compact "$cql" "$limit"
}

# Search pages in a specific space
cmd_search_space() {
  local query="$1"
  local space="$2"
  local limit="${3:-25}"
  local cql="type = page AND space.key = \"${space}\" AND (text ~ \"${query}\" OR title ~ \"${query}\")"
  cmd_search_compact "$cql" "$limit"
}

# List spaces
cmd_spaces() {
  local limit="${1:-100}"
  confluence_request GET "$(base_url)/space?limit=${limit}&expand=description.plain" | \
    jq '[.results[] | {key: .key, name: .name, type: .type, description: (.description.plain.value // "")}]'
}

# Get space info
cmd_space_info() {
  local space_key="$1"
  confluence_request GET "$(base_url)/space/${space_key}?expand=description.plain,homepage"
}

# Main dispatch
check_env

case "${1:-help}" in
  search)              cmd_search "$2" "${3:-25}" "${4:-0}" ;;
  search-compact)      cmd_search_compact "$2" "${3:-25}" ;;
  get-page)            cmd_get_page "$2" "${3:-body.storage,version,space,metadata.labels}" ;;
  get-page-text)       cmd_get_page_text "$2" ;;
  attachments)         cmd_attachments "$2" "${3:-50}" ;;
  download)            cmd_download "$2" "$3" ;;
  search-attachments)  cmd_search_attachments "$2" "${3:-}" "${4:-25}" ;;
  search-space)        cmd_search_space "$2" "$3" "${4:-25}" ;;
  spaces)              cmd_spaces "${2:-100}" ;;
  space-info)          cmd_space_info "$2" ;;
  help|*)
    cat <<'USAGE'
Usage: confluence-api.sh <command> [args]

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
USAGE
    ;;
esac
