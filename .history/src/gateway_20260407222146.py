"""Main gateway implementation"""

import json
import re
from typing import Optional, Dict, Any, List
from .config import config
from .citation import Citation, Context, Session, FileStorage


class CitationGateway:
    """引用网关 - 核心服务入口"""

    def __init__(self, kb_source: Optional[str] = None):
        """
        初始化网关

        Args:
            kb_source: 知识库来源 (logic_fingerprint, logicfp_credibility, etc)
        """
        self.kb_source = kb_source or config.default_kb_source
        self.storage = FileStorage(str(config.data_dir))

    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """创建新会话"""
        session = Session(source=self.kb_source, metadata=metadata or {})
        self.storage.save_session(session)
        return session

    def load_session(self, session_id: str) -> Optional[Session]:
        """加载会话"""
        return self.storage.load_session(session_id)

    def create_context(
        self, session_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Context:
        """创建新上下文"""
        context = Context(session_id=session_id, metadata=metadata or {})
        self.storage.save_context(context)
        return context

    def add_citation_to_context(self, context_id: str, citation: Citation) -> None:
        """向上下文添加引用"""
        context = self.storage.load_context(context_id)
        if context:
            context.add_citation(citation)
            self.storage.save_context(context)
            # 同时保存引用到 citations 目录便于查询
            self.storage.save_citation(citation, source=citation.source)

    def query_kb(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        查询本地知识库（引用数据）

        Args:
            query: 查询字符串
            top_k: 返回结果数量

        Returns:
            查询结果列表
        """
        results = []
        
        # 将查询字符串分词（中英混合，简单按空格和中文字符分割）
        query_keywords = self._tokenize_query(query)
        
        # 遍历所有引用，进行关键词匹配
        all_citations = self.storage.list_citations()
        
        for citation_id in all_citations:
            citation = self.storage.load_citation(citation_id)
            if citation:
                # 结合 description 和 code_snippet 进行匹配
                search_text = f"{citation.description or ''} {citation.code_snippet}".lower()
                
                # 任意一个关键词匹配即算成功
                if any(keyword in search_text for keyword in query_keywords):
                    results.append(citation.to_dict())
        
        # 按创建时间倒序排列，返回 top_k 结果
        results = sorted(results, key=lambda x: x.get('timestamp', ''), reverse=True)[:top_k]
        
        return {
            "success": True,
            "query": query,
            "total": len(results),
            "results": results,
        }

    def _tokenize_query(self, query: str) -> List[str]:
        """
        将查询字符串分词

        Args:
            query: 查询字符串

        Returns:
            关键词列表
        """
        # 简单分词：移除空格和标点，支持中英混合
        # 保留字母、数字、中文
        query = re.sub(r'[^\w\u4e00-\u9fff]', ' ', query, flags=re.UNICODE)
        
        # 按空格分割并过滤空字符串
        keywords = [k.lower() for k in query.split() if k]
        
        return keywords if keywords else [query.lower()]

    def answer_kb(self, question: str, output_format: str = "prompt") -> Dict[str, Any]:
        """
        基于本地知识库生成问答

        Args:
            question: 问题
            output_format: 输出格式 (prompt, json, etc)

        Returns:
            问答结果
        """
        # 先查询相关引用
        query_result = self.query_kb(question, top_k=5)
        citations = query_result.get('results', [])
        
        # 构建问答响应
        answer_data = {
            "question": question,
            "source": self.kb_source,
            "related_citations": citations,
            "total_related": len(citations),
        }
        
        if output_format == "prompt":
            # Prompt 格式：组织成易用的提示词
            prompt = self._format_as_prompt(question, citations)
            answer_data["prompt"] = prompt
        elif output_format == "json":
            answer_data["format"] = "json"
        
        return {
            "success": True,
            "question": question,
            "answer": answer_data,
        }

    def chat_kb(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        基于本地知识库的多轮对话

        Args:
            session_id: 会话ID
            message: 消息内容

        Returns:
            对话结果和更新后的上下文
        """
        # 加载或创建会话
        session = self.storage.load_session(session_id)
        if not session:
            return {
                "success": False,
                "error": f"Session {session_id} not found",
            }
        
        # 基于消息进行本地查询
        query_result = self.query_kb(message, top_k=3)
        citations = query_result.get('results', [])
        
        # 创建或获取会话的上下文
        context_ids = session.context_ids
        if not context_ids:
            # 创建新上下文
            context = self.create_context(session_id)
            session.context_ids.append(context.id)
        else:
            context = self.storage.load_context(context_ids[-1])
        
        # 将相关引用添加到上下文
        for citation_data in citations:
            citation = Citation.from_dict(citation_data)
            context.add_citation(citation)
        
        # 保存更新
        self.storage.save_session(session)
        self.storage.save_context(context)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": message,
            "context_id": context.id,
            "related_citations": citations,
            "total_citations_in_context": len(context.citations),
        }

    def _format_as_prompt(self, question: str, citations: List[Dict[str, Any]]) -> str:
        """
        将查询结果格式化为提示词

        Args:
            question: 问题
            citations: 相关引用列表

        Returns:
            格式化的提示词
        """
        prompt_lines = [f"问题: {question}\n", "相关代码引用:\n"]
        
        for i, citation in enumerate(citations, 1):
            prompt_lines.append(f"\n[引用 {i}]")
            if citation.get('file_path'):
                prompt_lines.append(f"位置: {citation['file_path']}")
            if citation.get('line_range'):
                prompt_lines.append(f"行号: {citation['line_range']}")
            if citation.get('description'):
                prompt_lines.append(f"描述: {citation['description']}")
            prompt_lines.append(f"代码:\n```\n{citation['code_snippet']}\n```")
        
        return "\n".join(prompt_lines)
