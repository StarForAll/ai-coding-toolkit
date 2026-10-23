# P2-3 / U1 / U2 深入分析与 dispatch mode 决策材料

- 日期：2026-10-23
- 范围：只分析与补充证据，不改代码
- 关联：`research/verification-report.md` §5；`implement.md` §C

## A. P2-3：默认 inline 与自动写 `.trellis/config.yaml`

### A.1 插件实际做了什么（源码事实）

- `lib/project-defaults.js` 在每次 `agent/pre-step` 解析到 Trellis 项目后调用 `createDshDefaultsEnsurer`；当 `.trellis/config.yaml` **缺少** `dsh.dispatch_mode` 时：
  - 追加注释块 + `dsh: dispatch_mode: inline`；
  - 使用 `.trellis/.runtime/` 下的锁 + temp/rename 原子写；
  - 已有显式值（包括 `auto`）不覆盖；文件缺失不创建；只读失败仅警告一次。
- `lib/workflow.js#dshDispatchMode` 的代码默认是 **auto**；也就是说“写文件失败/只读/旧项目”时行为会退回 auto，而文档口径是“缺省即 inline”。两者只在“无法写入”的边界上不一致。

### A.2 可观察到的具体影响（本轮证据）

1. **无操作产生 tracked 改动**：`proj-fresh` 首次 DSH 会话后 `git status` 出现 `M .trellis/config.yaml`，diff 为 6 行新增（注释 + `dsh.dispatch_mode: inline`）。
2. **`trellis update` 冲突提示**：`proj` 中 `trellis update --dry-run` 把 `.trellis/config.yaml` 列为 “Modified by you (need your decision)”。
3. **`trellis update -f` 会覆盖掉该段**：`proj-update` 实测 `✓ Overwritten: .trellis/config.yaml`，diff 为删除 6 行；下一次 DSH 会话又会写回，形成“删了又加”的循环（每次 update -f 后工作区再次变脏）。
4. **不改变 Trellis 核心闸门**：`task.py start` 的 JSONL 闸门由 `_has_subagent_platform()` 决定；`.dsh` 目录被无条件视为 sub-agent-capable（`scripts/common/task_store.py` 的 `_SUBAGENT_CONFIG_DIRS` 包含 `.dsh`），**与 `dsh.dispatch_mode` 无关**。实测 DSH-only 项目（无 `.codex`）即使 `dsh.dispatch_mode: inline`，`task.py start` 仍报 “implement.jsonl/check.jsonl have no curated entries”，必须 `--allow-empty-context`。
5. **不改变 phase detail**：`get_context.py --mode phase --step 2.1 --platform dsh` 在 `dsh.dispatch_mode: inline` 下仍输出 “Spawn the implement sub-agent…” + “pull-based sub-agent definition” 块；Trellis 0.7.0-beta.4 **没有 DSH-inline 变体块**（只有 `[codex-inline, Kilo, …]`）。插件只用 `<dsh-mode>inline` banner 提示“不要派发”，但 phase detail 与 banner 冲突。
6. **与 Codex 默认不一致**：Codex 默认 `codex.dispatch_mode: auto`，且不写项目文件；DSH 插件把首次运行改成 inline。

### A.3 影响面

| 场景 | 影响 |
| --- | --- |
| 单人项目 | 首次会话产生待提交改动；可接受但意外 |
| 团队/共享仓库 | 每个 DSH 用户首次运行都会写同一段；如果用户未提交，工作区反复脏 |
| CI/只读 checkout | 写失败 → 代码默认 auto，行为与文档“缺省 inline”不一致（仅警告一次） |
| Codex+DSH 同仓库 | Codex 默认 auto、DSH 默认 inline；`task.py`/phase 文本仍按 codex 判定；两套语义并存 |
| `trellis update` | `--dry-run` 每次提示 config 冲突；`-f` 会删除该段，随后插件又写回 |

### A.4 选项与取舍

