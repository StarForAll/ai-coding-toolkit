# CLI Command Interface Readiness Checklist

* Each command has a single clear responsibility and stable invocation shape.
* Required flags, optional flags, and defaults are explicit in help output.
* Success output, error output, and exit codes are predictable for scripts.
* Invalid usage fails with guidance instead of silent fallback behavior.
* Usage examples match the real command contract and supported modes.
