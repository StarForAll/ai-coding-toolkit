# 实施：P0（顺序执行，每步带验证命令）

> 回滚点：每步结束 `git status` 只应出现本步声明的路径；出现其他路径即停下核对。

## S0 基线（已测）

- `python3 scripts/build-wf-release.py --verify` → `OK byte reproduction (0.1.0, 57 assets)`
- `python3 -m unittest discover -s scripts/tests -t . -q` → `Ran 81 tests ... OK`

## S1 决策记录入库

- [ ] 复制 v42 到 `docs/workflows/wf/analysis/solution-review-v42.md`（逐字节，`sha256sum` 两侧比对）
- 验证：`sha256sum /tmp/wf-solution-review-2026-11-09.md docs/workflows/wf/analysis/solution-review-v42.md` 一致

## S2 证据固化

- [ ] 写 `scripts/wf-evidence-snapshot.py`（`--pack` / `--verify` / `--offline-verify`）
- [ ] 打包 4 类证据到 `analysis/evidence/`（归档任务、4 份 JSONL、`/tmp/wf-review`、目标侧 `.wf/lib` diff）
- [ ] 写 `analysis/evidence/README.md`（来源、范围、敏感性、复核命令）
- 验证：`python3 scripts/wf-evidence-snapshot.py --verify` 全绿；`--offline-verify` 校验 `manifests/*.sha256`

## S3 protocol 骨架

- [ ] `payload/protocol/states.json`（status/phase/阶段模型句/转移表/next_by_position）
- [ ] `payload/protocol/codes.json`（36 码 × tier/exit/prohibited_repairs）
- [ ] `payload/protocol/thresholds.json`（机制稿 §8.1 全部键）
- [ ] `payload/protocol/redaction.json` + `redaction.baseline.json`
- [ ] `payload/lib/wflib/protocol.py`（加载 + schema 校验 + `next_for`）
- 验证：`python3 -c "from wflib import protocol; print(protocol.PHASES, len(protocol.CODES))"`（PYTHONPATH 指向 payload/lib）

## S4 单源化改造

- [ ] `codes.py` 改为 protocol 投影（删手写表，保留公共名）
- [ ] `cli.cmd_status` 的 `next` 改取 `protocol.next_for()`（含 `--short` 分支）
- 验证：`grep -c 'WF_' payload/lib/wflib/codes.py` 为 0；`--verify` 与测试仍绿

## S5 文档片段生成 + 一致性

- [ ] `scripts/wf-protocol-docs.py`（渲染码表/转移/阈值/阶段句；`--check` 与机制稿比对）
- 验证：`python3 scripts/wf-protocol-docs.py`（输出片段）；`python3 scripts/wf-protocol-docs.py --check` 退出 0

## S6 6 条不变量测试

- [ ] `scripts/tests/wf_protocol/test_invariants.py`（①②③④⑤⑥）
- 验证：`python3 -m unittest discover -s scripts/tests -t . -q` 全绿（81 + 新增）

## S7 发行同步与收口

- [ ] `dev-manifest.json` 登记 4 个 protocol 资产；`PROJECT_CLASSES` 增 `payload/protocol/ → .wf/protocol/`
- [ ] 重建 `docs/workflows/wf-release/`（使 `--verify` 恢复绿）
- 验证：`python3 scripts/build-wf-release.py --verify` → OK；`git status` 只出现预期路径

## 交付（不提交）

- 改动清单（文件 → 动机 → 编号）
- 验证记录（命令 + 结果）
- 与 v42 的偏差
- 未完成项
