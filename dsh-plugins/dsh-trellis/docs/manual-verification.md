# dsh-trellis 手工验收清单

本文件只列 **agent 不能替代用户确认** 的项目。已由自动化验证覆盖的 bootstrap、`no-trellis`、任务面包屑、spec deny-once、子代理 push、dispatch guard、shell 身份、命令处理器、冲突路由与通知代码路径、单元测试与构建，不再列入手工步骤。

当前范围固定排除：项目级策略、vendored 自动同步脚本/补丁目录。排他只验收桌面通知警告；不自动禁用其他插件。

## M1. 真实 `/compact` 与 clear 后重新注入

**目的**：验证真实 Web 会话（不是 headless/mock）的压缩/clear 会移除 bootstrap/面包屑，并在下一次请求重新注入；spec 状态也会重置。

**前提**：已安装插件并在 Web UI 打开一个 **无 active task** 的 Trellis 项目；浏览器通知与压缩功能正常。

**步骤**：

先准备测试项目（只需解压一次）：解压得到的 `/tmp/dsh-trellis-manual-test` 即“前提”中无 active task 的 Trellis 测试项目，在 Web UI 中打开它作为工作目录。

```
tar -xzvf ~/tmp/dsh-trellis-manual-test.tar.gz -C /
cd /tmp/dsh-trellis-manual-test
```

1. 新建会话，连续发送 3 条普通消息（例如 `say one`、`say two`、`say three`）。如果 `/compact` 提示没有可压缩历史，继续多发几轮直到有可压缩内容。
2. 在输入框执行 `/compact`，等待命令返回压缩结果。
3. 再发送一条普通消息。
4. 用下面的命令检查当前会话日志（默认 DSH home 为 `~/.dsh`；如设置了 `DSH_HOME` 请替换）：

```bash
f=$(ls -t ~/.dsh/sessions/*/*/session.v4.jsonl.zstd | head -1)
echo "bootstrap=$(zstd -dc "$f" | grep -c '<trellis-bootstrap>')"
echo "breadcrumb=$(zstd -dc "$f" | grep -c 'Trellis workflow state')"
echo "compaction=$(zstd -dc "$f" | grep -c '"type":"compaction/end"')"
```

5. 再发送一条普通消息，重复第 4 步。

**正确效果**：

- 第 1 步后：`bootstrap=1`，`breadcrumb=1`；后续普通轮次不再增加（不是每轮重复）。
- **这是有意设计，不是缺陷**：如果第一次没有开始 Trellis，同一会话后续普通轮次不会再次催促；workflow 面包屑仍会随状态变化出现。需要重新提示时，手动加载 `trellis-start`，或让压缩/clear 移除后再次注入；新会话会重新注入。
- `/compact` 后：`compaction=1`；下一次请求后 `bootstrap=2`、`breadcrumb=2`（旧的被压缩移除，新的恰好补一次）。
- 再下一轮：计数保持不变，仍然只有一次新的 bootstrap/面包屑。
- 如果当前会话有 active task，bootstrap 不应出现（这是 P2 的设计）；改用无任务会话验证 bootstrap。
- clear 的预期相同：clear 后下一次请求重新出现一次 bootstrap/面包屑。
- spec 重置（可选）：在带 `paths:` 的 spec 项目中，第一次 `write/edit` 被 deny 并带 `<spec-context>`；`/compact` 后再次触发同一文件，应再次 deny，而不是静默放行。spec 去重分片在 `.trellis/.runtime/spec-inject/<session>.json`，压缩时会被删除。

**失败示例**：压缩后没有任何新 bootstrap/面包屑；或普通轮次每轮都新增（说明 projection 没有去重）；或压缩后 spec 不再 deny。

**不要把“首轮未开启 Trellis 后不再重复 bootstrap”记为失败**：当前设计就是每会话一次；需要再次提示请用 `trellis-start` 或压缩/clear。

## M1b. 重启后 spec 去重状态

**目的**：验证 spec 去重记录持久化：普通重启不重复 deny；压缩/clear 删除分片后重新 deny；损坏/只读时安全回退。

**前提**：Trellis 项目，`.trellis/spec/` 中有一个 `paths: ["src/**"]` 的 spec；Web UI 会话可以编辑 `src/` 下文件。

**步骤**：

1. 新建/继续一个 Web 会话，第一次 `write` 一个 `src/` 下的新文件：应被 deny，并带 `<spec-context>`。
2. 重试同一文件：应成功。
3. 完全退出并重启 DSH Web，回到同一会话（或继续同一 session），编辑 `src/` 下另一个新文件。
4. 再执行 `/compact`，然后编辑第三个 `src/` 新文件。

**正确效果**：

