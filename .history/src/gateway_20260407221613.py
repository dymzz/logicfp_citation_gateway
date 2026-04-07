"""Main gateway implementation"""

import json
import subprocess
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

    def query_kb(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        查询知识库

        Args:
            query: 查询字符串
            top_k: 返回结果数量

        Returns:
            查询结果
        """
        return self._execute_kb_command(
            "query",
            {
                "query": query,
                "top_k": top_k,
                "source": self.kb_source,
            }
        )

    def answer_kb(self, question: str, output_format: str = "prompt") -> Dict[str, Any]:
        """
        知识库问答

        Args:
            question: 问题
            output_format: 输出格式 (prompt, json, etc)

        Returns:
            问答结果
        """
        return self._execute_kb_command(
            "answer",
            {
                "question": question,
                "output_format": output_format,
                "source": self.kb_source,
            }
        )

    def chat_kb(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        知识库多轮对话

        Args:
            session_id: 会话ID
            message: 消息内容

        Returns:
            对话结果
        """
        return self._execute_kb_command(
            "chat",
            {
                "session_id": session_id,
                "message": message,
                "source": self.kb_source,
            }
        )

    def _execute_kb_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行知识库命令

        Args:
            command: 命令名称 (query, answer, chat)
            params: 命令参数

        Returns:
            命令执行结果
        """
        try:
            kb_home = config.get_kb_home()
            cmd = [
                "uv",
                "run",
                "--project",
                kb_home,
                "kb",
                command,
            ]
            
            result = subprocess.run(
                cmd,
                input=json.dumps(params),
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr or "Knowledge base command failed",
                    "command": command,
                }
            
            return {
                "success": True,
                "command": command,
                "data": json.loads(result.stdout) if result.stdout else {},
            }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Knowledge base command timeout",
                "command": command,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command,
            }
