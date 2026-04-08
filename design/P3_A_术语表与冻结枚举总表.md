附录 A：术语表与冻结枚举总表
A.1 文档目的

本附录用于集中冻结 P3 设计文档中已经分散定义的术语、状态枚举、错误码、触发器与接口名词，目标是减少后续实现、评审、回归和接入过程中反复改口径的问题。

本附录的作用不是引入新规则，而是把前文已经确认的内容收口为一个统一参照表。
后续涉及以下内容时，应优先以本附录为准：

名词解释
状态枚举
trigger code
error code
角色边界
核心输入输出对象
A.2 术语表
A.2.1 ContextPool

定义：
当前一次待放行回答中，允许被引用的上下文成员集合。

作用：
P3 的唯一合法引用边界来源。

说明：
P3 不从外部系统动态扩展引用范围，所有合法引用必须来自当前 ContextPool.members。

A.2.2 ContextMember

定义：
ContextPool 中的单个成员对象。

最小含义：
一个可被引用、可被归属的上下文单元。

关键字段：

member_id
source_id
content

说明：
member_id 是 P3 当前最基础的归属锚点。

A.2.3 member_id

定义：
ContextMember 的唯一标识符。

约束：

非空
唯一
在本轮调用内稳定

作用：
P3 进行引用归属判断的主键。

A.2.4 source_id

定义：
ContextMember 所属来源对象的标识符。

作用：
用于表达成员的来源归属。

说明：
当前最小版本中，P3 的核心匹配优先依赖 member_id；
未来若扩展复合引用形式，source_id 可作为辅助归属信息，但不能绕开 ContextPool 边界。

A.2.5 llm_output

定义：
宿主准备交付给用户或下游系统的最终待放行文本。

说明：
送入 P3 的 llm_output 必须是最终版本，而不是中间草稿或预处理片段。

A.2.6 ReferenceClaim

定义：
从 llm_output 中解析出来的单个引用声明。

作用：
表示“模型声称自己引用了某个对象”。

说明：
ReferenceClaim 只是解析结果，不代表该引用一定合法，也不代表已完成归属。

A.2.7 ResolvedReference

定义：
已经被成功绑定到 ContextPool 成员的引用。

说明：
只有成功映射到合法 ContextMember 的引用，才属于 resolved。

A.2.8 UnresolvedReference

定义：
无法被可靠解析或无法绑定到 ContextPool 的引用。

常见原因：

parse_failed
id_not_found
fabricated

说明：
unresolved 表示“当前无法可靠归属”，但不等同于 outside_pool。

A.2.9 outside-pool reference

定义：
明确不属于当前 ContextPool 的引用。

说明：
这类引用属于 P3 的硬失败路径之一。
它不是“暂时找不到”，而是“明确越界”。

A.2.10 fabricated reference

定义：
伪造出的、结构上表现为引用，但并不应被视为当前合法引用成员的对象。

说明：
fabricated 与 unresolved 不同：
fabricated 更强调“伪造/伪装引用”的硬失败语义。

A.2.11 reference integrity

定义：
引用完整性，即回答中的引用对象是否满足：

可解析
可归属
不越过当前 ContextPool

说明：
P3 的职责就是给出这个维度的判断结果。

A.2.12 Reference Integrity Gateway

定义：
P3 模块的功能定位名称。

含义：
一个只做引用归属与引用边界校验的结构网关。

说明：
它不是语义评估器，不是纠错器，也不是最终决策器。

A.2.13 HostP3Request

定义：
宿主传给 P3 的标准输入对象。

作用：
统一 P3 的接入入口。

A.2.14 P3Result

定义：
P3 对单次输入完成判断后的标准输出对象。

作用：
供主程序聚合层消费，用于后续与 P2 结果合并生成统一 decision。

A.2.15 DecisionResult

定义：
主程序统一聚合后的最终决策对象。

说明：
它属于主程序，不属于 P3。
P3 不直接生成最终 allow / warn / fallback / block。

A.2.16 P2

定义：
通用语义支持判断层。

职责：

判断回答是否被上下文语义支持
判断是否存在语义漂移、过度概括、冲突等问题

说明：
P2 解决“语义支持”问题，不解决“引用归属”问题。

A.2.17 P3

定义：
通用引用完整性网关。

职责：

解析引用
绑定 ContextPool
判断池内 / 池外 / unresolved / fabricated

说明：
P3 只解决“引用是否合法属于当前上下文池”这一问题。

A.2.18 P4

定义：
外部可选插件生态层。

职责示例：

行业专项规则
人工审核流程
自动纠错 / 重试
企业集成能力

说明：
P4 不属于 P3 的职责范围。

A.3 冻结状态枚举总表
A.3.1 reference_integrity_status

以下枚举为 P3 当前冻结状态集合：

clean
partial
unresolved
outside_pool
fabricated
clean

定义：
所有显式引用都成功归属到当前 ContextPool，未发现 unresolved / outside_pool / fabricated 问题。

partial

定义：
部分引用成功归属，但部分引用未能可靠归属。

unresolved

定义：
引用无法被可靠解析或归属，且未进入明确的 outside_pool 或 fabricated 路径。

outside_pool

定义：
检测到明确属于当前 ContextPool 之外的引用。

fabricated

定义：
检测到伪造引用路径。

A.3.2 severity

当前冻结等级枚举：

low
medium
high
critical

说明：

low：轻微风险或无风险
medium：中等风险，需要提示或人工关注
high：高风险，不应视为稳定通过
critical：关键风险，通常对应硬失败路径

当前建议：

clean → low
partial → medium
unresolved → high
outside_pool → critical
fabricated → critical
A.4 冻结 Trigger Code 总表

以下为当前冻结 trigger code 集合：

