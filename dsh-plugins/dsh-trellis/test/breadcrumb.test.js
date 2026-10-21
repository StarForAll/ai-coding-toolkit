import { test } from "node:test";
import assert from "node:assert/strict";
import {
  breadcrumbMessage,
  hasSkipKeyword,
  isBreadcrumbMessage,
  SOURCE_FORM,
  SOURCE_KIND,
} from "../lib/breadcrumb.js";

test("breadcrumb message carries stable ownership metadata", () => {
  const message = breadcrumbMessage(
    {
      status: "in_progress",
      taskPath: ".trellis/tasks/demo",
      body: "Do the next step.",
      digest: "abc",
    },
    4096,
  );
  assert.equal(isBreadcrumbMessage(message), true);
  assert.deepEqual(message.source, {
    kind: SOURCE_KIND,
    form: SOURCE_FORM,
    status: "in_progress",
    task: ".trellis/tasks/demo",
    digest: "abc",
  });
});

test("skip keyword matches standalone text only", () => {
  const messages = (text) => [{ content: [{ type: "text", text }] }];
  assert.equal(
    hasSkipKeyword(messages("please no-trellis this turn"), "no-trellis"),
    true,
  );
  assert.equal(
    hasSkipKeyword(messages("prefixno-trellissuffix"), "no-trellis"),
    false,
  );
});

test("skip keyword boundaries mirror Trellis's prompt_has_skip_keyword", () => {
  const messages = (text) => [{ content: [{ type: "text", text }] }];
  // A hyphen counts as a word character: no match inside a hyphenated word.
  assert.equal(
    hasSkipKeyword(messages("foo-no-trellis this turn"), "no-trellis"),
    false,
  );
  assert.equal(hasSkipKeyword(messages("(no-trellis)"), "no-trellis"), true);
  assert.equal(hasSkipKeyword(messages("no-trellis_extra"), "no-trellis"), false);
  // Punctuation-delimited keywords still match (an ASCII \b never would).
  assert.equal(hasSkipKeyword(messages("please skip. then"), "skip."), true);
  assert.equal(hasSkipKeyword(messages("please #skip then"), "#skip"), true);
  // Unicode letters are word characters for Trellis's matcher too.
  assert.equal(hasSkipKeyword(messages("跳过abc"), "跳过"), false);
  assert.equal(hasSkipKeyword(messages("请 跳过 这次"), "跳过"), true);
  assert.equal(hasSkipKeyword(messages("anything"), ""), false);
});
