# Validation record

## Baseline

- HEAD: 1c58bce1; working tree clean before task creation.
- Historical full green: parallel 204/210/212s, serial suites + parallel repro 301s (149 units).
- This session, original r68/r71 with PYTHONHASHSEED=0: paired totals 48/48/49s; median 48s (r68 26/25/26s, r71 22/23/23s). Raw logs: /tmp/wf-runner-audit/baseline-{3,4,5}/.
- Baseline-2 failed in r71 due to session identity hash collisions; seed 7 reproduces single/real-fail -> sess-Y58. Excluded from performance comparison and preserved as failure evidence.

## Observed verification

- First six targeted regressions went red on original evidence/gate logic (two stale-red sequences, nonzero rc, invalid duration, empty result and unsafe shell list transport).
- R68/R71 after migration: paired precise suite totals 23.69/22.94/22.22s; precise median 22.94s, about 52% less than original median. Raw logs: /tmp/wf-runner-audit/r68r71-{1,2,3}/. Timing granularity differs: original shell whole seconds, new cumulative time has finer resolution.
- Full green: /tmp/wf-runner-audit/full-green-final/summary.json and full-green-final.out. 149 units, zero failures, about 179s, requested/effective jobs 4, real unshare mode, no retry.
- Complete unit layer under setsid passed 837 tests with 8 slow tests skipped before the final cancellation/summary checks; rerun required after final code changes.
- Slow runner and fixture contracts passed 17 tests before final cancellation changes; rerun required after final code changes.
- Original no-setsid unit invocation failed two TestRealProc checks; getsid leader evidence was not available to that command. Explicit setsid creates a verifiable session, and all four real process tests pass without changing product anchor behavior.
- build-wf-release --verify --verify-token-parity: byte reproduction 0.1.2, 74 assets and token parity passed.
- validate-wf-design.py, check-doc-refs.py and validate-skills.sh passed.
- Mutation probes must cause assertion failures, not internal exceptions. Initial two incorrectly shaped doubles produced internal errors and are NOT counted as valid red evidence.

## Root causes found by integration

- Original p5_v1 emitted FAIL but old runner counted it as success. Corrected expected binding refusal and added no-new-task-directory assertion.
- cp3 relied on global Git excludes for check logs. Fixture now declares /.wf/tasks/**/check-logs/ in its private .git/info/exclude.
- cp3/r1r2 previously wrote real user state; now isolated synthetic confirmation fixtures, cleaned by executor. No real credential/confirmation record copied.
- Parallel setup must never bind the host fixture parent into private /tmp. Real mount regression verifies result propagation, read-only release/template and independent fixture storage.
- Nested run_all must consume ancestor kernel flock evidence; a child fd need not survive xargs. Inside user namespaces, local worker lease avoids access to protected host descriptors while host global lease remains held.

## Final observations

All requested final checks completed; see the delivery evidence below.


## Final code review

- Reviewed new execution, namespace and ownership modules plus every tracked test/script diff; no product payload or generated release edits.
- Replaced temporary lease-marker scheme with verifiable ancestor kernel FLOCK descriptors. User namespaces use a private worker lease while the host global lease remains held.
- Actual root cancellation contract passes: child running, SIGTERM to root, result cancelled/143, primary/legacy/template cleaned.
- Added frozen full-source digest, so changes in transitive product dependencies cannot reuse prior red evidence. Unknown target cases still run but never get reusable red proof.
- Repro phase snapshots are checked against actual rc/status and saved phase logs; metadata files are excluded explicitly.
- Suite output adapters cover saved counts, checks, steps with terminal identity, and named PASS/FAIL output. Missing workers fail directly; no automatic serial retry can overwrite earlier failures.
- Successful final unit run: 841 tests, 9 slow tests skipped, about 5.2s. Successful slow suite: 18 tests, about 43s.
- New code has no external dependencies or type-checker configuration; AST parsing, bash -n, JSON parsing and git diff --check are the applicable syntax/style checks.
- Existing ResourceWarning/open-file notices in unchanged unit tests remain visible in the raw unit log; they did not cause test failures and are outside this runner change.


## Acceptance evidence map

| Criterion | Evidence |
|---|---|
| AC1 | test_repro_selection: two original stale-red failures, source dependency invalidation, red-only, unknown target and legacy/corrupt cache behavior; real review-count-reject both and review group 12/12 both |
| AC2 | test_fixture_scope sentinel/symlink/overlap/ownership/competing lease checks; wf_fixture/f2/F0/auxiliary uninstall paths use the same guard; result cleanup leaves user notes |
| AC3 | test_execution timeout with detached descendant, cancellation result; slow root-runner cancellation checks actual running command plus primary/template cleanup |
| AC4 | Suite, flow, F0 install, fixture/init and repro logs + command JSON in result roots; failure output paths retained |
| AC5 | test_results_gate contradictory exit/status, malformed/missing/duplicate rows, shell multi-name quoting, frozen inputs and real saved phase verdict; p5_v1 old FAIL now detected |
| AC6 | Actual user-namespace mount regression tries writes to original/shared aliases and template; no worker binds host fixture parent; release tree digest unchanged |
| AC7 | summary requested/effective jobs, unshare branch, fallback reasons, monotonic command time and 10ms shell phase time; README/spec updated |
| AC8 | assertion-map.md: 36 original assertions = 27 retained integration + 9 field variants; report validation bypass produces target assertion failures with zero internal errors |
| AC9 | Three original paired suite totals 48/48/49s vs new 23.69/22.94/22.22s; 52.2% median improvement. Full parallel approved 174.24s vs historical 204s; serial approved 272.71s vs historical 301s |
| AC10 | Complete unit + slow contracts; parallel/serial 59 suite rows, 85 repro records and 5 flow conclusions equal; release byte reproduction, design/doc/skill validation; candidate from empty state regression |

