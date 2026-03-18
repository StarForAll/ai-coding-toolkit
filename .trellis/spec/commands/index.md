# Command Specification Guidelines

> How to create and organize reusable commands/scripts in this project.

---

## Overview

This project stores reusable commands, scripts, and workflows that standardize common operations across AI coding assistants.

---

## Directory Structure

```
commands/
  <platform>/
    <command-id>/
      README.md        # Purpose, usage, examples
      script.sh        # Main script (or .py, .js, etc.)
      config.json      # Configuration (optional)
  codex/              # Codex CLI commands
  claude/             # Claude Code commands
  shell/              # Platform-agnostic shell scripts
```

---

## Naming Conventions

- **Command IDs**: Use kebab-case: `deploy-helper`, `test-runner`
- **Platform prefixes**: `codex/`, `claude/`, `shell/`
- **Script files**: Match command ID: `deploy-helper.sh`

---

## Required Files

### README.md (Required)

Must include:
- **Problem**: What problem this command solves
- **Dependencies**: Required tools, environment
- **Usage**: How to run with common parameters
- **Side Effects**: What files it modifies, git state changes

### Script File (Required)

- Executable (`chmod +x`)
- Shebang line (`#!/bin/bash`, `#!/usr/bin/env python3`)
- Error handling with exit codes
- Usage function for help

---

## Quality Standards

### Must Have

- [ ] README with usage examples
- [ ] Error handling (exit on critical failure)
- [ ] Help output (`--help`, `-h`)
- [ ] Required dependencies documented

### Should Have

- [ ] Config file for customization
- [ ] Dry-run mode (`--dry-run`)
- [ ] Verbose mode (`-v`, `--verbose`)
- [ ] Exit code conventions (0=success, 1=error)

### Anti-Patterns

- **Hardcoded paths**: Use environment variables or config
- **Silent failures**: Always report status
- **No validation**: Check inputs before processing
- **Missing documentation**: Commands without README

---

## Script Template

```bash
#!/usr/bin/env bash
set -euo pipefail

# Configuration
COMMAND_NAME="my-command"
VERSION="1.0.0"

# Usage function
usage() {
    cat << EOF
Usage: $COMMAND_NAME [OPTIONS]

Description of what this command does.

OPTIONS:
    -h, --help      Show this help message
    -v, --verbose   Enable verbose output
    -n, --dry-run   Show what would be done without executing
    --config PATH  Custom config file

EXAMPLES:
    $COMMAND_NAME --dry-run
    $COMMAND_NAME --config /path/to/config.yaml

EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        -v|--verbose) VERBOSE=1 ;;
        -n|--dry-run) DRY_RUN=1 ;;
        --config) CONFIG="$2"; shift ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
    shift
done

# Main logic
main() {
    # Validate dependencies
    command -v required-tool >/dev/null 2>&1 || { echo "Error: required-tool not found"; exit 1; }

    # Implementation
    echo "Command executed"
}

main "$@"
```

---

## Platform-Specific Guidelines

### Shell Scripts (`shell/`)

- Use bash with `set -euo pipefail`
- Prefer POSIX-compliant commands
- Document required utilities

### Claude Code (`claude/`)

- Create MCP tools or slash commands
- Follow Claude Code's tool conventions
- Document in `.claude/commands/`

### Codex (`codex/`)

- Create custom commands for Codex CLI
- Follow Codex command format
- Document in `.codex/`

---

## Configuration Files

When commands need configuration:

```yaml
# config.yaml example
defaults:
  output_dir: ./output
  verbose: false

commands:
  deploy:
    timeout: 300
    retry: 3
```

---

## Versioning

- Add version constant at top of scripts
- Document changes in README
- Use semantic versioning

---

**Language**: English
