# brainstorm: trellis-library术语格式一致性评估

## Goal

评估当前 `git status` 中 `trellis-library/` 下的改动，是否已经使 `trellis-library` 全库在术语和文档格式上达到完全一致，并明确当前证据边界、剩余差距与后续收敛方案。

## What I already know

* 当前 `trellis-library/` 有 63 个未提交改动文件。
* 改动集中在三类资产：`checklists/`、`templates/`、`specs/`，并包含 `manifest.yaml`。
* `product-and-requirements` 相关 PRD 资产发生了较大规模裁剪与结构收敛，尤其是 checklist 与 overview 文件。
* `electron` 与 `nextjs` 框架规范中出现了批量统一动作，例如补充 `**Language**: English` 尾注，以及将 `should` 调整为 `must`。
* 从 `.trellis/spec/library-assets/*.md` 可知，`trellis-library` 对 checklist、template、spec 各自有明确结构约束，但这些约束并不自动证明全库现状已完全统一。

## Assumptions (temporary)

* 用户当前更关心“是否已经达到全库完全一致”的真实性判断，而不是立即修改文件。
* “术语一致”至少包含：相同概念使用同一命名；规范性语气一致；相关资产之间的引用关系一致。
* “格式一致”至少包含：同类资产的标题层级、段落骨架、尾注写法、列表样式和文档收尾形式一致。

## Open Questions

* 评估范围是否以“全量 trellis-library”为准，还是只要求“当前改动涉及的资产族内部一致”。

## Requirements (evolving)

* 盘点当前改动涉及的资产类型和主题范围。
* 抽查并比对 checklist / template / spec 三类资产的结构收敛情况。
* 识别至少一组可以支持“已统一”或“未完全统一”的具体证据。
* 明确哪些判断已被代码库证据支持，哪些仍属于范围边界问题。
* 先定义 `trellis-library` 术语与格式一致性的规则来源和落点，再决定是否批量整改。

## Acceptance Criteria (evolving)

* [ ] 给出当前改动覆盖范围的客观盘点结果。
* [ ] 给出至少 2-3 处具体证据，说明一致性改动已经发生在哪里。
* [ ] 给出至少 1 处具体证据，说明仍不能宣称“全库完全一致”，或说明为什么可以宣称。
* [ ] 给出后续收敛建议，能直接转化为实现或审查动作。

## Definition of Done (team quality bar)

* 结论基于仓库实际内容，而不是主观推断。
* 关键判断能回溯到具体文件或搜索结果。
* 明确标注已完成判断、未完成判断和证据边界。

## Out of Scope (explicit)

* 本轮不直接批量修改 `trellis-library/` 文件。
* 本轮不做“所有未改动文件逐行人工审校”。
* 本轮不对 `.trellis/spec/` 或工具部署层做同步性审计。

## Technical Notes

* Task dir: `.trellis/tasks/03-30-trellis-library-consistency-review`
* Diff summary: `git diff --stat -- trellis-library`
* Source-of-truth guidance checked:
  * `.trellis/spec/library-assets/index.md`
  * `.trellis/spec/library-assets/spec-authoring.md`
  * `.trellis/spec/library-assets/template-authoring.md`
  * `.trellis/spec/library-assets/checklist-authoring.md`
  * `trellis-library/taxonomy.md`
* Initial evidence indicates a large normalization pass, but not yet proof of full-library completion.

## Research Notes

### What changed in the current diff

* `product-and-requirements` assets were substantially simplified and normalized.
* `electron` and `nextjs` framework specs received batch footer and wording updates.
* `manifest.yaml` summaries were rewritten away from heading-like or emphasis-heavy text into flatter descriptive summaries.

### Concrete evidence that consistency improved

* `trellis-library/manifest.yaml` now rewrites many summary fields from inconsistent styles such as `**Purpose**: ...`, `## 1. Overview`, or severity-led blurbs into normalized descriptive summaries.
* `trellis-library/specs/technologies/frameworks/electron/overview.md` and `trellis-library/specs/technologies/frameworks/nextjs/overview.md` now both end with `**Language**: English`.
* `trellis-library/checklists/universal-domains/product-and-requirements/customer-facing-prd-checklist.md` and `developer-facing-prd-checklist.md` were both reworked toward sectioned, checklist-oriented structures.

### Concrete evidence that full-library consistency is NOT yet established

* Language footer format is still mixed across same-level framework spec files:
  * `trellis-library/specs/technologies/frameworks/electron/main-process/quality.md` ends with `**Language**: English`
  * `trellis-library/specs/technologies/frameworks/electron/renderer/quality.md` ends with `**Language**: All documentation must be written in **English**.`
* Checklist structure is still mixed across the checklist library:
  * `trellis-library/checklists/universal-domains/security/security-review-checklist.md` uses the minimal flat-bullet format
  * `trellis-library/checklists/universal-domains/product-and-requirements/customer-facing-prd-checklist.md` uses multi-section checkbox format
* Therefore the current diff demonstrates local normalization, not proof of complete all-file convergence.

## Preliminary Conclusion

Current changes do improve terminology and formatting consistency in several asset families, but they do not yet justify the claim that all files in `trellis-library` are now fully consistent.

## Decision (ADR-lite)

**Context**: User chose the "rules first" direction instead of immediately normalizing files.

**Decision**: Use the existing `.trellis/spec/library-assets/` authoring guidelines as the primary rule layer for consistency requirements, rather than starting with blind file edits.

**Consequences**:
* This keeps the source of truth close to existing asset-authoring policy.
* It allows later edits and reviews to be judged against explicit standards.
* We still need to decide whether the first version should be documentation-only or partially machine-enforced.

## Feasible Approaches Here

**Approach A: Authoring-rule MVP** (Recommended)

* Add explicit rules to:
  * `.trellis/spec/library-assets/spec-authoring.md`
  * `.trellis/spec/library-assets/template-authoring.md`
  * `.trellis/spec/library-assets/checklist-authoring.md`
  * optionally `.trellis/spec/library-assets/manifest-maintenance.md`
* Define canonical expectations for:
  * terminology
  * section skeletons
  * `Language` footer format
  * manifest `summary` style
* Pros:
  * Lowest risk
  * Fits existing source-of-truth structure
  * Fast to apply
* Cons:
  * Human review still needed; validator does not fully enforce it

**Approach B: Rule docs + lightweight validator**

* Do Approach A, plus extend `trellis-library/scripts/validation/validate-library-sync.py` to enforce a small set of machine-checkable consistency rules.
* Candidate checks:
  * manifest summary must be one-line plain summary, not heading fragments
  * `Language` footer must match one allowed canonical form
  * checklist/template required skeletons must match stricter patterns
* Pros:
  * Prevents regression automatically
  * Produces auditable findings
* Cons:
  * More scope
  * Requires careful allowlists for legacy assets

**Approach C: New dedicated style-consistency spec**

* Create a new reusable spec concern just for trellis-library wording/format consistency, then reference it from authoring guides.
* Pros:
  * Clean conceptual separation
  * Better for long-term governance if this grows large
* Cons:
  * Adds another layer before current basics are stable
  * Higher documentation overhead now

## Verification

* Ran `/ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings`
* Result: pass
* Limitation: this validation checks library integrity and sync-related rules, not semantic or stylistic full-library uniformity.
