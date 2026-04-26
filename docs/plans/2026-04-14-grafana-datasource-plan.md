# Grafana Datasource Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a plugin with three standalone Python CLI scripts (Prometheus, Elasticsearch, OpenSearch) that fetch data via Grafana's datasource proxy REST API and output CSV, plus a skill that invokes them.

**Architecture:** Three self-contained Python scripts (stdlib only), each validating env vars at startup, chunking the time range into 5-minute windows, querying the Grafana proxy endpoint, and writing CSV to stdout. A single SKILL.md routes agents to the right script — no other commands permitted.

**Tech Stack:** Python 3 (stdlib only: `argparse`, `urllib.request`, `json`, `csv`, `datetime`, `sys`, `os`, `math`), Grafana REST API datasource proxy.

**Design doc:** `docs/plans/2026-04-14-grafana-datasource-design.md`

---

## Task 1: Plugin Scaffold

**Files:**
- Create: `grafana-datasource/.claude-plugin/plugin.json`
- Create: `grafana-datasource/scripts/` (directory, empty)
- Create: `grafana-datasource/skills/grafana-datasource/` (directory, empty)

**Step 1: Create plugin.json**

```json
{
  "name": "grafana-datasource",
  "version": "0.1.0",
  "description": "Fetch data from Grafana datasources (Prometheus, Elasticsearch, OpenSearch) via REST API proxy. Outputs CSV.",
  "author": {
    "name": "kiryl"
  },
  "keywords": ["grafana", "prometheus", "elasticsearch", "opensearch", "metrics", "logs", "csv"]
}
```

**Step 2: Create directory structure**

```bash
mkdir -p grafana-datasource/.claude-plugin
mkdir -p grafana-datasource/scripts
mkdir -p grafana-datasource/skills/grafana-datasource
```

**Step 3: Commit**

```bash
git add grafana-datasource/
git commit -m "feat: scaffold grafana-datasource plugin"
```

---

## Task 2: Shared Utility Functions (inline in each script)

Each script is fully self-contained. The following utility functions are duplicated across all three scripts. Implement them identically in each.

### `parse_iso8601(s)` — parse ISO 8601 timestamp to datetime

```python
from datetime import datetime, timezone

def parse_iso8601(s):
    """Parse ISO 8601 timestamp string to UTC datetime. Accepts trailing Z."""
    s = s.replace('Z', '+00:00')
    return datetime.fromisoformat(s).astimezone(timezone.utc)
```

### `chunk_window(start, end, chunk_minutes=5)` — yield 5-min sub-windows

```python
from datetime import timedelta

def chunk_window(start, end, chunk_minutes=5):
    """Yield (chunk_start, chunk_end) pairs of chunk_minutes duration."""
    current = start
    delta = timedelta(minutes=chunk_minutes)
    while current < end:
        next_ts = min(current + delta, end)
        yield current, next_ts
        current = next_ts
```

### `percentile(sorted_vals, p)` — linear interpolation percentile

```python
def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    idx = (p / 100.0) * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    return sorted_vals[lo] + (idx - lo) * (sorted_vals[hi] - sorted_vals[lo])
```

### `calc_stats(values, extra_metrics)` — compute histogram statistics

```python
import math

def calc_stats(values, extra_metrics):
    """Return ordered list of (name, value) stat pairs."""
    if not values:
        return []
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mean = sum(sorted_vals) / n
    stats = [
        ('min',  sorted_vals[0]),
        ('max',  sorted_vals[-1]),
        ('mean', mean),
        ('p50',  percentile(sorted_vals, 50)),
        ('p95',  percentile(sorted_vals, 95)),
        ('p99',  percentile(sorted_vals, 99)),
    ]
    if 'p75' in extra_metrics:
        stats.append(('p75', percentile(sorted_vals, 75)))
    if 'p90' in extra_metrics:
        stats.append(('p90', percentile(sorted_vals, 90)))
    if 'stddev' in extra_metrics:
        variance = sum((v - mean) ** 2 for v in sorted_vals) / n
        stats.append(('stddev', math.sqrt(variance)))
    if 'iqr' in extra_metrics:
        stats.append(('iqr', percentile(sorted_vals, 75) - percentile(sorted_vals, 25)))
    return stats
```

### `make_histogram(values, num_buckets=20)` — compute bucket counts

