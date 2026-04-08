# src/logicfp_credibility/core/constants.py

from __future__ import annotations

from typing import Final


# ============================================================
# Plugin identity
# ============================================================

PLUGIN_NAME_REFERENCE_INTEGRITY_GATEWAY: Final[str] = "reference_integrity_gateway"


# ============================================================
# P3 reference integrity status (frozen)
# ============================================================

STATUS_CLEAN: Final[str] = "clean"
STATUS_PARTIAL: Final[str] = "partial"
STATUS_UNRESOLVED: Final[str] = "unresolved"
STATUS_OUTSIDE_POOL: Final[str] = "outside_pool"
STATUS_FABRICATED: Final[str] = "fabricated"

REFERENCE_INTEGRITY_STATUSES: Final[tuple[str, ...]] = (
    STATUS_CLEAN,
    STATUS_PARTIAL,
    STATUS_UNRESOLVED,
    STATUS_OUTSIDE_POOL,
    STATUS_FABRICATED,
)

REFERENCE_INTEGRITY_STATUS_SET: Final[frozenset[str]] = frozenset(
    REFERENCE_INTEGRITY_STATUSES
)


# ============================================================
# Severity (frozen)
# ============================================================

SEVERITY_LOW: Final[str] = "low"
SEVERITY_MEDIUM: Final[str] = "medium"
SEVERITY_HIGH: Final[str] = "high"
SEVERITY_CRITICAL: Final[str] = "critical"

SEVERITIES: Final[tuple[str, ...]] = (
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
)

SEVERITY_SET: Final[frozenset[str]] = frozenset(SEVERITIES)

STATUS_TO_SEVERITY: Final[dict[str, str]] = {
    STATUS_CLEAN: SEVERITY_LOW,
    STATUS_PARTIAL: SEVERITY_MEDIUM,
    STATUS_UNRESOLVED: SEVERITY_HIGH,
    STATUS_OUTSIDE_POOL: SEVERITY_CRITICAL,
    STATUS_FABRICATED: SEVERITY_CRITICAL,
}


# ============================================================
# Trigger codes (frozen)
# ============================================================

TRIGGER_REFERENCE_MEMBER_NOT_FOUND: Final[str] = "reference_member_not_found"
TRIGGER_CITATION_OUTSIDE_CONTEXT_POOL: Final[str] = "citation_outside_context_pool"
TRIGGER_UNRESOLVED_REFERENCE_POINTER: Final[str] = "unresolved_reference_pointer"
TRIGGER_FABRICATED_REFERENCE_DETECTED: Final[str] = "fabricated_reference_detected"
TRIGGER_REFERENCE_PARSE_FAILED: Final[str] = "reference_parse_failed"

TRIGGER_CODES: Final[tuple[str, ...]] = (
    TRIGGER_REFERENCE_MEMBER_NOT_FOUND,
    TRIGGER_CITATION_OUTSIDE_CONTEXT_POOL,
    TRIGGER_UNRESOLVED_REFERENCE_POINTER,
    TRIGGER_FABRICATED_REFERENCE_DETECTED,
    TRIGGER_REFERENCE_PARSE_FAILED,
)

TRIGGER_CODE_SET: Final[frozenset[str]] = frozenset(TRIGGER_CODES)


# ============================================================
# Error codes (frozen, host/program level)
# ============================================================

ERR_REFERENCE_OUTSIDE_CONTEXT_POOL: Final[str] = "ERR_REFERENCE_OUTSIDE_CONTEXT_POOL"
ERR_REFERENCE_UNRESOLVED: Final[str] = "ERR_REFERENCE_UNRESOLVED"
ERR_REFERENCE_FABRICATED: Final[str] = "ERR_REFERENCE_FABRICATED"

ERR_CONTEXT_POOL_INVALID: Final[str] = "ERR_CONTEXT_POOL_INVALID"
ERR_CONTEXT_POOL_EMPTY: Final[str] = "ERR_CONTEXT_POOL_EMPTY"
ERR_CONTEXT_MEMBER_ID_DUPLICATED: Final[str] = "ERR_CONTEXT_MEMBER_ID_DUPLICATED"
ERR_P3_INPUT_INVALID: Final[str] = "ERR_P3_INPUT_INVALID"

