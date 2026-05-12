// prometheus-skill-tracker - opencode plugin shim
//
// opencode has no PreToolUse external-command hook; plugins are JS/TS modules
// loaded from .opencode/plugins/ (project-local) or ~/.config/opencode/plugins/
// (global). This shim listens on tool.execute.before and forwards every call
// to scripts/report_skill.py, which speaks the same JSON contract as the
// Claude Code / Copilot CLI hooks.
//
// Install:
//   cp /path/to/prometheus-skill-tracker/opencode/skill-tracker.js \
//      ~/.config/opencode/plugins/
//   export SKILL_TRACKER_SCRIPT=/path/to/prometheus-skill-tracker/scripts/report_skill.py
//   export PROMETHEUS_PUSHGATEWAY_URL=...   # or SKILL_TRACKER_LOG_FILE=...
//
// If SKILL_TRACKER_SCRIPT is unset, the shim probes the standard install
// locations Claude Code and Copilot CLI use.

import { spawn, spawnSync } from "node:child_process"
import { existsSync, readdirSync } from "node:fs"
import { homedir, platform } from "node:os"
import { join } from "node:path"

const PLUGIN_NAME = "prometheus-skill-tracker"

function resolvePython() {
  if (process.env.PYTHON) return process.env.PYTHON
  // Windows installs Python as `python.exe`; everywhere else `python3` is the
  // safer default (`python` is often missing on modern Linux distros).
  const order = platform() === "win32" ? ["python", "python3"] : ["python3", "python"]
  for (const cmd of order) {
    try {
      const probe = spawnSync(cmd, ["-c", "import sys"], { stdio: "ignore" })
      if (probe.status === 0) return cmd
    } catch (_) {}
  }
  return order[0]
}

const PYTHON = resolvePython()

function collectFromMarketplaces(root) {
  if (!existsSync(root)) return []
  try {
    return readdirSync(root).map((mp) =>
      join(root, mp, PLUGIN_NAME, "scripts", "report_skill.py")
    )
  } catch (_) {
    return []
  }
}

function locateScript() {
  const explicit = process.env.SKILL_TRACKER_SCRIPT
  if (explicit && existsSync(explicit)) return explicit

  const home = homedir()
  const candidates = [
    ...collectFromMarketplaces(join(home, ".claude", "plugins", "marketplaces")),
    ...collectFromMarketplaces(
      join(process.env.COPILOT_HOME || join(home, ".copilot"), "installed-plugins")
    ),
  ]
  return candidates.find(existsSync) ?? null
}

const SCRIPT = locateScript()

export const PrometheusSkillTracker = async () => {
  return {
    "tool.execute.before": async (input, output) => {
      if (!SCRIPT) return
      if (!process.env.PROMETHEUS_PUSHGATEWAY_URL && !process.env.SKILL_TRACKER_LOG_FILE) return

      const toolName = input && typeof input.tool === "string" ? input.tool : null
      if (!toolName) return

      const payload = JSON.stringify({
        tool_name: toolName,
        tool_input: output && output.args ? output.args : {},
      })

      try {
        const child = spawn(PYTHON, [SCRIPT], {
          stdio: ["pipe", "ignore", "ignore"],
          env: process.env,
        })
        child.on("error", () => {})
        child.stdin.on("error", () => {})
        child.stdin.end(payload)
      } catch (_) {
        // Telemetry must never block the host tool.
      }
    },
  }
}
