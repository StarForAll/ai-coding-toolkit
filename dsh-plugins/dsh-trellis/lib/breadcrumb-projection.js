/**
 * Breadcrumb projection: the breadcrumb family's replayable identity.
 *
 * @module dsh-trellis/breadcrumb-projection
 */
import { isBreadcrumbMessage } from "./breadcrumb.js";
import {
  createMessageProjection,
  messageFingerprint,
  registerMessageProjection,
} from "./message-projection.js";

export const BREADCRUMB_PROJECTION_KEY = "dsh-trellis.breadcrumbs";

/** Stable JSON payload identity, excluding the per-injection message id. */
export function breadcrumbFingerprint(message) {
  return messageFingerprint(message);
}

export const breadcrumbProjection = createMessageProjection({
  key: BREADCRUMB_PROJECTION_KEY,
  isOwn: isBreadcrumbMessage,
});

/** Register/read on the owning runtime scope; unload removes our key only. */
export function registerBreadcrumbProjection(ctx) {
  return registerMessageProjection(ctx, breadcrumbProjection);
}
