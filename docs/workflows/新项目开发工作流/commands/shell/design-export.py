#!/usr/bin/env python3
"""Scaffold and validate workflow design-directory documents."""

from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path


REQUIRED_FILES = ["index.md", "TAD.md", "ODD-dev.md", "ODD-user.md"]
CONDITIONAL_FILES = ["DDD.md", "IDD.md", "AID.md", "STITCH-PROMPT.md"]
PLACEHOLDER_MARKERS = ("待补充", "待定", "暂空", "后续补充", "TBD", "TODO", "FIXME", "...")
TAD_REQUIRED_SECTIONS = [
    "## 架构冻结清单",
    "## 系统边界与外部依赖",
    "## 风险与回退",
    "## 阶段出口快照",
]
TAD_REQUIRED_FIELDS = [
    "`runtime_host`",
    "`application_stack`",
    "`persistence_strategy`",
    "`primary_processing_stack`",
    "`distribution_strategy`",
    "`remaining_unfrozen_items`",
    "`reopen_conditions`",
    "`system_boundary`",
    "`external_dependencies`",
    "`boundary_crossings`",
    "`ownership_boundaries`",
    "`fallback_assumptions`",
    "`completed_blocks`",
    "`current_status`",
    "`open_risks`",
]
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
SCAFFOLD_CONTENT = {
    "index.md": "# index\n\n- 记录 design 目录索引、文档关系与当前确认状态。\n",
    "TAD.md": """# TAD

## 架构冻结清单
- `runtime_host`: TBD
- `application_stack`: TBD
- `persistence_strategy`: TBD
- `primary_processing_stack`: TBD
- `distribution_strategy`: TBD
- `remaining_unfrozen_items`: TBD
- `reopen_conditions`: TBD

## 系统边界与外部依赖
- `system_boundary`: TBD
- `external_dependencies`: TBD
- `boundary_crossings`: TBD
- `ownership_boundaries`: TBD
- `fallback_assumptions`: TBD

## 风险与回退
- 主要风险：TBD
- 回退策略：TBD

## 阶段出口快照
- `completed_blocks`: TBD
- `current_status`: TBD
- `open_risks`: TBD
""",
    "ODD-dev.md": "# ODD-dev\n\n## 开发侧操作流\n- TBD\n",
    "ODD-user.md": "# ODD-user\n\n## 用户侧操作流\n- TBD\n",
    "DDD.md": "# DDD\n",
    "IDD.md": "# IDD\n",
    "AID.md": "# AID\n",
    "STITCH-PROMPT.md": "# STITCH-PROMPT\n",
}


def is_placeholder_like(text: str) -> bool:
    normalized = text.strip().lstrip("-").strip().strip("`*_ \t\r\n")
    if not normalized:
        return True
    lowered = normalized.lower()
    for marker in PLACEHOLDER_MARKERS:
        lowered_marker = marker.lower()
        if not lowered.startswith(lowered_marker):
            continue
        if len(lowered) == len(lowered_marker):
            return True
        next_char = normalized[len(marker)]
        if next_char.isspace():
            return True
        if unicodedata.category(next_char).startswith("P"):
            return True
    return False


def has_meaningful_body(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not is_placeholder_like(stripped):
            return True
    return False


def validate(design_dir: Path) -> int:
    print("=== 设计文档完整性检查 ===")

    if not design_dir.is_dir():
        print(f"❌ {design_dir}/ 目录不存在")
        return 1

    missing = 0
    for filename in REQUIRED_FILES:
        path = design_dir / filename
        if path.exists():
            if has_meaningful_body(path):
                print(f"✅ {filename}")
            else:
                print(f"❌ {filename} (只有标题或占位内容，未形成可审阅正文)")
                missing += 1
        else:
            print(f"❌ {filename} (缺失)")
            missing += 1

    tad_path = design_dir / "TAD.md"
    if tad_path.exists():
        tad_text = tad_path.read_text(encoding="utf-8")
        missing_sections = [section for section in TAD_REQUIRED_SECTIONS if section not in tad_text]
        if missing_sections:
            print("❌ TAD.md 缺少架构冻结/出口快照章节：")
            for section in missing_sections:
                print(f"   - {section}")
            missing += 1
        missing_fields = [field for field in TAD_REQUIRED_FIELDS if field not in tad_text]
        if missing_fields:
            print("❌ TAD.md 缺少结构化冻结字段：")
            for field in missing_fields:
                print(f"   - {field}")
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

    print(
        "ℹ️  本脚本只检查 design/ 目录内资产；README.md、正式 PRD、workflow-state.json 与用户确认点"
        " 需在项目主链中单独检查"
    )
    print(
        "ℹ️  design 正式退出仍需额外通过 workflow-state.py validate；"
        "该检查会覆盖 completed_blocks、developer-facing-prd.md、README.md 等退出门禁"
    )
    print()

    if missing:
        print(f"❌ 缺失 {missing} 个必需文件")
        return 1

    print("✅ 设计文档完整性检查通过")
    print("ℹ️  注意：这不等于 design 阶段可退出；仍需校验 workflow-state.json 并等待用户确认")
    return 0


def scaffold(design_dir: Path) -> int:
    print("=== 创建设计文档骨架 ===")
    (design_dir / "specs").mkdir(parents=True, exist_ok=True)
    (design_dir / "pages").mkdir(parents=True, exist_ok=True)

    for filename in SCAFFOLD_FILES:
        path = design_dir / filename
        if not path.exists():
            path.write_text(SCAFFOLD_CONTENT[filename], encoding="utf-8")
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
