"""
ProgrammaticAgent - 编程式工具调用 Agent

实现类似 Claude 的 programmatic tool calling 能力：
- LLM 生成 Python 代码来调用工具
- 代码在沙箱环境中安全执行
- 支持复杂的逻辑控制流
- 支持数据处理和转换
- 支持异步 MCP 工具调用

核心特性：
1. 代码生成：LLM 根据任务需求生成 Python 代码
2. 沙箱执行：代码在隔离环境中执行，确保安全
3. 工具注入：已注册的工具作为函数注入沙箱
4. 迭代执行：支持多轮代码生成和执行
5. 结果整合：自动整合执行结果生成最终响应

使用示例：
```python
from hello_agents.agents import ProgrammaticAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.tools.builtin import SearchTool, CalculatorTool

# 创建 Agent
llm = HelloAgentsLLM(provider="openai", model="gpt-4")
agent = ProgrammaticAgent(name="CodeBot", llm=llm)

# 添加工具
agent.add_tool(SearchTool())
agent.add_tool(CalculatorTool())

# 运行
result = agent.run("搜索北京今天的天气，然后计算温度转换为华氏度")
```
"""

from __future__ import annotations

import re
import json
from typing import Optional, List, Dict, Any, Iterator, Union, TYPE_CHECKING

from ..core.agent import Agent
from ..core.config import Config
from ..core.llm import HelloAgentsLLM
from ..core.message import Message
from ..tools.builtin.code_sandbox import CodeSandbox, ExecutionResult
from ..tools.builtin.tool_bridge import ToolBridge, ToolNamespace

if TYPE_CHECKING:
    from ..tools.base import Tool
    from ..protocols.mcp.client import MCPClient


# 默认系统提示词
# 注意：花括号需要转义为 {{ 和 }}，除了 {tools_description}
DEFAULT_SYSTEM_PROMPT = """你是一个强大的 AI 助手，能够通过编写和执行 Python 代码来完成任务。

## 工作模式
当你需要获取信息、执行计算或调用外部服务时，你应该编写 Python 代码。代码会在安全的沙箱环境中执行，你可以使用预定义的工具函数。

## 可用工具函数
{tools_description}

## 代码编写规范
1. 使用 ```python 和 ``` 包裹你的代码
2. 代码应该简洁、清晰、可读
3. **重要**: 将最终结果赋值给变量 `result`
4. 可以使用以下安全的 Python 模块: math, json, re, datetime, collections, itertools
5. 不能使用文件系统操作、网络请求等（这些功能通过工具函数提供）
6. **重要**: 调用工具函数时使用关键字参数，如 `search(query="北京天气")`

## 工具调用格式
工具函数需要使用**关键字参数**调用：
- search(query="查询内容") - 搜索信息
- calculator(expression="数学表达式") - 计算

## 示例
用户: 搜索北京天气并计算华氏度

```python
# 1. 搜索天气信息（使用关键字参数）
weather_info = search(query="北京今天天气")
print(f"搜索结果: {{weather_info}}")

# 2. 提取温度数值
import re
temp_match = re.search(r'(\\d+)', weather_info)
celsius = int(temp_match.group(1)) if temp_match else 25
print(f"摄氏度: {{celsius}}")

# 3. 转换为华氏度
fahrenheit = celsius * 9/5 + 32

# 4. 构建最终结果（必须赋值给 result）
result = f"北京当前温度: {{celsius}}°C = {{fahrenheit}}°F"
```

## 响应格式
- 如果需要执行代码，请在响应中包含 Python 代码块
- 如果不需要执行代码（如回答简单问题），直接给出文字回答
- 代码执行后，你会收到执行结果，然后可以继续分析或生成新代码
"""

# 代码执行后的继续提示词
CONTINUATION_PROMPT = """
## 代码执行结果
```
{execution_output}
```

{error_info}

请根据执行结果:
1. 如果结果满足需求，整理并给出最终答案（不需要代码块）
2. 如果需要进一步处理，继续编写代码
3. 如果出现错误，分析原因并修复代码
"""


