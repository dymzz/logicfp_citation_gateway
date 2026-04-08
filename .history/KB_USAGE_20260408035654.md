# KB Usage For AI

这份说明给 AI / agent / 自动化脚本使用，目标是让它们直接会调用 `logicfp-kb`，而不是先读完整仓库结构。

## 1. 这个仓是做什么的

`logicfp-kb` 是本地代码知识库仓。

它会把多个代码仓打包、切块、建索引，然后提供 3 种主要调用方式：

- `query_kb.py`
  做代码检索，返回命中的 chunk
- `answer_kb.py`
  做单轮问答上下文打包，或直接调用模型回答
- `chat_kb.py`
  做多轮代码问答，带历史和 session 持久化

当前主要 source：

- `logic_fingerprint`
- `logicfp_credibility`

## 2. 什么时候该调用它

当你满足任一条件时，优先调用知识库，而不是只靠猜：

- 需要查某个类 / 函数 / 模块的实现
- 需要回答“这段逻辑在哪里、怎么流转”
- 需要跨仓理解主仓和插件仓的关系
- 需要从代码里找证据支持一个回答
- 需要进入多轮代码问答

如果只是简单列目录、改单文件、跑测试，不一定要先查知识库。

补充：

- `repomix` 采集默认会按 [repomix.md](/D:/workspace/python/logicfp-kb/repomix.md) 排除 `tests/`、`demo/`、`examples/`、`docs/`、`documents/`、`scripts/`、`static/`、`dist/`、`analysis/`、`.pytest_cache/`、`.tmp/`、Markdown、日志、minified 产物和常见大文件
- 所以 `input/sources/*/repomix-output.xml` 会更偏源码和真正有检索价值的实现文件
- Python 源码在 chunk 前还会去掉低价值注释噪声，但保留 docstring

## 3. 最常用命令

推荐先统一设置环境变量：

```powershell
$env:LOGICFP_KB_HOME = "D:\workspace\python\logicfp-kb"
```

如果已经写入 Windows 用户环境变量 `LOGICFP_KB_HOME`，重新打开终端后可直接使用。

默认在 `logicfp-kb` 根目录执行：

```powershell
uv run kb-query "middleware fallback decision flow" --top-k 5
uv run kb-answer "What does LogicFingerprintMiddleware.execute_handler_async do?" --source logic_fingerprint --output-format prompt
uv run kb-chat --source logic_fingerprint --session-id main-chat --mode prompt
```

如果从其他仓调用，推荐统一通过 `LOGICFP_KB_HOME` 指定知识库项目路径：

```powershell
uv run --project $env:LOGICFP_KB_HOME kb-query "middleware fallback decision flow" --source logic_fingerprint
uv run --project $env:LOGICFP_KB_HOME kb-answer "What does LogicFingerprintMiddleware.execute_handler_async do?" --source logic_fingerprint --output-format prompt
uv run --project $env:LOGICFP_KB_HOME kb-chat --source logic_fingerprint --session-id main-chat --mode prompt
```

路径说明：

- 文档里 `scripts/...` 的旧写法是相对 `logicfp-kb` 根目录的相对路径
- 现在更推荐用 `kb-query` / `kb-answer` / `kb-chat`
- 不需要把这三个脚本单独暴露到系统环境变量
- 推荐只暴露一个环境变量：`LOGICFP_KB_HOME`
- 只要通过 `uv run` 在本项目里执行，或者从其他仓用 `uv run --project $env:LOGICFP_KB_HOME` 调用即可

## 4. 该用哪个脚本

### `kb-query`

适合：

- 找实现位置
- 看 top-k 命中
- 手动检查检索质量

例子：

```powershell
uv run kb-query "validate output result data" --source logic_fingerprint --top-k 5
uv run kb-query "success hook contract result schema" --profile plugin_contracts --top-k 5
```

### `kb-answer`

适合：

- 单轮问答
- 给下游模型构造 prompt
- 想要“问题 + 检索证据 + 预期回答结构”

例子：

