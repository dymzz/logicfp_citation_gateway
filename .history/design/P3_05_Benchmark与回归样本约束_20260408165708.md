# P3 Benchmark 与回归样本约束

## 5.1 本章目标

本章用于冻结 P3 Benchmark 的目标、样本边界、分类方式与最小结构要求，防止后续出现以下问题：

- benchmark 样本写成“想到什么测什么”的临时集合；
- 回归只看通过率，不看状态边界是否漂移；
- 样本混入语义判断、真实世界正确性判断、用户体验判断；
- 同一条 case 在不同机器、不同时间、不同人手里跑出不同结果；
- benchmark 被误用为“整体模型能力评估集”，导致 P3 职责失焦。

本章的目标不是追求样本数量最大化，而是保证：

**P3 的核心状态边界、引用归属规则、硬失败路径与可回归资产长期稳定。**

---

## 5.2 Benchmark 的定位（冻结）

P3 Benchmark 的正式定位是：

**围绕引用完整性边界的离线确定性验证集**

它服务于以下目标：

1. 验证当前实现是否仍满足冻结状态边界；
2. 验证当前实现是否仍能正确解析并绑定引用；
3. 验证 hard fail 路径是否仍然稳定；
4. 验证版本升级后是否发生状态漂移；
5. 验证失败是否集中在某一类样本或某一类路径。

因此，P3 Benchmark 不是：

- 语义正确率测试集；
- 用户体验测试集；
- 文风自然度测试集；
- 通用问答质量测试集；
- 大模型整体能力评估集。

---

## 5.3 Benchmark 只回答什么，不回答什么

### 5.3.1 P3 Benchmark 只回答以下问题

- 当前实现是否仍满足冻结状态边界；
- 当前实现是否仍能正确解析引用；
- 当前实现是否仍能把引用绑定到 ContextPool；
- 当前实现是否仍能稳定区分 clean / partial / unresolved / outside_pool / fabricated；
- 当前实现是否仍对 hard fail 路径保持阻断语义。

### 5.3.2 P3 Benchmark 不回答以下问题

- 模型整体效果提升了多少；
- 用户体验是否更好；
- 回答是否更自然；
- 语义正确率是否更高；
- 输出内容是否更像“聪明答案”；
- 真实世界事实是否正确。

这些问题不属于 P3 的职责，也不应污染 P3 Benchmark 的设计边界。

---

## 5.4 Benchmark 设计原则（冻结）

### 5.4.1 状态边界优先于表面通过率

P3 Benchmark 的核心不是“通过率看起来高不高”，而是：

**状态边界有没有被守住。**

如果某次升级让：

- `fabricated` 回退成 `unresolved`
- `outside_pool` 回退成 `partial`
- `clean` 被误伤成 `unresolved`

那么即使总体通过率看起来还可以，也应视为边界退化。

### 5.4.2 确定性优先于智能化补救

P3 Benchmark 只允许验证：

- 纯结构输入；
- 纯确定性解析；
- 纯本地引用归属；
- 纯离线输出。

不允许在 benchmark 执行中引入：

- 外部检索；
- 向量召回；
- LLM 辅助解释；
- 动态补全；
- 模糊修复；
- 人工中途改样本。

### 5.4.3 可复现优先于临时经验

同一条 case 在任何时间、任何机器、任何环境下，只要：

- `ContextPool` 相同；
- `llm_output` 相同；
- 规则版本相同；

就必须得到同样的 `P3Result`。

### 5.4.4 分类覆盖优先于样本堆积

P3 Benchmark 的首要目标不是先堆很多样本，而是先保证：

- 五大状态类都有覆盖；
- 每类样本内部有基础路径和边界路径；
- hard fail 类单独成组可追踪；
- 升级后能快速定位是哪一类先退化。

---

## 5.5 样本必须满足的基本约束

### 5.5.1 样本必须纯离线

每条样本都必须只依赖显式给定输入：

- `context_pool`
- `llm_output`
- 固定规则版本

不允许依赖：

- 外部检索；
- 数据库状态；
- 网络资源；
- 模型温度；
- 随机数；
- 上一条 case 的执行结果。

### 5.5.2 样本必须可复现

同一条样本应在：

- 本地开发环境；
- CI 环境；
- 后续版本回归环境；

