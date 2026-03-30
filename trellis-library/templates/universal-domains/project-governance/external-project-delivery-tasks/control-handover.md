# Task Template: Control Handover

## Purpose

Use this template to create a task for transferring administrative control of infrastructure, services, and deployment permissions to the client. This is the final step of handover.

## Applicability

- External projects where client will own or manage production environment
- For pure hosted/SaaS arrangements where developer retains infrastructure control indefinitely, this task is N/A
- Typically part of `permanent-authorization-delivery` or standalone for infrastructure handover

---

## Task Specification

| Field | Value |
|-------|-------|
| Task ID | DELIVERY-CTRL-001 |
| Task Name | Transfer Control and Admin Access |
| Task Type | 交付任务 |
| Risk Level | L2 (high) - security and access control |
| AI Execution Mode | Human-led (access control changes require care) |
| Evaluation Set | Access verification tests |

### Specific Requirements

1. Inventory all infrastructure and services requiring control transfer:
   - Cloud provider accounts (AWS, GCP, Azure, etc.)
   - Domain registrar and DNS management
   - Database servers and databases
   - Object storage (S3, etc.)
   - CDN services (Cloudflare, etc.)
   - Monitoring/observability services (Grafana Cloud, Datadog, etc.)
   - CI/CD platforms (GitHub Actions, GitLab CI, etc.)
2. For each item, document current access control setup
3. Prepare transfer plan:
   - Role changes (remove developer, add client)
   - Account transfer (if applicable)
   - Credential rotation (recommended: client creates new credentials, developer revokes old)
4. Execute transfer according to plan
5. Verify client can access each system
6. Document post-transfer access matrix (who has what)
7. Revoke developer access where appropriate (retain only if support contract)
8. Update `transfer-checklist.md` with control handover items

### Functional Boundary

**Included**:

- Cloud/Infrastructure admin access transfer
- Domain registrar/DNS control transfer
- Database admin access transfer
- CI/CD admin access transfer (if client manages deployments)
- Monitoring/alerting admin access transfer
- Documentation of post-transfer access rights

**Excluded**:

- Day-to-day operational support (separate support contract)
- Future access requests (handled by client's internal processes after transfer)
- Infrastructure provisioning from scratch (that was done in earlier tasks)

### Technical Constraints

- Transfer must not disrupt running services (minimize downtime)
- Prefer credential rotation over sharing existing credentials
- Document MFA recovery procedures (critical!)
- Ensure client understands responsibility for securing transferred access
- Developer should retain read-only audit access if support contract exists

### Acceptance Criteria

- [ ] All infrastructure/services inventoried and transfer plan approved
- [ ] Client admin accounts created with appropriate permissions (not using developer's personal accounts)
- [ ] Client verified they can log in to each system
- [ ] Developer's access revoked or downgraded to read-only (as per agreement)
- [ ] MFA and recovery procedures documented and transferred
- [ ] Post-transfer access matrix documented and acknowledged by client
- [ ] No service outage during transfer (or minimal, planned downtime)
- [ ] `transfer-checklist.md` control handover section completed

### Dependencies

- Infrastructure already provisioned and running
- Client organization and contact persons identified
- Payment received (if control transfer is payment-triggered)

### Execution Conditions

**Start when**:

- Infrastructure is running and stable
- Client has identified admin users
- Payment conditions met (if applicable)

**Wait if**:

- Client has not designated admin users
- Payment not received (for payment-triggered transfer)
- Critical services are in unstable state (avoid transferring broken systems)

**Parallel属性**: 可与 `DELIVERY-SECRETS`、`DELIVERY-SRC` 并行，但应在 `DELIVERY-PERMANENT` 主链中

---

## Definition of Ready (DoR)

- [ ] Complete infrastructure inventory available
- [ ] Client admin contacts and usernames/emails collected
- [ ] Transfer method for each system defined (role change, account transfer, etc.)
- [ ] Risk assessment completed (impact of transfer on service availability)

---

## Definition of Done (DoD)

- [ ] Client confirmed they can access all transferred systems
- [ ] Developer's access removed or read-only (as agreed)
- [ ] Access documentation updated with final state
- [ ] `transfer-checklist.md` completed for all control items
- [ ] No service interruption or all planned downtime communicated and completed

---

## Notes

- **Security best practice**: Do NOT share your own credentials with client. Instead, create new IAM/users for client admins and delete your credentials after transfer.
- **Domain transfer**: Process varies by registrar; may require client to initiate transfer to their account. Document steps.
- **Multi-factor authentication**: Ensure client's admin users have MFA enabled before granting access. Document MFA recovery process (who has recovery codes, how to reset if lost).
- **CI/CD access**: If client will manage deployments, ensure they have access to repository admin and CI/CD admin. Revoke developer-only service accounts if no longer needed.
- **Support transition**: If developer is retained for support, define clearly which access developer retains (read-only logs, limited incident response) and document in support agreement.
