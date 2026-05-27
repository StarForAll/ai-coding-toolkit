import { existsSync, readFileSync } from "fs"
import { basename, join } from "path"
import { execFileSync } from "child_process"
const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"

function hasCuratedJsonlEntry(jsonlPath) {
  return existsSync(jsonlPath)
}

// [workflow-embed-patch:strong-gate-session-utils]
function getTaskStatus(ctx, platformInput = null) {
  const active = ctx.getActiveTask(platformInput)
  const taskRef = active.taskPath
  const routeScript = join(ctx.directory, ".trellis", "scripts", "workflow", "workflow-state.py")

  if (!existsSync(routeScript)) {
    return `Status: ROUTER UNAVAILABLE\nSource: ${active.source}\nNext: Missing .trellis/scripts/workflow/workflow-state.py`
  }

  const args = [routeScript, "route", "--project-root", ctx.directory]
  if (taskRef) {
    args.splice(2, 0, taskRef)
  }

  try {
    const output = execFileSync(PYTHON_CMD, args, {
      cwd: ctx.directory,
      timeout: 5000,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        ...process.env,
        ...(platformInput && typeof ctx.getContextKey === "function" && ctx.getContextKey(platformInput)
          ? { TRELLIS_CONTEXT_ID: ctx.getContextKey(platformInput) }
          : {}),
      },
    })
    const data = JSON.parse(output)
    const stage = typeof data.stage === "string" && data.stage ? data.stage : "(unknown)"
    const action = typeof data.action === "string" ? data.action : "unknown"
    const target = typeof data.target === "string" && data.target ? data.target : ""
    const blockers = Array.isArray(data.blockers) ? data.blockers : []
    const blockerText = blockers.length > 0 ? `\nBlockers: ${blockers.join(" | ")}` : ""
    const targetText = target ? `\nTarget: ${target}` : ""
    return `Stage: ${stage}\nAction: ${action}${targetText}\nReason: ${data.reason || ""}${blockerText}`
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return `Status: ROUTER FAILED\nSource: ${active.source}\nNext: workflow-state.py route failed\nError: ${message}`
  }
}

function loadTrellisConfig() {
  return null
}

function stripBreadcrumbTagBlocks(content) {
  return content.replace(/\[workflow-state:[^\]]+\][\s\S]*?\[\/workflow-state:[^\]]+\]\n?/g, "").trimEnd()
}

export function buildSessionContext(ctx, platformInput = null) {
  const workflowContent = ctx.readProjectFile(".trellis/workflow.md")
  if (!workflowContent) return ""
  const allLines = workflowContent.split("\n")
  const overviewLines = []
  let rangeStart = -1
  let rangeEnd = allLines.length
  for (let i = 0; i < allLines.length; i++) {
    const stripped = allLines[i].trim()
    if (rangeStart === -1 && stripped === "## Phase Index") {
      rangeStart = i
    } else if (rangeStart !== -1 && stripped === "## Customizing Trellis (for forks)") {
      rangeEnd = i
      break
    }
  }
  if (rangeStart !== -1) {
    overviewLines.push(...allLines.slice(rangeStart, rangeEnd))
  }
  return overviewLines.join("\n")
}
