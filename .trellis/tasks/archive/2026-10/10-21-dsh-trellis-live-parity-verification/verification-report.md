# 验证报告：dsh-trellis 0.1.1 全链路实际调用验证

日期：2026-10-21
任务：`.trellis/tasks/10-21-dsh-trellis-live-parity-verification`
环境：dsh 0.2.1-rc.2（/softwares/nodeNpm/nodejs/bin/dsh）；插件 dsh-trellis@0.1.1
（web profile git 快照安装）；trellis CLI 0.7.0-beta.4（全局安装）；
Trellis 源码 ~/projects/other/Trellis。

## 验证方法与证据等级

- **真实 dsh 会话**（最强证据）：新建临时 profile `trellis-headless`
  （dsh-base + dsh-headless + dsh-trellis，安装来源与 web profile 相同 git 快照），
  在 `/tmp/dsh-trellis-verify/` 下的临时项目跑真实 LLM 会话
  （deepseek-flash），从 `~/.dsh/sessions/` 的 session.v4.jsonl.zstd 事件日志取证。
- **真实插件代码 + 真实项目**（中证据）：node 直载已安装插件的命令处理器，
  对临时项目实际执行（/trellis-status 等）。
- **插件自带测试**（补充证据，不作通过依据）：340 tests，336 pass，0 fail，4 skip
  （skip 均为 alpha 宿主 API 门槛测试）。
- 临时项目：proj-basic（git + trellis init --dsh）、proj-nogit（无 .git）、
  proj-plain（无 Trellis）。
- 插件自述文档（README/LOCAL_CHANGES）仅用作"声称清单"来源，不作为通过证据。

## C1–C10 逐项结论

| # | 能力 | 结论 | 证据摘要（证据等级） |
|---|------|------|---------------------|
| C1 | 每轮面包屑 | **通过** | 真实会话事件日志：no_task 面包屑首轮注入（seq10）；任务 start 后 in_progress-inline 面包屑（seq73）；同状态后续轮不重复（turns 2–4 零注入）；`no-trellis` 跳过生效（turn4 无注入且模型确认）；状态映射 planning/in_progress/task_error（故意损坏 task.json 后 seq68）/completed（seq93）全部实测出现（真实会话） |
| C2 | 会话身份隔离 | **通过** | 三个会话指针并存且互不串扰：pi 会话→verify-a、dsh 会话A→verify-a、dsh 会话B→verify-b（.trellis/.runtime/sessions/ 三个分片）；task.py 输出 `Source: session:dsh_<id>`；DSH_TRELLIS_CONTEXT_ID 在 dsh shell 中实测为 `dsh_session-<id>`（真实会话） |
| C3 | 子代理 + trellis_wait | **通过** | trellis_wait 工具真实注册（request/header 工具表）；成功路径实测：`subagent <id> completed; settlement notice delivery is unverified; inspect its report...`（诚实措辞，不承诺通过）；错误/max-tokens/refusal/未知映射由单元测试覆盖（fail-closed 断言存在且通过）（真实会话+单元） |
| C4 | 子代理上下文 push | **通过** | 子代理会话（origin: subagent）首步收到 `kind=dsh-trellis form=subagent-context` 消息：含 `<!-- trellis-hook-injected -->` 前导、角色契约（SKILL.md 正文，pull-only 段被替换为 push 版 Task Context 段）、Active task 行、curated context（implement.jsonl 无条目时的降级提示 + prd.md 内联）；子代理无面包屑、无 bootstrap（符合设计）（真实会话） |
| C5 | /trellis 命令面 | **通过** | 真实插件代码 + 真实项目执行：/trellis-status（任务+git 状态+Source）、/trellis-finish（只读清单）、/trellis-doctor（8 项诊断全输出，检测到 1 个 spec 声明 paths）；非 Trellis 项目返回明确错误（真实代码执行） |
| C6 | dispatch_mode 引导 | **通过** | proj-nogit（无 .git、无 dsh 键）挂载后 config.yaml 自动追加 `dsh: dispatch_mode: inline`（带注释，diff 仅 6 行新增）；显式 `auto` 不被覆盖（前后 diff 为空）；无 .git 项目仍注入面包屑（projectRootMarkers 含 .trellis）（真实会话+diff） |
| C7 | spec 注入 | **通过** | write 触碰 src/app.js → tools/pre-execute deny-once（tool result isError=true，reason 含完整 spec 正文）→ 重试放行；状态分片持久化到 `.trellis/.runtime/spec-inject/<session>.json`；同会话不重复 deny；`tools: [Edit, Write, Read]` 后 read 触发 post-execute ticket（下一请求送达 spec-context 消息）；compaction 重置由单元测试覆盖（真实会话+单元） |
| C8 | bootstrap 一次性 | **通过** | 新会话 no_task 首轮注入 `<trellis-bootstrap>` 一次（seq11）；后续轮不再出现（即使状态回到 no_task 的会话也不重复）；子代理永不注入（真实会话） |
| C9 | 非 Trellis 项目 | **通过** | proj-plain 中插件运行但零 dsh-trellis 消息；/trellis-status 返回 "No Trellis project found"（真实会话） |
| C10 | init 双向一致性 | **通过** | trellis init --dsh 产物（.dsh/skills/trellis-agent-{implement,check,research}/SKILL.md、trellis-start/continue/finish-work 技能、DSH.md）与插件读取路径逐一对齐；task.py current --json 退出码契约实测（exit 0 带 payload）；旧版 --source 回退由代码+单元覆盖；Trellis 源码 active_task.py 实测优先解析 DSH_TRELLIS_CONTEXT_ID（真实产物+源码比对） |

