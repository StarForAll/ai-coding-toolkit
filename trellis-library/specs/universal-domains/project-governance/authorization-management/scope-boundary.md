# Authorization Management — Scope Boundary

## In Scope

- Trial authorization terms definition and documentation
- Expiration behavior rules (must be non-destructive)
- Renewal process design (if offered)
- Permanent authorization transition mechanics
- Authorization state auditability

## Out of Scope

- General authentication/authorization (RBAC, OAuth, JWT) — see `spec.universal-domains.security.authn-authz`
- DRM or copy protection schemes
- Hardware-based licensing (dongles, TPM)
- Subscription billing integration (payment collection is separate)
- License key generation algorithms (security of the key system itself)

## Cross-Domain Dependencies

- `spec.universal-domains.project-governance.delivery-control`: Authorization management is only relevant for `trial_authorization` track
- `spec.universal-domains.verification.evidence-requirements`: Must provide test evidence of expiration behavior
