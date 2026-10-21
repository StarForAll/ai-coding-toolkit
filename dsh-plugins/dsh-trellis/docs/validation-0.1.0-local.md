GATE: PASS

# Validation record — local dsh-trellis 0.1.0

- 日期：2026-10-21
- 版本：**0.1.0（版本号重置）**；重置前历史见 `validation-0.3.*-local.md`
- 范围：项目级 `dsh.dispatch_mode` 自动引导、inline 边界修复、inline 派发门禁、跨平台配置文档
- 运行时：DSH `0.2.1-rc.2`；Node `v24.20.0`；Trellis `0.7.0-beta.4`；Codex `0.163.0`
- 源码：`dsh-plugins/dsh-trellis`（Strategy A，就地修改）
- 临时项目：`/tmp/trellis-verify-20261021-1547`；独立 `DSH_HOME` + 本地 mock LLM

## 版本策略

- 从 `0.1.0` 重新开始；普通修复/功能/文档按 `0.1.0 → 0.1.1` 递增。
- 次版本/主版本仅用于重大变化（运行时或配置契约破坏、manifest/设置面破坏、需要重新验证集成的重写）。
- `package.json`、`README.md`、`LOCAL_CHANGES.md`、本记录必须一致；`pnpm run build:client`
  会把 `PLUGIN_VERSION` 重新盖进 `lib/client.js`。
- 规范位置：`.trellis/spec/platforms/dsh-workflow-behavior.md` 的 “Versioning Policy”。

## 一、项目级 `dsh.dispatch_mode` 自动引导

启用插件后，在首次解析项目状态之前，插件确保 `.trellis/config.yaml` 含
`dsh.dispatch_mode: inline`。

实现边界（`lib/project-defaults.js`）：

| 规则 | 行为 |
| --- | --- |
| 只补缺失键 | 已有 `dispatch_mode`（`auto` / `inline` / 带引号或注释）一律不改 |
| 保留原文件 | 注释、键顺序、CRLF/LF、末尾换行保持；只在 `dsh:` 段内插入或文末追加 |
| 不凭空创建 | `config.yaml` 缺失时跳过，不生成 Trellis 配置 |
| 不改写非块形态 | `dsh: {…}` / `dsh: auto` 视为用户所有，跳过 |
| 原子写入 | 同目录临时文件 + `rename`，失败清理临时文件 |
| 并发安全 | `.trellis/.runtime/.dsh-trellis-config.lock` 目录锁（运行时目录被 Trellis 忽略，崩溃不会污染工作树）；拿到锁后**重新读取并合并当前文件**，避免用旧快照覆盖并发写入或重复追加；10s 后视为陈旧锁并恢复 |
| 失败降级 | 只读/写入失败回落到库默认 `auto`，每个项目只警告一次 |
| 同轮生效 | 引导在状态解析前执行，并清理读缓存；第一轮面包屑已是 inline |

会话接线（`lib/session-composer.js`）：先 `resolveTrellisProject`（复用已解析 cwd 与配置的
markers），执行引导，再把同一个 root 交给 `resolveTrellisState`，避免两套根目录判断分叉。
配置 marker 被用户排除的项目不会被引导接管。

真实 DSH headless 会话验证：

| 用例 | 结果 |
| --- | --- |
| 无 `dsh:` 段、含注释的 config | 追加文档化注释块 + `dispatch_mode: inline`；原注释与 `spec_injection` 保留 |
| 首轮面包屑 | 826 字符，含 `<dsh-mode>`（说明首轮即 inline） |
| 第二轮（同会话） | 文件 sha256 与 mtime 均不变，无重复写入 |
| 显式 `dispatch_mode: auto` | 文件逐字不变，面包屑无 `<dsh-mode>` |
| 目录锁存在（单测） | 不写入、reason=`locked`；锁过期后可恢复写入 |
| 只读 fs（单测） | reason=`fs-readonly`，不抛错 |
| 锁内重读（单测） | 旧快照称“无 dsh 段”但文件已有：不重复追加；并发无关编辑 `a: 2` 被保留 |
| 列首注释边界（单测） | `dsh:` 段后的列首注释归属下一个键，新键插在注释之前 |
| 面包屑预算为 0（单测） | 不注入面包屑，但仍完成项目配置引导 |