No product rule was changed to make a test pass. The bound-session p5_v1 assertion now checks existing binding identity and unchanged task directory set, matching the already-implemented refusal.

## Deliberate boundaries

- 13 conservative serial suite entries remain; field variants were moved out of slow suites, while permission-failure, handover and recovery integration stays. No historical suite or unique behavior was deleted.
- Full source inputs now invalidate reusable red proof conservatively; cases lacking explicit target metadata always need both in auto mode, even after a successful run. They can run green explicitly and do not create reusable red proof.
- Real host compaction/D1 remains manual and is not claimed by candidate install/reinstall or simulated test confirmations.
- Root runner is bounded to 1800s by default; subprocess limits remain configurable. Kernel kill or host termination cannot guarantee an opportunity to write cancellation metadata; controlled SIGINT/SIGTERM and timeout are verified.
- Implementation delivery was initially uncommitted. The user subsequently requested task close-out; the scoped work commit, archive and journal are handled under that request after the Phase 3.4 batch gate. No push, PR or history rewrite.


## Delivery evidence (final working tree)

| Check | Result |
|---|---|
| Complete unit layer | PASS: 843 tests, 10 explicit slow skips, 5.258s; /tmp/wf-runner-audit/unit-delivery.log |
| Slow contracts and real template | PASS: 19 tests, 63.598s; /tmp/wf-runner-audit/slow-delivery.log |
| Full green final | PASS: 149 units, 0 failures, 174.99s, requested/effective jobs 4, unshare; /tmp/wf-runner-audit/delivery-full/summary.json |
| Full serial equivalence | PASS: 149 units, 0 failures, 272.71s; /tmp/wf-runner-audit/full-serial-approved/summary.json. Suite identities/rc/status, all 85 repro mode/phase/verified and all 5 flow rc/PASS counts equal |
| Review repro both | PASS: 12/12, 10.70s; /tmp/wf-runner-audit/repro-both-approved.out |
| Candidate 0.1.2 representative | PASS: 6 units, 0 failures, 19.53s; /tmp/wf-runner-audit/delivery-candidate/summary.json. 17 smoke assertions, F0 and spec flows, 3 candidate repro; 6 non-candidate cases explicitly skipped |
| Candidate empty-state regression | PASS in final slow contracts. Fixed F0 under owned auxiliary root so subsequent primary clone is allowed |
| Byte reproduction/token parity | PASS: 0.1.2, 74 assets |
| Design/doc/skills | PASS: validate-wf-design, check-doc-refs, 25 skills + spec cross-check |
| Syntax/whitespace/artifacts | PASS: all 24 modified/new Python parses, changed JSON parses, bash -n, git diff --check; 43 changed/new paths inspected, no staged paths, no new pyc files |
| Product release | Unchanged: sha256:6b143947f23b8cbc45ddd1077fbeb638b133c57578ab4c445032b400072bdb4b; Git diff empty |
| Source input | Unchanged: sha256:4d1d74b8e60f34ead927f01e3a6291a68a74e07b9b296bbd01807b95150c0df0 |
| Fixture cleanup | PASS: primary, auxiliary roots and templates absent after final full and candidate runs; 68 full command logs and 7 candidate command logs retained |

Performance limits: 174.99s is a same-machine observation, 14.2% below the historical 204s run. It is not a cross-machine guarantee. The original r68/r71 baseline had whole-second resolution; after-change median is 22.94s versus 48s, about 52.2% less. Coverage mapping, not raw integrated assertion count, establishes the moved field checks.

Outcome: R1–R8 and AC1–AC10 verified within the declared test-asset scope. The user subsequently requested task close-out. Work commit, task archive and session record follow the Phase 3.4 batch confirmation; no remote push is included.


## Close-out authorization

The user confirmed the Phase 3.4 batch: one scoped work commit, native task archive, then session journal. No remote push. The verified code has not changed since delivery; close-out only updates task metadata and records.


## Work commit

- 6b64dfd52d35b759af09911b3168429c6d0d8363 — fix(test): 统一 wf 运行器执行边界并压缩慢套件回归
- Approved 35-path work batch matched the Git index exactly; git diff --cached --check passed. After commit, only the task documentation remained untracked.
- Native archive will acknowledge direct work on main with --skip-branch-validation; this task never had a PR branch.
