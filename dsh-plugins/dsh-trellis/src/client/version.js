/**
 * The installed plugin version, stamped at build time.
 *
 * `__DSH_TRELLIS_VERSION__` is replaced by tsdown with the package version.
 * Source-level tests and any unbundled load keep the literal fallback.
 */
export const PLUGIN_VERSION =
  typeof __DSH_TRELLIS_VERSION__ === "string" ? __DSH_TRELLIS_VERSION__ : "dev";
