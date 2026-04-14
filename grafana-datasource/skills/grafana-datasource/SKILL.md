---
name: Grafana Datasource
description: Use when the user asks to query Grafana, fetch metrics or logs from Grafana, run a PromQL query, run an Elasticsearch or OpenSearch query via Grafana, or analyze data from a Grafana datasource. The caller MUST supply the datasource UID (not name) and time range as ISO 8601 absolute timestamps (YYYY-MM-DDThh:mm:ssZ).
---

# Grafana Datasource Query

Fetch data from Grafana datasources (Prometheus, Elasticsearch, OpenSearch) via the Grafana REST API proxy. Results are returned as CSV.

## CRITICAL: Permitted Commands

You MUST only run one of these three commands. **No other commands. No exceptions.**

No curl. No wget. No bash. No API calls. No credential checks. No datasource lookups.

```bash
python3 ../../scripts/prometheus.py [flags]
python3 ../../scripts/elasticsearch.py [flags]
python3 ../../scripts/opensearch.py [flags]
```

Paths are relative to this skill file (`skills/grafana-datasource/SKILL.md`).

## Before Running — Gather From the User

Do NOT call any script until you have all required inputs. Ask the user if anything is missing.

| Input | Required | Notes |
|-------|----------|-------|
| **Datasource type** | yes | Prometheus, Elasticsearch, or OpenSearch |
| **Datasource UID** | yes | The Grafana UID string — NOT the display name. Ask the user; do not attempt to resolve it. |
| **Time range** | yes | Two absolute ISO 8601 timestamps: `YYYY-MM-DDThh:mm:ssZ`. Convert "last hour" / "today" etc. to absolute yourself. |
| **Query** | yes | PromQL expression (Prometheus) or JSON query DSL string (Elasticsearch/OpenSearch) |

## Prometheus

```bash
python3 ../../scripts/prometheus.py \
  --datasource-uid <uid> \
  --from <YYYY-MM-DDThh:mm:ssZ> \
  --to   <YYYY-MM-DDThh:mm:ssZ> \
  --query '<PromQL>' \
  [--step <seconds>] \
  [--histogram] \
  [--metrics p75,p90,stddev,iqr]
```

## Elasticsearch

```bash
python3 ../../scripts/elasticsearch.py \
  --datasource-uid <uid> \
  --from <YYYY-MM-DDThh:mm:ssZ> \
  --to   <YYYY-MM-DDThh:mm:ssZ> \
  --index <index-name-or-pattern> \
  --query '<JSON DSL>' \
  [--time-field <field>] \
  [--value-field <field>] \
  [--histogram] \
  [--metrics p75,p90,stddev,iqr]
```

## OpenSearch

```bash
python3 ../../scripts/opensearch.py \
  --datasource-uid <uid> \
  --from <YYYY-MM-DDThh:mm:ssZ> \
  --to   <YYYY-MM-DDThh:mm:ssZ> \
  --index <index-name-or-pattern> \
  --query '<JSON DSL>' \
  [--time-field <field>] \
  [--value-field <field>] \
  [--histogram] \
  [--metrics p75,p90,stddev,iqr]
```

## Environment Variables

The scripts validate these at startup and will return a clear error if missing. Do not attempt to set, find, or verify them yourself.

| Variable | Description |
|----------|-------------|
| `GRAFANA_URL` | Base URL e.g. `https://grafana.company.com` |
| `GRAFANA_TOKEN` | Grafana API token (service account or user token) |

## Output & Errors

Script stdout is CSV — return it directly to the user.

If the script exits with an error, show the error message to the user verbatim. Do not retry. Do not attempt to fix credentials. Do not fall back to any other approach.
