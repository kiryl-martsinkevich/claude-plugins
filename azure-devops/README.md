# Azure DevOps Plugin for Claude Code

Manage Azure DevOps pull requests and builds using the ADO REST API with PAT authentication.

## Prerequisites

- **Azure DevOps PAT** — Set the `ADO_PAT` environment variable with a Personal Access Token
  - Required scopes: **Code (Read & Write)**, **Build (Read & Execute)**
- **Git repository** — The plugin auto-detects organization, project, and repo from the git remote URL

```bash
export ADO_PAT="your-personal-access-token"
```

## Commands

| Command | Description |
|---------|-------------|
| `/azure-devops:create-pr` | Create a PR from the current branch |
| `/azure-devops:pr-status` | Check PR status, reviewers, and linked builds |
| `/azure-devops:review-pr` | Review a PR — fetch changes, analyze code, post comments, vote |
| `/azure-devops:check-build` | Diagnose why a build failed and classify as transient or code issue |
| `/azure-devops:rerun-pipeline` | Re-run a pipeline to resolve transient failures |

## Skill

The `ado-operations` skill activates automatically when discussing Azure DevOps PRs, builds, or pipelines. It provides REST API knowledge so Claude can perform ad-hoc ADO operations beyond the predefined commands.

## Installation

```bash
claude --plugin-dir /path/to/azure-devops
```
