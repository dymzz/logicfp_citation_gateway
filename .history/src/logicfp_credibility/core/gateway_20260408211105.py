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
    Parse explicit [ref:...] claims with a sequential scanner.

    修补目标：
    - 不再让前一个 malformed [ref: ... 吞掉后一个合法 claim
    - 允许 malformed 与后续 fake / outside / missing 并存
    - 遇到“下一个 [ref:”早于当前“]”时，当前片段按 parse_failed 处理
    """
    claims: list[ReferenceClaim] = []
    malformed_refs: list[UnresolvedReference] = []

    cursor = 0
    prefix_len = len(REFERENCE_PREFIX)

    while True:
        start = llm_output.find(REFERENCE_PREFIX, cursor)
        if start == -1:
            break

        content_start = start + prefix_len
        close = llm_output.find(REFERENCE_SUFFIX, content_start)
        next_prefix = _find_next_ref_prefix(llm_output, content_start)

        # 情况 A：
        # 当前 [ref: 没有找到 ]，或者在找到 ] 之前先遇到了下一个 [ref:
        # -> 说明当前 claim 是 malformed
        if close == -1 or (next_prefix != -1 and next_prefix < close):
            raw_fragment = _extract_malformed_fragment(
                llm_output=llm_output,
                start=start,
                next_prefix=next_prefix,
            )
            malformed_refs.append(
                UnresolvedReference(
                    raw_text=raw_fragment,
                    reason="parse_failed",
                )
            )

            # 关键点：
            # 如果后面还有新的 [ref:，从那个位置继续扫描；
            # 这样后续 fake / outside / missing 还能被独立识别。
            if next_prefix != -1 and next_prefix > start:
                cursor = next_prefix
            else:
                cursor = start + prefix_len
            continue

        # 情况 B：当前 claim 合法闭合
        raw_text = llm_output[start : close + len(REFERENCE_SUFFIX)]
        ref_id = llm_output[content_start:close].strip()

        claims.append(
            ReferenceClaim(
                raw_text=raw_text,
                ref_id=ref_id if ref_id else None,
                position=start,
            )
        )

        cursor = close + len(REFERENCE_SUFFIX)

    return claims, malformed_refs


def _find_next_ref_prefix(text: str, start: int) -> int:
    """
    Find the next explicit [ref: after `start`.
    Returns -1 if not found.
    """
    return text.find(REFERENCE_PREFIX, start)


def _extract_malformed_fragment(
    *,
    llm_output: str,
    start: int,
    next_prefix: int,
    max_len: int = 80,
) -> str:
    """
    提取一个更短、更稳定的 malformed 片段。

    修补目标：
    - 如果后面还有新的 [ref:，当前 malformed 只截到下一个 [ref: 之前
    - 不再把后续合法 / fake / outside claim 一起吞进去
    - 仍然保留一点坏片段后的自然语言上下文，便于调试
    """
    end_candidates = [min(len(llm_output), start + max_len)]

    # 若后面还有新的 [ref:，当前坏片段必须在它之前截断
    if next_prefix != -1 and next_prefix > start:
        end_candidates.append(next_prefix)

    # 若中间有换行，也可提前截断
    newline_pos = llm_output.find("\n", start)
    if newline_pos != -1:
        end_candidates.append(newline_pos)

    end = min(end_candidates)
    fragment = llm_output[start:end].strip()

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
