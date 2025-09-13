import os
from typing import List
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model_name = os.getenv("MODEL_NAME")


# 初始化客户端，使用自定义的 base URL 和 API key
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

# 发送请求示例 - 调用聊天模型
try:
    response = client.chat.completions.create(
        model= model_name,
        messages=[
            {"role": "system", "content": "你是一个 helpful 的助手。"},
            {"role": "user", "content": "Hello, 这是一个测试消息！"}
        ]
    )
    
    # 输出响应结果
    print(response.choices[0].message.content)
    
except Exception as e:
    print(f"调用 API 时发生错误: {e}")

### 构建LLM Client

class LLMClient:
    def __init__(self, api_key = None, base_url = None):
        self.api_key = os.getenv("API_KEY")
        self.base_url = os.getenv("BASE_URL")

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )


    def generate(self, messages: List[dict], model:str = "Qwen/Qwen3-8B", stream: bool = False):
        response = client.chat.completions.create(
        model= model_name,
        messages=messages,
        stream = stream,
        # extra_body = {"enable_thinking": False}
        )
    
        # 输出响应结果
        content = response.choices[0].message.content
        return content