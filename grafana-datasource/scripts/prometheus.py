#!/usr/bin/env python3
"""Fetch Prometheus metrics via Grafana datasource proxy. Outputs CSV to stdout."""

import argparse
import csv
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Utilities (inlined — script must be self-contained)
# ---------------------------------------------------------------------------

def get_env(name):
    """Read required env var. Exit with clear message if missing."""
    val = os.environ.get(name)
    if not val:
        print(f'Error: {name} environment variable is not set.', file=sys.stderr)
        print(f'Set it with: export {name}=<value>', file=sys.stderr)
        sys.exit(1)
    return val


def parse_iso8601(s):
    """Parse ISO 8601 timestamp string to UTC datetime. Accepts trailing Z."""
    return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc)


def chunk_window(start, end, chunk_minutes=5):
    """Yield (chunk_start, chunk_end) pairs covering [start, end]."""
    current = start
    delta = timedelta(minutes=chunk_minutes)
    while current < end:
        next_ts = min(current + delta, end)
        yield current, next_ts
        current = next_ts


def grafana_request(url, token, data=None):
    """GET if data is None, POST otherwise. Returns parsed JSON or raises RuntimeError."""
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


def percentile(sorted_vals, p):
    """Linear interpolation percentile on a sorted list."""
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    idx = (p / 100.0) * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    return sorted_vals[lo] + (idx - lo) * (sorted_vals[hi] - sorted_vals[lo])


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


def make_histogram(values, num_buckets=20):
    """Return list of [bucket_start, bucket_end, count] for the given values."""
    if not values:
        return []
    min_v, max_v = min(values), max(values)
    if min_v == max_v:
        return [[min_v, max_v, len(values)]]
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


def write_histogram_csv(values, extra_metrics):
    """Write histogram buckets + stats section to stdout."""
    writer = csv.writer(sys.stdout)
    writer.writerow(['bucket_start', 'bucket_end', 'count'])
    for lo, hi, count in make_histogram(values):
        writer.writerow([f'{lo:.6f}', f'{hi:.6f}', count])
    stats = calc_stats(values, extra_metrics)
    if stats:
        writer.writerow(['__stats__'])
        writer.writerow([name for name, _ in stats])
        writer.writerow([f'{val:.6f}' for _, val in stats])


# ---------------------------------------------------------------------------
# Prometheus-specific
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description='Fetch Prometheus metrics via Grafana datasource proxy. Outputs CSV to stdout.')
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
                   help='Extra histogram stats: comma-separated from p75,p90,stddev,iqr')
    return p.parse_args()


def query_chunk(base_url, token, uid, query, start, end, step):
    """Query Prometheus query_range for one time window.
    Returns list of (timestamp_int, metric_name, labels_str, value_str)."""
    url = (
        f'{base_url}/api/datasources/proxy/uid/{uid}/api/v1/query_range'
        f'?query={urllib.parse.quote(query)}'
        f'&start={int(start.timestamp())}'
        f'&end={int(end.timestamp())}'
        f'&step={step}'
    )
    data = grafana_request(url, token)
    if data.get('status') != 'success':
        raise RuntimeError(f'Prometheus error: {data.get("error", data)}')
    rows = []
    for series in data['data']['result']:
        metric = series['metric']
        name = metric.get('__name__', '')
        labels = ','.join(
            f'{k}={v}' for k, v in sorted(metric.items()) if k != '__name__'
        )
        for ts, val in series['values']:
            rows.append((ts, name, labels, val))
    return rows


def main():
    args = parse_args()
    grafana_url   = get_env('GRAFANA_URL').rstrip('/')
    grafana_token = get_env('GRAFANA_TOKEN')
    extra_metrics = [m.strip() for m in args.metrics.split(',') if m.strip()]

    start = parse_iso8601(args.from_ts)
    end   = parse_iso8601(args.to_ts)

    all_rows = []
    seen = set()  # deduplicate datapoints at chunk boundaries

    for chunk_start, chunk_end in chunk_window(start, end):
        try:
            rows = query_chunk(
                grafana_url, grafana_token, args.datasource_uid,
                args.query, chunk_start, chunk_end, args.step,
            )
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
