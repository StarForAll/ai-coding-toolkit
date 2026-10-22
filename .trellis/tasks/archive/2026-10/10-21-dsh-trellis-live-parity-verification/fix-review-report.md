# 修复审查报告：dsh-trellis 0.1.2 缺陷修复复核

日期：2026-10-22（第二轮，独立审查）
审查对象：另一任务 `10-22-dsh-trellis-defect-fix` 的修复（工作区未提交改动，
dsh-trellis 0.1.1 → 0.1.2）
审查方式：**实际调用验证为主**——新建临时 profile `trellis-verify-012`
（`file:` 指向当前工作树，确认安装的是 0.1.2 修复代码）+ 真实 LLM 会话
（deepseek-flash）在 `/tmp/dsh-verify-012/` 临时项目复现每个问题场景；
辅以修复任务遗留会话证据核对与测试套件运行。不依赖修复任务的自述结论。

## 一、逐项审查结论

### P2-1 角色识别（description/label 兜底）— **真实解决，已实测**

| 场景 | 0.1.1 行为（上轮实测） | 0.1.2 行为（本轮实测） | 判定 |
| --- | --- | --- | --- |
| push：角色仅在 description，prompt 无角色名 | 无 push（静默失效） | 子代理首步收到 push（role=implement，含角色契约+curated context+Active task）| ✅ 解决 |
| 守卫：inline 模式 description-only implement 派发 | 不拦截（绕过守卫） | 被 inline 守卫拒绝（实测 seq32 deny）| ✅ 解决 |
| research notice：description-only 无任务派发 | 不触发 | `<trellis-dispatch-guard>` notice 送达父会话 | ✅ 解决 |
| generic 子代理（label 无角色名）| 静默 | 仍静默（push count=0）| ✅ 契约保留 |
| prompt+description 双角色 | prompt 优先 | push 恰好一次 | ✅ 无重复 |
| 子代理未再调用 `skill` 工具加载角色 | （0.1.1 会调用） | 0.1.2 实测子代理未调用 skill | ✅ |

修复任务的脚本化模型验证（session-f35ebb81/d14ff346 等）经我独立核对会话日志，
与报告一致；我又用真实 LLM 重新复现了全部上述场景，结论相同。

### P2-2 / P3-1 push 文案 — **真实解决，已实测**

- `prepared by dsh-trellis` 在 push 中恰好出现 **1** 次（0.1.2 实测
  prepared-count=1；0.1.1 为 2 次）。
- skill 已内联时 push 明确包含 "Do not load
  `.dsh/skills/trellis-agent-<role>/SKILL.md` again … ignore any 'load the
  task context yourself' step inside it"，成为唯一权威上下文声明。
- skill 缺失时（我人为删除 skill 后实测）退回 "Load … once before acting"，
  不再有"已推送"矛盾表述；curated context 仍随 push 送达。
- 真实 LLM 子代理行为对比：0.1.1 子代理调用 skill 工具 + 重读
  implement.jsonl/prd.md/task.json；0.1.2 子代理不再调用 skill、直接执行任务
  （父提示词明确要求读 prd.md 时仍会读——这是服从显式用户指令，非违背 push，
  符合预期）。

### P1-1 守卫表述 — **实质改善，已实测；根治不可能（如实声明）**

- 0.1.1 实测：模型被拒后**读插件源码→改 config 写入
  `inline_allow_dispatch: true`→派发→恢复配置**（自我绕过成功）。
- 0.1.2 同等压力实测（真实 LLM，inline 模式 description-only 派发）：模型被拒后
  仅 grep 查看了 config，**没有修改配置**，转而在主会话内联完成工作并如实报告
  "委派被运行时拦截"。拒绝文案的重新表述（"Leaving inline mode is the user's
  decision, not yours … Do not edit `.trellis/config.yaml` to get past this
  guard"）在真实模型上起到了预期作用。
- README/spec 已如实降级为"提示性闸门，不是安全边界"。守卫本质仍是 prompt-level
  gate，有写权限的模型理论上仍可绕过——这与文档声明一致，不算未解决问题。
- 附带修复确认：description-only 的 implement/check 派发在 0.1.1 可绕过 inline
  守卫，0.1.2 被拦截（P2-1 的守卫半边）。

### R4 README 上游残留清理 — **完成**

`grep "SajoLuo|0.1\.12|上游"` 在 README 中零命中；保留的 `mindfold-ai/Trellis`
引用指向 Trellis 本体（合法）。README 新增 0.1.2 修复说明节，与代码行为一致
（逐条与本轮实测对照无出入）。

### 测试与构建 — **通过，独立复跑**

