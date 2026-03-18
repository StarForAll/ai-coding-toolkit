# Normative Rules

* Events must communicate stable business meaning rather than merely mirroring internal implementation transitions.
* Event payloads should preserve enough context for consumers to act without hidden synchronous backchannels.
* Event versioning and evolution must account for asynchronous consumers that may lag behind producers.
* Similar event categories should follow consistent envelope and failure semantics where consumers rely on them.
* When ordering, duplication, or eventual-delivery limits affect interpretation, those limits must remain explicit.
