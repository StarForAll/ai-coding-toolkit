# Task Template: Hosted Deployment Setup

## Purpose

Use this template to create a task for preparing and configuring a hosted trial environment for client verification. This task is only for projects using the `hosted_deployment` delivery track.

## Applicability

- External projects (outsourcing, custom development, new clients)
- Delivery track: `hosted_deployment`
- Developer maintains control of production until final payment
- Client gets access to trial/demo environment for verification

---

## Task Specification

| Field | Value |
|-------|-------|
| Task ID | DELIVERY-HOSTED-001 |
| Task Name | Setup Hosted Trial Environment |
| Task Type | 交付任务 |
| Risk Level | L1 (medium) - involves client-accessible environment |
| AI Execution Mode | Semi-automated (infrastructure as code preferred) |
| Evaluation Set | Infrastructure validation tests |

### Specific Requirements

1. Provision trial/staging environment (separate from eventual production)
2. Deploy application to trial environment
3. Seed trial/demo data if needed
4. Configure client access (VPN, SSO, or direct credentials)
5. Test client access flow
6. Document environment URL, access method, credentials
7. Provide client with access instructions
8. Verify client can log in and explore core features
9. Define trial period duration and post-trial degradation (if any)
10. Set up monitoring for trial environment usage (optional)

### Functional Boundary

**Included**:

- Trial environment provisioning (cloud or on-prem)
- Application deployment to trial environment
- Client access setup and testing
- Access documentation for client

**Excluded**:

- Production environment deployment (deferred until final payment)
- Client data migration from trial to production (if applicable, separate task)
- Long-term production support (handled by support contract if any)

### Technical Constraints

- Trial environment must be isolated from production (no shared database)
- Client access should be revocable (in case of non-payment or abuse)
- Trial environment should be cost-efficient (auto-shutdown, low-spec)
- Security: client should not have access to developer's production secrets

### Acceptance Criteria

- [ ] Trial environment URL reachable and responsive
- [ ] Client test account can log in
- [ ] Core features accessible in trial environment
- [ ] Trial environment data is isolated from production
- [ ] Client can complete key user journeys (onboarding, primary use case)
- [ ] Access credentials and instructions delivered to client
- [ ] Trial period or access limitations clearly communicated
- [ ] Developer can revoke access if needed (security measure)

### Dependencies

- Application built and tested
- Infrastructure provisioning scripts/automation ready
- `assessment.md` specifies `delivery_control_track: hosted_deployment`

### Execution Conditions

**Start when**:

- Application build ready for deployment
- Infrastructure as code (Terraform, CloudFormation, etc.) or provisioning scripts exist
- Delivery track confirmed as `hosted_deployment`

**Wait if**:

- Application not yet built
- Infrastructure automation not ready
- Client payment terms not finalized

**Parallel属性**: 可与 `DELIVERY-TRIAL-xxx` 并行（如果意外选择了两个轨道则冲突，但逻辑上互斥）

---

## Definition of Ready (DoR)

- [ ] Build artifact available (Docker image, binary, etc.)
- [ ] Infrastructure provisioning method defined
- [ ] Client access credentials plan established
- [ ] Trial environment specification (region, specs, budget) approved

---

## Definition of Done (DoD)

- [ ] Trial environment deployed and accessible
- [ ] Client can log in and use core features (verified by client or test video)
- [ ] Access credentials and documentation delivered
- [ ] Trial period and access revocation policy communicated
- [ ] Environment monitoring/alerts configured (optional but recommended)
- [ ] `delivery/hosted-deployment-evidence/` contains environment access test logs

---

## Notes

- Hosted deployment track means developer retains production control until final payment.
- Trial environment should be clearly distinguished from eventual production environment.
- Consider using lower-cost infrastructure for trial (can be shut down after trial period).
- Client should understand that trial environment is for verification only and may be reset/reprovisioned.
