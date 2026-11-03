/**
 * dsh-deepseek-keyring — Host half.
 *
 * 多把 DeepSeek 官方 API Key 的管理与自动轮换：
 *
 * 1. 同一时刻只有一把 Key 生效：它就是官方 provider 读取的那个凭证引用
 *    （默认 `DEEPSEEK_API_KEY`）。切 Key 的做法是改写该引用的值，provider 每次
 *    请求都会重新 `credentials.resolve`，所以下一轮请求就换成了新 Key，不需要重启。
 * 2. 只有当前 Key 的余额耗尽（或已过期）才轮到下一把：优先级为「有到期日的
 *    Key 先用，到期日早的先用」，其余按加入顺序。
 * 3. 余额来自官方 `GET /user/balance`；轮询之外还会在模型请求因欠费失败时
 *    （`agent/request-error`）立即切到下一把，并让这次请求重试。
 * 4. Key 本体存放在 credentials 服务（`$DSH_HOME/.credentials.yaml`，0600），
 *    本插件自己的状态文件只保存元数据（引用名、到期日、余额快照、隐藏标记）。
 * 5. 过期或额度用完的 Key 只打隐藏标记，不删除记录、不回收凭证。
 *
 * 对外只新增一个同源 HTTP 路由给浏览器半边用（只回掩码，不回明文 Key）。
 */

