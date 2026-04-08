# P3 主程序聚合规则与 DecisionResult Contract

## 3.1 本章目标

本章不再讨论 P3 的内部实现，而是明确：

1. P2Result 与 P3Result 如何进入主程序统一聚合层；
2. 当 P2 与 P3 同时存在时，谁优先；
3. 主程序最终对外暴露的统一决策对象应该长什么样；
4. 什么情况下允许 `allow`，什么情况下必须 `warn`、`fallback` 或 `block`；
5. 聚合层有哪些禁止项，哪些行为属于错误实现。

本章的目标，是把 P3 从“一个有结果的模块”收敛为“主程序统一 decision 链中的确定性输入源”。

---

## 3.2 聚合定位

P2 与 P3 的关系不是并列放行器，而是：

- **P2** 负责回答：当前输出是否被上下文语义支持；
- **P3** 负责回答：当前输出中的引用是否属于当前 ContextPool；
- **主程序聚合层** 负责回答：系统最终应该如何处理这次输出。

因此：

- P2 不直接输出最终业务动作；
- P3 不直接输出最终业务动作；
- 最终 `allow / warn / fallback / block` 只能由主程序统一生成。

换句话说：

**P2 与 P3 是判断层，主程序聚合器才是决策层。**

---

## 3.3 聚合优先级（冻结）

### 3.3.1 总原则

聚合优先级固定为：

**P3 > P2**

原因如下：

1. P3 处理的是引用边界问题；
2. 引用越界属于结构性硬风险；
3. 只要引用不属于当前 ContextPool，语义再“像支持”也不能放行；
4. 若允许 P2 覆盖 P3，则 P3 将退化为无效日志模块。

### 3.3.2 冻结解释

这里的 “P3 > P2” 不表示 P3 比 P2 更重要，  
而是表示：

**当 P3 给出 hard fail 信号时，P2 不得覆盖。**

也就是说：

- P3 的硬失败优先阻断；
- P3 的非硬失败优先给出风险等级；
- 只有当 P3 没有触发阻断或告警路径时，主程序才继续依赖 P2 的语义结果。

---

## 3.4 聚合输入对象

主程序聚合层的最小输入固定为：

- `p2_result: P2Result`
- `p3_result: P3Result`

其中：

- `P2Result` 是语义支持判断结果；
- `P3Result` 是引用完整性判断结果；
- 二者都不是最终对外输出对象；
- 聚合器的唯一职责是生成统一的 `DecisionResult`。

主程序不得跳过聚合器，直接根据单个模块结果输出最终 verdict。

---

## 3.5 主程序统一出口（冻结）

主程序统一出口固定为：

- `verdict`
- `trigger_codes`
- `reason_codes`
- `error_codes`

含义如下：

### 3.5.1 verdict

主程序最终决策动作。  
当前最小建议枚举为：

- `allow`
- `warn`
- `fallback`
- `block`

### 3.5.2 trigger_codes

表示触发本次决策的规则事件。  
它表达的是：

**“什么现象触发了这次 decision。”**

例如：

- `citation_outside_context_pool`
- `fabricated_reference_detected`
- `unresolved_reference_pointer`
- `reference_parse_failed`

### 3.5.3 reason_codes

表示主程序对本次决策的解释性归因。  
它表达的是：

**“为什么最终得出这个 verdict。”**

reason_code 允许由主程序在聚合层重新组织，不要求与 trigger_code 一一相同。

### 3.5.4 error_codes

表示主程序侧统一错误表达。  
它表达的是：

**“这次结果如果被视为错误，应以什么系统级错误码对外或对审计链表达。”**

例如：

- `ERR_REFERENCE_OUTSIDE_CONTEXT_POOL`
- `ERR_REFERENCE_UNRESOLVED`
- `ERR_REFERENCE_FABRICATED`

---

## 3.6 DecisionResult 数据契约（冻结）

