# Normative Rules

* A system definition must identify its external dependencies and major boundary crossings explicitly.
* Ownership should be assigned at the boundary where responsibility changes, not only inside modules.
* External systems must not be treated as implicitly reliable or controllable by default.
* Architectural decisions should preserve clarity about what is inside the system and what is integrated from outside.
* Boundary ambiguity must be resolved before implementation is treated as stable.
