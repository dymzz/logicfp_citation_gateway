"""Configuration management"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """应用配置"""

    def __init__(self):
        """初始化配置"""
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"

        # Knowledge base configuration
        self.kb_home = os.getenv("LOGICFP_KB_HOME", "")
        self.kb_sources = ["logic_fingerprint", "logicfp_credibility"]

        # Default KB source
        self.default_kb_source = "logic_fingerprint"

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_kb_home(self) -> str:
        """获取知识库主目录"""
        if not self.kb_home:
            raise ValueError("LOGICFP_KB_HOME environment variable not set")
        return self.kb_home

    def is_kb_available(self) -> bool:
        """检查知识库是否可用"""
        return bool(self.kb_home) and Path(self.kb_home).exists()


# Global config instance
config = Config()
