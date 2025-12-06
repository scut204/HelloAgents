#!/usr/bin/env python3
"""第八章：Mem0 AI 记忆系统演示

展示如何使用 Mem0 AI 记忆系统来增强 HelloAgents 框架中的 Agent，
实现智能化的对话记忆管理功能。

本文件展示：
1. 🧠 Mem0Memory 基础使用：记忆的添加、检索、更新和删除
2. 💬 对话记忆提取：自动从对话中提取重要信息
3. 🔍 语义搜索：基于语义的智能记忆检索
4. 🤖 SimpleAgent + Mem0MemoryTool：智能记忆助手
5. 🔄 与现有记忆系统的对比

特色功能：
- 自动记忆提取：从对话中智能提取和存储重要信息
- 语义搜索：基于语义相似度的记忆检索
- 用户隔离：每个用户的记忆独立管理
- 云端/本地双模式：支持 Mem0 Cloud 或本地部署

使用前请确保：
1. 安装 mem0ai: pip install mem0ai
2. 配置 OpenAI API Key（用于 LLM 和 Embedding）
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def check_dependencies():
    """检查依赖是否满足"""
    print("🔍 检查依赖...")
    
    # 检查 mem0ai
    try:
        from hello_agents.memory.types.mem0 import is_mem0_available
        if is_mem0_available():
            print("  ✅ mem0ai 已安装")
            return True
        else:
            print("  ⚠️ mem0ai 未安装")
            print("     请运行: pip install mem0ai")
            return False
    except ImportError:
        print("  ⚠️ mem0ai 未安装")
        print("     请运行: pip install mem0ai")
        return False


def demo_mem0_memory_basic():
    """演示1: Mem0Memory 基础使用"""
    print("\n" + "=" * 60)
    print("🧠 演示1: Mem0Memory 基础使用")
    print("=" * 60)
    
    from hello_agents.memory import Mem0Memory, Mem0MemoryConfig, MemoryItem
    from datetime import datetime
    
    # 创建配置
    print("\n📋 创建 Mem0 配置...")
    config = Mem0MemoryConfig(
        use_local_mode=True,
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        embedder_provider="openai",
        embedder_model="text-embedding-3-small"
    )
    
    # 创建记忆实例
    memory = Mem0Memory(config=config, user_id="demo_user_001")
    print(f"  用户ID: demo_user_001")
    print(f"  Mem0 可用: {memory.is_available}")
    print(f"  运行模式: {'本地' if config.use_local_mode else '云端'}")
    
    # 添加记忆
    print("\n📝 添加记忆...")
    memories_to_add = [
        "我是一名软件工程师，专注于Python开发",
        "我正在学习机器学习和深度学习",
        "我喜欢使用VSCode作为主要的开发工具"
    ]
    
    for i, content in enumerate(memories_to_add, 1):
        memory_item = MemoryItem(
            id=f"demo_memory_{i}",
            content=content,
            memory_type="mem0",
            user_id="demo_user_001",
            timestamp=datetime.now(),
            importance=0.7 + i * 0.05,
            metadata={"source": "demo"}
        )
        memory.add(memory_item)
        print(f"  ✅ 记忆 {i}: {content[:40]}...")
    
    # 检索记忆
    print("\n🔍 检索记忆...")
    search_queries = ["Python开发", "学习", "工具"]
    
    for query in search_queries:
        results = memory.retrieve(query, limit=2)
        print(f"\n  查询: '{query}'")
        if results:
            for j, result in enumerate(results, 1):
                print(f"    {j}. {result.content[:50]}... (重要性: {result.importance:.2f})")
        else:
            print("    未找到相关记忆")
    
    # 获取统计信息
    print("\n📊 统计信息:")
    stats = memory.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 清空记忆
    print("\n🧹 清空记忆...")
    memory.clear()
    print("  ✅ 记忆已清空")
    
    return memory


def demo_conversation_memory():
    """演示2: 对话记忆提取"""
    print("\n" + "=" * 60)
    print("💬 演示2: 对话记忆提取")
    print("=" * 60)
    
    from hello_agents.memory import Mem0Memory, Mem0MemoryConfig
    
    # 创建记忆实例
    config = Mem0MemoryConfig(use_local_mode=True)
    memory = Mem0Memory(config=config, user_id="conversation_user")
    
    # 模拟对话
    conversations = [
        [
            {"role": "user", "content": "你好！我叫张三，是一名数据科学家"},
            {"role": "assistant", "content": "你好张三！很高兴认识你。作为数据科学家，你主要使用什么工具和技术呢？"}
        ],
        [
            {"role": "user", "content": "我主要使用Python和R语言，以及TensorFlow和PyTorch框架"},
            {"role": "assistant", "content": "这些都是非常强大的工具！Python和R是数据科学的主流语言，TensorFlow和PyTorch则是深度学习的两大主流框架。"}
        ],
        [
            {"role": "user", "content": "我最近在研究大语言模型，特别是如何用于金融数据分析"},
            {"role": "assistant", "content": "这是一个很有前景的研究方向！LLM在金融领域有很多应用场景，比如情感分析、风险评估、报告生成等。"}
        ]
    ]
    
    print("\n💭 处理对话并提取记忆...")
    
    for i, conv in enumerate(conversations, 1):
        print(f"\n  对话 {i}:")
        for msg in conv:
            role_emoji = "👤" if msg["role"] == "user" else "🤖"
            print(f"    {role_emoji} {msg['role']}: {msg['content'][:50]}...")
        
        result = memory.add_from_messages(conv)
        
        if isinstance(result, dict):
            if result.get("status") == "stored_locally":
                print(f"    📝 已存储到本地缓存")
            elif "results" in result:
                extracted = result.get("results", [])
                print(f"    📝 提取了 {len(extracted)} 条记忆")
                for mem in extracted[:2]:
                    print(f"      • {mem.get('memory', '')[:40]}...")
    
    # 搜索记忆
    print("\n🔍 搜索对话记忆...")
    queries = ["张三的职业", "使用的工具", "研究方向"]
    
    for query in queries:
        results = memory.search(query, limit=2)
        print(f"\n  查询: '{query}'")
        if results:
            for j, r in enumerate(results, 1):
                print(f"    {j}. {r.get('memory', '')[:50]}...")
        else:
            print("    未找到相关记忆")
    
    # 获取所有记忆
    print("\n📋 所有记忆:")
    all_memories = memory.get_all(limit=10)
    for i, mem in enumerate(all_memories[:5], 1):
        print(f"  {i}. {mem.get('memory', '')[:60]}...")
    
    if len(all_memories) > 5:
        print(f"  ... 还有 {len(all_memories) - 5} 条记忆")
    
    return memory


def demo_mem0_tool():
    """演示3: Mem0MemoryTool 工具使用"""
    print("\n" + "=" * 60)
    print("🔧 演示3: Mem0MemoryTool 工具使用")
    print("=" * 60)
    
    from hello_agents.tools import Mem0MemoryTool
    
    # 创建工具
    print("\n🛠️ 创建 Mem0MemoryTool...")
    tool = Mem0MemoryTool(
        user_id="tool_demo_user",
        use_local_mode=True,
        llm_provider="openai",
        llm_model="gpt-4o-mini"
    )
    
    print(f"  工具名称: {tool.name}")
    print(f"  工具描述: {tool.description[:50]}...")
    print(f"  是否可用: {tool.is_available}")
    
    # 演示各种操作
    operations = [
        {
            "desc": "添加记忆",
            "params": {
                "action": "add",
                "content": "用户喜欢阅读科技新闻，特别是AI相关的内容"
            }
        },
        {
            "desc": "添加对话",
            "params": {
                "action": "add_conversation",
                "messages": [
                    {"role": "user", "content": "我每天早上都会浏览Hacker News"},
                    {"role": "assistant", "content": "Hacker News是获取技术资讯的好渠道！"}
                ]
            }
        },
        {
            "desc": "搜索记忆",
            "params": {
                "action": "search",
                "query": "阅读习惯",
                "limit": 3
            }
        },
        {
            "desc": "获取所有记忆",
            "params": {
                "action": "get_all",
                "limit": 5
            }
        },
        {
            "desc": "获取统计",
            "params": {
                "action": "stats"
            }
        }
    ]
    
    print("\n📋 执行工具操作...")
    
    for op in operations:
        print(f"\n  ▶️ {op['desc']}:")
        result = tool.run(op["params"])
        # 格式化输出
        for line in result.split("\n")[:5]:
            print(f"    {line}")
        if result.count("\n") > 4:
            print("    ...")
    
    # 演示便捷方法
    print("\n🔄 使用便捷方法...")
    
    # 自动记录对话
    tool.auto_record_conversation(
        user_input="我想学习Rust语言",
        agent_response="Rust是一门系统级编程语言，以安全性和性能著称。"
    )
    print("  ✅ 对话已自动记录")
    
    # 获取上下文
    context = tool.get_context_for_query("编程语言")
    print(f"  📎 查询上下文: {context[:100] if context else '(无)'}")
    
    # 清空
    print("\n🧹 清空记忆...")
    result = tool.run({"action": "clear"})
    print(f"  {result}")
    
    return tool


def demo_agent_with_mem0():
    """演示4: SimpleAgent + Mem0MemoryTool"""
    print("\n" + "=" * 60)
    print("🤖 演示4: SimpleAgent + Mem0MemoryTool")
    print("=" * 60)
    
    try:
        from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
        from hello_agents.tools import Mem0MemoryTool
    except ImportError as e:
        print(f"  ⚠️ 导入失败: {e}")
        print("  请确保已正确安装 hello_agents")
        return None
    
    # 检查 API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("  ⚠️ 未设置 OPENAI_API_KEY")
        print("  请设置环境变量后重试")
        return None
    
    print("\n🛠️ 创建智能记忆助手...")
    
    # 创建 LLM
    llm = HelloAgentsLLM()
    
    # 创建 Mem0 记忆工具
    mem0_tool = Mem0MemoryTool(
        user_id="smart_assistant_user",
        use_local_mode=True
    )
    
    # 创建工具注册表
    tool_registry = ToolRegistry()
    tool_registry.register_tool(mem0_tool)
    
    # 创建 Agent
    agent = SimpleAgent(
        name="智能记忆助手",
        llm=llm,
        tool_registry=tool_registry,
        system_prompt="""你是一个具有智能记忆能力的AI助手。你能够：
