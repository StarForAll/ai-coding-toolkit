# Normative Rules

## Business Intent Preservation

* Developer-facing PRDs must preserve the approved business intent while translating it into implementation-ready functional and non-functional requirements.
* Every technical requirement must be traceable to a business requirement or customer need.
* Business goals and success criteria must be translated into measurable technical metrics.

## Document Structure

A developer-facing PRD must include the following minimum sections or equivalent headings:

### Core Sections
1. **Problem Context**: Technical context and background, including existing system analysis
2. **Goals and Non-Goals**: Clear statement of what will and will not be achieved
3. **Scope Definition**: Detailed technical scope with boundaries and constraints
4. **Functional Requirements**: Detailed system behavior specifications
5. **Non-Functional Requirements**: Performance, security, reliability, and other quality attributes
6. **Data or State Model**: Data structures, schemas, and state transitions
7. **Interfaces and Integrations**: API contracts, external service integrations
8. **Error Handling and Edge Cases**: Failure modes, exception scenarios, and recovery procedures
9. **Dependencies and Constraints**: Technical dependencies, third-party services, and system constraints
10. **Acceptance Criteria**: Verifiable criteria for successful implementation
11. **Testing Expectations**: Test strategy, coverage requirements, and validation approach
12. **Risks and Mitigations**: Technical risks and planned mitigation strategies
13. **Open Questions**: Unresolved technical decisions and trade-offs

## Functional Requirements Specification

* Functional requirements must describe required system behavior clearly enough to support implementation and verification.
* Each functional requirement must include:
  - **Description**: Clear description of the required behavior
  - **Input/Output**: Expected inputs and outputs with formats
  - **Processing Logic**: Steps, algorithms, or business rules
  - **Error Conditions**: How errors and edge cases should be handled
  - **Acceptance Criteria**: How to verify the requirement is met

## Non-Functional Requirements Specification

Non-functional requirements must state concrete expectations for:

### Performance Requirements
- **Response Time**: Maximum acceptable latency (e.g., API response < 100ms)
- **Throughput**: Requests per second capacity (e.g., > 1000 TPS)
- **Concurrency**: Number of simultaneous users/connections supported (e.g., > 500 concurrent users)

### Security Requirements
- **Authentication**: Required authentication methods and protocols
- **Authorization**: Access control mechanisms and permissions
- **Data Protection**: Encryption requirements for data at rest and in transit
- **Compliance**: Security standards and regulations to follow

### Reliability Requirements
- **Availability**: System uptime requirements (e.g., > 99.9%)
- **Recovery Time**: Maximum time to recover from failures (e.g., < 5 minutes)
- **Data Integrity**: Data consistency and accuracy requirements

### Scalability Requirements
- **Horizontal Scaling**: Ability to scale out with increased load
- **Vertical Scaling**: Ability to scale up with increased resources
- **Load Handling**: Maximum load the system must handle

## Technical Specification Requirements

* Developer-facing PRDs must define data structures, state transitions, API or interface contracts, and integration points when those details affect implementation behavior.
* Required behavior must be separated from optional implementation suggestions so teams can distinguish contract from design preference.

### Data Model Specification
- **Entity Definitions**: Data entities with attributes, types, and constraints
- **Relationships**: Entity relationships and cardinality
- **State Transitions**: Valid state changes and transition rules
- **Validation Rules**: Data validation and business rules

### Interface Specification
- **API Contracts**: Endpoint definitions with request/response formats
- **Integration Points**: External service integrations and protocols
- **Event Definitions**: Event types, payloads, and routing rules
- **Error Contracts**: Error codes, messages, and handling procedures

## Error Handling and Edge Cases

* Error handling, failure modes, edge cases, and exception scenarios must be documented for critical flows.
* For each error scenario, document:
  - **Error Code**: Unique identifier for the error
  - **Error Description**: Clear description of what went wrong
  - **Trigger Condition**: What causes this error
  - **Recovery Action**: How the system should respond or recover
  - **User Message**: What the user should see or be notified about

## Dependencies and Constraints

* Dependencies, assumptions, third-party services, and system constraints must be identified explicitly.
* For each dependency, document:
  - **Dependency Type**: Internal/external, software/hardware
  - **Version Requirements**: Specific version requirements or compatibility ranges
  - **Fallback Options**: Alternative approaches if dependency is unavailable
  - **Impact Assessment**: What happens if dependency is not met

## Verification and Testing

* Acceptance criteria and testing expectations must be specific enough to support unit, integration, and end-to-end verification where relevant.
* Testing requirements must include:
  - **Unit Test Coverage**: Minimum coverage percentage (e.g., > 90%)
  - **Integration Test Scenarios**: Key integration points to test
  - **End-to-End Test Cases**: Critical user flows to validate
  - **Performance Test Criteria**: Load and stress test requirements

## Versioning and Compatibility

* Versioning, backward compatibility, rollout constraints, and migration requirements must be stated when the change affects persisted data or external contracts.
* Versioning requirements must include:
  - **API Versioning**: Versioning scheme and deprecation policy
  - **Data Migration**: Migration scripts and rollback procedures
  - **Backward Compatibility**: Compatibility requirements with existing systems
  - **Rollout Strategy**: Phased rollout or feature flag requirements

## Risk Management

* Technical risks, unresolved questions, and decision trade-offs must be visible so implementation planning can account for them.
* Risk documentation must include:
  - **Risk Description**: Clear description of the technical risk
  - **Impact Assessment**: Potential impact on implementation or operation
  - **Probability**: Likelihood of occurrence (High/Medium/Low)
  - **Mitigation Strategy**: Planned approach to mitigate the risk
  - **Contingency Plan**: Backup plan if risk materializes

## Prohibited Content

* Developer-facing PRDs must not substitute sales narrative, customer-friendly marketing copy, or vague feature intent for executable technical requirements.
* All requirements must be specific, measurable, and testable.
* Marketing language and customer-facing descriptions must be translated into precise technical specifications.
