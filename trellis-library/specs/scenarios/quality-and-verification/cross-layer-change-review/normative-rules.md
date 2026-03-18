# Normative Rules

* Cross-layer changes must be reviewed against the end-to-end behavior they intend to preserve or alter.
* A local pass in one layer must not be treated as sufficient evidence when neighboring layers also changed or depend on the same assumptions.
* Contract, data, configuration, and verification assumptions must remain aligned across the affected layers.
* Shared assumptions that bridge layers should be explicit enough to review rather than inferred from partial code context.
* If evidence covers only one slice of a cross-layer change, the remaining system risk must stay visible.
