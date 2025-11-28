"""
ToolBridge - 工具桥接器

将 HelloAgents 原生工具和 MCP 工具转换为可在沙箱中调用的 Python 函数。

功能：
- 将 Tool 对象转换为可调用函数
- 将 MCP 工具转换为异步可调用函数
- 提供统一的工具注册和管理接口
- 支持工具调用日志记录

使用示例：
```python
from hello_agents.tools.builtin import SearchTool, CalculatorTool
from hello_agents.protocols.mcp import MCPClient

# 创建桥接器
bridge = ToolBridge()

# 添加原生工具
bridge.add_tool(SearchTool())
bridge.add_tool(CalculatorTool())

# 添加 MCP 客户端
mcp_client = MCPClient("./server.py")
bridge.add_mcp_client(mcp_client, prefix="mcp_")

# 获取所有可调用函数
functions = bridge.get_callable_functions()

# 注入到沙箱
sandbox.inject_dict(functions)
```
"""

import asyncio
import inspect
from typing import Dict, Any, Optional, Callable, List, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
import json

if TYPE_CHECKING:
    from ..base import Tool
    from ...protocols.mcp.client import MCPClient


@dataclass
class ToolCallRecord:
    """工具调用记录"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": str(self.result) if self.result else None,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
            "execution_time": self.execution_time
        }


class ToolBridge:
    """
    工具桥接器 - 将工具转换为可在沙箱中调用的函数
    
    这个类负责：
    1. 将 HelloAgents Tool 对象转换为普通 Python 函数
    2. 将 MCP 工具转换为异步 Python 函数
    3. 管理工具的生命周期
    4. 记录所有工具调用
    
    使用示例：
    ```python
    bridge = ToolBridge()
    
    # 添加原生工具
    bridge.add_tool(SearchTool())
    
    # 添加 MCP 服务
    await bridge.add_mcp_client_async(MCPClient("server.py"))
    
    # 获取可调用函数字典
    functions = bridge.get_callable_functions()
    
    # 注入到沙箱
    sandbox.inject_dict(functions)
    
    # 获取调用历史
    history = bridge.get_call_history()
    ```
    """
    
    def __init__(self, enable_logging: bool = True):
        """
        初始化工具桥接器
        
        Args:
            enable_logging: 是否启用调用日志
        """
        self._tools: Dict[str, 'Tool'] = {}
        self._mcp_clients: List['MCPClient'] = []
        self._mcp_tools: Dict[str, Dict[str, Any]] = {}  # name -> {client, tool_info}
        self._callable_functions: Dict[str, Callable] = {}
        self._call_history: List[ToolCallRecord] = []
        self._enable_logging = enable_logging
    
    def add_tool(self, tool: 'Tool', name_override: Optional[str] = None):
        """
        添加 HelloAgents 原生工具
        
        Args:
            tool: Tool 实例
            name_override: 覆盖工具名称（可选）
        """
        name = name_override or tool.name
        self._tools[name] = tool
        
        # 创建可调用函数
        self._callable_functions[name] = self._create_tool_wrapper(tool, name)
        
        print(f"🔧 工具 '{name}' 已添加到桥接器")
    
    def add_tools(self, tools: List['Tool']):
        """批量添加工具"""
        for tool in tools:
            self.add_tool(tool)
    
    def _create_tool_wrapper(self, tool: 'Tool', name: str) -> Callable:
        """
        为 Tool 创建可调用的包装函数
        
        包装函数会：
        1. 处理参数转换
        2. 调用工具
        3. 记录调用历史
        4. 处理错误
        """
        import time
        
        def wrapper(*args, **kwargs) -> str:
            start_time = time.time()
            
            try:
                # 构建参数字典
                params = tool.get_parameters()
                param_dict = {}
                
                # 处理位置参数
                for i, arg in enumerate(args):
                    if i < len(params):
                        param_dict[params[i].name] = arg
                
                # 处理关键字参数
                param_dict.update(kwargs)
                
                # 如果只有一个参数且传入了字符串，直接使用
                if len(args) == 1 and len(kwargs) == 0 and len(params) == 1:
                    param_dict = {params[0].name: args[0]}
                
                # 调用工具
                result = tool.run(param_dict)
                
                execution_time = time.time() - start_time
                
                # 记录调用
                if self._enable_logging:
                    self._call_history.append(ToolCallRecord(
                        tool_name=name,
                        arguments=param_dict,
                        result=result,
                        success=True,
                        execution_time=execution_time
                    ))
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = f"工具调用失败: {e}"
                
                if self._enable_logging:
                    self._call_history.append(ToolCallRecord(
                        tool_name=name,
                        arguments=kwargs if kwargs else {"args": args},
                        result=None,
                        success=False,
                        error=str(e),
                        execution_time=execution_time
                    ))
                
                return error_msg
        
        # 设置函数元信息
        wrapper.__name__ = name
        wrapper.__doc__ = tool.description
        
        return wrapper
    
    async def add_mcp_client_async(
        self,
        client: 'MCPClient',
        prefix: str = "",
        auto_discover: bool = True
    ):
        """
        异步添加 MCP 客户端并发现工具
        
        Args:
            client: MCPClient 实例
            prefix: 工具名前缀（如 "mcp_"）
            auto_discover: 是否自动发现并注册工具
        """
        self._mcp_clients.append(client)
        
        if auto_discover:
            async with client:
                tools = await client.list_tools()
                
                for tool_info in tools:
                    tool_name = f"{prefix}{tool_info['name']}"
                    self._mcp_tools[tool_name] = {
                        "client": client,
                        "tool_info": tool_info,
                        "original_name": tool_info['name']
                    }
                    
                    # 创建异步可调用函数
                    self._callable_functions[tool_name] = self._create_mcp_tool_wrapper(
                        client, tool_info, tool_name
                    )
                
                print(f"🌐 MCP 客户端已添加，发现 {len(tools)} 个工具")
    
    def add_mcp_client(
        self,
        client: 'MCPClient',
        prefix: str = "",
        tools_info: Optional[List[Dict[str, Any]]] = None
    ):
        """
        同步添加 MCP 客户端（需要预先提供工具信息）
        
        如果不提供 tools_info，工具将在首次调用时动态发现。
        
        Args:
            client: MCPClient 实例
            prefix: 工具名前缀
            tools_info: 预先获取的工具信息列表
        """
        self._mcp_clients.append(client)
        
        if tools_info:
            for tool_info in tools_info:
                tool_name = f"{prefix}{tool_info['name']}"
                self._mcp_tools[tool_name] = {
                    "client": client,
                    "tool_info": tool_info,
                    "original_name": tool_info['name']
                }
                
                self._callable_functions[tool_name] = self._create_mcp_tool_wrapper(
                    client, tool_info, tool_name
                )
            
            print(f"🌐 MCP 客户端已添加，注册 {len(tools_info)} 个工具")
        else:
            # 创建延迟发现的包装器
            self._callable_functions[f"{prefix}discover_tools"] = lambda: asyncio.run(
                self._discover_mcp_tools_async(client, prefix)
            )
            print(f"🌐 MCP 客户端已添加（工具将在首次调用时发现）")
    
    async def _discover_mcp_tools_async(self, client: 'MCPClient', prefix: str) -> str:
        """异步发现 MCP 工具"""
        async with client:
            tools = await client.list_tools()
            
            for tool_info in tools:
                tool_name = f"{prefix}{tool_info['name']}"
                self._mcp_tools[tool_name] = {
                    "client": client,
                    "tool_info": tool_info,
                    "original_name": tool_info['name']
                }
                
                self._callable_functions[tool_name] = self._create_mcp_tool_wrapper(
                    client, tool_info, tool_name
                )
            
            return f"发现 {len(tools)} 个 MCP 工具: {[t['name'] for t in tools]}"
    
    def _create_mcp_tool_wrapper(
        self,
        client: 'MCPClient',
        tool_info: Dict[str, Any],
        tool_name: str
    ) -> Callable:
        """
        为 MCP 工具创建异步可调用的包装函数
        """
        import time
        
        async def async_wrapper(**kwargs) -> Any:
            start_time = time.time()
            
            try:
                async with client:
                    result = await client.call_tool(
                        tool_info['name'],
                        kwargs
                    )
                
                execution_time = time.time() - start_time
                
                if self._enable_logging:
                    self._call_history.append(ToolCallRecord(
                        tool_name=tool_name,
                        arguments=kwargs,
                        result=result,
                        success=True,
                        execution_time=execution_time
                    ))
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = f"MCP 工具调用失败: {e}"
                
                if self._enable_logging:
                    self._call_history.append(ToolCallRecord(
                        tool_name=tool_name,
                        arguments=kwargs,
                        result=None,
                        success=False,
                        error=str(e),
                        execution_time=execution_time
                    ))
                
                return error_msg
        
        # 创建同步包装器（用于沙箱调用）
        def sync_wrapper(**kwargs) -> Any:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 事件循环已在运行，使用 run_coroutine_threadsafe
                    import concurrent.futures
                    future = asyncio.run_coroutine_threadsafe(
                        async_wrapper(**kwargs), loop
                    )
                    return future.result(timeout=60)
                else:
                    return loop.run_until_complete(async_wrapper(**kwargs))
            except RuntimeError:
                # 没有事件循环
                return asyncio.run(async_wrapper(**kwargs))
        
        # 设置函数元信息
        sync_wrapper.__name__ = tool_name
        sync_wrapper.__doc__ = tool_info.get('description', f'MCP 工具: {tool_name}')
        sync_wrapper._is_mcp_tool = True
        sync_wrapper._async_version = async_wrapper
        
        return sync_wrapper
    
    def get_callable_functions(self) -> Dict[str, Callable]:
        """
        获取所有可调用函数
        
        返回的字典可以直接注入到沙箱中。
        
        Returns:
            函数名 -> 可调用对象 的字典
        """
        return self._callable_functions.copy()
    
    def get_async_functions(self) -> Dict[str, Callable]:
        """
        获取所有异步版本的函数
        
        Returns:
            函数名 -> 异步可调用对象 的字典
        """
        async_funcs = {}
        
        for name, func in self._callable_functions.items():
            if hasattr(func, '_async_version'):
                async_funcs[name] = func._async_version
            elif asyncio.iscoroutinefunction(func):
                async_funcs[name] = func
        
        return async_funcs
    
    def get_tool_descriptions(self) -> str:
        """
        获取所有工具的描述文本
        
        用于构建 LLM 提示词。
        
        Returns:
            格式化的工具描述字符串
        """
        descriptions = []
        
        # 原生工具描述
        for name, tool in self._tools.items():
            params = tool.get_parameters()
            param_str = ", ".join([
                f"{p.name}: {p.type}" + (f" = {p.default}" if p.default else "")
                for p in params
            ])
            descriptions.append(
                f"- {name}({param_str})\n  {tool.description}"
            )
        
        # MCP 工具描述
        for name, info in self._mcp_tools.items():
            tool_info = info['tool_info']
            schema = tool_info.get('input_schema', {})
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            params = []
            for pname, pinfo in properties.items():
                ptype = pinfo.get('type', 'any')
                req = '*' if pname in required else ''
                params.append(f"{pname}{req}: {ptype}")
            
            param_str = ", ".join(params)
            descriptions.append(
                f"- {name}({param_str}) [MCP]\n  {tool_info.get('description', '')}"
            )
        
        return "\n".join(descriptions) if descriptions else "暂无可用工具"
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的 JSON Schema 格式定义
        
        用于 function calling 模式。
        
        Returns:
            工具 schema 列表
        """
        schemas = []
        
        # 原生工具 schema
        for name, tool in self._tools.items():
            schemas.append(tool.to_openai_schema())
        
        # MCP 工具 schema
        for name, info in self._mcp_tools.items():
            tool_info = info['tool_info']
            schemas.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool_info.get('description', ''),
                    "parameters": tool_info.get('input_schema', {
                        "type": "object",
                        "properties": {}
                    })
                }
            })
        
        return schemas
    
    def get_call_history(self) -> List[ToolCallRecord]:
        """获取工具调用历史"""
        return self._call_history.copy()
    
    def get_call_history_json(self) -> str:
        """获取 JSON 格式的调用历史"""
        return json.dumps(
            [record.to_dict() for record in self._call_history],
            ensure_ascii=False,
            indent=2
        )
    
    def clear_call_history(self):
        """清除调用历史"""
        self._call_history.clear()
    
    def list_tools(self) -> List[str]:
        """列出所有可用工具名称"""
        return list(self._callable_functions.keys())
    
    def has_tool(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._callable_functions
    
    def remove_tool(self, name: str) -> bool:
        """移除工具"""
        if name in self._tools:
            del self._tools[name]
        if name in self._mcp_tools:
            del self._mcp_tools[name]
        if name in self._callable_functions:
            del self._callable_functions[name]
            return True
        return False
    
    def __repr__(self) -> str:
        return (
            f"ToolBridge(native_tools={len(self._tools)}, "
            f"mcp_tools={len(self._mcp_tools)}, "
            f"call_count={len(self._call_history)})"
        )


class ToolNamespace:
    """
    工具命名空间 - 提供更优雅的工具调用方式
    
    允许通过属性访问调用工具：
    ```python
    tools = ToolNamespace(bridge)
    result = tools.search("query")  # 等价于 bridge.get_callable_functions()['search']("query")
    ```
    """
    
    def __init__(self, bridge: ToolBridge):
        self._bridge = bridge
        self._functions = bridge.get_callable_functions()
    
    def __getattr__(self, name: str) -> Callable:
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        
        if name in self._functions:
            return self._functions[name]
        
        raise AttributeError(f"工具 '{name}' 不存在。可用工具: {list(self._functions.keys())}")
    
    def __dir__(self) -> List[str]:
        return list(self._functions.keys())
    
    def __repr__(self) -> str:
        return f"ToolNamespace({list(self._functions.keys())})"

