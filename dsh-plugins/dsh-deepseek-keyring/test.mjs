/**
 * dsh-deepseek-keyring 的离线集成测试：用假的 credentials + 本地假余额服务驱动 Host 半边。
 * 不碰真实的 .credentials.yaml，也不访问外网。
 *
 * 运行：node test.mjs
 */
import http from 'node:http'
import { mkdtemp, readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { tmpdir } from 'node:os'

const workdir = await mkdtemp(join(tmpdir(), 'dskr-test-'))

// ---- 假余额服务 -------------------------------------------------------------
/** key -> { status, body } */
const balances = new Map()
const balanceServer = http.createServer((req, res) => {
  const auth = String(req.headers.authorization ?? '')
  const key = auth.startsWith('Bearer ') ? auth.slice(7) : ''
  const entry = balances.get(key)
  if (entry === undefined) {
    res.writeHead(401, { 'content-type': 'application/json' })
    res.end(JSON.stringify({ error: { message: 'Authentication Fails' } }))
    return
  }
  res.writeHead(entry.status ?? 200, { 'content-type': 'application/json' })
  res.end(JSON.stringify(entry.body))
})
await new Promise((resolve) => balanceServer.listen(0, '127.0.0.1', resolve))
const balancePort = balanceServer.address().port

function setBalance(key, total, { isAvailable = true, currency = 'CNY' } = {}) {
  balances.set(key, {
    status: 200,
    body: {
      is_available: isAvailable && total > 0,
      balance_infos: [{ currency, total_balance: total.toFixed(2), granted_balance: total.toFixed(2), topped_up_balance: '0.00' }],
    },
  })
}

function setInvalid(key) {
  balances.delete(key)
}

// ---- 假 credentials ---------------------------------------------------------
const refs = new Map()
const credentials = {
  async resolve(ref) {
    const value = refs.get(ref)
    return typeof value === 'string' && value.length > 0 ? { value, source: 'file' } : undefined
  },
  async set(ref, value) {
    refs.set(ref, value)
  },
}

// ---- 假 ctx -----------------------------------------------------------------
let routeHandler = null
let requestErrorListener = null
let requestListener = null
const ctx = {
  credentials,
  logger: { info() {}, warn() {}, error() {} },
  effect(fn) {
    const dispose = fn()
    return () => dispose?.()
  },
  on(event, listener) {
    if (event === 'agent/request-error') requestErrorListener = listener
    if (event === 'agent/request') requestListener = listener
    return () => {}
  },
  inject(_deps, callback) {
    callback({
      effect(fn) {
        const dispose = fn()
        return () => dispose?.()
      },
      webServer: {
        register(route) {
          if (route.path === '/__dsh-deepseek-keyring/rpc') routeHandler = route.handler
          return () => {}
        },
      },
    })
    return () => {}
  },
}

// ---- 启动插件 ---------------------------------------------------------------
const MASTER = 'sk-master-0000000000000000'
const KEY_EXP_EARLY = 'sk-early-111111111111111111'
const KEY_EXP_LATE = 'sk-late-222222222222222222'
const KEY_PLAIN = 'sk-plain-333333333333333333'
const KEY_EMPTY = 'sk-empty-444444444444444444'
const KEY_BAD = 'sk-bad-555555555555555555'

refs.set('DEEPSEEK_API_KEY', MASTER)
setBalance(MASTER, 5)
setBalance(KEY_EXP_EARLY, 1)
setBalance(KEY_EXP_LATE, 3)
setBalance(KEY_PLAIN, 2)
setBalance(KEY_EMPTY, 0)
setInvalid(KEY_BAD)

const { apply } = await import('./index.js')
apply(ctx, {
  apiBase: `http://127.0.0.1:${balancePort}`,
  storePath: join(workdir, 'state.json'),
  pollIntervalMs: 3600000,
  importExisting: true,
})

// 等 bootstrap 跑完
for (let i = 0; i < 100; i += 1) {
  try {
    await readFile(join(workdir, 'state.json'), 'utf8')
    break
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 25))
  }
}

// ---- RPC 客户端 -------------------------------------------------------------
const rpcServer = http.createServer((req, res) => routeHandler(req, res))
await new Promise((resolve) => rpcServer.listen(0, '127.0.0.1', resolve))
const rpcBase = `http://127.0.0.1:${rpcServer.address().port}/__dsh-deepseek-keyring/rpc`

async function rpc(op, extra = {}) {
  const response = await fetch(rpcBase, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-dsh-keyring': '1' },
    body: JSON.stringify({ op, ...extra }),
  })
  return await response.json()
}

