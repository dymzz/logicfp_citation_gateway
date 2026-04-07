# logicfp-citation-gateway 使用指南

## 概念澄清

### logicfp-kb vs logicfp-citation-gateway

| 项目 | logicfp-kb | logicfp-citation-gateway |
|------|-----------|-------------------------|
| **职责** | 外部代码知识库（全量索引） | 本地引用管理（缓存和上下文） |
| **数据来源** | 从多个代码仓采集、建索引 | 手动添加或从知识库导入 |
| **查询范围** | 全量知识库检索 | 本地已导入的引用 |
| **存储形式** | 向量数据库/索引 | JSON 文件 |
| **用途** | 代码搜索、问答、反思 | 会话管理、引用追踪、缓存 |

## 何时使用本项目

### ✅ 使用场景

- 需要**保存和追踪**代码引用
- 需要维护**多轮对话**的上下文
- 需要将知识库查询结果**持久化**
- 需要在**不同会话**间重用引用
- 需要简单的**本地引用搜索**
- 需要为代码审查/问题诊断**记录证据**

### ❌ 不适用场景

- 需要全量代码库搜索 → 用 `logicfp-kb`
- 需要向量相似度检索 → 用 `logicfp-kb`
- 需要深度代码分析 → 用 `logicfp-kb`

## 核心功能

### 1. 创建和管理会话

```python
from src.gateway import CitationGateway

gateway = CitationGateway(kb_source="logic_fingerprint")

# 创建会话（对应一次代码审查、一个问题、一轮对话等）
session = gateway.create_session(metadata={
    "task": "code_review_PR#123",
    "reviewer": "alice"
})

# 为会话创建上下文
context = gateway.create_context(session.id)
```

### 2. 添加代码引用

```python
from src.citation import Citation

# 从知识库查询或手动创建引用
citation = Citation(
    source="logic_fingerprint",
    code_snippet="def handle_request(...): ...",
    description="HTTP 请求入口处理",
    file_path="src/gateway.py",
    line_range="10-45"
)

gateway.add_citation_to_context(context.id, citation)
```

### 3. 查询本地引用库

```python
# 关键词搜索（支持中英混合、分词）
result = gateway.query_kb("request handler", top_k=5)

for citation in result["results"]:
    print(f"{citation['description']}: {citation['file_path']}:{citation['line_range']}")
```

### 4. 生成问答

```python
# 生成 Prompt 格式（用于下游 AI 模型）
answer = gateway.answer_kb("请求处理流程如何工作", output_format="prompt")
print(answer["answer"]["prompt"])

# 生成 JSON 格式
answer = gateway.answer_kb("请求处理流程如何工作", output_format="json")
```

### 5. 多轮对话

```python
# 第一轮对话
result1 = gateway.chat_kb(session.id, "请求如何处理")
print(f"找到 {len(result1['related_citations'])} 条相关引用")

# 第二轮（自动维护上下文）
result2 = gateway.chat_kb(session.id, "验证逻辑在哪里")
print(f"上下文现有 {result2['total_citations_in_context']} 条引用")

# 加载历史会话继续问答
loaded_session = gateway.load_session(session.id)
```

## 与 logicfp-kb 的集成（未来规划）

目前本项目**不直接调用** `logicfp-kb`，但未来可以添加导入功能：

```python
# ⚠️ 规划中，暂未实现

# 从知识库导入查询结果
kb_results = gateway.import_from_kb("request validation", source="logic_fingerprint")

# 将 KB 结果添加到本地引用库
for kb_citation in kb_results:
    citation = Citation.from_kb_result(kb_citation)
    gateway.add_citation_to_context(context.id, citation)
```

## 数据组织

所有数据存储在 `data/` 目录，结构如下：

```
data/
├── sessions/              # 会话元数据
│   └── {session_id}.json
├── citations/             # 代码引用（按来源分组）
│   ├── logic_fingerprint/
│   │   └── {citation_id}.json
│   └── logicfp_credibility/
│       └── {citation_id}.json
└── contexts/              # 上下文数据
    └── {context_id}.json
```

## 开发和调试

### 运行演示

```bash
python main.py
```

### 运行测试

```bash
pytest tests/ -v
```

### 查看数据文件

生成的数据都是 JSON，可以直接查看：

```bash
cat data/sessions/{session_id}.json
cat data/contexts/{context_id}.json
```

## 常见工作流

### 工作流 1：代码审查

```python
# 审查者开始审查
gateway = CitationGateway()
session = gateway.create_session(metadata={"review": "PR#456"})
context = gateway.create_context(session.id)

# 审查过程中记录关键代码引用
for finding in review_findings:
    citation = Citation(
        source="logic_fingerprint",
        code_snippet=finding.code,
        description=finding.issue,
        file_path=finding.file,
        line_range=finding.lines
    )
    gateway.add_citation_to_context(context.id, citation)

# 生成审查总结
answer = gateway.answer_kb("代码审查发现了什么问题", output_format="prompt")
print(answer["answer"]["prompt"])
```

### 工作流 2：问题诊断

```python
# 用户报告问题
gateway = CitationGateway()
session = gateway.create_session(metadata={"issue": "BUG#789"})

# 诊断过程中多轮查询相关代码
chat1 = gateway.chat_kb(session.id, "错误日志: AttributeError in request handler")
chat2 = gateway.chat_kb(session.id, "该类的初始化逻辑是什么")
chat3 = gateway.chat_kb(session.id, "调用流程的依赖关系")

# 查看诊断历史
loaded = gateway.load_session(session.id)
for context_id in loaded.context_ids:
    ctx = gateway.storage.load_context(context_id)
    print(f"引用数: {len(ctx.citations)}")
```

### 工作流 3：文档生成

```python
# 生成 API 文档
gateway = CitationGateway()
session = gateway.create_session(metadata={"doc": "API_reference"})
context = gateway.create_context(session.id)

# 导入相关引用（来自知识库或手动）
api_functions = [...]
for func in api_functions:
    gateway.add_citation_to_context(context.id, func)

# 生成文档 Prompt
answer = gateway.answer_kb("生成 API 函数签名和用法", output_format="prompt")
```

## 配置

### 环境变量

虽然本项目目前不调用 `logicfp-kb`，但为了兼容性，推荐设置：

```bash
# Windows PowerShell
$env:LOGICFP_KB_HOME = "D:\workspace\python\logicfp-kb"

# Linux/Mac
export LOGICFP_KB_HOME="/path/to/logicfp-kb"
```

注：如果不设置，本项目仍然可以正常运行，只是一些未来的 KB 集成功能会不可用。

## 数据迁移和备份

由于所有数据都是 JSON 文件，可以直接备份：

```bash
# 备份所有会话和引用
cp -r data/ data.backup.$(date +%Y%m%d)

# 恢复
cp -r data.backup.20260407/* data/
```

## API 完整参考

见 [README.md](README.md) 的 "API 文档" 部分
