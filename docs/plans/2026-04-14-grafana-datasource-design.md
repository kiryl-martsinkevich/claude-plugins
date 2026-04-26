# Grafana Datasource Plugin — Design

## Overview

A plugin that lets agents fetch data from Grafana datasources (Prometheus, Elasticsearch, OpenSearch) via the Grafana REST API proxy. Each datasource has a dedicated Python CLI script (stdlib only). The skill's sole job is to invoke the right script.

---

## Plugin Layout

```
grafana-datasource/
  .claude-plugin/
    plugin.json
  skills/
    grafana-datasource/
      SKILL.md
  scripts/
    prometheus.py
    elasticsearch.py
    opensearch.py
```

---

## Authentication

Both `GRAFANA_URL` and `GRAFANA_TOKEN` are read from environment variables by each script at startup. No fallbacks. No config file lookups. If either is missing or the token is rejected, the script exits immediately with a clear human-readable error message on stderr and a non-zero exit code.

---

## Transport

All scripts use the Grafana datasource proxy:

```
/api/datasources/proxy/uid/{uid}/...
```

This proxies to the backend datasource using its native API:
- Prometheus: `GET /api/v1/query_range`
- Elasticsearch: `POST /{index}/_search`
- OpenSearch: `POST /{index}/_search`

Authorization header: `Authorization: Bearer {GRAFANA_TOKEN}`

---

## CLI Interface

### Shared flags (all three scripts)

| Flag | Required | Description |
|------|----------|-------------|
| `--datasource-uid` | yes | Grafana datasource UID (not name) |
| `--from` | yes | ISO 8601 start timestamp e.g. `2026-04-14T00:00:00Z` |
| `--to` | yes | ISO 8601 end timestamp e.g. `2026-04-14T01:00:00Z` |
| `--histogram` | no | Output histogram instead of raw rows |
| `--metrics` | no | Comma-separated extra stats: `p75,p90,stddev,iqr` (only with `--histogram`) |

### prometheus.py specific

| Flag | Required | Description |
|------|----------|-------------|
| `--query` | yes | PromQL expression |
| `--step` | no | Step in seconds (default: 60) |

### elasticsearch.py / opensearch.py specific

| Flag | Required | Description |
|------|----------|-------------|
| `--index` | yes | Index name or pattern |
| `--query` | yes | Elasticsearch JSON query DSL as a string |
| `--time-field` | no | Timestamp field name (default: `@timestamp`) |
| `--value-field` | no | Numeric field for histogram stats (default: `value`) |

---

## Chunking

Every script splits `[--from, --to]` into 5-minute windows. Each window is queried independently. Results are concatenated in order. If a chunk fails, a warning is printed to stderr and execution continues — partial data is still returned.

---

## CSV Output

Output is always written to stdout.

**Raw mode** (default): one row per datapoint.

- Prometheus: `timestamp,metric_name,labels,value`
- Elasticsearch/OpenSearch: one column per returned field, `timestamp` always first

**Histogram mode** (`--histogram`): bucket rows followed by a stats section.

```
bucket_start,bucket_end,count
...,..,...
__stats__
min,max,mean,p50,p95,p99[,p75,p90,stddev,iqr]
...,..,...
```

Extra stats are appended as additional columns in the `__stats__` row when `--metrics` is supplied.

---

## Skill Design

### Trigger

When the user asks to: query Grafana, fetch metrics, fetch logs from Grafana, analyze datasource data, run a PromQL/Elasticsearch query via Grafana.

### What the agent MUST gather before calling (ask the user if unknown)

1. **Datasource type**: Prometheus, Elasticsearch, or OpenSearch
2. **Datasource UID**: the Grafana-assigned UID — not the name. Do not attempt to resolve this via any API call.
3. **Time range**: absolute ISO 8601 timestamps. Convert any relative expression ("last hour", "today") yourself before calling.
4. **Query string**: PromQL expression or JSON DSL depending on type.

### Permitted commands

```
ONLY these three commands are permitted. No other commands. Ever.

  python3 ../../scripts/prometheus.py [flags]
  python3 ../../scripts/elasticsearch.py [flags]
  python3 ../../scripts/opensearch.py [flags]

Paths are relative to the skill file location (skills/grafana-datasource/SKILL.md).
Do not run curl, wget, bash, or any other command.
Do not attempt to verify credentials, list datasources, or resolve UIDs.
```

### Error handling

If a script exits with an error, surface the stderr message to the user verbatim. Do not retry, do not attempt to fix credentials, do not fall back to any other approach.

### Output

Script stdout is CSV. Return it directly to the user.

---

## Compatibility

The skill uses paths relative to the skill file (`../../scripts/`), so it works in any agent that loads skills from the filesystem and resolves relative paths from the skill file's location — including Claude Code and the GitHub Copilot VSCode plugin.
