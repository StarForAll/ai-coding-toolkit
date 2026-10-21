import { readFile } from "node:fs/promises";
import vm from "node:vm";
import { test } from "node:test";
import assert from "node:assert/strict";
import * as React from "react";
import * as jsxRuntime from "react/jsx-runtime";
import { renderToStaticMarkup } from "react-dom/server";
import { DEFAULTS } from "../src/client/form.js";

async function clientHarness(initialSlots = {}, modern = false, value = DEFAULTS) {
  const definitions = new Map(Object.entries(initialSlots));
  const registrations = new Map();
  const dependencies = new Map();
  const effects = [];
  const styles = new Set();
  const locales = new Set();
  const snapshot = { status: "ready", writable: true, value, base: {}, user: {} };
  const scope = { getSnapshot: () => snapshot, subscribe: () => () => {} };
  let declaration;
  vm.runInNewContext(await readFile(new URL("../lib/client.js", import.meta.url), "utf8"), {
    window: { __ModuleLoader__: { load(value) { declaration = value; } } },
    document: {
      querySelector() { return styles.values().next().value ?? null; },
      createElement() { const tag = { dataset: {}, remove() { styles.delete(tag); } }; return tag; },
      head: { appendChild(tag) { styles.add(tag); } },
    },
  });
  const client = declaration.factory((name) => {
    if (name === "react") return React;
    if (name === "react/jsx-runtime") return jsxRuntime;
    throw new Error(`Unexpected bundled client import: ${name}`);
  });
  const ctx = {
    inject(services, callback) {
      if (services[0] === (modern ? "configForms" : "settingsScope")) callback(ctx);
    },
    effect(callback) { const dispose = callback(); effects.push(dispose); return dispose; },
    locale: {
      register(ns) { locales.add(ns); return () => locales.delete(ns); },
      bind(ns) { assert.equal(ns, "settings.dsh-trellis"); return (key) => key; },
    },
    settingsScope: { bind({ namespace }) { assert.equal(namespace, "dsh-trellis"); return scope; } },
    configForms: { get(namespace) { assert.equal(namespace, "dsh-trellis"); return scope; } },
    slots: {
      spec(name) { return definitions.get(name); },
      inject(name, callback) {
        const record = { callback, dispose: definitions.has(name) ? callback() : undefined };
        dependencies.set(name, record);
        effects.push(() => { record.dispose?.(); dependencies.delete(name); });
      },
      register(options, Component) {
        const id = `${options.name}:${options.key ?? options.id}`;
        assert.equal(registrations.has(id), false, "duplicate slot registration");
        registrations.set(id, { options, Component });
        return () => registrations.delete(id);
      },
    },
  };
  client.apply(ctx);
  return {
    registrations, styles, locales, effects,
    mount(name, spec) {
      definitions.set(name, spec);
      const record = dependencies.get(name);
      record.dispose ??= record.callback();
    },
    unmount(name) {
      definitions.delete(name);
      const record = dependencies.get(name);
      record.dispose?.();
      record.dispose = undefined;
    },
    dispose() { for (const dispose of effects.splice(0).reverse()) dispose?.(); },
    render(name, view) {
      const entry = [...registrations.values()].find(({ options }) => options.name === name);
      assert.ok(entry);
      return renderToStaticMarkup(React.createElement(entry.Component, {
        ...(typeof entry.options.inject === "function" ? entry.options.inject() : {}),
        t: (key) => key,
        view,
        close: () => {},
      }));
    },
  };
}

for (const modern of [false, true]) {
  test(`${modern ? "configForms" : "legacy"} settings section renders the full Trellis page`, async () => {
    const h = await clientHarness({ "settings.section": { kind: "list" } }, modern);
    assert.deepEqual([...h.registrations.keys()], ["settings.section:trellis"]);
    const entry = [...h.registrations.values()][0];
    assert.equal(entry.options.order, 16);
    assert.equal(entry.options.locale, "settings.dsh-trellis");
    assert.equal(entry.options.label(), "sectionTitle");
    assert.equal(typeof entry.options.inject().scope.getSnapshot, "function");

    const page = h.render("settings.section");
    assert.match(page, /<div class="dsh-trellis-section"/);
    assert.match(page, /dsh-trellis-max-bytes/);
    assert.match(page, /dsh-trellis-version-check/);
    assert.match(page, /dsh-trellis-plugin-repo/);
    assert.match(page, /dsh-trellis-monitor/);
    assert.match(page, />save<\/button>/);
    assert.doesNotMatch(page, /aria-expanded/);
    assert.equal(h.render("settings.section", "summary"), "description");

    h.dispose();
    assert.equal(h.registrations.size, 0);
    assert.equal(h.styles.size, 0);
    assert.equal(h.locales.size, 0);
  });
}

test("late slot ownership and repeated section reloads do not duplicate registrations", async () => {
  const h = await clientHarness();
  assert.equal(h.registrations.size, 0);
  for (let i = 0; i < 3; i++) {
    h.mount("settings.section", { kind: "list" });
    h.mount("settings.section", { kind: "list" });
    assert.equal(h.registrations.size, 1);
    h.unmount("settings.section");
    assert.equal(h.registrations.size, 0);
  }
  h.mount("settings.section", { kind: "list" });
  h.dispose();
  assert.equal(h.registrations.size, 0);
  assert.equal(h.styles.size, 0);
  assert.equal(h.locales.size, 0);
});

test("disabling version monitoring hides its fields and the monitor panel", async () => {
  const h = await clientHarness({ "settings.section": { kind: "list" } }, true, {
    ...DEFAULTS,
    versionCheck: false,
  });
  const page = h.render("settings.section");
  assert.match(page, /dsh-trellis-version-check/);
  assert.doesNotMatch(page, /dsh-trellis-version-interval/);
  assert.doesNotMatch(page, /dsh-trellis-version-notify/);
  assert.doesNotMatch(page, /dsh-trellis-plugin-repo/);
  assert.doesNotMatch(page, /dsh-trellis-trellis-package/);
  assert.doesNotMatch(page, /dsh-trellis-monitor/);
  h.dispose();
});

test("capability switches (commands, guard, push, spec) sit at the top", async () => {
  const h = await clientHarness({ "settings.section": { kind: "list" } }, true);
  const page = h.render("settings.section");
  const commands = page.indexOf("dsh-trellis-commands");
  const guard = page.indexOf("dsh-trellis-dispatch-guard");
  const push = page.indexOf("dsh-trellis-subagent-context");
  const spec = page.indexOf("dsh-trellis-spec-injection");
  const behavior = page.indexOf("dsh-trellis-max-bytes");
  assert.ok(commands > 0, "commands switch");
  assert.ok(guard > commands, "guard below commands");
  assert.ok(push > guard, "push below guard");
  assert.ok(spec > push, "spec below push");
  assert.ok(behavior > spec, "behavior fields below the capability group");
  h.dispose();
});

test("the conflict banner occupies the frame overlay", async () => {
  const h = await clientHarness({
    "settings.section": { kind: "list" },
    "shell.overlay": { kind: "list" },
  });
  assert.deepEqual([...h.registrations.keys()].sort(), [
    "settings.section:trellis",
    "shell.overlay:dsh-trellis-conflict",
  ]);
  const entry = [...h.registrations.values()].find(
    ({ options }) => options.name === "shell.overlay",
  );
  assert.equal(entry.options.locale, "settings.dsh-trellis");
  assert.equal(entry.options.order, 20);
  // Static render does not run effects, so the banner is absent rather than
  // throwing when no conflict route is reachable.
  assert.equal(h.render("shell.overlay"), "");
  h.dispose();
});
