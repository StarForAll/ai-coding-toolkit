# 修复后独立复核

日期：2026-10-23。继续使用唯一任务 `dsh-trellis-full-usage-audit`。
本轮只审查外部修复并复跑验证；收尾阶段仅整理任务材料并按用户授权本地提交。

## 结论与范围

| 项目 | 最终判断 |
| --- | --- |
| F1：当前 DSH 兼容测试误失败 | 已真实修复。测试消息补齐 `source:{kind:'user'}`，符合精确 `0.2.1-rc.2` 的 `message.source.kind` 消费契约；增加 adapter 请求存在性断言，原有角色、spec、PRD、去重及泛描述边界断言全部保留。 |
| F2：headless profile 未安装插件 | 按任务记录中的实际用途关闭：该目录是待清理测试目录，不用于跑 Trellis，实际使用 web profile。这是范围澄清，不是补装或运行时修复。 |
| M1：headless 文本不路由命令 | 维持已接受的宿主限制，README 已给等价 shell 命令。 |
| 新问题 | 本次两处修改未发现需要处理的新问题。运行时代码、插件依赖声明和安装态未变，无需重建或重装插件。 |

实际宿主包与兼容 fixture 均为 DSH `0.2.1-rc.2`；源码和 web 安装插件均为
`0.1.7`；Node 为 `v24.20.0`。源码/安装态 `lib/` 的 `diff -rq` 退出 0。

## 独立执行结果

两条测试命令的工作目录均为 `dsh-plugins/dsh-trellis/`。

| 命令 | 结果 | 持久化证据 |
| --- | --- | --- |
| `pnpm test` | exit 0；350 tests / 346 pass / 4 skip / 0 fail；原 F1 两例通过 | [默认测试输出](post-fix-default.out) |
| `pnpm run test:compat 0.2.1-rc.2` | exit 0；隔离安装精确 host 后 350 pass / 0 skip / 0 fail | [兼容测试输出](post-fix-compat.out) |
| `diff -rq dsh-plugins/dsh-trellis/lib ~/.dsh/profiles/web/node_modules/dsh-trellis/lib` | exit 0；无差异 | 本轮命令结果，无输出 |
| `git diff --check` | exit 0 | 本轮命令结果，无输出 |

默认依赖锁定 DSH `0.2.0-rc.1`；四项 host 能力跳过不用于当前版本结论，
当前版本以无跳过的兼容集为准。兼容测试 fixture 为
`/tmp/dsh-trellis-compat-0.2.1-rc.2-RECCqU`。

## 故障对照

在 `/tmp/dsh-trellis-review-controls-XFm61j/` 建立临时测试副本，只读引用源码
`lib/` 和兼容 fixture 的依赖；未修改仓库测试或运行时代码。

| 临时变更 | 预期与实际 | 输出 |
| --- | --- | --- |
| 移除共享 user fixture 的 `source` 字段 | exit 1，2 fail；命中 `the child produced no model request`，证明旧消息格式仍被检出且诊断清楚 | [missing-source](post-fix-control-missing-source.out) |
| 把两次 `registerSubagentContext(...)` 注册替换为无操作 disposer | exit 1，1 fail；精确角色用例缺少角色上下文，证明 push 断言仍有效 | [missing-push](post-fix-control-missing-push.out) |
| 将泛描述用例的 descriptor 标签替换为精确 `trellis-agent-implement` | exit 1，1 fail；原“应保持 generic”断言检出角色上下文，证明负向边界断言仍有效 | [generic-label-became-role](post-fix-control-generic-label-became-role.out) |

归档副本中的两份故障输出仅去除行尾空格以通过差异检查，`/tmp` 原始输出保留。
三组均观察到预期失败，见 [机器摘要](post-fix-controls.json)。这些退出 1 是
主动构造的故障被正确检出，不是待处理的测试失败。

## 保留的限制与收尾

- 未因这两处修改重跑完整 CLI 套件；运行时代码未变，沿用原审计的真实 CLI/事件证据。
- Web UI、完整 Codex CLI 自动 hook 时序、真实模型服从性等原有未验证项继续保留。
- 上游 `.gitignore` 的 `+.bce-tool/` 既有变化仍在，归因仍有限；不是本次修复引入，未自行还原或修改上游。
- 用户已要求完结任务，授权仅做本地提交、不推送、保留其他文件。
- 工作提交仅包含测试修复、现有 DSH 用途说明和本任务材料；归档与日志使用 Trellis 原生脚本。
