'''
添加计算器、天气工具、网页内容获取工具
'''
import sys
import os
import json

import math
import requests

# 获取当前文件所在目录的上级目录路径
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 将上级目录添加到系统路径
sys.path.append(parent_dir)


from src.tool import tool, get_tools
from src.agent import ReactAgent

@tool
def get_weather(city: str = None) -> str:
    """
    使用wttr.in服务获取指定城市的天气预报信息。

    参数:
        city: 城市名称，例如："北京"、"纽约"、"东京"、"武汉"
        如果为None，将返回当前城市的天气。
    返回:
        str: Markdown格式的天气预报信息。
    """
    try:
        # endpoint = "https://wttr.in/{}?format=j1"
        endpoint = "https://wttr.in/{}"
        if city:
            response = requests.get(endpoint.format(city))
        else:
            response = requests.get(endpoint.format(""))
        response.raise_for_status()
        text_result = response.text
        print(f"Weather data for {city}: \n{text_result}")
        return text_result
    except Exception as e:
        print(f"Error in getting weather for {city}: {str(e)}")
        return json.dumps({"operation": "get_current_weather", "error": str(e)})


# https://github.com/TencentCloudADP/youtu-agent/blob/main/utu/tools/search/jina_crawl.py
class JinaCrawl:
    def __init__(self) -> None:
        self.jina_url = "https://r.jina.ai/"
        self.jina_header = {}
        api_key = os.environ.get("JINA_API_KEY", "")
        if api_key:
            self.jina_header["Authorization"] = f"Bearer {api_key}"
        else:
            # https://jina.ai/api-dashboard/rate-limit
            logger.warning("Jina API key not found! Access rate may be limited.")

    def crawl(self, url: str) -> str:
        """standard crawl interface."""
        return self.crawl_jina(url)

    def crawl_jina(self, url: str) -> str:
        # Get the content of the url
        response = requests.get(self.jina_url + url, headers=self.jina_header)

        try:
            text = response.text
            return text
        except Exception as e:
            return f"error: {str(e)}"

@tool
def fetch_web_content(url: str, query: str) -> str:
    """Ask question to a webpage, you will get the answer and related links from the specified url.

    Tips:
    - Use cases: gather information from a webpage, ask detailed questions.

    Args:
        url (str): The url to ask question to.
        query (str): The question to ask. Should be clear, concise, and specific.
    """
    crawl_engine = JinaCrawl()

    print(f"[tool] fetch_web_content: {url}, {query}")
    content = crawl_engine.crawl(url) 

    return content


@tool
def calculate(expression: str) -> str:
    """
    执行数学计算，支持加减乘除、幂运算及基础函数（sin/cos/sqrt等）
    
    Args:
        expression: 数学表达式字符串，例如"2+3*4"、"sqrt(16)"、"sin(pi/2)"
    
    Returns:
        计算结果或错误信息
    """
    try:
        # 安全执行数学计算，限制可用函数
        allowed = {
            'math': math,
            'pi': math.pi,
            'e': math.e
        }
        result = eval(expression, {"__builtins__": None}, allowed)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}. 请检查表达式格式"


if __name__ == "__main__":
    tools = get_tools(["calculate", "get_weather", "fetch_web_content"])
    agent = ReactAgent(instructions = "你是一个闲聊机器人小蛋", tools = tools)
    # print(agent.run("你是谁"))
    # print(agent.run("请问1+32x777+3023="))
    print(agent.run("上海天气怎么样"))

