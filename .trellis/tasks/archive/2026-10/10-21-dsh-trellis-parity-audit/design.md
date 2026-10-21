# Design — dsh-trellis 平台能力对标验证

## 验证对象与真实装载链

- 用户会话使用 `web` profile：`~/.dsh/profiles/web/cordis.patch.yml` 含
  `- id: dsh-trellis` 条目；`~/.dsh/profiles/web/node_modules/dsh-trellis` 是指向
  `/home/xzc/projects/personal/ai-coding-toolkit/dsh-plugins/dsh-trellis` 的符号链接，
  因此"已安装插件"== 本仓库未提交目录的当前内容（版本 0.3.7）。
- 端到端验证不直接改 web profile，使用 `DSH_HOME=/tmp/...` + 从 headless 模板派生的
  临时 profile，把同一插件目录以本地路径加入，保证测的就是同一份代码。

## 对照基线（Codex / Claude 平台）

- 解析基线：`.claude/hooks/*.py`、`.codex/hooks/*.py` 中的 workflow-state 解析器
  （标签后必须紧跟换行的约束）。
- 语义基线：`.trellis/workflow.md` 的 TAG ↔ PHASE 契约 + `.claude/.codex` 的
  spec / subagent 注入实现。
- 判定标准：同一 `workflow.md`、同一任务状态，DSH 侧注入给模型的文本与 Codex 侧
  hook 输出应等价（允许平台措辞差异，不允许语义缺失或跨块污染）。

## 证据等级

| 级别 | 定义 |
| --- | --- |
| E1 实测 | 真实执行插件代码 / 真实 DSH 进程 / 真实 hook，输出可复现 |
| E2 源码 | 读取实现并静态推导，未运行 |
| E3 声明 | 文档、测试名、作者声明 |

结论只用 E1；E2 需标注为推断；E3 仅作线索。

## 取证方法

1. 单元级：`node --input-type=module` 直接 import `lib/workflow.js` 跑真实
   `.trellis/workflow.md`；Python 侧跑 `.codex/hooks` 解析器同文件。
2. 会话级：`DSH_HOME=/tmp/... dsh headless "<prompt>"`，读取会话 JSONL 中
   `source.kind=dsh-trellis` 的消息，测量模型可见文本。
3. 插件级：运行插件自带 `node --test`，确认基线未被破坏（只作辅助，不作结论依据）。
4. 边界级：构造 planning / in_progress / task_error / stale / completed 五种状态与
   损坏 task.json、缺失指针等异常输入。

## 交付物

- 每个子任务一份 `findings.md`（证据 + 判定）。
- 父任务 `report.md`：问题清单（确认 / 未确认 / 通过）、影响面、修复建议（不实施）。
- 用户确认后再进入修复阶段（独立任务）。

## 风险与回滚

- 真实 DSH 会话可能写 `~/.dsh/sessions`；通过独立 `DSH_HOME` 隔离。
- 临时项目全部位于 `/tmp/dsh-trellis-audit-*`，可整体删除。
- 不触碰用户未被跟踪的工作区文件。
