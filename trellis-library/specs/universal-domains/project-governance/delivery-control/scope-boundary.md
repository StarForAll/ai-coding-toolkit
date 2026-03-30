# Delivery Control — Scope Boundary

## In Scope

- External projects (outsourcing, custom development, new clients) where developer retains control until final payment
- Trial authorization agreements with explicit terms
- Payment-triggered handover of source code, secrets, admin credentials, deployment control
- Prohibited delivery practices definition and enforcement

## Out of Scope

- Internal projects within same organization (no payment-triggered handover)
- Open source public releases
- Continuous delivery pipelines for SaaS products
- Ongoing maintenance contracts after project completion
- Third-party software distribution where developer never retains control

## Cross-Domain Dependencies

- `spec.universal-domains.project-governance.change-management`: Delivery track changes must follow change management
- `spec.universal-domains.security.secrets-and-config`: Secrets handover rules
- `spec.universal-domains.verification.release-readiness`: Release readiness includes delivery control compliance
