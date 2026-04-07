"""Tests for gateway module"""

import pytest
from src.gateway import CitationGateway
from src.citation import Citation, Context


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
        
        citation = Citation(
            source="logic_fingerprint",
            code_snippet="def foo(): pass"
        )
        gateway.add_citation_to_context(context.id, citation)
        
        loaded_context = gateway.storage.load_context(context.id)
        assert len(loaded_context.citations) == 1
        assert loaded_context.citations[0].code_snippet == "def foo(): pass"
