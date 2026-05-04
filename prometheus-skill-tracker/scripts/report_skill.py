#!/usr/bin/env python3
"""Report a tool/skill invocation to a Prometheus Pushgateway.

Cross-platform (Windows/Linux/macOS). Tool-agnostic: usable with any agentic
harness (Claude Code, Copilot, ...) that can spawn a process on a tool-use
event. Standard library only - no third-party dependencies.

Inputs (checked in order):
    1. JSON on stdin in Claude Code / Copilot hook shape:
         {"tool_name": "<name>", "tool_input": {...}}
       For tool_name == "Skill" the actual skill name is taken from
       tool_input.skill (falls back to tool_input.name); for any other
       tool_name the value of tool_name itself is used.
    2. JSON on stdin in generic shape: {"tool": "<name>"} or {"skill": "<name>"}
    3. Env var TOOL_NAME (or legacy SKILL_NAME)
    4. argv[1]

Configuration:
    PROMETHEUS_PUSHGATEWAY_URL  Base URL of the pushgateway (e.g.
                                http://pushgateway:9091). Optional; if unset
                                no push is performed.
    SKILL_TRACKER_LOG_FILE      If set, every (non-empty) invocation also
                                writes a single JSONL line to this path -
                                useful for testing without a pushgateway.
                                Use "-" to log to stderr. Tilde and
                                ${VAR} are expanded.
    SKILL_TRACKER_EXCLUDE_TOOLS Comma-separated fnmatch patterns of tool
                                names to skip (default: noisy built-ins
                                like Bash, Read, Write, Edit, Glob, Grep,
                                LS, Notebook*, Todo*, Task*, BashOutput,
                                KillShell, ToolSearch). Patterns match
                                the resolved tool name (i.e. for the Skill
                                tool, the skill name - so e.g. "Skill"
                                in the list will NOT exclude individual
                                skill invocations). Skipped invocations
                                are still recorded in the log file with
                                action="skip" so you can verify your
                                patterns.
    SKILL_TRACKER_MARKETPLACE   Override the marketplace label (otherwise
                                derived from Claude Code's installed
                                plugin index).

If neither PROMETHEUS_PUSHGATEWAY_URL nor SKILL_TRACKER_LOG_FILE is set,
the script silently exits 0 (the hook does nothing).

User identity (first non-empty wins):
    BANKID -> PSID -> USER -> USERNAME -> "unknown"

If SKILL_TRACKER_ANONYMOUS is truthy ("1"/"true"/"yes"/"on", case-insensitive)
the resolved user is replaced with the literal "anon" everywhere it lands
(both the prometheus label and the pushgateway URL path).

Marketplace and author lookup is best-effort:
    - For "<plugin>:<skill>" namespaced names, parses
      ~/.claude/plugins/installed_plugins.json (override location with
      CLAUDE_CONFIG_DIR) whose plugin keys are "<plugin>@<marketplace>".
      The matching entry's installPath is then read for author info from
      <installPath>/.claude-plugin/plugin.json (supports both string and
      {name: ...} object forms of the author field).
    - Non-namespaced names default to marketplace="user", author="".
    - Lookup failure -> marketplace="unknown", author="".

Emits a Prometheus gauge whose value is the unix timestamp of the
invocation:

    agent_tool_invocation{user="...",tool="...",marketplace="...",author="..."} <ts>

Exits 0 on every code path so the hook never blocks the host tool.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import quote

URL_ENV = "PROMETHEUS_PUSHGATEWAY_URL"
LOG_FILE_ENV = "SKILL_TRACKER_LOG_FILE"
EXCLUDE_ENV = "SKILL_TRACKER_EXCLUDE_TOOLS"
MARKETPLACE_OVERRIDE_ENV = "SKILL_TRACKER_MARKETPLACE"
ANONYMOUS_ENV = "SKILL_TRACKER_ANONYMOUS"
ANONYMOUS_USER = "anon"
TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})
JOB_NAME = "agent_tool_tracker"
HTTP_TIMEOUT_SECONDS = 3.0

DEFAULT_EXCLUDE_PATTERNS = (
    "Bash",
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "LS",
    "Notebook*",
    "Todo*",
    "Task*",
    "BashOutput",
    "KillShell",
    "ToolSearch",
)

_LABEL_TRANSLATION = str.maketrans({"\\": r"\\", '"': r"\"", "\n": r"\n"})
_PATH_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]")


def read_stdin() -> str:
    if sys.stdin is None or sys.stdin.closed:
        return ""
    try:
        return sys.stdin.read()
    except (OSError, ValueError):
        return ""


def extract_tool_from_payload(payload: object) -> Optional[str]:
    if not isinstance(payload, dict):
        return None

    tool_name = payload.get("tool_name")
    if isinstance(tool_name, str) and tool_name:
        if tool_name == "Skill":
            tool_input = payload.get("tool_input") or {}
            if isinstance(tool_input, dict):
                value = tool_input.get("skill") or tool_input.get("name")
                if isinstance(value, str) and value:
                    return value
        return tool_name

    for key in ("tool", "skill", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def resolve_tool_name(stdin_text: str, argv: list) -> Optional[str]:
    text = stdin_text.strip()
    if text:
        try:
            payload = json.loads(text)
        except ValueError:
            payload = None
        if payload is not None:
            name = extract_tool_from_payload(payload)
            if name:
                return name

    for env_key in ("TOOL_NAME", "SKILL_NAME"):
        name = os.environ.get(env_key, "").strip()
        if name:
            return name

    if len(argv) > 1 and argv[1].strip():
        return argv[1].strip()

    return None


def load_exclude_patterns() -> list:
    raw = os.environ.get(EXCLUDE_ENV)
    if raw is None:
        return list(DEFAULT_EXCLUDE_PATTERNS)
    return [p.strip() for p in raw.split(",") if p.strip()]


def is_excluded(tool: str, patterns: list) -> bool:
    return any(fnmatch.fnmatchcase(tool, pattern) for pattern in patterns)


def is_anonymous() -> bool:
    return os.environ.get(ANONYMOUS_ENV, "").strip().lower() in TRUTHY_VALUES


def resolve_user() -> str:
    if is_anonymous():
        return ANONYMOUS_USER
    for var in ("BANKID", "PSID", "USER", "USERNAME"):
        value = os.environ.get(var)
        if value:
            return value
    return "unknown"


def _read_plugin_author(install_path: str) -> str:
    try:
        manifest = Path(install_path) / ".claude-plugin" / "plugin.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    author = data.get("author")
    if isinstance(author, str):
        return author.strip()
    if isinstance(author, dict):
        name = author.get("name")
        if isinstance(name, str):
            return name.strip()
    return ""


def resolve_plugin_info(tool_name: str) -> tuple:
    """Return (marketplace, author) for the given tool/skill name."""
    override = os.environ.get(MARKETPLACE_OVERRIDE_ENV, "").strip()

    if ":" not in tool_name:
        return (override or "user", "")
    plugin = tool_name.split(":", 1)[0]
    if not plugin:
        return (override or "user", "")

    config_dir = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    base_dir = Path(config_dir) if config_dir else Path.home() / ".claude"
    installed = base_dir / "plugins" / "installed_plugins.json"

    try:
        data = json.loads(installed.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return (override or "unknown", "")

    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, dict):
        return (override or "unknown", "")

    prefix = plugin + "@"
    marketplace = "unknown"
    install_path = ""
    for key, entries in plugins.items():
        if not (isinstance(key, str) and key.startswith(prefix)):
            continue
        marketplace = key[len(prefix):]
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    ip = entry.get("installPath")
                    if isinstance(ip, str) and ip:
                        install_path = ip
                        break
        break

    author = _read_plugin_author(install_path) if install_path else ""
    return (override or marketplace, author)


def escape_label(value: str) -> str:
    return value.translate(_LABEL_TRANSLATION)


def safe_path_segment(value: str) -> str:
    sanitized = _PATH_UNSAFE.sub("_", value)
    return sanitized or "unknown"


def build_metric_body(user: str, tool: str, marketplace: str, author: str, ts: int) -> str:
    return (
        "# TYPE agent_tool_invocation gauge\n"
        "# HELP agent_tool_invocation Unix timestamp of last tool invocation\n"
        f'agent_tool_invocation{{user="{escape_label(user)}",'
        f'tool="{escape_label(tool)}",'
        f'marketplace="{escape_label(marketplace)}",'
        f'author="{escape_label(author)}"}} {ts}\n'
    )


def write_log_line(log_target: str, entry: dict) -> None:
    line = json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
    if log_target == "-":
        try:
            sys.stderr.write(line)
            sys.stderr.flush()
        except (OSError, ValueError):
            pass
        return
    expanded = os.path.expanduser(os.path.expandvars(log_target))
    try:
        with open(expanded, "a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass


def push(url: str, user: str, body: str) -> None:
    base = url.rstrip("/")
    user_segment = quote(safe_path_segment(user), safe="")
    push_url = f"{base}/metrics/job/{JOB_NAME}/user/{user_segment}"
    request = urlrequest.Request(
        push_url,
        data=body.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "text/plain; version=0.0.4"},
    )
    try:
        response = urlrequest.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS)
    except (urlerror.URLError, OSError, ValueError):
        return
    try:
        response.close()
    except OSError:
        pass


def main(argv: list) -> int:
    url = os.environ.get(URL_ENV, "").strip()
    log_target = os.environ.get(LOG_FILE_ENV, "").strip()
    if not url and not log_target:
        return 0

    tool = resolve_tool_name(read_stdin(), argv)
    if not tool:
        return 0

    user = resolve_user()
    marketplace, author = resolve_plugin_info(tool)
    ts = int(time.time())
    excluded = is_excluded(tool, load_exclude_patterns())

    if log_target:
        action = "skip" if excluded else ("push" if url else "log_only")
        write_log_line(log_target, {
            "ts": ts,
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
            "tool": tool,
            "user": user,
            "marketplace": marketplace,
            "author": author,
            "action": action,
        })

    if not excluded and url:
        body = build_metric_body(user, tool, marketplace, author, ts)
        push(url, user, body)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:
        sys.exit(0)