const failures = []
function check(name, condition, detail) {
  if (condition) {
    console.log(`  ok   ${name}`)
  } else {
    failures.push(name)
    console.log(`  FAIL ${name}${detail === undefined ? '' : ` — ${JSON.stringify(detail)}`}`)
  }
}

const activeRef = () => refs.get('DEEPSEEK_API_KEY')
const stateFile = async () => JSON.parse(await readFile(join(workdir, 'state.json'), 'utf8'))

// ---- 1. 首次启用：现有 Key 自动入池 ----------------------------------------
let state = (await rpc('state')).data
check('导入现有 Key', state.keys.length === 1 && state.active.masked.endsWith(MASTER.slice(-4)), state.keys)
check('显示余额', state.active.balance?.total === 5, state.active)
check('合计余额', state.totals.length === 1 && state.totals[0].amount === 5, state.totals)
check('掩码不含明文', !JSON.stringify(state).includes(MASTER), 'leak')

// ---- 2. 批量补充：有效期 / 无有效期 / 余额 0 / 无效 --------------------------
let added = (await rpc('add', { text: [
  `${KEY_EXP_LATE} 2027-12-31 晚到期`,
  `${KEY_EXP_EARLY} 2027-06-01 早到期`,
  KEY_PLAIN,
  KEY_EMPTY,
  KEY_BAD,
].join('\n') })).data
check('有效 Key 全部加入', added.added.length === 4 && added.added.every((item) => item.hidden === false || item.hidden === true), added.added)
check('无效 Key 被拒绝', added.rejected.some((item) => item.reason === 'invalid-key'), added.rejected)
state = added.state
check('余额 0 的 Key 被隐藏', state.keys.every((view) => view.masked !== `sk-…${KEY_EMPTY.slice(-4)}`), state.keys.map((view) => view.masked))
check('当前 Key 不变（还有额度）', state.active.masked.endsWith(MASTER.slice(-4)), state.active)
check('合计只算可见 Key', state.totals[0].amount === 11, state.totals)

// ---- 3. 当前 Key 用完后按“有到期日优先、到期日早优先”切换 -------------------
setBalance(MASTER, 0)
state = (await rpc('refresh')).data
check('主 Key 用尽后切到早到期的 Key', activeRef() === KEY_EXP_EARLY, state.active)
check('用尽的 Key 被隐藏', state.keys.every((view) => !view.masked.endsWith(MASTER.slice(-4))))

setBalance(KEY_EXP_EARLY, 0)
state = (await rpc('refresh')).data
check('第二把用尽后切到晚到期的 Key', activeRef() === KEY_EXP_LATE, state.active)

setBalance(KEY_EXP_LATE, 0)
state = (await rpc('refresh')).data
check('到期 Key 都用尽后切到无到期日的 Key', activeRef() === KEY_PLAIN, state.active)

// ---- 4. 到期日已过的 Key 自动隐藏 ------------------------------------------
const before = await stateFile()
before.entries.push({
  id: 'k99',
  ref: 'DEEPSEEK_KEYRING_K99',
  label: '已过期',
  expiry: '2020-01-01',
  addedAt: Date.now(),
  hidden: false,
  exhaustedAt: null,
  invalidAt: null,
  balance: { currency: 'CNY', total: 9, granted: 9, toppedUp: 0 },
  checkedAt: Date.now(),
  error: null,
})
refs.set('DEEPSEEK_KEYRING_K99', 'sk-expired-9999999999999999')
setBalance('sk-expired-9999999999999999', 9)
await import('node:fs/promises').then(({ writeFile }) => writeFile(join(workdir, 'state.json'), JSON.stringify(before)))
state = (await rpc('refresh')).data
check('过期 Key 不显示', state.keys.every((view) => view.label !== '已过期'), state.keys.map((view) => view.label))

// ---- 5. 欠费失败：余额还有就交回原链路，真欠费才换 --------------------------
async function fireRequestError(provider = 'deepseek-official', failure = { code: 'PAYMENT', status: 402, message: 'Insufficient Balance' }) {
  let nextCalled = false
  const action = await requestErrorListener(
    { provider, failure },
    async () => {
      nextCalled = true
      return undefined
    },
  )
  return { action, nextCalled }
}

const KEY_SPARE = 'sk-spare-666666666666666666'
setBalance(KEY_SPARE, 4)
await rpc('add', { text: KEY_SPARE })