1. 记住用户的重要信息（姓名、职业、兴趣等）
2. 从对话中自动提取和存储有价值的信息
3. 在回答时参考相关的历史记忆
4. 提供个性化的建议和服务

工具使用说明：
- 添加记忆: [TOOL_CALL:mem0:action=add,content=记忆内容]
- 搜索记忆: [TOOL_CALL:mem0:action=search,query=查询内容]
- 获取统计: [TOOL_CALL:mem0:action=stats]

请主动记录用户的重要信息，并在合适的时候引用历史记忆。"""
    )
    
    print(f"  Agent 名称: {agent.name}")
    print(f"  已注册工具: {list(tool_registry.list_tools().keys())}")
    
    # 模拟对话
    conversations = [
        "你好！我是李明，是一名前端工程师，主要使用React和Vue框架",
        "我最近在学习TypeScript，感觉类型系统很有用",
        "你还记得我的职业和正在学习什么吗？"
    ]
    
    print("\n💬 开始智能对话...")
    
    for i, user_input in enumerate(conversations, 1):
        print(f"\n--- 对话 {i} ---")
        print(f"👤 用户: {user_input}")
        
        try:
            response = agent.run(user_input)
            print(f"🤖 助手: {response[:200]}...")
        except Exception as e:
            print(f"⚠️ 响应失败: {e}")
    
    # 显示记忆统计
    print("\n📊 记忆系统状态:")
    stats_result = mem0_tool.run({"action": "stats"})
    print(stats_result)
    
    return agent, mem0_tool


def demo_comparison_with_memory_tool():
    """演示5: 与现有 MemoryTool 的对比"""
    print("\n" + "=" * 60)
    print("🔄 演示5: Mem0MemoryTool vs MemoryTool 对比")
    print("=" * 60)
    
    from hello_agents.tools import MemoryTool, Mem0MemoryTool
    
    print("\n📊 功能对比:")
    print("""
