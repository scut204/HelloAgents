"""
ProgrammaticAgent 使用示例

展示如何使用 ProgrammaticAgent 实现编程式工具调用：
- LLM 生成 Python 代码来调用工具
- 代码在沙箱环境中安全执行
- 支持复杂的逻辑控制和数据处理

运行方式:
    python examples/programmatic_agent_demo.py
"""

import os
import sys
import importlib.util

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def load_module_directly(name, path):
    """直接加载模块，绕过包的 __init__.py"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# 直接加载核心模块
code_sandbox = load_module_directly(
    "code_sandbox",
    os.path.join(project_root, "hello_agents/tools/builtin/code_sandbox.py")
)
tool_bridge = load_module_directly(
    "tool_bridge",
    os.path.join(project_root, "hello_agents/tools/builtin/tool_bridge.py")
)

CodeSandbox = code_sandbox.CodeSandbox
ExecutionResult = code_sandbox.ExecutionResult
ToolBridge = tool_bridge.ToolBridge
ToolNamespace = tool_bridge.ToolNamespace


# ============================================================
# 示例 1: 单独使用 CodeSandbox（沙箱执行器）
# ============================================================
def demo_code_sandbox():
    """演示沙箱执行器的基本用法"""
    print("\n" + "=" * 60)
    print("示例 1: CodeSandbox 沙箱执行器")
    print("=" * 60)
    
    # 创建沙箱
    sandbox = CodeSandbox(timeout=10, max_memory_mb=256)
    
    # 基本代码执行
    print("\n1.1 基本代码执行:")
    result = sandbox.execute('''
import math
result = math.sqrt(144) + math.pi
''')
    print(f"    计算 sqrt(144) + pi = {result.output}")
    print(f"    执行成功: {result.success}")
    
    # 注入工具函数
    print("\n1.2 注入工具函数:")
    
    def search(query: str) -> str:
        """模拟搜索工具"""
        return f"搜索「{query}」的结果: 北京今天晴，气温 25°C"
    
    def calculator(expression: str) -> float:
        """模拟计算器工具"""
        return eval(expression)
    
    sandbox.inject("search", search)
    sandbox.inject("calc", calculator)
    
    result = sandbox.execute('''
# 搜索天气
weather = search("北京天气")

# 从结果中提取温度并转换
import re
match = re.search(r"(\\d+)°C", weather)
celsius = int(match.group(1)) if match else 20

# 转换为华氏度
fahrenheit = calc(f"{celsius} * 9 / 5 + 32")

result = f"温度转换: {celsius}°C = {fahrenheit}°F"
''')
    print(f"    结果: {result.output}")
    
    # 安全限制测试
    print("\n1.3 安全限制测试:")
    
    # 尝试导入危险模块
    result = sandbox.execute('import os')
    print(f"    导入 os 模块: 成功={result.success}, 错误={result.error}")
    
    # 尝试访问文件系统
    result = sandbox.execute('open("/etc/passwd")')
    print(f"    打开文件: 成功={result.success}, 错误类型={result.error_type}")


# ============================================================
# 示例 2: 使用 ToolBridge（工具桥接器）
# ============================================================
def demo_tool_bridge():
    """演示工具桥接器的用法"""
    print("\n" + "=" * 60)
    print("示例 2: ToolBridge 工具桥接器")
    print("=" * 60)
    
    # 创建简单的工具类（模拟 Tool 基类）
    class MockToolParameter:
        def __init__(self, name, type_, description, required=True, default=None):
            self.name = name
            self.type = type_
            self.description = description
            self.required = required
            self.default = default
    
    class MockTool:
        def __init__(self, name, description):
            self.name = name
            self.description = description
        
        def to_openai_schema(self):
            return {"type": "function", "function": {"name": self.name}}
    
    class WeatherTool(MockTool):
        def __init__(self):
            super().__init__("get_weather", "获取指定城市的天气信息")
        
        def get_parameters(self):
            return [MockToolParameter("city", "string", "城市名称")]
        
        def run(self, params):
            city = params.get("city", "未知")
            weather_data = {
                "北京": "晴，25°C，湿度 45%",
                "上海": "多云，28°C，湿度 65%",
                "深圳": "小雨，30°C，湿度 80%",
            }
            return weather_data.get(city, f"{city}: 暂无数据")
    
    class CalculatorTool(MockTool):
        def __init__(self):
            super().__init__("calculate", "执行数学计算")
        
        def get_parameters(self):
            return [MockToolParameter("expression", "string", "数学表达式")]
        
        def run(self, params):
            expr = params.get("expression", "0")
            try:
                return str(eval(expr))
            except Exception as e:
                return f"计算错误: {e}"
    
    # 创建桥接器
    bridge = ToolBridge(enable_logging=True)
    
    # 添加工具
    bridge.add_tool(WeatherTool())
    bridge.add_tool(CalculatorTool())
    
    print(f"\n2.1 已注册工具: {bridge.list_tools()}")
    
    # 获取工具描述
    print("\n2.2 工具描述:")
    print(bridge.get_tool_descriptions())
    
    # 获取可调用函数
    funcs = bridge.get_callable_functions()
    
    print("\n2.3 调用工具:")
    result = funcs["get_weather"](city="北京")
    print(f"    get_weather('北京') = {result}")
    
    result = funcs["calculate"](expression="100 * 1.5 + 50")
    print(f"    calculate('100 * 1.5 + 50') = {result}")
    
    # 查看调用历史
    print("\n2.4 调用历史:")
    for record in bridge.get_call_history():
        print(f"    - {record.tool_name}: {record.arguments} -> {record.result}")


# ============================================================
# 示例 3: 沙箱 + 工具桥接器 组合使用
# ============================================================
def demo_sandbox_with_bridge():
    """演示沙箱和工具桥接器的组合使用"""
    print("\n" + "=" * 60)
    print("示例 3: 沙箱 + 工具桥接器 组合")
    print("=" * 60)
    
    # 创建简单的工具类
    class MockToolParameter:
        def __init__(self, name, type_, description, required=True, default=None):
            self.name = name
            self.type = type_
            self.description = description
            self.required = required
            self.default = default
    
    class MockTool:
        def __init__(self, name, description):
            self.name = name
            self.description = description
        
        def to_openai_schema(self):
            return {"type": "function", "function": {"name": self.name}}
    
    class SearchTool(MockTool):
        def __init__(self):
            super().__init__("search", "搜索信息")
        
        def get_parameters(self):
            return [MockToolParameter("query", "string", "搜索查询")]
        
        def run(self, params):
            query = params.get("query", "")
            if "天气" in query:
                return "北京天气: 晴朗，温度 25°C，适合出行"
            elif "股票" in query:
                return "茅台股票: 1800元，涨幅 2.5%"
            return f"搜索「{query}」的结果..."
    
    class CalculatorTool(MockTool):
        def __init__(self):
            super().__init__("calc", "计算数学表达式")
        
        def get_parameters(self):
            return [MockToolParameter("expr", "string", "表达式")]
        
        def run(self, params):
            return str(eval(params.get("expr", "0")))
    
    # 1. 创建工具桥接器
    bridge = ToolBridge(enable_logging=True)
    bridge.add_tool(SearchTool())
    bridge.add_tool(CalculatorTool())
    
    # 2. 创建沙箱并注入工具
    sandbox = CodeSandbox(timeout=30)
    
    # 获取可调用函数并注入到沙箱
    funcs = bridge.get_callable_functions()
    sandbox.inject_dict(funcs)
    
    print("\n3.1 可用工具:")
    print(f"    {bridge.list_tools()}")
    
    # 3. 执行复杂的代码，调用多个工具
    print("\n3.2 执行复杂代码（多工具调用）:")
    
    code = '''
# 搜索天气信息
weather_info = search(query="北京天气")
print(f"天气信息: {weather_info}")

# 提取温度
import re
match = re.search(r"(\\d+)°C", weather_info)
celsius = int(match.group(1)) if match else 20

# 温度转换计算
fahrenheit = calc(expr=f"{celsius} * 9/5 + 32")
kelvin = calc(expr=f"{celsius} + 273.15")

# 构建结果
result = f"""
北京天气分析:
- 原始信息: {weather_info}
- 摄氏度: {celsius}°C
- 华氏度: {fahrenheit}°F
- 开尔文: {kelvin}K
"""
'''
    
    result = sandbox.execute(code)
    
    if result.success:
        print(f"    执行成功!")
        print(f"    输出:\n{result.output}")
        if result.stdout:
            print(f"\n    标准输出:\n{result.stdout}")
    else:
        print(f"    执行失败: {result.error}")
    
    # 4. 显示工具调用历史
    print("\n3.3 工具调用历史:")
    for record in bridge.get_call_history():
        print(f"    - {record.tool_name}({record.arguments}) -> {record.result}")


# ============================================================
# 示例 4: 使用 Ollama 运行 ProgrammaticAgent
# ============================================================
def demo_programmatic_agent_with_ollama():
    """使用 Ollama 本地模型运行 ProgrammaticAgent"""
    print("\n" + "=" * 60)
    print("示例 4: 使用 Ollama 运行 ProgrammaticAgent")
    print("=" * 60)
    
    try:
        # 尝试导入完整的包
        from hello_agents.agents import ProgrammaticAgent
        from hello_agents.core.llm import HelloAgentsLLM
        from hello_agents.tools.base import Tool, ToolParameter
    except ImportError as e:
        print(f"\n⚠️  无法导入完整包: {e}")
        print("    请先安装依赖: pip install openai pydantic")
        return
    
    # 创建模拟工具
    class SearchTool(Tool):
        def __init__(self):
            super().__init__("search", "搜索信息")
        
        def get_parameters(self):
            return [ToolParameter(name="query", type="string", description="搜索查询")]
        
        def run(self, params):
            query = params.get("query", "")
            if "天气" in query or "weather" in query.lower():
                return "北京今天天气：晴，温度 25°C，湿度 45%，东风 3 级"
            elif "股票" in query:
                return "茅台股票: 1800元，涨幅 2.5%"
            return f"搜索「{query}」的结果: 这是一个模拟的搜索结果"
    
    class CalculatorTool(Tool):
        def __init__(self):
            super().__init__("calculator", "数学计算")
        
        def get_parameters(self):
            return [ToolParameter(name="expression", type="string", description="数学表达式")]
        
        def run(self, params):
            expr = params.get("expression", "0")
            try:
                return str(eval(expr))
            except Exception as e:
                return f"计算错误: {e}"
    
    print("\n正在连接 Ollama 服务 (http://localhost:11434)...")
    
    try:
        # 创建 Ollama LLM
        # provider="ollama" 会自动使用:
        # - base_url: http://localhost:11434/v1
        # - api_key: ollama
        llm = HelloAgentsLLM(
            provider="ollama",
            model="gpt-oss:120b-cloud",  # 使用 gpt-oss:120b-cloud 模型
        )
        
        print(f"✅ 已连接到 Ollama，使用模型: {llm.model}")
        
        # 创建 ProgrammaticAgent
        agent = ProgrammaticAgent(
            name="OllamaCodeBot",
            llm=llm,
            max_iterations=3,
            sandbox_timeout=30,
        )
        
        # 添加工具
        agent.add_tool(SearchTool())
        agent.add_tool(CalculatorTool())
        
        print(f"可用工具: {agent.list_tools()}")
        
        # 运行 Agent
        print("\n" + "-" * 40)
        print("开始处理任务: 搜索北京天气并转换温度")
        print("-" * 40)
        
        try:
            result = agent.run("搜索北京天气，然后把温度从摄氏度转换为华氏度")
            
            print("\n" + "-" * 40)
            print(f"最终结果:\n{result}")
            print("-" * 40)
            
            # 显示工具调用历史
            print("\n工具调用历史:")
            for record in agent.get_tool_call_history():
                print(f"  - {record['tool_name']}: {record['arguments']}")
                result_str = str(record.get('result', ''))
                print(f"    结果: {result_str[:80]}...")
        
        except Exception as e:
            import traceback
            print(f"\n❌ Agent 运行出错: {type(e).__name__}: {e}")
            print("\n详细错误信息:")
            traceback.print_exc()
        
    except Exception as e:
        import traceback
        print(f"\n❌ 初始化失败: {type(e).__name__}: {e}")
        print("\n详细错误信息:")
        traceback.print_exc()
        print("\n请确保:")
        print("  1. Ollama 服务正在运行: ollama serve")
        print("  2. 已安装模型: ollama pull gpt-oss:120b-cloud")
        print("  3. 已安装依赖: pip install openai pydantic")


# ============================================================
# 示例 5: ProgrammaticAgent 使用说明
# ============================================================
def demo_programmatic_agent_usage():
    """展示 ProgrammaticAgent 的使用方式"""
    print("\n" + "=" * 60)
    print("示例 5: ProgrammaticAgent 使用说明")
    print("=" * 60)
    
    print("""