// 5a. 其它异常不切换（超时 / 5xx / 限流 / 非本 provider）
for (const [name, provider, failure] of [
  ['超时不切换', 'deepseek-official', { code: 'TIMEOUT', message: 'stream idle timeout' }],
  ['5xx 不切换', 'deepseek-official', { code: 'SERVER', status: 503, message: 'upstream unavailable' }],
  ['限流不切换', 'deepseek-official', { code: 'RATE_LIMIT', status: 429, message: 'rate limited' }],
  ['其它 provider 不切换', 'yeta', { code: 'INSUFFICIENT_BALANCE', status: 402, message: '余额不足' }],
]) {
  const result = await fireRequestError(provider, failure)
  check(name, result.nextCalled === true && result.action === undefined, result)
}
check('异常之后 Key 未被换掉', activeRef() === KEY_PLAIN, activeRef() === KEY_PLAIN ? 'ok' : 'wrong-key')

// 5b. 官方「额度已用尽」但余额接口仍报正数残值：必须切换（原缺陷）
setBalance(KEY_PLAIN, 0.001)
const residual = await fireRequestError('deepseek-official', { code: 'SERVER', status: 402, message: '当前请求的额度已用尽' })
check('额度用尽且余额残留正数时仍切换', residual.action?.kind === 'retry', residual)
check('切换后当前 Key 变成备用 Key', activeRef() === KEY_SPARE, activeRef() === KEY_SPARE ? 'ok' : 'wrong-key')

// 5c. 只有文案、没有状态码也必须认得（先补一把，确保池里还有下一把）
const KEY_TEXT = 'sk-text-777777777777777777'
setBalance(KEY_TEXT, 6)
await rpc('add', { text: KEY_TEXT })
setBalance(KEY_SPARE, 0.004)
const textOnly = await fireRequestError('deepseek-official', { code: 'UNKNOWN', message: '当前请求的额度已用尽，请充值后重试' })
check('仅凭官方文案也切换', textOnly.action?.kind === 'retry', textOnly)

// 5d. 池子里没有可用 Key：交回原链路，不无限重试
setBalance(KEY_SPARE, 0)
const exhausted = await fireRequestError()
check('没有可用 Key 时交回原链路', exhausted.nextCalled === true && exhausted.action === undefined, exhausted)

