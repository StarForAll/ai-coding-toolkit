# Dependency Selection & Compatibility

> Use this file to choose dependency families and compatibility checks. Pin
> exact versions in the target project after checking the current stable
> release notes for the stack you actually ship.

---

## Core Dependency Families

| Area | Representative packages | Guidance |
|------|--------------------------|----------|
| Framework core | `next`, `react`, `react-dom`, `typescript` | Keep these on mutually supported stable majors and verify App Router compatibility before upgrades. |
| API layer | `hono`, `@orpc/server`, `@orpc/client`, `@orpc/zod`, `@orpc/openapi`, `zod` | Upgrade server, client, adapters, and schema packages as a compatibility group. |
| Database | `drizzle-orm`, `drizzle-kit`, `drizzle-zod`, `pg` | Pin ORM, CLI, and codegen helpers together; run migrations and type checks after every major change. |
| Authentication | `better-auth` | Add only when the target project uses this auth model. |
| Cache and queue | `@upstash/redis`, `@upstash/qstash` | Keep optional infrastructure packages out of minimal installs. |
| AI integration | `ai`, `@ai-sdk/react`, provider packages | Select provider packages and model IDs from current stable vendor docs; avoid experimental SDK APIs in baseline guidance. |
| UI primitives | `@radix-ui/*`, `lucide-react`, `cmdk`, `sonner` | Pin explicitly in the target project; never rely on `latest`. |
| Styling | `tailwindcss`, `@tailwindcss/postcss`, `tailwind-merge`, `class-variance-authority`, `clsx` | Upgrade styling plugins with their parent framework/tooling compatibility in mind. |
| State and forms | `@tanstack/react-query`, `@orpc/tanstack-query`, `nuqs`, `react-hook-form`, `@hookform/resolvers` | Treat bridge packages as version-coupled with the primary state library. |
| Internationalization and utilities | `next-intl`, `date-fns`, `es-toolkit`, `nanoid`, `p-limit` | Keep only the packages the target project actually uses. |
| Observability and QA | `@sentry/nextjs`, `@playwright/test`, `@biomejs/biome`, `husky`, `turbo`, `tsx` | Validate build, type-check, lint, and end-to-end flows after major upgrades. |

---

## Selection Rules

1. Prefer current stable releases over canary, beta, or experimental lines for shared project baselines.
2. Never use `latest` in reusable documentation as a version recommendation.
3. Pin exact versions in the target project's package manifest and lockfile, not in this library asset.
4. Upgrade framework triplets together when they are closely coupled, especially `next` + `react` + `react-dom`.
5. Keep generator and runtime packages aligned for families such as oRPC, Drizzle, and AI SDK providers.
6. Remove packages that do not support an active feature in the target project.

---

## Compatibility Checks

When updating dependencies:

1. Check the current stable Next.js release notes and React compatibility matrix.
2. Verify App Router behavior, build output, and type-checks after framework upgrades.
3. Re-run migrations and schema generation when changing Drizzle or database adapters.
4. Re-test auth, caching, queue, and AI integrations when their bridge packages change.
5. Run `pnpm install`, `pnpm type-check`, and `pnpm build` in the target project before shipping.

---

## Dependency Hygiene

- Prefer the smallest install surface that supports the target project's active features.
- Remove stale or partially adopted packages instead of carrying speculative dependencies.
- Record exceptional compatibility constraints close to the target project's package manifest or architecture notes.

---

**Language**: English
