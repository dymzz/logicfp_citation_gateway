# src/logicfp_credibility/core/merge.py

from __future__ import annotations

from typing import Any

from .constants import (
    ERR_REFERENCE_FABRICATED,
    ERR_REFERENCE_OUTSIDE_CONTEXT_POOL,
    ERR_REFERENCE_UNRESOLVED,
    REASON_P2_SEMANTIC_UNSUPPORTED,
    REASON_P3_HARD_FAIL_FABRICATED,
    REASON_P3_HARD_FAIL_OUTSIDE_POOL,
    REASON_P3_REFERENCE_PARTIAL,
    REASON_P3_REFERENCE_UNRESOLVED,
    STATUS_CLEAN,
    STATUS_FABRICATED,
    STATUS_OUTSIDE_POOL,
    STATUS_PARTIAL,
    STATUS_UNRESOLVED,
    TRIGGER_CITATION_OUTSIDE_CONTEXT_POOL,
    TRIGGER_FABRICATED_REFERENCE_DETECTED,
    VERDICT_ALLOW,
    VERDICT_BLOCK,
    VERDICT_FALLBACK,
    VERDICT_WARN,
    severity_for_status,
)
from .contracts import DecisionResult, P3Result


def merge_p2_p3_to_decision(
    *,
    p2_result: Any,
    p3_result: P3Result,
) -> DecisionResult:
    """
    Merge P2Result and P3Result into a unified DecisionResult.

    Frozen minimal merge rule:
    - P3 > P2
    - outside_pool -> block
    - fabricated -> block
    - unresolved -> warn
    - partial -> warn
    - clean -> defer to P2

    Notes:
    - This function intentionally follows the current *minimal* frozen matrix.
    - It does not yet encode older draft extensions such as action_risk-sensitive
      overrides for unresolved/partial paths.
    """
    if not isinstance(p3_result, P3Result):
        raise TypeError("p3_result must be a P3Result.")

    p2_status = _extract_p2_status(p2_result)
    p3_status = p3_result.reference_integrity_status

    # ------------------------------------------------------------
    # P3 hard fail paths
    # ------------------------------------------------------------
    if p3_status == STATUS_OUTSIDE_POOL:
        return DecisionResult(
            verdict=VERDICT_BLOCK,
            trigger_codes=_coalesce_trigger_codes(
                p3_result.triggers,
                default=[TRIGGER_CITATION_OUTSIDE_CONTEXT_POOL],
            ),
            reason_codes=[REASON_P3_HARD_FAIL_OUTSIDE_POOL],
            error_codes=[ERR_REFERENCE_OUTSIDE_CONTEXT_POOL],
            p2_status=p2_status,
            p3_status=p3_status,
            severity=severity_for_status(p3_status),
            allow_primary=False,
            allow_fallback=False,
            audit_meta=_build_audit_meta(p2_result=p2_result, p3_result=p3_result),
        )

    if p3_status == STATUS_FABRICATED:
        return DecisionResult(
            verdict=VERDICT_BLOCK,
            trigger_codes=_coalesce_trigger_codes(
                p3_result.triggers,
                default=[TRIGGER_FABRICATED_REFERENCE_DETECTED],
            ),
            reason_codes=[REASON_P3_HARD_FAIL_FABRICATED],
            error_codes=[ERR_REFERENCE_FABRICATED],
            p2_status=p2_status,
            p3_status=p3_status,
            severity=severity_for_status(p3_status),
            allow_primary=False,
            allow_fallback=False,
            audit_meta=_build_audit_meta(p2_result=p2_result, p3_result=p3_result),
        )

    # ------------------------------------------------------------
    # P3 warn paths
    # ------------------------------------------------------------
    if p3_status == STATUS_UNRESOLVED:
        return DecisionResult(
            verdict=VERDICT_WARN,
            trigger_codes=list(p3_result.triggers),
            reason_codes=[REASON_P3_REFERENCE_UNRESOLVED],
            error_codes=[ERR_REFERENCE_UNRESOLVED],
            p2_status=p2_status,
            p3_status=p3_status,
            severity=severity_for_status(p3_status),
            allow_primary=True,
            allow_fallback=False,
            audit_meta=_build_audit_meta(p2_result=p2_result, p3_result=p3_result),
        )

    if p3_status == STATUS_PARTIAL:
        return DecisionResult(
            verdict=VERDICT_WARN,
            trigger_codes=list(p3_result.triggers),
            reason_codes=[REASON_P3_REFERENCE_PARTIAL],
            error_codes=[],
            p2_status=p2_status,
            p3_status=p3_status,
            severity=severity_for_status(p3_status),
            allow_primary=True,
            allow_fallback=False,
            audit_meta=_build_audit_meta(p2_result=p2_result, p3_result=p3_result),
        )

    # ------------------------------------------------------------
    # P3 clean -> defer to P2
    # ------------------------------------------------------------
    if p3_status == STATUS_CLEAN:
        return _use_p2_result_as_final_decision(
            p2_result=p2_result,
            p2_status=p2_status,
            p3_result=p3_result,
        )

    raise ValueError(f"Unsupported P3 status: {p3_status!r}")


