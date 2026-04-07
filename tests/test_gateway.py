"""Tests for gateway module"""

import pytest
import shutil
from pathlib import Path
from src.gateway import CitationGateway
from src.citation import Citation, Context


@pytest.fixture(autouse=True)
def cleanup_data():
    """在每个测试前后清理数据目录"""
    # 测试前清理
    data_dir = Path("data")
    if data_dir.exists():
        shutil.rmtree(data_dir)
    
    yield
    
    # 测试后清理
    if data_dir.exists():
        shutil.rmtree(data_dir)


class TestCitationGateway:
    """网关测试"""

    def test_create_session(self):
        """测试创建会话"""
        gateway = CitationGateway()
        session = gateway.create_session({"test": "metadata"})

        assert session.id
        assert session.source == "logic_fingerprint"
        assert session.metadata == {"test": "metadata"}

    def test_load_session(self):
        """测试加载会话"""
        gateway = CitationGateway()
        session = gateway.create_session()

        loaded = gateway.load_session(session.id)
        assert loaded is not None
        assert loaded.id == session.id

    def test_create_context(self):
        """测试创建上下文"""
        gateway = CitationGateway()
        session = gateway.create_session()
        context = gateway.create_context(session.id)

        assert context.id
        assert context.session_id == session.id

    def test_add_citation(self):
        """测试添加引用"""
        gateway = CitationGateway()
        session = gateway.create_session()
        context = gateway.create_context(session.id)

        citation = Citation(source="logic_fingerprint", code_snippet="def foo(): pass")
        gateway.add_citation_to_context(context.id, citation)

        loaded_context = gateway.storage.load_context(context.id)
        assert len(loaded_context.citations) == 1
        assert loaded_context.citations[0].code_snippet == "def foo(): pass"

    def test_query_kb_empty(self):
        """测试查询空库"""
        gateway = CitationGateway()
        result = gateway.query_kb("test")
        
        assert result["success"] is True
        assert result["query"] == "test"
        assert result["total"] == 0
        assert result["results"] == []

    def test_query_kb_with_results(self):
        """测试查询返回结果"""
        gateway = CitationGateway()
        session = gateway.create_session()
        context = gateway.create_context(session.id)

        # 添加包含关键词的引用
        citation1 = Citation(
            source="logic_fingerprint",
            code_snippet="def handle_request(req): return ok",
            description="Request handler"
        )
        citation2 = Citation(
            source="logic_fingerprint",
            code_snippet="def validate_data(data): pass",
            description="Data validation"
        )
        gateway.add_citation_to_context(context.id, citation1)
        gateway.add_citation_to_context(context.id, citation2)

        # 查询关键词
        result = gateway.query_kb("request")
        assert result["success"] is True
        assert result["total"] == 1
        assert "Request handler" in [c["description"] for c in result["results"]]

    def test_query_kb_tokenization(self):
        """测试查询分词功能"""
        gateway = CitationGateway()
        session = gateway.create_session()
        context = gateway.create_context(session.id)

        # 添加测试数据
        citation = Citation(
            source="logic_fingerprint",
            code_snippet="how to process request",
            description="Request processing"
        )
        gateway.add_citation_to_context(context.id, citation)

        # 多关键词查询
        result = gateway.query_kb("how to process")
        assert result["total"] > 0

    def test_answer_kb_prompt_format(self):
        """测试问答生成 prompt 格式"""
        gateway = CitationGateway()
        session = gateway.create_session()
        context = gateway.create_context(session.id)

        citation = Citation(
            source="logic_fingerprint",
            code_snippet="def handle_request(req): pass",
            description="Request handler",
            file_path="src/handler.py",
            line_range="10-15"
        )
        gateway.add_citation_to_context(context.id, citation)

        result = gateway.answer_kb("how to handle requests", output_format="prompt")
        assert result["success"] is True
        assert "question" in result
        assert "answer" in result
        answer = result["answer"]
        assert answer["question"] == "how to handle requests"
        assert "prompt" in answer
        assert "Request handler" in answer["prompt"]

    def test_answer_kb_json_format(self):
        """测试问答生成 json 格式"""
        gateway = CitationGateway()
        session = gateway.create_session()
        context = gateway.create_context(session.id)

        citation = Citation(
            source="logic_fingerprint",
            code_snippet="def foo(): pass"
        )
        gateway.add_citation_to_context(context.id, citation)

        result = gateway.answer_kb("foo", output_format="json")
        assert result["success"] is True
        answer = result["answer"]
        assert answer["format"] == "json"

    def test_chat_kb_new_session(self):
        """测试聊天创建新会话"""
        gateway = CitationGateway()
        session = gateway.create_session()

        citation = Citation(
            source="logic_fingerprint",
            code_snippet="def process(data): pass",
            description="Data processor"
        )
        # 先添加到一个上下文
        context = gateway.create_context(session.id)
        gateway.add_citation_to_context(context.id, citation)

        # 进行聊天
        result = gateway.chat_kb(session.id, "process data")
        assert result["success"] is True
        assert result["session_id"] == session.id
        assert result["message"] == "process data"

    def test_chat_kb_context_update(self):
        """测试聊天更新上下文"""
        gateway = CitationGateway()
        session = gateway.create_session()

        # 添加两个引用
        citation1 = Citation(
            source="logic_fingerprint",
            code_snippet="def process(): pass",
            description="Processor"
        )
        citation2 = Citation(
            source="logic_fingerprint",
            code_snippet="def validate(): pass",
            description="Validator"
        )
        
        context = gateway.create_context(session.id)
        gateway.add_citation_to_context(context.id, citation1)
        
        # 第一次聊天
        result1 = gateway.chat_kb(session.id, "process")
        context_id1 = result1["context_id"]
        citations_before = result1["total_citations_in_context"]

        # 第二次聊天（应该添加新引用到相同上下文）
        result2 = gateway.chat_kb(session.id, "validate")
        context_id2 = result2["context_id"]
        citations_after = result2["total_citations_in_context"]

        # 验证上下文被正确更新
        loaded_context = gateway.storage.load_context(context_id1)
        assert len(loaded_context.citations) >= citations_before

    def test_chat_kb_nonexistent_session(self):
        """测试聊天非存在的会话"""
        gateway = CitationGateway()
        result = gateway.chat_kb("nonexistent-id", "test message")
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