```python
def make_histogram(values, num_buckets=20):
    """Return list of (bucket_start, bucket_end, count) tuples."""
    if not values:
        return []
    min_v, max_v = min(values), max(values)
    if min_v == max_v:
        return [(min_v, max_v, len(values))]
    bucket_size = (max_v - min_v) / num_buckets
    buckets = []
    for i in range(num_buckets):
        lo = min_v + i * bucket_size
        hi = min_v + (i + 1) * bucket_size
        count = sum(1 for v in values if lo <= v < hi)
        buckets.append([lo, hi, count])
    # Make last bucket right-inclusive
    last = buckets[-1]
    buckets[-1] = [last[0], max_v, sum(1 for v in values if last[0] <= v <= max_v)]
    return buckets
```

### `write_histogram_csv(writer, values, extra_metrics)` — write histogram + stats

```python
import csv, sys

def write_histogram_csv(values, extra_metrics):
    writer = csv.writer(sys.stdout)
    writer.writerow(['bucket_start', 'bucket_end', 'count'])
    for lo, hi, count in make_histogram(values):
        writer.writerow([f'{lo:.6f}', f'{hi:.6f}', count])
    stats = calc_stats(values, extra_metrics)
    if stats:
        writer.writerow(['__stats__'])
        writer.writerow([name for name, _ in stats])
        writer.writerow([f'{val:.6f}' for _, val in stats])
```

### `grafana_request(url, token, data=None)` — HTTP call with auth

```python
import urllib.request, urllib.error, json

def grafana_request(url, token, data=None):
    """GET if data is None, POST otherwise. Returns parsed JSON or raises."""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers,
                                  method='POST' if body else 'GET')
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors='replace')
        raise RuntimeError(f'HTTP {e.code} from Grafana: {body_text}') from e
```

### `get_env(name)` — validate env var present, fail with clear message

```python
import os, sys

def get_env(name):
    val = os.environ.get(name)
    if not val:
        print(f'Error: {name} environment variable is not set.', file=sys.stderr)
        print(f'Set it with: export {name}=<value>', file=sys.stderr)
        sys.exit(1)
    return val
```

---

## Task 3: prometheus.py

**Files:**
- Create: `grafana-datasource/scripts/prometheus.py`

**Step 1: Write prometheus.py**

Complete script — include ALL utility functions from Task 2 inline at the top, then:

```python
#!/usr/bin/env python3
"""Fetch Prometheus data via Grafana datasource proxy. Outputs CSV to stdout."""

import argparse, csv, sys
# ... (all utility functions from Task 2 inlined here) ...

def parse_args():
    p = argparse.ArgumentParser(
        description='Fetch Prometheus metrics via Grafana proxy. Outputs CSV.')
    p.add_argument('--datasource-uid', required=True,
                   help='Grafana datasource UID (not name)')
    p.add_argument('--from', dest='from_ts', required=True,
                   help='Start time ISO 8601 e.g. 2026-04-14T00:00:00Z')
    p.add_argument('--to', dest='to_ts', required=True,
                   help='End time ISO 8601 e.g. 2026-04-14T01:00:00Z')
    p.add_argument('--query', required=True,
                   help='PromQL expression')
    p.add_argument('--step', type=int, default=60,
                   help='Step interval in seconds (default: 60)')
    p.add_argument('--histogram', action='store_true',
                   help='Output histogram + stats instead of raw rows')
    p.add_argument('--metrics', default='',
                   help='Extra stats for histogram: p75,p90,stddev,iqr')
    return p.parse_args()

def query_chunk(base_url, token, uid, query, start, end, step):
    """Query Prometheus query_range for one time window. Returns list of (ts, metric_name, labels_str, value)."""
    url = (f'{base_url}/api/datasources/proxy/uid/{uid}/api/v1/query_range'
           f'?query={urllib.parse.quote(query)}'
           f'&start={int(start.timestamp())}'
           f'&end={int(end.timestamp())}'
           f'&step={step}')
    data = grafana_request(url, token)
    if data.get('status') != 'success':
        raise RuntimeError(f'Prometheus error: {data.get("error", data)}')
    rows = []
    for series in data['data']['result']:
        metric = series['metric']
        name = metric.get('__name__', '')
        labels = ','.join(f'{k}={v}' for k, v in sorted(metric.items())
                          if k != '__name__')
        for ts, val in series['values']:
            rows.append((ts, name, labels, val))
    return rows

def main():
    args = parse_args()
    grafana_url = get_env('GRAFANA_URL').rstrip('/')
    grafana_token = get_env('GRAFANA_TOKEN')
    extra_metrics = [m.strip() for m in args.metrics.split(',') if m.strip()]

    start = parse_iso8601(args.from_ts)
    end   = parse_iso8601(args.to_ts)

    all_rows = []
    seen = set()  # deduplicate by (ts, metric_name, labels) across chunk boundaries

    for chunk_start, chunk_end in chunk_window(start, end):
        try:
            rows = query_chunk(grafana_url, grafana_token, args.datasource_uid,
                               args.query, chunk_start, chunk_end, args.step)
            for row in rows:
                key = (row[0], row[1], row[2])
                if key not in seen:
                    seen.add(key)
                    all_rows.append(row)
        except Exception as e:
            print(f'Warning: chunk {chunk_start.isoformat()} failed: {e}',
                  file=sys.stderr)

    if args.histogram:
        values = []
        for _, _, _, val in all_rows:
            try:
                values.append(float(val))
            except (ValueError, TypeError):
                pass
        write_histogram_csv(values, extra_metrics)
    else:
        writer = csv.writer(sys.stdout)
        writer.writerow(['timestamp', 'metric_name', 'labels', 'value'])
        for ts, name, labels, val in sorted(all_rows, key=lambda r: r[0]):
            writer.writerow([ts, name, labels, val])

if __name__ == '__main__':
    main()
```

