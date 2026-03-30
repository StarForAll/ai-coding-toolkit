# Task Template: Source Code Transfer

## Purpose

Use this template to create a task for transferring complete source code and build materials to the client. This is a component of the final handover.

## Applicability

- External projects where source code is a deliverable (self-hosted or client-owned projects)
- NOT applicable for pure SaaS or hosted-only arrangements where client never receives source
- Can be used independently or as part of `permanent-authorization-delivery`

---

## Task Specification

| Field | Value |
|-------|-------|
| Task ID | DELIVERY-SRC-001 |
| Task Name | Transfer Source Code and Build Artifacts |
| Task Type | Delivery Task |
| Risk Level | L2 (high) - irreversible transfer of IP |
| AI Execution Mode | Automated packaging + human verification |
| Evaluation Set | Checksum verification, build-from-source test |

### Specific Requirements

1. Prepare complete source code bundle (include all dependencies that are not vendored)
2. Generate cryptographic hash (SHA256) of source bundle
3. Verify bundle completeness (no missing files, no `.git` history truncation if needed)
4. Include build scripts, CI/CD configs, and any developer tooling needed to reproduce builds
5. Include dependency lock files to ensure reproducible builds
6. Document any proprietary or third-party components with incompatible licenses
7. Transfer bundle to client via secure channel (encrypted archive, repository access)
8. Verify client can access and extract bundle
9. Optionally: have client build from source to verify completeness
10. Archive transfer record with hash and timestamp

### Functional Boundary

**Included**:

- All source code files (application code, scripts, configs)
- Build system (scripts, Makefile, package.json, etc.)
- Dependency manifests (`requirements.txt`, `Cargo.toml`, `pom.xml`, etc.) and lock files
- CI/CD configuration (if part of deliverable)
- Developer documentation (README, architecture docs, ADRs)
- License file(s) if applicable

**Excluded**:

- Build outputs (binaries, dist/ folders) — these are separate deliverable
- Secrets and production credentials — separate handover task
- Third-party dependencies that are not redistributable (client must obtain separately)

### Technical Constraints

- Use archive format that preserves permissions (tar, zip with Unix permissions)
- Compress appropriately (gzip, bzip2, xz)
- Provide checksum for integrity verification
- Use secure transfer (encrypted email, secure file share, SSH, etc.)
- Document any non-standard tools required to build

### Acceptance Criteria

- [ ] Source bundle includes all files needed to build application from scratch
- [ ] Bundle checksum recorded and shared with client
- [ ] Client verified receipt and could extract bundle
- [ ] Client verified they can run build command (or test build successful)
- [ ] Any third-party dependencies with redistribution restrictions are documented
- [ ] License terms clearly stated and client acknowledged
- [ ] Transfer recorded in `transfer-checklist.md`

### Dependencies

- Final application version committed and tagged
- Build system confirmed working on clean checkout
- Decision on whether to include `.git` history (optional but nice to have)

### Execution Conditions

**Start when**:

- Final code freeze completed
- Build from clean checkout verified
- Payment confirmed (if source transfer is payment-triggered)

**Wait if**:

- Payment not yet received (for payment-triggered handover)
- Build system incomplete or broken

**Parallel Execution**: Can run in parallel with `DELIVERY-SECRETS`, but should still remain within the sequential `DELIVERY-PERMANENT` handover chain

---

## Definition of Ready (DoR)

- [ ] Final code version tagged (e.g., `v1.0.0` or `release-2025-03-30`)
- [ ] Build from clean checkout passes all tests
- [ ] `.gitignore` appropriate for client (no local secrets, no IDE files)
- [ ] Transfer method (repository access or archive) decided

---

## Definition of Done (DoD)

- [ ] Source bundle created with SHA256 checksum
- [ ] Client received bundle and confirmed checksum matches
- [ ] Client can build application from source (verified or self-reported)
- [ ] `transfer-checklist.md` source code section completed
- [ ] Transfer evidence archived (checksum, transfer log, client acknowledgment)

---

## Notes

- If providing repository access instead of archive, document:
  - Repository URL
  - Access method (SSH key, HTTPS with credentials)
  - Client's username/access level
  - Whether full history or shallow clone is provided
- Consider providing `.git` history for transparency, but ensure no sensitive data in history (use `git filter-repo` if needed)
- For very large repos, archive might be impractical; repository access preferred.
- License considerations: ensure you have right to distribute all included code (MIT, BSD, Apache OK; GPL requires source availability anyway; proprietary third-party libs may need exclusion).