- 第 1 步：deny 一次 + spec 正文；第 2 步：成功。
- 第 3 步：**不再 deny**（同一会话已经教过该 spec；分片在 `.trellis/.runtime/spec-inject/<session>.json`）。
- 第 4 步：`/compact` 后再次 deny（内存记录和磁盘分片都删除，重新教学）。
- 可选：删除该分片或写入损坏 JSON，再编辑 `src/` 文件，应重新 deny，而不是静默放行。

**失败示例**：重启后第一次编辑又 deny（状态没有持久化）；压缩后不 deny（分片没有删除）；损坏分片导致静默放行（没有回退到重新教学）。

## M2. Web 设置页与保存/重启

**目的**：确认真实浏览器里的设置入口、字段和持久化。

**步骤**：

1. 打开 DSH Web UI → 设置 → **Trellis**。
2. 检查顶部能力开关：启用插件、`/trellis` 命令、派发守卫、子代理任务上下文 push、路径级 spec 注入。
3. 检查面包屑/命令行为字段、版本监控分组。
4. 关闭“版本监控”，确认间隔、通知、三个来源地址和检查面板立即隐藏；重新打开，确认恢复。
5. 修改一个无害值（例如面包屑字节数），保存；刷新页面并重启 DSH，重新打开设置页。
6. 点“立即检查”，确认版本监控结果/通知行为正常。

**正确效果**：

- 设置列表只有一个“Trellis”入口，没有重复 section。
- 版本监控关闭时相关控件全部隐藏；重新开启后恢复。
- 保存成功；刷新/重启后读回保存值，不出现“保存失败/冲突”提示。
- 插件详情页不再重复渲染旧表单。
- 页面无未捕获 JS 错误；版本监控按钮和通知行为与用户已确认的“正常”一致。

**失败示例**：出现两个 Trellis 设置入口；关闭版本监控后仍显示相关控件；保存后刷新丢失；控制台报错。

## M3. 真实第二个 Trellis 插件 + 桌面通知

**目的**：验证排他告警的实际用户可见效果。注意：设置页“版本监控”的通知是版本监控通知，不是本项冲突告警。

**前提**：同一 DSH profile 中再安装一个包名或 loader id 含 `trellis` 的插件（例如测试副本 `dsh-trellis-conflict`，或真实的 `dsh-trellis-plus`）。不要同时启用两个会写入同一 profile 的正式副本。

**步骤**：

1. 把第二个 Trellis 插件加入当前 profile，重启 DSH。
2. 在浏览器中允许该站点通知（设置 → 站点权限 → 通知 → 允许）。
3. 打开/刷新 DSH Web UI。
4. 观察桌面通知和页面右下角/底部横幅。
5. 关闭横幅；刷新页面，确认同一冲突集合只通知一次（页面生命周期内）。
6. 移除第二个插件，重启并刷新，确认告警消失。
7. 再把浏览器通知权限改为“拒绝”，刷新，确认仍显示横幅并提示到站点设置开启，而不是静默。

**正确效果**：

- 桌面通知标题为“检测到另一个 Trellis 插件”（或当前语言对应标题），正文列出冲突插件名/id。
- 同时出现可关闭的页内横幅；关闭后本页不再重复弹出同一集合。
- 通知权限为 `default` 时，横幅提供“启用桌面通知”按钮；点击后授权并通知。
- 权限为 `denied` 时，横幅保留并提示到站点设置中重新允许。
- 不会自动禁用另一个插件；移除冲突插件后告警消失。
- 没有第二个插件时，页面不应出现该告警。

**失败示例**：只有日志没有用户可见告警；两个插件共存但无通知/横幅；自动禁用了另一个插件；移除后仍一直告警。

## M0. 项目级 `dsh.dispatch_mode` 只读默认

**目的**：确认插件把缺省的 Trellis 项目当作 inline，且**从不写**项目配置。

> 背景：`dsh.dispatch_mode` 未配置时缺省为 `inline`，这是有意设计：插件对项目配置只读，避免写入 `.trellis/config.yaml` 造成污染。

辅助预检（agent 亦可代跑；本节验收仍以下列真实会话步骤为准）：在测试项目目录（`.trellis/config.yaml` 存在且无 `dsh:` 段）执行，预期输出 `inline`；如设置了 `DSH_HOME`，把代码里的 `$HOME/.dsh` 换成 `$DSH_HOME`；使用其他 profile 时把 `profiles/web` 替换为对应 profile 名。

```bash
# 在测试项目目录下执行
node --input-type=module -e '
import { readFile } from "node:fs/promises";
const base = process.env.HOME + "/.dsh/profiles/web/node_modules/dsh-trellis/lib/";
const { dshDispatchMode } = await import(base + "workflow.js");
console.log(dshDispatchMode(await readFile(".trellis/config.yaml", "utf8")));
'
```

**步骤**：