Note: add `import urllib.parse` at the top alongside other imports.

**Step 2: Verify script starts and shows help**

```bash
python3 grafana-datasource/scripts/prometheus.py --help
```

Expected: argparse help text listing all flags, no import errors.

**Step 3: Verify env var error message**

```bash
python3 grafana-datasource/scripts/prometheus.py \
  --datasource-uid test --from 2026-04-14T00:00:00Z \
  --to 2026-04-14T01:00:00Z --query 'up'
```

Expected: `Error: GRAFANA_URL environment variable is not set.` on stderr, exit code 1.

**Step 4: Commit**

```bash
git add grafana-datasource/scripts/prometheus.py
git commit -m "feat: add prometheus.py datasource script"
```

---

## Task 4: elasticsearch.py

**Files:**
- Create: `grafana-datasource/scripts/elasticsearch.py`

**Step 1: Write elasticsearch.py**

Include ALL utility functions from Task 2 inline. The key difference is injecting a time-range filter and flattening ES hits to CSV.

```python
#!/usr/bin/env python3
"""Fetch Elasticsearch data via Grafana datasource proxy. Outputs CSV to stdout."""

import argparse, csv, json, sys
# ... (all utility functions from Task 2 inlined here) ...

def parse_args():
    p = argparse.ArgumentParser(
        description='Fetch Elasticsearch data via Grafana proxy. Outputs CSV.')
    p.add_argument('--datasource-uid', required=True)
    p.add_argument('--from', dest='from_ts', required=True,
                   help='ISO 8601 start e.g. 2026-04-14T00:00:00Z')
    p.add_argument('--to', dest='to_ts', required=True,
                   help='ISO 8601 end e.g. 2026-04-14T01:00:00Z')
    p.add_argument('--index', required=True, help='ES index name or pattern')
    p.add_argument('--query', required=True,
                   help='ES query DSL as JSON string, e.g. \'{"query":{"match_all":{}}}\'')
    p.add_argument('--time-field', default='@timestamp',
                   help='Timestamp field name (default: @timestamp)')
    p.add_argument('--value-field', default='value',
                   help='Numeric field for histogram stats (default: value)')
    p.add_argument('--histogram', action='store_true')
    p.add_argument('--metrics', default='',
                   help='Extra stats: p75,p90,stddev,iqr')
    return p.parse_args()

def inject_time_range(query_dict, time_field, from_str, to_str):
    """Inject a range filter on time_field into query_dict (mutates in place)."""
    range_filter = {'range': {time_field: {'gte': from_str, 'lte': to_str}}}
    if 'query' not in query_dict:
        query_dict['query'] = {'bool': {'filter': [range_filter]}}
    elif 'bool' in query_dict['query']:
        filters = query_dict['query']['bool'].setdefault('filter', [])
        if isinstance(filters, list):
            filters.append(range_filter)
        else:
            query_dict['query']['bool']['filter'] = [filters, range_filter]
    else:
        query_dict['query'] = {
            'bool': {'must': [query_dict['query']], 'filter': [range_filter]}
        }
    return query_dict

def flatten_hit(hit):
    """Flatten _source dict. Returns ordered dict with all fields."""
    return hit.get('_source', {})

def query_chunk(base_url, token, uid, index, query_dict, time_field, from_dt, to_dt):
    """Query ES _search for one time window. Returns list of flat dicts."""
    from_str = from_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    to_str   = to_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    q = inject_time_range(dict(query_dict), time_field, from_str, to_str)
    # Add size limit and sort by time field
    q.setdefault('size', 10000)
    q['sort'] = [{time_field: {'order': 'asc'}}]
    url = f'{base_url}/api/datasources/proxy/uid/{uid}/{index}/_search'
    data = grafana_request(url, token, data=q)
    hits = data.get('hits', {}).get('hits', [])
    return [flatten_hit(h) for h in hits]

def main():
    args = parse_args()
    grafana_url   = get_env('GRAFANA_URL').rstrip('/')
    grafana_token = get_env('GRAFANA_TOKEN')
    extra_metrics = [m.strip() for m in args.metrics.split(',') if m.strip()]

    try:
        base_query = json.loads(args.query)
    except json.JSONDecodeError as e:
        print(f'Error: --query is not valid JSON: {e}', file=sys.stderr)
        sys.exit(1)

    start = parse_iso8601(args.from_ts)
    end   = parse_iso8601(args.to_ts)

    all_rows = []
    all_keys = []  # track column order from first chunk

    for chunk_start, chunk_end in chunk_window(start, end):
        try:
            rows = query_chunk(grafana_url, grafana_token, args.datasource_uid,
                               args.index, base_query, args.time_field,
                               chunk_start, chunk_end)
            for row in rows:
                for k in row:
                    if k not in all_keys:
                        all_keys.append(k)
                all_rows.append(row)
        except Exception as e:
            print(f'Warning: chunk {chunk_start.isoformat()} failed: {e}',
                  file=sys.stderr)

    # Ensure time field is first column
    if args.time_field in all_keys:
        all_keys.remove(args.time_field)
        all_keys.insert(0, args.time_field)

    if args.histogram:
        values = []
        for row in all_rows:
            try:
                values.append(float(row[args.value_field]))
            except (KeyError, ValueError, TypeError):
                pass
        write_histogram_csv(values, extra_metrics)
    else:
        writer = csv.writer(sys.stdout)
        writer.writerow(all_keys)
        for row in all_rows:
            writer.writerow([row.get(k, '') for k in all_keys])

if __name__ == '__main__':
    main()
```

