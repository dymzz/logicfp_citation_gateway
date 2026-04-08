# src/logicfp_credibility/benchmark_runner.py

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from logicfp_credibility.core.contracts import (
    ContextMember,
    ContextPool,
    HostP3Request,
)
from logicfp_credibility.core.gateway import reference_gateway


@dataclass(slots=True)
class CaseRunResult:
    case_id: str
    category: str
    expected_status: str
    actual_status: str
    passed: bool
    case_path: str
    error: str | None = None


def load_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def load_manifest(benchmark_dir: Path) -> dict[str, Any]:
    manifest_path = benchmark_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found: {manifest_path}")
    return load_json_file(manifest_path)


def discover_case_files(benchmark_dir: Path) -> list[Path]:
    case_files = sorted(
        p for p in benchmark_dir.rglob("*.json") if p.name != "manifest.json"
    )
    return case_files


def build_context_pool(case_data: dict[str, Any]) -> ContextPool:
    raw_pool = case_data["context_pool"]
    raw_members = raw_pool["members"]

    members = [
        ContextMember(
            member_id=item["member_id"],
            source_id=item["source_id"],
            content=item["content"],
            title=item.get("title"),
            metadata=item.get("metadata", {}),
        )
        for item in raw_members
    ]

    return ContextPool(
        pool_id=raw_pool["pool_id"],
        members=members,
        retrieval_meta=raw_pool.get("retrieval_meta", {}),
    )


def build_p3_request(case_data: dict[str, Any]) -> HostP3Request:
    context_pool = build_context_pool(case_data)

    return HostP3Request(
        request_id=case_data["case_id"],
        llm_output=case_data["llm_output"],
        context_pool=context_pool,
        decision_type=case_data.get("decision_type", "benchmark"),
        action_risk=case_data.get("action_risk", "low"),
        metadata=case_data.get("metadata"),
    )


def run_one_case(case_path: Path) -> CaseRunResult:
    case_data = load_json_file(case_path)

    case_id = str(case_data["case_id"])
    category = str(case_data["category"])
    expected_status = str(case_data["expected"]["reference_integrity_status"])

    try:
        request = build_p3_request(case_data)
        actual = reference_gateway.run(request)
        actual_status = actual.reference_integrity_status
        passed = actual_status == expected_status

        return CaseRunResult(
            case_id=case_id,
            category=category,
            expected_status=expected_status,
            actual_status=actual_status,
            passed=passed,
            case_path=str(case_path),
            error=None,
        )
    except Exception as exc:
        return CaseRunResult(
            case_id=case_id,
            category=category,
            expected_status=expected_status,
            actual_status="__runner_error__",
            passed=False,
            case_path=str(case_path),
            error=f"{type(exc).__name__}: {exc}",
        )


def summarize_results(results: list[CaseRunResult]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    by_category: dict[str, dict[str, int]] = {}
    for result in results:
        if result.category not in by_category:
            by_category[result.category] = {"total": 0, "passed": 0, "failed": 0}
        by_category[result.category]["total"] += 1
        if result.passed:
            by_category[result.category]["passed"] += 1
        else:
            by_category[result.category]["failed"] += 1

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "by_category": by_category,
    }


def print_console_summary(
    *,
    benchmark_dir: Path,
    manifest: dict[str, Any],
    results: list[CaseRunResult],
) -> None:
    summary = summarize_results(results)

    print("=" * 72)
    print("P3 Benchmark Runner")
    print("=" * 72)
    print(f"benchmark_dir     : {benchmark_dir}")
    print(f"benchmark_name    : {manifest.get('benchmark_name', '<unknown>')}")
    print(f"benchmark_version : {manifest.get('benchmark_version', '<unknown>')}")
    print("-" * 72)
    print(f"total_cases       : {summary['total']}")
    print(f"passed            : {summary['passed']}")
    print(f"failed            : {summary['failed']}")
    print("-" * 72)
    print("By Category:")
    for category in sorted(summary["by_category"].keys()):
        stats = summary["by_category"][category]
        print(
            f"  - {category}: "
            f"total={stats['total']}, "
            f"passed={stats['passed']}, "
            f"failed={stats['failed']}"
        )

    failed_cases = [r for r in results if not r.passed]
    if failed_cases:
        print("-" * 72)
        print("Failed Cases:")
        for item in failed_cases:
            print(f"* case_id         : {item.case_id}")
            print(f"  category        : {item.category}")
            print(f"  expected_status : {item.expected_status}")
            print(f"  actual_status   : {item.actual_status}")
            print(f"  case_path       : {item.case_path}")
            if item.error:
                print(f"  error           : {item.error}")
            print()

    print("=" * 72)


def validate_manifest_vs_files(
    manifest: dict[str, Any],
    case_files: list[Path],
) -> None:
    expected_total = manifest.get("total_cases")
    if isinstance(expected_total, int) and expected_total != len(case_files):
        raise ValueError(
            f"manifest total_cases={expected_total} does not match "
            f"discovered case count={len(case_files)}"
        )


def run_benchmark(benchmark_dir: Path) -> int:
    manifest = load_manifest(benchmark_dir)
    case_files = discover_case_files(benchmark_dir)
    validate_manifest_vs_files(manifest, case_files)

    results = [run_one_case(case_path) for case_path in case_files]
    print_console_summary(
        benchmark_dir=benchmark_dir,
        manifest=manifest,
        results=results,
    )

    has_failures = any(not r.passed for r in results)
    return 1 if has_failures else 0


def resolve_benchmark_dir(argv: list[str]) -> Path:
    if len(argv) >= 2:
        return Path(argv[1]).resolve()

    # 默认从当前文件位置向上找仓库，再落到 benchmarks/p3
    return (Path(__file__).resolve().parents[2] / "benchmarks" / "p3").resolve()


def main() -> int:
    benchmark_dir = resolve_benchmark_dir(sys.argv)
    return run_benchmark(benchmark_dir)


if __name__ == "__main__":
    raise SystemExit(main())
