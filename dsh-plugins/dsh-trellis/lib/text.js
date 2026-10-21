/**
 * Shared text helpers for model-visible payloads.
 *
 * @module dsh-trellis/text
 */

/**
 * Truncate UTF-8 text to a byte budget without splitting a code point.
 *
 * @param {string} value
 * @param {number} maxBytes - `<= 0` disables the budget.
 * @returns {string}
 */
export function truncateUtf8(value, maxBytes) {
  if (maxBytes <= 0) return value;
  const bytes = Buffer.from(value, "utf8");
  if (bytes.length <= maxBytes) return value;
  let end = Math.trunc(maxBytes);
  while (end > 0 && (bytes.readUInt8(end) & 0xc0) === 0x80) end -= 1;
  return bytes.subarray(0, end).toString("utf8");
}
