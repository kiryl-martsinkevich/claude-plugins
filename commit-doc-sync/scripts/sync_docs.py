#!/usr/bin/env python3
"""PostToolUse hook: after a successful git commit, review the diff and
amend CLAUDE.md / README.md if the code change warrants it.

Cross-platform (Linux/macOS/Windows). Stdlib only — no dependencies.

Configuration:
    COMMIT_DOC_AGENT_CMD    Agent command to spawn. Default: claude -p.
                            The prompt is appended as the final argument.
    COMMIT_DOC_SYNC_DISABLE  Set to 1 to disable the hook entirely.

Exit 0 on every path — never blocks the session.
"""
from __future__ import annotations

import fnmatch
import json
import os
import shlex
import subprocess
import sys
from pathlib import PurePosixPath

_DISABLE_ENV = "COMMIT_DOC_SYNC_DISABLE"
_AGENT_CMD_ENV = "COMMIT_DOC_AGENT_CMD"
_DEFAULT_AGENT_CMD = "claude -p"
_AGENT_TIMEOUT = 50  # seconds; hook timeout is 60, leave headroom
_MAX_DIFF_BYTES = 50_000  # cap diff size to keep the sub-agent prompt manageable

# Patterns that, if they cover *all* files in a commit, suppress the agent.
# Uses fnmatch against the full relative path (forward slashes).
_SKIP_PATTERNS = (
    # Docs
    "*.md", "*.mdx", "*.rst", "*.txt",
    # Tests — Python / JS / TS / Go
    "**/test_*.py", "**/*_test.go", "**/*.test.*", "**/*.spec.*",
    "tests/**", "__tests__/**", "**/__tests__/**",
    # Tests — Java / Scala
    "**/*Test.java", "**/*Tests.java", "**/*IT.java",
    "**/*Test.scala", "**/*Spec.scala",
    "src/test/**",
    # Lockfiles
    "*.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.lock", "poetry.lock", "uv.lock", "Pipfile.lock",
    # Repo dotfiles
    ".gitignore", ".gitattributes", ".editorconfig",
    # Build / generated
    "dist/**", "build/**", "out/**", "node_modules/**",
    "__pycache__/**", ".next/**", "target/**", ".gradle/**",
    # JVM IDE / tooling
    ".idea/**", "*.iml", ".bsp/**", ".metals/**", ".bloop/**",
)


def read_stdin() -> str:
    if sys.stdin is None or sys.stdin.closed:
        return ""
    try:
        return sys.stdin.read()
    except (OSError, ValueError):
        return ""


def is_git_commit_command(cmd: str) -> bool:
    """True if *cmd* is a `git commit` that is NOT an amend."""
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        return False
    if len(tokens) < 2:
        return False
    if tokens[0] != "git":
        return False
    # Must contain "commit"
    if "commit" not in tokens:
        return False
    # Must NOT contain "--amend"
    if "--amend" in tokens:
        return False
    return True


def exit_code_from_result(result: object) -> int | None:
    """Extract exit code from tool_result, handling both naming conventions."""
    if not isinstance(result, dict):
        return None
    for key in ("exitCode", "exit_code", "returncode", "return_code"):
        val = result.get(key)
        if isinstance(val, int):
            return val
    return None


