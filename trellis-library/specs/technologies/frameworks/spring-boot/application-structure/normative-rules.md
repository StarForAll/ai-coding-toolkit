# Normative Rules

* Spring Boot application structure should keep domain behavior, framework wiring, and integration boundaries distinguishable.
* Framework entry points such as controllers, configuration, and bootstrapping code must not become dumping grounds for displaced business logic.
* Structural choices should preserve testability and module discoverability rather than optimizing only for framework convenience.
* Cross-layer reach-through should not be normalized just because Spring injection makes access easy.
* Similar application slices should follow consistent structural conventions.
