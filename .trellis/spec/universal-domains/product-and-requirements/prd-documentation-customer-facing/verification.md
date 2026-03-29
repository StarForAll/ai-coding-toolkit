# Verification

## Verification Process

Follow this verification process for customer-facing PRDs:

1. **Initial Review**: Check document structure and completeness
2. **Content Review**: Validate language, content, and business focus
3. **Stakeholder Review**: Have non-technical stakeholders review for clarity
4. **Final Validation**: Ensure all verification criteria are met

## Language and Expression Verification

- [ ] **Plain Language Check**: The document uses simple, non-technical language that a business stakeholder can understand without specialized knowledge
- [ ] **Term Definition Check**: All technical terms, acronyms, and specialized vocabulary are defined when first introduced
- [ ] **Jargon Elimination Check**: Internal system names, technical shorthand, and engineering terminology are avoided or translated into business language
- [ ] **Customer Perspective Check**: Requirements are written from the customer's point of view, describing experiences and outcomes, not implementation mechanics

## Document Structure Verification

- [ ] **Problem/Opportunity Section**: Document clearly describes the problem being solved or opportunity being addressed
- [ ] **Target Users Section**: Identifies and describes the primary and secondary users/stakeholders
- [ ] **Business Goals Section**: States measurable business objectives and expected outcomes
- [ ] **Scope Definition Section**: Clearly separates core features, enhancements, and out-of-scope items
- [ ] **Solution Overview Section**: Provides a high-level description of the proposed solution without technical details
- [ ] **User Requirements Section**: Describes key user scenarios and requirements in customer terms
- [ ] **Delivery Priorities Section**: Outlines the phasing and prioritization of features
- [ ] **Success Criteria Section**: Defines measurable success metrics from the customer's perspective
- [ ] **Open Questions Section**: Documents assumptions, dependencies, and pending decisions

## Content Quality Verification

- [ ] **Value Proposition Check**: Each requirement clearly explains why it matters to the customer or business
- [ ] **Outcome Focus Check**: Requirements focus on business outcomes and customer experiences, not implementation processes
- [ ] **Testability Check**: All success criteria can be objectively measured and verified through customer-visible outcomes
- [ ] **Completeness Check**: No critical requirements or assumptions are missing from the document

## Scope Boundary Verification

- [ ] **Core Features Definition**: Core commitments for the current phase are clearly defined and documented
- [ ] **Enhancement Planning**: Future enhancements are identified and separated from core deliverables
- [ ] **Out-of-Scope Clarity**: Items explicitly not included are listed with rationale
- [ ] **Scope Change Process**: Process for handling scope changes is documented

## Validation Methods Verification

- [ ] **Measurable Criteria**: Success criteria use quantifiable metrics where possible (e.g., "increase by 20%", "reduce to < 3 minutes")
- [ ] **Observable Outcomes**: Success can be observed through customer behavior, system performance, or business metrics
- [ ] **Validation Approach**: Methods for validating success criteria are described (e.g., user testing, analytics, surveys)
- [ ] **Acceptance Thresholds**: Clear thresholds for what constitutes success are defined

## Examples and Documentation Quality

- [ ] **Example Clarity**: Any examples, diagrams, or mockups clearly illustrate the requirement without introducing new functionality
- [ ] **No Hidden Scope**: Examples do not imply additional features or commitments beyond what is explicitly stated
- [ ] **Consistency Check**: All sections of the document use consistent terminology and definitions
- [ ] **Review Evidence**: Document shows evidence of stakeholder review and feedback incorporation

## Prohibited Content Verification

- [ ] **No Technical Implementation Details**: Document does not contain API specifications, database schemas, class designs, or deployment details
- [ ] **No Internal System References**: Internal system names, technical architecture, and implementation specifics are avoided
- [ ] **Business Language Only**: All technical concepts are translated into business-friendly descriptions

## Scoring and Validation

### Scoring System
- **Fully Compliant (✓)**: Criterion is fully met (3 points)
- **Partially Compliant (△)**: Criterion is partially met (1 point)
- **Non-Compliant (✗)**: Criterion is not met (0 points)

### Minimum Requirements
- **Total Score**: Must achieve at least 21 out of 27 points (75% compliance)
- **Critical Items**: All "Must Have" criteria (marked with *) must be fully compliant
- **No Blockers**: No "Non-Compliant" ratings on scope boundary or success criteria sections

### Validation Evidence
- [ ] **Stakeholder Sign-off**: Document has been reviewed and approved by target audience representatives
- [ ] **Test Readiness**: Success criteria are specific enough to support user acceptance testing
- [ ] **Communication Ready**: Document can be used for stakeholder communication and alignment
