#!/usr/bin/env python3
"""设计文档导出与验证。

用法:
  python3 design-export.py --validate [design_dir]    # 验证完整性
  python3 design-export.py --scaffold [design_dir]    # 创建骨架
"""
import argparse
import sys
from pathlib import Path


REQUIRED_FILES = ["index.md", "BRD.md", "TAD.md", "DDD.md", "IDD.md"]
OPTIONAL_FILES = ["AID.md", "ODD.md"]


def validate(design_dir: Path):
    print("=== 设计文档完整性检查 ===")

    if not design_dir.is_dir():
        print(f"❌ {design_dir}/ 目录不存在")
        sys.exit(1)

    missing = 0
    for f in REQUIRED_FILES:
        p = design_dir / f
        if p.exists():
            print(f"✅ {f}")
        else:
            print(f"❌ {f} (缺失)")
            missing += 1

    for f in OPTIONAL_FILES:
        p = design_dir / f
        if p.exists():
            print(f"✅ {f} (可选)")
        else:
            print(f"⚠️  {f} (可选，未创建)")

    specs_dir = design_dir / "specs"
    if specs_dir.is_dir():
        count = len(list(specs_dir.glob("*.md")))
        print(f"✅ specs/ ({count} 个模块规格)")
    else:
        print("⚠️  specs/ 目录不存在（如无前端可忽略）")

    print()
    if missing > 0:
        print(f"❌ 缺失 {missing} 个必需文件")
        sys.exit(1)
    else:
        print("✅ 设计文档完整性检查通过")


def scaffold(design_dir: Path):
    print("=== 创建设计文档骨架 ===")
    (design_dir / "specs").mkdir(parents=True, exist_ok=True)
    (design_dir / "pages").mkdir(parents=True, exist_ok=True)

    for doc in ["index", "BRD", "TAD", "DDD", "IDD", "AID", "ODD"]:
        p = design_dir / f"{doc}.md"
        if not p.exists():
            p.write_text(f"# {doc}\n", encoding="utf-8")
            print(f"已创建 {p}")

    print("✅ 骨架创建完成")


def main():
    parser = argparse.ArgumentParser(description="设计文档工具")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--scaffold", action="store_true")
    parser.add_argument("design_dir", nargs="?", type=Path, default=Path("./design"))
    args = parser.parse_args()

    if args.scaffold:
        scaffold(args.design_dir)
    else:
        validate(args.design_dir)


if __name__ == "__main__":
    main()
