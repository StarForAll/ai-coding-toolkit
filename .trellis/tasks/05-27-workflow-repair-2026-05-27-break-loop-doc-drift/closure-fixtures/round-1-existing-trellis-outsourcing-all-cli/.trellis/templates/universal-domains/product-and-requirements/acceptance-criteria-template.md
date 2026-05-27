# Acceptance Criteria Template

## Purpose

Use this template to turn a requirement into explicit, observable, and verifiable acceptance criteria. This template ensures that all necessary elements are considered and documented.

## Instructions

1. **Fill in all sections**: Complete each section with specific information
2. **Be specific**: Use measurable terms and clear language
3. **Test each criterion**: Ensure each criterion can be verified through testing or observation
4. **Review with stakeholders**: Have both technical and business stakeholders review the criteria
5. **Update as needed**: Revise criteria as requirements evolve

## Acceptance Criteria Template

### 1. Scope Covered
*What is included in this acceptance criteria?*

**In Scope:**
- [Feature/Function 1]: [Brief description]
- [Feature/Function 2]: [Brief description]
- [Additional items as needed]

**Out of Scope:**
- [Item 1]: [Reason for exclusion]
- [Item 2]: [Reason for exclusion]
- [Additional items as needed]

### 2. Required Outcomes
*What must be achieved for this to be considered successful?*

**Primary Outcomes:**
- [ ] **Outcome 1**: [Specific, measurable outcome with success metric]
  - *Success Metric*: [How to measure this outcome]
  - *Target Value*: [Target number, percentage, or condition]
  - *Measurement Method*: [How to collect this data]

- [ ] **Outcome 2**: [Specific, measurable outcome with success metric]
  - *Success Metric*: [How to measure this outcome]
  - *Target Value*: [Target number, percentage, or condition]
  - *Measurement Method*: [How to collect this data]

**Secondary Outcomes:**
- [ ] **Outcome 3**: [Specific outcome with measurement approach]
- [ ] **Outcome 4**: [Specific outcome with measurement approach]

### 3. Failure or Rejection Conditions
*What conditions would cause this to be considered failed or rejected?*

**Hard Failure Conditions (Must Not Occur):**
- [ ] **Condition 1**: [Specific condition that would cause failure]
  - *Detection Method*: [How to detect this condition]
  - *Impact*: [What happens if this occurs]
  - *Mitigation*: [How to prevent or handle this]

- [ ] **Condition 2**: [Specific condition that would cause failure]
  - *Detection Method*: [How to detect this condition]
  - *Impact*: [What happens if this occurs]
  - *Mitigation*: [How to prevent or handle this]

**Soft Failure Conditions (Should Be Avoided):**
- [ ] **Condition 3**: [Condition that should be avoided but may be acceptable in some cases]
- [ ] **Condition 4**: [Condition that should be avoided but may be acceptable in some cases]

### 4. Evidence Expected
*What evidence will demonstrate that the criteria have been met?*

**Testing Evidence:**
- [ ] **Unit Test Results**: [Expected test coverage and results]
- [ ] **Integration Test Results**: [Expected integration test outcomes]
- [ ] **End-to-End Test Results**: [Expected user flow validation results]

**Performance Evidence:**
- [ ] **Performance Metrics**: [Specific metrics to collect]
  - *Target*: [Target values for each metric]
  - *Measurement Tool*: [Tool or method for measurement]
  - *Acceptance Threshold*: [Minimum acceptable values]

**User Experience Evidence:**
- [ ] **User Testing Results**: [Expected user testing outcomes]
- [ ] **Usability Metrics**: [Specific usability measures]
- [ ] **Accessibility Compliance**: [Expected accessibility standards]

**Business Evidence:**
- [ ] **Business Metrics**: [Specific business metrics to track]
- [ ] **Stakeholder Sign-off**: [Required approvals and sign-offs]

### 5. Open Assumptions
*What assumptions are being made, and what happens if they are incorrect?*

**Critical Assumptions:**
- [ ] **Assumption 1**: [Description of critical assumption]
  - *Impact if False*: [What happens if this assumption is wrong]
  - *Validation Method*: [How to verify this assumption]
  - *Contingency Plan*: [What to do if assumption is false]

- [ ] **Assumption 2**: [Description of critical assumption]
  - *Impact if False*: [What happens if this assumption is wrong]
  - *Validation Method*: [How to verify this assumption]
  - *Contingency Plan*: [What to do if assumption is false]

**Dependencies:**
- [ ] **Dependency 1**: [Description of dependency]
  - *Provider*: [Who or what provides this dependency]
  - *Timeline*: [When this dependency is needed]
  - *Fallback Option*: [Alternative if dependency is unavailable]

- [ ] **Dependency 2**: [Description of dependency]
  - *Provider*: [Who or what provides this dependency]
  - *Timeline*: [When this dependency is needed]
  - *Fallback Option*: [Alternative if dependency is unavailable]

**Open Questions:**
- [ ] **Question 1**: [Unresolved question that needs clarification]
  - *Decision Needed By*: [Date or milestone when decision is needed]
  - *Decision Maker*: [Who needs to make this decision]

- [ ] **Question 2**: [Unresolved question that needs clarification]
  - *Decision Needed By*: [Date or milestone when decision is needed]
  - *Decision Maker*: [Who needs to make this decision]

## Quality Checklist

Before finalizing acceptance criteria, verify:
- [ ] **Measurability**: Each criterion can be measured objectively
- [ ] **Testability**: Each criterion can be verified through testing or observation
- [ ] **Clarity**: Each criterion is unambiguous and clearly understood
- [ ] **Completeness**: All important aspects are covered
- [ ] **Feasibility**: Criteria are realistic and achievable
- [ ] **Traceability**: Criteria can be traced back to requirements

## Integration with PRD Specifications

This template is designed to work with:
- **Customer-Facing PRD**: Use customer-focused language and business metrics
- **Developer-Facing PRD**: Include technical implementation details and test requirements
- **Acceptance Quality Checklist**: Use to validate the completeness of your criteria

## Related Documents

- `spec.universal-domains.product-and-requirements.acceptance-criteria`: Detailed specification for acceptance criteria
- `checklist.universal-domains.product-and-requirements.acceptance-quality-checklist`: Checklist for validating acceptance criteria
- `spec.universal-domains.product-and-requirements.prd-documentation-customer-facing`: Customer-facing PRD specification
- `spec.universal-domains.product-and-requirements.prd-documentation-developer-facing`: Developer-facing PRD specification
