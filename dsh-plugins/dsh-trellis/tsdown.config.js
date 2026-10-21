import { readFileSync } from "node:fs";
import { defineConfig } from "tsdown";

const id = "dsh-trellis";
const pkg = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8"));
const externals = new Set(["react", "react/jsx-runtime"]);

export default defineConfig({
  name: `${id}/client`,
  entry: { client: "src/client/index.jsx" },
  outDir: "lib",
  format: "cjs",
  platform: "browser",
  target: "es2022",
  dts: false,
  sourcemap: true,
  // The settings page shows the installed plugin version without asking the
  // host for it; the build stamps this package's own version.
  define: { __DSH_TRELLIS_VERSION__: JSON.stringify(pkg.version) },
  clean: false,
  deps: {
    neverBundle: (specifier) => externals.has(specifier),
    alwaysBundle: (specifier) => !externals.has(specifier),
  },
  outputOptions: {
    entryFileNames: "client.js",
    // Keep committed/published maps reproducible across LF and CRLF checkouts.
    // The source paths still resolve in a development checkout; embedding the
    // source text would make Windows prepack output differ byte-for-byte.
    sourcemapExcludeSources: true,
    banner: `window.__ModuleLoader__.load({ id: ${JSON.stringify(id)}, factory: (require) => {`,
    footer: "return module.exports; } });",
    intro: "var module = { exports: {} }; var exports = module.exports;",
  },
});