┌────────────────────┬──────────────────────┬──────────────────────┐
│ 功能特性           │ MemoryTool           │ Mem0MemoryTool       │
├────────────────────┼──────────────────────┼──────────────────────┤
│ 记忆类型           │ 工作/情景/语义/感知  │ 统一智能记忆         │
│ 记忆提取方式       │ 手动添加             │ 自动从对话提取       │
│ 检索方式           │ 关键词 + TF-IDF      │ 语义向量检索         │
│ 存储后端           │ SQLite + Qdrant      │ Mem0 内置向量库      │
│ 用户隔离           │ 支持                 │ 原生支持             │
│ 记忆历史           │ 不支持               │ 支持版本追踪         │
│ 部署模式           │ 本地                 │ 本地/云端            │
│ 依赖复杂度         │ 低                   │ 中（需要 LLM）       │
└────────────────────┴──────────────────────┴──────────────────────┘
    """)
    
    print("\n💡 使用建议:")
    print("""
1. 使用 MemoryTool 的场景：
   - 需要细粒度控制不同类型的记忆
   - 不需要自动记忆提取
   - 希望减少外部依赖
   - 离线环境或有限资源

2. 使用 Mem0MemoryTool 的场景：
   - 需要自动从对话中提取记忆
   - 需要更智能的语义搜索
   - 需要记忆版本追踪
   - 需要云端同步（Mem0 Cloud）