**Step 2: Verify help and env error**

```bash
python3 grafana-datasource/scripts/elasticsearch.py --help
python3 grafana-datasource/scripts/elasticsearch.py \
  --datasource-uid x --index logs --query '{}' \
  --from 2026-04-14T00:00:00Z --to 2026-04-14T01:00:00Z
```

Expected: help text clean; second command: `Error: GRAFANA_URL...` on stderr.

**Step 3: Verify bad JSON query error**

```bash
GRAFANA_URL=http://x GRAFANA_TOKEN=t \
python3 grafana-datasource/scripts/elasticsearch.py \
  --datasource-uid x --index logs --query 'not-json' \
  --from 2026-04-14T00:00:00Z --to 2026-04-14T01:00:00Z
```

Expected: `Error: --query is not valid JSON:` on stderr, exit 1.

**Step 4: Commit**

```bash
git add grafana-datasource/scripts/elasticsearch.py
git commit -m "feat: add elasticsearch.py datasource script"
```

---

## Task 5: opensearch.py

**Files:**
- Create: `grafana-datasource/scripts/opensearch.py`

**Step 1: Copy elasticsearch.py, change description only**

OpenSearch uses the same `_search` API. The only differences:
- Shebang comment: `"""Fetch OpenSearch data via Grafana datasource proxy. Outputs CSV to stdout."""`
- argparse description: `'Fetch OpenSearch data via Grafana proxy. Outputs CSV.'`
- All logic is identical to elasticsearch.py.

Do NOT create a shared module. Each script must be fully self-contained.

**Step 2: Verify help and env error**

```bash
python3 grafana-datasource/scripts/opensearch.py --help
```

Expected: identical structure to elasticsearch.py help.

**Step 3: Commit**

```bash
git add grafana-datasource/scripts/opensearch.py
git commit -m "feat: add opensearch.py datasource script"
```

---

## Task 6: SKILL.md

**Files:**
- Create: `grafana-datasource/skills/grafana-datasource/SKILL.md`

**Step 1: Write SKILL.md**

