# dogfood 证据包（v42 P0）

本目录固化 wf 首次真实 dogfood 的事实基线，供 `analysis/solution-review-v42.md` 的每条结论复算。
证据属 **authoring 侧**材料：不进发行清单、不投放目标项目。

## 1. 内容

| 文件 | 内容 | 源 |
|---|---|---|
| `archived-task.tar.gz`（69 文件） | dogfood 唯一归档任务的完整目录树（`task.json`、PRD、每轮报告、材料） | `~/projects/personal/traffic_monitor/.wf/tasks/archive/2026-11/2026-9b960d83632646deb8203c384c3beb84-task` |
| `sessions.tar.gz`（4 文件） | 4 份 Codex 会话 JSONL（16:12 / 17:00 / 17:10 / 17:16） | `~/.codex/sessions/2026/11/08/rollout-*.jsonl` |
| `wf-review-tree.tar.gz`（7261 文件） | dogfood 期间每一轮的审查材料树 | `/tmp/wf-review` |
| `target-lib/lib-files.sha256` | 源树与目标侧 `.wf/lib/wflib` 共 25 个模块的两侧摘要 | `docs/workflows/新项目开发工作流/payload/lib/wflib` ↔ `traffic_monitor/.wf/lib/wflib` |
| `target-lib/lib.diff` | 两侧 `cli.py`、`review.py`、`check.py` 的 unified diff（作者仓库漂移的机械证据） | 同上 |
| `manifests/*.sha256` | 每个归档与 `target-lib` 的摘要清单 | 由打包脚本生成 |

每个 tar 包内另有 `_manifest/files.sha256`：`<sha256>  <size>  <mode>  <相对路径>`，逐文件。

## 2. 复核

```bash
# 在线：重打包并比字节（源侧仍在时；证明归档就是源侧当时的字节）
python3 scripts/wf-evidence-snapshot.py --verify

# 离线：只校验已存归档摘要 + 包内逐文件清单（源侧被清理后仍可用）
python3 scripts/wf-evidence-snapshot.py --offline-verify

# 重建（仅在确认需要重取时使用；会覆盖现有归档）
python3 scripts/wf-evidence-snapshot.py --pack
```

打包确定性：条目按相对路径字节序、`mtime=0`、`uid/gid=0`、`gzip mtime=0`，因此重打包可逐字节比对。

`target-lib/` **不参与在线重打包比对**：它是时点快照（dogfood 时的作者侧源树 ↔ 目标侧 `.wf/lib`），源树此后继续演进，重算必然不同；它的完整性由 `manifests/target-lib.sha256` 与 `--offline-verify` 保证。

## 3. 当前摘要

| 归档 | sha256 | 体积 |
|---|---|---|
| `archived-task.tar.gz` | `a5413f9de25eb0ddfab37a4edd90991fdd6d44935726e8c8bfe306115064f87b` | 95,067 B |
| `sessions.tar.gz` | `b2d7aece8af30958413cd03ce1a35d7a250e403cbcd4a506ed2d546dd0fb4b9d` | 2,784,399 B |
| `wf-review-tree.tar.gz` | `b746f3f33a06d803be4b2740169cd941fe43b0eff03cc8f65196a1dc4959d18b` | 1,270,241 B |
| `target-lib/lib.diff` | `0aa72fad88ee1ba68a4e18b9357193f79d72ed67cc2b5e857489aaa334cee321` | 31,192 B |
| `target-lib/lib-files.sha256` | `7da95d7500b5a5be022133b4cfda9f969c04c4a736483af93aa1e9303a805cde` | 4,592 B |

## 4. 敏感性与边界

- 内容含目标项目（`traffic_monitor`）的源码片段与完整会话转录，属私有材料；只在本 authoring 仓库留存，不随发行投放、不外发。
- 会话 JSONL 是宿主原始记录，可能含本机路径与命令输出；不做改写（改写即失去证据效力），只在 README 声明范围。
- 证据只作**事实复算**用，不构成对目标项目的任何批准或验收。

## 发布口径（2026-11-09 人裁）

**不发布原始证据包**。原始 `*.tar.gz` 留在本机工作区，不入库（全局 ignore `*.tar.gz`）、
不作为任何 release 附件（含自建 Forgejo）。理由：`sessions.tar.gz` 是完整会话日志，
按形态扫到 `sk-` 类串 2 处、`password` 9 处、`api_key` 6 处、绝对路径 902 处；release 附件
长期可下载且撤回不等于消失。

**可校验面仍在库里**：`manifests/*.sha256`、`target-lib/lib.diff`、`target-lib/lib-files.sha256`。
需要复算时在本机跑 `scripts/wf-evidence-snapshot.py --verify`（在线）或 `--offline-verify`（摘要）。

若将来确需远程留存，只能走**脱敏包**（按 `authorize.redact` 口径重建 + 记 `original_digest`），
且需重新取得覆盖该发布动作与可见性的授权。