// ---- 6. 同源闸门 ------------------------------------------------------------
const noHeader = await fetch(rpcBase, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{"op":"state"}' })
check('缺少自定义头被拒绝', noHeader.status === 403, noHeader.status)
const crossOrigin = await fetch(rpcBase, {
  method: 'POST',
  headers: { 'content-type': 'application/json', 'x-dsh-keyring': '1', origin: 'http://evil.example' },
  body: '{"op":"state"}',
})
check('跨站 Origin 被拒绝', crossOrigin.status === 403, crossOrigin.status)

// ---- 7. 重新粘贴同一把 Key 恢复 --------------------------------------------
setBalance(MASTER, 7)
const revived = (await rpc('add', { text: MASTER })).data
check('重新添加可恢复已隐藏的 Key', revived.added.some((item) => item.revived === true && item.hidden === false), revived.added)
state = revived.state
check('恢复后回到可见列表', state.keys.some((view) => view.masked.endsWith(MASTER.slice(-4))), state.keys.map((view) => view.masked))

const storeText = await readFile(join(workdir, 'state.json'), 'utf8')
const leaked = [MASTER, KEY_EXP_EARLY, KEY_EXP_LATE, KEY_PLAIN, KEY_EMPTY, KEY_SPARE].filter((key) => storeText.includes(key))
check('状态文件不含明文 Key', leaked.length === 0, leaked.length)

// ---- 8. 排序启发式：赠送余额临期先消耗，手填到期日仍最优先 -----------------
// 插件只在 bootstrap 读状态文件，所以这里换一个新实例 + 新状态文件，避免前面用例的残留。
const { writeFile: writeState } = await import('node:fs/promises')
const seeded = { version: 1, activeId: null, entries: [] }
seeded.entries = [
  { id: 'g1', ref: 'DEEPSEEK_KEYRING_G1', label: '无赠送', expiry: null, addedAt: 3, hidden: false, exhaustedAt: null, invalidAt: null, balance: { currency: 'CNY', total: 5, granted: 0, toppedUp: 5 }, checkedAt: null, error: null },
  { id: 'g2', ref: 'DEEPSEEK_KEYRING_G2', label: '有赠送', expiry: null, addedAt: 2, hidden: false, exhaustedAt: null, invalidAt: null, balance: { currency: 'CNY', total: 5, granted: 5, toppedUp: 0 }, checkedAt: null, error: null },
  { id: 'g3', ref: 'DEEPSEEK_KEYRING_G3', label: '手填临期', expiry: '2027-01-01', addedAt: 1, hidden: false, exhaustedAt: null, invalidAt: null, balance: { currency: 'CNY', total: 5, granted: 0, toppedUp: 5 }, checkedAt: null, error: null },
]
seeded.activeId = null
refs.set('DEEPSEEK_KEYRING_G1', 'sk-g1-11111111111111111111')
refs.set('DEEPSEEK_KEYRING_G2', 'sk-g2-22222222222222222222')
refs.set('DEEPSEEK_KEYRING_G3', 'sk-g3-33333333333333333333')
setBalance('sk-g1-11111111111111111111', 5)
setBalance('sk-g2-22222222222222222222', 5)
setBalance('sk-g3-33333333333333333333', 5)
const store2 = join(workdir, 'state2.json')
await writeState(store2, JSON.stringify(seeded))
const { apply: applyFresh } = await import('./index.js')
applyFresh(ctx, {
  apiBase: `http://127.0.0.1:${balancePort}`,
  storePath: store2,
  pollIntervalMs: 3600000,
  minRefreshGapMs: 3000,
  importExisting: false,
})
for (let i = 0; i < 100; i += 1) {
  const text = await readFile(store2, 'utf8').catch(() => '')
  if (text.includes('g3')) break
  await new Promise((resolve) => setTimeout(resolve, 25))
}
const reordered = (await rpc('state')).data
check('手填临期排第一', reordered.keys[0]?.label === '手填临期', reordered.keys.map((view) => view.label))
check('有赠送余额排第二', reordered.keys[1]?.label === '有赠送', reordered.keys.map((view) => view.label))
check('无赠送排最后', reordered.keys.at(-1)?.label === '无赠送', reordered.keys.map((view) => view.label))

// ---- 9. 请求前刷新：节流内不重复查，耗尽时请求前就换掉 ----------------------
check('注册了请求前刷新钩子', typeof requestListener === 'function')
let balanceHits = 0
const countingServer = balanceServer
countingServer.on('request', () => { balanceHits += 1 })

async function fireRequest() {
  return await requestListener({ turn: 1, step: 1 }, async () => 'CONFIG')
}
setBalance(activeRef(), 5)
const first = await fireRequest()
check('请求前刷新不改配置', first === 'CONFIG' && balanceHits >= 1, { first, balanceHits })
const hitsAfterFirst = balanceHits
await fireRequest()
check('节流窗口内不重复查余额', balanceHits === hitsAfterFirst, { hitsAfterFirst, balanceHits })

await new Promise((resolve) => setTimeout(resolve, 3300))
setBalance(activeRef(), 0)
const keyBefore = activeRef()
await fireRequest()
check('节流过后请求前发现耗尽即换 Key', activeRef() !== keyBefore, { keyBefore, after: activeRef() })

// ---- 10. 三种导出：有效 / 失效 / 全部 --------------------------------------
const g2Val = 'sk-g2-22222222222222222222'
const g3Val = 'sk-g3-33333333333333333333'
// 上一段把 active(g3) 用尽隐藏了，先恢复它；再把 g2 用尽造出一条失效记录。
setBalance('sk-g3-33333333333333333333', 5)
await rpc('add', { text: g3Val })
setBalance('sk-g2-22222222222222222222', 0)
await rpc('refresh')

const validOut = (await rpc('export', { scope: 'valid' })).data
check('有效导出含可用 Key', validOut.text.includes(g3Val), validOut.text)
check('有效导出不含已用完 Key', !validOut.text.includes(g2Val), validOut.text)
check('有效导出文件名', /^deepseek-keys-valid-\d{8}\.txt$/.test(validOut.filename), validOut.filename)

const deadOut = (await rpc('export', { scope: 'dead' })).data
check('失效导出含已用完 Key', deadOut.text.includes(g2Val), deadOut.text)
check('失效导出不含有效 Key', !deadOut.text.includes(g3Val), deadOut.text)

const allOut = (await rpc('export', { scope: 'all' })).data
check('全部导出两者都含', allOut.text.includes(g2Val) && allOut.text.includes(g3Val), allOut.text)
check('导出带格式说明注释', allOut.text.startsWith('#') && allOut.text.includes('格式'), allOut.text.slice(0, 80))
check('导出行数统计正确', allOut.count === allOut.text.trim().split('\n').filter((line) => !line.startsWith('#')).length, allOut.count)

await new Promise((resolve) => rpcServer.close(resolve))
await new Promise((resolve) => balanceServer.close(resolve))

console.log(failures.length === 0 ? '\nALL PASS' : `\nFAILED: ${failures.join(', ')}`)
process.exit(failures.length === 0 ? 0 : 1)
