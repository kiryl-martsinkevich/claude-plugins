# Shipit Plugin for Claude Code

End-to-end workflow that turns an Azure DevOps work item into a green, review-ready pull request — clarifying, planning, implementing under TDD, branching, pushing, and monitoring the PR build until it passes.

`shipit` is a pure orchestration plugin. It does not re-implement ADO REST calls, PR creation, or language-specific patterns. Instead, it delegates each step to the appropriate sub-skill or specialist sub-agent.

## What It Does

For a given ADO work item ID, the workflow runs seven steps:

1. **Fetch & clarify** — Read the work item (and any attached BRD). If requirements are ambiguous, run a brainstorming session.
2. **Post clarified requirements** — Write the resolved scope and acceptance criteria back to the work item as a comment.
3. **Plan** — Produce a phased implementation plan with a coverage target, post it to the work item.
4. **Implement (TDD)** — Dispatch a language-specific sub-agent that follows strict red → green → refactor and achieves **≥ 60 % line coverage** on changed code.
5. **Branch, commit, push, PR** — A separate DevOps sub-agent creates `feature/<id>_<short-description>`, commits as `ADO #<id>: <description>`, pushes, and opens a PR linked to the work item.
6. **Monitor the build** — Poll the PR pipeline; on failure, hand the failed-task log to the developer agent for a fix, hand the fix back to the DevOps agent, repeat until green.
7. **Wrap up** — Update `README.md` / `CLAUDE.md` only if the change requires it, then post a summary comment on the work item.

Hard caps prevent runaway loops: three implementation attempts, five build-fix iterations. The skill never bypasses tests, signed-commit policy, or branch protection, and never auto-merges.

## Prerequisites

| Requirement | Notes |
|---|---|
| `ADO_PAT` | Personal Access Token with **Work Items (R/W)**, **Code (R/W)**, **Build (R/E)** scopes |
| `ADO_ORG` | Azure DevOps organization name |
| `ADO_PROJECT` | Azure DevOps project name |
| Git repo with `origin` on Azure DevOps | The DevOps sub-agent auto-detects org/project/repo from the remote |
| `ado-workitems` plugin | Provides the work-item fetch / BRD-extraction skill |
| `azure-devops` plugin | Provides the PR / pipeline operations skill |
| `superpowers` plugin | Provides `brainstorming`, `writing-plans`, `test-driven-development`, `verification-before-completion` |

```bash
export ADO_PAT="your-personal-access-token"
export ADO_ORG="your-org"
export ADO_PROJECT="your-project"
```

## Commands

| Command | Description |
|---------|-------------|
| `/shipit <ADO-id>` | Run the full workflow for the given work item |

## Skill

The `shipit` skill activates automatically on phrases like "shipit", "ship it", "ship work item #12345", or "ship the change". It also fires when the slash command above is invoked.

## How Sub-Agents Are Picked

The implementation step inspects the repo to choose a specialist agent:

| Detected stack | Sub-agent |
|---|---|
| C# / .NET (`*.csproj`) | `jvm-languages:csharp-pro` |
| Java (`pom.xml`, `build.gradle`) | `jvm-languages:java-pro` |
| Scala (`build.sbt`) | `jvm-languages:scala-pro` |
| React / TypeScript frontend | `application-performance:frontend-developer` |
| Anything else | `general-purpose` |

The implementation agent is instructed to *only* edit files and run tests — it never touches git. The DevOps agent (separate) handles every git / PR / build-monitoring action.

## Installation

```bash
claude --plugin-dir /path/to/shipit
```

## Layout

```
shipit/
├── .claude-plugin/plugin.json
├── commands/
│   └── shipit.md                       # /shipit <ADO#>
└── skills/
    └── shipit/
        ├── SKILL.md                    # Workflow definition
        └── references/
            └── comment-template.md     # HTML scaffolds for ADO comments
```

## What This Plugin Deliberately Does NOT Do

- Does not invent ADO REST patterns — those live in the `ado-workitems` and `azure-devops` plugins.
- Does not write production code itself — the implementation sub-agent does.
- Does not commit or push — the DevOps sub-agent does.
- Does not merge or complete PRs. Human review is always required.
