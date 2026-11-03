/**
 * dsh-deepseek-keyring — Client half（浏览器侧）。
 *
 * 1. 在 `shell.overlay` 里放一个可拖拽的胶囊，显示当前 Key 余额与有效 Key 合计余额；
 *    拖到任意一边就收成窄握把，点一下展开，5s 后自动收回。
 * 2. 点开胶囊是弹窗：批量粘贴 Key、刷新余额、按「有效 / 失效 / 全部」三种范围导出。
 *
 * 界面数据走 Host 半边的同源路由，列表里只有掩码；只有导出时才取回明文。
 */

window.__ModuleLoader__.load({
  id: 'dsh-deepseek-keyring',
  factory(require) {
    const React = require('react')
    const h = React.createElement
    const ROUTE = '/__dsh-deepseek-keyring/rpc'
    const STYLE_ID = 'dsh-deepseek-keyring-styles'

    const DICT = {
      zh: {
        badgeTitle: 'DeepSeek Key 余额',
        current: '当前',
        total: '合计',
        noActive: '无可用 Key',
        loading: '读取中…',
        dialogTitle: 'DeepSeek 官方 Key',
        dialogSubtitle: '额度用完才换下一把；到期的先用。过期或用尽的 Key 只隐藏，不删除。',
        colStatus: '状态',
        colKey: 'Key',
        colExpiry: '到期',
        colBalance: '余额',
        statusActive: '使用中',
        statusReady: '可用',
        statusEmpty: '额度已用完',
        statusExpired: '已过期',
        grantedTag: '赠送额度',
        addTitle: '批量补充 Key',
        addHint: '每行一个：sk-xxx 或 sk-xxx 2026-12-31 备注',
        exportTitle: '导出',
        exportHint: '导出为可原样粘回的文本，含明文 Key。',
        exportValid: '导出有效 Key',
        exportDead: '导出失效/已用完',
        exportAll: '导出全部',
        exporting: '导出中…',
        exported: (n) => `已导出 ${n} 条`,
        addButton: '添加',
        adding: '添加中…',
        refresh: '刷新余额',
        refreshing: '刷新中…',
        close: '关闭',
        empty: '还没有 Key。把官方 Key 粘贴到下面，一行一个。',
        noRoute: 'Host 半边未生效：路由不可用',
        addedCount: (n) => `已加入 ${n} 把`,
        addedHidden: (n) => `${n} 把余额为 0，已隐藏`,
        rejectedCount: (n) => `${n} 行未加入`,
        revived: '重新启用',
        hiddenNote: (n) => `${n} 把已隐藏`,
        unverifiedNote: (n) => `${n} 把余额未知`,
        neverExpire: '长期',
        unknown: '—',
        poolFull: '池子已满',
        invalidKey: 'Key 无效',
      },
      en: {
        badgeTitle: 'DeepSeek key balance',
        current: 'Current',
        total: 'Total',
        noActive: 'No usable key',
        loading: 'Loading…',
        dialogTitle: 'DeepSeek official keys',
        dialogSubtitle: 'Switch only when the quota runs out; expiring keys go first. Expired or exhausted keys are hidden, never deleted.',
        colStatus: 'Status',
        colKey: 'Key',
        colExpiry: 'Expires',
        colBalance: 'Balance',
        statusActive: 'In use',
        statusReady: 'Ready',
        statusEmpty: 'Exhausted',
        statusExpired: 'Expired',
        grantedTag: 'Granted',
        addTitle: 'Add keys in bulk',
        addHint: 'One per line: sk-xxx or sk-xxx 2026-12-31 note',
        exportTitle: 'Export',
        exportHint: 'Exports paste-ready text including plaintext keys.',
        exportValid: 'Export usable',
        exportDead: 'Export dead',
        exportAll: 'Export all',
        exporting: 'Exporting…',
        exported: (n) => `${n} exported`,
        addButton: 'Add',
        adding: 'Adding…',
        refresh: 'Refresh',
        refreshing: 'Refreshing…',
        close: 'Close',
        empty: 'No keys yet. Paste official keys below, one per line.',
        noRoute: 'Host half is not active: route unavailable',
        addedCount: (n) => `${n} added`,
        addedHidden: (n) => `${n} with a zero balance were hidden`,
        rejectedCount: (n) => `${n} rejected`,
        revived: 're-enabled',
        hiddenNote: (n) => `${n} hidden`,
        unverifiedNote: (n) => `${n} unverified`,
        neverExpire: 'No expiry',
        unknown: '—',
        poolFull: 'Pool is full',
        invalidKey: 'Invalid key',
      },
    }

    const CSS = [
      '.dskr-badge{position:fixed;right:16px;bottom:84px;z-index:30;display:flex;align-items:center;gap:8px;',
      'padding:7px 12px;border-radius:999px;background:var(--dsw-alias-bg-overlay);',
      'border:.5px solid var(--dsw-alias-border-l2);color:var(--dsw-alias-label-primary);',
      'font-size:12px;line-height:1.2;font-family:inherit;cursor:pointer;pointer-events:auto;',
      'box-shadow:0 6px 20px rgba(0,0,0,.16);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px)}',
      '.dskr-badge{cursor:grab;touch-action:none;transition:opacity .16s,box-shadow .16s}',
      '.dskr-badge.is-dragging{cursor:grabbing;transition:none;box-shadow:0 10px 26px rgba(0,0,0,.28)}',
      '.dskr-badge.is-collapsed{width:14px;height:14px;padding:0;gap:0;justify-content:center;border-radius:999px;opacity:.6}',
      '.dskr-badge.is-collapsed:hover{opacity:1}',
      '.dskr-badge.is-collapsed .dskr-label,.dskr-badge.is-collapsed .dskr-amount,.dskr-badge.is-collapsed .dskr-sep{display:none}',
      '.dskr-badge:hover{border-color:var(--dsw-alias-brand-primary)}',
      '.dskr-badge:focus-visible{outline:2px solid var(--dsw-alias-brand-primary);outline-offset:2px}',
      '.dskr-dot{width:7px;height:7px;border-radius:50%;background:var(--dsw-alias-state-success-primary);flex:none}',
      '.dskr-dot[data-tone="warn"]{background:var(--dsw-alias-state-warn-primary)}',
      '.dskr-dot[data-tone="error"]{background:var(--dsw-alias-state-error-primary)}',
      '.dskr-dot[data-tone="idle"]{background:var(--dsw-alias-state-idle-primary)}',
      '.dskr-label{color:var(--dsw-alias-label-secondary)}',
      '.dskr-amount{font-variant-numeric:tabular-nums;font-weight:600}',
      '.dskr-sep{color:var(--dsw-alias-border-l2)}',
      '.dskr-backdrop{position:fixed;inset:0;z-index:60;display:flex;align-items:center;justify-content:center;',
      'background:rgba(0,0,0,.34);pointer-events:auto}',
      '.dskr-panel{width:min(580px,calc(100vw - 32px));max-height:min(76vh,680px);overflow:auto;',
      'background:var(--dsw-alias-bg-overlay);color:var(--dsw-alias-label-primary);',
      'border:.5px solid var(--dsw-alias-border-l2);border-radius:14px;padding:18px 20px 16px;',
      'font-size:13px;line-height:1.5;box-shadow:0 24px 64px rgba(0,0,0,.3)}',
      '.dskr-head{display:flex;align-items:flex-start;gap:12px;justify-content:space-between}',
      '.dskr-title{font-size:15px;font-weight:600;margin:0}',
      '.dskr-subtitle{margin:4px 0 0;color:var(--dsw-alias-label-secondary);font-size:12px}',
      '.dskr-summary{display:flex;flex-wrap:wrap;gap:10px 24px;margin:14px 0 4px}',
      '.dskr-summary-item{display:flex;flex-direction:column;gap:2px}',
      '.dskr-summary-key{font-size:11px;color:var(--dsw-alias-label-secondary)}',
      '.dskr-summary-value{font-size:14px;font-weight:600;font-variant-numeric:tabular-nums}',
      '.dskr-table{width:100%;border-collapse:collapse;margin-top:12px}',
      '.dskr-table th{text-align:left;font-size:11px;font-weight:500;color:var(--dsw-alias-label-secondary);padding:6px 8px;border-bottom:.5px solid var(--dsw-alias-border-l1)}',
      '.dskr-table td{padding:7px 8px;border-bottom:.5px solid var(--dsw-alias-border-l1);vertical-align:middle}',
      '.dskr-table tr:last-child td{border-bottom:none}',
      '.dskr-mask{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}',
      '.dskr-num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}',
      '.dskr-tag{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;',
      'border:.5px solid var(--dsw-alias-border-l2);color:var(--dsw-alias-label-secondary);white-space:nowrap}',
      '.dskr-tag[data-status="active"]{color:var(--dsw-alias-state-success-primary);border-color:currentColor}',
      '.dskr-tag[data-status="empty"],.dskr-tag[data-status="expired"]{color:var(--dsw-alias-state-warn-primary);border-color:currentColor}',
      '.dskr-empty{margin:14px 0;color:var(--dsw-alias-label-secondary);font-size:12px}',
      '.dskr-field{margin-top:16px}',
      '.dskr-field-label{font-size:12px;font-weight:600;margin-bottom:6px}',
      '.dskr-hint{font-size:11px;color:var(--dsw-alias-label-secondary);margin:0 0 6px}',
      '.dskr-textarea{width:100%;box-sizing:border-box;min-height:92px;resize:vertical;padding:8px 10px;',
      'border-radius:8px;border:.5px solid var(--dsw-alias-border-l2);background:var(--dsw-alias-bg-layer-1);',
      'color:var(--dsw-alias-label-primary);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;line-height:1.55}',
      '.dskr-textarea:focus{outline:none;border-color:var(--dsw-alias-brand-primary)}',
      '.dskr-actions{display:flex;align-items:center;gap:8px;margin-top:10px;flex-wrap:wrap}',
      '.dskr-spacer{flex:1}',
      '.dskr-btn{font:inherit;font-size:12px;padding:6px 12px;border-radius:8px;cursor:pointer;',
      'border:.5px solid var(--dsw-alias-border-l2);background:var(--dsw-alias-bg-layer-1);color:var(--dsw-alias-label-primary)}',
      '.dskr-btn:hover{border-color:var(--dsw-alias-brand-primary)}',
      '.dskr-btn:disabled{opacity:.55;cursor:default}',
      '.dskr-btn[data-variant="primary"]{background:var(--dsw-alias-brand-primary);border-color:transparent;color:#fff}',
      '.dskr-notice{margin-top:10px;font-size:12px;padding:8px 10px;border-radius:8px;',
      'border:.5px solid var(--dsw-alias-border-l2);background:var(--dsw-alias-bg-layer-1)}',
      '.dskr-notice[data-kind="error"]{color:var(--dsw-alias-state-error-primary);border-color:currentColor}',
      '.dskr-notice ul{margin:4px 0 0;padding-left:16px}',
      '.dskr-foot{margin-top:12px;font-size:11px;color:var(--dsw-alias-label-secondary)}',
    ].join('')

    function ensureStyles() {
      if (typeof document === 'undefined') return
      if (document.getElementById(STYLE_ID) !== null) return
      const element = document.createElement('style')
      element.id = STYLE_ID
      element.dataset.plugin = 'dsh-deepseek-keyring'
      element.dataset.pluginCss = STYLE_ID
      element.textContent = CSS
      document.head.appendChild(element)
    }

    async function callHost(op, extra) {
      const response = await fetch(ROUTE, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-dsh-keyring': '1' },
        body: JSON.stringify({ op, ...(extra ?? {}) }),
      })
      let payload = null
      try {
        payload = await response.json()
      } catch {
        payload = null
      }
      if (!response.ok || payload === null || payload.ok !== true) {
        const reason = payload !== null && typeof payload.error === 'string' ? payload.error : `HTTP ${response.status}`
        throw new Error(reason)
      }
      return payload.data
    }

    const POS_KEY = 'dsh-deepseek-keyring.position'
    const EDGE = 26

    /** 读取持久化的胶囊位置；没有或已失效时返回 null（走 CSS 默认的右下角）。 */
    function readPosition() {
      try {
        const raw = window.localStorage.getItem(POS_KEY)
        if (raw === null) return null
        const parsed = JSON.parse(raw)
        if (typeof parsed?.x !== 'number' || typeof parsed?.y !== 'number') return null
        return clampPosition(parsed, null)
      } catch {
        return null
      }
    }

    function writePosition(value) {
      try {
        if (value === null) window.localStorage.removeItem(POS_KEY)
        else window.localStorage.setItem(POS_KEY, JSON.stringify(value))
      } catch {
        /* 隐私模式下 localStorage 可能不可写 */
      }
    }

    /** 把位置夹进视口（留 4px 余量）。 */
    function clampPosition(value, element) {
      const width = element?.offsetWidth ?? 180
      const height = element?.offsetHeight ?? 34
      const maxX = Math.max(4, window.innerWidth - width - 4)
      const maxY = Math.max(4, window.innerHeight - height - 4)
      return { x: Math.min(Math.max(4, value.x), maxX), y: Math.min(Math.max(4, value.y), maxY) }
    }

    /** 是否贴在某一条边上（四条边任一）。 */
    function atEdge(value, width = 0, height = 0) {
      if (value === null) return false
      return (
        value.x <= EDGE ||
        value.y <= EDGE ||
        window.innerWidth - (value.x + width) <= EDGE ||
        window.innerHeight - (value.y + height) <= EDGE
      )
    }

    /** 触发一次浏览器下载。 */
    function downloadText(filename, text) {
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      setTimeout(() => URL.revokeObjectURL(url), 4000)
    }

    function money(balance) {
      if (balance === null || balance === undefined || typeof balance.total !== 'number') return DICT.zh.unknown
      const currency = typeof balance.currency === 'string' ? balance.currency : 'CNY'
      const symbol = currency === 'CNY' ? '¥' : currency === 'USD' ? '$' : ''
      const value = balance.total.toFixed(2)
      return symbol.length > 0 ? `${symbol}${value}` : `${value} ${currency}`
    }

    function totalsText(totals) {
      if (!Array.isArray(totals) || totals.length === 0) return money(null)
      return totals
        .map((item) => money({ currency: item.currency, total: item.amount }))
        .join(' · ')
    }

    function createStore() {
      let snapshot = { loading: true, data: null, error: null }
      const listeners = new Set()
      return {
        get: () => snapshot,
        set(next) {
          snapshot = { ...snapshot, ...next }
          for (const listener of listeners) listener()
        },
        subscribe(listener) {
          listeners.add(listener)
          return () => listeners.delete(listener)
        },
      }
    }

    function useStore(store) {
      const [snapshot, setSnapshot] = React.useState(store.get())
      React.useEffect(() => store.subscribe(() => setSnapshot(store.get())), [store])
      return snapshot
    }

    function useLocaleId(ctx) {
      const locale = ctx !== null && typeof ctx.get === 'function' ? ctx.get('locale') : undefined
      const read = () => {
        try {
          const active = locale?.getLocale?.()?.active
          return typeof active === 'string' ? active : 'zh'
        } catch {
          return 'zh'
        }
      }
      const [id, setId] = React.useState(read)
      React.useEffect(() => {
        if (locale === undefined || locale === null || typeof locale.subscribe !== 'function') return undefined
        return locale.subscribe(() => setId(read()))
      }, [locale])
      return id
    }

    /**
     * 挂载一个插件实例：store + 一个 shell.overlay 条目。
     * @param {object} ctx - Client cordis 上下文。
     */
    function mount(ctx) {
      ensureStyles()
      const store = createStore()

      const load = async (op) => {
        try {
          const data = await callHost(op ?? 'state')
          store.set({ loading: false, data, error: null })
          return data
        } catch (error) {
          store.set({ loading: false, error: error instanceof Error ? error.message : String(error) })
          return null
        }
      }

      function Badge() {
        const localeId = useLocaleId(ctx)
        const t = DICT[localeId.startsWith('zh') ? 'zh' : 'en']
        const { data, error, loading } = useStore(store)
        const [open, setOpen] = React.useState(false)
        const [draft, setDraft] = React.useState('')
        const [busy, setBusy] = React.useState(null)
        const [notice, setNotice] = React.useState(null)
        const [pos, setPos] = React.useState(readPosition)
        const [collapsed, setCollapsed] = React.useState(false)
        const [dragging, setDragging] = React.useState(false)
        const badgeRef = React.useRef(null)
        const dragState = React.useRef(null)
        const collapseTimer = React.useRef(null)
        const suppressClick = React.useRef(false)

        React.useEffect(() => {
          load('state')
          const timer = setInterval(() => load('state'), 20000)
          const onFocus = () => load('state')
          if (typeof window !== 'undefined') window.addEventListener('focus', onFocus)
          return () => {
            clearInterval(timer)
            if (typeof window !== 'undefined') window.removeEventListener('focus', onFocus)
          }
        }, [])

        React.useEffect(() => {
          if (!open) return undefined
          const onKey = (event) => {
            if (event.key === 'Escape') setOpen(false)
          }
          document.addEventListener('keydown', onKey)
          load('refresh')
          return () => document.removeEventListener('keydown', onKey)
        }, [open])

        React.useEffect(() => {
          if (open) {
            clearTimeout(collapseTimer.current)
            setCollapsed(false)
          }
        }, [open])

        React.useEffect(() => () => clearTimeout(collapseTimer.current), [])

        // 贴边折叠：拖到边界就收成一条窄握把；再次点击展开后 5s 自动收回。
        React.useEffect(() => {
          if (open || pos === null) return
          const element = badgeRef.current
          setCollapsed(atEdge(pos, element?.offsetWidth ?? 180, element?.offsetHeight ?? 34))
          const keepExpanded = () => setCollapsed(false)
          window.addEventListener('resize', keepExpanded)
          return () => window.removeEventListener('resize', keepExpanded)
        }, [pos, open])

        const armCollapse = (value) => {
          clearTimeout(collapseTimer.current)
          if (value === null) return
          const element = badgeRef.current
          if (!atEdge(value, element?.offsetWidth ?? 180, element?.offsetHeight ?? 34)) return
          collapseTimer.current = setTimeout(() => setCollapsed(true), 5000)
        }

        const onPointerDown = (event) => {
          if (event.button !== 0) return
          const element = badgeRef.current
          if (element === null) return
          const box = element.getBoundingClientRect()
          dragState.current = { id: event.pointerId, startX: event.clientX, startY: event.clientY, originX: box.left, originY: box.top, moved: false }
          suppressClick.current = false
          element.setPointerCapture?.(event.pointerId)
        }

        const onPointerMove = (event) => {
          const drag = dragState.current
          if (drag === null || drag.id !== event.pointerId) return
          const dx = event.clientX - drag.startX
          const dy = event.clientY - drag.startY
          if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 4) return
          drag.moved = true
          suppressClick.current = true
          setDragging(true)
          setCollapsed(false)
          setPos(clampPosition({ x: drag.originX + dx, y: drag.originY + dy }, badgeRef.current))
        }

        const onPointerUp = (event) => {
          const drag = dragState.current
          dragState.current = null
          badgeRef.current?.releasePointerCapture?.(event.pointerId)
          setDragging(false)
          if (drag === null || !drag.moved) return
          const element = badgeRef.current
          const settled = clampPosition({ x: drag.originX + (event.clientX - drag.startX), y: drag.originY + (event.clientY - drag.startY) }, element)
          setPos(settled)
          writePosition(settled)
          setCollapsed(atEdge(settled, element?.offsetWidth ?? 180, element?.offsetHeight ?? 34))
        }

        const onClick = () => {
          if (suppressClick.current) {
            suppressClick.current = false
            return
          }
          // 折叠态点一下是展开并重新计时；正常态点开/收回弹窗。
          if (collapsed) {
            setCollapsed(false)
            armCollapse(pos)
            return
          }
          setOpen((value) => !value)
        }

        const active = data?.active ?? null
        const keys = Array.isArray(data?.keys) ? data.keys : []
        const tone = error !== null ? 'error' : active === null ? (data === null ? 'idle' : 'warn') : 'ok'
        const badgeAmount = data === null ? (loading ? t.loading : t.noRoute) : active === null ? t.noActive : money(active.balance)

        const exportKeys = async (scope) => {
          if (busy !== null) return
          setBusy(`export:${scope}`)
          setNotice(null)
          try {
            const result = await callHost('export', { scope })
            downloadText(result.filename, result.text)
            setNotice({ kind: 'ok', exported: result.count, scope })
          } catch (failure) {
            setNotice({ kind: 'error', error: failure instanceof Error ? failure.message : String(failure) })
          } finally {
            setBusy(null)
          }
        }

        const submit = async () => {
          if (busy !== null) return
          const text = draft.trim()
          if (text.length === 0) return
          setBusy('add')
          setNotice(null)
          try {
            const result = await callHost('add', { text })
            if (result?.state) store.set({ data: result.state, error: null, loading: false })
            setNotice({ kind: 'ok', added: result?.added ?? [], rejected: result?.rejected ?? [] })
            setDraft('')
          } catch (failure) {
            setNotice({ kind: 'error', error: failure instanceof Error ? failure.message : String(failure) })
          } finally {
            setBusy(null)
          }
        }

        const refresh = async () => {
          if (busy !== null) return
          setBusy('refresh')
          setNotice(null)
          try {
            const data2 = await callHost('refresh')
            if (data2) store.set({ data: data2, error: null, loading: false })
          } catch (failure) {
            setNotice({ kind: 'error', error: failure instanceof Error ? failure.message : String(failure) })
          } finally {
            setBusy(null)
          }
        }

        const rows = keys.map((view) => {
          const statusText =
            view.status === 'active'
              ? t.statusActive
              : view.status === 'empty'
                ? t.statusEmpty
                : view.status === 'expired'
                  ? t.statusExpired
                  : t.statusReady
          const label = view.label ? ` · ${view.label}` : ''
          return h(
            'tr',
            { key: view.id },
            h('td', null, h('span', { className: 'dskr-tag', 'data-status': view.status }, statusText)),
            h(
              'td',
              { className: 'dskr-mask', title: label },
              `${view.masked}${label}`,
              typeof view.balance?.granted === 'number' && view.balance.granted > 0
                ? h('span', { className: 'dskr-tag', style: { marginLeft: 6 } }, t.grantedTag)
                : null,
            ),
            h('td', null, view.expiry ?? t.neverExpire),
            h('td', { className: 'dskr-num' }, money(view.balance)),
          )
        })

        const summary = (labelText, valueText) =>
          h(
            'div',
            { className: 'dskr-summary-item' },
            h('span', { className: 'dskr-summary-key' }, labelText),
            h('span', { className: 'dskr-summary-value' }, valueText),
          )

        const noticeText =
          notice === null
            ? null
            : notice.kind === 'error'
              ? notice.error
              : typeof notice.exported === 'number'
                ? t.exported(notice.exported)
                : [t.addedCount(notice.added.length), notice.rejected.length > 0 ? t.rejectedCount(notice.rejected.length) : null]
                    .filter((part) => part !== null)
                    .join('，')

        const hiddenAdded =
          notice !== null && notice.kind === 'ok' && Array.isArray(notice.added)
            ? notice.added.filter((item) => item.hidden === true).length
            : 0

        const panel =
          open === false
            ? null
            : h(
                'div',
                {
                  className: 'dskr-backdrop',
                  onMouseDown: (event) => {
                    if (event.target === event.currentTarget) setOpen(false)
                  },
                },
                h(
                  'div',
                  { className: 'dskr-panel', role: 'dialog', 'aria-modal': 'true', 'aria-label': t.dialogTitle },
                  h(
                    'div',
                    { className: 'dskr-head' },
                    h(
                      'div',
                      null,
                      h('h2', { className: 'dskr-title' }, t.dialogTitle),
                      h('p', { className: 'dskr-subtitle' }, t.dialogSubtitle),
                    ),
                    h(
                      'div',
                      { className: 'dskr-actions', style: { marginTop: 0 } },
                      h(
                        'button',
                        { className: 'dskr-btn', type: 'button', onClick: refresh, disabled: busy !== null },
                        busy === 'refresh' ? t.refreshing : t.refresh,
                      ),
                      h('button', { className: 'dskr-btn', type: 'button', onClick: () => setOpen(false) }, t.close),
                    ),
                  ),
                  h(
                    'div',
                    { className: 'dskr-summary' },
                    summary(t.current, active === null ? t.noActive : `${money(active.balance)} · ${active.masked}`),
                    summary(t.total, totalsText(data?.totals ?? [])),
                  ),
                  error !== null ? h('div', { className: 'dskr-notice', 'data-kind': 'error' }, error) : null,
                  rows.length > 0
                    ? h(
                        'table',
                        { className: 'dskr-table' },
                        h(
                          'thead',
                          null,
                          h(
                            'tr',
                            null,
                            h('th', null, t.colStatus),
                            h('th', null, t.colKey),
                            h('th', null, t.colExpiry),
                            h('th', { style: { textAlign: 'right' } }, t.colBalance),
                          ),
                        ),
                        h('tbody', null, rows),
                      )
                    : h('p', { className: 'dskr-empty' }, t.empty),
                  h(
                    'div',
                    { className: 'dskr-field' },
                    h('div', { className: 'dskr-field-label' }, t.exportTitle),
                    h('p', { className: 'dskr-hint' }, t.exportHint),
                    h(
                      'div',
                      { className: 'dskr-actions' },
                      h(
                        'button',
                        {
                          className: 'dskr-btn',
                          type: 'button',
                          onClick: () => exportKeys('valid'),
                          disabled: busy !== null,
                        },
                        busy === 'export:valid' ? t.exporting : t.exportValid,
                      ),
                      h(
                        'button',
                        {
                          className: 'dskr-btn',
                          type: 'button',
                          onClick: () => exportKeys('dead'),
                          disabled: busy !== null,
                        },
                        busy === 'export:dead' ? t.exporting : t.exportDead,
                      ),
                      h(
                        'button',
                        {
                          className: 'dskr-btn',
                          type: 'button',
                          onClick: () => exportKeys('all'),
                          disabled: busy !== null,
                        },
                        busy === 'export:all' ? t.exporting : t.exportAll,
                      ),
                    ),
                  ),
                  h(
                    'div',
                    { className: 'dskr-field' },
                    h('div', { className: 'dskr-field-label' }, t.addTitle),
                    h('p', { className: 'dskr-hint' }, t.addHint),
                    h('textarea', {
                      className: 'dskr-textarea',
                      value: draft,
                      spellCheck: false,
                      placeholder: 'sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\nsk-yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy 2026-12-31 备用',
                      onChange: (event) => setDraft(event.target.value),
                    }),
                    h(
                      'div',
                      { className: 'dskr-actions' },
                      h(
                        'button',
                        {
                          className: 'dskr-btn',
                          'data-variant': 'primary',
                          type: 'button',
                          onClick: submit,
                          disabled: busy !== null || draft.trim().length === 0,
                        },
                        busy === 'add' ? t.adding : t.addButton,
                      ),
                      h('span', { className: 'dskr-spacer' }),
                      h(
                        'span',
                        { className: 'dskr-foot' },
                        [
                          typeof data?.hiddenCount === 'number' && data.hiddenCount > 0 ? t.hiddenNote(data.hiddenCount) : null,
                          typeof data?.unverified === 'number' && data.unverified > 0 ? t.unverifiedNote(data.unverified) : null,
                        ]
                          .filter((part) => part !== null)
                          .join(' · '),
                      ),
                    ),
                  ),
                  noticeText === null
                    ? null
                    : h(
                        'div',
                        { className: 'dskr-notice', 'data-kind': notice.kind },
                        noticeText,
                        hiddenAdded > 0 ? h('div', null, t.addedHidden(hiddenAdded)) : null,
                        notice.kind === 'ok' && Array.isArray(notice.rejected) && notice.rejected.length > 0
                          ? h(
                              'ul',
                              null,
                              notice.rejected.slice(0, 8).map((item, index) =>
                                h('li', { key: `${index}-${item.reason}` }, `${item.line} — ${item.reason}`),
                              ),
                            )
                          : null,
                      ),
                ),
              )

        return h(
          React.Fragment,
          null,
          h(
            'button',
            {
              ref: badgeRef,
              className: `dskr-badge${collapsed ? ' is-collapsed' : ''}${dragging ? ' is-dragging' : ''}`,
              style: pos === null ? undefined : { left: `${pos.x}px`, top: `${pos.y}px`, right: 'auto', bottom: 'auto' },
              type: 'button',
              title: collapsed ? t.badgeTitle : `${t.badgeTitle}${error !== null ? ` · ${error}` : ''}`,
              'aria-haspopup': 'dialog',
              'aria-expanded': open,
              onPointerDown,
              onPointerMove,
              onPointerUp,
              onPointerCancel: onPointerUp,
              onClick,
            },
            h('span', { className: 'dskr-dot', 'data-tone': tone }),
            h('span', { className: 'dskr-label' }, t.current),
            h('span', { className: 'dskr-amount' }, badgeAmount),
            h('span', { className: 'dskr-sep' }, '|'),
            h('span', { className: 'dskr-label' }, t.total),
            h('span', { className: 'dskr-amount' }, data === null ? t.unknown : totalsText(data.totals ?? [])),
          ),
          panel,
        )
      }

      ctx.slots.inject('shell.overlay', () =>
        ctx.slots.register({ name: 'shell.overlay', id: 'deepseek-keyring', order: 60 }, Badge),
      )
    }

    return {
      inject: ['slots'],
      apply(ctx) {
        ctx.effect(() => {
          ensureStyles()
          return () => {
            const element = document.getElementById(STYLE_ID)
            if (element !== null) element.remove()
          }
        }, 'deepseek-keyring: styles')
        mount(ctx)
      },
    }
  },
})