1. 选一个 `.trellis/config.yaml` 里没有 `dsh:` 段的测试项目，发送一条普通消息（或重启后首次进入）。
2. 打开 `.trellis/config.yaml`，确认**没有新增任何内容**（`git status` 也不应出现该文件）。
3. 确认第一轮面包屑末尾有 `<dsh-mode>`（缺省 inline）。
4. 把该值改成 `auto`，再发一条消息；确认文件逐字不变、面包屑没有 `<dsh-mode>`。
5. 对只读项目重复第 1 步，确认会话照常工作（缺省 inline）且没有写入尝试/警告。

**正确效果**：

- 缺省即 inline；插件只读配置，不追加键、不改注释/换行、不创建缺失的 `config.yaml`。
- 显式 `auto` / `sub-agent` 永远优先；非法值回落 inline。

---

## M4. 重启、安装态与重复注册

**目的**：确认真实 host 重启后加载的是本地当前版本，且没有重复工具/命令/设置页。

**步骤**：

1. 完全退出并重启 DSH Web。
2. 打开插件/设置页，确认 `dsh-trellis` 版本显示为实际构建版本。
3. 分别执行一次 `/trellis-status`、`/trellis-finish`。
4. 检查可用工具中只有一份 `trellis_wait`，命令只有一组 `/trellis-status`、`/trellis-finish`。
5. 查看启动日志/页面控制台，确认没有插件加载错误、重复注册错误或未捕获异常。

**正确效果**：

- 版本与已安装插件 `package.json` 的 `version` 字段一致（如 `~/.dsh/profiles/web/node_modules/dsh-trellis/package.json`；设置了 `DSH_HOME` 或使用其他 profile 时相应替换路径），不要求具体版本号；两个命令各执行一次并返回正常结果（无任务时也是 success）。
- 不出现重复命令、重复工具或重复设置页。
- 启动日志无 `dsh-trellis` 相关错误；只有一份插件实例运行。

**失败示例**：仍是旧版本；命令重复出现；`trellis_wait` 注册两次；启动报错。

## M5. 真实项目切换 / worktree

**目的**：验证 Web 会话切换工作目录后，面包屑、任务指针和命令跟随新项目，不串项目。

**步骤**：

1. 准备两个不同的 Trellis 项目 A、B（B 可以没有 active task；A 有 active task）。
2. 在 Web UI 中从 A 切换工作目录到 B，发送一条消息。
3. 再切回 A，发送一条消息。
4. 分别执行 `/trellis-status`。
5. 如使用 git worktree，重复 A→worktree→A 的切换。

**正确效果**：

- B 中显示 B 的无任务/任务状态，不显示 A 的 `Active task:`。
- 切回 A 后恢复 A 的任务指针和项目面包屑。
- 命令的 cwd 和 `DSH_TRELLIS_CONTEXT_ID` 跟随当前工作目录；不读取另一个项目的 task.json。
- 原生 session id 不因切换目录而变化；切换失败时不要偷偷回退旧项目。

**失败示例**：B 中仍显示 A 的任务；切回 A 后任务丢失；命令在错误目录执行。

## M6. 真实 slash command 在 Web UI 中的分发（可选）

**目的**：确认 Web 客户端的命令适配器确实把 `/trellis-status` / `/trellis-finish` 送到插件命令，而不是当普通文本发给模型。

**步骤**：

1. 在 Web UI 输入 `/trellis-status` 发送。
2. 在 Web UI 输入 `/trellis-finish` 发送。
3. 检查会话历史：命令生命周期不应作为模型消息出现（`recordInput: false`）。

**正确效果**：

- 返回 `Current task:` / 收尾清单，不消耗模型轮次。
- 有任务时显示任务目录、状态、标题；无任务时显示 `Current task: (none)` 并 success。
- `/trellis-finish` 只读，不清除 active-task 指针、不归档任务。

**失败示例**：命令被当成普通 prompt；输出重复；`/trellis-finish` 提前清指针。

---

## 不需要手工重复的项目

以下已由 agent 自动验证，手工清单不重复：

- 单元/集成测试、`dsh 0.2.1-rc.2` 兼容矩阵、客户端构建；
- 新会话 bootstrap 一次、`no-trellis` 跳过、非 Trellis 目录不注入；
- 有任务面包屑、子代理首步 push（含角色契约）且无 no_task 消息；
- spec deny-once / 重试放行、spec 状态 round-trip/损坏回退/重启与压缩重置、dispatch guard deny；
- shell `DSH_TRELLIS_CONTEXT_ID` 与 `task.py current`；
- 冲突路由返回、冲突通知代码路径、页内横幅渲染；
- 命令处理器在真实 Trellis 0.7.0-beta.4 项目上的无任务/有任务返回。

已接受的非问题：本地副本无 LICENSE；版本监控通知（用户已确认正常）；**首轮未开启 Trellis 后，同会话后续不再重复 bootstrap（有意降噪）**。