```powershell
uv run kb-answer "How does middleware validate result data?" --source logic_fingerprint --output-format prompt
uv run kb-answer "How does middleware validate result data?" --source logic_fingerprint --output-format both
```

如果环境里配置了 `OPENAI_API_KEY`，还可以：

```powershell
uv run kb-answer "How does middleware validate result data?" --source logic_fingerprint --output-format answer
```

### `kb-chat`

适合：

- 多轮追问
- 需要保留历史
- 想持续围绕同一个仓 / 同一类问题往下问

例子：

```powershell
uv run kb-chat --source logic_fingerprint --session-id main-chat --mode prompt
uv run kb-chat --profile plugin_contracts --session-id plugin-chat --mode prompt
```

## 5. `source` 和 `profile` 怎么选

### 优先按 `source`

当你已经知道问题属于哪个仓时，优先加 `--source`。

常用值：

- `logic_fingerprint`
- `logicfp_credibility`

例子：

```powershell
--source logic_fingerprint
```

### 其次按 `profile`

当你想按职责域过滤时，用 `--profile`。

当前常见值：

- `main_core`
- `plugin_contracts`

例子：

```powershell
--profile plugin_contracts
```

如果不确定，先不加过滤，让知识库全局检索。

## 6. 推荐调用顺序

### 场景 A：先定位，再回答

1. 先用 `kb-query` 看 top-k 是否合理
2. 再用 `kb-answer` 产 prompt 或 answer-context
3. 最后决定是否直答

### 场景 B：直接单轮问答

1. 直接调用 `kb-answer`
2. 默认先用 `--output-format prompt`
3. 如果已配置 `OPENAI_API_KEY`，再考虑 `--output-format answer`

### 场景 C：进入多轮模式

1. 用 `kb-chat`
2. 固定 `--session-id`
3. 一轮轮追问

## 7. 输出怎么理解

### `kb-query`

重点看：

- `file_path`
- `chunk_type`
- `symbol`
- `line_range`
- `content_type`

如果命中是 `src/...py` 且 `chunk_type` 是：

- `python_symbol`
- `python_symbol_window`

通常说明命中质量不错。

### `kb-answer`

如果输出 `prompt`：

- 这是给下游模型直接用的
- 已经带检索上下文

如果输出 `context`：

- 这是纯证据材料
- 适合自定义 prompt

### `kb-chat`

默认会：

- 带最近几轮历史
- 压缩更早轮次
- 持久化 session 到：

```text
cache/chat_sessions/<session-id>.json
```

## 8. 多轮 session 规则

如果使用 `chat_kb.py`：

- 用 `--session-id` 指定稳定会话名
- 不同任务不要复用同一个 session
- 想从头开始可用：

```text
/clear
```

也可以临时禁用持久化：

```powershell
uv run kb-chat --source logic_fingerprint --no-persist
```

## 9. 推荐默认值

对 AI / agent，推荐默认策略：

- 单轮问题：
  先用 `kb-answer --output-format prompt`
- 不确定范围：
  不加 `--source`
- 已知主仓：
  `--source logic_fingerprint`
- 已知插件契约：
  `--profile plugin_contracts`
- 多轮问题：
  `kb-chat --mode prompt --session-id <task-name>`

## 10. 一个最小工作流模板

```powershell
# 1. 先检索
uv run kb-query "your question" --top-k 5

# 2. 再产单轮回答 prompt
uv run kb-answer "your question" --output-format prompt

# 3. 如果需要多轮追问
uv run kb-chat --session-id your-task --mode prompt
```

## 11. 当前限制

- 当前仍是命令行入口，不是正式 Python API
- `answer_kb.py --output-format answer` 依赖 `OPENAI_API_KEY`
- 检索底层仍是 `jsonl + npy`
- 长会话虽然已做压缩，但还没有更高级的记忆检索

## 12. 一句话建议

如果你是其他仓里的 AI：

- 先把 `logicfp-kb` 当外部命令行知识库用
- 优先依赖 `LOGICFP_KB_HOME`，不要硬编码知识库仓绝对路径
- 单轮用 `kb-answer`
- 多轮用 `kb-chat`
- 需要证据时回看 `kb-query`
