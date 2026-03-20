# Customer-Facing PRD Checklist

## Purpose

This checklist helps verify that customer-facing Product Requirement Documents (PRDs) are complete, clear, and appropriate for business stakeholders. Use this checklist during requirement review and quality assurance processes.

## Checklist Items

### 1. Language and Expression
- [ ] **Plain Language**: Document uses simple, non-technical language that business stakeholders can understand
- [ ] **Term Definitions**: All technical terms, acronyms, and specialized vocabulary are defined when first introduced
- [ ] **Jargon Elimination**: Internal system names, technical shorthand, and engineering terminology are avoided or translated
- [ ] **Customer Perspective**: Requirements are written from the customer's point of view, describing experiences and outcomes

### 2. Document Structure
- [ ] **Problem/Opportunity Section**: Clearly describes the problem being solved or opportunity being addressed
- [ ] **Target Users Section**: Identifies and describes primary and secondary users/stakeholders
- [ ] **Business Goals Section**: States measurable business objectives and expected outcomes
- [ ] **Scope Definition Section**: Clearly separates core features, enhancements, and out-of-scope items
- [ ] **Solution Overview Section**: Provides high-level description without technical implementation details
- [ ] **User Requirements Section**: Describes key user scenarios and requirements in customer terms
- [ ] **Delivery Priorities Section**: Outlines phasing and prioritization of features
- [ ] **Success Criteria Section**: Defines measurable success metrics from customer perspective
- [ ] **Open Questions Section**: Documents assumptions, dependencies, and pending decisions

### 3. Content Quality
- [ ] **Value Proposition**: Each requirement explains why it matters to the customer or business
- [ ] **Outcome Focus**: Requirements focus on business outcomes and customer experiences
- [ ] **Testability**: All success criteria can be objectively measured and verified
- [ ] **Completeness**: No critical requirements or assumptions are missing

### 4. Scope Boundary
- [ ] **Core Features Definition**: Core commitments for current phase are clearly defined
- [ ] **Enhancement Planning**: Future enhancements are identified and separated from deliverables
- [ ] **Out-of-Scope Clarity**: Items not included are listed with rationale
- [ ] **Scope Change Process**: Process for handling scope changes is documented

### 5. Validation Methods
- [ ] **Measurable Criteria**: Success criteria use quantifiable metrics where possible
- [ ] **Observable Outcomes**: Success can be observed through customer behavior or business metrics
- [ ] **Validation Approach**: Methods for validating success criteria are described
- [ ] **Acceptance Thresholds**: Clear thresholds for what constitutes success are defined

### 6. Examples and Documentation Quality
- [ ] **Example Clarity**: Examples, diagrams, or mockups clearly illustrate requirements
- [ ] **No Hidden Scope**: Examples do not imply additional features beyond stated requirements
- [ ] **Consistency**: All sections use consistent terminology and definitions
- [ ] **Review Evidence**: Document shows evidence of stakeholder review and feedback

### 7. Prohibited Content Check
- [ ] **No Technical Implementation**: Document does not contain API specifications or database schemas
- [ ] **No Internal References**: Internal system names and technical architecture are avoided
- [ ] **Business Language Only**: All concepts are translated into business-friendly descriptions

## Scoring System

### Compliance Levels
- **Fully Compliant (✓)**: Criterion is fully met (3 points)
- **Partially Compliant (△)**: Criterion is partially met (1 point)
- **Non-Compliant (✗)**: Criterion is not met (0 points)

### Minimum Requirements
- **Total Score**: Must achieve at least 21 out of 27 points (75% compliance)
- **Critical Items**: All items in sections 1, 2, and 3 must be at least partially compliant
- **No Blockers**: No "Non-Compliant" ratings on scope boundary or success criteria sections

### Scoring Table
| Section | Max Points | Your Score | Status |
|---------|------------|------------|--------|
| Language and Expression | 3 | | |
| Document Structure | 9 | | |
| Content Quality | 4 | | |
| Scope Boundary | 4 | | |
| Validation Methods | 4 | | |
| Examples and Documentation | 3 | | |
| Prohibited Content | 3 | | |
| **Total** | **30** | | |

## Usage Guidelines

### When to Use
- During customer-facing PRD creation or review
- Before stakeholder sign-off on business requirements
- When updating existing customer-facing documents
- During quality assurance of business documentation

### How to Use
1. Review each checklist item against your customer-facing PRD
2. Mark each item as ✓, △, or ✗
3. Calculate scores for each section
4. Address any non-compliant items before final approval
5. Document specific evidence for each rating
6. Obtain stakeholder sign-off when checklist is complete

## Integration with PRD Specifications

This checklist integrates with:
- **Customer-Facing PRD Specification**: `spec.universal-domains.product-and-requirements.prd-documentation-customer-facing`
- **Acceptance Quality Checklist**: `checklist.universal-domains.product-and-requirements.acceptance-quality-checklist`
- **Customer-Facing PRD Template**: `template.universal-domains.product-and-requirements.customer-facing-prd-template`

## Related Documents

- `spec.universal-domains.product-and-requirements.prd-documentation-customer-facing.overview`: Customer-facing PRD overview
- `spec.universal-domains.product-and-requirements.prd-documentation-customer-facing.normative-rules`: Customer-facing PRD rules
- `spec.universal-domains.product-and-requirements.prd-documentation-customer-facing.verification`: Customer-facing PRD verification
- `template.universal-domains.product-and-requirements.customer-facing-prd-template`: Customer-facing PRD template
- `example.universal-domains.product-and-requirements.customer-facing-prd-example`: Customer-facing PRD example