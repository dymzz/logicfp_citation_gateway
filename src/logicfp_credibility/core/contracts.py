# src/logicfp_credibility/core/contracts.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ContextMember:
    """
    单个可被引用、可被归属的上下文成员。

    设计来源：
    - member_id 是当前最基础的归属锚点
    - source_id 表达来源归属
    - content 是最小有效内容载体
    """

    member_id: str
    source_id: str
    content: str
    title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.member_id or not self.member_id.strip():
            raise ValueError("ContextMember.member_id must be a non-empty string.")
        if not self.source_id or not self.source_id.strip():
            raise ValueError("ContextMember.source_id must be a non-empty string.")
        if not isinstance(self.content, str):
            raise TypeError("ContextMember.content must be a string.")


@dataclass(slots=True)
class ContextPool:
    """
    当前轮合法引用边界。

    P3 的唯一合法引用边界来源是 ContextPool。
    """

    pool_id: str
    members: list[ContextMember]
    retrieval_meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.pool_id or not self.pool_id.strip():
            raise ValueError("ContextPool.pool_id must be a non-empty string.")
        if not isinstance(self.members, list):
            raise TypeError("ContextPool.members must be a list[ContextMember].")
        if not self.members:
            raise ValueError("ContextPool.members must not be empty.")

        seen: set[str] = set()
        for member in self.members:
            if not isinstance(member, ContextMember):
                raise TypeError("ContextPool.members must contain only ContextMember.")
            if member.member_id in seen:
                raise ValueError(
                    f"Duplicated ContextMember.member_id detected: {member.member_id!r}"
                )
            seen.add(member.member_id)

    def member_ids(self) -> set[str]:
        return {member.member_id for member in self.members}

    def get_member(self, member_id: str) -> ContextMember | None:
        for member in self.members:
            if member.member_id == member_id:
                return member
        return None


@dataclass(slots=True)
class HostP3Request:
    """
    宿主传给 P3 的标准输入对象。
    """

    request_id: str
    llm_output: str
    context_pool: ContextPool
    decision_type: str
    action_risk: str
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.request_id or not self.request_id.strip():
            raise ValueError("HostP3Request.request_id must be a non-empty string.")
        if not isinstance(self.llm_output, str) or not self.llm_output.strip():
            raise ValueError("HostP3Request.llm_output must be a non-empty string.")
        if not isinstance(self.context_pool, ContextPool):
            raise TypeError("HostP3Request.context_pool must be a ContextPool.")
        if not self.decision_type or not self.decision_type.strip():
            raise ValueError("HostP3Request.decision_type must be a non-empty string.")
        if not self.action_risk or not self.action_risk.strip():
            raise ValueError("HostP3Request.action_risk must be a non-empty string.")


@dataclass(slots=True)
class ReferenceClaim:
    """
    从 llm_output 中解析出来的单个引用声明。
    """

    raw_text: str
    ref_id: str | None
    position: int

    def __post_init__(self) -> None:
        if not isinstance(self.raw_text, str) or not self.raw_text:
            raise ValueError("ReferenceClaim.raw_text must be a non-empty string.")
        if self.ref_id is not None and not isinstance(self.ref_id, str):
            raise TypeError("ReferenceClaim.ref_id must be str | None.")
        if not isinstance(self.position, int) or self.position < 0:
            raise ValueError("ReferenceClaim.position must be a non-negative integer.")


@dataclass(slots=True)
class ResolvedReference:
    """
    已成功绑定到 ContextPool 成员的引用。
    """

    ref_id: str
    member: ContextMember

    def __post_init__(self) -> None:
        if not self.ref_id or not self.ref_id.strip():
            raise ValueError("ResolvedReference.ref_id must be a non-empty string.")
        if not isinstance(self.member, ContextMember):
            raise TypeError("ResolvedReference.member must be a ContextMember.")