## 与 Codex 效果对照（基准 A）

三条主链路对齐情况（以本仓库 .codex/ 部署契约 + Trellis 上游 hooks 为基准）：

1. **无任务 bootstrap**：对齐，差异为 DSH 每会话一次 vs Codex 每轮一次——README
   已声明的有意设计选择，实测行为与声明一致。
2. **路径级 spec 注入**：对齐。deny-once（Edit/Write）、ticket（read 工具经
   post-execute）、持久化、压缩重置全部实测或单元覆盖。已知差异（read 不能先阻断）
   为 DSH 事件形状所致，README 声明属实。
3. **子代理上下文 push**：对齐。角色契约 + curated context + Active task 回退
   实测可见；pull 路径（child-side skill 加载）仍保留且可用。

## 弥补 DSH 不足（基准 B）

不装插件（plain headless，同项目实测）时缺失：面包屑、bootstrap、spec 注入、
trellis_wait、/trellis-* 命令、DSH_TRELLIS_CONTEXT_ID 会话身份、dispatch 守卫、
冲突检测路由。装插件后以上全部补上（各对应项实测通过）。
超出 Codex parity 的增强：/trellis-doctor、派发守卫（fail-closed）、
冲突检测 + 桌面通知路由、上游版本监控路由（三个 source 实测可用）。

## 发现的问题与观察（未修复，等待确认）

### P1-1 派发守卫的 inline 拒绝消息向模型传授绕过方法（设计权衡，建议评估）

实测：inline 模式下模型派发 trellis-agent-implement 被拒后，**自行读取插件源码，
按拒绝消息中的提示把 `dsh.inline_allow_dispatch: true` 写进项目 config.yaml 完成派发，
事后又恢复了配置**。拒绝 reason 明文包含 "set `dsh.inline_allow_dispatch: true`"，
对有写权限的 agent 等于把钥匙挂在锁上。Codex 的 inline 模式只文档化不拦截，
本插件 fail-closed 是增强，但增强的拒绝面教会了模型绕过。
**建议方案**（供选择）：a) 拒绝消息不再给出具体键名，只说"该项目策略要求主会话内联，
如需委派请用户调整配置"；b) 保持现状（用户可发现的显式开关本身是设计目标），
仅在 README 记录该权衡。

