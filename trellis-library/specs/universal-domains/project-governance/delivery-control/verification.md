# Delivery Control — Verification

## Evidence Requirements

### Before Implementation (Gate Check)

When entering implementation phase (after design/plan), verify:

1. **Delivery track is decided**:
   ```bash
   grep -q "delivery_control_track" .trellis/tasks/*/assessment.md
   grep -qE "(hosted_deployment|trial_authorization)" .trellis/tasks/*/assessment.md
   ```

2. **If trial authorization, terms are documented**:
   ```bash
   # Check for these fields in assessment.md or contract docs
   grep -q "trial_authorization_terms" .trellis/tasks/*/assessment.md
   ```

3. **Change management for delivery track changes**:
   - Any change to delivery track after project start must generate a change record
   - Change must be client-approved

### During Implementation (Ongoing)

Monitor `task_plan.md` for delivery-related tasks:

- If external project: `task_plan.md` must contain delivery handover tasks
- These tasks should be marked with appropriate `开始条件` (final payment confirmation)
- No delivery tasks should be marked `可开始` before payment condition is met

### Before Delivery (Final Check)

Before running `/trellis:delivery`, verify:

1. **Payment status confirmed**:
   - Check `assessment.md` or payment records for "final payment received" flag
   - For trial authorization, verify "permanent authorization trigger" condition met

2. **Delivery track compliance**:
   ```bash
   # For hosted deployment, ensure no early handover occurred
   git log --oneline | grep -i "transfer.*source\|transfer.*secret\|handover" || echo "OK"
   # Manual check: verify no .env files or secrets were committed before final payment
   ```

3. **Trial version behavior** (if applicable):
   - Test expiration: set system clock past expiration, verify demo mode/read-only behavior
   - Test data export: ensure client can export data before expiration

4. **Transfer checklist completeness**:
   ```bash
   test -f delivery/transfer-checklist.md
   grep -q "\[x\]" delivery/transfer-checklist.md  # All items checked
   ```

## Failure Modes

| Failure Mode | Symptoms | Response |
|-------------|---------|----------|
| **Missing delivery track decision** | No `delivery_control_track` in assessment.md | Block implementation until decision recorded |
| **Early handover** | Source code committed before final payment milestone | Remove commits, rotate secrets if exposed, renegotiate payment terms |
| **Trial without terms** | Client using trial but no written expiration/upgrade terms | Suspend trial access until terms are documented and signed |
| **Undisclosed termination** | Code contains hidden `if expired then lock()` without documentation | Remove mechanism, document intended behavior, disclose to client |
| **Incomplete transfer** | Delivery checklist has unchecked items | Do not mark delivery complete; fulfill missing items |

## Related Specs

- `spec.universal-domains.project-governance.change-management`: For changing delivery track mid-project
- `spec.universal-domains.security.secrets-and-config`: For secure secret handover
- `spec.universal-domains.verification.release-readiness`: For release gate checks