ProgrammaticAgent 是一个让 LLM 通过编写代码来调用工具的 Agent。

核心特性:
1. LLM 生成 Python 代码而不是指定工具名+参数
2. 代码在安全沙箱中执行
3. 支持复杂的逻辑控制和数据处理
4. 支持多轮代码生成和执行

## 使用 Ollama (本地模型)
""")
    
    print('''
from hello_agents.agents import ProgrammaticAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.tools.builtin import SearchTool, CalculatorTool

# 1. 创建 Ollama LLM (默认地址 http://localhost:11434)
llm = HelloAgentsLLM(
    provider="ollama",
    model="llama3.2",  # 或 "qwen2.5:7b", "mistral", "codellama" 等
)

# 2. 创建 ProgrammaticAgent
agent = ProgrammaticAgent(
    name="CodeBot",
    llm=llm,
    max_iterations=5,
    sandbox_timeout=30,
)

# 3. 添加工具
agent.add_tool(SearchTool())
agent.add_tool(CalculatorTool())

# 4. 运行 Agent
result = agent.run("搜索北京天气，然后将温度转换为华氏度")
print(result)
''')
    
    print("""
## 使用其他 LLM 提供商

```python
# OpenAI
llm = HelloAgentsLLM(provider="openai", model="gpt-4o-mini")

# DeepSeek
llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")

# 通义千问
llm = HelloAgentsLLM(provider="qwen", model="qwen-plus")

# 智谱 AI
llm = HelloAgentsLLM(provider="zhipu", model="glm-4")

# vLLM 本地部署
llm = HelloAgentsLLM(provider="vllm", model="your-model")
```

