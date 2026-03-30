# pnpm + Electron Setup Guide

> **Purpose**: Provide a complete setup guide for managing Electron projects
> with pnpm, including monorepo layout, native-module handling, and packaging
> configuration.

---

## Why Electron Projects Need Special pnpm Configuration

pnpm uses a **symlinked, content-addressable store** by default, which produces
a non-flat `node_modules` layout:

```
node_modules/
├── .pnpm/                    # Actual package store
│   ├── better-sqlite3@9.0.0/
│   │   └── node_modules/
│   │       └── better-sqlite3/
│   └── bindings@1.5.0/
└── your-package -> .pnpm/... # Symlink
```

**Problems**:

1. **Native module path resolution fails** because Electron packaging does not
   always handle symlinks correctly.
2. **`electron-rebuild` cannot find modules** reliably without a flatter
   layout.
3. **asar packaging breaks** because symlinks are not packaged into asar
   archives.

**Recommended fix**: use `shamefully-hoist` to emulate an npm-like flat
dependency layout.

---

## Base Configuration

### 1. `.npmrc` Configuration (Required)

```ini
# .npmrc

# Use a hoisted node_modules layout similar to npm
node-linker=hoisted

# Hoist dependencies into the root node_modules directory
shamefully-hoist=true

# Optional: relax peer-dependency failures
strict-peer-dependencies=false

# Optional: speed up repeated installs
prefer-offline=true
```

**Why these settings matter**:

| Setting | Effect | Why it matters |
| ------- | ------ | -------------- |
| `node-linker=hoisted` | Uses a flat `node_modules` tree | Electron packaging expects this layout more often |
| `shamefully-hoist=true` | Hoists dependencies to the root | Helps native-module resolution |
| `strict-peer-dependencies=false` | Ignores peer-dependency warnings | Electron ecosystem packages often have version friction |

### 2. `pnpm-workspace.yaml` for Monorepos

```yaml
# pnpm-workspace.yaml

packages:
  - 'apps/*' # Electron applications
  - 'packages/*' # Shared packages
  - '!**/dist' # Exclude build output
  - '!**/out' # Exclude Electron packaging output
```

**Typical monorepo structure**:

```
my-electron-project/
├── .npmrc
├── pnpm-workspace.yaml
├── package.json              # Root package.json
├── apps/
│   └── desktop/              # Electron application
│       ├── package.json
│       ├── forge.config.ts
│       ├── src/
│       │   ├── main/         # Main process
│       │   ├── renderer/     # Renderer process
│       │   └── preload/      # Preload scripts
│       └── ...
└── packages/
    ├── shared/               # Shared code
    │   └── package.json
    └── ui/                   # Shared UI components
        └── package.json
```

### 3. Root `package.json`

```json
{
  "name": "my-electron-monorepo",
  "private": true,
  "scripts": {
    "dev": "pnpm --filter @my-app/desktop dev",
    "build": "pnpm --filter @my-app/desktop build",
    "package": "pnpm --filter @my-app/desktop package",
    "make": "pnpm --filter @my-app/desktop make",
    "lint": "pnpm -r lint",
    "typecheck": "pnpm -r typecheck",
    "postinstall": "electron-builder install-app-deps"
  },
  "devDependencies": {
    "electron": "^28.0.0"
  },
  "engines": {
    "node": ">=18.0.0",
    "pnpm": ">=8.0.0"
  },
  "packageManager": "pnpm@8.15.0"
}
```

---

## Native Module Configuration

### Problem: Native Modules Must Be Rebuilt for Electron

Native modules such as `better-sqlite3` contain compiled C++ code and must be
built against Electron's Node.js ABI, not stock Node.js.

### Option 1: `electron-rebuild` (Recommended)

```json
// apps/desktop/package.json
{
  "scripts": {
    "postinstall": "electron-rebuild",
    "rebuild": "electron-rebuild -f"
  },
  "devDependencies": {
    "@electron/rebuild": "^3.6.0"
  }
}
```

### Option 2: `electron-builder install-app-deps`

