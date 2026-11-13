# Repository Analysis

The goal is to discover the project's real architecture before writing rules. Do not start from generic spec templates and fill blanks. Start from the code, then let the spec structure follow.

## Analysis Order

1. Read the existing `.trellis/spec/` tree and note which files are templates, outdated, or already project-specific.
2. Inspect package manifests, build scripts, workspace config, and top-level documentation to identify packages and runtime layers.
3. Follow the host's retrieval policy to locate entry points, module boundaries, dependency hubs, and impact-sensitive areas.
4. Use available language-native tooling and source inspection for exact signatures, types, class boundaries, and implementation examples.
5. Read representative source and test files directly before turning any finding into a spec rule.

## What To Capture

| Area | Questions |
|------|-----------|
| Package boundaries | What does each package own? What imports cross boundaries? |
| Runtime layers | Which code is CLI, backend, frontend, worker, shared library, test-only, or tooling? |
| Core abstractions | Which types, services, stores, commands, routes, or adapters define the system shape? |
| Data flow | Where does user input enter, how is it validated, and where does state persist? |
| Error handling | How are failures represented, logged, surfaced, and tested? |
| Configuration | Where do defaults, environment config, generated files, and templates live? |
| Tests | Which test styles are trusted examples for new work? |

## Trace Flows From Source

Start from entry points named by package manifests, command registration, routes, or tests. Once a symbol or file is located, use exact searches and direct reads to follow imports, calls, validation, and state changes across files. Route unlocated code questions through the host's retrieval policy.

Record the files and symbols supporting each relationship, then check representative tests before making it a spec rule. Textual tracing does not prove exhaustive callers or runtime impact: note unresolved dynamic dispatch, dependency injection, or generated wiring when it matters.

## Inspect Exact Code Shapes

Use an already available compiler, language server, or static analyzer when exact signatures, types, class boundaries, or static references need confirmation. Verify its findings against the relevant source and tests.

If language tooling is unavailable, continue with direct source inspection and state the precision limit. Do not claim AST or graph guarantees from text matches, or require a new service or index before writing source-backed specs.

## Analysis Notes

Keep short notes while analyzing. The notes should include:

- Package or layer name.
- Files that define the local pattern.
- Rules the spec should teach.
- Anti-patterns found in old code, comments, tests, or migration paths.
- Spec files that should be created, deleted, renamed, or merged.
