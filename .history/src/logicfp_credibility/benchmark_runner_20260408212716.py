# src/logicfp_credibility/benchmark_runner.py

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from logicfp_credibility.core.contracts import (
    ContextMember,
    ContextPool,
    HostP3Request,
    P3Result,
)
from logicfp_credibility.core.gateway import reference_gateway


FAILURE_PASS = "pass"
FAILURE_SOFT = "soft_fail"
FAILURE_MEDIUM = "medium_fail"
FAILURE_HARD = "hard_fail"


@dataclass(slots=True)
class CaseRunResult:
    case_id: str
    category: str
    expected_status: str
    actual_status: str
    passed: bool
    failure_level: str
    case_path: str
    diff_summary: list[str] = field(default_factory=list)
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
    return sorted(p for p in benchmark_dir.rglob("*.json") if p.name != "manifest.json")


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


def normalize_expected(case_data: dict[str, Any]) -> dict[str, Any]:
    expected = case_data["expected"]
    if not isinstance(expected, dict):
        raise ValueError("case_data['expected'] must be an object")

    return {
        "reference_integrity_status": str(expected["reference_integrity_status"]),
        "resolved_members": _normalize_str_list(expected.get("resolved_members", [])),
        "unresolved_members": _normalize_str_list(
            expected.get("unresolved_members", [])
        ),
        "outside_pool_references": _normalize_str_list(
            expected.get("outside_pool_references", [])
        ),
        "triggers": _normalize_str_list(expected.get("triggers", [])),
    }


def extract_actual(p3_result: P3Result) -> dict[str, Any]:
    return {
        "reference_integrity_status": p3_result.reference_integrity_status,
        "resolved_members": list(p3_result.resolved_members),
        "unresolved_members": list(p3_result.unresolved_members),
        "outside_pool_references": list(p3_result.outside_pool_references),
        "triggers": list(p3_result.triggers),
    }