建议主程序统一决策对象冻结为：

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class DecisionResult:
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
```

## 3.7 字段约束说明
### 3.7.1 verdict

必填。
只能由主程序聚合层生成。
P2 与 P3 不允许直接写入最终 verdict。

### 3.7.2 trigger_codes

必填列表。
允许为空，但一旦进入 warn / fallback / block 路径，原则上应至少有一个可追溯 trigger。

### 3.7.3 reason_codes

必填列表。
作用是为报告、日志、审计、测试失败解释提供统一语义归因。

### 3.7.4 error_codes

必填列表。
允许为空。
注意：不是所有 warn 都必须带 error_code，但所有明确的结构性错误路径应映射到统一错误码。

### 3.7.5 p2_status / p3_status

用于保留聚合前的判断结果，便于审计、回归和解释。

### 3.7.6 severity

表示主程序最终收敛后的风险等级。
它不是简单复制 P2 或 P3，而是主程序统一归并后的等级。

### 3.7.7 allow_primary / allow_fallback

用于明确：

是否允许继续主链路；
是否允许进入 fallback 链路。

这样可以避免仅靠 verdict 推断执行动作。

### 3.7.8 audit_meta

用于承载审计扩展信息，例如：

request_id
trace_id
pool_id
matched_reference_count
unresolved_count
benchmark_case_id
ruleset_version

该字段允许扩展，但不得替代主字段。

## 3.8 最小聚合矩阵（冻结）

主程序最小聚合矩阵固定如下：

P3 状态	P2 状态	主程序 verdict	说明
outside_pool	任意	block	明确池外引用，硬失败
fabricated	任意	block	明确伪造引用，硬失败
unresolved	supported / partial	warn	引用未可靠归属，不允许视为稳定通过
partial	supported	warn	部分引用合法，部分不完整，需提示风险
clean	supported	allow	引用干净，语义支持，可走主链路
clean	partial / weak	warn	引用干净，但语义支持不足
clean	unsupported	fallback 或 block	引用合法，但语义不支持
## 3.9 聚合规则正文（冻结）

主程序聚合逻辑可冻结表达为：
```python
def merge_p2_p3_to_decision(p2_result, p3_result) -> DecisionResult:
    if p3_result.reference_integrity_status == "outside_pool":
        return DecisionResult(
            verdict="block",
            trigger_codes=["citation_outside_context_pool"],
            reason_codes=["p3_hard_fail_outside_pool"],
            error_codes=["ERR_REFERENCE_OUTSIDE_CONTEXT_POOL"],
            p2_status=getattr(p2_result, "support_status", None),
            p3_status="outside_pool",
            severity="critical",
            allow_primary=False,
            allow_fallback=False,
        )

    if p3_result.reference_integrity_status == "fabricated":
        return DecisionResult(
            verdict="block",
            trigger_codes=["fabricated_reference_detected"],
            reason_codes=["p3_hard_fail_fabricated"],
            error_codes=["ERR_REFERENCE_FABRICATED"],
            p2_status=getattr(p2_result, "support_status", None),
            p3_status="fabricated",
            severity="critical",
            allow_primary=False,
            allow_fallback=False,
        )

    if p3_result.reference_integrity_status == "unresolved":
        return DecisionResult(
            verdict="warn",
            trigger_codes=list(p3_result.triggers),
            reason_codes=["p3_reference_unresolved"],
            error_codes=["ERR_REFERENCE_UNRESOLVED"],
            p2_status=getattr(p2_result, "support_status", None),
            p3_status="unresolved",
            severity="high",
            allow_primary=True,
            allow_fallback=False,
        )

    if p3_result.reference_integrity_status == "partial":
        return DecisionResult(
            verdict="warn",
            trigger_codes=list(p3_result.triggers),
            reason_codes=["p3_reference_partial"],
            error_codes=[],
            p2_status=getattr(p2_result, "support_status", None),
            p3_status="partial",
            severity="medium",
            allow_primary=True,
            allow_fallback=False,
        )

    return use_p2_result_as_final_decision(p2_result, p3_result)
