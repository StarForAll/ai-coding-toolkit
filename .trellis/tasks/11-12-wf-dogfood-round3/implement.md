# 执行计划：wf 第二轮 dogfood 缺陷修正

> 顺序按“先机制、后指引、最后文档与发行”；每步都有能区分的断言，不留“有实现无断言”。

## 0. 基线

- [ ] 记录基线：`git -C . status --short`、`git log --oneline -3`，确认工作区干净。
- [ ] 跑一次现有套件，记录基线绿灯：
      `python3 -m unittest discover -s scripts/tests/wf_runtime`。

## 1. R1 交付集合单一实现

- [ ] `payload/lib/wflib/scope.py` 新增 `delivery_set(root, task, *, receipts=None)`（设计 §2.1）。
- [ ] `check.object_paths()` 改为消费 `delivery_set()["paths"]`。
- [ ] `check.run_check_scope()` 的 f 分支改消费 `uncovered_f`（去掉第二次 `covers()` 调用）。
- [ ] `tasks.pending_delivery_paths()` 改为消费 `delivery_set()`。
- [ ] 新增 `scripts/tests/wf_runtime/test_delivery_set.py`：
  - 已获 expand 授权的越界路径同时出现在 `object_paths` 与材料路径集合；
  - 未获授权仍抛 `WF_SCOPE_VIOLATION`；
  - `pending_delivery_paths` 含已批准扩面的未提交路径。

## 2. R2 材料物化

- [ ] `payload/lib/wflib/review.py` 新增 `materialize_delivery(ctx, paths)`（设计 §3.1）。
- [ ] `review.context()` 改用该函数，写 `materials/status.json`，删除 `# 无工作树差异` 文案，
      `facts` 增 `materials_status` / `material_problems`。
- [ ] 新增 `scripts/tests/wf_runtime/test_material_diff.py`：
  - 临时 git 仓库中新增未跟踪文件 → `diff.patch` 含其内容（`--no-index` 分支生效）；
  - 已暂存 + 未暂存混合改动 → 两者都出现；
  - 删除文件 → 删除 hunk 可读；
  - 注入 `git` 失败（mock `scope.git` 返回非 0/1）→ `problems` 非空且无“无差异”文案；
  - 交付面为空 → `status.empty is True`。

## 3. R3 代次会话携带

- [ ] `payload/lib/wflib/session.py` 新增 `update_runtime(root, key, **fields)`（合并写）。
- [ ] `payload/lib/wflib/writer.py` 新增 `sync_session_generation(root, record)`；`save()` 内调用。
- [ ] `payload/lib/wflib/cli.py::Context.require_held` 改为“显式优先 → 会话侧车 → 明确出口”，
      成功后幂等同步侧车。
- [ ] 新增 `scripts/tests/wf_runtime/test_generation_carry.py`：
  - 自动身份（`provider=wf`）下持权后不传 generation 的写命令成功；
  - 侧车代次落后于 writer → `WF_GENERATION_STALE` 且 `facts` 给当前代次；
  - 显式 generation 优先：显式错误值即使侧车正确也拒绝。

## 4. R4 回显与骨架

- [ ] `tasks.cmd_task_check` 的 `next_` 按 `plan.complexity` 分流。
- [ ] `review.context()` 写完整报告骨架（预填 task-id/round/check-anchor）。
- [ ] `skills/wf-review/SKILL.md` 对齐（lint、`--as`、去掉 `scope-exceptions`）。
- [ ] 新增/扩展 `scripts/tests/wf_runtime/test_check_next_route.py`：
  - complex 任务 Check pass 的 `next_` 指向 review-launch；
  - light 任务仍指向 finish。
- [ ] 骨架断言并入 `test_material_diff.py` 或新建 `test_report_skeleton.py`：占位文件含协议标记、
      五轴键与预填锚点，且 `read_report()` 能解析出 `REPORT_FIELDS` 全集。

## 5. R5 帮助取值域

- [ ] `cli.COMMAND_HELP["task-approve"]` 的 choice 行由 `decisions.DOMAINS` 生成。
- [ ] 新增 `scripts/tests/wf_runtime/test_help_domains.py`：帮助里列出的每个 choice 都能被
      `decisions.accepts()` 接受；`approve-light`/`mechanical` 不再出现。

## 6. R6 文档与发行对齐

- [ ] `AGENTS.md`：wf 源树现状描述。
- [ ] `docs/workflows/wf/README.md`：11 → 13（三处）。
- [ ] 设计稿 §301、机制稿 §10.1、实现稿目录注释、`payload/install.py` 托管段回退（设计 §7）。
- [ ] `scripts/check-doc-refs.py` + `scripts/validate-wf-design.py` 跑通。
- [ ] 如新增/删除 payload 资产：同步 `dev-manifest.json`（本轮预计只改既有文件，不新增资产）。

