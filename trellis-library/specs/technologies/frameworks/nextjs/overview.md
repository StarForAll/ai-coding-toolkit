# Next.js Full-Stack with oRPC/Drizzle Baseline

Development guidelines for production Next.js applications using the oRPC API layer and PostgreSQL with Drizzle ORM.

> **Applicability**: These guidelines document a specific, proven stack (Next.js 15 + oRPC + Drizzle + PostgreSQL). They are not universal — they assume this exact stack. If your project uses a different API layer (tRPC, REST, GraphQL) or ORM (Prisma, TypeORM), adapt accordingly.

## Structure

### [Frontend](./frontend/)

React 19 + Next.js 15 App Router frontend development patterns:

- [Directory Structure](./frontend/directory-structure.md)
- [Components](./frontend/components.md)
- [State Management](./frontend/state-management.md)
- [Hooks](./frontend/hooks.md)
- [API Integration](./frontend/api-integration.md)
- [oRPC Usage](./frontend/orpc-usage.md)
- [Authentication](./frontend/authentication.md)
- [AI SDK Integration](./frontend/ai-sdk-integration.md)
- [CSS & Layout](./frontend/css-layout.md)
- [Type Safety](./frontend/type-safety.md)
- [Quality Checklist](./frontend/quality.md)

### [Backend](./backend/)

oRPC + Drizzle ORM backend development patterns:

- [Directory Structure](./backend/directory-structure.md)
- [oRPC Usage](./backend/orpc-usage.md)
- [Authentication](./backend/authentication.md)
- [Database](./backend/database.md)
- [AI SDK Integration](./backend/ai-sdk-integration.md)
- [Logging](./backend/logging.md)
- [Performance](./backend/performance.md)
- [Type Safety](./backend/type-safety.md)
- [Quality Checklist](./backend/quality.md)

### [Shared](./shared/)

Cross-cutting concerns:

- [Dependencies](./shared/dependencies.md)
- [Code Quality](./shared/code-quality.md)
- [TypeScript Conventions](./shared/typescript.md)

### [Guides](./guides/)

Development thinking guides:

- [Pre-Implementation Checklist](./guides/pre-implementation-checklist.md)
- [Cross-Layer Thinking](./guides/cross-layer-thinking.md)

### [Common Issues / Pitfalls](../../../scenarios/defect-and-debugging/nextjs-pitfalls/)

Common issues and solutions (filed under `scenarios/`):

- [PostgreSQL JSON vs JSONB](../../../scenarios/defect-and-debugging/nextjs-pitfalls/postgres-json-jsonb.md)
- [WebKit Tap Highlight](../../../scenarios/defect-and-debugging/nextjs-pitfalls/webkit-tap-highlight.md)
- [Sentry & next-intl Conflict](../../../scenarios/defect-and-debugging/nextjs-pitfalls/sentry-nextintl-conflict.md)
- [Turbopack vs Webpack Flexbox](../../../scenarios/defect-and-debugging/nextjs-pitfalls/turbopack-webpack-flexbox.md)

## Tech Stack

- **Frontend**: Next.js 15, React 19, TailwindCSS 4, Radix UI, React Query
- **Backend**: oRPC, Drizzle ORM, PostgreSQL, better-auth
- **AI**: Vercel AI SDK (multi-provider)
- **Real-time**: Ably / WebSocket / SSE
- **Build**: Turborepo + pnpm (monorepo)
- **Monitoring**: Sentry + OpenTelemetry

## Placeholder Convention

> `@your-app/*` is a **project-specific placeholder**. Replace it with your actual project scope/name (e.g., `@myproject/*`, `@acme-desktop/*`).

Do not use `@your-app/*` literally in production code — it is a convention placeholder indicating "insert your project identifier here". Other common placeholder patterns:
- `@shared/*` — shared types/utilities (not project-specific)
- `@server/*`, `@lib/*` — internal barrel aliases

## Non-Goals

These guidelines do **not** cover:
- Non-Next.js frameworks (Express, NestJS, FastAPI standalone backends)
- Non-Drizzle ORMs (Prisma, TypeORM, raw SQL)
- Non-oRPC API layers (tRPC, REST controllers, GraphQL resolvers)
- Non-TypeScript projects
- Single-page deployments without a monorepo structure

## Usage

These guidelines can be used as:

1. **New Project Template** - Copy the entire structure for new Next.js projects
2. **Reference Documentation** - Consult specific guides when implementing features
3. **Code Review Checklist** - Verify implementations against established patterns
4. **Onboarding Material** - Help new developers understand project conventions