| 方案 | 行为 | 优点 | 缺点 |
| --- | --- | --- | --- |
| A. 默认 auto + 不写 config | 代码默认 auto；不写项目文件 | 与 Codex 默认一致；phase/gate/脚本语义一致；无工作区副作用 | 改变插件既有设计；auto 下需要 curated jsonl；用户若想要 inline 需显式设置 |
| B. 默认 inline + 不写 config | 代码默认 inline；不写项目文件 | 保留插件设计；无工作区副作用 | 与 Codex 默认不同；Trellis phase detail 仍是 sub-agent 文本（需补 DSH-inline 变体或强化 banner）；`task.py start` 仍需 `--allow-empty-context` |
| C. 现状（inline + 自动写） | 首次写 config | 零配置；inline 立即可用 | A.2 的全部副作用；与 Codex 默认不同 |
| D. 首次询问后写 | 未设置时提示用户选择 inline/auto，再写 | 尊重用户 | 需要 UI/交互设计；headless 无法提示，仍需默认 |

**分析结论（供用户决策，不等于执行）**：如果目标是“尽可能接近 Codex 并减少意外”，A 的语义一致性最好；如果目标是“保留插件当前的 inline 工作形态”，B 更合理，但必须补一个 DSH-inline 的 phase 变体或让 banner 明确覆盖 phase detail，否则“inline”只在面包屑层成立。C 的自动写文件是独立于模式选择的问题，建议无论选 A/B 都不再自动改 tracked config。

## B. U1（上游只读观察，不计入问题）：Codex-in-DSH 跨宿主身份优先级

### B.1 机制事实（源码）

Trellis `scripts/common/active_task.py#resolve_context_key` 的优先级（有环境变量时）：

1. `DSH_TRELLIS_CONTEXT_ID`（插件贡献）
2. `DSH_SHELL=1` + `DSH_SESSION_ID`（DSH 原生托管 shell）
3. `TRELLIS_CONTEXT_ID`（通用覆盖）
4. payload 的 session_id / conversation_id / transcript
5. 平台环境（如 `CODEX_THREAD_ID`）
6. shell ticket

`CODEX_THREAD_ID` 在 Codex 的 shell 子进程里存在，但排在第 5；DSH 的 1/2 优先命中。

DSH 的“重建 DSH_* 命名空间”只发生在 **DSH 自己的托管 shell**；从一个 DSH shell 启动的任意非 DSH 子进程（Codex、bash 脚本等）会继承 `DSH_SHELL`/`DSH_SESSION_ID`/`DSH_TRELLIS_CONTEXT_ID`，DSH 不会替它们清理。

### B.2 实测

| 场景 | 结果 |
| --- | --- |
| DSH 托管 shell 内启动 `codex exec`，执行 `task.py create` | `Source: session:dsh_session-d9b7dd5b…`（当前 web 会话）→ 指针写到 DSH key；Codex thread key 无指针 |
| 清除 `DSH_TRELLIS_CONTEXT_ID`、`DSH_SHELL`、`DSH_SESSION_ID` 后启动 Codex | `Source: session:codex_01a16620-c537…`；指针正确 |
| 仅保留 `DSH_SHELL=1`+`DSH_SESSION_ID`（无插件变量），再加 `CODEX_THREAD_ID` | 仍解析为 DSH key（证明不是插件独有） |
| 在 DSH 内再启动 DSH headless | 内层托管 shell 显示内层 session id（DSH 自己的清理生效） |

### B.3 影响与边界

- 影响：在 DSH shell 里跑 Codex 做 Trellis 任务时，任务指针/状态落到外层 DSH 会话；两个宿主看到同一任务，或 Codex 重启后找不到自己的指针。
- 频率：只在“嵌套启动”时出现；正常从终端启动 Codex 不受影响。
- 归属：**上游 Trellis 的优先级问题**；插件贡献的 `DSH_TRELLIS_CONTEXT_ID` 让它更早命中，但不是唯一原因（去掉插件变量仍命中 `DSH_SHELL`+`DSH_SESSION_ID`）。
- 处理（按 *Upstream Trellis Is Read-Only* 政策）：**不作为本仓库问题或修复项**。
  - 官方上游无修改权限，不能改 `resolve_context_key`；
  - 不提议上游补丁，不把“插件开关”列入待办；
  - 如需规避，仅在操作层记录：不要从 DSH 托管 shell 启动 Codex 执行 Trellis 任务（边界说明，不是修复计划）。

## C. U2（上游只读观察，不计入问题）：Trellis 0.7.0-beta.4 的 DSH 指令/文档过期

### C.1 过期点

1. `workflow.md` 的 `[Claude Code, …, DeepSeek Harness]` 块（Phase 2.1/2.2 等）写：
   > Without `trellis_wait`, dispatch that child with `run_in_background: false`.
