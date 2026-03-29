# Acceptance Quality Checklist

## Purpose

This checklist helps verify that acceptance criteria are well-defined, measurable, and actionable. Use this checklist during requirement review and quality assurance processes.

## Checklist Items

### Outcome-Based Criteria
- [ ] **Observable Outcomes**: Acceptance criteria describe observable outcomes that can be verified through testing, observation, or measurement
- [ ] **No Implementation Guesses**: Criteria focus on what should happen, not how it should be implemented
- [ ] **Customer-Visible Results**: Success can be observed from the customer or end-user perspective
- [ ] **Business Value Focus**: Each criterion contributes to achieving business objectives

### Scope Clarity
- [ ] **Scope Definition**: What is included in the current scope is clearly defined
- [ ] **Out-of-Scope Items**: Items explicitly not included are listed and justified
- [ ] **No Scope Mixing**: Core commitments, enhancements, and out-of-scope items are separated clearly
- [ ] **Scope Boundaries**: Boundaries between different phases or versions are well-defined

### Success and Failure Conditions
- [ ] **Success Conditions**: What constitutes successful completion is clearly defined
- [ ] **Failure Conditions**: What constitutes failure or rejection is clearly defined
- [ ] **Partial Success**: Conditions for partial success or degraded performance are defined where applicable
- [ ] **Edge Cases**: Boundary conditions and edge cases are considered

### Measurability and Evidence
- [ ] **Measurable Criteria**: Each criterion can be measured quantitatively where possible
- [ ] **Evidence-Based**: Success can be demonstrated through evidence (logs, metrics, test results)
- [ ] **No Intuition-Based**: Criteria do not rely on subjective judgment or intuition alone
- [ ] **Clear Pass/Fail**: It is clear when a criterion passes or fails

### Assumptions and Dependencies
- [ ] **Explicit Assumptions**: All assumptions underlying the criteria are documented
- [ ] **Unresolved Ambiguity**: Any ambiguous requirements are flagged for clarification
- [ ] **Dependency Identification**: Dependencies that affect acceptance are identified
- [ ] **Risk Acknowledgment**: Risks that might affect acceptance are noted

## Scoring System

### Compliance Levels
- **Fully Compliant (✓)**: Criterion is completely and clearly met
- **Partially Compliant (△)**: Criterion is partially met but needs improvement
- **Non-Compliant (✗)**: Criterion is not met or is missing

### Minimum Requirements
- All criteria must be at least partially compliant
- At least 80% of criteria must be fully compliant
- No "Non-Compliant" ratings on outcome-based or measurability items

## Usage Guidelines

### When to Use
- During requirement review processes
- Before sign-off on product requirements
- When creating or updating acceptance criteria
- During quality assurance of deliverables

### How to Use
1. Review each checklist item against your acceptance criteria
2. Mark each item as ✓, △, or ✗
3. Document specific evidence for each rating
4. Address any non-compliant items before final approval
5. Track improvements and re-evaluate as needed

## Integration with PRD Specifications

This checklist integrates with:
- **Customer-Facing PRD Verification**: Use to validate business-facing acceptance criteria
- **Developer-Facing PRD Verification**: Use to validate technical acceptance criteria
- **Acceptance Criteria Template**: Use as a guide when creating new acceptance criteria

## Related Documents

- `spec.universal-domains.product-and-requirements.acceptance-criteria`: Detailed specification for acceptance criteria
- `template.universal-domains.product-and-requirements.acceptance-criteria-template`: Template for creating acceptance criteria
- `spec.universal-domains.product-and-requirements.prd-documentation-customer-facing.verification`: Customer-facing PRD verification
- `spec.universal-domains.product-and-requirements.prd-documentation-developer-facing.verification`: Developer-facing PRD verification
