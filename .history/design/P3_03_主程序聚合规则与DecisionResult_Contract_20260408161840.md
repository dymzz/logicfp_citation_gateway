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