def _use_p2_result_as_final_decision(
    *,
    p2_result: Any,
    p2_status: str | None,
    p3_result: P3Result,
) -> DecisionResult:
    """
    Apply the frozen minimal clean-path policy:

    - P2 = supported        -> allow
    - P2 = partial / weak   -> warn
    - P2 = unsupported      -> fallback
    - P2 missing / unknown  -> warn (conservative inference)
    """
    p3_status = p3_result.reference_integrity_status
    normalized = _normalize_p2_status(p2_status)

    if normalized == "supported":
        return DecisionResult(
            verdict=VERDICT_ALLOW,
            trigger_codes=[],
            reason_codes=[],
            error_codes=[],
            p2_status=p2_status,
            p3_status=p3_status,
            severity=severity_for_status(p3_status),
            allow_primary=True,
            allow_fallback=False,
            audit_meta=_build_audit_meta(p2_result=p2_result, p3_result=p3_result),
        )

    if normalized in {"partial", "weak"}:
        return DecisionResult(
            verdict=VERDICT_WARN,
            trigger_codes=[],
            reason_codes=["p2_semantic_partial_or_weak"],
            error_codes=[],
            p2_status=p2_status,
            p3_status=p3_status,
            severity="medium",
            allow_primary=True,
            allow_fallback=False,
            audit_meta=_build_audit_meta(p2_result=p2_result, p3_result=p3_result),
        )

    if normalized == "unsupported":
        return DecisionResult(
            verdict=VERDICT_FALLBACK,
            trigger_codes=[],
            reason_codes=[REASON_P2_SEMANTIC_UNSUPPORTED],
            error_codes=[],
            p2_status=p2_status,
            p3_status=p3_status,
            severity="high",
            allow_primary=False,
            allow_fallback=True,
            audit_meta=_build_audit_meta(p2_result=p2_result, p3_result=p3_result),
        )

    # Conservative fallback for unknown / missing P2 status.
    return DecisionResult(
        verdict=VERDICT_WARN,
        trigger_codes=[],
        reason_codes=["p2_status_unknown"],
        error_codes=[],
        p2_status=p2_status,
        p3_status=p3_status,
        severity="medium",
        allow_primary=True,
        allow_fallback=False,
        audit_meta=_build_audit_meta(p2_result=p2_result, p3_result=p3_result),
    )


def _extract_p2_status(p2_result: Any) -> str | None:
    """
    Best-effort extraction from either:
    - object.support_status
    - object.p2_status
    - dict["support_status"]
    - dict["p2_status"]

    We intentionally keep this loose so the merge layer can integrate with
    different P2Result shapes without rewriting the whole contract first.
    """
    if p2_result is None:
        return None

    for field_name in ("support_status", "p2_status"):
        value = _read_attr_or_key(p2_result, field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _read_attr_or_key(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _normalize_p2_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None

    aliases = {
        "supported": "supported",
        "support": "supported",
        "ok": "supported",
        "clean": "supported",
        "partial": "partial",
        "weak": "weak",
        "unsupported": "unsupported",
        "not_supported": "unsupported",
        "fail": "unsupported",
    }
    return aliases.get(normalized, normalized)


def _coalesce_trigger_codes(
    trigger_codes: list[str],
    *,
    default: list[str],
) -> list[str]:
    return list(trigger_codes) if trigger_codes else list(default)


def _build_audit_meta(
    *,
    p2_result: Any,
    p3_result: P3Result,
) -> dict[str, Any]:
    """
    Minimal audit payload for merge output.

    Keep this lightweight for now. The main point is to preserve enough context
    for debugging and benchmark diffs without binding the merge layer to a
    specific audit backend.
    """
    p2_status = _extract_p2_status(p2_result)

    return {
        "plugin_name": p3_result.plugin_name,
        "p2_status": p2_status,
        "p3_status": p3_result.reference_integrity_status,
        "resolved_count": len(p3_result.resolved_members),
        "unresolved_count": len(p3_result.unresolved_members),
        "outside_pool_count": len(p3_result.outside_pool_references),
        "triggers": list(p3_result.triggers),
    }
