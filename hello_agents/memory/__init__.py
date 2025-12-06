"""HelloAgents记忆系统模块

按照第8章架构设计的分层记忆系统：
- Memory Core Layer: 记忆核心层
- Memory Types Layer: 记忆类型层
- Storage Layer: 存储层
- Integration Layer: 集成层
- Mem0 AI Layer: Mem0 智能记忆层（可选）
"""

# Memory Core Layer (记忆核心层)
from .manager import MemoryManager

# Memory Types Layer (记忆类型层)
from .types.working import WorkingMemory
from .types.episodic import EpisodicMemory
from .types.semantic import SemanticMemory
from .types.perceptual import PerceptualMemory

# Mem0 AI Layer (可选依赖)
try:
    from .types.mem0 import Mem0Memory, Mem0MemoryConfig, is_mem0_available
    _MEM0_AVAILABLE = True
except ImportError:
    Mem0Memory = None
    Mem0MemoryConfig = None
    is_mem0_available = lambda: False
    _MEM0_AVAILABLE = False

# Storage Layer (存储层)
from .storage.document_store import DocumentStore, SQLiteDocumentStore

# Base classes and utilities
from .base import MemoryItem, MemoryConfig, BaseMemory

__all__ = [
    # Core Layer
    "MemoryManager",

    # Memory Types
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "PerceptualMemory",
    
    # Mem0 AI (可选)
    "Mem0Memory",
    "Mem0MemoryConfig",
    "is_mem0_available",

    # Storage Layer
    "DocumentStore",
    "SQLiteDocumentStore",

    # Base
    "MemoryItem",
    "MemoryConfig",
    "BaseMemory"
]
