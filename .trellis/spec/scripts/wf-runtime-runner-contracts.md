# wf 运行期运行器契约（candidate / temp / outcome）

> 适用于 `scripts/tests/wf_runtime/full/` 的作者侧测试运行器与其候选审计。
> 详细操作面见 `scripts/tests/wf_runtime/full/README.md`；本文件只固定可执行契约与回归点。

## Scenario: 候选发行证据、临时材料归属与结果归因

### 1. Scope / Trigger

- Trigger：修改 `run_all.sh` / `run_one.sh` / `execution.py` / `runner_cleanup.py` /
  `results_summary.py` / `candidate_audit.py`，或修改任何以发行资产为断言对象的套件。
- 影响面：候选资格证据（`candidate-audit.json`）、结果 schema4 字段、临时目录归属与
  清理证据。改动这些契约必须同时更新 `test_candidate_audit.py`、`test_runner_cleanup.py`、
  `test_results_summary.py`、`test_unit_temp_paths.py` 与慢契约。

### 2. Signatures

```bash
# 每个受监督命令的私有 TMPDIR（父目录在本次结果 logs 内）
execution.py --local-tmp-root <results>/logs -- <target command ...>

# 安装身份唯一核验点（wf_fixture.sh / f2_setup.sh / run_one.sh install 分支 / 审计共用）
verify_install_identity.py --target <project> --release-root <root> \
  --ref <refs/tags/wf-vX.Y.Z> --version X.Y.Z [--no-lib-check] [--json]

# 候选审计（schema 3）
candidate_audit.py --tree <source-release-tree> --version X.Y.Z \
  [--candidate-root <verified candidate>] [--workdir <scope>/audit] --out <report> \
  [--only <unit>]...
```

字段：

- 命令 receipt 新增 `local_tmp_created: bool`（仅当命令声明了 `--local-tmp-root`），
  `local_cleanup ∈ none|removed|retained-keep|retained-unknown|failed`，`retained_paths`
  只含真实存在且未回收的路径。
- `assertion_result`（test result JSON）：`ok, failures, expected, declared_total,
  counts_complete, kind, observed, passed, reason, tail`。
- `summary.json` schema 4（additive）：`unit_outcomes=[{unit, outcome}]`（可选）、
  `failure_owner.assertion|preparation|execution|cancelled|unverified`。
  既有 `gate.bad`、`failure_owner.rows|structural|repro|unregistered` 语义不变。
- 审计报告：`schema_version=3`、`audit={kind: full|incremental, status: complete|failed,
  audited_at}`、`identity={version, release_ref, candidate_commit, candidate_tree_digest,
  source_tree_digest, release_subject, manifest_digest, rules_digest,
  units_registry_digest, helpers, runtime, interpreter}`；逐行 `script_sha256, kind, expect,
  fixture, isolated_user, template{source,tree_digest,install}, installation, input_identity,
  input_digest`。

### 3. Contracts

- 发行来源：托管 runner 必须提供 `WF_RELEASE_REPO` 与 `WF_INSTALL_REF`；缺失即失败，
  禁止回退 `/tmp/wf-fixtures/release-repo`。候选断言对象的安装记录必须能核回本次
  `version/release_ref/source_commit/rules_digest`，且 `.wf/lib` 字节等于
  `<release-root>/wf-release/lib`。
- 临时材料：套件材料一律 `wfdrive.temp()`/`temp_dir()`；历史夹具根用
  `wfdrive.legacy_root()`；`TMPDIR/TMP/TEMP` 由执行器下发，嵌套步骤继承同一根。
  `fixture_scope.validate` 同时接受 `WF_HOST_TMPDIR` 与命令私有 TMPDIR；记录的宿主根必须是
  存在目录且不得是 `/`、HOME/仓库本身或其祖先/内部路径（环境变量不放宽删除域）。
- 单元 outcome 有限集：`passed | assertion_failed | preparation_failed |
  execution_failed | cancelled | unverified`，由 `runner_cleanup.classify_unit` 唯一产生。
- `evidence_state=complete` 仅当每个计划单元都有合法、同代、可分类结果与必要 receipts；
  结构完整的准备/执行/取消失败仍可为 complete，但类别明确且不计为断言失败。