reference_member_not_found
citation_outside_context_pool
unresolved_reference_pointer
fabricated_reference_detected
reference_parse_failed
A.4.1 reference_member_not_found

含义：
引用解析得到的标识未在当前 ContextPool.members 中找到对应成员。

A.4.2 citation_outside_context_pool

含义：
检测到明确池外引用。

A.4.3 unresolved_reference_pointer

含义：
当前引用未能被可靠归属。

A.4.4 fabricated_reference_detected

含义：
检测到伪造引用路径。

A.4.5 reference_parse_failed

含义：
引用文本格式未能被当前解析器可靠解析。

A.5 冻结 Error Code 总表

以下为当前建议保留的 P3 相关主程序级错误码：

ERR_REFERENCE_OUTSIDE_CONTEXT_POOL
ERR_REFERENCE_UNRESOLVED
ERR_REFERENCE_FABRICATED
ERR_CONTEXT_POOL_INVALID
ERR_CONTEXT_POOL_EMPTY
ERR_CONTEXT_MEMBER_ID_DUPLICATED
ERR_P3_INPUT_INVALID
A.5.1 ERR_REFERENCE_OUTSIDE_CONTEXT_POOL

含义：
主程序根据 P3 结果判定存在池外引用错误。

A.5.2 ERR_REFERENCE_UNRESOLVED

含义：
主程序根据 P3 结果判定引用未能可靠归属。

A.5.3 ERR_REFERENCE_FABRICATED

含义：
主程序根据 P3 结果判定存在伪造引用。

A.5.4 ERR_CONTEXT_POOL_INVALID

含义：
宿主提供的 ContextPool 结构无效。

A.5.5 ERR_CONTEXT_POOL_EMPTY

含义：
宿主提供的 ContextPool 为空或缺失成员集合。

A.5.6 ERR_CONTEXT_MEMBER_ID_DUPLICATED

含义：
ContextPool.members 中存在重复 member_id。

A.5.7 ERR_P3_INPUT_INVALID

含义：
宿主传入 P3 的输入对象不满足基本结构约束。

A.6 冻结边界总表
A.6.1 P3 能做什么
项目	是否属于 P3
解析引用格式	是
将引用绑定到 ContextPool	是
判断 pool 内 / pool 外	是
标记 unresolved / fabricated	是
输出 P3Result	是
A.6.2 P3 不能做什么
项目	是否属于 P3
判断语义是否被支持	否
判断推理是否合理	否
判断真实世界正确性	否
自动修复引用	否
自动补全引用	否
调用外部系统查询补全	否
直接决定 allow / block	否
执行业务 fallback	否
引入行业专项规则	否
A.6.3 P2 / P3 / 主程序 / P4 边界表
能力	P2	P3	主程序	P4
语义支持判断	是	否	否	可扩展
引用归属判断	否	是	否	否
最终 verdict 生成	否	否	是	否
错误码统一映射	否	否	是	否
审计事件落盘	否	否	是	可扩展
行业专项规则	否	否	否	是
人工审核流程	否	否	否	是
自动纠错 / 重试	否	否	否	是
A.7 冻结接口总表
A.7.1 ContextMember
字段	类型	必填	含义
member_id	str	是	成员唯一 ID
source_id	str	是	来源 ID
content	str	是	成员内容
title	str | None	否	标题
metadata	dict[str, Any]	否	扩展元数据
A.7.2 ContextPool
字段	类型	必填	含义
pool_id	str	是	本轮上下文池 ID
members	list[ContextMember]	是	合法引用成员集合
retrieval_meta	dict[str, Any]	否	检索附加信息
A.7.3 HostP3Request
字段	类型	必填	含义
request_id	str	是	请求 ID
llm_output	str	是	最终待放行文本
context_pool	ContextPool	是	当前上下文池
decision_type	str	是	决策类型
action_risk	str	是	动作风险等级
metadata	dict[str, Any] | None	否	扩展信息
A.7.4 ReferenceClaim
字段	类型	必填	含义
raw_text	str	是	原始引用文本
ref_id	str | None	是	解析得到的引用 ID
position	int	是	在输出文本中的位置
A.7.5 ResolvedReference
字段	类型	必填	含义
ref_id	str	是	引用 ID
member	ContextMember	是	对应已归属成员
A.7.6 UnresolvedReference
字段	类型	必填	含义
raw_text	str	是	原始引用文本
reason	str	是	未归属原因
A.7.7 P3Result
字段	类型	必填	含义
plugin_name	str	是	插件/模块名
reference_integrity_status	str	是	P3 核心状态
resolved_members	list[str]	是	已归属成员 ID 列表
unresolved_members	list[str]	是	未归属引用列表
outside_pool_references	list[str]	是	池外引用列表
severity	str	是	风险等级
triggers	list[str]	是	触发器列表
reasons	list[str]	是	解释说明
metrics	dict[str, Any]	是	统计指标
A.8 冻结判断优先级提示

为了避免后续实现时重复争论，补充以下冻结提示：

P3 只判断引用归属，不判断语义支持。
P3 的唯一合法边界来源是 ContextPool。
P3 不能调用外部系统补全引用。
P3 不能自动修复输出。
P3 不直接生成最终业务 verdict。
P3 的 hard fail 语义不能被 P2 覆盖。
A.9 附录结论

本附录的意义，不在于增加功能，而在于提供一个稳定的“术语与枚举冻结层”。
后续在以下场景中，应优先回看本附录：

设计评审时确认名词口径
写代码时确认字段与状态含义
写 benchmark 时确认 expected 枚举
做版本升级时判断是否触碰冻结边界
做主程序集成时确认职责分层

如果前文某处表述与本附录冲突，应以显式更新后的附录版本为准，而不应各章各自为政。