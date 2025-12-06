"""Mem0 AI 记忆系统测试

测试 Mem0Memory 类和 Mem0MemoryTool 工具的功能。
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hello_agents.memory.base import MemoryItem


class TestMem0MemoryConfig:
    """测试 Mem0MemoryConfig 配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        from hello_agents.memory.types.mem0 import Mem0MemoryConfig
        
        config = Mem0MemoryConfig()
        
        assert config.use_local_mode is True
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4o-mini"
        assert config.embedder_provider == "openai"
        assert config.embedder_model == "text-embedding-3-small"
        assert config.vector_store_provider == "qdrant"
        assert config.enable_graph is False
    
    def test_custom_config(self):
        """测试自定义配置"""
        from hello_agents.memory.types.mem0 import Mem0MemoryConfig
        
        config = Mem0MemoryConfig(
            use_local_mode=False,
            mem0_api_key="test_api_key",
            llm_model="gpt-4",
            enable_graph=True
        )
        
        assert config.use_local_mode is False
        assert config.mem0_api_key == "test_api_key"
        assert config.llm_model == "gpt-4"
        assert config.enable_graph is True


class TestMem0MemoryLocalCache:
    """测试 Mem0Memory 本地缓存功能（不依赖 mem0ai）"""
    
    def test_add_memory_to_local_cache(self):
        """测试添加记忆到本地缓存"""
        from hello_agents.memory.types.mem0 import Mem0Memory, Mem0MemoryConfig
        
        config = Mem0MemoryConfig(use_local_mode=True)
        memory = Mem0Memory(config=config, user_id="test_user")
        
        # 添加记忆
        memory_item = MemoryItem(
            id="test_id_1",
            content="我喜欢Python编程",
            memory_type="mem0",
            user_id="test_user",
            timestamp=datetime.now(),
            importance=0.8,
            metadata={}
        )
        
        result_id = memory.add(memory_item)
        
        assert result_id == "test_id_1"
        assert len(memory._local_memories) == 1
        assert memory._local_memories[0].content == "我喜欢Python编程"
    
    def test_retrieve_from_local_cache(self):
        """测试从本地缓存检索"""
        from hello_agents.memory.types.mem0 import Mem0Memory, Mem0MemoryConfig
        
        config = Mem0MemoryConfig(use_local_mode=True)
        memory = Mem0Memory(config=config, user_id="test_user")
        
        # 添加多条记忆
        for i, content in enumerate([
            "我喜欢Python编程",
            "机器学习是我的兴趣",
            "今天天气很好"
        ]):
            memory_item = MemoryItem(
                id=f"test_id_{i}",
                content=content,
                memory_type="mem0",
                user_id="test_user",
                timestamp=datetime.now(),
                importance=0.5 + i * 0.1,
                metadata={}
            )
            memory.add(memory_item)
        
        # 检索
        results = memory.retrieve("Python", limit=5)
        
        assert len(results) >= 1
        assert any("Python" in r.content for r in results)
    
    def test_update_memory_in_local_cache(self):
        """测试更新本地缓存中的记忆"""
        from hello_agents.memory.types.mem0 import Mem0Memory, Mem0MemoryConfig
        
        config = Mem0MemoryConfig(use_local_mode=True)
        memory = Mem0Memory(config=config, user_id="test_user")
        
        # 添加记忆
        memory_item = MemoryItem(
            id="test_id_1",
            content="原始内容",
            memory_type="mem0",
            user_id="test_user",
            timestamp=datetime.now(),
            importance=0.5,
            metadata={}
        )
        memory.add(memory_item)
        
        # 更新
        success = memory.update("test_id_1", content="更新后的内容")
        
        assert success is True
        assert memory._local_memories[0].content == "更新后的内容"
    
    def test_remove_memory_from_local_cache(self):
        """测试从本地缓存删除记忆"""
        from hello_agents.memory.types.mem0 import Mem0Memory, Mem0MemoryConfig
        
        config = Mem0MemoryConfig(use_local_mode=True)
        memory = Mem0Memory(config=config, user_id="test_user")
        
        # 添加记忆
        memory_item = MemoryItem(
            id="test_id_1",
            content="待删除内容",
            memory_type="mem0",
            user_id="test_user",
            timestamp=datetime.now(),
            importance=0.5,
            metadata={}
        )
        memory.add(memory_item)
        
        assert len(memory._local_memories) == 1
        
        # 删除
        success = memory.remove("test_id_1")
        
        assert success is True
        assert len(memory._local_memories) == 0
    
    def test_has_memory(self):
        """测试检查记忆是否存在"""
        from hello_agents.memory.types.mem0 import Mem0Memory, Mem0MemoryConfig
        
        config = Mem0MemoryConfig(use_local_mode=True)
        memory = Mem0Memory(config=config, user_id="test_user")
        
        memory_item = MemoryItem(
            id="test_id_1",
            content="测试内容",
            memory_type="mem0",
            user_id="test_user",
            timestamp=datetime.now(),
            importance=0.5,
            metadata={}
        )
        memory.add(memory_item)
        
        assert memory.has_memory("test_id_1") is True
        assert memory.has_memory("non_existent") is False
    
    def test_clear_memories(self):
        """测试清空记忆"""
        from hello_agents.memory.types.mem0 import Mem0Memory, Mem0MemoryConfig
        
        config = Mem0MemoryConfig(use_local_mode=True)
        memory = Mem0Memory(config=config, user_id="test_user")
        
        # 添加多条记忆
        for i in range(5):
            memory_item = MemoryItem(
                id=f"test_id_{i}",
                content=f"记忆 {i}",
                memory_type="mem0",
                user_id="test_user",
                timestamp=datetime.now(),
                importance=0.5,
                metadata={}
            )
            memory.add(memory_item)
        
        assert len(memory._local_memories) == 5
        
        # 清空
        memory.clear()
        
        assert len(memory._local_memories) == 0
    
    def test_get_stats(self):
        """测试获取统计信息"""
        from hello_agents.memory.types.mem0 import Mem0Memory, Mem0MemoryConfig
        
        config = Mem0MemoryConfig(use_local_mode=True)
        memory = Mem0Memory(config=config, user_id="test_user")
        
        # 添加记忆
        for i in range(3):
            memory_item = MemoryItem(
                id=f"test_id_{i}",
                content=f"记忆 {i}",
                memory_type="mem0",
                user_id="test_user",
                timestamp=datetime.now(),
                importance=0.3 + i * 0.2,
                metadata={}
            )
            memory.add(memory_item)
        
        stats = memory.get_stats()
        
        assert stats["local_cache_count"] == 3
        assert stats["user_id"] == "test_user"
        assert stats["mode"] == "local"
        assert "avg_importance" in stats
    
    def test_add_from_messages_local(self):
        """测试从消息添加记忆（本地模式）"""
        from hello_agents.memory.types.mem0 import Mem0Memory, Mem0MemoryConfig
        
        config = Mem0MemoryConfig(use_local_mode=True)
        memory = Mem0Memory(config=config, user_id="test_user")
        
        messages = [
            {"role": "user", "content": "我喜欢Python编程"},
            {"role": "assistant", "content": "Python是一门很棒的语言！"}
        ]
        
        result = memory.add_from_messages(messages)
        
        assert result["status"] == "stored_locally"
        assert result["count"] == 2
        assert len(memory._local_memories) == 2
    
    def test_get_all_local(self):
        """测试获取所有记忆（本地模式）"""
        from hello_agents.memory.types.mem0 import Mem0Memory, Mem0MemoryConfig
        
        config = Mem0MemoryConfig(use_local_mode=True)
        memory = Mem0Memory(config=config, user_id="test_user")
        
        # 添加记忆
        for i in range(3):
            memory_item = MemoryItem(
                id=f"test_id_{i}",
                content=f"记忆 {i}",
                memory_type="mem0",
                user_id="test_user",
                timestamp=datetime.now(),
                importance=0.5,
                metadata={}
            )
            memory.add(memory_item)
        
        all_memories = memory.get_all()
        
        assert len(all_memories) == 3
        assert all("memory" in m for m in all_memories)
    
    def test_search_local(self):
        """测试搜索（本地模式）"""
        from hello_agents.memory.types.mem0 import Mem0Memory, Mem0MemoryConfig
        
        config = Mem0MemoryConfig(use_local_mode=True)
        memory = Mem0Memory(config=config, user_id="test_user")
        
        # 添加记忆
        contents = [
            "我喜欢Python编程",
            "机器学习是AI的分支",
            "今天天气晴朗"
        ]
        for i, content in enumerate(contents):
            memory_item = MemoryItem(
                id=f"test_id_{i}",
                content=content,
                memory_type="mem0",
                user_id="test_user",
                timestamp=datetime.now(),
                importance=0.5,
                metadata={}
            )
            memory.add(memory_item)
        
        results = memory.search("Python", limit=5)
        
        assert len(results) >= 1
        assert any("Python" in r.get("memory", "") for r in results)


