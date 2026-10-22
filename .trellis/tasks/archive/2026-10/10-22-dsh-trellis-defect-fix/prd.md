# dsh-trellis 问题修复：角色识别、push 文案、守卫表述与 README 上游残留

## Goal

修复 2026-10-22 真实性与机制复核（会话 `session-dcdc1c4d`）中已确认的 dsh-trellis 实际缺陷，
并完全去除插件 README 中“原本插件（上游 fork）部分”的说明。修复后用真实调用与真实宿主
运行时做多角度验证，且不得引入新问题。

## 背景与问题定性（来自复核结论）

| 编号 | 事实 | 本次处置 |
| --- | --- | --- |
| P2-1 | 角色识别只解析 dispatch prompt 文本。模型把角色名放 `description` 参数时，push 静默失效；同一个解析也用在派发守卫上，`description`-only 的 implement/check 派发可绕过 inline 守卫 | 修复：从 `description` 与子代理自身 descriptor label 识别角色 |
| P2-2 | push 前导要求“不要重新读取任务工件/不要按主会话指令行事”，而父会话按 Trellis 协议要求子代理加载角色 skill，磁盘上的 skill 正文又要求“自己加载上下文”；子代理收到互相排斥的指令，重复加载 skill 与任务文件 | 修复：push 明确“角色 skill 正文已经推送、不要再次加载”，并给出唯一权威上下文来源 |
| P3-1 | push 文本中“The task context below was prepared by dsh-trellis before this message.”出现两次（前导 + `## Task Context` 替换段） | 修复：只保留一处 |
| P1-1 | README 称派发守卫“会执行 inline 契约”，但拒绝文案直接把开关名交给模型，且模型对项目配置有写权限 | 修复：README 降级为“提示性闸门，不是安全边界”；拒绝文案明确“改配置是用户决定，模型不得自行改” |

## Requirements

1. **R1 角色识别（P2-1）**
   - 派发守卫读取 `subagent` / `subagent_fork` 的 `arguments.description`，prompt 中无角色时用
     description 判定角色（prompt 优先，description 兜底）。兜底在 description **以角色名开头**
     （后接结尾或括号/冒号/破折号标注）时生效：`trellis-agent-implement (audit round 3)`
     算角色；`研究 trellis-agent-implement 插件的 README` 这类话题型描述必须保持 generic
     （0.1.2 首版子串匹配已实测误拒/误推，属回归；0.1.3 补回带标注的角色 label）。
   - 子代理首步 push 在 prompt 无角色时，用子代理会话自身 `subagent/descriptor` 的 `label`
     判定角色；label 同样按“角色名开头 + 可选标注”识别。该读取必须走 `sessionProjections` 注册表
     （禁止 `eventAt`/`snapshotEvents`/`ownEvents` 等已弃用同步读）。
   - 角色识别失败时的静默行为仅限“既无 prompt 角色、也无 description/label 角色”，generic
     子代理仍保持静默。
2. **R2 push 文案（P2-2 / P3-1）**
   - 角色 skill 正文已推送时，push 必须明确：正文已包含在 `## Role Instructions`，不要再次加载
     该 skill 文件，也不要执行其中“自己加载上下文”的段落。
   - 角色 skill 缺失时仍提示加载路径，且不产生“已推送”的矛盾表述。
   - “the task context … was prepared”类说明在一条 push 中只出现一次；`## Task Context`
     替换段不再重复该说明。
3. **R3 守卫表述（P1-1）**
   - README 不再声称守卫“执行 inline 契约”；改为提示性闸门，并说明 `inline_allow_dispatch`
     是用户决定项。
   - 拒绝文案保留可发现性，但明确要求模型不要自行修改 `.trellis/config.yaml` 绕过守卫。
4. **R4 README 上游内容清除**
   - 删除 README 中关于上游 fork 插件的全部说明：上游基线/版本号重置叙述、上游 0.1.5–0.1.12
     版本历史、从 npm 安装上游 0.1.12 的整套步骤、指向上游仓库的验证记录链接与旧宿主 CI 叙述。
   - 保留本插件自身的功能、安装方式（本地源码替换 / git 依赖）、配置、工作原理、开发命令。
5. **R5 不引入新问题**
   - 全部现有单元/集成测试通过；新行为有对应测试（含真实 AgentLoop/SubagentRuntime 集成）。
   - 客户端 bundle 与源码同步重建；版本号按本地策略递增到 0.1.2。
   - 未启用 `sessionProjections` 的宿主/测试环境必须安全降级（不抛错、不误判角色）。

## Acceptance Criteria

- [x] `pnpm test` 全绿（含新增用例），`client-bundle.test.js` 通过（bundle 与源码一致）。
- [x] 单元验证：`parseDispatchRequest(prompt, description)` 在 prompt 无角色、description 有
      角色时返回角色；守卫在 inline 模式对 description-only 的 implement/check 派发拒绝。
- [x] 集成验证：真实 AgentLoop + SubagentRuntime 派发 `description = "trellis-agent-implement"`
      的子代理，子代理首个请求前收到 `subagent-context` push，且内容含角色契约与任务上下文。
- [x] push 文本断言：`was prepared by dsh-trellis` 恰好出现一次；“不要再次加载 skill”的
      权威说明存在；skill 缺失时改为“加载 skill”提示。
- [x] 真实 DSH 会话验证（headless profile + 临时 Trellis 项目）：实际派发后检查子会话首步
      消息与工具结果，确认角色识别、push、守卫行为与新的拒绝文案。
- [x] README 中 `SajoLuo/dsh-trellis`、`0.1.12`、`上游` 版本历史段落不再存在；README 描述
      与代码实际行为一致。
- [x] `git diff` 只包含本任务范围内的改动；现有未提交工作未被破坏。
