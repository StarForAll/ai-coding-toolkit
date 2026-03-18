# Normative Rules

* A workflow must treat repeated contradiction, stale assumptions, or direction drift as contamination signals.
* When contamination is detected, the workflow should prefer a reset with stable summaries over continuing to append noisy context.
* Hallucinated or disproven claims must not remain active in working context without correction.
* Context resets must preserve validated decisions and discard untrusted residue.
* A contaminated session must not be presented as reliable simply because it is long-running.