## 二、inline 边界修复（0.3.10 候选，纳入 0.1.0）

1. `dsh.dispatch_mode: inline` 但 workflow 变体无 `*-inline` 块时，不再静默退回 auto 语义：
   横幅与块选择解耦，所有状态都追加 `<dsh-mode>`。与 Codex 在同输入下仍输出 `<codex-mode>` 对齐。
2. inline 模式下派发 `trellis-agent-implement` / `trellis-agent-check` 被守卫拒绝；
   `trellis-agent-research` 仍放行；`dsh.inline_allow_dispatch: true` 是项目级逃生口。

真实会话验证：

| 场景 | 结果 |
| --- | --- |
| 变体无 / 空 / 有 `planning-inline` 块 | 基础块 / 基础块 / inline 块，均带横幅 |
| `completed`（inline） | 无 `*-inline` 块，仍输出横幅 |
| inline 派发 implement | 拒绝：`Trellis inline mode: … dispatch is refused.` |
| inline + `inline_allow_dispatch: true` | 放行，子代理启动 |
| auto 回归 | 放行；面包屑正文仍与 Codex 逐字节相同 |

## 三、推送前构建钩子

- 新增 `scripts/git-hooks/pre-push` 与 `scripts/install-git-hooks.sh`；安装到
  `.git/hooks/pre-push`，由 Sonar 的 `core.hooksPath` 钩子链式调用（不替换现有管理器）。
- 只在推送提交涉及 `dsh-plugins/dsh-trellis` 时构建；构建后若 bundle 与 HEAD 不一致则中止
  推送并给出 `git add`/`git commit` 指令；`--no-verify` 是显式逃生口。
- 本地克隆验证：正常推送路径 exit 0；修改 `package.json` 版本触发重建后未提交时 exit 1，
  提示提交 `lib/client.js`。

## 四、测试

```
node --test "test/*.test.js"
tests 321 | pass 317 | fail 0 | skipped 4
```

新增：`test/project-defaults.test.js`（17 例：文本合并、幂等、CRLF、注释、显式值、缺失文件、
只读 shim、锁与陈旧锁）、composer 2 例（首轮引导生效、显式值不被覆盖）、
guard/config/workflow 的 inline 用例。

## 五、已知边界（有意保留）

- 非法 `dsh.dispatch_mode` 回落 `auto`（Codex 回落 `inline`）：避免笔误静默变成“禁止派发”。
- 已有 `dsh: {…}` 流式写法不迁移；用户可自行改为块写法后由插件继续维护。
- `trellis_wait` 成功文案保留 “settlement notice delivery is unverified”。
- `task.py start` 的 jsonl 门禁属于 Trellis CLI；inline 首次启动仍需 `--allow-empty-context`。
- bootstrap 每会话一次不变（安装态审查确认是预期设计）。

## 六、check 轮修正

- 发现并修复“读 → 等锁 → 写”竞态：写入前在锁内重读当前文件并重新合并，旧快照不再可能覆盖并发编辑或重复追加 `dsh:` 段。
- 修复 `maxBytes: 0` 时项目引导被跳过：配置引导属于“启用插件”，与是否渲染面包屑无关。
- 修复列首注释被误并进 `dsh:` 段：注释现在终止段并保留给下一个键。
- 两个 git 钩子脚本按仓库 Shell 规范统一 `#!/usr/bin/env sh`、`set -eu`、`fail()` 与 `ERROR:/WARN:/OK:` 前缀。
- 锁与临时文件从 `.trellis/` 迁到被 Trellis 忽略的 `.trellis/.runtime/`，崩溃残留不再污染工作树；
  8 路并发写入实测只生成一个 `dsh:` 段与一个 `dispatch_mode`。