中得到可比较的一致结果。

### 5.5.3 样本必须可解释

每条样本都应能回答三个问题：

1. 这条 case 在测什么；
2. 为什么预期状态是这个；
3. 如果失败，失败说明了哪条边界被破坏。

### 5.5.4 样本必须可长期维护

case 不应写成“只有当前作者自己看得懂”的临时材料。  
后续任何维护者都应能根据：

- `case_id`
- `description`
- `context_pool`
- `llm_output`
- `expected`

理解这条样本的测试意图。

---

## 5.6 样本最小结构（冻结）

建议将 benchmark 样本统一为以下结构：

```json
{
  "case_id": "p3_clean_001",
  "description": "single valid reference inside pool",
  "context_pool": {
    "pool_id": "pool_1",
    "members": [
      {"member_id": "doc_1", "source_id": "s1", "content": "aaa"},
      {"member_id": "doc_2", "source_id": "s2", "content": "bbb"}
    ]
  },
  "llm_output": "结论来自 [ref:doc_1]",
  "expected": {
    "reference_integrity_status": "clean",
    "resolved_members": ["doc_1"],
    "unresolved_members": [],
    "outside_pool_references": [],
    "triggers": []
  }
}
```
5.7 样本字段最小要求（冻结）

每条样本至少必须包含：

case_id
context_pool
llm_output
expected.reference_integrity_status

推荐补充：

description
expected.triggers
expected.resolved_members
expected.unresolved_members
expected.outside_pool_references

不建议在首版样本中强制加入：

大量解释性元数据；
语义判断结果；
用户侧展示字段；
与 P3 无关的业务字段。
5.8 case_id 规则（冻结）
5.8.1 case_id 必须稳定

case_id 必须：

全局唯一；
长期稳定；
不因描述优化而改变。

因为回归系统最终依赖 case_id 跟踪历史结果变化。

5.8.2 case_id 不应直接写成长描述

不建议将 case_id 写成可读句子本身。
建议使用稳定编号形式。

5.8.3 推荐命名规则

建议统一命名为：

p3_<status>_<serial>

例如：

p3_clean_001
p3_partial_003
p3_unresolved_002
p3_outside_pool_001
p3_fabricated_001
5.9 样本分类（冻结）

P3 Benchmark 必须至少覆盖以下五大类：

Clean
Partial
Unresolved
Outside_pool
Fabricated

这五类不是建议项，而是首版 benchmark 的最小覆盖面。

5.10 Clean 类样本
5.10.1 目标

验证所有显式引用都能被正确解析并绑定到当前 ContextPool。

5.10.2 最小覆盖点
单引用命中；
多引用全部命中；
引用顺序变化但结果不变；
重复引用同一成员；
无显式引用情况下的当前策略行为（若当前版本允许该路径存在，应单独说明）。
5.10.3 该类样本用于防止
正常合法引用被误判；
parser 升级后误伤基础路径；
resolver 对池内成员匹配失稳。
5.11 Partial 类样本
5.11.1 目标

验证“部分引用可归属，部分引用不可归属”的混合情况能够稳定落入 partial。

5.11.2 最小覆盖点
一个引用命中，一个引用未命中；
多引用中只有部分在池内；
部分解析成功，部分解析失败；
同时存在已归属引用和未归属引用。
5.11.3 该类样本用于防止
混合路径被误判成 clean；
混合路径被直接打成过重的硬失败；
局部异常吞没整体状态。
5.12 Unresolved 类样本
5.12.1 目标

验证引用无法被可靠解析或绑定，但又未进入明确 outside_pool 或 fabricated 路径时，能够稳定落入 unresolved。

5.12.2 最小覆盖点
引用格式解析失败；
引用 ID 不存在于当前 pool；
无法可靠归属但也不能明确认定为池外；
未命中但仍属于“未知/未解析”路径。
5.12.3 该类样本用于防止
unresolved 被误升级成 fabricated；
unresolved 被误降级成 partial 或 clean；
解析失败与归属失败混成不可追踪的杂类。
5.13 Outside_pool 类样本
5.13.1 目标

验证明确越过当前 ContextPool 边界的引用，能够稳定识别为 outside_pool。

