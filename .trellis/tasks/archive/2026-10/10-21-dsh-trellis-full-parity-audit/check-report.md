# Check Report — 审计任务自查

> 本任务只做验证与报告，没有修改插件源码、Trellis 上游、DSH 安装或用户 profile。因此本轮 check 的重点是证据完整性、报告一致性、无越界改动与无凭据泄露。

## 1. 变更范围

`git status --short --branch`：

```
## main...origin/main
?? .trellis/tasks/10-21-dsh-trellis-full-parity-audit/
?? docs/capability-inventory.md      # 用户既有未跟踪文件，未触碰
?? dsh-plugins/plugin-create.md      # 用户既有未跟踪文件，未触碰
```

- 本任务只新增 `.trellis/tasks/10-21-dsh-trellis-full-parity-audit/`。
- `dsh-plugins/dsh-trellis/**`、`.trellis/spec/**`、`.codex/**`、用户 profile 均无改动。
- `git diff --check` 通过。

## 2. 自动化检查

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 插件单测 | 321 tests / 317 pass / 0 fail / 4 skip | `/tmp/trellis-dsh-parity-20261021/scenarios/s0b-tests.txt` |
| 安装态哈希 | host/client/patch 三组一致 | `s0-installed.txt` |
| 隔离 DSH smoke | mock LLM + headless 正常 | `smoke/` |
| Codex hook 对照 | in_progress 正文逐字节相同；spec 文案等价 | `s43-codex-inprogress.txt`、`codex-spec-out.json` |
| 无插件对照 | 0 注入 / 0 trellis 工具 | `s39-control/`、`s39b-control-subagent/` |
| 证据文件齐全 | 关键场景目录/文件均存在 | 抽查 14 项全部 OK |
| 敏感值扫描 | 任务目录无 `sk-`/token/私钥值；误报仅为 `task-error` 等词 | grep |

## 3. 报告一致性复核

- `findings/07-issues.md` 总览原写 “P3：6 项” 但正文有 7 项；已改为 7，并补齐总览中的 wait 条目。
- `report.md` 的 “4 P2 + 6 P3” 与 `07-issues.md` 的编号一致（P3-1..P3-4、P3-6、P3-7；P3-5 已撤销）。
- P2-1/P2-2/P2-3/P2-4 的 file:line、证据目录与复现描述均可在本机复核。
- 未把未验证项写成通过：Web 设置页、真实 slash、压缩/clear 重注入、第二插件通知、真实模型遵循率、上游 0.1.13 均明确列为“未验证”。

## 4. 发现的问题（自查层面）

| 项 | 处理 |
| --- | --- |
| 问题数量不一致（6 vs 7） | 已修报告文本 |
| 证据目录引用大小写/路径 | 抽查关键路径存在；未发现断链 |
| 临时测试状态污染 `~/.trellis/spec-inject` | 本轮 Codex spec 测试误用默认状态目录，已删除本轮创建的 `session_codex-spec-test.jsonl`；未触碰其它既有分片 |
| 临时目录/进程 | mock 进程已无残留；`/tmp/trellis-dsh-parity-20261021` 与 `/tmp/dsh-parity-home-20261021` 保留供复核 |

## 5. 未做 / 不做

- 未修改 `.trellis/spec/`：本轮是审计，且修复方案未经用户确认；把“已知缺陷”写进项目规范属于修复/契约变更，留到确认后执行。
- 任务未归档：当前 `main == base_branch`，`task.py archive` 会被 Trellis 的 PR 元数据门禁拒绝；插件代码由用户手动提交。
- 未安装第二个 Trellis 插件到用户 profile；未读取 Web 认证 token。

## 6. 结论

**PASS WITH LIMITATIONS**：

- 证据链足以支撑主链路“基本等价 + DSH 补足”的结论；
- 4 个 P2、6 个 P3 均有 E1/E2 证据或明确标注；
- 没有越界修改、没有凭据泄露、没有把未验证项伪装成通过；
- Web UI/真实 slash/压缩、第二插件通知、真实模型遵循率仍是明确边界，需用户决定是否另开验证或修复任务。

---

## 7. 修复轮自查（0.1.1）

- 单测：`340 tests / 336 pass / 0 fail / 4 skipped`。
- client bundle：`pnpm run build:client` 成功，`PLUGIN_VERSION = "0.1.1"`。
- 真实 DSH E2E：零块 fallback、普通 Git 静默、flow-style inline、命令归一、research spec-tree、角色契约、wait 超时均通过。
- 版本检查：真实 GitHub 200；挂起 feed 10ms 超时返回 200 partial，UI 不再收到原始 `This operation was aborted`。
- 变更范围：`dsh-plugins/dsh-trellis/{lib,src,test,README.md,LOCAL_CHANGES.md,docs/package.json}` 与 `.trellis/spec/platforms/dsh-workflow-behavior.md`；未改用户 profile。
- 用户已提交 `5baa8d7` 与 `bca5a15` 并更新 web profile；当前 Web 进程已加载新 bundle（进程启动在安装文件之后）。
- P3-5 已按用户确认撤销；P3-7 已改为版本检查 abort 并修复。

## 8. Check 轮发现并修复

| 发现 | 证据 | 修复 |
| --- | --- | --- |
| `fetchText` 构造 `UpstreamError` 时未带 HTTP status，导致 release REST 回退无法把 404 识别为“无 release” | `test/upstream.test.js` 新增回退用例首次失败 | 传入 `response.status`；404 归一为 null |
| `trellis_wait` 超时只覆盖 settlement 等待，目录查询挂起时仍无界 | 代码审查 | 超时 AbortController 合并进整个 execute 的 signal，目录查询与等待共享超时 |
| inline 启动提示写 `task.py start`，未给出仓库内实际路径 | 代码审查 | 改为 `python3 ./.trellis/scripts/task.py start ...` |
| 缺失 workflow 与“无匹配块”共用 fallback 文案，不够准确 | 代码审查 | 新增 `MISSING_WORKFLOW_BREADCRUMB` |

修复后复跑：`340 tests / 336 pass / 0 fail / 4 skip`；真实 GitHub 通过 REST 回退返回 commit/release；安装态 0.1.1 的 research/fallback E2E 通过。
