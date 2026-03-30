# Electron Development Guidelines

Development guidelines for production Electron applications (main process + renderer process).

> **Applicability**: These guidelines document a specific, proven stack (Electron + Vite + electron-builder + better-sqlite3). They assume this exact combination. If your project uses a different bundler (webpack), a different package manager (npm/yarn), or a different database (SQLite alternatives), adapt accordingly.

## Structure

### [Renderer Process](./renderer/)

React + TypeScript renderer process development patterns:

- [Directory Structure](./renderer/directory-structure.md)
- [Components](./renderer/components.md)
- [State Management](./renderer/state-management.md)
- [Hooks](./renderer/hooks.md)
- [IPC Communication](./renderer/ipc-electron.md)
- [CSS Design](./renderer/css-design.md)
- [Type Safety](./renderer/type-safety.md)
- [React Pitfalls](./renderer/react-pitfalls.md)
- [Electron Browser API Restrictions](./renderer/electron-browser-api-restrictions.md)

### [Main Process](./main-process/)

Electron main process development patterns:

- [Directory Structure](./main-process/directory-structure.md)
- [API Module](./main-process/api-module.md)
- [API Patterns](./main-process/api-patterns.md)
- [Database](./main-process/database.md)
- [Logging](./main-process/logging.md)
- [Error Handling](./main-process/error-handling.md)
- [Pagination](./main-process/pagination.md)
- [Environment](./main-process/environment.md)
- [Type Safety](./main-process/type-safety.md)
- [macOS Permissions](./main-process/macos-permissions.md)
- [Text Input](./main-process/text-input.md)

### [Shared](./shared/)

Cross-cutting concerns:

- [TypeScript Conventions](./shared/typescript.md)
- [Code Quality](./shared/code-quality.md)
- [Git Conventions](./shared/git-conventions.md)
- [Timestamp Handling](./shared/timestamp.md)
- [pnpm + Electron Setup](./shared/pnpm-electron-setup.md)

### [Guides](./guides/)

Development thinking guides:

- [Pre-Implementation Checklist](./guides/pre-implementation-checklist.md)
- [Cross-Layer Thinking](./guides/cross-layer-thinking.md)
- [Code Reuse Thinking](./guides/code-reuse-thinking.md)
- [Bug Root Cause Thinking](./guides/bug-root-cause-thinking.md)
- [DB Schema Change](./guides/db-schema-change.md)
- [Transaction Consistency](./guides/transaction-consistency.md)
- [Semantic Change Checklist](./guides/semantic-change.md)

### [Common Issues / Pitfalls](../../../scenarios/defect-and-debugging/electron-pitfalls/)

Common issues and solutions (filed under `scenarios/`):

- [Native Module Packaging](../../../scenarios/defect-and-debugging/electron-pitfalls/native-module-packaging.md)
- [Native Module Complex Dependencies](../../../scenarios/defect-and-debugging/electron-pitfalls/native-module-complex-deps.md)
- [IPC Handler Registration](../../../scenarios/defect-and-debugging/electron-pitfalls/ipc-handler-registration.md)
- [Network Stack Differences](../../../scenarios/defect-and-debugging/electron-pitfalls/network-stack-differences.md)
- [Transaction Silent Failure](../../../scenarios/defect-and-debugging/electron-pitfalls/transaction-silent-failure.md)
- [React useState Function](../../../scenarios/defect-and-debugging/electron-pitfalls/react-usestate-function.md)
- [CSS Flex Centering](../../../scenarios/defect-and-debugging/electron-pitfalls/css-flex-centering.md)
- [Timestamp Precision](../../../scenarios/defect-and-debugging/electron-pitfalls/timestamp-precision.md)
- [Bluetooth HID Device](../../../scenarios/defect-and-debugging/electron-pitfalls/bluetooth-hid-device.md)
- [Global Keyboard Hooks](../../../scenarios/defect-and-debugging/electron-pitfalls/global-keyboard-hooks.md)

## Tech Stack

- **Package Manager**: pnpm (see [pnpm + Electron Setup](./shared/pnpm-electron-setup.md))
- **Renderer**: React 18, TypeScript, TanStack Query, Tailwind CSS
- **Main Process**: Electron, better-sqlite3, TypeScript
- **IPC**: Type-safe contextBridge pattern
- **Build**: Vite, electron-builder

## Placeholder Convention

> `@your-app/*` is a **project-specific placeholder**. Replace it with your actual monorepo scope/name (e.g., `@acme/shared`, `@acme/icons`).

Do not use `@your-app/*` literally in production code — it is a convention placeholder indicating "insert your project scope here". Other common placeholder patterns:
- `@shared/*` — shared packages within the monorepo (not project-specific)
- `@server/*`, `@lib/*` — internal barrel aliases

## Non-Goals

These guidelines do **not** cover:
- Non-Electron desktop frameworks (Tauri, Neutralino.js, NW.js)
- Non-Vite build tooling (webpack, esbuild standalone)
- Non-better-sqlite3 databases (Prisma, TypeORM, remote databases)
- Non-TypeScript projects
- Web-only applications without a desktop target

## Usage

These guidelines can be used as:

1. **New Project Template** - Copy the entire structure for new Electron projects
2. **Reference Documentation** - Consult specific guides when implementing features
3. **Code Review Checklist** - Verify implementations against established patterns
4. **Onboarding Material** - Help new developers understand project conventions

---

**Language**: English