- `--only`：缺席=完整审计；空值/纯空白/未知/不可计划 ID 整组在启动套件前拒绝；增量要求
  旧报告同 schema、同身份、全 ID、待保留行 `input_identity/input_digest` 一致。
  审计在候选发行锁内运行，开始冻结、结束重算身份与脚本字节；漂移/缺行/证据异常不发布。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| `--local-tmp-root` 父目录不存在 | 命令失败，receipt `local_tmp_created=false`、`local_cleanup=failed`、`retained_paths=[]` |
| 候选安装记录 version/ref/commit/rules 不符 | 安装/夹具准备失败（`INSTALL-IDENTITY-MISMATCH` 或 `INSTALL-IDENTITY`），不回退 dev |
| 候选行无安装记录或 `.wf/lib` 字节不同 | 审计行 `stale-evidence`，整次拒绝发布 |
| target_rc 非零 | `execution_failed`（不得称断言失败） |
| target_rc=0 + 显式 FAIL + 计数完整 | `assertion_failed` |
| PASS 不足且无显式 FAIL / 计数不完整 / receipt 错代 | `unverified` → `evidence_state=incomplete` |
| 审计期间 helper/脚本/候选树变化 | `AUDIT-REFUSED`，旧报告字节不变 |
| `--only` 旧身份或待保留行过期 | `AUDIT-REFUSED`，提示在新路径完整审计 |

### 5. Good/Base/Bad Cases

- Good：候选 0.1.1 经代表入口 + CP5 F2 + install repro 全部核回同一 commit；全量审计
  65/65 ID，仅 dev-only 单元保留具体失败断言。
- Base：dev full green（59 suites + 5 flows + 85 repro）`status=ok`，`unit_outcomes` 全
  `passed`，repro `unverified=0`。
- Bad：用作者 payload 安装器 + 固定 `wf-v0.1.0` 冒充候选；套件读写 `/tmp/<固定名>`；
  只凭 `gate.bad` 把单元判成断言失败；用新报告头包装旧执行事实。

### 6. Tests Required

| 断言点 | 测试 |
| --- | --- |
| 私有 TMPDIR 创建/命名/回收、创建失败不伪报、并行唯一根、run_one 四命令接线 | `test_unit_temp_paths.py` |
| 可计划脚本与 fixture/init helper 无未登记 `/tmp` 字面量 | `test_unit_temp_paths.StaticGuardTest` |
| 安装记录 version/ref/commit/rules 与 `.wf/lib` 字节不符、缺记录、错 ref 的拒绝 | `test_verify_install_identity.py` |
| 宿主临时根有界、私有 TMPDIR 桥接 | `test_unit_temp_paths.HostTempBridgeTest` |
| test receipt 的 rc/status 与单元结果不一致、无原因 preflight → unverified | `test_runner_cleanup.ClassifyUnitTest` |
| 单元分类矩阵（断言/执行/准备/取消/未验证 × 清理三态） | `test_runner_cleanup.ClassifyUnitTest` |
| `evidence_state` 与行级 bad 分离、同代 receipt 交叉核对 | `test_runner_cleanup.AssessRunTest` |
| `unit_outcomes`/typed counts 的 additive 校验与 unverified⇒incomplete | `test_results_summary.BuildTest` |
| 审计 schema/身份/`--only` 拒绝与增量合并 | `test_candidate_audit.py`、`test_source_coverage.py` |
| 0.1.1 候选代表入口、CP5 F2 dev/candidate 对拍、install repro | `test_run_all_contract.test_candidate_release_identity_is_exercised_end_to_end` |
| `/tmp` 仓库回退串行 + 旧固定输入不被消费 | `test_run_all_contract.test_repository_under_tmp_falls_back_to_serial_without_mocking`、`..._ignore_legacy_fixed_inputs` |

### 7. Wrong vs Correct

#### Wrong

```python
subprocess.run(["python3", "install.py", "--source", "/tmp/wf-fixtures/release-repo",
                "--release-ref", "refs/tags/wf-v0.1.0", ...])
notes = "/tmp/r70_notes.json"
```

#### Correct

```python
release = wfdrive.release_root()          # 缺失即失败，不回退固定旧目录
ref = os.environ["WF_INSTALL_REF"]
notes = wfdrive.temp("r70_notes.json")    # 本命令私有 TMPDIR
subprocess.run([wfdrive.TOOL_PYTHON, os.path.join(release, "install.py"),
                "--source", release, "--release-ref", ref, ...])
```