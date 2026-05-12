# Stable Documentation Audit

Date: 2026-05-12

## Scope

Audit version-sensitive or experimental-sensitive content in `trellis-library/` against current stable official documentation retrieved through Context7.

## Evidence Summary

### Next.js

Source: Context7 `/vercel/next.js`

Findings:

* App Router is stable and recommended by default for new work.
* The old `appDir` option is no longer needed since App Router stabilization.
* Stable reusable guidance should focus on App Router patterns, data fetching, layouts, and routing behavior instead of brittle version labels when the rule is not version-specific.

Implication for local assets:

* `specs/technologies/frameworks/nextjs/overview.md` should stop over-indexing on exact version labels when the normative guidance is really about App Router + stack shape.
* Version-heavy dependency inventory should be generalized or narrowed to compatibility classes instead of long exact package lists.

### Vercel AI SDK

Source: Context7 `/vercel/ai/ai_5_0_0`

Findings:

* In stable AI SDK 5 docs, telemetry is still configured with `experimental_telemetry`.
* The docs explicitly describe telemetry as experimental and subject to change.
* AI SDK 5 introduces transport-based chat configuration, with `DefaultChatTransport` as the documented pattern for `useChat`.
* Tool-part formats in UI messages changed in AI SDK 5 and are typed, so reusable docs should avoid presenting one ad hoc internal shape as a durable contract unless clearly scoped.

Implication for local assets:

* `nextjs/backend/ai-sdk-integration.md` and `nextjs/backend/logging.md` must not say telemetry should always be enabled as a stable default without warning that the API is experimental.
* `nextjs/frontend/ai-sdk-integration.md` should prefer transport-based `useChat` guidance over older `api:` shorthand examples.
* Detailed tool-part parsing examples should be reduced or clearly marked as version-sensitive if retained.

### Spring Boot

Source: Context7 `/spring-projects/spring-boot/v4.0.3`

Findings:

* Current stable Spring Boot 4 documentation requires Java 17 or higher.
* Stable official positioning remains production-grade Spring-powered applications and services with minimal configuration overhead.

Implication for local assets:

* Example content that still treats `Spring Boot 2.5+` and `Java 11+` as the current baseline is stale and should be updated to a modern stable baseline or generalized if the example does not require exact numbers.

### React

Source: Context7 `/reactjs/react.dev`

Findings:

* Stable React guidance centers on components, props, state, hooks, and purity rules.
* Version policy distinguishes stable from unstable channels, which supports avoiding unnecessary hard-coded version claims in reusable docs unless a feature truly depends on them.

Implication for local assets:

* Documents like `electron/overview.md` should describe React as the renderer UI layer without freezing the guidance to `React 18` unless that version is materially required.

### Vue

Source: Context7 `/websites/vuejs_guide`

Findings:

* Stable Vue guidance emphasizes component-based architecture, reactive state, composables, and Pinia for larger-scale state management.
* Reusable guidance should remain pattern-oriented and version-stable where possible.

Implication for local assets:

* Existing Vue component/state docs look structurally aligned; no immediate version-specific correction surfaced in this audit.

### Electron

Source: Context7 `/electron/electron`

Findings:

* Stable Electron positioning is framework-neutral: Chromium + Node.js + optional native code.
* Security guidance favors staying on current Electron versions rather than pinning reusable docs to a fixed React version.

Implication for local assets:

* `electron/overview.md` should stay stack-specific where helpful, but exact React version labeling is lower-value than describing renderer/main process responsibilities and the underlying Electron model.

## Recommended Edit Strategy

1. Replace experimental-as-default wording with experimental-with-caution wording.
2. Replace exact version inventories that will drift quickly with compatibility-oriented guidance.
3. Keep explicit versions only where the stable official docs make them a current baseline requirement with high authoring value.
4. Remove or compress low-value volatile details whose maintenance cost exceeds their reusable benefit.
