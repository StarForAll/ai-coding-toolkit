# 修复审查报告（第三轮）：dsh-trellis 0.1.2 全问题复核

日期：2026-10-22（第三轮独立审查）
审查对象：第二轮审查后再次执行的修复（工作区未提交改动，仍为 0.1.2，
本轮新增 `roleFromLabel` 整体标签匹配 + LOCAL_CHANGES 0.1.2 小节）
审查方式：**实际调用验证**——临时 profile `trellis-verify-012` 重装当前工作树
代码（确认含 `roleFromLabel`），真实 LLM 会话（deepseek-flash）在
`/tmp/dsh-verify-r3/` 全新临时项目复现两轮以来的全部问题场景；
辅以 352 项测试套件、`roleFromLabel` 边界用例直接执行、命令处理器真实执行。

## 一、历史问题全量复核结果

### 第一轮问题（0.1.1 → 0.1.2 修复项）

| 问题 | 本轮实测 | 判定 |
| --- | --- | --- |
| P2-1 角色识别（description-only） | description=精确角色名 + prompt 无角色 → 子代理收到 push（role=implement，prepared×1、do-not-load-again、skill 正文、curated 全在）；generic label + Active task → 静默；prompt+label 双角色 → push 恰一次 | ✅ 仍解决 |
| P2-2 push/父提示词/skill 三方矛盾 | 子代理实测未调用 skill 工具、未重读任务工件，直接执行任务 | ✅ 仍解决 |
| P3-1 prepared 重复段落 | push 中 `prepared by dsh-trellis` 恰好 1 次（含 skill 缺失回退路径） | ✅ 仍解决 |
| P1-1 守卫表述/自我绕过 | inline 模式强制派发：新文案拒绝、模型转述拒绝并停止、**零 edit/write 调用**、config 未被改动；另有一次模型主动遵守 `<dsh-mode>` 横幅未尝试派发 | ✅ 仍解决 |
| skill 缺失回退文案 | 人为删 skill 后实测：`Load … once before acting`、curated context 仍送达、无"已推送"矛盾 | ✅ 仍解决 |
| R4 README 上游残留 | `SajoLuo|0.1.12|上游` 零命中；README 新增"整体标签"规则说明与实测一致 | ✅ 仍解决 |

### 第二轮新发现问题（NEW-1 / NEW-2）

| 问题 | 上轮行为 | 本轮实测 | 判定 |
| --- | --- | --- | --- |
| NEW-1a 守卫误拒（话题型 description） | `description="研究 trellis-agent-implement 插件的 README…"` 被误拒，模型放弃委派 | **同场景派发成功**：子代理完成 README 总结；父会话零错误结果；子代理零 push（generic 静默） | ✅ 解决 |
| NEW-1b push 误标（话题型 label） | `description="about trellis-agent-check plugin docs"` 收到 Check 角色契约 | **同场景零 push**，子代理按 generic 运行 | ✅ 解决 |
| NEW-2 LOCAL_CHANGES 无 0.1.2 小节 | 缺失 | 已补 `## 0.1.2 — defect-fix round`，明确记录了"第一版子串匹配的回归及收紧"（含 `roleFromLabel` 整体匹配原因）；package.json/README/LOCAL_CHANGES/client.js 四处版本一致（0.1.2） | ✅ 解决 |

### NEW-1 修复实现的边界核对（真实调用 + 直接执行）

`roleFromLabel` 直接执行边界用例：

| 输入 | 结果 | 判定 |
| --- | --- | --- |
| `trellis-agent-implement` / `trellis-implement` / `TRELLIS-AGENT-CHECK` | 角色 | ✅ |
| 引号/CJK 引号/尾标点包裹（`` `Trellis-Agent-Check` ``、`"trellis-agent-implement"`、`trellis-agent-implement:`） | 角色（剥包裹后整体匹配） | ✅ |
| `研究 trellis-agent-implement 插件的 README` | null | ✅ |
| `about trellis-agent-check plugin docs` | null | ✅ |
| `trellis-agent-implement (audit round 3)` | null（括号后缀=话题型） | ✅ |
| 非字符串（undefined/null/数字） | null | ✅ |

括号后缀场景双重实测：
- 干净 prompt + 括号 label → **零 push**（guard 亦不拒，inline 模式放行）——label 兜底正确判为 generic
- 父提示词自己写了"加载 trellis-agent-implement skill"时 → push 触发（role 来自 **prompt** 匹配，prompt 是权威角色信号，符合契约，非 label 误判）

### 基线回归（本轮全部重测，均通过）

- 面包屑 no_task 注入 + bootstrap 一次性（新会话实测）
- spec 注入 deny-once（真实 write 被拒一次、模型遵从 spec 加注释、重试放行）
- `/trellis-status`、`/trellis-finish`、`/trellis-doctor` 真实执行（doctor 报告 Plugin 0.1.2）
- research 精确 label 无任务派发 → notice 送达、inline 模式 research 仍放行
- exact-label check 派发在 inline 模式仍被守卫拦截（兜底识别不削弱守卫）
- 测试套件：352 tests / 348 pass / 0 fail / 4 skip（skip 为 alpha 宿主门槛项）

## 二、本轮新引入问题

**未发现新的功能性或行为回归。**

两点如实说明（非缺陷）：

1. **整体标签匹配的已知代价**：`description="trellis-agent-implement (main)"` 这类
   "角色名+后缀"的 label 现在判为 generic（不 push、不守卫）。模型若想表达角色，
   必须让 description 恰好是角色名。README/spec 已写明此规则；实测 DSH 生态里
   description 本就是短标签，这是有意收窄，且 prompt 通道（权威信号）不受影响。
2. **prompt 仍是权威角色信号**：父会话在 prompt 里写角色名时 push/守卫照常触发
   （实测确认）。这是契约本身（prompt 优先），不是 label 匹配的漏洞。

## 三、总结

两轮修复的全部问题（P1-1、P2-1、P2-2、P3-1、R4、NEW-1a、NEW-1b、NEW-2）
经第三轮真实调用验证**全部真实解决**，未发现新引入问题。0.1.2 的实现与
README/LOCAL_CHANGES/spec 文档声明一致。修复质量合格，可以收尾（提交前建议
按仓库惯例跑一次 `pnpm test` + `build:client`，本轮已代跑均通过）。

## 四、环境副作用

- `~/.dsh/profiles/trellis-verify-012/`（审查用临时 profile，可删）
- `/tmp/dsh-verify-r3/`（第三轮临时项目，保留供复查）
- `~/.dsh/sessions/` 下新增验证会话
- 主仓库：仅本报告，无代码改动
