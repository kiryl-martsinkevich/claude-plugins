# commit-doc-sync

After Claude makes a `git commit`, this plugin launches a sub-agent to review the diff and update `CLAUDE.md` / `README.md` if the code change warrants it. The edit is amended into the same commit — clean history, no follow-ups.

## How it works

1. **Gate:** Only triggers on successful `git commit` (not `--amend`).
2. **Heuristic:** Skips commits made entirely of docs, tests, lockfiles, generated files, or IDE config. If any "interesting" file survives, proceeds.
3. **Sub-agent:** Spawns the configured agent command with the commit diff, asking it to decide whether docs need updating.
4. **Amend:** If the sub-agent edits files, stages them and runs `git commit --amend --no-edit`.

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `COMMIT_DOC_AGENT_CMD` | `claude -p` | Command to spawn as sub-agent. Prompt is appended as final argument. |
| `COMMIT_DOC_SYNC_DISABLE` | (unset) | Set to `1` to disable. |

## Skiplist

The heuristic ignores files matching these patterns:

- Docs: `*.md`, `*.mdx`, `*.rst`, `*.txt`
- Tests: `test_*.py`, `*_test.go`, `*.test.*`, `*.spec.*`, `*Test.java`, `*Spec.scala`, `tests/**`, `__tests__/**`, `src/test/**`
- Lockfiles: `*.lock`, `package-lock.json`, `yarn.lock`, `Cargo.lock`, etc.
- Dotfiles: `.gitignore`, `.gitattributes`, `.editorconfig`
- Build/output: `dist/**`, `build/**`, `out/**`, `target/**`, `.gradle/**`, `.next/**`, `node_modules/**`, `__pycache__/**`
- IDE: `.idea/**`, `*.iml`, `.bsp/**`, `.metals/**`, `.bloop/**`

If no files survive the skiplist, the hook exits silently.
