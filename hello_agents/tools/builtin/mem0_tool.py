"""Mem0 AI 记忆工具

为 HelloAgents 框架提供基于 Mem0 的智能记忆能力。
Mem0 可以自动从对话中提取重要信息并存储，支持语义搜索和检索。
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from ..base import Tool, ToolParameter, tool_action

logger = logging.getLogger(__name__)

# 延迟导入，避免在 mem0ai 未安装时报错
_Mem0Memory = None
_Mem0MemoryConfig = None
_is_mem0_available = None


def _ensure_mem0_imported():
    """确保 Mem0 相关类已导入"""
    global _Mem0Memory, _Mem0MemoryConfig, _is_mem0_available
    
    if _Mem0Memory is None:
        try:
            from ...memory.types.mem0 import Mem0Memory, Mem0MemoryConfig, is_mem0_available
            _Mem0Memory = Mem0Memory
            _Mem0MemoryConfig = Mem0MemoryConfig
            _is_mem0_available = is_mem0_available
        except ImportError:
            _is_mem0_available = lambda: False


class Mem0MemoryTool(Tool):
    """Mem0 AI 记忆工具
    
    为 Agent 提供基于 Mem0 的智能记忆功能：
    - 自动从对话中提取和存储重要信息
    - 基于语义的智能检索
    - 支持用户级别的记忆隔离
    
    使用示例：
        ```python
        from hello_agents.tools import Mem0MemoryTool
        
        # 创建工具
        mem0_tool = Mem0MemoryTool(user_id="user_123")
        
        # 从对话中提取记忆
        result = mem0_tool.run({
            "action": "add_conversation",
            "messages": [
                {"role": "user", "content": "我喜欢Python编程"},
                {"role": "assistant", "content": "Python是一门很棒的语言！"}
            ]
        })
        
        # 搜索相关记忆
        result = mem0_tool.run({
            "action": "search",
            "query": "编程语言偏好"
        })
        ```
    """
    
    def __init__(
        self,
        user_id: str = "default_user",
        agent_id: Optional[str] = None,
        use_local_mode: bool = True,
        llm_provider: str = "openai",
        llm_model: str = "gpt-4o-mini",
        embedder_provider: str = "openai",
        embedder_model: str = "text-embedding-3-small",
        expandable: bool = False
    ):
        """初始化 Mem0 记忆工具
        
        Args:
            user_id: 用户ID，用于隔离不同用户的记忆
            agent_id: Agent ID（可选）
            use_local_mode: 是否使用本地模式（True: 使用本地 LLM/Embedder，False: 使用 Mem0 Cloud）
            llm_provider: LLM 提供商（openai, azure_openai, groq 等）
            llm_model: LLM 模型名称
            embedder_provider: 嵌入模型提供商
            embedder_model: 嵌入模型名称
            expandable: 是否可展开为多个子工具
        """
        super().__init__(
            name="mem0",
            description="Mem0 AI 记忆工具 - 智能对话记忆管理，自动提取和检索重要信息",
            expandable=expandable
        )
        
        _ensure_mem0_imported()
        
        self.user_id = user_id
        self.agent_id = agent_id
        
        # 初始化 Mem0 记忆系统
        self._memory = None
        self._init_error = None
        
        try:
            if _Mem0MemoryConfig and _Mem0Memory:
                config = _Mem0MemoryConfig(
                    use_local_mode=use_local_mode,
                    llm_provider=llm_provider,
                    llm_model=llm_model,
                    embedder_provider=embedder_provider,
                    embedder_model=embedder_model
                )
                self._memory = _Mem0Memory(config=config, user_id=user_id)
            else:
                self._init_error = "mem0ai 未安装"
        except Exception as e:
            self._init_error = str(e)
            logger.warning(f"Mem0 初始化失败: {e}")
    
    @property
    def is_available(self) -> bool:
        """检查 Mem0 是否可用"""
        return self._memory is not None and self._memory.is_available
    
    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具
        
        Args:
            parameters: 工具参数字典，必须包含 action 参数
            
        Returns:
            执行结果字符串
        """
        if not self.validate_parameters(parameters):
            return "❌ 参数验证失败：缺少必需的参数"
        
        if self._memory is None:
            return f"❌ Mem0 未初始化: {self._init_error or '未知错误'}"
        
        action = parameters.get("action")
        
        if action == "add":
            return self._add_memory(
                content=parameters.get("content", ""),
                metadata=parameters.get("metadata")
            )
        elif action == "add_conversation":
            return self._add_conversation(
                messages=parameters.get("messages", []),
                metadata=parameters.get("metadata")
            )
        elif action == "search":
            return self._search_memory(
                query=parameters.get("query", ""),
                limit=parameters.get("limit", 5)
            )
        elif action == "get_all":
            return self._get_all_memories(
                limit=parameters.get("limit", 100)
            )
        elif action == "update":
            return self._update_memory(
                memory_id=parameters.get("memory_id", ""),
                content=parameters.get("content", "")
            )
        elif action == "delete":
            return self._delete_memory(
                memory_id=parameters.get("memory_id", "")
            )
        elif action == "history":
            return self._get_history(
                memory_id=parameters.get("memory_id", "")
            )
        elif action == "stats":
            return self._get_stats()
        elif action == "clear":
            return self._clear_all()
        else:
            return f"❌ 不支持的操作: {action}"
    
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="action",
                type="string",
                description=(
                    "要执行的操作：add(添加记忆), add_conversation(从对话添加), "
                    "search(搜索记忆), get_all(获取所有), update(更新), "
                    "delete(删除), history(历史版本), stats(统计), clear(清空)"
                ),
                required=True
            ),
            ToolParameter(
                name="content",
                type="string",
                description="记忆内容（add/update 时使用）",
                required=False
            ),
            ToolParameter(
                name="messages",
                type="array",
                description="对话消息列表，格式为 [{role: 'user/assistant', content: '...'}]（add_conversation 时使用）",
                required=False
            ),
            ToolParameter(
                name="query",
                type="string",
                description="搜索查询（search 时使用）",
                required=False
            ),
            ToolParameter(
                name="memory_id",
                type="string",
                description="记忆ID（update/delete/history 时使用）",
                required=False
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="结果数量限制（默认：5）",
                required=False,
                default=5
            ),
            ToolParameter(
                name="metadata",
                type="object",
                description="额外的元数据（可选）",
                required=False
            )
        ]
    
    @tool_action("mem0_add", "添加新记忆")
    def _add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加记忆
        
        Args:
            content: 记忆内容
            metadata: 额外元数据
            
        Returns:
            执行结果
        """
        try:
            messages = [{"role": "user", "content": content}]
            result = self._memory.add_from_messages(
                messages=messages,
                user_id=self.user_id,
                agent_id=self.agent_id,
                metadata=metadata
            )
            
            if isinstance(result, dict):
                if result.get("status") == "stored_locally":
                    return f"✅ 记忆已添加（本地模式）"
                elif "results" in result:
                    count = len(result.get("results", []))
                    return f"✅ 已提取并存储 {count} 条记忆"
                elif "error" in result:
                    return f"⚠️ 添加记忆时出现问题: {result['error']}"
            
            return "✅ 记忆已添加"
            
        except Exception as e:
            return f"❌ 添加记忆失败: {str(e)}"
    
    @tool_action("mem0_add_conversation", "从对话中提取并存储记忆")
    def _add_conversation(
        self,
        messages: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """从对话中提取记忆
        
        Args:
            messages: 对话消息列表
            metadata: 额外元数据
            
        Returns:
            执行结果
        """
        try:
            if not messages:
                return "⚠️ 没有提供对话消息"
            
            result = self._memory.add_from_messages(
                messages=messages,
                user_id=self.user_id,
                agent_id=self.agent_id,
                metadata=metadata
            )
            
            if isinstance(result, dict):
                if result.get("status") == "stored_locally":
                    return f"✅ 已存储 {result.get('count', 0)} 条对话记录（本地模式）"
                elif "results" in result:
                    extracted = result.get("results", [])
                    if extracted:
                        memories = "\n".join([f"  • {r.get('memory', '')[:60]}..." for r in extracted[:3]])
                        return f"✅ 从对话中提取了 {len(extracted)} 条记忆:\n{memories}"
                    else:
                        return "ℹ️ 对话已处理，但未提取到新记忆"
            
            return "✅ 对话已处理"
            
        except Exception as e:
            return f"❌ 处理对话失败: {str(e)}"
    
    @tool_action("mem0_search", "搜索相关记忆")
    def _search_memory(
        self,
        query: str,
        limit: int = 5
    ) -> str:
        """搜索记忆
        
        Args:
            query: 搜索查询
            limit: 结果数量限制
            
        Returns:
            搜索结果
        """
        try:
            if not query:
                return "⚠️ 请提供搜索查询"
            
            results = self._memory.search(
                query=query,
                user_id=self.user_id,
                agent_id=self.agent_id,
                limit=limit
            )
            
            if not results:
                return f"🔍 未找到与 '{query}' 相关的记忆"
            
            formatted = [f"🔍 找到 {len(results)} 条相关记忆:"]
            for i, mem in enumerate(results, 1):
                memory_content = mem.get("memory", "")[:80]
                score = mem.get("score", 0)
                if score:
                    formatted.append(f"  {i}. {memory_content}... (相关度: {score:.2f})")
                else:
                    formatted.append(f"  {i}. {memory_content}...")
            
            return "\n".join(formatted)
            
        except Exception as e:
            return f"❌ 搜索失败: {str(e)}"
    
    @tool_action("mem0_get_all", "获取所有记忆")
    def _get_all_memories(self, limit: int = 100) -> str:
        """获取所有记忆
        
        Args:
            limit: 结果数量限制
            
        Returns:
            所有记忆列表
        """
        try:
            results = self._memory.get_all(
                user_id=self.user_id,
                agent_id=self.agent_id,
                limit=limit
            )
            
            if not results:
                return "📭 暂无存储的记忆"
            
            formatted = [f"📋 共有 {len(results)} 条记忆:"]
            for i, mem in enumerate(results[:10], 1):  # 只显示前10条
                memory_content = mem.get("memory", "")[:60]
                formatted.append(f"  {i}. {memory_content}...")
            
            if len(results) > 10:
                formatted.append(f"  ... 还有 {len(results) - 10} 条记忆")
            
            return "\n".join(formatted)
            
        except Exception as e:
            return f"❌ 获取记忆失败: {str(e)}"
    
    @tool_action("mem0_update", "更新记忆内容")
    def _update_memory(
        self,
        memory_id: str,
        content: str
    ) -> str:
        """更新记忆
        
        Args:
            memory_id: 记忆ID
            content: 新内容
            
        Returns:
            执行结果
        """
        try:
            if not memory_id:
                return "⚠️ 请提供记忆ID"
            if not content:
                return "⚠️ 请提供新内容"
            
            success = self._memory.update(
                memory_id=memory_id,
                content=content
            )
            
            if success:
                return f"✅ 记忆已更新 (ID: {memory_id[:8]}...)"
            else:
                return f"⚠️ 更新失败，可能记忆不存在"
                
        except Exception as e:
            return f"❌ 更新记忆失败: {str(e)}"
    
    @tool_action("mem0_delete", "删除记忆")
    def _delete_memory(self, memory_id: str) -> str:
        """删除记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            执行结果
        """
        try:
            if not memory_id:
                return "⚠️ 请提供记忆ID"
            
            success = self._memory.remove(memory_id)
            
            if success:
                return f"✅ 记忆已删除 (ID: {memory_id[:8]}...)"
            else:
                return f"⚠️ 删除失败，可能记忆不存在"
                
        except Exception as e:
            return f"❌ 删除记忆失败: {str(e)}"
    
    @tool_action("mem0_history", "获取记忆的历史版本")
    def _get_history(self, memory_id: str) -> str:
        """获取记忆历史
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            历史版本列表
        """
        try:
            if not memory_id:
                return "⚠️ 请提供记忆ID"
            
            history = self._memory.get_memory_history(
                memory_id=memory_id,
                user_id=self.user_id
            )
            
            if not history:
                return f"📜 记忆 {memory_id[:8]}... 暂无历史记录"
            
            formatted = [f"📜 记忆历史 (共 {len(history)} 个版本):"]
            for i, version in enumerate(history[:5], 1):
                old_val = version.get("old_memory", "")[:40]
                new_val = version.get("new_memory", "")[:40]
                event = version.get("event", "unknown")
                formatted.append(f"  {i}. [{event}] {old_val}... → {new_val}...")
            
            return "\n".join(formatted)
            
        except Exception as e:
            return f"❌ 获取历史失败: {str(e)}"
    
    @tool_action("mem0_stats", "获取记忆系统统计信息")
    def _get_stats(self) -> str:
        """获取统计信息
        
        Returns:
            统计信息
        """
        try:
            stats = self._memory.get_stats()
            
            mode = "云端" if stats.get("mode") == "cloud" else "本地"
            available = "✅ 可用" if stats.get("mem0_available") else "⚠️ 降级模式"
            
            return "\n".join([
                f"📊 Mem0 记忆系统统计",
                f"  用户ID: {stats.get('user_id', 'unknown')}",
                f"  运行模式: {mode}",
                f"  服务状态: {available}",
                f"  总记忆数: {stats.get('count', 0)}",
                f"  本地缓存: {stats.get('local_cache_count', 0)} 条",
                f"  Mem0 存储: {stats.get('mem0_count', 0)} 条",
                f"  平均重要性: {stats.get('avg_importance', 0):.2f}"
            ])
            
        except Exception as e:
            return f"❌ 获取统计失败: {str(e)}"
    
    @tool_action("mem0_clear", "清空所有记忆")
    def _clear_all(self) -> str:
        """清空所有记忆
        
        Returns:
            执行结果
        """
        try:
            self._memory.clear()
            return "🧹 已清空所有记忆"
            
        except Exception as e:
            return f"❌ 清空失败: {str(e)}"
    
    def get_context_for_query(self, query: str, limit: int = 3) -> str:
        """为查询获取相关上下文
        
        便捷方法，可以被 Agent 调用来获取相关的记忆上下文。
        
        Args:
            query: 查询内容
            limit: 返回数量限制
            
        Returns:
            相关记忆上下文
        """
        if self._memory is None:
            return ""
        
        try:
            results = self._memory.retrieve(
                query=query,
                limit=limit,
                user_id=self.user_id
            )
            
            if not results:
                return ""
            
            context_parts = ["相关记忆:"]
            for mem in results:
                context_parts.append(f"- {mem.content}")
            
            return "\n".join(context_parts)
            
        except Exception:
            return ""
    
    def auto_record_conversation(
        self,
        user_input: str,
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """自动记录对话
        
        便捷方法，可以被 Agent 调用来自动记录对话历史。
        
        Args:
            user_input: 用户输入
            agent_response: Agent 响应
            metadata: 额外元数据
        """
        if self._memory is None:
            return
        
        try:
            messages = [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": agent_response}
            ]
            
            self._memory.add_from_messages(
                messages=messages,
                user_id=self.user_id,
                agent_id=self.agent_id,
                metadata=metadata
            )
            
        except Exception as e:
            logger.warning(f"自动记录对话失败: {e}")
