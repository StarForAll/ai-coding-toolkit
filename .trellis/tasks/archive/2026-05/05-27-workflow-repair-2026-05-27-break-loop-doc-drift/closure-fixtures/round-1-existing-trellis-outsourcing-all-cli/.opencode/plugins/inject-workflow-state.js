/* global process */
import { existsSync, readFileSync } from "fs"
import { join } from "path"
import { TrellisContext } from "../lib/trellis-context.js"
import { execFileSync } from "child_process"
const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"


const ACTION_BREADCRUMB_KEYS = new Set([
  "awaiting_confirmation",
  "awaiting_confirmation_with_blockers",
  "blocked",
  "context_needed",
  "repair_needed",
  "recovery_needed",
  "embed_invalid",
  "workflow-state.route_failed",
])

function getActiveTask(ctx, platformInput = null) {
  const active = ctx.getActiveTask(platformInput)
  const taskRef = active.taskPath
  if (!taskRef) return null
  const taskDir = ctx.resolveTaskDir(taskRef)
  if (active.stale || !taskDir || !existsSync(taskDir)) {
    return { id: taskRef.split("/").pop(), status: "stale", source: active.source, extraLines: [] }
  }
  const taskJsonPath = join(taskDir, "task.json")
  let data = {}
  if (existsSync(taskJsonPath)) {
    try {
      const parsed = JSON.parse(readFileSync(taskJsonPath, "utf-8"))
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        data = parsed
      }
    } catch {
      data = {}
    }
  }
  const rawStatus = typeof data.status === "string" ? data.status : ""
  const id = typeof data.id === "string" && data.id ? data.id : taskRef.split("/").pop()

  // [workflow-embed-patch:prefer-workflow-state-json]
  // [workflow-embed-patch:prefer-workflow-route]
  // Prefer workflow-state.py route over task.json.status for strong-gate projects.
  let status = rawStatus
  let source = active.source
  const extraLines = []
  const routeScript = join(ctx.directory, ".trellis", "scripts", "workflow", "workflow-state.py")
  if (existsSync(routeScript)) {
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
      })
      const routeData = JSON.parse(output)
      const routeStage = typeof routeData.stage === "string" ? routeData.stage : ""
      const routeAction = typeof routeData.action === "string" ? routeData.action : ""
      const routeStageStatus = typeof routeData.status === "string" ? routeData.status : ""
      const routeTarget = typeof routeData.target === "string" ? routeData.target : ""
      const routeReason = typeof routeData.reason === "string" ? routeData.reason : ""
      const routeBlockers = Array.isArray(routeData.blockers) ? routeData.blockers : []
      const routeWarnings = Array.isArray(routeData.warnings) ? routeData.warnings : []
      const usesActionBreadcrumb = ACTION_BREADCRUMB_KEYS.has(routeAction)
      if (usesActionBreadcrumb) {
        status = routeAction
        if (routeStage) extraLines.push(`Stage: ${routeStage}`)
      } else if (routeStage) {
        status = routeStage
      } else if (routeAction) {
        status = routeAction
      }
      if (routeStageStatus) extraLines.push(`Stage-Status: ${routeStageStatus}`)
      if (routeTarget) extraLines.push(`Target-Stage: ${routeTarget}`)
      if (routeReason) extraLines.push(`Reason: ${routeReason}`)
      if (routeBlockers.length > 0) extraLines.push(`Blockers: ${routeBlockers.map(item => String(item)).join("; ")}`)
      if (routeWarnings.length > 0) extraLines.push(`Warnings: ${routeWarnings.map(item => String(item)).join("; ")}`)
      source = "workflow-state.route"
    } catch (error) {
      status = "workflow-state.route_failed"
      source = "workflow-state.route_failed"
      extraLines.push(`Reason: ${String(error).split("\n").pop()}`)
    }
  }
  if (!status) return null
  return { id, status, source, extraLines }
}



function buildBreadcrumb(id, status, templates, source = null, extraLines = []) {
  let body = templates[status]
  if (body === undefined) {
    body = "Refer to workflow.md for current step."
  }
  const headerLines = [id === null ? `Status: ${status}` : `Task: ${id} (${status})`]
  if (source) {
    headerLines.push(`Source: ${source}`)
  }
  if (Array.isArray(extraLines) && extraLines.length > 0) {
    headerLines.push(...extraLines)
  }
  return `<workflow-state>\n${headerLines.join("\n")}\n${body}\n</workflow-state>`
}



export default async ({ directory }) => {
  const ctx = new TrellisContext(directory)
  return {
    "chat.message": async (input, output) => {
      const templates = {}
      const task = getActiveTask(ctx, input)
      const breadcrumb = task
        ? buildBreadcrumb(task.id, task.status, templates, task.source, task.extraLines)
        : buildBreadcrumb(null, "no_task", templates)
      const parts = output?.parts || []
      parts.unshift({ type: "text", text: breadcrumb })
    },
  }
}
