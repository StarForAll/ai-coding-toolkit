# R0 人工执行步骤（本机跑不了的 3 类环境）

> 前置：`r0-run.sh` 已覆盖本机可自动化的 8 类（bash / zsh / 嵌套 shell / setsid×2 / systemd-run / docker run / docker exec -t / leader 先死）。
> 下面 3 类需要你的环境。**每类都要跑两次：①人在终端直接跑（对照）②通过 agent 的命令工具跑（判据用这个）。**
> 命令只需替换 `PROBE` 路径；脚本**只读**，不写项目、不改状态。

```bash
PROBE=/home/xzc/projects/personal/ai-coding-toolkit/.trellis/tasks/11-05-wf-implementation-gap-audit/r0-anchor-probe.py
```


---

## 0. 必测：A2「同一守护进程 + 多个聊天」（最高优先级）

这是**唯一无法靠终端模拟**的形态，且直接决定自动模式在日常 IDE 场景是否成立。

**做法（任选其一，能跑通即可）**：

1. **VS Code / Cursor**：同一窗口开**两个 Chat 面板**（或一个 Chat + 一个 Copilot 面板），
   在每个面板里让 agent 执行 `python3 $PROBE > /tmp/r0-A2-chat1.json` 与 `...-chat2.json`；
2. **一个扩展宿主 + 两个工作区**：同一 VS Code 窗口里打开两个聊天，分别执行；
3. 若你的宿主是自研执行服务：对同一 service 并发发两条命令，各跑一次探针。

**判据（R0-B）**：两份结果的 `l1_key` **是否相同**。

| 结果 | 含义 | 后续 |
|---|---|---|
| **相同** | 两个聊天共享一个 L1 ⇒ **自动模式无法区分** | 该宿主列入"**仅显式模式**"；这也是 §10 待裁项 2b 的数据 |
| **不同** | 每个聊天有独立 sid ⇒ 自动模式可用 | 记入"支持环境"表 |

**同时记**：两份结果里的 `l2_key` 是否相同（若相同 ⇒ 即使 L1 不同，L2 也会退化为多主，需靠 `attached_l1` 裁决）。

## 1. tmux（多 pane）

```bash
tmux new-session -d -s r0
tmux split-window -h -t r0
# pane 0
tmux send-keys -t r0:0.0 "python3 $PROBE > /tmp/r0-tmux-p0.json" C-m
# pane 1
tmux send-keys -t r0:0.1 "python3 $PROBE > /tmp/r0-tmux-p1.json" C-m
sleep 3
cat /tmp/r0-tmux-p0.json /tmp/r0-tmux-p1.json
tmux kill-session -t r0
```

**判据**：两个 pane 的 `l1_key` **必须不同**（R0-B）；每个 pane 内 `l1_stable=true`（R0-A）。
再在同一 pane 里跑第二次，确认键不变。

## 2. VS Code / JetBrains 集成终端

1. 打开两个终端标签；
2. 各跑一次 `python3 $PROBE > /tmp/r0-ide-$TAG.json`（`$TAG` 自己取名）；
3. 再在各标签里**通过 agent 的命令执行**跑一次同样命令（不是你自己敲）。

**判据**：两标签 `l1_key` 不同（R0-B）；同标签两次相同（R0-A）。
**特别注意**：VS Code 的集成终端由 node-pty 创建，通常每终端一个独立 session；但 agent 经扩展执行命令时**可能每次新建会话**——这正是 P2 路径，要单独记录 L2 是否稳定（R0-A3）。

## 3. CI runner

在你的 CI 里加一步（不改产品代码）：

```yaml
- name: wf R0 anchor probe
  run: |
    python3 .trellis/tasks/11-05-wf-implementation-gap-audit/r0-anchor-probe.py || true
```

**判据**：记录 `l1_key` 是否非空、`l2` 是否为 init 直接子进程（脚本会打印 `chain`）。
按 §2.4c 的三分法，CI 属于"部署前提"类：**即使探针给出键，也按不支持处理**（除非你明确接受"一个 job = 一个执行会话"）。

## 4. 补测：`ssh -t` / `sudo -i` / `script`

```bash
ssh -t <host> "python3 $PROBE"          # 每连接应不同 L1
sudo -i python3 $PROBE                  # 记录是否继承当前 sid
script -qc "python3 $PROBE" /dev/null   # 记录是否新 sid
```

## 6. `ssh -t`（不需要把项目代码拷到服务端）

**探针不依赖项目代码**：它是单文件、纯标准库（`hashlib/json/os/time`），只读 `/proc`。所以你**不需要**复制整个项目。

三种跑法（任选）：

```bash
# ① 直接把脚本内容通过 stdin 送到远端执行（最省事，不留文件）
ssh -t <host> 'python3 -' < /home/xzc/projects/personal/ai-coding-toolkit/.trellis/tasks/11-05-wf-implementation-gap-audit/r0-anchor-probe.py

# ② 只拷这一个文件
scp /home/xzc/projects/personal/ai-coding-toolkit/.trellis/tasks/11-05-wf-implementation-gap-audit/r0-anchor-probe.py <host>:/tmp/
ssh -t <host> 'python3 /tmp/r0-anchor-probe.py'

# ③ 远端没有 python3 时先确认：ssh -t <host> 'python3 -V'
```

**要看什么**

| 观测 | 期望 | 含义 |
|---|---|---|
| 同一条 `ssh -t` 会话里连跑两次 | `l1_key` **相同**（`l1_stable=true`） | 同一执行边界稳定 |
| **开两条** `ssh -t` 各跑一次 | 两个 `l1_key` **不同** | 每条连接是独立边界（R0-B） |
| `chain` 里是否有 `sshd`/`systemd` | 记录下来 | 远端结构可能影响 L2（若 `parent==init` 会被拒） |

> 远端必须是 **Linux**（需要 `/proc`）。`ssh` 不加 `-t` 时没有 pty，`sid` 仍存在但语义不同——两种情况都值得各记一次。

## 5. 记录方式

把每个环境的 `l1_key / l2_key / l1_stable / l2_stable / chain` 填进 `r0-results.md`（模板见方案 §2.5），
并把"经 agent 命令路径"的那一次作为**判定依据**、终端直跑作为对照。

## 6. 完成后

1. 把结论表贴回 `identity-redesign.md` §2.5；
2. 任何不满足 R0-A/B/C/D 的环境 ⇒ 写入"不支持清单"；
3. 只有 R0 完成后才允许开始 R1（`session.py`）。