class ProgrammaticAgent(Agent):
    """
    编程式工具调用 Agent
    
    这个 Agent 让 LLM 通过编写 Python 代码来调用工具，
    代码在安全的沙箱环境中执行。
    
    与传统 function calling 的区别：
    - 传统方式：LLM 指定工具名和参数 -> 系统调用工具 -> 返回结果
    - 编程式：LLM 生成完整代码 -> 代码在沙箱执行 -> 返回结果
    
    优势：
    - 支持复杂的逻辑控制（条件判断、循环等）
    - 支持数据处理和转换
    - 单次调用可以组合多个工具
    - 更灵活的错误处理
    
    Attributes:
        tool_bridge: 工具桥接器，管理所有工具
        sandbox: 代码沙箱，负责安全执行代码
        max_iterations: 最大代码执行迭代次数
    """
    
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_iterations: int = 5,
        sandbox_timeout: int = 30,
        sandbox_max_memory_mb: int = 512,
        enable_tool_logging: bool = True,
    ):
        """
        初始化 ProgrammaticAgent
        
        Args:
            name: Agent 名称
            llm: LLM 实例
            system_prompt: 自定义系统提示词（可选）
            config: 配置对象
            max_iterations: 最大代码执行迭代次数
            sandbox_timeout: 沙箱执行超时时间（秒）
            sandbox_max_memory_mb: 沙箱最大内存（MB）
            enable_tool_logging: 是否启用工具调用日志
        """
        super().__init__(name, llm, system_prompt, config)
        
        self.max_iterations = max_iterations
        self._custom_system_prompt = system_prompt
        
        # 初始化工具桥接器
        self.tool_bridge = ToolBridge(enable_logging=enable_tool_logging)
        
        # 初始化沙箱
        self.sandbox = CodeSandbox(
            timeout=sandbox_timeout,
            max_memory_mb=sandbox_max_memory_mb
        )
        
        # MCP 客户端列表（用于异步操作）
        self._mcp_clients: List[MCPClient] = []
    
    def add_tool(self, tool: 'Tool', name_override: Optional[str] = None):
        """
        添加原生工具
        
        Args:
            tool: Tool 实例
            name_override: 覆盖工具名称（可选）
        """
        self.tool_bridge.add_tool(tool, name_override)
        self._update_sandbox_functions()
    
    def add_tools(self, tools: List['Tool']):
        """批量添加工具"""
        self.tool_bridge.add_tools(tools)
        self._update_sandbox_functions()
    
    async def add_mcp_client_async(
        self,
        client: 'MCPClient',
        prefix: str = "mcp_"
    ):
        """
        异步添加 MCP 客户端
        
        这个方法会连接到 MCP 服务器并发现所有可用工具。
        
        Args:
            client: MCPClient 实例
            prefix: 工具名前缀
        """
        await self.tool_bridge.add_mcp_client_async(client, prefix)
        self._mcp_clients.append(client)
        self._update_sandbox_functions()
    
    def add_mcp_client(
        self,
        client: 'MCPClient',
        prefix: str = "mcp_",
        tools_info: Optional[List[Dict[str, Any]]] = None
    ):
        """
        同步添加 MCP 客户端
        
        Args:
            client: MCPClient 实例
            prefix: 工具名前缀
            tools_info: 预先获取的工具信息（如果不提供，将延迟发现）
        """
        self.tool_bridge.add_mcp_client(client, prefix, tools_info)
        self._mcp_clients.append(client)
        self._update_sandbox_functions()
    
    def _update_sandbox_functions(self):
        """更新沙箱中注入的函数"""
        self.sandbox.clear_injections()
        
        # 注入所有工具函数
        functions = self.tool_bridge.get_callable_functions()
        self.sandbox.inject_dict(functions)
        
        # 注入 tools 命名空间（可选的调用方式）
        self.sandbox.inject("tools", ToolNamespace(self.tool_bridge))
    
    def _get_system_prompt(self) -> str:
        """构建系统提示词"""
        if self._custom_system_prompt:
            base_prompt = self._custom_system_prompt
        else:
            base_prompt = DEFAULT_SYSTEM_PROMPT
        
        # 获取工具描述
        tools_desc = self.tool_bridge.get_tool_descriptions()
        
        return base_prompt.format(tools_description=tools_desc)
    
    def _extract_code_blocks(self, text: str) -> List[str]:
        """从 LLM 响应中提取 Python 代码块"""
        # 匹配 ```python ... ``` 格式
        pattern = r'```python\s*(.*?)\s*```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            return matches
        
        # 如果没有明确标记，尝试匹配通用代码块
        pattern = r'```\s*(.*?)\s*```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        # 过滤掉明显不是 Python 的代码块
        python_blocks = []
        for block in matches:
            block = block.strip()
            # 简单启发式：检查是否像 Python 代码
            if any([
                'import ' in block,
                'def ' in block,
                'class ' in block,
                '=' in block,
                'print(' in block,
                'result' in block,
                block.startswith('#'),
            ]):
                python_blocks.append(block)
        
        return python_blocks
    
    def _execute_code(self, code: str) -> ExecutionResult:
        """执行代码并返回结果"""
        # 使用支持异步工具的执行方法
        return self.sandbox.execute_with_async_tools(code)
    
    def _format_execution_result(self, result: ExecutionResult) -> str:
        """格式化执行结果用于显示"""
        parts = []
        
        if result.stdout:
            parts.append(f"[标准输出]\n{result.stdout}")
        
        if result.output is not None:
            parts.append(f"[返回值]\n{result.output}")
        
        if result.stderr:
            parts.append(f"[标准错误]\n{result.stderr}")
        
        if not parts:
            parts.append("[无输出]")
        
        return "\n\n".join(parts)
    
    def run(
        self,
        input_text: str,
        *,
        max_iterations: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        运行 Agent 处理用户输入
        
        Agent 会：
        1. 将用户输入发送给 LLM
        2. 如果 LLM 生成了代码，在沙箱中执行
        3. 将执行结果反馈给 LLM
        4. 重复步骤 2-3 直到 LLM 给出最终答案或达到最大迭代次数
        
        Args:
            input_text: 用户输入
            max_iterations: 覆盖最大迭代次数
            **kwargs: 传递给 LLM 的额外参数
            
        Returns:
            最终响应文本
        """
        iterations_limit = max_iterations or self.max_iterations
        
        # 构建初始消息
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self._get_system_prompt()},
        ]
        
        # 添加历史消息
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # 添加用户输入
        messages.append({"role": "user", "content": input_text})
        
        print(f"\n🤖 {self.name} 开始处理: {input_text[:50]}...")
        
        current_iteration = 0
        final_response = ""
        
        while current_iteration < iterations_limit:
            current_iteration += 1
            
            # 调用 LLM
            response_text = self.llm.invoke(messages, **kwargs)
            
            if not response_text:
                print("❌ LLM 未返回有效响应")
                break
            
            print(f"\n--- 迭代 {current_iteration} ---")
            
            # 提取代码块
            code_blocks = self._extract_code_blocks(response_text)
            
            if not code_blocks:
                # 没有代码块，认为是最终答案
                final_response = response_text
                print(f"📝 最终回答: {final_response[:100]}...")
                break
            
            # 执行代码
            print(f"🔧 发现 {len(code_blocks)} 个代码块，开始执行...")
            
            all_results = []
            for i, code in enumerate(code_blocks):
                print(f"\n执行代码块 {i+1}:")
                print(f"```python\n{code[:200]}{'...' if len(code) > 200 else ''}\n```")
                
                result = self._execute_code(code)
                
                if result.success:
                    print(f"✅ 执行成功 (耗时: {result.execution_time:.2f}s)")
                    if result.output:
                        print(f"   返回值: {str(result.output)[:100]}...")
                else:
                    print(f"❌ 执行失败: {result.error_type}: {result.error}")
                
                all_results.append(result)
            
            # 构建执行结果反馈
            result_text = ""
            error_info = ""
            
            for i, result in enumerate(all_results):
                if len(all_results) > 1:
                    result_text += f"\n### 代码块 {i+1} 结果\n"
                
                result_text += self._format_execution_result(result)
                
                if not result.success:
                    error_info += f"\n⚠️ 代码块 {i+1} 执行出错: {result.error_type}: {result.error}"
            
            # 添加 LLM 响应到消息历史
            messages.append({"role": "assistant", "content": response_text})
            
            # 添加执行结果作为系统消息
            continuation = CONTINUATION_PROMPT.format(
                execution_output=result_text,
                error_info=error_info
            )
            messages.append({"role": "user", "content": continuation})
        
        if current_iteration >= iterations_limit and not final_response:
            # 达到最大迭代次数，请求 LLM 总结
            messages.append({
                "role": "user",
                "content": "请根据以上所有执行结果，给出最终的总结答案。"
            })
            final_response = self.llm.invoke(messages, **kwargs)
            print(f"⏰ 达到最大迭代次数，强制总结: {final_response[:100]}...")
        
        # 保存到历史
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_response, "assistant"))
        
        return final_response
    
    async def run_async(
        self,
        input_text: str,
        *,
        max_iterations: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        异步运行 Agent
        
        与 run() 相同，但支持异步执行。
        
        Args:
            input_text: 用户输入
            max_iterations: 覆盖最大迭代次数
            **kwargs: 传递给 LLM 的额外参数
            
        Returns:
            最终响应文本
        """
        import asyncio
        
        # 在线程池中运行同步版本
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.run(input_text, max_iterations=max_iterations, **kwargs)
        )
    
    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        """
        流式运行 Agent
        
        返回一个生成器，逐步产出响应内容。
        
        Args:
            input_text: 用户输入
            **kwargs: 传递给 LLM 的额外参数
            
        Yields:
            响应文本片段
        """
        # 目前简单实现：运行完成后一次性返回
        # TODO: 实现真正的流式输出
        result = self.run(input_text, **kwargs)
        yield result
    
    def get_tool_call_history(self) -> List[Dict[str, Any]]:
        """获取工具调用历史"""
        return [
            record.to_dict() 
            for record in self.tool_bridge.get_call_history()
        ]
    
    def clear_tool_call_history(self):
        """清除工具调用历史"""
        self.tool_bridge.clear_call_history()
    
    def list_tools(self) -> List[str]:
        """列出所有可用工具"""
        return self.tool_bridge.list_tools()
    
    def has_tool(self, name: str) -> bool:
        """检查工具是否存在"""
        return self.tool_bridge.has_tool(name)
    
    def remove_tool(self, name: str) -> bool:
        """移除工具"""
        result = self.tool_bridge.remove_tool(name)
        if result:
            self._update_sandbox_functions()
        return result
    
    def get_sandbox_info(self) -> Dict[str, Any]:
        """获取沙箱信息"""
        return {
            "timeout": self.sandbox.config.timeout,
            "max_memory_mb": self.sandbox.config.max_memory_mb,
            "allowed_modules": list(self.sandbox.config.allowed_modules),
            "injected_functions": self.sandbox.get_injected_names()
        }
    
    def __repr__(self) -> str:
        return (
            f"ProgrammaticAgent(name={self.name}, "
            f"tools={len(self.list_tools())}, "
            f"max_iterations={self.max_iterations})"
        )

