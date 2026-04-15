#!/usr/bin/env python3
"""Scaffold and validate workflow design-directory documents."""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_FILES = ["index.md", "TAD.md", "ODD-dev.md", "ODD-user.md"]
CONDITIONAL_FILES = ["DDD.md", "IDD.md", "AID.md", "STITCH-PROMPT.md"]
STITCH_PROMPT_BASELINE_TERMS = [
    "不要通用 SaaS 模板感",
    "不要廉价渐变和无意义炫光装饰",
    "不要过度圆角、过度玻璃拟态、过度悬浮阴影",
    "不要无信息密度的卡片堆砌",
    "不要与业务无关的装饰性图形或占位文案",
    "不要“英雄区 + 三栏卖点 + 泛化插画”的通用 AI 生成组合",
]
SCAFFOLD_FILES = [
    "index.md",
    "TAD.md",
    "ODD-dev.md",
    "ODD-user.md",
    "DDD.md",
    "IDD.md",
    "AID.md",
    "STITCH-PROMPT.md",
]


def validate(design_dir: Path) -> int:
    print("=== 设计文档完整性检查 ===")

    if not design_dir.is_dir():
        print(f"❌ {design_dir}/ 目录不存在")
        return 1

    missing = 0
    for filename in REQUIRED_FILES:
        path = design_dir / filename
        if path.exists():
            print(f"✅ {filename}")
        else:
            print(f"❌ {filename} (缺失)")
            missing += 1

    for filename in CONDITIONAL_FILES:
        path = design_dir / filename
        if path.exists():
            print(f"✅ {filename} (条件文档)")
        else:
            print(f"⚠️  {filename} (条件文档，按项目是否涉及决定)")

    stitch_prompt_path = design_dir / "STITCH-PROMPT.md"
    if stitch_prompt_path.exists():
        stitch_text = stitch_prompt_path.read_text(encoding="utf-8")
        missing_terms = [term for term in STITCH_PROMPT_BASELINE_TERMS if term not in stitch_text]
        if missing_terms:
            print("❌ STITCH-PROMPT.md 缺少去 AI 味基线项：")
            for term in missing_terms:
                print(f"   - {term}")
            missing += 1
        else:
            print("✅ STITCH-PROMPT.md 去 AI 味基线项完整")

    specs_dir = design_dir / "specs"
    if specs_dir.is_dir():
        count = len(list(specs_dir.glob("*.md")))
        print(f"✅ specs/ ({count} 个模块规格)")
    else:
        print("⚠️  specs/ 目录不存在（复杂模块时补充）")

    pages_dir = design_dir / "pages"
    if pages_dir.is_dir():
        count = len(list(pages_dir.glob("*.md")))
        print(f"✅ pages/ ({count} 个页面说明)")
    else:
        print("⚠️  pages/ 目录不存在（页面复杂时补充）")

    print("ℹ️  本脚本只检查 design/ 目录内资产；README.md 与 customer-facing-prd.md / developer-facing-prd.md 需在项目主链中单独检查")
    print()

    if missing:
        print(f"❌ 缺失 {missing} 个必需文件")
        return 1

    print("✅ 设计文档完整性检查通过")
    return 0


def scaffold(design_dir: Path) -> int:
    print("=== 创建设计文档骨架 ===")
    (design_dir / "specs").mkdir(parents=True, exist_ok=True)
    (design_dir / "pages").mkdir(parents=True, exist_ok=True)

    for filename in SCAFFOLD_FILES:
        path = design_dir / filename
        if not path.exists():
            title = path.stem
            path.write_text(f"# {title}\n", encoding="utf-8")
            print(f"已创建 {path}")

    print("✅ 骨架创建完成")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="设计文档工具")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--scaffold", action="store_true")
    parser.add_argument("design_dir", nargs="?", type=Path, default=Path("./design"))
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.scaffold:
        return scaffold(args.design_dir)
    return validate(args.design_dir)


if __name__ == "__main__":
    raise SystemExit(main())