@dataclass(slots=True)
class UnresolvedReference:
    """
    无法被可靠解析或绑定到 ContextPool 的引用。

    reason 当前最小口径建议只保留：
    - parse_failed
    - id_not_found

    fabricated 是独立硬失败语义，不建议混入这里。
    """

    raw_text: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.raw_text, str) or not self.raw_text:
            raise ValueError("UnresolvedReference.raw_text must be a non-empty string.")
        if not self.reason or not self.reason.strip():
            raise ValueError("UnresolvedReference.reason must be a non-empty string.")


@dataclass(slots=True)
class P3Result:
    """
    P3 对单次输入完成判断后的标准输出对象。
    P3 只输出结构判断结果，不直接输出最终业务动作。
    """

    plugin_name: str
    reference_integrity_status: str

    resolved_members: list[str] = field(default_factory=list)
    unresolved_members: list[str] = field(default_factory=list)
    outside_pool_references: list[str] = field(default_factory=list)

    severity: str = "low"
    triggers: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.plugin_name or not self.plugin_name.strip():
            raise ValueError("P3Result.plugin_name must be a non-empty string.")
        if (
            not self.reference_integrity_status
            or not self.reference_integrity_status.strip()
        ):
            raise ValueError(
                "P3Result.reference_integrity_status must be a non-empty string."
            )
        if not self.severity or not self.severity.strip():
            raise ValueError("P3Result.severity must be a non-empty string.")

        self._validate_str_list("resolved_members", self.resolved_members)
        self._validate_str_list("unresolved_members", self.unresolved_members)
        self._validate_str_list("outside_pool_references", self.outside_pool_references)
        self._validate_str_list("triggers", self.triggers)
        self._validate_str_list("reasons", self.reasons)

        if not isinstance(self.metrics, dict):
            raise TypeError("P3Result.metrics must be a dict[str, Any].")

    @staticmethod
    def _validate_str_list(field_name: str, value: list[str]) -> None:
        if not isinstance(value, list):
            raise TypeError(f"P3Result.{field_name} must be a list[str].")
        for item in value:
            if not isinstance(item, str):
                raise TypeError(f"P3Result.{field_name} must contain only strings.")


@dataclass(slots=True)
class DecisionResult:
    """
    主程序统一聚合后的最终决策对象。

    注意：
    - 它属于主程序，不属于 P3
    - 最终 allow / warn / fallback / block 只由主程序输出
    """

    verdict: str
    trigger_codes: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)

    p2_status: str | None = None
    p3_status: str | None = None

    severity: str | None = None
    allow_primary: bool = False
    allow_fallback: bool = False

    audit_meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.verdict or not self.verdict.strip():
            raise ValueError("DecisionResult.verdict must be a non-empty string.")

        self._validate_str_list("trigger_codes", self.trigger_codes)
        self._validate_str_list("reason_codes", self.reason_codes)
        self._validate_str_list("error_codes", self.error_codes)

        if self.p2_status is not None and not isinstance(self.p2_status, str):
            raise TypeError("DecisionResult.p2_status must be str | None.")
        if self.p3_status is not None and not isinstance(self.p3_status, str):
            raise TypeError("DecisionResult.p3_status must be str | None.")
        if self.severity is not None and not isinstance(self.severity, str):
            raise TypeError("DecisionResult.severity must be str | None.")
        if not isinstance(self.allow_primary, bool):
            raise TypeError("DecisionResult.allow_primary must be bool.")
        if not isinstance(self.allow_fallback, bool):
            raise TypeError("DecisionResult.allow_fallback must be bool.")
        if not isinstance(self.audit_meta, dict):
            raise TypeError("DecisionResult.audit_meta must be dict[str, Any].")

    @staticmethod
    def _validate_str_list(field_name: str, value: list[str]) -> None:
        if not isinstance(value, list):
            raise TypeError(f"DecisionResult.{field_name} must be a list[str].")
        for item in value:
            if not isinstance(item, str):
                raise TypeError(
                    f"DecisionResult.{field_name} must contain only strings."
                )
