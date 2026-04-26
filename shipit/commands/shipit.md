---
name: shipit
description: Ship an ADO work item end-to-end — clarify, plan, implement (TDD), branch, push, PR, monitor build until green, post summary
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - Skill
  - Agent
  - AskUserQuestion
  - TodoWrite
argument-hint: "<ADO-workitem-id>"
---

Invoke the `shipit` skill to ship the change requested in ADO work item `$ARGUMENTS`. Follow the skill's workflow exactly — do not skip steps. If `$ARGUMENTS` is empty, ask the user for the work item ID before proceeding.
