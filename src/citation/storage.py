"""File-based storage for citations and contexts"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .models import Citation, Context, Session


class FileStorage:
    """文件存储层"""

    def __init__(self, data_dir: str = "data"):
        """
        初始化文件存储

        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.sessions_dir = self.data_dir / "sessions"
        self.citations_dir = self.data_dir / "citations"
        self.contexts_dir = self.data_dir / "contexts"

        # 确保目录存在
        for dir_path in [self.sessions_dir, self.citations_dir, self.contexts_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    # ==================== Session Operations ====================

    def save_session(self, session: Session) -> None:
        """保存会话"""
        file_path = self.sessions_dir / f"{session.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

    def load_session(self, session_id: str) -> Optional[Session]:
        """加载会话"""
        file_path = self.sessions_dir / f"{session_id}.json"
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Session.from_dict(data)

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        file_path = self.sessions_dir / f"{session_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_sessions(self) -> List[str]:
        """列出所有会话ID"""
        return [f.stem for f in self.sessions_dir.glob("*.json")]

    # ==================== Context Operations ====================

    def save_context(self, context: Context) -> None:
        """保存上下文"""
        file_path = self.contexts_dir / f"{context.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(context.to_dict(), f, ensure_ascii=False, indent=2)

    def load_context(self, context_id: str) -> Optional[Context]:
        """加载上下文"""
        file_path = self.contexts_dir / f"{context_id}.json"
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Context.from_dict(data)

    def delete_context(self, context_id: str) -> bool:
        """删除上下文"""
        file_path = self.contexts_dir / f"{context_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_contexts(self) -> List[str]:
        """列出所有上下文ID"""
        return [f.stem for f in self.contexts_dir.glob("*.json")]

    # ==================== Citation Operations ====================

    def save_citation(self, citation: Citation, source: Optional[str] = None) -> None:
        """保存引用"""
        # 使用 source 组织目录结构
        if source is None:
            source = citation.source

        source_dir = self.citations_dir / source
        source_dir.mkdir(parents=True, exist_ok=True)

        file_path = source_dir / f"{citation.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(citation.to_dict(), f, ensure_ascii=False, indent=2)

    def load_citation(
        self, citation_id: str, source: Optional[str] = None
    ) -> Optional[Citation]:
        """加载引用"""
        if source:
            file_path = self.citations_dir / source / f"{citation_id}.json"
        else:
            # 如果未指定 source，遍历所有目录查找
            for source_dir in self.citations_dir.iterdir():
                if source_dir.is_dir():
                    file_path = source_dir / f"{citation_id}.json"
                    if file_path.exists():
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            return Citation.from_dict(data)
            return None

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Citation.from_dict(data)

    def list_citations(self, source: Optional[str] = None) -> List[str]:
        """列出引用ID"""
        if source:
            source_dir = self.citations_dir / source
            if source_dir.exists():
                return [f.stem for f in source_dir.glob("*.json")]
            return []
        else:
            # 列出所有来源的引用
            citations = []
            for source_dir in self.citations_dir.iterdir():
                if source_dir.is_dir():
                    citations.extend([f.stem for f in source_dir.glob("*.json")])
            return citations
