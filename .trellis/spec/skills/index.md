# Skill Specification Guidelines

> How to create and organize reusable AI skills (powered by Skills CLI).

---

## Overview

Skills are self-contained AI capabilities that can be discovered and installed via Skills CLI (`npx skills`). This project uses skills to encapsulate domain-specific expertise and workflows.

---

## Directory Structure

```
skills/
  <skill-id>/
    SKILL.md           # Required: Skill definition
    README.md          # Optional: Additional documentation
    scripts/           # Optional: Helper scripts
    references/        # Optional: Reference materials
    tests/             # Optional: Validation tests
```

---

## Coupled Skill Contracts (CRITICAL)

Some skills in this repository form a **single protocol surface** even though
they live in separate directories.

Current mandatory coupled pair:

- `skills/multi-cli-review/SKILL.md`
- `skills/multi-cli-review-action/SKILL.md`

These two files must be treated as **one shared contract**:

- reviewer-side report emission contract
- aggregator-side report intake contract
- shared path layout under `tmp/multi-cli-review/`
- shared metadata fields such as `task-id`, `round`, `reviewer-id`, and `protocol`
- shared role boundaries between reviewer and fixer
- shared legacy compatibility expectations

### Required Rule

If a change modifies **either** of these files in a way that can affect the
shared protocol or role boundary, the other file must be reviewed and updated
in the **same change**.

Do not treat them as independently maintainable when changing:

- path shapes or filenames
- frontmatter / metadata fields
- protocol names or protocol selection rules
- reviewer-id or round handling
- role boundaries such as "reviewer only" vs "current CLI only"
- legacy compatibility parameters
- output artifacts consumed by the paired skill

### Minimum Verification For This Pair

After editing either file:

- confirm whether the paired skill also needs a matching change
- read both diffs together before finishing
- verify there is no protocol drift between reviewer output and action-side intake

---

## Naming Conventions

- **Skill IDs**: Use kebab-case: `demand-risk-assessment`, `code-review-helper`
- **Directory name**: Matches skill ID exactly
- **Case sensitive**: `Demand-Risk-Assessment` ≠ `demand-risk-assessment`

---

## Required Files

### SKILL.md (Required)

Must include YAML frontmatter with:
```yaml
---
name: <skill-id>
description: <one-line description of when to use this skill>
---
```

Followed by detailed skill content:
- **Purpose**: What problem this skill solves
- **Trigger conditions**: When to invoke
- **Input/Output**: Expected format
- **Detailed instructions**: Step-by-step guidance
- **Examples**: Sample inputs and outputs

---

## SKILL.md Template

```yaml
---
name: my-skill
description: Use when <scenario description>
---

# My Skill (v1.0)

## Version History
- **v1.0**: Initial release

## Purpose
Describe what this skill does and when to use it.

## Trigger Conditions
When user asks/says <specific triggers>:
- "Do X"
- "Help with Y"
- "Use skill: my-skill"

## Input
Expected user input format:
- Type A: <description>
- Type B: <description>

## Output
Skill produces:
- <output format>
- <examples>

## Workflow

### Step 1: <Name>
<description>

### Step 2: <Name>
<description>

## Output Format
```markdown
## Result
...
```

## Examples

### Example 1: <Description>
Input:
<user input>

Output:
<skill output>
```

---

## Quality Standards

### Must Have

- [ ] Valid YAML frontmatter with `name` and `description`
- [ ] Clear trigger conditions
- [ ] Step-by-step workflow
- [ ] Output format specification
- [ ] At least one example

### Should Have

- [ ] Version history in header
- [ ] Version notes section
- [ ] Error handling guidance
- [ ] Edge cases documented

### Anti-Patterns

- **Missing frontmatter**: SKILL.md must start with `---`
- **Generic descriptions**: "Helps with coding" ← Too vague
- **No examples**: Users need to see expected input/output
- **Overly complex**: Skills should be focused, not catch-all
- **Tool-specific assumptions**: Don't assume specific AI tool unless required

---

## References Directory

For skills that need external references:

```
skills/
  <skill-id>/
    SKILL.md
    references/
      guide-1.md      # Supporting documentation
      template.md     # Templates
      examples/        # Additional examples
```

Reference paths in SKILL.md:
```markdown
See `references/guide-1.md` for details.
```

---

## Scripts Directory

For skills that execute code:

```
skills/
  <skill-id>/
    SKILL.md
    scripts/
      validate.sh      # Validation script
      setup.sh         # Environment setup
```

Make scripts executable and document in SKILL.md.

---

## Validation

Run project validation:
```bash
./scripts/validate-skills.sh
```

Or list skills without installing:
```bash
npx skills add . --list
```

---

## Installation

After pushing to GitHub:
```bash
# Install from GitHub
npx skills add <owner>/<repo>

# Or use full URL
npx skills add https://github.com/<owner>/<repo>
```

---

## Best Practices

1. **Focused scope**: One skill = one capability
2. **Clear triggers**: Explicit about when to use
3. **Consistent format**: Follow template structure
4. **Version tracking**: Document changes
5. **Tested**: Validate skill works as expected
6. **Discoverable**: Description should be searchable

---

## Common Mistakes

- Putting multiple unrelated capabilities in one skill
- Using the skill ID in the description (redundant)
- Forgetting to update version when making changes
- Not specifying input format → users don't know what to provide
- Making it tool-specific when it could be generic
- Updating `multi-cli-review` or `multi-cli-review-action` alone when the shared protocol changed

---

## Examples

### Good Skill Structure

```
skills/
  demand-risk-assessment/
    SKILL.md              # Full skill definition
    README.md              # Additional context
    references/
      评估标准.md          # Evaluation criteria
```

### Minimum Viable Skill

```
skills/
  my-helper/
    SKILL.md              # Just the required file
```

---

**Language**: English (or match project's primary language)

**Note**: SKILL.md content can be in any language, but frontmatter and structure should be consistent.
