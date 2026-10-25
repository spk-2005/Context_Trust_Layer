"""
Smart Test Router for Context Layer AI.

Inspects git changes and runs the minimal sufficient test lane for immediate feedback:
- Fast Lane (< 5s): Golden micro-fixtures on extractor/normalizer changes.
- Integration Lane (< 30s): Unit and component suites on core backend changes.
- Ingestion Lane (< 15s): Fast benchmark slice (DOC-005, DOC-009) on parser changes.
- Certification Lane: Full corpus evaluation and lifecycle provenance barriers on manifest/release changes.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Set

ROOT_DIR = Path(__file__).resolve().parent.parent
PYTEST_BIN = ROOT_DIR / "backend" / ".venv" / "Scripts" / "pytest.exe"
PYTHON_BIN = ROOT_DIR / "backend" / ".venv" / "Scripts" / "python.exe"


def get_changed_files() -> List[str]:
    """Inspects git status to get modified, staged, and untracked files."""
    try:
        # Check diff against HEAD
        res_diff = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            check=True,
        )
        changed = set(line.strip() for line in res_diff.stdout.splitlines() if line.strip())

        # Check untracked files
        res_untracked = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            check=True,
        )
        for line in res_untracked.stdout.splitlines():
            line = line.strip()
            if line:
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    changed.add(parts[1])

        return sorted(list(changed))
    except Exception as e:
        print(f"[WARN] Failed to query git status: {e}. Defaulting to full test suite.")
        return []


def determine_lanes(changed_files: List[str]) -> Set[str]:
    """Maps changed files to required testing lanes."""
    if not changed_files:
        return {"fast"}

    lanes: Set[str] = set()

    for path_str in changed_files:
        p = path_str.replace("\\", "/")

        # Manifest, gold labels, or lifecycle guard require full certification
        if (
            "corpus_manifest.json" in p
            or "gold_labels" in p
            or "lifecycle_provenance_guard" in p
            or "holdout" in p
        ):
            lanes.add("certify")
            continue

        # Ingestion or parser changes require fast benchmark verification
        if "backend/app/ingestion" in p:
            lanes.add("fast")
            lanes.add("benchmark_fast")
            continue

        # Extraction and normalization changes require golden micro-fixtures
        if (
            "backend/app/extraction" in p
            or "backend/app/normalization" in p
            or "golden_micro" in p
        ):
            lanes.add("fast")
            continue

        # Backend core logic (db, api, models, gate)
        if "backend/app/" in p or "backend/tests/" in p:
            lanes.add("unit")
            continue

        # Fallback for other changes
        lanes.add("fast")

    return lanes if lanes else {"fast"}


def run_command(cmd: List[str], desc: str) -> int:
    """Executes a command and reports elapsed time."""
    print(f"\n>>> Running: {desc}")
    print(f"    Command: {' '.join(cmd)}")
    start = time.perf_counter()
    ret = subprocess.run(cmd, cwd=str(ROOT_DIR))
    elapsed = time.perf_counter() - start
    status = "SUCCESS" if ret.returncode == 0 else "FAILED"
    print(f"<<< {desc} finished in {elapsed:.2f}s [{status}]")
    return ret.returncode


def main():
    parser = argparse.ArgumentParser(description="Context Layer AI Smart Test Router")
    parser.add_argument("--fast", action="store_true", help="Force fast developer lane (< 5s)")
    parser.add_argument("--unit", action="store_true", help="Run backend unit tests")
    parser.add_argument("--benchmark", action="store_true", help="Run fast benchmark slice")
    parser.add_argument("--certify", action="store_true", help="Run full certification lane")
    parser.add_argument("--all", action="store_true", help="Run all test lanes")
    parser.add_argument("--dry-run", action="store_true", help="Print selected lanes without running")

    args = parser.parse_args()

    # Determine lanes to run
    if args.all:
        selected_lanes = {"fast", "unit", "certify"}
    elif args.certify:
        selected_lanes = {"certify"}
    elif args.unit:
        selected_lanes = {"unit"}
    elif args.benchmark:
        selected_lanes = {"benchmark_fast"}
    elif args.fast:
        selected_lanes = {"fast"}
    else:
        changed = get_changed_files()
        print(f"Git detected {len(changed)} changed file(s):")
        for f in changed[:8]:
            print(f"  - {f}")
        if len(changed) > 8:
            print(f"  ... and {len(changed) - 8} more.")
        selected_lanes = determine_lanes(changed)

    print(f"\nActive Test Lane(s): {', '.join(sorted(selected_lanes))}")

    if args.dry_run:
        print("[Dry Run] Exiting without running tests.")
        sys.exit(0)

    total_start = time.perf_counter()
    exit_code = 0

    # Execute lanes
    if "fast" in selected_lanes:
        cmd = [str(PYTEST_BIN), "-m", "fast", "-q"]
        code = run_command(cmd, "Fast Developer Lane (Micro-Fixtures)")
        if code != 0:
            sys.exit(code)

    if "benchmark_fast" in selected_lanes:
        cmd = [
            str(PYTHON_BIN),
            "research/evaluation/benchmark_harness.py",
            "--profile",
            "fast",
        ]
        code = run_command(cmd, "Ingestion Fast Benchmark Slice (DOC-005, DOC-009)")
        if code != 0:
            sys.exit(code)

    if "unit" in selected_lanes:
        cmd = [str(PYTEST_BIN), "backend/tests/unit/", "-q"]
        code = run_command(cmd, "Backend Unit Test Lane")
        if code != 0:
            sys.exit(code)

    if "certify" in selected_lanes:
        cmd = [
            str(PYTHON_BIN),
            "research/evaluation/benchmark_harness.py",
            "--profile",
            "certify",
        ]
        code = run_command(cmd, "Full Certification Lane")
        if code != 0:
            sys.exit(code)

    total_elapsed = time.perf_counter() - total_start
    print(f"\nAll selected test lanes completed successfully in {total_elapsed:.2f}s!")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()