## 7. 发行重建与全量验证

- [ ] `python3 scripts/build-wf-release.py --version 0.1.0`（单独提交）。
- [ ] `python3 scripts/build-wf-release.py --verify`、`--verify-token-parity`。
- [ ] `python3 -m unittest discover -s scripts/tests`。
- [ ] `python3 -m unittest discover -s scripts/tests/wf_runtime`。
- [ ] `bash scripts/tests/wf_runtime/full/run_all.sh`（独占，先确认无并发实例；
      必要时 `WF_SUITES="<name>"` 先跑受影响套件，再跑全量）。
- [ ] `./scripts/validate-skills.sh`。
- [ ] 交付前复核 `git diff`（只含本任务范围），确认未动目标项目。

## 验证命令（最小证据集）

```bash
python3 -m unittest discover -s scripts/tests
python3 -m unittest discover -s scripts/tests/wf_runtime
bash scripts/tests/wf_runtime/full/run_all.sh
python3 scripts/build-wf-release.py --verify
python3 scripts/build-wf-release.py --verify-token-parity
python3 scripts/validate-wf-design.py
python3 scripts/check-doc-refs.py
./scripts/validate-skills.sh
```

## 高风险文件与回退点

| 文件 | 风险 | 回退点 |
|---|---|---|
| `wflib/scope.py` | 交付集合变大影响锚点与 spec 覆盖 | 单测先锁行为；异常时只回退 `object_paths` 接线 |
| `wflib/review.py` | 材料生成与骨架 | 保留旧函数名 `_material_diff` 作为薄包装直至测试通过 |
| `wflib/cli.py::require_held` | 写权限拦截语义 | 显式代次路径保持原样，新增分支可独立回退 |
| `wflib/writer.py::save` | 所有写权持久化入口 | 侧车写失败只降级，不影响写权事务 |
| 发行树 | 生成物 | 重新执行 build 脚本即可复原 |

## 收口前自检

- [ ] 新增断言在人为回退实现时会变红（至少对 R1/R2/R3/R5 各做一次手工验证，记录命令与结果）。
- [ ] `prd.md` 的验收项逐条有对应证据（测试名/命令输出）。
- [ ] 更新 `.trellis/spec/docs/wf-delivery-discipline.md` 若本轮暴露新的收口纪律（如“材料生成必须区分无差异与生成失败”）。

---

## 执行记录（2026-11-12）

| 项 | 结果 | 证据 |
|---|---|---|
| R1 交付集合 | 完成；`scope.delivery_set` 为唯一实现，`check.object_paths`/`review.context`/`tasks.pending_delivery_paths` 消费它 | `scripts/tests/wf_runtime/test_delivery_set.py`（4 例） |
| R2 材料物化 | 完成；未跟踪 `--no-index`、失败进 `problems`、删除 `# 无工作树差异` | `test_material_diff.py`（7 例） |
| R3 代次携带 | 完成；`writer.save` → 会话侧车；`resolve_generation` 显式优先 | `test_generation_carry.py`（5 例） |
| R4 回显与骨架 | 完成；`check_next_hint` 分流；`review-context` 落完整骨架；`wf-review` 技能对齐 | `test_check_next_route.py`、骨架断言 |
| R5 帮助取值域 | 完成；由 `decisions.DOMAINS` 生成 | `test_help_domains.py` |
| R6 文档/发行 | 完成；设计稿 §301、机制稿 §10.1、实现稿注释、README 13、AGENTS.md、install 托管段 fail-closed | `validate-wf-design.py`、`test_install_manifest.py` |
| 回退注入自检 | R1/R2/R3/R5 各一次：临时改回旧实现 → 对应用例 RED；恢复后字节一致 | 本轮命令输出 |

验证结果：

```text
python3 -m unittest discover -s scripts/tests              → 620 tests OK
python3 -m unittest discover -s scripts/tests/wf_runtime   → 315 tests OK
bash scripts/tests/wf_runtime/full/run_all.sh              → 149 项，失败 0；repro 85/85（green+red）
python3 scripts/build-wf-release.py --verify               → OK byte reproduction (74 assets)
python3 scripts/build-wf-release.py --verify-token-parity  → OK token parity
python3 scripts/validate-wf-design.py                      → 七项检查 + 覆盖率断言通过
python3 scripts/check-doc-refs.py                          → 0 problem(s)
./scripts/validate-skills.sh                               → 25 skills OK
```

范围外但相邻、已登记：`authorize._pattern_hits` 原先只查已跟踪文件，导致"给新增文件登记的
扩面确认"永远匹配不到（`covers` 判 broken）；本轮把它改成 `--cached --others --exclude-standard`，
否则 R1 的"已批准扩面新路径"不可达。B（脱敏/外发授权）与 C（未提交越界归属通道）仍未动。
