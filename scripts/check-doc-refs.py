#!/usr/bin/env python3
"""W25 引用自检：裸 §x.y 必须命中本文件章节；指设计稿的必须带前缀。

用法：scripts/check-doc-refs.py docs/workflows/workflow-implementation.md
退出码：0 干净；1 有裸引用指向不存在的本地章节（附录 D 左列豁免）。
"""
import re
import sys

HEADING = re.compile(r"^#{2,4} (\d+(?:\.\d+)*)")
EXEMPT_SECTIONS = ("## 附录 D", "### 9.4")


def main(path: str) -> int:
    lines = open(path, encoding="utf-8").read().split("\n")
    heads = {m.group(1) for m in map(HEADING.match, lines) if m}
    in_exempt = False
    bad = []
    for no, line in enumerate(lines, 1):
        if line.startswith(("## ", "### ")):
            in_exempt = line.startswith(EXEMPT_SECTIONS)
        for m in re.finditer(r"§(\d+(?:\.\d+)*)", line):
            ref, start = m.group(1), m.start()
            if len(ref.split(".")) < 2:
                continue
            if line[max(0, start - 4):start].endswith(("设计稿 ", "依赖说明 ", "原 ")):
                continue
            if in_exempt and line.startswith("|"):
                continue
            if ref not in heads:
                bad.append(f"{no}: §{ref} 本地无此章节")
    for item in bad:
        print(item)
    print(f"{len(bad)} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "docs/workflows/workflow-implementation.md"))
