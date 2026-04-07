#!/usr/bin/env python3
"""
logicfp-citation-gateway 演示应用入口
"""

from src.gateway import CitationGateway
from src.citation import Citation


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
    
    # 添加引用
    citation = Citation(
        source="logic_fingerprint",
        code_snippet="def handle_request(req): return {'status': 'ok'}",
        description="Example request handler",
        file_path="src/handlers.py",
        line_range="42-45"
    )
    gateway.add_citation_to_context(context.id, citation)
    print(f"\n✓ 添加引用: {citation.id}")
    print(f"  代码: {citation.code_snippet}")
    print(f"  位置: {citation.file_path}:{citation.line_range}")
    
    # 加载并验证
    loaded_session = gateway.load_session(session.id)
    loaded_context = gateway.storage.load_context(context.id)
    
    print(f"\n✓ 加载验证成功")
    print(f"  会话中包含的上下文ID: {loaded_session.context_ids if hasattr(loaded_session, 'context_ids') else 'N/A'}")
    print(f"  上下文中的引用数: {len(loaded_context.citations)}")
    
    print("\n" + "=" * 60)
    print("演示完成！可通过以下方式扩展:")
    print("  1. 实现 KB 集成 (query_kb, answer_kb, chat_kb)")
    print("  2. 添加引用链接和依赖跟踪")
    print("  3. 集成 API 接口")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
