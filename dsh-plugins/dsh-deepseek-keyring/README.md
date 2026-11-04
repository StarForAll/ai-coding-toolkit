# dsh-deepseek-keyring

多把 DeepSeek 官方 API Key 的池子：右下角常驻一个余额胶囊，当前 Key 额度用完后自动换下一把，点开胶囊可以批量补充 Key。

## 行为

1. **一次只用一把 Key。** 生效的 Key 就是官方 provider（默认 `deepseek-official`）读取的凭证引用 `DEEPSEEK_API_KEY`。切 Key 时改写这个引用的值，provider 每次请求都会重新解析，所以下一轮请求就用上了新 Key，不需要重启。
2. **只有当前 Key 额度用完才切。判定只看余额，不看报错。**
   - 切：余额接口返回 `is_available: false` 或余额 ≤ 0；或模型请求明确报「额度/余额用尽」（含有该文案、`INSUFFICIENT_BALANCE` 一类的 code、或 HTTP 402）。
   - 不切：超时、传输失败、5xx、限流、Key 鉴权错误，一律交回 DSH 自己的重试/报错逻辑。
   - 明确欠费的信号**不会被回查到的正数余额否决**：官方扣费与余额接口有时间差，用尽瞬间常残留 0.00x。
   - 没有手动切换入口。
3. **切换优先级（临期先用）**：手填的到期日最早者最优先；其次是有赠送余额（`granted_balance > 0`，官方赠送额度带期限，属于自动识别的临期近似）；最后才是其余 Key，按加入顺序。手填始终压过启发式。
4. **余额尽量实时**：界面每 5s 拉一次状态，每次拉取都会顺带查一次当前 Key（同一 5s 闸门），所以数字会自己往前走，不用手动点刷新。全池仍按 20s 轮询，模型请求前也会走同一条闸门。查询只发 HTTP、失败不影响请求。
5. **显示与位置**：胶囊 = `当前 Key 余额 | 所有有效 Key 合计余额`。灰色/黄色点表示没有可用 Key 或读取失败。胶囊可拖拽到任意位置并记住。**四条边行为一致**：停在任意一边都不会立刻收起，停够 5s 才收成一条同宽高、同边框同底色的窄握把，并**紧贴到那条边上**（收起态不留缝）；期间离开边界就保持展开。点握把只把余额摊开看（不出弹窗），若仍在边上 5s 后再次收起；摊开状态下再点一下才打开弹窗。拖离边界则一直展开。
6. **弹窗**：点胶囊打开，点弹窗外面或按 Esc 关闭。这里只做查看、补充与导出，不提供手动切换。导出分三种范围——有效 Key、失效/额度用完的 Key、全部 Key——导出的是可原样粘回补充框的文本，**含明文 Key**。上半部分是当前 Key 与合计、可用 Key 列表（状态 / 掩码 Key / 到期日 / 余额，**每页 5 条**，超过 5 条出现翻页条，打开弹窗回到第 1 页）；下半部分是导出按钮与批量补充输入框。
7. **隐藏而不是删除**：余额用完、Key 失效（401/403）、超过到期日的条目只打 `hidden` 标记，记录和凭证都保留。把同一把 Key 再粘一次即可恢复（会重新查余额）。
8. **复查隐藏的 Key**：弹窗右上角有「检查隐藏」按钮，逐个复查已隐藏条目——余额仍大于 0 的恢复回可用队列，其余保持隐藏。结果用一个 2s 后自动消失的小提示浮层报出，不打断弹窗。**到期日已过但确实还有额度的，恢复时会把到期日清掉**（到期日该作废、余额说明官方仍计它的额度，冲突时以余额为准，否则刚恢复就会被过期判定再藏回去）。

> `DEEPSEEK_API_KEY` 由本插件托管：轮询发现它和当前 Key 不一致时会改回当前 Key。想换 Key 请在弹窗里操作，不要直接在 Models 页面改这个引用。
>
> 安装后刷新一次页面：右下角胶囊由浏览器侧模块渲染，刷新后才会出现（位置在 `dsh-toolbox-ui` 圆形按钮上方，避免遮挡）。

## 批量补充格式
每行一把，`#` 开头的行忽略：

```
sk-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
sk-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb 2026-12-31
sk-cccccccccccccccccccccccccccccccc 2026-06-30 备用
```

第二列是可选的到期日（`YYYY-MM-DD`，当天 23:59:59 后视为过期），其余列合并为备注。加入时会先向官方余额接口校验：401/403 视为无效并拒绝；查不到余额（网络问题）仍然加入，标记为「余额未知」。

## 配置（`cordis.patch.yml`）

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `provider` | `deepseek-official` | 受管的官方 provider 路由 |
| `credentialRef` | `DEEPSEEK_API_KEY` | 官方 provider 读取的凭证引用名 |
| `apiBase` | `https://api.deepseek.com` | 余额接口站点根 |
| `balancePath` | `/user/balance` | 余额接口路径 |
| `pollIntervalMs` | `20000` | 全池余额轮询间隔（5s–1h） |
| `minRefreshGapMs` | `5000` | 请求前刷新的最小间隔（1s–60s） |
| `refreshOnActivity` | `true` | 是否在模型请求前做节流刷新 |
| `requestTimeoutMs` | `15000` | 单次余额请求超时 |
| `storePath` | 空 = `$DSH_HOME/deepseek-keyring.json` | 池元数据文件 |
| `importExisting` | `true` | 首次启用时把当前在用的官方 Key 收进池子 |
| `maxKeys` | `50` | 池子上限（含已隐藏条目） |

## 数据与安全

- Key 本体写在 credentials 服务里（`$DSH_HOME/.credentials.yaml`，0600），每把 Key 一个引用 `DEEPSEEK_KEYRING_K<n>`；当前生效的一把同时写入 `DEEPSEEK_API_KEY`。
- `$DSH_HOME/deepseek-keyring.json`（0600）只存元数据：引用名、备注、到期日、余额快照、隐藏标记。
- 浏览器半边通过同源路由 `/__dsh-deepseek-keyring/rpc` 读写，返回的 Key 一律是掩码（`sk-…abcd`），接口不回明文；路由要求同源 + `x-dsh-keyring` 自定义头。
- 日志里不打印 Key。

## 文件

- `index.js` — Host 半边：池状态、余额轮询、切换、`agent/request-error` 欠费换 Key、同源 RPC 路由。
- `client.js` — 浏览器半边：`shell.overlay` 里的右下角胶囊与弹窗。
- `cordis.patch.yml` — 插入一条 Loader 行。
