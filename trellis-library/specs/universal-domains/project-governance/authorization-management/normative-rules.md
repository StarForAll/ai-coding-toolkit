# Authorization Management — Normative Rules

## Core Rules

### RA-1: Trial Terms Must Be Explicit and Documented

Before implementing trial authorization, document:

- Validity period (start → end)
- Clock source (system vs server)
- Usage limits if applicable (count-based)
- Expiration behavior (demo mode, read-only, etc.)
- Renewal availability and conditions
- Upgrade path to permanent

**Documentation location**: `assessment.md` or signed contract attachment.

### RA-2: Expiration Must Be Non-Destructive

On authorization expiration:

- Preserve all user data
- Allow full data export
- Disable only the restricted features
- Provide clear upgrade instructions
- Do NOT delete, encrypt (without providing key), or corrupt data

**Rationale**: Ethical licensing. Trial should convert, not coerce.

### RA-3: State Should Be Visible and Auditable

Within the application, provide a "License Information" or "Authorization Status" page showing:

- Current status: Trial / Expired / Permanent
- Expiration date if in trial
- Days remaining or uses remaining
- Last check-in time with licensing server (if applicable)

This transparency reduces disputes.

### RA-4: Transition to Permanent Should Be Seamless

Upon applying permanent license:

- No reinstallation required
- User data and settings preserved
- Trial restrictions lifted immediately or within brief verification window
- Authorization status updates without manual migration steps

If online activation is required, it should be a lightweight process (not a full re-download).

## Implementation Guidance

### Clock Synchronization

If using time-based expiration:

- Prefer UTC or timezone-independent timestamps
- If using client system clock, accept drift but log warnings
- For high-value software, consider server-side time validation to prevent clock rollback attacks

### Grace Periods

Consider a short grace period (1-3 days) after expiration:

- Allows for payment processing delays
- Client still has access during upgrade coordination
- Clearly communicate grace period in UI

### Offline Operation

If software must work offline:

- Clock-based expiration can be circumvented by setting system clock back
- Mitigation: store last-known-good timestamp securely, refuse to run if clock rolled back
- Or use usage-count based model instead of time

## Compliance Checklist

- [ ] Trial terms documented and client-signed
- [ ] Expiration behavior tested: data remains accessible and exportable
- [ ] Authorization status page exists and shows all required info
- [ ] Permanent license application does not require reinstall or data migration
- [ ] No evidence of destructive behavior on expiration (data deletion, irreversible encryption)
