"""记忆类型层模块

按照第8章架构设计的记忆类型层：
- WorkingMemory: 工作记忆 - 短期上下文管理
- EpisodicMemory: 情景记忆 - 具体交互事件存储
- SemanticMemory: 语义记忆 - 抽象知识和概念存储
- PerceptualMemory: 感知记忆 - 多模态数据存储
- Mem0Memory: Mem0 AI 记忆 - 智能对话记忆管理
"""

from .working import WorkingMemory
from .episodic import EpisodicMemory, Episode
from .semantic import SemanticMemory, Entity, Relation
from .perceptual import PerceptualMemory, Perception

# Mem0 AI 记忆（可选依赖）
try:
    from .mem0 import Mem0Memory, Mem0MemoryConfig, is_mem0_available
    _MEM0_AVAILABLE = True
except ImportError:
    Mem0Memory = None
    Mem0MemoryConfig = None
    is_mem0_available = lambda: False
    _MEM0_AVAILABLE = False

__all__ = [
    # 记忆类型
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "PerceptualMemory",
    "Mem0Memory",
    "Mem0MemoryConfig",
    "is_mem0_available",

    # 辅助类
    "Episode",
    "Entity",
    "Relation",
    "Perception"
]
