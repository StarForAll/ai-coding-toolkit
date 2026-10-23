# 执行计划：dsh-trellis 对等性全面验证

> 本清单的 Phase A 是本次授权的审计工作；Phase B 只有在用户看过完整报告并确认具体问题与方案后才可执行。两阶段共用当前唯一 Trellis 任务，不创建其他任务。

## Phase A：只读审计与隔离验证

- [x] A1. 用户批准规划；已用 inline 必需的 `task.py start --allow-empty-context` 启动，唯一任务 active。
- [x] A2. 版本/profile 安装形态核验，30 个 lib 哈希与源码一致；上游起始干净，最终只读边界异常已单独披露。
- [x] A3. 已核对上游 DSH/Codex configurator、fresh 生成物、任务身份、workflow/spec/subagent 与当前宿主契约。
- [x] A4. bce/fast-context 定位后本地精确跟踪；GitNexus 无本仓库/上游索引，未宣称图完整性。
- [x] A5. 当前 CLI fresh init 成功；临时项目只复用自动生成的 00-bootstrap-guidelines。
- [x] A6. 隔离 bare / trellis / web profile，只读引用实际安装包；未复制凭据，真实 profile 未修改。
- [x] A7. 主批次 24 调用及补充实验，29 项最终事件断言通过；实际 native compactNow、并发、push/wait 等通过。UI/真实模型等限制见报告。
- [x] A8. fresh Codex hooks 实际 payload 直调通过，清除 DSH/generic identity override；未运行完整 Codex CLI 模型会话，已明确标级。
- [x] A9. `pnpm test` 346 pass/4 skip；正确兼容入口 `pnpm run test:compat 0.2.1-rc.2` 原始 348 pass/2 fail。临时 fixture 根因实验 350 pass；仓库测试未修。
- [x] A10. 报告、证据索引、持久化摘要、兼容失败日志和复核脚本已完成。
- [x] A11. 主仓库只有当前任务新增和原有两项 untracked；源码/安装态 lib 一致。上游 `.gitignore` 出现 `+.bce-tool/`（疑似检索副作用，未完全归因、未还原），不能宣称其工作树全程不变。
- [x] A12. 审计报告已准备交付；停在用户确认问题与方案的闸门，不执行修复。

### 审计后决策与执行

- F1：已确认并修复 `test/native-subagent-push.test.js`：`user()` 补 `source:{kind:'user'}`，`requestText` 先断言至少一次模型请求；`pnpm test` 346 pass / 4 skip，`pnpm run test:compat 0.2.1-rc.2` 350 pass / 0 fail。仅测试文件变更，安装态无变化。
- F2：用户确认 `~/.dsh/profiles/headless` 是测试目录、后续删除，不用于跑 Trellis；不安装插件，判定关闭。
- M1：接受现状，不实施提示缓解；README 已给等价 shell 命令。
- Web UI、完整 Codex CLI、真实模型服从性等未验证项与上游 `.gitignore` 边界事件见 `research/verification-report.md`。
- 任务 manifest 校验退出 1：inline 刻意保持 implement/check JSONL 空，已按 Phase 1.4 用 `--allow-empty-context` 启动；不补造未消费上下文。

## Phase B：仅执行用户确认的修复

- [x] B1. 已记录确认范围：仅修复 F1 测试夹具；F2 按非 Trellis 使用目录关闭，M1 接受现状。
- [x] B2. F1 由外部会话修复，本轮只审查和独立验证；未修改插件运行时代码、安装态或上游。
- [x] B3. 独立复跑默认测试和精确当前 host 兼容测试；三组 `/tmp` 故障对照均按预期失败，安装态 `lib/` 与源码一致。运行时代码未变，不重复整套 CLI 实验；沿用 Phase A 的实际运行证据并保留其覆盖限制。
- [x] B4. 已更新修复后复核记录与证据。用户随后要求完结当前任务，并明确授权本地提交、不推送、保留其他文件。

### 最终复核与收尾范围

- 最终结论：F1 已真实修复；F2 为使用范围澄清；M1 为已接受的宿主边界。未发现本次修改引入需要处理的新问题。
- 复核证据：`research/post-fix-review.md` 及同目录 `post-fix-*` 输出。
- 本地工作提交仅包含测试修复、既有 DSH 用途说明和本任务材料；随后使用原生 `task.py archive` 与 `add_session.py` 完成归档和日志提交。
- 原有 `docs/capability-inventory.md`、`dsh-plugins/plugin-create.md` 不纳入提交；上游 `.gitignore` 的既有变化保持原样。

## 交付与质量门

- Phase A 的报告必须包含实际执行的命令和退出状态；任何未运行的步骤必须有原因和可替代证据。
- 不以测试数量、注册表项存在或 README 声明单独推断功能端到端可用。
- 不把 host limitation、Trellis 上游限制或部署选择误标成插件缺陷；如果插件能缓解边界，单列候选方案。
- 只有用户明确确认报告中的问题和方案后，才从 A12 转 B1。
- 最终是否需要修改共享 spec、归档或提交，依据实际结果和用户授权处理；不得因本计划自动扩大范围。