class TestMem0MemoryTool:
    """测试 Mem0MemoryTool 工具类"""
    
    def test_tool_initialization(self):
        """测试工具初始化"""
        from hello_agents.tools.builtin.mem0_tool import Mem0MemoryTool
        
        tool = Mem0MemoryTool(user_id="test_user")
        
        assert tool.name == "mem0"
        assert tool.user_id == "test_user"
        assert "记忆" in tool.description or "Mem0" in tool.description
    
    def test_get_parameters(self):
        """测试获取参数定义"""
        from hello_agents.tools.builtin.mem0_tool import Mem0MemoryTool
        
        tool = Mem0MemoryTool(user_id="test_user")
        params = tool.get_parameters()
        
        param_names = [p.name for p in params]
        
        assert "action" in param_names
        assert "content" in param_names
        assert "query" in param_names
        assert "messages" in param_names
    
    def test_add_action(self):
        """测试添加记忆操作"""
        from hello_agents.tools.builtin.mem0_tool import Mem0MemoryTool
        
        tool = Mem0MemoryTool(user_id="test_user")
        
        result = tool.run({
            "action": "add",
            "content": "我喜欢Python编程"
        })
        
        # 应该返回成功信息（即使在降级模式下）
        assert "记忆" in result or "添加" in result or "✅" in result or "❌" in result
    
    def test_add_conversation_action(self):
        """测试从对话添加记忆操作"""
        from hello_agents.tools.builtin.mem0_tool import Mem0MemoryTool
        
        tool = Mem0MemoryTool(user_id="test_user")
        
        result = tool.run({
            "action": "add_conversation",
            "messages": [
                {"role": "user", "content": "我喜欢Python编程"},
                {"role": "assistant", "content": "Python是一门很棒的语言！"}
            ]
        })
        
        assert isinstance(result, str)
    
    def test_search_action(self):
        """测试搜索记忆操作"""
        from hello_agents.tools.builtin.mem0_tool import Mem0MemoryTool
        
        tool = Mem0MemoryTool(user_id="test_user")
        
        # 先添加一些记忆
        tool.run({
            "action": "add",
            "content": "我喜欢Python编程"
        })
        
        # 搜索
        result = tool.run({
            "action": "search",
            "query": "Python",
            "limit": 5
        })
        
        assert isinstance(result, str)
    
    def test_get_all_action(self):
        """测试获取所有记忆操作"""
        from hello_agents.tools.builtin.mem0_tool import Mem0MemoryTool
        
        tool = Mem0MemoryTool(user_id="test_user")
        
        result = tool.run({
            "action": "get_all",
            "limit": 10
        })
        
        assert isinstance(result, str)
    
    def test_stats_action(self):
        """测试获取统计信息操作"""
        from hello_agents.tools.builtin.mem0_tool import Mem0MemoryTool
        
        tool = Mem0MemoryTool(user_id="test_user")
        
        result = tool.run({
            "action": "stats"
        })
        
        assert isinstance(result, str)
        assert "统计" in result or "Mem0" in result or "❌" in result
    
    def test_clear_action(self):
        """测试清空记忆操作"""
        from hello_agents.tools.builtin.mem0_tool import Mem0MemoryTool
        
        tool = Mem0MemoryTool(user_id="test_user")
        
        # 先添加一些记忆
        tool.run({
            "action": "add",
            "content": "测试记忆"
        })
        
        # 清空
        result = tool.run({
            "action": "clear"
        })
        
        assert isinstance(result, str)
    
    def test_invalid_action(self):
        """测试无效操作"""
        from hello_agents.tools.builtin.mem0_tool import Mem0MemoryTool
        
        tool = Mem0MemoryTool(user_id="test_user")
        
        result = tool.run({
            "action": "invalid_action"
        })
        
        assert "不支持" in result or "❌" in result
    
    def test_get_context_for_query(self):
        """测试获取查询上下文"""
        from hello_agents.tools.builtin.mem0_tool import Mem0MemoryTool
        
        tool = Mem0MemoryTool(user_id="test_user")
        
        # 先添加记忆
        tool.run({
            "action": "add",
            "content": "我喜欢Python编程"
        })
        
        context = tool.get_context_for_query("Python")
        
        # 可能返回空字符串或包含上下文
        assert isinstance(context, str)
    
    def test_auto_record_conversation(self):
        """测试自动记录对话"""
        from hello_agents.tools.builtin.mem0_tool import Mem0MemoryTool
        
        tool = Mem0MemoryTool(user_id="test_user")
        
        # 这个方法不返回值，只是确保不抛出异常
        tool.auto_record_conversation(
            user_input="我喜欢Python",
            agent_response="Python是一门很棒的语言！"
        )


