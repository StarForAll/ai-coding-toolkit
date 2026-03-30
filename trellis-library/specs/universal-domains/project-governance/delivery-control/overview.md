# Delivery Control

## Purpose

Define reusable rules for controlling external project delivery, including dual-track delivery (hosted deployment vs trial authorization), payment-triggered handover, and prohibition of undisclosed termination mechanisms.

## Applicability

Use this concern for外包、定制开发、新客户项目等需要控制源码、密钥、权限移交时机的场景。

## Scope Boundary

This spec governs:

- Delivery control轨道选择（托管部署 vs 试运行授权）
- 尾款到账前的交付限制（仅提供试运行环境/演示地址）
- 尾款到账后的正式移交（源码、密钥、管理员权限）
- 禁止的交付行为（未披露的失效机制、远程锁定、数据破坏）

This spec does NOT govern:

- 内部项目的交付流程
- 开源项目的公开发布
- 持续交付（CI/CD）的自动化部署

## Normative Rules

### Delivery Track Selection

1. **Default Track: Hosted Deployment**
   - Developer maintains control of production environment
   - Client accesses trial/demo environment for verification
   - Final handover (source code, admin credentials, deployment control) occurs after final payment

2. **Alternative Track: Trial Authorization**
   - Only used when client explicitly requires early access to runnable version
   - Must be disclosed in quotation, contract, delivery documentation
   - Authorization terms must be explicit:
     - Validity period
     - Renewal mechanism
     - Expiration behavior (must be "demo mode" or "read-only", never data-destructive)
     - Conditions for permanent authorization (final payment trigger)

### Prohibited Practices

- ❌ Undisclosed backdoors or hidden switches
- ❌ Remote kill switches that can disable client's operation
- ❌ Irreversible data locking or export prevention
- ❌ "Obfuscated delivery" (deliberately unreadable code pretending to be source)
- ❌ Misrepresenting trial version as "full unrestricted delivery"

### Payment-to-Handover Coupling

- Source code repository access or package
- Permanent authorization file or unrestricted version
- Build scripts, deployment scripts, CI/CD configurations
- Production environment variables, secrets, certificates, third-party configs
- Server, domain, database, object storage admin credentials
- Final operations documentation, rollback procedures, handover records

**All above items must be withheld until final payment is confirmed**, unless alternative track with explicit terms is agreed.

## Verification

To verify delivery control compliance:

- [ ] `assessment.md` specifies chosen delivery track before project start
- [ ] Contract/quotation discloses trial authorization terms if using alternative track
- [ ] No source code, secrets, or admin credentials shared before final payment (for default track)
- [ ] Trial version has clear expiration behavior that preserves client data
- [ ] Final handover checklist completed only after payment confirmation
- [ ] Delivery documentation clearly distinguishes "trial" vs "permanent" deliverables
