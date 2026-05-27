# Developer-Facing PRD Checklist

* Business intent preservation: each technical requirement traces back to a business requirement or customer need.
* Business intent preservation: technical goals align with business objectives.
* Business intent preservation: technical metrics support business success criteria.
* Business intent preservation: the specified implementation behavior delivers the intended business value.
* Document structure: technical context and background are documented.
* Document structure: technical objectives and exclusions are stated clearly.
* Document structure: detailed technical scope and boundaries are defined.
* Document structure: complete functional specifications are present.
* Document structure: performance, security, and reliability requirements are documented.
* Document structure: data structures and state transitions are defined where relevant.
* Document structure: API contracts and integration points are documented.
* Document structure: error scenarios and handling procedures are described.
* Document structure: technical dependencies are documented.
* Document structure: verifiable completion criteria are defined.
* Document structure: test strategy and validation requirements are documented.
* Document structure: technical risks and mitigation strategies are documented.
* Document structure: unresolved technical decisions are listed.
* Functional requirements: each functional requirement is specific enough to implement.
* Functional requirements: inputs and outputs are clearly defined with formats.
* Functional requirements: business logic and processing rules are specified.
* Functional requirements: edge cases and boundary conditions are identified.
* Functional requirements: error conditions and recovery procedures are defined.
* Functional requirements: each requirement has clear, verifiable acceptance criteria.
* Non-functional requirements: maximum latency is specified where performance matters.
* Non-functional requirements: capacity requirements are defined.
* Non-functional requirements: concurrent user or connection limits are specified where applicable.
* Non-functional requirements: memory, CPU, and storage requirements are documented where relevant.
* Non-functional requirements: authentication requirements are defined.
* Non-functional requirements: access-control requirements are specified.
* Non-functional requirements: encryption requirements are documented where relevant.
* Non-functional requirements: applicable security standards or regulations are identified.
* Non-functional requirements: uptime requirements are specified where applicable.
* Non-functional requirements: recovery-time objectives are defined where applicable.
* Non-functional requirements: data-consistency requirements are documented.
* Non-functional requirements: backup and recovery procedures or expectations are defined where applicable.
* Technical specification: data entities and relationships are defined where they affect implementation behavior.
* Technical specification: valid state changes and transition rules are documented.
* Technical specification: endpoint specifications with request and response formats are complete.
* Technical specification: external service integrations are specified.
* Technical specification: event types and payloads are documented where relevant.
* Technical specification: error codes and handling procedures are defined where relevant.
* Implementation clarity: required behavior is clearly separated from optional implementation suggestions.
* Implementation clarity: requirements stay technology-agnostic where possible.
* Implementation clarity: different implementation approaches remain possible as long as the required behavior is met.
* Implementation clarity: unnecessary implementation details that constrain design are avoided.
* Error handling: critical error scenarios have defined error codes or error categories where relevant.
* Error handling: each error meaning is described clearly.
* Error handling: trigger conditions for each important error case are documented.
* Error handling: expected system responses to each important error case are defined.
* Error handling: user-visible behavior for each important error case is specified where applicable.
* Error handling: unusual scenarios and boundary conditions are addressed.
* Dependencies and constraints: technical dependencies are identified.
* Dependencies and constraints: specific version requirements are documented where relevant.
* Dependencies and constraints: external service dependencies are specified.
* Dependencies and constraints: hardware, software, and environmental constraints are listed.
* Dependencies and constraints: fallback or alternative approaches for critical dependencies are documented where needed.
* Dependencies and constraints: consequences of dependency failures are documented.
* Verification and testing: requirements can be verified through testing or equivalent validation.
* Verification and testing: coverage expectations are specified where relevant.
* Verification and testing: key integration points for testing are identified.
* Verification and testing: critical user flows or system flows for validation are documented.
* Verification and testing: load or stress-test requirements are defined where relevant.
* Verification and testing: acceptance-testing procedures are described clearly.
* Versioning and compatibility: the versioning scheme and deprecation policy are documented where relevant.
* Versioning and compatibility: migration requirements and procedures are specified when data or contracts change.
* Versioning and compatibility: compatibility requirements are defined.
* Versioning and compatibility: deployment and rollout requirements are documented where relevant.
* Versioning and compatibility: rollback requirements and procedures are specified where relevant.
* Risk management: technical risks are identified and documented.
* Risk management: the potential impact of each important risk is assessed.
* Risk management: the likelihood of each important risk is estimated where useful.
* Risk management: mitigation approaches are documented.
* Risk management: contingency plans for critical risks are defined where needed.
* Risk management: risk-monitoring expectations during implementation are described where relevant.
* Prohibited content: the document does not contain sales narrative or customer-facing marketing copy in place of technical requirements.
* Prohibited content: requirements are specific and measurable.
* Prohibited content: business justification remains in the customer-facing PRD rather than replacing technical requirements here.
* Prohibited content: content stays appropriate for technical implementation and verification.