```markdown
---
name: Grafana Datasource
description: Use when the user asks to query Grafana, fetch metrics or logs from Grafana, run a PromQL query, run an Elasticsearch or OpenSearch query via Grafana, or analyze data from a Grafana datasource. Requires the caller to supply the datasource UID and ISO 8601 absolute timestamps.
---

# Grafana Datasource Query

Fetch data from Grafana datasources (Prometheus, Elasticsearch, OpenSearch) via the Grafana REST API proxy. Results are returned as CSV.

## CRITICAL: Only These Commands Are Permitted

You MUST only run one of these three commands. No other commands. No exceptions. No curl. No wget. No bash. No API calls to look anything up.

```
python3 ../../scripts/prometheus.py [flags]
python3 ../../scripts/elasticsearch.py [flags]
python3 ../../scripts/opensearch.py [flags]
```

Paths are relative to this skill file (`skills/grafana-datasource/SKILL.md`).

## Before Running — Gather These From the User

Do NOT call any script until you have all required inputs. Ask the user if any are missing.

| Input | Required | Notes |
|-------|----------|-------|
| **Datasource type** | yes | Prometheus, Elasticsearch, or OpenSearch |
| **Datasource UID** | yes | The Grafana UID string — NOT the display name. Ask the user if unknown. |
| **Time range** | yes | Two absolute ISO 8601 timestamps: `YYYY-MM-DDThh:mm:ssZ`. Convert "last hour", "today", etc. to absolute yourself before calling. |
| **Query** | yes | PromQL expression (Prometheus) or JSON query DSL string (Elasticsearch/OpenSearch) |

## Flags

### Prometheus

```
python3 ../../scripts/prometheus.py \
  --datasource-uid <uid> \
  --from <ISO8601> \
  --to <ISO8601> \
  --query '<PromQL>' \
  [--step <seconds>] \
  [--histogram] \
  [--metrics p75,p90,stddev,iqr]
```

### Elasticsearch / OpenSearch

```
python3 ../../scripts/elasticsearch.py \
  --datasource-uid <uid> \
  --from <ISO8601> \
  --to <ISO8601> \
  --index <index-name> \
  --query '<JSON DSL>' \
  [--time-field <field>] \
  [--value-field <field>] \
  [--histogram] \
  [--metrics p75,p90,stddev,iqr]
```

## Environment Variables

The scripts require these to be set in the environment. They validate this themselves and will return a clear error message if missing. Do not attempt to set or find these yourself.

| Variable | Description |
|----------|-------------|
| `GRAFANA_URL` | Base URL e.g. `https://grafana.company.com` |
| `GRAFANA_TOKEN` | API token (service account or user token) |

## Output

Script stdout is CSV. Return it directly to the user.

If the script exits with an error, show the error message to the user verbatim. Do not retry. Do not try to fix credentials. Do not fall back to any other approach.
```

**Step 2: Verify SKILL.md is valid markdown**

```bash
python3 -c "
import sys
with open('grafana-datasource/skills/grafana-datasource/SKILL.md') as f:
    content = f.read()
assert '---' in content, 'missing frontmatter'
assert 'python3 ../../scripts/prometheus.py' in content
assert 'python3 ../../scripts/elasticsearch.py' in content
assert 'python3 ../../scripts/opensearch.py' in content
print('SKILL.md OK')
"
```

Expected: `SKILL.md OK`

**Step 3: Commit**

```bash
git add grafana-datasource/skills/grafana-datasource/SKILL.md
git commit -m "feat: add grafana-datasource skill"
```

---

## Task 7: Final Smoke Tests

**Step 1: Verify all three scripts parse args cleanly**

```bash
for script in prometheus elasticsearch opensearch; do
  echo "=== $script ==="
  python3 grafana-datasource/scripts/$script.py --help 2>&1 | head -3
done
```

Expected: each prints a description line and `options:` or `optional arguments:` without errors.

**Step 2: Verify env var failure on all three**

```bash
for script in prometheus elasticsearch opensearch; do
  python3 grafana-datasource/scripts/$script.py \
    --datasource-uid x --from 2026-04-14T00:00:00Z --to 2026-04-14T01:00:00Z \
    --query 'up' 2>&1 | head -1
done
```

Expected: `Error: GRAFANA_URL environment variable is not set.` for each.

**Step 3: Verify chunking logic inline**

```bash
python3 -c "
from datetime import datetime, timezone, timedelta

def parse_iso8601(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc)

def chunk_window(start, end, chunk_minutes=5):
    current = start
    delta = timedelta(minutes=chunk_minutes)
    while current < end:
        next_ts = min(current + delta, end)
        yield current, next_ts
        current = next_ts

start = parse_iso8601('2026-04-14T00:00:00Z')
end   = parse_iso8601('2026-04-14T00:17:00Z')
chunks = list(chunk_window(start, end))
assert len(chunks) == 4, f'expected 4 chunks, got {len(chunks)}: {chunks}'
assert chunks[0][0] == start
assert chunks[-1][1] == end
print(f'chunking OK: {len(chunks)} chunks for 17-minute window')
"
```

Expected: `chunking OK: 4 chunks for 17-minute window`

**Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete grafana-datasource plugin"
```