def compare_case_result(
    *,
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> tuple[str, list[str]]:
    """
    Comparison rule:
    1) status mismatch -> hard_fail
    2) status same, but resolved/unresolved/outside_pool mismatch -> medium_fail
    3) status same, key member fields same, but triggers mismatch -> soft_fail
    4) everything aligned -> pass
    """
    diffs: list[str] = []

    if actual["reference_integrity_status"] != expected["reference_integrity_status"]:
        diffs.append(
            "reference_integrity_status mismatch: "
            f"expected={expected['reference_integrity_status']!r}, "
            f"actual={actual['reference_integrity_status']!r}"
        )
        _append_list_diff(diffs, "resolved_members", expected, actual)
        _append_list_diff(diffs, "unresolved_members", expected, actual)
        _append_list_diff(diffs, "outside_pool_references", expected, actual)
        _append_list_diff(diffs, "triggers", expected, actual)
        return FAILURE_HARD, diffs

    key_field_changed = False
    for field_name in (
        "resolved_members",
        "unresolved_members",
        "outside_pool_references",
    ):
        changed = _append_list_diff(diffs, field_name, expected, actual)
        key_field_changed = key_field_changed or changed

    if key_field_changed:
        _append_list_diff(diffs, "triggers", expected, actual)
        return FAILURE_MEDIUM, diffs

    trigger_changed = _append_list_diff(diffs, "triggers", expected, actual)
    if trigger_changed:
        return FAILURE_SOFT, diffs

    return FAILURE_PASS, diffs


def _append_list_diff(
    diffs: list[str],
    field_name: str,
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> bool:
    expected_value = list(expected.get(field_name, []))
    actual_value = list(actual.get(field_name, []))
    if expected_value != actual_value:
        diffs.append(
            f"{field_name} mismatch: expected={expected_value!r}, actual={actual_value!r}"
        )
        return True
    return False


def _normalize_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Expected list[str], got: {type(value).__name__}")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(
                f"Expected list[str], but found item type: {type(item).__name__}"
            )
        result.append(item)
    return result


def load_case_stub(case_path: Path) -> dict[str, str]:
    """
    Read only the minimum identifying fields for filtering.
    """
    data = load_json_file(case_path)
    case_id = str(data["case_id"])
    category = str(data["category"])
    return {
        "case_id": case_id,
        "category": category,
    }


def filter_case_files(
    *,
    case_files: list[Path],
    benchmark_dir: Path,
    case_selector: str | None,
    category_selector: str | None,
) -> list[Path]:
    selected = case_files

    if category_selector:
        selected_by_category: list[Path] = []
        for path in selected:
            stub = load_case_stub(path)
            if stub["category"] == category_selector:
                selected_by_category.append(path)
        selected = selected_by_category

    if case_selector:
        # 先尝试按文件路径选
        selector_path = Path(case_selector)
        path_candidates = [
            selector_path,
            benchmark_dir / selector_path,
        ]

        for candidate in path_candidates:
            if candidate.exists() and candidate.is_file():
                candidate = candidate.resolve()
                matched = [p for p in selected if p.resolve() == candidate]
                if matched:
                    selected = matched
                    break
        else:
            # 再尝试按 case_id 选
            selected_by_case_id: list[Path] = []
            for path in selected:
                stub = load_case_stub(path)
                if stub["case_id"] == case_selector:
                    selected_by_case_id.append(path)
            selected = selected_by_case_id

    return sorted(selected)


def run_one_case(case_path: Path) -> CaseRunResult:
    case_data = load_json_file(case_path)

    case_id = str(case_data["case_id"])
    category = str(case_data["category"])
    expected = normalize_expected(case_data)
    expected_status = expected["reference_integrity_status"]

    try:
        request = build_p3_request(case_data)
        p3_result = reference_gateway.run(request)
        actual = extract_actual(p3_result)

        failure_level, diff_summary = compare_case_result(
            expected=expected,
            actual=actual,
        )

        return CaseRunResult(
            case_id=case_id,
            category=category,
            expected_status=expected_status,
            actual_status=actual["reference_integrity_status"],
            passed=(failure_level == FAILURE_PASS),
            failure_level=failure_level,
            case_path=str(case_path),
            diff_summary=diff_summary,
            error=None,
        )
    except Exception as exc:
        return CaseRunResult(
            case_id=case_id,
            category=category,
            expected_status=expected_status,
            actual_status="__runner_error__",
            passed=False,
            failure_level=FAILURE_HARD,
            case_path=str(case_path),
            diff_summary=["runner_exception"],
            error=f"{type(exc).__name__}: {exc}",
        )


def summarize_results(results: list[CaseRunResult]) -> dict[str, Any]:
    summary = {
        "total": len(results),
        "pass": 0,
        "soft_fail": 0,
        "medium_fail": 0,
        "hard_fail": 0,
        "by_category": {},
    }

    for result in results:
        summary[result.failure_level] += 1

        category_stats = summary["by_category"].setdefault(
            result.category,
            {
                "total": 0,
                "pass": 0,
                "soft_fail": 0,
                "medium_fail": 0,
                "hard_fail": 0,
            },
        )
        category_stats["total"] += 1
        category_stats[result.failure_level] += 1

    return summary


def print_console_summary(
    *,
    benchmark_dir: Path,
    manifest: dict[str, Any],
    results: list[CaseRunResult],
    case_selector: str | None,
    category_selector: str | None,
) -> None:
    summary = summarize_results(results)

    print("=" * 72)
    print("P3 Benchmark Runner (Level-2 Compare)")
    print("=" * 72)
    print(f"benchmark_dir     : {benchmark_dir}")
    print(f"benchmark_name    : {manifest.get('benchmark_name', '<unknown>')}")
    print(f"benchmark_version : {manifest.get('benchmark_version', '<unknown>')}")
    if category_selector:
        print(f"category_filter   : {category_selector}")
    if case_selector:
        print(f"case_filter       : {case_selector}")
    print("-" * 72)
    print(f"total_cases       : {summary['total']}")
    print(f"pass              : {summary['pass']}")
    print(f"soft_fail         : {summary['soft_fail']}")
    print(f"medium_fail       : {summary['medium_fail']}")
    print(f"hard_fail         : {summary['hard_fail']}")
    print("-" * 72)
    print("By Category:")
    for category in sorted(summary["by_category"].keys()):
        stats = summary["by_category"][category]
        print(
            f"  - {category}: "
            f"total={stats['total']}, "
            f"pass={stats['pass']}, "
            f"soft_fail={stats['soft_fail']}, "
            f"medium_fail={stats['medium_fail']}, "
            f"hard_fail={stats['hard_fail']}"
        )

    failed_cases = [r for r in results if r.failure_level != FAILURE_PASS]
    if failed_cases:
        print("-" * 72)
        print("Non-Pass Cases:")
        for item in failed_cases:
            print(f"* case_id         : {item.case_id}")
            print(f"  category        : {item.category}")
            print(f"  failure_level   : {item.failure_level}")
            print(f"  expected_status : {item.expected_status}")
            print(f"  actual_status   : {item.actual_status}")
            print(f"  case_path       : {item.case_path}")
            if item.diff_summary:
                print("  diff_summary    :")
                for diff in item.diff_summary:
                    print(f"    - {diff}")
            if item.error:
                print(f"  error           : {item.error}")
            print()

    print("=" * 72)


def build_markdown_report(
    *,
    benchmark_dir: Path,
    manifest: dict[str, Any],
    results: list[CaseRunResult],
    case_selector: str | None,
    category_selector: str | None,
) -> str:
    summary = summarize_results(results)
    failed_cases = [r for r in results if r.failure_level != FAILURE_PASS]
    hard_fail_detected = summary["hard_fail"] > 0
    release_blocking = "yes" if hard_fail_detected else "no"

    lines: list[str] = [
        "# P3 Benchmark Report",
        "",
        f"- benchmark_dir: {benchmark_dir}",
        f"- benchmark_name: {manifest.get('benchmark_name', '<unknown>')}",
        f"- benchmark_version: {manifest.get('benchmark_version', '<unknown>')}",
        f"- runner_version: v3_case_filter_markdown_report",
    ]

    if category_selector:
        lines.append(f"- category_filter: {category_selector}")
    if case_selector:
        lines.append(f"- case_filter: {case_selector}")

    lines.extend(
        [
            "",
            "## Summary",
            f"- total_cases: {summary['total']}",
            f"- pass: {summary['pass']}",
            f"- soft_fail: {summary['soft_fail']}",
            f"- medium_fail: {summary['medium_fail']}",
            f"- hard_fail: {summary['hard_fail']}",
            "",
            "## By Category",
        ]
    )

    for category in sorted(summary["by_category"].keys()):
        stats = summary["by_category"][category]
        lines.append(
            f"- {category}: total={stats['total']}, "
            f"pass={stats['pass']}, "
            f"soft_fail={stats['soft_fail']}, "
            f"medium_fail={stats['medium_fail']}, "
            f"hard_fail={stats['hard_fail']}"
        )

    lines.append("")
    lines.append("## Failed Cases")

    if not failed_cases:
        lines.append("- none")
    else:
        for item in failed_cases:
            lines.append("")
            lines.append(f"### {item.case_id}")
            lines.append(f"- category: {item.category}")
            lines.append(f"- failure_level: {item.failure_level}")
            lines.append(f"- expected.status: {item.expected_status}")
            lines.append(f"- actual.status: {item.actual_status}")
            lines.append(f"- case_path: {item.case_path}")
            if item.diff_summary:
                lines.append("- diff_summary:")
                for diff in item.diff_summary:
                    lines.append(f"  - {diff}")
            if item.error:
                lines.append(f"- error: {item.error}")

    lines.extend(
        [
            "",
            "## Conclusion",
            f"- hard_fail_detected: {'yes' if hard_fail_detected else 'no'}",
            f"- release_blocking: {release_blocking}",
            "- notes: level-2 compare on status + key fields + triggers",
            "",
        ]
    )

    return "\n".join(lines)


def write_markdown_report(
    *,
    benchmark_dir: Path,
    manifest: dict[str, Any],
    results: list[CaseRunResult],
    report_path: Path | None,
    case_selector: str | None,
    category_selector: str | None,
) -> Path:
    if report_path is None:
        repo_root = Path(__file__).resolve().parents[2]
        reports_dir = repo_root / "benchmark_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / "p3_benchmark_report.md"
    else:
        report_path.parent.mkdir(parents=True, exist_ok=True)

    content = build_markdown_report(
        benchmark_dir=benchmark_dir,
        manifest=manifest,
        results=results,
        case_selector=case_selector,
        category_selector=category_selector,
    )
    report_path.write_text(content, encoding="utf-8")
    return report_path


def validate_manifest_vs_files(
    manifest: dict[str, Any],
    case_files: list[Path],
    *,
    is_filtered_run: bool,
) -> None:
    if is_filtered_run:
        return

    expected_total = manifest.get("total_cases")
    if isinstance(expected_total, int) and expected_total != len(case_files):
        raise ValueError(
            f"manifest total_cases={expected_total} does not match "
            f"discovered case count={len(case_files)}"
        )


def run_benchmark(
    benchmark_dir: Path,
    *,
    case_selector: str | None,
    category_selector: str | None,
    report_path: Path | None,
) -> int:
    manifest = load_manifest(benchmark_dir)
    all_case_files = discover_case_files(benchmark_dir)

    filtered_case_files = filter_case_files(
        case_files=all_case_files,
        benchmark_dir=benchmark_dir,
        case_selector=case_selector,
        category_selector=category_selector,
    )

    if not filtered_case_files:
        raise ValueError("No benchmark cases matched the given filters.")

    validate_manifest_vs_files(
        manifest,
        filtered_case_files,
        is_filtered_run=(case_selector is not None or category_selector is not None),
    )

    results = [run_one_case(case_path) for case_path in filtered_case_files]

    print_console_summary(
        benchmark_dir=benchmark_dir,
        manifest=manifest,
        results=results,
        case_selector=case_selector,
        category_selector=category_selector,
    )

    final_report_path = write_markdown_report(
        benchmark_dir=benchmark_dir,
        manifest=manifest,
        results=results,
        report_path=report_path,
        case_selector=case_selector,
        category_selector=category_selector,
    )
    print(f"markdown_report   : {final_report_path}")

    has_non_pass = any(r.failure_level != FAILURE_PASS for r in results)
    return 1 if has_non_pass else 0


def resolve_benchmark_dir(benchmark_dir_arg: str | None) -> Path:
    if benchmark_dir_arg:
        return Path(benchmark_dir_arg).resolve()
    return (Path(__file__).resolve().parents[2] / "benchmarks" / "p3").resolve()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run P3 benchmark cases.")
    parser.add_argument(
        "benchmark_dir",
        nargs="?",
        default=None,
        help="Benchmark directory path. Defaults to repo_root/benchmarks/p3",
    )
    parser.add_argument(
        "--case",
        dest="case_selector",
        default=None,
        help="Case selector: exact case_id or case file path.",
    )
    parser.add_argument(
        "--category",
        dest="category_selector",
        default=None,
        help="Run only one category, e.g. clean / partial / unresolved / outside_pool / fabricated",
    )
    parser.add_argument(
        "--report-path",
        dest="report_path",
        default=None,
        help="Optional custom markdown report output path.",
    )
    return parser.parse_args(argv[1:])


def main() -> int:
    args = parse_args(sys.argv)

    benchmark_dir = resolve_benchmark_dir(args.benchmark_dir)
    report_path = Path(args.report_path).resolve() if args.report_path else None

    return run_benchmark(
        benchmark_dir,
        case_selector=args.case_selector,
        category_selector=args.category_selector,
        report_path=report_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
