# Scope Boundary

This concern covers:

* the source-library registry model built around `manifest.yaml`
* target-project asset state tracking through `.trellis/library-lock.yaml`
* downstream synchronization from source library to target project
* upstream proposal and apply boundaries from target project back to source library
* validation and reporting requirements for sync tooling

This concern does not cover:

* project-specific business rules inside imported assets
* framework-specific or platform-specific implementation details
* direct code generation rules for product repositories
* human approval policy outside the Trellis library workflow