import { chmod, mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'

export const name = 'deepseek-keyring'
export const inject = ['credentials']

/** 浏览器半边调用的同源路由。 */
export const ROUTE = '/__dsh-deepseek-keyring/rpc'

const STORE_VERSION = 1
const MAX_BODY_BYTES = 256 * 1024
const KEY_TOKEN = /^(?:sk-)?[A-Za-z0-9_-]{16,}$/
const DATE_TOKEN = /^(\d{4})-(\d{2})-(\d{2})$/

const DEFAULT_CONFIG = {
  provider: 'deepseek-official',
  credentialRef: 'DEEPSEEK_API_KEY',
  apiBase: 'https://api.deepseek.com',
  balancePath: '/user/balance',
  pollIntervalMs: 20000,
  minRefreshGapMs: 5000,
  refreshOnActivity: true,
  requestTimeoutMs: 15000,
  storePath: '',
  importExisting: true,
  maxKeys: 50,
}

function dshHome() {
  const fromEnv = typeof process.env.DSH_HOME === 'string' ? process.env.DSH_HOME.trim() : ''
  return fromEnv.length > 0 ? fromEnv : join(homedir(), '.dsh')
}

/**
 * 归一化 Loader 行里给出的 config；缺项一律回到默认值（profile 覆盖是整块替换）。
 * @param {unknown} raw - 行里的 config。
 * @returns 完整的运行配置。
 */
function resolveConfig(raw) {
  const input = raw !== null && typeof raw === 'object' ? raw : {}
  const text = (value, fallback) => (typeof value === 'string' && value.trim().length > 0 ? value.trim() : fallback)
  const apiBase = text(input.apiBase, DEFAULT_CONFIG.apiBase).replace(/\/+$/, '')
  const poll = Number(input.pollIntervalMs)
  const gap = Number(input.minRefreshGapMs)
  const timeout = Number(input.requestTimeoutMs)
  const maxKeys = Number(input.maxKeys)
  return {
    provider: text(input.provider, DEFAULT_CONFIG.provider),
    credentialRef: text(input.credentialRef, DEFAULT_CONFIG.credentialRef),
    apiBase,
    balancePath: text(input.balancePath, DEFAULT_CONFIG.balancePath),
    pollIntervalMs: Number.isFinite(poll) ? Math.min(Math.max(poll, 5000), 3600000) : DEFAULT_CONFIG.pollIntervalMs,
    minRefreshGapMs: Number.isFinite(gap) ? Math.min(Math.max(gap, 1000), 60000) : DEFAULT_CONFIG.minRefreshGapMs,
    refreshOnActivity: input.refreshOnActivity !== false,
    requestTimeoutMs: Number.isFinite(timeout) ? Math.min(Math.max(timeout, 2000), 60000) : DEFAULT_CONFIG.requestTimeoutMs,
    storePath: text(input.storePath, join(dshHome(), 'deepseek-keyring.json')),
    importExisting: input.importExisting !== false,
    maxKeys: Number.isFinite(maxKeys) ? Math.min(Math.max(Math.trunc(maxKeys), 1), 500) : DEFAULT_CONFIG.maxKeys,
  }
}

/** 掩码：只露前三后四，界面与接口都只见到这个形态。 */
function maskKey(value) {
  if (typeof value !== 'string' || value.length === 0) return '—'
  if (value.length <= 8) return `${value.slice(0, 2)}…`
  return `${value.slice(0, 3)}…${value.slice(-4)}`
}

function toAmount(value) {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function errorText(error) {
  if (error instanceof Error) return error.message
  return String(error)
}

/** `YYYY-MM-DD` 到当天最后一毫秒；格式或日历非法时返回 null。 */
function expiryEndMs(expiry) {
  if (typeof expiry !== 'string') return null
  const match = DATE_TOKEN.exec(expiry)
  if (match === null) return null
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const start = new Date(year, month - 1, day)
  if (start.getFullYear() !== year || start.getMonth() !== month - 1 || start.getDate() !== day) return null
  start.setHours(23, 59, 59, 999)
  return start.getTime()
}

function isExpired(entry, nowMs) {
  const end = expiryEndMs(entry.expiry)
  return end !== null && end < nowMs
}

function isBalanceEmpty(entry) {
  const total = entry.balance === null || entry.balance === undefined ? null : entry.balance.total
  return typeof total === 'number' && total <= 0
}

/** 有效（可以成为当前 Key）的判定。余额未知时先乐观放行，由下一次轮询校正。 */
function isUsable(entry, nowMs) {
  if (entry === null || entry === undefined) return false
  if (entry.hidden === true || entry.exhaustedAt || entry.invalidAt) return false
  if (isExpired(entry, nowMs)) return false
  return !isBalanceEmpty(entry)
}

/**
 * 切换优先级：临期的先用。
 *
 * 第一档是用户手填的到期日（越早越先用）；第二档是自动识别的“临期近似”——
 * 赠送余额（granted_balance）本身有有效期，先把有赠送余额的 Key 消耗掉；
 * 其余按加入顺序。手填的到期日始终优先于启发式。
 * @param {object} a - 条目。
 * @param {object} b - 条目。
 * @returns 排序值。
 */
function comparePriority(a, b) {
  const rankOf = (entry) => {
    const end = expiryEndMs(entry.expiry)
    if (end !== null) return { tier: 0, window: end }
    const granted = typeof entry.balance?.granted === 'number' ? entry.balance.granted : 0
    return { tier: granted > 0 ? 1 : 2, window: 0 }
  }
  const left = rankOf(a)
  const right = rankOf(b)
  if (left.tier !== right.tier) return left.tier - right.tier
  if (left.window !== right.window) return left.window - right.window
  return Number(a.addedAt ?? 0) - Number(b.addedAt ?? 0)
}

/**
 * 判定一次失败是否属于「额度用尽」这一类。
 *
 * 只有这一类才切换 Key：超时、传输、5xx、限流、鉴权错误都不算。
 * @param {unknown} failure - LlmFailure。
 * @returns 命中的信号名，或 null 表示不是欠费。
 */
function quotaSignal(failure) {
  if (failure === null || typeof failure !== 'object') return null
  const code = typeof failure.code === 'string' ? failure.code.toUpperCase() : ''
  if (code === 'INSUFFICIENT_BALANCE' || code === 'PAYMENT_REQUIRED' || code === 'INSUFFICIENT_QUOTA') return `code:${code}`
  if (failure.status === 402) return 'status:402'
  const message = typeof failure.message === 'string' ? failure.message : ''
  if (/insufficient\s*balance|balance\s*(?:is\s*)?insufficient|no\s*available\s*balance|insufficient\s*quota|out\s*of\s*quota/i.test(message)) {
    return 'message'
  }
  // 官方中文文案（含「当前请求的额度已用尽」）：额度/余额 + 用尽/不足/耗尽。
  if (/(额度|余额)[^。；;]{0,8}(用尽|不足|耗尽|为零|为 0|为0)/.test(message)) return 'message'
  return null
}

/** 逐行解析批量输入：`sk-xxx`、`sk-xxx,2026-12-31`、`sk-xxx 2026-12-31 备注`。 */
function parseKeyLines(text) {
  const rows = []
  const rejected = []
  const lines = String(text ?? '').split(/\r?\n/)
  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.length === 0 || trimmed.startsWith('#')) continue
    const tokens = trimmed.split(/[\s,，]+/).filter((token) => token.length > 0)
    const key = tokens.shift()
    if (key === undefined || !KEY_TOKEN.test(key)) {
      rejected.push({ line: trimmed, reason: 'unrecognized-key' })
      continue
    }
    let expiry = null
    const dateIndex = tokens.findIndex((token) => DATE_TOKEN.test(token))
    if (dateIndex >= 0) {
      const candidate = tokens.splice(dateIndex, 1)[0]
      if (expiryEndMs(candidate) === null) {
        rejected.push({ line: trimmed, reason: 'bad-expiry' })
        continue
      }
      expiry = candidate
    }
    rows.push({ key, expiry, label: tokens.join(' ').slice(0, 60) })
  }
  return { rows, rejected }
}