ERROR_CODES: Final[tuple[str, ...]] = (
    ERR_REFERENCE_OUTSIDE_CONTEXT_POOL,
    ERR_REFERENCE_UNRESOLVED,
    ERR_REFERENCE_FABRICATED,
    ERR_CONTEXT_POOL_INVALID,
    ERR_CONTEXT_POOL_EMPTY,
    ERR_CONTEXT_MEMBER_ID_DUPLICATED,
    ERR_P3_INPUT_INVALID,
)

ERROR_CODE_SET: Final[frozenset[str]] = frozenset(ERROR_CODES)


# ============================================================
# Decision / merge layer constants
# ============================================================

VERDICT_ALLOW: Final[str] = "allow"
VERDICT_WARN: Final[str] = "warn"
VERDICT_FALLBACK: Final[str] = "fallback"
VERDICT_BLOCK: Final[str] = "block"

VERDICTS: Final[tuple[str, ...]] = (
    VERDICT_ALLOW,
    VERDICT_WARN,
    VERDICT_FALLBACK,
    VERDICT_BLOCK,
)

VERDICT_SET: Final[frozenset[str]] = frozenset(VERDICTS)

P3_HARD_FAIL_STATUSES: Final[frozenset[str]] = frozenset(
    {
        STATUS_OUTSIDE_POOL,
        STATUS_FABRICATED,
    }
)

P3_WARN_STATUSES: Final[frozenset[str]] = frozenset(
    {
        STATUS_PARTIAL,
        STATUS_UNRESOLVED,
    }
)


# ============================================================
# Reference parser mini-conventions
# ============================================================

REFERENCE_PREFIX: Final[str] = "[ref:"
REFERENCE_SUFFIX: Final[str] = "]"

OUTSIDE_POOL_REF_PREFIX: Final[str] = "outside:"
FABRICATED_REF_PREFIX: Final[str] = "fake:"


# ============================================================
# Suggested reason codes for merge layer
# ============================================================

REASON_P3_HARD_FAIL_OUTSIDE_POOL: Final[str] = "p3_hard_fail_outside_pool"
REASON_P3_HARD_FAIL_FABRICATED: Final[str] = "p3_hard_fail_fabricated"
REASON_P3_REFERENCE_UNRESOLVED: Final[str] = "p3_reference_unresolved"
REASON_P3_REFERENCE_PARTIAL: Final[str] = "p3_reference_partial"
REASON_P2_SEMANTIC_UNSUPPORTED: Final[str] = "p2_semantic_unsupported"

REASON_CODES_SUGGESTED: Final[tuple[str, ...]] = (
    REASON_P3_HARD_FAIL_OUTSIDE_POOL,
    REASON_P3_HARD_FAIL_FABRICATED,
    REASON_P3_REFERENCE_UNRESOLVED,
    REASON_P3_REFERENCE_PARTIAL,
    REASON_P2_SEMANTIC_UNSUPPORTED,
)


# ============================================================
# Lightweight validation helpers
# ============================================================


def is_valid_reference_integrity_status(value: str) -> bool:
    return value in REFERENCE_INTEGRITY_STATUS_SET


def is_valid_severity(value: str) -> bool:
    return value in SEVERITY_SET


def is_valid_trigger_code(value: str) -> bool:
    return value in TRIGGER_CODE_SET


def is_valid_error_code(value: str) -> bool:
    return value in ERROR_CODE_SET


def is_valid_verdict(value: str) -> bool:
    return value in VERDICT_SET


def severity_for_status(status: str) -> str:
    """
    Return the frozen default severity for a given P3 status.
    """
    try:
        return STATUS_TO_SEVERITY[status]
    except KeyError as exc:
        raise ValueError(f"Unknown P3 status: {status!r}") from exc
