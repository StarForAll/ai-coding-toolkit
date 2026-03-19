# Normative Rules

* Developer-facing PRDs must preserve the approved business intent while translating it into implementation-ready functional and non-functional requirements.
* A developer-facing PRD must include the following minimum sections or equivalent headings: problem context, goals and non-goals, scope, functional requirements, non-functional requirements, data or state model, interfaces and integrations, error handling and edge cases, dependencies and constraints, acceptance criteria, testing expectations, risks, and open questions.
* Functional requirements must describe required system behavior clearly enough to support implementation and verification.
* Non-functional requirements must state concrete expectations for performance, security, reliability, scalability, maintainability, or observability when those qualities matter.
* Developer-facing PRDs must define data structures, state transitions, API or interface contracts, and integration points when those details affect implementation behavior.
* Required behavior must be separated from optional implementation suggestions so teams can distinguish contract from design preference.
* Error handling, failure modes, edge cases, and exception scenarios must be documented for critical flows.
* Dependencies, assumptions, third-party services, and system constraints must be identified explicitly.
* Acceptance criteria and testing expectations must be specific enough to support unit, integration, and end-to-end verification where relevant.
* Versioning, backward compatibility, rollout constraints, and migration requirements must be stated when the change affects persisted data or external contracts.
* Technical risks, unresolved questions, and decision trade-offs must be visible so implementation planning can account for them.
* Developer-facing PRDs must not substitute sales narrative, customer-friendly marketing copy, or vague feature intent for executable technical requirements.
