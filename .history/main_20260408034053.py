#!/usr/bin/env python3
"""
logicfp-citation-gateway 演示应用入口
"""

from src.gateway import CitationGateway
from src.citation import Citation
import json


def main():
    """演示网关基本功能"""

    print("=" * 60)
    print("logicfp-citation-gateway 演示")
    print("=" * 60)

    # 初始化网关
    gateway = CitationGateway(kb_source="logic_fingerprint")
    print("\n✓ 网关初始化成功")

    # 创建会话
    session = gateway.create_session({"demo": "example"})
    print(f"\n✓ 创建会话: {session.id}")
    print(f"  来源: {session.source}")
    print(f"  创建时间: {session.created_at}")

    # 创建上下文
    context = gateway.create_context(session.id)
    print(f"\n✓ 创建上下文: {context.id}")
    print(f"  会话ID: {context.session_id}")

    # 添加多个引用示例
    citations_data = [
        {
            "source": "logic_fingerprint",
            "code_snippet": "def handle_request(req): return {'status': 'ok'}",
            "description": "Example request handler",
            "file_path": "src/handlers.py",
            "line_range": "42-45",
        },
        {
            "source": "logic_fingerprint",
            "code_snippet": "def validate_input(data): return len(data) > 0",
            "description": "Input validation function",
            "file_path": "src/validators.py",
            "line_range": "10-12",
        },
        {
            "source": "logic_fingerprint",
            "code_snippet": "class RequestHandler: def process(self, req): pass",
            "description": "Main request handler class",
            "file_path": "src/core.py",
            "line_range": "1-5",
        },
    ]

    print(f"\n✓ 添加 {len(citations_data)} 个引用:")
    for i, citation_data in enumerate(citations_data, 1):
        citation = Citation(**citation_data)
        gateway.add_citation_to_context(context.id, citation)
        print(f"  [{i}] {citation.id[:8]}... - {citation.description}")

    # 演示 query_kb - 查询本地知识库
    print(f"\n✓ 本地查询演示:")
    query_result = gateway.query_kb("request", top_k=3)
    print(f"  查询: 'request'")
    print(f"  找到 {query_result['total']} 条结果:")
    for i, result in enumerate(query_result["results"], 1):
        print(f"    [{i}] {result['description']}")

    # 演示 answer_kb - 生成问答
    print(f"\n✓ 问答演示:")
    answer_result = gateway.answer_kb("如何处理 request", output_format="prompt")
    print(f"  问题: '如何处理 request'")
    print(f"  找到 {answer_result['answer']['total_related']} 条相关引用")
    print(f"  Prompt 预览:\n")
    print(answer_result["answer"]["prompt"][:300] + "...")

    # 演示 chat_kb - 多轮对话
    print(f"\n✓ 多轮对话演示:")
    chat_result = gateway.chat_kb(session.id, "validator 如何工作")
    print(f"  消息: 'validator 如何工作'")
    print(f"  找到 {len(chat_result['related_citations'])} 条相关引用")
    print(f"  上下文中现有 {chat_result['total_citations_in_context']} 条引用")

    # 加载并验证
    loaded_session = gateway.load_session(session.id)
    loaded_context = gateway.storage.load_context(context.id)

    print(f"\n✓ 加载验证成功")
    print(f"  会话中包含的上下文ID: {loaded_session.context_ids}")
    print(f"  上下文中的引用数: {len(loaded_context.citations)}")

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
