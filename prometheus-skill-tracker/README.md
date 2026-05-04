# prometheus-skill-tracker

A `PreToolUse` hook plugin that reports every tool/skill invocation to a
Prometheus Pushgateway and/or a JSONL log file. Pure Python, standard library
only, no third-party dependencies, runs on Windows, Linux, and macOS, and is
compatible with both Claude Code and GitHub Copilot in VS Code.

The hook fires once per tool call. For invocations of the special `Skill`
tool the recorded label is the actual skill name (e.g. `plugin-dev:hook-development`),
not the literal string `Skill`. For everything else the tool name itself is
recorded.

## Metric shape

```
# TYPE agent_tool_invocation gauge
# HELP agent_tool_invocation Unix timestamp of last tool invocation
agent_tool_invocation{user="kiryl",tool="superpowers:brainstorming",marketplace="superpowers-marketplace",author="Jesse Vincent"} 1777898479
```

The gauge value is the unix timestamp of the most recent invocation for the
given label set. The pushgateway grouping key is `job=agent_tool_tracker,
user=<user>` so multiple skills/tools accumulate as distinct series under
each user's grouping.

## Quick start

### Claude Code

1. Install from the marketplace:
   ```bash
   /plugin install prometheus-skill-tracker@claude-plugins
   ```
2. Point at your pushgateway:
   ```bash
   export PROMETHEUS_PUSHGATEWAY_URL=http://pushgateway.example.com:9091
   ```
3. That's it. The plugin's `hooks/hooks.json` registers the `PreToolUse`
   hook on the `*` matcher and resolves `${CLAUDE_PLUGIN_ROOT}` automatically.

### GitHub Copilot in VS Code

The Claude plugin format is shared with Copilot, and Copilot expands
`${CLAUDE_PLUGIN_ROOT}` the same way Claude Code does. Either:

- Add this marketplace to `chat.plugins.marketplaces` in VS Code settings and
  install through the plugin picker, **or**
- Point `chat.pluginLocations` at a local checkout.

Then set `PROMETHEUS_PUSHGATEWAY_URL` in your environment.

> **Note:** Copilot has no `Skill` tool — skills are loaded on-demand and
> aren't surfaced through `PreToolUse`. The hook still fires on every other
> tool call, which is what the wildcard matcher is for.

### Testing without a pushgateway

```bash
export SKILL_TRACKER_LOG_FILE=/tmp/agent-tools.jsonl
# ...use Claude Code/Copilot normally...
tail -f /tmp/agent-tools.jsonl
```

Use `SKILL_TRACKER_LOG_FILE=-` to log to stderr instead (handy with
`claude --debug`). When both `PROMETHEUS_PUSHGATEWAY_URL` and
`SKILL_TRACKER_LOG_FILE` are set, the script does both.

## Configuration

| Env var | Required | Default | Purpose |
|---|---|---|---|
| `PROMETHEUS_PUSHGATEWAY_URL` | one of | (unset) | Base URL of the pushgateway, e.g. `http://pushgateway:9091`. No auth. |
| `SKILL_TRACKER_LOG_FILE` | one of | (unset) | Append a JSONL line per invocation. Use `-` for stderr. `~` and `${VAR}` are expanded. |
| `SKILL_TRACKER_EXCLUDE_TOOLS` | no | `Bash,Read,Write,Edit,Glob,Grep,LS,Notebook*,Todo*,Task*,BashOutput,KillShell,ToolSearch` | Comma-separated `fnmatch` patterns to skip. Setting this **replaces** the defaults. |
| `SKILL_TRACKER_ANONYMOUS` | no | (unset) | If `1`/`true`/`yes`/`on`, replaces the user identity with `anon` in both the label and the pushgateway URL path. |
| `SKILL_TRACKER_MARKETPLACE` | no | (auto) | Override the `marketplace` label. Author lookup still runs independently. |
| `BANKID`, `PSID` | no | — | Preferred user identifiers (in that order); fall back to `USER` then `USERNAME`. |
| `CLAUDE_CONFIG_DIR` | no | `~/.claude` | Override the directory containing `plugins/installed_plugins.json` for marketplace/author resolution. |

If neither `PROMETHEUS_PUSHGATEWAY_URL` nor `SKILL_TRACKER_LOG_FILE` is set,
the hook silently exits 0 (does nothing).

## Labels