3. 组合使用：
   - 可以同时使用两种工具
   - MemoryTool 用于结构化数据
   - Mem0MemoryTool 用于对话记忆
    """)
    
    # 简单的功能演示
    print("\n🔧 功能演示对比:")
    
    # MemoryTool
    print("\n  📌 MemoryTool:")
    memory_tool = MemoryTool(user_id="compare_user")
    result1 = memory_tool.run({
        "action": "add",
        "content": "用户喜欢Python编程",
        "memory_type": "semantic",
        "importance": 0.8
    })
    print(f"    添加语义记忆: {result1}")
    
    result2 = memory_tool.run({
        "action": "search",
        "query": "Python"
    })
    print(f"    搜索结果: {result2[:80]}...")
    
    # Mem0MemoryTool
    print("\n  📌 Mem0MemoryTool:")
    mem0_tool = Mem0MemoryTool(user_id="compare_user")
    result3 = mem0_tool.run({
        "action": "add_conversation",
        "messages": [
            {"role": "user", "content": "我喜欢Python编程"},
            {"role": "assistant", "content": "Python是很棒的语言！"}
        ]
    })
    print(f"    添加对话记忆: {result3[:80]}...")
    
    result4 = mem0_tool.run({
        "action": "search",
        "query": "Python"
    })
    print(f"    搜索结果: {result4[:80]}...")
    
    return memory_tool, mem0_tool


def show_system_capabilities():
    """展示系统能力总结"""
    print("\n" + "=" * 60)
    print("🎯 Mem0 AI 记忆系统能力总结")
    print("=" * 60)
    
    print("""
🧠 Mem0Memory 核心能力:
  ✅ 智能记忆提取：自动从对话中提取重要信息
  ✅ 语义向量检索：基于语义相似度的智能搜索
  ✅ 用户记忆隔离：每个用户的记忆独立管理
  ✅ 记忆版本追踪：支持查看记忆的历史变更
  ✅ 双模式部署：支持本地模式和 Mem0 Cloud