async function readBody(req, limit) {
  return await new Promise((resolve, reject) => {
    const chunks = []
    let size = 0
    req.on('data', (chunk) => {
      size += chunk.length
      if (size > limit) {
        reject(new Error('body-too-large'))
        req.destroy()
        return
      }
      chunks.push(chunk)
    })
    req.on('end', () => {
      if (chunks.length === 0) {
        resolve({})
        return
      }
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')))
      } catch {
        reject(new Error('bad-json'))
      }
    })
    req.on('error', () => reject(new Error('read-failed')))
  })
}

function sendJson(res, status, payload) {
  const body = JSON.stringify(payload)
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store',
    'content-length': Buffer.byteLength(body),
  })
  res.end(body)
}

/**
 * 同源闸门：只接受同源页面发起的 POST，且要求自定义头（跨站表单无法伪造）。
 * @param {import('node:http').IncomingMessage} req - 请求。
 * @returns 拒绝原因，或 null 表示放行。
 */
function gateRequest(req) {
  if (req.headers['x-dsh-keyring'] !== '1') return 'missing-header'
  const contentType = String(req.headers['content-type'] ?? '')
  if (!contentType.toLowerCase().includes('application/json')) return 'bad-content-type'
  const host = String(req.headers.host ?? '')
  if (host.length === 0) return 'bad-host'
  const origin = req.headers.origin
  if (typeof origin !== 'string' || origin.length === 0) return null
  if (origin === 'dsh-app://app') return null
  let parsed
  try {
    parsed = new URL(origin)
  } catch {
    return 'bad-origin'
  }
  if (parsed.host !== host) return 'cross-origin'
  return null
}

/** 一把 Key 的池子。所有读写都串行，避免并发轮询与手动操作互相覆盖。 */
class DeepSeekKeyring {
  /**
   * @param {import('@deepseek-ai/cordis').Context} ctx - 插件上下文。
   * @param {ReturnType<typeof resolveConfig>} config - 运行配置。
   */
  constructor(ctx, config) {
    this.ctx = ctx
    this.config = config
    this.store = { version: STORE_VERSION, activeId: null, entries: [] }
    this.appliedId = null
    this.lastError = null
    this.queue = Promise.resolve()
    this.timer = null
    this.lastActiveCheckAt = 0
    this.disposed = false
  }

  /** 串行执行一次状态变更。 */
  enqueue(task) {
    const run = this.queue.then(() => task())
    this.queue = run.then(
      () => undefined,
      () => undefined,
    )
    return run
  }

  start() {
    this.enqueue(() => this.bootstrap()).catch((error) => {
      this.lastError = errorText(error)
      this.log('warn', `启动失败：${this.lastError}`)
    })
    this.timer = setInterval(() => {
      this.enqueue(() => this.poll()).catch(() => undefined)
    }, this.config.pollIntervalMs)
    this.timer.unref?.()
  }

  stop() {
    this.disposed = true
    if (this.timer !== null) {
      clearInterval(this.timer)
      this.timer = null
    }
  }

  log(level, message) {
    try {
      const logger = this.ctx.logger
      if (logger && typeof logger[level] === 'function') logger[level](`[deepseek-keyring] ${message}`)
    } catch {
      /* 日志不可用时静默：绝不因为日志失败影响主流程 */
    }
  }

  // ---- 状态文件 -------------------------------------------------------------

