# Normative Rules

## Language and Expression

* Customer-facing PRDs must use plain language that a non-technical stakeholder can read without needing implementation knowledge.
* Technical jargon, internal system names, and engineering shorthand must be avoided or explained in plain language when they cannot be removed.
* All technical terms must be defined when first introduced, and a glossary should be provided if the document contains multiple specialized terms.

## Document Structure

* A customer-facing PRD must include the following minimum sections or equivalent headings:
  1. Problem or opportunity description
  2. Target users or stakeholders
  3. Business goal and success metrics
  4. Scope definition (core features, enhancements, out-of-scope)
  5. Proposed solution overview
  6. Key user requirements or scenarios
  7. Delivery priorities and phasing
  8. Success criteria and validation methods
  9. Open questions, assumptions, and dependencies

## Content Requirements

* Requirements must be expressed from the customer's point of view, describing the expected experience, workflow, or business outcome rather than internal implementation mechanics.
* Customer-facing PRDs must focus on what will change, why it matters, and what result the customer should expect.
* Scope must distinguish core commitments from later enhancements, and must list out-of-scope items when confusion is likely.

## Success Criteria Examples

* **Quantitative Metrics**: User task completion rate improvement of 20%, customer satisfaction score ≥ 4.5/5, system response time < 2 seconds
* **Qualitative Outcomes**: Improved user experience, reduced training time, increased adoption rate
* **Business Impact**: Revenue increase, cost reduction, market share growth

## Scope Definition Examples

* **Core Features (Phase 1)**: Essential functionality that must be delivered first
* **Enhancements (Phase 2)**: Additional features that improve the core experience
* **Future Considerations**: Features that may be developed in later phases based on feedback and resources
* **Explicitly Out of Scope**: Items that will not be addressed in the current project

## Examples and Validation

* If examples, diagrams, or mockups are used, they must clarify the requirement rather than introduce new hidden scope.
* All assumptions and dependencies must be clearly stated, with impact assessment if they are not met.
* Success criteria must be measurable from the customer's viewpoint, such as observable workflow outcomes, service levels, or adoption expectations.

## Prohibited Content

* Customer-facing PRDs must not define API shapes, database structures, class designs, or deployment details as part of the required format.
* Technical implementation details should only be included if they directly affect customer experience or business outcomes.
* Internal system names and technical architecture references must be translated into business-friendly descriptions.

## Documentation Quality

* Ambiguities, assumptions, dependencies, and pending decisions must be called out explicitly in customer-readable language.
* Each requirement should be testable and verifiable from a customer perspective.
* The document should be reviewed by both technical and non-technical stakeholders to ensure clarity and completeness.
