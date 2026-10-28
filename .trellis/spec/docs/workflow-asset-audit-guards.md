# Workflow Asset Audit Guards

> False-positive guards distilled from the retired `workflow-scan` / `workflow-repair` pair
> before its deletion (2026-10-28). They are **path-independent**: apply them when auditing any
> authored workflow asset set, including the future `wf` module.
> Why keep them: the pair accumulated these through many rounds of mis-reported defects; the
> rules survive their tooling.

---

## Guards

1. **Installed template vs task-local generated file.** A template that ships with the asset set
   and a file generated per task may share a filename (for example a `*-template.md` and the
   `*.md` produced from it). The generated file's absence is not a defect, and its content is not
   the template's content. Compare against the template, never against a generated sibling.

2. **Same-name skill in more than one root.** A shared skill root and a platform-specific root may
   legitimately carry the same skill. Presence in both is not duplication; drift exists only when
   the contents differ *and* the renderer contract says they must be identical.

3. **Uppercase `SKILL.md` is the convention**, not a naming defect. Only a skill with no
   `SKILL.md` at all (or one whose frontmatter is unreadable) is actionable.

4. **A retired or disabled command's absence from the active surface is expected.** Missing
   entrypoints for commands that were intentionally removed are state, not defects.

5. **Filename- or path-shape-only findings need content-level verification** before adoption.
   A reference that "looks broken" may point at a renamed-but-equivalent target; check the target
   before filing it.

---

## Scope note

These guards belong to *authoring-side* auditing. They do not replace runtime probes: mechanism
correctness is asserted by the plan's W-series probes and `wf doctor`, not by document review.