2. `DSH.md` 表格写：
   > Without companion plugin: Foreground native sub-agent / With plugin: Background native sub-agent
3. 但 DSH 0.2.1-rc.2 的 `subagent` 工具 schema **没有** `run_in_background`；传入该参数会被静默忽略，工具立即返回 child id（实测 `headless-19`：返回 `started subagent …`，无报错）。
4. 同时，Phase detail 的 DSH 块没有 inlne 变体（见 A.2.5），`dsh.dispatch_mode: inline` 下仍显示 “Spawn …”。

### C.2 后果

- **plain DSH（无插件）**：按 workflow 文本传 `run_in_background:false` 不会生效；子代理仍后台运行，主会话可能继续推进到依赖步骤。文档给出的 fallback 不可执行。
- **有插件**：`trellis_wait` 可用，主链路能正确等待；但模型仍可能被 phase detail 的过期文本误导去传参（无害但无效），或先按 sub-agent 文本派发、再被 inline guard 拒绝（浪费一轮）。
- **DSH.md**：用户会以为无插件时是前台子代理；实际不是。这会影响“是否安装插件”的判断。

### C.3 处理归属

- 属于 Trellis 官方上游模板/文档（`packages/cli/src/templates/trellis/workflow.md`、`packages/cli/src/templates/dsh/DSH.md`），**只读参考、无修改权限**。
- 按 *Upstream Trellis Is Read-Only* 政策：不作为本仓库问题、不进入修复计划、不提议上游补丁；本仓库只通过插件 banner/README 缓解。
- 不要在本仓库的嵌入工作流里“顺手同步”上游模板；除非用户另行明确要求，并只改本仓库自己的资产。

## D. dispatch mode 决策材料（供用户选择）

### D.1 事实对照

| 维度 | Codex auto（默认） | DSH inline（插件当前默认） |
| --- | --- | --- |
| 主会话角色 | 协调 + 派发 implement/check | 主会话直接实现/检查 |
| 子代理 push | `SubagentStart` 有任务才注入 | 插件 push 可用，但 inline guard 拒绝 implement/check |
| `task.py start` 闸门 | 需要 curated jsonl（auto） | **仍需要**（`.dsh` 被无条件视为 sub-agent-capable；与 dsh mode 无关），除非 `--allow-empty-context` |
| phase detail | codex-sub-agent 块 | 仍是 DSH sub-agent 块（无 DSH-inline 变体） |
| 默认配置写入 | 无 | 首次会话写 `dsh.dispatch_mode: inline` |
| 与 Codex 同仓库 | codex 默认 auto；DSH 默认 inline，两套语义 | 同左 |

### D.2 三个可选目标

1. **对齐 Codex（auto + 不写 config）**
   - 需改：插件默认 auto；移除/禁用自动写；无需新增 workflow 变体（phase 文本天然一致）。
   - 代价：DSH 用户需要像 Codex 一样在 auto 下维护 implement.jsonl/check.jsonl；inline 用户显式设置。
   - 风险：改变现有插件使用习惯。
2. **保留 inline（不写 config + 补 inline 契约）**
   - 需改：插件默认 inline；不写 tracked config；**上游 Trellis 增加 DSH-inline 的 workflow 块**（或在插件 banner 中显式覆盖 phase detail）；`task.py start` 仍要 banner 提示 `--allow-empty-context`。
   - 代价：上游改动（用户已说先不改）；否则 inline 只在面包屑层成立。
3. **现状（inline + 自动写）**
   - 需改：无。
   - 代价：A.2 的工作区/update 副作用；phase detail 冲突仍在。

**分析建议（不代替用户决定）**：若以“与 Codex 同效果、最少意外”为目标，选 1；若坚持插件现有 inline 工作流，选 2，但必须把“不写 tracked config”和“inline 契约”一起做，否则只是把不一致藏起来。选 3 只适合个人、可接受工作区反复变脏、且不介意 phase 文本与 banner 冲突的场景。

## E. 结论

- P2-3 是本仓库可修复的模式/config 问题（0.1.6 已按方案 B 处理）；U1/U2 是上游只读观察，按政策不计入问题清单、不做修复。
- 0.1.6 的 inline banner/README 已对 U2 的 phase 文本做了本地缓解，但这不改变“上游只读”的边界。