  async load() {
    let text
    try {
      text = await readFile(this.config.storePath, 'utf8')
    } catch (error) {
      if (error?.code === 'ENOENT') return
      throw error
    }
    let parsed
    try {
      parsed = JSON.parse(text)
    } catch {
      this.log('warn', `状态文件不是合法 JSON，按空池处理：${this.config.storePath}`)
      return
    }
    const entries = Array.isArray(parsed?.entries) ? parsed.entries : []
    this.store = {
      version: STORE_VERSION,
      activeId: typeof parsed?.activeId === 'string' ? parsed.activeId : null,
      entries: entries.filter((entry) => typeof entry?.id === 'string' && typeof entry?.ref === 'string').map((entry) => ({
        id: entry.id,
        ref: entry.ref,
        label: typeof entry.label === 'string' ? entry.label : '',
        expiry: typeof entry.expiry === 'string' ? entry.expiry : null,
        addedAt: Number(entry.addedAt ?? Date.now()),
        hidden: entry.hidden === true,
        exhaustedAt: entry.exhaustedAt ?? null,
        invalidAt: entry.invalidAt ?? null,
        balance: entry.balance && typeof entry.balance === 'object' ? entry.balance : null,
        checkedAt: entry.checkedAt ?? null,
        error: typeof entry.error === 'string' ? entry.error : null,
      })),
    }
  }

  async persist() {
    const target = this.config.storePath
    await mkdir(dirname(target), { recursive: true, mode: 0o700 })
    const temporary = `${target}.${process.pid}.tmp`
    await writeFile(temporary, `${JSON.stringify(this.store, null, 2)}\n`, { mode: 0o600 })
    await rename(temporary, target)
    await chmod(target, 0o600).catch(() => undefined)
  }

  // ---- 凭证 -----------------------------------------------------------------

  /** 池内某条目在 credentials 里的引用名。 */
  refFor(id) {
    return `DEEPSEEK_KEYRING_${id.toUpperCase()}`
  }

  /** 读出某条目的明文 Key（只在 Host 进程内使用）。 */
  async keyOf(entry) {
    const resolved = await this.ctx.credentials.resolve(entry.ref)
    return resolved?.value
  }

  /** 把某条目设为当前 Key：改写 provider 读取的那个引用。 */
  async applyCredential(entry) {
    const value = await this.keyOf(entry)
    if (typeof value !== 'string' || value.length === 0) {
      throw new Error(`池内 Key 的凭证已丢失：${entry.ref}`)
    }
    const current = await this.ctx.credentials.resolve(this.config.credentialRef)
    if (current?.value !== value) {
      await this.ctx.credentials.set(this.config.credentialRef, value)
    }
    this.appliedId = entry.id
    this.store.activeId = entry.id
  }

  // ---- 余额 -----------------------------------------------------------------

