# D1 压缩检查点（供压缩后的会话接手）

> 本文件存在的唯一目的：在真实会话压缩发生后，把「压缩后是否仍保持同一会话标识与同一绑定」这条证据补上。
> 压缩摘要由宿主生成、我们无法向其注入内容；但本文件在磁盘上，压缩后仍可读到。

## 0. 已观察到的事实（2026-11-04）

| 时点 | 事实 |
|---|---|
| 2026-11-03T12:58:34Z（快照写入时） | `$DSH_SESSION_ID = session-826cbd83-3b6e-4185-830e-2d87287e7c77` |
| 2026-11-04（本日两次真实压缩之后） | `$DSH_SESSION_ID` **仍是** `session-826cbd83-3b6e-4185-830e-2d87287e7c77` |

即：**真实压缩发生后，运行时没有换会话标识**。这条已记入 `validation.md` §71，并按人声明写入 `d1host` 夹具
`installation.json` 的 `session_profile.capability.evidence_refs`（`kind=compaction`，经部署预览写入，未手改运行时记录）。

同日的绑定键复核：用当前 `$DSH_SESSION_ID` 重算 `session.session_key()` 得到
`7eeebb6213f2c38f5d33c2d8ff7484c395544aee0ec602981340d78d61a0ddf7`，与磁盘上绑定文件名完全一致——
说明绑定键只由「身份来源 + 标识」派生，不依赖任何随压缩失效的上下文令牌。

## 1. 下一次压缩要核的事（照抄即可）

1. 读当前会话标识：`echo "$DSH_SESSION_ID"`，与 §0 的 `session-826cbd83-…` 比较。
2. 读绑定（夹具已移到 `/tmp` 之外，抗 `/tmp` 清空）：
   ```
   cd ~/.cache/wf-fixtures/d1host
   printf '%s' '{"session":{"provider":"host","identity":{"host_id":"dsh","session_id":"'"$DSH_SESSION_ID"'"},"instance_id":"<从上下文取到的 instance_id>","activation":{"enabled":true,"start_source":"human:resume","enabled_at":"2026-11-04T00:00:00Z"}},"inputs":{}}' \
     | /usr/bin/python3 .wf/bin/wf.py status --json
   ```
3. 判定：
   - 标识未变 **且** `facts.binding.object.id == 2026-1e1b84fdcff74a00bfc1b498b7215d78` → 「压缩后绑定未变」成立，写入 `validation.md` 下一空章。
   - 标识未变但 `instance_id` 不匹配（`WF_IDENTITY_UNRESOLVED`/`WF_BINDING_MISMATCH`）→ 属**压缩丢失实例标识**：按设计稿 §1.3 走人工核实出口，登记为框架行为而非缺陷；同时把这条例外写进实现稿。
   - 标识变了 → 该宿主压缩后换身份；`capability.status` 收回 `unknown`，附事实。

## 2. 当前绑定的快照（2026-11-04）

| 项 | 值 |
|---|---|
| 夹具 | `~/.cache/wf-fixtures/d1host`（host 路径）、`~/.cache/wf-fixtures/d1wf`（wf 签发路径） |
| 绑定键文件名 | `7eeebb6213f2c38f5d33c2d8ff7484c395544aee0ec602981340d78d61a0ddf7.json` |
| 绑定对象 | `2026-1e1b84fdcff74a00bfc1b498b7215d78` |
| `instance_id` | **不记录**（它是定位会话的凭据，写进仓库等于共享值）；压缩后从自己的上下文里取，取不到按 `WF_IDENTITY_UNRESOLVED` 走人工核实 |
| 已跑结论 | host 路径 **12/12**、wf 签发路径 **8/8**（`validation.md` §71） |

## 3. 边界与已知限制

- 压缩不可按需触发；本文件只能保证「一旦压缩发生，接手方知道该核什么」。
- `$DSH_SESSION_ID` 在同一进程内本身稳定，因此「压缩后标识未变」的力量有限：它证明**运行时没有因压缩换身份**，不证明宿主在进程重启/跨设备场景下的稳定性。报告口径照此写，不升级为「宿主身份稳定性已完全核实」。
- 绑定轴（跨压缩仍可解析）需**下一次**压缩才能观察；本次只补到「标识未变 + 绑定键可由标识确定性重算」。
