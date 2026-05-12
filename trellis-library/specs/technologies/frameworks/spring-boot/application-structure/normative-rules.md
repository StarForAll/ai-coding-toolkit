# Normative Rules

* Spring Boot application structure should keep domain behavior, framework wiring, and integration boundaries distinguishable.
* Framework entry points such as controllers, configuration, and bootstrapping code must not become dumping grounds for displaced business logic.
* Structural choices should preserve testability and module discoverability rather than optimizing only for framework convenience.
* Cross-layer reach-through should not be normalized just because Spring injection makes access easy.
* Similar application slices should follow consistent structural conventions.
* Spring-managed roles such as controllers, services, repositories, and configuration classes should be named and placed consistently enough that ownership is obvious from the class boundary.
* Dependency injection should prefer explicit constructor-based wiring or equivalently reviewable patterns over hidden field injection that obscures required collaborators.
* Service, repository, and adapter layering should make intermediate coordination responsibilities explicit rather than collapsing all business support code into controllers or persistence classes.
* Intermediate coordination layers such as manager/application-service style modules should exist only where they clarify third-party integration, shared orchestration, or cross-repository composition responsibilities that do not belong in web or persistence edges.
