# External Project Transfer Checklist

**Purpose**: Verify all required items are handed over to client upon project completion, after final payment confirmation.

**Scope**: For external projects (outsourcing, custom development, new clients) only. Internal projects skip this checklist.

**Gate**: All items must be checked before delivery is marked complete.

---

## Pre-Transfer Prerequisites

- [ ] Final payment confirmed received (attach payment receipt or bank record reference)
- [ ] All core functionality tested and accepted by client (acceptance criteria met)
- [ ] No critical (P0/P1) bugs outstanding
- [ ] Client has identified delivery contact and handover meeting scheduled

---

## Source Code and Build Artifacts

- [ ] Source code repository cloned/archived (provide `.tar.gz` or repository access)
- [ ] Repository hash/commit ID recorded and verified with client
- [ ] Build scripts present and verified (`package.json`, `Makefile`, `build.gradle`, etc.)
- [ ] CI/CD configuration included if applicable (`.github/workflows/`, `.gitlab-ci.yml`)
- [ ] Dependencies lock file included (`package-lock.json`, `Pipfile.lock`, `Cargo.lock`)
- [ ] README with build instructions updated and tested from scratch

---

## Secrets and Configuration

- [ ] Production environment variables documented (template `.env.example` or equivalent)
- [ ] All API keys, tokens, certificates transferred via secure channel (not in repo)
- [ ] Database connection strings and credentials transferred securely
- [ ] Third-party service credentials (AWS, GCP, Azure, etc.) handed over
- [ ] Client confirmed receipt and ability to rotate secrets if desired

**Note**: For hosted deployment track, this section may be "N/A - developer retains control". For trial authorization or self-hosted projects, this section is required.

---

## Infrastructure and Deployment

- [ ] Server access credentials (SSH, RDP, cloud console) transferred if client owns infrastructure
- [ ] Domain name ownership confirmed and transfer initiated (if applicable)
- [ ] SSL certificates transferred or re-issuance instructions provided
- [ ] Database admin credentials transferred (if client-managed database)
- [ ] Object storage (S3, etc.) access credentials transferred
- [ ] Deployment instructions documented (how to deploy to staging/production)

For hosted deployment where developer retains control, document instead:

- [ ] Client has access to trial/demo environment for verification
- [ ] Client understands developer retains production control until handover
- [ ] Post-handover support period and SLA documented

---

## Operations and Maintenance

- [ ] Operations manual/runbook provided (startup, shutdown, backup, restore)
- [ ] Monitoring and alerting setup documented (Grafana, CloudWatch, etc.)
- [ ] Log aggregation access credentials provided
- [ ] Incident response procedures documented
- [ ] Backup schedule and restore procedures documented and tested
- [ ] Rollback procedures for deployments documented

---

## Documentation

- [ ] User manual (end-user documentation) provided
- [ ] Administrator guide (for system management) provided
- [ ] API documentation (if applicable) provided and verified
- [ ] Architecture decision records (ADRs) included if available
- [ ] Known issues and workarounds documented

---

## Final Verification

- [ ] Client has reviewed complete deliverable package
- [ ] Client has tested deployment in trial/staging environment (if applicable)
- [ ] Client has signed handover receipt or provided written acceptance
- [ ] Developer and client agree on post-delivery support terms (if any)
- [ ] Warranty period and scope defined (if offered)

---

## Delivery Artifacts Index

After handover, generate `delivery/deliverables.md` listing all delivered items with checksums:

```markdown
## Delivered Items

| Item | Format | Checksum (SHA256) | Notes |
|------|--------|-------------------|-------|
| Source code | repository.tar.gz | abc123... | Commit abc123 |
| Build script | build.sh | def456... | Tested on Ubuntu 22.04 |
| Env template | .env.example | ghi789... | Secrets transferred separately |
| ... | ... | ... | ... |
```

---

## Sign-Off

**Developer**: ___________________ Date: ___________

**Client**: _____________________ Date: ___________

**Project Name**: ___________________

**Task Directory**: `$PLAN_TASK_DIR`

---

## References

- `spec.universal-domains.project-governance.delivery-control`: Delivery control rules
- `spec.universal-domains.project-governance.authorization-management`: Trial authorization terms
- Workflow: `docs/workflows/新项目开发工作流/commands/delivery.md` Step 6