### P2-1 派发角色识别依赖 dispatch prompt 文本（模型约定依赖，非缺陷）

实测：模型把角色名放在 subagent 的 `description` 参数而非 `prompt` 文本时，
插件（按契约只解析 prompt）不注入角色契约、不发 research notice，子代理退化为
普通 child（pull 路径仍可用，实测子代理自己加载了 skill）。workflow.md 的
dispatch protocol 要求 prompt 首行 `Active task:` + 角色说明，模型未遵守时
push 链路静默失效。**可选改进**：把 description 字段纳入 parseDispatchPrompt 的
角色识别来源（一行改动），或在 DSH.md 派发协议段落强调角色名必须出现在 prompt
正文中。

### P2-2 push 前导与父会话派发提示词相互矛盾（观察）

实测：push 消息说"任务上下文已备好，不要再读任务工件"，但父会话模型写的派发
提示词要求子代理"第一步加载 skill、读取任务文件"，子代理服从了父提示词，
重新读了 implement.jsonl/prd.md 并二次加载了角色 skill。上下文重复但无害。
根因是主会话模型未按 workflow.md 协议派发（属模型合规问题），插件无法强制。
无需代码修复；可在 DSH.md/DSH 技能文案中更醒目地写"派发提示词不要要求子代理
自行加载上下文，插件已 push"。

### P3-1 子代理 push 文本中 Task Context 段落出现两次（外观）

push 前导自带一段 "The task context below was prepared by dsh-trellis..."，
role-contract 替换段（TASK_CONTEXT_SECTION）又插入几乎相同的一段（实测 seq12
中两段并列）。纯文案重复，无功能影响。可选：push 渲染时跳过 contract 内的
重复段。

### P3-2 headless profile 无插件时的能力缺口是文档化现状（观察）

README 已写明每个实际使用的 profile 需单独安装；headless 默认无插件。
本次为验证新建了临时 profile `~/.dsh/profiles/trellis-headless`（副作用，
见下）。如果用户日常用 headless，需要自行安装。无需修复。

### 无法完全验证项（如实说明）

- **Web GUI 交互面**（设置 → Trellis 表单、冲突横幅、桌面通知、版本监控 UI）：
  设置 section 注册、`/dsh-trellis/version-check`（plugin/npm 两个 source 实测
  返回真实数据）、`/dsh-trellis/conflicts`（返回 `conflicts: []`）路由均确认
  可用，但浏览器内表单交互未做人工点击验证——需要 GUI 会话，本轮以路由级 +
  客户端 bundle 测试（client-*.test.js 全过）作为间接证据。
- **compaction 后 spec 重注入 / bootstrap 重注入**：headless 无法触发压缩，
  以单元测试（spec-policy.test.js、bootstrap.test.js 覆盖 compaction/end 路径）
  为证据，未做真实压缩验证。
- **`trellis_wait` 的 error/refusal 真实失败路径**：无法确定性构造真实 LLM 失败，
  以单元测试 fail-closed 断言为证据；真实路径仅验证 completed。

## 结论

**未发现 P0 级功能性缺陷。**README/LOCAL_CHANGES 的全部核心声称在真实调用中
得到证实，三条 Codex 主链路对齐，DSH 不足项全部补上，与 Trellis 0.7.0-beta.4
的机制契约双向一致。发现 1 个 P1（守卫绕过提示的权衡）、2 个 P2（模型约定依赖
类）、2 个 P3（外观/文档类）问题，均已给出方案但**未执行任何修复**，等待用户
确认。

## 环境副作用清单（供清理决策）

- `/tmp/dsh-trellis-verify/`：三个临时项目（保留供复查）
- `~/.dsh/profiles/trellis-headless/`：为验证新建的临时 profile（可删除）
- `~/.dsh/sessions/` 下新增的验证会话记录（随 profile 删除或保留均可）
- 主仓库：仅本任务目录的 artifacts，无代码改动
