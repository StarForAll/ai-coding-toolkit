#!/usr/bin/env python3
"""Patch OpenCode inject-subagent-context.js for strong-gate routing awareness."""

from __future__ import annotations

import argparse
from pathlib import Path

PATCH_MARKER = "// [workflow-embed-patch:opencode-subagent-gates]"

ROUTE_HELPER_BLOCK = """// [workflow-embed-patch:opencode-subagent-gates]
const PYTHON_CMD = process.platform === "win32" ? "python" : "python3"

function parseRouteStatus(taskStatusText) {
  if (typeof taskStatusText !== "string" || !taskStatusText.trim()) return null
  const lines = taskStatusText.split(/\\r?\\n/)
  const routeData = {}
  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line || !line.includes(":")) continue
    const idx = line.indexOf(":")
    const key = line.slice(0, idx).trim()
    const value = line.slice(idx + 1).trim()
    if (key === "Stage") routeData.stage = value
    else if (key === "Action") routeData.action = value
    else if (key === "Target" || key === "Target-Stage") routeData.target = value
    else if (key === "Reason") routeData.reason = value
    else if (key === "Stage-Status") routeData.status = value
    else if (key === "Blockers") routeData.blockers = value ? value.split(" | ").map(item => item.trim()).filter(Boolean) : []
    else if (key === "Warnings") routeData.warnings = value ? value.split(" | ").map(item => item.trim()).filter(Boolean) : []
  }
  return routeData
}

function shouldAllowTaskInjection(routeData, subagentType) {
  if (!routeData || typeof routeData !== "object") return false
  const action = typeof routeData.action === "string" ? routeData.action : ""
  const stage = typeof routeData.stage === "string" ? routeData.stage : ""
  const target = typeof routeData.target === "string" ? routeData.target : ""
  const allowedStages = new Set(["implementation", "check", "review-gate", "project-audit", "delivery"])

  if (action === "reenter" && target === "implementation") {
    return subagentType === "implement" || subagentType === "check"
  }
  if (action === "awaiting_confirmation" || action === "awaiting_confirmation_with_blockers") {
    return false
  }
  if (action === "blocked" || action === "repair_needed" || action === "recovery_needed" || action === "context_needed" || action === "embed_invalid") {
    return false
  }
  if (allowedStages.has(stage)) {
    if (stage === "implementation") {
      return subagentType === "implement" || subagentType === "check"
    }
    return subagentType === "check"
  }
  return subagentType === "research"
}

function loadRouteData(ctx, taskDir) {
  const routeScript = join(ctx.directory, ".trellis", "scripts", "workflow", "workflow-state.py")
  if (!existsSync(routeScript)) return null
  try {
    const output = execFileSync(PYTHON_CMD, [
      routeScript,
      "route",
      taskDir,
      "--project-root",
      ctx.directory,
    ], {
      cwd: ctx.directory,
      timeout: 5000,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
      env: process.env,
    })
    return parseRouteStatus(output)
  } catch {
    return null
  }
}

function buildBlockedSubagentPrompt(routeData, subagentType, originalPrompt) {
  const action = typeof routeData?.action === "string" && routeData.action.trim()
    ? routeData.action.trim()
    : "unknown"
  const stage = typeof routeData?.stage === "string" && routeData.stage.trim()
    ? routeData.stage.trim()
    : "unknown"
  const target = typeof routeData?.target === "string" && routeData.target.trim()
    ? routeData.target.trim()
    : "unknown"
  const reason = typeof routeData?.reason === "string" && routeData.reason.trim()
    ? routeData.reason.trim()
    : "workflow-state.py route did not allow this subagent"
  const blockers = Array.isArray(routeData?.blockers) && routeData.blockers.length
    ? routeData.blockers.join(" | ")
    : "none"
  const warnings = Array.isArray(routeData?.warnings) && routeData.warnings.length
    ? routeData.warnings.join(" | ")
    : "none"
  return [
    "Strong-gate blocked this subagent dispatch.",
    `Subagent: ${subagentType}`,
    `Action: ${action}`,
    `Stage: ${stage}`,
    `Target: ${target}`,
    `Reason: ${reason}`,
    `Blockers: ${blockers}`,
    `Warnings: ${warnings}`,
    "Required next step: return control to the main session and follow the current workflow stage entry instead of continuing inside this subagent.",
    "",
    "Original prompt:",
    originalPrompt || "",
  ].join("\\n")
}
"""

