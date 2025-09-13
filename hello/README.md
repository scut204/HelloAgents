# @file: README.md
# @date: 2025/01/15
# @author: jiaohui
# @description: Hello Agents - React Agent教学项目

# Hello Agents 🤖

一个基于ReAct模式的AI Agent教学项目，旨在帮助开发者理解和实现智能代理系统。

## 📋 项目概述

本项目实现了一个完整的ReAct (Reasoning and Acting) Agent框架，包含：

- **ReAct Agent**: 基于思考-行动-观察循环的智能代理
- **工具系统**: 可扩展的工具注册和调用机制  
- **LLM客户端**: 统一的大语言模型调用接口
- **多Agent架构**: 支持多智能体协作的团队框架

## 🏗️ 项目架构

```
hello/
├── src/                    # 核心源码
│   ├── agent.py           # ReactAgent核心实现
│   ├── llm.py             # LLM客户端封装
│   ├── tool.py            # 工具系统和装饰器
│   ├── team.py            # 多Agent团队管理
│   └── utils/             # 工具函数
│       ├── completions.py # 对话历史管理
│       └── extraction.py  # 标签内容提取
├── tests/                 # 测试用例
│   ├── test_react.py      # ReAct Agent测试
│   ├── test_tool.py       # 工具系统测试
│   └── test_client.py     # LLM客户端测试
├── requirements.txt       # 依赖包列表
├── env.example           # 环境变量示例
└── README.md             # 项目文档
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd hello

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp env.example .env
# 编辑.env文件，填入你的API配置
```

### 2. 环境变量配置

在`.env`文件中配置以下参数：

```bash
API_KEY=your_api_key_here
BASE_URL=https://api.siliconflow.cn/v1
MODEL_NAME=Qwen/Qwen3-8B
```

### 3. 运行示例

```bash
# 运行ReAct Agent测试
python tests/test_react.py

# 运行工具系统测试  
python tests/test_tool.py

# 运行LLM客户端测试
python tests/test_client.py
```

## 🔧 核心组件

### ReactAgent

基于ReAct模式的智能代理，支持：
- 思考-行动-观察循环
- 工具调用和结果处理
- 多轮对话管理
- 错误处理和恢复

```python
from src.agent import ReactAgent
from src.tool import get_tools

# 创建Agent
tools = get_tools(["calculate", "get_weather"])
agent = ReactAgent(
    instructions="你是一个智能助手",
    tools=tools
)

# 运行对话
result = agent.run("请计算1+2*3的结果")
print(result)
```

### 工具系统

简单易用的工具注册和调用机制：

```python
from src.tool import tool

@tool
def calculate(expression: str) -> str:
    """执行数学计算"""
    try:
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"
```

### LLM客户端

统一的大语言模型调用接口：

```python
from src.llm import LLMClient

llm = LLMClient()
messages = [
    {"role": "system", "content": "你是一个助手"},
    {"role": "user", "content": "你好"}
]
response = llm(messages)
```

## 🛠️ 内置工具

项目包含以下预置工具：

1. **计算器 (calculate)**: 执行数学表达式计算
2. **天气查询 (get_weather)**: 获取指定城市天气信息
3. **网页抓取 (fetch_web_content)**: 获取网页内容

## 📚 使用示例

### 基础对话

```python
from src.agent import ReactAgent

agent = ReactAgent(instructions="你是一个友好的助手")
response = agent.run("你好，请介绍一下自己")
```

### 工具调用

```python
from src.agent import ReactAgent
from src.tool import get_tools

tools = get_tools(["calculate"])
agent = ReactAgent(
    instructions="你是一个数学助手",
    tools=tools
)
response = agent.run("请计算 (2+3)*4 的结果")
```

### 多轮对话

```python
agent = ReactAgent(tools=get_tools(["calculate", "get_weather"]))

# 第一轮：数学计算
result1 = agent.run("计算1+1")

# 第二轮：天气查询  
result2 = agent.run("北京今天天气如何")
```

## 🔄 开发进度

- [x] 1. OpenAI API调用
- [x] 2. LLM客户端构建
- [x] 3. 工具系统实现
- [x] 4. ReAct Agent核心逻辑
- [ ] 5. 多Agent架构设计
- [ ] 6. 团队协作机制
- [ ] 7. 架构优化重构

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- 感谢 OpenAI 提供的强大API
- 感谢开源社区的贡献和支持
- 参考了多个优秀的Agent框架设计

---

**Happy Coding! 🎉**
