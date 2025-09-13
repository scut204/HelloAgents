import os
from typing import List, Optional
from openai import OpenAI


class LLMClient:
    """LLM客户端类，用于调用指定的语言模型API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化LLM客户端
        
        参数:
            api_key: API密钥，若未提供则从环境变量获取
            base_url: API基础地址，若未提供则从环境变量获取
        """
        # 优先使用传入的参数，若无则从环境变量获取
        self.api_key = api_key or os.getenv("API_KEY")
        self.base_url = base_url or os.getenv("BASE_URL")

        # 验证必要配置
        if not self.api_key:
            raise ValueError("API密钥未提供，请通过参数或环境变量设置API_KEY")
        if not self.base_url:
            raise ValueError("API基础地址未提供，请通过参数或环境变量设置BASE_URL")
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def generate(self, 
                 messages: List[dict], 
                 model: str = "Qwen/Qwen3-8B", 
                 stream: bool = False) -> str:
        """
        调用模型生成响应
        
        参数:
            messages: 消息列表，格式为[{"role": "...", "content": "..."}]
            model: 模型名称
            stream: 是否流式返回
        
        返回:
            模型生成的内容
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=stream,
                # 如需启用思考链可取消下面注释
                # extra_body={"enable_thinking": False}
            )
            
            # 非流式返回时获取内容
            if not stream:
                return response.choices[0].message.content
            
            # 流式返回时处理
            content = []
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content.append(chunk.choices[0].delta.content)
            return ''.join(content)
            
        except Exception as e:
            raise RuntimeError(f"模型调用失败: {str(e)}") from e

    def __call__(self, 
                 messages: List[dict], 
                 model: str = "Qwen/Qwen3-8B", 
                 stream: bool = False) -> str:
        """
        使实例可调用，内部调用generate方法
        
        参数:
            messages: 消息列表，格式为[{"role": "...", "content": "..."}]
            model: 模型名称
            stream: 是否流式返回
        
        返回:
            模型生成的内容
        """
        return self.generate(messages, model, stream)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    messages=[
            {"role": "system", "content": "你是一个 helpful 的助手。"},
            {"role": "user", "content": "1+1=?"}
        ]

    llm = LLMClient()
    print(llm(messages))
    # print(llm.generate(messages))