```json
// root package.json
{
  "scripts": {
    "postinstall": "electron-builder install-app-deps"
  },
  "devDependencies": {
    "electron-builder": "^24.0.0"
  }
}
```

### Option 3: Let Electron Forge Handle It

If you use Electron Forge, configure `rebuildConfig`:

```typescript
// forge.config.ts
import type { ForgeConfig } from '@electron-forge/shared-types';

const config: ForgeConfig = {
  rebuildConfig: {
    force: true, // Force all native modules to rebuild
  },
  // ...
};

export default config;
```

---

## Electron Forge + pnpm Configuration

### Full `forge.config.ts` Example

```typescript
// apps/desktop/forge.config.ts
import type { ForgeConfig } from '@electron-forge/shared-types';
import { FusesPlugin } from '@electron-forge/plugin-fuses';
import { VitePlugin } from '@electron-forge/plugin-vite';
import { FuseV1Options, FuseVersion } from '@electron/fuses';
import path from 'path';
import { cp, mkdir } from 'fs/promises';

// Native modules and the packages they depend on
const nativeModules = ['better-sqlite3', 'bindings', 'file-uri-to-path'];

const config: ForgeConfig = {
  packagerConfig: {
    asar: {
      // Extract native binaries outside the asar bundle
      unpack: '*.{node,dll}',
    },
    // Include only the node_modules entries that are actually required
    ignore: [
      // Exclude all node_modules except the allowlisted native modules
      new RegExp(`node_modules/(?!(${nativeModules.join('|')})/)`),
      // Exclude development files
      /\.git/,
      /\.vscode/,
      /\.idea/,
      /src\//,
      /\.ts$/,
      /\.map$/,
    ],
  },

  rebuildConfig: {
    force: true,
  },

  hooks: {
    // Copy native modules after packaging
    packageAfterCopy: async (_forgeConfig, buildPath) => {
      const sourceNodeModules = path.resolve(__dirname, 'node_modules');
      const destNodeModules = path.resolve(buildPath, 'node_modules');

      for (const packageName of nativeModules) {
        const sourcePath = path.join(sourceNodeModules, packageName);
        const destPath = path.join(destNodeModules, packageName);

        try {
          await mkdir(path.dirname(destPath), { recursive: true });
          await cp(sourcePath, destPath, {
            recursive: true,
            preserveTimestamps: true,
          });
        } catch (error) {
          console.warn(`Failed to copy ${packageName}:`, error);
        }
      }
    },
  },

  plugins: [
    new VitePlugin({
      build: [
        { entry: 'src/main/index.ts', config: 'vite.main.config.ts' },
        { entry: 'src/preload/index.ts', config: 'vite.preload.config.ts' },
      ],
      renderer: [{ name: 'main_window', config: 'vite.renderer.config.ts' }],
    }),

    new FusesPlugin({
      version: FuseVersion.V1,
      [FuseV1Options.RunAsNode]: false,
      [FuseV1Options.EnableCookieEncryption]: true,
      [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,
      [FuseV1Options.EnableNodeCliInspectArguments]: false,
      [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: true,
      [FuseV1Options.OnlyLoadAppFromAsar]: false, // Allow unpacked files
    }),
  ],
};

export default config;
```

### Vite Configuration: Externalize Native Modules

```typescript
// vite.main.config.ts
import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    rollupOptions: {
      external: [
        'electron',
        'better-sqlite3',
        // Other native modules
      ],
    },
  },
  resolve: {
    // Ensure Node.js built-ins resolve correctly
    conditions: ['node'],
    mainFields: ['module', 'jsnext:main', 'jsnext'],
  },
});
```

---

## Common Troubleshooting Cases

### Issue 1: `Cannot find module 'better-sqlite3'`

**Cause**: the native module was not packaged correctly.

**Checks**:

```bash
# 1. Confirm .npmrc is correct
cat .npmrc
# Expected:
# node-linker=hoisted
# shamefully-hoist=true

# 2. Reinstall dependencies
rm -rf node_modules pnpm-lock.yaml
pnpm install

# 3. Check node_modules layout
ls -la node_modules/better-sqlite3
# This should be a real directory, not a symlink

# 4. Rebuild the native module
pnpm rebuild better-sqlite3
```

### Issue 2: `NODE_MODULE_VERSION mismatch`

**Error**:

```
Error: The module was compiled against a different Node.js version
```

**Cause**: the native module was built for Node.js instead of Electron.

**Fix**:

```bash
# Force a rebuild of all native modules
npx electron-rebuild -f

# Or set this in forge.config.ts
rebuildConfig: {
  force: true,
}
```

### Issue 3: Shared Packages Cannot Be Resolved in a Monorepo

**Cause**: the workspace protocol or workspace file is configured incorrectly.

**Fix**:

```json
// apps/desktop/package.json
{
  "dependencies": {
    "@my-app/shared": "workspace:*"
  }
}
```

Make sure `pnpm-workspace.yaml` includes the shared package paths.

### Issue 4: Packaged App Fails to Start

**Debug steps**:

```bash
# 1. Inspect the packaged resources
ls -la out/*/resources/

# 2. Inspect the asar archive
npx asar list out/*/resources/app.asar

# 3. Inspect unpacked files
ls -la out/*/resources/app.asar.unpacked/

# 4. Run the packaged app and inspect logs
# macOS
./out/MyApp-darwin-x64/MyApp.app/Contents/MacOS/MyApp

# Windows
./out/MyApp-win32-x64/MyApp.exe
```

### Issue 5: `electron-rebuild` Fails After `pnpm install`

**Cause**: Python or C++ build tools may be missing.

**Fix**:

```bash
# macOS
xcode-select --install

# Windows (Administrator PowerShell)
# OS-level exception: native-module build tooling still comes from npm global
# installation because pnpm does not provide an equivalent global system-tool flow.
npm install --global windows-build-tools

# Or install Visual Studio Build Tools directly
```

---

## Best Practices

### 1. Pin the Electron Version

```json
// package.json
{
  "devDependencies": {
    "electron": "28.0.0" // Pin the exact version instead of using ^
  }
}
```

### 2. Declare `packageManager`

```json
// package.json
{
  "packageManager": "pnpm@8.15.0",
  "engines": {
    "node": ">=18.0.0",
    "pnpm": ">=8.0.0"
  }
}
```

### 3. Configure CI/CD Explicitly

```yaml
# .github/workflows/build.yml
jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [macos-latest, windows-latest, ubuntu-latest]

    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v2
        with:
          version: 8

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'pnpm'

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build
        run: pnpm build

      - name: Package
        run: pnpm package
```

### 4. Keep Development Scripts Consistent

```json
// apps/desktop/package.json
{
  "scripts": {
    "dev": "electron-forge start",
    "build": "tsc && vite build",
    "package": "electron-forge package",
    "make": "electron-forge make",
    "lint": "eslint src/",
    "typecheck": "tsc --noEmit",
    "postinstall": "electron-rebuild"
  }
}
```

---

## Setup Checklist

When starting a new Electron + pnpm project:

- [ ] Create `.npmrc` with `shamefully-hoist=true` and `node-linker=hoisted`
- [ ] Create `pnpm-workspace.yaml` if the project is a monorepo
- [ ] Add a `postinstall` script that runs `electron-rebuild`
- [ ] Configure `rebuildConfig.force = true` in `forge.config.ts`
- [ ] Mark native modules as external in the Vite configuration
- [ ] Handle `node_modules` correctly in `packagerConfig.ignore`
- [ ] Test packaging by running `pnpm package` and launching the packaged app

---

## References

- [pnpm Documentation](https://pnpm.io/)
- [Electron Forge](https://www.electronforge.io/)
- [electron-rebuild](https://github.com/electron/rebuild)
- [Native Module Packaging Guide](../../../../scenarios/defect-and-debugging/electron-pitfalls/native-module-packaging.md)

---

**Language**: English
