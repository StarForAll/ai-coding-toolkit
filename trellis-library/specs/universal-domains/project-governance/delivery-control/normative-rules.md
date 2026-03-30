# Delivery Control — Normative Rules

## Must-Follow Rules (强制)

### RD-1: Delivery Track Must Be Decided Before Work Begins

Before entering implementation, the project must have a documented delivery control track in `assessment.md`:

- `hosted_deployment` (default)
- `trial_authorization` (with explicit terms)
- `undecided` → must be resolved before moving from feasibility to brainstorm

**Rationale**: Delivery control affects task planning, payment terms, and legal exposure. Deciding late causes rework and negotiation risk.

### RD-2: Default Track Withholds Control Until Final Payment

For `hosted_deployment` track:

- ❌ DO NOT deliver source code repository access before final payment
- ❌ DO NOT share production environment credentials before final payment
- ❌ DO NOT provide permanent authorization before final payment
- ✅ DO provide trial/demo environment for verification
- ✅ DO deliver all artifacts to client after payment confirmation

**Exception**: If client explicitly agrees to分期付款与分期移交，must be documented in change management record.

### RD-3: Trial Authorization Must Be Fully Disclosed

If using `trial_authorization` track, the following MUST be in writing (quotation, contract, or `assessment.md`):

1. **Authorization validity period**: explicit start and end dates, or condition-based expiration
2. **Renewal mechanism**: how client can extend trial, under what conditions
3. **Expiration behavior**:
   - Must degrade to "demo mode" or "read-only"
   - Must NOT destroy or lock client's data
   - Must allow data export before expiration
4. **Permanent authorization trigger**: typically "final payment received" or "signature on handover receipt"

### RD-4: No Undisclosed Termination Mechanisms

Developer may NOT embed:

- Hidden backdoors that can remotely disable client's usage
- Undocumented kill switches activated by developer
- Code obfuscation that prevents client from maintaining the system after handover
- Any mechanism whose existence is not disclosed in delivery documentation

**Rationale**: Trust and legal compliance. Client must have full visibility into what they are receiving.

### RD-5: Handover Must Be Atomic and Verifiable

Final handover (post-payment) must produce a signed/recorded `transfer-checklist.md` with:

- [ ] Source code (repository clone or archive) verified by hash
- [ ] Build and deployment instructions tested
- [ ] All secrets/configs transferred via secure channel
- [ ] Admin credentials for all external services
- [ ] Operations documentation and runbooks
- [ ] Client sign-off or electronic acknowledgment

## Should-Follow Rules (推荐)

### RS-1: Separate Trial and Production Environments

- Use separate infrastructure for trial/demo vs eventual production
- Prevent trial data from mixing with production data (GDPR/privacy risk)
- Allow trial environment to be reset/reprovisioned without affecting client's eventual production data

### RS-2: Provide Clear Upgrade Path

If using trial authorization, document:

- What changes between trial and permanent version (feature unlocks, watermark removal, etc.)
- How client initiates upgrade (payment + handover process)
- Expected downtime during upgrade (aim for zero)

### RS-3: Document Trial Limitations Transparently

Trial version limitations should be clearly communicated:

- Feature restrictions (if any)
- Performance throttling (if any)
- Time limits
- Support level differences

Avoid surprising clients with "trial expires in 3 days" without prior warning.

## Compliance Checklist

When reviewing a project's delivery control compliance:

- [ ] Delivery track recorded in `assessment.md` before implementation starts
- [ ] If trial authorization: terms documented and client-signed
- [ ] No source code/secrets/admin credentials transferred before final payment (for hosted deployment)
- [ ] Trial expiration behavior is non-destructive and allows data export
- [ ] Final handover checklist completed with client acknowledgment
- [ ] No evidence of hidden termination mechanisms in codebase
