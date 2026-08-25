import httpx

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


class LLMService:
    """负责调用大语言模型服务。"""

    def __init__(self) -> None:
        self.api_key = LLM_API_KEY
        self.base_url = LLM_BASE_URL
        self.model = LLM_MODEL

    def is_configured(self) -> bool:
        """判断大模型配置是否完整。"""
        return bool(
            self.api_key
            and self.base_url
            and self.model
        )

    async def chat(self, message: str) -> str:
        """向大模型发送一条用户消息并返回回答。"""
        if not self.is_configured():
            raise ValueError("大模型配置不完整，请检查 .env")

        url = f"{self.base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个回答简洁、准确的 AI 助手。",
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RuntimeError("大模型请求超时") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise RuntimeError(
                f"大模型服务返回错误状态码：{status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError("无法连接大模型服务") from exc

        
        try:
            data = response.json()
            # response.json() 不是“得到 JSON 类型”，而是把 JSON 数据解析成 Python 对象。
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("大模型返回格式异常") from exc

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("大模型返回了空内容")

        return content        