  /** 查询单把 Key 的余额。 */
  async queryBalance(key) {
    const url = new URL(this.config.balancePath, `${this.config.apiBase}/`).toString()
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), this.config.requestTimeoutMs)
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: { authorization: `Bearer ${key}`, accept: 'application/json' },
        signal: controller.signal,
      })
      const text = await response.text()
      let payload = null
      try {
        payload = JSON.parse(text)
      } catch {
        payload = null
      }
      if (!response.ok) {
        return {
          ok: false,
          status: response.status,
          error: typeof payload?.error?.message === 'string' ? payload.error.message : `HTTP ${response.status}`,
        }
      }
      const info = Array.isArray(payload?.balance_infos) ? payload.balance_infos[0] : null
      return {
        ok: true,
        isAvailable: payload?.is_available !== false,
        currency: typeof info?.currency === 'string' ? info.currency : 'CNY',
        total: toAmount(info?.total_balance),
        granted: toAmount(info?.granted_balance),
        toppedUp: toAmount(info?.topped_up_balance),
      }
    } catch (error) {
      return { ok: false, error: error?.name === 'AbortError' ? 'timeout' : errorText(error) }
    } finally {
      clearTimeout(timer)
    }
  }

  /** 把一次余额结果写回条目：有效则更新数字，欠费/失效则隐藏。 */
  recordBalance(entry, result) {
    entry.checkedAt = Date.now()
    if (result.ok === true) {
      entry.error = null
      entry.balance = {
        currency: result.currency,
        total: result.total,
        granted: result.granted,
        toppedUp: result.toppedUp,
      }
      if (result.isAvailable === false || (typeof result.total === 'number' && result.total <= 0)) {
        entry.exhaustedAt = entry.exhaustedAt ?? Date.now()
        entry.hidden = true
      }
      return
    }
    if (result.status === 401 || result.status === 403) {
      entry.invalidAt = entry.invalidAt ?? Date.now()
      entry.hidden = true
      entry.error = result.error ?? 'invalid-key'
      return
    }
    entry.error = result.error ?? 'balance-unavailable'
  }

  async refreshEntry(entry) {
    const key = await this.keyOf(entry)
    if (typeof key !== 'string' || key.length === 0) {
      entry.invalidAt = entry.invalidAt ?? Date.now()
      entry.hidden = true
      entry.error = 'missing-credential'
      return
    }
    this.recordBalance(entry, await this.queryBalance(key))
  }

  /** 刷新所有未隐藏条目的余额（并发 3，够快又不至于打满）。 */
  async refreshAll() {
    const targets = this.store.entries.filter((entry) => entry.hidden !== true)
    let cursor = 0
    const worker = async () => {
      while (cursor < targets.length) {
        const index = cursor
        cursor += 1
        try {
          await this.refreshEntry(targets[index])
        } catch (error) {
          targets[index].error = errorText(error)
        }
      }
    }
    await Promise.all([worker(), worker(), worker()])
  }

  // ---- 选择与切换 -----------------------------------------------------------

  activeEntry() {
    const id = this.store.activeId
    if (typeof id !== 'string') return null
    return this.store.entries.find((entry) => entry.id === id) ?? null
  }

  /** 按优先级挑下一把可用 Key。 */
  pickNext(excludeId) {
    const now = Date.now()
    const candidates = this.store.entries.filter((entry) => entry.id !== excludeId && isUsable(entry, now))
    if (candidates.length === 0) return null
    candidates.sort(comparePriority)
    return candidates[0]
  }

  /** 把过期条目隐藏掉（只打标记，不删除）。 */
  applyExpiry() {
    const now = Date.now()
    for (const entry of this.store.entries) {
      if (entry.hidden !== true && isExpired(entry, now)) entry.hidden = true
    }
  }

  /** 校正「当前 Key」：能继续用就留着，不能用了就按优先级换下一把。 */
  async reconcile() {
    this.applyExpiry()
    if (this.store.entries.length === 0) return false
    const active = this.activeEntry()
    if (active !== null && isUsable(active, Date.now())) {
      await this.applyCredential(active)
      return false
    }
    const next = this.pickNext(active?.id)
    if (next === null) {
      this.store.activeId = null
      return false
    }
    await this.applyCredential(next)
    try {
      await this.refreshEntry(next)
    } catch (error) {
      next.error = errorText(error)
    }
    return true
  }

  // ---- 生命周期里的几步 -----------------------------------------------------

  async bootstrap() {
    await this.load()
    if (this.config.importExisting && this.store.entries.length === 0) await this.importExisting()
    await this.refreshAll()
    await this.reconcile()
    await this.persist()
  }

  /** 首次启用时把本来就在用的官方 Key 收进池子，避免用户重填一遍。 */
  async importExisting() {
    const current = await this.ctx.credentials.resolve(this.config.credentialRef)
    const value = current?.value
    if (typeof value !== 'string' || value.length === 0) return
    const id = this.nextId()
    const ref = this.refFor(id)
    await this.ctx.credentials.set(ref, value)
    this.store.entries.push({
      id,
      ref,
      label: '现有 Key',
      expiry: null,
      addedAt: Date.now(),
      hidden: false,
      exhaustedAt: null,
      invalidAt: null,
      balance: null,
      checkedAt: null,
      error: null,
    })
    this.store.activeId = id
    this.appliedId = id
  }

  nextId() {
    let max = 0
    for (const entry of this.store.entries) {
      const match = /^k(\d+)$/.exec(entry.id)
      if (match !== null) max = Math.max(max, Number(match[1]))
    }
    return `k${max + 1}`
  }

  async poll() {
    try {
      await this.refreshAll()
      const rotated = await this.reconcile()
      await this.persist()
      this.lastError = null
      return rotated
    } catch (error) {
      this.lastError = errorText(error)
      throw error
    }
  }

  /**
   * 每次模型请求前的一次「只查当前 Key」节流刷新。
   *
   * 定时轮询之外再加一层，让余额数字贴近真实；节流保证同一间隔内不重复发 HTTP，
   * 查的是当前正在用的那一把（一次请求），并在它真的耗尽时立刻换 Key，
   * 使这次请求直接用上新 Key。任何失败都不影响请求本身。
   * @returns 完成信号。
   */
  async beforeRequest() {
    if (this.disposed || !this.config.refreshOnActivity) return
    const now = Date.now()
    if (now - this.lastActiveCheckAt < this.config.minRefreshGapMs) return
    this.lastActiveCheckAt = now
    try {
      await this.enqueue(async () => {
        // 当前 Key 若已判为不可用（上一轮耗尽/过期），先让位，请求就能用上新的那把。
        if (!isUsable(this.activeEntry(), Date.now())) {
          await this.reconcile()
          await this.persist()
        }
        const current = this.activeEntry()
        if (current === null) return
        const key = await this.keyOf(current)
        if (typeof key !== 'string' || key.length === 0) return
        this.recordBalance(current, await this.queryBalance(key))
        if (!isUsable(current, Date.now())) {
          await this.reconcile()
          await this.persist()
        }
      })
    } catch {
      /* 请求前刷新只是尽力而为 */
    }
  }

  // ---- 批量补充 -------------------------------------------------------------

  async addKeys(text) {
    const { rows, rejected } = parseKeyLines(text)
    const added = []
    const failed = [...rejected]
    if (rows.length === 0) return { added, rejected: failed }

    const known = new Map()
    for (const entry of this.store.entries) {
      const value = await this.keyOf(entry).catch(() => undefined)
      if (typeof value === 'string') known.set(value, entry)
    }

    for (const row of rows) {
      if (known.has(row.key)) {
        const entry = known.get(row.key)
        const revived = entry.hidden === true || entry.exhaustedAt !== null || entry.invalidAt !== null
        entry.hidden = false
        entry.exhaustedAt = null
        entry.invalidAt = null
        entry.error = null
        if (row.expiry !== null) entry.expiry = row.expiry
        if (row.label.length > 0) entry.label = row.label
        try {
          await this.refreshEntry(entry)
        } catch (error) {
          entry.error = errorText(error)
        }
        if (entry.invalidAt !== null) {
          failed.push({ line: row.key, reason: entry.error ?? 'invalid-key' })
        } else {
          added.push({ id: entry.id, masked: maskKey(row.key), revived, hidden: entry.hidden === true })
        }
        continue
      }
      if (this.store.entries.length >= this.config.maxKeys) {
        failed.push({ line: row.key, reason: 'pool-full' })
        continue
      }
      const probe = await this.queryBalance(row.key)
      if (probe.ok === false && (probe.status === 401 || probe.status === 403)) {
        failed.push({ line: row.key, reason: 'invalid-key' })
        continue
      }
      const id = this.nextId()
      const ref = this.refFor(id)
      await this.ctx.credentials.set(ref, row.key)
      const entry = {
        id,
        ref,
        label: row.label,
        expiry: row.expiry,
        addedAt: Date.now(),
        hidden: false,
        exhaustedAt: null,
        invalidAt: null,
        balance: null,
        checkedAt: null,
        error: null,
      }
      this.store.entries.push(entry)
      known.set(row.key, entry)
      if (probe.ok === true) this.recordBalance(entry, probe)
      else entry.error = probe.error ?? 'unverified'
      added.push({ id: entry.id, masked: maskKey(row.key), revived: false, hidden: entry.hidden === true })
    }

    const rotated = await this.reconcile()
    await this.persist()
    return { added, rejected: failed, rotated }
  }

  // ---- 快照 -----------------------------------------------------------------

  async viewOf(entry, activeId) {
    const key = await this.keyOf(entry).catch(() => undefined)
    const now = Date.now()
    const status = entry.id === activeId ? 'active' : entry.hidden === true ? 'hidden' : isExpired(entry, now) ? 'expired' : isBalanceEmpty(entry) ? 'empty' : 'ready'
    return {
      id: entry.id,
      masked: maskKey(key),
      label: entry.label ?? '',
      expiry: entry.expiry ?? null,
      addedAt: entry.addedAt ?? null,
      balance: entry.balance ?? null,
      checkedAt: entry.checkedAt ?? null,
      error: entry.error ?? null,
      status,
    }
  }

  async snapshot() {
    const active = this.activeEntry()
    const activeId = active?.id ?? null
    const visible = this.store.entries.filter((entry) => entry.hidden !== true)
    visible.sort(comparePriority)
    const keys = []
    for (const entry of visible) keys.push(await this.viewOf(entry, activeId))
    const sums = new Map()
    let unverified = 0
    for (const view of keys) {
      const total = view.balance?.total
      if (typeof total !== 'number') {
        unverified += 1
        continue
      }
      const currency = view.balance.currency ?? 'CNY'
      sums.set(currency, (sums.get(currency) ?? 0) + total)
    }
    return {
      revision: STORE_VERSION,
      provider: this.config.provider,
      credentialRef: this.config.credentialRef,
      activeId,
      active: active === null ? null : await this.viewOf(active, activeId),
      keys,
      totals: [...sums].map(([currency, amount]) => ({ currency, amount: Math.round(amount * 100) / 100 })),
      unverified,
      hiddenCount: this.store.entries.length - visible.length,
      pollIntervalMs: this.config.pollIntervalMs,
      updatedAt: Date.now(),
      error: this.lastError,
    }
  }

  // ---- HTTP 入口 ------------------------------------------------------------

  async handle(req, res) {
    if (req.method === 'GET') {
      sendJson(res, 200, { ok: true, data: { route: ROUTE, provider: this.config.provider } })
      return
    }
    if (req.method !== 'POST') {
      sendJson(res, 405, { ok: false, error: 'method-not-allowed' })
      return
    }
    const refusal = gateRequest(req)
    if (refusal !== null) {
      sendJson(res, 403, { ok: false, error: refusal })
      return
    }
    let body
    try {
      body = await readBody(req, MAX_BODY_BYTES)
    } catch (error) {
      sendJson(res, 400, { ok: false, error: errorText(error) })
      return
    }
    const op = typeof body?.op === 'string' ? body.op : ''
    try {
      if (op === 'state') {
        sendJson(res, 200, { ok: true, data: await this.enqueue(() => this.snapshot()) })
        return
      }
      if (op === 'refresh') {
        sendJson(
          res,
          200,
          { ok: true, data: await this.enqueue(async () => {
            await this.poll()
            return await this.snapshot()
          }) },
        )
        return
      }
      if (op === 'add') {
        const text = typeof body?.text === 'string' ? body.text : ''
        sendJson(
          res,
          200,
          { ok: true, data: await this.enqueue(async () => {
            const result = await this.addKeys(text)
            return { ...result, state: await this.snapshot() }
          }) },
        )
        return
      }
      if (op === 'export') {
        const scope = body?.scope === 'dead' || body?.scope === 'all' ? body.scope : 'valid'
        sendJson(res, 200, { ok: true, data: await this.enqueue(() => this.exportKeys(scope)) })
        return
      }
      sendJson(res, 400, { ok: false, error: 'unknown-op' })
    } catch (error) {
      this.lastError = errorText(error)
      sendJson(res, 500, { ok: false, error: this.lastError })
    }
  }

  // ---- 导出 -----------------------------------------------------------------

  /**
   * 导出一份可原样粘回补充框的文本（含明文 Key）。
   *
   * 三类互不重叠：`valid` 只含可用 Key，`dead` 只含失效/用尽/过期/已隐藏的 Key，
   * `all` 是全部条目。
   * @param {'valid'|'dead'|'all'} scope - 导出范围。
   * @returns 文件名、文本与条数。
   */
  async exportKeys(scope) {
    const now = Date.now()
    const isDead = (entry) =>
      entry.hidden === true || Boolean(entry.exhaustedAt) || Boolean(entry.invalidAt) || isExpired(entry, now) || isBalanceEmpty(entry)
    const picked = this.store.entries.filter((entry) => {
      const dead = isDead(entry)
      if (scope === 'valid') return !dead
      if (scope === 'dead') return dead
      return true
    })
    picked.sort(comparePriority)

    const stamp = new Date(now)
    const pad = (value) => String(value).padStart(2, '0')
    const today = `${stamp.getFullYear()}${pad(stamp.getMonth() + 1)}${pad(stamp.getDate())}`
    const title = scope === 'valid' ? '有效' : scope === 'dead' ? '失效或已用完' : '全部'
    const lines = [`# DeepSeek Key 导出 · ${title} · ${stamp.toISOString()}`, '# 格式：key [到期日] [备注]（可直接粘回批量补充框）']
    for (const entry of picked) {
      const key = await this.keyOf(entry).catch(() => undefined)
      if (typeof key !== 'string' || key.length === 0) continue
      const parts = [key]
      if (typeof entry.expiry === 'string' && entry.expiry.length > 0) parts.push(entry.expiry)
      if (typeof entry.label === 'string' && entry.label.length > 0) parts.push(entry.label.replace(/\s+/g, ' '))
      lines.push(parts.join(' '))
    }
    return { scope, filename: `deepseek-keys-${scope}-${today}.txt`, count: lines.length - 2, text: `${lines.join('\n')}\n` }
  }

  // ---- 模型请求因欠费失败时立刻换 Key ---------------------------------------

  /**
   * `agent/request-error` 水面：只在官方 provider 明确报「额度/余额用尽」时接手，
   * 换好下一把后要求重试。超时、传输、5xx、限流等其它异常一律交回原有链路。
   *
   * 判定顺序刻意如此：先认消息与状态码，再回查余额校验；但**明确欠费信号不会被
   * 回查到的正数余额否决**——官方余额接口与扣费之间有时间差，用尽的一瞬间它仍可能
   * 报出 0.001 之类的残值，若以余额为准就会错过切换（这是原先的缺陷）。
   * @param {unknown} payload - 事件负载。
   * @param {() => Promise<unknown>} next - 原处理链。
   * @returns 处理结果。
   */
  onRequestError(payload, next) {
    if (this.disposed) return next()
    if (payload === null || typeof payload !== 'object') return next()
    if (payload.provider !== this.config.provider) return next()
    const signal = quotaSignal(payload.failure)
    if (signal === null) return next()
    return this.enqueue(async () => {
      const active = this.activeEntry()
      if (active === null) return undefined
      const failedId = active.id
      this.log('info', `欠费信号(${signal})，当前 Key ${failedId}，开始切换`)
      // 回查一次只用于记录余额快照；判定已由消息给出，正数余额不再否决切换。
      const key = await this.keyOf(active).catch(() => undefined)
      if (typeof key === 'string' && key.length > 0) {
        try {
          this.recordBalance(active, await this.queryBalance(key))
        } catch {
          /* 快照失败不影响切换决定 */
        }
      }
      this.markExhausted(active)
      const nextEntry = this.pickNext(failedId)
      if (nextEntry === null) {
        await this.persist()
        this.log('warn', '池内没有可用的下一把 Key，交回原有链路')
        return undefined
      }
      await this.applyCredential(nextEntry)
      try {
        await this.refreshEntry(nextEntry)
      } catch {
        /* 余额留到下一次轮询 */
      }
      await this.persist()
      this.log('info', `已切换到 ${nextEntry.id}`)
      return { kind: 'retry' }
    }).then(
      (action) => (action === undefined ? next() : action),
      (error) => {
        this.log('warn', `切换失败，交回原有链路：${errorText(error)}`)
        return next()
      },
    )
  }

  /** 把条目记为耗尽并隐藏（余额清零，避免下一轮又被当成可用）。 */
  markExhausted(entry) {
    entry.exhaustedAt = entry.exhaustedAt ?? Date.now()
    entry.hidden = true
    if (entry.balance === null || entry.balance === undefined) {
      entry.balance = { currency: 'CNY', total: 0, granted: 0, toppedUp: 0 }
    } else {
      entry.balance = { ...entry.balance, total: 0 }
    }
    entry.checkedAt = Date.now()
  }
}

