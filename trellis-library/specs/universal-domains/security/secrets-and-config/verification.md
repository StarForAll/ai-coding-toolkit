# Verification

Check the following:

* secrets and non-secret config are clearly separated
* sensitive values do not appear in reusable assets
* required secret absence fails safely
* environment overrides are explicit
* debug convenience settings do not silently weaken secure behavior
* logs and diagnostic outputs do not expose sensitive configuration values
