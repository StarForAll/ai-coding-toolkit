# Task Template: Secrets and Configuration Transfer

## Purpose

Use this template to create a task for securely transferring all secrets, certificates, and environment configuration to the client.

## Applicability

- External projects where client will manage production environment or needs API credentials
- For hosted-only arrangements where developer retains all secrets, this task may be N/A
- Can be standalone or part of final handover

---

## Task Specification

| Field | Value |
|-------|-------|
| Task ID | DELIVERY-SECRETS-001 |
| Task Name | Transfer Secrets and Configuration |
| Task Type | Delivery Task |
| Risk Level | L2 (high) - security-sensitive |
| AI Execution Mode | Human-led (security-critical) |
| Evaluation Set | Access verification, rotation tests |

### Specific Requirements

1. Inventory all secrets and sensitive configuration:
   - Database passwords and connection strings
   - API keys and tokens (Stripe, SendGrid, etc.)
   - SSL/TLS certificates and private keys
   - Cloud service credentials (AWS keys, GCP service accounts, etc.)
   - JWT signing keys, encryption keys
   - Third-party integration secrets
   - Admin passwords for any client-controlled systems
2. For each secret, document:
   - Purpose (what it's used for)
   - Location/usage in the application
   - Rotation procedure (if compromised)
   - Expiration date if applicable
3. Prepare transfer:
   - Generate new credentials for client where possible (do NOT share developer's personal credentials)
   - For certificates: provide certificate files and private keys, or provide certificate signing request (CSR) process
   - Document any credentials that cannot be transferred (e.g., developer's own OAuth client secrets that must be recreated by client)
4. Transfer via secure channel (encrypted email, password manager share, in-person, etc.)
5. Have client verify receipt and test at least one critical secret (e.g., database connection)
6. Invalidate developer's credentials where appropriate (or rotate if needed for support)
7. Document post-transfer credential ownership matrix

### Functional Boundary

**Included**:

- All runtime secrets needed to operate the system
- SSL/TLS certificates and private keys
- Environment variable templates with placeholders for actual values
- Credential rotation instructions

**Excluded**:

- Developer's personal account credentials (these should be revoked, not transferred)
- Secrets that are not needed by client (e.g., third-party accounts that developer will continue to manage under support contract)
- Ongoing secret rotation (client's responsibility after handover)

### Technical Constraints

- Transfer via secure channel only (no plaintext email, no public Slack channels)
- Prefer out-of-band transfer (encrypted archive with password shared via separate channel)
- Encourage client to rotate secrets after first use (generate new keys, revoke transferred ones if they were developer's)
- Document expiration dates for time-bound credentials
- Do NOT commit secrets to repository at any point during transfer

### Acceptance Criteria

- [ ] Complete inventory of all secrets and sensitive configuration documented
- [ ] Transfer method chosen is secure and agreed with client
- [ ] Client confirmed receipt of all items
- [ ] Client verified at least one critical secret works (e.g., connected to database)
- [ ] Any developer-owned credentials that were transferred are documented for future rotation
- [ ] Post-transfer access matrix documented (who owns which secret)
- [ ] `transfer-checklist.md` secrets section completed

### Dependencies

- Application configuration fully documented
- Client has identified admin recipients for secrets
- Delivery track finalized (secrets transfer is part of final handover)

### Execution Conditions

**Start when**:

- Application configuration is final
- Client has designated security admins
- Final payment received (if secrets transfer is payment-triggered)

**Wait if**:

- Client has not designated recipients
- Configuration not yet finalized (secrets may still be in flux)
- Payment not received (for payment-triggered delivery)

**Parallel Execution**: Can run in parallel with `DELIVERY-SRC` and `DELIVERY-CTRL`

---

## Definition of Ready (DoR)

- [ ] All application secrets identified and documented
- [ ] Client security contacts identified
- [ ] Secure transfer method prepared (e.g., password-protected ZIP, password manager share)
- [ ] Any credential rotation needed before transfer is planned

---

## Definition of Done (DoD)

- [ ] Client confirmed receipt of all secrets
- [ ] Client verified at least database connection works
- [ ] Any shared credentials are scheduled for rotation by client (documented)
- [ ] `transfer-checklist.md` secrets section fully checked
- [ ] Developer has removed or rotated any shared credentials from their personal accounts

---

## Security Warnings

- **Never** commit secrets to git, even in private repos. Use `.gitignore` and environment variables.
- **Never** send secrets via unencrypted channels. Assume any intercepted message will be exploited.
- **Encourage client to rotate**: Any credential that developer and client both know should be rotated (developer generates new for themselves, client generates new for themselves).
- **Certificate private keys**: Transfer with extreme care. Prefer providing CSR and having client generate their own private key. If developer-generated, strongly recommend client regenerate.

---

## Notes

- This task is security-critical. Take time to do it right. A secret leak after delivery can compromise both client and developer.
- If the project uses a secrets management system (Vault, AWS Secrets Manager, etc.), document access policies and how to grant client admin access to the system.
- For cloud credentials, consider using IAM roles and cross-account access rather than sharing root credentials. Document least-privilege principle.
