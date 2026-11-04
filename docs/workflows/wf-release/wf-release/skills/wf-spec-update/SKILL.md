---
name: wf-spec-update
description: 更新 spec：准入、新增/更新/拆分/合并/改名/删除、索引与 metadata 同步、依赖解除与处置留痕。
disable-model-invocation: false
---

# wf-spec-update

已启用会话内的知识变更入口，只能在当前任务批准范围内执行。默认路径不依赖 MCP、索引服务或知识图谱。

## 步骤

1. 读现有索引、相关 spec 与本地证据（真实失败、已验证契约、人的长期约定、明确边界）。
2. 判断准入：有可追溯依据、有消费者、与既有条目不冲突；给正反例，不写空泛建议。
3. 起草变更数组（每项 `{operation, old_paths, new_paths, before_digests, after_digests, reference_dispositions}`，`add/update` 带 `content`）。
4. `spec-update --task <id> --changes <path>` 成组应用；删除/停用前逐个解除活动任务依赖，未解除时按出口先解除/推迟/指定替代。
5. 变更后重新 `task-check`（spec 属检查输入，旧 pass 失效）。

## 不做

- 不借知识变更扩大触碰面或改其他任务的目标/批准/check 结论。
- 不自动停用或删除无法核实的条目；交人裁决。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令一律形如 `python3 <项目根>/.wf/bin/wf.py <子命令>`；不装 PATH、不做 shell shim。