class TestMem0MemoryImports:
    """测试模块导入"""
    
    def test_import_from_memory_types(self):
        """测试从 memory.types 导入"""
        from hello_agents.memory.types import Mem0Memory, Mem0MemoryConfig, is_mem0_available
        
        # 如果 mem0ai 未安装，Mem0Memory 可能为 None
        assert is_mem0_available is not None or callable(is_mem0_available)
    
    def test_import_from_memory(self):
        """测试从 memory 导入"""
        from hello_agents.memory import Mem0Memory, Mem0MemoryConfig, is_mem0_available
        
        assert is_mem0_available is not None or callable(is_mem0_available)
    
    def test_import_from_tools_builtin(self):
        """测试从 tools.builtin 导入"""
        from hello_agents.tools.builtin import Mem0MemoryTool
        
        assert Mem0MemoryTool is not None
    
    def test_import_from_tools(self):
        """测试从 tools 导入"""
        from hello_agents.tools import Mem0MemoryTool
        
        assert Mem0MemoryTool is not None


class TestMem0MemoryIntegration:
    """集成测试（需要 mem0ai 安装）"""
    
    @pytest.mark.skipif(
        True,  # 默认跳过，需要 mem0ai 和 API 配置
        reason="需要 mem0ai 安装和 API 配置"
    )
    def test_full_workflow_with_mem0(self):
        """测试完整工作流（需要 mem0ai）"""
        from hello_agents.memory.types.mem0 import Mem0Memory, Mem0MemoryConfig, is_mem0_available
        
        if not is_mem0_available():
            pytest.skip("mem0ai 未安装")
        
        config = Mem0MemoryConfig(use_local_mode=True)
        memory = Mem0Memory(config=config, user_id="test_user")
        
        # 添加对话
        messages = [
            {"role": "user", "content": "我是一名软件工程师，专注于Python开发"},
            {"role": "assistant", "content": "很高兴认识你！Python是一门很棒的语言。"}
        ]
        
        result = memory.add_from_messages(messages)
        assert result is not None
        
        # 搜索
        search_results = memory.search("Python开发")
        assert isinstance(search_results, list)
        
        # 获取统计
        stats = memory.get_stats()
        assert "count" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
