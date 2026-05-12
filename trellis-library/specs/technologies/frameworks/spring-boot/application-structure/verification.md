# Verification

Check the following:

* domain behavior, framework wiring, and integrations are distinguishable
* framework entry points are not carrying displaced business logic
* structure preserves testability and discoverability
* injection convenience is not hiding cross-layer reach-through
* similar slices follow consistent structure
* Spring-managed roles are named and placed consistently across modules
* dependency injection style leaves required collaborators explicit and reviewable
* intermediate coordination responsibilities are intentionally placed rather than collapsed into web or persistence layers
* manager/application-service style layers exist only where they clarify shared coordination responsibilities
