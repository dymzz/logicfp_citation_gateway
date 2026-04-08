# src/logicfp_credibility/core/gateway.py

from __future__ import annotations

import re
from typing import Iterable

from .constants import (
    FABRICATED_REF_PREFIX,
    OUTSIDE_POOL_REF_PREFIX,
    PLUGIN_NAME_REFERENCE_INTEGRITY_GATEWAY,
    REFERENCE_PREFIX,
    REFERENCE_SUFFIX,
    STATUS_CLEAN,
    STATUS_FABRICATED,
    STATUS_OUTSIDE_POOL,
    STATUS_PARTIAL,
    STATUS_UNRESOLVED,
    TRIGGER_CITATION_OUTSIDE_CONTEXT_POOL,
    TRIGGER_FABRICATED_REFERENCE_DETECTED,
    TRIGGER_REFERENCE_MEMBER_NOT_FOUND,
    TRIGGER_REFERENCE_PARSE_FAILED,
    TRIGGER_UNRESOLVED_REFERENCE_POINTER,
    severity_for_status,
)
from .contracts import (
    ContextPool,
    HostP3Request,
    P3Result,
    ReferenceClaim,
    ResolvedReference,
    UnresolvedReference,
)


_REF_PATTERN = re.compile(r"\[ref:([^\]]+)\]")


class ReferenceIntegrityGateway:
    """
    Minimal P3 gateway.

    Current behavior:
    - parse explicit [ref:...] claims
    - resolve against ContextPool
    - classify as:
        clean / partial / unresolved / outside_pool / fabricated
    - return P3Result only
    """

    def __init__(
        self,
        *,
        plugin_name: str = PLUGIN_NAME_REFERENCE_INTEGRITY_GATEWAY,
    ) -> None:
        self.plugin_name = plugin_name

    def run(self, p3_request: HostP3Request) -> P3Result:
        """
        Unified P3 entrypoint expected by the host:
            p3_result = reference_gateway.run(p3_request)
        """
        self._validate_request(p3_request)

        claims, malformed_refs = _parse_reference_claims(p3_request.llm_output)

        resolution = _resolve_claims(
            claims=claims,
            malformed_refs=malformed_refs,
            context_pool=p3_request.context_pool,
        )

        status = _evaluate_status(
            resolved_refs=resolution["resolved_refs"],
            unresolved_refs=resolution["unresolved_refs"],
            outside_pool_references=resolution["outside_pool_references"],
            fabricated_refs=resolution["fabricated_refs"],
        )

        severity = severity_for_status(status)
        triggers = _unique_preserve_order(resolution["triggers"])
        reasons = _build_reasons(
            status=status,
            resolved_refs=resolution["resolved_refs"],
            unresolved_refs=resolution["unresolved_refs"],
            outside_pool_references=resolution["outside_pool_references"],
            fabricated_refs=resolution["fabricated_refs"],
        )
        metrics = _build_metrics(
            claims=claims,
            malformed_refs=malformed_refs,
            resolved_refs=resolution["resolved_refs"],
            unresolved_refs=resolution["unresolved_refs"],
            outside_pool_references=resolution["outside_pool_references"],
            fabricated_refs=resolution["fabricated_refs"],
        )

        # Note:
        # Current frozen P3Result contract does not define a dedicated
        # fabricated_references field, so fabricated raw texts are surfaced
        # via `unresolved_members` + status/triggers/reasons.
        unresolved_members = [
            item.raw_text for item in resolution["unresolved_refs"]
        ] + list(resolution["fabricated_refs"])

        return P3Result(
            plugin_name=self.plugin_name,
            reference_integrity_status=status,
            resolved_members=[
                ref.member.member_id for ref in resolution["resolved_refs"]
            ],
            unresolved_members=unresolved_members,
            outside_pool_references=list(resolution["outside_pool_references"]),
            severity=severity,
            triggers=triggers,
            reasons=reasons,
            metrics=metrics,
        )

    @staticmethod
    def _validate_request(p3_request: HostP3Request) -> None:
        if not isinstance(p3_request, HostP3Request):
            raise TypeError("p3_request must be a HostP3Request.")
        if not isinstance(p3_request.context_pool, ContextPool):
            raise TypeError("p3_request.context_pool must be a ContextPool.")


def _parse_reference_claims(
    llm_output: str,
) -> tuple[list[ReferenceClaim], list[UnresolvedReference]]:
    """
    Parse explicit [ref:...] claims and also capture malformed prefix hits.

    Example valid:
        [ref:doc_1]
        [ref:outside:secret_doc]
        [ref:fake:made_up_doc]

    Example malformed:
        [ref:doc_1
    """
    claims: list[ReferenceClaim] = []

    matches = list(_REF_PATTERN.finditer(llm_output))
    matched_starts = {match.start() for match in matches}

    for match in matches:
        raw_text = match.group(0)
        ref_id = match.group(1).strip()
        claims.append(
            ReferenceClaim(
                raw_text=raw_text,
                ref_id=ref_id if ref_id else None,
                position=match.start(),
            )
        )

    malformed_refs: list[UnresolvedReference] = []
    for prefix_match in re.finditer(re.escape(REFERENCE_PREFIX), llm_output):
        if prefix_match.start() in matched_starts:
            continue
        raw_fragment = _extract_malformed_fragment(llm_output, prefix_match.start())
        malformed_refs.append(
            UnresolvedReference(
                raw_text=raw_fragment,
                reason="parse_failed",
            )
        )

    return claims, malformed_refs


