"""Mem0 AI 记忆系统集成

集成 mem0ai 库，提供智能化的记忆存储、检索和管理功能。
Mem0 提供了一个强大的记忆层，支持：
- 智能记忆提取和存储
- 语义搜索和检索
- 用户级别的记忆隔离
- 自动记忆组织和关联
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import os

from ..base import BaseMemory, MemoryItem, MemoryConfig

logger = logging.getLogger(__name__)

# 检查 mem0ai 是否可用
_MEM0_AVAILABLE = False
_Memory = None

try:
    from mem0 import Memory as Mem0Memory_Core
    _Memory = Mem0Memory_Core
    _MEM0_AVAILABLE = True
except ImportError:
    logger.warning("mem0ai 未安装，Mem0Memory 功能将不可用。请运行: pip install mem0ai")


class Mem0MemoryConfig(MemoryConfig):
    """Mem0 记忆系统配置
    
    扩展基础配置，添加 Mem0 特有的配置项。
    """
    
    # Mem0 配置
    mem0_api_key: Optional[str] = None  # Mem0 Cloud API Key
    mem0_org_id: Optional[str] = None   # Mem0 组织ID
    mem0_project_id: Optional[str] = None  # Mem0 项目ID
    
    # 本地模式配置
    use_local_mode: bool = True  # 是否使用本地模式（不需要API Key）
    
    # LLM 配置（本地模式）
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    
    # 嵌入模型配置（本地模式）
    embedder_provider: str = "openai"
    embedder_model: str = "text-embedding-3-small"
    embedder_api_key: Optional[str] = None
    embedder_base_url: Optional[str] = None
    
    # 向量存储配置（本地模式）
    vector_store_provider: str = "qdrant"  # qdrant, chroma, pgvector
    vector_store_config: Dict[str, Any] = {}
    
    # 图存储配置（可选）
    enable_graph: bool = False
    graph_store_provider: str = "neo4j"
    graph_store_config: Dict[str, Any] = {}


class Mem0Memory(BaseMemory):
    """Mem0 AI 记忆系统
    
    基于 mem0ai 库的智能记忆系统，特点：
    - 自动从对话中提取和存储重要信息
    - 基于语义的智能检索
    - 支持用户级别的记忆隔离
    - 可配置本地或云端模式
    
    使用示例：
        ```python
        from hello_agents.memory import Mem0Memory, Mem0MemoryConfig
        
        # 本地模式（使用 OpenAI 兼容的 API）
        config = Mem0MemoryConfig(
            use_local_mode=True,
            llm_provider="openai",
            llm_model="gpt-4o-mini",
        )
        memory = Mem0Memory(config, user_id="user_123")
        
        # 添加记忆
        memory.add_from_messages([
            {"role": "user", "content": "我喜欢Python编程"},
            {"role": "assistant", "content": "Python是一门很棒的语言！"}
        ])
        
        # 检索相关记忆
        results = memory.retrieve("编程语言偏好")
        ```
    """
    
    def __init__(
        self, 
        config: Optional[Mem0MemoryConfig] = None,
        user_id: str = "default_user",
        storage_backend=None
    ):
        """初始化 Mem0 记忆系统
        
        Args:
            config: Mem0 配置对象
            user_id: 用户ID，用于隔离不同用户的记忆
            storage_backend: 存储后端（可选，Mem0 有自己的存储）
        """
        self.mem0_config = config or Mem0MemoryConfig()
        super().__init__(self.mem0_config, storage_backend)
        
        self.user_id = user_id
        self._client: Optional[Any] = None
        self._local_memories: List[MemoryItem] = []  # 本地缓存
        
        # 初始化 Mem0 客户端
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化 Mem0 客户端"""
        if not _MEM0_AVAILABLE:
            logger.warning("mem0ai 未安装，将使用本地缓存模式")
            return
        
        try:
            if self.mem0_config.use_local_mode:
                # 本地模式配置
                mem0_config = self._build_local_config()
                self._client = _Memory.from_config(mem0_config)
                logger.info("Mem0 本地模式初始化成功")
            else:
                # 云端模式
                api_key = self.mem0_config.mem0_api_key or os.getenv("MEM0_API_KEY")
                if not api_key:
                    raise ValueError("Mem0 Cloud 模式需要提供 API Key")
                
                from mem0 import MemoryClient
                self._client = MemoryClient(api_key=api_key)
                logger.info("Mem0 Cloud 模式初始化成功")
                
        except Exception as e:
            logger.error(f"Mem0 初始化失败: {e}")
            self._client = None
    
    def _build_local_config(self) -> Dict[str, Any]:
        """构建本地模式配置"""
        # 从环境变量或配置获取 API Key
        llm_api_key = (
            self.mem0_config.llm_api_key or 
            os.getenv("OPENAI_API_KEY") or 
            os.getenv("LLM_API_KEY")
        )
        llm_base_url = (
            self.mem0_config.llm_base_url or 
            os.getenv("OPENAI_BASE_URL") or 
            os.getenv("LLM_BASE_URL")
        )
        
        embedder_api_key = (
            self.mem0_config.embedder_api_key or 
            llm_api_key
        )
        embedder_base_url = (
            self.mem0_config.embedder_base_url or 
            llm_base_url
        )
        
        config = {
            "llm": {
                "provider": self.mem0_config.llm_provider,
                "config": {
                    "model": self.mem0_config.llm_model,
                }
            },
            "embedder": {
                "provider": self.mem0_config.embedder_provider,
                "config": {
                    "model": self.mem0_config.embedder_model,
                }
            },
            "vector_store": {
                "provider": self.mem0_config.vector_store_provider,
                "config": self.mem0_config.vector_store_config or {
                    "collection_name": "mem0_memories",
                }
            }
        }
        
        # 添加 API Key 和 Base URL
        if llm_api_key:
            config["llm"]["config"]["api_key"] = llm_api_key
        if llm_base_url:
            config["llm"]["config"]["openai_base_url"] = llm_base_url
            
        if embedder_api_key:
            config["embedder"]["config"]["api_key"] = embedder_api_key
        if embedder_base_url:
            config["embedder"]["config"]["openai_base_url"] = embedder_base_url
        
        # 图存储配置（可选）
        if self.mem0_config.enable_graph:
            config["graph_store"] = {
                "provider": self.mem0_config.graph_store_provider,
                "config": self.mem0_config.graph_store_config or {}
            }
        
        return config
    
    @property
    def is_available(self) -> bool:
        """检查 Mem0 是否可用"""
        return self._client is not None
    
    def add(self, memory_item: MemoryItem) -> str:
        """添加记忆项
        
        Args:
            memory_item: 记忆项对象
            
        Returns:
            记忆ID
        """
        # 添加到本地缓存
        self._local_memories.append(memory_item)
        
        if not self.is_available:
            logger.debug(f"Mem0 不可用，记忆仅存储在本地缓存: {memory_item.id[:8]}...")
            return memory_item.id
        
        try:
            # 使用 Mem0 添加记忆
            messages = [
                {"role": "user", "content": memory_item.content}
            ]
            
            metadata = memory_item.metadata.copy()
            metadata["importance"] = memory_item.importance
            metadata["memory_type"] = memory_item.memory_type
            metadata["timestamp"] = memory_item.timestamp.isoformat()
            
            result = self._client.add(
                messages=messages,
                user_id=self.user_id,
                metadata=metadata
            )
            
            # 如果 Mem0 返回了 ID，更新本地记录
            if result and isinstance(result, dict) and "results" in result:
                for r in result.get("results", []):
                    if "id" in r:
                        memory_item.metadata["mem0_id"] = r["id"]
                        break
            
            logger.debug(f"记忆已添加到 Mem0: {memory_item.id[:8]}...")
            return memory_item.id
            
        except Exception as e:
            logger.warning(f"添加记忆到 Mem0 失败: {e}")
            return memory_item.id
    
    def add_from_messages(
        self,
        messages: List[Dict[str, str]],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """从对话消息中提取并添加记忆
        
        这是 Mem0 的核心功能 - 自动从对话中提取重要信息并存储。
        
        Args:
            messages: 对话消息列表，格式为 [{"role": "user/assistant", "content": "..."}]
            user_id: 用户ID（可选，使用实例默认值）
            agent_id: Agent ID（可选）
            run_id: 运行ID（可选）
            metadata: 额外的元数据
            
        Returns:
            Mem0 返回的结果
        """
        if not self.is_available:
            # 回退到本地存储
            for msg in messages:
                content = msg.get("content", "")
                if content:
                    memory_item = MemoryItem(
                        id=self._generate_id(),
                        content=content,
                        memory_type="mem0",
                        user_id=user_id or self.user_id,
                        timestamp=datetime.now(),
                        importance=0.5,
                        metadata={
                            "role": msg.get("role", "user"),
                            **(metadata or {})
                        }
                    )
                    self._local_memories.append(memory_item)
            
            return {"status": "stored_locally", "count": len(messages)}
        
        try:
            result = self._client.add(
                messages=messages,
                user_id=user_id or self.user_id,
                agent_id=agent_id,
                run_id=run_id,
                metadata=metadata
            )
            
            # 同步到本地缓存
            if result and isinstance(result, dict) and "results" in result:
                for r in result.get("results", []):
                    memory_item = MemoryItem(
                        id=r.get("id", self._generate_id()),
                        content=r.get("memory", ""),
                        memory_type="mem0",
                        user_id=user_id or self.user_id,
                        timestamp=datetime.now(),
                        importance=0.7,
                        metadata={
                            "mem0_id": r.get("id"),
                            "event": r.get("event"),
                            **(metadata or {})
                        }
                    )
                    self._local_memories.append(memory_item)
            
            return result
            
        except Exception as e:
            logger.error(f"添加消息到 Mem0 失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def retrieve(
        self, 
        query: str, 
        limit: int = 5,
        user_id: Optional[str] = None,
        **kwargs
    ) -> List[MemoryItem]:
        """检索相关记忆
        
        Args:
            query: 查询内容
            limit: 返回数量限制
            user_id: 用户ID（可选）
            **kwargs: 其他参数（min_importance 等）
            
        Returns:
            相关记忆列表
        """
        results = []
        
        if self.is_available:
            try:
                search_result = self._client.search(
                    query=query,
                    user_id=user_id or self.user_id,
                    limit=limit
                )
                
                # 转换为 MemoryItem
                memories = search_result.get("results", []) if isinstance(search_result, dict) else search_result
                
                for mem in memories:
                    if isinstance(mem, dict):
                        memory_item = MemoryItem(
                            id=mem.get("id", self._generate_id()),
                            content=mem.get("memory", ""),
                            memory_type="mem0",
                            user_id=mem.get("user_id", user_id or self.user_id),
                            timestamp=datetime.fromisoformat(
                                mem.get("created_at", datetime.now().isoformat()).replace("Z", "+00:00")
                            ) if "created_at" in mem else datetime.now(),
                            importance=mem.get("score", 0.5),
                            metadata={
                                "mem0_id": mem.get("id"),
                                "score": mem.get("score"),
                                **mem.get("metadata", {})
                            }
                        )
                        results.append(memory_item)
                        
            except Exception as e:
                logger.warning(f"Mem0 检索失败: {e}")
        
        # 如果 Mem0 检索失败或结果不足，从本地缓存补充
        if len(results) < limit:
            min_importance = kwargs.get("min_importance", 0.0)
            query_lower = query.lower()
            
            for mem in self._local_memories:
                if mem.importance >= min_importance:
                    if query_lower in mem.content.lower():
                        if mem not in results:
                            results.append(mem)
                            if len(results) >= limit:
                                break
        
        return results[:limit]
    
    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Mem0 原生搜索接口
        
        Args:
            query: 搜索查询
            user_id: 用户ID
            agent_id: Agent ID
            limit: 结果数量限制
            
        Returns:
            Mem0 搜索结果列表
        """
        if not self.is_available:
            # 返回本地缓存中匹配的结果
            results = []
            query_lower = query.lower()
            for mem in self._local_memories:
                if query_lower in mem.content.lower():
                    results.append({
                        "id": mem.id,
                        "memory": mem.content,
                        "user_id": mem.user_id,
                        "score": 0.5,
                        "metadata": mem.metadata
                    })
                    if len(results) >= limit:
                        break
            return results
        
        try:
            result = self._client.search(
                query=query,
                user_id=user_id or self.user_id,
                agent_id=agent_id,
                limit=limit
            )
            return result.get("results", []) if isinstance(result, dict) else result
            
        except Exception as e:
            logger.error(f"Mem0 搜索失败: {e}")
            return []
    
    def get_all(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取所有记忆
        
        Args:
            user_id: 用户ID
            agent_id: Agent ID
            limit: 结果数量限制
            
        Returns:
            所有记忆列表
        """
        if not self.is_available:
            return [
                {
                    "id": mem.id,
                    "memory": mem.content,
                    "user_id": mem.user_id,
                    "metadata": mem.metadata
                }
                for mem in self._local_memories[:limit]
            ]
        
        try:
            result = self._client.get_all(
                user_id=user_id or self.user_id,
                agent_id=agent_id,
                limit=limit
            )
            return result.get("results", []) if isinstance(result, dict) else result
            
        except Exception as e:
            logger.error(f"获取所有记忆失败: {e}")
            return []
    
    def update(
        self,
        memory_id: str,
        content: str = None,
        importance: float = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """更新记忆
        
        Args:
            memory_id: 记忆ID
            content: 新内容
            importance: 新重要性
            metadata: 新元数据
            
        Returns:
            是否更新成功
        """
        # 更新本地缓存
        for mem in self._local_memories:
            if mem.id == memory_id or mem.metadata.get("mem0_id") == memory_id:
                if content is not None:
                    mem.content = content
                if importance is not None:
                    mem.importance = importance
                if metadata is not None:
                    mem.metadata.update(metadata)
                break
        
        if not self.is_available:
            return True
        
        try:
            if content is not None:
                self._client.update(
                    memory_id=memory_id,
                    data=content
                )
            return True
            
        except Exception as e:
            logger.warning(f"更新 Mem0 记忆失败: {e}")
            return False
    
    def remove(self, memory_id: str) -> bool:
        """删除记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            是否删除成功
        """
        # 从本地缓存删除
        self._local_memories = [
            mem for mem in self._local_memories 
            if mem.id != memory_id and mem.metadata.get("mem0_id") != memory_id
        ]
        
        if not self.is_available:
            return True
        
        try:
            self._client.delete(memory_id=memory_id)
            return True
            
        except Exception as e:
            logger.warning(f"删除 Mem0 记忆失败: {e}")
            return False
    
    def has_memory(self, memory_id: str) -> bool:
        """检查记忆是否存在
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            是否存在
        """
        # 检查本地缓存
        for mem in self._local_memories:
            if mem.id == memory_id or mem.metadata.get("mem0_id") == memory_id:
                return True
        return False
    
    def clear(self):
        """清空所有记忆"""
        self._local_memories.clear()
        
        if self.is_available:
            try:
                # Mem0 需要按用户删除
                self._client.delete_all(user_id=self.user_id)
            except Exception as e:
                logger.warning(f"清空 Mem0 记忆失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息
        
        Returns:
            统计信息字典
        """
        local_count = len(self._local_memories)
        mem0_count = 0
        
        if self.is_available:
            try:
                all_memories = self.get_all(limit=1000)
                mem0_count = len(all_memories)
            except Exception:
                pass
        
        avg_importance = 0.0
        if self._local_memories:
            avg_importance = sum(m.importance for m in self._local_memories) / len(self._local_memories)
        
        return {
            "count": max(local_count, mem0_count),
            "local_cache_count": local_count,
            "mem0_count": mem0_count,
            "avg_importance": avg_importance,
            "user_id": self.user_id,
            "mem0_available": self.is_available,
            "mode": "cloud" if not self.mem0_config.use_local_mode else "local",
            "memory_type": "mem0"
        }
    
    def get_memory_history(
        self,
        memory_id: str,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取记忆的历史版本
        
        Args:
            memory_id: 记忆ID
            user_id: 用户ID
            
        Returns:
            历史版本列表
        """
        if not self.is_available:
            return []
        
        try:
            history = self._client.history(
                memory_id=memory_id,
                user_id=user_id or self.user_id
            )
            return history if isinstance(history, list) else history.get("results", [])
            
        except Exception as e:
            logger.warning(f"获取记忆历史失败: {e}")
            return []
    
    def __str__(self) -> str:
        stats = self.get_stats()
        mode = "Cloud" if not self.mem0_config.use_local_mode else "Local"
        return f"Mem0Memory(user={self.user_id}, mode={mode}, count={stats['count']})"


def is_mem0_available() -> bool:
    """检查 mem0ai 是否已安装"""
    return _MEM0_AVAILABLE