5.13.2 最小覆盖点
明确引用池外成员；
明确带有池外语义标记的引用；
当前 pool 中无对应成员，且可明确判定为越界；
单池外引用与多池外引用路径。
5.13.3 该类样本用于防止
明确越界被误降级为 unresolved；
hard fail 路径被“温和化”；
主程序阻断语义失效。
5.14 Fabricated 类样本
5.14.1 目标

验证伪造引用路径能够稳定落入 fabricated，而不是被吞并到 unresolved。

5.14.2 最小覆盖点
明确伪造引用；
结构上像引用，但不应被视为合法成员；
带有 fake/fabricated 语义标记的引用路径；
应进入硬失败而非普通未归属路径的样本。
5.14.3 该类样本用于防止
fabricated 回退成 unresolved；
伪造路径被低估；
硬失败路径失去区分度。
5.15 样本分布要求（建议冻结）

首版 benchmark 不强求总样本数很大，但建议每一类至少都有：

基础样本；
边界样本；
易回归失败样本。

建议首版至少保证五类全覆盖，且不要出现：

只测 clean；
只测解析成功路径；
hard fail 类只有 1 条且没有备用样本；
fabricated / outside_pool 完全没有独立分组。

如果样本总量暂时有限，也应优先保证分类完整，而不是优先扩充同类重复样本。

5.16 expected 字段约束（冻结）

expected 至少必须冻结以下核心字段：

reference_integrity_status

推荐同时冻结：

resolved_members
unresolved_members
outside_pool_references
triggers

其中：

5.16.1 一级核心字段

reference_integrity_status
这是回归中最核心、最不可放松的比较字段。

5.16.2 二级辅助字段

resolved_members / unresolved_members / outside_pool_references / triggers
用于帮助解释失败、定位漂移来源、提高报告可读性。

5.16.3 不建议在本章强制冻结的字段
与主程序聚合相关的最终 verdict
与 P2 相关的语义支持字段
用户侧展示字段
与外部插件有关的扩展字段

因为本章只约束 P3 Benchmark，不扩展到主程序完整决策链。

5.17 样本与实现的边界关系

Benchmark 的职责不是“迎合当前实现”，而是：

守住冻结边界，并监督实现是否持续符合边界。

因此，不允许出现以下做法：

为了让当前实现通过而静默改写 expected；
为了减少失败数，把 hard fail 样本删掉；
为了兼容临时实现，把 fabricated 改成 unresolved；
用“这次先放宽一点”替代正式版本升级。

如果边界确实要改，应先更新正式设计文档与版本控制文档，再升级 benchmark，而不是反过来。

5.18 Benchmark 与版本控制的关系

P3 Benchmark 必须与版本控制绑定。
至少应记录：

benchmark_version
runner_version
code_version

原因是：

benchmark_version 表示样本集版本；
runner_version 表示执行器版本；
code_version 表示被测实现版本。

如果这些信息不清晰，则后续回归报告将无法可靠复盘，也无法准确判断是：

样本变化导致结果变化；
执行器变化导致结果变化；
还是被测代码本身发生了变化。
5.19 Benchmark 构建禁止项（冻结）

以下做法全部视为错误方向：

5.19.1 禁止把 Benchmark 做成半在线系统

不允许在跑样本时临时查外部数据、补 pool、补知识、补引用。

5.19.2 禁止引入语义评分或模型判断

P3 Benchmark 只测引用归属，不引入语义支持判断，不调用 LLM 决定 expected。

5.19.3 禁止让样本依赖执行顺序

每条 case 必须完全独立。
前一条样本的结果不得影响后一条样本。

5.19.4 禁止把失败解释写成口头经验

每类失败都应能落回：

状态边界；
触发器；
样本类别；
版本差异；

而不是“看起来不太对”。

5.19.5 禁止静默修改历史真值

历史 case 的 expected 不允许无版本说明地直接覆盖。
否则历史回归结果将失去可比较性。

5.20 本章结论

P3 Benchmark 不是“顺手写几条 case 的测试目录”，
而是 P3 工程边界的长期守卫资产。

本章应冻结四条原则：

Benchmark 只测引用完整性，不测语义能力；
样本必须纯离线、纯确定性、可复现；
五大状态类必须全部覆盖；
状态边界优先于表面通过率。