🔧 Mem0MemoryTool 功能:
  ✅ add - 添加单条记忆
  ✅ add_conversation - 从对话提取记忆
  ✅ search - 语义搜索记忆
  ✅ get_all - 获取所有记忆
  ✅ update - 更新记忆内容
  ✅ delete - 删除记忆
  ✅ history - 查看记忆历史
  ✅ stats - 获取统计信息
  ✅ clear - 清空所有记忆

🚀 使用场景:
  ✅ 个人AI助手：记住用户偏好和历史
  ✅ 客服系统：记录客户信息和问题历史
  ✅ 教育助手：跟踪学生学习进度和难点
  ✅ 健康助手：记录健康数据和建议历史
  ✅ 智能家居：记住用户习惯和偏好设置

💡 配置说明:
  • 本地模式：需要 OpenAI API Key（LLM + Embedding）
  • 云端模式：需要 Mem0 Cloud API Key
  • 支持自定义 LLM 和 Embedding 提供商
    """)


def main():
    """主函数 - Mem0 AI 记忆系统演示"""
    print("🎯 第八章：Mem0 AI 记忆系统演示")
    print("展示如何使用 Mem0 AI 记忆系统增强 HelloAgents 框架")
    print("=" * 70)
    
    # 检查依赖
    has_mem0 = check_dependencies()
    
    # 显示菜单
    print("\n请选择演示类型：")
    print("1. 🧠 Mem0Memory 基础使用")
    print("2. 💬 对话记忆提取")
    print("3. 🔧 Mem0MemoryTool 工具使用")
    print("4. 🤖 SimpleAgent + Mem0MemoryTool")
    print("5. 🔄 与 MemoryTool 对比")
    print("6. 🎪 完整演示（运行所有）")
    
    if not has_mem0:
        print("\n⚠️ 注意: mem0ai 未安装，部分功能将在降级模式下运行")
    
    try:
        choice = input("\n请输入选择 (1-6): ").strip()
        
        if choice == "1" or choice == "6":
            demo_mem0_memory_basic()
        
        if choice == "2" or choice == "6":
            demo_conversation_memory()
        
        if choice == "3" or choice == "6":
            demo_mem0_tool()
        
        if choice == "4" or choice == "6":
            demo_agent_with_mem0()
        
        if choice == "5" or choice == "6":
            demo_comparison_with_memory_tool()
        
        if choice == "6":
            show_system_capabilities()
        
        print("\n" + "=" * 70)
        print("🎉 演示完成！")
        
        if choice == "1":
            print("\n💡 Mem0Memory 基础使用特点:")
            print("  ✅ 统一的记忆管理接口")
            print("  ✅ 支持多种操作：添加、检索、更新、删除")
            print("  ✅ 自动降级到本地缓存模式")
        elif choice == "2":
            print("\n💡 对话记忆提取特点:")
            print("  ✅ 自动从对话中提取重要信息")
            print("  ✅ 支持多轮对话处理")
            print("  ✅ 语义搜索和关联")
        elif choice == "3":
            print("\n💡 Mem0MemoryTool 特点:")
            print("  ✅ 符合 HelloAgents 工具规范")
            print("  ✅ 支持所有 Mem0 操作")
            print("  ✅ 便捷的上下文获取方法")
        elif choice == "4":
            print("\n💡 智能记忆助手特点:")
            print("  ✅ 自动记录对话历史")
            print("  ✅ 智能引用历史记忆")
            print("  ✅ 个性化服务能力")
        elif choice == "5":
            print("\n💡 工具对比总结:")
            print("  ✅ MemoryTool: 结构化、细粒度控制")
            print("  ✅ Mem0MemoryTool: 智能化、自动提取")
            print("  ✅ 可根据场景选择或组合使用")
        elif choice == "6":
            print("\n🚀 Mem0 AI 记忆系统展现了强大的智能记忆能力！")
        
        print("✅ HelloAgents Mem0 记忆系统运行正常")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断演示")
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {str(e)}")
        print("请检查依赖是否正确安装")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
