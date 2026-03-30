# Task Template: Trial Run Delivery

## Purpose

Use this template to create a task for preparing and delivering a trial version of the software to the client before final payment. This task is only for projects using the `trial_authorization` delivery track.

## Applicability

- External projects (outsourcing, custom development, new clients)
- Delivery track: `trial_authorization`
- Do NOT use for `hosted_deployment` track or internal projects

---

## Task Specification

| Field | Value |
|-------|-------|
| Task ID | DELIVERY-TRIAL-001 (adjust as needed) |
| Task Name | Prepare Trial Version Delivery |
| Task Type |交付任务 |
| Risk Level | L1 (medium) - involves client-facing deliverable |
| AI Execution Mode | Human-led with AI assistance (legal/business terms require human judgment) |
| Evaluation Set | N/A (manual verification) |

### Specific Requirements

1. Build release candidate of trial version
2. Implement trial authorization checks (expiration, feature restrictions)
3. Apply trial branding (watermarks, "Trial Version" labels) if applicable
4. Create trial license key or trial activation mechanism
5. Test trial activation flow end-to-end
6. Package delivery artifacts (installer, archive, or deployment package)
7. Generate trial authorization terms document for client
8. Deliver to client via agreed channel (email, cloud share, etc.)
9. Verify client can install/run and activate trial

### Functional Boundary

**Included**:

- Trial build with all core features (but restricted by authorization)
- Trial activation mechanism (license key, account, etc.)
- Trial terms documentation
- Installation/usage instructions for trial

**Excluded**:

- Permanent license keys (delivered after final payment)
- Production deployment by developer (client self-hosts or hosted later)
- Full technical documentation (developer docs are separate)

### Technical Constraints

- Trial authorization must expire or degrade after specified period
- Expiration must NOT destroy client's trial data
- Trial version should clearly indicate "Trial" status in UI
- No hidden trial-to-permanent backdoors (must be documented upgrade path)

### Acceptance Criteria

- [ ] Client can successfully install/run trial version
- [ ] Trial authorization activates correctly (test with sample trial key)
- [ ] Trial period countdown works as documented
- [ ] On expiration, system enters demo/read-only mode (not data-locking)
- [ ] Client can export their trial data before and after expiration
- [ ] Upgrade path to permanent version is documented and tested (without reinstall)
- [ ] Trial terms document provided and client acknowledged receipt

### Dependencies

- Build artifacts from implementation tasks (version to be delivered)
- Authorization system implementation (if not already in codebase)
- Delivery control track decision: must be `trial_authorization`

### Execution Conditions

**Start when**:

- Core functionality complete and tested
- Authorization mechanism implemented
- `assessment.md` specifies `delivery_control_track: trial_authorization`
- Final payment NOT yet received (this is trial delivery)

**Wait if**:

- Delivery track not decided
- Core functionality incomplete
- Authorization mechanism not ready

**Parallel属性**: 独立任务，但与 `DELIVERY-PERMANENT` 互斥（同一项目只能选一个轨道）

---

## Definition of Ready (DoR)

- [ ] Task specification fully populated
- [ ] Authorization mechanism implemented and tested
- [ ] Build system ready for release packaging
- [ ] Trial terms finalized and documented
- [ ] Client delivery channel identified

---

## Definition of Done (DoD)

- [ ] Trial package built and verified
- [ ] Client confirmed receipt and successful activation
- [ ] Trial terms acknowledged in writing
- [ ] Delivery checklist updated with trial delivery items
- [ ] `delivery/trial-delivery-evidence/` contains activation test evidence
- [ ] No P0/P1 bugs introduced during trial packaging

---

## Notes

- This task does **not** imply final payment received. Final payment triggers `DELIVERY-PERMANENT` task.
- If client does not convert to permanent by trial expiration, project may be considered complete with no further handover (per contract terms).
- Developer retains all intellectual property until final payment; trial delivery is a limited license only.