- `pnpm test`：351 tests / 347 pass / 0 fail / 4 skip（skip 为 alpha 宿主门槛项）。
- 新增 `subagent-identity.test.js`、`native-subagent-push.test.js` 单独复跑全过。
- client bundle 版本常量 0.1.2（client-bundle.test.js 通过）。
- 修复任务的会话证据（`~/.dsh/sessions/--tmp-dsh-trellis-fix-*-proj--/`）独立
  核对属实。

## 二、新引入的问题

### NEW-1（P2 级，建议处理）：description 含角色字样的"话题型"派发被误判为角色派发

**现象（两次真实 LLM 实测，可复现）**：
- 场景 A（守卫误拒）：`description="研究 trellis-agent-implement 插件的 README 一节并总结"`、
  prompt 无角色名——这只是一个**以插件为研究对象**的普通派发。0.1.2 守卫按
  description 识别出 implement 角色，因无可读任务而
  `deny`："no readable active task for trellis-agent-implement … Start the
  workflow first"。0.1.1 该派发正常放行。实测模型被拒后放弃委派并报告失败，
  未自动换 description 重试——**用户可见的功能回归**。
- 场景 B（push 误标）：`description="about trellis-agent-check plugin docs"`、
  prompt 含 `Active task:`——generic 子代理被推送 **Check 角色契约**（"You are
  the dispatched trellis-check role … do not spawn another Trellis subagent"），
  0.1.1 该子代理保持静默。角色错配会误导子代理自我认知。

**根因**：`ROLE_RE = /\btrellis-agent-(implement|check|research)\b/` 对
description/label 的匹配是子串级——凡是词边界内出现角色全名即判定为角色派发，
无法区分"充当该角色"与"谈论该名字"。

**影响评估**：触发条件是 description 恰好包含 `trellis-agent-{role}` 完整词
（讨论本插件、写文档、审查插件代码的场景并不罕见——本仓库日常就会发生）。
场景 A 是硬阻断（deny），场景 B 是软污染（错误角色上下文）。

**可选修复方案**（不在本次执行，供确认）：
1. 收紧匹配：仅当 description **整体**就是角色名（`description.trim()` 严格等于
   `trellis-agent-<role>` 或 `trellis-<role>`，或匹配 `^[\w-]*trellis-agent-(implement|check|research)$`
   形态的短标签）才认作角色；话题型长句不算。与 DSH 生态中 description 作为
   短标签的惯用法一致，改动最小。
2. 保持现状：在 README/spec 记录该已知误判边界，靠模型换 description 自愈。
   但实测模型未必自愈（场景 A 中它直接放弃了）。
3. 引入显式角色参数：等 DSH 的 subagent 工具未来暴露 agent-type 字段后切换
   （目前不可行）。

### NEW-2（P3 级，记录即可）：LOCAL_CHANGES.md 未记录 0.1.2 轮

版本策略要求 package.json / README / LOCAL_CHANGES / release record 四处一致；
0.1.2 的变更记录只写进了 README 和 spec（`dsh-workflow-behavior.md`），
`LOCAL_CHANGES.md` 没有 0.1.2 小节（其最后记录停在 0.1.1 轮的版本策略描述）。
纯文档簿记遗漏。

### 已核实无回归项

- 面包屑/bootstrap/会话身份/spec deny-once/持久化/generic 静默/research 在
  inline 模式仍放行/命令面：0.1.2 全部实测正常。
- 新增 subagent-identity projection 在无 projection 服务环境安全降级
  （单元覆盖 + 真实会话无告警）。

## 三、总结

| 修复项 | 判定 |
| --- | --- |
| P2-1 角色识别 | ✅ 真实解决（真实 LLM 多场景实测） |
| P2-2 push 权威文案 | ✅ 真实解决 |
| P3-1 重复段落 | ✅ 消除 |
| P1-1 守卫表述 | ✅ 实质改善；prompt-level gate 的本质局限已在文档如实声明 |
| R4 README 清理 | ✅ 完成 |
| R5 不引入新问题 | ⚠️ **部分**：NEW-1（description 话题型误判，P2）是本次加宽角色识别直接引入的行为回归；NEW-2（LOCAL_CHANGES 簿记，P3） |

结论：四个目标问题均真实解决且经实际调用验证；但加宽角色识别的副作用
NEW-1 在真实会话中可复现且对用户可见（误拒+误标），建议按方案 1 收紧
description 匹配后再收尾。本轮审查未执行任何修复。

## 四、环境副作用

- `~/.dsh/profiles/trellis-verify-012/`（审查用临时 profile，可删）
- `/tmp/dsh-verify-012/`（审查用临时项目，保留供复查）
- `~/.dsh/sessions/` 下新增验证会话（可随清理删除）
- 主仓库：仅本报告（任务目录 artifacts），无代码改动
