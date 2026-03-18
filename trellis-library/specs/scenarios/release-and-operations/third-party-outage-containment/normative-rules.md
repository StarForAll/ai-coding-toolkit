# Normative Rules

* Third-party outage handling must make the affected dependency, exposed user impact, and available fallback paths explicit.
* Containment should focus on reducing user harm and uncontrolled retries before pursuing deep diagnosis of provider internals.
* A provider-side problem must not be used as an excuse to ignore product-side resilience gaps that amplify the outage.
* Degraded modes, throttling, circuit breaking, or temporary disablement should be considered when they materially reduce blast radius.
* When provider status is uncertain, the remaining uncertainty must be communicated rather than replaced with confident guesses.