## Agent 工作流程
1. 接收用户输入
2. 构建系统提示词（包含工具描述）
3. 调用 LLM 生成 Python 代码
4. 在沙箱中执行代码
5. 将执行结果反馈给 LLM
6. 重复直到得出最终答案

## 与传统 Function Calling 的区别
- 传统: LLM 指定工具名和参数 -> 系统调用 -> 返回结果
- 编程式: LLM 生成完整代码 -> 沙箱执行 -> 返回结果

编程式的优势:
- 支持复杂的逻辑控制（if/else, for 循环等）
- 支持数据处理和转换
- 单次调用可以组合多个工具
- 更灵活的错误处理
""")


# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ProgrammaticAgent 使用示例")
    parser.add_argument("--ollama", action="store_true", help="运行 Ollama 完整示例")
    parser.add_argument("--all", action="store_true", help="运行所有示例")
    args = parser.parse_args()
    
    print("=" * 60)
    print("ProgrammaticAgent 使用示例")
    print("=" * 60)
    
    if args.ollama:
        # 只运行 Ollama 示例
        demo_programmatic_agent_with_ollama()
    elif args.all:
        # 运行所有示例
        demo_code_sandbox()
        demo_tool_bridge()
        demo_sandbox_with_bridge()
        demo_programmatic_agent_with_ollama()
        demo_programmatic_agent_usage()
    else:
        # 默认运行基础示例（不需要 LLM）
        demo_code_sandbox()
        demo_tool_bridge()
        demo_sandbox_with_bridge()
        demo_programmatic_agent_usage()
    
    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)