| Label | Source |
|---|---|
| `user` | `BANKID` → `PSID` → `USER` → `USERNAME` → `"unknown"`, or `"anon"` if `SKILL_TRACKER_ANONYMOUS` is truthy. |
| `tool` | The skill name (for the `Skill` tool — read from `tool_input.skill`/`tool_input.name`) or the tool name otherwise. |
| `marketplace` | Parsed from `~/.claude/plugins/installed_plugins.json` keys (`<plugin>@<marketplace>`). `"user"` for non-namespaced names; `"unknown"` if the plugin isn't discoverable. Overridable via `SKILL_TRACKER_MARKETPLACE`. |
| `author` | Read from the discovered plugin's `.claude-plugin/plugin.json` — supports both string and `{name: ...}` object shapes. Empty string when not discoverable or not present. |

## JSONL log entry shape

```json
{"action":"push","author":"Anthropic","iso_time":"2026-05-04T12:41:18Z","marketplace":"claude-plugins-official","tool":"plugin-dev:hook-development","ts":1777898478,"user":"kiryl"}
```

`action` is one of:

- `push` — `PROMETHEUS_PUSHGATEWAY_URL` is set, the metric was sent.
- `log_only` — only `SKILL_TRACKER_LOG_FILE` is set, no push attempted.
- `skip` — matched an entry in `SKILL_TRACKER_EXCLUDE_TOOLS`. Logged so you
  can see the exclusion patterns in action; useful for tuning the filter.

## Examples

**Public/community telemetry — never sends user identity:**
```bash
export PROMETHEUS_PUSHGATEWAY_URL=http://stats.example.com:9091
export SKILL_TRACKER_ANONYMOUS=1
```

**Track only MCP and skill calls, ignore everything else:**
```bash
export SKILL_TRACKER_EXCLUDE_TOOLS='Bash,Read,Write,Edit,Glob,Grep,LS,Notebook*,Todo*,Task*,BashOutput,KillShell,ToolSearch,WebFetch,WebSearch,Agent,AskUserQuestion'
```

**Disable filtering (log every tool call):**
```bash
export SKILL_TRACKER_EXCLUDE_TOOLS=''
```

**Tune your exclude list against a real session:**
```bash
SKILL_TRACKER_LOG_FILE=/tmp/agent-tools.jsonl claude   # use as normal
jq -r '.tool' /tmp/agent-tools.jsonl | sort | uniq -c | sort -rn
```

**One-shot ad-hoc smoke test:**
```bash
echo '{"tool_name":"Skill","tool_input":{"skill":"foo:bar"}}' | \
  SKILL_TRACKER_LOG_FILE=- python3 scripts/report_skill.py
```

## Querying in Prometheus

The metric is a gauge whose value is the **unix timestamp of the last
invocation** for the given label set. Useful queries:

```promql
# When was each (user, tool) pair last invoked?
agent_tool_invocation

# Tool calls in the last hour, by tool
count by (tool) (agent_tool_invocation > (time() - 3600))

# Skill usage per author
count by (author) (agent_tool_invocation{author!=""})

# Approximate invocation rate (gauge value changes mean a new invocation)
changes(agent_tool_invocation[5m])
```

The pushgateway accumulates series indefinitely. Configure a TTL or run
`pushgateway-cleanup` periodically to prune stale users.

## Using outside Claude Code / Copilot

The script is tool-agnostic: any agentic harness that can spawn a process
on a "tool used" event can drive it. Inputs are checked in order:

1. JSON on stdin in Claude Code / Copilot hook shape:
   `{"tool_name": "<name>", "tool_input": {...}}`
2. JSON on stdin in generic shape: `{"tool": "<name>"}` or `{"skill": "<name>"}`
3. Env var `TOOL_NAME` (or legacy `SKILL_NAME`)
4. `argv[1]`

```bash
# Direct CLI invocation:
PROMETHEUS_PUSHGATEWAY_URL=http://pushgateway:9091 \
  python3 scripts/report_skill.py my-skill-name
```

## Cross-platform notes

- The script uses only Python stdlib and `pathlib` — no shell calls, no
  `curl`/`jq` dependencies.
- User detection covers both POSIX (`USER`) and Windows (`USERNAME`).
- Hook command in `hooks/hooks.json` invokes `python` rather than `python3`,
  since Windows installations expose only `python.exe`. Ensure `python` on
  PATH points to Python 3.8+ (on Linux distros where `python` is missing,
  install `python-is-python3` or symlink).
- `${CLAUDE_PLUGIN_ROOT}` is expanded by both Claude Code and Copilot — no
  per-platform shell branching is needed in the hook config.

## Files

```
prometheus-skill-tracker/
├── .claude-plugin/
│   └── plugin.json
├── hooks/
│   └── hooks.json
├── scripts/
│   └── report_skill.py
└── README.md
```

## License

MIT (matching the parent marketplace).