def get_changed_files(cwd: str) -> list[str]:
    """Return list of files changed in HEAD, or empty list on failure."""
    try:
        proc = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    if proc.returncode == 0 and proc.stdout.strip():
        return [f for f in proc.stdout.strip().split("\n") if f]
    # Possibly an initial commit (no parent). Fall back to `git show`.
    try:
        proc2 = subprocess.run(
            ["git", "show", "--name-only", "--format=", "HEAD"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    return [f for f in proc2.stdout.strip().split("\n") if f]


def is_skippable(file_path: str) -> bool:
    """True if *file_path* matches any skiplist pattern."""
    pp = PurePosixPath(file_path)
    for pattern in _SKIP_PATTERNS:
        if fnmatch.fnmatchcase(file_path, pattern):
            return True
        # Also match against just the filename for patterns without path separators
        if "/" not in pattern and fnmatch.fnmatchcase(pp.name, pattern):
            return True
    return False


def get_head_sha(cwd: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        )
        return proc.stdout.strip()[:12] if proc.returncode == 0 else "HEAD"
    except (subprocess.TimeoutExpired, OSError):
        return "HEAD"


def get_diff(cwd: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "show", "HEAD"],
            capture_output=True, text=True, cwd=cwd, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return "(could not retrieve diff)"
    if proc.returncode != 0:
        return "(could not retrieve diff)"
    diff = proc.stdout
    if len(diff.encode("utf-8", errors="replace")) > _MAX_DIFF_BYTES:
        diff = diff[:_MAX_DIFF_BYTES] + "\n\n[... diff truncated ...]"
    return diff


def build_prompt(head_sha: str, diff: str) -> str:
    return (
        "You just helped commit changes to a git repository. "
        "Review the commit's diff and decide whether CLAUDE.md or README.md "
        "(at the repo root, or any directly relevant nested ones) need "
        "updating to reflect the change.\n\n"
        "- If yes: edit them. Make minimal, accurate changes.\n"
        "- If no: do nothing. Don't create files. Don't reformat.\n\n"
        f"Commit SHA: {head_sha}\n\n"
        f"Diff:\n{diff}\n\n"
        "When done, exit. Do NOT run any git commands yourself."
    )


def spawn_agent(agent_cmd: str, prompt: str, cwd: str) -> bool:
    """Spawn the configured agent. Returns True if it ran without error."""
    try:
        argv = shlex.split(agent_cmd)
    except ValueError:
        print(f"commit-doc-sync: failed to parse AGENT_CMD: {agent_cmd!r}", file=sys.stderr)
        return False
    argv.append(prompt)
    try:
        subprocess.run(
            argv, cwd=cwd, timeout=_AGENT_TIMEOUT,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"commit-doc-sync: agent failed: {exc}", file=sys.stderr)
        return False
    return True


def has_working_changes(cwd: str) -> bool:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        )
        return proc.stdout.strip() != ""
    except (subprocess.TimeoutExpired, OSError):
        return False


def amend_commit(cwd: str) -> bool:
    """Stage all changes and amend the commit. Returns True on success."""
    try:
        subprocess.run(
            ["git", "add", "-A"], cwd=cwd, timeout=10,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "--amend", "--no-edit"],
            cwd=cwd, timeout=10,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        print(f"commit-doc-sync: amend failed: {exc}", file=sys.stderr)
        return False
    return True


def main() -> int:
    if os.environ.get(_DISABLE_ENV, "").strip() == "1":
        return 0

    payload_text = read_stdin()
    if not payload_text.strip():
        return 0

    try:
        payload = json.loads(payload_text)
    except (ValueError, TypeError):
        return 0
    if not isinstance(payload, dict):
        return 0

    # --- 1. Pre-checks -------------------------------------------------
    if payload.get("tool_name") != "Bash":
        return 0

    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str) or not command:
        return 0
    if not is_git_commit_command(command):
        return 0

    tool_result = payload.get("tool_result") or {}
    exit_code = exit_code_from_result(tool_result)
    if exit_code is None or exit_code != 0:
        return 0

    cwd = payload.get("cwd", "") or os.getcwd()

    # --- 2. Heuristic gate ----------------------------------------------
    files = get_changed_files(cwd)
    if not files:
        return 0
    interesting = [f for f in files if not is_skippable(f)]
    if not interesting:
        return 0

    # --- 3. Sub-agent ---------------------------------------------------
    agent_cmd = os.environ.get(_AGENT_CMD_ENV, "").strip() or _DEFAULT_AGENT_CMD
    head_sha = get_head_sha(cwd)
    diff = get_diff(cwd)
    prompt = build_prompt(head_sha, diff)

    if not spawn_agent(agent_cmd, prompt, cwd):
        return 0

    # --- 4. Amend if changed --------------------------------------------
    if has_working_changes(cwd):
        amend_commit(cwd)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