/**
 * Host 入口。
 * @param {import('@deepseek-ai/cordis').Context} ctx - 插件上下文。
 * @param {unknown} config - Loader 行配置。
 */
export function apply(ctx, config) {
  const keyring = new DeepSeekKeyring(ctx, resolveConfig(config))
  ctx.effect(
    () => {
      keyring.start()
      return () => keyring.stop()
    },
    'deepseek-keyring: lifecycle',
  )
  ctx.effect(
    () => ctx.on('agent/request-error', (payload, next) => keyring.onRequestError(payload, next)),
    'deepseek-keyring: quota switch',
  )
  // 请求前的一次节流刷新：让余额贴近真实，并在当前 Key 已耗尽时赶在请求发出前换掉。
  // 只改 Key，不动返回的调用配置，所以对其它 provider 与其它插件都无影响。
  ctx.effect(
    () =>
      ctx.on('agent/request', async (payload, next) => {
        await keyring.beforeRequest()
        return next()
      }),
    'deepseek-keyring: pre-request refresh',
  )
  ctx.inject(['webServer'], (webCtx) => {
    webCtx.effect(
      () =>
        webCtx.webServer.register({
          kind: 'exact',
          path: ROUTE,
          handler: (req, res) => {
            keyring.handle(req, res).catch(() => {
              if (!res.headersSent) sendJson(res, 500, { ok: false, error: 'internal-error' })
            })
          },
        }),
      'deepseek-keyring: rpc route',
    )
  })
}
