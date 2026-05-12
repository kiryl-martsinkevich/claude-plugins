# prometheus-skill-tracker

A telemetry hook that reports every tool/skill invocation to a Prometheus
Pushgateway and/or a JSONL log file. Pure Python, standard library only, no
third-party dependencies; runs on Windows, Linux, and macOS.

The hook fires once per tool call. For Claude Code's `Skill` tool the
recorded label is the actual skill name (e.g.
`plugin-dev:hook-development`), not the literal string `Skill`. For every
other tool the tool name itself is recorded.

## Tool compatibility

| Tool | Hook surface | Install path |
|---|---|---|
| **Claude Code** | `PreToolUse` (native) | `/plugin install` — the bundled `hooks/hooks.json` wires up automatically. |
| **VS Code Copilot Chat** | `PreToolUse` (Claude-format) — reads `.claude/settings.json` and `.claude-plugin/plugin.json`, expands `${CLAUDE_PLUGIN_ROOT}`. | Add this marketplace to `chat.plugins.marketplaces` **or** point `chat.pluginLocations` at a local checkout. |
| **GitHub Copilot CLI** (`copilot`) | `PreToolUse` (VS-Code-compat alias) **or** native `preToolUse` (camelCase) — the script accepts both payload shapes. | `copilot plugin install` from a registered marketplace, **or** drop `hooks/hooks.json` into `~/.copilot/hooks/` and replace `${CLAUDE_PLUGIN_ROOT}` with the absolute path to your checkout (`${CLAUDE_PLUGIN_ROOT}` expansion isn't documented for the CLI). |
| **opencode** | `tool.execute.before` (JS plugin shim — opencode has no external-command hook surface) | Copy `opencode/skill-tracker.js` to `~/.config/opencode/plugins/` (global) or `.opencode/plugins/` (per-project) and set `SKILL_TRACKER_SCRIPT` to the absolute path of `scripts/report_skill.py`. |
| **GitHub Copilot in IntelliJ / JetBrains** | None as of May 2026 — GitHub's hooks surface is documented only for the cloud agent + the Copilot CLI; JetBrains exposes no per-tool-call event. | **Not supported.** Workaround: front Copilot's MCP servers with a proxy that calls `scripts/report_skill.py` per request. The plugin format won't auto-install here. |

The same Python script handles all four supported surfaces — the only
per-tool variation is how the script is wired up.

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

```bash
/plugin install prometheus-skill-tracker@claude-plugins
export PROMETHEUS_PUSHGATEWAY_URL=http://pushgateway.example.com:9091
```

The plugin's `hooks/hooks.json` registers the `PreToolUse` hook on the `*`
matcher and resolves `${CLAUDE_PLUGIN_ROOT}` automatically.

### VS Code Copilot Chat

VS Code Copilot Chat reads Claude-format hooks directly. Either:

- Add the marketplace to `chat.plugins.marketplaces` (VS Code settings) and
  install from the plugin picker, **or**
- Point `chat.pluginLocations` at a local checkout.

Then set `PROMETHEUS_PUSHGATEWAY_URL` in your shell. The same
`hooks/hooks.json` and `${CLAUDE_PLUGIN_ROOT}` expansion that Claude Code
uses works here too.

> Copilot has no `Skill` tool, so skill loads are invisible to
> `PreToolUse`. All other tool calls (Bash, Read, Edit, …, MCP calls) fire
> as expected.

### GitHub Copilot CLI

If you've registered this plugin's marketplace with the CLI:

```bash
copilot plugin install prometheus-skill-tracker
export PROMETHEUS_PUSHGATEWAY_URL=http://pushgateway.example.com:9091
```

If `${CLAUDE_PLUGIN_ROOT}` expansion doesn't apply at your CLI version,
register the hook directly instead:

```bash
mkdir -p ~/.copilot/hooks
cat > ~/.copilot/hooks/skill-tracker.json <<JSON
{
  "PreToolUse": [{
    "matcher": "*",
    "hooks": [{
      "type": "command",
      "command": "python /absolute/path/to/prometheus-skill-tracker/scripts/report_skill.py",
      "timeout": 10
    }]
  }]
}
JSON
```

The CLI sends snake_case payloads (`tool_name` / `tool_input`) when the
event is named `PreToolUse` and camelCase (`toolName` / `toolArgs`) when
the event is named `preToolUse`. The script accepts both — pick whichever
you prefer.

### opencode

opencode has no external-command hook surface, so we ship a JS plugin shim
that calls `report_skill.py` from `tool.execute.before`:

```bash
mkdir -p ~/.config/opencode/plugins
cp /path/to/prometheus-skill-tracker/opencode/skill-tracker.js \
   ~/.config/opencode/plugins/

export SKILL_TRACKER_SCRIPT=/path/to/prometheus-skill-tracker/scripts/report_skill.py
export PROMETHEUS_PUSHGATEWAY_URL=http://pushgateway.example.com:9091
```

The shim auto-detects `python3` / `python` on PATH (override with `PYTHON`)
and will try to locate the script under `~/.claude/plugins/marketplaces/`
and `~/.copilot/installed-plugins/` if `SKILL_TRACKER_SCRIPT` is unset.

### JetBrains (gap)

The GitHub Copilot JetBrains plugin does not expose tool-call hooks or a
machine-readable per-tool event stream (verified against GitHub Copilot
docs and the JetBrains plugin pages, May 2026). If you need coverage
there, the practical options are:

- Add an MCP proxy: configure Copilot to call your MCP servers through a
  middleware that pipes each request to `scripts/report_skill.py` via the
  generic `{"tool": "..."}` stdin shape.
- Watch the IntelliJ Copilot diagnostic log (`idea.log` with debug
  logging enabled) and grep for tool-call lines — fragile, not a stable
  contract.
- Wait for GitHub to extend hooks beyond the cloud-agent + CLI surface.

This plugin does not solve the JetBrains gap; the script can be driven by
any of the above approaches because it accepts stdin / env / argv input.

### Testing without a pushgateway

```bash
export SKILL_TRACKER_LOG_FILE=/tmp/agent-tools.jsonl
# ...use Claude Code / Copilot / opencode normally...
tail -f /tmp/agent-tools.jsonl
```

Use `SKILL_TRACKER_LOG_FILE=-` to log to stderr (handy with `claude
--debug`). When both `PROMETHEUS_PUSHGATEWAY_URL` and
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
| `COPILOT_HOME` | no | `~/.copilot` | Override the directory containing `installed-plugins/<marketplace>/<plugin>/` for Copilot CLI marketplace/author resolution. |
| `SKILL_TRACKER_SCRIPT` | opencode only | (auto-probe) | Absolute path to `report_skill.py`. The opencode shim uses this; falls back to probing Claude Code / Copilot CLI install dirs. |
| `PYTHON` | opencode only | auto (`python3` then `python`) | Python interpreter the opencode shim should invoke. |

If neither `PROMETHEUS_PUSHGATEWAY_URL` nor `SKILL_TRACKER_LOG_FILE` is set,
the hook silently exits 0 (does nothing).

## Labels

| Label | Source |
|---|---|
| `user` | `BANKID` → `PSID` → `USER` → `USERNAME` → `"unknown"`, or `"anon"` if `SKILL_TRACKER_ANONYMOUS` is truthy. |
| `tool` | The skill name (for Claude Code's `Skill` tool — read from `tool_input.skill`/`tool_input.name`) or the tool name otherwise. Both snake_case (`tool_name`) and camelCase (`toolName`) payloads are accepted. |
| `marketplace` | First checked against `~/.claude/plugins/installed_plugins.json` (keys like `<plugin>@<marketplace>`), then against `~/.copilot/installed-plugins/<marketplace>/<plugin>/`. `"user"` for non-namespaced names; `"unknown"` if the plugin isn't discoverable. Overridable via `SKILL_TRACKER_MARKETPLACE`. |
| `author` | Read from the discovered plugin's manifest — searches `.claude-plugin/plugin.json`, `.plugin/plugin.json`, `plugin.json`, and `.github/plugin/plugin.json` in that order. Supports both string and `{name: ...}` object shapes. Empty when not discoverable. |

## JSONL log entry shape

```json
{"action":"push","author":"Anthropic","iso_time":"2026-05-04T12:41:18Z","marketplace":"claude-plugins-official","tool":"plugin-dev:hook-development","ts":1777898478,"user":"kiryl"}
```

`action` is one of:

- `push` — `PROMETHEUS_PUSHGATEWAY_URL` is set, the metric was sent.
- `log_only` — only `SKILL_TRACKER_LOG_FILE` is set, no push attempted.
- `skip` — matched an entry in `SKILL_TRACKER_EXCLUDE_TOOLS`. Logged so
  you can see the exclusion patterns in action; useful for tuning the
  filter.

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

**One-shot ad-hoc smoke test (Claude Code payload):**
```bash
echo '{"tool_name":"Skill","tool_input":{"skill":"foo:bar"}}' | \
  SKILL_TRACKER_LOG_FILE=- python3 scripts/report_skill.py
```

**One-shot ad-hoc smoke test (Copilot CLI camelCase payload):**
```bash
echo '{"toolName":"foo:bar","toolArgs":{}}' | \
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

## Using outside the four supported tools

The script is tool-agnostic: any agentic harness that can spawn a process
on a "tool used" event can drive it. Inputs are checked in order:

1. JSON on stdin in Claude Code / VS Code Copilot Chat / Copilot CLI
   (VS-Code-compat) shape: `{"tool_name": "<name>", "tool_input": {...}}`
2. JSON on stdin in Copilot CLI native shape:
   `{"toolName": "<name>", "toolArgs": {...}}`
3. JSON on stdin in generic shape: `{"tool": "<name>"}` or `{"skill": "<name>"}`
4. Env var `TOOL_NAME` (or legacy `SKILL_NAME`)
5. `argv[1]`

```bash
# Direct CLI invocation:
PROMETHEUS_PUSHGATEWAY_URL=http://pushgateway:9091 \
  python3 scripts/report_skill.py my-skill-name
```

## Cross-platform notes

- The Python script uses only stdlib and `pathlib` — no shell calls, no
  `curl`/`jq` dependencies.
- User detection covers both POSIX (`USER`) and Windows (`USERNAME`).
- The hook command in `hooks/hooks.json` invokes `python` rather than
  `python3` since Windows installations expose only `python.exe`. Ensure
  `python` on PATH points to Python 3.8+; on Linux distros where it's
  missing, install `python-is-python3` or symlink.
- `${CLAUDE_PLUGIN_ROOT}` is expanded by Claude Code and VS Code Copilot
  Chat but not documented for the Copilot CLI — for the CLI either use
  the plugin-install path (auto-resolved) or substitute an absolute path
  in your `~/.copilot/hooks/skill-tracker.json`.
- The opencode shim picks `python3` first on POSIX, `python` first on
  Windows; override with `PYTHON=/path/to/interpreter`.

## Files

```
prometheus-skill-tracker/
├── .claude-plugin/
│   └── plugin.json
├── hooks/
│   └── hooks.json
├── opencode/
│   └── skill-tracker.js
├── scripts/
│   └── report_skill.py
└── README.md
```

## License

MIT (matching the parent marketplace).