BASH_INJECTION_OLD = """function injectTrellisContextIntoBash(ctx, input, output, hostPlatform, env) {
  const args = output?.args
  const commandKey = getBashCommandKey(args)
  if (!commandKey) return false

  const command = args[commandKey]
  if (!command.trim()) return false
  if (commandStartsWithTrellisContext(command)) return false

  const contextKey = ctx.getContextKey(input)
  if (!contextKey) return false

  args[commandKey] = `${buildTrellisContextPrefix(contextKey, hostPlatform, env)}${command}`
  return true
}"""

BASH_INJECTION_NEW = """function injectTrellisContextIntoBash(ctx, input, output, hostPlatform, env) {
  const args = output?.args
  const commandKey = getBashCommandKey(args)
  if (!commandKey) return false

  const command = args[commandKey]
  if (!command.trim()) return false
  if (commandStartsWithTrellisContext(command)) return false
  if (!/\\.trellis\\/scripts\\/|TRELLIS_CONTEXT_ID|workflow-state\\.py|task\\.py|get_context\\.py/.test(command)) {
    return false
  }

  const contextKey = ctx.getContextKey(input)
  if (!contextKey) return false

  args[commandKey] = `${buildTrellisContextPrefix(contextKey, hostPlatform, env)}${command}`
  return true
}"""

INJECTION_GUARD_OLD = """          if (!AGENTS_ALL.includes(subagentType)) {
            debugLog("inject", "Skipping - unsupported subagent_type")
            return
          }
"""

INJECTION_GUARD_NEW = """          if (!AGENTS_ALL.includes(subagentType)) {
            debugLog("inject", "Skipping - unsupported subagent_type")
            return
          }
"""


def patch_opencode_inject_subagent_context(target_path: Path) -> bool:
    if not target_path.is_file():
        print(f"⚠️ {target_path} 不存在，跳过")
        return False

    content = target_path.read_text(encoding="utf-8")
    patched = content

    if PATCH_MARKER not in patched:
        anchor = 'const ACTIVE_TASK_HINT_RE = /^\\s*Active task:\\s*(\\S+)\\s*$/m\n'
        if anchor not in patched:
            print(f"⚠️ {target_path} 中未找到 Active task hint anchor，跳过")
            return False
        patched = patched.replace(anchor, anchor + "\n" + ROUTE_HELPER_BLOCK + "\n", 1)

    if 'import { execFileSync } from "child_process"' not in patched:
        patched = patched.replace('import { join } from "path"\n', 'import { join } from "path"\nimport { execFileSync } from "child_process"\n', 1)

    if BASH_INJECTION_OLD in patched:
        patched = patched.replace(BASH_INJECTION_OLD, BASH_INJECTION_NEW, 1)

    if INJECTION_GUARD_OLD in patched:
        patched = patched.replace(INJECTION_GUARD_OLD, INJECTION_GUARD_NEW, 1)

    route_guard_anchor = """          if (!taskDir) {
            const fallback = ctx._resolveSingleSessionFallback()
            if (fallback?.taskPath) {
              const fallbackDir = ctx.resolveTaskDir(fallback.taskPath)
              if (fallbackDir && existsSync(fallbackDir)) {
                taskDir = fallback.taskPath
                taskSource = fallback.source
                debugLog("inject", "Resolved task via single-session fallback:", taskDir, "source:", taskSource)
              }
            }
          }
"""
    route_guard_insert = route_guard_anchor + """
          const routeData = taskDir ? loadRouteData(ctx, ctx.resolveTaskDir(taskDir)) : null
          if (!shouldAllowTaskInjection(routeData, subagentType)) {
            args.prompt = buildBlockedSubagentPrompt(routeData, subagentType, originalPrompt)
            debugLog("inject", "Skipping - strong-gate route does not allow subagent injection", JSON.stringify(routeData))
            return
          }
"""
    if route_guard_anchor in patched and "loadRouteData(ctx, ctx.resolveTaskDir(taskDir))" not in patched:
        patched = patched.replace(route_guard_anchor, route_guard_insert, 1)

    if patched == content:
        print(f"✅ {target_path} 已包含 OpenCode strong-gate subagent patch，跳过")
        return True

    target_path.write_text(patched, encoding="utf-8")
    print(f"✅ 已为 {target_path} 应用 OpenCode strong-gate subagent patch")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply the OpenCode strong-gate subagent patch to inject-subagent-context.js."
    )
    parser.add_argument("target_path", help="Path to the target inject-subagent-context.js file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target_path = Path(args.target_path).resolve()
    return 0 if patch_opencode_inject_subagent_context(target_path) else 1


if __name__ == "__main__":
    raise SystemExit(main())
