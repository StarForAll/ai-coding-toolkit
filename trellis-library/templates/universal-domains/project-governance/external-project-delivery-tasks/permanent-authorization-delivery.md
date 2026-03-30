# Task Template: Permanent Authorization Delivery

## Purpose

Use this template to create a task for delivering permanent authorization and full control to the client after final payment confirmation. This is the final handover task for both `hosted_deployment` and `trial_authorization` tracks.

## Applicability

- External projects where final payment has been received
- This is the final handover task
- Applies to both delivery tracks

---

## Task Specification

| Field | Value |
|-------|-------|
| Task ID | DELIVERY-PERMANENT-001 |
| Task Name | Permanent Authorization and Final Handover |
| Task Type | 交付任务 |
| Risk Level | L2 (high) - irreversible transfer of control |
| AI Execution Mode | Human-led with AI documentation assistance |
| Evaluation Set | Transfer checklist completeness |

### Specific Requirements

1. Verify final payment received (attach proof)
2. Generate or provide permanent authorization credential (license key, admin account, etc.)
3. Transfer source code repository access or archive
4. Transfer all secrets and configuration (production environment variables, certificates, API keys)
5. Transfer infrastructure control (server admin, cloud account roles, domain ownership)
6. Transfer operations documentation (runbooks, monitoring, backup/restore)
7. Conduct handover meeting with client
8. Obtain client sign-off or electronic acknowledgment
9. Archive complete delivery package record
10. Update project status to "Delivered" or "Closed"

### Functional Boundary

**Included**:

- Full source code transfer
- Permanent authorization (unrestricted version)
- All admin credentials and secrets
- Infrastructure control (if self-hosted)
- Final documentation package

**Excluded**:

- Ongoing support (unless separate support contract)
- Bug fixes discovered after delivery (handled via warranty or change requests)
- Feature enhancements (new project scope)

### Technical Constraints

- Transfer must be secure (encrypted channels for credentials)
- Transfer must be complete (no missing files or credentials)
- Client must acknowledge receipt and ability to access
- Developer should retain backup of delivered artifacts for warranty period

### Acceptance Criteria

- [ ] Final payment confirmed and recorded
- [ ] Transfer checklist fully completed with all items checked
- [ ] Client received all items in `deliverables.md` index
- [ ] Client verified they can:
  - [ ] Access source code repository
  - [ ] Build and deploy application
  - [ ] Access production environment (if applicable)
  - [ ] Use permanent authorization without restrictions
- [ ] Client signed handover receipt or provided written acceptance
- [ ] Developer archived delivery evidence and signed-off record
- [ ] Project status updated to "Delivered"

### Dependencies

- All core functionality implemented and accepted
- Trial delivery completed (if using `trial_authorization` track)
- Hosted trial environment available for client verification (if using `hosted_deployment` track)
- `transfer-checklist.md` prepared

### Execution Conditions

**Start when**:

- Final payment confirmed received
- All functional acceptance criteria met
- No P0/P1 defects outstanding

**Wait if**:

- Payment not received
- Client has outstanding acceptance issues
- Delivery checklist incomplete

**Parallel属性**: 无（final handover 必须串行且完整）

---

## Definition of Ready (DoR)

- [ ] Final payment proof available
- [ ] All deliverable items identified and prepared
- [ ] Client contact for handover confirmed
- [ ] Transfer checklist initialized but incomplete

---

## Definition of Done (DoD)

- [ ] Client has physically received all items (repository access, credentials, docs)
- [ ] Client verified they can operate the system independently
- [ ] Client signed handover document or provided written acceptance via email
- [ ] Developer archived complete delivery record including:
  - `delivery/deliverables.md` with checksums
  - `delivery/transfer-checklist.md` fully checked
  - Payment confirmation
  - Client acceptance communication
- [ ] Project marked "Delivered" in task tracker
- [ ] Developer support warranty period (if any) started and documented

---

## Notes

- This is the **final delivery task**. After completion, developer's obligation is limited to warranty (if offered) and knowledge transfer during warranty period.
- For `hosted_deployment` track: after this task, developer transfers production environment control to client. Developer should also provide migration support if client wants to move to self-hosted.
- For `trial_authorization` track: this task upgrades client from trial to permanent authorization and provides full source code.
- Keep a copy of all delivered artifacts for warranty period (typically 30-90 days) in case client loses them.
