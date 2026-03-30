# Authorization Management

## Purpose

Define reusable rules for trial authorization lifecycle: validity periods, renewal, expiration behavior, and permanent authorization transition. Used in conjunction with delivery-control for external projects using trial authorization track.

## Applicability

When a project adopts the `trial_authorization` delivery track, this spec governs:

- Authorization validity period definition
- Renewal process and conditions
- Expiration behavior requirements (must preserve data)
- Transition to permanent authorization upon payment fulfillment

## Scope Boundary

This spec applies to:

- Software delivered under trial/limited license
- Time-bound or feature-limited evaluation versions
- Authorization systems that control feature access or system usage

This spec does NOT apply to:

- Hosted deployment track (client never receives executable with authorization checks)
- Open source or freely distributable software
- SaaS subscription models (different authorization pattern)
- Hardware-locked or DRM systems (different concern)

## Normative Rules

### RA-1: Trial Authorization Must Have Explicit Expiration

Every trial authorization must include:

1. **Start date/time**: when trial begins counting
2. **End date/time** OR **duration** (e.g., 30 days from start)
3. **Clock source**: whether using system clock, developer server time, or client-provided time

If using condition-based expiration (e.g., "expires after 100 uses"), the condition must be clearly defined and documented.

### RA-2: Expiration Behavior Must Preserve Data

When trial authorization expires:

- ✅ System must remain in "read-only" or "demo" mode, allowing data viewing and export
- ❌ System must NOT encrypt or lock user's data irreversibly
- ❌ System must NOT delete user's data automatically
- ✅ System must provide clear instructions for obtaining permanent authorization
- ✅ System must allow data export in standard formats (CSV, JSON, PDF, etc.)

**Rationale**: Client's data is their asset. Expiration should encourage payment, not hold data hostage.

### RA-3: Renewal Process Must Be Documented

If trial renewal is possible (before expiration):

- Document renewal conditions: free extension? paid extension? new full-term trial?
- Document renewal mechanism: contact sales? enter new license key? automatic?
- Document any changes: Does renewal reset the expiration clock? Stack additional time?

Renewal terms should be discoverable from within the software before expiration.

### RA-4: Permanent Authorization Transition Must Be Seamless

Upon receiving permanent authorization (typically final payment):

- Trial restrictions should be lifted without requiring reinstallation
- Any watermarks, demo banners, feature locks should be removed cleanly
- User data and configuration should be preserved
- Authorization state should transition from "trial" to "permanent" in the system

Ideally, the client should not need to reinstall or re-enter data.

### RA-5: Authorization State Must Be Auditable

The system should provide a way for authorized user (client or developer) to verify:

- Current authorization status (trial/demo/permanent)
- Expiration date/time if still in trial
- Remaining trial usage count if usage-limited
- History of state transitions (when trial started, when renewed, when upgraded)

This aids transparency and dispute resolution.

## Template: Authorization Terms Documentation

When using trial authorization, include this in `assessment.md` or contract:

```markdown
### Trial Authorization Terms

- **Validity period**: 30 days from first launch
- **Clock source**: Developer server time (checked via API)
- **Expiration behavior**: System enters "read-only demo mode"; all data remains accessible for export
- **Renewal**: Not available (must upgrade to permanent)
- **Permanent authorization trigger**: Final payment of $X received; developer provides license key
- **Upgrade process**: Enter license key in Settings → License; system transitions to permanent within 24h
- **Data export**: CSV export available for all data types before and after expiration
```

## Verification

To verify authorization management compliance:

- [ ] Trial terms documented in writing (assessment.md or contract)
- [ ] Expiration behavior tested: system enters non-destructive mode on expiration
- [ ] Data export verified to work before and after expiration
- [ ] Permanent authorization transition tested with sample license key
- [ ] No evidence of data-destructive behavior on expiration (no deletion, no irreversible encryption)
- [ ] Client can view current authorization status within software

## Related Specs

- `spec.universal-domains.project-governance.delivery-control`: Overall delivery track selection and handover rules
- `spec.universal-domains.security.authn-authz`: If authorization is implemented as role-based access control
- `spec.universal-domains.verification.release-readiness`: Release gate includes authorization compliance check
