#!/usr/bin/env python3
"""Matrix validation for workflow installation across multiple scenarios.

Usage:
    /ops/softwares/python/bin/python3 validate-matrix.py [--keep-temp] [--output PATH]
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from constants import (
    SCENARIOS,
    TEMP_DIR_PATTERN,
    MIN_DISK_SPACE,
)
from scenario_setup import setup_scenario
from validation_runner import run_validations
from report_generator import generate_report, parse_validation_output_to_findings
from runtime_bundle_manager import (
    assert_bundle_in_sync_if_repo_available,
    bundle_workflow_root,
    require_authoring_repo_root,
    workflow_version_and_schema,
)


def check_disk_space() -> bool:
    """Check if sufficient disk space available."""
    stat = shutil.disk_usage("/tmp")
    return stat.free >= MIN_DISK_SPACE


def check_trellis_available() -> bool:
    """Check if trellis command is available."""
    try:
        subprocess.run(
            ["trellis", "-v"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_trellis_version() -> str:
    """Get trellis version."""
    try:
        result = subprocess.run(
            ["trellis", "-v"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"

def create_temp_dir(scenario_name: str, timestamp: str) -> Path:
    """Create unique temp directory for a scenario."""
    temp_dir = Path(TEMP_DIR_PATTERN.format(timestamp=timestamp, scenario=scenario_name))
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def cleanup_temp_dir(temp_dir: Path) -> None:
    """Clean up temp directory."""
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


def run_scenario(
    scenario: Dict[str, Any],
    timestamp: str,
    workflow_root: Path,
    repo_root: Path,
) -> Dict[str, Any]:
    """Run validation for a single scenario."""
    scenario_name = scenario["name"]
    print(f"  Running scenario: {scenario_name}...", flush=True)

    temp_dir = create_temp_dir(scenario_name, timestamp)

    try:
        # Setup scenario
        print(f"    Setting up {scenario_name}...", flush=True)
        setup_scenario(scenario, temp_dir, workflow_root, repo_root)

        # Run validations
        print(f"    Running validations...", flush=True)
        validation_results = run_validations(
            temp_dir,
            workflow_root,
            repo_root,
            scenario,
        )

        findings = parse_validation_output_to_findings(validation_results, scenario_name)

        failed_steps = [r for r in validation_results if not r.success]

        if failed_steps:
            error_msg = "; ".join([f"{r.step}: {r.error}" for r in failed_steps])
            print(f"    ❌ Failed: {error_msg}", flush=True)
            return {
                "scenario": scenario_name,
                "description": scenario["description"],
                "status": "failed",
                "error": error_msg,
                "error_details": "\n".join([r.error for r in failed_steps]),
                "findings": findings,
                "temp_dir": str(temp_dir),
            }

        print(f"    ✅ Success: {len(findings)} findings", flush=True)
        return {
            "scenario": scenario_name,
            "description": scenario["description"],
            "status": "success",
            "findings": findings,
            "temp_dir": str(temp_dir),
        }

    except Exception as e:
        print(f"    ❌ Exception: {str(e)}", flush=True)
        return {
            "scenario": scenario_name,
            "description": scenario["description"],
            "status": "failed",
            "error": str(e),
            "error_details": str(e),
            "findings": [],
            "temp_dir": str(temp_dir),
        }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run matrix validation across multiple workflow scenarios"
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temporary directories after validation (for debugging)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./WORKFLOW_QUESTIONS.md"),
        help="Output report path (default: ./WORKFLOW_QUESTIONS.md)",
    )

    args = parser.parse_args()

    print("🔍 Workflow Matrix Validation")
    print("=" * 60)

    # Pre-flight checks
    print("\n1. Pre-flight checks...")

    try:
        repo_root = require_authoring_repo_root()
        assert_bundle_in_sync_if_repo_available(repo_root)
        workflow_root = bundle_workflow_root()
        print(f"✅ Using runtime bundle: {workflow_root}")
    except RuntimeError as e:
        print(f"❌ {e}")
        return 1

    if not check_disk_space():
        print("❌ Insufficient disk space (need at least 500MB in /tmp)")
        return 1

    if not check_trellis_available():
        print("❌ 'trellis' command not found in PATH")
        return 1

    trellis_version = get_trellis_version()
    print(f"✅ Trellis version: {trellis_version}")

    workflow_version, workflow_schema_version = workflow_version_and_schema()
    print(f"✅ Workflow version: {workflow_version}")
    print(f"✅ Workflow schema version: {workflow_schema_version}")

    # Run scenarios
    print(f"\n2. Running {len(SCENARIOS)} scenarios...")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    scenario_results = []

    for scenario in SCENARIOS:
        result = run_scenario(scenario, timestamp, workflow_root, repo_root)
        scenario_results.append(result)

    # Generate report
    print("\n3. Generating report...")
    try:
        generate_report(
            scenario_results,
            args.output,
            workflow_version=workflow_version,
            workflow_schema_version=workflow_schema_version,
            trellis_version=trellis_version,
        )
        print(f"✅ Report written to: {args.output}")
    except Exception as e:
        print(f"❌ Failed to generate report: {e}")
        return 1

    # Cleanup
    if not args.keep_temp:
        print("\n4. Cleaning up temp directories...")
        matrix_root = Path(scenario_results[0]["temp_dir"]).parent if scenario_results else None
        preserved = 0
        for result in scenario_results:
            temp_dir = Path(result["temp_dir"])
            has_findings = bool(result.get("findings"))
            if result["status"] != "success" or has_findings:
                print(f"  📁 Keeping scenario dir with findings/failure: {temp_dir}")
                preserved += 1
                continue
            try:
                cleanup_temp_dir(temp_dir)
                print(f"  ✅ Cleaned: {temp_dir}")
            except Exception as e:
                print(f"  ⚠️  Failed to clean {temp_dir}: {e}")
        if matrix_root is not None:
            matrix_root.mkdir(parents=True, exist_ok=True)
            if preserved == 0:
                print(f"  📁 Keeping matrix root for report context: {matrix_root}")
    else:
        print("\n4. Keeping temp directories (--keep-temp):")
        for result in scenario_results:
            print(f"  📁 {result['temp_dir']}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)

    successful = [r for r in scenario_results if r["status"] == "success"]
    failed = [r for r in scenario_results if r["status"] == "failed"]

    # Calculate total findings (same as report)
    total_findings = sum(len(r.get("findings", [])) for r in successful) + len(failed)

    print(f"Scenarios tested: {len(scenario_results)}")
    print(f"  ✅ Successful: {len(successful)}")
    print(f"  ❌ Failed: {len(failed)}")
    print(f"Total findings: {total_findings}")
    print(f"Report: {args.output}")

    # Determine exit code
    exit_code = 0
    if len(failed) > 0:
        print("\n⚠️  Some scenarios failed. Review the report for details.")
        print("➡️  Next: Fix critical failures, then run /workflow-repair")
        exit_code = 1
    elif total_findings > 0:
        print("\n✅ All scenarios completed successfully!")
        print("➡️  Next: Run /workflow-repair to fix the issues")
        exit_code = 0  # Findings are not failures, just issues to fix
    else:
        print("\n✅ All scenarios passed with no issues!")
        exit_code = 0

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
