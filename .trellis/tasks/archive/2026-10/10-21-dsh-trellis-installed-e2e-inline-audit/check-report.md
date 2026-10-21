# Check report — 0.1.0 改动复核

- 任务：`10-21-dsh-trellis-installed-e2e-inline-audit`
- 复核方式：`trellis-check`（inline 模式，主会话直接检查）
- 结论：**PASS（修复 3 个实质问题 + 2 个卫生/规范问题）**

## 范围

`dsh-plugins/dsh-trellis` 的 0.1.0 改动（自动引导、inline 边界/门禁、版本重置、文档）、
`scripts/git-hooks/pre-push`、`scripts/install-git-hooks.sh`、`.trellis/spec` 与 `AGENTS.md`。

## 发现与处理

| # | 问题 | 级别 | 处理 |
| --- | --- | --- | --- |
| 1 | 读→等锁→写竞态：旧快照在拿到锁后仍被写入，可能重复追加 `dsh:` 段或覆盖并发编辑 | 高（正确性） | 锁内重读当前文件并重新合并；新增 2 个回归用例 |
| 2 | `maxBytes: 0` 时项目配置引导被跳过 | 中（功能缺口） | 引导移到预算早退之前；新增 composer 用例 |
| 3 | `dsh:` 段后的列首注释被并入段内，新键插入破坏注释归属 | 低（格式） | 段在列首注释处结束；新增用例 |
| 4 | 两个 Shell 钩子未遵循仓库 Shell 规范（shebang、`fail()`、输出前缀） | 低（规范） | 统一为 `#!/usr/bin/env sh` + `set -eu` + `fail()` + `ERROR:/WARN:/OK:` |
| 5 | 锁与临时文件写在 `.trellis/` 下，崩溃残留会污染工作树 | 低（卫生） | 迁移到被 Trellis 忽略的 `.trellis/.runtime/`；E2E 确认运行后无锁残留 |

## 未改动的判断项

- 非法 `dsh.dispatch_mode` 继续回落 `auto`（与 Codex 的 `inline` 不同）：更保守，已记录。
- `task.py start` 的 jsonl 门禁属于 Trellis CLI，插件仅在文档中给出 `--allow-empty-context`。
- `trellis_wait` 的 “settlement notice delivery is unverified” 保留：DSH 只能证明执行结算。
- bootstrap 每会话一次：用户确认保留。

## 验证

```
node --test "test/*.test.js"   → 321 tests / 317 pass / 0 fail / 4 skip
pnpm run build:client          → 构建前后 sha256 一致（可复现）
真实 DSH 会话                  → 首轮项目引导 + `<dsh-mode>`；显式 auto 不变
pre-push 钩子（临时克隆）      → 正常推送 exit 0；未提交的重建 exit 1；无插件改动跳过
git diff --check               → 通过
```
