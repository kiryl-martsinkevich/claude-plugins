# commit-doc-sync — design

A Claude Code plugin that, after a Claude-made `git commit`, optionally launches a sub-agent to update `CLAUDE.md` / `README.md` and amends the commit with the result.

## Goals

- Keep top-level docs in sync with code changes without the user remembering to ask.
- Attach doc edits to the *same* commit (not a follow-up), so history stays clean.
- Stay out of the way: skip commits that don't plausibly affect docs; never block.
- Cross-platform (Linux/macOS/Windows-with-Git-Bash). Implementation in Python, stdlib only.

## Non-goals

- Updating non-Claude commits (terminal commits don't fire hooks — by design).
- Updating arbitrary docs trees. MVP targets root-level `CLAUDE.md` / `README.md` and any directly relevant nested ones the sub-agent finds.
- Generating new docs from scratch.

## Plugin layout

```
commit-doc-sync/
├── .claude-plugin/plugin.json
├── hooks/hooks.json
├── scripts/sync_docs.py
└── README.md
```

## Hook wiring

`PostToolUse` on `Bash`. The script reads the hook payload from stdin, fast-bails on anything that isn't a successful `git commit`, then runs the heuristic gate and (if it passes) the sub-agent.

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "python ${CLAUDE_PLUGIN_ROOT}/scripts/sync_docs.py",
        "timeout": 60
      }]
    }]
  }
}
```

## Configuration (env vars)

- `COMMIT_DOC_AGENT_CMD` — agent command to spawn. Default: `claude -p`. Whatever is set runs as `<cmd> "<prompt>"` (parsed with `shlex.split`, no shell).
- `COMMIT_DOC_SYNC_DISABLE=1` — kill switch.

## Behavior

### 1. Pre-checks (fast bail-out, no git calls)

- Hook payload `tool_name == "Bash"`.
- `tool_input.command` parses to a `git commit` invocation that is *not* `--amend`.
- `tool_response.exit_code == 0` (or the equivalent success signal in the payload).
- `COMMIT_DOC_SYNC_DISABLE` not set.

If any check fails: exit 0 silently.

### 2. Heuristic gate — file-type based skiplist

Get the just-committed file list:

```
git diff-tree --no-commit-id --name-only -r HEAD
```

Falls back to `git show --name-only --format=` for the initial commit case.

Drop files matching any of these glob patterns (using `fnmatch` / `PurePosixPath.match`):

- **Docs:** `*.md`, `*.mdx`, `*.rst`, `*.txt`
- **Tests (cross-language):**
  - Python/JS/TS/Go: `**/test_*.py`, `**/*_test.go`, `**/*.test.*`, `**/*.spec.*`, `tests/**`, `__tests__/**`, `**/__tests__/**`
  - Java/Scala: `**/*Test.java`, `**/*Tests.java`, `**/*IT.java`, `**/*Test.scala`, `**/*Spec.scala`, `src/test/**`
- **Lockfiles:** `*.lock`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `Cargo.lock`, `poetry.lock`, `uv.lock`, `Pipfile.lock`
- **Repo dotfiles:** `.gitignore`, `.gitattributes`, `.editorconfig`
- **Build / generated dirs:** `dist/**`, `build/**`, `out/**`, `node_modules/**`, `__pycache__/**`, `.next/**`, `target/**`, `.gradle/**`
- **JVM IDE/tooling:** `.idea/**`, `*.iml`, `.bsp/**`, `.metals/**`, `.bloop/**`

If any file *survives* the skiplist → trigger sub-agent. Else → exit 0 silently.

### 3. Sub-agent invocation

Build a prompt of roughly this shape:

```
You just helped commit changes to a git repository. Review the
commit's diff and decide whether CLAUDE.md or README.md (at the
repo root, or any directly relevant nested ones) need updating to
reflect the change.

- If yes: edit them. Make minimal, accurate changes.
- If no: do nothing. Don't create files. Don't reformat.

Commit SHA: <HEAD>
Diff:
<output of `git show HEAD`>

When done, exit. Do NOT run any git commands yourself.
```

Spawn `$COMMIT_DOC_AGENT_CMD` as a subprocess. Argv built with `shlex.split` (no `shell=True`). CWD set to the repo root. Timeout 50s (leaves 10s headroom under the hook's 60s).

### 4. Detect edits & amend

After the sub-agent returns, run `git status --porcelain`.

- **No changes** → exit 0. Sub-agent judged no update needed.
- **Changes** → `git add` the changed paths, then `git commit --amend --no-edit`. Exit 0.

The amend is a subprocess call from inside the hook, not a Claude `Bash` tool call, so it does *not* re-trigger `PostToolUse`. No recursion.

### 5. Failure handling

Sub-agent crashes, times out, or amend fails: log to stderr, exit 0. Never block the original commit. If the amend itself fails partway, leave the working tree dirty so the user sees it next turn — better than silently losing the doc edits.

## Open questions for implementation

- Exact JSON schema of the PostToolUse payload (the `tool_response.exit_code` field name, whether stdout/stderr are separate). Verify against an example payload before shipping.
- Whether to also handle `git commit -a` correctly (file list still comes from `git diff-tree HEAD`, so should be fine — confirm).
- Whether to skip merge commits (`git rev-parse --verify HEAD^2` succeeds). MVP: don't special-case; let the heuristic decide.
