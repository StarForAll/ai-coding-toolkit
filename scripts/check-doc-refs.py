#!/usr/bin/env python3
"""W25 引用自检：每个 `§x.y` 必须带所有者前缀；`本文 ` 前缀另核本文件章节。

用法：
  scripts/check-doc-refs.py                                  # 默认查当前 wf 四稿中的三稿（机制稿由 validate-wf-design 核）
  scripts/check-doc-refs.py <文件> [<文件> ...]                # 逐个查，末尾给总数
退出码：0 干净；1 有问题（缺所有者前缀、本文引用指向不存在的章节、宽松文档的裸引用本地无此章节）。

判定（默认严格）：
  - 所有者前缀：`本文 `、`机制稿 `、`设计稿 `、`依赖说明 `、`原 `。紧邻 `§`，或与 `§` 之间
    只隔同类引用与列举分隔符（`、，,与和`、连接号 `-`/`–`/`—`、空白）时，视为该引用继承前缀。
  - 缺前缀的裸引用在严格模式下**一律报错**，即使本文件存在同号章节——否则「本应指上游文档、
    却因本文件恰好有同号章节」的引用会被静默放过（本脚本上一版的实际漏检形态）。
  - `本文 §x.y` 另核本文件章节是否真实存在；`机制稿 ` 等其他前缀不在本脚本核对范围内
    （由 validate-wf-design.py 与各自的引用约定负责）。
  - 单级 `§n`（不带点）跳过。
R2 边界：本脚本只核引用形状与可解析性，不核语义归属，也不核 markdown 链接目标是否存在。

文件模式（名单外新增文件默认严格）：
  - strict：每个 `§x.y` 必须带所有者前缀；`本文 ` 另核本文件章节。默认模式。
  - lenient-local：裸 `§x.y` 指本文件章节，核本地可解析性（沿用旧行为）。
  - lenient-cross：裸 `§x.y` 指设计稿章节（本文件没有编号章节可核），本脚本跳过，由
    validate-wf-design.py 负责。只给确实以「裸 § = 设计稿」书写且已有机检覆盖的文件。

  这份名单：
  - docs/workflows/wf-framework-design.md（lenient-local）：正文以「裸 § = 本文件」书写。
  - docs/workflows/wf-framework-design.sources.md（lenient-cross）：来源表引用设计稿章节。
  - docs/workflows/wf-framework-design.index.md（lenient-cross）：索引表每格的 § 指设计稿章节，
    由 validate-wf-design.py 校验。
  - docs/workflows/workflow-implementation.md（lenient-local）：旧模块实现计划，约定
    「Bare §x.y means this plan」，登记在 .trellis/spec/docs/workflow-implementation-constraints.md。
新增基线文件若沿用裸引用约定，必须登记到本表并写模式与理由，否则默认按严格模式报错。
"""
import re
import sys

HEADING = re.compile(r"^#{2,4} (\d+(?:\.\d+)*)")
EXEMPT_SECTIONS = ("## 附录 D", "### 9.4")
OWNER_PREFIXES = ("本文 ", "机制稿 ", "设计稿 ", "依赖说明 ", "原 ")
PREFIX_WINDOW = max(len(p) for p in OWNER_PREFIXES)
DEFAULT_PATHS = ("docs/workflows/wf-framework-implementation.md",
                 "docs/workflows/wf-framework-charter.md",
                 "docs/workflows/wf-framework-design.md")
LOCAL_OWNER = "本文 "

FILE_MODES = (
    ("docs/workflows/wf-framework-design.md", "local", "裸 § = 本文件"),
    ("docs/workflows/workflow-implementation.md", "local", "旧计划约定 bare § = this plan（见 spec/docs/workflow-implementation-constraints.md）"),
    ("docs/workflows/wf-framework-design.index.md", "cross", "索引每格的 § 指设计稿章节，由 validate-wf-design.py 校验"),
    ("docs/workflows/wf-framework-design.sources.md", "cross", "来源表引用设计稿章节，由 validate-wf-design.py 校验"),
)

ENUM_TAIL = re.compile(r"(?:§\d+(?:\.\d+)*[、，,与和\u2013\u2014\s-]*)*")


def file_mode(path: str) -> str:
    norm = path.replace("\\", "/")
    for name, mode, _ in FILE_MODES:
        if norm.endswith(name):
            return mode
    return "strict"


def owner_prefix(line: str, ref_start: int) -> str | None:
    """返回该 `§` 的所有者前缀；紧邻或仅隔列举分隔符/同类引用才算命中。"""
    head = line[:ref_start]
    for prefix in OWNER_PREFIXES:
        idx = head.rfind(prefix)
        if idx >= 0 and ENUM_TAIL.fullmatch(head[idx + len(prefix):]):
            return prefix
    return None


def check(path: str) -> list[str]:
    lines = open(path, encoding="utf-8").read().split("\n")
    heads = {m.group(1) for m in map(HEADING.match, lines) if m}
    mode = file_mode(path)
    in_exempt = False
    bad = []
    for no, line in enumerate(lines, 1):
        if line.startswith(("## ", "### ")):
            in_exempt = line.startswith(EXEMPT_SECTIONS)
        for m in re.finditer(r"§(\d+(?:\.\d+)*)", line):
            ref, start = m.group(1), m.start()
            if len(ref.split(".")) < 2:
                continue
            prefix = owner_prefix(line, start)
            if prefix == LOCAL_OWNER:
                if ref not in heads:
                    bad.append(f"{no}: §{ref} 本文无此章节")
                continue
            if prefix is not None:
                continue
            if in_exempt and line.startswith("|"):
                continue
            if mode == "strict":
                bad.append(f"{no}: §{ref} 缺所有者前缀（本文/机制稿/设计稿）")
            elif mode == "local" and ref not in heads:
                bad.append(f"{no}: §{ref} 本地无此章节")
    return bad


def main(paths: list[str]) -> int:
    total = 0
    for path in paths:
        bad = check(path)
        for item in bad:
            print(f"{path}:{item}" if len(paths) > 1 else item)
        total += len(bad)
        if len(paths) > 1:
            print(f"{path}: {len(bad)} problem(s) [{file_mode(path)}]")
    print(f"{total} problem(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or list(DEFAULT_PATHS)))
