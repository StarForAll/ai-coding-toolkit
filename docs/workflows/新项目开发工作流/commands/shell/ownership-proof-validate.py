#!/usr/bin/env python3
"""Validate source watermark and ownership-proof workflow artifacts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


VALID_LEVELS = {"none", "basic", "hybrid", "forensic"}
TRUE_VALUES = {"yes", "true", "on", "1", "是"}
WMID_PATTERN = re.compile(r"\bwm_[A-Za-z0-9_-]{4,}\b")


def print_result(ok: bool, success: str, failure: str) -> bool:
    """Print a validation result and return True for pass, False for fail."""
    if ok:
        print(f"✅ {success}")
        return True
    print(f"❌ {failure}")
    return False


def normalize_bool(value: str | None) -> bool:
    """Normalize a yes/no-like field to bool."""
    if value is None:
        return False
    return value.strip().strip("`").lower() in TRUE_VALUES


def extract_field(content: str, field_name: str) -> str | None:
    """Extract a markdown list-style field value."""
    pattern = re.compile(
        rf"(?:`)?{re.escape(field_name)}(?:`)?\s*:\s*(.+?)(?:\n|$)",
        re.IGNORECASE,
    )
    match = pattern.search(content)
    if not match:
        return None
    value = match.group(1).strip()
    value = value.strip("`").strip()
    return value or None


def parse_channels(raw: str | None) -> set[str]:
    """Parse comma-separated channels into a normalized set."""
    if not raw:
        return set()
    parts = re.split(r"[,\uFF0C/\s]+", raw.lower())
    channels = {part for part in parts if part}
    normalized = set()
    for channel in channels:
        if channel in {"visible", "可见", "可见水印", "comment", "comments"}:
            normalized.add("visible")
        elif channel in {"zero-width", "zero", "zw", "零宽", "zero_width"}:
            normalized.add("zero-width")
        elif channel in {"subtle", "subtle-marker", "subtle-markers", "marker", "markers", "隐蔽", "不起眼"}:
            normalized.add("subtle-markers")
        elif channel in {"zero-watermark", "zero-watermarks", "fingerprint", "fingerprints", "零水印", "指纹"}:
            normalized.add("zero-watermark")
        else:
            normalized.add(channel)
    return normalized


def load_assessment(task_dir: Path) -> tuple[str | None, set[str], bool, bool, bool]:
    """Load watermark settings from assessment.md."""
    assessment_file = task_dir / "assessment.md"
    if not assessment_file.exists():
        raise FileNotFoundError(f"{assessment_file} 不存在")

    content = assessment_file.read_text(encoding="utf-8")
    level = extract_field(content, "source_watermark_level")
    channels = parse_channels(extract_field(content, "source_watermark_channels"))
    zero_width_enabled = normalize_bool(extract_field(content, "zero_width_watermark_enabled"))
    subtle_enabled = normalize_bool(extract_field(content, "subtle_code_marker_enabled"))
    ownership_required = normalize_bool(extract_field(content, "ownership_proof_required"))
    return level, channels, zero_width_enabled, subtle_enabled, ownership_required


def ownership_proof_enabled(level: str | None, ownership_required: bool) -> bool:
    """Whether downstream ownership-proof checks should run.

    This gate is enabled for every non-`none` level when the project explicitly
    requires ownership proof. The concrete checks still come from
    `source_watermark_channels`, not from a separate "basic mode" code path.
    """
    if level is None:
        return False
    return level.lower() != "none" and ownership_required


def validate_non_feasibility_prerequisites(
    level: str | None,
    channels: set[str],
    ownership_required: bool,
) -> str | None:
    """Validate gating prerequisites for downstream phases."""
    if ownership_required and level is None:
        return "`ownership_proof_required = yes` 但 `source_watermark_level` 缺失，不能跳过后续阶段校验"
    if ownership_required and level.lower() not in VALID_LEVELS:
        return f"`source_watermark_level` 取值无效: {level}"
    if ownership_required and not channels:
        return "`ownership_proof_required = yes` 但 `source_watermark_channels` 为空，不能跳过后续阶段校验"
    if ownership_required and "visible" not in channels:
        return "`ownership_proof_required = yes` 时，`source_watermark_channels` 必须包含 `visible`"
    return None


def validate_feasibility(task_dir: Path) -> tuple[int, int, bool, set[str], bool, bool]:
    """Validate assessment watermark policy fields."""
    print("\n=== 验证 assessment.md (Ownership / Feasibility) ===")

    assessment_file = task_dir / "assessment.md"
    if not assessment_file.exists():
        print(f"❌ {assessment_file} 不存在")
        return 0, 1, False, set(), False, False

    content = assessment_file.read_text(encoding="utf-8")
    checks = 0
    passed = 0

    level = extract_field(content, "source_watermark_level")
    channels = parse_channels(extract_field(content, "source_watermark_channels"))
    zero_width_enabled = normalize_bool(extract_field(content, "zero_width_watermark_enabled"))
    subtle_enabled = normalize_bool(extract_field(content, "subtle_code_marker_enabled"))
    ownership_required = normalize_bool(extract_field(content, "ownership_proof_required"))

    checks += 1
    if level and level.lower() in VALID_LEVELS:
        passed += print_result(True, f"`source_watermark_level`: {level}", "")
    else:
        passed += print_result(False, "", "`source_watermark_level` 缺失或取值无效")

    checks += 1
    if channels:
        passed += print_result(True, f"`source_watermark_channels`: {', '.join(sorted(channels))}", "")
    else:
        passed += print_result(False, "", "`source_watermark_channels` 缺失或为空")

    checks += 1
    if extract_field(content, "zero_width_watermark_enabled") is not None:
        passed += print_result(True, f"`zero_width_watermark_enabled`: {zero_width_enabled}", "")
    else:
        passed += print_result(False, "", "缺少 `zero_width_watermark_enabled` 字段")

    checks += 1
    if extract_field(content, "subtle_code_marker_enabled") is not None:
        passed += print_result(True, f"`subtle_code_marker_enabled`: {subtle_enabled}", "")
    else:
        passed += print_result(False, "", "缺少 `subtle_code_marker_enabled` 字段")

    checks += 1
    if extract_field(content, "ownership_proof_required") is not None:
        passed += print_result(True, f"`ownership_proof_required`: {ownership_required}", "")
    else:
        passed += print_result(False, "", "缺少 `ownership_proof_required` 字段")

    checks += 1
    if zero_width_enabled and "zero-width" not in channels:
        passed += print_result(False, "", "已启用零宽字符水印，但 `source_watermark_channels` 未包含 `zero-width`")
    else:
        passed += print_result(True, "零宽字符水印通道配置一致", "")

    checks += 1
    if subtle_enabled and "subtle-markers" not in channels:
        passed += print_result(False, "", "已启用不起眼代码标识，但 `source_watermark_channels` 未包含 `subtle-markers`")
    else:
        passed += print_result(True, "隐蔽代码标识通道配置一致", "")

    checks += 1
    if ownership_required and (level is None or level.lower() == "none"):
        passed += print_result(False, "", "`ownership_proof_required = yes` 时，`source_watermark_level` 不能为 `none`")
    else:
        passed += print_result(True, "归属证明需求与水印等级一致", "")

    checks += 1
    if ownership_required and "visible" not in channels:
        passed += print_result(False, "", "`ownership_proof_required = yes` 时，`source_watermark_channels` 必须包含 `visible`")
    else:
        passed += print_result(True, "可见源码水印通道配置一致", "")

    enabled = ownership_proof_enabled(level, ownership_required)
    print(f"\n归属证明门禁: {'启用' if enabled else '未启用'}")
    print(f"评估阶段验证: {passed}/{checks} 通过")
    return passed, checks, enabled, channels if enabled else set(), zero_width_enabled, subtle_enabled


def find_watermark_plan(task_dir: Path) -> Path | None:
    """Locate the source watermark plan file."""
    candidates = [
        task_dir / "design" / "source-watermark-plan.md",
        task_dir / "source-watermark-plan.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def validate_design(
    task_dir: Path,
    enabled: bool,
    channels: set[str],
    zero_width_enabled: bool,
    subtle_enabled: bool,
) -> tuple[int, int]:
    """Validate design-stage watermark planning artifacts."""
    print("\n=== 验证 source-watermark-plan.md (Design 阶段) ===")
    if not enabled:
        print("ℹ️  当前项目未启用归属证明门禁，跳过 design 校验")
        return 0, 0

    plan_file = find_watermark_plan(task_dir)
    if plan_file is None:
        print("❌ 未找到 `design/source-watermark-plan.md` 或 `source-watermark-plan.md`")
        return 0, 1

    content = plan_file.read_text(encoding="utf-8")
    checks = 0
    passed = 0

    required_keywords = [
        ("wmid", "包含 `WMID` 设计载荷"),
        ("excluded", "包含 excluded paths / 排除路径"),
        ("extract", "包含 extraction / 提取说明"),
        ("verification", "包含 verification / 验证说明"),
    ]
    if zero_width_enabled or "zero-width" in channels:
        required_keywords.append(("zero-width", "包含 zero-width channel 设计"))
    if subtle_enabled or "subtle-markers" in channels:
        required_keywords.append(("subtle", "包含 subtle marker channel 设计"))
    normalized = content.lower()

    for needle, success in required_keywords:
        checks += 1
        if needle in normalized:
            passed += print_result(True, success, "")
        else:
            passed += print_result(False, "", f"`{plan_file.name}` 缺少与 `{needle}` 相关的设计说明")

    if zero_width_enabled or "zero-width" in channels:
        checks += 1
        boundary_ok = (
            ("注释" in content or "comment" in normalized)
            and ("文档字符串" in content or "docstring" in normalized)
            and ("markdown" in normalized or "markdown" in content.lower())
            and ("标识符" in content or "identifier" in normalized)
            and ("只允许" in content or "only allowed" in normalized)
            and ("禁止" in content or "不得" in content or "must not" in normalized)
        )
        if boundary_ok:
            passed += print_result(True, "零宽字符水印边界已明确（允许注释/文档字符串，禁止执行语义位置）", "")
        else:
            passed += print_result(False, "", "零宽字符水印边界说明不完整")

        checks += 1
        forbidden_allow_patterns = [
            "可以放入标识符",
            "允许放入标识符",
            "can be placed in identifiers",
            "allowed in identifiers",
            "可以放入import",
            "允许放入import",
        ]
        if any(pattern in content for pattern in forbidden_allow_patterns):
            passed += print_result(False, "", "设计文档出现了允许把零宽字符放入禁区位置的描述")
        else:
            passed += print_result(True, "零宽字符禁区描述未出现明显自相矛盾", "")

    if any(channel in channels for channel in {"zero-width", "subtle-markers", "zero-watermark"}):
        checks += 1
        if "分片" in content or "fragment" in normalized:
            passed += print_result(True, "source-watermark-plan.md 已记录分片/冗余策略", "")
        else:
            passed += print_result(False, "", "source-watermark-plan.md 缺少分片/冗余策略说明")

    checks += 1
    if WMID_PATTERN.search(content):
        passed += print_result(True, "source-watermark-plan.md 记录了符合格式的 WMID", "")
    else:
        passed += print_result(False, "", "source-watermark-plan.md 缺少符合格式的 WMID")

    print(f"\n设计阶段验证: {passed}/{checks} 通过")
    return passed, checks


def validate_task_plan(task_dir: Path, enabled: bool, zero_width_enabled: bool, subtle_enabled: bool) -> tuple[int, int]:
    """Validate task planning for watermark work items."""
    print("\n=== 验证 task_plan.md (Plan 阶段) ===")
    if not enabled:
        print("ℹ️  当前项目未启用归属证明门禁，跳过 plan 校验")
        return 0, 0

    plan_file = task_dir / "task_plan.md"
    if not plan_file.exists():
        print(f"❌ {plan_file} 不存在")
        return 0, 1

    content = plan_file.read_text(encoding="utf-8")
    checks = 0
    passed = 0

    required_tasks = [
        "可见源码水印任务",
        "水印验证任务",
        "归属证明包任务",
    ]
    if zero_width_enabled:
        required_tasks.append("零宽字符水印任务")
    if subtle_enabled:
        required_tasks.append("隐蔽代码标识任务")

    for task_name in required_tasks:
        checks += 1
        if task_name in content:
            passed += print_result(True, f"已拆分 `{task_name}`", "")
        else:
            passed += print_result(False, "", f"`task_plan.md` 缺少 `{task_name}`")

    checks += 1
    if "source-watermark-plan.md" in content:
        passed += print_result(True, "任务计划引用了 `source-watermark-plan.md`", "")
    else:
        passed += print_result(False, "", "`task_plan.md` 未引用 `source-watermark-plan.md`")

    print(f"\n计划阶段验证: {passed}/{checks} 通过")
    return passed, checks


def validate_delivery(
    task_dir: Path,
    enabled: bool,
    channels: set[str],
    zero_width_enabled: bool,
    subtle_enabled: bool,
) -> tuple[int, int]:
    """Validate delivery-stage ownership proof artifacts."""
    print("\n=== 验证 delivery/ 归属证明产物 (Delivery 阶段) ===")
    if not enabled:
        print("ℹ️  当前项目未启用归属证明门禁，跳过 delivery 校验")
        return 0, 0

    delivery_dir = task_dir / "delivery"
    if not delivery_dir.exists():
        print(f"❌ {delivery_dir} 目录不存在")
        return 0, 1

    checks = 0
    passed = 0

    required_files = [
        "ownership-proof.md",
        "source-watermark-verification.md",
        "deliverables.md",
    ]
    for filename in required_files:
        checks += 1
        if (delivery_dir / filename).exists():
            passed += print_result(True, f"存在 `{filename}`", "")
        else:
            passed += print_result(False, "", f"缺少 `{filename}`")

    ownership_file = delivery_dir / "ownership-proof.md"
    if ownership_file.exists():
        content = ownership_file.read_text(encoding="utf-8")
        lowered = content.lower()

        checks += 1
        if WMID_PATTERN.search(content):
            passed += print_result(True, "ownership-proof.md 记录了符合格式的 WMID", "")
        else:
            passed += print_result(False, "", "ownership-proof.md 缺少符合格式的 WMID")

        checks += 1
        if "sha256" in lowered or "checksum" in lowered:
            passed += print_result(True, "ownership-proof.md 记录了 checksum / SHA256", "")
        else:
            passed += print_result(False, "", "ownership-proof.md 缺少 checksum / SHA256")

        checks += 1
        if "timestamp" in lowered or "时间戳" in content:
            passed += print_result(True, "ownership-proof.md 记录了时间戳 / 存证线索", "")
        else:
            passed += print_result(False, "", "ownership-proof.md 缺少时间戳 / 存证线索")

    verification_file = delivery_dir / "source-watermark-verification.md"
    if verification_file.exists():
        content = verification_file.read_text(encoding="utf-8")
        lowered = content.lower()

        checks += 1
        if "visible" in lowered or "可见" in content:
            passed += print_result(True, "source-watermark-verification.md 覆盖了可见水印验证", "")
        else:
            passed += print_result(False, "", "source-watermark-verification.md 缺少可见水印验证")

        if zero_width_enabled:
            checks += 1
            if "zero-width" in lowered or "零宽" in content:
                passed += print_result(True, "source-watermark-verification.md 覆盖了零宽字符水印验证", "")
            else:
                passed += print_result(False, "", "source-watermark-verification.md 缺少零宽字符水印验证")

        if subtle_enabled:
            checks += 1
            if "subtle" in lowered or "隐蔽" in content or "不起眼" in content:
                passed += print_result(True, "source-watermark-verification.md 覆盖了隐蔽代码标识验证", "")
            else:
                passed += print_result(False, "", "source-watermark-verification.md 缺少隐蔽代码标识验证")

        if "zero-watermark" in channels:
            checks += 1
            if "zero-watermark" in lowered or "零水印" in content or "指纹" in content:
                passed += print_result(True, "source-watermark-verification.md 覆盖了零水印 / 指纹验证", "")
            else:
                passed += print_result(False, "", "source-watermark-verification.md 缺少零水印 / 指纹验证")

    deliverables_file = delivery_dir / "deliverables.md"
    if deliverables_file.exists():
        content = deliverables_file.read_text(encoding="utf-8")
        checks += 1
        if any(token in content for token in ["ownership-proof", "WMID", "source-watermark-verification"]):
            passed += print_result(True, "deliverables.md 已纳入归属证明交付物", "")
        else:
            passed += print_result(False, "", "deliverables.md 未列出归属证明交付物")

    checklist_file = delivery_dir / "transfer-checklist.md"
    if checklist_file.exists():
        content = checklist_file.read_text(encoding="utf-8")
        checks += 1
        if (
            any(token in content for token in ["ownership-proof", "归属证明"])
            and any(token in content for token in ["source-watermark-verification", "水印验证", "WMID"])
        ):
            passed += print_result(True, "transfer-checklist.md 已纳入归属证明与水印验证检查项", "")
        else:
            passed += print_result(False, "", "transfer-checklist.md 未同时纳入归属证明与水印验证检查项")

    print(f"\n交付阶段验证: {passed}/{checks} 通过")
    return passed, checks


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(description="验证源码水印与归属证明 workflow 产物")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--phase", choices=["feasibility", "design", "plan", "delivery"], help="验证特定阶段")
    group.add_argument("--all", action="store_true", help="验证所有阶段")
    parser.add_argument("--task-dir", required=True, help="任务目录或项目根目录")
    return parser


def main() -> int:
    """Run the requested validation mode."""
    parser = build_parser()
    args = parser.parse_args()
    task_dir = Path(args.task_dir)

    if not task_dir.exists():
        print(f"❌ 路径不存在: {task_dir}", file=sys.stderr)
        return 1

    total_passed = 0
    total_checks = 0
    enabled = False
    channels: set[str] = set()
    zero_width_enabled = False
    subtle_enabled = False

    if args.phase == "feasibility" or args.all:
        passed, checks, enabled, channels, zero_width_enabled, subtle_enabled = validate_feasibility(task_dir)
        total_passed += passed
        total_checks += checks
        if args.phase == "feasibility":
            return 0 if passed == checks else 1
    else:
        try:
            level, channels, zero_width_enabled, subtle_enabled, ownership_required = load_assessment(task_dir)
        except FileNotFoundError as exc:
            print(f"❌ {exc}", file=sys.stderr)
            return 1
        prerequisite_error = validate_non_feasibility_prerequisites(level, channels, ownership_required)
        if prerequisite_error:
            print(f"❌ {prerequisite_error}", file=sys.stderr)
            return 1
        enabled = ownership_proof_enabled(level, ownership_required)
        channels = channels if enabled else set()
    phase_map = {
        "design": lambda: validate_design(task_dir, enabled, channels, zero_width_enabled, subtle_enabled),
        "plan": lambda: validate_task_plan(task_dir, enabled, zero_width_enabled, subtle_enabled),
        "delivery": lambda: validate_delivery(task_dir, enabled, channels, zero_width_enabled, subtle_enabled),
    }

    if args.phase in phase_map:
        passed, checks = phase_map[args.phase]()
        return 0 if passed == checks else 1

    for phase_name in ("design", "plan", "delivery"):
        passed, checks = phase_map[phase_name]()
        total_passed += passed
        total_checks += checks

    print(f"\n总计: {total_passed}/{total_checks} 通过")
    return 0 if total_passed == total_checks else 1


if __name__ == "__main__":
    raise SystemExit(main())
