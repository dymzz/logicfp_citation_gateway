P3 下一步：主程序聚合约束
1. 目标

把 P2Result + P3Result 合并成主程序可消费的统一结果，明确：

谁优先
什么情况 block
什么情况 warn
什么情况允许继续走主链路
2. 必须先定死的规则
2.1 优先级
P3 > P2

原因：
P3 是硬约束。只要引用越界，语义再像也不能放。

2.2 最小聚合表
P3状态	P2状态	主程序verdict
outside_pool	任意	block
fabricated	任意	block
unresolved	supported/partial	warn
partial	supported	warn
clean	supported	allow
clean	partial/weak	warn
clean	unsupported	fallback 或 block
2.3 主程序只认统一出口

不要让 P2/P3 自己返回最终业务动作。
统一出口只保留：

verdict
trigger_codes
reason_codes
error_codes
3. 文档里要补的禁止项

加上这几条：

P2 不能覆盖 P3 的 hard fail
P3 不能直接产出最终业务响应
主程序不能跳过 P3 直接按 P2 放行
没有 ContextPool 时，P3 不降级为语义判断
4. 这一步产出物

你下一版文档只需要补 3 个小节：

P2/P3 聚合规则表
主程序统一 decision contract
聚合层禁止项