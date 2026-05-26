#!/usr/bin/env python3
"""Patch Claude inject-subagent-context.py to block embedded workflow agent dispatch."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCH_MARKER = "# [workflow-embed-patch:claude-subagent-gates]"

BLOCK_HELPER = '''
# [workflow-embed-patch:claude-subagent-gates]
BLOCKED_SUBAGENT_REASON = "current embedded workflow disables agent/subagent execution paths"


def _emit_blocked_subagent_output(subagent_type: str, original_prompt: str, tool_input: dict) -> None:
    blocked_prompt = (
        "Strong-gate blocked this subagent dispatch.\\n"
        f"Subagent: {subagent_type}\\n"
        f"Reason: {BLOCKED_SUBAGENT_REASON}\\n"
        "Required next step: return control to the main session and follow the current workflow stage entry instead of continuing inside this subagent.\\n\\n"
        "Original prompt:\\n"
        f"{original_prompt}"
    )
    updated = {**tool_input, "prompt": blocked_prompt}
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": updated,
        },
        "permission": "allow",
        "updated_input": updated,
        "updatedInput": updated,
    }
    print(json.dumps(output, ensure_ascii=False))
'''

MAIN_FUNCTION_REPLACEMENT = """def main():
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        sys.exit(0)

    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    subagent_type, original_prompt, tool_input = _parse_hook_input(input_data)

    # Only handle subagent types we care about
    if subagent_type not in AGENTS_ALL:
        sys.exit(0)

    _emit_blocked_subagent_output(subagent_type, original_prompt, tool_input)
    sys.exit(0)
"""


def _replace_main_function(content: str) -> str | None:
    start = content.find("def main():\n")
    end = content.find('\n\nif __name__ == "__main__":\n', start)
    if start == -1 or end == -1:
        return None
    current = content[start:end]
    if current == MAIN_FUNCTION_REPLACEMENT.rstrip():
        return content
    return content[:start] + MAIN_FUNCTION_REPLACEMENT.rstrip() + content[end:]


def patch_claude_inject_subagent_context(target_path: Path) -> bool:
    if not target_path.is_file():
        print(f"⚠️ {target_path} 不存在，跳过")
        return False

    content = target_path.read_text(encoding="utf-8")
    patched = content

    if PATCH_MARKER not in patched:
        anchor = "AGENTS_ALL = (AGENT_IMPLEMENT, AGENT_CHECK, AGENT_RESEARCH)\n"
        if anchor not in patched:
            print(f"⚠️ {target_path} 中未找到 AGENTS_ALL anchor，跳过")
            return False
        patched = patched.replace(anchor, anchor + BLOCK_HELPER + "\n", 1)

    replaced_main = _replace_main_function(patched)
    if replaced_main is None:
        print(f"⚠️ {target_path} 中未找到 main() 边界，跳过")
        return False
    patched = replaced_main

    if patched == content:
        print(f"✅ {target_path} 已包含 Claude strong-gate subagent patch，跳过")
        return True

    target_path.write_text(patched, encoding="utf-8")
    print(f"✅ 已为 {target_path} 应用 Claude strong-gate subagent patch")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply the Claude strong-gate subagent patch to inject-subagent-context.py."
    )
    parser.add_argument("target_path", help="Path to the target inject-subagent-context.py file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target_path = Path(args.target_path).resolve()
    return 0 if patch_claude_inject_subagent_context(target_path) else 1


if __name__ == "__main__":
    raise SystemExit(main())
