# Verification

Check the following:

* each required gate is named explicitly
* each gate has an observable outcome
* failures block closure unless policy states otherwise
* missing automation is recorded as a gap
* manual review gates are documented where needed
* mandatory quality-platform project ids are present and valid before stage entry or state changes
* `sonar verify -p <project-id>` results are recorded when that gate is declared
* failed quality-platform findings show a fix, similar-issue review, and rerun evidence before closure
