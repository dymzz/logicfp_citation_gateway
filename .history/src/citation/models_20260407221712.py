"""Data models for citation and context management"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid


@dataclass
class Citation:
    """代码引用数据模型"""

    source: str  # 来源（如 logic_fingerprint）
    code_snippet: str  # 代码片段
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: Optional[str] = None
    file_path: Optional[str] = None  # 源文件路径
    line_range: Optional[str] = None  # 行号范围
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Citation":
        """从字典创建"""
        return Citation(**data)


@dataclass
class Context:
    """引用上下文数据模型"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    citations: List[Citation] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_citation(self, citation: Citation) -> None:
        """添加引用"""
        self.citations.append(citation)
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["citations"] = [c.to_dict() for c in self.citations]
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Context":
        """从字典创建"""
        citations = [Citation.from_dict(c) for c in data.pop("citations", [])]
        ctx = Context(**data)
        ctx.citations = citations
        return ctx


@dataclass
class Session:
    """会话数据模型"""

    source: str  # KB source (logic_fingerprint, credibility, etc)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    context_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Session":
        """从字典创建"""
        return Session(**data)
