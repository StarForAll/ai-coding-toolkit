window.__ModuleLoader__.load({
	id: "dsh-trellis",
	factory: (require) => {
		var module = { exports: {} };
		var exports = module.exports;
		Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
		let react = require("react");
		let react_jsx_runtime = require("react/jsx-runtime");
		//#region src/client/conflicts.js
		/**
		* Client half of the Trellis-plugin conflict check.
		*
		* The Host reads its loader entries and serves the result; this module fetches
		* it once per page load and decides how to make it visible. A conflict means
		* both plugins inject the same workflow messages and register overlapping
		* tools, so the user has to act — a log line would not reach them.
		*
		* @module dsh-trellis/client/conflicts
		*/
		const CONFLICTS_ROUTE_PATH = "/dsh-trellis/conflicts";
		/**
		* Read the Host's conflict result.
		*
		* A missing route (older Host, Electron IPC) degrades to `unavailable`: the
		* client never invents a conflict, and never claims there is none.
		*
		* @param {typeof fetch} [fetchImpl]
		* @returns {Promise<{status: string, conflicts: Array<{id: string, name: string}>}>}
		*/
		async function fetchConflicts(fetchImpl = globalThis.fetch) {
			if (typeof fetchImpl !== "function") return {
				status: "unavailable",
				conflicts: []
			};
			try {
				const payload = await (await fetchImpl(CONFLICTS_ROUTE_PATH, { headers: { accept: "application/json" } })).json();
				if (payload?.ok !== true) return {
					status: "unavailable",
					conflicts: []
				};
				return {
					status: typeof payload.status === "string" ? payload.status : "unavailable",
					conflicts: Array.isArray(payload.conflicts) ? payload.conflicts : []
				};
			} catch {
				return {
					status: "unavailable",
					conflicts: []
				};
			}
		}
		/** Stable identity of a conflict set, used to notify once per set. */
		function conflictSignature(conflicts) {
			return conflicts.map((conflict) => `${conflict.id}:${conflict.name}`).sort().join("|");
		}
		/** Human-readable one-line list of the conflicting plugins. */
		function conflictSummary(conflicts, separator = "、") {
			return conflicts.map((conflict) => `${conflict.name}（${conflict.id}）`).join(separator);
		}
		//#endregion
		//#region src/client/version-check.js
		/**
		* Upstream version monitoring for the settings page — client half.
		*
		* The Host owns the outbound request (`lib/upstream.js`): GitHub's Atom feeds
		* have no CORS headers and the REST API's unauthenticated quota is what made a
		* browser check return 403. The client calls one same-origin route, compares
		* what it receives with what this browser recorded last time, and raises the
		* desktop notification.
		*
		* Three external dependencies can require updating this plugin or break it:
		* the plugin's upstream fork (watched by commit), and the Trellis and DSH npm
		* packages (watched by their published dist-tags — the same data `npm view
		* <pkg> dist-tags` prints).
		*
		* @module dsh-trellis/client/version-check
		*/
		const ROUTE_PATH = "/dsh-trellis/version-check";
		const LAST_CHECK_KEY = "dsh-trellis:version-check:last";
		const SEEN_PREFIX = "dsh-trellis:version-check:";
		/** Upstream sources, in display order. */
		const SOURCES = Object.freeze([
			{
				id: "plugin",
				kind: "commits",
				labelKey: "monitor.source.plugin",
				field: "versionCheckPluginRepo",
				defaultUrl: "https://github.com/SajoLuo/dsh-trellis"
			},
			{
				id: "trellis",
				kind: "npm",
				labelKey: "monitor.source.trellis",
				field: "versionCheckTrellisPackage",
				defaultUrl: "@mindfoldhq/trellis"
			},
			{
				id: "dsh",
				kind: "npm",
				labelKey: "monitor.source.dsh",
				field: "versionCheckDshPackage",
				defaultUrl: "@deepseek-ai/dsh"
			}
		]);
		/**
		* Same-origin route URL for one source.
		* @param {{id: string, kind: string}} source
		* @param {string} value - configured repository URL or package name.
		* @returns {string}
		*/
		function checkRouteUrl(source, value) {
			const params = new URLSearchParams({ source: source.kind === "npm" ? "npm" : "plugin" });
			if (source.kind === "npm") params.set("name", value);
			else params.set("url", value);
			return `${ROUTE_PATH}?${params.toString()}`;
		}
		/**
		* Ask the Host to look up one source.
		*
		* A failed check rejects with the Host's message so each source can report its
		* own error without taking the others down.
		*
		* @param {object} options
		* @param {{id: string, kind: string}} options.source
		* @param {string} options.value
		* @param {typeof fetch} [options.fetchImpl]
		* @returns {Promise<{commit?: object, release?: object | null, tags?: Record<string, string>}>}
		*/
		async function requestUpstream({ source, value, fetchImpl = globalThis.fetch }) {
			if (typeof fetchImpl !== "function") throw new Error("fetch is not available");
			const response = await fetchImpl(checkRouteUrl(source, value), { headers: { accept: "application/json" } });
			let payload;
			try {
				payload = await response.json();
			} catch {
				throw new Error(`version-check route returned ${response.status}`);
			}
			if (payload?.ok !== true) throw new Error(payload?.error ?? `version-check route returned ${response.status}`);
			return payload;
		}
		/** In-memory storage used when `localStorage` is unavailable (SSR, tests). */
		function memoryStorage(initial = {}) {
			const map = new Map(Object.entries(initial));
			return {
				getItem: (key) => map.get(key) ?? null,
				setItem: (key, value) => {
					map.set(key, String(value));
				},
				removeItem: (key) => {
					map.delete(key);
				}
			};
		}
		/** `localStorage` when reachable, otherwise a per-process fallback. */
		function defaultStorage() {
			try {
				if (typeof localStorage !== "undefined") {
					const probe = "dsh-trellis:probe";
					localStorage.setItem(probe, "1");
					localStorage.removeItem(probe);
					return localStorage;
				}
			} catch {}
			return memoryStorage();
		}
		/**
		* True when an automatic check is due.
		* @param {{versionCheck?: boolean, versionCheckIntervalMinutes?: number}} config
		* @param {{getItem(key: string): string | null}} storage
		* @param {number} now - epoch milliseconds.
		* @returns {boolean}
		*/
		function isCheckDue(config, storage, now) {
			if (config?.versionCheck === false) return false;
			const minutes = Number(config?.versionCheckIntervalMinutes ?? 1440);
			if (!(minutes > 0)) return false;
			const last = Number(storage.getItem("dsh-trellis:version-check:last") ?? 0);
			return !(last > 0 && now - last < minutes * 6e4);
		}
		/** Browser notification when permitted; returns whether one was shown. */
		function notifyDesktop(title, body, tag) {
			if (typeof Notification === "undefined") return false;
			if (Notification.permission !== "granted") return false;
			try {
				new Notification(title, {
					body,
					tag
				});
				return true;
			} catch {
				return false;
			}
		}
		/** Ask for notification permission when the browser still allows the prompt. */
		async function requestNotificationPermission() {
			if (typeof Notification === "undefined") return "unsupported";
			if (Notification.permission !== "default") return Notification.permission;
			try {
				return await Notification.requestPermission();
			} catch {
				return "denied";
			}
		}
		/**
		* Compare two version strings numerically; a missing or non-numeric part is 0.
		* Pre-release suffixes are ignored, which is the conservative direction for a
		* "newer release exists" hint.
		* @param {string} left
		* @param {string} right
		* @returns {number}
		*/
		function compareVersions(left, right) {
			const parse = (value) => String(value ?? "").trim().replace(/^v/i, "").split("-")[0].split(".").map((part) => Number.parseInt(part, 10)).map((part) => Number.isFinite(part) && part >= 0 ? part : 0);
			const a = parse(left);
			const b = parse(right);
			for (let index = 0; index < Math.max(a.length, b.length); index += 1) {
				const diff = (a[index] ?? 0) - (b[index] ?? 0);
				if (diff !== 0) return diff;
			}
			return 0;
		}
		/** Stable identity of a dist-tag map, used to detect any published change. */
		function tagSignature(tags) {
			return Object.entries(tags).sort(([left], [right]) => left.localeCompare(right)).map(([tag, version]) => `${tag}=${version}`).join(";");
		}
		/** One-line tag summary for the UI and notifications. */
		function tagSummary(tags) {
			return Object.entries(tags).sort(([left], [right]) => left.localeCompare(right)).map(([tag, version]) => `${tag} ${version}`).join(" · ");
		}
		/**
		* Check every configured upstream source once.
		*
		* @param {object} options
		* @param {Record<string, unknown>} options.config - settings values (draft or saved).
		* @param {typeof fetch} [options.fetchImpl] - route fetch.
		* @param {ReturnType<typeof defaultStorage>} [options.storage]
		* @param {boolean} [options.notify]
		* @param {(source: {id: string, labelKey: string}) => string} [options.labelOf]
		* @param {typeof notifyDesktop} [options.notifyImpl]
		* @param {number} [options.now]
		* @param {string} [options.localVersion] - used to flag a newer plugin release.
		* @returns {Promise<{checkedAt: number, results: Array<object>}>}
		*/
		async function runVersionCheck({ config, fetchImpl = globalThis.fetch, storage = defaultStorage(), notify = false, labelOf = (source) => source.id, notifyImpl = notifyDesktop, now = Date.now(), localVersion }) {
			const results = [];
			for (const source of SOURCES) {
				const value = String(config?.[source.field] ?? "").trim();
				if (value === "") {
					results.push({
						...source,
						value,
						ok: true,
						skipped: true
					});
					continue;
				}
				const seenKey = `${SEEN_PREFIX}${source.id}`;
				const previous = storage.getItem(seenKey);
				try {
					const payload = await requestUpstream({
						source,
						value,
						fetchImpl
					});
					if (source.kind === "npm") {
						const tags = payload.tags ?? {};
						const signature = tagSignature(tags);
						const firstSeen = previous === null;
						const isNew = !firstSeen && previous !== signature;
						storage.setItem(seenKey, signature);
						results.push({
							...source,
							value,
							url: `https://www.npmjs.com/package/${value}`,
							ok: true,
							npm: {
								name: value,
								tags
							},
							isNew,
							firstSeen
						});
						if (notify && isNew && config?.versionCheckNotify !== false) notifyImpl(`Trellis: ${labelOf(source)} 官方版本有变化`, tagSummary(tags), `dsh-trellis:${source.id}`);
						continue;
					}
					const commit = payload.commit;
					const release = payload.release ?? null;
					const errors = Array.isArray(payload.errors) ? payload.errors : [];
					if (commit === void 0 || commit === null || typeof commit.sha !== "string") {
						const detail = errors.map((entry) => entry?.message).filter((message) => typeof message === "string" && message !== "").join("; ");
						results.push({
							...source,
							value,
							ok: true,
							partial: true,
							latestRelease: release,
							errors,
							url: release?.url ?? void 0,
							error: detail || "commit feed unavailable"
						});
						continue;
					}
					const updateAvailable = release !== null && localVersion !== void 0 ? compareVersions(release.tag, localVersion) > 0 : false;
					const firstSeen = previous === null;
					const isNew = !firstSeen && previous !== commit.sha;
					storage.setItem(seenKey, commit.sha);
					results.push({
						...source,
						value,
						url: release?.url ?? commit.url,
						ok: true,
						latest: commit,
						latestRelease: release,
						updateAvailable,
						warnings: errors,
						isNew,
						firstSeen
					});
					if (notify && isNew && config?.versionCheckNotify !== false) notifyImpl(`Trellis: ${labelOf(source)} 上游有新提交`, `${commit.shortSha} ${commit.message}`.trim(), `dsh-trellis:${source.id}:${commit.sha}`);
				} catch (error) {
					results.push({
						...source,
						value,
						ok: false,
						error: error?.message ?? String(error)
					});
				}
			}
			storage.setItem(LAST_CHECK_KEY, String(now));
			return {
				checkedAt: now,
				results
			};
		}
		//#endregion
		//#region src/client/conflict-view.js
		/**
		* Pure presentation and permission-action half of the conflict banner.
		*
		* The stateful banner (`ConflictBanner.jsx`) owns fetching, dismissal, and the
		* "already notified" set; this module stays JSX-free so the four permission
		* states and the permission-request action are directly testable without a DOM.
		*
		* @module dsh-trellis/client/conflict-view
		*/
		/**
		* Which notification affordances a permission state calls for.
		* @param {string} permission - `Notification.permission` or `"unsupported"`.
		* @returns {{canRequest: boolean, blocked: boolean}}
		*/
		function conflictPermissionState(permission) {
			return {
				canRequest: permission === "default",
				blocked: permission === "denied"
			};
		}
		/**
		* Request permission from a user gesture and notify once it is granted.
		*
		* Browsers only show the permission prompt in response to a user gesture, which
		* is why this lives behind the banner button rather than in the page-load
		* effect. A denied/unsupported result changes only the banner state; it never
		* throws into React.
		*
		* @param {object} options
		* @param {Array<{id: string, name: string}>} options.conflicts
		* @param {(key: string) => string} options.t
		* @param {() => Promise<string>} [options.permissionRequest]
		* @param {(title: string, body: string, tag: string) => boolean} [options.notify]
		* @returns {Promise<string>} the resulting permission.
		*/
		async function enableConflictNotifications({ conflicts, t, permissionRequest = requestNotificationPermission, notify = notifyDesktop }) {
			const permission = await permissionRequest();
			if (permission !== "granted") return permission;
			notify(t("conflict.title"), t("conflict.body").replace("{plugins}", conflictSummary(conflicts)), "dsh-trellis:conflict");
			return permission;
		}
		/**
		* Render the banner for one permission state.
		*
		* @param {object} props
		* @param {(key: string) => string} props.t
		* @param {Array<{id: string, name: string}>} props.conflicts
		* @param {string} props.permission
		* @param {() => void} props.onEnable
		* @param {() => void} props.onDismiss
		*/
		function ConflictBannerView({ t, conflicts, permission, onEnable, onDismiss }) {
			const { canRequest, blocked } = conflictPermissionState(permission);
			return (0, react.createElement)("div", {
				className: "dsh-trellis-conflict",
				role: "alert"
			}, (0, react.createElement)("div", {
				className: "dsh-trellis-conflict-copy",
				key: "copy"
			}, (0, react.createElement)("strong", { key: "title" }, t("conflict.title")), (0, react.createElement)("span", { key: "body" }, t("conflict.body").replace("{plugins}", conflictSummary(conflicts))), blocked ? (0, react.createElement)("span", {
				key: "hint",
				className: "dsh-trellis-conflict-hint"
			}, t("conflict.notificationsBlocked")) : null), canRequest ? (0, react.createElement)("button", {
				key: "enable",
				type: "button",
				className: "dsh-trellis-button",
				onClick: onEnable
			}, t("conflict.enableNotifications")) : null, (0, react.createElement)("button", {
				key: "dismiss",
				type: "button",
				className: "dsh-trellis-button",
				onClick: onDismiss
			}, t("conflict.dismiss")));
		}
		//#endregion
		//#region src/client/ConflictBanner.jsx
		/** Desktop notifications already raised for this page, one per conflict set. */
		const notified = /* @__PURE__ */ new Set();
		function notificationPermission() {
			return typeof Notification === "undefined" ? "unsupported" : Notification.permission;
		}
		/**
		* Frame-wide banner for a competing Trellis plugin.
		*
		* A desktop notification is the primary signal the user asked for, but it only
		* exists while the browser permission is granted. The banner therefore offers
		* the permission request itself (a click is the user gesture browsers require)
		* instead of waiting for the user to find the notification setting, and stays
		* visible as the fallback when notifications are blocked or unsupported.
		*
		* @param {{t: (key: string) => string}} props
		*/
		function ConflictBanner({ t }) {
			const [conflicts, setConflicts] = (0, react.useState)([]);
			const [dismissed, setDismissed] = (0, react.useState)(false);
			const [permission, setPermission] = (0, react.useState)(notificationPermission);
			(0, react.useEffect)(() => {
				let cancelled = false;
				fetchConflicts().then((result) => {
					if (cancelled) return;
					if (result.status !== "checked" || result.conflicts.length === 0) return;
					setConflicts(result.conflicts);
					const signature = conflictSignature(result.conflicts);
					if (notified.has(signature)) return;
					notified.add(signature);
					notifyDesktop(t("conflict.title"), t("conflict.body").replace("{plugins}", conflictSummary(result.conflicts)), "dsh-trellis:conflict");
				});
				return () => {
					cancelled = true;
				};
			}, [t]);
			const enableNotifications = async () => {
				setPermission(await enableConflictNotifications({
					conflicts,
					t
				}));
			};
			if (dismissed || conflicts.length === 0) return null;
			return /* @__PURE__ */ (0, react_jsx_runtime.jsx)(ConflictBannerView, {
				t,
				conflicts,
				permission,
				onEnable: enableNotifications,
				onDismiss: () => setDismissed(true)
			});
		}
		//#endregion
		//#region src/client/form.js
		const DEFAULTS = Object.freeze({
			enabled: true,
			maxBytes: 4096,
			projectRootMarkers: Object.freeze([".trellis", ".git"]),
			skipKeyword: "no-trellis",
			pythonCmd: "",
			commandsEnabled: true,
			specInjection: true,
			subagentContext: true,
			dispatchGuard: true,
			versionCheck: true,
			versionCheckIntervalMinutes: 1440,
			versionCheckNotify: true,
			versionCheckPluginRepo: "https://github.com/SajoLuo/dsh-trellis",
			versionCheckTrellisPackage: "@mindfoldhq/trellis",
			versionCheckDshPackage: "@deepseek-ai/dsh"
		});
		const FIELD_NAMES = Object.freeze(Object.keys(DEFAULTS));
		function record(value) {
			return typeof value === "object" && value !== null && !Array.isArray(value) ? value : {};
		}
		function sameValue(left, right) {
			return JSON.stringify(left) === JSON.stringify(right);
		}
		function fallbackValue(snapshot, field) {
			const base = record(snapshot.base);
			return Object.hasOwn(base, field) ? base[field] : DEFAULTS[field];
		}
		function makeDraft(snapshot) {
			const value = record(snapshot.value);
			return Object.fromEntries(FIELD_NAMES.map((field) => [field, {
				mode: "clean",
				value: value[field] ?? DEFAULTS[field]
			}]));
		}
		function editDraft(draft, field, value) {
			return {
				...draft,
				[field]: {
					mode: "set",
					value
				}
			};
		}
		function resetDraft(snapshot, draft, field) {
			return {
				...draft,
				[field]: {
					mode: "unset",
					value: fallbackValue(snapshot, field)
				}
			};
		}
		function parseMarkers(text) {
			return [...new Set(text.split(/\r?\n/).map((entry) => entry.trim()).filter(Boolean))];
		}
		function parseDraft(draft) {
			const maxBytes = Number(String(draft.maxBytes.value).trim());
			const interval = Number(String(draft.versionCheckIntervalMinutes.value).trim());
			return {
				invalid: !Number.isInteger(maxBytes) || maxBytes < 0 || !Number.isInteger(interval) || interval < 0 || [
					"enabled",
					"commandsEnabled",
					"specInjection",
					"subagentContext",
					"dispatchGuard",
					"versionCheck",
					"versionCheckNotify"
				].some((field) => typeof draft[field].value !== "boolean"),
				value: {
					enabled: draft.enabled.value,
					maxBytes,
					projectRootMarkers: parseMarkers(Array.isArray(draft.projectRootMarkers.value) ? draft.projectRootMarkers.value.join("\n") : String(draft.projectRootMarkers.value)),
					skipKeyword: String(draft.skipKeyword.value),
					pythonCmd: String(draft.pythonCmd.value),
					commandsEnabled: draft.commandsEnabled.value,
					specInjection: draft.specInjection.value,
					subagentContext: draft.subagentContext.value,
					dispatchGuard: draft.dispatchGuard.value,
					versionCheck: draft.versionCheck.value,
					versionCheckIntervalMinutes: interval,
					versionCheckNotify: draft.versionCheckNotify.value,
					versionCheckPluginRepo: String(draft.versionCheckPluginRepo.value),
					versionCheckTrellisPackage: String(draft.versionCheckTrellisPackage.value),
					versionCheckDshPackage: String(draft.versionCheckDshPackage.value)
				}
			};
		}
		function planDraft(snapshot, draft) {
			const user = record(snapshot.user);
			const current = record(snapshot.value);
			const parsed = parseDraft(draft);
			const writes = [];
			for (const field of FIELD_NAMES) {
				const staged = draft[field];
				if (staged.mode === "clean") continue;
				if (staged.mode === "unset") {
					if (Object.hasOwn(user, field)) writes.push({
						field,
						kind: "unset"
					});
					continue;
				}
				const value = parsed.value[field];
				if (!sameValue(current[field], value)) writes.push({
					field,
					kind: "set",
					value
				});
			}
			return {
				invalid: parsed.invalid,
				writes
			};
		}
		function isOverridden(snapshot, draft, field) {
			if (draft[field].mode === "set") return true;
			if (draft[field].mode === "unset") return false;
			return Object.hasOwn(record(snapshot.user), field);
		}
		function planLanded(snapshot, writes) {
			const user = record(snapshot.user);
			return writes.every((write) => write.kind === "unset" ? !Object.hasOwn(user, write.field) : Object.hasOwn(user, write.field) && sameValue(user[write.field], write.value));
		}
		/** New hosts commit a staged form atomically against its edit-start revision. */
		async function savePlan(scope, writes, revision) {
			if (typeof scope.mutate === "function") {
				if (await scope.mutate(writes.map(({ kind, field, value }) => kind === "unset" ? {
					op: "unset",
					path: [field]
				} : {
					op: "set",
					path: [field],
					value
				}), revision) === false) return false;
			} else for (const write of writes) if ((write.kind === "unset" ? await scope.unset(write.field) : await scope.set(write.field, write.value)) === false) return false;
			return planLanded(scope.getSnapshot(), writes);
		}
		//#endregion
		//#region src/client/version.js
		/**
		* The installed plugin version, stamped at build time.
		*
		* `__DSH_TRELLIS_VERSION__` is replaced by tsdown with the package version.
		* Source-level tests and any unbundled load keep the literal fallback.
		*/
		const PLUGIN_VERSION = "0.1.7";
		//#endregion
		//#region src/client/VersionMonitor.jsx
		/**
		* Upstream version monitor rendered inside the Trellis settings page.
		*
		* Manual checks run with the page's current draft values, so a repository URL
		* can be verified before saving it. The automatic check (owned by the client
		* plugin, not this component) uses saved values.
		*
		* @param {object} props
		* @param {Record<string, unknown>} props.config - parsed draft values.
		* @param {(key: string) => string} props.t
		* @param {boolean} props.disabled
		*/
		function VersionMonitor({ config, t, disabled }) {
			const [state, setState] = (0, react.useState)({
				phase: "idle",
				result: null,
				error: null
			});
			const [permission, setPermission] = (0, react.useState)(() => typeof Notification === "undefined" ? "unsupported" : Notification.permission);
			const check = (0, react.useCallback)(async () => {
				setState((current) => current.phase === "running" ? current : {
					phase: "running",
					result: current.result,
					error: null
				});
				try {
					if (config.versionCheckNotify !== false) setPermission(await requestNotificationPermission());
					const result = await runVersionCheck({
						config,
						notify: false,
						labelOf: (source) => t(source.labelKey),
						localVersion: PLUGIN_VERSION
					});
					setState({
						phase: "done",
						result,
						error: null
					});
					if (config.versionCheckNotify !== false) {
						const changed = result.results.filter((row) => row.isNew || row.updateAvailable).length;
						notifyDesktop(t("monitor.doneTitle"), t("monitor.doneBody").replace("{count}", String(result.results.length)).replace("{changed}", String(changed)), "dsh-trellis:manual-check");
					}
				} catch (error) {
					setState({
						phase: "failed",
						result: null,
						error: error?.message ?? String(error)
					});
				}
			}, [config, t]);
			const running = state.phase === "running";
			const result = state.result;
			return /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("section", {
				className: "dsh-trellis-monitor",
				"aria-label": t("monitor.title"),
				children: [
					/* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
						className: "dsh-trellis-field-head",
						children: [/* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
							className: "dsh-trellis-label",
							children: t("monitor.title")
						}), /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", {
							className: "dsh-trellis-badge",
							children: [
								t("monitor.localVersion"),
								" ",
								PLUGIN_VERSION
							]
						})]
					}),
					/* @__PURE__ */ (0, react_jsx_runtime.jsx)("p", {
						className: "dsh-trellis-hint",
						children: t("monitor.description")
					}),
					/* @__PURE__ */ (0, react_jsx_runtime.jsx)("p", {
						className: "dsh-trellis-hint",
						children: t("monitor.localNote")
					}),
					permission === "granted" ? null : /* @__PURE__ */ (0, react_jsx_runtime.jsx)("p", {
						className: "dsh-trellis-hint",
						"data-invalid": permission === "denied" || void 0,
						children: permission === "denied" ? t("monitor.permissionDenied") : t("monitor.permissionHint")
					}),
					/* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
						className: "dsh-trellis-monitor-actions",
						children: [/* @__PURE__ */ (0, react_jsx_runtime.jsx)("button", {
							className: "dsh-trellis-button",
							type: "button",
							disabled: disabled || running,
							onClick: () => {
								check();
							},
							children: running ? t("monitor.checking") : t("monitor.checkNow")
						}), result === null ? null : /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", {
							className: "dsh-trellis-hint",
							children: [
								t("monitor.lastChecked"),
								": ",
								new Date(result.checkedAt).toLocaleString()
							]
						})]
					}),
					state.error === null ? null : /* @__PURE__ */ (0, react_jsx_runtime.jsx)("p", {
						className: "dsh-trellis-error",
						children: state.error
					}),
					result === null ? null : /* @__PURE__ */ (0, react_jsx_runtime.jsx)("ul", {
						className: "dsh-trellis-monitor-list",
						children: result.results.map((row) => /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("li", {
							className: "dsh-trellis-monitor-row",
							children: [/* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
								className: "dsh-trellis-monitor-source",
								children: t(row.labelKey)
							}), row.ok && row.npm !== void 0 ? /* @__PURE__ */ (0, react_jsx_runtime.jsxs)(react_jsx_runtime.Fragment, { children: [
								/* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
									className: "dsh-trellis-monitor-status",
									"data-new": row.isNew || void 0,
									children: row.isNew ? t("monitor.versionChanged") : row.firstSeen ? t("monitor.firstSeen") : t("monitor.upToDate")
								}),
								/* @__PURE__ */ (0, react_jsx_runtime.jsx)("a", {
									className: "dsh-trellis-monitor-link",
									href: row.url,
									target: "_blank",
									rel: "noreferrer",
									children: tagSummary(row.npm.tags)
								}),
								/* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
									className: "dsh-trellis-monitor-meta",
									children: row.npm.name
								})
							] }) : row.ok && row.partial ? /* @__PURE__ */ (0, react_jsx_runtime.jsxs)(react_jsx_runtime.Fragment, { children: [
								/* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
									className: "dsh-trellis-monitor-status",
									"data-partial": "true",
									children: t("monitor.partial")
								}),
								row.latestRelease ? /* @__PURE__ */ (0, react_jsx_runtime.jsx)("a", {
									className: "dsh-trellis-monitor-link",
									href: row.latestRelease.url,
									target: "_blank",
									rel: "noreferrer",
									children: row.latestRelease.tag
								}) : null,
								/* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", {
									className: "dsh-trellis-monitor-meta",
									children: [
										row.error,
										" · ",
										t("monitor.partialHint")
									]
								})
							] }) : row.ok && row.latest !== void 0 ? /* @__PURE__ */ (0, react_jsx_runtime.jsxs)(react_jsx_runtime.Fragment, { children: [
								/* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
									className: "dsh-trellis-monitor-status",
									"data-new": row.isNew || void 0,
									children: row.isNew ? t("monitor.newCommit") : row.firstSeen ? t("monitor.firstSeen") : t("monitor.upToDate")
								}),
								row.updateAvailable && row.latestRelease ? /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", {
									className: "dsh-trellis-monitor-status",
									"data-new": "true",
									children: [
										t("monitor.updateAvailable"),
										" ",
										row.latestRelease.tag
									]
								}) : null,
								/* @__PURE__ */ (0, react_jsx_runtime.jsx)("a", {
									className: "dsh-trellis-monitor-link",
									href: row.latest.url,
									target: "_blank",
									rel: "noreferrer",
									children: row.latest.shortSha
								}),
								/* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
									className: "dsh-trellis-monitor-meta",
									children: [row.latest.date, row.latest.message].filter(Boolean).join(" · ")
								})
							] }) : row.skipped ? /* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
								className: "dsh-trellis-monitor-status",
								children: t("monitor.disabledSource")
							}) : /* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
								className: "dsh-trellis-monitor-status",
								"data-error": "true",
								children: row.error
							})]
						}, row.id))
					})
				]
			});
		}
		//#endregion
		//#region src/client/TrellisSettingsCard.jsx
		function Reset({ visible, disabled, label, onClick }) {
			return visible ? /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", {
				className: "dsh-trellis-field-head",
				children: [/* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
					className: "dsh-trellis-badge",
					children: label.overridden
				}), /* @__PURE__ */ (0, react_jsx_runtime.jsx)("button", {
					className: "dsh-trellis-reset",
					type: "button",
					disabled,
					onClick,
					children: label.reset
				})]
			}) : null;
		}
		function TextField({ id, label, hint, value, disabled, multiline = false, invalid = false, invalidHint, onChange, onReset, overridden, t }) {
			const Control = multiline ? "textarea" : "input";
			return /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
				className: "dsh-trellis-field",
				children: [
					/* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
						className: "dsh-trellis-field-head",
						children: [/* @__PURE__ */ (0, react_jsx_runtime.jsx)("label", {
							className: "dsh-trellis-label",
							htmlFor: id,
							children: label
						}), /* @__PURE__ */ (0, react_jsx_runtime.jsx)(Reset, {
							visible: overridden,
							disabled,
							label: {
								overridden: t("overridden"),
								reset: t("reset")
							},
							onClick: onReset
						})]
					}),
					/* @__PURE__ */ (0, react_jsx_runtime.jsx)(Control, {
						id,
						className: multiline ? "dsh-trellis-textarea" : "dsh-trellis-input",
						...multiline ? {} : { type: "text" },
						value,
						disabled,
						"aria-invalid": invalid || void 0,
						onChange: (event) => onChange(event.target.value)
					}),
					/* @__PURE__ */ (0, react_jsx_runtime.jsx)("p", {
						className: "dsh-trellis-hint",
						"data-invalid": invalid,
						children: invalid ? invalidHint ?? t("maxBytesInvalid") : hint
					})
				]
			});
		}
		function BooleanField({ id, label, hint, value, disabled, onChange, onReset, overridden, t }) {
			return /* @__PURE__ */ (0, react_jsx_runtime.jsx)("div", {
				className: "dsh-trellis-field",
				children: /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
					className: "dsh-trellis-field-head",
					children: [/* @__PURE__ */ (0, react_jsx_runtime.jsxs)("label", {
						className: "dsh-trellis-switch-row",
						htmlFor: id,
						children: [/* @__PURE__ */ (0, react_jsx_runtime.jsx)("input", {
							id,
							type: "checkbox",
							checked: value,
							disabled,
							onChange: (event) => onChange(event.target.checked)
						}), /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", {
							className: "dsh-trellis-switch-copy",
							children: [/* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
								className: "dsh-trellis-label",
								children: label
							}), /* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
								className: "dsh-trellis-hint",
								children: hint
							})]
						})]
					}), /* @__PURE__ */ (0, react_jsx_runtime.jsx)(Reset, {
						visible: overridden,
						disabled,
						label: {
							overridden: t("overridden"),
							reset: t("reset")
						},
						onClick: onReset
					})]
				})
			});
		}
		function TrellisSettingsPage({ view, ...props }) {
			return view === "summary" ? props.t("description") : /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
				className: "dsh-trellis-section",
				children: [
					/* @__PURE__ */ (0, react_jsx_runtime.jsx)("h2", {
						className: "dsh-trellis-section-title",
						children: props.t("sectionTitle")
					}),
					/* @__PURE__ */ (0, react_jsx_runtime.jsx)("p", {
						className: "dsh-trellis-section-desc",
						children: props.t("description")
					}),
					/* @__PURE__ */ (0, react_jsx_runtime.jsx)(TrellisSettingsCard, {
						...props,
						presentation: "page"
					})
				]
			});
		}
		function TrellisSettingsCard({ scope, t, presentation = "card" }) {
			const subscribe = (0, react.useCallback)((listener) => scope.subscribe(listener), [scope]);
			const getSnapshot = (0, react.useCallback)(() => scope.getSnapshot(), [scope]);
			const snapshot = (0, react.useSyncExternalStore)(subscribe, getSnapshot, getSnapshot);
			const [open, setOpen] = (0, react.useState)(false);
			const [draft, setDraft] = (0, react.useState)(() => makeDraft(snapshot));
			const [revision, setRevision] = (0, react.useState)(snapshot.revision);
			const [saving, setSaving] = (0, react.useState)(false);
			const [failed, setFailed] = (0, react.useState)(false);
			const page = presentation === "page";
			const Container = page ? "section" : "li";
			const plan = (0, react.useMemo)(() => planDraft(snapshot, draft), [snapshot, draft]);
			const dirty = plan.writes.length > 0;
			(0, react.useEffect)(() => {
				if (!dirty && snapshot.status === "ready") {
					setDraft(makeDraft(snapshot));
					setRevision(snapshot.revision);
				}
			}, [dirty, snapshot]);
			if (snapshot.status !== "ready") return null;
			const disabled = !snapshot.writable || saving;
			const parsed = parseDraft(draft);
			const field = (name) => ({
				overridden: isOverridden(snapshot, draft, name),
				onReset: () => {
					setDraft((current) => resetDraft(snapshot, current, name));
					setFailed(false);
				}
			});
			const edit = (name, value) => {
				setDraft((current) => editDraft(current, name, value));
				setFailed(false);
			};
			const discard = () => {
				setDraft(makeDraft(snapshot));
				setRevision(snapshot.revision);
				setFailed(false);
			};
			const save = async () => {
				if (saving || plan.invalid || plan.writes.length === 0) return;
				setSaving(true);
				setFailed(false);
				try {
					const landed = await savePlan(scope, plan.writes, revision);
					if (landed) {
						setDraft(makeDraft(scope.getSnapshot()));
						setRevision(scope.getSnapshot().revision);
					}
					setFailed(!landed);
				} catch {
					setFailed(true);
				} finally {
					setSaving(false);
				}
			};
			return /* @__PURE__ */ (0, react_jsx_runtime.jsxs)(Container, {
				className: page ? "dsh-trellis-page" : "dsh-trellis-card",
				"data-open": page || open,
				children: [!page ? /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("button", {
					type: "button",
					className: "dsh-trellis-header",
					"aria-expanded": open,
					"aria-label": `${t(open ? "collapse" : "expand")}: ${t("title")}`,
					onClick: () => setOpen((value) => !value),
					children: [
						/* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", {
							className: "dsh-trellis-head-text",
							children: [/* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
								className: "dsh-trellis-name",
								children: t("title")
							}), /* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
								className: "dsh-trellis-description",
								children: t("description")
							})]
						}),
						dirty ? /* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
							className: "dsh-trellis-badge",
							children: t("unsaved")
						}) : null,
						/* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
							className: "dsh-trellis-chevron",
							"aria-hidden": "true",
							children: "⌄"
						})
					]
				}) : null, page || open ? /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
					className: "dsh-trellis-body",
					children: [
						!snapshot.writable ? /* @__PURE__ */ (0, react_jsx_runtime.jsx)("p", {
							className: "dsh-trellis-readonly",
							role: "status",
							children: t("readOnly")
						}) : null,
						/* @__PURE__ */ (0, react_jsx_runtime.jsx)(BooleanField, {
							id: "dsh-trellis-enabled",
							label: t("enabled"),
							hint: t("enabledHint"),
							value: Boolean(draft.enabled.value),
							disabled,
							onChange: (value) => edit("enabled", value),
							t,
							...field("enabled")
						}),
						/* @__PURE__ */ (0, react_jsx_runtime.jsx)(BooleanField, {
							id: "dsh-trellis-commands",
							label: t("commandsEnabled"),
							hint: t("commandsEnabledHint"),
							value: Boolean(draft.commandsEnabled.value),
							disabled,
							onChange: (value) => edit("commandsEnabled", value),
							t,
							...field("commandsEnabled")
						}),
						/* @__PURE__ */ (0, react_jsx_runtime.jsx)(BooleanField, {
							id: "dsh-trellis-dispatch-guard",
							label: t("dispatchGuard"),
							hint: t("dispatchGuardHint"),
							value: Boolean(draft.dispatchGuard.value),
							disabled,
							onChange: (value) => edit("dispatchGuard", value),
							t,
							...field("dispatchGuard")
						}),
						/* @__PURE__ */ (0, react_jsx_runtime.jsx)(BooleanField, {
							id: "dsh-trellis-subagent-context",
							label: t("subagentContext"),
							hint: t("subagentContextHint"),
							value: Boolean(draft.subagentContext.value),
							disabled,
							onChange: (value) => edit("subagentContext", value),
							t,
							...field("subagentContext")
						}),
						/* @__PURE__ */ (0, react_jsx_runtime.jsx)(BooleanField, {
							id: "dsh-trellis-spec-injection",
							label: t("specInjection"),
							hint: t("specInjectionHint"),
							value: Boolean(draft.specInjection.value),
							disabled,
							onChange: (value) => edit("specInjection", value),
							t,
							...field("specInjection")
						}),
						/* @__PURE__ */ (0, react_jsx_runtime.jsx)(TextField, {
							id: "dsh-trellis-max-bytes",
							label: t("maxBytes"),
							hint: t("maxBytesHint"),
							value: String(draft.maxBytes.value),
							disabled,
							invalid: parsed.invalid && (!Number.isInteger(parsed.value.maxBytes) || parsed.value.maxBytes < 0),
							onChange: (value) => edit("maxBytes", value),
							t,
							...field("maxBytes")
						}),
						/* @__PURE__ */ (0, react_jsx_runtime.jsx)(TextField, {
							id: "dsh-trellis-markers",
							label: t("projectRootMarkers"),
							hint: t("projectRootMarkersHint"),
							value: Array.isArray(draft.projectRootMarkers.value) ? draft.projectRootMarkers.value.join("\n") : String(draft.projectRootMarkers.value),
							disabled,
							multiline: true,
							onChange: (value) => edit("projectRootMarkers", value),
							t,
							...field("projectRootMarkers")
						}),
						/* @__PURE__ */ (0, react_jsx_runtime.jsx)(TextField, {
							id: "dsh-trellis-skip-keyword",
							label: t("skipKeyword"),
							hint: t("skipKeywordHint"),
							value: String(draft.skipKeyword.value),
							disabled,
							onChange: (value) => edit("skipKeyword", value),
							t,
							...field("skipKeyword")
						}),
						/* @__PURE__ */ (0, react_jsx_runtime.jsx)(TextField, {
							id: "dsh-trellis-python",
							label: t("pythonCmd"),
							hint: t("pythonCmdHint"),
							value: String(draft.pythonCmd.value),
							disabled,
							onChange: (value) => edit("pythonCmd", value),
							t,
							...field("pythonCmd")
						}),
						/* @__PURE__ */ (0, react_jsx_runtime.jsx)(BooleanField, {
							id: "dsh-trellis-version-check",
							label: t("versionCheck"),
							hint: t("versionCheckHint"),
							value: Boolean(draft.versionCheck.value),
							disabled,
							onChange: (value) => edit("versionCheck", value),
							t,
							...field("versionCheck")
						}),
						draft.versionCheck.value ? /* @__PURE__ */ (0, react_jsx_runtime.jsxs)(react_jsx_runtime.Fragment, { children: [
							/* @__PURE__ */ (0, react_jsx_runtime.jsx)(TextField, {
								id: "dsh-trellis-version-interval",
								label: t("versionCheckInterval"),
								hint: t("versionCheckIntervalHint"),
								value: String(draft.versionCheckIntervalMinutes.value),
								disabled,
								invalid: parsed.invalid && (!Number.isInteger(parsed.value.versionCheckIntervalMinutes) || parsed.value.versionCheckIntervalMinutes < 0),
								invalidHint: t("versionCheckIntervalInvalid"),
								onChange: (value) => edit("versionCheckIntervalMinutes", value),
								t,
								...field("versionCheckIntervalMinutes")
							}),
							/* @__PURE__ */ (0, react_jsx_runtime.jsx)(BooleanField, {
								id: "dsh-trellis-version-notify",
								label: t("versionCheckNotify"),
								hint: t("versionCheckNotifyHint"),
								value: Boolean(draft.versionCheckNotify.value),
								disabled,
								onChange: (value) => edit("versionCheckNotify", value),
								t,
								...field("versionCheckNotify")
							}),
							/* @__PURE__ */ (0, react_jsx_runtime.jsx)(TextField, {
								id: "dsh-trellis-plugin-repo",
								label: t("versionCheckPluginRepo"),
								hint: t("versionCheckPluginRepoHint"),
								value: String(draft.versionCheckPluginRepo.value),
								disabled,
								onChange: (value) => edit("versionCheckPluginRepo", value),
								t,
								...field("versionCheckPluginRepo")
							}),
							/* @__PURE__ */ (0, react_jsx_runtime.jsx)(TextField, {
								id: "dsh-trellis-trellis-package",
								label: t("versionCheckTrellisPackage"),
								hint: t("versionCheckPackageHint"),
								value: String(draft.versionCheckTrellisPackage.value),
								disabled,
								onChange: (value) => edit("versionCheckTrellisPackage", value),
								t,
								...field("versionCheckTrellisPackage")
							}),
							/* @__PURE__ */ (0, react_jsx_runtime.jsx)(TextField, {
								id: "dsh-trellis-dsh-package",
								label: t("versionCheckDshPackage"),
								hint: t("versionCheckPackageHint"),
								value: String(draft.versionCheckDshPackage.value),
								disabled,
								onChange: (value) => edit("versionCheckDshPackage", value),
								t,
								...field("versionCheckDshPackage")
							}),
							page ? /* @__PURE__ */ (0, react_jsx_runtime.jsx)(VersionMonitor, {
								config: parsed.value,
								t,
								disabled
							}) : null
						] }) : null,
						/* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
							className: "dsh-trellis-footer",
							children: [
								failed ? /* @__PURE__ */ (0, react_jsx_runtime.jsx)("p", {
									className: "dsh-trellis-error",
									role: "status",
									children: t("saveFailed")
								}) : null,
								/* @__PURE__ */ (0, react_jsx_runtime.jsx)("button", {
									className: "dsh-trellis-button",
									type: "button",
									disabled: !dirty || saving,
									onClick: discard,
									children: t("discard")
								}),
								/* @__PURE__ */ (0, react_jsx_runtime.jsx)("button", {
									className: "dsh-trellis-button",
									"data-primary": "true",
									type: "button",
									disabled: !snapshot.writable || plan.invalid || plan.writes.length === 0 || saving,
									onClick: () => void save(),
									children: t(saving ? "saving" : "save")
								})
							]
						})
					]
				}) : null]
			});
		}
		//#endregion
		//#region src/client/locales.js
		const zh = {
			title: "Trellis 工作流",
			description: "工作流状态面包屑、命令和 DSH 会话同步。",
			expand: "展开",
			collapse: "收起",
			unsaved: "未保存",
			readOnly: "当前设置文档为只读。",
			saveFailed: "保存未生效，草稿已保留。若配置已被其他窗口修改，请先丢弃草稿、读取新值后重新编辑。",
			discard: "放弃更改",
			save: "保存",
			saving: "保存中…",
			overridden: "已覆盖",
			reset: "恢复配置文件值",
			enabled: "启用插件",
			enabledHint: "关闭后立即卸载 Trellis 面包屑、命令、会话变量和等待工具。",
			commandsEnabled: "启用 /trellis 命令",
			commandsEnabledHint: "注册 /trellis-status、只读的 /trellis-finish 和 /trellis-doctor。",
			specInjection: "路径级 spec 注入",
			specInjectionHint: "工具触碰文件时注入匹配的 .trellis/spec；项目 .trellis/config.yaml 仍是逐项目开关。",
			subagentContext: "子代理任务上下文 push",
			subagentContextHint: "Trellis 角色子代理首个请求前注入任务产物与角色清单。",
			dispatchGuard: "派发守卫（fail-closed）",
			dispatchGuardHint: "implement/check 派发没有可读任务时拒绝；research 放行并提示确认输出位置。比 Codex 更严格。",
			maxBytes: "面包屑字节上限",
			maxBytesHint: "UTF-8 字节数；0 表示不注入工作流状态。",
			maxBytesInvalid: "请输入大于等于 0 的整数。",
			projectRootMarkers: "项目根标记",
			projectRootMarkersHint: "每行一个目录项；向上查找时任意一项命中即视为项目根。",
			skipKeyword: "单轮跳过关键词",
			skipKeywordHint: "提示词中独立出现该关键词时跳过本轮面包屑；留空可关闭。",
			pythonCmd: "Python 3 命令",
			pythonCmdHint: "留空使用平台默认候选；仅影响 /trellis 命令。",
			sectionTitle: "Trellis",
			"conflict.title": "检测到另一个 Trellis 插件",
			"conflict.body": "请只保留一个：{plugins}。两者会重复注入工作流消息并争用同一组工具和命令。",
			"conflict.enableNotifications": "启用桌面通知",
			"conflict.notificationsBlocked": "桌面通知已被浏览器拒绝；可在站点设置中重新允许。",
			"conflict.dismiss": "知道了",
			versionCheck: "版本监控",
			versionCheckHint: "在浏览器中检查本插件、Trellis、DSH 上游仓库的最新 commit。",
			versionCheckInterval: "自动检查间隔（分钟）",
			versionCheckIntervalHint: "0 表示只手动检查；默认 1440（每天一次）。",
			versionCheckIntervalInvalid: "请输入大于等于 0 的整数。",
			versionCheckNotify: "新提交时通知",
			versionCheckNotifyHint: "需要浏览器通知权限；未授权时只显示页内结果。",
			versionCheckPluginRepo: "插件上游 fork 仓库",
			versionCheckPluginRepoHint: "监控该 fork 的 commit，用于吸收其优点到本插件；支持 owner/repo 或完整 GitHub URL。",
			versionCheckTrellisPackage: "Trellis 官方 npm 包",
			versionCheckDshPackage: "DSH 官方 npm 包",
			versionCheckPackageHint: "监控该包 dist-tags 的版本变化（等同 npm view）；留空表示不监控该来源。",
			"monitor.title": "上游版本",
			"monitor.localVersion": "本地版本",
			"monitor.description": "检查由 Host 执行，只发送仓库名或包名；不发送项目内容或凭据。",
			"monitor.localNote": "本地 Trellis/DSH 版本由 /trellis-doctor 报告。",
			"monitor.doneTitle": "Trellis 版本检查完成",
			"monitor.doneBody": "已检查 {count} 个仓库，{changed} 个有更新。",
			"monitor.permissionHint": "授予通知权限后，发现新提交会弹出桌面通知。",
			"monitor.permissionDenied": "通知权限已被拒绝；检查结果仍会显示在这里，可在浏览器站点设置里重新允许。",
			"monitor.checkNow": "立即检查",
			"monitor.checking": "检查中…",
			"monitor.lastChecked": "上次检查",
			"monitor.newCommit": "有新提交",
			"monitor.firstSeen": "首次记录",
			"monitor.upToDate": "已是最新",
			"monitor.versionChanged": "官方版本有变化",
			"monitor.updateAvailable": "有新版本",
			"monitor.disabledSource": "未配置（已跳过）",
			"monitor.partial": "部分结果",
			"monitor.partialHint": "可稍后重试；上次基线未被覆盖。",
			"monitor.source.plugin": "上游 fork",
			"monitor.source.trellis": "Trellis",
			"monitor.source.dsh": "DSH"
		};
		const en = {
			title: "Trellis workflow",
			description: "Workflow breadcrumbs, commands, and DSH session synchronization.",
			expand: "Expand",
			collapse: "Collapse",
			unsaved: "Unsaved",
			readOnly: "The current settings document is read-only.",
			saveFailed: "Save failed; your draft is preserved. If another editor changed the configuration, discard the draft to load current values, then edit again.",
			discard: "Discard",
			save: "Save",
			saving: "Saving…",
			overridden: "Overridden",
			reset: "Use composed value",
			enabled: "Enable plugin",
			enabledHint: "Turning this off immediately unloads breadcrumbs, commands, session facts, and the wait tool.",
			commandsEnabled: "Enable /trellis commands",
			commandsEnabledHint: "Register /trellis-status, the read-only /trellis-finish helper, and /trellis-doctor.",
			specInjection: "Path-scoped spec injection",
			specInjectionHint: "Inject matching .trellis/spec documents when a tool touches a file; the project .trellis/config.yaml remains the per-project switch.",
			subagentContext: "Sub-agent task-context push",
			subagentContextHint: "Inject task artifacts and the role manifest before a Trellis role child's first request.",
			dispatchGuard: "Dispatch guard (fail closed)",
			dispatchGuardHint: "Refuse an implement/check dispatch with no readable task; allow research and remind it to confirm its output location. Stricter than Codex.",
			maxBytes: "Breadcrumb byte limit",
			maxBytesHint: "UTF-8 bytes; 0 disables workflow-state injection.",
			maxBytesInvalid: "Enter an integer greater than or equal to 0.",
			projectRootMarkers: "Project-root markers",
			projectRootMarkersHint: "One directory entry per line; any match identifies the root while walking upward.",
			skipKeyword: "Per-turn skip keyword",
			skipKeywordHint: "A standalone occurrence in the prompt skips this turn's breadcrumb; empty disables it.",
			pythonCmd: "Python 3 command",
			pythonCmdHint: "Empty uses platform-aware candidates; affects only /trellis commands.",
			sectionTitle: "Trellis",
			"conflict.title": "Another Trellis plugin is enabled",
			"conflict.body": "Keep only one: {plugins}. Both inject workflow messages and compete for the same tools and commands.",
			"conflict.enableNotifications": "Enable desktop notifications",
			"conflict.notificationsBlocked": "Desktop notifications are blocked; re-allow them in the browser's site settings.",
			"conflict.dismiss": "Dismiss",
			versionCheck: "Version monitoring",
			versionCheckHint: "Check the newest commit of this plugin, Trellis, and DSH upstream repositories from the browser.",
			versionCheckInterval: "Automatic check interval (minutes)",
			versionCheckIntervalHint: "0 keeps checks manual; the default is 1440 (once a day).",
			versionCheckIntervalInvalid: "Enter an integer greater than or equal to 0.",
			versionCheckNotify: "Notify on a new commit",
			versionCheckNotifyHint: "Needs browser notification permission; without it the result stays on the page.",
			versionCheckPluginRepo: "Upstream fork repository",
			versionCheckPluginRepoHint: "Watches the fork's commits so its improvements can be absorbed; accepts owner/repo or a full GitHub URL.",
			versionCheckTrellisPackage: "Trellis official npm package",
			versionCheckDshPackage: "DSH official npm package",
			versionCheckPackageHint: "Watches the package dist-tags for version changes (what npm view reports); empty disables that source.",
			"monitor.title": "Upstream versions",
			"monitor.localVersion": "Local version",
			"monitor.description": "Checks run in the Host and send only repository or package names; no project content or credentials leave the machine.",
			"monitor.localNote": "Local Trellis/DSH versions are reported by /trellis-doctor.",
			"monitor.doneTitle": "Trellis version check complete",
			"monitor.doneBody": "Checked {count} repositories; {changed} with updates.",
			"monitor.permissionHint": "Grant notification permission to receive a desktop notification when a new commit appears.",
			"monitor.permissionDenied": "Notification permission is denied; results still appear here. Re-allow it in the browser's site settings.",
			"monitor.checkNow": "Check now",
			"monitor.checking": "Checking…",
			"monitor.lastChecked": "Last checked",
			"monitor.newCommit": "New commit",
			"monitor.firstSeen": "Baseline recorded",
			"monitor.upToDate": "Up to date",
			"monitor.versionChanged": "Official version changed",
			"monitor.updateAvailable": "Newer release",
			"monitor.disabledSource": "Not configured (skipped)",
			"monitor.partial": "Partial result",
			"monitor.partialHint": "Retry later; the previous baseline was kept.",
			"monitor.source.plugin": "Upstream fork",
			"monitor.source.trellis": "Trellis",
			"monitor.source.dsh": "DSH"
		};
		//#endregion
		//#region src/client/styles.js
		const styles = String.raw`
.dsh-trellis-page{min-width:0}.dsh-trellis-page .dsh-trellis-body{border-top:0;margin:0}.dsh-trellis-page .dsh-trellis-field:first-child{padding-top:0}
.dsh-trellis-card{list-style:none;border:1px solid var(--dsw-alias-border-l2);border-radius:12px;background:var(--dsw-alias-bg-layer-3);transition:border-color .16s,background .16s}.dsh-trellis-card:hover{border-color:var(--dsw-alias-label-dimmed)}.dsh-trellis-card[data-open=true]{background:var(--dsw-alias-bg-layer-2);border-color:var(--dsw-alias-label-dimmed)}.dsh-trellis-header{width:100%;appearance:none;border:0;background:none;font:inherit;color:inherit;text-align:left;cursor:pointer;display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:12px}.dsh-trellis-header:focus-visible,.dsh-trellis-button:focus-visible,.dsh-trellis-reset:focus-visible{outline:2px solid var(--dsw-alias-brand-primary);outline-offset:1px}.dsh-trellis-head-text{flex:1;min-width:0;display:flex;flex-direction:column;gap:4px}.dsh-trellis-name{font-size:15px;font-weight:600;line-height:1.4;color:var(--dsw-alias-label-primary)}.dsh-trellis-description{font-size:13px;line-height:1.5;color:var(--dsw-alias-label-tertiary)}.dsh-trellis-chevron{flex:none;color:var(--dsw-alias-label-tertiary);font-size:14px;transition:transform .16s}.dsh-trellis-card[data-open=true] .dsh-trellis-chevron{transform:rotate(180deg)}.dsh-trellis-badge{flex:none;border-radius:999px;padding:1px 8px;font-size:11px;line-height:17px;font-weight:500;white-space:nowrap;background:var(--dsw-alias-bg-module-platform);color:var(--dsw-alias-label-secondary)}.dsh-trellis-body{border-top:1px solid var(--dsw-alias-border-l2);margin:0 16px;padding-bottom:8px}.dsh-trellis-readonly,.dsh-trellis-error{margin:12px 0 0;font-size:12px;line-height:1.5}.dsh-trellis-readonly{color:var(--dsw-alias-label-tertiary)}.dsh-trellis-error{color:var(--dsw-alias-label-error)}.dsh-trellis-field{display:flex;flex-direction:column;gap:6px;padding:12px 0}.dsh-trellis-field+.dsh-trellis-field{border-top:1px solid var(--dsw-alias-border-l2)}.dsh-trellis-field-head{display:flex;align-items:center;gap:8px}.dsh-trellis-label{flex:1;min-width:0;font-size:13px;font-weight:500;line-height:1.5;color:var(--dsw-alias-label-primary)}.dsh-trellis-reset{border:0;background:none;padding:0;font:inherit;font-size:12px;line-height:1.5;color:var(--dsw-alias-label-secondary);cursor:pointer}.dsh-trellis-input,.dsh-trellis-textarea{width:100%;box-sizing:border-box;padding:0 12px;border:1px solid var(--dsw-alias-border-l2);border-radius:8px;background:var(--dsw-alias-bg-layer-3);font:inherit;font-size:13px;line-height:1.5;color:var(--dsw-alias-label-primary)}.dsh-trellis-input{height:34px}.dsh-trellis-textarea{min-height:68px;padding-top:8px;padding-bottom:8px;resize:vertical}.dsh-trellis-input:focus-visible,.dsh-trellis-textarea:focus-visible{outline:none;border-color:var(--dsw-alias-brand-primary)}.dsh-trellis-input[aria-invalid=true]{border-color:var(--dsw-alias-label-error)}.dsh-trellis-hint{margin:0;font-size:12px;line-height:1.5;color:var(--dsw-alias-label-tertiary)}.dsh-trellis-hint[data-invalid=true]{color:var(--dsw-alias-label-error)}.dsh-trellis-switch-row{display:flex;flex:1;align-items:flex-start;gap:10px}.dsh-trellis-switch-row input{margin-top:3px;accent-color:var(--dsw-alias-brand-primary)}.dsh-trellis-switch-copy{display:flex;flex:1;min-width:0;flex-direction:column;gap:3px}.dsh-trellis-footer{display:flex;align-items:center;justify-content:flex-end;gap:8px;padding:12px 0 4px;border-top:1px solid var(--dsw-alias-border-l2)}.dsh-trellis-footer .dsh-trellis-error{flex:1;margin:0}.dsh-trellis-button{appearance:none;border:1px solid var(--dsw-alias-border-l2);border-radius:8px;padding:5px 14px;font:inherit;font-size:13px;line-height:1.5;cursor:pointer;background:none;color:var(--dsw-alias-label-secondary)}.dsh-trellis-button[data-primary=true]{border-color:transparent;background:var(--dsw-alias-label-primary);color:var(--dsw-alias-bg-layer-3)}.dsh-trellis-button:disabled,.dsh-trellis-reset:disabled,.dsh-trellis-input:disabled,.dsh-trellis-textarea:disabled{opacity:.45;cursor:default}
.dsh-trellis-monitor{display:flex;flex-direction:column;gap:8px;padding:12px 0;border-top:1px solid var(--dsw-alias-border-l2)}.dsh-trellis-monitor-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.dsh-trellis-monitor-list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}.dsh-trellis-monitor-row{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;font-size:12px;line-height:1.5;color:var(--dsw-alias-label-secondary)}.dsh-trellis-monitor-source{font-weight:500;color:var(--dsw-alias-label-primary)}.dsh-trellis-monitor-status{border-radius:999px;padding:0 8px;background:var(--dsw-alias-bg-module-platform);color:var(--dsw-alias-label-secondary)}.dsh-trellis-monitor-status[data-new=true]{background:var(--dsw-alias-brand-primary);color:var(--dsw-alias-bg-layer-3)}.dsh-trellis-monitor-status[data-error=true]{color:var(--dsw-alias-label-error)}.dsh-trellis-monitor-link{color:var(--dsw-alias-brand-primary)}.dsh-trellis-monitor-meta{color:var(--dsw-alias-label-tertiary)}
.dsh-trellis-monitor{display:flex;flex-direction:column;gap:8px;padding:12px 0;border-top:1px solid var(--dsw-alias-border-l2)}.dsh-trellis-monitor-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.dsh-trellis-monitor-list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}.dsh-trellis-monitor-row{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;font-size:12px;line-height:1.5;color:var(--dsw-alias-label-secondary)}.dsh-trellis-monitor-source{font-weight:500;color:var(--dsw-alias-label-primary)}.dsh-trellis-monitor-status{border-radius:999px;padding:0 8px;background:var(--dsw-alias-bg-module-platform);color:var(--dsw-alias-label-secondary)}.dsh-trellis-monitor-status[data-new=true]{background:var(--dsw-alias-brand-primary);color:var(--dsw-alias-bg-layer-3)}.dsh-trellis-monitor-status[data-error=true]{color:var(--dsw-alias-label-error)}.dsh-trellis-monitor-link{color:var(--dsw-alias-brand-primary)}.dsh-trellis-monitor-meta{color:var(--dsw-alias-label-tertiary)}
.dsh-trellis-section{display:flex;flex-direction:column;gap:6px;min-width:0}.dsh-trellis-section-title{margin:0;font-size:16px;font-weight:600;line-height:1.4;color:var(--dsw-alias-label-primary)}.dsh-trellis-section-desc{margin:0 0 4px;font-size:13px;line-height:1.5;color:var(--dsw-alias-label-tertiary)}
.dsh-trellis-conflict{position:fixed;right:16px;bottom:16px;z-index:9999;max-width:440px;display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border:1px solid var(--dsw-alias-label-error);border-radius:12px;background:var(--dsw-alias-bg-layer-2);box-shadow:0 8px 24px rgba(0,0,0,.18)}.dsh-trellis-conflict-copy{display:flex;flex-direction:column;gap:4px;font-size:13px;line-height:1.5;color:var(--dsw-alias-label-primary)}.dsh-trellis-conflict-hint{font-size:12px;line-height:1.5;color:var(--dsw-alias-label-tertiary)}
`;
		//#endregion
		//#region src/client/index.jsx
		const SETTINGS_NAMESPACE = "dsh-trellis";
		const LOCALE_NAMESPACE = "settings.dsh-trellis";
		const inject = ["slots", "locale"];
		/** Settings section id; the shell shows it as "Trellis" in the settings list. */
		const SECTION_ID = "trellis";
		function apply(ctx) {
			ctx.effect(() => ctx.locale.register(LOCALE_NAMESPACE, {
				zh,
				en
			}), "dsh-trellis.client.locale");
			ctx.effect(() => {
				if (document.querySelector("style[data-plugin-css=\"dsh-trellis/client\"]") !== null) return () => {};
				const tag = document.createElement("style");
				tag.dataset.plugin = "dsh-trellis";
				tag.dataset.pluginCss = "dsh-trellis/client";
				tag.textContent = styles;
				document.head.appendChild(tag);
				return () => tag.remove();
			}, "dsh-trellis.client.styles");
			const t = typeof ctx.locale.bind === "function" ? ctx.locale.bind(LOCALE_NAMESPACE) : (key) => key;
			ctx.slots.inject("shell.overlay", () => ctx.slots.register({
				name: "shell.overlay",
				id: "dsh-trellis-conflict",
				order: 20,
				locale: LOCALE_NAMESPACE
			}, ConflictBanner));
			let registered = false;
			const setup = (slotCtx, scope) => {
				if (registered) return;
				registered = true;
				registerSettingsSection(slotCtx, scope, t);
				startVersionMonitor(slotCtx, scope, t);
			};
			ctx.inject(["configForms"], (formsCtx) => {
				setup(formsCtx, formsCtx.configForms.get(SETTINGS_NAMESPACE));
			});
			ctx.inject(["settingsScope"], (legacyCtx) => {
				setup(legacyCtx, legacyCtx.settingsScope.bind({ namespace: SETTINGS_NAMESPACE }));
			});
		}
		function registerSettingsSection(ctx, scope, t) {
			ctx.slots.inject("settings.section", () => ctx.slots.register({
				name: "settings.section",
				id: SECTION_ID,
				order: 16,
				label: () => t("sectionTitle"),
				locale: LOCALE_NAMESPACE,
				inject: () => ({ scope })
			}, TrellisSettingsPage));
		}
		/**
		* Automatic upstream check while the page is open.
		*
		* The browser is the only place a desktop notification can be shown, so the
		* interval lives here rather than in the Host. It re-arms whenever saved
		* settings change; a manual check in the page is independent of it.
		*/
		function startVersionMonitor(ctx, scope, t) {
			ctx.effect(() => {
				const storage = defaultStorage();
				const configNow = () => scope?.getSnapshot?.()?.value ?? {};
				let timer;
				let disposed = false;
				let running = false;
				const tick = async () => {
					if (disposed || running) return;
					running = true;
					try {
						await runVersionCheck({
							config: configNow(),
							storage,
							notify: true,
							labelOf: (source) => t(source.labelKey),
							localVersion: PLUGIN_VERSION
						});
					} catch {} finally {
						running = false;
					}
				};
				const arm = () => {
					if (timer !== void 0) {
						clearInterval(timer);
						timer = void 0;
					}
					const value = configNow();
					if (value.versionCheck === false) return;
					const minutes = Number(value.versionCheckIntervalMinutes ?? 1440);
					if (!(minutes > 0)) return;
					if (typeof setInterval !== "function") return;
					timer = setInterval(() => {
						tick();
					}, minutes * 6e4);
					if (typeof timer?.unref === "function") timer.unref();
				};
				const unsubscribe = typeof scope?.subscribe === "function" ? scope.subscribe(() => {
					arm();
				}) : () => {};
				arm();
				if (typeof Notification !== "undefined" && isCheckDue(configNow(), storage, Date.now())) tick();
				return () => {
					disposed = true;
					if (timer !== void 0) clearInterval(timer);
					unsubscribe();
				};
			}, "dsh-trellis.client.version-monitor");
		}
		//#endregion
		exports.LOCALE_NAMESPACE = LOCALE_NAMESPACE;
		exports.SECTION_ID = SECTION_ID;
		exports.SETTINGS_NAMESPACE = SETTINGS_NAMESPACE;
		exports.apply = apply;
		exports.inject = inject;
		return module.exports;
	}
});

//# sourceMappingURL=client.js.map