def _extract_malformed_fragment(text: str, start: int, *, max_len: int = 80) -> str:
    """
    Extract a short malformed fragment for reporting.
    """
    end = min(len(text), start + max_len)

    # Try to stop at newline first.
    newline_pos = text.find("\n", start, end)
    if newline_pos != -1:
        end = newline_pos

    fragment = text[start:end].strip()
    return fragment or REFERENCE_PREFIX.rstrip(REFERENCE_SUFFIX)


def _resolve_claims(
    *,
    claims: list[ReferenceClaim],
    malformed_refs: list[UnresolvedReference],
    context_pool: ContextPool,
) -> dict[str, list]:
    resolved_refs: list[ResolvedReference] = []
    unresolved_refs: list[UnresolvedReference] = list(malformed_refs)
    outside_pool_references: list[str] = []
    fabricated_refs: list[str] = []
    triggers: list[str] = []

    if malformed_refs:
        triggers.extend(
            [
                TRIGGER_REFERENCE_PARSE_FAILED,
                TRIGGER_UNRESOLVED_REFERENCE_POINTER,
            ]
        )

    for claim in claims:
        ref_id = claim.ref_id or ""

        if ref_id.startswith(OUTSIDE_POOL_REF_PREFIX):
            outside_pool_references.append(ref_id)
            triggers.append(TRIGGER_CITATION_OUTSIDE_CONTEXT_POOL)
            continue

        if ref_id.startswith(FABRICATED_REF_PREFIX):
            fabricated_refs.append(claim.raw_text)
            triggers.append(TRIGGER_FABRICATED_REFERENCE_DETECTED)
            continue

        member = context_pool.get_member(ref_id)
        if member is not None:
            resolved_refs.append(
                ResolvedReference(
                    ref_id=ref_id,
                    member=member,
                )
            )
            continue

        unresolved_refs.append(
            UnresolvedReference(
                raw_text=claim.raw_text,
                reason="id_not_found",
            )
        )
        triggers.extend(
            [
                TRIGGER_REFERENCE_MEMBER_NOT_FOUND,
                TRIGGER_UNRESOLVED_REFERENCE_POINTER,
            ]
        )

    return {
        "resolved_refs": resolved_refs,
        "unresolved_refs": unresolved_refs,
        "outside_pool_references": outside_pool_references,
        "fabricated_refs": fabricated_refs,
        "triggers": triggers,
    }


def _evaluate_status(
    *,
    resolved_refs: list[ResolvedReference],
    unresolved_refs: list[UnresolvedReference],
    outside_pool_references: list[str],
    fabricated_refs: list[str],
) -> str:
    """
    Minimal status evaluation order:

    1) outside_pool
    2) fabricated
    3) partial
    4) unresolved
    5) clean
    """
    if outside_pool_references:
        return STATUS_OUTSIDE_POOL

    if fabricated_refs:
        return STATUS_FABRICATED

    if resolved_refs and unresolved_refs:
        return STATUS_PARTIAL

    if unresolved_refs and not resolved_refs:
        return STATUS_UNRESOLVED

    # Current minimal behavior:
    # no explicit claims -> clean
    return STATUS_CLEAN


def _build_reasons(
    *,
    status: str,
    resolved_refs: list[ResolvedReference],
    unresolved_refs: list[UnresolvedReference],
    outside_pool_references: list[str],
    fabricated_refs: list[str],
) -> list[str]:
    if status == STATUS_OUTSIDE_POOL:
        return [
            "detected_reference_outside_context_pool",
            f"outside_pool_count={len(outside_pool_references)}",
        ]

    if status == STATUS_FABRICATED:
        return [
            "detected_fabricated_reference",
            f"fabricated_count={len(fabricated_refs)}",
        ]

    if status == STATUS_PARTIAL:
        return [
            "some_references_resolved_some_unresolved",
            f"resolved_count={len(resolved_refs)}",
            f"unresolved_count={len(unresolved_refs)}",
        ]

    if status == STATUS_UNRESOLVED:
        parse_failed = sum(
            1 for item in unresolved_refs if item.reason == "parse_failed"
        )
        id_not_found = sum(
            1 for item in unresolved_refs if item.reason == "id_not_found"
        )
        return [
            "references_cannot_be_reliably_resolved",
            f"parse_failed_count={parse_failed}",
            f"id_not_found_count={id_not_found}",
        ]

    return [
        "all_explicit_references_resolved_within_context_pool",
        f"resolved_count={len(resolved_refs)}",
    ]


def _build_metrics(
    *,
    claims: list[ReferenceClaim],
    malformed_refs: list[UnresolvedReference],
    resolved_refs: list[ResolvedReference],
    unresolved_refs: list[UnresolvedReference],
    outside_pool_references: list[str],
    fabricated_refs: list[str],
) -> dict[str, float | int]:
    total_claim_units = len(claims) + len(malformed_refs)

    resolved_count = len(resolved_refs)
    unresolved_count = len(unresolved_refs)
    outside_pool_count = len(outside_pool_references)
    fabricated_count = len(fabricated_refs)

    resolution_rate = (
        resolved_count / total_claim_units if total_claim_units > 0 else 1.0
    )

    coverage_denominator = (
        resolved_count + unresolved_count + outside_pool_count + fabricated_count
    )
    coverage_rate = (
        resolved_count / coverage_denominator if coverage_denominator > 0 else 1.0
    )

    return {
        "total_claims": len(claims),
        "malformed_claims": len(malformed_refs),
        "resolved_count": resolved_count,
        "unresolved_count": unresolved_count,
        "outside_pool_count": outside_pool_count,
        "fabricated_count": fabricated_count,
        "resolution_rate": round(resolution_rate, 6),
        "coverage_rate": round(coverage_rate, 6),
    }


def _unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)

    return result


reference_gateway = ReferenceIntegrityGateway()