```

## 3.10 clean 状态下对 P2 的接管规则

当且仅当：

p3_result.reference_integrity_status == "clean"

主程序才继续依赖 P2 结果决定最终动作。

建议最小规则如下：

### 3.10.1 P2 = supported

输出：

verdict = allow

说明：

引用完整；
语义支持充足；
允许继续主链路。
### 3.10.2 P2 = partial / weak

输出：

verdict = warn

说明：

引用虽然合法；
但语义支持不足以视为稳定通过；
主程序应保留风险提示。
3.10.3 P2 = unsupported

输出：

verdict = fallback 或 block

说明：

当前回答虽然没有引用越界；
但语义层不支持当前输出；
是否允许 fallback，取决于主程序策略。
3.11 推荐的 verdict 语义

为了避免不同实现对 verdict 产生歧义，建议固定以下语义：

3.11.1 allow

允许主链路继续执行，不附加结构性风险告警。

3.11.2 warn

允许结果继续流转，但必须带风险标记。
warn 不等于“没问题”，而是“问题存在，但当前策略允许继续”。

3.11.3 fallback

禁止主链路结果直接交付，允许进入替代路径。
例如：

更保守回答；
模板化回答；
人工审核队列；
本地简化模型；
二次重试链路。
3.11.4 block

不允许继续主链路，也不允许将当前结果视为可交付答案。
通常对应：

明确池外引用；
明确伪造引用；
或主程序定义的其他不可放行条件。
3.12 trigger / reason / error 的映射原则
3.12.1 trigger_code 表示“触发事件”

trigger_code 应尽量贴近底层检测结果，例如：

citation_outside_context_pool
unresolved_reference_pointer
reference_parse_failed
fabricated_reference_detected
3.12.2 reason_code 表示“聚合解释”

reason_code 应尽量贴近主程序对本次结果的解释，例如：

p3_hard_fail_outside_pool
p3_hard_fail_fabricated
p3_reference_unresolved
p3_reference_partial
p2_semantic_unsupported
3.12.3 error_code 表示“统一错误出口”

error_code 应尽量稳定，不应频繁修改文案或语义。
它的目标是：

便于上层系统识别；
便于审计；
便于 benchmark / 回归比较；
便于对外接口保持稳定。
3.13 宿主输入错误与业务决策错误的分离

聚合层必须区分两类问题：

3.13.1 宿主输入错误

例如：

ContextPool 非法；
ContextPool 为空；
member_id 重复；
HostP3Request 结构不合法。

这类问题应由主程序输入校验层直接拦截，进入输入错误分支。
它们不是 P3 的引用判断结果。

3.13.2 P3 业务结果

例如：

outside_pool
fabricated
unresolved
partial
clean

这类问题属于 P3 的业务判断结果，才能进入当前聚合规则。

这两类错误不能混用。
否则会导致：

输入错误被误记为引用错误；
benchmark 口径混乱；
回归报告无法解释失败来源。
3.14 聚合层禁止项（冻结）

以下做法全部视为错误实现：

3.14.1 禁止 P2 覆盖 P3 的 hard fail

一旦 P3 给出：

outside_pool
fabricated

主程序不得因 P2 “supported” 而改判为 allow 或 warn。

3.14.2 禁止 P3 直接输出最终业务响应

P3 只能输出 P3Result，
不能直接输出：

allow
fallback
block
对用户的最终响应体
3.14.3 禁止主程序跳过 P3 直接按 P2 放行

只要当前链路声称支持基于引用的放行校验，
主程序就不得跳过 P3。

3.14.4 禁止没有 ContextPool 时降级为语义判断

在无 ContextPool 的情况下，
主程序不得把“没有引用边界”偷偷降级为“那就按语义大概看一下”。

这是输入错误，不是语义替代路径。

3.14.5 禁止在聚合层重新解释 P3 的边界定义

聚合器只能消费 P3 的结果，
不能把：

outside_pool 改写成 partial
fabricated 改写成 unresolved
unresolved 改写成 “其实差不多算 clean”

否则 P3 的状态冻结将失效。

3.15 审计与回归要求

为了保证聚合逻辑可复盘，主程序在生成 DecisionResult 时，建议至少记录：

request_id
trace_id
p2_status
p3_status
verdict
trigger_codes
reason_codes
error_codes
ruleset_version
benchmark_case_id（如有）

这样可以保证：

聚合结果可追溯；
回归失败可解释；
版本升级前后可比较；
代码实现与 benchmark 真值保持一致。
3.16 本章结论

主程序聚合层的本质，不是简单把 P2 和 P3 结果拼起来，
而是把两类不同性质的判断，收敛为统一、稳定、可审计的系统出口。

本章应冻结三条原则：

P3 > P2
P2 / P3 都不直接输出最终业务动作
主程序统一出口只认 DecisionResult