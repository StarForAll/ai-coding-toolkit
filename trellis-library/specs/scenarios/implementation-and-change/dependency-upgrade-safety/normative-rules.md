# Normative Rules

* Dependency upgrades must be classified by semantic risk, not treated as uniform routine maintenance.
* Upgrades should be reviewed for compatibility, security, deprecation, operational, and build-time impact where relevant.
* Transitive behavior changes, default changes, and removed capabilities must be considered alongside version numbers.
* Verification depth should scale with the affected surface area and the maturity of the dependency evidence.
* When upgrade impact cannot be characterized confidently, the change must be treated as carrying elevated integration risk.
